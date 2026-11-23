# © 2026 Miguel Ángel Martínez. Todos los derechos reservados. Ver LICENSE.
"""Definiciones compartidas: features, columnas prohibidas y partición por estudiante."""
import os
import sys
from pathlib import Path

import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

RAIZ = Path(__file__).resolve().parents[1]
# Datos del usuario: en la app instalada, %APPDATA%\StudySmart (la carpeta del programa se reemplaza al actualizar)
DATOS_USUARIO = (Path(os.environ.get("APPDATA", Path.home())) / "StudySmart" if getattr(sys, "frozen", False)
                 else RAIZ / "data/raw")
SEED = 42
OBJETIVO = "riesgo_academico"
GRUPO = "id_estudiante"
PROHIBIDAS = {"nota_final", OBJETIVO, GRUPO}  # fuga de datos / identificador

NUM = [
    "semestre", "creditos", "dificultad_asignatura", "trabaja",
    "asignaturas_reprobadas_previas", "horas_estudio_semana", "asistencia_pct",
    "inasistencias", "actividades_completadas_pct", "ejercicios_correctos_pct",
    "comprension_tema", "nota_corte1", "nota_corte2", "horas_sueno",
    "dias_a_proxima_evaluacion", "promedio_cortes", "tendencia_notas",
]
CAT = ["asignatura", "jornada"]
FEATURES = NUM + CAT
assert not PROHIBIDAS & set(FEATURES), "fuga de datos en FEATURES"

# Hábitos de estudio para K-Means (sin notas: el cluster describe comportamiento)
HABITOS = [
    "horas_estudio_semana", "asistencia_pct", "actividades_completadas_pct",
    "ejercicios_correctos_pct", "comprension_tema",
]


def particion_por_estudiante(df: pd.DataFrame, test_size: float = 0.2):
    """Devuelve (train, test) sin estudiantes compartidos."""
    gss = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=SEED)
    i_tr, i_te = next(gss.split(df, groups=df[GRUPO]))
    tr, te = df.iloc[i_tr], df.iloc[i_te]
    assert not set(tr[GRUPO]) & set(te[GRUPO])
    return tr, te
