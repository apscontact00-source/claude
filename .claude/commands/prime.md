---
description: Scan de niches resell et ajout automatique dans Notion "Niches intéressantes selon Claude"
argument-hint: "[nb de niches | catégorie ciblée, ex: 8 | doudounes techniques]"
allowed-tools: WebSearch, WebFetch, mcp__Notion__notion-search, mcp__Notion__notion-fetch, mcp__Notion__notion-create-pages, mcp__Notion__notion-query-data-sources, Bash, Read, Write
---

# /prime — Scan de niches resell → Notion

Tu es mon assistant de veille **resell** (coulisse privée qui finance, jamais un sujet vidéo).
Quand je tape `/prime`, tu réalises un **scan de niches** : tu trouves de **nouvelles marques /
niches** intéressantes à revendre, et tu les enregistres directement comme sous-pages dans ma page
Notion **« Niches intéressantes selon Claude »**.

- Page Notion cible (parent des sous-pages) :
  `https://app.notion.com/p/37a2c750db1e80efb0fde5a5b995f896`
  (ID : `37a2c750-db1e-80ef-b0fd-e5a5b995f896`, arbo : Business ▸ Resell ▸ Niches ▸ Niche China)
- Argument optionnel `$ARGUMENTS` : nombre de niches à trouver (défaut **6**) et/ou une catégorie à
  cibler (ex : `10 maroquinerie`, `doudounes techniques`, `montres`). Si vide → 6 niches, catégories libres.

---

## Profil d'une bonne niche (le filtre de tout)

Déduit des niches déjà présentes (Herno, Parajumpers, Woolrich, Officine Creative, Grand Seiko,
DÔEN, Our Legacy, Coperni, Marni, Red Wing, Gianvito Rossi…). Une niche est retenue **seulement si**
elle coche l'essentiel :

1. **Premium / haut de gamme, mais pas ultra-mainstream** — assez désirable pour avoir de la valeur
   en seconde main, assez de niche pour garder de la marge (évite Nike/Zara génériques sans angle).
2. **Fort ratio marge** — grand écart entre prix payé au sourcing (friperie, déstockage, lots,
   sourcing) et prix de revente constaté.
3. **Demande réelle et vérifiable** — signal concret : recherches Vinted/Vestiaire, hype TikTok/Pinterest
   mode, hausse Google Trends, articles. Pas d'intuition sans preuve.
4. **Sourçable** — on peut réellement en trouver (dispo en friperie/lots/déstockage/sourcing).
5. **Saturation faible à moyenne** — pas déjà revendue par tout le monde au même prix.

⛔ **À exclure** : toute marque **déjà présente** sur la page Notion (dédup stricte) ; les marques
trop mainstream sans angle de marge ; les contrefaçons.

---

## Déroulé du scan (à exécuter à chaque `/prime`)

1. **Dédup — lis l'existant.** Récupère la liste des sous-pages déjà présentes sur la page cible via
   `notion-fetch` (ID `37a2c750-db1e-80ef-b0fd-e5a5b995f896`). Construis la liste des marques déjà
   listées : tu ne dois **jamais** re-proposer l'une d'elles.

2. **Veille demande & tendances.** Avec `WebSearch` / `WebFetch`, cherche des marques/niches qui
   montent en seconde main *maintenant* — signaux : « brands that resell well 2026 », tendances
   Vinted/Vestiaire Collective/Grailed/Depop, hype mode TikTok/Pinterest, Google Trends, déstockages.
   Si `$ARGUMENTS` cible une catégorie, concentre la recherche dessus. Vérifie chaque piste (2-3 sources).

3. **Filtre & score.** Applique le profil ci-dessus. Écarte tout doublon et tout ce qui ne coche pas
   l'essentiel. Attribue à chaque niche retenue un **score /10** (demande × marge × faible saturation ×
   sourçabilité) avec une phrase de justification. Garde les N meilleures (N = arg ou 6).

4. **Écriture Notion.** Pour **chaque** nouvelle niche, crée une **sous-page** sous la page cible via
   `notion-create-pages` (parent = l'ID ci-dessus). Titre de la page = **nom de la marque / niche**.
   Contenu de la page selon le template ci-dessous.

5. **Archive locale.** Écris aussi `./out/niches-YYYY-MM-DD.md` avec les niches complètes du run
   (même contenu que Notion), pour archive et relecture rapide.

6. **Résumé console.** Affiche : nombre de niches créées, la top niche + score, la liste avec liens
   Notion, et les doublons écartés.

---

## Template d'une sous-page niche (contenu Notion)

```
## 🎯 [Nom de la marque / niche] — score /10

- Catégorie : (maroquinerie / doudounes techniques / sneakers / montres / prêt-à-porter fém. / …)
- Thèse resell (pourquoi c'est intéressant, en 1-2 phrases)
- Signal de demande : (source + métrique — ex : X annonces Vinted vendues, hausse Vestiaire, hype TikTok)
- Prix : retail neuf ~ __ € → seconde main constatée ~ __ € → marge estimée
- Où sourcer : (friperies / lots / déstockage / sourcing …)
- Où revendre : (Vinted / Vestiaire / Grailed / Depop …)
- Saturation / concurrence : faible / moyenne / forte (+ pourquoi)
- Score /10 : __ — justification en une phrase
- Sources vérifiées : 2-3 URL
```

---

## Contraintes

- **Rien de doublon** : ne crée jamais une page pour une marque déjà présente ; logue-la comme écartée.
- **Tout vérifié** : chaque niche s'appuie sur des sources réelles (URL). Pas d'invention de chiffres.
- **Robuste** : si une source échoue, continue avec les autres ; produis toujours au moins quelques niches.
- Commence par me montrer la **liste courte** (nom + score + une ligne) **avant** d'écrire dans Notion si
  je lance `/prime dry` ; sinon écris directement puis affiche le résumé.
