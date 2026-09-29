---
title: "Modelos de decisión: cómo se ha medido"
lang: es
---

Esta página explica cómo se han hecho las pruebas del
[toolkit de evaluación de modelos de decisión](https://github.com/joakinen/toolkit-modelos-de-decision): de dónde salen
los datos, qué se mide, cómo se calcula cada cifra y qué no dicen. Los resultados están en la
[página de resultados](index.html) y la explicación para quien empieza, en el
[informe](modelos-de-decision.pdf). Aquí va el detalle, para quien quiera comprobarlo o repetirlo.

# Principios

**El diseño se fija antes de medir.** Qué se pregunta, con qué datos, qué modelos y cómo se puntúa se escribe antes de
pasar ningún modelo por la prueba. Lo que se cambie después de ver resultados se anota, con la fecha y el motivo, en
la sección 9 ([Cambios al diseño y correcciones](#cambios)). Así se evita el sesgo más común en estas comparaciones: ajustar la prueba
hasta que salga lo que uno espera.

**Los datos de entrenar, calibrar y medir no se mezclan.** Cada prueba tiene su parte de entrenamiento (para los modelos
que se ajustan y para el clasificador clásico), a veces una de calibración, y una de prueba que ningún modelo ha visto
al prepararse. En los textos con fecha, el reparto es por fechas: se entrena con lo antiguo y se mide con lo reciente,
como pasaría en un uso real.

**Siempre hay una referencia clásica.** Junto a los modelos de decisión se mide un clasificador de los de antes de los
modelos de lenguaje (TF-IDF y regresión logística). Si el clásico iguala a un modelo de decisión, el modelo no está
justificado en esa tarea, por muy bien que acierte.

**Se publica también lo que sale mal.** Las pruebas en que los modelos fallan, y las correcciones de versiones
anteriores del informe, se cuentan igual que las que salen bien.

# Las métricas

## Acierto medio por clase

Es la media de los aciertos de cada opción por separado. Si una prueba tiene 80 correos de Tributos y 20 de Contratación,
un modelo que dijera siempre «Tributos» acertaría el 80 % de los correos, pero su acierto medio por clase sería
(100 % + 0 %) / 2 = 50 %: el del azar con dos opciones. Por eso se usa esta medida en lugar del acierto a secas. En la
prueba del BOE se llama «acierto medio por apartado».

## Intervalo de confianza

Con unos cientos de casos, parte de cualquier diferencia es suerte. Para saber cuánta se usa un *bootstrap*: se sortean
2.000 veces, con repetición, tantos casos como tiene la prueba, se recalcula la cifra en cada sorteo y se mira entre qué
valores cae el 95 % de las veces. Ese es el **intervalo de confianza del 95 %**. Si el intervalo de una diferencia entre
dos modelos no incluye el cero, la diferencia no se explica por azar. Cuando se comparan dos modelos se sortean los
mismos casos para los dos (*bootstrap* pareado), porque así se descuenta que unos casos sean más difíciles que otros.
Semilla 0 en todos los sorteos, para que las cifras se puedan repetir.

## Calibración y «falsa seguridad»

Un modelo está **calibrado** si, cuando dice «80 %», acierta el 80 % de las veces. Importa porque en un uso real la
probabilidad decide qué pasa sin revisión y qué va a una persona.

- **Falsa seguridad:** de las respuestas que el modelo da con un 90 % de probabilidad o más, qué parte son errores. Es la
  cifra más útil en la práctica: si se deja pasar sin revisar lo que supere el 90 %, esa es la parte de errores que se
  cuela.
- **ECE** (*expected calibration error*): se reparten las respuestas en diez tramos por su probabilidad (0-10 %,
  10-20 %…) y se mide, en cada tramo, la distancia entre la probabilidad media y el acierto real. Cero es la calibración
  perfecta.

## Log-loss

Mide cómo reparte el modelo la probabilidad, no solo si acierta: castiga mucho dar una probabilidad muy baja a la
respuesta correcta. Cuanto más bajo, mejor. Sirve para distinguir un modelo que acierta dudando de otro que acierta de
casualidad.

# Cómo se le pregunta a cada modelo

No todos los modelos entienden la pregunta igual, y eso afecta a la comparación:

- **Por el protocolo de decisión** (Kev y Jeff): se les manda el texto, la pregunta y las opciones con su descripción
  (`POST /v1/systemone`), y devuelven una probabilidad por opción. Las preguntas de sí o no van como tipo `noul`, que es
  el que conocen de su entrenamiento.
- **Por letras** (las réplicas abiertas de Jev y Qwen3.5 9B): se les presentan las opciones con una letra delante
  (A, B, C…), se les pide que contesten solo con la letra y se lee la probabilidad que el modelo da a cada letra en su
  primera palabra, repartiendo el total entre las letras válidas. Las preguntas de sí o no van como dos opciones.

A cada modelo se le pregunta por su vía natural, la que usa el laboratorio. Una comparación en que todos recibieran la
pregunta del mismo modo sería más igualada en la forma, pero penalizaría a quien no está hecho para ese modo.

# Las pruebas

Cada prueba se describe igual: qué pregunta, de dónde salen los datos, cómo se reparten, cómo se comprueba que los
modelos no los han visto antes y qué límites tiene.

## El BOE: una pregunta de vocabulario {#boe}

- **Pregunta:** ¿en qué apartado del BOE se publica este texto? Siete opciones, las secciones del sumario.
- **Datos:** textos descargados de la API de datos abiertos del BOE. La respuesta correcta es la sección en que lo
  publicó el propio BOE, así que es fiable por construcción. Al modelo se le da el cuerpo del texto, sin el título.
- **Reparto por fechas:** 1.400 textos de enero a junio de 2026 para entrenar (200 por apartado), 350 de julio y agosto
  para medir (50 por apartado) y 140 de septiembre para calibrar. Como mucho tres textos casi idénticos por tipo.
- **Ajuste:** Kev-0.8B y Kev-4B, con los hiperparámetros fijados antes de medir: 3 pasadas, lote de 4, 160 ejemplos
  generales de repaso, LoRA de rango 16, ritmo 4e-5 (0.8B) y 2e-5 (4B).
- **Comprobación de memoria:** se revisó a mano una muestra de aciertos y se separaron los textos cuyo tipo de título
  aparece en el entrenamiento de los que no; el 4B ajustado acierta casi igual en los dos grupos.
- **Límites:** un solo periodo de prueba y una sola pregunta; los textos del BOE están más normalizados que los escritos
  de un registro.
- **Scripts:** `boe/construir.py`, `boe/evaluar.py`, `boe/evaluar_kev.py`, `boe/ajustar.sh`, `boe/exportar.py`.

## El clasificador clásico y su curva de aprendizaje {#clasico}

- **Qué es:** cada texto se convierte en un vector TF-IDF (qué palabras y pares de palabras tiene, pesadas por lo raras
  que son) y una regresión logística aprende a separar las opciones. Se entrena en segundos, sin GPU.
- **En el BOE:** con los mismos 1.400 textos que los modelos ajustados; la regularización se eligió por validación cruzada
  en 5 partes sobre el entrenamiento, sin mirar la prueba.
- **Curva de aprendizaje:** el mismo clasificador con 1, 2, 5, 10, 20, 50, 100 y 200 textos por apartado, 10 sorteos por
  tamaño, para ver cuántos ejemplos le hacen falta.
- **En pares de textos** (PAWS-X y respuestas apoyadas): cada texto del par se convierte en un vector y el par se describe
  por la diferencia y el producto de los dos, la forma habitual de comparar textos con un clasificador lineal.
- **Scripts:** `boe/clasico.py`, `boe/clasico_curva.py`, `pawsx/clasico.py`.

## Fuera de la tarea: olvido y calibración {#olvido}

- **Pregunta:** ¿ajustar un modelo con una tarea le hace olvidar lo que ya sabía, o le quita la capacidad de dudar?
- **Datos:** 560 preguntas en inglés (las 12 pruebas del laboratorio y 440 casos de la partición de prueba del conjunto
  con que se publica Kev: noticias, reseñas, consultas, inferencia) y 150 en español (50 de XNLI, 50 de PAWS-X y 50
  reseñas de Amazon, de sus particiones de prueba, al azar con semilla 0).
- **Qué se mide:** acierto y falsa seguridad antes y después del ajuste, con los mismos casos.
- **Límites:** las preguntas en inglés salen del conjunto de prueba de Kev, así que favorecen a Kev frente a otros modelos;
  el control en español es pequeño.
- **Scripts:** `boe/control.py`, `boe/control_ampliado.py`, `boe/control_es.py`, `boe/evaluar_servidor.py`.

## Recalibración {#recalibracion}

- **Qué es:** corregir la seguridad del modelo con una **temperatura**, un número que suaviza las probabilidades sin
  cambiar cuál es la respuesta más probable.
- **Datos:** 400 casos que no se usan para nada más: 140 textos del BOE de septiembre, 200 preguntas generales y 60 en
  español (de las particiones de validación).
- **Cómo:** con el mismo procedimiento que trae Kev, se prueban temperaturas entre 0,25 y 4 y se elige la que da menos
  log-loss en esos 400 casos; después se mide el efecto en las pruebas. Como diagnóstico se mira también qué temperatura
  pediría cada parte de la mezcla por separado: si difieren mucho, una sola temperatura no basta.
- **Scripts:** `boe/calibracion.py`, `boe/calibrar.py`.

## PAWS-X: una pregunta de significado {#pawsx}

- **Pregunta:** ¿significan lo mismo estas dos oraciones? PAWS-X son pares con casi las mismas palabras que unas veces
  significan lo mismo y otras no («El vuelo de Madrid a Lima» frente a «El vuelo de Lima a Madrid»). Se hizo para que
  fallen los métodos que miran qué palabras hay.
- **Datos:** la versión en español. Prueba: 400 pares de su partición de prueba (traducida por personas), al azar con
  semilla 1, sin los 50 que usa el control en español. Entrenamiento: una bolsa de 5.000 pares de su partición de
  entrenamiento (traducida a máquina), al azar con semilla 0.
- **Ajuste:** Kev-0.8B con los primeros 200 pares de la bolsa y los mismos hiperparámetros que en el BOE.
- **¿Lo han visto antes?** Kev no: en su conjunto de entrenamiento, PAWS solo se usa para medir. **Jeff sí:** se entrenó
  con 12.000 pares de PAWS en inglés y usó su partición de validación para elegir su versión final, y los pares de PAWS-X
  son traducciones de pares de PAWS. Su resultado en esta prueba es la tarea aprendida en inglés trasladada al español,
  no una prueba sin datos de la tarea.
- **Scripts:** `pawsx/construir.py`, `pawsx/clasico.py`.

## Casos de uso {#casos}

El diseño completo, con fecha anterior a cualquier medida, está en
[`casos/DISENO.md`](https://github.com/joakinen/toolkit-modelos-de-decision/blob/main/casos/DISENO.md).

### Triaje del buzón general {#correo}

- **Preguntas:** a qué unidad corresponde (8 opciones), qué es (5) y si es urgente (sí o no), sobre correos que llegan al
  buzón general de un ayuntamiento ficticio.
- **Datos públicos:** correos sintéticos escritos para la prueba: 160 para entrenar el clásico y 120 para medir, 15 por
  unidad, de los que casi la mitad son difíciles a propósito (temas mezclados, lenguaje informal, reenvíos, palabras
  clave de otra unidad, plazos que hay que calcular con la fecha). Los de entrenamiento y los de prueba los escribieron
  autores distintos, para que no compartan frases hechas que le faciliten el trabajo al clasificador clásico; se
  comprobó que ninguna frase larga se repite más de dos veces y que ningún correo de prueba comparte más del 41 % de sus
  grupos de tres palabras con uno de entrenamiento.
- **Datos privados:** correos reales de un buzón general, anonimizados y etiquetados por quien lo lleva, que no salen de
  la máquina. Solo se publican las cifras. Instrucciones en `casos/correo/privado/LEEME.md`.
- **Límites:** unos correos sintéticos son más limpios que los reales; por eso existe la prueba privada.

### Completitud de un expediente {#expedientes}

- **Preguntas:** si consta el pago de la tasa, si está firmada la solicitud y si se aporta el documento de identidad
  (sí, no o no consta), y quién la presenta (el interesado, un representante con autorización o uno sin ella).
- **Datos:** resúmenes sintéticos de expedientes: 40 para entrenar el clásico y 60 para medir, con trampas deliberadas
  (el pago que se hará más adelante, el justificante de otra tasa, la firma pendiente, el documento citado pero no
  adjunto). Autores distintos para entrenamiento y prueba, con sus criterios cruzados para que las etiquetas no se
  contradigan.

### ¿La respuesta se apoya en el documento? {#apoyo}

- **Pregunta:** dado un texto, una pregunta sobre él y una respuesta, ¿todo lo que afirma la respuesta está en el texto?
- **Datos:** textos del BOE sin nombres de personas (disposiciones y anuncios de contratación). Por cada texto, un modelo
  local escribe una respuesta que solo usa el texto; después, esa respuesta se altera cambiando un solo dato o añadiendo
  una afirmación que el texto no contiene. La etiqueta se conoce por construcción, y cada texto aparece con su respuesta
  correcta y con la alterada. Comprobaciones automáticas: las cifras de la correcta están en el texto y la cifra nueva
  de la alterada no. 60 casos para entrenar el clásico y 194 para medir (tras excluir tres pares mal construidos; ver
  la sección 9 («Cambios al diseño y correcciones»)). Los textos del BOE no se publican: el conjunto se reconstruye con el script.
- **Quién escribe las respuestas:** Gemma 4 12B, un modelo que no se mide en la prueba ni es de la familia Qwen, en la
  que se basan Kev, Jeff y las réplicas de Jev. Así ningún modelo juzga textos escritos por él mismo o por un pariente.

### Los «conviene»: una prueba privada {#conviene}

- **Pregunta:** en un párrafo con «conviene», ¿da un consejo práctico al lector o solo anuncia o subraya lo que el texto
  va a decir? El segundo uso es uno de los tics de los textos generados por modelos de lenguaje.
- **Datos:** 100 casos de revisiones reales de textos propios, que no se publican; solo 17 son consejos prácticos.
- **Cómo:** validación cruzada en 5 partes (cada caso se mide con un modelo que no lo vio al ajustarse), Kev-0.8B con 160
  ejemplos generales de repaso y ritmo 4e-5, y el clasificador clásico con las mismas partes.
- **Límites:** es una prueba que nadie más puede repetir; se cita como indicio, no como resultado del toolkit.

# La nota de 1 a 10 {#nota}

Cada modelo recibe una nota por caso de uso, con reglas escritas antes de medir:

1. **Acierto medio por clase** (A) y acierto del azar (Z = 1 dividido entre el número de opciones).
2. **Nota de calidad** = 1 + 9 × (A − Z) / (1 − Z), limitada entre 1 y 10. Responder al azar da un 1; acertarlo todo,
   un 10.
3. **Penalización por falsa seguridad:** si falla más del 5 % de las respuestas dadas con un 90 % o más, se resta 1; si
   falla más del 10 %, se restan 2. Nunca por debajo de 1.
4. **Nota del caso:** la media de las notas de sus preguntas.

**Un ejemplo resuelto.** En la pregunta «¿qué es este correo?» hay 5 opciones, así que el azar acierta un 20 %. Un modelo
con un acierto medio por clase del 62 % saca 1 + 9 × (0,62 − 0,20) / (1 − 0,20) = 1 + 9 × 0,525 = 5,7. Si de sus
respuestas dadas con un 90 % o más fallara el 8 %, perdería un punto: 4,7.

**Cómo leerla.** La nota dice cómo rinde el modelo en esta prueba, no si hay que usarlo. Si el clasificador clásico saca
una nota igual o mayor, el modelo de decisión no está justificado en ese caso salvo por otra razón que habrá que decir,
como que las preguntas cambien a menudo o que no haya ejemplos etiquetados. El tiempo por decisión y la memoria van
aparte: no se mezclan con la nota.

# Cómo se miden los tiempos {#tiempos}

Los tiempos que guarda cada evaluación dependen de lo que hubiera en marcha a la vez, así que se miden aparte
(`casos/tiempos.py`): un modelo cada vez, sobre los mismos 30 correos del triaje (tres preguntas cada uno), tras dos de
calentamiento, y se da la mediana de segundos por correo. Antes de empezar, la máquina se deja en reposo hasta que el chip
baja de 50 °C, y antes de cada modelo, de 55 °C: con horas de carga seguida la GPU llegó a 98 °C, y un chip caliente
puede bajar su frecuencia y dar tiempos peores de los reales. Se usa la temperatura de los núcleos de CPU, que están en
el mismo chip, porque el sensor de la GPU no da lecturas válidas cuando la GPU está apagada (se lee con `macmon`). En los *embeddings* se cuenta también el cálculo del vector; en el
clasificador clásico, solo la predicción, porque se entrena una vez y en segundos.

# Qué no mide todo esto

- **Un solo equipo:** todo se ha medido en un Mac mini con M4 Pro y 24 GB. En otro equipo, los tiempos cambian.
- **Pocas pruebas por caso:** entre 60 y 400 casos por prueba. Los intervalos de confianza dicen cuánto pesa eso.
- **Datos sintéticos:** los casos de uso públicos son sintéticos, más limpios que los reales.
- **Sin ajustar, salvo donde se dice:** los casos de uso miden los modelos tal como se publican. Ajustarlos con datos
  propios cambiaría las notas, como enseñan el BOE y PAWS-X.
- **Un solo modo de preguntar por modelo:** otra redacción de la pregunta o de las opciones daría otras cifras.

# Cómo reproducirlo

El [README del repositorio](https://github.com/joakinen/toolkit-modelos-de-decision) explica cómo instalarlo y arrancar
los modelos. Después, en este orden:

```sh
# el BOE (descarga los textos, evalúa, ajusta y exporta)
python boe/construir.py && python boe/evaluar.py
KEV_DIR=/ruta/a/kev sh boe/ajustar.sh
python boe/clasico.py && python boe/clasico_curva.py
python boe/exportar.py && python boe/pagina.py

# PAWS-X
PAWSX_DATOS=<carpeta> python pawsx/construir.py && PAWSX_DATOS=<carpeta> python pawsx/clasico.py

# casos de uso
python casos/construir.py correo && python casos/construir.py expedientes
BOE_DATOS=<carpeta del BOE> python casos/apoyo/construir.py
python casos/evaluar.py correo    # y expedientes, apoyo
python casos/notas.py correo expedientes apoyo
```

# Cambios al diseño y correcciones {#cambios}

- **29 de septiembre de 2026.** En los expedientes, la pregunta sobre el representante se redactó con tres opciones
  (interesado, representante con autorización, representante sin ella) en lugar de «sí, no o no consta», que no
  encajaba cuando no hay representante. Se cambió antes de medir.
- **29 de septiembre de 2026.** Los tiempos por decisión que guardaron las primeras evaluaciones se descartaron: se
  midieron con varios modelos cargados a la vez (la máquina llegó a quedarse sin memoria) y con la GPU a 93-98 °C tras
  horas de carga. Se volvieron a medir aparte, un modelo cada vez y con el chip enfriado (ver la sección 6 («Cómo se miden los
  tiempos»)). Un primer intento de esa nueva medida también se descartó: esperaba a que bajara la temperatura de la GPU,
  pero con la GPU apagada su sensor devuelve un valor sin sentido (unos 2 °C), así que no hubo reposo; se repitió
  usando la temperatura de la CPU, del mismo chip. En la práctica, los tiempos con reposo y sin él apenas difieren (menos
  de un 5 %, salvo Jeff-0.8B, un 20 % más lento con reposo). Las notas y los aciertos no dependen de nada de esto.
- **29 de septiembre de 2026.** Revisión a mano del caso de respuestas apoyadas: en tres textos, la afirmación que se
  añadió para que la respuesta no se apoyara en el texto sí estaba en él. Se excluyeron esos tres pares y la prueba quedó
  en 194 casos. Se revisaron todas las respuestas con algo añadido que se parecía al texto, no solo aquellas en que los
  modelos fallaban, para no corregir las etiquetas a favor de los modelos.
- **29 de septiembre de 2026.** La primera versión del caso de respuestas apoyadas se construyó con Qwen3.5 9B, que
  también se medía: juzgaba respuestas escritas por él mismo, y además los demás modelos son de su misma familia. Se
  descartó entera y se reconstruyó con Gemma 4 12B, que no se mide; todas las notas de ese caso son de la segunda
  versión.
- **29 de septiembre de 2026.** En los expedientes, la pregunta de identidad decía «del solicitante», que es ambiguo
  cuando presenta un representante. Se vio al revisar los casos en que los dos mejores modelos coincidían contra la
  etiqueta. Se cambió a «del interesado (el titular del trámite, no su representante)», sin tocar las etiquetas, y se
  volvieron a medir todos los modelos; las notas con la redacción anterior se descartaron.
- **29 de septiembre de 2026.** El ajuste de Kev-0.8B con PAWS-X se hizo con los servidores de Kev del laboratorio en
  marcha: se intentaron parar para liberar memoria, pero el sistema los volvió a arrancar. Solo afecta al tiempo del
  ajuste, no a sus resultados.
- **28 de septiembre de 2026.** La primera versión del control de olvido usó 12 preguntas y concluyó que el ajuste no
  estropeaba nada; con 710 preguntas se vio que el modelo ajustado pierde la capacidad de dudar. El informe se corrigió.
