# Casos de uso: diseño de las pruebas y de la puntuación

Fijado el 29 de septiembre de 2026, **antes de medir ningún modelo** con estos casos. Si algo cambia después de ver
resultados, se anota al final, en «Cambios al diseño», con la fecha y el motivo.

## Para qué

La prueba del BOE mide una pregunta que se resuelve por el vocabulario, y ahí un clasificador clásico basta
(`boe/clasico_curva.py`). PAWS-X mide una pregunta de significado. Estos tres casos acercan la medida a usos reales en
una administración y dan a cada modelo una **nota de 1 a 10 por caso**, siempre al lado del clasificador clásico.

## Los tres casos

### 1. Triaje del buzón general (`correo/`)

Correos que llegan al buzón general de un ayuntamiento ficticio, el «Ayuntamiento de Villanueva del Ejemplo» (un nombre
inventado a propósito: no debe coincidir con ningún municipio real). Tres preguntas sobre
cada correo:

| Pregunta | Tipo | Opciones |
|---|---|---|
| ¿A qué unidad corresponde? | choice | Atención ciudadana y registro · Tributos y recaudación · Urbanismo y obras · Servicios sociales · Recursos humanos · Contratación · Sede electrónica e informática · Ninguna (no es competencia municipal, o es publicidad) |
| ¿Qué es? | choice | Solicitud de información · Trámite o solicitud · Queja o reclamación · Respuesta a un requerimiento · Publicidad o correo no deseado |
| ¿Es urgente? | noul | Urgente: hay un plazo que vence en menos de una semana, un riesgo para personas o un servicio caído |

**Vía doble:**

- **Pública:** correos sintéticos, escritos para la prueba y revisados. 20 por unidad para entrenar el clasificador
  clásico (160) y 15 por unidad para medir (120). Deliberadamente, al menos un tercio de los de prueba son difíciles:
  temas mezclados, lenguaje informal o con faltas, hilos reenviados, la palabra clave de otra unidad («el recibo de la
  obra»), plazos implícitos. Se publican con licencia CC BY-SA 4.0.
- **Privada:** correos reales de un buzón general, anonimizados en local, con las mismas tres preguntas y las
  etiquetas que ponga una persona que conozca el buzón. No salen de la máquina ni se publican: solo las cifras
  agregadas. El formato está en `correo/privado/LEEME.md`.

### 2. Completitud de un expediente (`expedientes/`)

Resúmenes sintéticos de solicitudes (licencias de obra menor, ayudas, certificados) tal como los vería quien revisa
un expediente: qué dice la solicitud y qué documentos se han aportado. Cuatro preguntas sobre cada uno:

| Pregunta | Opciones |
|---|---|
| ¿Consta el pago de la tasa? | sí · no · no consta |
| ¿Está firmada la solicitud? | sí · no · no consta |
| ¿Se aporta el documento de identidad del interesado (el titular del trámite, no su representante)? | sí · no · no consta |
| ¿Quién presenta la solicitud? | el interesado en nombre propio · un representante con autorización aportada · un representante sin autorización aportada |

Trampas deliberadas: «el pago se hará en ventanilla», «adjunta justificante de otra tasa», «firma pendiente», «DNI
caducado», negaciones y documentos citados pero no adjuntos. 40 expedientes para entrenar el clásico y 60 para medir
(240 preguntas). Públicos, CC BY-SA 4.0.

### 3. ¿La respuesta se apoya en el documento? (`apoyo/`)

Un texto del BOE (disposiciones y anuncios de contratación, sin nombres de personas), una pregunta sobre él y una
respuesta. Pregunta noul: **¿Todo lo que afirma la respuesta está en el texto?**

Las respuestas se construyen para que la etiqueta se conozca por construcción: la correcta la redacta un modelo local
(Gemma 4 12B; ver «Cambios al diseño») con la instrucción de ceñirse al texto y se revisa; la incorrecta es esa misma respuesta con **un solo
dato cambiado** (una fecha, un importe, un plazo, un organismo) o con una afirmación añadida que el texto no contiene.
Mitad y mitad. 60 para entrenar el clásico y 200 para medir. Los textos del BOE no se publican (como en `boe/`): el
script los descarga y construye el conjunto.

