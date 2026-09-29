"""Referencia clásica para la prueba del BOE: TF-IDF y regresión logística, sin ningún modelo de lenguaje.

Aprende con los mismos 1.400 textos con los que se ajustaron los modelos Kev (entrenamiento.jsonl) y se mide con los
mismos 350 de prueba (prueba.jsonl). La regularización se elige con validación cruzada en 5 partes sobre el
entrenamiento, sin mirar la prueba. Sirve para saber cuánto aporta un modelo de decisión ajustado frente a lo que se
hacía antes de los modelos de lenguaje. Guarda eval/clasico.jsonl con la misma forma que evaluar.py, para que
exportar.py lo lea como un modelo más.
Uso: python clasico.py   (con BOE_DATOS apuntando a la carpeta de los datos, como exportar.py)
"""
import json, os, time
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import make_pipeline

AQUI = Path(os.environ.get("BOE_DATOS", Path(__file__).parent))


def leer(nombre):
    casos = [json.loads(l) for l in (AQUI / nombre).read_text().splitlines() if l.strip()]
    return casos, [c["state"] for c in casos], [c["questions"]["apartado"]["label"] for c in casos]


_, x_ent, y_ent = leer("entrenamiento.jsonl")
prueba, x_pru, y_pru = leer("prueba.jsonl")
apartados = list(prueba[0]["questions"]["apartado"]["criteria"])

t0 = time.time()
tuberia = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
                        LogisticRegression(max_iter=5000))
busqueda = GridSearchCV(tuberia, {"logisticregression__C": [1, 3, 10, 30, 100]}, cv=5, scoring="balanced_accuracy")
busqueda.fit(x_ent, y_ent)
segundos = time.time() - t0

t0 = time.time()
probas = busqueda.predict_proba(x_pru)
ms = (time.time() - t0) * 1000 / len(x_pru)
clases = list(busqueda.classes_)
(AQUI / "eval").mkdir(exist_ok=True)
with open(AQUI / "eval" / "clasico.jsonl", "w", encoding="utf-8") as out:
    for c, p, y in zip(prueba, probas, y_pru):
        ranking = sorted(((a, float(p[clases.index(a)])) for a in apartados), key=lambda x: -x[1])
        out.write(json.dumps({"id": c["id"], "label": y, "ranking": ranking, "ms": round(ms, 2)}, ensure_ascii=False) + "\n")
print(json.dumps({"C": busqueda.best_params_["logisticregression__C"], "cv_balanced_accuracy": round(busqueda.best_score_, 4),
                  "segundos_entrenamiento": round(segundos, 1), "ms_por_texto": round(ms, 2)}))
