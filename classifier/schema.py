"""
schema.py -- definicion compartida de los campos que el LLM debe devolver,
usada tanto por ollama_client.py como por claude_client.py para no duplicar
la definicion (y que ambos queden sincronizados si se agrega/cambia un campo).

Nota de diseno: fecha_vencimiento_sugerida y responsable_sugerido NO estan
aqui -- esos se calculan con reglas deterministas en classifier/routing.py,
no se le piden al LLM (ver el docstring de routing.py para el porque).
"""
import json
import os

_COMERCIOS_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "comercios.json")


def get_comercio_names():
    with open(_COMERCIOS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [c["nombre"] for c in data["comercios"]]


def build_classification_properties():
    comercios = get_comercio_names()
    return {
        "category_id": {
            "type": "string",
            "description": "El id de categoria elegido, debe coincidir EXACTAMENTE con uno de la lista provista en el prompt.",
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Confianza calibrada entre 0 y 1, sobre la categoria elegida.",
        },
        "prioridad_sugerida": {
            "type": "string",
            "enum": ["Baja", "Normal", "Alta", "Urgente"],
            "description": (
                "Prioridad sugerida SOLO si el contenido justifica un bloqueo real. "
                "Por defecto usa 'Normal' salvo que el texto describa claramente un "
                "bloqueo significativo (ver regla de politica estricta en el prompt). "
                "Nunca subas a Alta/Urgente solo porque el ticket use esa palabra."
            ),
        },
        "comercio_sugerido": {
            "type": "string",
            "enum": comercios + ["No identificado"],
            "description": "El comercio/convenio mencionado o mas probable segun el contenido. Usa 'No identificado' si el texto no da pistas suficientes.",
        },
        "summary": {"type": "string", "description": "Resumen de 1-2 frases para un agente humano."},
        "suggested_action": {"type": "string", "description": "Accion operativa breve recomendada."},
        "informacion_completa": {
            "type": "boolean",
            "description": (
                "SOLO relevante cuando category_id='Incidente'. Para que un desarrollador "
                "pueda tratar el incidente sin pedir mas datos, el ticket debe traer, "
                "explicitamente en el texto, estos 3 datos minimos: (1) el comercio/convenio, "
                "(2) el 'tipo de universidad' en escala de 1 a 5, y (3) la cedula (CC) de la "
                "persona afectada por la falla. Pon 'false' si falta CUALQUIERA de los 3. "
                "Para cualquier otra categoria distinta de 'Incidente', deja siempre 'true' "
                "(este chequeo no aplica a otras categorias)."
            ),
        },
        "campos_faltantes": {
            "type": "array",
            "items": {"type": "string", "enum": ["comercio", "tipo_universidad", "cedula_afectado"]},
            "description": (
                "SOLO para category_id='Incidente' con informacion_completa=false: lista cuales "
                "de los 3 datos minimos faltan en el texto (comercio, tipo_universidad, "
                "cedula_afectado). Deja la lista vacia si informacion_completa=true o si la "
                "categoria no es 'Incidente'."
            ),
        },
        "extracted_entities": {
            "type": "object",
            "description": "Otras entidades explicitas encontradas en el texto (numeros de documento, de solicitud, montos, etc). Todos los valores deben ser texto. No repitas aqui prioridad ni comercio, ya tienen su propio campo.",
            "additionalProperties": {"type": "string"},
        },
        "reasoning": {"type": "string", "description": "Justificacion breve (max. 2 frases)."},
    }


CLASSIFICATION_REQUIRED = [
    "category_id", "confidence", "prioridad_sugerida", "comercio_sugerido",
    "summary", "suggested_action", "informacion_completa", "campos_faltantes", "reasoning",
]
