# Teoría didáctica del PERT/CPM con Activity on Arrow y reducción segura de ficticias

## 1. Objetivo

Esta aplicación estudia una red de proyecto mediante la representación **Activity on Arrow**, abreviada como **AOA**.

En una red AOA:

- las **actividades reales** se representan mediante **flechas**;
- los **nodos** representan **sucesos** o **hitos**;
- una flecha va desde el suceso que permite comenzar una actividad hasta el suceso que se alcanza al terminarla;
- algunas flechas pueden ser **ficticias**: tienen duración cero y sirven solo para expresar restricciones lógicas.

El objetivo de la aplicación es:

1. construir una red AOA a partir de una tabla de actividades y predecesoras;
2. reducir el número de actividades ficticias sin alterar la lógica del proyecto;
3. calcular tiempos tempranos y tardíos;
4. identificar actividades y caminos críticos;
5. estimar una distribución probabilística aproximada de la duración del proyecto;
6. dejar preparada la estructura para una futura simulación Monte Carlo.

La idea central es esta:

> Una ficticia solo debe conservarse si es necesaria para representar correctamente las precedencias del proyecto.

---

## 2. Conjunto de actividades y predecesoras

Sea $A$ el conjunto de actividades reales del proyecto:

$$
A=\{a_1,a_2,\ldots,a_n\}.
$$

Se lee así:

> $A$ es el conjunto formado por las actividades $a_1$, $a_2$, hasta $a_n$.

Para cada actividad $a\in A$, se define su conjunto de predecesoras directas:

$$
P(a)\subseteq A.
$$

Se lee así:

> $P(a)$ es el subconjunto de actividades que deben terminar antes de que pueda comenzar la actividad $a$.

Por ejemplo, si:

$$
P(D)=\{A,B\},
$$

entonces la actividad $D$ no puede comenzar hasta que hayan terminado $A$ y $B$.

La entrada matemática del problema es:

$$
(A,P),
$$

donde $A$ es el conjunto de actividades y $P$ es la función que asigna a cada actividad su conjunto de predecesoras directas.

---

## 3. Condiciones de validez de la tabla

Antes de construir la red, la tabla debe cumplir tres condiciones básicas.

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

Una red PERT/CPM debe ser acíclica. No puede existir una cadena como:

$$
A\rightarrow B\rightarrow C\rightarrow A.
$$

Si esto ocurriera, $A$ tendría que terminar antes de $B$, $B$ antes de $C$ y $C$ antes de $A$. El proyecto quedaría bloqueado.

---

## 4. Capas topológicas mediante conjuntos

Para comprobar que no hay ciclos, se puede construir una sucesión de conjuntos.

Primero se define:

$$
Q_0=\varnothing.
$$

Se lee así:

> Al principio no hay ninguna actividad procesada.

En la etapa $k$, se define:

$$
L_k=\{a\in A\setminus Q_k\mid P(a)\subseteq Q_k\}.
$$

Esta fórmula se lee así:

> $L_k$ es el conjunto de actividades $a$ que están en $A$ pero todavía no están en $Q_k$, y cuyas predecesoras ya están todas incluidas en $Q_k$.

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

## 5. De la tabla de predecesoras a una red AOA

Una tabla de predecesoras describe de forma natural una red **Activity on Node**. En AON, cada actividad es un nodo y cada flecha representa una dependencia.

En AOA ocurre lo contrario:

- las actividades son flechas;
- los nodos son sucesos.

La conversión de una tabla de predecesoras a una red AOA no es única. Una misma tabla puede representarse mediante varias redes AOA equivalentes.

Algunas redes tienen:

- menos sucesos;
- menos actividades ficticias;
- menos cruces visuales;
- más claridad didáctica.

Por tanto, no basta con construir una red correcta. También interesa compactarla.

La aplicación usa dos etapas:

$$
\text{tabla de predecesoras}
\longrightarrow
\text{red AOA canónica}
\longrightarrow
\text{red AOA reducida}.
$$

La primera red es correcta por construcción. La segunda se obtiene mediante reducciones verificadas.

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

