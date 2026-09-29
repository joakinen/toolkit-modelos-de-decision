"""Convierte los textos etiquetados de un caso (<caso>/{entrenamiento,prueba}-textos.jsonl) en peticiones con el
formato del protocolo de TypeSafe (state + questions, con la etiqueta en cada pregunta), las mismas para todos los
modelos. Las preguntas y sus opciones se fijan aquí, una sola vez, tal como están en DISENO.md.
Uso: python construir.py correo|expedientes   -> <caso>/entrenamiento.jsonl y <caso>/prueba.jsonl
"""
import json, sys
from pathlib import Path

AQUI = Path(__file__).parent

UNIDADES = {
    "Atención ciudadana y registro": "Información general, citas, registro de documentos, padrón y certificados",
    "Tributos y recaudación": "Impuestos y tasas municipales, recibos, bonificaciones, embargos y devoluciones",
    "Urbanismo y obras": "Licencias de obra, disciplina urbanística, vía pública, edificios y obras municipales",
    "Servicios sociales": "Ayudas sociales, dependencia, ayuda a domicilio, personas vulnerables",
    "Recursos humanos": "Personal del ayuntamiento, oposiciones, bolsas de empleo, nóminas",
    "Contratación": "Licitaciones, contratos públicos, proveedores y sus facturas",
    "Sede electrónica e informática": "Sede electrónica, certificados digitales, pagos en línea, avisos de fraude informático",
    "Ninguna (no es competencia municipal, o es publicidad)": "Asuntos de otras administraciones o empresas, y publicidad",
}
TIPOS = {
    "Solicitud de información": "Pregunta algo, sin iniciar un trámite",
    "Trámite o solicitud": "Pide que se haga algo o inicia un procedimiento",
    "Queja o reclamación": "Protesta por un servicio, un daño o una actuación",
    "Respuesta a un requerimiento": "Contesta a algo que le pidió antes la administración",
    "Publicidad o correo no deseado": "Ofertas comerciales, cadenas, fraudes que no preguntan nada",
}
URGENTE = ("¿Es urgente? Lo es si hay un plazo que vence en menos de una semana desde la fecha del correo, un riesgo "
           "para personas o un servicio caído; no basta con que el correo diga que es urgente.")
SNC = ["sí", "no", "no consta"]
REPRESENTACION = ["el interesado en nombre propio", "un representante con autorización aportada",
                  "un representante sin autorización aportada"]


def correo(r):
    return {"id": r["id"], "dificil": r["dificil"], "state": r["correo"], "questions": {
        "unidad": {"type": "choice", "instructions": "¿A qué unidad del ayuntamiento corresponde este correo?",
                   "criteria": UNIDADES, "label": r["unidad"]},
        "tipo": {"type": "choice", "instructions": "¿Qué es este correo?", "criteria": TIPOS, "label": r["tipo"]},
        "urgente": {"type": "noul", "instructions": URGENTE, "label": r["urgente"]}}}


def expediente(r):
    q = lambda texto, opciones, etiqueta: {"type": "choice", "instructions": texto,
                                           "criteria": {o: None for o in opciones}, "label": etiqueta}
    return {"id": r["id"], "dificil": r["dificil"], "state": r["texto"], "questions": {
        "pago": q("¿Consta el pago de la tasa de este trámite?", SNC, r["pago"]),
        "firma": q("¿Está firmada la solicitud?", SNC, r["firma"]),
        "identidad": q("¿Se aporta el documento de identidad, válido, del interesado (el titular del trámite, no su "
                       "representante)?", SNC, r["identidad"]),
        "representacion": q("¿Quién presenta la solicitud?", REPRESENTACION, r["representacion"])}}


caso = sys.argv[1]
convertir = {"correo": correo, "expedientes": expediente}[caso]
for parte in ("entrenamiento", "prueba"):
    filas = [convertir(json.loads(l)) for l in (AQUI / caso / f"{parte}-textos.jsonl").read_text().splitlines() if l.strip()]
    for f in filas:   # toda etiqueta tiene que ser una de las opciones
        for qid, q in f["questions"].items():
            assert q["type"] == "noul" or q["label"] in q["criteria"], (f["id"], qid, q["label"])
    with open(AQUI / caso / f"{parte}.jsonl", "w", encoding="utf-8") as out:
        for f in filas:
            out.write(json.dumps(f, ensure_ascii=False) + "\n")
    print(caso, parte, len(filas))
