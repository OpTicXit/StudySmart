# © 2026 Miguel Ángel Martínez. Todos los derechos reservados. Ver LICENSE.
"""Actualización desde GitHub Releases y registro de las novedades ya vistas.

La última release de github.com/OpTicXit/StudySmart trae el instalador StudySmart-Setup-x.y.z.exe
y sus notas (sección de CHANGELOG.md). `instalar()` lo ejecuta en silencio y cierra la app;
el instalador reemplaza los archivos y vuelve a abrir StudySmart.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import urllib.request
from pathlib import Path

from features import DATOS_USUARIO
from version import REPO, __version__, tupla

INSTALADO = bool(getattr(sys, "frozen", False))  # True en el .exe (también en su proceso servidor)
API = f"https://api.github.com/repos/{REPO}/releases/latest"
ESTADO = DATOS_USUARIO / "estado.json"
_UA = {"User-Agent": "StudySmart-actualizador", "Accept": "application/vnd.github+json"}


def ultima_version(timeout: float = 6) -> dict | None:
    """Datos de la última release o None si no hay conexión o aún no hay releases."""
    try:
        with urllib.request.urlopen(urllib.request.Request(API, headers=_UA), timeout=timeout) as r:
            d = json.load(r)
    except (OSError, ValueError):
        return None
    exe = next((a for a in d.get("assets", []) if a["name"].lower().endswith(".exe")), None)
    return {"version": d.get("tag_name", "").lstrip("v"), "notas": d.get("body") or "",
            "pagina": d.get("html_url"), "url": exe and exe["browser_download_url"],
            "tamano": exe and exe["size"], "digest": exe and exe.get("digest")}


def hay_nueva(info: dict | None) -> bool:
    return bool(info and info["version"]) and tupla(info["version"]) > tupla(__version__)


def descargar(info: dict, progreso=None) -> Path:
    """Descarga el instalador a %TEMP% y comprueba tamaño y SHA-256 (si GitHub lo publica)."""
    url = info["url"]
    if not url or not url.startswith(f"https://github.com/{REPO}/releases/download/"):
        raise ValueError("La release no tiene un instalador válido.")
    destino = Path(tempfile.gettempdir()) / url.rsplit("/", 1)[-1]
    sha, hecho = hashlib.sha256(), 0
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": _UA["User-Agent"]}), timeout=30) as r, \
            open(destino, "wb") as f:
        total = int(r.headers.get("Content-Length") or info.get("tamano") or 0)
        while bloque := r.read(1 << 20):
            f.write(bloque); sha.update(bloque); hecho += len(bloque)
            if progreso and total:
                progreso(min(hecho / total, 1.0))
    if info.get("tamano") and hecho != info["tamano"]:
        raise ValueError("La descarga quedó incompleta; inténtalo de nuevo.")
    if info.get("digest") and info["digest"] != f"sha256:{sha.hexdigest()}":
        raise ValueError("El instalador descargado no coincide con el publicado; no se instaló.")
    return destino


def instalar(instalador: Path):
    """Lanza el instalador sin preguntas y cierra este proceso; el lanzador cierra la ventana."""
    flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP: sobrevive al cierre de la app
    subprocess.Popen([str(instalador), "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS"],
                     creationflags=flags, close_fds=True)
    threading.Timer(2.0, os._exit, [0]).start()  # deja que la interfaz muestre el aviso antes de cerrar


def version_vista() -> str | None:
    try:
        return json.loads(ESTADO.read_text(encoding="utf-8")).get("version_vista")
    except (OSError, ValueError):
        return None


def marcar_vista():
    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    ESTADO.write_text(json.dumps({"version_vista": __version__}), encoding="utf-8")
