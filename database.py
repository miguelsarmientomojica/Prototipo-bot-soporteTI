"""
database.py -- Fase 1 de la hoja de ruta: base de datos local SQLite.

Este modulo es INDEPENDIENTE de Flask a proposito -- se puede importar y
probar sin levantar el dashboard. La Fase 2 (siguiente paso) conectara
dashboard/app.py a estas mismas funciones, reemplazando las variables en
memoria (_historial, _stats) que se usan hoy.

Diseno: 2 tablas, no 1.
  - tickets: el ticket en si (que se recibio).
  - clasificaciones: el veredicto del bot sobre ese ticket (que se decidio).
Separarlas permite, mas adelante, volver a clasificar el mismo ticket con
otro modelo/umbral sin duplicar los datos del ticket, y es prerrequisito
para la fase de evaluacion con "ground truth" (Fase 5 de la hoja de ruta).

Uso basico:
    import database
    database.init_db()
    ticket_id = database.crear_ticket({...})
    database.guardar_clasificacion(ticket_id, resultado, accion, elapsed_ms)
    tickets = database.listar_tickets(limit=20)
"""
import sqlite3
import json
import os
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "tickets.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    solicitante TEXT,
    rol TEXT,
    comercio TEXT,
    tags TEXT,              -- JSON: lista de strings
    origen TEXT NOT NULL,   -- 'auto' | 'manual'
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS clasificaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id),
    category_id TEXT,
    confidence REAL,
    prioridad_sugerida TEXT,
    comercio_sugerido TEXT,
    fecha_vencimiento_sugerida TEXT,
    responsable_sugerido TEXT,
    informacion_completa INTEGER,   -- 0 o 1 (SQLite no tiene boolean nativo)
    campos_faltantes TEXT,          -- JSON: lista de strings
    accion TEXT,                    -- 'auto_update' | 'revision_normal' | 'revision_prioritaria'
    summary TEXT,
    suggested_action TEXT,
    reasoning TEXT,
    otras_entidades TEXT,
    elapsed_ms INTEGER,
    error TEXT,                     -- NULL si la clasificacion fue exitosa
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_clasificaciones_ticket_id ON clasificaciones(ticket_id);
CREATE INDEX IF NOT EXISTS idx_clasificaciones_category ON clasificaciones(category_id);
CREATE INDEX IF NOT EXISTS idx_clasificaciones_accion ON clasificaciones(accion);
"""


@contextmanager
def get_connection():
    """Context manager: abre la conexion, la cierra sola al salir del 'with'."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # permite acceder a columnas por nombre, ej. fila["subject"]
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Crea las tablas si no existen. Se puede llamar tantas veces como se
    quiera -- no borra datos existentes (usa CREATE TABLE IF NOT EXISTS)."""
    with get_connection() as conn:
        conn.executescript(_SCHEMA)


def crear_ticket(ticket: dict) -> int:
    """Guarda un ticket nuevo. Devuelve el id asignado."""
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO tickets (subject, body, solicitante, rol, comercio, tags, origen, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                ticket["subject"],
                ticket["body"],
                ticket.get("solicitante", ""),
                ticket.get("rol", "Member"),
                ticket.get("comercio", ""),
                json.dumps(ticket.get("tags", []), ensure_ascii=False),
                ticket.get("origen", "auto"),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        return cursor.lastrowid


def guardar_clasificacion(ticket_id: int, resultado: dict, accion: str, elapsed_ms: int, error: str = None) -> int:
    """Guarda el veredicto del bot para un ticket ya existente. Devuelve el id
    de la fila de clasificacion creada (un ticket puede tener mas de una si
    se re-clasifica)."""
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO clasificaciones (
                   ticket_id, category_id, confidence, prioridad_sugerida, comercio_sugerido,
                   fecha_vencimiento_sugerida, responsable_sugerido, informacion_completa,
                   campos_faltantes, accion, summary, suggested_action, reasoning,
                   otras_entidades, elapsed_ms, error, created_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                ticket_id,
                resultado.get("category_id"),
                resultado.get("confidence"),
                resultado.get("prioridad_sugerida"),
                resultado.get("comercio_sugerido"),
                resultado.get("fecha_vencimiento_sugerida"),
                resultado.get("responsable_sugerido"),
                int(bool(resultado.get("informacion_completa", True))),
                json.dumps(resultado.get("campos_faltantes", []), ensure_ascii=False),
                accion,
                resultado.get("summary"),
                resultado.get("suggested_action"),
                resultado.get("reasoning"),
                resultado.get("otras_entidades"),
                elapsed_ms,
                error,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        return cursor.lastrowid


def listar_tickets(limit: int = 50, offset: int = 0) -> list:
    """Devuelve los tickets mas recientes junto con su ULTIMA clasificacion
    (si un ticket se reclasifico varias veces, trae solo la mas reciente).
    Pensado para alimentar la pestana 'Todos los tickets' del dashboard."""
    with get_connection() as conn:
        filas = conn.execute(
            """
            SELECT t.*, c.category_id, c.confidence, c.prioridad_sugerida, c.comercio_sugerido,
                   c.fecha_vencimiento_sugerida, c.responsable_sugerido, c.informacion_completa,
                   c.campos_faltantes, c.accion, c.summary, c.suggested_action, c.reasoning,
                   c.otras_entidades, c.elapsed_ms, c.error AS clasificacion_error
            FROM tickets t
            LEFT JOIN clasificaciones c ON c.id = (
                SELECT id FROM clasificaciones
                WHERE ticket_id = t.id
                ORDER BY id DESC LIMIT 1
            )
            ORDER BY t.id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
        return [_fila_a_dict(f) for f in filas]


