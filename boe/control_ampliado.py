"""Genera control-ampliado.jsonl: las 12 pruebas de control.py más 440 casos de la partición de test de decision-v7, el
conjunto con el que se publica Kev (11 fuentes públicas: noticias, reseñas, consultas bancarias, inferencia…).

Las 12 pruebas son pocas para ver si el ajuste estropea algo: un acierto más o menos mueve la cifra 8 puntos. Estos 440
casos no entran en el ajuste (el repaso de ajustar.sh sale de la partición de entrenamiento de decision-v7, no de la de
test). Decisiones fijadas el 28-sep-2026 antes de medir: 40 casos por fuente, semilla 0, todas las preguntas de cada caso.
Casi todos están en inglés; el español lo cubre control_es.py.

Uso: KEV_DIR=/ruta/a/kev python control_ampliado.py   (después de control.py)
"""
import collections, json, os, random
from pathlib import Path

AQUI = Path(__file__).parent
TEST = Path(os.environ["KEV_DIR"]) / "evals/v7/decision-v7/test.jsonl"
POR_FUENTE, SEMILLA = 40, 0

por_fuente = collections.defaultdict(list)
for l in open(TEST, encoding="utf-8"):
    r = json.loads(l)
    por_fuente[r["_meta"]["source"]].append(r)
rnd = random.Random(SEMILLA)
muestra = [r for f in sorted(por_fuente) for r in rnd.sample(por_fuente[f], min(POR_FUENTE, len(por_fuente[f])))]

with open(AQUI / "control-ampliado.jsonl", "w", encoding="utf-8") as out:
    publicas = (AQUI / "control.jsonl").read_text(encoding="utf-8").splitlines()
    for l in publicas:
        out.write(l + "\n")
    for r in muestra:
        out.write(json.dumps({"state": r["state"], "questions": r["questions"]}, ensure_ascii=False) + "\n")
print(f"control-ampliado.jsonl: {len(publicas)} pruebas + {len(muestra)} de decision-v7 test",
      dict(collections.Counter(r["_meta"]["source"] for r in muestra)))
