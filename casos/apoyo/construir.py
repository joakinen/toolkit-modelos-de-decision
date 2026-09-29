"""Caso 3: ¿todo lo que afirma la respuesta está en el texto? Construye el conjunto a partir de textos del BOE.

Textos: los de entrenamiento de la prueba del BOE (BOE_DATOS/entrenamiento.jsonl) de los apartados I (disposiciones
generales), III (otras disposiciones) y V.A (contratación), que rara vez nombran a personas; recortados a 350 palabras.
Por cada texto, un modelo local que NO se mide en la prueba ni es de la familia de los medidos (Gemma 4 12B en Ollama,
sin razonamiento, temperatura 0; la primera versión usó Qwen3.5 9B, que también se medía y juzgaba así sus propios textos):
1. escribe una pregunta sobre el texto y una respuesta corta que solo use datos del texto y cite al menos un dato
   concreto (fecha, importe, plazo, organismo, número): es la respuesta APOYADA;
2. cambia en esa respuesta exactamente un dato concreto por otro verosímil, o le añade una afirmación que el texto no
   contiene: es la respuesta NO APOYADA.
Comprobaciones automáticas (se descarta el texto si alguna falla): las cifras de la apoyada aparecen en el texto; la no
apoyada es distinta; si cambia una cifra, la cifra nueva no aparece en el texto. Cada texto da los dos casos, así que
el conjunto queda mitad y mitad y cada par se compara consigo mismo. 30 textos para entrenar el clásico (60 casos) y 100
para medir (200). Los textos del BOE no se publican: el conjunto se reconstruye con este script.
Uso: BOE_DATOS=<carpeta de la prueba del BOE> python construir.py
"""
import json, os, random, re, urllib.request
from pathlib import Path

AQUI = Path(__file__).parent
BOE = Path(os.environ.get("BOE_DATOS", AQUI.parent.parent / "boe"))
OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODELO = os.environ.get("REDACTOR", "gemma4:12b")
APARTADOS = ("I. ", "III. ", "V.A. ")
N_ENT, N_PRU, PALABRAS = 30, 100, 350
PREGUNTA = "¿Todo lo que afirma esta respuesta está en el texto?"

PIDE_APOYADA = """Lee el texto y escribe una pregunta sobre él y su respuesta.
La respuesta: una o dos frases, en español, SOLO con información que esté en el texto, y con al menos un dato concreto
copiado del texto (una fecha, un importe, un plazo, un número o el nombre de un organismo).
Contesta solo con JSON: {{"pregunta": "...", "respuesta": "..."}}

Texto:
{texto}"""

PIDE_ALTERADA = """Aquí tienes un texto, una pregunta y una respuesta correcta.
Escribe una versión de la respuesta que parezca igual de creíble pero NO se apoye en el texto, de una de estas dos
formas (elige la que se indica): {forma}
Contesta solo con JSON: {{"respuesta": "...", "cambio": "qué has cambiado o añadido"}}

Texto:
{texto}

Pregunta: {pregunta}
Respuesta correcta: {respuesta}"""

FORMAS = {"cambio": "cambia EXACTAMENTE UN dato concreto (fecha, importe, plazo, número u organismo) por otro distinto "
                    "y verosímil; no cambies nada más.",
          "añadido": "deja la respuesta igual y añádele UNA afirmación breve y verosímil que el texto no dice."}


def pedir(prompt):
    body = {"model": MODELO, "think": False, "stream": False, "format": "json",   # sin razonamiento: una respuesta directa
            "messages": [{"role": "user", "content": prompt}], "options": {"temperature": 0}}
    req = urllib.request.Request(f"{OLLAMA}/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(json.load(r)["message"]["content"])


cifras = lambda t: set(re.findall(r"\d+(?:[.,]\d+)*", t))

textos = [json.loads(l) for l in (BOE / "entrenamiento.jsonl").read_text().splitlines() if l.strip()]
textos = [t for t in textos if t["questions"]["apartado"]["label"].startswith(APARTADOS)]
random.Random(0).shuffle(textos)
salida, descartes = [], 0
for i, t in enumerate(textos):
    if len(salida) >= 2 * (N_ENT + N_PRU):
        break
    texto = " ".join(t["state"].split()[:PALABRAS])
    forma = "cambio" if len(salida) // 2 % 2 == 0 else "añadido"
    try:
        a = pedir(PIDE_APOYADA.format(texto=texto))
        b = pedir(PIDE_ALTERADA.format(texto=texto, pregunta=a["pregunta"], respuesta=a["respuesta"], forma=FORMAS[forma]))
        ok = (cifras(a["respuesta"]) and cifras(a["respuesta"]) <= cifras(texto)
              and b["respuesta"].strip() != a["respuesta"].strip()
              and (forma == "añadido" or not (cifras(b["respuesta"]) - cifras(a["respuesta"])) <= cifras(texto)))
    except Exception:
        ok = False
    if not ok:
        descartes += 1
        continue
    for apoyada, resp in ((True, a["respuesta"]), (False, b["respuesta"])):
        salida.append({"id": f"{t['id']}-{'si' if apoyada else 'no'}", "texto_boe": t["id"], "forma": None if apoyada else forma,
                       "cambio": None if apoyada else b.get("cambio"),
                       "state": f"Texto:\n{texto}\n\nPregunta: {a['pregunta']}\nRespuesta: {resp}",
                       "questions": {"apoyada": {"type": "noul", "instructions": PREGUNTA, "label": apoyada}}})
    print(len(salida) // 2, "textos,", descartes, "descartados", flush=True)

for nombre, filas in (("entrenamiento", salida[:2 * N_ENT]), ("prueba", salida[2 * N_ENT:])):
    with open(AQUI / f"{nombre}.jsonl", "w", encoding="utf-8") as out:
        for f in filas:
            out.write(json.dumps({**f, "dificil": f["forma"] == "cambio"}, ensure_ascii=False) + "\n")
    print(nombre, len(filas))
