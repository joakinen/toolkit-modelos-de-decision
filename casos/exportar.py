"""Resume los casos de uso y PAWS-X en resultados/casos.json y resultados/pawsx.json, sin ningún texto: solo notas,
aciertos, intervalos y tiempos. Es lo que muestran la página de resultados y el informe.
Uso: python casos/exportar.py   (después de casos/notas.py; PAWSX_DATOS apunta a la carpeta de PAWS-X)
"""
import json, os, random
from pathlib import Path

RAIZ = Path(__file__).parent.parent
NOMBRES = {"kev-08b": "Kev · 0.8B", "kev-4b": "Kev · 4B", "jeff-08b": "Jeff · 0.8B", "jeff-2b": "Jeff · 2B",
           "jev-v1": "Jev-style v1 · 2B", "jev-v3": "Jev-style v3 · 0.8B", "llm-9b": "Qwen3.5 · 9B (letras)",
           "clasico": "Clasificador clásico", "embeddings": "Embeddings y clasificador",
           "ajustado08b": "Kev · 0.8B ajustado con 200 pares"}
ESCALON = {"clasico": 2, "embeddings": 3, "llm-9b": 5}
CASOS = {"correo": ("Triaje del buzón general", {"unidad": "Unidad", "tipo": "Tipo", "urgente": "Urgente"}),
         "expedientes": ("Completitud de un expediente", {"pago": "Pago", "firma": "Firma", "identidad": "Identidad",
                                                          "representacion": "Quién presenta"}),
         "apoyo": ("¿La respuesta se apoya en el documento?", {"apoyada": "Apoyada"})}

salida = {}
for caso, (titulo, preguntas) in CASOS.items():
    f = RAIZ / "casos" / caso / "notas.json"
    if not f.exists() or not (RAIZ / "casos" / caso / "resultados").exists():
        continue
    notas = json.loads(f.read_text())
    salida[caso] = {"titulo": titulo, "preguntas": preguntas, "n": next(iter(notas.values()))["n"], "modelos": [
        {"id": m, "nombre": NOMBRES.get(m, m), "escalon": ESCALON.get(m, 4), "nota": t["nota"], "ms": t["ms_por_caso"],
         "preguntas": {q: {k: t["preguntas"][q][k] for k in ("nota", "acierto", "ic95", "seguras", "fallo_seguras")}
                       for q in preguntas}}
        for m, t in sorted(notas.items(), key=lambda x: -x[1]["nota"])]}
(RAIZ / "resultados" / "casos.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1))
print("resultados/casos.json:", ", ".join(salida))


def media_por_clase(filas, idx=None):
    idx = range(len(filas)) if idx is None else idx
    por = {}
    for i in idx:
        p = filas[i]["p"]; por.setdefault(int(filas[i]["label"]), []).append(max(range(len(p)), key=p.__getitem__) == int(filas[i]["label"]))
    return sum(sum(v) / len(v) for v in por.values()) / len(por)


def ic(filas):
    rnd, b = random.Random(0), []
    for _ in range(2000):
        b.append(media_por_clase(filas, [rnd.randrange(len(filas)) for _ in filas]))
    b.sort()
    return [b[50], b[1950]]


P = Path(os.environ.get("PAWSX_DATOS", RAIZ / "pawsx"))
if (P / "prueba.jsonl").exists():
    filas = []
    for d, ajustado in (("eval", False), ("eval-kev", True)):
        for f in sorted((P / d).glob("*/rows.json")):
            m = f.parent.name.replace("kev08b", "kev-08b").replace("kev4b", "kev-4b").replace("jeff08b", "jeff-08b").replace("jeff2b", "jeff-2b")
            if d == "eval-kev" and m != "ajustado08b":
                continue   # el original medido con el evaluador de Kev es el mismo que eval/kev08b
            r = sorted(json.loads(f.read_text()), key=lambda x: int(x["id"].split("/")[1]))
            seguras = [x for x in r if max(x["p"]) >= 0.9]
            falla = sum(max(range(len(x["p"])), key=x["p"].__getitem__) != int(x["label"]) for x in seguras)
            filas.append({"id": m, "nombre": NOMBRES.get(m, m), "escalon": ESCALON.get(m, 4), "ejemplos": 200 if ajustado else 0,
                          "acierto": media_por_clase(r), "ic95": ic(r), "seguras": len(seguras), "fallo_seguras": falla / max(1, len(seguras))})
    for ref, fichero in (("clasico", "clasico.json"), ("embeddings", "embeddings.json")):
        if (P / fichero).exists():
            curva = json.loads((P / fichero).read_text())
            filas.append({"id": ref, "nombre": NOMBRES[ref], "escalon": ESCALON[ref], "curva": curva})
    (RAIZ / "resultados" / "pawsx.json").write_text(json.dumps({"n": 400, "modelos": filas}, ensure_ascii=False, indent=1))
    print("resultados/pawsx.json:", len(filas), "filas")
