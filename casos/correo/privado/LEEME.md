# Prueba privada del triaje de correo

La parte pública de esta prueba usa correos sintéticos. Esta es la otra mitad: **correos reales** de un buzón general,
que se miden en tu máquina y **nunca se publican**. Solo salen las cifras agregadas (acierto, calibración, nota).
Todo lo que pongas en esta carpeta, salvo este fichero, está excluido de git (`.gitignore`).

## Qué hace falta

Entre 80 y 150 correos reales, de varias semanas, sin elegirlos a mano (por ejemplo, todos los de unos días concretos),
para que la muestra se parezca al buzón de verdad. Un fichero `correos.jsonl`, una línea por correo:

```json
{"id": "r-001", "correo": "De: …\nFecha: …\nAsunto: …\n\n<cuerpo>", "unidad": "…", "tipo": "…", "urgente": false}
```

Las etiquetas, con los mismos valores exactos que la prueba pública (ver `casos/DISENO.md`). Si tu organismo tiene otras
unidades, se puede hacer una versión propia de la pregunta, pero entonces la nota no es comparable con la pública.

**Quién etiqueta:** alguien que lleve el buzón, sin ver las respuestas de ningún modelo. Si son dos personas, mejor:
los correos en que no coincidan dicen cuánto de difícil es la tarea incluso para una persona.

## Antes de nada: anonimizar

Aunque los datos no salgan de la máquina, trabaja con copias anonimizadas: cambia nombres, DNI, direcciones,
teléfonos, correos y números de expediente por marcadores (`[NOMBRE]`, `[DNI]`, `[DIRECCIÓN]`…). Revisa también los
adjuntos citados en el cuerpo y las firmas. Si hay categorías especiales de datos (salud, datos de menores, víctimas),
es mejor dejar fuera esos correos que confiar en la anonimización.

## Cómo se mide

`python casos/evaluar.py correo privado` (cuando exista) usa los mismos modelos y reglas de nota que la prueba pública y
escribe solo cifras agregadas en `privado/resultados.json`.
