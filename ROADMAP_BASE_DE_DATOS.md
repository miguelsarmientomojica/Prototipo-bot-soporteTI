# Hoja de ruta — De "demo en memoria" a prototipo con base de datos real

## Dónde estás parado hoy (Fase 0, ya hecho)

Tu dashboard actual funciona así:

```
Ollama (clasifica) → Flask (dashboard/app.py) → variables Python en RAM (_historial, _stats)
                                                        │
                                                        ▼
                                              Frontend (JS, se resetea al recargar)
```

Funciona bien para la demo, pero tiene 2 limitaciones que ahora quieres resolver:
1. **No persiste** — si reinicias el servidor, se pierde todo.
2. **El frontend no "recuerda"** — al recargar la página, el feed vuelve a estar vacío aunque el servidor sí tenga datos.

Eso es exactamente lo que resuelve tener una base de datos real detrás.

---

## El plan completo, en 5 fases (cada una es un mensaje/sesión de trabajo, no todo junto)

### **Fase 1 — Base de datos local (SQLite)** ✅ Hecho
Diseñar el esquema y crear el archivo de base de datos. Nada de Flask todavía, solo la
base de datos en sí.

- **Por qué SQLite y no otra cosa**: es un archivo (`tickets.db`), no necesita instalar
  ningún servidor de base de datos, viene incluido en Python (`sqlite3`), y es
  exactamente lo que se usa en prototipos/proyectos académicos locales de este tamaño.
  Migrar a PostgreSQL/MySQL después, si algún día hace falta, es un cambio pequeño
  porque el diseño de tablas es el mismo.
- **2 tablas, no 1** (te explico por qué separar):
  - `tickets` — el ticket en sí: asunto, cuerpo, solicitante, comercio, origen
    (auto/manual), fecha de creación.
  - `clasificaciones` — el veredicto del bot sobre ese ticket: categoría, confianza,
    prioridad sugerida, fecha de vencimiento, responsable, si la info está completa,
    acción recomendada, fecha de la clasificación.
  - Separarlas te permite, más adelante, volver a clasificar el mismo ticket con otro
    modelo o umbral y comparar — imposible si mezclas todo en una sola tabla.

**Entregable de esta fase:** un archivo `database.py` con la definición de las tablas y
funciones básicas (`crear_ticket()`, `guardar_clasificacion()`, `listar_tickets()`), y
el archivo `tickets.db` ya creado. Se prueba de forma aislada, sin tocar Flask.

### **Fase 2 — Migrar el backend de Flask a la base de datos** ✅ Hecho
Reemplazar las variables `_historial` y `_stats` en `dashboard/app.py` por llamadas a
`database.py`.

- Los endpoints que ya tienes (`/api/tickets`, `/api/tickets/manual`,
  `/api/tickets/historial`, `/api/stats`) **mantienen la misma forma de respuesta JSON**
  — así no tienes que tocar nada del frontend en esta fase. Solo cambia qué hay "detrás"
  de cada endpoint.
- Resultado: apagas el servidor, lo vuelves a prender, y los tickets siguen ahí.

### **Fase 3 — El frontend deja de depender de la memoria del navegador** ✅ Hecho y verificado

Confirmado con pruebas reales: 28 tickets (25 automáticos + 3 manuales), feed inicial
carga los últimos 10 al abrir la página, filtros por categoría/comercio/prioridad/
responsable/acción funcionan en SQL (no en el navegador), búsqueda por texto con
debounce, umbral de confianza mínima, y paginación (20 por página) — todo probado y
sin errores.
- Al abrir el dashboard, en vez de arrancar con el feed vacío, carga los últimos N
  tickets reales desde la base de datos.
- La pestaña "Todos los tickets" deja de usar el array que vive solo en el navegador y
  pagina directo contra la base de datos — importante para cuando tengas cientos o
  miles de tickets (como los 5,000 que mencionas para más adelante) y no quieras cargar
  todo de un golpe en el navegador.

### **Fase 4 — (Opcional) Actualizaciones en vivo sin botón**
Ahora mismo generas un ticket con un click. Para que se sienta más "sistema real
recibiendo tickets solo", se podría agregar un proceso de fondo que genere tickets cada
cierto tiempo y los empuje al navegador automáticamente (Server-Sent Events, más simple
que WebSocket para este caso). **Esto es cosmético, no crítico** — lo dejaría para el
final, solo si sobra tiempo antes de la entrega.

### **Fase 5 — Terreno preparado para la evaluación (conecta con tu documento de tesis)**
Con la base de datos ya en pie, cuando llegue el momento de los 5,000 tickets sintéticos
para evaluación (lo que dejamos pendiente a propósito), simplemente:
- Se agrega una columna `categoria_esperada` (el "ground truth") a la tabla `tickets`.
- Las métricas (accuracy, F1, etc. que ya quedaron definidas en tu documento de
  investigación) se calculan con una consulta SQL simple, no procesando todo en memoria
  de Python.

Esto no lo hacemos ahora — es solo para que veas que el orden de las fases no es
arbitrario: la base de datos es el prerrequisito real de esa fase, por eso va primero.

---

## Qué NO cambia en ningún momento de este plan

- Sigue siendo 100% local — SQLite es un archivo en tu disco, no un servidor.
- Ollama sigue igual, `classifier/` no se toca.
- El diseño visual del dashboard (colores, sello, tarjetas) no cambia — solo de dónde
  saca los datos.

## Cómo seguimos

Dime cuándo quieres que empecemos con la **Fase 1** (base de datos y su esquema) y la
armo — sola, sin tocar Flask todavía, para que puedas revisarla con calma antes de que
sigamos a la Fase 2.
