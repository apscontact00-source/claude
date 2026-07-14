#!/usr/bin/env node
// scan_niches_browser.mjs — même scan de niches que scan_niches.py, mais via un VRAI navigateur.
//
// Pourquoi : Vinted a un anti-bot (DataDome) qui peut renvoyer 403 à un script "nu".
// Ici on pilote Chrome (comme ton émulateur web) : on ouvre vinted.fr, on hérite des cookies,
// puis on interroge l'API depuis la page (même origine) → pas de 403, pas de compte requis.
//
// Filtres : article >= 20 favoris ET < 3 semaines ET >= prix mini ; marque = niche si >= N articles.
// Sortie : out/niches-<catalog>-<date>.json + .md (5-8 articles/marque, modèle·taille·état + C3PO).
//
// Prérequis (sur la machine qui a accès à Vinted) :
//   npm i playwright-core      (Chrome/Chromium doit être installé)
//   node scripts/scan_niches_browser.mjs --catalog-id <ID> --min-price 150 --known-file out/known.txt
//
// Options : --min-favs 20  --max-age-days 21  --min-price 0  --min-articles 3  --max-pages 8
//           --executable "/chemin/vers/chrome"  (sinon on utilise le Chrome système)  --headful

import { chromium } from 'playwright-core';
import fs from 'node:fs';
import path from 'node:path';

// ---- args ----------------------------------------------------------------
function arg(name, def) {
  const i = process.argv.indexOf(`--${name}`);
  if (i === -1) return def;
  const v = process.argv[i + 1];
  return v && !v.startsWith('--') ? v : true;
}
const CATALOG_ID = arg('catalog-id');
const MIN_FAVS = +arg('min-favs', 20);
const MAX_AGE_DAYS = +arg('max-age-days', 21);
const MIN_PRICE = +arg('min-price', 0);
const MIN_ARTICLES = +arg('min-articles', 3);
const MAX_PAGES = +arg('max-pages', 8);
const KNOWN_FILE = arg('known-file');
const OUT = arg('out', 'out');
const EXECUTABLE = arg('executable', process.env.PW_CHROME);
const HEADFUL = arg('headful', false);
const BASE = process.env.VINTED_BASE || 'https://www.vinted.fr';

if (!CATALOG_ID) {
  console.error('--catalog-id requis (l’ID est dans l’URL Vinted : ?catalog[]=NNNN).');
  process.exit(2);
}

// ---- helpers -------------------------------------------------------------
const loadKnown = (f) =>
  f && fs.existsSync(f)
    ? new Set(fs.readFileSync(f, 'utf8').split('\n').map((s) => s.trim().toLowerCase()).filter(Boolean))
    : new Set();

function priceOf(it) {
  let p = it.price;
  if (p && typeof p === 'object') p = p.amount;
  const n = parseFloat(p);
  return Number.isFinite(n) ? n : null;
}
function tsOf(it) {
  const hi = (it.photo && it.photo.high_resolution) || {};
  const ts = hi.timestamp || (it.photo && it.photo.timestamp);
  return ts ? +ts : null;
}

// ---- scan ----------------------------------------------------------------
// Un scan = un contexte navigateur NEUF (cookies vierges), fermé et vidé à la fin.
async function scanCatalog(browser, catalogId, cutoff) {
  const ctx = await browser.newContext({ locale: 'fr-FR' });
  await ctx.clearCookies();                       // session vierge avant de commencer
  const page = await ctx.newPage();
  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 40000 });
  await page.waitForTimeout(2500);                // laisse l’anti-bot poser ses cookies

  const hot = [];
  let staleStreak = 0;
  for (let p = 1; p <= MAX_PAGES; p++) {
    const url =
      `${BASE}/api/v2/catalog/items?catalog_ids=${catalogId}` +
      `&order=newest_first&per_page=96&page=${p}` +
      (MIN_PRICE ? `&price_from=${MIN_PRICE}` : '');
    let items;
    try {
      items = await page.evaluate(async (u) => {
        const r = await fetch(u, { headers: { Accept: 'application/json' } });
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return (await r.json()).items || [];
      }, url);
    } catch (e) {
      console.error(`  ! [${catalogId}] page ${p} échouée : ${e.message}`);
      break;
    }
    if (!items.length) break;

    let recent = false;
    for (const it of items) {
      const ts = tsOf(it);
      if (ts === null || ts < cutoff) continue; // fraîcheur stricte < 3 semaines
      recent = true;
      if ((it.favourite_count | 0) < MIN_FAVS) continue;
      const price = priceOf(it);
      if (MIN_PRICE && (price === null || price < MIN_PRICE)) continue;
      hot.push({
        brand: (it.brand_title || 'Sans marque').trim(),
        title: it.title,          // modèle + couleur
        size: it.size_title,      // taille
        status: it.status,        // état
        price,
        favourites: it.favourite_count | 0,
        url: it.url,
        photo: it.photo && it.photo.url,
      });
    }
    staleStreak = recent ? 0 : staleStreak + 1;
    if (staleStreak >= 1 && p >= 2) break;
    await page.waitForTimeout(600);
  }
  await ctx.clearCookies();                       // supprime les cookies entre chaque scan
  await ctx.close();
  return hot;
}