## Modelos

Kev-0.8B, Kev-4B, Jeff-0.8B, Jeff-2B, Jev-style v1 (2B), Jev-style v3 (0.8B) y Qwen3.5 9B (letras), todos sin ajustar, y
el **clasificador clásico** (TF-IDF y regresión logística; en el caso 3, con los rasgos de par de `pawsx/clasico.py`)
entrenado con la parte de entrenamiento de cada caso.

## Nota de 1 a 10

Por cada modelo, caso y pregunta:

1. **Acierto medio por clase** (A) y acierto del azar (Z = 1 / número de opciones).
2. **Nota de calidad** = 1 + 9 × (A − Z) / (1 − Z), redondeada a una cifra y limitada entre 1 y 10. Azar = 1; acertarlo
   todo = 10.
3. **Penalización por falsa seguridad:** de las respuestas dadas con un 90 % o más, si falla más del 5 %, se resta 1;
   si falla más del 10 %, se restan 2. Nunca por debajo de 1.
4. **Nota del caso** = media de las notas de sus preguntas.

Se publica siempre con el número de ejemplos y el intervalo de confianza del 95 % del acierto (bootstrap, 2.000
remuestreos, semilla 0). El tiempo por decisión y la memoria van en columnas aparte, sin mezclarse con la nota.

**Cómo leerla:** la nota dice cómo rinde el modelo en esta prueba, no si hay que usarlo. Si el clasificador clásico
saca una nota igual o mayor, el modelo de decisión no está justificado en ese caso salvo por otra razón (preguntas que
cambian, falta de ejemplos etiquetados) que habrá que decir.

## Cambios al diseño

- **29-sep-2026, antes de medir:** la cuarta pregunta de expedientes pasa de «sí · no · no consta» a tres opciones sobre
  quién presenta la solicitud, porque la primera redacción no encajaba cuando no hay representante.
- **29-sep-2026, antes de medirla:** se añade una cuarta referencia además del clasificador clásico: *embeddings*
  (bge-m3) con regresión logística (`embeddings.py`), el punto intermedio entre un clasificador que solo ve palabras y
  un modelo de decisión.
- **29-sep-2026, después de medir:** la pregunta de identidad decía «del solicitante», que es ambiguo cuando presenta un
  representante: los autores de los datos entendieron el titular y los modelos, quien presenta. Se detectó al revisar
  los casos en que los dos mejores modelos coincidían contra la etiqueta (exp-p-038, 048 y 052: se aporta el DNI del
  titular y los modelos responden «no consta»). Las etiquetas no cambian; cambia la redacción de la pregunta, a «del
  interesado (el titular del trámite, no su representante)», y se vuelven a medir todos los modelos en expedientes. Las
  notas medidas con la redacción anterior se descartan.
- **29-sep-2026, después de medir:** el caso 3 se había construido con Qwen3.5 9B, que también se medía, así que
  juzgaba respuestas escritas por él mismo; y Kev, Jeff y las réplicas de Jev son de la misma familia Qwen. Se descarta
  esa versión entera (queda en local, sin publicar) y se reconstruye con Gemma 4 12B, que no se mide ni es de la
  familia. Mismo script, mismas comprobaciones y mismos tamaños.
- **29-sep-2026, después de medir:** revisión a mano del caso 3. Se leyeron todos los casos en que los dos mejores
  modelos coincidían contra la etiqueta y, para no revisar solo donde fallan los modelos, todas las respuestas con una
  afirmación añadida cuyo contenido aparecía en el texto. En tres textos de la prueba, lo añadido sí estaba en el texto:
  se excluyen esos tres pares (`casos/apoyo/revision.py`), y la prueba queda en 194 casos. En el entrenamiento no se
  encontró ninguno.