# Base del JOIN que se reutiliza tanto para listar_tickets() (sin filtros,
# usado por el feed en vivo) como para listar_tickets_filtrado() (con
# filtros/paginacion, usado por la tabla). Mantenerlo en un solo lugar evita
# que las dos consultas se desincronicen si se agrega una columna despues.
_JOIN_BASE = """
    FROM tickets t
    LEFT JOIN clasificaciones c ON c.id = (
        SELECT id FROM clasificaciones
        WHERE ticket_id = t.id
        ORDER BY id DESC LIMIT 1
    )
    WHERE c.error IS NULL
"""


def listar_tickets_filtrado(limit=20, offset=0, categoria=None, comercio=None,
                             prioridad=None, responsable=None, accion=None,
                             confianza_min=None, busqueda=None):
    """Version con filtros aplicados en SQL (no en Python/JS), pensada para
    que la tabla del dashboard escale a miles de tickets sin tener que cargar
    todo en el navegador. Devuelve (tickets, total_que_cumple_los_filtros)."""
    condiciones = []
    params = []

    if categoria:
        condiciones.append("c.category_id = ?")
        params.append(categoria)
    if comercio:
        condiciones.append("c.comercio_sugerido = ?")
        params.append(comercio)
    if prioridad:
        condiciones.append("c.prioridad_sugerida = ?")
        params.append(prioridad)
    if responsable:
        condiciones.append("c.responsable_sugerido = ?")
        params.append(responsable)
    if accion:
        condiciones.append("c.accion = ?")
        params.append(accion)
    if confianza_min is not None:
        condiciones.append("c.confidence >= ?")
        params.append(confianza_min)
    if busqueda:
        condiciones.append("LOWER(t.subject) LIKE ?")
        params.append(f"%{busqueda.lower()}%")

    where_extra = (" AND " + " AND ".join(condiciones)) if condiciones else ""

    with get_connection() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) AS n {_JOIN_BASE}{where_extra}", params
        ).fetchone()["n"]

        filas = conn.execute(
            f"""SELECT t.*, c.category_id, c.confidence, c.prioridad_sugerida, c.comercio_sugerido,
                       c.fecha_vencimiento_sugerida, c.responsable_sugerido, c.informacion_completa,
                       c.campos_faltantes, c.accion, c.summary, c.suggested_action, c.reasoning,
                       c.otras_entidades, c.elapsed_ms, c.error AS clasificacion_error
                {_JOIN_BASE}{where_extra}
                ORDER BY t.id DESC
                LIMIT ? OFFSET ?""",
            params + [limit, offset],
        ).fetchall()

        return [_fila_a_dict(f) for f in filas], total


