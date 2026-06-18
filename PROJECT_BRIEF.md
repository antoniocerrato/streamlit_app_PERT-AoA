# Project brief — PERT/CPM Activity on Arrow en Streamlit

## Resumen

Este proyecto es una aplicación didáctica para estudiar redes PERT/CPM mediante **Activity on Arrow (AOA)**.

El usuario introduce una tabla de actividades con predecesoras directas y tres estimaciones de duración:

- optimista;
- más probable;
- pesimista.

La app construye una red AOA, reduce actividades ficticias de forma segura, calcula los resultados CPM/PERT y muestra una aproximación probabilística de la duración total del proyecto.

## Objetivo docente

La aplicación no debe ser solo una calculadora. Debe ayudar a entender:

1. qué significa una tabla de predecesoras;
2. por qué una red AOA puede necesitar actividades ficticias;
3. cuándo una ficticia es necesaria y cuándo puede eliminarse;
4. cómo se calculan tiempos tempranos y tardíos;
5. por qué una actividad es crítica;
6. qué limitaciones tiene la aproximación normal clásica de PERT;
7. por qué Monte Carlo será una mejora natural.

## Evolución del proyecto

El trabajo empezó con una app PERT/CPM con **Activity on Node (AON)**. Después se desarrolló una teoría para **Activity on Arrow (AOA)**.

La primera implementación AOA usaba una red canónica expandida:

- cada actividad real tenía un suceso inicial privado y un suceso final privado;
- cada precedencia directa se representaba con una actividad ficticia;
- la construcción era correcta, pero generaba demasiadas ficticias.

Después se actualizó el motor para reducir ficticias mediante contracciones y eliminaciones seguras, verificando siempre que la relación de precedencia entre actividades reales no cambiara.

## Estado funcional actual

La app permite:

- cargar un ejemplo didáctico;
- generar proyectos aleatorios;
- editar la tabla en Streamlit;
- validar la entrada;
- construir capas topológicas;
- construir red AOA canónica;
- reducir red AOA;
- comparar ficticias canónicas y finales;
- mostrar la red con Graphviz;
- calcular resultados por actividad;
- mostrar caminos críticos;
- seleccionar una actividad y ver explicación detallada;
- visualizar una distribución probabilística aproximada;
- calcular `P(T <= plazo)`;
- leer la teoría integrada.

## Concepto de red reducida

La red reducida se obtiene a partir de una red canónica correcta.

Una reducción solo se acepta si conserva exactamente el cierre transitivo de precedencias entre actividades reales.

Esto quiere decir que para cada par de actividades reales `(i, j)` debe conservarse si `i` precede o no precede a `j`.

## Advertencia conceptual

No presentar la red reducida como “mínima global” salvo que el modo exacto lo haya certificado dentro de sus límites.

Usar expresiones como:

- “reducción segura”;
- “red reducida verificable”;
- “búsqueda exacta acotada”;
- “reducción voraz segura”.

Evitar expresiones como:

- “red AOA mínima”;
- “número mínimo garantizado de ficticias”;
- “óptimo global para cualquier red”.

## Archivos de referencia

- `THEORY.md`: teoría integrada en la app.
- `docs/AOA_ALGORITHM.md`: explicación técnica del algoritmo.
- `docs/MONTE_CARLO_ROADMAP.md`: plan de simulación futura.
- `docs/VALIDATION_AND_TESTING.md`: invariantes y pruebas.
- `docs/CODEX_TASKS.md`: próximas tareas recomendadas.
