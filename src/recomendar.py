# © 2026 Miguel Ángel Martínez. Todos los derechos reservados. Ver LICENSE.
"""DECISIÓN: dado un registro, devuelve riesgo, cluster, notas previstas y recomendaciones.

    python src/recomendar.py            # ejemplo + autocomprobación

Uso:
    from recomendar import recomendar, priorizar
    r = recomendar({"asignatura": "Calculo Diferencial", "horas_estudio_semana": 4, ...},
                   notas={"corte1": 2.6}, esquema="0-5 (3 cortes 30/30/40)", umbral_alerta=0.5)

`esquema` y `umbral_alerta` son los parámetros que fija cada institución o profesor.
Los campos que falten en `registro` se imputan con la mediana de train (dentro del Pipeline).
"""
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from calificacion import ESQUEMA_DEFECTO, ESQUEMAS, Esquema  # noqa: E402
from features import CAT, FEATURES, HABITOS, RAIZ  # noqa: E402
from modelo import nombres_clusters  # noqa: E402

RUTA_MODELO = RAIZ / "models/modelo_riesgo.joblib"
_paquete = None

TEXTOS = {
    "ejercicios_correctos_pct": "Practica más ejercicios del tema y revisa cada error: aciertas {v:.0f} % (la mediana es {m:.0f} %).",
    "comprension_tema": "Refuerza el tema con tutoría o asesoría del profesor: tu comprensión es {v:.0f}/5 (mediana {m:.0f}/5).",
    "actividades_completadas_pct": "Ponte al día con las actividades: llevas {v:.0f} % entregadas (mediana {m:.0f} %).",
    "asistencia_pct": "Sube tu asistencia: estás en {v:.0f} % (mediana {m:.0f} %).",
    "horas_estudio_semana": "Aumenta las horas de estudio semanales: {v:.1f} h (mediana {m:.1f} h).",
}


def cargar():
    global _paquete
    if _paquete is None:
        if not RUTA_MODELO.exists():
            raise FileNotFoundError(f"No existe {RUTA_MODELO}. Ejecuta notebooks/04_prediccion_etapas.ipynb.")
        _paquete = joblib.load(RUTA_MODELO)
        _paquete["nombres_clusters"] = nombres_clusters(_paquete["kmeans"])  # regla vigente de modelo.py
    return _paquete


def _a_features(registro: dict, conocidos_ref: list) -> pd.DataFrame:
    """Registro + notas (en escala de referencia) -> fila con las columnas del modelo."""
    fila = {c: registro.get(c, np.nan) for c in FEATURES}
    fila["asignatura"] = registro.get("asignatura_modelo") or registro.get("asignatura", np.nan)  # nombre que conoce el modelo
    if conocidos_ref:
        # shortcut: con 3+ cortes conocidos, corte1 = promedio de los anteriores y corte2 = el último
        # (el modelo se entrenó con 2 cortes); si hay datos reales con más cortes, reentrenar.
        c1 = float(np.mean(conocidos_ref[:-1])) if len(conocidos_ref) >= 2 else conocidos_ref[0]
        fila["nota_corte1"] = c1
        if len(conocidos_ref) >= 2:
            c2 = conocidos_ref[-1]
            fila.update(nota_corte2=c2, promedio_cortes=(c1 + c2) / 2, tendencia_notas=c2 - c1)
    # categorías como object: si vienen vacías (NaN) el one-hot las ignora en vez de fallar
    return pd.DataFrame([fila]).astype({c: object for c in CAT})


def _recomendaciones(registro, etapa, prob, alerta, perfil, esq, notas, final_prevista, max_n=3):
    p = cargar()
    ref, imp = p["ref_train"], p["etapas"][etapa]["importancia"].clip(lower=0)
    puntajes = {}
    for c in p["accionables"]:
        v = registro.get(c)
        if v is None or pd.isna(v):
            continue
        deficit = (ref.loc["median", c] - v) / ref.loc["std", c]  # >0: por debajo de lo típico
        if deficit > 0 and imp.get(c, 0) > 0:
            puntajes[c] = imp[c] * deficit
    recs = []
    asig = registro.get("asignatura", "esta asignatura")
    if alerta:
        necesario = esq.promedio_necesario(notas, esq.aprobatoria)
        if necesario is None:
            recs.append(f"Prioriza {asig}: la nota final ya está definida y no alcanza el aprobado.")
        elif necesario > esq.maximo:
            recs.append(f"Prioriza {asig}: ya no es posible aprobar solo con las notas pendientes; habla con el profesor.")
        else:
            recs.append(f"Prioriza {asig}: necesitas {max(necesario, esq.minimo):.2f} en cada nota pendiente "
                        f"para aprobar la asignatura (nota final prevista: {final_prevista:.2f}).")
    for c in sorted(puntajes, key=puntajes.get, reverse=True)[: max_n - len(recs)]:
        t = TEXTOS[c].format(v=registro[c], m=ref.loc["median", c])
        if c == "comprension_tema" and perfil.startswith("esfuerzo alto"):
            t += " Ya dedicas muchas horas: cambia el método (ejercicios guiados, explicar en voz alta) más que estudiar más."
        recs.append(t)
    if not recs:
        sin_habitos = all(pd.isna(registro.get(c, np.nan)) for c in p["accionables"])
        recs.append("Ingresa tus hábitos de estudio para recibir recomendaciones personalizadas." if sin_habitos else
                    "Mantén tus hábitos: estás en o por encima de lo típico en las variables que más pesan.")
    return recs


