#!/usr/bin/env python3
"""Costruisce docs/db.json: tutte le carte YGOPRODeck (nome inglese e italiano, prezzi, stampe) + hash
percettivi delle immagini. Le immagini si scaricano UNA volta in data/small/ (policy YGOPRODeck: scarica e
ri-ospita, mai hotlink) e restano fuori dal repo. Se docs/db.json esiste gia', gli hash delle immagini non
presenti in locale vengono riusati: cosi' GitHub Actions aggiorna carte nuove e prezzi scaricando solo le
immagini nuove (.github/workflows/update-db.yml).

  python build_db.py                 # build completa (~15k immagini, ~40 min la prima volta, poi incrementale)
  python build_db.py --limit 300     # prova rapida
  python build_db.py --hash-only     # ricalcola db.json dalle immagini gia' scaricate
  python build_db.py --selftest      # controllo: gli hash sono stabili e distinguono carte diverse
"""
import argparse, json, os, sys, time, urllib.request
import numpy as np, cv2

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data"); IMGDIR = os.path.join(DATA, "small")
API = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
IMG = "https://images.ygoprodeck.com/images/cards_small/{}.jpg"
ART = (0.116, 0.179, 0.884, 0.705)   # riquadro illustrazione, frazioni (x0,y0,x1,y1) del layout standard
RATE = 10.0                           # immagini al secondo (con la latenza di rete ≈ 5/s reali; il server chiede di non martellare)


def get(url, binary=False):
    for i in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ygoscan-build/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read() if binary else json.load(r)
        except Exception as e:                       # rete instabile: riprova con attesa crescente
            if i == 3: raise
            time.sleep(3 * (i + 1))


# --- hash percettivi: DEVONO restare identici a docs/index.html (stessa formula, stesso ordine dei bit)
def gray(im):
    return cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)

def phash_small(s):                                  # s: 32x32 (valori interi 0-255)
    d = cv2.dct(np.ascontiguousarray(s, np.float32))[:8, :8].flatten()   # 64 coeff. a bassa frequenza, DC incluso
    med = np.median(d)
    return "".join("1" if v > med else "0" for v in d)

def dhash_small(s):                                  # s: 8 righe x 9 colonne
    return "".join("1" if b else "0" for b in (s[:, 1:] > s[:, :-1]).flatten())

def phash(g):
    return phash_small(cv2.resize(g, (32, 32), interpolation=cv2.INTER_AREA))

def dhash(g):
    return dhash_small(cv2.resize(g, (9, 8), interpolation=cv2.INTER_AREA).astype(np.int16))

def art(im):
    h, w = im.shape[:2]
    return im[int(ART[1]*h):int(ART[3]*h), int(ART[0]*w):int(ART[2]*w)]

def bits2hex(b):
    return "%016x" % int(b, 2)

def hashes(im):
    g = gray(im)
    return [bits2hex(dhash(g)), bits2hex(phash(g)), bits2hex(phash(gray(art(im))))]


