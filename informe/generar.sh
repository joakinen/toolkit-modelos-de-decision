#!/bin/sh
# Genera el PDF del informe (y su copia en docs/ para GitHub Pages). Necesita pandoc, XeLaTeX y las fuentes Helvetica
# Neue y Menlo (vienen con macOS; en otro sistema, cámbialas aquí y en portada.tex). El preámbulo está en preambulo.tex y la portada, en portada.tex.
#   sh informe/generar.sh
set -eu
cd "$(dirname "$0")"
pandoc modelos-de-decision.md -o modelos-de-decision.pdf --pdf-engine=xelatex --include-in-header=preambulo.tex --include-in-header=portada.tex \
  -V papersize=a4 -V geometry:margin=2.3cm -V mainfont="Helvetica Neue" -V monofont=Menlo -V fontsize=11pt -V colorlinks=true \
  -V linestretch=1.15
cp modelos-de-decision.pdf ../docs/
echo "informe/modelos-de-decision.pdf y docs/modelos-de-decision.pdf"
