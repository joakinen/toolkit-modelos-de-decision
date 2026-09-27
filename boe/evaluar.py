"""Pasa prueba.jsonl por los modelos del laboratorio (los mismos ejecutores que la web de :8090) sin ajustar.
Guarda una línea por texto y modelo en eval/<modelo>.jsonl y se puede reanudar: salta lo ya hecho.
Uso: python evaluar.py [modelo ...]   (por defecto, los cinco)"""
import json, sys, time
from pathlib import Path

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI.parent / "laboratorio"))
from app import POR_ID  # noqa: E402

casos = [json.loads(l) for l in (AQUI / "prueba.jsonl").read_text().splitlines() if l.strip()]
(AQUI / "eval").mkdir(exist_ok=True)
for mid in sys.argv[1:] or list(POR_ID):
    f = AQUI / "eval" / f"{mid}.jsonl"
    hechos = {json.loads(l)["id"] for l in f.read_text().splitlines()} if f.exists() else set()
    with open(f, "a", encoding="utf-8") as out:
        for i, c in enumerate(casos):
            if c["id"] in hechos:
                continue
            q = c["questions"]["apartado"]
            t0 = time.time()
            try:
                ranking = POR_ID[mid]["run"](c["state"], [("apartado", q["instructions"], list(q["criteria"]))])["apartado"]
            except Exception as e:  # un fallo aislado no para la evaluación; queda anotado
                out.write(json.dumps({"id": c["id"], "error": str(e)[:300]}, ensure_ascii=False) + "\n"); continue
            out.write(json.dumps({"id": c["id"], "label": q["label"], "ranking": ranking,
                                  "ms": round((time.time() - t0) * 1000)}, ensure_ascii=False) + "\n")
            out.flush()
            if (i + 1) % 100 == 0:
                print(mid, i + 1, "de", len(casos), flush=True)
    print(mid, "terminado", flush=True)
