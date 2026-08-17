"""
Limpieza de HTML proveniente del campo firstComment/comments de Plumsail.
Los tickets suelen incluir firmas, tablas de contacto, imágenes embebidas y
avisos legales que no aportan señal para la clasificación. Este módulo reduce
el HTML a texto plano relevante.
"""
import re
from bs4 import BeautifulSoup

# Frases típicas de firma / disclaimer legal que se recortan si aparecen,
# para no confundir al LLM ni gastar tokens innecesarios.
_CUT_MARKERS = [
    "Aviso legal:",
    "El contenido de este mensaje",
    "CONFIDENCIALIDAD",
]


def clean_html_to_text(html: str, max_chars: int = 4000) -> str:
    """Convierte HTML de un comentario de Plumsail a texto plano recortado.

    - Elimina tags, estilos, imágenes y tablas de firma.
    - Corta el texto en el primer marcador de aviso legal/firma conocido.
    - Colapsa espacios y líneas en blanco repetidas.
    - Trunca a max_chars para controlar el tamaño del prompt.
    """
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["img", "script", "style"]):
        tag.decompose()

    text = soup.get_text(separator="\n")

    for marker in _CUT_MARKERS:
        idx = text.find(marker)
        if idx != -1:
            text = text[:idx]
            break

    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    cleaned = "\n".join(lines)

    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars].rstrip() + "…"

    return cleaned
