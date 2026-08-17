#!/usr/bin/env python3
"""
Simulacion local del prototipo de clasificacion de tickets (Trabajo de Grado).

No se autorizo el acceso a la API de Plumsail Helpdesk de la empresa (temas de
seguridad). Por lo tanto, el prototipo NO se conecta a ningun sistema real de
la empresa: no hay Plumsail, no hay Azure, no hay SharePoint. Es un prototipo
100% autocontenido y local.

Cada ticket se califica en 4 datos que decide el LLM (categoria, confianza,
prioridad sugerida, comercio sugerido) y 2 que se calculan con reglas
deterministas de negocio (fecha de vencimiento sugerida y responsable
sugerido -- ver classifier/routing.py).

Requisitos:
    pip install -r requirements.txt
    Ollama instalado y corriendo, con el modelo descargado:
        ollama pull qwen3:14b
"""
import os
import sys
import json
from datetime import datetime
from openpyxl import Workbook

sys.path.insert(0, os.path.dirname(__file__))
from classifier.html_cleaner import clean_html_to_text  # noqa: E402
from classifier.prompt_builder import (  # noqa: E402
    get_config,
    build_system_prompt,
    build_user_prompt,
    valid_category_ids,
)
from classifier.ollama_client import classify_ticket, LLMClassificationError  # noqa: E402
from classifier.routing import sugerir_fecha_vencimiento, sugerir_responsable  # noqa: E402

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "tickets_sinteticos.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "outputs", "resultado_simulacion.xlsx")

EXCEL_HEADERS = [
    "TicketId", "Asunto", "Categoria", "Confianza", "PrioridadSugerida",
    "ComercioSugerido", "FechaVencimientoSugerida", "ResponsableSugerido",
    "InformacionCompleta", "CamposFaltantes",
    "Resumen", "AccionSugerida", "Razonamiento", "OtrasEntidades",
    "AccionRecomendada", "Fecha",
]


def _excel_safe(value):
    """El modelo a veces se sale del schema pedido. openpyxl no acepta
    listas/dicts como valor de celda -- esto los convierte a texto en vez
    de romper el script."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def load_synthetic_tickets():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    tickets = load_synthetic_tickets()
    print(f"Tickets sinteticos cargados: {len(tickets)}\n")

    config = get_config()
    system_prompt = build_system_prompt(config)
    threshold_high = config["confidence_thresholds"]["high"]
    threshold_low = config["confidence_thresholds"]["low"]

    wb = Workbook()
    ws = wb.active
    ws.title = "ResultadoSimulacion"
    ws.append(EXCEL_HEADERS)

    contador_por_categoria = {}
    contador_por_accion = {"auto_update": 0, "revision_normal": 0, "revision_prioritaria": 0}

    for ticket in tickets:
        clean_body = clean_html_to_text(ticket.get("firstComment", ""))
        user_prompt = build_user_prompt(ticket, clean_body)

        try:
            result = classify_ticket(system_prompt, user_prompt)
        except LLMClassificationError as e:
            print(f"  [!] Error clasificando ticket {ticket.get('id')}: {e}")
            continue

        confidence = result.get("confidence", 0)
        category_id = result.get("category_id")
        if category_id not in valid_category_ids(config):
            confidence = 0

        if confidence >= threshold_high:
            accion = "auto_update"
        elif confidence >= threshold_low:
            accion = "revision_normal"
        else:
            accion = "revision_prioritaria"

        informacion_completa = result.get("informacion_completa", True)
        campos_faltantes = result.get("campos_faltantes", []) or []
        if isinstance(campos_faltantes, str):
            campos_faltantes = [campos_faltantes]

        # Un Incidente sin los 3 datos minimos nunca se auto-actualiza, sin
        # importar la confianza -- un desarrollador no podria trabajarlo.
        if category_id == "Incidente" and not informacion_completa:
            accion = "revision_prioritaria"

        contador_por_accion[accion] += 1
        contador_por_categoria[category_id] = contador_por_categoria.get(category_id, 0) + 1

        prioridad_sugerida = result.get("prioridad_sugerida") or "Normal"
        comercio_sugerido = result.get("comercio_sugerido") or "No identificado"
        fecha_vencimiento_sugerida = sugerir_fecha_vencimiento(prioridad_sugerida)
        responsable_sugerido = sugerir_responsable(category_id, comercio_sugerido)

        entities = result.get("extracted_entities", {}) or {}

        ws.append([
            ticket.get("id"),
            ticket.get("subject"),
            _excel_safe(category_id),
            confidence,
            _excel_safe(prioridad_sugerida),
            _excel_safe(comercio_sugerido),
            fecha_vencimiento_sugerida,
            _excel_safe(responsable_sugerido),
            "Sí" if informacion_completa else "No",
            _excel_safe(", ".join(campos_faltantes)),
            _excel_safe(result.get("summary")),
            _excel_safe(result.get("suggested_action")),
            _excel_safe(result.get("reasoning")),
            _excel_safe(entities),
            accion,
            datetime.now().isoformat(timespec="seconds"),
        ])

        print(f"  Ticket {ticket.get('id')} ({ticket.get('subject')[:40]}...)")
        print(f"    -> {category_id} | confianza={confidence:.2f} | prioridad={prioridad_sugerida} | comercio={comercio_sugerido}")
        if category_id == "Incidente":
            print(f"    -> info completa={informacion_completa} | faltantes={campos_faltantes}")
        print(f"    -> vence={fecha_vencimiento_sugerida} | responsable={responsable_sugerido} | accion={accion}\n")

    wb.save(OUTPUT_PATH)

    print("=" * 60)
    print("RESUMEN DE LA SIMULACION")
    print("=" * 60)
    print("Por categoria:")
    for cat, count in sorted(contador_por_categoria.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")
    print("\nPor accion recomendada:")
    for accion, count in contador_por_accion.items():
        print(f"  {accion}: {count}")
    print(f"\nReporte completo guardado en: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
