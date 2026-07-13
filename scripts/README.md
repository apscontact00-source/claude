# Scanner de niches resell (Vinted) — sans tokens IA

`scan_niches.py` fait le scan de niches **en pur script Python** : il n'appelle aucune IA,
donc **ne consomme aucun token Claude**. Il tape directement l'API publique de Vinted.

## Ce qu'il fait

1. Tu choisis une **catégorie + sous-catégorie** Vinted (un `catalog_id`).
2. Il liste les annonces récentes de cette sous-catégorie.
3. Il ne garde que les articles **≥ 20 favoris** ET **de moins de 3 semaines**.
4. Il regroupe par **marque** ; toute marque avec assez d'articles chauds = une **niche**.
5. Il écarte les marques déjà connues et enregistre les nouvelles avec l'**analyse prix C3PO**
   (prix vente moyen, prix d'achat = vente ÷ 3, marge brute, favoris moyens).

Sortie dans `out/` : un `.json` + un `.md` prêt à coller dans Notion.

## Install

```bash
pip install -r scripts/requirements.txt
cp scripts/.env.example scripts/.env   # optionnel (écriture Notion directe)
```

## Trouver le bon `catalog_id`

Deux façons :

```bash
# a) l'arbre des catégories renvoyé par Vinted
python scripts/scan_niches.py --list-catalogs

# b) le plus simple : ouvre la catégorie sur vinted.fr et lis l'URL,
#    elle contient ...?catalog[]=NNNN  → NNNN est ton catalog_id
```

## Lancer un scan

```bash
python scripts/scan_niches.py --catalog-id 1206
# options : --min-favs 20  --max-age-days 21  --min-price 150  --min-articles 3  --known-file known.txt
```

- `--known-file` : un fichier texte, une marque par ligne, des niches déjà dans Notion
  (à écarter). `/prime` peut le générer depuis la page Notion.

## ⚠️ Réseau & compte

- **Aucun compte Vinted requis.** Le script ouvre une **session anonyme** (il récupère un token
  anonyme sur la home, comme une fenêtre de navigation privée). Pas de login, pas de mot de passe.
- Mais Vinted doit être **joignable depuis la machine qui lance le script**. Dans un environnement
  sandbox à réseau restreint (Claude Code sur le web), tout le domaine `vinted.fr` est bloqué au
  niveau du proxy (403) — l'anonymat n'y change rien : lance alors le script sur ta machine locale.

## Où atterrissent les sacs de luxe

Le scan des sacs de luxe se range dans la page Notion **« Sacs de luxe »** (sous *Niche China*) :
`https://app.notion.com/p/39c2c750db1e8118af23cb660869b321`

## Cron (100 % sans IA, optionnel)

Si tu remplis `NOTION_TOKEN` + `NOTION_PARENT_PAGE_ID` dans `.env`, le script peut pousser
directement dans Notion. Sinon, lance `/prime` dans Claude Code : il lit le `.json` et écrit
les nouvelles niches dans Notion via le MCP (seule étape qui touche l'IA, et elle est légère).
