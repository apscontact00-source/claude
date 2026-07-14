#!/usr/bin/env python3
"""
push_to_notion.py — écrit les niches d'un scan dans Notion, SANS tokens IA.

Lit un fichier out/niches-*.json (produit par scan_niches.py OU scan_niches_browser.mjs)
et crée, via l'API officielle Notion, une page par marque + une sous-page catégorie
contenant les photos des annonces et le callout "📊 Analyse prix C3PO".

C'est le dernier maillon de l'algo autonome : aucune IA, aucun token Claude.
Tout passe par un jeton d'intégration Notion (NOTION_TOKEN), pas par moi.

Usage :
  export NOTION_TOKEN=secret_xxx           # ou dans scripts/.env
  python scripts/push_to_notion.py out/niches-<id>-<date>.json \
      --parent 39c2c750db1e8118af23cb660869b321 --category Sacs
Options : --dry (n'écrit rien, affiche), --category "Sacs"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

try:
    import requests
except ImportError:
    sys.exit("pip install -r scripts/requirements.txt")

API = "https://api.notion.com/v1"
VERSION = "2022-06-28"


def load_env(path: str = "scripts/.env") -> None:
    """Mini-loader .env (évite une dépendance)."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def headers() -> dict:
    tok = os.environ.get("NOTION_TOKEN", "").strip()
    if not tok:
        sys.exit("NOTION_TOKEN manquant (mets-le dans scripts/.env ou en variable d'env).")
    return {"Authorization": f"Bearer {tok}",
            "Notion-Version": VERSION,
            "Content-Type": "application/json"}


def req(method: str, path: str, payload: dict | None = None) -> dict:
    for attempt in range(4):
        r = requests.request(method, API + path, headers=headers(),
                             json=payload, timeout=30)
        if r.status_code == 429:  # rate limit → backoff
            time.sleep(float(r.headers.get("Retry-After", 2)))
            continue
        if r.status_code >= 400:
            raise RuntimeError(f"{r.status_code} {r.text[:300]}")
        time.sleep(0.35)  # ~3 req/s max
        return r.json()
    raise RuntimeError("Notion: trop de tentatives (429).")


# --------------------------------------------------------------------------- #
def existing_brands(parent_id: str) -> set[str]:
    """Titres des sous-pages déjà présentes sous le parent (dédup)."""
    names, cursor = set(), None
    while True:
        q = f"/blocks/{parent_id}/children?page_size=100"
        if cursor:
            q += f"&start_cursor={cursor}"
        data = req("GET", q)
        for b in data.get("results", []):
            if b.get("type") == "child_page":
                names.add(b["child_page"]["title"].strip().lower())
        if not data.get("has_more"):
            break
        cursor = data["next_cursor"]
    return names


def title_prop(text: str) -> dict:
    return {"title": {"title": [{"text": {"content": text[:2000]}}]}}


def callout_block(n: dict) -> dict:
    txt = (f"📊 Analyse prix C3PO (auto) — {n['articles']} article(s)\n"
           f"Prix de vente moyen : {n['avg_price']}€ "
           f"(min {n['min_price']}€ / max {n['max_price']}€)\n"
           f"Prix d'achat estimé (vente ÷3) : {n['buy_estimate']}€\n"
           f"Marge brute estimée : {n['gross_margin']}€\n"
           f"Favoris moyens : {n['avg_favourites']}")
    return {"object": "block", "type": "callout",
            "callout": {"rich_text": [{"type": "text", "text": {"content": txt}}],
                        "icon": {"emoji": "📊"}, "color": "blue_background"}}


def article_blocks(a: dict) -> list[dict]:
    meta = " · ".join(str(x) for x in (a.get("title"), a.get("size"), a.get("status")) if x)
    line = f"{a.get('favourites', 0)}❤ {a.get('price')}€ — {meta}"
    blocks = [{"object": "block", "type": "paragraph",
               "paragraph": {"rich_text": [{"type": "text",
                             "text": {"content": line[:2000],
                                      "link": {"url": a["url"]} if a.get("url") else None}}]}}]
    if a.get("photo"):
        blocks.append({"object": "block", "type": "image",
                       "image": {"type": "external", "external": {"url": a["photo"]}}})
    return blocks


def create_page(parent_id: str, title: str, children: list[dict] | None = None,
                icon: str | None = None) -> str:
    payload = {"parent": {"type": "page_id", "page_id": parent_id},
               "properties": title_prop(title)}
    if children:
        payload["children"] = children[:100]
    if icon:
        payload["icon"] = {"type": "emoji", "emoji": icon}
    return req("POST", "/pages", payload)["id"]


# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description="Pousse les niches d'un scan dans Notion (sans IA).")
    ap.add_argument("json_file", help="out/niches-*.json produit par un scan.")
    ap.add_argument("--parent", default=os.environ.get("NOTION_PARENT_PAGE_ID"),
                    help="ID de la page Notion parente (défaut: NOTION_PARENT_PAGE_ID).")
    ap.add_argument("--category", default="Sacs", help="Nom de la sous-page catégorie.")
    ap.add_argument("--dry", action="store_true", help="N'écrit rien, affiche seulement.")
    args = ap.parse_args()

    load_env()
    if not args.parent:
        sys.exit("--parent requis (ou NOTION_PARENT_PAGE_ID dans .env).")

    with open(args.json_file, encoding="utf-8") as f:
        niches = json.load(f).get("niches", [])
    if not niches:
        print("Aucune niche dans le JSON.")
        return

    known = set() if args.dry else existing_brands(args.parent)
    created, skipped = 0, 0
    for n in niches:
        brand = n["brand"]
        if brand.strip().lower() in known:
            skipped += 1
            print(f"  = {brand} (déjà présent, ignoré)")
            continue
        if args.dry:
            print(f"  + {brand} — {n['articles']} art. · vente {n['avg_price']}€ "
                  f"· marge {n['gross_margin']}€ · {n['avg_favourites']}❤")
            continue
        try:
            brand_id = create_page(args.parent, brand, icon="👜")
            children = [callout_block(n)]
            for a in n.get("samples", [])[:8]:
                children += article_blocks(a)
            create_page(brand_id, args.category, children=children)
            created += 1
            print(f"  + {brand} → créé")
        except Exception as e:
            print(f"  ! {brand} : {e}", file=sys.stderr)

    print(f"\nTerminé : {created} créée(s), {skipped} déjà présente(s).")


if __name__ == "__main__":
    main()