def recomendar(registro: dict, notas: dict | None = None, esquema: str | Esquema = ESQUEMA_DEFECTO,
               umbral_alerta: float | None = None) -> dict:
    p = cargar()
    esq = ESQUEMAS[esquema] if isinstance(esquema, str) else esquema
    notas = notas or {}
    umbral = p["umbral_prob"] if umbral_alerta is None else umbral_alerta
    conocidos = esq.conocidos(notas)
    faltan = [c for c in esq.cortes if c not in conocidos]
    etapa = min(len(conocidos), 2)
    m = p["etapas"][etapa]
    X = _a_features(registro, [esq.a_ref(v) for v in conocidos.values()])[m["features"]]

    cluster = int(p["kmeans"].transform(X[HABITOS])[0, 0])
    perfil = p["nombres_clusters"][cluster]
    if all(pd.isna(registro.get(h, np.nan)) for h in HABITOS):  # sin hábitos el cluster sale de medianas
        perfil = "sin datos de hábitos"

    r_asig = esq.resumen(notas)
    if r_asig["pendientes"] == 0:  # todo calificado: la nota final ya está definida
        final = r_asig["acumulado"]
        prob, previstos = float(final < esq.aprobatoria), {}
    else:
        prob = float(m["clf"].predict_proba(X)[0, 1])
        final = esq.desde_ref(m["reg_final"].predict(X)[0])
        previstos = {}
        if m["reg_siguiente"] is not None and len(faltan) >= 2:
            previstos[faltan[0]] = esq.desde_ref(m["reg_siguiente"].predict(X)[0])
        resto = [c for c in faltan if c not in previstos]
        if resto:  # lo que deben valer los demás cortes para que la nota final sea la prevista
            prom = esq.promedio_necesario({**conocidos, **previstos}, final)
            previstos.update({c: float(np.clip(prom, esq.minimo, esq.maximo)) for c in resto})

    alerta = prob >= umbral
    nivel = "alto" if alerta else "medio" if prob >= 0.6 * umbral else "bajo"
    por_corte = {c: _redondear(esq.resumen(notas, corte=c)) for c in esq.cortes}
    recs = _recomendaciones(registro, etapa, prob, alerta, perfil, esq, notas, final)
    for c, d in reversed(list(por_corte.items())):
        if 0 < d["evaluado"] < 1:  # corte a medias: decir cuánto falta para aprobarlo
            n = d["necesario"]
            recs.insert(0, f"En {c} llevas {d['evaluado']:.0%} calificado (promedio {d['promedio_actual']:.2f}): "
                           f"necesitas {max(n, esq.minimo):.2f} en cada nota pendiente para aprobarlo."
                           if n <= esq.maximo else
                           f"En {c} ya no alcanzas {esq.aprobatoria:g} con lo pendiente; compénsalo en los siguientes.")
    return {
        "asignatura": registro.get("asignatura"),
        "esquema": esq.nombre,
        "cortes_conocidos": len(conocidos),
        "etapa_modelo": etapa,
        "prob_riesgo": round(prob, 3),
        "nivel_riesgo": nivel,
        "alerta": alerta,
        "cluster": cluster,
        "perfil": perfil,
        "nota_final_prevista": round(final, 2),
        "letra_prevista": esq.a_letra(final),
        "cortes_previstos": {c: round(v, 2) for c, v in previstos.items()},
        "promedio_actual": None if r_asig["promedio_actual"] is None else round(r_asig["promedio_actual"], 2),
        "evaluado": round(r_asig["evaluado"], 3),
        "promedio_necesario_para_aprobar": None if r_asig["necesario"] is None else round(r_asig["necesario"], 2),
        "por_corte": por_corte,
        "recomendaciones": recs[:3],
    }


