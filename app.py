from __future__ import annotations

from io import StringIO
from pathlib import Path
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from pert_aoa_core import (
    ValidationError,
    activities_to_dataframe,
    compute_project,
    dataframe_to_activities,
    example_project,
    generate_random_project,
    monte_carlo_simulation,
    normal_cdf,
    probability_curve,
    to_dot,
)


APP_DIR = Path(__file__).resolve().parent
THEORY_PATH = APP_DIR / "THEORY.md"


st.set_page_config(
    page_title="PERT/CPM Activity on Arrow",
    page_icon="↗️",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
    .small-note {font-size: 0.9rem; color: #666;}
    .metric-card {border: 1px solid #ddd; border-radius: 0.7rem; padding: 1rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_theory() -> str:
    if THEORY_PATH.exists():
        return THEORY_PATH.read_text(encoding="utf-8")
    return "# Teoría\n\nNo se ha encontrado el archivo THEORY.md."


def duration_mode() -> str:
    return st.session_state.get("duration_mode", "pert")


def table_for_duration_mode(df: pd.DataFrame, mode: str) -> pd.DataFrame:
    """Return the editable table columns expected by the selected duration mode."""
    result = pd.DataFrame()
    result["id"] = df["id"] if "id" in df.columns else ""

    if mode == "single":
        if "duration" in df.columns:
            result["duration"] = df["duration"]
        elif {"optimistic", "most_likely", "pessimistic"}.issubset(df.columns):
            o = pd.to_numeric(df["optimistic"], errors="coerce")
            m = pd.to_numeric(df["most_likely"], errors="coerce")
            p = pd.to_numeric(df["pessimistic"], errors="coerce")
            result["duration"] = (o + 4.0 * m + p) / 6.0
        else:
            result["duration"] = 0.0
    else:
        if {"optimistic", "most_likely", "pessimistic"}.issubset(df.columns):
            result["optimistic"] = df["optimistic"]
            result["most_likely"] = df["most_likely"]
            result["pessimistic"] = df["pessimistic"]
        elif "duration" in df.columns:
            result["optimistic"] = df["duration"]
            result["most_likely"] = df["duration"]
            result["pessimistic"] = df["duration"]
        else:
            result["optimistic"] = 0.0
            result["most_likely"] = 0.0
            result["pessimistic"] = 0.0

    result["predecessors"] = df["predecessors"] if "predecessors" in df.columns else ""
    return result


def set_activity_table(df: pd.DataFrame) -> None:
    st.session_state["activity_df"] = df
    st.session_state["editor_version"] = st.session_state.get("editor_version", 0) + 1


def reset_with_example() -> None:
    set_activity_table(activities_to_dataframe(example_project(), duration_mode=duration_mode()))


def reset_with_random() -> None:
    n = st.session_state.get("n_activities", 8)
    density = st.session_state.get("edge_probability", 0.25)
    seed = st.session_state.get("seed", 17)
    min_o = st.session_state.get("min_optimistic", 1)
    max_o = st.session_state.get("max_optimistic", 8)
    spread = st.session_state.get("max_spread", 6)
    activities = generate_random_project(
        n_activities=n,
        edge_probability=density,
        min_optimistic=min_o,
        max_optimistic=max_o,
        max_spread=spread,
        seed=seed,
    )
    set_activity_table(activities_to_dataframe(activities, duration_mode=duration_mode()))


JSON_EXAMPLE = """[
  {"id": "A", "duration": 4, "predecessors": []},
  {"id": "B", "duration": 3, "predecessors": ["A"]},
  {"id": "C", "duration": 5, "predecessors": ["A"]},
  {"id": "D", "duration": 2, "predecessors": ["B", "C"]}
]"""


def json_to_activity_dataframe(text: str) -> pd.DataFrame:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"El texto no es JSON válido: {exc.msg}.") from exc

    if isinstance(payload, dict):
        if "activities" not in payload:
            raise ValidationError("El JSON debe contener una clave 'activities' o ser una lista de actividades.")
        payload = payload["activities"]
    if not isinstance(payload, list):
        raise ValidationError("El JSON debe ser una lista de actividades.")

    rows = []
    uses_duration = False
    uses_three_point = False
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise ValidationError(f"La actividad JSON número {index} debe ser un objeto.")
        row = {"id": item.get("id", "")}
        if "duration" in item:
            row["duration"] = item["duration"]
            uses_duration = True
        if {"optimistic", "most_likely", "pessimistic"}.issubset(item):
            row["optimistic"] = item["optimistic"]
            row["most_likely"] = item["most_likely"]
            row["pessimistic"] = item["pessimistic"]
            uses_three_point = True
        predecessors = item.get("predecessors", "")
        if isinstance(predecessors, list):
            predecessors = ", ".join(str(value) for value in predecessors)
        row["predecessors"] = predecessors
        rows.append(row)

    if not rows:
        raise ValidationError("El JSON no contiene actividades.")
    if uses_duration and uses_three_point:
        raise ValidationError("Usa 'duration' o las tres estimaciones PERT, pero no mezcles ambos formatos.")
    if uses_duration:
        columns = ["id", "duration", "predecessors"]
    elif uses_three_point:
        columns = ["id", "optimistic", "most_likely", "pessimistic", "predecessors"]
    else:
        raise ValidationError(
            "Cada actividad debe incluir 'duration' o 'optimistic', 'most_likely' y 'pessimistic'."
        )
    return pd.DataFrame(rows, columns=columns)


@st.dialog("Introducir ejemplo en JSON")
def json_input_dialog() -> None:
    st.markdown(
        """
        Puedes usar una lista de actividades o un objeto con clave `activities`.
        Cada actividad debe incluir `id`, `predecessors` y `duration`, o bien las tres estimaciones PERT.
        """
    )
    text = st.text_area("JSON", value=JSON_EXAMPLE, height=280)
    if st.button("Cargar JSON", type="primary", use_container_width=True):
        try:
            df = json_to_activity_dataframe(text)
            dataframe_to_activities(df)
        except ValidationError as exc:
            st.error(str(exc))
        else:
            set_activity_table(table_for_duration_mode(df, duration_mode()))
            st.session_state.pop("mc_result", None)
            st.session_state.pop("mc_signature", None)
            st.rerun()


if "duration_mode" not in st.session_state:
    st.session_state["duration_mode"] = "pert"

if "activity_df" not in st.session_state:
    reset_with_example()


st.title("PERT/CPM con Activity on Arrow")
st.caption(
    "Aplicación didáctica para construir una red AOA canónica, calcular tiempos tempranos y tardíos, "
    "identificar caminos críticos y aproximar la distribución probabilística de la duración del proyecto."
)


with st.sidebar:
    st.header("Tipo de duración")
    selected_duration_mode = st.radio(
        "Datos de duración",
        options=["pert", "single"],
        format_func=lambda value: "Tres estimaciones PERT" if value == "pert" else "Una duración",
        index=0 if duration_mode() == "pert" else 1,
    )
    if selected_duration_mode != duration_mode():
        st.session_state["duration_mode"] = selected_duration_mode
        set_activity_table(table_for_duration_mode(st.session_state["activity_df"], selected_duration_mode))
        st.rerun()
    st.divider()

    st.header("Entrada aleatoria")
    st.number_input("Número de actividades", min_value=2, max_value=24, value=8, step=1, key="n_activities")
    st.slider("Probabilidad de precedencia", min_value=0.0, max_value=0.8, value=0.25, step=0.05, key="edge_probability")
    st.number_input("Semilla aleatoria", min_value=0, max_value=999999, value=17, step=1, key="seed")
    st.divider()
    st.number_input("Mínimo optimista", min_value=0, max_value=100, value=1, step=1, key="min_optimistic")
    st.number_input("Máximo optimista", min_value=1, max_value=100, value=8, step=1, key="max_optimistic")
    st.number_input("Dispersión máxima", min_value=0, max_value=100, value=6, step=1, key="max_spread")
    st.button("Generar proyecto aleatorio", on_click=reset_with_random, use_container_width=True)
    st.button("Cargar ejemplo didáctico", on_click=reset_with_example, use_container_width=True)
    if st.button("Introducir JSON manualmente", use_container_width=True):
        json_input_dialog()
    st.divider()
    st.header("Reducción AOA")
    st.selectbox(
        "Método de reducción",
        options=["auto", "greedy", "exact", "none"],
        index=0,
        key="reduction_method",
        help=(
            "auto usa búsqueda exacta acotada en redes pequeñas y reducción voraz segura en redes grandes. "
            "none muestra la red canónica sin compactar."
        ),
    )
    st.number_input(
        "Límite de actividades para búsqueda exacta",
        min_value=2,
        max_value=18,
        value=7,
        step=1,
        key="exact_activity_limit",
    )
    st.number_input(
        "Máximo de estados en búsqueda exacta",
        min_value=500,
        max_value=100000,
        value=3000,
        step=500,
        key="max_exact_states",
    )
    st.markdown(
        """
        **Modelo usado**

        La app parte de una red AOA canónica correcta y después la reduce.
        Una contracción solo se acepta si conserva exactamente la relación de
        precedencia entre actividades reales.
        """
    )


tabs = st.tabs(
    [
        "1. Datos",
        "2. Red AOA",
        "3. Cálculo CPM/PERT",
        "4. Distribución probabilística",
        "5. Teoría",
        "6. Monte Carlo",
    ]
)


with tabs[0]:
    st.subheader("Tabla de actividades")
    st.markdown(
        """
        Introduce una fila por actividad. Las predecesoras deben escribirse como identificadores separados por comas.

        La aplicación usa las tres estimaciones clásicas de PERT:

        - `optimistic`: duración optimista;
        - `most_likely`: duración más probable;
        - `pessimistic`: duración pesimista.
        """
    )
    if duration_mode() == "single":
        st.info("Modo activo: introduce una sola duración por actividad. Internamente se usa como o = m = p.")

    if duration_mode() == "single":
        column_config = {
            "id": st.column_config.TextColumn("Actividad", required=True),
            "duration": st.column_config.NumberColumn("Duración", min_value=0.0, step=0.5, format="%.2f"),
            "predecessors": st.column_config.TextColumn("Predecesoras directas"),
        }
    else:
        column_config = {
            "id": st.column_config.TextColumn("Actividad", required=True),
            "optimistic": st.column_config.NumberColumn("Optimista", min_value=0.0, step=0.5, format="%.2f"),
            "most_likely": st.column_config.NumberColumn("Más probable", min_value=0.0, step=0.5, format="%.2f"),
            "pessimistic": st.column_config.NumberColumn("Pesimista", min_value=0.0, step=0.5, format="%.2f"),
            "predecessors": st.column_config.TextColumn("Predecesoras directas"),
        }

    edited = st.data_editor(
        table_for_duration_mode(st.session_state["activity_df"], duration_mode()),
        num_rows="dynamic",
        use_container_width=True,
        column_config=column_config,
        hide_index=True,
        key=f"activity_editor_{duration_mode()}_{st.session_state.get('editor_version', 0)}",
    )
    st.session_state["activity_df"] = edited

    csv = edited.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Descargar tabla de entrada",
        csv,
        file_name="pert_aoa_input.csv",
        mime="text/csv",
        use_container_width=True,
    )

    try:
        activities = dataframe_to_activities(edited)
        result = compute_project(
            activities,
            reduction_method=st.session_state.get("reduction_method", "auto"),
            exact_activity_limit=st.session_state.get("exact_activity_limit", 7),
            max_exact_states=st.session_state.get("max_exact_states", 3000),
        )
        canonical_result = result
        if result.reduction_info.method_used != "none":
            canonical_result = compute_project(
                activities,
                reduction_method="none",
                exact_activity_limit=st.session_state.get("exact_activity_limit", 7),
                max_exact_states=st.session_state.get("max_exact_states", 3000),
            )
        st.success("La tabla es válida: no hay referencias desconocidas, autorrelaciones ni ciclos.")
        st.markdown("**Capas topológicas de actividades**")
        layer_text = " → ".join(["{" + ", ".join(layer) + "}" for layer in result.activity_layers])
        st.code(layer_text, language="text")
    except ValidationError as exc:
        st.error(str(exc))
        result = None
        canonical_result = None


if result is not None:
    with tabs[1]:
        st.subheader("Red Activity on Arrow")
        st.markdown(
            """
            En esta representación, las **actividades reales** son flechas continuas y las **actividades ficticias** son flechas discontinuas.
            Las flechas rojas pertenecen a algún camino crítico de la red generada.

            La red se ha compactado de forma segura: la aplicación comprueba que la alcanzabilidad entre actividades
            reales sigue siendo exactamente la misma que en la tabla de predecesoras.
            """
        )
        info = result.reduction_info
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Ficticias canónicas", str(info.canonical_dummy_arcs))
        m2.metric("Ficticias finales", str(info.reduced_dummy_arcs), delta=-(info.canonical_dummy_arcs - info.reduced_dummy_arcs))
        m3.metric("Sucesos", f"{info.reduced_events}", delta=-(info.canonical_events - info.reduced_events))
        m4.metric("Método", info.method_used)
        st.caption(info.note + f" Estados explorados: {info.states_explored}.")

        with st.expander("Resumen de reducción", expanded=True):
            reduction_summary = pd.DataFrame(
                [
                    {
                        "red": "Canónica",
                        "sucesos": info.canonical_events,
                        "flechas": info.canonical_arcs,
                        "ficticias": info.canonical_dummy_arcs,
                    },
                    {
                        "red": "Reducida",
                        "sucesos": info.reduced_events,
                        "flechas": info.reduced_arcs,
                        "ficticias": info.reduced_dummy_arcs,
                    },
                ]
            )
            st.dataframe(reduction_summary, use_container_width=True, hide_index=True)
            st.write(
                f"Contracciones aceptadas: **{info.contractions}**. "
                f"Ficticias eliminadas: **{info.dummy_arcs_removed}**."
            )

        network_view = st.radio(
            "Red a visualizar",
            options=["Reducida", "Canónica", "Comparación"],
            horizontal=True,
            help=(
                "La red canónica es la construcción expandida correcta; la reducida conserva la misma lógica "
                "con menos ficticias cuando es posible."
            ),
        )

        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            show_dummy_labels = st.checkbox("Mostrar etiquetas de ficticias", value=True)
        with c2:
            compact_labels = st.checkbox("Etiquetas compactas", value=False)
        with c3:
            st.metric("Duración esperada del proyecto", f"{result.project_duration:.2f}")

        if network_view == "Comparación":
            left, right = st.columns(2)
            with left:
                st.markdown("### Canónica")
                canonical_dot = to_dot(canonical_result, show_dummy_labels=show_dummy_labels, compact_labels=True)
                st.graphviz_chart(canonical_dot, use_container_width=True)
            with right:
                st.markdown("### Reducida")
                dot = to_dot(result, show_dummy_labels=show_dummy_labels, compact_labels=True)
                st.graphviz_chart(dot, use_container_width=True)
        else:
            graph_result = canonical_result if network_view == "Canónica" else result
            dot = to_dot(graph_result, show_dummy_labels=show_dummy_labels, compact_labels=compact_labels)
            st.graphviz_chart(dot, use_container_width=True)

        with st.expander("Ver código DOT del grafo"):
            st.code(dot, language="dot")

        st.markdown("### Tabla de sucesos")
        st.dataframe(result.event_table.round(4), use_container_width=True, hide_index=True)

        st.markdown("### Tabla de flechas AOA")
        st.dataframe(result.arc_table.round(4), use_container_width=True, hide_index=True)

        with st.expander("Comprobación didáctica de la reducción"):
            st.markdown(
                f"""
                La red canónica tenía **{info.canonical_dummy_arcs}** actividades ficticias y
                **{info.canonical_events}** sucesos. La red reducida tiene **{info.reduced_dummy_arcs}**
                actividades ficticias y **{info.reduced_events}** sucesos.

                Una reducción se acepta únicamente si cumple esta equivalencia lógica:

                `actividad i precede a actividad j en la tabla`  ⇔  `el final de i alcanza el inicio de j en la red AOA`.

                Por eso la app no elimina una ficticia si al hacerlo aparece una precedencia falsa o desaparece una
                precedencia necesaria.
                """
            )

    with tabs[2]:
        st.subheader("Resultados CPM/PERT por actividad")
        col1, col2, col3 = st.columns(3)
        col1.metric("Duración esperada", f"{result.project_duration:.2f}")
        col2.metric("Actividades críticas", str(len(result.critical_activities)))
        col3.metric("Caminos críticos detectados", str(len(result.critical_paths)))

        st.markdown("### Actividades")
        display_cols = [
            "activity",
            "predecessors",
            "successors",
            "optimistic",
            "most_likely",
            "pessimistic",
            "mean_duration",
            "variance",
            "ES",
            "EF",
            "LS",
            "LF",
            "total_float",
            "free_float_activity",
            "critical",
        ]
        st.dataframe(result.activity_table[display_cols].round(4), use_container_width=True, hide_index=True)

        st.download_button(
            "Descargar resultados por actividad",
            result.activity_table.to_csv(index=False).encode("utf-8"),
            file_name="pert_aoa_activity_results.csv",
            mime="text/csv",
            use_container_width=True,
        )

        st.markdown("### Caminos críticos")
        if result.critical_paths:
            for i, path in enumerate(result.critical_paths, start=1):
                st.write(f"**Camino crítico {i}:** " + " → ".join(path))
        else:
            st.warning("No se ha encontrado ningún camino crítico completo. Revisa la red.")

        st.markdown("### Explicación de una actividad")
        selected = st.selectbox("Selecciona una actividad", result.activity_topological_order)
        row = result.activity_table[result.activity_table["activity"] == selected].iloc[0]
        st.markdown(
            f"""
            Para la actividad **{selected}**:

            - Su duración esperada es `{row['mean_duration']:.2f}`.
            - Suceso inicial: `{row['start_event']}`.
            - Suceso final: `{row['finish_event']}`.
            - Inicio temprano: `ES = {row['ES']:.2f}`.
            - Final temprano: `EF = ES + t = {row['EF']:.2f}`.
            - Final tardío: `LF = {row['LF']:.2f}`.
            - Inicio tardío: `LS = LF - t = {row['LS']:.2f}`.
            - Holgura total: `HT = LS - ES = {row['total_float']:.2f}`.
            - Holgura libre proyectada a nivel de actividad: `{row['free_float_activity']:.2f}`.
            """
        )
        if bool(row["critical"]):
            st.success("Esta actividad es crítica porque su holgura total es cero.")
        else:
            st.info("Esta actividad no es crítica porque tiene holgura total positiva.")

    with tabs[3]:
        st.subheader("Distribución probabilística aproximada de la duración del proyecto")
        st.markdown(
            """
            La distribución se calcula con la aproximación clásica de PERT: se toma un camino crítico dominante,
            se suma la media de sus actividades y se suma su varianza. Después se aproxima la duración del proyecto
            mediante una distribución normal.

            Esta aproximación es didáctica y útil como primera estimación. Cuando existan varios caminos casi críticos,
            el futuro módulo de Monte Carlo será más adecuado porque calculará la duración como el máximo de todos los
            caminos en cada simulación.
            """
        )

        mu = result.project_duration
        sigma = result.critical_path_std
        default_deadline = float(mu + sigma) if sigma > 0 else float(mu)
        max_deadline = float(mu + 4 * max(sigma, 1.0))
        min_deadline = max(0.0, float(mu - 4 * max(sigma, 1.0)))
        deadline = st.slider(
            "Plazo objetivo",
            min_value=min_deadline,
            max_value=max_deadline,
            value=default_deadline,
            step=0.1,
        )
        probability = normal_cdf(deadline, mu, sigma)

        c1, c2, c3 = st.columns(3)
        c1.metric("Media aproximada", f"{mu:.2f}")
        c2.metric("Desviación típica", f"{sigma:.2f}")
        c3.metric("P(T ≤ plazo)", f"{100 * probability:.1f} %")

        if result.dominant_critical_path:
            st.write("**Camino usado para la varianza:** " + " → ".join(result.dominant_critical_path))
            st.write(f"**Varianza total del camino:** {result.critical_path_variance:.4f}")

        curve = probability_curve(mu, sigma, deadline)
        fig, ax = plt.subplots(figsize=(9, 4.5))
        ax.plot(curve["duration"], curve["density"], linewidth=2)
        left = curve[curve["duration"] <= deadline]
        ax.fill_between(left["duration"], left["density"], alpha=0.25)
        ax.axvline(mu, linestyle="--", linewidth=1.5, label="Media")
        ax.axvline(deadline, linestyle=":", linewidth=2, label="Plazo")
        ax.set_xlabel("Duración del proyecto")
        ax.set_ylabel("Densidad de probabilidad")
        ax.set_title("Aproximación normal de la duración del proyecto")
        ax.legend()
        ax.grid(True, alpha=0.25)
        st.pyplot(fig, use_container_width=True)

        with st.expander("Tabla de la curva"):
            st.dataframe(curve.round(6), use_container_width=True, hide_index=True)

        st.download_button(
            "Descargar curva de probabilidad",
            curve.to_csv(index=False).encode("utf-8"),
            file_name="pert_aoa_probability_curve.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with tabs[4]:
        st.markdown(load_theory())

    with tabs[5]:
        st.subheader("Simulación Monte Carlo")
        st.markdown(
            """
            La simulación reutiliza una única topología AOA reducida y, en cada iteración, muestrea duraciones
            beta-PERT para las actividades reales. Así estima directamente la distribución empírica de la duración
            total, las fechas de comienzo y terminación, y la probabilidad de que cada actividad pertenezca al camino crítico.
            """
        )

        mc1, mc2, mc3, mc4 = st.columns(4)
        with mc1:
            mc_iter = st.number_input(
                "Iteraciones",
                min_value=100,
                max_value=50000,
                value=5000,
                step=500,
                key="mc_iter",
            )
        with mc2:
            mc_seed = st.number_input("Semilla", min_value=0, max_value=999999, value=1234, step=1, key="mc_seed")
        with mc3:
            mc_lambda = st.slider("Lambda beta-PERT", min_value=1.0, max_value=10.0, value=4.0, step=0.5, key="mc_lambda")
        with mc4:
            mc_deadline = st.number_input(
                "Plazo objetivo",
                min_value=0.0,
                value=float(result.project_duration),
                step=0.5,
                key="mc_deadline",
            )

        mc_signature = (
            edited.to_csv(index=False),
            int(mc_iter),
            int(mc_seed),
            float(mc_lambda),
            float(mc_deadline),
            st.session_state.get("reduction_method", "auto"),
            st.session_state.get("exact_activity_limit", 7),
            st.session_state.get("max_exact_states", 3000),
        )

        if st.button("Ejecutar simulación Monte Carlo", type="primary", use_container_width=True):
            with st.spinner("Simulando duraciones y recalculando CPM..."):
                st.session_state["mc_result"] = monte_carlo_simulation(
                    activities,
                    n_iter=int(mc_iter),
                    seed=int(mc_seed),
                    reduction_method=st.session_state.get("reduction_method", "auto"),
                    exact_activity_limit=st.session_state.get("exact_activity_limit", 7),
                    max_exact_states=st.session_state.get("max_exact_states", 3000),
                    deadline=float(mc_deadline),
                    lamb=float(mc_lambda),
                )
                st.session_state["mc_signature"] = mc_signature

        mc_result = st.session_state.get("mc_result")
        if mc_result is None:
            st.info("Ejecuta la simulación para obtener resultados empíricos.")
        elif st.session_state.get("mc_signature") != mc_signature:
            st.warning("Los datos o parámetros han cambiado. Ejecuta de nuevo la simulación para actualizar los resultados.")
        else:
            summary = mc_result.duration_summary.round(4)
            p_deadline = mc_result.deadline_probability if mc_result.deadline_probability is not None else float("nan")
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Media simulada", f"{summary.loc[0, 'project_duration_mean']:.2f}")
            s2.metric("P50", f"{summary.loc[0, 'project_duration_p50']:.2f}")
            s3.metric("P90", f"{summary.loc[0, 'project_duration_p90']:.2f}")
            s4.metric("P(T ≤ plazo)", f"{100 * p_deadline:.1f} %")

            fig_mc, ax_mc = plt.subplots(figsize=(9, 4.5))
            ax_mc.hist(mc_result.durations, bins=35, density=True, alpha=0.45, label="Histograma")
            sorted_durations = np.sort(mc_result.durations)
            ecdf = np.arange(1, len(sorted_durations) + 1) / len(sorted_durations)
            ax_ecdf = ax_mc.twinx()
            ax_ecdf.plot(sorted_durations, ecdf, color="firebrick", linewidth=2, label="ECDF")
            ax_mc.axvline(float(mc_deadline), linestyle=":", linewidth=2, color="black", label="Plazo")
            ax_mc.set_xlabel("Duración del proyecto")
            ax_mc.set_ylabel("Densidad empírica")
            ax_ecdf.set_ylabel("Probabilidad acumulada")
            ax_mc.grid(True, alpha=0.25)
            ax_mc.legend(loc="upper left")
            ax_ecdf.legend(loc="lower right")
            st.pyplot(fig_mc, use_container_width=True)

            st.markdown("### Estadísticas por actividad")
            activity_cols = [
                "activity",
                "critical_probability",
                "duration_mean",
                "early_start_mean",
                "early_start_p05",
                "early_start_p50",
                "early_start_p95",
                "early_finish_mean",
                "early_finish_p05",
                "early_finish_p50",
                "early_finish_p95",
                "late_start_mean",
                "late_finish_mean",
                "total_float_mean",
            ]
            st.dataframe(
                mc_result.activity_stats[activity_cols].round(4),
                use_container_width=True,
                hide_index=True,
            )

            st.markdown("### Estadísticas por sucesos")
            event_cols = [
                "event",
                "critical_probability",
                "early_time_mean",
                "early_time_p05",
                "early_time_p50",
                "early_time_p95",
                "late_time_mean",
                "late_time_p05",
                "late_time_p50",
                "late_time_p95",
                "slack_mean",
            ]
            st.dataframe(
                mc_result.event_stats[event_cols].round(4),
                use_container_width=True,
                hide_index=True,
            )

            d1, d2, d3 = st.columns(3)
            with d1:
                st.download_button(
                    "Descargar resumen Monte Carlo",
                    mc_result.duration_summary.to_csv(index=False).encode("utf-8"),
                    file_name="pert_aoa_monte_carlo_summary.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            with d2:
                st.download_button(
                    "Descargar actividades Monte Carlo",
                    mc_result.activity_stats.to_csv(index=False).encode("utf-8"),
                    file_name="pert_aoa_monte_carlo_activities.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            with d3:
                st.download_button(
                    "Descargar sucesos Monte Carlo",
                    mc_result.event_stats.to_csv(index=False).encode("utf-8"),
                    file_name="pert_aoa_monte_carlo_events.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

else:
    for tab in tabs[1:]:
        with tab:
            st.warning("Corrige primero la tabla de actividades en la pestaña de datos.")