- $\alpha_a$: suceso propio de comienzo de la actividad $a$;
- $\omega_a$: suceso propio de final de la actividad $a$.

La actividad real $a$ se representa mediante la flecha:

$$
\alpha_a\longrightarrow\omega_a.
$$

Esta flecha tiene duración igual a la duración esperada de la actividad.

Si $p$ es predecesora directa de $a$, es decir:

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
t_{\omega_p,\alpha_a}=0.
$$

También tiene varianza cero:

$$
\sigma^2_{\omega_p,\alpha_a}=0.
$$

Su única función es imponer la relación lógica:

> $a$ no puede empezar hasta que $p$ haya terminado.

Si una actividad no tiene predecesoras, se puede conectar a un suceso global de inicio $S$. Si una actividad no tiene sucesoras, se puede conectar a un suceso global de fin $T$.

La red canónica es muy clara, pero suele tener demasiadas ficticias. Por eso la aplicación no se queda ahí.

---

## 7. Relación de precedencia que debe conservarse

Para saber si una red AOA reducida sigue siendo correcta, necesitamos comparar relaciones de precedencia.

Primero se calcula la relación de precedencia completa de la tabla. Diremos que:

$$
a\prec b
$$

si $a$ debe terminar antes de que $b$ pueda comenzar, ya sea por una dependencia directa o por una cadena de dependencias.

Por ejemplo, si:

$$
A\rightarrow B\rightarrow C,
$$

entonces:

$$
A\prec B,
$$

$$
B\prec C,
$$

 y también:

$$
A\prec C.
$$

La relación completa puede escribirse como:

$$
R_P=\{(a,b)\in A\times A\mid a\prec b\}.
$$

Se lee así:

> $R_P$ es el conjunto de pares de actividades tales que la primera precede a la segunda.

---

## 8. Precedencia inducida por una red AOA

En una red AOA, cada actividad real $a$ es una flecha:

$$
i_a\longrightarrow j_a.
$$

Aquí:

- $i_a$ es el suceso inicial de la actividad $a$;
- $j_a$ es el suceso final de la actividad $a$.

La red AOA dice que $a$ precede a $b$ si existe un camino desde el final de $a$ hasta el comienzo de $b$:

$$
a\prec_G b
\quad\Longleftrightarrow\quad
j_a\leadsto i_b.
$$

El símbolo $\leadsto$ significa:

> Existe un camino dirigido desde un suceso hasta otro.

La relación inducida por la red AOA es:

$$
R_G=\{(a,b)\in A\times A\mid j_a\leadsto i_b\}.
$$

La red AOA es correcta si y solo si:

$$
R_G=R_P.
$$

Esta igualdad es la clave de toda la reducción.

Se lee así:

> La red reducida representa exactamente las mismas precedencias que la tabla original: ni añade precedencias falsas ni elimina precedencias necesarias.

Además, la aplicación exige una condición propia de la representación AOA: dos actividades reales distintas no pueden tener exactamente el mismo suceso inicial y el mismo suceso final.

Formalmente, si:

$$
a=(i_a,j_a)
$$

y:

$$
b=(i_b,j_b),
$$

entonces, para actividades reales distintas:

$$
a\neq b \Longrightarrow (i_a,j_a)\neq(i_b,j_b).
$$

Esta condición significa que la aplicación:

$$
a\longmapsto(i_a,j_a)
$$

debe ser inyectiva sobre las actividades reales.

No es solo una cuestión estética. Si dos actividades reales comparten los dos sucesos, quedan superpuestas como flechas paralelas entre el mismo par de eventos. La red puede seguir conservando $R_G=R_P$, pero deja de ser una representación AOA identificable: los sucesos ya no distinguen una actividad real de la otra. En ese caso puede ser necesario conservar una ficticia.

---

## 9. Por qué no se pueden borrar ficticias sin comprobar

Una actividad ficticia puede parecer innecesaria visualmente, pero eliminarla puede producir dos tipos de errores.

### 9.1. Eliminar una precedencia necesaria

Si se borra una ficticia que era el único camino entre el final de $p$ y el comienzo de $a$, entonces desaparece la relación:

$$
p\prec a.
$$

La red permitiría empezar $a$ demasiado pronto.

### 9.2. Crear una precedencia falsa

Si se fusionan sucesos sin cuidado, puede aparecer un camino nuevo entre actividades que antes eran independientes.

Eso produciría una relación falsa:

$$
a\prec_G b
$$

cuando realmente:

$$
(a,b)\notin R_P.
$$

En ese caso, la red sería demasiado restrictiva.

Por eso la aplicación aplica una regla estricta:

> Una reducción solo se acepta si después de aplicarla sigue cumpliéndose $R_G=R_P$.

---

## 10. Contracción segura de sucesos

Una forma eficaz de reducir ficticias es fusionar sucesos.

Sean $u$ y $v$ dos sucesos de la red. Contraerlos significa sustituirlos por un único suceso:

$$
u\sim v.
$$

La red resultante se puede escribir como:

$$
G/(u\sim v).
$$

Se lee así:

> Red obtenida al identificar o fusionar los sucesos $u$ y $v$.

Después de la contracción, algunas flechas ficticias pueden convertirse en bucles de duración cero. Un bucle ficticio es una flecha de un suceso a sí mismo:

$$
u\longrightarrow u.
$$

Ese bucle no aporta ninguna restricción y se elimina.

También pueden aparecer varias ficticias iguales entre los mismos sucesos. En ese caso se conserva solo una, porque varias ficticias paralelas de duración cero tienen el mismo efecto lógico que una sola.

La contracción se acepta solo si:

$$
R_{G/(u\sim v)}=R_P.
$$

Es decir:

> Al fusionar los sucesos $u$ y $v$, la red sigue representando exactamente las mismas precedencias entre actividades reales.

La aplicación añade una segunda comprobación: después de la contracción, las actividades reales deben seguir siendo identificables por sus pares de sucesos.

Por tanto, una contracción segura debe cumplir simultáneamente:

$$
R_{G/(u\sim v)}=R_P
$$

y:

$$
a\neq b \Longrightarrow (i_a,j_a)\neq(i_b,j_b).
$$

Esta segunda condición explica por qué en un diamante:

```text
A -> B
A -> C
B,C -> D
```

puede seguir siendo necesaria una ficticia. Si se fusionan demasiado los sucesos, $B$ y $C$ podrían quedar como dos actividades reales paralelas con el mismo origen y el mismo destino. La precedencia lógica seguiría siendo correcta, pero la representación AOA perdería identificabilidad.

---

## 11. Eliminación segura de ficticias redundantes

Después de contraer sucesos, puede ocurrir que una ficticia ya no sea necesaria.

Sea $d=(u,v)$ una ficticia. La red sin esa ficticia se escribe:

$$
G-d.
$$

La ficticia $d$ es redundante si:

$$
R_{G-d}=R_P.
$$

Se lee así:

> Si al quitar la ficticia la relación de precedencia entre actividades reales no cambia, entonces la ficticia es redundante.

En ese caso, la aplicación la elimina.

---

## 12. Algoritmo de reducción usado en la aplicación

La aplicación sigue este esquema:

1. Construir la red AOA canónica expandida.
2. Calcular la relación de precedencia completa $R_P$ de la tabla.
3. Probar contracciones de sucesos.
4. Para cada contracción candidata, recalcular $R_G$.
5. Aceptar la contracción solo si $R_G=R_P$ y las actividades reales siguen teniendo pares de sucesos distintos.
6. Eliminar ficticias redundantes con el mismo criterio.
7. Repetir mientras se pueda mejorar la red.

La función objetivo usada es lexicográfica:

$$
J(G)=\big(|E_D|,|V|,|E|\big).
$$

Esto significa que la aplicación intenta reducir, por este orden:

1. el número de actividades ficticias $|E_D|$;
2. el número de sucesos $|V|$;
3. el número total de flechas $|E|$.

Se compara de forma lexicográfica. Por ejemplo:

$$
(2,8,14)<(3,6,12)
$$

