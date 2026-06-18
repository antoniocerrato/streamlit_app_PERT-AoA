# Arquitectura del proyecto

## Estructura

```text
pert_aoa_streamlit_app/
├── app.py
├── pert_aoa_core.py
├── THEORY.md
├── README.md
├── requirements.txt
├── example_project.csv
├── AGENTS.md
├── PROJECT_BRIEF.md
└── docs/
    ├── ARCHITECTURE.md
    ├── AOA_ALGORITHM.md
    ├── MONTE_CARLO_ROADMAP.md
    ├── VALIDATION_AND_TESTING.md
    ├── UI_AND_DIDACTICS.md
    ├── CODEX_TASKS.md
    └── CHANGELOG_CONTEXT.md
```

## Separación de responsabilidades

### `app.py`

Contiene la interfaz Streamlit.

Responsabilidades:

- mostrar controles de entrada;
- mantener `session_state`;
- mostrar tablas, métricas, grafos y gráficos;
- llamar al motor matemático;
- no implementar algoritmos complejos.

### `pert_aoa_core.py`

Contiene el motor matemático.

Responsabilidades:

- parsear y validar datos;
- construir relaciones de precedencia;
- construir redes AOA canónicas;
- reducir redes AOA;
- calcular tiempos de sucesos;
- calcular resultados por actividad;
- obtener caminos críticos;
- preparar funciones de distribución probabilística;
- preparar funciones para Monte Carlo.

### `THEORY.md`

Documento teórico integrado en la pestaña de teoría de la app.

Debe estar escrito de forma didáctica y usar delimitadores `$` para LaTeX.

### `docs/`

Carpeta de contexto para desarrollo. Estos archivos no son necesariamente visibles en la app, pero ayudan a Codex o a cualquier desarrollador a entender el proyecto.

## Flujo de datos

```text
Streamlit data_editor
    ↓
DataFrame
    ↓
dataframe_to_activities
    ↓
Dict[str, Activity]
    ↓
compute_project
    ↓
ProjectResult
    ↓
tablas + grafo + distribución + teoría
```

## Objetos principales

### `Activity`

Representa una actividad real de la tabla de entrada.

Campos principales:

- `id`;
- `optimistic`;
- `most_likely`;
- `pessimistic`;
- `predecessors`.

Propiedades:

- `mean`;
- `variance`;
- `std`.

### `Arc`

Representa una flecha AOA.

Puede ser:

- `real`;
- `dummy_start`;
- `dummy_finish`;
- `dummy_precedence`.

Campos principales:

- `id`;
- `tail`;
- `head`;
- `duration`;
- `variance`;
- `kind`;
- `activity_id`;
- `predecessor`;
- `successor`.

### `ReductionInfo`

Resume el proceso de reducción.

Debe usarse en la interfaz para explicar cuánto se ha reducido la red y qué método se ha usado.

### `ProjectResult`

Objeto de salida principal de `compute_project`.

Contiene:

- actividades;
- predecesoras y sucesoras;
- capas topológicas;
- sucesos;
- flechas;
- tiempos tempranos y tardíos;
- tablas de actividad, flecha y suceso;
- duración esperada del proyecto;
- actividades críticas;
- caminos críticos;
- datos probabilísticos;
- información de reducción.

## Dependencias

Ver `requirements.txt`.

Actualmente se usa:

- Streamlit;
- Pandas;
- NumPy;
- Matplotlib;
- Graphviz a través de `st.graphviz_chart`.

## Puntos de extensión

1. Simulación Monte Carlo.
2. Comparación entre red canónica y red reducida en dos paneles.
3. Exportación de grafo a DOT/SVG/PNG.
4. Edición visual de la red.
5. Simplificación multiobjetivo con legibilidad gráfica.
6. Traducción o versión bilingüe de la teoría.
