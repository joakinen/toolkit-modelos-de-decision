"""Conjunto «apartado del BOE» construido desde la API pública del BOE (datos abiertos, reutilizables citando la fuente).

La etiqueta es la sección del sumario en que se publicó cada texto: la pone el propio BOE, así que es correcta por
construcción. Al modelo se le da solo el cuerpo del texto, sin el título (que a menudo delata la sección).

Decisiones fijadas el 27-sep-2026 antes de medir ningún modelo:
- periodo de entrenamiento enero-junio de 2026 y de prueba julio-agosto de 2026 (reparto temporal: el ajuste nunca ve
  un texto del periodo de prueba);
- como mucho 3 textos por «plantilla» (título sin cifras ni fechas, primeros 70 caracteres), para que no dominen los
  textos casi idénticos (cambios del euro, subastas, etc.); textos de menos de 150 caracteres fuera;
- recorte a los primeros 2.000 caracteres, cortando en el último final de frase o de párrafo (igual que en LexBOE);
- 50 por apartado en la prueba y hasta 200 por apartado en el entrenamiento, semilla 0; las opciones son las secciones
  del sumario con su nombre oficial, en el orden del BOE.

Uso: python construir.py sumarios            descarga los sumarios de enero a septiembre (un día por segundo, con caché)
     python construir.py prueba              elige la muestra de prueba y descarga sus textos -> prueba.jsonl
     python construir.py entrenamiento       lo mismo para el entrenamiento -> entrenamiento.jsonl
     python construir.py calibracion         20 por apartado de septiembre, para recalibrar -> calibracion.jsonl
"""
import datetime as dt, json, random, re, sys, time, urllib.error, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

AQUI = Path(__file__).parent
SUMARIOS, TEXTOS = AQUI / "datos/sumarios", AQUI / "datos/textos"
PREGUNTA = "¿En qué apartado del BOE se publica este texto?"
APARTADOS = {  # código del sumario -> nombre oficial de la sección
    "1": "I. Disposiciones generales",
    "2A": "II.A. Autoridades y personal: nombramientos, situaciones e incidencias",
    "2B": "II.B. Autoridades y personal: oposiciones y concursos",
    "3": "III. Otras disposiciones",
    "4": "IV. Administración de Justicia",
    "5A": "V.A. Anuncios: contratación del sector público",
    "5B": "V.B. Anuncios: otros anuncios oficiales",
}  # V.C (anuncios particulares) y Tribunal Constitucional no publican nada en enero-agosto de 2026: fuera de las opciones
PERIODOS = {"entrenamiento": (dt.date(2026, 1, 1), dt.date(2026, 6, 30), 200),
            "prueba": (dt.date(2026, 7, 1), dt.date(2026, 8, 31), 50),
            # añadido el 28-sep-2026 para recalibrar los ajustados: textos de después de la prueba, sin solape con nada
            "calibracion": (dt.date(2026, 9, 1), dt.date(2026, 9, 27), 20)}
# las peticiones se identifican con el proyecto, no con el nombre genérico de Python (cortesía con el servidor del BOE)
AGENTE = "laboratorio-decisiones/1.0 (evaluacion local de modelos de decision; reutilizacion de datos abiertos del BOE)"
POR_PLANTILLA, MIN_CARACTERES, MAX_CARACTERES, SEMILLA = 3, 150, 2000, 0


def pedir(url, json_=False):
    for intento in range(4):
        try:
            cab = {"User-Agent": AGENTE, **({"Accept": "application/json"} if json_ else {})}
            req = urllib.request.Request(url, headers=cab)
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None                                       # domingos y festivos no hay BOE
            time.sleep(2 ** intento)
        except (urllib.error.URLError, TimeoutError):
            time.sleep(2 ** intento)
    raise RuntimeError(f"no se pudo descargar {url}")


def lista(x):
    return x if isinstance(x, list) else ([x] if x else [])


def sumarios():
    SUMARIOS.mkdir(parents=True, exist_ok=True)
    d, fin = PERIODOS["entrenamiento"][0], max(p[1] for p in PERIODOS.values())
    while d <= fin:
        f = SUMARIOS / f"{d:%Y%m%d}.json"
        if not f.exists():
            txt = pedir(f"https://www.boe.es/datosabiertos/api/boe/sumario/{d:%Y%m%d}", json_=True)
            f.write_text(txt or "{}")
            time.sleep(1)
        d += dt.timedelta(days=1)


