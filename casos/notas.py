"""Nota de 1 a 10 por modelo y caso, con las reglas de DISENO.md (fijadas antes de medir):

- A = acierto medio por clase; Z = 1 / número de opciones (azar);
- nota de calidad = 1 + 9 × (A − Z) / (1 − Z), limitada entre 1 y 10;
- de las respuestas dadas con un 90 % o más, si falla más del 5 % se resta 1, y si falla más del 10 %, 2 (mínimo 1);
- nota del caso = media de las notas de sus preguntas.
Lee <caso>/resultados/*.json y escribe <caso>/notas.json; imprime una tabla. Uso: python notas.py <caso> [<caso> ...]
"""
import json, random, sys
from pathlib import Path

AQUI = Path(__file__).parent


def media_por_clase(pares):
    por = {}
    for pred, lab in pares:
        por.setdefault(lab, []).append(pred == lab)
    return sum(sum(v) / len(v) for v in por.values()) / len(por)


def nota_pregunta(filas):
    """filas: [(p: dict opción -> prob, etiqueta)]. Devuelve la nota y sus piezas."""
    n_opc = len(filas[0][0])
    pares = [(max(p, key=p.get), lab) for p, lab in filas]
    a, z = media_por_clase(pares), 1 / n_opc
    calidad = max(1.0, min(10.0, 1 + 9 * (a - z) / (1 - z)))
    seguras = [(max(p, key=p.get) == lab) for p, lab in filas if max(p.values()) >= 0.9]
    fallo = (len(seguras) - sum(seguras)) / len(seguras) if seguras else 0.0
    penal = 2 if fallo > 0.10 else 1 if fallo > 0.05 else 0
    rnd, boots = random.Random(0), []
    for _ in range(2000):
        m = [pares[rnd.randrange(len(pares))] for _ in pares]
        if len({lab for _, lab in m}) == len({lab for _, lab in pares}):
            boots.append(media_por_clase(m))
    boots.sort()
    return {"nota": round(max(1.0, calidad - penal), 1), "acierto": a, "ic95": [boots[int(.025 * len(boots))],
            boots[int(.975 * len(boots))]], "seguras": len(seguras), "fallo_seguras": fallo, "penalizacion": penal}


for caso in sys.argv[1:]:
    tabla = {}
    for f in sorted((AQUI / caso / "resultados").glob("*.json")):
        r = json.loads(f.read_text())
        preguntas = {}
        for c in r["casos"]:
            for qid, x in c["respuestas"].items():
                preguntas.setdefault(qid, []).append((x["p"], x["label"]))
        notas = {qid: nota_pregunta(filas) for qid, filas in preguntas.items()}
        tabla[r["modelo"]] = {"nota": round(sum(n["nota"] for n in notas.values()) / len(notas), 1),
                              "ms_por_caso": r["ms_por_caso"], "preguntas": notas, "n": len(r["casos"])}
    (AQUI / caso / "notas.json").write_text(json.dumps(tabla, ensure_ascii=False, indent=1))
    qids = list(next(iter(tabla.values()))["preguntas"])
    print(f"\n== {caso} (n = {next(iter(tabla.values()))['n']})")
    print(f"{'modelo':10s} {'NOTA':>5s} " + " ".join(f"{q[:14]:>22s}" for q in qids) + "   ms/caso")
    for m, t in sorted(tabla.items(), key=lambda x: -x[1]["nota"]):
        celdas = " ".join(f"{t['preguntas'][q]['nota']:4.1f} ({t['preguntas'][q]['acierto']*100:3.0f} %{'-' * t['preguntas'][q]['penalizacion']:2s})".rjust(22) for q in qids)
        print(f"{m:10s} {t['nota']:5.1f} {celdas}   {t['ms_por_caso']:.0f}")
