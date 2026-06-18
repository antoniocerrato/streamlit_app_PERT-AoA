# Historial de contexto del proyecto

## 1. App AON inicial

Se comenzó con una aplicación Streamlit para PERT/CPM con **Activity on Node**.

Características principales:

- actividades como nodos;
- predecesoras como arcos;
- cálculo ES, EF, LS, LF;
- camino crítico;
- generación aleatoria;
- teoría integrada.

## 2. Desarrollo de teoría AOA

Después se desarrolló una teoría para **Activity on Arrow**.

Se explicó:

- diferencia entre AON y AOA;
- sucesos y actividades;
- actividades ficticias;
- construcción canónica;
- cálculo de tiempos de sucesos;
- cálculo de tiempos de actividades;
- holguras;
- camino crítico;
- estimaciones PERT de tres valores.

El usuario pidió usar delimitadores `$` para LaTeX en Markdown porque `\[...\]` daba problemas de renderizado.

## 3. Revisión bibliográfica

Se revisó si la construcción automática AOA desde tablas de precedencia era novedosa.

Conclusión:

- el problema ha sido tratado extensamente;
- no conviene venderlo como nuevo método general;
- sí hay oportunidad en la parte didáctica, explicable y computacional;
- también podría haber oportunidad en simplificación segura, legibilidad y Monte Carlo, pero con cuidado.

## 4. Primera app AOA

Se creó una app AOA usando red canónica expandida.

Ventaja:

- correcta por construcción.

Problema:

- demasiadas ficticias.

## 5. Reducción segura de ficticias

El usuario indicó que había muchas ficticias innecesarias.

Se actualizó el enfoque:

```text
red canónica correcta
→ reducción segura
→ red reducida verificable
```

La regla clave fue conservar exactamente la relación de precedencia entre actividades reales.

## 6. Estado actual para Codex

Este paquete contiene la versión reducida de la app y documentación adicional para continuar el desarrollo.

La prioridad siguiente es consolidar pruebas y después implementar Monte Carlo.
