#!/usr/bin/env python3
"""Prezzi Cardmarket (€) per singola stampa, dal listino pubblico che Cardmarket aggiorna ogni notte:
  price_guide_3.json (prezzi per prodotto) + products_singles_3.json (prodotti: nome + id espansione).
Il listino non ha codici set ne' rarita': ogni espansione Cardmarket viene agganciata ai set YGOPRODeck
confrontando gli elenchi di nomi delle carte (anche piu' set per espansione: Cardmarket fonde i Duel
Terminal negli Hidden Arsenal e le edizioni OTS in una sola), e dentro il set le stampe si abbinano cosi':
  1 prodotto  <-> 1 stampa           -> esatto                          (cm_flag 0)
  k prodotti  <-> k stampe           -> per rarita'                     (cm_flag 1: rarita' piu' alta = prezzo piu' alto)
  conteggi diversi                   -> intervallo                      (cm_flag 2: trend = massimo, low = minimo dei candidati)
  stampa assente dal listino         -> stima dalle stampe simili       (cm_flag 3: mediana delle stampe della stessa carta
                                                                          con la stessa rarita', o la piu' vicina)
Uso: enrich(cards) aggiunge a ogni card_set le chiavi cm_trend, cm_low, cm_flag (solo se trovate).
  python cardmarket.py            # statistiche di copertura sul cardinfo.json locale
  python cardmarket.py --selftest # controllo dell'abbinamento per rarita' e della normalizzazione dei nomi
"""
import collections, json, os, re, statistics, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, "data")
BASE = "https://downloads.s3.cardmarket.com/productCatalog/"
FILES = {"cm_price.json": "priceGuide/price_guide_3.json", "cm_prod.json": "productList/products_singles_3.json"}
RANK = {"C": 0, "SP": 0, "SSP": 0, "SFR": 0, "NR": 0, "R": 1, "DNPR": 1, "SR": 2, "DRPR": 2, "UR": 3, "DUPR": 3, "GUR": 3,
        "ScR": 4, "PS": 4, "DSPR": 4, "MLR": 4, "GScR": 4, "CR": 5, "UtR": 5, "PScR": 5, "PGR": 5, "UScR": 5,
        "QCSR": 6, "Quarter Century Secret Rare": 6, "StR": 7, "GR": 7}
INVISIBLE = re.compile("[​-‏⁠﻿]")


def fetch(name):
    p = os.path.join(DATA, name); os.makedirs(DATA, exist_ok=True)
    if not os.path.exists(p) or time.time() - os.path.getmtime(p) > 20 * 3600:
        for i in range(3):
            try:
                req = urllib.request.Request(BASE + FILES[name], headers={"User-Agent": "ygoscan-build/1.0"})
                with urllib.request.urlopen(req, timeout=120) as r: open(p, "wb").write(r.read()); break
            except Exception:
                if i == 2:
                    if os.path.exists(p): break          # rete giu': si usa il file precedente
                    raise
                time.sleep(5)
    return json.load(open(p, encoding="utf-8"))

def norm(n):
    n = INVISIBLE.sub("", n.replace('""', '"')).replace("’", "'").replace("–", "-").replace("—", "-")
    n = re.sub(r"\s*\((skill card|skill)\)\s*$", "", n.strip().lower())
    return re.sub(r"\s+", " ", n)
def squash(n): return re.sub(r"[^a-z0-9]", "", norm(n))          # chiave tollerante: solo lettere e cifre
def rank(s): return RANK.get((s.get("set_rarity_code") or "").strip("()") or s.get("set_rarity", ""), 2)


def pair(prints, prods):
    """abbina stampe (per rarita' crescente) a prodotti (per trend crescente): -> lista di (stampa, prodotto)"""
    ps = sorted(prints, key=rank); qs = sorted(prods, key=lambda q: q["trend"])
    return list(zip(ps, qs))


