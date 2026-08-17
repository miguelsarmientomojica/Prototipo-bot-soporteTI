# Cómo ejecutar el dashboard en tu navegador

## 1. Requisitos (una sola vez)

```powershell
# Desde la raíz del proyecto (donde está requirements.txt)
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Y si aún no tienes Ollama instalado con el modelo descargado:

```powershell
# instalar desde https://ollama.com/download, luego:
ollama pull qwen3:14b
```

Ollama queda corriendo solo en segundo plano (no necesitas "abrirlo" cada vez).

## 2. Arrancar el servidor

```powershell
cd dashboard
python app.py
```

Vas a ver algo como:

```
Dashboard disponible en http://localhost:5000
Base de datos: C:\...\proto\tickets.db
 * Running on http://127.0.0.1:5000
```

**Deja esa ventana de PowerShell abierta** — mientras esté corriendo, el servidor está
disponible. Si la cierras, el dashboard deja de funcionar (pero tus datos siguen
guardados en `tickets.db` para la próxima vez).

## 3. Abrir el dashboard en el navegador

Abre tu navegador normal (Chrome, Edge, Firefox — cualquiera) y ve a:

```
http://localhost:5000
```

Eso es todo — ahí ya tienes la "Sala de control": el botón para generar tickets, el
formulario manual, las pestañas "En llegada" / "Todos los tickets" con filtros.

## 4. Para cerrar

En la ventana de PowerShell donde corre el servidor, presiona `Ctrl + C`. Tus datos
quedan guardados en `tickets.db` — la próxima vez que corras `python app.py`, todo
sigue ahí.

## Problemas comunes (por si algo falla)

**`ModuleNotFoundError: No module named 'flask'`**
El entorno virtual existe pero nunca se instalaron las dependencias dentro de él (o
estás corriendo con el Python del sistema, no el de `.venv`). Arréglalo así:
```powershell
cd "ruta\a\tu\proyecto"
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
Deberías ver al final algo como `Successfully installed flask-...`. Luego vuelve a
correr `python dashboard\app.py`. (Si usas `iniciar_dashboard.bat`, ya no te va a pasar
esto — lo actualicé para que detecte e instale automáticamente lo que falte.)

**"This site can't be reached" / no carga la página**
El servidor no está corriendo. Revisa la ventana de PowerShell — si no dice
`Running on http://127.0.0.1:5000`, algo falló al arrancar (lee el error que muestra).

**Error de conexión al generar un ticket ("Error de Ollama")**
Ollama no está corriendo o no tiene el modelo descargado. Prueba en otra ventana:
```powershell
ollama run qwen3:14b "di hola"
```
Si eso falla, reinstala/reabre Ollama antes de volver a intentar en el dashboard.

**"Address already in use" / puerto 5000 ocupado**
Ya tienes otra instancia de `app.py` corriendo (revisa si dejaste otra ventana
abierta), o algún otro programa usa ese puerto. Ciérrala, o cambia el puerto editando
la última línea de `dashboard/app.py`: `app.run(debug=False, port=5001)` y entra por
`http://localhost:5001`.

## 5. Para que se vea bonito (modo presentación)

El diseño (tema oscuro, sellos rotados, tarjetas animadas) está pensado para verse bien
en un navegador moderno de escritorio, no en móvil ni en ventanas muy angostas.

- **Usa Chrome, Edge o Firefox actualizados** — el diseño usa CSS Grid, que estos
  navegadores soportan perfecto (si alguna vez viste una captura rara de este dashboard,
  era por una herramienta de captura vieja, no por el diseño real).
- **Maximiza la ventana** — el layout está pensado para pantallas anchas (mínimo
  ~1200px). En una ventana angosta las tarjetas se ven apretadas.
- **Necesitas internet la primera vez que abres la página** — carga 3 tipografías desde
  Google Fonts (Space Grotesk, Inter, IBM Plex Mono). Sin internet igual funciona, solo
  cae a una tipografía genérica del sistema, se ve un poco menos pulido.
- **Modo "app" sin barras del navegador** (opcional, se ve más profesional en una
  sustentación): en vez de abrir una pestaña normal, corre esto en PowerShell con el
  servidor ya prendido:
  ```powershell
  start chrome --app=http://localhost:5000
  ```
  Abre una ventana limpia, sin barra de direcciones ni pestañas — parece una aplicación
  de escritorio real. (Si no tienes Chrome, con Edge es `start msedge --app=http://localhost:5000`.)
- **F11** en el navegador activa pantalla completa — combínalo con el modo app de arriba
  para la demo en vivo.

## 6. Arranque en un clic (opcional)

Para no escribir los comandos cada vez, usa `iniciar_dashboard.bat` (en la raíz del
proyecto, junto a este archivo) — ábrelo con doble clic y hace todo: activa el entorno,
arranca el servidor, y abre el navegador en modo app automáticamente.



## 7. Nota: esto NO sale a internet

`http://localhost:5000` solo es accesible **desde tu propia computadora**. Nadie más
puede entrar a esa URL, ni siquiera en tu misma red — es exactamente el comportamiento
que buscamos (100% local, sin exponer nada). Si algún día quisieras que otra persona lo
vea desde otro dispositivo, eso sería un paso aparte (no necesario para tu entrega).
