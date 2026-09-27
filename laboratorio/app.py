"""Laboratorio de modelos de decisión: una web local para comparar varios modelos con los mismos casos.

Cada modelo corre en su propio servidor en esta máquina (Ollama, servidores Kev, llama.cpp) y esta app hace de
intermediaria. Arranque:  uv run uvicorn app:app --host 127.0.0.1 --port 8090
Configuración por variables de entorno (todas opcionales):
  OLLAMA_URL      por defecto http://127.0.0.1:11434
  KEV_08B_PORT    por defecto 8008   (python -m kev.serve --run jaredpalmer/kev-0.8b --port 8008)
  KEV_4B_PORT     por defecto 8009
  JEV_V3_DIR      carpeta de Jev-style v3 con jev-score compilado; sin ella ese modelo aparece como «no responde»
Un modelo que no esté en marcha aparece como parado; el resto funciona igual.
"""
import json, math, os, statistics, sys, threading, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from casos import CASOS, TRIAJES

AQUI = Path(__file__).parent
RESULTADOS = AQUI / "resultados.json"                     # los tuyos, se crean al ejecutar las pruebas
REFERENCIA = AQUI / "resultados-referencia.json"          # los de referencia, mientras no tengas los tuyos
RESULTADOS_BOE = AQUI.parent / "resultados" / "boe.json"  # agregados, sin textos (boe/exportar.py)
V3_DIR = Path(os.environ.get("JEV_V3_DIR", Path.home() / "jev-v3-gguf"))
OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
KEV_08B_PORT = int(os.environ.get("KEV_08B_PORT", 8008))
KEV_4B_PORT = int(os.environ.get("KEV_4B_PORT", 8009))
V1_MODEL = "hf.co/chaoliangUNSW/Jev-Style-Qwen3.5-2B-Decision-GGUF:Q8_0"
LETRAS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
PROMPT_V1 = """You are a decision function. Read the state, then answer the question by choosing exactly one option.

[State]
{state}

[Question]
{question}

[Options]
{options}

Answer:"""


def post_json(url, body, timeout=120):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def get_json(url, timeout=3):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.load(r)


# ---------- ejecutores: cada uno recibe (estado, [(id, pregunta, opciones)]) y devuelve {id: [(opción, p), ...]} ----------

def _dist_letras(top_logprobs, options):
    """Probabilidad de cada opción a partir de la del primer token (A, B, C...), renormalizada sobre las letras válidas."""
    p = {}
    for c in top_logprobs:
        tok = c["token"].strip()
        if len(tok) == 1 and tok in LETRAS[: len(options)]:
            p[tok] = p.get(tok, 0) + math.exp(c["logprob"])
    z = sum(p.values()) or 1
    return sorted(((o, p.get(LETRAS[i], 0) / z) for i, o in enumerate(options)), key=lambda x: -x[1])


def run_v1(state, questions):
    out = {}
    for qid, question, options in questions:
        opts = "\n".join(f"{LETRAS[i]}. {o}" for i, o in enumerate(options))
        r = post_json(f"{OLLAMA}/api/generate", {
            "model": V1_MODEL, "prompt": PROMPT_V1.format(state=state, question=question, options=opts),
            "raw": True, "stream": False, "logprobs": True, "top_logprobs": 20,
            "options": {"num_predict": 1, "temperature": 0}})
        out[qid] = _dist_letras(r["logprobs"][0]["top_logprobs"], options)
    return out


# Modelo general, sin ajustar, convertido en «modelo de decisión» con el truco de las letras
# (https://allanrbo.blogspot.com/2026/09/a-jev-like-wrapper-for-llms-including.html)
LLM_MODEL = "qwen3.5:9b"
PROMPT_LLM = """Read the state and answer the question by choosing exactly one option. Reply with the option letter only.

[State]
{state}

[Question]
{question}

[Options]
{options}"""


def run_llm(state, questions):
    out = {}
    for qid, question, options in questions:
        opts = "\n".join(f"{LETRAS[i]}. {o}" for i, o in enumerate(options))
        r = post_json(f"{OLLAMA}/api/chat", {
            "model": LLM_MODEL, "think": False, "stream": False, "logprobs": True, "top_logprobs": 20,
            "messages": [{"role": "user", "content": PROMPT_LLM.format(state=state, question=question, options=opts)}],
            "options": {"num_predict": 1, "temperature": 0}}, timeout=300)
        out[qid] = _dist_letras(r["logprobs"][0]["top_logprobs"], options)
    return out


