#!/bin/sh
# Ajusta Kev-0.8B y Kev-4B para la pregunta «¿en qué apartado del BOE se publica este texto?» y los evalúa.
#
#   KEV_DIR=/ruta/a/kev sh boe/ajustar.sh            los dos modelos
#   KEV_DIR=/ruta/a/kev sh boe/ajustar.sh 08b        solo el 0.8B
#
# Necesita una copia de Kev (https://github.com/jaredpalmer/kev) con su entorno instalado (uv sync --extra serve) y
# haber ejecutado antes construir.py (sumarios, prueba, entrenamiento) y control.py.
# Pasos: convierte los conjuntos al formato de Kev, entrena, y evalúa el original y el ajustado sobre la prueba y el
# control con evaluar_kev.py (eval-kev/). Después: python exportar.py && python pagina.py.
#
# Hiperparámetros fijados antes de ver resultados: 3 épocas, lote 4, 160 ejemplos generales de repaso (decision-v7),
# LoRA 16; ritmo 4e-5 para el 0.8B y 2e-5 para el 4B, este con la base en media precisión (bf16).
# Duración medida en un Mac mini M4 Pro (24 GB): unas 3,5 horas el 0.8B; el 4B, unas 11 (estimación). En una sola GPU los
# entrenamientos no deben solaparse: dos a la vez se frenan unas diez veces. Conviene parar los servidores Kev mientras.
set -eu
B="$(cd "$(dirname "$0")" && pwd)"
: "${KEV_DIR:?indica la carpeta de Kev: KEV_DIR=/ruta/a/kev sh boe/ajustar.sh}"
QUE="${1:-todos}"
cd "$KEV_DIR"
KEV_PY="uv run python"

for N in entrenamiento prueba; do   # copias solo con los campos que usa Kev (state + questions)
  $KEV_PY -c "import json,sys; [print(json.dumps({k: json.loads(l)[k] for k in ('state', 'questions')}, ensure_ascii=False)) for l in open(sys.argv[1])]" \
    "$B/$N.jsonl" > "$B/$N-kev.jsonl"
done

entrenar() {  # $1 nombre, $2 modelo publicado, $3 base, $4 revisión de la base, $5 ritmo, $6 opciones extra
  [ -f "$B/runs/$1/adapter_model.safetensors" ] && { echo "$1 ya entrenado, se salta"; return; }
  rm -rf "$B/runs/$1"
  $KEV_PY -m kev.train --data "$B/entrenamiento-kev.jsonl" --suite evals/v7/decision-v7 --replay 160 \
    --init_from "$2" --base "$3" --base_revision "$4" --lora 16 --head_dim 256 --lora_targets all --checkpointing 1 \
    --max_state 1024 --lr "$5" --epochs 3 --batch 4 --accum 1 --seed 1 $6 --out "$B/runs/$1" > "$B/entrenar-$1.log" 2>&1
  echo "$1 entrenado $(date +%H:%M)"
}

evaluar() {  # $1 nombre del resultado, $2 modelo (Hub o carpeta)
  for D in prueba:"$B/prueba-kev.jsonl" control:"$B/control.jsonl"; do
    rm -rf "$B/eval-kev/$1-${D%%:*}"
    $KEV_PY "$B/evaluar_kev.py" "$2" "${D#*:}" "$B/eval-kev/$1-${D%%:*}" > "$B/evaluar-$1-${D%%:*}.log" 2>&1
  done
  echo "$1 evaluado $(date +%H:%M)"
}

if [ "$QUE" = todos ] || [ "$QUE" = 08b ]; then
  entrenar ajustado08b jaredpalmer/kev-0.8b Qwen/Qwen3.5-0.8B-Base dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68 4e-5 ""
  evaluar base08b jaredpalmer/kev-0.8b
  evaluar ajustado08b "$B/runs/ajustado08b"
fi
if [ "$QUE" = todos ] || [ "$QUE" = 4b ]; then
  entrenar ajustado4b jaredpalmer/kev-4b Qwen/Qwen3.5-4B-Base 1001bb4d826a52d1f399e183466143f4da7b741b 2e-5 "--weights_dtype bf16"
  export KEV_DTYPE=bf16   # en precisión completa el 4B ocupa unos 17 GB
  evaluar base4b jaredpalmer/kev-4b
  evaluar ajustado4b "$B/runs/ajustado4b"
fi
echo FIN