def selftest():
    rng = np.random.default_rng(0)
    a = rng.integers(0, 255, (391, 268, 3), np.uint8); a = cv2.GaussianBlur(a, (21, 21), 0)
    b = rng.integers(0, 255, (391, 268, 3), np.uint8); b = cv2.GaussianBlur(b, (21, 21), 0)
    def ham(x, y): return bin(int(x, 16) ^ int(y, 16)).count("1")
    ha, hb = hashes(a), hashes(b)
    a2 = cv2.resize(cv2.GaussianBlur(a, (5, 5), 0), (200, 292))   # stessa immagine, sfocata e ridimensionata
    ha2 = hashes(a2)
    same = [ham(x, y) for x, y in zip(ha, ha2)]; diff = [ham(x, y) for x, y in zip(ha, hb)]
    assert all(s <= 10 for s in same), same       # stessa carta: pochi bit diversi
    assert all(d >= 20 for d in diff), diff       # carte diverse: molti bit diversi
    assert len(ha[0]) == 16 and len(ha[1]) == 16 and len(ha[2]) == 16
    print("selftest OK  stessa carta:", same, " carte diverse:", diff)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--hash-only", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest: return selftest()
    os.makedirs(IMGDIR, exist_ok=True)
    cache, cache_it = os.path.join(DATA, "cardinfo.json"), os.path.join(DATA, "cardinfo_it.json")
    for path, url in ((cache, API), (cache_it, API + "?language=it")):
        if not os.path.exists(path) or time.time() - os.path.getmtime(path) > 86400:
            print("scarico l'elenco carte", url.split("?")[-1] if "?" in url else "(inglese)", "...")
            json.dump(get(url), open(path, "w", encoding="utf-8"))
    cards = json.load(open(cache, encoding="utf-8"))["data"]
    names_it = {c["id"]: c["name"] for c in json.load(open(cache_it, encoding="utf-8")).get("data", [])}
    if a.limit: cards = cards[: a.limit]
    dst = os.path.join(HERE, "docs", "db.json"); prev = {}
    if os.path.exists(dst):                          # hash gia' calcolati (es. GitHub Actions senza immagini locali): si riusano
        try:
            for c in json.load(open(dst, encoding="utf-8"))["cards"]:
                for im in c[6]: prev[im[0]] = im
        except Exception: prev = {}
    print("carte:", len(cards), "| nomi italiani:", len(names_it), "| hash riusabili:", len(prev))

    have = lambda iid: os.path.exists(os.path.join(IMGDIR, f"{iid}.jpg")) or iid in prev
    todo = [img["id"] for c in cards for img in c.get("card_images", []) if not have(img["id"])]
    if not a.hash_only and todo:
        print("immagini da scaricare:", len(todo)); t0 = time.time()
        for i, iid in enumerate(todo):
            p = os.path.join(IMGDIR, f"{iid}.jpg")
            try:
                open(p, "wb").write(get(IMG.format(iid), binary=True))
            except Exception as e:
                print("KO", iid, e)
            if i % 200 == 0: print(f"  {i}/{len(todo)}  {time.time()-t0:.0f}s", flush=True)
            time.sleep(1.0 / RATE)

    try:
        import cardmarket; cardmarket.enrich(cards)      # prezzi Cardmarket € per stampa (listino pubblico giornaliero)
    except Exception as e:
        print("Cardmarket non disponibile, si va avanti con TCGplayer:", e)
    out, missing = [], 0
    for c in cards:
        imgs = []
        for img in c.get("card_images", []):
            im = cv2.imread(os.path.join(IMGDIR, f"{img['id']}.jpg"))
            if im is not None: imgs.append([img["id"]] + hashes(im))
            elif img["id"] in prev: imgs.append(prev[img["id"]])
            else: missing += 1
        if not imgs: continue
        pr = (c.get("card_prices") or [{}])[0]
        sets = [[s["set_code"], s.get("set_rarity_code", "").strip("()") or s.get("set_rarity", ""), float(s.get("set_price") or 0)]
                + ([round(s["cm_trend"], 2), round(s["cm_low"], 2), s["cm_flag"]] if "cm_trend" in s else [])
                for s in c.get("card_sets", [])]
        name_it = names_it.get(c["id"], "")
        out.append([c["id"], c["name"], c.get("humanReadableCardType", c.get("type", "")),
                    float(pr.get("cardmarket_price") or 0), float(pr.get("tcgplayer_price") or 0), sets, imgs,
                    name_it if name_it != c["name"] else "", c.get("attribute", "") or "", int(c.get("level") or c.get("linkval") or 0)])
    db = {"v": 4, "built": time.strftime("%Y-%m-%d"), "n": len(out),
          "fields": "id,name,type,cardmarket_eur,tcgplayer_usd,sets[[code,rarity,usd,cm_trend_eur?,cm_low_eur?,cm_flag?(0 esatto,1 per rarita',2 intervallo)]],images[[id,dhash,phash,arthash]],name_it,attribute,level",
          "cards": out}
    json.dump(db, open(dst, "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False)
    print(f"db.json: {len(out)} carte, {missing} immagini mancanti, {os.path.getsize(dst)/1e6:.1f} MB")


if __name__ == "__main__":
    main()