_v3, _v3_lock = None, threading.Lock()


def run_v3(state, questions):
    global _v3
    with _v3_lock:
        if _v3 is None:
            sys.path.insert(0, str(V3_DIR))
            from jev_style_decision_gguf import JevStyleDecisionGGUF
            _v3 = JevStyleDecisionGGUF(str(V3_DIR), quant="Q4_K_M")
        out = {}
        for qid, question, options in questions:
            r = _v3.decide(state, question, options=options)
            out[qid] = sorted(r["probabilities"].items(), key=lambda x: -x[1])
        return out


def kev_runner(port):
    def run(state, questions):
        # Kev responde todas las preguntas sobre el mismo estado en una sola pasada
        body = {"model": "kev-latest", "state": state, "questions": {
            qid: {"type": "choice", "instructions": q, "criteria": {o: None for o in opts}} for qid, q, opts in questions}}
        r = post_json(f"http://127.0.0.1:{port}/v1/systemone", body)
        answers = r.get("answers", r)
        return {qid: sorted(answers[qid]["probabilities"].items(), key=lambda x: -x[1]) for qid, _, _ in questions}
    return run


def ok_v1():
    return any(m["name"] == V1_MODEL for m in get_json(f"{OLLAMA}/api/tags")["models"])


def ok_llm():
    return any(m["name"] == LLM_MODEL for m in get_json(f"{OLLAMA}/api/tags")["models"])


def ok_v3():
    return (V3_DIR / "build/jev-score").exists()


def ok_kev(port):
    return lambda: bool(get_json(f"http://127.0.0.1:{port}/v1/models")["models"])


MODELOS = [
    {"id": "jev-v1", "nombre": "Jev-style v1 · 2B", "run": run_v1, "ok": ok_v1,
     "motor": "Ollama (GGUF Q8_0, 2,1 GB)", "autor": "chaoliangUNSW",
     "fuente": "https://huggingface.co/chaoliangUNSW/Jev-Style-Qwen3.5-2B-Decision-GGUF",
     "resumen": "Qwen3.5-2B ajustado para responder con la letra de la opción. Se lee la probabilidad del siguiente token y se renormaliza sobre las letras. No instala nada nuevo: usa el Ollama de siempre."},
    {"id": "jev-v3", "nombre": "Jev-style v3 · 0.8B", "run": run_v3, "ok": ok_v3,
     "motor": "llama.cpp + jev-score (GGUF Q4_K_M, 0,53 GB)", "autor": "chaoliangUNSW",
     "fuente": "https://huggingface.co/chaoliangUNSW/Jev-Style-0.8B-Decision-v3-GGUF",
     "resumen": "Versión nueva y más pequeña del mismo autor: 51 idiomas y contexto de 25.600 tokens. Lee un «hueco de veredicto» por opción, así que necesita su propio programa (jev-score) compilado contra llama.cpp."},
    {"id": "kev-08b", "nombre": "Kev · 0.8B", "run": kev_runner(KEV_08B_PORT), "ok": ok_kev(KEV_08B_PORT),
     "motor": "Servidor Kev (MLX en Apple Silicon, PyTorch en el resto)", "autor": "jaredpalmer",
     "fuente": "https://huggingface.co/jaredpalmer/kev-0.8b",
     "resumen": "LoRA más una «pointer head» sobre Qwen3.5-0.8B: no genera texto, apunta a una opción. Habla el protocolo de TypeSafe, así que un cliente de Jev funciona cambiando la URL. Calibración incluida (temperatura 2,35)."},
    {"id": "kev-4b", "nombre": "Kev · 4B", "run": kev_runner(KEV_4B_PORT), "ok": ok_kev(KEV_4B_PORT),
     "motor": "Servidor Kev (MLX en Apple Silicon, PyTorch en el resto)", "autor": "jaredpalmer",
     "fuente": "https://huggingface.co/jaredpalmer/kev-4b",
     "resumen": "El mismo diseño sobre Qwen3.5-4B, con entrenamiento extra en documentos reales y en habilidades (fechas, abstención, varios pasos). Es el hermano mayor que la ficha de Kev recomienda para calidad."},
    {"id": "llm-9b", "nombre": "Qwen3.5 · 9B (letras)", "run": run_llm, "ok": ok_llm,
     "motor": "Ollama (qwen3.5:9b, Q4_K_M, 6,6 GB)", "autor": "Qwen (Alibaba)",
     "fuente": "https://ollama.com/library/qwen3.5",
     "resumen": "Modelo de chat general, sin ningún ajuste para decidir. Se le pide que conteste solo con la letra de la opción, se lee la probabilidad de cada letra en el primer token y se renormaliza (el truco de allanrbo.blogspot.com). Sirve de control: ¿un modelo general más grande iguala a un modelo de decisión pequeño y entrenado para ello?"},
]
POR_ID = {m["id"]: m for m in MODELOS}

