#!/usr/bin/env bash
# run.sh — pipeline niche COMPLET, sans aucun token IA : install + scan Vinted + écriture Notion.
# À lancer sur TA machine (celle qui accède à vinted.fr) :
#   NOTION_TOKEN=secret_xxx NOTION_PARENT_PAGE_ID=<page> bash scripts/run.sh <catalog_id> [min_price]
# Exemple :
#   NOTION_TOKEN=secret_xxx NOTION_PARENT_PAGE_ID=39c2c750db1e8118af23cb660869b321 \
#     bash scripts/run.sh 16 150
set -euo pipefail
cd "$(dirname "$0")/.."

CATALOG_ID="${1:?usage: run.sh <catalog_id> [min_price]  (l'ID est dans l'URL Vinted ?catalog[]=NNNN)}"
MIN_PRICE="${2:-150}"

command -v node >/dev/null    || { echo "❌ Node.js requis : https://nodejs.org"; exit 1; }
command -v python3 >/dev/null  || { echo "❌ Python 3 requis"; exit 1; }

echo "▶ 1/3 Installation des dépendances…"
( cd scripts && npm install --silent )
python3 -m pip install -q -r scripts/requirements.txt

echo "▶ 2/3 Scan Vinted (navigateur, sans token)…"
node scripts/scan_niches_browser.mjs --catalog-id "$CATALOG_ID" --min-price "$MIN_PRICE"

JSON="$(ls -t out/niches-*.json 2>/dev/null | head -1 || true)"
[ -n "$JSON" ] || { echo "Aucun résultat de scan (rien ne correspond aux filtres)."; exit 0; }

echo "▶ 3/3 Écriture dans Notion (sans token)…"
python3 scripts/push_to_notion.py "$JSON" --category Sacs

echo "✅ Terminé. Résultats : $JSON"
