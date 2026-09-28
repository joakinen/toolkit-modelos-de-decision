"""Genera calibracion-mezcla.jsonl: los casos con los que se recalibran los modelos ajustados (una temperatura).

El entrenador de Kev deja la temperatura del modelo ajustado en 1,0 (el Kev publicado trae la suya, en torno a 2,4), y
el modelo sale demasiado seguro de sí mismo. La temperatura se ajusta con casos que no entran ni en el entrenamiento ni
en ninguna medida, mezclando los tres usos que se miden (400 casos, fijados el 28-sep-2026 antes de medir):
- BOE: los 140 textos de septiembre de calibracion.jsonl (construir.py calibracion: 20 por apartado, del 1 al 27);
- tareas generales: 20 por fuente de la partición de calibración de decision-v7, de las 10 fuentes públicas que también
  están en el control ampliado, semilla 0;
- español: 20 por fuente de la partición de validación de XNLI, PAWS-X y reseñas de Amazon, semilla 0, con el mismo
  formato que control_es.py (el control usa su partición de test).

Uso: KEV_DIR=/ruta/a/kev python calibracion.py   (después de construir.py calibracion y control_es.py)
"""
import collections, json, os, random, time, urllib.parse, urllib.request
from pathlib import Path

import pyarrow.parquet as pq

AQUI = Path(__file__).parent
CALIBRACION_V7 = Path(os.environ["KEV_DIR"]) / "evals/v7/decision-v7/calibration.jsonl"
CACHE = AQUI / "datos/control-es"
POR_FUENTE, SEMILLA = 20, 0
PUBLICAS = ["agnews", "amazon", "banking77", "boolq", "dbpedia14", "imdb", "mnli", "sst5", "trec", "yelp"]
FUENTES_ES = {"xnli": ("facebook/xnli", "es"), "pawsx": ("google-research-datasets/paws-x", "es"),
              "amazon_es": ("SetFit/amazon_reviews_multi_es", "default")}


def validacion(dataset, config):
    """Filas de la partición de validación, desde el parquet que publica Hugging Face (con caché)."""
    f = CACHE / f"{dataset.replace('/', '__')}-{config}-validation.parquet"
    if not f.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        q = urllib.parse.urlencode(dict(dataset=dataset))
        with urllib.request.urlopen(f"https://datasets-server.huggingface.co/parquet?{q}", timeout=30) as r:
            urls = [x["url"] for x in json.load(r)["parquet_files"] if x["config"] == config and x["split"] == "validation"]
        if len(urls) != 1:
            raise RuntimeError(f"{dataset}/{config}: se esperaba un parquet de validación y hay {len(urls)}")
        for intento in range(4):
            try:
                with urllib.request.urlopen(urls[0], timeout=60) as r:
                    f.write_bytes(r.read()); break
            except Exception:
                time.sleep(2 ** intento)
        else:
            raise RuntimeError(f"no se pudo descargar {urls[0]}")
    return pq.read_table(f).to_pylist()


def registro_es(fuente, fila):
    """El mismo formato que control_es.py."""
    if fuente == "xnli":
        return {"state": fila["premise"], "questions": {"relacion": {
            "type": "choice", "src": "xnli",
            "instructions": f'Hipótesis: «{fila["hypothesis"]}». ¿Qué relación tiene con la premisa?',
            "criteria": {"entailment": "La premisa implica la hipótesis",
                         "neutral": "La hipótesis puede ser verdadera o no, según la premisa",
                         "contradiction": "La hipótesis contradice la premisa"},
            "label": ["entailment", "neutral", "contradiction"][fila["label"]]}}}
    if fuente == "pawsx":
        return {"state": fila["sentence1"], "questions": {"parafrasis": {
            "type": "noul", "src": "pawsx",
            "instructions": f'¿Significa lo mismo que esta otra oración?: «{fila["sentence2"]}»',
            "label": fila["label"] == 1}}}
    return {"state": " ".join(fila["text"].split()[:220]), "questions": {"estrellas": {
        "type": "score", "src": "amazon_es", "instructions": "¿Cuántas estrellas dio el cliente en esta reseña?",
        "criteria": ["1 estrella: muy negativa", "2 estrellas: negativa", "3 estrellas: intermedia",
                     "4 estrellas: positiva", "5 estrellas: muy positiva"],
        "label": int(fila["label"])}}}


salida = [{"state": r["state"], "questions": r["questions"]}
          for r in map(json.loads, open(AQUI / "calibracion.jsonl", encoding="utf-8"))]
n_boe = len(salida)

por_fuente = collections.defaultdict(list)
for l in open(CALIBRACION_V7, encoding="utf-8"):
    r = json.loads(l)
    por_fuente[r["_meta"]["source"]].append(r)
rnd = random.Random(SEMILLA)
for f in PUBLICAS:
    salida += [{"state": r["state"], "questions": r["questions"]} for r in rnd.sample(por_fuente[f], POR_FUENTE)]
n_gen = len(salida) - n_boe

rnd = random.Random(SEMILLA)
for fuente, (ds, cfg) in FUENTES_ES.items():
    filas = validacion(ds, cfg)
    salida += [registro_es(fuente, filas[i]) for i in sorted(rnd.sample(range(len(filas)), POR_FUENTE))]

with open(AQUI / "calibracion-mezcla.jsonl", "w", encoding="utf-8") as out:
    for r in salida:
        out.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"calibracion-mezcla.jsonl: {n_boe} BOE + {n_gen} generales + {len(salida) - n_boe - n_gen} en español = {len(salida)}")
