# AGENTS.md — Contexto de trabajo para Codex

## Propósito del proyecto

Este repositorio contiene una aplicación didáctica en Streamlit para analizar proyectos mediante **PERT/CPM con Activity on Arrow (AOA)**.

La aplicación debe permitir que un estudiante vea cómo se pasa de una tabla de actividades y predecesoras a una red AOA, cómo se reducen actividades ficticias de forma segura, cómo se calculan los tiempos tempranos y tardíos, y cómo se estima probabilísticamente la duración del proyecto.

## Estado actual

La versión actual ya incluye:

- entrada editable de actividades;
- generación aleatoria de proyectos válidos;
- estimaciones PERT de tres valores: optimista, más probable y pesimista;
- validación de referencias desconocidas, actividades repetidas, autorrelaciones y ciclos;
- construcción de una red AOA canónica correcta;
- reducción segura de actividades ficticias;
- modos de reducción `auto`, `greedy`, `exact` y `none`;
- cálculo CPM/PERT sobre la red AOA;
- identificación de actividades y caminos críticos;
- representación Graphviz de la red;
- distribución probabilística aproximada de la duración del proyecto;
- cálculo de probabilidad de cumplir un plazo;
- teoría integrada en `THEORY.md`;
- funciones preparatorias para una futura simulación Monte Carlo.

## Regla de oro

No sacrificar la corrección lógica de la red para obtener un dibujo más simple.

Una simplificación AOA solo es válida si conserva exactamente la relación de precedencia entre actividades reales:

```text
actividad i precede a actividad j en la tabla
⇔
el suceso final de i alcanza el suceso inicial de j en la red AOA
```

Por tanto, no elimines ni contraigas ficticias sin comprobar la equivalencia lógica mediante alcanzabilidad.

## Decisión matemática principal

La app no debe afirmar que siempre obtiene una red AOA globalmente mínima. La minimización exacta del número de actividades ficticias es un problema combinatorio difícil en general.

La formulación correcta para esta app es:

```text
tabla de predecesoras
→ red AOA canónica correcta
→ reducción segura exacta acotada o voraz
→ red AOA reducida verificable
```

El modo `exact` es acotado y apto para redes pequeñas. El modo `greedy` es rápido y seguro, pero no garantiza mínimo global. El modo `auto` decide entre ambos.

## Estilo de implementación

- Mantener el motor matemático separado de la interfaz.
- Evitar lógica compleja dentro de `app.py`.
- Implementar algoritmos en `pert_aoa_core.py` y exponer funciones claras.
- Usar nombres descriptivos en español cuando sean visibles al usuario y nombres de código consistentes en inglés.
- Mantener la app didáctica: cada cálculo importante debe poder explicarse.
- No añadir dependencias pesadas sin justificarlo.
- Mantener compatibilidad con Streamlit y Graphviz.

## Archivos principales

- `app.py`: interfaz Streamlit.
- `pert_aoa_core.py`: motor matemático y algorítmico.
- `THEORY.md`: teoría mostrada dentro de la app.
- `README.md`: instrucciones básicas de instalación y uso.
- `example_project.csv`: ejemplo didáctico.
- `docs/`: documentación de contexto para desarrollo.

## Comandos de comprobación

En este equipo, no confiar en `python` del PATH: puede apuntar al alias de Microsoft Store. Para ejecutar la app y las pruebas, usar el entorno Conda:

```powershell
D:\Usuarios\antonio\anaconda3\envs\streamlit-apps\python.exe
```

El entorno contiene Python 3.11 y Streamlit. Si `conda env list` falla por plugins de Conda, usar directamente el ejecutable anterior.

Antes de proponer cambios relevantes, ejecutar al menos:

```bash
python -m py_compile app.py pert_aoa_core.py
python - <<'PY'
from pert_aoa_core import self_test
self_test()
print('self_test ok')
PY
```

Equivalente recomendado en PowerShell para este equipo:

```powershell
& "$env:USERPROFILE\anaconda3\envs\streamlit-apps\python.exe" -m py_compile app.py pert_aoa_core.py
& "$env:USERPROFILE\anaconda3\envs\streamlit-apps\python.exe" -c "from pert_aoa_core import self_test; self_test(); print('self_test ok')"
& "$env:USERPROFILE\anaconda3\envs\streamlit-apps\python.exe" -m unittest discover -s tests -v
```

Si `py_compile` falla por permisos escribiendo en `__pycache__`, redirigir la caché de bytecode a una carpeta temporal:

```powershell
$env:PYTHONPYCACHEPREFIX="$env:TEMP\codex_pycache"
& "$env:USERPROFILE\anaconda3\envs\streamlit-apps\python.exe" -m py_compile app.py pert_aoa_core.py
```

Para probar la interfaz:

```bash
streamlit run app.py
```

Equivalente recomendado en PowerShell:

```powershell
& "$env:USERPROFILE\anaconda3\envs\streamlit-apps\python.exe" -m streamlit run app.py
```

## Reglas específicas para Markdown y LaTeX

En los documentos Markdown de teoría, usar delimitadores con dólar:

- ecuaciones en línea: `$...$`;
- ecuaciones independientes:

```markdown
$$
formula
$$
```

Evitar `\[...\]` y `\(...\)` porque han dado problemas de renderizado.

## Próxima gran ampliación

La siguiente fase prevista es implementar simulación Monte Carlo.

No reescribir la arquitectura para hacerlo. La idea es reutilizar:

- la misma topología reducida;
- muestreos aleatorios de duración por actividad;
- recálculo CPM en cada iteración;
- almacenamiento de duración total y camino crítico observado.

Ver `docs/MONTE_CARLO_ROADMAP.md`.
