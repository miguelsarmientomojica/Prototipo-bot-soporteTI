"""
routing.py -- reglas de negocio deterministas para dos de los datos que pide
calificar el usuario: fecha de vencimiento y responsable sugerido.

A propósito estas NO se le piden al LLM. Son reglas fijas de la empresa
(plazos por prioridad, asignación por nivel/comercio) -- calcularlas en
código es más confiable que pedirle a un modelo de lenguaje que haga
aritmética de fechas o que "recuerde" una tabla de asignaciones, que es
justo el tipo de tarea donde los LLM fallan más. El LLM se usa solo donde
sí aporta valor real: comprender el texto libre del ticket (categoría,
prioridad sugerida, comercio mencionado).

Basado en las reglas descritas por soporte nivel 1 (Miguel Sarmiento):
  - Fecha de vencimiento: 3-4 días hábiles desde que llega el ticket
    (1-2 para la solución + 48h/2 días hábiles de cierre automático tras
    la respuesta). Aquí se ajusta según la prioridad sugerida.
  - Responsable: nivel 1 (Miguel Sarmiento) recibe todo por defecto;
    Requerimientos van al PM del área según el tipo de comercio (educativo
    -> Julian Araque, cooperativo -> Jenny Forero); "No soporte" no se
    asigna dentro de TI.

Nota importante: el propio equipo de soporte indica que en la práctica la
asignación real varía según disponibilidad, porque todos son desarrolladores
compartidos entre soporte y desarrollo. Por eso esto se entrega como
"responsable_sugerido", una sugerencia de primer nivel, no una asignación
definitiva.
"""
import json
import os
from datetime import datetime, timedelta

_COMERCIOS_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "comercios.json")

DIAS_HABILES_POR_PRIORIDAD = {
    "Urgente": 1,
    "Alta": 2,
    "Normal": 3,
    "Baja": 4,
}

# Nombres ficticios que representan los roles reales descritos por soporte,
# para mantener el prototipo sin datos reales de personas de la empresa.
RESPONSABLE_NIVEL_1 = "Agente Nivel 1 (triage inicial)"
RESPONSABLE_NIVEL_2_EDUCATIVO = "Agente Nivel 2 — Sector Educativo"
RESPONSABLE_NIVEL_2_COOPERATIVO = "Agente Nivel 2 — Sector Cooperativo"
RESPONSABLE_NIVEL_3 = "Agente Nivel 3 (escalamiento)"
PM_AREA_EDUCATIVA = "PM Área Educativa"
PM_AREA_COOPERATIVA = "PM Área Cooperativa"
NO_APLICA_TI = "No aplica a soporte TI — redirigir a otra área"


def _load_tipo_por_comercio():
    with open(_COMERCIOS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {c["nombre"]: c["tipo"] for c in data["comercios"]}


_TIPO_POR_COMERCIO = _load_tipo_por_comercio()


def sugerir_fecha_vencimiento(prioridad: str, desde: datetime = None) -> str:
    """Calcula la fecha de vencimiento sugerida sumando dias habiles segun
    la prioridad (Urgente=1, Alta=2, Normal=3, Baja=4), saltando fines de
    semana. Devuelve la fecha en formato ISO (YYYY-MM-DD)."""
    dias = DIAS_HABILES_POR_PRIORIDAD.get(prioridad, 3)
    fecha = desde or datetime.now()
    agregados = 0
    while agregados < dias:
        fecha += timedelta(days=1)
        if fecha.weekday() < 5:  # 0-4 = lunes a viernes
            agregados += 1
    return fecha.strftime("%Y-%m-%d")


def sugerir_responsable(category_id: str, comercio: str) -> str:
    """Sugiere un responsable de primer nivel segun la categoria y el tipo
    de comercio. Es una sugerencia de triage inicial, no una asignacion
    definitiva (la real varia por disponibilidad, segun el propio equipo)."""
    if category_id == "No soporte":
        return NO_APLICA_TI

    tipo = _TIPO_POR_COMERCIO.get(comercio)

    if category_id == "Requerimiento":
        if tipo == "cooperativo":
            return PM_AREA_COOPERATIVA
        return PM_AREA_EDUCATIVA  # por defecto si no se identifica el comercio

    if category_id == "Problema":
        # Afecta a muchas solicitudes/varios comercios -> se sugiere escalar directo
        return RESPONSABLE_NIVEL_3

    if tipo == "cooperativo":
        return RESPONSABLE_NIVEL_2_COOPERATIVO if category_id == "Incidente" else RESPONSABLE_NIVEL_1

    if tipo == "educativo" and category_id == "Incidente":
        return RESPONSABLE_NIVEL_2_EDUCATIVO

    return RESPONSABLE_NIVEL_1
