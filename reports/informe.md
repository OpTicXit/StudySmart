# StudySmart — Informe de minería de datos

**Sistema de seguimiento y predicción del riesgo académico**

> **Aviso:** los resultados principales vienen de datos **sintéticos** (`data/raw/registros_sinteticos.csv`, generados con `src/generate_data.py`). Sirven para construir y validar el pipeline, **no** para afirmar qué tan preciso sería el sistema con estudiantes reales. La sección 8 contrasta las conclusiones con un dataset real (UCI 320). Todas las cifras de este informe salen de los notebooks ejecutados (`notebooks/01`–`04`) y de los archivos de `reports/`.

---

## 1. Resumen

StudySmart toma registros por estudiante × asignatura × semestre, deriva indicadores, encuentra perfiles de estudio con K-Means y predice `riesgo_academico` con Random Forest. Con eso prioriza las asignaturas en riesgo y genera recomendaciones. El sistema admite **cualquier esquema de calificación** (0-5, 0-10, 0-20, 0-100, letras; cualquier número de cortes y pesos) y **predice el resultado desde la primera nota**.

Hallazgos principales:
- El **Random Forest** (PR-AUC en CV 0,713) supera al **árbol de decisión** (0,623). El **híbrido K-Means + RF** (0,714) **no mejora de forma apreciable** al RF solo: la diferencia (0,0004) es mucho menor que la variación entre folds (±0,05).
- Con datos sintéticos, el modelo anticipa el riesgo **antes de tener notas** casi tan bien como con dos cortes (PR-AUC en test de 0,670 frente a 0,675).
- Con datos **reales** (UCI 320), la primera nota predice bien las siguientes (R² 0,66–0,75), pero el modelo de ML apenas mejora a la regla "la siguiente nota será igual a la última". Esto limita lo que se puede prometer del sistema con datos reales.

---

## 2. Problema y variable objetivo

**Pregunta:** ¿qué asignaturas de un estudiante están en riesgo de perderse y qué conviene hacer al respecto?

**Variable objetivo:** `riesgo_academico = 1` si `nota_final < 3.0` (escala 0-5), y `0` si alcanza el umbral. El umbral es configurable. En UCI 320 equivale a G3 < 10 en escala 0-20.

**Reglas aplicadas en todo el proyecto:**

| Regla | Cómo se cumple |
|---|---|
| Sin fuga de datos | `nota_final`, `riesgo_academico` e `id_estudiante` nunca son features. `src/features.py` lo verifica con un `assert`. |
| Partición por estudiante | `GroupShuffleSplit` 80/20 por `id_estudiante`: 240 estudiantes en train y 60 en test, ninguno compartido. Los hiperparámetros se ajustan con `GroupKFold(5)` dentro de train. |
| Pipeline | Imputación (mediana), one-hot y K-Means van dentro del `Pipeline` y se ajustan en cada fold solo con datos de train. |
| Desbalance (~21 %) | `class_weight="balanced"`. Se evalúa con recall, precision y F1 de la clase riesgo, PR-AUC y ROC-AUC. |
| Reproducibilidad | `random_state=42` en todo. Al volver a ejecutar se obtienen las mismas cifras. |

---

## 3. Dato

**Fuente principal:** 6000 registros, 300 estudiantes, 4 semestres y 10 asignaturas (≈ 20 registros por estudiante). Hay 22 columnas: identificación, características de la materia (créditos, dificultad 1-5), contexto (jornada, trabaja, asignaturas reprobadas previas), hábitos (horas de estudio, asistencia, actividades, ejercicios, comprensión), notas de corte (corte 1 y corte 2) y dos variables de ruido (horas de sueño, días a la próxima evaluación).

**Calidad** (`notebooks/01_eda_preparacion.ipynb`):

