# Instalación desde cero — para correr el proyecto en un equipo nuevo

Esta guía asume que acabas de clonar (o descargar) el repositorio desde GitHub en una
computadora Windows que **no tiene nada de esto instalado todavía**. Al subir a GitHub
solo viaja el código — `.venv/` (el entorno de Python) y `tickets.db` (la base de
datos) están excluidos a propósito (ver `.gitignore`), así que hay que crearlos de
nuevo en cada equipo. Sigue los pasos en orden.

---

## 1. Requisitos previos (instalar una sola vez en el equipo nuevo)

### Python 3.11 o superior

1. Ve a **https://www.python.org/downloads/** y descarga la versión más reciente de
   Python 3 para Windows.
2. Al instalar, **marca la casilla "Add python.exe to PATH"** en la primera pantalla
   del instalador — es el error más común si se te olvida.
3. Verifica que quedó instalado, en PowerShell:
   ```powershell
   python --version
   ```
   Debe mostrar algo como `Python 3.11.x` o superior. Si dice que no reconoce el
   comando, cierra y vuelve a abrir PowerShell (a veces el PATH no se actualiza hasta
   reiniciar la terminal), y si sigue sin funcionar, reinstala marcando la casilla del
   paso 2.

### Git (si vas a clonar el repo, no si solo descargaste el .zip)

1. Descarga desde **https://git-scm.com/download/win** e instala con las opciones por
   defecto.
2. Verifica:
   ```powershell
   git --version
   ```

### Ollama (el motor de IA local — gratis, sin necesidad de tarjeta ni cuenta)

1. Ve a **https://ollama.com/download** y descarga el instalador de Windows.
2. Ejecútalo — no pide configuración especial, solo "Siguiente, Siguiente, Instalar".
3. Ollama queda corriendo en segundo plano automáticamente (ícono en la bandeja del
   sistema, junto al reloj) y arranca solo cada vez que enciendes el equipo. No hace
   falta iniciarlo manualmente.
4. Verifica que quedó instalado:
   ```powershell
   ollama --version
   ```

---

## 2. Descargar el modelo de IA (una sola vez, ~9 GB)

Con Ollama ya instalado y corriendo:

```powershell
ollama pull qwen3:14b
```

Esto descarga el modelo Qwen3 de 14 mil millones de parámetros — dependiendo de tu
conexión, puede tardar entre 10 y 40 minutos. Es un solo descargo; las siguientes veces
que uses el proyecto no hay que repetirlo.

**Requisito de hardware:** funciona bien en un equipo con al menos 16 GB de RAM. Si
tienes una GPU dedicada (NVIDIA con 8+ GB de VRAM), corre notablemente más rápido, pero
no es obligatorio — sin GPU corre en CPU, más lento pero funcional.

Prueba rápida de que el modelo responde:
```powershell
ollama run qwen3:14b "Responde solo con la palabra: funciona"
```
Debería responder algo como `funciona`. Sal con `/bye`.

---

## 3. Obtener el código del proyecto

**Si vas a clonar desde GitHub:**
```powershell
git clone https://github.com/tu-usuario/tu-repositorio.git
cd tu-repositorio
```

**Si descargaste un .zip desde GitHub** ("Code" → "Download ZIP"): descomprímelo en la
carpeta donde quieras trabajar, y abre PowerShell dentro de esa carpeta (Shift + clic
derecho → "Abrir ventana de PowerShell aquí", o `cd` manualmente hasta ahí).

---

## 4. Crear el entorno de Python e instalar las dependencias

Desde la carpeta raíz del proyecto (donde está `requirements.txt`):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea la activación con un error de "execution policy", corre una sola
vez (en una PowerShell como administrador si hace falta):
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
y vuelve a intentar activar.

Con el entorno activado (verás `(.venv)` al inicio de la línea):
```powershell
pip install -r requirements.txt
```

Esto instala Flask, openpyxl, beautifulsoup4, openai y anthropic — tarda uno o dos
minutos. Al final debe decir `Successfully installed ...` con la lista de paquetes.

---

## 5. Primera ejecución

### Opción A — con el lanzador de un clic (recomendada)

Haz doble clic en **`iniciar_dashboard.bat`** (está en la raíz del proyecto). Detecta
solo si faltan dependencias, arranca el servidor, y abre el navegador ya listo. Si todo
salió bien en los pasos anteriores, esto es lo único que necesitas de aquí en adelante.

### Opción B — manual

```powershell
cd dashboard
python app.py
```

Y abre **http://localhost:5000** en tu navegador (Chrome o Edge, de preferencia).

La primera vez que arranca, `database.py` crea automáticamente el archivo
`tickets.db` — no necesitas crearlo a mano, ni te va a dar error de que no existe.

---

## 6. Verificación de que todo quedó bien

1. En el dashboard, click en **"Generar ticket"**.
2. En unos segundos (puede tardar más la primera vez, mientras el modelo "calienta")
   debería aparecer el ticket con su clasificación: categoría, confianza, prioridad,
   comercio, fecha de vencimiento y responsable.
3. Ve a la pestaña **"Todos los tickets"** — debería aparecer ahí también.

Si esto funciona, la instalación quedó completa.

---

## 7. Problemas comunes en una instalación nueva

**`python no se reconoce como un comando interno o externo`**
Python no quedó en el PATH. Reinstala Python marcando "Add python.exe to PATH" (paso 1),
o cierra y abre una PowerShell nueva después de instalar.

**`No se puede cargar el archivo ... porque la ejecución de scripts está deshabilitada`**
Falta el permiso de ejecución de scripts de PowerShell — corre el comando
`Set-ExecutionPolicy` del paso 4.

**`ModuleNotFoundError: No module named 'flask'` (o cualquier otro módulo)**
El entorno virtual no tiene las dependencias instaladas, o estás corriendo con el
Python del sistema en vez del de `.venv`. Repite el paso 4 completo (activar `.venv` +
`pip install -r requirements.txt`). Si usas `iniciar_dashboard.bat`, esto se corrige
solo.

**`Error de Ollama: Connection error` al generar un ticket**
Ollama no está corriendo, o el modelo no se descargó. Verifica el ícono de Ollama en la
bandeja del sistema, y confirma que corriste `ollama pull qwen3:14b` (paso 2).

**El puerto 5000 ya está en uso / la página no carga**
Puede que otro proceso (a veces AirPlay en Mac, no aplica en Windows normalmente, o una
sesión anterior del dashboard que quedó abierta) esté usando el puerto. Cierra
cualquier ventana de PowerShell/CMD que diga "Dashboard - servidor" y vuelve a
intentar.

**El antivirus o el firewall de Windows preguntan si permitir Python/Flask**
Es normal la primera vez — dale "Permitir acceso" (solo afecta a redes locales, el
servidor sigue sin ser accesible desde internet).

---