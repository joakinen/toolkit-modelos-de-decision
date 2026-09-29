"""Tiempo por decisión de cada herramienta, medido aparte y con la máquina descargada: los tiempos que guarda
evaluar.py dependen de lo que hubiera en marcha a la vez (en la primera medida, varios modelos compartían memoria).

Mide un modelo cada vez sobre los mismos 30 correos de casos/correo/prueba.jsonl (las tres preguntas de cada uno) y da
la mediana de segundos por correo, después de dos correos de calentamiento. Para los embeddings cuenta también el cálculo
del vector (sin caché); para el clasificador clásico, solo la predicción, porque se entrena una vez.
Uso: python casos/tiempos.py <modelo> [...]   -> añade o actualiza su línea en casos/tiempos.json
"""
import json, statistics, sys, time
from pathlib import Path

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(AQUI.parent))
from evaluar import POR_ID, PROTOCOLO, por_letras, por_protocolo  # noqa: E402

N, CALIENTES = 30, 2
leer = lambda n: [json.loads(l) for l in (AQUI / "correo" / f"{n}.jsonl").read_text().splitlines() if l.strip()]
prueba = leer("prueba")[:N + CALIENTES]
salida = AQUI / "tiempos.json"
tiempos = json.loads(salida.read_text()) if salida.exists() else {}

for mid in sys.argv[1:]:
    medidas = []
    if mid == "clasico":   # se entrena una vez (segundos) y se cronometra solo la predicción de cada correo
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline
        from evaluar import etiqueta
        ent = leer("entrenamiento")
        modelos = [make_pipeline(TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True), LogisticRegression(C=10, max_iter=5000))
                   .fit([c["state"] for c in ent], [etiqueta(c["questions"][q]) for c in ent]) for q in prueba[0]["questions"]]
        for c in prueba:
            t0 = time.perf_counter(); [m.predict_proba([c["state"]]) for m in modelos]; medidas.append(time.perf_counter() - t0)
    elif mid == "embeddings":
        import embeddings as E
        import tempfile
        E.CACHE = Path(tempfile.mkdtemp())   # caché vacía: fuerza el cálculo del vector
        for i, c in enumerate(prueba):
            t0 = time.perf_counter(); E.vectores([c["state"] + f" [{time.time()}]"]); medidas.append(time.perf_counter() - t0)
    else:
        if not POR_ID[mid]["ok"]():
            print(mid, "no responde"); continue
        f = por_protocolo if mid in PROTOCOLO else por_letras
        for c in prueba:
            t0 = time.perf_counter(); f(mid, c); medidas.append(time.perf_counter() - t0)
    s = statistics.median(medidas[CALIENTES:])
    tiempos[mid] = {"segundos_por_correo": round(s, 3), "correos": N, "preguntas_por_correo": 3}
    print(f"{mid}: {s:.3f} s por correo (mediana de {N})", flush=True)
salida.write_text(json.dumps(tiempos, indent=1))
