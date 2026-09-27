"""Resume la prueba del apartado del BOE en resultados/boe.json, sin ningún texto: solo identificadores del BOE, la
respuesta de cada modelo y las cifras agregadas. Es lo que muestran la pestaña BOE del laboratorio y la página estática.

Lee eval/<modelo>.jsonl (modelos sin ajustar, de evaluar.py) y eval-kev/<nombre>-{prueba,control}/rows.json (Kev original
y ajustado, de evaluar_kev.py). Las diferencias entre modelos llevan un intervalo de confianza del 95 % por bootstrap
pareado (2.000 remuestreos, semilla 0) sobre la media del acierto por apartado.
Uso: python exportar.py
"""
import json, math, random
from pathlib import Path

import os
SALIDA = Path(__file__).parent.parent / "resultados" / "boe.json"
AQUI = Path(os.environ.get("BOE_DATOS", Path(__file__).parent))   # carpeta con prueba.jsonl, eval/ y eval-kev/
SIN_AJUSTAR = {"jev-v1": "Jev-style v1 · 2B", "jev-v3": "Jev-style v3 · 0.8B", "kev-08b": "Kev · 0.8B",
               "kev-4b": "Kev · 4B", "llm-9b": "Qwen3.5 · 9B (letras)"}
AJUSTADOS = {"ajustado08b": "Kev · 0.8B ajustado", "ajustado4b": "Kev · 4B ajustado"}
ORIGINAL_DE = {"ajustado08b": "base08b", "ajustado4b": "base4b"}   # el mismo modelo sin ajustar, medido igual
N_CONTROL = 12   # control.py: las 12 pruebas de laboratorio/casos.py
CONTROL_DE = {"kev-08b": "base08b", "kev-4b": "base4b", "ajustado08b": "ajustado08b", "ajustado4b": "ajustado4b"}


