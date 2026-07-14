#!/usr/bin/env python3
"""
scan_niches.py — Scan de niches resell sur Vinted, SANS tokens IA.

Principe (déterministe, 0 conso Claude) :
  1. On choisit une CATÉGORIE + SOUS-CATÉGORIE Vinted (catalog_id).
  2. On liste les annonces les plus récentes de cette sous-catégorie.
  3. On ne garde QUE les articles qui ont >= 20 favoris ET < 3 semaines.
  4. On regroupe par MARQUE : chaque marque avec assez d'articles chauds = une niche.
  5. On écarte les marques déjà connues (dédup) et on enregistre les NOUVELLES,
     avec l'analyse prix façon "C3PO" (prix vente moyen, achat = vente ÷3, marge, favoris).

Sortie : out/niches-<catalog>-<YYYY-MM-DD>.json  +  .md (prêt à coller dans Notion).
Écriture Notion optionnelle et facultative (si NOTION_TOKEN présent).

⚠️ À lancer sur une machine où vinted.fr est joignable (pas dans un sandbox réseau restreint).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
from collections import defaultdict

try:
    import requests
except ImportError:
    sys.exit("Dépendance manquante : pip install -r scripts/requirements.txt")

VINTED_BASE = os.environ.get("VINTED_BASE", "https://www.vinted.fr")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")

# --- Critères par défaut (surchargables en CLI) -----------------------------
MIN_FAVS = 20            # un article doit avoir >= 20 favoris
MAX_AGE_DAYS = 21        # ... et dater de moins de 3 semaines
MIN_PRICE = 0            # ... et coûter au moins ce prix (0 = pas de filtre)
MIN_ARTICLES = 3         # une marque = niche si >= 3 articles chauds
MAX_PAGES = 8            # garde-fou pagination


# --------------------------------------------------------------------------- #
# Session Vinted
# --------------------------------------------------------------------------- #
def new_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "fr-FR,fr;q=0.9",
        "Referer": VINTED_BASE + "/",
    })
    # La home pose les cookies (access_token_web) nécessaires à l'API publique.
    s.get(VINTED_BASE, timeout=20)
    return s


def get_json(s: requests.Session, path: str, params: dict) -> dict:
    """GET API avec 1 retry (re-arme les cookies sur 401/403)."""
    url = VINTED_BASE + path
    for attempt in range(2):
        r = s.get(url, params=params, timeout=25)
        if r.status_code in (401, 403) and attempt == 0:
            s.get(VINTED_BASE, timeout=20)  # refresh cookies
            time.sleep(1)
            continue
        r.raise_for_status()
        return r.json()
    r.raise_for_status()
    return {}


# --------------------------------------------------------------------------- #
# Découverte de catégories (pour "choisir une catégorie précise")
# --------------------------------------------------------------------------- #
def list_catalogs(s: requests.Session) -> None:
    """Affiche l'arbre des catégories id → titre, pour choisir un catalog_id."""
    data = get_json(s, "/api/v2/catalog", {})
    catalogs = data.get("catalogs") or data.get("dtos", {}).get("catalogs") or []

    def walk(nodes, depth=0):
        for n in nodes:
            print(f"{'  ' * depth}{n.get('id'):>7}  {n.get('title')}")
            walk(n.get("catalogs", []), depth + 1)

    if not catalogs:
        print("Aucun catalogue renvoyé. Astuce : ouvre la catégorie sur vinted.fr,\n"
              "l'URL contient ?catalog[]=NNNN — c'est le catalog_id à passer en --catalog-id.")
        return
    walk(catalogs)


# --------------------------------------------------------------------------- #
# Scan
# --------------------------------------------------------------------------- #
def item_timestamp(item: dict) -> int | None:
    """Timestamp de mise en ligne (approx via la photo haute résolution)."""
    photo = item.get("photo") or {}
    hi = photo.get("high_resolution") or {}
    ts = hi.get("timestamp") or photo.get("timestamp")
    return int(ts) if ts else None


