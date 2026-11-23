# © 2026 Miguel Ángel Martínez. Todos los derechos reservados. Ver LICENSE.
"""StudySmart — app de seguimiento del riesgo académico.

    streamlit run app.py        (o el ejecutable instalado StudySmart.exe)
"""
import html
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from actualizar import INSTALADO, descargar, hay_nueva, instalar, marcar_vista, ultima_version, version_vista  # noqa: E402
from calificacion import ESQUEMA_DEFECTO, ESQUEMAS, Esquema  # noqa: E402
from features import DATOS_USUARIO, RAIZ  # noqa: E402
from recomendar import recomendar  # noqa: E402
from version import COPYRIGHT, REPO, __version__, notas_de  # noqa: E402

st.set_page_config(page_title="StudySmart", page_icon="📚", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
  .block-container {max-width: 1320px; padding-top: 1.6rem; padding-bottom: 3rem;}
  header[data-testid="stHeader"] {background: transparent;}
  input::placeholder {color: #9AA0B5 !important; font-style: italic; opacity: 1 !important;}
  h1, h2, h3, h4 {letter-spacing: -0.01em;}
  .marca {display:flex; align-items:center; gap:.7rem; margin-bottom:.2rem;}
  .marca .logo {font-size:2rem;} .marca .t {font-size:1.75rem; font-weight:800; color:#1F2A5C; line-height:1;}
  .marca .s {color:#5B6380; font-size:.95rem; margin-top:.25rem;}
  .sec {display:flex; align-items:center; gap:.55rem; font-weight:700; font-size:1.08rem; color:#16182B; margin:.1rem 0 .6rem;}
  .sec .n {display:inline-flex; width:1.6rem; height:1.6rem; border-radius:50%; background:#1F2A5C; color:#fff;
           align-items:center; justify-content:center; font-size:.85rem;}
  .comp {font-weight:600; color:#16182B; line-height:1.25;} .comp small {display:block; font-weight:400; color:#5B6380;}
  .kpis {display:grid; grid-template-columns:repeat(auto-fit, minmax(120px, 1fr)); gap:.6rem; margin:.4rem 0 .8rem;}
  .kpi {background:#F5F7FC; border:1px solid #E3E7F1; border-radius:12px; padding:.7rem .9rem;}
  .kpi .l {font-size:.8rem; color:#5B6380; font-weight:600; text-transform:uppercase; letter-spacing:.03em;}
  .kpi .v {font-size:1.6rem; font-weight:800; color:#16182B; line-height:1.25; margin-top:.15rem;}
  .kpi .v.t {font-size:1.05rem; font-weight:700; line-height:1.35; margin:.3rem 0 .1rem;}
  .kpi .x {font-size:.8rem; color:#5B6380;}
  .meta {border-radius:12px; padding:.9rem 1rem; margin:.2rem 0 .6rem; border:1px solid;}
  .meta .v {font-size:1.9rem; font-weight:800; line-height:1.15;} .meta .l {font-size:.95rem;}
  .tono-ok {background:#ECF8F0; border-color:#BFE6CC; color:#14532D;}
  .tono-info {background:#EEF3FF; border-color:#C9D6FB; color:#1E3A8A;}
  .tono-aviso {background:#FFF6E5; border-color:#F7D9A0; color:#7A4B00;}
  .tono-mal {background:#FDEDED; border-color:#F5C2C2; color:#7F1D1D;}
  .pill {display:inline-block; padding:.15rem .65rem; border-radius:999px; font-weight:700; font-size:.9rem;}
  .barra {height:10px; border-radius:6px; background:#E6E9F2; overflow:hidden; margin:.35rem 0 .2rem;}
  .barra > div {height:100%; border-radius:6px;}
  div[data-testid="stColumn"]:has(.fijo) > div {position: sticky; top: 3.2rem;}
  hr.sep {margin:.15rem 0 !important; border:none; border-top:1px solid #EDF0F6;}
  table.mini {width:100%; font-size:.82rem; border-collapse:collapse; margin:.2rem 0 .4rem;}
  table.mini th {color:#5B6380; font-weight:600; text-align:left; border-bottom:1px solid #E3E7F1; padding:.35rem .4rem;}
  table.mini td {border-bottom:1px solid #F0F2F8; padding:.35rem .4rem;}
  table.mini small {color:#7A8099;}
  .pie {color:#7A8099; font-size:.8rem; text-align:center; margin-top:2.5rem;}
</style>""", unsafe_allow_html=True)

PERSONALES = DATOS_USUARIO / "registros_personales.csv"
PLAN = pd.read_csv(RAIZ / "data/plan_estudios.csv")
CONFIDENCIALES = {"creditos"}  # no se usan aunque vengan en el CSV del profesor
NIVEL = {"alto": "🔴 Alto", "medio": "🟠 Medio", "bajo": "🟢 Bajo"}
COLOR_NIVEL = {"alto": ("#FDEDED", "#B42318"), "medio": ("#FFF6E5", "#B54708"), "bajo": ("#ECF8F0", "#067647")}


def fmt(x, nd=2):
    return "—" if x is None or pd.isna(x) else f"{x:.{nd}f}"


def seccion(n, texto):
    st.markdown(f'<div class="sec"><span class="n">{n}</span>{html.escape(texto)}</div>', unsafe_allow_html=True)


def kpis(items):
    """items: [(etiqueta, valor, nota)] en una fila de tarjetas del mismo tamaño."""
    celdas = "".join(f'<div class="kpi"><div class="l">{html.escape(l)}</div>'
                     f'<div class="v{" t" if len(str(v)) > 10 else ""}">{html.escape(str(v))}</div>'
                     f'<div class="x">{html.escape(x)}</div></div>' for l, v, x in items)
    st.markdown(f'<div class="kpis">{celdas}</div>', unsafe_allow_html=True)


def pill(nivel):
    fondo, color = COLOR_NIVEL[nivel]
    return f'<span class="pill" style="background:{fondo};color:{color}">{NIVEL[nivel]}</span>'


# ---------------- actualizaciones y novedades ----------------
@st.cache_data(ttl=3600, show_spinner=False)
def buscar_version():
    return ultima_version()


@st.dialog("Novedades de StudySmart", width="large")
def dialogo_novedades(version, notas):
    st.markdown(f"#### Versión {version}")
    st.markdown(notas or "_Esta versión no tiene notas._")
    if st.button("Entendido", type="primary", width="stretch"):
        st.rerun()


@st.dialog("Actualización disponible", width="large")
def dialogo_actualizar(info):
    st.markdown(f"Hay una versión nueva: **StudySmart {info['version']}** (tienes la {__version__}).")
    with st.container(height=280, border=True):
        st.markdown(info["notas"] or "_Esta versión no tiene notas._")
    if not INSTALADO:
        st.info("Estás usando StudySmart desde el código fuente: actualízalo con `git pull`. "
                "La actualización con un clic funciona en la versión instalada.")
        return
    if not info["url"]:
        st.warning("Esta versión todavía no tiene instalador. Vuelve a intentarlo en unos minutos.")
        return
    if st.button("⬇️ Actualizar ahora", type="primary", width="stretch"):
        barra = st.progress(0.0, "Descargando…")
        try:
            ruta = descargar(info, lambda f: barra.progress(f, f"Descargando… {f:.0%}"))
        except (OSError, ValueError) as e:
            st.error(f"No se pudo descargar la actualización: {e}")
            return
        barra.progress(1.0, "Listo")
        st.success("Instalando la actualización. StudySmart se cerrará y volverá a abrirse solo en unos segundos.")
        instalar(ruta)


def avisos_de_version():
    """Al abrir: novedades de la versión recién instalada y aviso si hay una más nueva."""
    if st.session_state.get("_novedades_revisadas"):
        return
    st.session_state._novedades_revisadas = True
    if version_vista() != __version__:
        marcar_vista()
        dialogo_novedades(__version__, notas_de(__version__))
    elif hay_nueva(info := buscar_version()):
        dialogo_actualizar(info)


# ---------------- barra lateral ----------------
def barra_lateral() -> tuple[Esquema, float]:
    sb = st.sidebar
    sb.markdown(f"### 📚 StudySmart\nVersión **{__version__}**")
    sb.markdown("#### ⚙️ Configuración")
    opciones = list(ESQUEMAS) + ["Personalizado…"]
    nombre = sb.selectbox("Sistema de calificación", opciones, index=opciones.index(ESQUEMA_DEFECTO))
    if nombre != "Personalizado…":
        esq = ESQUEMAS[nombre]
    else:
        c1, c2, c3 = sb.columns(3)
        mn, mx = c1.number_input("Mínimo", value=0.0), c2.number_input("Máximo", value=5.0)
        ap = c3.number_input("Aprueba", value=3.0)
        sb.caption("Cortes en orden; los pesos deben sumar 100.")
        cortes = sb.data_editor(pd.DataFrame({"corte": ["Corte 1", "Corte 2", "Corte 3"],
                                              "peso_%": [30.0, 30.0, 40.0]}), num_rows="dynamic").dropna()
        try:
            esq = Esquema("Personalizado", mn, mx, ap, {str(r.corte): r["peso_%"] / 100 for _, r in cortes.iterrows()})
        except ValueError as e:
            sb.error(f"Esquema inválido: {e}")
            st.stop()
    umbral = sb.slider("Alerta de riesgo desde", 0.05, 0.95, 0.50, 0.05, format="%.2f",
                       help="Probabilidad a partir de la cual una materia se marca en riesgo alto.")
    sb.caption("El modelo se entrenó con datos simulados: úsalo como apoyo, no como veredicto.")

    sb.divider()
    sb.markdown("#### 🔄 Actualizaciones")
    if sb.button("Buscar actualizaciones", width="stretch"):
        buscar_version.clear()
        info = buscar_version()
        if info is None:
            sb.warning("No se pudo consultar GitHub. Revisa tu conexión a internet.")
        elif hay_nueva(info):
            dialogo_actualizar(info)
        else:
            sb.success(f"Tienes la última versión ({__version__}).")
    if sb.button("Ver novedades de esta versión", width="stretch"):
        dialogo_novedades(__version__, notas_de(__version__))

    sb.divider()
    sb.caption(f"{COPYRIGHT}  \nUso gratuito según la [licencia](https://github.com/{REPO}/blob/main/LICENSE).  \n"
               f"[Código y descargas](https://github.com/{REPO})")
    return esq, umbral


# ---------------- notas: lectura del estado y captura ----------------
def clave(esq, asig, *partes):
    return "|".join([esq.nombre, asig, *map(str, partes)])


def n_por_defecto(componente):
    return 2 if "Actividades" in componente else 1


def leer_notas(esq: Esquema, asig: str) -> dict:
    """Construye `notas` desde lo que el usuario ya escribió (session_state)."""
    ss, notas = st.session_state, {}
    for c in esq.cortes:
        comps = (esq.componentes or {}).get(c)
        if comps and not ss.get(clave(esq, asig, c, "total?"), False):
            notas[c] = {k: [ss.get(clave(esq, asig, c, k, i)) for i in range(ss.get(clave(esq, asig, c, k, "n"), n_por_defecto(k)))]
                        for k in comps}
        else:
            notas[c] = ss.get(clave(esq, asig, c, "total"))
    return notas


def texto_necesario(esq: Esquema, nec):
    if nec is None:
        return "Completo"
    if nec <= esq.minimo:
        return "Ya está asegurado"
    if nec > esq.maximo:
        return "Ya no alcanza"
    return f"Necesitas {esq.a_letra(nec)}" if esq.letras else f"Necesitas {nec:.2f}"


def placeholder(esq: Esquema, nec):
    if nec is None or nec <= esq.minimo or nec > esq.maximo:
        return "pendiente"
    return f"pendiente · necesitas {esq.a_letra(nec) if esq.letras else f'{nec:.2f}'}"


def campo_nota(esq, etiqueta, key, ayuda):
    if esq.letras:
        return st.selectbox(etiqueta, list(esq.letras), index=None, key=key, placeholder=ayuda)
    return st.number_input(etiqueta, min_value=float(esq.minimo), max_value=float(esq.maximo), value=None,
                           step=0.1, format="%.2f", key=key, placeholder=ayuda)


def capturar_corte(esq: Esquema, asig: str, corte: str, ayuda: str):
    """Dibuja los campos de un corte. `ayuda` es lo que se muestra en cada espacio vacío."""
    comps = (esq.componentes or {}).get(corte)
    st.caption(f"**{corte}** vale {esq.cortes[corte]:.0%} de la asignatura.")
    if not comps:
        campo_nota(esq, "Nota del corte", clave(esq, asig, corte, "total"), ayuda)
        return
    if st.toggle("Solo tengo la nota total de este seguimiento", key=clave(esq, asig, corte, "total?")):
        campo_nota(esq, "Nota total", clave(esq, asig, corte, "total"), ayuda)
        return
    for j, (comp, w) in enumerate(comps.items()):
        if j:
            st.markdown('<hr class="sep">', unsafe_allow_html=True)
        nombre, cant = st.columns([3, 1.3], vertical_alignment="bottom")
        nombre.markdown(f'<div class="comp">{html.escape(comp)}<small>{w:.0%} del seguimiento</small></div>',
                        unsafe_allow_html=True)
        n = cant.number_input("N.º de notas", 1, 10, n_por_defecto(comp), key=clave(esq, asig, corte, comp, "n"),
                              help="Si este componente tiene varias notas (p. ej. varias actividades), "
                                   "todas pesan igual dentro del componente.")
        cols = st.columns(min(n, 3))
        for i in range(n):
            with cols[i % 3]:
                campo_nota(esq, f"Nota {i + 1}" if n > 1 else "Nota", clave(esq, asig, corte, comp, i), ayuda)


def bloque_resultado(esq: Esquema, r: dict, alcance: str):
    nec, prom = r["necesario"], r["promedio_actual"]
    if nec is None:
        ok = prom >= esq.aprobatoria
        tono, valor, texto = ("ok" if ok else "mal"), fmt(prom), f"{alcance} terminado: {'aprobado' if ok else 'no aprobado'} " \
                                                                 f"(se aprueba con {esq.aprobatoria:g})."
    elif nec <= esq.minimo:
        tono, valor, texto = "ok", "Asegurado", f"Con lo que llevas ya tienes {esq.aprobatoria:g} en {alcance.lower()}."
    elif nec > esq.maximo:
        tono, valor, texto = "mal", "No alcanza", f"Aunque saques {esq.maximo:g} en todo lo pendiente no llegas a " \
                                                  f"{esq.aprobatoria:g} en {alcance.lower()}."
    else:
        tono = "aviso" if nec > esq.aprobatoria else "info"
        valor = esq.a_letra(nec) if esq.letras else fmt(nec)
        texto = f"en cada nota pendiente para llegar a {esq.aprobatoria:g} en {alcance.lower()}."
    st.markdown(f'<div class="meta tono-{tono}"><div class="l">{"Necesitas" if tono in ("info", "aviso") else "Estado"}</div>'
                f'<div class="v">{html.escape(valor)}</div><div class="l">{html.escape(texto)}</div></div>',
                unsafe_allow_html=True)
    kpis([("Promedio actual", fmt(prom), "con lo calificado"), ("Calificado", f"{r['evaluado']:.0%}", "del total")])


# ---------------- pestaña estudiante ----------------
def habitos(asig: str) -> dict:
    k = lambda n: f"hab|{asig}|{n}"  # noqa: E731
    with st.expander("Mis hábitos en esta materia · opcional, mejoran la predicción"):
        a, b, c = st.columns(3)
        h = dict(
            horas_estudio_semana=a.number_input("Horas de estudio por semana", 0.0, 60.0, None, 0.5, key=k("h"), placeholder="sin dato"),
            asistencia_pct=b.number_input("Asistencia (%)", 0, 100, None, key=k("as"), placeholder="sin dato"),
            actividades_completadas_pct=c.number_input("Actividades entregadas (%)", 0, 100, None, key=k("ac"), placeholder="sin dato"),
        )
        a, b, c = st.columns(3)
        h.update(
            ejercicios_correctos_pct=a.number_input("Ejercicios correctos (%)", 0, 100, None, key=k("ej"), placeholder="sin dato"),
            comprension_tema=b.selectbox("Comprensión del tema", [1, 2, 3, 4, 5], index=None, key=k("co"),
                                         placeholder="sin dato",
                                         format_func=lambda v: f"{v} · " + ["muy baja", "baja", "media", "buena", "muy buena"][v - 1]),
            horas_sueno=c.number_input("Horas de sueño", 0.0, 14.0, None, 0.5, key=k("su"), placeholder="sin dato"),
        )
        a, b, c = st.columns(3, vertical_alignment="center")
        h.update(trabaja=int(a.toggle("Trabajo mientras estudio", key="hab|trabaja")),
                 jornada=b.radio("Jornada", ["diurna", "nocturna"], horizontal=True, key="hab|jornada"),
                 asignaturas_reprobadas_previas=c.number_input("Materias reprobadas antes", 0, 30, 0, key="hab|prev"))
        st.caption("Lo que dejes vacío se completa con el valor típico de los datos de entrenamiento.")
    if h["asistencia_pct"] is not None:
        h["inasistencias"] = round((100 - h["asistencia_pct"]) / 100 * 32)
    return {k: v for k, v in h.items() if v is not None}


def registro_base(fila_plan) -> dict:
    eq = fila_plan.equivalente_modelo
    return dict(asignatura=fila_plan.asignatura, asignatura_modelo=eq if isinstance(eq, str) else None,
                semestre=int(fila_plan.semestre), dificultad_asignatura=int(fila_plan.dificultad))


def pestaña_estudiante(esq: Esquema, umbral: float):
    izq, der = st.columns([1.25, 1], gap="large")
    with izq:
        with st.container(border=True):
            seccion(1, "Elige la asignatura")
            a, b = st.columns([1.15, 2])
            sem = a.selectbox("Semestre", sorted(PLAN.semestre.unique()), format_func=lambda s: f"{s}.º semestre")
            asig = b.selectbox("Asignatura", PLAN[PLAN.semestre == sem].asignatura)
            fila = PLAN[PLAN.asignatura == asig].iloc[0]
            alcance = st.radio("¿Qué quieres calcular?", ["Toda la asignatura", "Un solo seguimiento"], horizontal=True,
                               captions=[f"Lo que necesitas para que la nota final sea {esq.aprobatoria:g}",
                                         f"Lo que necesitas para que un seguimiento quede en {esq.aprobatoria:g}"])
            corte_sel = None
            if alcance == "Un solo seguimiento":
                corte_sel = st.segmented_control("Seguimiento", list(esq.cortes), default=list(esq.cortes)[0],
                                                 key=f"sel|{asig}") or list(esq.cortes)[0]

        notas = leer_notas(esq, asig)
        try:
            r = esq.resumen(notas, corte=corte_sel)
        except ValueError as e:
            st.error(str(e)); return
        with st.container(border=True):
            seccion(2, "Ingresa las notas que ya tienes")
            st.caption("Deja vacío lo que aún no te han calificado: ese espacio te dice cuánto necesitas.")
            ayuda = placeholder(esq, r["necesario"])
            if corte_sel or len(esq.cortes) == 1:
                capturar_corte(esq, asig, corte_sel or list(esq.cortes)[0], ayuda)
            else:  # una pestaña por seguimiento para no mostrar todo a la vez
                for tab, c in zip(st.tabs(list(esq.cortes)), esq.cortes):
                    with tab:
                        capturar_corte(esq, asig, c, ayuda)

        with st.container(border=True):
            seccion(3, "Cuéntanos cómo estudias")
            registro = {**registro_base(fila), **habitos(asig)}

    with der:
        st.markdown('<div class="fijo"></div>', unsafe_allow_html=True)
        with st.container(border=True):
            seccion("✓", f"Resultado · {corte_sel or 'asignatura completa'}")
            bloque_resultado(esq, r, corte_sel or "La asignatura")
            if not corte_sel and len(esq.cortes) > 1:
                filas = "".join(
                    f"<tr><td>{html.escape(c)} <small>({esq.cortes[c]:.0%})</small></td><td>{rc['evaluado']:.0%}</td>"
                    f"<td>{fmt(rc['promedio_actual'])}</td><td>{texto_necesario(esq, rc['necesario']).replace('Necesitas ', '')}</td></tr>"
                    for c, rc in ((c, esq.resumen(notas, corte=c)) for c in esq.cortes))
                st.markdown('<table class="mini"><thead><tr><th>Seguimiento</th><th>Calificado</th>'
                            f'<th>Promedio</th><th>Necesitas</th></tr></thead><tbody>{filas}</tbody></table>',
                            unsafe_allow_html=True)

        try:
            p = recomendar(registro, notas, esq, umbral)
        except ValueError as e:
            st.error(str(e)); return
        with st.container(border=True):
            seccion("★", "Predicción")
            fondo, color = COLOR_NIVEL[p["nivel_riesgo"]]
            st.markdown(f'Riesgo de perder la materia: <b>{p["prob_riesgo"]:.0%}</b> &nbsp;{pill(p["nivel_riesgo"])}'
                        f'<div class="barra"><div style="width:{p["prob_riesgo"]:.0%};background:{color}"></div></div>',
                        unsafe_allow_html=True)
            prevista = fmt(p["nota_final_prevista"]) + (f" ({p['letra_prevista']})" if p["letra_prevista"] else "")
            perfil = p["perfil"] if p["perfil"] != "sin datos de hábitos" else "Completa el paso 3"
            kpis([("Nota final prevista", prevista, f"aprueba con {esq.aprobatoria:g}"), ("Perfil de estudio", perfil, "")])
            if p["cortes_previstos"]:
                objetivo = {corte_sel: p["cortes_previstos"][corte_sel]} if corte_sel in p["cortes_previstos"] else p["cortes_previstos"]
                st.caption("Nota prevista · " + " · ".join(f"{c}: **{fmt(v)}**" for c, v in objetivo.items()))
            elif corte_sel:
                st.caption(f"{corte_sel} ya tiene suficientes notas: el modelo lo usa como dato, no lo predice.")
            st.markdown("**Recomendaciones**\n" + "\n".join(f"1. {x}" for x in p["recomendaciones"]))
            st.caption(f"Predicción con {p['cortes_conocidos']} seguimiento(s) con al menos la mitad calificada. "
                       "Modelo entrenado con datos simulados.")
            a, b = st.columns(2)
            if a.button("➕ Agregar a la lista", width="stretch", type="primary", help="La compara con tus otras materias en «Mis materias»"):
                st.session_state.setdefault("materias", {})[asig] = (registro, notas)
                st.toast(f"{asig} agregada a Mis materias")
            if b.button("💾 Guardar registro", width="stretch"):
                fila_csv = {**registro, "fecha": datetime.now().isoformat(timespec="seconds"), "esquema": esq.nombre,
                            "notas": json.dumps(notas, ensure_ascii=False), "prob_riesgo": p["prob_riesgo"]}
                PERSONALES.parent.mkdir(parents=True, exist_ok=True)
                pd.DataFrame([fila_csv]).to_csv(PERSONALES, mode="a", header=not PERSONALES.exists(), index=False)
                st.toast(f"Guardado en {PERSONALES}")


def pestaña_materias(esq: Esquema, umbral: float):
    materias = st.session_state.get("materias", {})
    if not materias:
        st.info("Aún no agregas materias. En **Mi asignatura** usa «➕ Agregar a la lista» para compararlas aquí.")
        return
    filas = []
    for asig, (reg, notas) in materias.items():
        try:
            p = recomendar(reg, notas, esq, umbral)
        except ValueError:
            continue  # notas de otro sistema de calificación
        filas.append({"Asignatura": asig, "Riesgo": p["prob_riesgo"], "Nivel": NIVEL[p["nivel_riesgo"]],
                      "Promedio actual": p["promedio_actual"], "Nota prevista": p["nota_final_prevista"],
                      "Necesitas en lo pendiente": texto_necesario(esq, p["promedio_necesario_para_aprobar"]),
                      "Primera recomendación": p["recomendaciones"][0]})
    df = pd.DataFrame(filas).sort_values("Riesgo", ascending=False)
    st.markdown("### Prioridad de mis materias")
    st.caption("Ordenadas de mayor a menor riesgo: dedica primero tu tiempo a las de arriba.")
    kpis([("Materias", len(df), "en la lista"), ("En riesgo alto", int((df.Nivel == NIVEL["alto"]).sum()), "priorízalas"),
          ("Primera en la lista", df.Asignatura.iloc[0], f"riesgo {df.Riesgo.iloc[0]:.0%}")])
    dos = st.column_config.NumberColumn(format="%.2f")
    st.dataframe(df, hide_index=True, width="stretch",
                 column_config={"Riesgo": st.column_config.ProgressColumn("Riesgo", min_value=0, max_value=1, format="percent"),
                                "Promedio actual": dos, "Nota prevista": dos,
                                "Primera recomendación": st.column_config.TextColumn(width="large")})
    if st.button("Vaciar lista"):
        st.session_state.materias = {}
        st.rerun()


# ---------------- pestaña profesor ----------------
def col_csv(corte, comp=None):
    return f"{corte} · {comp}" if comp else corte


def plantilla(esq: Esquema, n=30) -> pd.DataFrame:
    """Ejemplo con estudiantes simulados: Seguimiento 1 calificado, el 2 a medias, el 3 vacío."""
    df = pd.read_csv(RAIZ / "data/processed/registros_limpios.csv")
    t = df[df.particion == "test"].sample(n, random_state=42).reset_index(drop=True)
    asigs = PLAN.asignatura.sample(n, replace=True, random_state=1).values
    out = pd.DataFrame({"estudiante": t.id_estudiante, "asignatura": asigs})
    for c in ["horas_estudio_semana", "asistencia_pct", "actividades_completadas_pct", "ejercicios_correctos_pct",
              "comprension_tema", "trabaja", "jornada", "asignaturas_reprobadas_previas"]:
        out[c] = t[c]
    cortes = list(esq.cortes)
    for i, c in enumerate(cortes):
        comps = (esq.componentes or {}).get(c)
        fuente = t["nota_corte1"] if i == 0 else t["nota_corte2"] if i == 1 else None
        if not comps:
            out[col_csv(c)] = [round(esq.desde_ref(v), 2) for v in fuente] if fuente is not None else None
            continue
        for j, k in enumerate(comps):
            if fuente is None or (i == 1 and j > 0):  # seguimiento 2: solo el primer componente calificado
                out[col_csv(c, k)] = ";".join([""] * n_por_defecto(k)) if n_por_defecto(k) > 1 else None
            else:
                v = [f"{esq.desde_ref(x):.2f}" for x in fuente]
                out[col_csv(c, k)] = [";".join([x] * n_por_defecto(k)) for x in v]
    return out


def a_lista(v):
    """'3.5;4;' -> [3.5, 4.0, None] (vacío = nota pendiente)."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return [None]
    return [float(x) if x.strip() else None for x in str(v).replace(",", ".").split(";")] if ";" in str(v) else [float(v)]


def notas_de_fila(fila: dict, esq: Esquema) -> dict:
    notas = {}
    for c in esq.cortes:
        comps = (esq.componentes or {}).get(c)
        total = fila.get(col_csv(c))
        if comps and not (total is not None and pd.notna(total)):
            notas[c] = {k: a_lista(fila.get(col_csv(c, k))) for k in comps}
        else:
            notas[c] = None if total is None or pd.isna(total) else (total if esq.letras else float(total))
    return notas


def pestaña_profesor(esq: Esquema, umbral: float):
    izq, der = st.columns([1.4, 1], gap="large")
    with izq:
        st.markdown("### Panel docente")
        st.markdown("Sube un CSV con **una fila por estudiante y asignatura**:")
        st.markdown(f"- Una columna por componente, por ejemplo `{col_csv(*_ejemplo_col(esq))}`.\n"
                    "- Varias notas del mismo componente se separan con `;`; un hueco es una nota pendiente: `3.5;4.0;`.\n"
                    "- Si solo tienes la nota total de un seguimiento, usa una columna con su nombre, por ejemplo "
                    f"`{list(esq.cortes)[0]}`.")
    with der:
        with st.container(border=True):
            archivo = st.file_uploader("Archivo CSV de tu curso", type="csv")
            st.download_button("⬇️ Descargar plantilla de ejemplo", plantilla(esq).to_csv(index=False).encode("utf-8"),
                               "plantilla_studysmart.csv", width="stretch")
            ejemplo = archivo is None and st.toggle("Ver con datos de ejemplo", value=True)
    if archivo is None and not ejemplo:
        return
    datos = pd.read_csv(archivo) if archivo is not None else plantilla(esq)
    faltan = [c for c in ["estudiante", "asignatura"] if c not in datos]
    if faltan:
        st.error(f"Faltan columnas obligatorias: {faltan}")
        return

    filas, errores = [], []
    barra = st.progress(0.0, "Analizando…")
    for i, f in enumerate(datos.to_dict("records")):
        plan = PLAN[PLAN.asignatura == f["asignatura"]]
        reg = {**(registro_base(plan.iloc[0]) if len(plan) else {}),
               **{k: v for k, v in f.items() if pd.notna(v) and k not in CONFIDENCIALES}}
        try:
            p = recomendar(reg, notas_de_fila(f, esq), esq, umbral)
            filas.append({"estudiante": f["estudiante"], **p})
        except ValueError as e:
            errores.append(f"Fila {i + 2} ({f['estudiante']}): {e}")
        barra.progress((i + 1) / len(datos), "Analizando…")
    barra.empty()
    if errores:
        with st.expander(f"⚠️ {len(errores)} fila(s) con errores"):
            st.write("\n\n".join(errores))
    if not filas:
        return
    res = pd.DataFrame(filas).sort_values("prob_riesgo", ascending=False)

    if archivo is None:
        st.caption("Mostrando datos de ejemplo simulados.")
    kpis([("Registros", len(res), "analizados")] +
         [(f"Riesgo {n}", int((res.nivel_riesgo == n).sum()), f"{(res.nivel_riesgo == n).mean():.0%} del curso")
          for n in ["alto", "medio", "bajo"]])

    f1, f2 = st.columns(2)
    niveles = f1.multiselect("Nivel de riesgo", list(NIVEL), list(NIVEL), format_func=NIVEL.get)
    asigs = f2.multiselect("Asignatura", sorted(res.asignatura.unique()), placeholder="Todas")
    vista = res[res.nivel_riesgo.isin(niveles)]
    if asigs:
        vista = vista[vista.asignatura.isin(asigs)]
    tabla = pd.DataFrame({
        "Estudiante": vista.estudiante, "Asignatura": vista.asignatura, "Riesgo": vista.prob_riesgo,
        "Nivel": vista.nivel_riesgo.map(NIVEL), "Calificado": vista.evaluado,
        "Promedio actual": vista.promedio_actual, "Nota prevista": vista.nota_final_prevista,
        "Necesita en lo pendiente": vista.promedio_necesario_para_aprobar.map(lambda x: texto_necesario(esq, None if pd.isna(x) else x))})
    dos = st.column_config.NumberColumn(format="%.2f")
    st.dataframe(tabla, hide_index=True, width="stretch", height=380,
                 column_config={"Riesgo": st.column_config.ProgressColumn(min_value=0, max_value=1, format="percent"),
                                "Calificado": st.column_config.NumberColumn(format="percent"),
                                "Promedio actual": dos, "Nota prevista": dos})

    g1, g2 = st.columns([3, 2], gap="large")
    with g1:
        st.markdown("**Riesgo medio por asignatura**")
        por_asig = (res.groupby("asignatura").agg(Riesgo=("prob_riesgo", "mean"), Registros=("prob_riesgo", "size"))
                    .sort_values("Riesgo", ascending=False).reset_index().rename(columns={"asignatura": "Asignatura"}))
        st.dataframe(por_asig, hide_index=True, width="stretch", height=300,
                     column_config={"Riesgo": st.column_config.ProgressColumn(min_value=0, max_value=1, format="percent")})
    with g2:
        st.markdown("**Estudiantes por perfil de estudio**")
        st.dataframe(res.perfil.value_counts().rename_axis("Perfil").reset_index(name="Registros"),
                     hide_index=True, width="stretch")

    st.markdown("**Detalle de un estudiante**")
    sel = st.selectbox("Estudiante", vista.estudiante.astype(str).unique(), label_visibility="collapsed")
    for _, r in vista[vista.estudiante.astype(str) == sel].iterrows():
        with st.container(border=True):
            st.markdown(f"#### {html.escape(str(r.asignatura))} &nbsp;{pill(r.nivel_riesgo)} "
                        f"<span style='color:#5B6380;font-size:1rem'>{r.prob_riesgo:.0%}</span>", unsafe_allow_html=True)
            st.write(f"**Perfil de estudio:** {r.perfil}")
            st.dataframe(pd.DataFrame([{"Seguimiento": c, "Calificado": d["evaluado"], "Promedio actual": d["promedio_actual"],
                                        "Para aprobar el seguimiento": texto_necesario(esq, d["necesario"])}
                                       for c, d in r.por_corte.items()]), hide_index=True, width="stretch",
                         column_config={"Calificado": st.column_config.NumberColumn(format="percent"),
                                        "Promedio actual": st.column_config.NumberColumn(format="%.2f")})
            st.markdown("\n".join(f"1. {x}" for x in r.recomendaciones))

    salida = res.drop(columns=["por_corte", "cortes_previstos"]).assign(recomendaciones=res.recomendaciones.str.join(" | "))
    st.download_button("⬇️ Descargar resultados", salida.to_csv(index=False).encode("utf-8"), "resultados_studysmart.csv")


def _ejemplo_col(esq):
    c = list(esq.cortes)[0]
    comps = (esq.componentes or {}).get(c)
    return (c, list(comps)[-1]) if comps else (c,)


# ---------------- main ----------------
st.markdown('<div class="marca"><span class="logo">📚</span><div><div class="t">StudySmart</div>'
            '<div class="s">Calcula lo que necesitas para aprobar y anticipa el riesgo en cada asignatura.</div></div></div>',
            unsafe_allow_html=True)
esq, umbral = barra_lateral()
t1, t2, t3 = st.tabs(["🎓 Mi asignatura", "📋 Mis materias", "👩‍🏫 Profesor"])
with t1:
    pestaña_estudiante(esq, umbral)
with t2:
    pestaña_materias(esq, umbral)
with t3:
    pestaña_profesor(esq, umbral)
st.markdown(f'<div class="pie">StudySmart {__version__} · {html.escape(COPYRIGHT)}</div>', unsafe_allow_html=True)
avisos_de_version()
