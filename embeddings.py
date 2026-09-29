"""Referencia con embeddings: el texto se convierte en un vector con un modelo de embeddings local (bge-m3, en Ollama) y
una regresión logística aprende encima. Es el punto intermedio entre el clasificador clásico (que solo ve palabras) y
un modelo de decisión: capta algo de significado con el coste de entrenar un clasificador.

Se aplica igual a todas las pruebas, con los mismos repartos que el clasificador clásico:
- boe: 1.400 textos para entrenar, 350 para medir, y la curva de aprendizaje de boe/clasico_curva.py (10 sorteos);
- pawsx: la bolsa de entrenamiento y los 400 pares de prueba, con 50, 200, 1.000 y 5.000 pares (10 sorteos);
- correo, expedientes y apoyo: <caso>/entrenamiento.jsonl y <caso>/prueba.jsonl; el resultado va a
  <caso>/resultados/embeddings.json, con la forma de casos/evaluar.py, para que casos/notas.py lo puntúe.
En los pares (pawsx y apoyo), el par se describe como en el clásico: |a − b| y a × b de los dos vectores.
Regresión logística con C = 10 en todas, sin elegirlo mirando la prueba. Los vectores se guardan en .cache/ (no se
publica) para no recalcularlos.
Uso: python embeddings.py boe|pawsx|correo|expedientes|apoyo   (BOE_DATOS y PAWSX_DATOS como en los demás scripts)
"""
import hashlib, json, os, random, sys, time, urllib.request
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score

RAIZ = Path(__file__).parent
OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODELO = "bge-m3"
CACHE = RAIZ / ".cache" / "embeddings"
C = 10


