"""Dibuja docs/caja-escalonada.svg: la caja de herramientas escalonada, cinco escalones con la misma geometría.

El dibujo es una caja de herramientas que se abre en bandejas escalonadas; en el texto, cada nivel se llama «escalón».
La versión en PDF para el informe (informe/caja-escalonada.pdf) se saca de este SVG imprimiéndolo con un navegador.
Uso: python informe/caja_escalonada.py
"""
from pathlib import Path
W, H = 1000, 725
X0, ANCHO, PASO_X, PASO_Y, ALTO = 40, 176, 184, 80, 176
T1 = 470                       # parte de arriba del escalón 1 (el cuerpo de la caja)
EJE_Y = T1 + ALTO + 26
B = [  # nombre (líneas), qué entiende, datos (2 líneas), ejemplos (2 líneas)
    (["Reglas"], "Lo mecánico", ["Sin ejemplos", "· instantáneo"], ["¿Hay un NIF?", "¿Una fecha?"]),
    (["Clasificador", "clásico"], "Palabras", ["Decenas o cientos de", "ejemplos · milésimas"], ["¿En qué sección del", "BOE? ¿A qué unidad?"]),
    (["Embeddings", "+ clasificador"], "Algo de significado", ["Ejemplos etiquetados", "· décimas de segundo"], ["Cuando las palabras", "casi bastan"]),
    (["Modelo de", "decisión"], "Significado", ["Sin ejemplos para empezar;", "se ajusta · 0,2 a 1,5 s"], ["¿Es urgente? ¿Consta", "el pago?"]),
    (["Modelo de", "lenguaje"], "Significado y redacción", ["Sin ejemplos · segundos,", "más memoria"], ["Redactar, resumir,", "explicar"]),
]
o = []
w = o.append
w(f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Helvetica Neue, Helvetica, Arial, sans-serif" role="img" aria-labelledby="t d">
  <title id="t">La caja de herramientas escalonada</title>
  <desc id="d">Una caja de herramientas escalonada con cinco escalones, de abajo arriba: reglas, clasificador clásico, embeddings con clasificador, modelo de decisión y modelo de lenguaje. Cada escalón cuesta más y entiende más. Se sube al siguiente solo si el de abajo no llega. Obra de Joaquín Herrero Pintado, licencia CC BY-SA 4.0.</desc>
  <style>
    .fondo {{ fill: #ffffff; }}
    .bandeja {{ fill: #f3f6ec; stroke: #8cb724; stroke-width: 2; }}
    .cuerpo {{ fill: #e6efd2; stroke: #6f9a18; stroke-width: 2.5; }}
    .suelo {{ fill: #dfe8c9; }}
    .borde {{ stroke: #8cb724; stroke-width: 5; stroke-linecap: round; }}
    .asa {{ fill: none; stroke: #6f9a18; stroke-width: 6; stroke-linecap: round; }}
    .brazo {{ stroke: #a4acb5; stroke-width: 7; stroke-linecap: round; }}
    .pivote {{ fill: #ffffff; stroke: #7a838e; stroke-width: 2; }}
    .num {{ fill: #6f9a18; font-size: 12px; font-weight: 700; letter-spacing: 1.5px; }}
    .nom {{ fill: #15171c; font-size: 17px; font-weight: 700; }}
    .ent {{ fill: #3d6b0f; font-size: 13.5px; font-style: italic; }}
    .dato {{ fill: #3a3f48; font-size: 12.5px; }}
    .ej {{ fill: #6b7280; font-size: 12px; }}
    .titulo {{ fill: #15171c; font-size: 26px; font-weight: 700; }}
    .sub {{ fill: #3a3f48; font-size: 15px; }}
    .regla {{ fill: #15171c; font-size: 15px; font-weight: 700; }}
    .eje {{ fill: #6b7280; font-size: 12.5px; font-weight: 700; letter-spacing: 1px; }}
    .flecha {{ stroke: #6b7280; stroke-width: 2; fill: none; }}
    .aviso {{ fill: #fff8e6; stroke: #d9a400; stroke-width: 1.5; }}
    .avisot {{ fill: #7a5a00; font-size: 14px; font-weight: 700; }}
    .firma {{ fill: #8a919b; font-size: 11.5px; }}
    @media (prefers-color-scheme: dark) {{
      .fondo {{ fill: #0b0d11; }} .bandeja {{ fill: #15171c; }} .cuerpo {{ fill: #1d2415; }} .suelo {{ fill: #232c16; }}
      .brazo {{ stroke: #4a515a; }} .pivote {{ fill: #0b0d11; stroke: #9aa1ac; }}
      .nom, .titulo, .regla {{ fill: #f4f4f2; }} .ent, .num {{ fill: #b5d86a; }} .dato, .sub {{ fill: #c8ccd3; }}
      .ej, .eje, .firma {{ fill: #9aa1ac; }} .flecha {{ stroke: #9aa1ac; }} .aviso {{ fill: #2a2410; }} .avisot {{ fill: #f0c24a; }}
    }}
  </style>
  <defs><marker id="punta" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0 L10 5 L0 10 z" fill="#6b7280"/></marker></defs>
  <rect class="fondo" width="{W}" height="{H}"/>
  <text class="titulo" x="40" y="50">La caja de herramientas escalonada</text>
  <text class="sub" x="40" y="77">Cuándo usar cada herramienta de IA para preguntas cerradas sobre textos. Cada escalón cuesta más y entiende más.</text>
  <text class="regla" x="40" y="103">Se empieza por abajo y se sube al escalón siguiente solo si el de abajo no llega, midiéndolo.</text>
  <rect class="aviso" x="40" y="132" width="352" height="92" rx="6"/>
  <text class="avisot" x="54" y="156">Ojo: ordena por coste, no por acierto.</text>
  <text class="dato" x="54" y="178">Subir solo ayuda si la pregunta depende del</text>
  <text class="dato" x="54" y="196">significado. Si la respuesta la delatan las</text>
  <text class="dato" x="54" y="214">palabras, el escalón 2 acierta como el 4.</text>''')
geo = [(X0 + i * PASO_X, T1 - i * PASO_Y, ANCHO + (8 if i == 4 else 0)) for i in range(5)]
# brazos: dos por unión, del lateral derecho de un escalón al izquierdo del siguiente, detrás de todo
piv = []
for i in range(4):
    x, t, a = geo[i]; x2, t2, _ = geo[i + 1]
    for dy in (ALTO - 95, ALTO - 35):   # los brazos van de borde a borde, por el hueco entre escalones
        p1, p2 = (x + a, t + dy), (x2, t2 + dy)
        w(f'  <line class="brazo" x1="{p1[0]}" y1="{p1[1]}" x2="{p2[0]}" y2="{p2[1]}"/>'); piv += [p1, p2]
for i, ((nombre, ent, datos, ejs), (x, t, a)) in enumerate(zip(B, geo)):
    if i == 0:
        w(f'  <path class="asa" d="M{x+38} {t} v-14 q0 -8 8 -8 h{a-92} q8 0 8 8 v14"/>')
        w(f'  <rect class="cuerpo" x="{x}" y="{t}" width="{a}" height="{ALTO}" rx="6"/>')
    else:
        w(f'  <rect class="bandeja" x="{x}" y="{t}" width="{a}" height="{ALTO}" rx="6"/>')
        w(f'  <rect class="suelo" x="{x+1}" y="{t+ALTO-12}" width="{a-2}" height="11" rx="5"/>')
    w(f'  <line class="borde" x1="{x+2}" y1="{t}" x2="{x+a-2}" y2="{t}"/>')
    y = t + 24; w(f'  <text class="num" x="{x+12}" y="{y}">ESCALÓN {i+1}</text>')
    y += 22
    for n in nombre:
        w(f'  <text class="nom" x="{x+12}" y="{y}">{n}</text>'); y += 20
    y = t + 90; w(f'  <text class="ent" x="{x+12}" y="{y}">{ent}</text>')
    y += 20
    for d in datos:
        w(f'  <text class="dato" x="{x+12}" y="{y}">{d}</text>'); y += 17
    y += 4
    for e in ejs:
        w(f'  <text class="ej" x="{x+12}" y="{y}">{e}</text>'); y += 15
for px, py in piv:
    w(f'  <circle class="pivote" cx="{px}" cy="{py}" r="4.5"/>')
w(f'''  <path class="flecha" d="M40 {EJE_Y} H960" marker-end="url(#punta)"/>
  <path class="flecha" d="M22 {EJE_Y} V260" marker-end="url(#punta)"/>
  <text class="eje" x="960" y="{EJE_Y+20}" text-anchor="end">MÁS COSTE: TIEMPO, MEMORIA, DEPENDENCIA</text>
  <text class="eje" transform="translate(14 {EJE_Y-5}) rotate(-90)">ENTIENDE MÁS</text>
  <text class="firma" x="40" y="{EJE_Y+40}">© 2026 Joaquín Herrero Pintado · CC BY-SA 4.0 · creativecodeworks.com</text>
</svg>''')
(Path(__file__).parent.parent / "docs" / "caja-escalonada.svg").write_text("\n".join(o) + "\n")
print("alto usado:", EJE_Y + 40, "de", H)