| Revisión | Resultado |
|---|---|
| Nulos | `horas_estudio_semana` 2,85 %, `ejercicios_correctos_pct` 2,85 %, `comprension_tema` 3,10 % |
| Duplicados | 0 exactos y 0 de clave (estudiante, semestre, asignatura) |
| Fuera de dominio | 0 (porcentajes en 0-100, notas en 0-5, comprensión en 1-5) |
| Outliers (IQR 1,5) | menos del 0,8 % por variable. **Se conservan**: son valores plausibles y justamente corresponden a los casos de riesgo. |
| Objetivo | 1258 de 6000 en riesgo (**20,97 %**). Train 20,98 %, test 20,90 %. |

**Limpieza:** imputación por mediana dentro de un `Pipeline` ajustado solo con train (medianas: 7,0 h de estudio, 53,9 % de ejercicios correctos, comprensión 3,0). Salidas:
- `data/processed/registros_limpios.csv`: con los nulos sin imputar y la columna `particion`. Se usa para modelar.
- `data/processed/registros_imputados.csv`: con los nulos imputados.

**Fuentes secundarias:** UCI Student Performance (id 320; 649 estudiantes reales de secundaria con G1, G2 y G3) y UCI Dropout & Academic Success (id 697; 4424 registros, todavía sin usar).

---

## 4. Información

| Dato crudo | Indicador (información) | Qué dice |
|---|---|---|
| `nota_corte1`, `nota_corte2` | `promedio_cortes` = (c1 + c2) / 2 | nivel antes del final |
| `nota_corte1`, `nota_corte2` | `tendencia_notas` = c2 − c1 | si el estudiante mejora o empeora |
| actividades entregadas / asignadas | `actividades_completadas_pct` | constancia |
| ejercicios correctos / intentados | `ejercicios_correctos_pct` | dominio práctico |
| autoevaluación | `comprension_tema` (1-5) | comprensión percibida |
| clases asistidas | `asistencia_pct`, `inasistencias` | presencia |
| historial | `asignaturas_reprobadas_previas` | rezago acumulado (solo semestres anteriores, sin fuga) |
| asignatura | dificultad, créditos, tasa de riesgo por asignatura | exigencia de la materia |
| `nota_final` | `riesgo_academico` | **objetivo** (nunca es feature) |

**Lo que muestran los indicadores:**
- **Correlación con el riesgo:** las más fuertes son `promedio_cortes` (−0,54), `nota_corte2` (−0,50), `asignaturas_reprobadas_previas` (+0,46), `nota_corte1` (−0,45), `comprension_tema` (−0,44) y `ejercicios_correctos_pct` (−0,41). Las variables de ruido tienen correlación ≈ 0 (sueño 0,005; días a la evaluación −0,009).
- **Riesgo por asignatura:** va del 8,1 % (Ética Profesional, dificultad 1) al 33,4 % (Cálculo Diferencial, dificultad 5).
- **Redundancias:** `asistencia_pct` e `inasistencias` (r = −0,995) y `creditos` con `dificultad_asignatura` (r = 0,80).

---

## 5. Patrón

### 5.1 Perfiles de estudio (K-Means)
`notebooks/02_clustering_kmeans.ipynb`. El K-Means usa solo los **hábitos** (horas, asistencia, actividades, ejercicios y comprensión), sin notas, estandarizados y ajustados con train.

**Elección de k:** la silueta más alta es en k = 2 (0,212) y el codo (la mayor desaceleración de la caída de inercia) está en k = 3. Se eligió **k = 3** (silueta 0,190) porque da perfiles con significado distinto y accionable. La silueta es baja para cualquier k: los hábitos forman un continuo, y los clusters son una segmentación útil de ese continuo, no grupos naturales.

| Perfil | Horas/sem | Asistencia | Actividades | Ejercicios | Comprensión | Riesgo train | Riesgo test |
|---|---|---|---|---|---|---|---|
| Esfuerzo alto, baja comprensión | 9,1 | 91,5 % | 84,4 % | 43,8 % | 2,38 | 24,2 % | 23,7 % |
| Pocas horas y baja constancia | 4,5 | 80,1 % | 61,8 % | 48,7 % | 2,38 | 36,7 % | 36,0 % |
| Estudio constante y dominio | 7,3 | 87,6 % | 82,8 % | 69,8 % | 3,85 | 2,1 % | 3,6 % |

