#!/bin/sh
# Genera el PDF del informe (y su copia en docs/ para GitHub Pages). Necesita pandoc, XeLaTeX y las fuentes Helvetica
# Neue y Menlo (vienen con macOS; en otro sistema, cámbialas aquí y en portada.tex). El preámbulo está en preambulo.tex y la portada, en portada.tex.
# La versión y la fecha salen del primer «## X.Y · fecha» de CAMBIOS.md: van a la portada y al pie de página (por
# version.tex, que se genera aquí) y a las dos frases del texto que las citan, que se reescriben en el propio .md.
#   sh informe/generar.sh
set -eu
cd "$(dirname "$0")"
LINEA="$(grep -m1 '^## [0-9][0-9.]* · ' ../CAMBIOS.md)" || { echo "CAMBIOS.md no tiene ninguna versión" >&2; exit 1; }
VERSION="$(echo "$LINEA" | sed 's/^## \([0-9.]*\) · .*/\1/')"
FECHA="$(echo "$LINEA" | sed 's/^## [0-9.]* · //')"
MES="$(echo "$FECHA" | sed 's/^[0-9]* de //')"
printf '%s\n' "\\newcommand{\\informeVersion}{$VERSION}" "\\newcommand{\\informeFecha}{$FECHA}" \
  "\\newcommand{\\informeMes}{$MES}" > version.tex
sed -i.bak -e "s/^Esta es la versión [0-9.]*, del [^;]*;/Esta es la versión $VERSION, del $FECHA;/" \
  -e "s/^Versión [0-9.]* · [^\\\\]*\\\\\$/Versión $VERSION · $FECHA\\\\/" modelos-de-decision.md && rm modelos-de-decision.md.bak
grep -q "^Esta es la versión $VERSION, del $FECHA;" modelos-de-decision.md && grep -q "^Versión $VERSION · $FECHA\\\\\$" modelos-de-decision.md \
  || { echo "no encuentro en el .md las frases con la versión (Antes de empezar y créditos)" >&2; exit 1; }
python3 comprobar_referencias.py
pandoc modelos-de-decision.md -o modelos-de-decision.pdf --pdf-engine=xelatex --include-in-header=version.tex \
  --include-in-header=preambulo.tex --include-in-header=portada.tex \
  -V papersize=a4 -V geometry:margin=2.3cm -V mainfont="Helvetica Neue" -V monofont=Menlo -V fontsize=11pt -V colorlinks=true \
  -V linestretch=1.15 --number-sections
cp modelos-de-decision.pdf ../docs/
echo "versión $VERSION ($FECHA): informe/modelos-de-decision.pdf y docs/modelos-de-decision.pdf"
