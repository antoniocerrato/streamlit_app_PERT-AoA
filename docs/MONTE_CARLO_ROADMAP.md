# Hoja de ruta para implementar Monte Carlo

## Objetivo

Añadir una simulación Monte Carlo de la duración del proyecto para superar las limitaciones de la aproximación normal clásica de PERT.

La idea principal es simular muchas veces las duraciones de las actividades reales y recalcular la duración total del proyecto en cada simulación.

## Por qué Monte Carlo es necesario

La aproximación clásica calcula la varianza sobre un camino crítico dominante.

Eso puede fallar cuando:

- hay varios caminos críticos;
- hay caminos casi críticos;
- las incertidumbres son grandes;
- el camino crítico cambia según las duraciones simuladas.

Monte Carlo estima directamente:

$$
T=\max_{\text{caminos } c}\sum_{a\in c}D_a
$$

sin fijar previamente un único camino crítico.

## Funciones ya preparadas

En `pert_aoa_core.py` existen funciones iniciales:

- `pert_beta_parameters`;
- `sample_pert_beta`;
- `schedule_with_activity_durations`.

Estas funciones sirven como base, pero conviene reorganizarlas o ampliarlas para devolver resultados más ricos.

## Diseño recomendado

Crear una función nueva:

```python
def monte_carlo_simulation(
    activities: Dict[str, Activity],
    n_iter: int = 10000,
    seed: int | None = None,
    reduction_method: str = "auto",
    distribution: str = "beta_pert",
) -> MonteCarloResult:
    ...
```

Crear una clase o dataclass:

```python
@dataclass
class MonteCarloResult:
    durations: np.ndarray
    criticality_index: pd.DataFrame
    path_frequencies: pd.DataFrame
    summary: pd.DataFrame
```

## Algoritmo básico

```text
1. Validar actividades.
2. Construir una red AOA reducida una sola vez.
3. Para k = 1,...,N:
   a. muestrear duración de cada actividad real;
   b. actualizar duraciones de arcos reales;
   c. recalcular tiempos tempranos y tardíos;
   d. guardar duración total del proyecto;
   e. guardar actividades críticas observadas.
4. Calcular estadísticos empíricos.
5. Mostrar histograma, ECDF y probabilidad de cumplir plazo.
```

## Importante

La reducción de la red depende solo de la topología, no de las duraciones. Por tanto, no es necesario reducir la red en cada iteración.

Esto permite:

- construir la red una vez;
- simular miles de duraciones;
- recalcular tiempos eficientemente.

## Distribución de actividad

La opción inicial recomendada es beta-PERT escalada en `[o, p]`.

Con parámetro de forma `lambda`, la media objetivo es:

$$
\mu=\frac{o+\lambda m+p}{\lambda+2}
$$

Para la beta escalada:

$$
X=o+(p-o)Y
$$

con:

$$
Y\sim Beta(\alpha,\beta)
$$

Una parametrización habitual es:

$$
\alpha=1+\lambda\frac{m-o}{p-o}
$$

$$
\beta=1+\lambda\frac{p-m}{p-o}
$$

Si $p=o$, la duración debe tratarse como determinista.

## Resultados a mostrar en la app

### Pestaña Monte Carlo

Añadir una nueva pestaña o completar la pestaña existente.

Elementos recomendados:

- número de iteraciones;
- semilla;
- botón de simulación;
- media empírica;
- mediana;
- desviación típica;
- percentiles P5, P50, P80, P90, P95;
- probabilidad empírica de cumplir plazo;
- histograma de duración total;
- curva acumulada empírica;
- índice de criticidad por actividad.

## Índice de criticidad

Para cada actividad $a$:

$$
CI_a=\frac{\text{número de iteraciones en las que }a\text{ es crítica}}{N}
$$

Esto es muy didáctico porque muestra que una actividad puede no ser crítica en el cálculo medio, pero tener alta probabilidad de volverse crítica.

## Riesgos técnicos

- Streamlit puede volverse lento con muchas iteraciones.
- Matplotlib puede tardar si se redibuja continuamente.
- La búsqueda exacta no debe ejecutarse dentro de cada iteración.
- Conviene cachear la topología reducida.
- Para muchas iteraciones puede hacer falta vectorizar o usar NumPy de forma intensiva.

## Primera implementación mínima viable

1. Añadir `monte_carlo_simulation` en `pert_aoa_core.py`.
2. Simular solo duración total y actividades críticas.
3. Añadir histograma y tabla resumen.
4. Añadir índice de criticidad.
5. Comparar distribución Monte Carlo con aproximación normal actual.

## Segunda fase

- guardar camino crítico dominante de cada iteración;
- mostrar caminos más frecuentes;
- exportar CSV de simulaciones;
- añadir intervalos de confianza;
- añadir opciones de distribución: triangular, beta-PERT, determinista;
- optimizar rendimiento.
