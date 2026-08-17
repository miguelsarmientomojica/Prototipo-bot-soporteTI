@echo off
REM Lanzador de un clic para el dashboard.
REM Doble clic en este archivo desde el Explorador de Windows.

cd /d "%~dp0"

echo.
echo ==========================================
echo       CREDYTY DASHBOARD - INICIO
echo ==========================================
echo.

REM --------------------------------------------------
REM 1. Verificar entorno virtual
REM --------------------------------------------------

if not exist ".venv\Scripts\python.exe" (
    echo No encuentro el entorno virtual .venv en esta carpeta.
    echo Creandolo ahora...
    echo.

    python -m venv .venv

    if errorlevel 1 (
        echo.
        echo ERROR: No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
)

REM --------------------------------------------------
REM 2. Verificar dependencias
REM --------------------------------------------------

echo Verificando dependencias...

".venv\Scripts\python.exe" -c "import flask, openpyxl, bs4, openai, anthropic" >nul 2>nul

if errorlevel 1 (
    echo Faltan dependencias, instalando ahora...
    echo.

    ".venv\Scripts\python.exe" -m pip install -r requirements.txt

    if errorlevel 1 (
        echo.
        echo ==========================================
        echo ERROR: Fallo la instalacion de dependencias.
        echo ==========================================
        echo.
        pause
        exit /b 1
    )

    echo.
    echo Dependencias instaladas correctamente.
    echo.
)

REM --------------------------------------------------
REM 3. Comprobacion final
REM --------------------------------------------------

echo Comprobando que las dependencias funcionen...

".venv\Scripts\python.exe" -c "import flask, openpyxl, bs4, openai, anthropic" >nul 2>nul

if errorlevel 1 (
    echo.
    echo ==========================================
    echo ERROR: Las dependencias no pudieron
    echo importarse correctamente.
    echo ==========================================
    echo.
    pause
    exit /b 1
)

echo Dependencias OK.
echo.

REM --------------------------------------------------
REM 4. Arrancar dashboard
REM --------------------------------------------------

echo Arrancando el servidor del dashboard...

start "Dashboard - servidor (no cerrar)" cmd /k ".venv\Scripts\python.exe dashboard\app.py"

REM --------------------------------------------------
REM 5. Esperar al servidor
REM --------------------------------------------------

timeout /t 3 /nobreak >nul

REM --------------------------------------------------
REM 6. Abrir navegador
REM --------------------------------------------------

echo Abriendo el navegador...

where chrome >nul 2>nul

if errorlevel 1 (
    where msedge >nul 2>nul

    if errorlevel 1 (
        start http://localhost:5000
    ) else (
        start msedge --app=http://localhost:5000
    )
) else (
    start chrome --app=http://localhost:5000
)

echo.
echo ==========================================
echo Dashboard iniciado correctamente.
echo ==========================================
echo.
echo La ventana negra "Dashboard - servidor"
echo debe permanecer abierta mientras uses
echo el dashboard.
echo.
echo Para cerrar el servidor:
echo Ctrl+C dentro de la ventana del servidor.
echo.

exit /b 0