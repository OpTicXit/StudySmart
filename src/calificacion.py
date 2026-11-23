# © 2026 Miguel Ángel Martínez. Todos los derechos reservados. Ver LICENSE.
"""Esquemas de calificación configurables (cualquier escuela/universidad).

El modelo se entrenó en una escala de REFERENCIA 0-5 que aprueba con 3.0.
Para cualquier otra escala, la nota se convierte por tramos: [mín, aprobatoria] -> [0, 3]
y [aprobatoria, máx] -> [3, 5]. Así "aprobar" significa lo mismo en todos los esquemas.

Formato de las notas de un estudiante (`notas`):
    {corte: número | letra | None,                            # nota total del corte (o pendiente)
     corte: {componente: número | [n1, n2, None, ...]}}       # por componentes; varias notas del
                                                              # mismo componente pesan igual; None = pendiente
"""
from dataclasses import dataclass

REF_MIN, REF_APROB, REF_MAX = 0.0, 3.0, 5.0


@dataclass
class Esquema:
    nombre: str
    minimo: float
    maximo: float
    aprobatoria: float
    cortes: dict            # nombre del corte -> peso (deben sumar 1), en orden cronológico
    letras: dict | None = None  # opcional: letra -> valor numérico (p. ej. A=4)
    componentes: dict | None = None  # opcional: corte -> {componente: peso} (cada uno suma 1)

    def __post_init__(self):
        if not self.minimo < self.aprobatoria < self.maximo:
            raise ValueError("debe cumplirse mínimo < aprobatoria < máximo")
        if not self.cortes or abs(sum(self.cortes.values()) - 1) > 1e-6:
            raise ValueError("los pesos de los cortes deben sumar 1")
        for c, comps in (self.componentes or {}).items():
            if c not in self.cortes:
                raise ValueError(f"componentes de un corte inexistente: {c}")
            if abs(sum(comps.values()) - 1) > 1e-6:
                raise ValueError(f"los pesos de los componentes de {c} deben sumar 1")

    # --- conversión ---
    def a_numero(self, nota):
        if isinstance(nota, str):
            if not self.letras or nota.strip().upper() not in self.letras:
                raise ValueError(f"letra no válida para {self.nombre}: {nota!r}")
            return float(self.letras[nota.strip().upper()])
        nota = float(nota)
        if not self.minimo <= nota <= self.maximo:
            raise ValueError(f"nota {nota} fuera de la escala {self.minimo:g}-{self.maximo:g}")
        return nota

    def a_ref(self, nota):
        n = self.a_numero(nota)
        if n <= self.aprobatoria:
            return REF_MIN + (n - self.minimo) / (self.aprobatoria - self.minimo) * (REF_APROB - REF_MIN)
        return REF_APROB + (n - self.aprobatoria) / (self.maximo - self.aprobatoria) * (REF_MAX - REF_APROB)

    def desde_ref(self, r):
        r = min(max(float(r), REF_MIN), REF_MAX)
        if r <= REF_APROB:
            return self.minimo + (r - REF_MIN) / (REF_APROB - REF_MIN) * (self.aprobatoria - self.minimo)
        return self.aprobatoria + (r - REF_APROB) / (REF_MAX - REF_APROB) * (self.maximo - self.aprobatoria)

    def a_letra(self, n):
        """Letra más alta cuyo valor no supera n (solo si el esquema usa letras)."""
        if not self.letras:
            return None
        validas = [l for l, v in sorted(self.letras.items(), key=lambda t: -t[1]) if v <= n + 1e-9]
        return validas[0] if validas else min(self.letras, key=self.letras.get)

    # --- espacios calificables ---
    def espacios(self, notas: dict) -> list:
        """Desglosa las notas en espacios con su peso en el corte y en la asignatura."""
        extra = set(notas) - set(self.cortes)
        if extra:
            raise ValueError(f"cortes no definidos en {self.nombre}: {extra}")
        out = []
        for c, wc in self.cortes.items():
            v, comps = notas.get(c), (self.componentes or {}).get(c)
            if isinstance(v, dict) or (v is None and comps):
                if not comps:
                    raise ValueError(f"{c} no tiene componentes definidos")
                v = v or {}
                malos = set(v) - set(comps)
                if malos:
                    raise ValueError(f"componentes no definidos en {c}: {malos}")
                for k, wk in comps.items():
                    vals = v.get(k)
                    vals = list(vals) if isinstance(vals, (list, tuple)) else [vals]
                    vals = vals or [None]
                    for i, x in enumerate(vals, 1):
                        out.append({"corte": c, "componente": k, "n": i, "peso_corte": wk / len(vals),
                                    "peso": wc * wk / len(vals), "nota": None if x is None else self.a_numero(x)})
            else:
                out.append({"corte": c, "componente": None, "n": 1, "peso_corte": 1.0, "peso": wc,
                            "nota": None if v is None else self.a_numero(v)})
        return out

    def resumen(self, notas: dict, corte: str | None = None, objetivo: float | None = None) -> dict:
        """Estado de un corte (o de toda la asignatura si corte=None) con lo calificado hasta ahora.

        promedio_actual: promedio ponderado SOLO de lo ya calificado.
        evaluado:        fracción del peso ya calificada (0-1).
        necesario:       nota que hace falta en CADA espacio pendiente para llegar a `objetivo`
                         (por defecto la aprobatoria). None si no queda nada pendiente.
        """
        esp = [e for e in self.espacios(notas) if corte is None or e["corte"] == corte]
        if not esp:
            raise ValueError(f"corte no definido: {corte}")
        w = "peso" if corte is None else "peso_corte"
        cal = [e for e in esp if e["nota"] is not None]
        w_cal = sum(e[w] for e in cal)
        suma = sum(e[w] * e["nota"] for e in cal)
        w_pend = sum(e[w] for e in esp) - w_cal
        obj = self.aprobatoria if objetivo is None else objetivo
        return {"promedio_actual": suma / w_cal if w_cal > 1e-9 else None,
                "evaluado": w_cal, "acumulado": suma,
                "necesario": (obj - suma) / w_pend if w_pend > 1e-9 else None,
                "pendientes": len(esp) - len(cal)}

    def conocidos(self, notas: dict, min_evaluado: float = 0.5) -> dict:
        """Nota de cada corte para el modelo, en orden cronológico.
        shortcut: un corte con al menos `min_evaluado` calificado se aproxima con su promedio actual;
        si con datos reales se ve sesgo, subir el umbral a 1.0 (solo cortes completos)."""
        out = {}
        for c in self.cortes:
            r = self.resumen(notas, corte=c)
            if r["evaluado"] >= min_evaluado - 1e-9:
                out[c] = r["promedio_actual"]
        return out

    def promedio_necesario(self, notas: dict, objetivo: float):
        """Nota necesaria en cada espacio pendiente de la asignatura para llegar a `objetivo`."""
        return self.resumen(notas, objetivo=objetivo)["necesario"]


