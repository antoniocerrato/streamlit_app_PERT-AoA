# PERT/CPM Activity on Arrow — Streamlit

Aplicación didáctica para construir y analizar redes **PERT/CPM con Activity on Arrow (AOA)** a partir de una tabla de actividades y predecesoras.

La versión actual incorpora una mejora importante: la red ya no se queda en la construcción canónica expandida, sino que aplica una **reducción segura de actividades ficticias**.

## Características principales

- Entrada editable de actividades.
- Generación aleatoria de proyectos válidos.
- Estimaciones PERT de tres valores:
  - optimista;
  - más probable;
  - pesimista.
- Validación de:
  - actividades repetidas;
  - predecesoras desconocidas;
  - autorrelaciones;
  - ciclos.
- Construcción de una red AOA canónica correcta.
- Reducción segura de ficticias mediante:
  - contracción de sucesos;
  - eliminación de ficticias redundantes;
  - verificación exacta de la relación de precedencia.
- Modos de reducción:
  - `auto`;
  - `greedy`;
  - `exact`;
  - `none`.
- Cálculo de:
  - tiempos tempranos de sucesos;
  - tiempos tardíos de sucesos;
  - ES, EF, LS, LF por actividad;
  - holgura total;
  - holgura libre proyectada;
  - actividades críticas;
  - caminos críticos.
- Representación Graphviz de la red AOA.
- Gráfica de distribución probabilística aproximada de la duración del proyecto.
- Cálculo de probabilidad de cumplir un plazo.
- Simulación Monte Carlo con:
  - distribución empírica de la duración total;
  - fechas simuladas de comienzo y finalización por actividad;
  - tiempos simulados por suceso;
  - probabilidad empírica de pertenecer al camino crítico.
- Apartado de teoría integrado en la app.

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecución

```bash
streamlit run app.py
```

## Estructura del proyecto

```text
pert_aoa_streamlit_app/
├── app.py                # Interfaz Streamlit
├── pert_aoa_core.py      # Motor matemático y algorítmico
├── THEORY.md             # Teoría integrada en la app
├── examples/             # Casos didácticos pequeños en CSV
├── tests/                # Pruebas unitarias con unittest
├── example_project.csv   # Datos de ejemplo
├── requirements.txt      # Dependencias
└── README.md             # Este documento
```

## Idea matemática de la reducción

La aplicación parte de una red canónica expandida que siempre representa correctamente la tabla de predecesoras.

Después intenta reducir ficticias. Una reducción solo se acepta si conserva exactamente esta equivalencia:

```text
actividad i precede a actividad j en la tabla
⇔
el suceso final de i alcanza el suceso inicial de j en la red AOA
```

Por tanto, la app no elimina una ficticia si al hacerlo:

- desaparece una precedencia necesaria; o
- aparece una precedencia falsa.

La función objetivo de reducción es:

```text
J(G) = (número de ficticias, número de sucesos, número total de flechas)
```

El orden es lexicográfico: primero se intenta minimizar el número de ficticias.

## Modos de reducción

### auto

Usa búsqueda exacta acotada para redes pequeñas y reducción voraz segura para redes mayores.

### exact

Explora muchas contracciones posibles hasta el límite de estados definido en la barra lateral.

Es útil para ejemplos pequeños, pero puede ser costoso.

### greedy

En cada paso aplica la mejor contracción segura disponible.

Es rápido y adecuado para uso interactivo. No garantiza mínimo global en redes grandes, pero siempre conserva la lógica de precedencias.

### none

Muestra la red canónica expandida sin reducir. Sirve para comparar.

## Comprobación

La batería mínima de comprobación puede ejecutarse con:

```bash
python -m py_compile app.py pert_aoa_core.py
python -m unittest discover
```

También se mantiene una prueba interna rápida:

```bash
python -c "from pert_aoa_core import self_test; self_test(); print('self_test ok')"
```

La carpeta `examples/` contiene redes pequeñas para revisar casos lineales, uniones paralelas, diamantes, predecesoras compartidas y caminos críticos múltiples.

## Simulación Monte Carlo

El archivo `pert_aoa_core.py` incluye una simulación Monte Carlo basada en la misma topología AOA reducida:

- `pert_beta_parameters`;
- `sample_pert_beta`;
- `schedule_with_activity_durations`.
- `monte_carlo_simulation`.

La reducción de la red depende solo de la topología, no de las duraciones. Por eso, la misma red reducida se reutiliza con duraciones aleatorias en cada iteración.

La pestaña Monte Carlo muestra la distribución empírica del proyecto, la probabilidad de cumplir un plazo, estadísticas por actividad y estadísticas por suceso. La columna `critical_probability` estima la frecuencia con la que una actividad o suceso resulta crítico en las simulaciones.