El patrón se mantiene en test. El perfil "esfuerzo alto, baja comprensión" muestra que **más horas no bastan**: lo que necesita es cambiar el método de estudio.

### 5.2 Modelos de clasificación
`notebooks/03_modelos.ipynb`. Hiperparámetros ajustados con `GridSearchCV` + `GroupKFold(5)`, optimizando la PR-AUC. Umbral de decisión: 0,5.

| Modelo | Mejores hiperparámetros |
|---|---|
| Árbol de decisión | gini, profundidad 4, min_samples_leaf 50 |
| Random Forest | 300 árboles, profundidad 10, max_features sqrt, min_samples_leaf 20 |
| Híbrido K-Means + RF | igual que el RF, más el cluster (one-hot) como feature |

**Tabla comparativa** (`reports/comparativa_modelos.csv`). Test con 60 estudiantes no vistos; la PR-AUC de un clasificador al azar sería 0,209.

| Modelo | PR-AUC en CV | ROC-AUC en CV | PR-AUC test | ROC-AUC test | Recall riesgo | Precisión riesgo | F1 riesgo | Accuracy |
|---|---|---|---|---|---|---|---|---|
| Árbol | 0,623 ± 0,051 | 0,866 ± 0,012 | 0,594 | 0,854 | 0,704 | 0,518 | 0,597 | 0,801 |
| Random Forest | 0,713 ± 0,050 | 0,892 ± 0,008 | 0,675 | 0,885 | 0,812 | 0,527 | 0,639 | 0,809 |
| Híbrido | 0,714 ± 0,048 | 0,893 ± 0,008 | 0,675 | 0,884 | 0,820 | 0,524 | 0,640 | 0,807 |

**Lectura:**
- El RF y el híbrido **detectan alrededor del 81–82 %** de los casos en riesgo. A cambio, **cerca de la mitad de las alertas son falsas** (precisión ≈ 0,52).
- Para una herramienta de apoyo es un intercambio razonable, porque una alerta falsa cuesta poco y un riesgo no detectado cuesta mucho.
- El híbrido quedó como "mejor" por la regla de selección (PR-AUC en CV), pero **su ventaja sobre el RF es ruido**. El cluster aporta interpretación, no precisión.

### 5.3 Importancia de variables
Importancia por permutación en test (cuánto cae la PR-AUC al desordenar cada variable), con el modelo de dos cortes:

| Variable | RF | Híbrido |
|---|---|---|
| promedio_cortes | 0,064 | 0,067 |
| asignaturas_reprobadas_previas | 0,058 | 0,051 |
| nota_corte2 | 0,043 | 0,041 |
| comprension_tema | 0,032 | 0,034 |
| ejercicios_correctos_pct | 0,023 | 0,020 |
| nota_corte1 | 0,018 | 0,018 |
| horas_estudio_semana | −0,002 | −0,001 |

Las variables de ruido (horas de sueño, días a la evaluación) quedan en ≈ 0, como se esperaba. `horas_estudio_semana` **tampoco aporta** una vez que se conocen la comprensión y los ejercicios.

### 5.4 Reglas del árbol (referencia interpretable)
Están completas en `reports/reglas_arbol.txt`. Algunas reglas que predicen riesgo (n = registros de train):
- SI `promedio_cortes ≤ 2,91` Y `asignaturas_reprobadas_previas > 2,5` Y `ejercicios_correctos_pct ≤ 32` ENTONCES riesgo (n = 164; peso de riesgo 0,97).
- SI `promedio_cortes ≤ 2,62` Y `asignaturas_reprobadas_previas ≤ 2,5` ENTONCES riesgo (n = 146; 0,89).
- SI `2,91 < promedio_cortes ≤ 3,31` Y `ejercicios_correctos_pct ≤ 44,2` Y `reprobadas_previas ≤ 3,5` ENTONCES riesgo (n = 228; 0,70).
- SI `3,31 < promedio_cortes ≤ 3,70` Y `ejercicios_correctos_pct ≤ 36,35` Y `actividades_completadas_pct ≤ 78,15` ENTONCES riesgo (n = 57; 0,80).

