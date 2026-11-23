# © 2026 Miguel Ángel Martínez. Todos los derechos reservados. Ver LICENSE.
"""Versión de StudySmart y lectura de sus novedades en CHANGELOG.md.

    python src/version.py              # imprime la versión
    python src/version.py --notas 1.2.0  # imprime las novedades de esa versión (falla si no existen)
"""
import re
import sys
from pathlib import Path

__version__ = "1.0.0"
REPO = "OpTicXit/StudySmart"
AUTOR = "Miguel Ángel Martínez"
COPYRIGHT = f"© 2026 {AUTOR}. Todos los derechos reservados."
CHANGELOG = Path(__file__).resolve().parents[1] / "CHANGELOG.md"


def tupla(v: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3])


def notas_de(version: str, texto: str | None = None) -> str:
    """Sección '## [x.y.z] ...' de CHANGELOG.md, sin el título."""
    texto = CHANGELOG.read_text(encoding="utf-8") if texto is None else texto
    v = re.escape(version.lstrip("v"))
    m = re.search(rf"^## \[?v?{v}\]?[^\n]*\n(.*?)(?=^## |\Z)", texto, re.M | re.S)
    return m.group(1).strip() if m else ""


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    assert tupla("v1.10.0") > tupla("1.9.3") and notas_de("1.0", "## [1.0] - x\nA\n## [0.9]\nB") == "A"
    if len(sys.argv) == 3 and sys.argv[1] == "--notas":
        if tupla(sys.argv[2]) != tupla(__version__):
            sys.exit(f"La etiqueta {sys.argv[2]} no coincide con __version__ = {__version__} en src/version.py")
        notas = notas_de(sys.argv[2])
        if not notas:
            sys.exit(f"CHANGELOG.md no tiene una sección '## [{__version__}]' con novedades")
        print(notas)
    else:
        print(__version__)
