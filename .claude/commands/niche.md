---
description: Scan de niches resell Vinted — interactif : je regarde le setup puis je te demande quoi analyser
argument-hint: "(rien — je te poserai les questions) | ou directement un catalog_id"
allowed-tools: Bash, Read, AskUserQuestion, mcp__Notion__notion-fetch, mcp__Notion__notion-create-pages
---

# /niche — Scan de niches resell (Vinted, sans tokens IA)

Quand je tape `/niche`, tu **regardes d'abord le contexte**, puis tu **me demandes ce que je veux
analyser**, et seulement ensuite tu scannes et écris dans Notion. Le scan lui-même ne consomme
aucun token IA : tout le travail Vinted est fait par `scripts/scan_niches.py`.

- Page Notion cible : `https://app.notion.com/p/37a2c750db1e80efb0fde5a5b995f896`
  (ID `37a2c750-db1e-80ef-b0fd-e5a5b995f896`).

## Étape 1 — Tu regardes le setup (silencieux, rapide)

- Ouvre `scripts/scan_niches.py` et `scripts/README.md` pour te rappeler les options.
- Lis la page Notion cible via `notion-fetch` : récupère les marques déjà listées (pour la dédup)
  et écris-les dans `out/known.txt` (une par ligne).
- Ne lance encore **rien** d'autre.

## Étape 2 — Tu me demandes quoi analyser (AskUserQuestion)

Pose-moi, en une fois, les choix suivants (propose des valeurs par défaut sensées) :
1. **Quelle catégorie / sous-catégorie Vinted ?** — donne 2-3 suggestions cohérentes avec le profil
   resell (premium, forte marge : ex. manteaux/doudounes homme, maroquinerie, bottes femme, montres).
   Si je ne connais pas l'ID, propose de lancer `python scripts/scan_niches.py --list-catalogs`
   ou de coller une URL Vinted (l'ID est dans `?catalog[]=NNNN`).
2. **Filtres** — défaut : **≥ 20 favoris**, **< 3 semaines**, **≥ 3 articles/marque**. Demande si je
   veux ajuster.
3. **Écrire dans Notion, ou juste prévisualiser** (dry-run) ?

Attends mes réponses avant de continuer.

## Étape 3 — Tu scannes (sans tokens)

```bash
python scripts/scan_niches.py --catalog-id <ID> --known-file out/known.txt \
  [--min-favs N] [--max-age-days N] [--min-articles N]
```
Le script sort `out/niches-<ID>-<date>.json` + `.md`. Ne ré-analyse pas les annonces toi-même :
tout est dans le JSON. Si Vinted est injoignable (réseau restreint), dis-le-moi et arrête-toi —
il faut lancer le script sur une machine où vinted.fr est accessible.

## Étape 4 — Tu écris dans Notion (sauf dry-run)

Pour **chaque** niche du JSON, crée une sous-page sous la page cible via `notion-create-pages` :
- Titre = **nom de la marque** ; une sous-page catégorie (Vêtements / Chaussures / Maroquinerie…)
  contenant les **photos** des `samples` (blocs image) + un **callout** `📊 Analyse prix C3PO (auto)`
  reprenant exactement le JSON : `N article(s)` · `Prix de vente moyen : X€ (min / max)` ·
  `Prix d'achat estimé (vente ÷3) : Y€` · `Marge brute estimée : Z€` · `Favoris moyens : F`.

## Étape 5 — Résumé

Sous-catégorie scannée, nb de niches créées, top niches (marque · marge · favoris), marques
écartées car déjà connues. N'invente aucun chiffre : tout vient du JSON.
