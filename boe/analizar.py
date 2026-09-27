"""Resultados de la prueba del apartado del BOE: acierto global, media por apartado, log-loss, acierto por apartado
y las confusiones más frecuentes de cada modelo."""
import collections, json, math
from pathlib import Path

AQUI = Path(__file__).parent
casos = {json.loads(l)["id"]: json.loads(l) for l in (AQUI / "prueba.jsonl").read_text().splitlines() if l.strip()}
apartados = list(next(iter(casos.values()))["questions"]["apartado"]["criteria"])


def resultados():
    out = {}
    for f in sorted((AQUI / "eval").glob("*.jsonl")):
        filas = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
        ok = [r for r in filas if "ranking" in r]
        if ok:
            out[f.stem] = (ok, len(filas) - len(ok))
    return out


if __name__ == "__main__":
    for mid, (filas, errores) in resultados().items():
        por = collections.defaultdict(list)
        ll, conf = 0, collections.Counter()
        for r in filas:
            top = r["ranking"][0][0]
            por[r["label"]].append(top == r["label"])
            ll -= math.log(max(dict(r["ranking"]).get(r["label"], 0), 1e-6))
            if top != r["label"]:
                conf[(r["label"], top)] += 1
        acierto = sum(sum(v) for v in por.values()) / len(filas)
        media = sum(sum(v) / len(v) for v in por.values()) / len(por)
        ms = sorted(r["ms"] for r in filas)[len(filas) // 2]
        print(f"\n{mid}: n={len(filas)} (errores {errores})  acierto {acierto:.0%}  media por apartado {media:.0%}  "
              f"log-loss {ll / len(filas):.2f}  mediana {ms} ms")
        print("  ", "  ".join(f"{a.split(':')[0].split(' Autoridades')[0].split(' Anuncios')[0].rstrip('.')} {sum(por[a])}/{len(por[a])}"
                              for a in apartados if por[a]))
        print("   confusiones:", "; ".join(f"{a[:22]} → {b[:22]} ×{n}" for (a, b), n in conf.most_common(3)))
