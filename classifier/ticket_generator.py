"""
ticket_generator.py -- genera tickets sinteticos aleatorios, combinando
plantillas de texto por categoria con nombres/comercios ficticios. Se usa
para el banco fijo (data/tickets_sinteticos.json) y para el dashboard en
vivo, que necesita poder generar tickets nuevos indefinidamente durante
la demo sin repetirse siempre igual.

Todos los datos (nombres, correos, comercios, documentos) son inventados.
"""
import random

NOMBRES = [
    "Laura Fernanda Gómez", "Andrés Felipe Rojas", "Camilo Torres",
    "Diana Marcela Ruiz", "Julián David Peña", "Paula Andrea Sánchez",
    "Esteban Ariza", "Sofía Martínez", "Mateo Londoño", "Valentina Ortiz",
    "Santiago Cárdenas", "Isabella Reyes", "Nicolás Vargas", "Camila Herrera",
    "Sebastián Molina", "Daniela Castro", "Tomás Guzmán", "Manuela Prieto",
]

from .schema import get_comercio_names

COMERCIOS = get_comercio_names()

DOMINIOS = ["correo-ejemplo.com", "ejemplo-edu.co", "cooperativa-ejemplo.coop"]

_next_id = [2000]  # contador simple, evita ids repetidos dentro de una sesion


def _fake_email(nombre, dominio):
    partes = nombre.lower().replace("é", "e").replace("í", "i").replace("ó", "o").split()
    return f"{partes[0][0]}{partes[-1]}@{dominio}".replace(" ", "")


def _fake_documento():
    return str(random.randint(1_000_000_000, 1_199_999_999))


def _fake_solicitud():
    return f"302500{random.randint(1000, 9999)}"


# Cada entrada: (asunto_template, cuerpo_template, prioridad_original)
# Los templates usan {nombre}, {comercio}, {documento}, {solicitud}
PLANTILLAS = {
    "Pedido": [
        (
            "Cambio No. Documento Estudiante",
            "<div>Buen dia soporte.</div><div>Solicito su colaboracion modificando el No. Documento del estudiante a CC {documento}, solicitud {solicitud}.</div><div>No firma garantias, se puede realizar la modificacion.</div><div>Cordialmente.</div>",
        ),
        (
            "Crear Usuario",
            "<div>Cordial saludo,</div><div>Solicito crear un usuario para {nombre}, correo asociado y rol de Agente SAC en {comercio}.</div>",
        ),
        (
            "Cambio de estado de solicitud",
            "<div>Buen dia, solicito cambio de estado de la solicitud {solicitud} a FINANCIACION LEGALIZADA, no requiere renovacion.</div><div>Cordialmente.</div>",
        ),
        (
            "Ajuste de fecha de pago",
            "<div>Buen dia, favor ajustar la fecha de pago de la primera cuota de la solicitud {solicitud}, el asociado solicita que quede para el dia 15 en vez del dia 5.</div>",
        ),
    ],
    "Pregunta": [
        (
            "Consulta estado de mi solicitud",
            "<div>Hola, buenas tardes.</div><div>Queria preguntar en que estado va mi solicitud de credito educativo, la radique hace 2 semanas y no he recibido novedades.</div><div>Gracias.</div>",
        ),
        (
            "Duda sobre requisitos",
            "<div>Buenas, tengo una duda sobre que documentos necesito para renovar mi garantia en {comercio}, me pueden confirmar el listado?</div>",
        ),
        (
            "Pregunta sobre tasa de interes",
            "<div>Buen dia, quisiera saber cual es la tasa de interes aplicada a las garantias de {comercio} este semestre.</div>",
        ),
        (
            "Consulta sobre documentos requeridos",
            "<div>Hola, para radicar una nueva solicitud en {comercio}, necesito el certificado de matricula o basta con el recibo de pago?</div>",
        ),
    ],
    "Incidente": [
        # Variante COMPLETA -- trae comercio, tipo de universidad (1-5) y CC del afectado
        (
            "Error al subir documento de identidad",
            "<div>Buenas, al intentar subir mi cedula escaneada en el paso 3 del formulario me sale un error y no me deja continuar. Ya intente con otro navegador.</div><div>Comercio: {comercio}. Tipo de universidad: {tipo_universidad}. CC del afectado: {documento}.</div>",
        ),
        # Variante INCOMPLETA -- a proposito no trae tipo de universidad ni CC
        (
            "No logro subir mi documento de identidad",
            "<div>Buenas, al intentar subir mi cedula escaneada en el paso 3 del formulario me sale un error y no me deja continuar. Ya intente con otro navegador.</div>",
        ),
        (
            "No me deja avanzar en el formulario",
            "<div>Hola, llevo desde ayer intentando terminar mi solicitud pero el boton de siguiente no responde en el paso de datos financieros.</div><div>Comercio: {comercio}. Tipo de universidad: {tipo_universidad}. CC del afectado: {documento}.</div>",
        ),
        (
            "No me deja avanzar en el formulario",
            "<div>Hola, llevo desde ayer intentando terminar mi solicitud pero el boton de siguiente no responde en el paso de datos financieros. No se a quien mas escribirle.</div>",
        ),
        (
            "La plataforma no carga mi historial",
            "<div>Buenas, entro a mi perfil y la seccion de historial de pagos se queda cargando indefinidamente.</div><div>Comercio: {comercio}. Tipo de universidad: {tipo_universidad}. CC del afectado: {documento}.</div>",
        ),
    ],
    "Problema": [
        (
            "Plataforma caida - varios usuarios afectados",
            "<div>Buen dia, nos estan reportando desde varias sedes que la plataforma de radicacion no carga desde hace 40 minutos. Ya son mas de 10 solicitantes afectados en {comercio} y otros convenios. Por favor revisar con urgencia.</div>",
        ),
        (
            "Fallo general tras actualizacion",
            "<div>Desde la actualizacion de esta manana varios comercios reportan que no pueden radicar solicitudes nuevas, parece un problema general de la plataforma, no aislado.</div>",
        ),
    ],
    "Requerimiento": [
        (
            "Solicitud de nueva funcionalidad - firma digital",
            "<div>Buenas, desde {comercio} nos solicitan que el proceso de firma de garantias se pueda hacer con firma digital, hoy no existe esa opcion en la plataforma.</div>",
        ),
        (
            "Solicitud de reporte automatico",
            "<div>Quisieramos saber si es posible generar un reporte automatico mensual de cartera para {comercio}, hoy toca pedirlo manualmente cada mes. Si no existe, dejarlo como requerimiento formal.</div>",
        ),
    ],
    "No soporte": [
        (
            "Undeliverable: Mail delivery failed",
            "<div>This is an automatically generated message. Delivery has failed to these recipients. The following organization rejected your message.</div>",
        ),
        (
            "Excepcion no controlada",
            "<div>Excepcion no controlada en el modulo de notificaciones: NullReferenceException. Este es un correo generado automaticamente por el sistema de monitoreo.</div>",
        ),
    ],
    "_urgente_falso": [  # caso especial: dice urgente pero prioridad real es Normal
        (
            "Urgente - Cambio estado solicitud {solicitud}",
            "<div>Buen dia soporte.</div><div>Solicito cambio de estado de la solicitud {solicitud} a FINANCIACION LEGALIZADA, no requiere renovacion.</div><div>Cordialmente.</div>",
        ),
    ],
}


