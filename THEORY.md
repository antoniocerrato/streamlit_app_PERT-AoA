# Teoría didáctica del PERT/CPM con Activity on Arrow

## 1. Objetivo

Esta aplicación estudia una red de proyecto usando la representación **Activity on Arrow**, abreviada normalmente como **AOA**.

En una red AOA:

- las **actividades** se representan mediante **flechas**;
- los **nodos** representan **sucesos** o **hitos**;
- una flecha va desde el suceso que permite comenzar una actividad hasta el suceso que se alcanza al terminarla;
- algunas flechas pueden ser **ficticias**, es decir, tienen duración cero y solo sirven para expresar una relación lógica.

El objetivo es construir una red correcta a partir de una tabla de actividades y predecesoras, calcular los tiempos tempranos y tardíos, identificar el camino crítico y estimar la distribución probabilística de la duración del proyecto.

---

## 2. Tabla de actividades

Sea $A$ el conjunto de actividades reales del proyecto:

$$
A=\{a_1,a_2,\ldots,a_n\}.
$$

Esta expresión se lee así:

> $A$ es el conjunto formado por las actividades $a_1$, $a_2$, hasta $a_n$.

Para cada actividad $a\in A$, se define su conjunto de predecesoras directas:

$$
P(a)\subseteq A.
$$

Se lee así:

> $P(a)$ es un subconjunto de $A$ que contiene las actividades que deben terminar antes de que pueda empezar la actividad $a$.

Por ejemplo, si:

$$
P(D)=\{A,B\},
$$

entonces la actividad $D$ no puede comenzar hasta que hayan terminado las actividades $A$ y $B$.

La entrada matemática del problema es, por tanto:

$$
(A,P),
$$

donde $A$ es el conjunto de actividades y $P$ es la función que asigna a cada actividad su conjunto de predecesoras.

---

## 3. Condiciones de validez

Antes de construir la red, la tabla debe cumplir algunas condiciones.

### 3.1. Todas las predecesoras deben existir

Para toda actividad $a\in A$, debe cumplirse:

$$
P(a)\subseteq A.
$$

Esto significa que no se puede escribir como predecesora una actividad que no exista en la tabla.

### 3.2. Una actividad no puede precederse a sí misma

Debe cumplirse:

$$
a\notin P(a).
$$

Se lee así:

> La actividad $a$ no pertenece a su propio conjunto de predecesoras.

Si una actividad dependiera de sí misma, nunca podría empezar.

### 3.3. La red no puede contener ciclos

Una red PERT/CPM debe ser acíclica. No puede existir una cadena lógica como:

$$
A\rightarrow B\rightarrow C\rightarrow A.
$$

Si esto ocurriese, $A$ tendría que terminar antes de $B$, $B$ antes de $C$ y $C$ antes de $A$. El proyecto quedaría bloqueado.

---

## 4. Capas topológicas

Para comprobar si la red es acíclica, se puede construir una sucesión de conjuntos.

Primero se define:

$$
Q_0=\varnothing.
$$

Se lee así:

> Al principio no hay ninguna actividad procesada.

En la etapa $k$, se define el conjunto:

$$
L_k=\{a\in A\setminus Q_k\mid P(a)\subseteq Q_k\}.
$$

Esta fórmula es muy importante. Se lee así:

> $L_k$ es el conjunto de actividades $a$ que están en $A$ pero no están en $Q_k$, y cuyas predecesoras están todas incluidas en $Q_k$.

El símbolo $A\setminus Q_k$ significa:

$$
A\setminus Q_k=\{a\in A\mid a\notin Q_k\}.
$$

Es decir:

> Actividades que todavía no han sido procesadas.

La condición $P(a)\subseteq Q_k$ significa:

> Todas las predecesoras de $a$ ya han sido procesadas.

Después se actualiza:

$$
Q_{k+1}=Q_k\cup L_k.
$$

Se lee así:

