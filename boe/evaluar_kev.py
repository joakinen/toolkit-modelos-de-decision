"""Evalúa un modelo Kev sobre un fichero propio con el mismo límite de contexto que el entrenamiento (--max_state 1024).

`kev.benchmark --data` usa el contexto de entrenamiento por defecto (384 tokens de estado) y descarta en silencio los
textos más largos: en la prueba del BOE descartó 182 de 350, casi todos los anuncios de contratación. Este script es
el mismo camino de Kev (LocalPredictor + evaluate_records) con el límite con el que se entrenó; así no se descarta nada.
Uso: python evaluar_kev.py <modelo: Hub o carpeta> <datos.jsonl> <carpeta de salida>"""
import json, sys
from pathlib import Path

from kev.benchmark import evaluate_records
from kev.checkpoint import LoadOptions
from kev.data import load_records
from kev.device import default_device
from kev.model import training_context
from kev.predictors import LocalPredictor

run, datos, salida = sys.argv[1:4]
contexto = {**training_context(1024), "truncate": False}
predictor = LocalPredictor(run, default_device(), LoadOptions.from_env(), context=contexto)
report, _ = evaluate_records(load_records(datos), predictor, salida, skip_overlong=True)
report.update(run=run, data=datos, context=contexto)
(Path(salida) / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1, default=str))
print(json.dumps({"coverage": report["coverage"], "acc": report["clean"]["acc"]}, indent=1))