async function run() {
  const launchOpts = { headless: !HEADFUL };
  if (EXECUTABLE) launchOpts.executablePath = EXECUTABLE;
  else launchOpts.channel = 'chrome'; // Chrome système sur ta machine
  const browser = await chromium.launch(launchOpts);
  const cutoff = Date.now() / 1000 - MAX_AGE_DAYS * 86400;
  // Plusieurs sous-catégories possibles : --catalog-id 16,19,246 → un scan (cookies neufs) par ID.
  const ids = String(CATALOG_ID).split(',').map((s) => s.trim()).filter(Boolean);
  let hot = [];
  for (const id of ids) {
    console.log(`  → scan catalog ${id} (session vierge, cookies supprimés après)`);
    hot = hot.concat(await scanCatalog(browser, id, cutoff));
  }
  await browser.close();
  return hot;
}

// ---- agrégation + sortie -------------------------------------------------
function aggregate(hot, known) {
  const byBrand = new Map();
  for (const a of hot) {
    if (!byBrand.has(a.brand)) byBrand.set(a.brand, []);
    byBrand.get(a.brand).push(a);
  }
  const niches = [];
  for (const [brand, arts] of byBrand) {
    if (known.has(brand.toLowerCase()) || brand.toLowerCase() === 'sans marque') continue;
    if (arts.length < MIN_ARTICLES) continue;
    const prices = arts.map((a) => a.price).filter((x) => x != null);
    if (!prices.length) continue;
    const avg = Math.round(prices.reduce((s, x) => s + x, 0) / prices.length);
    const buy = Math.round(avg / 3);
    niches.push({
      brand,
      articles: arts.length,
      avg_price: avg,
      min_price: Math.round(Math.min(...prices)),
      max_price: Math.round(Math.max(...prices)),
      buy_estimate: buy,
      gross_margin: avg - buy,
      avg_favourites: Math.round(arts.reduce((s, a) => s + a.favourites, 0) / arts.length),
      samples: arts.sort((a, b) => b.favourites - a.favourites).slice(0, 8),
    });
  }
  niches.sort((a, b) => b.gross_margin * b.avg_favourites - a.gross_margin * a.avg_favourites);
  return niches;
}

function write(niches) {
  fs.mkdirSync(OUT, { recursive: true });
  const day = new Date().toISOString().slice(0, 10);
  const idTag = String(CATALOG_ID).replace(/[^0-9]+/g, '-');
  const stem = path.join(OUT, `niches-${idTag}-${day}`);
  fs.writeFileSync(stem + '.json', JSON.stringify({ catalog_id: +CATALOG_ID, date: day, niches }, null, 2));

  const L = [`# Scan niches — catalog ${CATALOG_ID} — ${day}`,
    `\n${niches.length} nouvelle(s) niche(s) (≥${MIN_FAVS} favoris, <${MAX_AGE_DAYS}j, ≥${MIN_PRICE}€)\n`];
  for (const n of niches) {
    L.push(`## ${n.brand}`);
    L.push(`📊 Analyse prix C3PO (auto) — ${n.articles} article(s)`);
    L.push(`Prix de vente moyen : ${n.avg_price}€ (min ${n.min_price}€ / max ${n.max_price}€)`);
    L.push(`Prix d'achat estimé (vente ÷3) : ${n.buy_estimate}€`);
    L.push(`Marge brute estimée : ${n.gross_margin}€`);
    L.push(`Favoris moyens : ${n.avg_favourites}`);
    L.push(`\nArticles (modèle · taille · état) :`);
    for (const a of n.samples) {
      const meta = [a.title, a.size, a.status].filter(Boolean).join(' · ');
      L.push(`- ${a.favourites}❤ ${a.price}€ — ${meta}`);
      L.push(`  ${a.url}`);
      if (a.photo) L.push(`  ![](${a.photo})`);
    }
    L.push('');
  }
  fs.writeFileSync(stem + '.md', L.join('\n'));
  return stem;
}

// ---- main ----------------------------------------------------------------
(async () => {
  console.log(`Scan (navigateur) catalog ${CATALOG_ID} — ≥${MIN_FAVS} favoris, <${MAX_AGE_DAYS}j, ≥${MIN_PRICE}€, ≥${MIN_ARTICLES} art/marque`);
  const hot = await run();
  console.log(`  ${hot.length} article(s) chaud(s).`);
  const niches = aggregate(hot, loadKnown(KNOWN_FILE));
  console.log(`  ${niches.length} nouvelle(s) niche(s) après dédup.`);
  if (!niches.length) { console.log('Rien à enregistrer.'); return; }
  const stem = write(niches);
  console.log(`\nÉcrit : ${stem}.json / .md`);
  for (const n of niches.slice(0, 10))
    console.log(`  • ${n.brand} — ${n.articles} art. · vente ${n.avg_price}€ · achat ${n.buy_estimate}€ · marge ${n.gross_margin}€ · ${n.avg_favourites}❤`);
})().catch((e) => { console.error('ERREUR:', e.message); process.exit(1); });
