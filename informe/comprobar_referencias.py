"""Comprueba que cada «sección N («Título»)» del informe apunta a la sección N de verdad: numera los títulos de primer
nivel como lo hace pandoc (sin contar los {.unnumbered} ni lo que hay dentro de bloques de código) y compara. Lo llama
generar.sh antes de hacer el PDF, y boe/pagina.py con la metodología (python comprobar_referencias.py <fichero>); si el informe se reordena y una referencia queda mal, la generación se detiene."""
import re, sys
from pathlib import Path

texto = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent / "modelos-de-decision.md").read_text()
titulos, en_codigo = {}, False
for linea in texto.splitlines():
    if linea.startswith("```"):
        en_codigo = not en_codigo
    elif not en_codigo and linea.startswith("# ") and "{.unnumbered}" not in linea:
        titulos[len(titulos) + 1] = re.sub(r"\s*\{#[^}]*\}$", "", linea[2:].strip())
plano = re.sub(r"\s+", " ", texto)
errores = []
for n, titulo in re.findall(r"secci[oó]n (\d+) \(«([^»]+)»\)", plano):
    if titulos.get(int(n)) != titulo:
        errores.append(f"«sección {n}» dice «{titulo}», pero la sección {n} es «{titulos.get(int(n))}»")
for a, b in re.findall(r"secciones (\d+) a (\d+)", plano):
    if not (int(a) in titulos and int(b) in titulos):
        errores.append(f"«secciones {a} a {b}» se sale del informe")
if errores:
    sys.exit("Referencias rotas:\n  " + "\n  ".join(errores))
total = len(re.findall(r"secci[oó]n \d+ \(«", plano))
print(f"referencias: {total} comprobadas, todas bien")
