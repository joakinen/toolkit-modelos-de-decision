"""Revisión a mano del caso de respuestas apoyadas: excluye los textos cuya respuesta «no apoyada» resultó estar apoyada.

Se revisaron (29-sep-2026) todos los casos en que los dos mejores modelos coincidían contra la etiqueta, y todas las
respuestas con una afirmación añadida cuyo contenido aparecía en el texto. En tres textos de la prueba, el modelo que
redactó las respuestas añadió algo que sí dice el texto, así que la etiqueta «no apoyada» es falsa. Se excluye el par
entero (la respuesta correcta y la alterada), para que cada texto siga comparándose consigo mismo. Las respuestas con un
dato cambiado no necesitan esta revisión: el constructor exige que la cifra nueva no aparezca en el texto.
Uso: python casos/apoyo/revision.py   (después de construir.py y de evaluar; es idempotente)
"""
import json
from pathlib import Path

AQUI = Path(__file__).parent
EXCLUIDOS = {
    "BOE-B-2026-9337": "lo añadido («procedimiento de emergencia») está en el texto",
    "BOE-A-2026-11182": "lo añadido («polígono 10 del Catastro») está en el texto",
    "BOE-A-2026-4494": "lo añadido («remitida por el Ministerio para la Transición Ecológica») está en el texto",
}
fuera = lambda i: any(i.startswith(t + "-") for t in EXCLUIDOS)

f = AQUI / "prueba.jsonl"
filas = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
quedan = [r for r in filas if not fuera(r["id"])]
f.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in quedan))
print(f"prueba: {len(filas)} -> {len(quedan)} casos")
for r in sorted((AQUI / "resultados").glob("*.json")):
    d = json.loads(r.read_text())
    d["casos"] = [c for c in d["casos"] if not fuera(c["id"])]
    r.write_text(json.dumps(d, ensure_ascii=False, indent=0))
print("resultados filtrados:", len(list((AQUI / "resultados").glob("*.json"))), "modelos")
