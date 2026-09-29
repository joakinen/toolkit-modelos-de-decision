"""Curva de aprendizaje de la referencia clásica (clasico.py) en la prueba del BOE: cuántos ejemplos por apartado le
hacen falta para alcanzar a los modelos de decisión sin ajustar y a los ajustados.

Para cada tamaño (ejemplos por apartado) sortea 10 subconjuntos de los 1.400 textos de entrenamiento, entrena la misma
tubería (TF-IDF y regresión logística, con C fijo, porque con 5 ejemplos no cabe validación cruzada) y la mide con los
350 textos de prueba. Da la media, el mínimo y el máximo de los 10 sorteos.
Uso: python clasico_curva.py   (con BOE_DATOS apuntando a la carpeta de los datos)
"""
import json, os, random
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score
from sklearn.pipeline import make_pipeline

AQUI = Path(os.environ.get("BOE_DATOS", Path(__file__).parent))
TAMANOS = [1, 2, 5, 10, 20, 50, 100, 200]
SORTEOS = 10
C = 100   # el que eligió la validación cruzada de clasico.py con los 1.400


def leer(nombre):
    casos = [json.loads(l) for l in (AQUI / nombre).read_text().splitlines() if l.strip()]
    return [c["state"] for c in casos], [c["questions"]["apartado"]["label"] for c in casos]


x_ent, y_ent = leer("entrenamiento.jsonl")
x_pru, y_pru = leer("prueba.jsonl")
por_apartado = {}
for i, y in enumerate(y_ent):
    por_apartado.setdefault(y, []).append(i)

curva = []
for n in TAMANOS:
    aciertos = []
    for s in range(SORTEOS if n < 200 else 1):
        rnd = random.Random(s)
        idx = [i for v in por_apartado.values() for i in rnd.sample(v, n)]
        # con muy pocos textos, min_df=2 dejaría el vocabulario casi vacío
        tuberia = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=2 if n >= 5 else 1, sublinear_tf=True),
                                LogisticRegression(C=C, max_iter=5000))
        tuberia.fit([x_ent[i] for i in idx], [y_ent[i] for i in idx])
        aciertos.append(balanced_accuracy_score(y_pru, tuberia.predict(x_pru)))
    curva.append({"por_apartado": n, "media": sum(aciertos) / len(aciertos), "min": min(aciertos), "max": max(aciertos)})
    print(f"{n:4d} por apartado: {curva[-1]['media']:.1%}  (de {curva[-1]['min']:.1%} a {curva[-1]['max']:.1%})", flush=True)
(AQUI / "clasico-curva.json").write_text(json.dumps(curva, indent=1))