_historial_reciente = []  # guarda las ultimas plantillas usadas, para no repetir seguido
_VENTANA_ANTI_REPETICION = 5  # no repite ninguna de las ultimas 5 combinaciones (categoria, plantilla)


def _elegir_categoria_y_plantilla():
    """Elige categoria + plantilla evitando repetir lo usado en las ultimas
    _VENTANA_ANTI_REPETICION generaciones, siempre que existan alternativas
    disponibles (si ya se agotaron todas las combinaciones distintas, permite
    repetir en vez de quedar en un ciclo infinito)."""
    if random.random() < 0.125:
        categoria_real = "_urgente_falso"
        indice = 0
        return categoria_real, indice

    categorias = list(k for k in PLANTILLAS if not k.startswith("_"))
    intentos = 0
    while intentos < 20:
        categoria_real = random.choice(categorias)
        indice = random.randrange(len(PLANTILLAS[categoria_real]))
        combo = (categoria_real, indice)
        if combo not in _historial_reciente:
            return categoria_real, indice
        intentos += 1
    # No se encontro una combinacion nueva en 20 intentos (banco muy chico) -> se permite repetir
    return categoria_real, indice


def _registrar_uso(categoria_real, indice):
    _historial_reciente.append((categoria_real, indice))
    if len(_historial_reciente) > _VENTANA_ANTI_REPETICION:
        _historial_reciente.pop(0)


def generate_random_ticket():
    """Genera un ticket sintetico aleatorio (dict), en la misma estructura
    de campos que la API real de Plumsail, con datos ficticios. Evita repetir
    la misma plantilla en generaciones consecutivas (ver _elegir_categoria_y_plantilla)."""
    _next_id[0] += 1
    ticket_id = _next_id[0]

    categoria_real, indice = _elegir_categoria_y_plantilla()
    _registrar_uso(categoria_real, indice)

    asunto_tpl, cuerpo_tpl = PLANTILLAS[categoria_real][indice]
    nombre = random.choice(NOMBRES)
    comercio = random.choice(COMERCIOS)
    dominio = random.choice(DOMINIOS)
    documento = _fake_documento()
    solicitud = _fake_solicitud()
    tipo_universidad = str(random.randint(1, 5))

    fmt = dict(nombre=nombre, comercio=comercio, documento=documento, solicitud=solicitud, tipo_universidad=tipo_universidad)

    return {
        "id": ticket_id,
        "subject": asunto_tpl.format(**fmt),
        "requester": {"id": ticket_id, "title": nombre, "email": _fake_email(nombre, dominio), "role": "End-User"},
        "status": "Nuevo",
        "category": None,
        "priority": "Normal",
        "tags": [{"title": comercio.replace(" ", ""), "id": ticket_id}],
        "firstComment": cuerpo_tpl.format(**fmt),
    }