> El nuevo conjunto de actividades procesadas es el conjunto anterior más las actividades que pueden procesarse ahora.

Si en algún paso se obtiene:

$$
Q_m=A,
$$

entonces todas las actividades han podido ordenarse y no hay ciclos.

Si, por el contrario:

$$
L_k=\varnothing
$$

pero todavía queda alguna actividad sin procesar, entonces existe un ciclo.

---

## 5. De AON a AOA: decisión de modelización

Una tabla de predecesoras describe de forma natural una red **Activity on Node**. En AON, cada actividad es un nodo y cada flecha representa una dependencia.

En AOA ocurre al revés:

- las actividades son flechas;
- los nodos son sucesos.

La conversión de una tabla de predecesoras a una red AOA no es única. Una misma tabla puede representarse mediante varias redes AOA equivalentes. Algunas redes tienen menos sucesos, otras tienen menos actividades ficticias, y otras son más fáciles de leer.

Esta aplicación utiliza una red AOA **canónica expandida**.

Esto significa:

> La red generada no intenta ser la red AOA con el menor número posible de sucesos o de actividades ficticias. Su objetivo principal es ser correcta, transparente y fácil de explicar.

Esta decisión es importante porque las redes AOA mínimas pueden ser difíciles de construir y no siempre son las mejores para aprender la lógica del método.

---

## 6. Red AOA canónica expandida

Para cada actividad real $a\in A$, se crean dos sucesos:

$$
\alpha_a
$$

y

$$
\omega_a.
$$

Se leen así:

- $\alpha_a$: suceso de comienzo propio de la actividad $a$;
- $\omega_a$: suceso de final propio de la actividad $a$.

La actividad real $a$ se representa mediante la flecha:

$$
\alpha_a\longrightarrow\omega_a.
$$

Esta flecha tiene duración igual a la duración esperada de la actividad $a$.

Además, se crea un suceso global de inicio:

$$
S,
$$

y un suceso global de fin:

$$
T.
$$

---

## 7. Actividades ficticias

Si una actividad $p$ es predecesora directa de una actividad $a$, es decir:

$$
p\in P(a),
$$

se añade una flecha ficticia:

$$
\omega_p\longrightarrow\alpha_a.
$$

Esta flecha se lee así:

> Desde el final de $p$ hasta el comienzo de $a$.

Tiene duración cero:

$$
d_{\omega_p,\alpha_a}=0.
$$

También tiene varianza cero:

$$
\sigma^2_{\omega_p,\alpha_a}=0.
$$

Su única función es imponer la relación lógica:

> $a$ no puede empezar hasta que $p$ haya terminado.

Si una actividad no tiene predecesoras, se conecta al inicio global:

$$
S\longrightarrow\alpha_a.
$$

Si una actividad no tiene sucesoras, se conecta al final global:

$$
\omega_a\longrightarrow T.
$$

---

## 8. Conjunto de sucesos y conjunto de flechas

El conjunto de sucesos de la red canónica es:

$$
V=\{S,T\}\cup\{\alpha_a\mid a\in A\}\cup\{\omega_a\mid a\in A\}.
$$

Se lee así:

> El conjunto de sucesos contiene el inicio, el final, todos los comienzos propios de actividades y todos los finales propios de actividades.

El conjunto de flechas contiene tres tipos de elementos.

### 8.1. Flechas reales

$$
E_R=\{(\alpha_a,\omega_a)\mid a\in A\}.
$$

Cada flecha de $E_R$ representa una actividad real.

### 8.2. Flechas ficticias de precedencia

$$
E_D=\{(\omega_p,\alpha_a)\mid a\in A,\;p\in P(a)\}.
$$

Cada flecha de $E_D$ representa una dependencia directa.

### 8.3. Flechas de inicio y fin

$$
E_S=\{(S,\alpha_a)\mid P(a)=\varnothing\},
$$

$$
E_T=\{(\omega_a,T)\mid a\text{ no tiene sucesoras}\}.
$$

