"""Genera docs/index.html (resultados) y docs/metodologia.html (cómo se ha medido), páginas estáticas para GitHub Pages.

No necesita servidor ni modelos: lleva dentro resultados/boe.json, los estilos de laboratorio/index.html y el mismo
laboratorio/boe.js que usa la pestaña BOE, así que las dos muestran siempre lo mismo. La tabla «Modelos probados» sale
de la lista de modelos del laboratorio (laboratorio/app.py), con el enlace a la ficha de cada uno. La metodología se
escribe en informe/metodologia.md y se convierte con pandoc.
La versión y la fecha salen del primer «## X.Y · fecha» de CAMBIOS.md, igual que en el PDF (informe/generar.sh).
Uso: python pagina.py   (después de exportar.py)
"""
import html, json, re, subprocess, sys, tempfile
from pathlib import Path

RAIZ = Path(__file__).parent.parent
datos = json.loads((RAIZ / "resultados" / "boe.json").read_text())
estilos = re.search(r"<style>(.*?)</style>", (RAIZ / "laboratorio" / "index.html").read_text(), re.S).group(1)
boe_js = (RAIZ / "laboratorio" / "boe.js").read_text()
version, fecha = re.search(r"^## ([0-9.]+) · (.+)$", (RAIZ / "CAMBIOS.md").read_text(), re.M).groups()
CAMBIOS = "https://github.com/joakinen/toolkit-modelos-de-decision/blob/main/CAMBIOS.md"
sys.path.insert(0, str(RAIZ / "laboratorio"))
from app import MODELOS  # noqa: E402

# Los que no están en el laboratorio: los ajustados en estas pruebas y la referencia clásica.
OTROS = [
    {"nombre": "Kev · 0.8B y 4B ajustados", "autor": "ajustados aquí a partir de Kev", "fuente": "https://huggingface.co/jaredpalmer/kev-0.8b",
     "motor": "Entrenador de Kev (LoRA de rango 16), en el mismo Mac mini"},
    {"nombre": "Clasificador clásico", "autor": "scikit-learn", "fuente": "https://scikit-learn.org/stable/modules/linear_model.html#logistic-regression",
     "motor": "TF-IDF y regresión logística, en la CPU; se entrena en segundos"},
]
# Casos de uso y PAWS-X: tablas estáticas a partir de resultados/casos.json y resultados/pawsx.json (casos/exportar.py).
leer_json = lambda n: json.loads((RAIZ / "resultados" / n).read_text()) if (RAIZ / "resultados" / n).exists() else {}
coma = lambda x, d=1: f"{x:.{d}f}".replace(".", ",")
BANDEJAS = {2: "2 · clásico", 3: "3 · embeddings", 4: "4 · decisión", 5: "5 · lenguaje"}
ANCLA = {"correo": "correo", "expedientes": "expedientes", "apoyo": "apoyo"}   # identificadores de informe/metodologia.md


def tabla_caso(clave, caso):
    qs = caso["preguntas"]
    cab = "<tr><th>Herramienta</th><th>Bandeja</th><th>Nota</th>" + "".join(f"<th>{html.escape(v)}</th>" for v in qs.values()) + "</tr>"
    mejor = {q: max(m["preguntas"][q]["nota"] for m in caso["modelos"]) for q in qs}
    filas = []
    for m in caso["modelos"]:
        celdas = "".join(f'<td class="{"ok" if m["preguntas"][q]["nota"] == mejor[q] else ""}" title="acierto {coma(m["preguntas"][q]["acierto"] * 100, 0)} %">'
                         f'{coma(m["preguntas"][q]["nota"])}{" ·" * (m["preguntas"][q]["fallo_seguras"] > 0.05)}</td>' for q in qs)
        filas.append(f'<tr><td>{html.escape(m["nombre"])}</td><td>{BANDEJAS[m["escalon"]]}</td><td><b>{coma(m["nota"])}</b></td>{celdas}</tr>')
    return (f'<h3>{html.escape(caso["titulo"])}</h3><p class="sub">{caso["n"]} casos de prueba · '
            f'<a href="metodologia.html#{ANCLA[clave]}">cómo se midió</a></p>'
            f'<div class="card scroll"><table class="matrix">{cab}{"".join(filas)}</table></div>')