porque dos ficticias es mejor que tres, aunque tenga más sucesos.

---

## 13. Búsqueda exacta y reducción voraz

La reducción exacta de actividades ficticias puede ser un problema combinatorio muy costoso cuando la red crece. Por eso la aplicación ofrece varios modos.

### 13.1. Modo exacto acotado

En redes pequeñas, la aplicación puede explorar muchas contracciones posibles y quedarse con la mejor red encontrada según:

$$
J(G)=\big(|E_D|,|V|,|E|\big).
$$

Si la exploración termina dentro del límite de estados, la solución encontrada es exacta dentro de ese espacio de contracciones seguras.

### 13.2. Modo voraz seguro

En redes grandes, la aplicación usa una estrategia voraz:

> En cada paso se elige la contracción segura que más mejora $J(G)$.

Este método es rápido e interactivo. No promete siempre el mínimo global en redes grandes, pero nunca acepta una red lógicamente incorrecta.

### 13.3. Modo automático

El modo automático usa búsqueda exacta acotada para redes pequeñas y reducción voraz segura para redes mayores.

---

## 14. Duraciones PERT de las actividades

Para cada actividad real $a$, se introducen tres estimaciones:

- duración optimista: $o_a$;
- duración más probable: $m_a$;
- duración pesimista: $p_a$.

La duración esperada clásica de PERT es:

$$
t_a=\frac{o_a+4m_a+p_a}{6}.
$$

Se lee así:

> La duración esperada es una media ponderada en la que la duración más probable pesa cuatro veces.

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

## 15. Recorrido hacia delante: tiempos tempranos de sucesos

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

Se toma el máximo porque un suceso solo puede ocurrir cuando han terminado todas las flechas que llegan a él.

---

## 16. Recorrido hacia atrás: tiempos tardíos de sucesos

A cada suceso $i\in V$ se le asigna un tiempo tardío:

$$
L_i.
$$

Se lee así:

> $L_i$ es el instante más tardío en el que puede ocurrir el suceso $i$ sin retrasar el proyecto.

Si existe un único suceso final $T$, se cumple:

$$
L_T=E_T.
$$

En una red reducida puede ocurrir que no se conserve un único suceso llamado $T$. En ese caso se considera el conjunto de sucesos terminales:

$$
Z=\{z\in V\mid z\text{ no tiene flechas salientes}\}.
$$

La duración esperada del proyecto es:

$$
T_P=\max_{z\in Z}E_z.
$$

Todos los sucesos terminales se inicializan con esa misma fecha tardía:

$$
L_z=T_P \quad \text{para todo } z\in Z.
$$

Para cualquier otro suceso $i$, el tiempo tardío se calcula como:

$$
L_i=\min_{(i,j)\in E}\{L_j-t_{ij}\}.
$$

Se lee así:

> El tiempo tardío de $i$ es el mínimo de los tiempos máximos permitidos por todas las flechas que salen de $i$.

Se toma el mínimo porque todas las actividades sucesoras deben poder realizarse sin retrasar el proyecto.

---

## 17. Tiempos de cada actividad real

Sea una actividad real $a$ representada por la flecha:

$$
i_a\longrightarrow j_a.
$$

Su inicio temprano es:

$$
ES_a=E_{i_a}.
$$

Su final temprano es:

$$
EF_a=ES_a+t_a.
$$

Su final tardío es:

$$
LF_a=L_{j_a}.
$$

Su inicio tardío es:

$$
LS_a=LF_a-t_a.
$$

Estas cuatro magnitudes son las que se muestran en la aplicación para cada actividad.

---

## 18. Holgura total

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

## 19. Holgura libre

En una red AOA, la holgura libre de una flecha $(i,j)$ suele definirse como:

$$
HL_{ij}=E_j-E_i-t_{ij}.
$$

Para actividades reales, la aplicación muestra también una holgura libre proyectada a nivel de actividad:

$$
HL_a=\min_{s\in S(a)}ES_s-EF_a,
$$

si $a$ tiene sucesoras. Aquí $S(a)$ es el conjunto de sucesoras directas de $a$.

