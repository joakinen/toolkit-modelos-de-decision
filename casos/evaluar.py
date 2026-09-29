"""Pasa la prueba de un caso de uso por los modelos del laboratorio y por el clasificador clásico, y guarda las
probabilidades de cada pregunta en <caso>/resultados/<modelo>.json (ids y números, sin textos).

Cada modelo recibe la pregunta por su vía natural, la misma que en el laboratorio:
- Kev y Jeff (protocolo de TypeSafe): la pregunta tal cual, con las descripciones de las opciones y las de sí/no como
  tipo noul;
- Jev-style v1, v3 y Qwen3.5 9B (letras): las opciones como «clave: descripción», y las de sí/no como dos opciones, «sí»
  y «no».
El clásico (TF-IDF y regresión logística) se entrena por pregunta con <caso>/entrenamiento.jsonl; en el caso apoyo,
con los rasgos de par de pawsx/clasico.py (texto frente a respuesta).
Se puede reanudar: salta los modelos que ya tienen resultados. Uso: python evaluar.py <caso> [modelo ...]
"""
import json, sys, time
from pathlib import Path

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI.parent / "laboratorio"))
from app import MODELOS, post_json  # noqa: E402

PROTOCOLO = {"kev-08b": 8008, "kev-4b": 8009, "jeff-08b": 8010, "jeff-2b": 8011}
NOMBRE_SERVIDOR = {"kev-08b": "kev-latest", "kev-4b": "kev-latest", "jeff-08b": "jeff-latest", "jeff-2b": "jeff-latest"}
POR_ID = {m["id"]: m for m in MODELOS}


def opciones(q):
    """Claves y textos que ve un modelo de letras; las claves son las respuestas que se puntúan."""
    if q["type"] == "noul":
        return ["true", "false"], ["sí", "no"]
    claves = list(q["criteria"])
    return claves, [k if q["criteria"][k] is None else f"{k}: {q['criteria'][k]}" for k in claves]


def por_protocolo(mid, caso):
    body = {"model": NOMBRE_SERVIDOR[mid], "state": caso["state"],
            "questions": {qid: {k: v for k, v in q.items() if k != "label"} for qid, q in caso["questions"].items()}}
    for _ in range(20):
        try:
            r = post_json(f"http://127.0.0.1:{PROTOCOLO[mid]}/v1/systemone", body, timeout=300)
            break
        except Exception as e:  # 529: ocupado
            if "529" not in str(e):
                raise
            time.sleep(1)
    answers = r.get("answers", r)
    out = {}
    for qid, q in caso["questions"].items():
        a = answers[qid]
        out[qid] = {"true": a["noul"], "false": 1 - a["noul"]} if q["type"] == "noul" else a["probabilities"]
    return out


def por_letras(mid, caso):
    out = {}
    for qid, q in caso["questions"].items():
        claves, textos = opciones(q)
        ranking = dict(POR_ID[mid]["run"](caso["state"], [(qid, q["instructions"], textos)])[qid])
        out[qid] = {c: ranking.get(t, 0.0) for c, t in zip(claves, textos)}
    return out


def etiqueta(q):
    return ("true" if q["label"] else "false") if q["type"] == "noul" else q["label"]


def clasico_par(ent, prueba):
    """Caso apoyo: el par (texto, respuesta) se describe como en pawsx/clasico.py: |a - b| y a * b de sus TF-IDF."""
    from scipy.sparse import hstack
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    partes = lambda c: (c["state"].split("\n\nPregunta: ")[0], c["state"].split("\nRespuesta: ", 1)[1])
    vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True).fit([x for c in ent for x in partes(c)])
    def rasgos(filas):
        a, b = vec.transform([partes(c)[0] for c in filas]), vec.transform([partes(c)[1] for c in filas])
        return hstack([abs(a - b), a.multiply(b)]).tocsr()
    m = LogisticRegression(C=10, max_iter=5000).fit(rasgos(ent), [etiqueta(c["questions"]["apoyada"]) for c in ent])
    return [{"apoyada": {k: float(p[list(m.classes_).index(k)]) for k in ("true", "false")}}
            for p in m.predict_proba(rasgos(prueba))]


def clasico(ent, prueba):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    if "apoyada" in prueba[0]["questions"]:
        return clasico_par(ent, prueba)
    out = [{} for _ in prueba]
    for qid, q0 in prueba[0]["questions"].items():
        m = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True), LogisticRegression(C=10, max_iter=5000))
        m.fit([c["state"] for c in ent], [etiqueta(c["questions"][qid]) for c in ent])
        claves = opciones(q0)[0]
        for o, p in zip(out, m.predict_proba([c["state"] for c in prueba])):
            o[qid] = {k: float(p[list(m.classes_).index(k)]) if k in m.classes_ else 0.0 for k in claves}
    return out


if __name__ == "__main__":
    caso = sys.argv[1]
    leer = lambda n: [json.loads(l) for l in (AQUI / caso / f"{n}.jsonl").read_text().splitlines() if l.strip()]
    prueba = leer("prueba")
    salida = AQUI / caso / "resultados"
    salida.mkdir(exist_ok=True)
    for mid in sys.argv[2:] or [*PROTOCOLO, "jev-v1", "jev-v3", "llm-9b", "clasico"]:
        f = salida / f"{mid}.json"
        if f.exists():
            print(mid, "ya hecho"); continue
        t0 = time.time()
        if mid == "clasico":
            probs = clasico(leer("entrenamiento"), prueba)
        else:
            if not POR_ID[mid]["ok"]():
                print(mid, "no responde, se salta"); continue
            probs = [(por_protocolo if mid in PROTOCOLO else por_letras)(mid, c) for c in prueba]
        ms = (time.time() - t0) * 1000 / len(prueba)
        f.write_text(json.dumps({"modelo": mid, "ms_por_caso": round(ms, 1), "casos": [
            {"id": c["id"], "dificil": c["dificil"], "respuestas": {qid: {"label": etiqueta(q), "p": p[qid]}
                                                                    for qid, q in c["questions"].items()}}
            for c, p in zip(prueba, probs)]}, ensure_ascii=False, indent=0))
        print(mid, "hecho", round(ms), "ms por caso", flush=True)
