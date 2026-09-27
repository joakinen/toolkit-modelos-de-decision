# Modelos de decisión

Un **modelo de decisión** es un modelo de inteligencia artificial que no escribe. Recibe un texto, una pregunta cerrada y
una lista de respuestas posibles, y devuelve **una probabilidad para cada respuesta**:

> **Texto:** «El interesado presentó la solicitud el 15 de enero, pero no consta el pago de la tasa.»
> **Pregunta:** ¿Está la solicitud completa?
> **Respuesta:** sí 3 % · no 91 % · no consta 6 %

No puede inventar una respuesta fuera de la lista, devuelve datos en lugar de texto y dice cuánta seguridad tiene. Por
eso sirve para clasificar, encaminar y comprobar documentos: el trabajo que hoy se hace a mano en un registro de entrada
o en una cola de expedientes.

Este repositorio reúne tres cosas para quien quiera entenderlos y probarlos, sobre todo en una administración:

| Carpeta | Qué contiene |
|---|---|
| [`informe/`](informe/) | Un informe introductorio: qué son, cómo se les pregunta, cómo se entrenan, usos posibles y límites ([PDF](informe/modelos-de-decision.pdf)) |
| [`laboratorio/`](laboratorio/) | Una web local para comparar varios modelos de decisión con los mismos casos |
| [`boe/`](boe/) | Una prueba con textos reales del BOE: construir los datos, evaluar, ajustar un modelo y medirlo |
| [`resultados/`](resultados/) y [`docs/`](docs/) | Los resultados de esa prueba (sin textos) y una página estática para verlos |

**Ver los resultados sin instalar nada:** <https://joakinen.github.io/modelos-de-decision/>

## El resultado principal

Pregunta: *¿en qué apartado del BOE se publica este texto?* Siete apartados, 350 textos de prueba (50 por apartado)
de julio y agosto de 2026, que el modelo ajustado nunca vio al entrenar.

| Modelo | Acierto medio por apartado |
|---|---|
| **Kev-0.8B ajustado con 1.400 textos del BOE** (200 por apartado) | **95 %** |
| Jev-style v1, 2.000 millones de parámetros, sin ajustar | 73 % |
| Kev-4B, sin ajustar | 69 % |
| Qwen3.5 9B, un modelo de chat general, sin ajustar | 66 % |
| Jev-style v3, 800 millones, sin ajustar | 64 % |
| Kev-0.8B, sin ajustar | 49 % |

Con unos cientos de ejemplos por opción, un modelo pequeño ajustado supera con claridad a modelos mucho mayores sin
ajustar: la mejora es de +45 puntos (intervalo de confianza del 95 %: +41 a +49). Sin ajustar, ningún modelo distingue
una disposición general de una «otra disposición»: es una convención del BOE que solo se aprende con ejemplos. Con pocos
datos, en cambio, el ajuste no sirve: en otra prueba con 17 ejemplos de la clase difícil, no se distinguió del azar.

Todo se ejecutó en un ordenador de sobremesa (Mac mini con M4 Pro y 24 GB), con modelos de pesos abiertos y sin enviar
nada fuera. El detalle está en el [informe](informe/modelos-de-decision.pdf) y en la [página de resultados](https://joakinen.github.io/modelos-de-decision/).

## Probar el laboratorio

El laboratorio es una web que hace de intermediaria entre tú y varios modelos que se ejecutan en tu máquina. Trae 12
casos de prueba (seis fáciles y seis con trampa), triajes de ejemplo y un formulario para hacer tus propias preguntas.

```sh
git clone https://github.com/joakinen/modelos-de-decision && cd modelos-de-decision
uv sync
cd laboratorio && uv run uvicorn app:app --host 127.0.0.1 --port 8090
```

Abre <http://127.0.0.1:8090>. Verás los resultados de referencia; para usar los modelos, arranca los que quieras (los
que no estén en marcha aparecen como parados y el resto funciona igual):