_LP, _PA, _CE, _AA, _CG = ("Lectura previa", "Proyecto de aula", "Competencias específicas",
                           "Actividades académicas", "Competencias genéricas")
ESQUEMAS = {
    # Esquema institucional del usuario (imagen de referencia): 3 seguimientos con componentes.
    "Institucional 0-5 (3 seguimientos)": Esquema(
        "Institucional 0-5 (3 seguimientos)", 0, 5, 3.0,
        {"Seguimiento 1": 0.3, "Seguimiento 2": 0.3, "Seguimiento 3": 0.4},
        componentes={
            "Seguimiento 1": {_LP: 0.30, _CE: 0.35, _AA: 0.35},
            "Seguimiento 2": {_PA: 0.30, _CE: 0.35, _AA: 0.35},
            "Seguimiento 3": {_PA: 0.30, _CE: 0.35, _AA: 0.20, _CG: 0.15},
        }),
    "0-5 (3 cortes 30/30/40)": Esquema("0-5 (3 cortes 30/30/40)", 0, 5, 3.0,
                                       {"Corte 1": 0.3, "Corte 2": 0.3, "Corte 3": 0.4}),
    "0-10 (3 parciales iguales)": Esquema("0-10 (3 parciales iguales)", 0, 10, 6.0,
                                          {"Parcial 1": 1 / 3, "Parcial 2": 1 / 3, "Parcial 3": 1 / 3}),
    "0-20 (3 periodos, UCI)": Esquema("0-20 (3 periodos, UCI)", 0, 20, 10.0,
                                      {"G1": 1 / 3, "G2": 1 / 3, "G3": 1 / 3}),
    "0-100 (25/25/50)": Esquema("0-100 (25/25/50)", 0, 100, 60.0,
                                {"Parcial 1": 0.25, "Parcial 2": 0.25, "Final": 0.5}),
    "Letras A-F (40/60)": Esquema("Letras A-F (40/60)", 0, 4, 2.0, {"Midterm": 0.4, "Final": 0.6},
                                  letras={"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}),
}
ESQUEMA_DEFECTO = "Institucional 0-5 (3 seguimientos)"


if __name__ == "__main__":  # autocomprobación
    near = lambda a, b: abs(a - b) < 1e-9  # noqa: E731
    e = ESQUEMAS["0-20 (3 periodos, UCI)"]
    assert e.a_ref(10) == 3.0 and e.a_ref(0) == 0 and e.a_ref(20) == 5
    assert near(e.desde_ref(e.a_ref(13.7)), 13.7)

    i = ESQUEMAS[ESQUEMA_DEFECTO]
    s1 = {_LP: 4.0, _CE: 3.0, _AA: [2.0, 2.0]}
    assert near(i.conocidos({"Seguimiento 1": s1})["Seguimiento 1"], 1.2 + 1.05 + 0.7)
    # Solo la lectura previa (30 %): no alcanza el 50 % para el modelo; necesita (3 - 0.6) / 0.7 en lo demás
    parcial = {_LP: 2.0}
    assert i.conocidos({"Seguimiento 1": parcial}) == {}
    r = i.resumen({"Seguimiento 1": parcial}, corte="Seguimiento 1")
    assert near(r["necesario"], 2.4 / 0.7) and r["promedio_actual"] == 2.0 and r["pendientes"] == 2
    # Varias actividades: 2 de 3 calificadas, cada una pesa 0.35/3 dentro del corte
    acts = {_LP: 3.0, _CE: 3.0, _AA: [4.0, 2.0, None]}
    r = i.resumen({"Seguimiento 1": acts}, corte="Seguimiento 1")
    assert near(r["promedio_actual"], 3.0) and near(r["necesario"], 3.0) and r["pendientes"] == 1
    # Asignatura completa: con todo vacío el necesario es la aprobatoria
    assert near(i.resumen({})["necesario"], 3.0) and i.resumen({})["promedio_actual"] is None
    # Seguimiento entero como un solo número también vale
    assert near(i.resumen({"Seguimiento 1": 2.0, "Seguimiento 2": 3.0})["necesario"], (3 - 0.6 - 0.9) / 0.4)

    c = ESQUEMAS["0-5 (3 cortes 30/30/40)"]
    assert near(c.promedio_necesario({"Corte 1": 2.0, "Corte 2": 3.0}, 3.0), 3.75)
    assert c.promedio_necesario({"Corte 1": 3, "Corte 2": 3, "Corte 3": 3}, 3.0) is None
    l = ESQUEMAS["Letras A-F (40/60)"]
    assert l.a_ref("C") == 3.0 and l.a_letra(3.4) == "B"
    for bad in (lambda: c.a_numero(6), lambda: l.a_numero("Z"), lambda: c.conocidos({"Corte 9": 3}),
                lambda: Esquema("x", 0, 5, 3, {"a": 0.5}),
                lambda: Esquema("x", 0, 5, 3, {"a": 1}, componentes={"a": {"p": 0.9}}),
                lambda: i.conocidos({"Seguimiento 1": {"Inventado": 4}}),
                lambda: i.resumen({"Seguimiento 1": {_AA: [2.0, 9.0]}})):
        try:
            bad(); raise AssertionError("debía fallar")
        except ValueError:
            pass
    print("calificacion.py OK")
