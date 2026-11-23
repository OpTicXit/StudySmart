# © 2026 Miguel Ángel Martínez. Todos los derechos reservados. Ver LICENSE.
"""
Generador de datos SINTÉTICOS para StudySmart.

Simula los registros académicos que la app capturaría (un registro por
estudiante-asignatura-semestre), SOLO con información disponible ANTES del
resultado final. La variable objetivo se deriva de la nota final.

IMPORTANTE: son datos simulados con relaciones que definimos nosotros. Sirven
para construir y probar el pipeline (limpieza, K-Means, Random Forest, árbol,
dashboard), NO para afirmar precisión real. Para eso se usan los datasets de
UCI y los registros personales reales.

Uso:
    python src/generate_data.py --n-estudiantes 300 --seed 42
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ASIGNATURAS = {
    # nombre: (dificultad 1-5, créditos)
    "Calculo Diferencial": (5, 4),
    "Algebra Lineal": (4, 3),
    "Programacion I": (3, 4),
    "Estructuras de Datos": (4, 4),
    "Bases de Datos": (3, 3),
    "Estadistica": (4, 3),
    "Ingles": (2, 2),
    "Ingenieria de Software": (3, 3),
    "Fisica Mecanica": (5, 4),
    "Etica Profesional": (1, 2),
}


def generar(n_estudiantes: int, semestres: int, umbral: float, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    nombres = list(ASIGNATURAS)
    filas = []

    for est in range(1, n_estudiantes + 1):
        # Rasgos latentes del estudiante (no se exportan)
        habilidad = rng.normal(0, 1)          # capacidad base
        disciplina = rng.normal(0, 1)         # constancia / organización
        trabaja = rng.random() < 0.3          # trabaja y estudia
        jornada = rng.choice(["diurna", "nocturna"], p=[0.75, 0.25])
        previas = 0                           # asignaturas reprobadas acumuladas

        for sem in range(1, semestres + 1):
            n_mat = int(rng.integers(4, 7))
            reprobadas_sem = 0
            for mat in rng.choice(nombres, size=n_mat, replace=False):
                dificultad, creditos = ASIGNATURAS[mat]

                # --- Hábitos (dependen de disciplina, trabajo y dificultad) ---
                horas = np.clip(
                    rng.normal(6 + 2.0 * disciplina - 2.5 * trabaja + 0.5 * dificultad, 2.5),
                    0, 30,
                )
                asistencia = np.clip(
                    rng.normal(88 + 5 * disciplina - 5 * trabaja, 8), 40, 100
                )
                actividades = np.clip(
                    rng.normal(75 + 10 * disciplina + 0.8 * horas - 6 * (dificultad - 3), 14),
                    0, 100,
                )
                comprension = np.clip(
                    np.round(3 + 0.7 * habilidad + 0.06 * (horas - 8) - 0.35 * (dificultad - 3)
                             + rng.normal(0, 0.7)),
                    1, 5,
                )
                ejercicios = np.clip(
                    rng.normal(55 + 9 * habilidad + 4 * (comprension - 3) - 3 * (dificultad - 3), 12),
                    0, 100,
                )

                # --- Rendimiento latente del semestre ---
                base = (
                    3.75
                    + 0.38 * habilidad
                    + 0.022 * (horas - 8)
                    + 0.012 * (asistencia - 85)
                    + 0.004 * (actividades - 75)
                    + 0.004 * (ejercicios - 55)
                    + 0.10 * (comprension - 3)
                    - 0.12 * (dificultad - 3)
                    - 0.06 * previas
                )

                # Notas parciales previas (corte 1 y corte 2) con ruido propio
                corte1 = np.clip(base + rng.normal(0, 0.55), 0, 5)
                tendencia = rng.normal(0.08 * disciplina - 0.03 * (dificultad - 3), 0.25)
                corte2 = np.clip(base + tendencia + rng.normal(0, 0.55), 0, 5)

                # Nota final (EL OBJETIVO se deriva de aquí; no es feature)
                nota_final = float(np.clip(base + 0.5 * tendencia + rng.normal(0, 0.45), 0, 5))

                # Distractores débiles (para que el modelo no sea trivial)
                horas_sueno = float(np.clip(rng.normal(6.5, 1.2), 3, 10))
                dias_a_eval = int(rng.integers(1, 30))

                filas.append(
                    dict(
                        id_estudiante=est,
                        semestre=sem,
                        asignatura=mat,
                        creditos=creditos,
                        dificultad_asignatura=dificultad,
                        jornada=jornada,
                        trabaja=int(trabaja),
                        asignaturas_reprobadas_previas=previas,
                        horas_estudio_semana=round(float(horas), 1),
                        asistencia_pct=round(float(asistencia), 1),
                        inasistencias=int(round((100 - asistencia) / 100 * 32)),
                        actividades_completadas_pct=round(float(actividades), 1),
                        ejercicios_correctos_pct=round(float(ejercicios), 1),
                        comprension_tema=int(comprension),
                        nota_corte1=round(float(corte1), 2),
                        nota_corte2=round(float(corte2), 2),
                        horas_sueno=round(horas_sueno, 1),
                        dias_a_proxima_evaluacion=dias_a_eval,
                        nota_final=round(nota_final, 2),
                    )
                )
                if nota_final < umbral:
                    reprobadas_sem += 1
            previas = min(previas + reprobadas_sem, 6)  # acumulado al cerrar el semestre

    df = pd.DataFrame(filas)

    # Variables derivadas que la app calcularía (INFORMACIÓN)
    df["promedio_cortes"] = ((df.nota_corte1 + df.nota_corte2) / 2).round(2)
    df["tendencia_notas"] = (df.nota_corte2 - df.nota_corte1).round(2)

    # Variable objetivo
    df["riesgo_academico"] = (df.nota_final < umbral).astype(int)

    # Suciedad realista para practicar la limpieza (~3% de nulos en algunas columnas)
    for col in ["horas_estudio_semana", "comprension_tema", "ejercicios_correctos_pct"]:
        mask = rng.random(len(df)) < 0.03
        df[col] = df[col].astype("float64")
        df.loc[mask, col] = np.nan

    return df


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--n-estudiantes", type=int, default=300)
    p.add_argument("--semestres", type=int, default=4)
    p.add_argument("--umbral", type=float, default=3.0, help="Nota mínima de aprobación (escala 0-5)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", type=str, default="data/raw/registros_sinteticos.csv")
    a = p.parse_args()

    df = generar(a.n_estudiantes, a.semestres, a.umbral, a.seed)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)

    print(f"Registros: {len(df)} | Estudiantes: {df.id_estudiante.nunique()}")
    print(f"Guardado en: {out}")
    print("Balance riesgo_academico:")
    print(df.riesgo_academico.value_counts(normalize=True).round(3).to_string())


if __name__ == "__main__":
    main()
