# © 2026 Miguel Ángel Martínez. Todos los derechos reservados. Ver LICENSE.
"""Constructores de pipelines compartidos por notebooks, recomendar.py y app."""
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

from features import CAT, HABITOS, NUM, SEED

K_CLUSTERS = 3  # elegido en notebooks/02 (codo + silueta + interpretabilidad)


class ClusterLabel(BaseEstimator, TransformerMixin):
    """K-Means como transformador: devuelve la etiqueta del cluster (columna 2D)."""

    def __init__(self, k=K_CLUSTERS):
        self.k = k

    def fit(self, X, y=None):
        self.km_ = KMeans(self.k, n_init=10, random_state=SEED).fit(X)
        return self

    def transform(self, X):
        return self.km_.predict(X).reshape(-1, 1)

    def get_feature_names_out(self, input_features=None):
        return np.array(["cluster"])


def pipeline_kmeans(k=K_CLUSTERS):
    """Imputación + escalado + K-Means sobre HABITOS (ajustar solo con train)."""
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), ClusterLabel(k))


def nombrar_cluster(z_horas, z_comprension):
    """Nombre del perfil según el centroide estandarizado (horas vs. comprensión)."""
    if z_comprension > 0:
        return "estudio constante y dominio" if z_horas > 0 else "eficiente con pocas horas"
    return "esfuerzo alto, baja comprensión" if z_horas > 0 else "pocas horas y baja constancia"


def nombres_clusters(pipe_km):
    """Nombres de cada cluster de un pipeline (ya ajustado) que contenga ClusterLabel."""
    c = next(s for s in pipe_km if isinstance(s, ClusterLabel)).km_.cluster_centers_
    ih, ic = HABITOS.index("horas_estudio_semana"), HABITOS.index("comprension_tema")
    return {i: nombrar_cluster(c[i, ih], c[i, ic]) for i in range(len(c))}


def preprocesador(con_cluster=False, num=NUM):
    pasos = [
        ("num", SimpleImputer(strategy="median"), num),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CAT),
    ]
    if con_cluster:
        km = pipeline_kmeans()
        km.steps.append(("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False)))
        pasos.append(("km", km, HABITOS))
    return ColumnTransformer(pasos, verbose_feature_names_out=False)


def construir(tipo, num=NUM, regresion=False):
    """tipo: 'arbol' | 'rf' | 'hibrido' (K-Means + RF). regresion=True predice la nota (RF)."""
    if regresion:
        clf = RandomForestRegressor(n_estimators=300, n_jobs=-1, random_state=SEED)
    elif tipo == "arbol":
        clf = DecisionTreeClassifier(max_depth=4, class_weight="balanced", random_state=SEED)
    else:
        clf = RandomForestClassifier(n_estimators=300, class_weight="balanced",
                                     n_jobs=-1, random_state=SEED)
    return Pipeline([("prep", preprocesador(tipo == "hibrido", num)), ("clf", clf)])


# Etapas del semestre según cuántas notas de corte se conocen.
CORTES = ["nota_corte1", "nota_corte2", "promedio_cortes", "tendencia_notas"]
NUM_ETAPA = {
    0: [c for c in NUM if c not in CORTES],                          # alerta temprana
    1: [c for c in NUM if c not in CORTES[1:]],                      # solo primer corte
    2: NUM,                                                          # dos cortes
}
