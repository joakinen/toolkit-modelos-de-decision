"""Casos de prueba y triajes que usa la web. Los 12 primeros son los mismos de comparar.py."""

CASOS = [
    # id, grupo, estado, pregunta, opciones, correcta, qué mide
    ("noticia", "fácil", "Shares of the chipmaker jumped 8% after it raised its revenue forecast.",
     "Which news section does this article belong to?", ["World", "Sports", "Business", "Science/Technology"],
     "Business", "El ejemplo de la ficha del GGUF v1: sirve para comprobar que el cliente lee bien las probabilidades."),
    ("refund-en", "fácil", "I was charged twice for my subscription this month and want a refund.",
     "What is the customer's intent?", ["refund", "cancel", "technical issue", "general question"],
     "refund", "El ejemplo de triaje de la portada de Ollaya."),
    ("refund-es", "fácil", "Me han cobrado dos veces la suscripción este mes y quiero que me devolváis el dinero.",
     "¿Cuál es la intención del cliente?", ["reembolso", "baja", "incidencia técnica", "consulta general"],
     "reembolso", "El mismo caso en español: ¿entiende el modelo otro idioma?"),
    ("tramite", "fácil", "Solicito la ampliación del plazo de alegaciones del expediente 2026/0412 por baja médica del interesado.",
     "¿Qué tipo de trámite se solicita?", ["recurso", "ampliación de plazo", "desistimiento", "subsanación de documentación"],
     "ampliación de plazo", "Clasificación de un escrito administrativo."),
    ("frustracion", "fácil", "Llevo tres semanas esperando y nadie me contesta. Es una vergüenza.",
     "¿Está el ciudadano frustrado?", ["sí", "no"], "sí", "Detección de tono."),
    ("negacion-en", "fácil", "The meeting was moved from Tuesday to Thursday.",
     "Is the meeting on Tuesday?", ["yes", "no"], "no", "Negación implícita: «martes» aparece, pero ya no es el día."),
    ("no-baja", "trampa", "No quiero darme de baja, solo que me expliquéis por qué ha subido la cuota este mes.",
     "¿Cuál es la intención del cliente?", ["reembolso", "baja", "incidencia técnica", "consulta general"],
     "consulta general", "La palabra «baja» aparece, pero negada."),
    ("recurso-plazo", "trampa", "El recurso de alzada se presentó el día 3 de octubre; el plazo vencía el 1 de octubre.",
     "¿Se presentó el recurso dentro de plazo?", ["sí", "no"], "no", "Comparar dos fechas."),
    ("ironia", "trampa", "Genial, otra vez sin luz en pleno agosto. Muchas gracias por el servicio, de verdad.",
     "¿Qué sentimiento expresa el mensaje?", ["positivo", "negativo", "neutro"], "negativo",
     "Ironía: todas las palabras son positivas y el mensaje no."),
    ("mas-joven", "trampa", "Ana es mayor que Luis. Luis es mayor que Marta.",
     "¿Quién es la persona más joven?", ["Ana", "Luis", "Marta"], "Marta", "Deducción en dos pasos."),
    ("no-consta", "trampa", "El solicitante adjunta DNI y certificado de empadronamiento.",
     "¿Ha aportado el justificante de pago de la tasa?", ["sí", "no", "no consta"], "no consta",
     "Abstención: el texto no dice nada de la tasa, así que lo correcto es no afirmar ni negar."),
    ("dias-habiles", "trampa",
     "La notificación se recibió el sábado 28 de febrero de 2026. El plazo para alegar es de 10 días hábiles.",
     "¿Sigue abierto el plazo el viernes 20 de marzo de 2026?", ["sí", "no"], "no",
     "Cómputo de días hábiles: el plazo empieza el lunes 2 de marzo y vence el viernes 13."),
]

TRIAJES = {
    "cliente": {
        "nombre": "Atención al cliente",
        "descripcion": "El triaje de la portada de Ollaya, en español: cinco preguntas sobre el mismo mensaje.",
        "ejemplos": [
            "Me han cobrado dos veces la suscripción este mes y quiero que me devolváis el dinero.",
            "Es la tercera vez que se cae la aplicación en plena reunión. Si esto sigue así me voy a la competencia.",
            "Hola, ¿el plan anual incluye la factura con IVA desglosado?",
        ],
        "preguntas": [
            ("intencion", "¿Cuál es la intención del cliente?", ["reembolso", "baja", "incidencia técnica", "consulta general"]),
            ("urgente", "¿Requiere atención urgente?", ["sí", "no"]),
            ("frustracion", "¿Qué nivel de frustración muestra?", ["ninguna", "baja", "media", "alta"]),
            ("pide_reembolso", "¿Pide que le devuelvan dinero?", ["sí", "no"]),
            ("riesgo_baja", "¿Hay riesgo de que se dé de baja?", ["sí", "no"]),
        ],
    },
    "expediente": {
        "nombre": "Escrito de expediente",
        "descripcion": "Un triaje de entrada de escritos: qué se pide, si falta algo y con qué prioridad tramitarlo.",
        "ejemplos": [
            "Solicito la ampliación del plazo de alegaciones del expediente 2026/0412 por baja médica del interesado. Adjunto informe médico.",
            "Llevo tres meses esperando respuesta a mi solicitud de licencia y nadie me contesta. Exijo que se resuelva ya o acudiré al Defensor del Pueblo.",
            "Por la presente desisto de la solicitud de subvención presentada el pasado 4 de mayo.",
        ],
        "preguntas": [
            ("tramite", "¿Qué tipo de trámite se solicita?",
             ["recurso", "ampliación de plazo", "desistimiento", "subsanación de documentación", "queja", "consulta"]),
            ("documentacion", "¿Aporta documentación adjunta?", ["sí", "no", "no consta"]),
            ("plazo", "¿Hay un plazo o fecha límite en juego?", ["sí", "no"]),
            ("tono", "¿Qué tono tiene el escrito?", ["neutro", "molesto", "muy molesto"]),
            ("prioridad", "¿Con qué prioridad debería tramitarse?", ["baja", "normal", "alta"]),
        ],
    },
}
