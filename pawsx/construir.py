"""Prueba de paráfrasis con PAWS-X en español: una pregunta que no se resuelve contando palabras.

PAWS-X (google-research-datasets/paws-x) son pares de oraciones con casi las mismas palabras que unas veces significan
lo mismo y otras no («El vuelo de Madrid a Lima» frente a «El vuelo de Lima a Madrid»). Se hizo para que fallen los
métodos que miran qué palabras hay. Sirve para comparar un clasificador clásico con un modelo de decisión en un terreno
donde el vocabulario no basta; en la prueba del BOE, sí basta (ver boe/clasico_curva.py).

Decisiones fijadas el 29-sep-2026 antes de medir ningún modelo sobre estos datos:
- prueba: 400 pares del test en español, al azar con semilla 1, sin los 50 que usa el control en español (control_es.py);
- entrenamiento: una bolsa de 5.000 pares de la partición de entrenamiento en español (traducida a máquina, las de test y
  validación las tradujeron personas), al azar con semilla 0; los tamaños más pequeños salen de ella (clasico.py y el
  ajuste de Kev usan los primeros N de cada sorteo);
- la pregunta, la misma del control en español: tipo noul, «¿Significa lo mismo que esta otra oración?».
Los datos no se publican aquí: el script los descarga (parquet oficial de Hugging Face) a PAWSX_DATOS/datos.
Uso: PAWSX_DATOS=<carpeta> python construir.py   -> entrenamiento.jsonl y prueba.jsonl en esa carpeta
"""
import json, os, random, time, urllib.parse, urllib.request
from pathlib import Path

import pyarrow.parquet as pq

AQUI = Path(os.environ.get("PAWSX_DATOS", Path(__file__).parent))
CACHE = AQUI / "datos"
CONTROL_ES = Path(os.environ.get("CONTROL_ES", AQUI.parent / "boe" / "control2-es.jsonl"))
N_PRUEBA, N_BOLSA = 400, 5000
PREGUNTA = "¿Significa lo mismo que esta otra oración?: «{}»"


def particion(split):
    f = CACHE / f"paws-x-es-{split}.parquet"
    if not f.exists():
        q = urllib.parse.urlencode(dict(dataset="google-research-datasets/paws-x"))
        with urllib.request.urlopen(f"https://datasets-server.huggingface.co/parquet?{q}", timeout=30) as r:
            urls = [x["url"] for x in json.load(r)["parquet_files"] if x["config"] == "es" and x["split"] == split]
        if len(urls) != 1:
            raise RuntimeError(f"se esperaba un parquet de {split} y hay {len(urls)}")
        for intento in range(4):
            try:
                with urllib.request.urlopen(urls[0], timeout=120) as r:
                    f.write_bytes(r.read()); break
            except Exception:
                time.sleep(2 ** intento)
        else:
            raise RuntimeError(f"no se pudo descargar {urls[0]}")
    return [r for r in pq.read_table(f).to_pylist() if r["sentence1"] and r["sentence2"] and r["label"] in (0, 1)]


def registro(fila):
    return {"id": f"pawsx-{fila['id']}", "s1": fila["sentence1"], "s2": fila["sentence2"],
            "state": fila["sentence1"], "questions": {"parafrasis": {
                "type": "noul", "instructions": PREGUNTA.format(fila["sentence2"]), "label": fila["label"] == 1}}}


CACHE.mkdir(parents=True, exist_ok=True)
en_control = set()
if CONTROL_ES.exists():
    for l in CONTROL_ES.read_text().splitlines():
        r = json.loads(l)
        if any(q.get("src") == "pawsx" for q in r["questions"].values()):
            en_control.add(r["state"])
test = [r for r in particion("test") if r["sentence1"] not in en_control]
train = particion("train")
prueba = [registro(r) for r in random.Random(1).sample(test, N_PRUEBA)]
bolsa = [registro(r) for r in random.Random(0).sample(train, N_BOLSA)]
vistas = {(r["s1"], r["s2"]) for r in prueba}
bolsa = [r for r in bolsa if (r["s1"], r["s2"]) not in vistas]
for nombre, filas in (("prueba", prueba), ("entrenamiento", bolsa)):
    with open(AQUI / f"{nombre}.jsonl", "w", encoding="utf-8") as out:
        for r in filas:
            out.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(nombre, len(filas), "pares,", sum(r["questions"]["parafrasis"]["label"] for r in filas), "paráfrasis",
          f"(test sin los {len(en_control)} del control)" if nombre == "prueba" else "")
