# © 2026 Miguel Ángel Martínez. Todos los derechos reservados. Ver LICENSE.
"""Punto de entrada de StudySmart.exe: abre la app en su propia ventana.

El mismo ejecutable corre en dos procesos: la ventana (este main) y el servidor de Streamlit
(`StudySmart.exe --servidor <puerto>`). Si el servidor termina (por ejemplo, al instalar una
actualización) la ventana se cierra; si se cierra la ventana, se detiene el servidor.

    python lanzador.py          # probarlo desde el código fuente
"""
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

CONGELADO = bool(getattr(sys, "frozen", False))
BASE = Path(sys._MEIPASS) if CONGELADO else Path(__file__).resolve().parent  # noqa: SLF001

CARGANDO = """<html><body style="margin:0;height:100vh;display:flex;align-items:center;justify-content:center;
font-family:'Segoe UI',sans-serif;background:#F5F7FC;color:#1F2A5C"><div style="text-align:center">
<div style="font-size:56px">📚</div><div style="font-size:26px;font-weight:700">StudySmart</div>
<div style="margin-top:8px;color:#5B6380">Abriendo… la primera vez puede tardar unos segundos.</div>
</div></body></html>"""
ERROR = """<html><body style="font-family:'Segoe UI',sans-serif;padding:40px;color:#7F1D1D">
<h2>StudySmart no pudo iniciar</h2><p>Revisa el registro en <code>{log}</code> y vuelve a abrir el programa.</p>
</body></html>"""


def _modulos_para_pyinstaller():
    """Nunca se llama: le indica a PyInstaller qué incluir, porque app.py y src/ se copian como archivos."""
    import dataclasses, hashlib, html, json, threading  # noqa: F401, E401
    import joblib, numpy, pandas, pyarrow  # noqa: F401, E401
    import sklearn.cluster, sklearn.compose, sklearn.ensemble, sklearn.impute  # noqa: F401, E401
    import sklearn.model_selection, sklearn.pipeline, sklearn.preprocessing, sklearn.tree  # noqa: F401, E401


def carpeta_logs() -> Path:
    raiz = Path(os.environ.get("APPDATA", Path.home())) / "StudySmart" if CONGELADO else BASE / "data/raw"
    (raiz / "logs").mkdir(parents=True, exist_ok=True)
    return raiz / "logs"


def servidor(puerto: str):
    log = open(carpeta_logs() / "servidor.log", "w", encoding="utf-8", buffering=1)  # sin consola en el .exe
    sys.stdout = sys.stderr = log
    os.chdir(BASE)  # para que Streamlit lea .streamlit/config.toml
    from streamlit.web import cli
    sys.argv = ["streamlit", "run", str(BASE / "app.py"), "--server.port", puerto, "--server.address", "127.0.0.1",
                "--server.headless", "true", "--server.fileWatcherType", "none", "--global.developmentMode", "false",
                "--browser.gatherUsageStats", "false"]
    sys.exit(cli.main())


def puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def esperar(url: str, proc: subprocess.Popen, limite: float = 180) -> bool:
    t0 = time.time()
    while time.time() - t0 < limite and proc.poll() is None:
        try:
            urllib.request.urlopen(url + "/_stcore/health", timeout=1)
            return True
        except OSError:
            time.sleep(0.3)
    return False


def main():
    import webview

    puerto = str(puerto_libre())
    url = f"http://127.0.0.1:{puerto}"
    cmd = [sys.executable, "--servidor", puerto] if CONGELADO else [sys.executable, __file__, "--servidor", puerto]
    proc = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
    ventana = webview.create_window("StudySmart", html=CARGANDO, width=1280, height=800, min_size=(980, 640),
                                    maximized=True)

    def arrancar():
        if esperar(url, proc):
            ventana.load_url(url)
            proc.wait()  # el servidor terminó: actualización en curso o error
        else:
            ventana.load_html(ERROR.format(log=carpeta_logs() / "servidor.log"))
            return
        ventana.destroy()

    try:
        webview.start(arrancar, icon=str(BASE / "installer/studysmart.ico"))
    finally:
        if proc.poll() is None:
            proc.terminate()
    os._exit(0)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--servidor":
        servidor(sys.argv[2])
    else:
        main()