def leer(p):
    try:
        return json.loads(p.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def media_por_apartado(top, etiqueta, indices=None):
    indices = range(len(etiqueta)) if indices is None else indices
    por = {}
    for i in indices:
        por.setdefault(etiqueta[i], []).append(top[i] == etiqueta[i])
    return sum(sum(v) / len(v) for v in por.values()) / len(por)


def comparar(a, b, etiqueta):
    """Diferencia de la media por apartado entre a y b, con intervalo de confianza por bootstrap pareado."""
    rnd, n, difs = random.Random(0), len(etiqueta), []
    for _ in range(2000):
        idx = [rnd.randrange(n) for _ in range(n)]
        if len({etiqueta[i] for i in idx}) == len(set(etiqueta)):
            difs.append(media_por_apartado(a, etiqueta, idx) - media_por_apartado(b, etiqueta, idx))
    difs.sort()
    return {"diferencia": media_por_apartado(a, etiqueta) - media_por_apartado(b, etiqueta),
            "ic95": [difs[int(.025 * len(difs))], difs[int(.975 * len(difs))]]}


casos = [json.loads(l) for l in (AQUI / "prueba.jsonl").read_text().splitlines() if l.strip()]
apartados = list(casos[0]["questions"]["apartado"]["criteria"])
etiqueta = [apartados.index(c["questions"]["apartado"]["label"]) for c in casos]
por_id = {c["id"]: i for i, c in enumerate(casos)}

dist = {}   # id de modelo -> (nombre, ajustado, [probabilidad por apartado, por caso], mediana de ms)
for mid, nombre in SIN_AJUSTAR.items():
    filas = [json.loads(l) for l in (AQUI / "eval" / f"{mid}.jsonl").read_text().splitlines()] if (AQUI / "eval" / f"{mid}.jsonl").exists() else []
    d, ms = [None] * len(casos), []
    for r in filas:
        if "ranking" in r and r["id"] in por_id:
            p = dict(r["ranking"])
            d[por_id[r["id"]]] = [p.get(a, 0) for a in apartados]
            ms.append(r["ms"])
    if all(d):
        dist[mid] = (nombre, False, d, sorted(ms)[len(ms) // 2])
for mid in list(AJUSTADOS) + list(ORIGINAL_DE.values()):
    filas = leer(AQUI / "eval-kev" / f"{mid}-prueba" / "rows.json")
    if isinstance(filas, list) and len(filas) == len(casos):   # evaluate_records respeta el orden de prueba.jsonl
        dist[mid] = (AJUSTADOS.get(mid, mid), mid in AJUSTADOS, [r["p"] for r in filas], None)
top = {m: [max(range(len(p)), key=p.__getitem__) for p in v[2]] for m, v in dist.items()}

modelos = []
for mid, (nombre, ajustado, d, ms) in dist.items():
    if mid in ORIGINAL_DE.values():
        continue   # los originales medidos con el evaluador de Kev solo sirven de pareja para comparar
    clases = [[sum(1 for i, e in enumerate(etiqueta) if e == k and top[mid][i] == k), etiqueta.count(k)] for k in range(len(apartados))]
    conf = {}
    for i, e in enumerate(etiqueta):
        if top[mid][i] != e:
            conf[(e, top[mid][i])] = conf.get((e, top[mid][i]), 0) + 1
    ctrl = leer(AQUI / "eval-kev" / f"{CONTROL_DE.get(mid, '-')}-control" / "rows.json")
    if isinstance(ctrl, list):
        ctrl = ctrl[-N_CONTROL:]   # las 12 pruebas públicas van al final (un control local puede llevar casos propios delante)
    modelos.append({"id": mid, "nombre": nombre, "ajustado": ajustado, "ms": ms, "clases": clases,
                    "media": media_por_apartado(top[mid], etiqueta),
                    "logloss": sum(-math.log(max(p[e], 1e-6)) for p, e in zip(d, etiqueta)) / len(casos),
                    "confusiones": [[apartados[a], apartados[b], n] for (a, b), n in sorted(conf.items(), key=lambda x: -x[1])[:4]],
                    "control": [sum(max(range(len(x["p"])), key=x["p"].__getitem__) == int(x["label"]) for x in ctrl), len(ctrl)]
                               if isinstance(ctrl, list) and ctrl else None})

# lo que costó cada ajuste, de los propios registros de Kev (runs/<nombre>/training_metrics.json y training_config.json)
EQUIPO = os.environ.get("EQUIPO", "Mac mini con M4 Pro y 24 GB de memoria unificada")
for m in modelos:
    met, cfg = leer(AQUI / "runs" / m["id"] / "training_metrics.json"), leer(AQUI / "runs" / m["id"] / "training_config.json")
    if m["ajustado"] and met and cfg:
        a = cfg["args"]
        m["ajuste"] = {"equipo": EQUIPO, "segundos": round(met["wall_seconds"]), "epocas": a["epochs"],
                       "ejemplos_propios": sum(1 for _ in open(AQUI / "entrenamiento.jsonl")) if (AQUI / "entrenamiento.jsonl").exists() else None,
                       "ejemplos_repaso": a.get("replay"), "ejemplos_procesados": met["records_seen"], "tokens": met["forward_tokens"],
                       "s_por_ejemplo": round(met["wall_seconds"] / met["records_seen"], 2),
                       "memoria_gpu_gb": round(met["peak_device_bytes"] / 1e9, 1), "memoria_proceso_gb": round(met["peak_rss_bytes"] / 1e9, 1),
                       "parametros_entrenados": "LoRA de rango %d" % a["lora"], "base_en_media_precision": a.get("weights_dtype") == "bf16"}

comparaciones = []
for aj, orig in ORIGINAL_DE.items():
    if aj in top and orig in top:
        comparaciones.append({"a": aj, "b": orig, "texto": f"{AJUSTADOS[aj]} frente al mismo modelo sin ajustar", **comparar(top[aj], top[orig], etiqueta)})
mejor_sin = max((m for m in modelos if not m["ajustado"]), key=lambda m: m["media"], default=None)
for aj in AJUSTADOS:
    if aj in top and mejor_sin:
        comparaciones.append({"a": aj, "b": mejor_sin["id"], "texto": f"{AJUSTADOS[aj]} frente a {mejor_sin['nombre']}",
                              **comparar(top[aj], top[mejor_sin["id"]], etiqueta)})

SALIDA.parent.mkdir(exist_ok=True)
SALIDA.write_text(json.dumps({
    "pregunta": casos[0]["questions"]["apartado"]["instructions"], "apartados": apartados, "n": len(casos),
    "periodo_prueba": "julio y agosto de 2026", "periodo_entrenamiento": "enero a junio de 2026",
    "fuente": "Agencia Estatal Boletín Oficial del Estado (boe.es), datos abiertos",
    "modelos": sorted(modelos, key=lambda m: -m["media"]), "comparaciones": comparaciones,
    "casos": [{"id": c["id"], "etiqueta": etiqueta[i]} for i, c in enumerate(casos)],
    "respuestas": {m["id"]: top[m["id"]] for m in modelos},
}, ensure_ascii=False, indent=1))
print(f"{SALIDA}: {len(modelos)} modelos;", "; ".join(f"{m['nombre']} {m['media']:.0%}" for m in sorted(modelos, key=lambda m: -m["media"])))
for c in comparaciones:
    print(f"  {c['texto']}: {c['diferencia']:+.0%} (IC 95 % {c['ic95'][0]:+.0%} a {c['ic95'][1]:+.0%})")
