"""Ajusta la temperatura de cada modelo ajustado con la mezcla de calibración y la deja en calibracion.json.

Usa el mismo ajuste que Kev (kev.metrics.fit_temperature con TEMPERATURE_FIT: la temperatura que minimiza la log-loss
media en una rejilla de 0,25 a 4) sobre las filas de eval-kev/<modelo>-calibracion (medidas por ajustar.sh a
temperatura 1,0). Como diagnóstico da también:
- la temperatura sin el tope de 4 (rejilla hasta 32) y cuánta log-loss se pierde por el tope;
- la que pediría cada parte de la mezcla por separado (BOE, generales, español): si difieren mucho, una sola
  temperatura no puede calibrar bien las tres;
- una estimación fuera de muestra (validación cruzada por grupos de Kev) sobre la propia mezcla.

La temperatura no cambia la respuesta más probable, así que el acierto no cambia. No escribe nada en el modelo: si el
resultado convence, se escribe con el script de Kev (el comando se imprime al final). En la prueba publicada se escribió
en el 4B (su temperatura óptima queda en el tope y apenas pierde nada) y no en el 0.8B (pide más de 7 y cada parte de
la mezcla una distinta).

Uso, con el entorno de Kev:  cd $KEV_DIR && uv run python /ruta/a/boe/calibrar.py
"""
import json, os, sys
from pathlib import Path

import numpy as np
from kev.metrics import TEMPERATURE_FIT, cross_validated_temperature, fit_temperature, nll_at_temperature, raw_row

AQUI = Path(os.environ.get("BOE_DATOS", Path(__file__).parent))
N_BOE = sum(1 for _ in open(AQUI / "calibracion.jsonl", encoding="utf-8")) if (AQUI / "calibracion.jsonl").exists() else 140
N_GEN = 200   # orden de calibracion-mezcla.jsonl: BOE, generales, español
REJILLA_AMPLIA = np.exp(np.linspace(np.log(0.25), np.log(32), 241))


def parte(fila):
    i = int(fila["id"].split("/")[1])
    return "BOE" if i < N_BOE else "generales" if i < N_BOE + N_GEN else "español"


def nll(filas, t):
    return float(np.mean([nll_at_temperature(f, t) for f in filas]))


def sin_tope(filas):
    valores = [nll(filas, t) for t in REJILLA_AMPLIA]
    return float(REJILLA_AMPLIA[int(np.argmin(valores))]), float(min(valores))


resultado = {}
for modelo in ("ajustado08b", "ajustado4b"):
    ruta = AQUI / "eval-kev" / f"{modelo}-calibracion" / "rows.json"
    if not ruta.exists():
        continue
    filas = [raw_row(f) for f in json.loads(ruta.read_text()) if f.get("variant", "clean") == "clean"]
    t = fit_temperature(filas, **TEMPERATURE_FIT)
    t_libre, nll_libre = sin_tope(filas)
    cv = cross_validated_temperature(filas, **TEMPERATURE_FIT)
    resultado[modelo] = {
        "temperatura": t, "preguntas": len(filas), "nll_con_temperatura": nll(filas, t),
        "temperatura_sin_tope": t_libre, "nll_sin_tope": nll_libre,
        "temperatura_por_parte": {p: sin_tope([f for f in filas if parte(f) == p])[0] for p in ("BOE", "generales", "español")},
        "fuera_de_muestra": {"ece_sin_calibrar": cv["raw"]["ece"], "ece_calibrado": cv["out_of_fold"]["ece"],
                             "temperaturas_por_pliegue": cv["temperatures"]}}
    r = resultado[modelo]
    print(f"{modelo}: T = {t:.2f} (log-loss {r['nll_con_temperatura']:.3f}); sin tope T = {t_libre:.2f} (log-loss {nll_libre:.3f});"
          f" por parte " + ", ".join(f"{p} {v:.2f}" for p, v in r["temperatura_por_parte"].items()) +
          f"; fuera de muestra ECE {r['fuera_de_muestra']['ece_sin_calibrar']:.3f} -> {r['fuera_de_muestra']['ece_calibrado']:.3f}")
    print(f"  para escribirla: uv run python scripts/calibrate_checkpoint.py --run {AQUI / 'runs' / modelo} --rows {ruta}")

(AQUI / "calibracion.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=1))
print(AQUI / "calibracion.json")
