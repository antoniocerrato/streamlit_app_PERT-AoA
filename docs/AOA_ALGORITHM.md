# Algoritmo AOA usado en la aplicación

## 1. Entrada matemática

La entrada es un conjunto finito de actividades reales:

$$
A=\{a_1,a_2,\ldots,a_n\}
$$

Para cada actividad $a\in A$, se define un conjunto de predecesoras directas:

$$
P(a)\subseteq A
$$

La entrada completa es:

$$
(A,P)
$$

En código, esto se representa mediante un diccionario `Dict[str, Activity]`.

## 2. Validación

La tabla debe cumplir:

### Referencias válidas

$$
P(a)\subseteq A
$$

### Sin autorrelaciones

$$
a\notin P(a)
$$

### Sin ciclos

Se construyen capas topológicas:

$$
Q_0=\varnothing
$$

$$
L_k=\{a\in A\setminus Q_k \mid P(a)\subseteq Q_k\}
$$

$$
Q_{k+1}=Q_k\cup L_k
$$

Si en algún paso $L_k=\varnothing$ y $Q_k\neq A$, hay un ciclo.

## 3. Cierre transitivo de actividades

La relación de precedencia directa se convierte en una relación de precedencia completa.

Una actividad $i$ precede a $j$ si existe un camino de predecesoras desde $i$ hasta $j$.

En código:

```python
activity_transitive_closure(activities)
```

Devuelve pares `(i, j)` que deben preservarse en cualquier red AOA equivalente.

## 4. Red AOA canónica

Para cada actividad real $a$, se crean dos sucesos privados:

$$
\alpha_a
$$

$$
\omega_a
$$

La actividad real se representa como:

$$
\alpha_a \xrightarrow{a} \omega_a
$$

Para cada precedencia directa $p\in P(a)$, se añade una ficticia:

$$
\omega_p \xrightarrow{0} \alpha_a
$$

Además:

- se añade un suceso global `S`;
- se añade un suceso global `T`;
- las actividades iniciales reciben una ficticia desde `S`;
- las actividades finales reciben una ficticia hacia `T`.

Esta red es correcta, pero suele tener demasiadas ficticias.

## 5. Relación de precedencia inducida por una red AOA

Una red AOA induce una relación de precedencia entre actividades reales.

Si la actividad real $i$ va de $s_i$ a $f_i$, y la actividad real $j$ va de $s_j$ a $f_j$, entonces:

$$
i\prec_G j
\iff
f_i \text{ alcanza } s_j
$$

Es decir, $i$ precede a $j$ si desde el suceso final de $i$ existe un camino hasta el suceso inicial de $j$.

## 6. Criterio de representación exacta

Una red AOA $G$ representa exactamente la tabla si:

$$
i\prec_P j
\iff i\prec_G j
$$

para todo par de actividades reales $i,j\in A$.

Este es el criterio más importante del proyecto.

La aplicación conserva además una condición de identificabilidad AOA. Si una actividad real $a$ está representada por el par de sucesos $(s_a,f_a)$, entonces:

$$
a\neq b \Longrightarrow (s_a,f_a)\neq(s_b,f_b).
$$

Es decir, dos actividades reales distintas no pueden compartir simultáneamente el mismo suceso inicial y el mismo suceso final. Esta condición evita que una reducción convierta actividades paralelas reales en flechas indistinguibles entre los mismos dos sucesos. En esos casos una ficticia puede seguir siendo necesaria aunque la relación de precedencia $R_G=R_P$ se conserve.

En código:

```python
is_exact_representation(events, arcs, target_closure)
```

## 7. Reducción segura

La app reduce la red mediante dos operaciones principales:

1. contracción de sucesos;
2. eliminación de ficticias redundantes.

Una contracción de sucesos identifica dos sucesos $u$ y $v$ como si fueran uno solo.

Una contracción solo se acepta si:

- la red resultante no tiene ciclos;
- ninguna actividad real queda con el mismo suceso inicial y final;
- no aparecen arcos reales duplicados imposibles de distinguir;
- la representación exacta se conserva.

La tercera condición se comprueba sobre actividades reales, no sobre ficticias. Las ficticias paralelas de duración cero sí pueden deduplicarse porque no representan trabajo real; las actividades reales deben seguir identificándose por su par de sucesos.

## 8. Función objetivo

Las redes se comparan mediante una puntuación lexicográfica:

$$
J(G)=\left(n_D, n_V, n_E\right)
$$

donde:

- $n_D$ es el número de ficticias;
- $n_V$ es el número de sucesos;
- $n_E$ es el número total de flechas.

Primero se minimizan ficticias; en caso de empate, sucesos; en caso de empate, flechas totales.

## 9. Métodos de reducción

### `none`

No reduce. Muestra la red canónica.

### `greedy`

Busca contracciones seguras y aplica la mejor mejora local.

Ventajas:

- rápido;
- interactivo;
- seguro.

Limitación:

- no garantiza mínimo global.

### `exact`

Explora estados de red mediante búsqueda acotada.

Ventajas:

- puede encontrar mejores soluciones en redes pequeñas;
- útil para ejemplos docentes.

Limitaciones:

- está acotado por `max_exact_states`;
- puede ser costoso.

### `auto`

Usa exacto si el número de actividades está por debajo del límite configurado y voraz en caso contrario.

## 10. Cálculo CPM sobre AOA

Para cada suceso $v$ se calcula su tiempo temprano $E(v)$:

$$
E(v)=\max_{(u,v)\in E}\left(E(u)+d_{uv}\right)
$$

Para cada suceso $u$ se calcula su tiempo tardío $L(u)$:

$$
L(u)=\min_{(u,v)\in E}\left(L(v)-d_{uv}\right)
$$

Si la red tiene un único sumidero `T`, se inicializa $L(T)=E(T)$. Si una reducción deja varios sumideros, se usa:

$$
Z=\{z\in V\mid z\text{ no tiene sucesores}\}
$$

y:

$$
T_P=\max_{z\in Z}E(z).
$$

Entonces:

$$
L(z)=T_P \quad \text{para todo } z\in Z.
$$

Esto evita depender de un nombre concreto de suceso final y hace robusto el cálculo CPM tras reducciones topológicas seguras.

Para una actividad real $a=(i,j)$ con duración $d_a$:

$$
ES_a=E(i)
$$

$$
EF_a=E(i)+d_a
$$

$$
LF_a=L(j)
$$

$$
LS_a=L(j)-d_a
$$

La holgura total es:

$$
TF_a=LS_a-ES_a
$$

La actividad es crítica si:

$$
TF_a=0
$$

## 11. Aproximación probabilística clásica

Para cada actividad se usa:

$$
\mu_a=\frac{o_a+4m_a+p_a}{6}
$$

$$
\sigma_a^2=\left(\frac{p_a-o_a}{6}\right)^2
$$

La duración esperada del proyecto se obtiene con las medias. La varianza aproximada se calcula sobre un camino crítico dominante:

$$
\sigma_T^2=\sum_{a\in CP}\sigma_a^2
$$

Después se aproxima:

$$
T\sim \mathcal{N}(\mu_T,\sigma_T^2)
$$

Esta aproximación es didáctica, pero tiene limitaciones cuando existen varios caminos casi críticos. La simulación Monte Carlo futura debe resolver esta limitación.
