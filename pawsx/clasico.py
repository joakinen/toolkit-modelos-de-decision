"""Referencia clásica en la prueba de paráfrasis: TF-IDF y regresión logística, sin ningún modelo de lenguaje.

Cada oración se convierte en un vector TF-IDF (palabras sueltas y pares de palabras) y el par se describe con dos
vectores: la diferencia en valor absoluto y el producto elemento a elemento, la forma habitual de comparar dos textos
con un clasificador lineal. Para cada tamaño se sortean 10 subconjuntos de la bolsa de entrenamiento (el primer sorteo de
200 es el mismo con el que se ajusta Kev) y se mide con los 400 pares de prueba. C fijo, como en boe/clasico_curva.py.
Uso: PAWSX_DATOS=<carpeta> python clasico.py   -> clasico.json en esa carpeta
"""
import json, os, random
from pathlib import Path

from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score

AQUI = Path(os.environ.get("PAWSX_DATOS", Path(__file__).parent))
TAMANOS, SORTEOS, C = [50, 200, 1000, 5000], 10, 10


def leer(nombre):
    return [json.loads(l) for l in (AQUI / nombre).read_text().splitlines() if l.strip()]


def muestra(bolsa, n, sorteo):
    """Los n pares de un sorteo; el sorteo 0 son los primeros n de la bolsa (ya barajada por construir.py)."""
    return bolsa[:n] if sorteo == 0 else random.Random(sorteo).sample(bolsa, n)


def rasgos(vec, filas):
    a, b = vec.transform([r["s1"] for r in filas]), vec.transform([r["s2"] for r in filas])
    return hstack([abs(a - b), a.multiply(b)]).tocsr()


etiqueta = lambda filas: [int(r["questions"]["parafrasis"]["label"]) for r in filas]
bolsa, prueba = leer("entrenamiento.jsonl"), leer("prueba.jsonl")
resultados = []
for n in TAMANOS:
    aciertos = []
    for s in range(SORTEOS if n < len(bolsa) else 1):
        ent = muestra(bolsa, n, s)
        vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True).fit([r["s1"] for r in ent] + [r["s2"] for r in ent])
        modelo = LogisticRegression(C=C, max_iter=5000).fit(rasgos(vec, ent), etiqueta(ent))
        aciertos.append(balanced_accuracy_score(etiqueta(prueba), modelo.predict(rasgos(vec, prueba))))
    resultados.append({"n": n, "media": sum(aciertos) / len(aciertos), "min": min(aciertos), "max": max(aciertos),
                       "sorteo0": aciertos[0]})
    print(f"{n:5d} pares: {resultados[-1]['media']:.1%}  (de {min(aciertos):.1%} a {max(aciertos):.1%})", flush=True)
(AQUI / "clasico.json").write_text(json.dumps(resultados, indent=1))