def _redondear(d):
    return {k: (round(v, 3) if isinstance(v, float) else v) for k, v in d.items()}


def priorizar(registros: list, **kwargs) -> pd.DataFrame:
    """Lista de (registro, notas) -> tabla de asignaturas ordenada por riesgo (decisión de prioridad)."""
    filas = [recomendar(r, n, **kwargs) for r, n in registros]
    return pd.DataFrame(filas).sort_values("prob_riesgo", ascending=False).reset_index(drop=True)


if __name__ == "__main__":
    base = dict(semestre=2, dificultad_asignatura=5, jornada="diurna", trabaja=1,
                asignaturas_reprobadas_previas=2, horas_estudio_semana=4.0, asistencia_pct=78,
                inasistencias=7, actividades_completadas_pct=60, ejercicios_correctos_pct=35,
                comprension_tema=2, horas_sueno=6, dias_a_proxima_evaluacion=10)
    debil = {**base, "asignatura": "Calculo Diferencial"}
    fuerte = {**base, "asignatura": "Bases de Datos", "dificultad_asignatura": 3,
              "horas_estudio_semana": 8, "asistencia_pct": 95, "inasistencias": 2,
              "actividades_completadas_pct": 95, "ejercicios_correctos_pct": 80, "comprension_tema": 4,
              "asignaturas_reprobadas_previas": 0, "trabaja": 0}

    import json
    seg1 = {"Lectura previa": 2.5, "Competencias específicas": 2.4, "Actividades académicas": [2.8, 3.0]}  # ≈ 2.605
    for notas in ({}, {"Seguimiento 1": {"Lectura previa": 2.5}}, {"Seguimiento 1": seg1},
                  {"Seguimiento 1": seg1, "Seguimiento 2": 2.8}):
        print(json.dumps(recomendar(debil, notas), ensure_ascii=False, indent=1))
    print(priorizar([(debil, {"Seguimiento 1": 2.6}), (fuerte, {"Seguimiento 1": 4.2})])
          [["asignatura", "prob_riesgo", "nivel_riesgo", "perfil", "nota_final_prevista"]])

    # Componentes con varias notas = nota del seguimiento
    r5 = recomendar(debil, {"Seguimiento 1": seg1})
    v1 = ESQUEMAS[ESQUEMA_DEFECTO].conocidos({"Seguimiento 1": seg1})["Seguimiento 1"]
    r_total = recomendar(debil, {"Seguimiento 1": v1})
    assert (r5["prob_riesgo"], r5["nota_final_prevista"]) == (r_total["prob_riesgo"], r_total["nota_final_prevista"])
    # Seguimiento con solo 30 % calificado: no alimenta el modelo, pero informa lo que falta
    r_parcial = recomendar(debil, {"Seguimiento 1": {"Lectura previa": 2.5}})
    assert r_parcial["cortes_conocidos"] == 0 and r_parcial["recomendaciones"][0].startswith("En Seguimiento 1")
    assert r_parcial["por_corte"]["Seguimiento 1"]["evaluado"] == 0.3
    # Mismo estudiante en otra escala: el riesgo debe ser igual (la conversión conserva el aprobado)
    r20 = recomendar(debil, {"G1": ESQUEMAS["0-20 (3 periodos, UCI)"].desde_ref(v1)}, esquema="0-20 (3 periodos, UCI)")
    assert r5["prob_riesgo"] == r20["prob_riesgo"], (r5, r20)
    assert recomendar(fuerte, {"Seguimiento 1": 4.2})["prob_riesgo"] < r5["prob_riesgo"]
    todo = recomendar(debil, {"Seguimiento 1": 1, "Seguimiento 2": 1, "Seguimiento 3": 1})
    assert todo["prob_riesgo"] == 1.0 and todo["promedio_necesario_para_aprobar"] is None
    # Asignatura del plan nuevo (desconocida para el modelo) no rompe la predicción
    assert 0 <= recomendar({**debil, "asignatura": "Cálculo integral"}, {})["prob_riesgo"] <= 1
    # Sin jornada ni asignatura (categorías vacías) no debe fallar
    assert 0 <= recomendar({"dificultad_asignatura": 3}, {})["prob_riesgo"] <= 1
    letras = recomendar(debil, {"Midterm": "C"}, esquema="Letras A-F (40/60)")
    assert letras["letra_prevista"] in "ABCDF"
    assert recomendar(debil, {}, umbral_alerta=0.0)["alerta"] is True
    print("recomendar.py OK")