---

## 6. Predicción a lo largo del semestre y esquemas de calificación

### 6.1 Cualquier escala, cualquier número de cortes
`src/calificacion.py` define un `Esquema` con escala, nota aprobatoria, cortes con pesos, **componentes dentro de cada corte** y letras opcionales.

El esquema por defecto es el **institucional del usuario**: escala 0-5 (aprueba con 3.0, valor supuesto porque la tabla de referencia no indica la escala) y 3 seguimientos.

| Componente | Seguimiento 1 (sem. 1-6) · 30 % | Seguimiento 2 (sem. 7-11) · 30 % | Seguimiento 3 (sem. 12-16) · 40 % |
|---|---|---|---|
| Lectura previa | 30 % | — | — |
| Proyecto de aula | — | 30 % | 30 % |
| Competencias específicas (individual) | 35 % | 35 % | 35 % |
| Actividades académicas | 35 % | 35 % | 20 % |
| Competencias genéricas | — | — | 15 % |

Cada nota individual es un **espacio calificable** con su peso en la asignatura. Un componente puede tener varias notas (por ejemplo, 2 o más actividades académicas), que pesan igual dentro del componente. Con lo que ya está calificado, el sistema calcula:
- el **promedio actual**, que solo usa lo calificado;
- el **porcentaje evaluado**;
- la **nota necesaria en cada espacio pendiente** para llegar a 3.0. Esto se puede pedir para **un seguimiento** (para aprobar ese seguimiento) o para **toda la asignatura** (para aprobar la nota final).

Para el modelo predictivo, un seguimiento cuenta como conocido cuando tiene **al menos el 50 % calificado**, y entonces se usa su promedio actual. Es una aproximación, marcada como `shortcut` en el código.

El plan de estudios (6 semestres, 38 asignaturas) está en `data/plan_estudios.csv`. La dificultad y los créditos de cada asignatura son **estimaciones** editables. Las asignaturas que coinciden con las del entrenamiento se asocian a esa categoría; el resto entra al modelo solo con su dificultad y sus créditos.

También hay esquemas ya definidos para 0-5 (30/30/40 sin componentes), 0-10, 0-20, 0-100 (25/25/50) y letras A-F (40/60). Cada profesor o institución puede crear el suyo.

Cada nota se convierte a la escala de referencia del modelo (0-5, aprueba con 3.0) **por tramos que conservan la nota aprobatoria**. Así, 2,4/5, 8/20 y 48/100 equivalen a 2,40 en la referencia (verificado en el notebook 04).

### 6.2 Un modelo por etapa
`notebooks/04_prediccion_etapas.ipynb`. Cada etapa tiene un clasificador de riesgo, un regresor de la nota final y, en las etapas 0 y 1, un regresor del siguiente corte. Se usa el tipo de modelo y los hiperparámetros elegidos en el notebook 03. Resultados en test:

| Etapa (cortes conocidos) | PR-AUC riesgo | Recall | Precisión | Regla "nota < 3" (PR-AUC) | MAE nota final | R² | MAE regla ingenua |
|---|---|---|---|---|---|---|---|
| 0 (solo hábitos) | 0,670 | 0,824 | 0,502 | — | 0,424 | 0,524 | 0,616 (media de train) |
| 1 (primer corte) | 0,663 | 0,824 | 0,510 | 0,473 | 0,422 | 0,532 | 0,568 (= corte 1) |
| 2 (dos cortes) | 0,675 | 0,820 | 0,524 | 0,597 | 0,410 | 0,554 | 0,471 (= promedio) |

**Predicción del siguiente corte:**
- Corte 1 desde hábitos: MAE 0,463 (regla 0,627).
- Corte 2 desde el corte 1: MAE 0,490, R² 0,451 (regla "igual al corte 1": MAE 0,611).

