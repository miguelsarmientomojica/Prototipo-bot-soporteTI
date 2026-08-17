"""
Cliente para la API de Anthropic (Claude). Alternativa opcional a Ollama --
misma firma de classify_ticket, intercambiable con ollama_client.py.
"""
import os
import logging

import anthropic

from .schema import build_classification_properties, CLASSIFICATION_REQUIRED

logger = logging.getLogger("classify_ticket.claude_client")

DEFAULT_MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
MAX_TOKENS = int(os.environ.get("CLAUDE_MAX_TOKENS", "1024"))

_CLASSIFICATION_TOOL = {
    "name": "submit_classification",
    "description": "Envía el resultado de la clasificación del ticket.",
    "input_schema": {
        "type": "object",
        "properties": build_classification_properties(),
        "required": CLASSIFICATION_REQUIRED,
    },
}


class ClaudeClassificationError(Exception):
    pass


def classify_ticket(system_prompt: str, user_prompt: str, api_key: str) -> dict:
    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            tools=[_CLASSIFICATION_TOOL],
            tool_choice={"type": "tool", "name": "submit_classification"},
            messages=[{"role": "user", "content": user_prompt}],
        )
    except anthropic.APIError as e:
        logger.error("Error llamando a la API de Claude: %s", e)
        raise ClaudeClassificationError(f"Error de API Claude: {e}") from e

    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_classification":
            return block.input

    raise ClaudeClassificationError(
        "Claude no devolvió un bloque tool_use con la clasificación esperada."
    )