casos_json, pawsx_json = leer_json("casos.json"), leer_json("pawsx.json")
bloque_casos = "".join(tabla_caso(k, v) for k, v in casos_json.items())
filas_pawsx = []
orden_pawsx = lambda m: max(x["media"] for x in m["curva"]) if "curva" in m else m["acierto"]
for m in sorted(pawsx_json.get("modelos", []), key=orden_pawsx):
    if "curva" in m:
        a = [x["media"] for x in m["curva"]]
        acierto, ejemplos = f"{coma(min(a) * 100, 0)} % a {coma(max(a) * 100, 0)} %", "50 a 5.000"
    else:
        acierto = f'{coma(m["acierto"] * 100, 0)} % <small>({coma(m["ic95"][0] * 100, 0)} a {coma(m["ic95"][1] * 100, 0)})</small>'
        ejemplos = "200" if m["ejemplos"] else ("ninguno" if not m["id"].startswith("jeff") else "ver nota")
    filas_pawsx.append(f'<tr><td>{html.escape(m["nombre"])}</td><td>{BANDEJAS[m["escalon"]]}</td><td>{ejemplos}</td><td>{acierto}</td></tr>')
bloque_pawsx = ('<div class="card scroll"><table class="matrix"><tr><th>Herramienta</th><th>Bandeja</th><th>Ejemplos de la tarea</th>'
                '<th>Acierto medio (IC 95 %)</th></tr>' + "".join(filas_pawsx) + "</table></div>")

tiempos = leer_json("tiempos.json")
NOMBRE_T = {"clasico": "Clasificador clásico", "embeddings": "Embeddings y clasificador", "kev-08b": "Kev · 0.8B", "kev-4b": "Kev · 4B",
            "jeff-08b": "Jeff · 0.8B", "jeff-2b": "Jeff · 2B", "jev-v1": "Jev-style v1 · 2B", "jev-v3": "Jev-style v3 · 0.8B",
            "llm-9b": "Qwen3.5 · 9B (letras)"}
BANDEJA_T = {"clasico": 2, "embeddings": 3, "llm-9b": 5}
bloque_tiempos = ('<div class="card scroll"><table class="matrix"><tr><th>Herramienta</th><th>Bandeja</th><th>Segundos por correo</th></tr>'
                  + "".join(f'<tr><td>{NOMBRE_T[k]}</td><td>{BANDEJAS[BANDEJA_T.get(k, 4)]}</td><td>{"&lt; 0,01" if v["segundos_por_correo"] < 0.01 else coma(v["segundos_por_correo"], 2)}</td></tr>'
                            for k, v in sorted(tiempos.items(), key=lambda x: x[1]["segundos_por_correo"])) + "</table></div>")

filas_modelos = "\n".join(
    f'<tr><td>{html.escape(m["nombre"])}</td><td>{html.escape(m["autor"])}</td><td>{html.escape(m["motor"])}</td>'
    f'<td><a href="{html.escape(m["fuente"])}">ficha</a></td></tr>' for m in MODELOS + OTROS)

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
  para cada opción. No escribe: elige. Esta página compara varios de estos modelos, todos abiertos y ejecutados en un
  ordenador de sobremesa, con dos referencias sin modelo de lenguaje (un clasificador clásico y <i>embeddings</i>) y un
  modelo de chat general, en cinco pruebas en español: tres casos de uso, una pregunta de significado y una de vocabulario.</p>
  <p class="sub"><a href="modelos-de-decision.pdf">Informe: modelos de decisión y ajuste fino, para programadores (PDF)</a> ·
  <a href="https://github.com/joakinen/toolkit-modelos-de-decision">Código y cómo reproducirlo</a></p>
  <p class="sub">Versión {version} · {html.escape(fecha)} · <a href="metodologia.html">Cómo se ha medido</a> ·
  <a href="{CAMBIOS}">Qué cambia en cada versión</a></p>
</header>
<main>
<section id="caja">
  <h2>La caja de herramientas escalonada</h2>
  <p class="sub">Para responder una pregunta cerrada sobre un texto hay cinco herramientas, de la más barata a la más cara.
  Se empieza por abajo y se sube a la bandeja siguiente solo cuando la de abajo no llega, midiéndolo.
  La figura se puede reutilizar citando la fuente (CC BY-SA 4.0).</p>
  <div class="card"><img src="caja-escalonada.svg" alt="Una caja de herramientas abierta con cinco bandejas escalonadas, de abajo arriba: reglas, clasificador clásico, embeddings con clasificador, modelo de decisión y modelo de lenguaje. Cada bandeja cuesta más y entiende más." style="width:100%;height:auto"></div>