La red completa es:

$$
G=(V,E),
$$

con:

$$
E=E_R\cup E_D\cup E_S\cup E_T.
$$

---

## 9. Por qué la construcción es correcta

Si $p\in P(a)$, entonces la red contiene la flecha ficticia:

$$
\omega_p\longrightarrow\alpha_a.
$$

Como la actividad $p$ termina en $\omega_p$ y la actividad $a$ empieza en $\alpha_a$, esta flecha obliga a que $a$ solo pueda empezar después de que $p$ haya terminado.

Por tanto, toda precedencia directa de la tabla queda representada en la red.

Además, si existe una cadena de precedencias:

$$
p\rightarrow b\rightarrow c\rightarrow a,
$$

la red contendrá un camino desde el final de $p$ hasta el comienzo de $a$. Por tanto, también se conservan las precedencias indirectas.

La construcción no añade restricciones falsas entre actividades independientes, porque solo se insertan flechas ficticias para relaciones que aparecen explícitamente en la tabla de predecesoras.

---

## 10. Duraciones PERT de las actividades

Para cada actividad real $a$, se introducen tres estimaciones:

- duración optimista: $o_a$;
- duración más probable: $m_a$;
- duración pesimista: $p_a$.

La duración esperada clásica de PERT es:

$$
t_a=\frac{o_a+4m_a+p_a}{6}.
$$

Se lee así:

> La duración esperada es una media ponderada donde la duración más probable pesa cuatro veces.

La varianza clásica de PERT es:

$$
\sigma_a^2=\left(\frac{p_a-o_a}{6}\right)^2.
$$

La desviación típica es:

$$
\sigma_a=\sqrt{\sigma_a^2}.
$$

Las actividades ficticias tienen:

$$
t_d=0,
$$

$$
\sigma_d^2=0.
$$

---

## 11. Recorrido hacia delante: tiempos tempranos de sucesos

A cada suceso $i\in V$ se le asigna un tiempo temprano:

$$
E_i.
$$

Se lee así:

> $E_i$ es el instante más temprano en el que puede ocurrir el suceso $i$.

El suceso inicial cumple:

$$
E_S=0.
$$

Para cualquier otro suceso $j$, el tiempo temprano se calcula como:

$$
E_j=\max_{(i,j)\in E}\{E_i+t_{ij}\}.
$$

Se lee así:

> El tiempo temprano de $j$ es el máximo de los tiempos de llegada a $j$ desde todos sus sucesos anteriores.

Se toma el máximo porque un suceso solo puede ocurrir cuando han terminado todas las actividades que llegan a él.

La duración esperada del proyecto es:

$$
\mu_T=E_T.
$$

---

## 12. Recorrido hacia atrás: tiempos tardíos de sucesos

A cada suceso $i\in V$ se le asigna un tiempo tardío:

$$
L_i.
$$

Se lee así:

> $L_i$ es el instante más tardío en el que puede ocurrir el suceso $i$ sin retrasar el proyecto.

El suceso final cumple:

$$
L_T=E_T.
$$

Para cualquier otro suceso $i$, el tiempo tardío se calcula como:

$$
L_i=\min_{(i,j)\in E}\{L_j-t_{ij}\}.
$$

Se lee así:

> El tiempo tardío de $i$ es el mínimo de los tiempos máximos permitidos por todas las flechas que salen de $i$.

Se toma el mínimo porque todas las actividades sucesoras deben poder realizarse sin retrasar el proyecto.

---

## 13. Tiempos de cada actividad real

Sea una actividad real $a$ representada por la flecha:

$$
\alpha_a\longrightarrow\omega_a.
$$

Su inicio temprano es:

$$
ES_a=E_{\alpha_a}.
$$

Su final temprano es:

$$
EF_a=ES_a+t_a.
$$

Su final tardío es:

$$
LF_a=L_{\omega_a}.
$$

Su inicio tardío es:

$$
LS_a=LF_a-t_a.
$$

Estas cuatro magnitudes son las que se muestran en la aplicación para cada actividad.

---

## 14. Holgura total

La holgura total de una actividad real es:

$$
HT_a=LS_a-ES_a.
$$

También puede escribirse como:

$$
HT_a=LF_a-EF_a.
$$

Si:

$$
HT_a=0,
$$

entonces la actividad es crítica.

Se lee así:

> Una actividad crítica no puede retrasarse sin retrasar la duración esperada del proyecto.

---

## 15. Holgura libre

En redes AOA compactas, la holgura libre de una flecha $(i,j)$ suele definirse como:

$$
HL_{ij}=E_j-E_i-t_{ij}.
$$

Sin embargo, en la red canónica expandida de esta aplicación cada actividad real tiene un suceso final propio. Por esa razón, la holgura libre de la flecha real aislada puede no ser la magnitud más didáctica.

La aplicación muestra una holgura libre proyectada a nivel de actividad:

$$
HL_a=\min_{s\in S(a)} ES_s-EF_a,
$$

si $a$ tiene sucesoras. Aquí $S(a)$ es el conjunto de sucesoras directas de $a$.

Si $a$ no tiene sucesoras, se usa:

$$
HL_a=E_T-EF_a.
$$

Esta magnitud responde a la pregunta:

> ¿Cuánto puede retrasarse la actividad $a$ sin retrasar el inicio temprano de ninguna sucesora directa?

---

## 16. Camino crítico

Un arco $(i,j)$ es crítico si su holgura total es cero:

$$
L_j-E_i-t_{ij}=0.
$$

Un camino crítico es un camino desde $S$ hasta $T$ formado por arcos críticos.

Al proyectar ese camino sobre las flechas reales, se obtiene una secuencia de actividades críticas:

$$
a_{c,1}\rightarrow a_{c,2}\rightarrow\cdots\rightarrow a_{c,r}.
$$

La suma de sus duraciones esperadas coincide con la duración esperada del proyecto:

$$
\sum_{q=1}^{r}t_{a_{c,q}}=E_T.
$$

Puede existir más de un camino crítico.

---

## 17. Distribución probabilística aproximada del proyecto

En el PERT clásico, cada actividad se considera una variable aleatoria. La duración esperada de una actividad es $t_a$ y su varianza es $\sigma_a^2$.

Si se selecciona un camino crítico dominante $C$, la media del proyecto se aproxima por:

$$
\mu_T=\sum_{a\in C}t_a.
$$

La varianza del proyecto se aproxima por:

$$
\sigma_T^2=\sum_{a\in C}\sigma_a^2.
$$

La desviación típica del proyecto es:

$$
\sigma_T=\sqrt{\sigma_T^2}.
$$

Después se usa una aproximación normal:

$$
T\sim\mathcal N(\mu_T,\sigma_T^2).
$$

Si se desea calcular la probabilidad de terminar antes de un plazo $D$, se calcula:

$$
P(T\leq D)=\Phi\left(\frac{D-\mu_T}{\sigma_T}\right),
$$

donde $\Phi$ es la función de distribución acumulada de la normal estándar.

---

## 18. Limitaciones de la aproximación normal

La aproximación anterior es útil y muy didáctica, pero tiene limitaciones.

La duración real del proyecto no es simplemente la duración de un camino fijo. En realidad, si las actividades son aleatorias, el camino crítico puede cambiar de una realización a otra.

Matemáticamente, la duración del proyecto puede verse como:

$$
T=\max_{C\in\mathcal C}\sum_{a\in C}X_a,
$$

donde $\mathcal C$ es el conjunto de caminos completos desde el inicio hasta el fin y $X_a$ es la duración aleatoria de la actividad $a$.

Por tanto, cuando hay varios caminos casi críticos, la aproximación mediante un único camino crítico puede infravalorar el riesgo de retraso.

