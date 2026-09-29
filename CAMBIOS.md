# Cambios

Cada versión publicada del informe y de la página de resultados, de la más reciente a la más antigua.

**La versión sale de aquí.** El primer encabezado `## X.Y · fecha` es la versión vigente: lo leen `informe/generar.sh`
(portada, pie de página y créditos del PDF) y `boe/pagina.py` (página de resultados). No hay que escribirla en ningún
otro sitio.

**Numeración.** Sube la primera cifra cuando cambia el veredicto provisional o la conclusión principal del informe; sube
la segunda con cada modelo o prueba nuevos y con las correcciones. Cada versión publicada lleva su etiqueta de git
(`v1.0`, `v1.1`…), así que cualquier versión anterior se puede recuperar.

**Para publicar una versión:**

1. Añadir aquí la entrada nueva, arriba del todo, con el número, la fecha y qué cambia.
2. `sh informe/generar.sh` (PDF) y `python boe/pagina.py` (página); revisar los dos.
3. Commit, etiqueta `git tag vX.Y` y `git push --follow-tags`.
4. En creativecodeworks.com: copiar el PDF a `web/static/`, poner la versión y la fecha en
   `web/toolkit-modelos-de-decision.html` y desplegar la página y el PDF.
5. Avisar a la lista del toolkit en MailerLite.

## 2.0 · 29 de septiembre de 2026

Cambia la conclusión principal, por eso sube la primera cifra.

- **La caja de herramientas escalonada.** El informe ya no compara solo modelos de decisión: propone elegir entre cinco
  herramientas, de la más barata a la más cara (reglas, clasificador clásico, *embeddings* con clasificador, modelo de
  decisión y modelo de lenguaje), y subir solo cuando la de abajo no llega. Figura nueva, reutilizable con CC BY-SA 4.0.
- **Dos referencias nuevas en todas las pruebas:** un clasificador clásico (TF-IDF y regresión logística) y *embeddings*
  (bge-m3) con clasificador. En el BOE, el clásico entrenado en 9 segundos iguala a los modelos ajustados durante horas.
- **Modelos nuevos:** Jeff-0.8B y Jeff-2B.
- **Pruebas nuevas:** PAWS-X en español (una pregunta de significado, con un ajuste de Kev-0.8B con 200 pares) y tres
  casos de uso con nota de 1 a 10: triaje del buzón general, completitud de expedientes y respuestas apoyadas en un
  documento. Diseño fijado antes de medir en `casos/DISENO.md`, con los cambios posteriores anotados.
- **Veredicto provisional nuevo:** para preguntas de significado, los modelos de decisión de 2.000 a 4.000 millones ya
  son útiles con revisión humana; para preguntas de vocabulario, basta un clasificador clásico.
- **Informe reorganizado** en cinco partes, con una página inicial «En cinco minutos». La metodología pasa a una página
  aparte (`docs/metodologia.html`), y la de resultados muestra los casos de uso, PAWS-X y la ficha técnica de cada modelo.
- **Versionado:** portada, pie de página, créditos y páginas web muestran la versión de este fichero.
- **Correcciones:** el laboratorio no podía usar Jev-style v3 sin instalar `tokenizers` (nuevo extra `jev-v3`); el
  informe explica ahora por qué se eligió la prueba de los «conviene».

## 1.0 · 28 de septiembre de 2026

Primera versión publicada. Prueba del BOE (350 textos, siete apartados) con Kev-0.8B y Kev-4B, ajustados y sin ajustar,
las réplicas abiertas de Jev de 800 y 2.000 millones de parámetros y Qwen3.5 9B como referencia; control de olvido en
inglés y en español; recalibración. Veredicto provisional: usables para clasificar y encaminar con revisión humana si se
ajustan con cientos de ejemplos por opción y se recalibran.
