# Criterios de interfaz y didáctica

## Principio general

La aplicación debe enseñar el método, no solo devolver resultados.

Cada resultado importante debe estar acompañado de una explicación breve y verificable.

## Público objetivo

Estudiantes de asignaturas relacionadas con:

- proyectos de ingeniería;
- planificación de obras;
- dirección de proyectos;
- programación temporal;
- PERT/CPM.

## Pestañas actuales

### 1. Datos

Objetivo: introducir o generar la tabla de actividades.

Debe mostrar:

- identificador de actividad;
- estimación optimista;
- estimación más probable;
- estimación pesimista;
- predecesoras directas.

Debe explicar que las predecesoras son directas, no todas las precedencias indirectas.

### 2. Red AOA

Objetivo: visualizar la red.

Debe mostrar:

- actividades reales;
- actividades ficticias;
- camino crítico;
- sucesos;
- métricas de reducción.

Sugerencia futura: mostrar comparación lado a lado entre red canónica y red reducida.

### 3. Cálculo CPM/PERT

Objetivo: explicar los resultados temporales.

Debe mostrar:

- ES;
- EF;
- LS;
- LF;
- holgura total;
- holgura libre;
- criticidad.

La explicación de actividad seleccionada es importante y debe mantenerse.

### 4. Distribución probabilística

Objetivo: mostrar la aproximación normal clásica.

Debe dejar claro que es una aproximación basada en un camino crítico dominante.

No debe presentarse como una simulación Monte Carlo.

### 5. Teoría

Objetivo: integrar el documento `THEORY.md`.

Debe ser legible en Streamlit y usar LaTeX con `$`.

### 6. Monte Carlo después

Objetivo: explicar la futura ampliación.

Cuando se implemente Monte Carlo, esta pestaña puede convertirse en una pestaña funcional.

## Recomendaciones visuales

- Usar rojo para el camino crítico.
- Usar línea discontinua para ficticias.
- No saturar etiquetas de ficticias por defecto en redes grandes.
- Mantener opción para etiquetas compactas.
- Mostrar métricas de reducción de forma destacada.

## Explicaciones importantes

La app debería insistir en estas ideas:

1. Una actividad ficticia no consume tiempo.
2. Una actividad ficticia sí impone lógica.
3. No toda ficticia es innecesaria.
4. Eliminar ficticias sin comprobación puede crear errores.
5. El camino crítico puede cambiar si las duraciones son aleatorias.
6. La aproximación normal clásica no sustituye a Monte Carlo.

## Mejoras didácticas futuras

- Paso a paso de la reducción.
- Botón “¿por qué esta ficticia sigue aquí?”.
- Comparación entre red AON y AOA.
- Cuestionarios automáticos.
- Registro de errores frecuentes.
- Generador de ejercicios con solución.
- Modo profesor para exportar enunciado y solución.