Los cortes restantes se deducen de la nota final prevista y de los pesos del esquema. También se calcula **el promedio que hace falta en lo que queda para aprobar**.

---

## 7. Decisión

`src/recomendar.py`:
- `recomendar(registro, notas, esquema, umbral_alerta)` devuelve:
  - la probabilidad y el nivel de riesgo;
  - el cluster y su perfil;
  - la nota final prevista;
  - los cortes previstos;
  - el promedio necesario para aprobar;
  - 2-3 recomendaciones.
- `priorizar(...)` ordena las asignaturas por riesgo.
- El **esquema** y el **umbral de alerta** son los parámetros que fija cada institución o profesor.

**Cómo se eligen las recomendaciones:**
- Si hay alerta, primero va "Prioriza la materia", con la nota que se necesita en cada nota pendiente.
- Después vienen los hábitos accionables en los que el estudiante está por debajo de la mediana de train. Se ordenan por *importancia de la variable en la etapa × qué tan por debajo está*.
- Si el perfil es "esfuerzo alto, baja comprensión", se recomienda cambiar el método de estudio en lugar de estudiar más horas.

**Ejemplo ejecutado:** Cálculo Diferencial; trabaja; 4 h por semana; 35 % de ejercicios correctos; comprensión 2/5; esquema institucional.
- Con el seguimiento 1 completo (lectura previa 2,5; competencias específicas 2,4; dos actividades: 2,8 y 3,0; nota del seguimiento ≈ 2,6), el resultado es:
- Riesgo de **0,857 (alto)**. Perfil: "pocas horas y baja constancia".
- Nota final prevista de 2,83. Seguimiento 2 previsto: 2,84; seguimiento 3: 3,00.
- *"Prioriza Calculo Diferencial: necesitas 3.17 en cada nota pendiente para aprobar la asignatura (nota final prevista: 2.83)."*
- *"Refuerza el tema con tutoría o asesoría del profesor: tu comprensión es 2/5 (mediana 3/5)."*
- *"Practica más ejercicios del tema y revisa cada error: aciertas 35 % (la mediana es 54 %)."*

Si en el seguimiento 1 solo se conoce la lectura previa (2,5, es decir, el 30 % del seguimiento), el sistema responde: *"En Seguimiento 1 llevas 30% calificado (promedio 2.50): necesitas 3.21 en cada nota pendiente para aprobarlo."*

En el mismo ejemplo, al priorizar junto a Bases de Datos con un perfil fuerte, Cálculo queda primero (nota prevista 2,83) y Bases de Datos queda al final (4,40). Las autocomprobaciones del script verifican que el mismo estudiante en escala 0-5 y en 0-20 recibe la misma probabilidad de riesgo.

---

## 8. Contraste con datos reales (UCI Student Performance, id 320)

Son 649 estudiantes reales de secundaria en Portugal (curso de portugués), con notas en escala 0-20; el 15,4 % tiene G3 < 10. Se usó KFold(5) porque hay una fila por estudiante. Se compara un RF con notas + contexto, un RF solo con notas y la regla "la siguiente nota será igual a la última" (`reports/uci320_prediccion_cortes.csv`):

| Caso | Modelo | MAE (0-20) | R² | Recall riesgo |
|---|---|---|---|---|
| G1 → G2 | RF notas + contexto | 1,074 | 0,735 | 0,779 |
| | regla: igual a la última | 1,018 | 0,739 | 0,738 |
| G1 → G3 | RF notas + contexto | 1,196 | 0,711 | 0,840 |
| | regla: igual a la última | 1,247 | 0,658 | 0,880 |
| G1+G2 → G3 | RF notas + contexto | 0,795 | 0,849 | 0,900 |
| | regla: igual a la última | 0,767 | 0,833 | 0,890 |