def vectores(textos, lote=16):
    """Un vector normalizado por texto; lo ya calculado sale de la caché."""
    CACHE.mkdir(parents=True, exist_ok=True)
    clave = lambda t: hashlib.sha256(f"{MODELO}\n{t}".encode()).hexdigest()
    faltan = [t for t in dict.fromkeys(textos) if not (CACHE / f"{clave(t)}.npy").exists()]
    for i in range(0, len(faltan), lote):
        parte = faltan[i:i + lote]
        req = urllib.request.Request(f"{OLLAMA}/api/embed", json.dumps({"model": MODELO, "input": parte}).encode(),
                                     {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as r:
            for t, v in zip(parte, json.load(r)["embeddings"]):
                np.save(CACHE / f"{clave(t)}.npy", np.asarray(v, dtype=np.float32))
        if (i // lote) % 20 == 0:
            print(f"  embeddings: {i + len(parte)} de {len(faltan)} nuevos", flush=True)
    m = np.stack([np.load(CACHE / f"{clave(t)}.npy") for t in textos])
    return m / np.linalg.norm(m, axis=1, keepdims=True)


par = lambda a, b: np.hstack([np.abs(a - b), a * b])
leer = lambda p: [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]
entrenar = lambda x, y: LogisticRegression(C=C, max_iter=5000).fit(x, y)


def boe():
    d = Path(os.environ.get("BOE_DATOS", RAIZ / "boe"))
    ent, pru = leer(d / "entrenamiento.jsonl"), leer(d / "prueba.jsonl")
    y = lambda cs: [c["questions"]["apartado"]["label"] for c in cs]
    xe, xp = vectores([c["state"] for c in ent]), vectores([c["state"] for c in pru])
    t0 = time.time()
    m = entrenar(xe, y(ent))
    probas = m.predict_proba(xp)
    ms = (time.time() - t0) * 1000 / len(pru)
    apartados = list(pru[0]["questions"]["apartado"]["criteria"])
    with open(d / "eval" / "embeddings.jsonl", "w", encoding="utf-8") as out:
        for c, p in zip(pru, probas):
            ranking = sorted(((a, float(p[list(m.classes_).index(a)])) for a in apartados), key=lambda x: -x[1])
            out.write(json.dumps({"id": c["id"], "label": c["questions"]["apartado"]["label"], "ranking": ranking,
                                  "ms": round(ms, 2)}, ensure_ascii=False) + "\n")
    print(f"BOE, 1.400 textos: {balanced_accuracy_score(y(pru), m.predict(xp)):.1%} (eval/embeddings.jsonl)")
    por = {}
    for i, c in enumerate(ent):
        por.setdefault(c["questions"]["apartado"]["label"], []).append(i)
    curva = []
    for n in [1, 2, 5, 10, 20, 50, 100, 200]:
        acc = []
        for s in range(10 if n < 200 else 1):
            idx = [i for v in por.values() for i in random.Random(s).sample(v, n)]
            acc.append(balanced_accuracy_score(y(pru), entrenar(xe[idx], [y(ent)[i] for i in idx]).predict(xp)))
        curva.append({"por_apartado": n, "media": sum(acc) / len(acc), "min": min(acc), "max": max(acc)})
        print(f"  {n:4d} por apartado: {curva[-1]['media']:.1%} (de {min(acc):.1%} a {max(acc):.1%})", flush=True)
    (d / "embeddings-curva.json").write_text(json.dumps(curva, indent=1))


def pawsx():
    d = Path(os.environ.get("PAWSX_DATOS", RAIZ / "pawsx"))
    bolsa, pru = leer(d / "entrenamiento.jsonl"), leer(d / "prueba.jsonl")
    y = lambda cs: [int(c["questions"]["parafrasis"]["label"]) for c in cs]
    todos = bolsa + pru
    v = dict(zip([x for c in todos for x in (c["s1"], c["s2"])], vectores([x for c in todos for x in (c["s1"], c["s2"])])))
    x = lambda cs: np.stack([par(v[c["s1"]], v[c["s2"]]) for c in cs])
    xp, res = x(pru), []
    for n in [50, 200, 1000, 5000]:
        acc = []
        for s in range(10 if n < len(bolsa) else 1):
            ent = bolsa[:n] if s == 0 else random.Random(s).sample(bolsa, n)
            acc.append(balanced_accuracy_score(y(pru), entrenar(x(ent), y(ent)).predict(xp)))
        res.append({"n": n, "media": sum(acc) / len(acc), "min": min(acc), "max": max(acc), "sorteo0": acc[0]})
        print(f"PAWS-X, {n:5d} pares: {res[-1]['media']:.1%} (de {min(acc):.1%} a {max(acc):.1%})", flush=True)
    (d / "embeddings.json").write_text(json.dumps(res, indent=1))


def caso(nombre):
    sys.path.insert(0, str(RAIZ / "casos"))
    from evaluar import etiqueta, opciones
    d = RAIZ / "casos" / nombre
    ent, pru = leer(d / "entrenamiento.jsonl"), leer(d / "prueba.jsonl")
    if nombre == "apoyo":   # par: el texto frente a la respuesta
        partes = lambda c: (c["state"].split("\n\nPregunta: ")[0], c["state"].split("\nRespuesta: ", 1)[1])
        x = lambda cs: par(vectores([partes(c)[0] for c in cs]), vectores([partes(c)[1] for c in cs]))
    else:
        x = lambda cs: vectores([c["state"] for c in cs])
    xe, xp = x(ent), x(pru)
    t0, out = time.time(), [{} for _ in pru]
    for qid, q0 in pru[0]["questions"].items():
        m = entrenar(xe, [etiqueta(c["questions"][qid]) for c in ent])
        claves = opciones(q0)[0]
        for o, p in zip(out, m.predict_proba(xp)):
            o[qid] = {k: float(p[list(m.classes_).index(k)]) if k in m.classes_ else 0.0 for k in claves}
    ms = (time.time() - t0) * 1000 / len(pru)
    (d / "resultados").mkdir(exist_ok=True)
    (d / "resultados" / "embeddings.json").write_text(json.dumps({"modelo": "embeddings", "ms_por_caso": round(ms, 1), "casos": [
        {"id": c["id"], "dificil": c["dificil"], "respuestas": {qid: {"label": etiqueta(q), "p": p[qid]}
                                                                for qid, q in c["questions"].items()}}
        for c, p in zip(pru, out)]}, ensure_ascii=False, indent=0))
    print(nombre, "hecho: casos/" + nombre + "/resultados/embeddings.json")


if __name__ == "__main__":
    que = sys.argv[1]
    {"boe": boe, "pawsx": pawsx}.get(que, lambda: caso(que))()