Esta es una de las razones por las que la aplicación está diseñada para poder incorporar después simulaciones de Monte Carlo.

---

## 19. Preparación para Monte Carlo

Una simulación de Monte Carlo seguirá esta idea:

1. Para cada actividad real $a$, generar una duración aleatoria $X_a$.
2. Recalcular los tiempos de la red AOA con esas duraciones.
3. Obtener una duración total simulada $T^{(k)}$.
4. Repetir el proceso muchas veces.
5. Construir una distribución empírica de la duración del proyecto.

Una forma habitual de generar duraciones compatibles con las tres estimaciones PERT es usar una distribución beta escalada entre $o_a$ y $p_a$.

Si $Y_a$ sigue una beta en el intervalo $[0,1]$, entonces:

$$
X_a=o_a+(p_a-o_a)Y_a.
$$

La aplicación aún no ejecuta la simulación Monte Carlo como resultado principal, pero el motor de cálculo ya contiene las funciones necesarias para añadir esa capa posteriormente.

---

## 20. Lectura crítica de la red AOA canónica

La red canónica expandida tiene ventajas:

- es correcta por construcción;
- cada actividad real aparece como una flecha clara;
- cada dependencia directa aparece como una ficticia clara;
- evita ambigüedades típicas de las redes AOA compactas;
- permite explicar el método paso a paso;
- es fácil de verificar mediante conjuntos y recorridos topológicos.

También tiene inconvenientes:

- puede contener más sucesos de los estrictamente necesarios;
- puede contener más actividades ficticias que una red AOA compacta;
- puede ser más grande visualmente.

Por eso debe interpretarse como una red didáctica y computacionalmente robusta, no como una red AOA mínima.

Una mejora natural sería añadir una fase posterior de contracción de sucesos, aceptando solo aquellas contracciones que mantengan exactamente las mismas precedencias entre actividades reales.

---

## 21. Resumen de fórmulas principales

Duración esperada de una actividad:

$$
t_a=\frac{o_a+4m_a+p_a}{6}.
$$

Varianza de una actividad:

$$
\sigma_a^2=\left(\frac{p_a-o_a}{6}\right)^2.
$$

Tiempo temprano de un suceso:

$$
E_j=\max_{(i,j)\in E}\{E_i+t_{ij}\}.
$$

Tiempo tardío de un suceso:

$$
L_i=\min_{(i,j)\in E}\{L_j-t_{ij}\}.
$$

Inicio temprano de una actividad:

$$
ES_a=E_{\alpha_a}.
$$

Final temprano:

$$
EF_a=ES_a+t_a.
$$

Final tardío:

$$
LF_a=L_{\omega_a}.
$$

Inicio tardío:

$$
LS_a=LF_a-t_a.
$$

Holgura total:

$$
HT_a=LS_a-ES_a.
$$

Probabilidad aproximada de cumplir un plazo $D$:

$$
P(T\leq D)=\Phi\left(\frac{D-\mu_T}{\sigma_T}\right).
$$

---

## 22. Referencias orientativas

- Dimsdale, B. (1963). *Computer Construction of Minimal Project Networks*. IBM Systems Journal.
- Sysło, M. M. (1981). *On the construction of event-node networks*. RAIRO - Operations Research.
- Mrozek, M. (1984). *A Note on Minimum-Dummy-Activities PERT Networks*. RAIRO - Operations Research.
- Krishnamoorthy, M. S. & Deo, N. (1979). *Complexity of the minimum-dummy-activities problem in a PERT network*. Networks.
- Mouhoub, N. E. & Benhocine, A. (2012). *An efficient algorithm for generating AoA networks*.
- Grande-González, F., Ballesteros-Pérez, P., González-Cruz, M. C. & Lucko, G. (2025). *An Alternative Representation of Project Activity Networks: Activity on Arcs and Nodes*.
- Project Management Institute. Materiales introductorios sobre CPM, holgura total y holgura libre.

