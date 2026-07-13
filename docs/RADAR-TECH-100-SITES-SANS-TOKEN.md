# 🛰️ Trouver des sujets vidéos tech — scraper 100 sites/jour SANS token

> Détecter chaque jour les sujets tech qui montent en scannant **100+ sources**, **sans dépenser un seul token d'IA** (aucun appel LLM) et **sans API payante**. Prompt de build en §5.

## 🔑 Principe : « sans token » = zéro LLM
Détection 100 % déterministe/offline (fréquence, stats, NLP classique). Aucun appel modèle → coût 0. Uniquement des flux **gratuits sans clé** (RSS/Atom, JSON publics). L'écriture Notion utilise la clé d'intégration Notion (gratuite), pas un token d'IA.

## 📡 1. Les sources (100+), gratuites & sans clé
**A. Agrégateurs sociaux (heat) :** Hacker News (Firebase `topstories.json` + Algolia `search_by_date`) · Reddit `r/<sub>/top.json?t=day` · Lobsters RSS · Product Hunt feed · Dev.to feed · GitHub Trending (miroir RSS) · Journal du Hacker RSS.
**B. Trends :** Google Trends Daily RSS `trends.google.com/trending/rss?geo=FR` (+ US).
**C. Presse tech (RSS) :** Verge, TechCrunch (full-text), Ars Technica, Wired, Engadget, Gizmodo, TechRadar, ZDNet, CNET, Mashable, VentureBeat, TNW, Techmeme, MIT Tech Review, IEEE Spectrum, The Register, Slashdot, Digital Trends, Tom's Hardware, 9to5Mac/Google, MacRumors, Android Police.
**D. IA :** Google AI, OpenAI, Anthropic, DeepMind, Hugging Face, MarkTechPost, VentureBeat AI, arXiv cs.AI/cs.LG RSS, Papers with Code.
**E. Startups/VC :** TechCrunch, Sifted, Crunchbase News, CB Insights, a16z, Indie Hackers.
**F. Dev :** GitHub Blog, Stack Overflow Blog, InfoQ, Hacker Noon, CSS-Tricks, Smashing, freeCodeCamp.
**G. Français :** Numerama, Frandroid, 01net, Les Numériques, Next, Journal du Geek, Presse-citron, Siècle Digital, Usine Digitale, Maddyness, BFM Tech.
**H. Science/futur :** New Scientist, Quanta, Nature News, ScienceAlert, Interesting Engineering.

> 📦 Atteindre 100+ : importer les OPML **Feedspot « Top 80 Tech News »** + gists GitHub de flux. Un `sources.opml` versionné = ta liste vivante.

