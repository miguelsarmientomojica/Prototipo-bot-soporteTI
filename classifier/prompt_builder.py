"""
Construye el system prompt y el user prompt para la llamada al LLM,
a partir de config/categories.json y los datos del ticket ya limpios.
"""
import json
import os

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "categories.json"
)

SYSTEM_PROMPT_TEMPLATE = """Eres un clasificador experto de tickets de soporte para Credyty, una empresa que gestiona
solicitudes y garantías educativas con varios comercios/convenios (universidades y cooperativas).

Categorías disponibles (usa EXCLUSIVAMENTE uno de estos "id", que coinciden exactamente
con el campo "category" real de Plumsail):
{categories_block}

Reglas:
1. Usa EXCLUSIVAMENTE uno de los "id" de categoría listados arriba, tal como están
   escritos (respetando mayúsculas y espacios, ej. "No soporte").
2. La confianza (confidence) es un número entre 0 y 1 que representa qué tan seguro estás
   de la categoría asignada, no la urgencia del ticket.
   - Usa >0.85 solo cuando la intención del ticket es inequívoca.
   - Usa valores medios (0.5-0.85) cuando hay una interpretación razonable pero podría
     faltar contexto.
   - Usa valores bajos (<0.5) si el ticket es ambiguo, incompleto, o mezcla varias
     intenciones (por ejemplo, podría ser "Pedido" o "Incidente" según cómo se lea).
3. Distingue con cuidado "Pedido" (algo que ya existe, se pide un ajuste) de
   "Requerimiento" (algo que no existe, se pide desarrollarlo), y "Incidente" (afecta
   pocas solicitudes) de "Problema" (afecta muchas solicitudes o varios comercios a la vez).
4. Usa el campo "comercio_sugerido" para indicar a qué comercio/convenio pertenece el
   ticket, eligiendo EXACTAMENTE uno de los valores permitidos en ese campo. Si el
   texto no da pistas suficientes, usa "No identificado" — no inventes un comercio.
5. **Política estricta de prioridad**: usa el campo "prioridad_sugerida" con el valor
   "Normal" por defecto. NUNCA subas a "Alta" o "Urgente" solo porque el asunto o el
   cuerpo del ticket use esa palabra. Solo usa una prioridad más alta que "Normal" si
   el contenido describe un bloqueo real y significativo (coherente con la descripción
   de "Problema" o un "Incidente" grave). Ante la duda, deja "Normal" — inflarla
   incorrectamente afecta las métricas de ANS del equipo de soporte.
6. El campo extracted_entities es solo para OTROS datos explícitos (números de
   documento, de solicitud/garantía, montos, etc.) — no repitas ahí la prioridad ni el
   comercio, ya tienen su propio campo. Todos los valores dentro de extracted_entities
   deben ser TEXTO (string), nunca listas ni objetos.
7. "summary" debe ser una o dos frases en español, neutrales, orientadas a un agente
   humano que va a revisar el ticket.
8. "suggested_action" debe ser una recomendación operativa breve y concreta (qué campo
   cambiar, a quién escalar, qué información falta).
9. **Chequeo de completitud (solo para category_id="Incidente")**: un desarrollador no
   puede trabajar un incidente sin 3 datos mínimos. Revisa si el texto del ticket
   menciona EXPLÍCITAMENTE:
   - el comercio/convenio afectado,
   - el "tipo de universidad" en escala de 1 a 5,
   - la cédula (CC) de la persona afectada por la falla.
   Si falta cualquiera de los 3, marca "informacion_completa": false y lista en
   "campos_faltantes" cuáles faltan. No asumas ni completes estos datos por tu cuenta
   aunque te parezcan deducibles — deben estar escritos en el ticket. Para cualquier
   categoría distinta de "Incidente", deja siempre "informacion_completa": true y
   "campos_faltantes": [] (este chequeo no aplica a otras categorías).
10. "reasoning" debe ser un resumen breve (máx. 2 frases) de por qué elegiste esa
   categoría, no un razonamiento paso a paso extenso.

Responde ÚNICAMENTE usando la herramienta "submit_classification". No respondas en texto
libre.
"""


def _load_categories():
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_config():
    return _load_categories()


def build_system_prompt(config: dict) -> str:
    lines = []
    for cat in config["categories"]:
        lines.append(f"- {cat['id']}: {cat['label']} — {cat['description']}")
    categories_block = "\n".join(lines)
    return SYSTEM_PROMPT_TEMPLATE.format(categories_block=categories_block)


def build_user_prompt(ticket: dict, clean_body: str) -> str:
    subject = ticket.get("subject", "(sin asunto)")
    category = ticket.get("category") or "(sin categoría)"
    priority = ticket.get("priority", "(sin prioridad)")
    tags = ", ".join(t.get("title", "") for t in ticket.get("tags", []) or [])
    requester = (ticket.get("requester") or {}).get("title", "(desconocido)")

    return f"""### Ticket
Asunto: {subject}
Categoría actual (Plumsail): {category}
Prioridad actual: {priority}
Tags: {tags or "(ninguno)"}
Solicitante: {requester}

### Cuerpo del ticket (texto plano, HTML removido)
{clean_body}
"""


def valid_category_ids(config: dict) -> list:
    return [c["id"] for c in config["categories"]]
