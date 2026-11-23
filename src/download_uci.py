# © 2026 Miguel Ángel Martínez. Todos los derechos reservados. Ver LICENSE.
"""
Descarga los datasets reales de UCI para StudySmart.

    python src/download_uci.py

Guarda en data/raw/:
  - student_performance.csv        (UCI id 320, secundaria, G1/G2/G3)
  - dropout_academic_success.csv   (UCI id 697, educación superior)

Si no hay acceso a internet, descarga los CSV a mano desde las páginas de UCI
y colócalos en data/raw/ con esos nombres.
"""
from pathlib import Path

import pandas as pd
from ucimlrepo import fetch_ucirepo

RAW = Path("data/raw")
RAW.mkdir(parents=True, exist_ok=True)


def guardar(uci_id: int, nombre: str) -> None:
    ds = fetch_ucirepo(id=uci_id)
    df = pd.concat([ds.data.features, ds.data.targets], axis=1)
    df.to_csv(RAW / nombre, index=False)
    print(f"[OK] {nombre}: {df.shape[0]} filas x {df.shape[1]} columnas")


if __name__ == "__main__":
    guardar(320, "student_performance.csv")
    guardar(697, "dropout_academic_success.csv")