**Conclusión honesta:**
- **Con datos reales, la primera nota sí anticipa bien las siguientes.** El error es de ≈ 1,2 puntos sobre 20 para la nota final.
- **El ML casi no supera a la regla simple.** La gran ventaja que se ve en los datos sintéticos viene en buena parte de cómo se generaron.
- El valor práctico del sistema con datos reales está más en **organizar la información** (la nota necesaria para aprobar, la priorización entre materias, los perfiles) que en ganar precisión.

---

## 9. Limitaciones

1. **Datos sintéticos.** Las relaciones entre hábitos y notas las definió el generador, así que las métricas de las secciones 5-7 validan el pipeline y no la realidad.
2. **UCI 320 es secundaria** (otro país y otro nivel educativo). Sirve como evidencia complementaria, no como validación del caso universitario. El dataset 697 (educación superior) todavía no se ha usado.
3. **Precisión moderada:** alrededor de la mitad de las alertas son falsas cuando el umbral es 0,5. El umbral es configurable y no se ajustó.
4. **Clusters débiles:** la silueta es de 0,19, así que los perfiles son una segmentación de un continuo.
5. **Más de 2 cortes:** los modelos se entrenaron con 2 cortes. Con 3 o más cortes conocidos se aproxima "corte 1 = promedio de los anteriores, corte 2 = el último". Habría que reentrenar con datos reales que tengan más cortes. Además, los **componentes** del esquema institucional (lectura previa, proyecto de aula, competencias, etc.) solo se usan para calcular la nota de cada seguimiento. **No son features del modelo**, porque los datos de entrenamiento no los tienen. Con registros reales por componente, podrían agregarse.
6. **Conversión entre escalas:** la conversión por tramos conserva el aprobado, pero supone que las escalas son comparables por encima y por debajo de él.
7. **Recomendaciones asociativas:** las recomendaciones salen de asociaciones, no de causalidad. Subir los ejercicios correctos se asocia a menos riesgo, pero el modelo no demuestra que hacerlo lo reduzca.
8. Los hiperparámetros por etapa no se ajustaron por separado: todas las etapas reutilizan los del notebook 03.

---

## 10. Conclusiones

- **Dato → Información:** los registros crudos se convierten en indicadores claros (promedio y tendencia de los cortes, porcentaje de actividades, rezago acumulado). Los más informativos son las notas de corte, las asignaturas reprobadas previas, la comprensión y los ejercicios correctos.
- **Patrón:** hay tres perfiles de estudio con riesgos muy distintos (2 %, 24 % y 37 %). El Random Forest es el mejor clasificador (PR-AUC en test de 0,675 frente a 0,594 del árbol). Agregar el cluster no mejora la predicción, pero sí ayuda a explicar y a recomendar.
- **Decisión:** el sistema prioriza las materias en riesgo, dice qué nota se necesita en los cortes restantes y da recomendaciones según las variables que más pesan. Funciona con cualquier esquema de calificación definido por la institución.
- **Siguiente paso clave:** recolectar registros **reales** (`data/raw/registros_personales.csv`) y reentrenar. Con datos reales hay que esperar que la ventaja sobre "mirar la última nota" sea pequeña, como muestra UCI 320.

---

## 11. Reproducibilidad

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python src/download_uci.py                  # UCI 320 y 697
python src/generate_data.py                 # solo si falta el CSV sintético
jupyter nbconvert --to notebook --execute --inplace notebooks/01_eda_preparacion.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/02_clustering_kmeans.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/03_modelos.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/04_prediccion_etapas.ipynb
python src/calificacion.py                  # autocomprobación de esquemas
python src/recomendar.py                    # ejemplo + autocomprobación
```

| Carpeta | Contenido |
|---|---|
| `src/` | `features.py` (features y partición), `modelo.py` (pipelines), `calificacion.py` (esquemas), `recomendar.py` (decisión) |
| `models/` | `modelo_riesgo.joblib` (paquete con las 3 etapas y el K-Means), `seleccion.json` |
| `reports/` | este informe, `comparativa_modelos.csv`, `etapas_*.csv`, `uci320_prediccion_cortes.csv`, `reglas_arbol.txt` |