</section>
<section id="casos">
  <h2>Casos de uso: nota de 1 a 10</h2>
  <p class="sub">1 es acertar como el azar y 10, acertarlo todo. Un punto (·) tras la nota indica que el modelo falla más del 5 % de las
  respuestas que da con un 90 % de seguridad o más, y ha perdido puntos por ello. Pasa el ratón por una nota para ver el acierto.
  <a href="metodologia.html#nota">Cómo se calcula</a>. Datos sintéticos, en español.</p>
  {bloque_casos}
  <h3>Cuánto tarda cada uno</h3>
  <p class="sub">Mediana de segundos por correo del triaje (tres preguntas), un modelo cada vez y con la máquina en reposo.
  <a href="metodologia.html#tiempos">Cómo se midió</a>.</p>
  {bloque_tiempos}
</section>
<section id="pawsx">
  <h2>Una pregunta de significado: PAWS-X</h2>
  <p class="sub">¿Significan lo mismo estas dos oraciones? Pares con casi las mismas palabras que unas veces dicen lo mismo y otras
  no, hechos para que fallen los métodos que miran qué palabras hay. 400 pares en español; el azar es el 50 %. Jeff se entrenó con
  la versión inglesa de estos pares: su resultado no es el de un modelo que ve la tarea por primera vez.
  <a href="metodologia.html#pawsx">Cómo se midió</a>.</p>
  {bloque_pawsx}
</section>
<section id="boe">
  <h2>Una pregunta de vocabulario: {html.escape(datos["pregunta"])}</h2>
  <p class="sub"><a href="metodologia.html#boe">Cómo se midió</a></p>
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
  <h2>Modelos probados</h2>
  <p class="sub">Todos de pesos abiertos y ejecutados en la misma máquina. Cómo se le pregunta a cada uno:
  <a href="metodologia.html#cómo-se-le-pregunta-a-cada-modelo">metodología</a>.</p>
  <div class="card scroll"><table class="matrix"><tr><th>Modelo</th><th>Autor</th><th>Cómo se ejecuta</th><th>Ficha técnica</th></tr>
  {filas_modelos}</table></div>
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

# La metodología: el cuerpo lo convierte pandoc (con enlaces a las secciones) y se envuelve con los mismos estilos.
with tempfile.NamedTemporaryFile("w", suffix=".html") as plantilla:   # solo el índice y el cuerpo, sin cabecera
    plantilla.write("$toc$<!--fin-indice-->$body$"); plantilla.flush()
    subprocess.run([sys.executable, str(RAIZ / "informe" / "comprobar_referencias.py"), str(RAIZ / "informe" / "metodologia.md")], check=True)
    cuerpo = subprocess.run(["pandoc", str(RAIZ / "informe" / "metodologia.md"), "-t", "html", "--toc", "--toc-depth=2", "--number-sections",
                             "--template", plantilla.name], capture_output=True, text=True, check=True).stdout
indice, cuerpo = cuerpo.split("<!--fin-indice-->")
entrada, cuerpo = cuerpo.split("<h1", 1)   # el párrafo de presentación va antes del índice
cuerpo = "<h1" + cuerpo
metodologia = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Modelos de decisión: metodología</title>
<meta name="description" content="Cómo se han medido los modelos de decisión del toolkit: datos, métricas, pruebas y nota de 1 a 10.">
<style>{estilos}
.metodo {{max-width: 52rem}} .metodo h1 {{font-size: 1.35rem; margin-top: 2.2rem}} .metodo h2 {{font-size: 1.1rem}}
.metodo h3 {{font-size: 1rem}} .metodo li {{margin: .3rem 0}} .metodo pre {{overflow-x: auto}}
</style>
</head>
<body>
<header>
  <h1>Cómo se ha medido</h1>
  <p class="sub"><a href="index.html">Resultados</a> · <a href="modelos-de-decision.pdf">Informe (PDF)</a> ·
  <a href="https://github.com/joakinen/toolkit-modelos-de-decision">Código</a></p>
  <p class="sub">Versión {version} · {html.escape(fecha)} · <a href="{CAMBIOS}">Qué cambia en cada versión</a></p>
</header>
<main class="metodo">
{entrada}
<nav class="card">{indice}</nav>
{cuerpo}
<p class="sub">Textos de esta página: <a href="https://creativecommons.org/licenses/by-sa/4.0/deed.es">CC BY-SA 4.0</a>.</p>
</main>
</body>
</html>
"""
(RAIZ / "docs" / "metodologia.html").write_text(metodologia)
print(RAIZ / "docs" / "metodologia.html", len(metodologia) // 1024, "KB")
