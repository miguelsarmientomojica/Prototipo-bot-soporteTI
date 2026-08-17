#!/usr/bin/env python3
"""
Dashboard en vivo -- genera tickets sinteticos (automaticos o manuales) y los
clasifica con el LLM local (Ollama) en tiempo real. Cada resultado incluye:
categoria, confianza, prioridad sugerida, comercio sugerido (todo decidido
por el LLM), y fecha de vencimiento sugerida + responsable sugerido (estos
dos calculados con reglas deterministas en classifier/routing.py, no por el
LLM -- ver el docstring de ese modulo para el porque).

FASE 2 de la hoja de ruta: ya no guarda nada en variables Python en memoria
-- todo se persiste en database.py (SQLite). Si reinicias este proceso, los
tickets siguen ahi (antes se perdian).

No se conecta a ningun sistema real de la empresa.

Uso:
    cd dashboard
    python app.py
Luego abre http://localhost:5000 en el navegador.
"""
import os
import sys
import time

from flask import Flask, jsonify, render_template, request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import database  # noqa: E402
from classifier.html_cleaner import clean_html_to_text  # noqa: E402
from classifier.prompt_builder import (  # noqa: E402
    get_config,
    build_system_prompt,
    build_user_prompt,
    valid_category_ids,
)
from classifier.ollama_client import classify_ticket, LLMClassificationError  # noqa: E402
from classifier.ticket_generator import generate_random_ticket, COMERCIOS  # noqa: E402
from classifier.routing import sugerir_fecha_vencimiento, sugerir_responsable  # noqa: E402

app = Flask(__name__)
database.init_db()  # crea las tablas si no existen -- no borra nada si ya existian

_config = get_config()
_system_prompt = build_system_prompt(_config)
_threshold_high = _config["confidence_thresholds"]["high"]
_threshold_low = _config["confidence_thresholds"]["low"]


def _safe_entity(value):
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    if isinstance(value, dict):
        return ", ".join(f"{k}: {v}" for k, v in value.items())
    return value if value else ""


def _clasificar_y_responder(ticket_raw, origen):
    """Logica compartida entre el modo automatico y el manual.

    A diferencia de la Fase 1 (memoria), el ticket se guarda en la base de
    datos ANTES de clasificarlo -- asi el id que se muestra en pantalla es
    el id real asignado por SQLite (autoincrement), no un contador manual
    en Python. Si la clasificacion falla, el ticket igual queda guardado
    (con la clasificacion marcando el error), en vez de perderse.
    """
    clean_body = clean_html_to_text(ticket_raw.get("firstComment", ""))
    solicitante = ticket_raw["requester"]["title"]
    rol = ticket_raw["requester"].get("role", "Member")
    tags = [t["title"] for t in ticket_raw.get("tags", [])]
    comercio = tags[0] if tags else ""

    ticket_id = database.crear_ticket({
        "subject": ticket_raw["subject"],
        "body": clean_body,
        "solicitante": solicitante,
        "rol": rol,
        "comercio": comercio,
        "tags": tags,
        "origen": origen,
    })

    ticket_para_prompt = {
        "subject": ticket_raw["subject"],
        "category": ticket_raw.get("category"),
        "priority": ticket_raw.get("priority", "Normal"),
        "tags": ticket_raw.get("tags", []),
        "requester": ticket_raw["requester"],
    }
    user_prompt = build_user_prompt(ticket_para_prompt, clean_body)

    t0 = time.time()
    try:
        result = classify_ticket(_system_prompt, user_prompt)
        error = None
    except LLMClassificationError as e:
        result = None
        error = str(e)
    elapsed_ms = int((time.time() - t0) * 1000)

    base_ticket = {
        "id": ticket_id,
        "subject": ticket_raw["subject"],
        "body": clean_body,
        "solicitante": solicitante,
        "tags": tags,
        "origen": origen,
    }

    if error:
        database.guardar_clasificacion(ticket_id, {}, accion=None, elapsed_ms=elapsed_ms, error=error)
        return {"ticket": base_ticket, "error": error, "elapsed_ms": elapsed_ms}

    confidence = result.get("confidence", 0)
    category_id = result.get("category_id")
    if category_id not in valid_category_ids(_config):
        confidence = 0

    if confidence >= _threshold_high:
        accion = "auto_update"
    elif confidence >= _threshold_low:
        accion = "revision_normal"
    else:
        accion = "revision_prioritaria"

    informacion_completa = result.get("informacion_completa", True)
    campos_faltantes = result.get("campos_faltantes", []) or []
    if isinstance(campos_faltantes, str):  # defensivo, por si el modelo no devuelve una lista
        campos_faltantes = [campos_faltantes]

    # Un Incidente sin los datos minimos NO se puede tratar, sin importar que
    # tan segura este el modelo de la categoria -- se fuerza a revision,
    # nunca se auto-actualiza un ticket que un desarrollador no podria trabajar.
    if category_id == "Incidente" and not informacion_completa:
        accion = "revision_prioritaria"

    prioridad_sugerida = result.get("prioridad_sugerida") or "Normal"
    comercio_sugerido = result.get("comercio_sugerido") or "No identificado"

    # Estos dos NO los decide el LLM -- son reglas deterministas de negocio
    # (ver classifier/routing.py). Mas confiables que pedirselo al modelo.
    fecha_vencimiento_sugerida = sugerir_fecha_vencimiento(prioridad_sugerida)
    responsable_sugerido = sugerir_responsable(category_id, comercio_sugerido)

    entities = result.get("extracted_entities", {}) or {}

    resultado = {
        "category_id": category_id,
        "confidence": confidence,
        "prioridad_sugerida": prioridad_sugerida,
        "comercio_sugerido": comercio_sugerido,
        "fecha_vencimiento_sugerida": fecha_vencimiento_sugerida,
        "responsable_sugerido": responsable_sugerido,
        "informacion_completa": bool(informacion_completa),
        "campos_faltantes": campos_faltantes,
        "summary": result.get("summary"),
        "suggested_action": result.get("suggested_action"),
        "reasoning": result.get("reasoning"),
        "otras_entidades": _safe_entity(entities),
    }

    database.guardar_clasificacion(ticket_id, resultado, accion, elapsed_ms)

    return {
        "ticket": base_ticket,
        "result": resultado,
        "accion": accion,
        "elapsed_ms": elapsed_ms,
        "error": None,
        "stats": database.obtener_stats(),
    }


