# run.ps1 — pipeline niche COMPLET sans token IA (Windows PowerShell).
# À lancer sur TA machine (celle qui accède à vinted.fr) :
#   $env:NOTION_TOKEN="secret_xxx"; $env:NOTION_PARENT_PAGE_ID="<page>"
#   powershell -File scripts\run.ps1 -CatalogId 16 -MinPrice 150
param(
  [Parameter(Mandatory=$true)][string]$CatalogId,
  [int]$MinPrice = 150
)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "* 1/3 Installation des dependances..."
Push-Location scripts; npm install --silent; Pop-Location
python -m pip install -q -r scripts\requirements.txt

Write-Host "* 2/3 Scan Vinted (navigateur, sans token)..."
node scripts\scan_niches_browser.mjs --catalog-id $CatalogId --min-price $MinPrice

$json = Get-ChildItem out\niches-*.json | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $json) { Write-Host "Aucun resultat de scan."; exit 0 }

Write-Host "* 3/3 Ecriture dans Notion (sans token)..."
python scripts\push_to_notion.py $json.FullName --category Sacs

Write-Host "OK. Resultats : $($json.FullName)"