def item_price(item: dict) -> float | None:
    p = item.get("price")
    if isinstance(p, dict):
        p = p.get("amount")
    try:
        return float(p)
    except (TypeError, ValueError):
        return None


def scan(catalog_id: int, min_favs: int, max_age_days: int,
         max_pages: int, min_price: float = 0) -> list[dict]:
    """Renvoie la liste des articles CHAUDS (>= min_favs favoris, < max_age_days, >= min_price)."""
    s = new_session()
    cutoff = time.time() - max_age_days * 86400
    hot: list[dict] = []
    stale_streak = 0

    for page in range(1, max_pages + 1):
        params = {
            "catalog_ids": catalog_id,
            "order": "newest_first",
            "per_page": 96,
            "page": page,
        }
        if min_price:
            params["price_from"] = min_price  # pré-filtre côté Vinted
        try:
            data = get_json(s, "/api/v2/catalog/items", params)
        except Exception as e:  # une page qui tombe ne casse pas le run
            print(f"  ! page {page} échouée : {e}", file=sys.stderr)
            break

        items = data.get("items", [])
        if not items:
            break

        page_had_recent = False
        for it in items:
            ts = item_timestamp(it)
            if ts is not None:
                if ts >= cutoff:
                    page_had_recent = True
                else:
                    continue  # trop vieux → on ignore (strict < 3 semaines)
            else:
                continue  # date inconnue → exclu (on respecte le critère de fraîcheur)

            if int(it.get("favourite_count", 0)) < min_favs:
                continue

            price = item_price(it)
            if min_price and (price is None or price < min_price):
                continue  # trop bon marché pour du luxe

            hot.append({
                "id": it.get("id"),
                "brand": (it.get("brand_title") or "Sans marque").strip(),
                "title": it.get("title"),          # porte souvent modèle + couleur
                "size": it.get("size_title"),      # taille (fiable, depuis la fiche)
                "status": it.get("status"),        # état (Neuf avec étiquette, Très bon état...)
                "price": price,
                "favourites": int(it.get("favourite_count", 0)),
                "url": it.get("url"),
                "photo": (it.get("photo") or {}).get("url"),
                "ts": ts,
            })

        # tri "newest_first" : si une page entière est déjà hors fenêtre, on stoppe
        stale_streak = 0 if page_had_recent else stale_streak + 1
        if stale_streak >= 1 and page >= 2:
            break
        time.sleep(0.6)  # politesse / anti-ban

    return hot


def aggregate(hot: list[dict], min_articles: int,
              known: set[str]) -> list[dict]:
    """Regroupe par marque → niches, écarte les marques connues."""
    by_brand: dict[str, list[dict]] = defaultdict(list)
    for a in hot:
        by_brand[a["brand"]].append(a)

    niches = []
    for brand, arts in by_brand.items():
        if brand.lower() in known or brand.lower() == "sans marque":
            continue
        if len(arts) < min_articles:
            continue
        prices = [a["price"] for a in arts if a["price"]]
        if not prices:
            continue
        avg = round(sum(prices) / len(prices))
        buy = round(avg / 3)
        niches.append({
            "brand": brand,
            "articles": len(arts),
            "avg_price": avg,
            "min_price": round(min(prices)),
            "max_price": round(max(prices)),
            "buy_estimate": buy,          # prix d'achat = vente ÷ 3
            "gross_margin": avg - buy,    # marge brute estimée
            "avg_favourites": round(sum(a["favourites"] for a in arts) / len(arts)),
            "samples": sorted(arts, key=lambda a: -a["favourites"])[:8],
        })
    # les niches les plus "chaudes" d'abord (marge × favoris)
    niches.sort(key=lambda n: (n["gross_margin"] * n["avg_favourites"]), reverse=True)
    return niches


# --------------------------------------------------------------------------- #
# Sorties
# --------------------------------------------------------------------------- #
def c3po_callout(n: dict) -> str:
    return (f"📊 Analyse prix C3PO (auto) — {n['articles']} article(s)\n"
            f"Prix de vente moyen : {n['avg_price']}€ "
            f"(min {n['min_price']}€ / max {n['max_price']}€)\n"
            f"Prix d'achat estimé (vente ÷3) : {n['buy_estimate']}€\n"
            f"Marge brute estimée : {n['gross_margin']}€\n"
            f"Favoris moyens : {n['avg_favourites']}")


