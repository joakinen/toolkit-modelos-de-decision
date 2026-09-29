#!/bin/sh
# Mide los casos de uso con un solo grupo de modelos cargado cada vez, para no pasar de la memoria de un equipo de 24 GB:
# 1) embeddings y clásico; 2) Kev; 3) Jeff; 4) los de Ollama y Jev-style v3.
#   KEV_ARRANCAR=<script que arranca y para los servidores Kev> JEFF_DIR=<copia de Jeff> JEV_V3_DIR=<carpeta de v3> \
#     sh casos/medir_por_fases.sh correo expedientes apoyo
# KEV_ARRANCAR recibe «arrancar» o «parar» (en el laboratorio del autor, el script que gobierna sus servicios). Sin él,
# se asume que los servidores de Kev ya están en marcha en los puertos 8008 y 8009.
set -eu
cd "$(dirname "$0")/.."
CASOS="${*:-correo expedientes apoyo}"
: "${JEFF_DIR:?indica la copia de Jeff: JEFF_DIR=/ruta/a/jeff}"
kev() { [ -n "${KEV_ARRANCAR:-}" ] && sh "$KEV_ARRANCAR" "$1" >/dev/null || true; }
esperar() { until curl -s "localhost:$1/v1/models" >/dev/null; do sleep 2; done; }
echo "fase 1 $(date +%H:%M)"
for c in $CASOS; do uv run python embeddings.py $c; uv run python casos/evaluar.py $c clasico; done
echo "fase 2 $(date +%H:%M)"
kev arrancar; esperar 8008; esperar 8009
for c in $CASOS; do uv run python casos/evaluar.py $c kev-08b kev-4b; done
kev parar
echo "fase 3 $(date +%H:%M)"
(cd "$JEFF_DIR" && JEFF_BACKEND=mlx JEFF_CHECKPOINT=checkpoints/jeff-0.8b PORT=8010 nohup .venv/bin/jeff-serve > /dev/null 2>&1 &)
(cd "$JEFF_DIR" && JEFF_BACKEND=mlx JEFF_CHECKPOINT=checkpoints/jeff-2b PORT=8011 nohup .venv/bin/jeff-serve > /dev/null 2>&1 &)
esperar 8010; esperar 8011
for c in $CASOS; do uv run python casos/evaluar.py $c jeff-08b jeff-2b; done
pkill -f jeff-serve || true
echo "fase 4 $(date +%H:%M)"
for c in $CASOS; do uv run --extra jev-v3 python casos/evaluar.py $c jev-v1 jev-v3 llm-9b; done
uv run python casos/notas.py $CASOS
echo "FIN $(date +%H:%M)"
