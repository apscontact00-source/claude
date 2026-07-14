# CLAUDE.md — Projet « Scan de niches resell »

> Mémoire projet pour Claude Code (et pense-bête humain).
> **Ce projet doit tourner EN LOCAL, pas dans le cloud.** L'environnement Claude Code sur le web
> bloque `vinted.fr` (politique réseau : 403 au proxy, prouvé). En local, Vinted est joignable → le
> scan fonctionne. Lance donc Claude Code / les scripts **sur ta machine**.

## But
Trouver des niches resell (surtout **sacs de luxe**) sur **Vinted**, puis les enregistrer dans
**Notion** — le tout **sans consommer de tokens IA** (scripts déterministes + API Notion).

## Règle d'or : zéro donnée inventée
Prix, favoris, marges, photos, tailles : **uniquement** ce que le scan a réellement trouvé.
Ne jamais fabriquer de chiffres ni de fausses annonces.

## Filtres d'une niche (déjà codés)
Un article compte s'il a **≥ 20 favoris** ET **< 3 semaines** ET **prix ≥ 150 €**.
Une marque = niche si **≥ 3 articles** chauds. On garde **5 à 8 articles** par marque
(modèle/couleur = titre, taille, état, prix, favoris, lien, photo).

## Scripts (dans `scripts/`)
- `scan_niches.py` — scan via l'API Vinted (Python `requests`). Sans token IA.
- `scan_niches_browser.mjs` — scan via un **vrai navigateur** (Playwright) pour passer l'anti-bot
  DataDome ; **cookies vidés entre chaque scan** ; accepte plusieurs `--catalog-id 16,19`.
- `push_to_notion.py` — écrit les niches dans Notion via l'**API officielle** (jeton d'intégration).
  Crée 1 page/marque + sous-page catégorie (photos + callout « 📊 Analyse prix C3PO »). Dédup auto.
- `run.sh` / `run.ps1` — pipeline complet en une commande : install + scan + écriture Notion.

## Lancer (en local)
```bash
# macOS / Linux
NOTION_TOKEN=secret_xxx NOTION_PARENT_PAGE_ID=<page_id> bash scripts/run.sh <catalog_id> 150
# Windows : powershell -File scripts\run.ps1 -CatalogId <catalog_id> -MinPrice 150
```
- **catalog_id** = ID de la sous-catégorie Vinted. Ouvre la catégorie sur vinted.fr, l'URL contient
  `?catalog[]=NNNN`. (Ou `python scripts/scan_niches.py --list-catalogs`.)
- **NOTION_TOKEN** : crée une intégration sur https://www.notion.so/my-integrations, copie le
  `secret_...`, puis **partage la page cible** avec l'intégration (menu ••• → Connexions).

## Cibles Notion
- Page « **Sacs de luxe** » (sous *Niche China*) : `39c2c750db1e8118af23cb660869b321`
- Page « **Niches intéressantes selon Claude** » : `37a2c750db1e80efb0fde5a5b995f896`
- Page « **Priorité** » (file de marques à scanner) : `3942c750db1e8004af29c5cf621077db`

## Commande `/niche`
`.claude/commands/niche.md` : flux interactif (regarde le setup → demande la catégorie/les filtres →
scanne → écrit dans Notion). En local, Claude Code peut lancer les scripts directement.

## Ne pas faire
- Ne pas relancer le scan depuis le cloud (bloqué) — c'est local.
- Ne pas commiter le dossier `out/` ni `scripts/.env` (déjà dans `.gitignore`).
- Ne pas contourner une politique réseau.