Si $a$ no tiene sucesoras, se usa:

$$
HL_a=E_T-EF_a.
$$

Esta magnitud responde a la pregunta:

> ¿Cuánto puede retrasarse la actividad $a$ sin retrasar el inicio temprano de ninguna sucesora directa?

---

## 20. Camino crítico

Un arco $(i,j)$ es crítico si su holgura total es cero:

$$
L_j-E_i-t_{ij}=0.
$$

Un camino crítico es un camino desde el inicio hasta el fin formado por arcos críticos.

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

## 21. Distribución probabilística aproximada del proyecto

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

## 22. Limitaciones de la aproximación normal

La aproximación anterior es útil y didáctica, pero tiene limitaciones.

La duración real del proyecto no es simplemente la duración de un camino fijo. En realidad, si las actividades son aleatorias, el camino crítico puede cambiar de una realización a otra.

Matemáticamente, la duración del proyecto puede verse como:

$$
T=\max_{C\in\mathcal C}\sum_{a\in C}X_a,
$$

donde $\mathcal C$ es el conjunto de caminos completos desde el inicio hasta el fin y $X_a$ es la duración aleatoria de la actividad $a$.

Por tanto, cuando hay varios caminos casi críticos, la aproximación mediante un único camino crítico puede infravalorar el riesgo de retraso.

Esta es una razón importante para preparar la aplicación para simulaciones de Monte Carlo.

---

## 23. Preparación para Monte Carlo

Una simulación de Monte Carlo seguirá esta idea:

1. Para cada actividad real $a$, generar una duración aleatoria $X_a$.
2. Recalcular los tiempos de la red AOA con esas duraciones.
3. Obtener una duración total simulada $T^{(k)}$.
4. Repetir el proceso muchas veces.
5. Construir una distribución empírica de la duración del proyecto.
6. Estimar directamente probabilidades como $P(T\leq D)$.

Una forma habitual de generar duraciones compatibles con las tres estimaciones PERT es usar una distribución beta escalada entre $o_a$ y $p_a$.

Si $Y_a$ sigue una beta en el intervalo $[0,1]$, entonces:

$$
X_a=o_a+(p_a-o_a)Y_a.
$$

La reducción AOA es topológica: depende de las precedencias, no de las duraciones. Por eso puede reutilizarse en cada iteración Monte Carlo.

---

## 24. Resumen de fórmulas principales

Duración esperada de una actividad:

$$
t_a=\frac{o_a+4m_a+p_a}{6}.
$$

Varianza de una actividad:

$$
\sigma_a^2=\left(\frac{p_a-o_a}{6}\right)^2.
$$

Relación de precedencia de la tabla:

$$
R_P=\{(a,b)\in A\times A\mid a\prec b\}.
$$

Relación de precedencia inducida por la red AOA:

$$
R_G=\{(a,b)\in A\times A\mid j_a\leadsto i_b\}.
$$

Criterio de corrección de la red AOA:

$$
R_G=R_P.
$$

Función objetivo de reducción:

$$
J(G)=\big(|E_D|,|V|,|E|\big).
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
ES_a=E_{i_a}.
$$

Final temprano:

$$
EF_a=ES_a+t_a.
$$

Final tardío:

$$
LF_a=L_{j_a}.
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

## 25. Referencias orientativas

- Dimsdale, B. (1963). *Computer Construction of Minimal Project Networks*. IBM Systems Journal.
- Sysło, M. M. (1981). *On the construction of event-node networks*. RAIRO - Operations Research.
- Mrozek, M. (1984). *A Note on Minimum-Dummy-Activities PERT Networks*. RAIRO - Operations Research.
- Krishnamoorthy, M. S. & Deo, N. (1979). *Complexity of the minimum-dummy-activities problem in a PERT network*. Networks.
- Mouhoub, N. E. & Benhocine, A. (2012). *An efficient algorithm for generating AoA networks*.
- Grande-González, F., Ballesteros-Pérez, P., González-Cruz, M. C. & Lucko, G. (2025). *An Alternative Representation of Project Activity Networks: Activity on Arcs and Nodes*.
