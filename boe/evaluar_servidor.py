"""Evalúa un servidor con el protocolo de TypeSafe (/v1/systemone), como Jeff, sobre un fichero de controles, y guarda
las filas con la misma forma que las de evaluar_kev.py (rows.json: una fila por pregunta, con keys, label y p), para
que exportar.py y los análisis de calibración las lean igual.

Manda cada pregunta por separado: si el servidor rechaza una (Jeff no acepta más de 26 opciones), solo se pierde esa.
Las rechazadas quedan en rechazadas.json con el motivo; hay que compararlas aparte, porque los demás modelos sí las
contestaron. No hay logits: solo las probabilidades servidas, así que no se puede recalibrar desde estas filas.
Uso: python evaluar_servidor.py <url base> <modelo> <datos.jsonl> <carpeta de salida>
     (p. ej. http://127.0.0.1:8010 jeff-latest control_ampliado.jsonl eval-kev/jeff08b-ampliado)"""
import json, sys, time, urllib.error, urllib.request
from pathlib import Path

url, modelo, datos, salida = sys.argv[1:5]
salida = Path(salida)
salida.mkdir(parents=True, exist_ok=True)


def pedir(body):
    req = urllib.request.Request(f"{url}/v1/systemone", json.dumps(body).encode(), {"Content-Type": "application/json"})
    for intento in range(20):   # 529: ocupado con otra petición; se reintenta
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 529:
                raise
            time.sleep(1)
    raise RuntimeError("el servidor sigue ocupado")


filas, rechazadas = [], []
casos = [json.loads(l) for l in Path(datos).read_text().splitlines() if l.strip()]
for i, caso in enumerate(casos):
    for qid, q in caso["questions"].items():
        pregunta = {k: v for k, v in q.items() if k not in ("label", "src")}
        if q["type"] == "noul":
            keys, label = ["false", "true"], int(bool(q["label"]))
        elif q["type"] == "score":
            keys, label = [str(k) for k in range(len(q["criteria"]))], int(q["label"])
        else:
            keys = list(q["criteria"])
            label = keys.index(q["label"])
        try:
            r = pedir({"model": modelo, "state": caso["state"], "questions": {qid: pregunta}})
        except urllib.error.HTTPError as e:
            rechazadas.append({"id": f"custom/{i}", "question": qid, "type": q["type"], "opciones": len(keys),
                               "motivo": f"{e.code} {e.read().decode()[:200]}"})
            continue
        a = r["answers"][qid]
        p = [1 - a["noul"], a["noul"]] if q["type"] == "noul" else [a["probabilities"][k] for k in keys]
        filas.append({"id": f"custom/{i}", "question": qid, "type": q["type"], "variant": "clean", "keys": keys,
                      "label": label, "p": p, "src": q.get("src")})
    if (i + 1) % 100 == 0:
        print(i + 1, "de", len(casos), flush=True)

(salida / "rows.json").write_text(json.dumps(filas, ensure_ascii=False))
(salida / "rechazadas.json").write_text(json.dumps(rechazadas, ensure_ascii=False, indent=1))
print(json.dumps({"preguntas": len(filas), "rechazadas": len(rechazadas)}))
