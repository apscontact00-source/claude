---
description: Scan de niches resell Vinted (sans tokens) → Notion "Niches intéressantes selon Claude"
argument-hint: "[catalog_id] | dry | --min-favs 20 --max-age-days 21"
allowed-tools: Bash, Read, mcp__Notion__notion-fetch, mcp__Notion__notion-create-pages
---

# /prime — Scan de niches resell (Vinted, sans tokens IA)

Quand je tape `/prime`, tu déclenches un **scan de niches** resell (coulisse privée, jamais un
sujet vidéo). Le scan lui-même **ne doit consommer aucun token IA** : tout le travail Vinted est
fait par le script `scripts/scan_niches.py`. Tu ne fais que le lancer, puis écrire les nouvelles
niches dans Notion.

- Page Notion cible : `https://app.notion.com/p/37a2c750db1e80efb0fde5a5b995f896`
  (ID `37a2c750-db1e-80ef-b0fd-e5a5b995f896`).
- `$ARGUMENTS` : un `catalog_id` Vinted (sous-catégorie précise) et/ou des options du script
  (`--min-favs`, `--max-age-days`, `--min-articles`). Si `dry` est passé → ne pas écrire dans Notion.

## Règles du scan (déjà codées dans le script — ne pas les refaire à la main / au LLM)

- On choisit **une catégorie + une sous-catégorie précises** sur Vinted (`--catalog-id`).
- Un article n'est retenu que s'il a **≥ 20 favoris** ET date de **moins de 3 semaines**.
- Les marques avec assez d'articles chauds = niches ; on **écarte les marques déjà dans Notion**.
- Analyse prix façon **C3PO** : vente moyenne, achat = vente ÷ 3, marge brute, favoris moyens.

## Déroulé

1. **Choix de la sous-catégorie.** Si `$ARGUMENTS` contient un `catalog_id`, utilise-le. Sinon,
   choisis une sous-catégorie précise cohérente avec le profil resell (premium, forte marge —
   ex. manteaux/doudounes homme, maroquinerie, bottes, montres) et indique-la-moi. Pour trouver
   l'ID : `python scripts/scan_niches.py --list-catalogs`, ou l'URL Vinted `?catalog[]=NNNN`.

2. **Dédup — exporte les marques déjà connues.** Lis la page Notion cible via `notion-fetch`
   (ID ci-dessus), récupère les titres des sous-pages (marques déjà listées) et écris-les, une par
   ligne, dans `out/known.txt`. C'est la seule lecture Notion nécessaire.

3. **Lance le scan (sans tokens).** Exécute :
   ```bash
   python scripts/scan_niches.py --catalog-id <ID> --known-file out/known.txt
   ```
   Le script produit `out/niches-<ID>-<date>.json` et `.md`. Ne ré-analyse pas les annonces
   toi-même : tout est déjà dans le JSON.
   - Si le script échoue faute d'accès réseau à Vinted, dis-le-moi (il faut le lancer sur une
     machine où vinted.fr est joignable) et arrête-toi là.

4. **Écris les nouvelles niches dans Notion** (sauf si `dry`). Lis le `.json` et, pour **chaque**
   niche, crée une sous-page sous la page cible via `notion-create-pages` :
   - Titre de la page = **nom de la marque**.
   - Une sous-page « catégorie » (ex. Vêtements / Chaussures / Maroquinerie) contenant :
     - les **photos** des annonces (`photo` des `samples`, en blocs image),
     - un **callout** `📊 Analyse prix C3PO (auto)` reprenant exactement les champs du JSON :
       `N article(s)` · `Prix de vente moyen : X€ (min / max)` · `Prix d'achat estimé (vente ÷3) : Y€`
       · `Marge brute estimée : Z€` · `Favoris moyens : F`.

5. **Résumé.** Affiche : sous-catégorie scannée, nb de niches créées, top niches (marque · marge ·
   favoris), et les marques écartées car déjà connues. N'invente aucun chiffre : tout vient du JSON.

## Notes

- « Sans tokens » = le **scan** (fetch + filtres + analyse prix) est 100 % script. Seule l'écriture
  de quelques niches dans Notion passe par l'IA, et elle est légère. Pour un run 100 % sans IA,
  remplis `NOTION_TOKEN` dans `scripts/.env` et laisse le script pousser dans Notion (cf. README).
- `/prime dry <ID>` : montre la liste des niches trouvées **sans** écrire dans Notion (validation).