def items(desde, hasta):
    """Todos los textos publicados entre dos fechas: (fecha, id, apartado, departamento, título)."""
    out = []
    for f in sorted(SUMARIOS.glob("*.json")):
        fecha = dt.datetime.strptime(f.stem, "%Y%m%d").date()
        if not desde <= fecha <= hasta:
            continue
        d = json.loads(f.read_text() or "{}")
        for diario in lista(d.get("data", {}).get("sumario", {}).get("diario")):
            for sec in lista(diario.get("seccion")):
                if sec.get("codigo") not in APARTADOS:
                    continue
                for dep in lista(sec.get("departamento")):
                    for bloque in lista(dep.get("epigrafe")) + [dep]:
                        for it in lista(bloque.get("item")):
                            if isinstance(it, dict) and it.get("identificador"):
                                out.append((f.stem, it["identificador"], sec["codigo"], dep.get("nombre", ""), it.get("titulo", "")))
    return out


def plantilla(titulo):
    t = re.sub(r"\d+", "#", titulo.lower())
    t = re.sub(r"\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\b", "M", t)
    return t[:70]


def cuerpo(ident):
    """Texto del cuerpo: el <texto> hijo directo de <documento>. Las leyes llevan antes, en su análisis, referencias
    a otras normas que también se llaman <texto>; por eso no vale buscar la primera etiqueta."""
    f = TEXTOS / f"{ident}.xml"
    if not f.exists():
        f.write_text(pedir(f"https://www.boe.es/diario_boe/xml.php?id={ident}") or "")
        time.sleep(1)
    try:
        nodo = ET.fromstring(f.read_text()).find("texto")
    except ET.ParseError:
        return ""
    if nodo is None:
        return ""
    # párrafos, celdas y las listas «campo: valor» de los anuncios de contratación (<dt>/<dd>); solo los elementos más
    # internos, para no repetir el texto de las listas anidadas
    bloques = ("p", "td", "dt", "dd", "li")
    hojas = [e for e in nodo.iter() if e.tag in bloques and not any(h.tag in bloques for h in e.iter() if h is not e)]
    return "\n".join(t for t in (" ".join(" ".join(e.itertext()).split()) for e in hojas) if t)


def recortar(texto):
    t = re.sub(r"[ \t  ]+", " ", texto)
    t = re.sub(r"\n\s*\n+", "\n", t).strip()
    if len(t) <= MAX_CARACTERES:
        return t
    corte = t[:MAX_CARACTERES]
    fin = max(corte.rfind(". "), corte.rfind(".\n"), corte.rfind("\n"))
    return corte[: fin + 1].strip() if fin > MAX_CARACTERES // 2 else corte.rstrip() + "…"


def muestra(nombre):
    TEXTOS.mkdir(parents=True, exist_ok=True)
    desde, hasta, n = PERIODOS[nombre]
    rnd = random.Random(SEMILLA)
    todos = items(desde, hasta)
    rnd.shuffle(todos)
    elegidos, por_apartado, por_plantilla = [], {}, {}
    for fecha, ident, sec, dep, titulo in todos:
        if por_apartado.get(sec, 0) >= n:
            continue
        p = (sec, plantilla(titulo))
        if por_plantilla.get(p, 0) >= POR_PLANTILLA:
            continue
        texto = recortar(cuerpo(ident))
        if len(texto) < MIN_CARACTERES:
            continue
        por_plantilla[p] = por_plantilla.get(p, 0) + 1
        por_apartado[sec] = por_apartado.get(sec, 0) + 1
        elegidos.append({"id": ident, "fecha": fecha, "departamento": dep, "titulo": titulo, "state": texto,
                         "questions": {"apartado": {"type": "choice", "instructions": PREGUNTA,
                                                    "criteria": {v: None for v in APARTADOS.values()},
                                                    "label": APARTADOS[sec]}}})
        if len(elegidos) % 50 == 0:
            print(len(elegidos), "textos", dict(sorted(por_apartado.items())), flush=True)
    with open(AQUI / f"{nombre}.jsonl", "w", encoding="utf-8") as out:
        for e in elegidos:
            out.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(nombre, len(elegidos), "textos;", "disponibles por apartado:",
          {s: sum(1 for x in todos if x[2] == s) for s in APARTADOS}, "elegidos:", dict(sorted(por_apartado.items())))


if __name__ == "__main__":
    {"sumarios": sumarios, "prueba": lambda: muestra("prueba"), "entrenamiento": lambda: muestra("entrenamiento"),
     "calibracion": lambda: muestra("calibracion")}[sys.argv[1]]()
