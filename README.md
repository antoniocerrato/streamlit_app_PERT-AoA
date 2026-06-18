# PERT/CPM Activity on Arrow — Streamlit App

Aplicación didáctica para construir y analizar redes PERT/CPM con representación **Activity on Arrow (AOA)**.

## Características

- Entrada editable de actividades reales.
- Estimaciones PERT de tres valores: optimista, más probable y pesimista.
- Generación aleatoria de proyectos válidos.
- Validación de:
  - actividades repetidas;
  - predecesoras inexistentes;
  - autorrelaciones;
  - ciclos.
- Construcción de una red AOA canónica expandida.
- Representación gráfica mediante Graphviz.
- Cálculo de sucesos tempranos y tardíos.
- Cálculo por actividad de:
  - `ES`: inicio temprano;
  - `EF`: final temprano;
  - `LS`: inicio tardío;
  - `LF`: final tardío;
  - holgura total;
  - holgura libre proyectada a nivel de actividad.
- Identificación de actividades y caminos críticos.
- Distribución probabilística aproximada de la duración del proyecto.
- Arquitectura preparada para añadir Monte Carlo posteriormente.

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecución

```bash
streamlit run app.py
```

## Estructura

```text
pert_aoa_streamlit_app/
├── app.py              # Interfaz Streamlit
├── pert_aoa_core.py    # Motor matemático y algorítmico
├── THEORY.md           # Teoría integrada en la aplicación
├── example_project.csv # Proyecto de ejemplo
├── requirements.txt    # Dependencias
└── README.md           # Este documento
```

## Decisión de modelización

La aplicación usa una **red AOA canónica expandida**, no una red AOA mínima. Cada actividad real tiene un suceso propio de inicio y un suceso propio de fin. Las relaciones de precedencia se representan mediante actividades ficticias de duración cero.

Esta construcción es especialmente adecuada para docencia porque es:

- correcta por construcción;
- fácil de verificar;
- transparente para el estudiante;
- robusta para cálculos computacionales;
- ampliable a Monte Carlo.

## Monte Carlo futuro

El archivo `pert_aoa_core.py` ya incluye funciones pensadas para esa ampliación:

- `pert_beta_parameters`;
- `sample_pert_beta`;
- `schedule_with_activity_durations`.

La futura simulación deberá muestrear duraciones de actividades, recalcular la red y guardar la duración final del proyecto en cada iteración.
