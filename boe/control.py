"""Genera control.jsonl: las 12 pruebas del laboratorio (laboratorio/casos.py) en el formato de Kev.

Sirve para comprobar que un modelo ajustado no olvida lo que ya sabía: se evalúa antes y después del ajuste con
evaluar_kev.py y el acierto no debería bajar. Uso: python control.py
"""
import json, sys
from pathlib import Path

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI.parent / "laboratorio"))
from casos import CASOS  # noqa: E402

with open(AQUI / "control.jsonl", "w", encoding="utf-8") as f:
    for _, _, estado, pregunta, opciones, correcta, _ in CASOS:
        f.write(json.dumps({"state": estado, "questions": {"q": {
            "type": "choice", "instructions": pregunta, "criteria": {o: None for o in opciones}, "label": correcta}}},
            ensure_ascii=False) + "\n")
print(len(CASOS), "casos en", AQUI / "control.jsonl")