def valores_distintos_filtros() -> dict:
    """Los valores distintos que ha tomado cada campo filtrable hasta ahora,
    para poblar los desplegables de filtros del frontend sin tener que
    cargar todos los tickets al navegador."""
    with get_connection() as conn:
        def distintos(campo):
            filas = conn.execute(
                f"""SELECT DISTINCT {campo} AS v FROM clasificaciones
                    WHERE error IS NULL AND {campo} IS NOT NULL
                    ORDER BY {campo}"""
            ).fetchall()
            return [f["v"] for f in filas]

        return {
            "categorias": distintos("category_id"),
            "comercios": distintos("comercio_sugerido"),
            "prioridades": distintos("prioridad_sugerida"),
            "responsables": distintos("responsable_sugerido"),
        }


def contar_tickets() -> int:
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) AS n FROM tickets").fetchone()["n"]


def obtener_stats() -> dict:
    """Equivalente a la variable _stats que hoy vive en memoria en app.py,
    pero calculado con SQL en vez de acumulado a mano en Python."""
    with get_connection() as conn:
        total = conn.execute(
            "SELECT COUNT(*) AS n FROM clasificaciones WHERE error IS NULL"
        ).fetchone()["n"]

        por_categoria = {
            row["category_id"]: row["n"]
            for row in conn.execute(
                """SELECT category_id, COUNT(*) AS n FROM clasificaciones
                   WHERE error IS NULL GROUP BY category_id"""
            ).fetchall()
        }

        por_accion_rows = conn.execute(
            """SELECT accion, COUNT(*) AS n FROM clasificaciones
               WHERE error IS NULL GROUP BY accion"""
        ).fetchall()
        por_accion = {"auto_update": 0, "revision_normal": 0, "revision_prioritaria": 0}
        for row in por_accion_rows:
            if row["accion"] in por_accion:
                por_accion[row["accion"]] = row["n"]

        return {"total": total, "por_categoria": por_categoria, "por_accion": por_accion}


def reset_all():
    """Borra todos los tickets y clasificaciones. Equivalente al boton
    'Reiniciar' del dashboard, pero borrando de verdad (hoy solo reinicia
    variables en memoria)."""
    with get_connection() as conn:
        conn.execute("DELETE FROM clasificaciones")
        conn.execute("DELETE FROM tickets")


def _fila_a_dict(fila: sqlite3.Row) -> dict:
    """Convierte una fila SQLite (con el JOIN de tickets+clasificaciones) al
    mismo formato de diccionario que ya usa el frontend hoy (ver
    dashboard/app.py y dashboard/static/app.js), para que conectar la Fase 2
    sea un cambio minimo."""
    d = dict(fila)
    return {
        "ticket": {
            "id": d["id"],
            "subject": d["subject"],
            "body": d["body"],
            "solicitante": d["solicitante"],
            "tags": json.loads(d["tags"] or "[]"),
            "origen": d["origen"],
        },
        "result": {
            "category_id": d["category_id"],
            "confidence": d["confidence"],
            "prioridad_sugerida": d["prioridad_sugerida"],
            "comercio_sugerido": d["comercio_sugerido"],
            "fecha_vencimiento_sugerida": d["fecha_vencimiento_sugerida"],
            "responsable_sugerido": d["responsable_sugerido"],
            "informacion_completa": bool(d["informacion_completa"]),
            "campos_faltantes": json.loads(d["campos_faltantes"] or "[]"),
            "summary": d["summary"],
            "suggested_action": d["suggested_action"],
            "reasoning": d["reasoning"],
            "otras_entidades": d["otras_entidades"],
        } if d["category_id"] is not None else None,
        "accion": d["accion"],
        "elapsed_ms": d["elapsed_ms"],
        "error": d["clasificacion_error"],
    }
