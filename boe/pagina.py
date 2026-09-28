"""Genera docs/index.html: una página estática con los resultados de la prueba del BOE, para GitHub Pages.

No necesita servidor ni modelos: lleva dentro resultados/boe.json, los estilos de laboratorio/index.html y el mismo
laboratorio/boe.js que usa la pestaña BOE, así que las dos muestran siempre lo mismo.
Uso: python pagina.py   (después de exportar.py)
"""
import html, json, re
from pathlib import Path

RAIZ = Path(__file__).parent.parent
datos = json.loads((RAIZ / "resultados" / "boe.json").read_text())
estilos = re.search(r"<style>(.*?)</style>", (RAIZ / "laboratorio" / "index.html").read_text(), re.S).group(1)
boe_js = (RAIZ / "laboratorio" / "boe.js").read_text()

pagina = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Modelos de decisión: resultados</title>
<meta name="description" content="Qué son los modelos de decisión y cómo rinden, con y sin ajuste, al clasificar textos del BOE.">
<style>{estilos}</style>
</head>
<body>
<header>
  <h1>Modelos de decisión</h1>
  <p class="sub">Un modelo de decisión lee un texto, recibe una pregunta con opciones cerradas y devuelve una probabilidad
  para cada opción. No escribe: elige. Esta página muestra cómo rinden varios de estos modelos, todos abiertos y ejecutados
  en un ordenador de sobremesa, al clasificar textos reales del BOE.</p>
  <p class="sub"><a href="modelos-de-decision.pdf">Informe: modelos de decisión y ajuste fino, para programadores (PDF)</a> ·
  <a href="https://github.com/joakinen/toolkit-modelos-de-decision">Código y cómo reproducirlo</a></p>
</header>
<main>
<section id="boe">
  <h2>{html.escape(datos["pregunta"])}</h2>
  <p class="sub">{datos["n"]} textos del BOE de {html.escape(datos["periodo_prueba"])}, {datos["n"] // len(datos["apartados"])} por apartado. Al modelo se
  le da el cuerpo del texto, sin título. La respuesta correcta es la sección en que lo publicó el propio BOE. Los modelos
  ajustados se entrenaron con textos de {html.escape(datos["periodo_entrenamiento"])}, sin ver nunca el periodo de prueba.
  El log-loss mide cómo reparte el modelo la probabilidad: cuanto más bajo, mejor.</p>
  <div class="score" id="boe-marcador"></div>
  <h2>Qué dice</h2>
  <div class="card" id="boe-lectura"></div>
  <h2>Acierto por apartado</h2>
  <p class="sub">Aciertos sobre {datos["n"] // len(datos["apartados"])} en cada apartado. En verde, el mejor de cada fila.</p>
  <div class="card scroll"><table class="matrix" id="boe-tabla"></table></div>
  <h2>Dónde se equivoca cada uno</h2>
  <div class="card scroll"><table class="matrix" id="boe-confusiones"></table></div>
  <h2>Cuánto cuesta el ajuste</h2>
  <p class="sub">Medido por el propio entrenador de Kev. Antes hay que descargar los textos: los 1.400 de entrenamiento tardaron unos 27 minutos, a una petición por segundo.</p>
  <div class="card scroll" id="boe-ajuste"></div>
  <h2>Control: ¿olvida lo que ya sabía?</h2>
  <p class="sub">Preguntas ajenas al BOE, antes y después del ajuste: 560 en inglés (las 12 pruebas y 440 del conjunto de prueba con el que se publica Kev: noticias, reseñas, consultas, inferencia…) y 150 en español (XNLI, PAWS-X y reseñas de Amazon). Se mira si acierta lo mismo y si su seguridad sigue siendo de fiar: de las respuestas que da con un 90 % o más, cuántas fallan.</p>
  <div class="card scroll" id="boe-olvido"></div>
  <p class="sub">Las 12 pruebas del laboratorio, por separado: <span id="boe-control"></span></p>
  <h2>Recalibración</h2>
  <p class="sub">El ajuste deja al modelo demasiado seguro. Se corrige con una temperatura, un número que suaviza las probabilidades sin cambiar la respuesta, ajustada con 400 casos que no se usan para nada más: 140 textos del BOE de septiembre, 200 generales y 60 en español. En el 4B se escribió en el modelo; en el 0.8B no, porque una sola temperatura no le basta.</p>
  <div class="card scroll" id="boe-calibracion"></div>
  <p class="sub">Fuente de los datos: {html.escape(datos["fuente"])}. Textos y resultados de esta página:
  <a href="https://creativecommons.org/licenses/by-sa/4.0/deed.es">CC BY-SA 4.0</a>.</p>
</section>
</main>
<script>{boe_js}
pintarBoe({json.dumps(datos, ensure_ascii=False)});
</script>
</body>
</html>
"""
(RAIZ / "docs").mkdir(exist_ok=True)
(RAIZ / "docs" / "index.html").write_text(pagina)
print(RAIZ / "docs" / "index.html", len(pagina) // 1024, "KB")
