@echo off
rem StudySmart desde el codigo fuente (los usuarios instalan StudySmart-Setup.exe). La primera vez prepara el entorno y entrena el modelo.
chcp 65001 >nul
title StudySmart
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creando el entorno de Python por primera vez...
  python -m venv .venv || goto :error
  ".venv\Scripts\python" -m pip install -r requirements.txt || goto :error
)

if not exist "models\modelo_riesgo.joblib" (
  echo [2/3] Entrenando el modelo por primera vez, puede tardar 10-15 minutos...
  if not exist "data\raw\registros_sinteticos.csv" ".venv\Scripts\python" src\generate_data.py || goto :error
  if not exist "data\raw\student_performance.csv" ".venv\Scripts\python" src\download_uci.py || goto :error
  for %%n in (01_eda_preparacion 02_clustering_kmeans 03_modelos 04_prediccion_etapas) do (
    ".venv\Scripts\jupyter" nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=3000 notebooks\%%n.ipynb || goto :error
  )
)

echo [3/3] Abriendo StudySmart en su ventana...
".venv\Scripts\python" lanzador.py
goto :eof

:error
echo.
echo Ocurrio un error. Revisa los mensajes de arriba.
pause
