"""Casos en español para el control de olvido: tres conjuntos públicos con etiqueta humana, en su partición de test.

- XNLI (facebook/xnli, es): relación entre premisa e hipótesis, traducida por personas; el mismo formato que mnli en
  decision-v7, con las instrucciones en español;
- PAWS-X (google-research-datasets/paws-x, es): si dos oraciones significan lo mismo;
- reseñas de Amazon (SetFit/amazon_reviews_multi_es): estrellas que dio el cliente (1-5), las pone el propio cliente.

Decisiones fijadas el 28-sep-2026 antes de medir ningún modelo sobre estos casos: 50 por fuente, filas elegidas al azar
con semilla 0 entre todas las del test; reseñas recortadas a 220 palabras como en decision-v7. Ninguna de las tres
fuentes entra en el entrenamiento del BOE ni en el replay (decision-v7 no tiene fuentes en español).
El test de cada fuente se descarga entero como parquet (conversión oficial de Hugging Face, refs/convert/parquet) y se
guarda en datos/control-es/ (caché); las filas se eligen después, en local. Los datos no se publican en este
repositorio: cada conjunto tiene su licencia (XNLI, por ejemplo, no permite el uso comercial) y el script los descarga.

Uso: python control_es.py   -> control-es.jsonl
"""
import json, random, time, urllib.parse, urllib.request
from pathlib import Path

import pyarrow.parquet as pq

AQUI = Path(__file__).parent
CACHE = AQUI / "datos/control-es"
POR_FUENTE, SEMILLA = 50, 0
FUENTES = {"xnli": ("facebook/xnli", "es"), "pawsx": ("google-research-datasets/paws-x", "es"),
           "amazon_es": ("SetFit/amazon_reviews_multi_es", "default")}
NLI = ["entailment", "neutral", "contradiction"]
ESTRELLAS = ["1 estrella: muy negativa", "2 estrellas: negativa", "3 estrellas: intermedia", "4 estrellas: positiva",
             "5 estrellas: muy positiva"]


def test(dataset, config):
    """Filas del test completo (lista de dicts), desde el parquet que publica Hugging Face."""
    f = CACHE / f"{dataset.replace('/', '__')}-{config}-test.parquet"
    if not f.exists():
        q = urllib.parse.urlencode(dict(dataset=dataset))
        with urllib.request.urlopen(f"https://datasets-server.huggingface.co/parquet?{q}", timeout=30) as r:
            urls = [x["url"] for x in json.load(r)["parquet_files"] if x["config"] == config and x["split"] == "test"]
        if len(urls) != 1:
            raise RuntimeError(f"{dataset}/{config}: se esperaba un parquet de test y hay {len(urls)}")
        for intento in range(4):
            try:
                with urllib.request.urlopen(urls[0], timeout=60) as r:
                    f.write_bytes(r.read()); break
            except Exception:
                time.sleep(2 ** intento)
        else:
            raise RuntimeError(f"no se pudo descargar {urls[0]}")
    return pq.read_table(f).to_pylist()


def registro(fuente, fila):
    if fuente == "xnli":
        return {"state": fila["premise"], "questions": {"relacion": {
            "type": "choice", "src": "xnli",
            "instructions": f'Hipótesis: «{fila["hypothesis"]}». ¿Qué relación tiene con la premisa?',
            "criteria": {"entailment": "La premisa implica la hipótesis",
                         "neutral": "La hipótesis puede ser verdadera o no, según la premisa",
                         "contradiction": "La hipótesis contradice la premisa"},
            "label": NLI[fila["label"]]}}}
    if fuente == "pawsx":
        return {"state": fila["sentence1"], "questions": {"parafrasis": {
            "type": "noul", "src": "pawsx",
            "instructions": f'¿Significa lo mismo que esta otra oración?: «{fila["sentence2"]}»',
            "label": fila["label"] == 1}}}
    return {"state": " ".join(fila["text"].split()[:220]), "questions": {"estrellas": {
        "type": "score", "src": "amazon_es", "instructions": "¿Cuántas estrellas dio el cliente en esta reseña?",
        "criteria": ESTRELLAS, "label": int(fila["label"])}}}


CACHE.mkdir(parents=True, exist_ok=True)
rnd = random.Random(SEMILLA)
salida = []
for fuente, (ds, cfg) in FUENTES.items():
    filas = test(ds, cfg)
    for i in sorted(rnd.sample(range(len(filas)), POR_FUENTE)):
        salida.append(registro(fuente, filas[i]))
    print(fuente, POR_FUENTE, "de", len(filas), flush=True)
with open(AQUI / "control-es.jsonl", "w", encoding="utf-8") as out:
    for r in salida:
        out.write(json.dumps(r, ensure_ascii=False) + "\n")
print("control-es.jsonl:", len(salida), "casos")