def write_outputs(niches: list[dict], catalog_id: int, out_dir: str) -> tuple[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    day = dt.date.today().isoformat()
    stem = os.path.join(out_dir, f"niches-{catalog_id}-{day}")

    with open(stem + ".json", "w", encoding="utf-8") as f:
        json.dump({"catalog_id": catalog_id, "date": day, "niches": niches},
                  f, ensure_ascii=False, indent=2)

    lines = [f"# Scan niches — catalog {catalog_id} — {day}",
             f"\n{len(niches)} nouvelle(s) niche(s) (≥{MIN_FAVS} favoris, <{MAX_AGE_DAYS}j)\n"]
    for n in niches:
        lines.append(f"## {n['brand']}")
        lines.append(c3po_callout(n))
        lines.append("\nArticles (modèle · taille · état) :")
        for a in n["samples"]:
            meta = " · ".join(str(x) for x in (a.get("title"), a.get("size"), a.get("status")) if x)
            lines.append(f"- {a['favourites']}❤ {a['price']}€ — {meta}")
            lines.append(f"  {a['url']}")
            if a["photo"]:
                lines.append(f"  ![]({a['photo']})")
        lines.append("")
    with open(stem + ".md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return stem + ".json", stem + ".md"


def load_known(path: str | None) -> set[str]:
    if not path or not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        return {line.strip().lower() for line in f if line.strip()}


# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description="Scan de niches resell Vinted (sans tokens IA).")
    ap.add_argument("--catalog-id", type=int, help="ID de la sous-catégorie Vinted (?catalog[]=NNNN dans l'URL).")
    ap.add_argument("--list-catalogs", action="store_true", help="Affiche l'arbre des catégories et quitte.")
    ap.add_argument("--min-favs", type=int, default=MIN_FAVS)
    ap.add_argument("--max-age-days", type=int, default=MAX_AGE_DAYS)
    ap.add_argument("--min-price", type=float, default=MIN_PRICE, help="Prix minimum en € (ex: 150).")
    ap.add_argument("--min-articles", type=int, default=MIN_ARTICLES)
    ap.add_argument("--max-pages", type=int, default=MAX_PAGES)
    ap.add_argument("--known-file", help="Fichier des marques déjà connues (1 par ligne) à écarter.")
    ap.add_argument("--out", default="out", help="Dossier de sortie (défaut: out/).")
    args = ap.parse_args()

    if args.list_catalogs:
        list_catalogs(new_session())
        return

    if not args.catalog_id:
        ap.error("--catalog-id requis (ou utilise --list-catalogs pour le trouver).")

    print(f"Scan catalog {args.catalog_id} — filtres : ≥{args.min_favs} favoris, "
          f"<{args.max_age_days}j, ≥{args.min_price:.0f}€, ≥{args.min_articles} articles/marque")
    hot = scan(args.catalog_id, args.min_favs, args.max_age_days,
               args.max_pages, args.min_price)
    print(f"  {len(hot)} article(s) chaud(s) trouvé(s).")

    known = load_known(args.known_file)
    niches = aggregate(hot, args.min_articles, known)
    print(f"  {len(niches)} nouvelle(s) niche(s) après dédup ({len(known)} marques connues écartées).")

    if not niches:
        print("Rien à enregistrer aujourd'hui.")
        return

    js, md = write_outputs(niches, args.catalog_id, args.out)
    print(f"\nÉcrit : {js}\n        {md}")
    print("\nTop niches :")
    for n in niches[:10]:
        print(f"  • {n['brand']:<22} {n['articles']} art. · vente {n['avg_price']}€ "
              f"· achat {n['buy_estimate']}€ · marge {n['gross_margin']}€ · {n['avg_favourites']}❤")


if __name__ == "__main__":
    main()
