# Validación y pruebas

## Principio general

La aplicación debe priorizar la corrección lógica de la red AOA sobre la belleza del dibujo.

Una red reducida es válida si representa exactamente las mismas precedencias entre actividades reales que la tabla original.

## Comandos mínimos

```bash
python -m py_compile app.py pert_aoa_core.py
```

```bash
python - <<'PY'
from pert_aoa_core import self_test
self_test()
print('self_test ok')
PY
```

## Invariantes que deben conservarse

### 1. Todas las actividades reales aparecen una vez

Para cada actividad real de entrada debe existir exactamente un arco real en la red AOA.

### 2. Ninguna actividad real puede tener el mismo suceso inicial y final

No debe existir una actividad real de la forma:

$$
u\xrightarrow{a}u
$$

### 3. La red AOA debe ser acíclica

Después de construir o reducir la red debe existir un orden topológico de sucesos.

### 4. La relación de precedencia debe conservarse exactamente

Para cada par de actividades reales $i,j$:

$$
i\prec_P j \iff i\prec_G j
$$

### 5. Las ficticias tienen duración y varianza cero

Toda actividad ficticia debe cumplir:

$$
d=0
$$

$$
\sigma^2=0
$$

### 6. Las actividades reales conservan duración y varianza

La reducción no debe modificar la duración esperada ni la varianza de las actividades reales.

### 7. El cálculo CPM debe ser coherente

Para cada actividad real:

$$
EF=ES+d
$$

$$
LS=LF-d
$$

$$
TF=LS-ES
$$

### 8. Las actividades críticas deben tener holgura total cero

Con tolerancia numérica `EPS`.

## Casos de prueba recomendados

### Caso lineal

```text
A -> B -> C
```

Esperado:

- sin ficticias de precedencia innecesarias;
- un único camino crítico si todas las duraciones son positivas;
- duración total igual a suma de duraciones.

### Caso paralelo simple

```text
A y B sin predecesoras
C depende de A y B
```

Esperado:

- la red debe expresar que C espera a A y B;
- puede requerir ficticias según la compactación;
- no debe introducir precedencia entre A y B.

### Caso diamante

```text
A -> B
A -> C
B,C -> D
```

Esperado:

- D debe esperar a B y C;
- B y C no deben precederse entre sí;
- debe existir una reducción razonable de ficticias.

### Caso con predecesoras compartidas

```text
A,B -> C
A,B -> D
C,D -> E
```

Esperado:

- buen caso para comprobar reducción por sucesos compartidos;
- no crear precedencias C -> D ni D -> C.

### Ciclo

```text
A depende de C
B depende de A
C depende de B
```

Esperado:

- error de validación.

### Predecesora desconocida

```text
A depende de Z
```

Esperado:

- error de validación.

### Autorrelación

```text
A depende de A
```

Esperado:

- error de validación.

## Pruebas aleatorias

Generar muchos DAG aleatorios y comprobar:

1. la red reducida es acíclica;
2. la representación exacta se conserva;
3. el número de ficticias finales no supera al canónico;
4. el cálculo de tiempos no falla.

## Pruebas futuras para Monte Carlo

Cuando se implemente Monte Carlo:

- con duraciones deterministas, todas las simulaciones deben dar la misma duración;
- con una sola cadena, la duración simulada debe ser la suma de duraciones simuladas;
- con dos caminos paralelos, la duración debe ser el máximo de ambos;
- el índice de criticidad debe estar entre 0 y 1;
- la suma de frecuencias de caminos críticos debe interpretarse cuidadosamente, porque puede haber empates.
