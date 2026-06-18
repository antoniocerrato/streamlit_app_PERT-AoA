from __future__ import annotations

from io import StringIO
from pathlib import Path

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


def reset_with_example() -> None:
    st.session_state["activity_df"] = activities_to_dataframe(example_project())


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
    st.session_state["activity_df"] = activities_to_dataframe(activities)


if "activity_df" not in st.session_state:
    reset_with_example()


st.title("PERT/CPM con Activity on Arrow")
st.caption(
    "Aplicación didáctica para construir una red AOA canónica, calcular tiempos tempranos y tardíos, "
    "identificar caminos críticos y aproximar la distribución probabilística de la duración del proyecto."
)


with st.sidebar:
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
        "6. Monte Carlo después",
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

    edited = st.data_editor(
        st.session_state["activity_df"],
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "id": st.column_config.TextColumn("Actividad", required=True),
            "optimistic": st.column_config.NumberColumn("Optimista", min_value=0.0, step=0.5, format="%.2f"),
            "most_likely": st.column_config.NumberColumn("Más probable", min_value=0.0, step=0.5, format="%.2f"),
            "pessimistic": st.column_config.NumberColumn("Pesimista", min_value=0.0, step=0.5, format="%.2f"),
            "predecessors": st.column_config.TextColumn("Predecesoras directas"),
        },
        hide_index=True,
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
        st.success("La tabla es válida: no hay referencias desconocidas, autorrelaciones ni ciclos.")
        st.markdown("**Capas topológicas de actividades**")
        layer_text = " → ".join(["{" + ", ".join(layer) + "}" for layer in result.activity_layers])
        st.code(layer_text, language="text")
    except ValidationError as exc:
        st.error(str(exc))
        result = None


if result is not None:
    with tabs[1]:
        st.subheader("Red Activity on Arrow reducida")
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

        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            show_dummy_labels = st.checkbox("Mostrar etiquetas de ficticias", value=True)
        with c2:
            compact_labels = st.checkbox("Etiquetas compactas", value=False)
        with c3:
            st.metric("Duración esperada del proyecto", f"{result.project_duration:.2f}")

        dot = to_dot(result, show_dummy_labels=show_dummy_labels, compact_labels=compact_labels)
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
        st.subheader("Preparada para Monte Carlo")
        st.markdown(
            """
            La aplicación todavía muestra como resultado principal la aproximación analítica clásica de PERT.
            Sin embargo, el motor está organizado para añadir Monte Carlo después sin reescribir la aplicación.
            La reducción AOA es topológica: no depende de las duraciones muestreadas, por lo que puede reutilizarse
            en cada iteración.

            La futura simulación debería hacer lo siguiente:

            1. Para cada iteración, muestrear una duración aleatoria de cada actividad real.
            2. Recalcular la red AOA con esas duraciones.
            3. Guardar la duración total del proyecto.
            4. Repetir el proceso muchas veces.
            5. Construir un histograma empírico de la duración del proyecto.
            6. Estimar probabilidades como `P(T ≤ D)` directamente desde las simulaciones.

            El archivo `pert_aoa_core.py` ya incluye las funciones base:

            - `pert_beta_parameters`;
            - `sample_pert_beta`;
            - `schedule_with_activity_durations`.
            """
        )
        st.code(
            """
# Esquema de la futura simulación Monte Carlo
for k in range(n_iter):
    durations = {}
    for activity in activities:
        durations[activity.id] = sample_pert_beta(activity, rng)
    project_duration[k] = schedule_with_activity_durations(activities, durations)
            """.strip(),
            language="python",
        )

else:
    for tab in tabs[1:]:
        with tab:
            st.warning("Corrige primero la tabla de actividades en la pestaña de datos.")
