#!/bin/sh
# Construit docs/oral/Oral_RL_Mario.pptx (pptxgenjs + nettoyage).
#   NODE_PATH=<node_modules contenant pptxgenjs> sh docs/oral/fabrication/build.sh
# Variables utiles : NO_VIDEO=1 (aperçu sans vidéos), DECK_OUT=<fichier de sortie>
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
node "$HERE/build_deck.js"
python3 "$HERE/fix_pptx.py" "${DECK_OUT:-$HERE/../Oral_RL_Mario.pptx}"
