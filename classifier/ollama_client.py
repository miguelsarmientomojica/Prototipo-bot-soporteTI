"""
Cliente para modelos locales servidos por Ollama -- intercambiable con
claude_client.py (misma firma de classify_ticket).

Requiere:
  1. Ollama instalado y corriendo (se instala como servicio de Windows, arranca solo).
  2. El modelo ya descargado una vez: `ollama pull qwen3:14b`
  3. pip install openai
"""
import os
import json
import logging

from openai import OpenAI

from .schema import build_classification_properties, CLASSIFICATION_REQUIRED

logger = logging.getLogger("classify_ticket.ollama_client")

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen3:14b")

_client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")

_CLASSIFICATION_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_classification",
        "description": "Envia el resultado de la clasificacion del ticket.",
        "parameters": {
            "type": "object",
            "properties": build_classification_properties(),
            "required": CLASSIFICATION_REQUIRED,
        },
    },
}


class LLMClassificationError(Exception):
    pass


def classify_ticket(system_prompt: str, user_prompt: str, api_key: str = None) -> dict:
    """Misma firma que claude_client.classify_ticket -- el parametro api_key se
    ignora (Ollama no lo necesita), se deja solo para que ambos clientes sean
    intercambiables sin tocar el codigo que los llama."""
    try:
        completion = _client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            tools=[_CLASSIFICATION_TOOL],
            tool_choice={"type": "function", "function": {"name": "submit_classification"}},
            temperature=0.2,
        )
    except Exception as e:
        logger.error("Error llamando a Ollama: %s", e)
        raise LLMClassificationError(
            f"Error de Ollama: {e}. Verifica que Ollama este corriendo y que "
            f"descargaste el modelo con 'ollama pull {LLM_MODEL}'."
        ) from e

    message = completion.choices[0].message
    if not message.tool_calls:
        raise LLMClassificationError(
            "El modelo no devolvio una tool call con la clasificacion esperada "
            "(devolvio texto libre en su lugar)."
        )

    tool_call = message.tool_calls[0]
    try:
        return json.loads(tool_call.function.arguments)
    except json.JSONDecodeError as e:
        raise LLMClassificationError(f"JSON invalido devuelto por el modelo: {e}") from e
