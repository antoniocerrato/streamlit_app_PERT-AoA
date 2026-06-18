# Tareas recomendadas para Codex

## Prioridad 1 — Consolidar la versión reducida

### 1.1. Verificar que el repositorio contiene la versión reducida

Comprobar que `pert_aoa_core.py` contiene:

- `ReductionInfo`;
- `build_reduced_aoa`;
- `safe_greedy_reduce`;
- `exact_reduce_bounded`;
- `is_exact_representation`.

Si no aparecen, se está usando la versión antigua canónica sin reducción.

### 1.2. Añadir pruebas unitarias separadas

Crear carpeta:

```text
tests/
```

Añadir al menos:

- `test_validation.py`;
- `test_reduction.py`;
- `test_cpm.py`;
- `test_probability.py`.

Usar `pytest` si se acepta añadir dependencia de desarrollo.

### 1.3. Añadir ejemplos de redes pequeñas

Crear carpeta:

```text
examples/
```

Con varios CSV:

- `linear.csv`;
- `parallel_join.csv`;
- `diamond.csv`;
- `shared_predecessors.csv`;
- `multiple_critical_paths.csv`.

## Prioridad 2 — Mejorar la app Streamlit

### 2.1. Mostrar red canónica vs red reducida

Añadir opción para ver ambas redes:

- canónica;
- reducida.

Esto es muy didáctico porque muestra qué ficticias desaparecen.

### 2.2. Explicar reducción

Añadir tabla o resumen:

- ficticias iniciales;
- ficticias finales;
- sucesos iniciales;
- sucesos finales;
- método usado;
- número de estados explorados si se usa `exact`.

### 2.3. Mejorar mensajes de error

Los errores de entrada deben proponer una corrección.

Ejemplo:

```text
La actividad D contiene la predecesora Z, pero Z no existe.
Añade una actividad Z o elimina Z de las predecesoras de D.
```

## Prioridad 3 — Monte Carlo

Implementar según `docs/MONTE_CARLO_ROADMAP.md`.

Orden recomendado:

1. `MonteCarloResult` dataclass.
2. `monte_carlo_simulation` en `pert_aoa_core.py`.
3. Histograma empírico en Streamlit.
4. ECDF.
5. Probabilidad empírica de cumplir plazo.
6. Índice de criticidad.
7. Exportación de simulaciones.

## Prioridad 4 — Rendimiento

### 4.1. Cachear topología

La reducción depende solo de predecesoras, no de duraciones.

Crear una firma topológica para poder cachear.

### 4.2. Optimizar Monte Carlo

No reconstruir la red completa en cada iteración.

Reutilizar:

- lista de sucesos;
- lista de arcos;
- orden topológico;
- índices de arcos reales.

## Prioridad 5 — Publicabilidad docente

Añadir funcionalidades que permitan estudiar el aprendizaje:

- modo ejercicio;
- preguntas automáticas;
- registro de intentos;
- exportación anónima de resultados;
- comparación antes/después.

## Tareas que NO hacer sin revisar

- No afirmar mínimo global de ficticias sin prueba.
- No eliminar ficticias por estética sin validar alcanzabilidad.
- No mezclar AON y AOA en una misma tabla sin explicar la diferencia.
- No cambiar delimitadores LaTeX a `\[...\]`.
- No meter toda la lógica Monte Carlo en `app.py`.