_lock_res = threading.Lock()


def cargar():
    for f in (RESULTADOS, REFERENCIA):
        try:
            return json.loads(f.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            continue
    return {}


def guardar(caso, modelo, dato):
    with _lock_res:
        try:   # solo los tuyos: la referencia no se mezcla con lo que ejecutes
            res = json.loads(RESULTADOS.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            res = {}
        res.setdefault(caso, {})[modelo] = dato
        RESULTADOS.write_text(json.dumps(res, ensure_ascii=False, indent=1))


def ejecutar(modelo, state, questions):
    m = POR_ID.get(modelo)
    if m is None:
        raise HTTPException(404, f"modelo desconocido: {modelo}")
    t = time.perf_counter()
    try:
        out = m["run"](state, questions)
    except Exception as e:  # el modelo puede estar parado: se informa en la web, no se cae el servidor
        raise HTTPException(503, f"{m['nombre']}: {type(e).__name__}: {e}")
    return out, (time.perf_counter() - t) * 1000


app = FastAPI(title="Laboratorio de decisiones")


@app.get("/")
def index():
    return FileResponse(AQUI / "index.html")


@app.get("/boe.js")
def boe_js():
    return FileResponse(AQUI / "boe.js", media_type="text/javascript")


@app.get("/api/meta")
def meta():
    def estado(m):
        try:
            return bool(m["ok"]())
        except Exception:
            return False
    with ThreadPoolExecutor(4) as ex:
        vivos = list(ex.map(estado, MODELOS))
    return {
        "modelos": [{k: v for k, v in m.items() if k not in ("run", "ok")} | {"activo": a} for m, a in zip(MODELOS, vivos)],
        "casos": [dict(zip(("id", "grupo", "estado", "pregunta", "opciones", "correcta", "mide"), c)) for c in CASOS],
        "triajes": {k: v | {"preguntas": [dict(zip(("id", "pregunta", "opciones"), q)) for q in v["preguntas"]]}
                    for k, v in TRIAJES.items()},
        "resultados": cargar(),
        "referencia": not RESULTADOS.exists(),
    }


class Caso(BaseModel):
    modelo: str
    caso: str


@app.post("/api/caso")
def caso(req: Caso):
    c = next((c for c in CASOS if c[0] == req.caso), None)
    if c is None:
        raise HTTPException(404, "caso desconocido")
    cid, _, state, question, options, correcta, _ = c
    out, ms = ejecutar(req.modelo, state, [("q", question, options)])
    ranking = out["q"]
    dato = {"ranking": ranking, "ms": round(ms), "acierto": ranking[0][0] == correcta,
            "cuando": datetime.now().isoformat(timespec="seconds")}
    guardar(cid, req.modelo, dato)
    return dato


class Pregunta(BaseModel):
    id: str
    pregunta: str
    opciones: list[str]


class Libre(BaseModel):
    modelo: str
    estado: str
    preguntas: list[Pregunta]


@app.post("/api/decidir")
def decidir(req: Libre):
    if not req.estado.strip() or not req.preguntas:
        raise HTTPException(422, "hace falta un texto y al menos una pregunta")
    for p in req.preguntas:
        if len([o for o in p.opciones if o.strip()]) < 2:
            raise HTTPException(422, f"«{p.pregunta}» necesita al menos dos opciones")
    qs = [(p.id, p.pregunta, [o.strip() for o in p.opciones if o.strip()]) for p in req.preguntas]
    out, ms = ejecutar(req.modelo, req.estado, qs)
    return {"respuestas": out, "ms": round(ms)}


@app.get("/api/boe")
def boe():
    """Resultados agregados de la prueba del apartado del BOE (sin textos: los genera boe/exportar.py)."""
    try:
        return json.loads(RESULTADOS_BOE.read_text())
    except FileNotFoundError:
        raise HTTPException(404, "no hay resultados del BOE: ejecuta boe/exportar.py")
