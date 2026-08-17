# Prototipo de clasificación de tickets — Simulación local (Trabajo de Grado)

## Por qué es una simulación

No se autorizó el acceso a la API de Plumsail Helpdesk de la empresa (por seguridad,
al ser un proyecto académico que queda en custodia de la universidad). Por lo tanto,
este prototipo **no se conecta a ningún sistema real de la empresa**: no hay Plumsail,
no hay Azure, no hay SharePoint. Es 100% autocontenido y local.

## Arquitectura

```
classifier/ticket_generator.py   genera tickets ficticios (nombres/comercios inventados)
        │
        ├──► run_simulation.py     modo por lote: clasifica 30 tickets fijos → Excel
        │
        └──► dashboard/app.py      modo en vivo: genera y clasifica tickets uno a uno,
                                     visualizados en tiempo real en el navegador
```

Ambos modos reutilizan la misma lógica de clasificación (`classifier/html_cleaner.py`,
`classifier/prompt_builder.py`, `classifier/ollama_client.py`).

## Estructura del proyecto

```
classifier/
  html_cleaner.py       limpia el HTML del cuerpo del ticket
  prompt_builder.py      arma el prompt con las categorías reales de Plumsail
  ollama_client.py        clasifica usando Ollama local (activo por defecto)
  claude_client.py        clasifica usando la API de Claude (alternativa, requiere key)
  ticket_generator.py      genera tickets sintéticos aleatorios (datos ficticios)
config/
  categories.json          taxonomía real (Pregunta, Incidente, Problema, Pedido,
                            Requerimiento, No soporte) y política de prioridad
data/
  tickets_sinteticos.json    30 tickets ficticios (banco fijo para el modo por lote)
outputs/
  resultado_simulacion.xlsx  (se genera al correr run_simulation.py)
dashboard/
  app.py                  backend Flask del dashboard en vivo
  templates/dashboard.html
  static/style.css
  static/app.js
run_simulation.py       modo por lote (30 tickets → reporte Excel)
```

## Instalación

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Para clasificar necesitas Ollama (gratis, local, por defecto):

```powershell
# instalar desde https://ollama.com/download, luego:
ollama pull qwen3:14b
```

(Alternativa de pago: cambiar el import de `classifier.ollama_client` a
`classifier.claude_client` en `run_simulation.py` o `dashboard/app.py`, con tu
`ANTHROPIC_API_KEY`.)

## Modo 1 — Por lote (30 tickets → Excel)

```powershell
python run_simulation.py
```

Clasifica los 30 tickets sintéticos del banco fijo, imprime el resultado y el resumen
en consola, y guarda el reporte completo en `outputs/resultado_simulacion.xlsx`.

## Modo 2 — Dashboard en vivo (para la sustentación)

```powershell
cd dashboard
python app.py
```

Abre **http://localhost:5000** en tu navegador. Verás una "sala de control" con:

- Botón **"Generar ticket"**: crea un ticket sintético nuevo y lo clasifica en vivo,
  mostrando el estado "Nuevo" → "Analizando IA…" → el resultado con un sello de
  categoría, barra de confianza, resumen y acción sugerida.
- **Modo automático**: genera un ticket nuevo cada 5 segundos, útil para dejarlo
  corriendo de fondo durante la demo.
- Panel lateral con distribución en vivo por categoría y por acción recomendada
  (auto-clasificado / revisión normal / revisión prioritaria).
- **Reiniciar**: limpia el feed y las estadísticas de la sesión.

Cada ticket que ves ahí es generado en el momento (nombres, comercios y contenido
ficticios combinados aleatoriamente por `ticket_generator.py`) y clasificado de
verdad por el modelo local — no es una animación simulada, es el bot real
funcionando en tiempo real.

## Sobre los datos sintéticos

Tanto el banco fijo (`data/tickets_sinteticos.json`) como el generador aleatorio
(`classifier/ticket_generator.py`) mantienen la misma estructura de campos que la API
real de Plumsail (para que la lógica de limpieza y clasificación sea técnicamente
válida), pero **todos los nombres, correos, empresas y números de documento son
ficticios**. Cubren las 6 categorías reales, más casos límite relevantes:

- Ticket con "Urgente" en el asunto pero prioridad real Normal — valida que el modelo
  no infla la prioridad solo por esa palabra (política estricta de la empresa).
- Incidente que afecta a varios comercios a la vez — valida la distinción entre
  "Incidente" (pocas solicitudes) y "Problema" (afecta muchos/varios comercios).
- Correos automáticos — deben clasificar como "No soporte".
- Solicitudes de funcionalidad que no existe — deben clasificar como "Requerimiento",
  distinto de "Pedido" (ajuste sobre algo que ya existe).

Puedes agregar más plantillas en `classifier/ticket_generator.py` (diccionario
`PLANTILLAS`) siguiendo el mismo patrón.