@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/comercios")
def comercios():
    return jsonify(COMERCIOS)


@app.route("/api/stats")
def stats():
    return jsonify(database.obtener_stats())


@app.route("/api/tickets/recientes")
def recientes():
    """Para cargar el feed 'En llegada' al abrir la pagina (Fase 3): trae los
    ultimos N tickets YA procesados, para que un refresh del navegador no
    vuelva a mostrar el feed vacio aunque el servidor si tenga historial."""
    limit = request.args.get("limit", default=10, type=int)
    return jsonify(database.listar_tickets(limit=limit, offset=0))


@app.route("/api/tickets/filtros")
def filtros_disponibles():
    """Valores distintos ya vistos por cada campo filtrable, para poblar los
    desplegables de la pestana 'Todos los tickets' sin tener que traer todos
    los tickets al navegador solo para armar esas listas."""
    return jsonify(database.valores_distintos_filtros())


@app.route("/api/tickets/historial")
def historial():
    """Tabla 'Todos los tickets': filtrado y paginado en SQL (no en el
    navegador), para que siga funcionando bien aunque haya miles de tickets
    mas adelante. Todos los filtros son opcionales via query string."""
    limit = request.args.get("limit", default=20, type=int)
    offset = request.args.get("offset", default=0, type=int)
    categoria = request.args.get("categoria") or None
    comercio = request.args.get("comercio") or None
    prioridad = request.args.get("prioridad") or None
    responsable = request.args.get("responsable") or None
    accion = request.args.get("accion") or None
    confianza_min = request.args.get("confianza_min", type=float)
    busqueda = request.args.get("busqueda") or None

    tickets, total = database.listar_tickets_filtrado(
        limit=limit, offset=offset, categoria=categoria, comercio=comercio,
        prioridad=prioridad, responsable=responsable, accion=accion,
        confianza_min=confianza_min, busqueda=busqueda,
    )
    return jsonify({"tickets": tickets, "total": total})


@app.route("/api/tickets/reset", methods=["POST"])
def reset_todo():
    """Borra de verdad todos los tickets y clasificaciones de la base de
    datos (antes solo reiniciaba variables en memoria)."""
    database.reset_all()
    return jsonify({"ok": True})


@app.route("/api/tickets", methods=["POST"])
def nuevo_ticket_auto():
    ticket = generate_random_ticket()
    return jsonify(_clasificar_y_responder(ticket, origen="auto"))


@app.route("/api/tickets/manual", methods=["POST"])
def nuevo_ticket_manual():
    """Crea un ticket a partir de lo que el usuario escribe en el formulario
    del dashboard -- simula a alguien de la empresa redireccionando o
    escalando manualmente un caso reportado por un comercio.

    Igual que en el sistema real, el ticket SIEMPRE entra con prioridad
    "Normal" sin importar lo que diga el asunto/cuerpo -- por eso el
    formulario no tiene un campo de prioridad; la prioridad sugerida la
    decide el modelo a partir del contenido, con la misma politica estricta.
    """
    data = request.get_json(force=True) or {}

    subject = (data.get("subject") or "").strip()
    body = (data.get("body") or "").strip()
    solicitante = (data.get("solicitante") or "Coordinador Comercial").strip()
    rol = data.get("rol") or "Member"
    comercio = (data.get("comercio") or "").strip()

    if not subject or not body:
        return jsonify({"error": "El asunto y el cuerpo del ticket son obligatorios."}), 400

    ticket = {
        "subject": subject,
        "requester": {"title": solicitante, "email": "", "role": rol},
        "status": "Nuevo",
        "category": None,
        "priority": "Normal",
        "tags": [{"title": comercio}] if comercio else [],
        "firstComment": f"<div>{body}</div>",
    }

    return jsonify(_clasificar_y_responder(ticket, origen="manual"))


if __name__ == "__main__":
    print("Dashboard disponible en http://localhost:5000")
    print(f"Base de datos: {database.DB_PATH}")
    app.run(debug=False, port=5000)