def enrich(cards, verbose=True):
    P = {p["idProduct"]: p for p in fetch("cm_price.json")["priceGuides"] if p.get("trend") is not None}
    prods = [dict(p, trend=P[p["idProduct"]]["trend"], low=P[p["idProduct"]].get("low") or 0)
             for p in fetch("cm_prod.json")["products"] if p["idProduct"] in P]
    exp_names = collections.defaultdict(set); by_exp_name = collections.defaultdict(list); by_exp_sq = collections.defaultdict(list)
    for q in prods:
        n = norm(q["name"]); exp_names[q["idExpansion"]].add(n)
        by_exp_name[(q["idExpansion"], n)].append(q); by_exp_sq[(q["idExpansion"], squash(q["name"]))].append(q)
    set_names = collections.defaultdict(set); by_name = collections.defaultdict(set)
    for c in cards:
        for s in c.get("card_sets", []): set_names[s["set_name"]].add(norm(c["name"])); by_name[norm(c["name"])].add(s["set_name"])
    # 1) espansione -> set: massima sovrapposizione di nomi; a parita' (es. Magic Ruler / Spell Ruler) il set ancora libero;
    #    inoltre ogni set contenuto quasi per intero nell'espansione (Duel Terminal in Hidden Arsenal, OTS EN in OTS POR)
    cand = []
    for e, names in exp_names.items():
        cnt = collections.Counter(s for n in names for s in by_name.get(n, ()))
        if cnt: cand.append((cnt.most_common(1)[0][1], e, cnt))
    assigned = collections.defaultdict(list)
    for best, e, cnt in sorted(cand, reverse=True):
        if best < 3: continue
        opts = [(len(assigned[s]), -cnt[s] / len(exp_names[e] | set_names[s]), s) for s, v in cnt.items() if v >= 0.9 * best]
        s = min(opts)[2]
        if cnt[s] / len(exp_names[e] | set_names[s]) >= 0.5 or cnt[s] >= 0.8 * len(exp_names[e]):
            assigned[s].append((cnt[s], e))
        for s2, v in cnt.items():
            if s2 != s and v >= 3 and v >= 0.8 * len(set_names[s2]) and all(x != e for _, x in assigned[s2]):
                assigned[s2].append((v, e))
    for s in assigned: assigned[s].sort(reverse=True)               # prima l'espansione che copre di piu'
    # 2) stampa -> prodotto
    stats = collections.Counter()
    for c in cards:
        n, sq = norm(c["name"]), squash(c["name"]); groups = collections.defaultdict(list)
        for s in c.get("card_sets", []): groups[s["set_name"]].append(s)
        for sname, prints in groups.items():
            qs = []
            for _, e in assigned.get(sname, []):
                qs = by_exp_name.get((e, n)) or by_exp_sq.get((e, sq)) or []
                if qs: break
            if not qs: continue
            if len(qs) == len(prints):
                for s, q in pair(prints, qs):
                    s["cm_trend"], s["cm_low"], s["cm_flag"] = q["trend"], q["low"], 0 if len(qs) == 1 else 1
                stats["esatto" if len(qs) == 1 else "per rarita'"] += len(prints)
            else:
                hi, lo = max(q["trend"] for q in qs), min(q["low"] for q in qs)
                for s in prints: s["cm_trend"], s["cm_low"], s["cm_flag"] = hi, lo, 2
                stats["intervallo"] += len(prints)
        # 3) stampe assenti dal listino: stima dalle stampe simili della stessa carta (stessa rarita', o la piu' vicina)
        known = collections.defaultdict(list)
        for s in c.get("card_sets", []):
            if s.get("cm_flag") in (0, 1): known[rank(s)].append(s)
        for s in c.get("card_sets", []):
            if "cm_trend" in s or not known: continue
            r = min(known, key=lambda k: (abs(k - rank(s)), k)); sim = known[r]
            s["cm_trend"] = round(statistics.median(x["cm_trend"] for x in sim), 2)
            s["cm_low"] = round(min(x["cm_low"] for x in sim), 2); s["cm_flag"] = 3
            stats["stima da stampe simili"] += 1
        stats["senza"] += sum(1 for s in c.get("card_sets", []) if "cm_trend" not in s)
    if verbose:
        tot = sum(stats.values())
        print("Cardmarket:", ", ".join(f"{k} {v} ({100*v/tot:.0f}%)" for k, v in stats.most_common()), f"| set agganciati {len(assigned)}")
    return stats


def selftest():
    prints = [{"set_rarity_code": "(UR)"}, {"set_rarity_code": "(C)"}, {"set_rarity_code": "(ScR)"}]
    prods = [{"trend": 5.0}, {"trend": 0.1}, {"trend": 30.0}]
    got = {p["set_rarity_code"]: q["trend"] for p, q in pair(prints, prods)}
    assert got == {"(C)": 0.1, "(UR)": 5.0, "(ScR)": 30.0}, got
    assert norm('""A"" Cell Breeding Device') == '"a" cell breeding device' and norm("Mind Scan (Skill)") == "mind scan"
    assert norm("Apple of Enlightenment‎‎") == "apple of enlightenment"
    assert squash("Blitzclique - Return Stroke") == squash("Blitzclique Return Stroke")
    print("selftest OK", got)


if __name__ == "__main__":
    if "--selftest" in sys.argv: selftest()
    else: enrich(json.load(open(os.path.join(DATA, "cardinfo.json"), encoding="utf-8"))["data"])