## 🧮 2. Le scoring SANS LLM (déterministe)
Pour chaque item (titre + résumé) des dernières 24-36 h :
1. **Extraction** offline : spaCy NER + noun phrases ; YAKE/RAKE/TF-IDF pour les n-grammes.
2. **Clustering** des quasi-doublons en « sujets » : TF-IDF + cosinus, ou MinHash/SimHash.
3. **Score de sujet** = corroboration (nb de sources distinctes) + vélocité (fréquence 24h vs baseline 7j) + chaleur sociale (points HN, upvotes Reddit, votes PH) + bonus Google Trends + décroissance de récence.
4. **Filtre DA** (règles, pas d'IA) : garder les piliers (IA, grandes boîtes, bourse/IPO, code, innovation) ; **blacklist** de mots pour exclure resell/sneakers/Vinted.

## 🏷️ 3. Titres candidats SANS LLM (templates R9)
Remplir des moules de questions avec l'entité détectée : « Pourquoi {X} {événement} ? » · « Comment {X} a {résultat} ? » · « {X} : ce que personne ne dit ». À polir à la main ensuite (0 token).

## 📤 4. Sortie quotidienne
Top 10-15 sujets classés par score, chacun avec titre(s), score + justification, 2-4 liens, pilier + style reco. Écriture dans Notion (base Scripts, Statut=Idée, ou base « Radar »). Archive `out/radar-YYYY-MM-DD.md`. Cron quotidien.

## 🤖 5. PROMPT à coller dans Claude Code
```
Construis-moi un outil CLI Python "radar-tech" qui, chaque matin, détecte les sujets tech qui
MONTENT en scannant 100+ sources d'actu, SANS AUCUN appel LLM (coût token = 0) et sans API
payante. Il propose des idées de vidéos dans Notion, calibrées sur ma DA.

## Contrainte absolue : ZERO TOKEN
- Aucune requête à un modèle d'IA. Détection déterministe/offline (stats + NLP classique).
  Uniquement des flux GRATUITS SANS CLÉ (RSS/Atom, JSON publics).
- L'écriture Notion utilise la clé d'intégration Notion (gratuite), pas un modèle.

## Sources (fichier sources.opml versionné, 100+)
- Sociaux/heat : HN (Firebase topstories + Algolia search_by_date), Reddit r/<sub>/top.json
  (technology, artificial, singularity, Futurology, programming, gadgets, SaaS, startups),
  Lobsters RSS, Product Hunt feed, Dev.to feed, GitHub Trending (miroir RSS), Journal du Hacker.
- Trends : Google Trends Daily RSS (geo=FR et geo=US).
- Presse tech (RSS) : Verge, TechCrunch, Ars, Wired, Engadget, TechRadar, ZDNet, VentureBeat,
  TNW, Techmeme, MIT Tech Review, IEEE Spectrum, The Register, Tom's Hardware, 9to5Mac/Google...
- IA : Google AI, OpenAI, Anthropic, DeepMind, Hugging Face, MarkTechPost, arXiv cs.AI/cs.LG.
- FR : Numerama, Frandroid, 01net, Les Numériques, Next, Journal du Geek, Siècle Digital,
  Usine Digitale, Maddyness.
- Fournis un sources.opml de départ (>= 100 flux) + un script d'ajout via OPML Feedspot/gists.

## Pipeline quotidien
1. Ingestion : feedparser sur tous les flux + fetch JSON HN/Reddit/PH. Chaque source dans un
   try/except isolé (une source down ne casse jamais le run), timeouts, retries backoff.
2. Normalisation : titre + résumé + source + date + url ; dedup par url et similarité de titre.
3. Extraction offline : spaCy NER + noun_chunks, YAKE/RAKE/TF-IDF pour les n-grammes.
4. Clustering : TF-IDF + cosinus (ou MinHash) pour regrouper les articles en "sujets".
5. Scoring déterministe : corroboration (nb sources) + vélocité (24h vs baseline 7j du state.json)
   + chaleur sociale (points HN, upvotes Reddit, votes PH) + bonus Google Trends + récence.
   Pondérations dans config.yaml.
6. Filtre DA (règles) : garder piliers (IA, grandes boîtes, bourse/IPO, code, innovation) ;
   blacklist pour EXCLURE resell/sneakers/Vinted.
7. Titres candidats SANS LLM : templates de questions (moules R9) remplis avec l'entité du cluster.
8. Sortie : top 10-15 sujets triés ; titre(s), score + justification, 2-4 liens, pilier + style.
   Écrire dans Notion (base Scripts, Statut=Idée, ou base "Radar") via l'API Notion.
   Archive out/radar-YYYY-MM-DD.md. Résumé console.

## Technique
Python 3.11+, deps : feedparser, requests, scikit-learn, spacy (fr+en), yake, datasketch,
pyyaml, python-dotenv, notion-client. AUCUNE lib LLM. Cache 24-36h, state.json (baseline +
titres déjà proposés = idempotence). README + tests (parsing, dedup, scoring, blacklist).
Cron : 0 7 * * * cd /chemin/radar-tech && python3 run.py >> out/cron.log 2>&1

Commence par l'arborescence + sources.opml + le plan, puis code, teste, et fais un dry-run
(sans écrire dans Notion) que je validerai avant d'activer l'écriture.
```

## ⚖️ Note « 0 token » vs qualité des titres
Le pipeline détecte et classe sans coût. Les titres par templates sont bruts : soit tu les polis à la main (0 coût), soit tu ajoutes **en option** une seule passe IA sur les 10 sujets finaux (coût minime). Le radar reste à token = 0.

### Sources
Feedspot (Top 80 Tech RSS) · gists GitHub de flux · HN API/Algolia · Google Trends RSS · Reddit .json · NLP sans LLM (TF-IDF, RAKE/YAKE, spaCy NER, MinHash).