| Modelo | Cómo arrancarlo |
|---|---|
| Kev-0.8B y Kev-4B | En una copia de [Kev](https://github.com/jaredpalmer/kev) (probado en el commit `3d9973b`): `uv sync --extra serve` y después `uv run python -m kev.serve --run jaredpalmer/kev-0.8b --port 8008` (y `kev-4b` en el 8009) |
| Jev-style v1 · 2B | Con [Ollama](https://ollama.com): `ollama pull hf.co/chaoliangUNSW/Jev-Style-Qwen3.5-2B-Decision-GGUF:Q8_0` |
| Qwen3.5 · 9B | Con Ollama: `ollama pull qwen3.5:9b` |
| Jev-style v3 · 0.8B | Necesita compilar `jev-score` contra llama.cpp ([ficha del modelo](https://huggingface.co/chaoliangUNSW/Jev-Style-0.8B-Decision-v3-GGUF)); indica su carpeta en `JEV_V3_DIR` |

Los puertos y direcciones se cambian con variables de entorno; están al principio de [`laboratorio/app.py`](laboratorio/app.py).
El laboratorio escucha solo en tu máquina.

## Repetir la prueba del BOE

Los textos no se publican aquí, porque algunos contienen nombres de personas. Se descargan de la API de datos abiertos
del BOE con [`boe/construir.py`](boe/construir.py), a una petición por segundo y con caché:

```sh
cd boe
uv run python construir.py sumarios        # sumarios de enero a agosto de 2026
uv run python construir.py prueba          # 350 textos de julio y agosto  -> prueba.jsonl
uv run python construir.py entrenamiento   # 1.400 textos de enero a junio -> entrenamiento.jsonl
uv run python control.py                   # 12 preguntas ajenas al BOE, para ver si el ajuste hace olvidar
uv run python evaluar.py                   # los modelos del laboratorio, sin ajustar
KEV_DIR=/ruta/a/kev sh ajustar.sh          # ajusta y evalúa Kev-0.8B y Kev-4B (horas; ver el script)
uv run python exportar.py && uv run python pagina.py   # resultados/boe.json y docs/index.html
```

Las reglas del conjunto (periodos, recorte a 2.000 caracteres, un máximo de tres textos casi idénticos, sin título) están
explicadas al principio de `construir.py` y se fijaron antes de medir ningún modelo.

## Cuidados

- **Datos personales.** Los textos del BOE son públicos, pero su reutilización debe respetar la protección de datos. No
  publiques el conjunto descargado ni un modelo ajustado con él.
- **Condiciones del BOE.** La reutilización está permitida citando la fuente, sin alterar el sentido de la información y
  sin sugerir que el BOE respalda el uso. Consulta el [aviso legal](https://www.boe.es/informacion/aviso_legal/index.php).
- **Decisiones con efectos sobre personas.** Estos modelos sirven como apoyo a la tramitación. El artículo 22 del RGPD y
  el artículo 41 de la Ley 40/2015 limitan las decisiones puramente automatizadas; el informe lo explica.
- **Una sola prueba no es una evaluación general.** Los resultados valen para esta pregunta, estos periodos y estos
  modelos. Mídelos siempre con tus propios casos.

## Créditos y licencias

- Código: [Apache-2.0](LICENSE). Informe y resultados: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.es).
- Datos: Agencia Estatal Boletín Oficial del Estado ([boe.es](https://www.boe.es)), datos abiertos.
- Modelos: [Kev](https://github.com/jaredpalmer/kev) de Jared Palmer; Jev-style de [chaoliangUNSW](https://huggingface.co/chaoliangUNSW);
  Qwen3.5 de Alibaba. La idea de convertir un modelo de chat en uno de decisión leyendo la probabilidad de cada letra
  viene de [este artículo de allanrbo](https://allanrbo.blogspot.com/2026/09/a-jev-like-wrapper-for-llms-including.html).
- Jev es un modelo cerrado de TypeSafe AI; este repositorio no está afiliado a TypeSafe.

Joaquín Herrero, asistido por Claude Opus 5.5.
