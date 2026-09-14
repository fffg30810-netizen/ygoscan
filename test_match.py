#!/usr/bin/env python3
"""Check eseguibile del riconoscimento. Simula la camera (sfondo, posa fuori centro, prospettiva,
riflessi, luce, sfocatura, rumore, jpeg) sulle carte del db e verifica che la ricerca usata da
docs/index.html (griglia di candidati attorno alla guida, pHash dell'illustrazione su tutto il db,
conferma con pHash+dHash dell'intera carta e margine sul secondo candidato) trovi la carta giusta
e RIFIUTI carte sconosciute e inquadrature vuote.

  python test_match.py [--n 150] [--seed 0]
Scrive anche data/test/photo_*.jpg + expected.json (con i risultati Python) per la prova di
parita' nel browser: ygo.scanStill('/data/test/photo_0.jpg') deve dare la stessa carta e distanze simili.
"""
import argparse, json, os
import numpy as np, cv2
from build_db import HERE, IMGDIR, ART, phash_small, dhash_small, gray

ASPECT = 59 / 86
WW, WH, M = 240, 350, 0.15                      # canvas di lavoro = guida + margine (come nel JS)
GW = WW / (1 + 2 * M); GH = GW / ASPECT
OFFS = [-2, -1, 0, 1, 2]; SCALES = [0.9, 1.0, 1.1]; STEP = 0.04; STEP2 = 0.015
T = dict(a=18, pd=40, m=4)                      # soglie: DEVONO coincidere con index.html (a, p+d, margine a2-a)


def popcount(a):
    if hasattr(np, "bitwise_count"): return np.bitwise_count(a)
    return np.unpackbits(a.view(np.uint8)).reshape(len(a), 64).sum(1)

def ham(x, y): return int(bin(x ^ y).count("1"))

def integral(g):
    I = np.zeros((g.shape[0] + 1, g.shape[1] + 1), np.float64)
    I[1:, 1:] = g.astype(np.float64).cumsum(0).cumsum(1); return I

def box_resize(I, x0, y0, x1, y1, w, h):
    """media per blocchi con bordi interi arrotondati come Math.round -> array h x w di interi"""
    xs = np.clip(np.floor(x0 + (x1 - x0) * np.arange(w + 1) / w + 0.5), 0, I.shape[1] - 1).astype(int)
    ys = np.clip(np.floor(y0 + (y1 - y0) * np.arange(h + 1) / h + 0.5), 0, I.shape[0] - 1).astype(int)
    s = (I[ys[1:, None], xs[None, 1:]] - I[ys[:-1, None], xs[None, 1:]]
         - I[ys[1:, None], xs[None, :-1]] + I[ys[:-1, None], xs[None, :-1]])
    area = (ys[1:, None] - ys[:-1, None]) * (xs[None, 1:] - xs[None, :-1])
    return np.floor(np.where(area > 0, s / np.maximum(area, 1), 0) + 0.5)


class DB:
    def __init__(self, cards):
        self.img, self.card, d, p, a = [], [], [], [], []
        for ci, c in enumerate(cards):
            for im in c[6]:
                self.img.append(im[0]); self.card.append(ci)
                d.append(int(im[1], 16)); p.append(int(im[2], 16)); a.append(int(im[3], 16))
        self.d, self.p, self.a = (np.array(x, dtype=np.uint64) for x in (d, p, a))
        self.cards = cards

    def _pass(self, I, rects, minA, best):
        for (x0, y0, w, h) in rects:
            ah = int(phash_small(box_resize(I, x0 + ART[0] * w, y0 + ART[1] * h,
                                            x0 + ART[2] * w, y0 + ART[3] * h, 32, 32)), 2)
            dist = popcount(self.a ^ np.uint64(ah)).astype(np.int64); minA = np.minimum(minA, dist)
            k = int(dist.argmin())
            if dist[k] < best[0]: best = (int(dist[k]), k, (x0, y0, w, h))
        return minA, best

    def search(self, g):
        """-> (indice immagine, dist dHash carta, dist pHash carta, dist pHash illustrazione, 2a migliore illustrazione)"""
        I = integral(g); minA = np.full(len(self.a), 99, np.int64); best = (99, -1, None)
        coarse = [(WW / 2 - GW * s / 2 + dx * STEP * GW, WH / 2 - GH * s / 2 + dy * STEP * GH, GW * s, GH * s)
                  for s in SCALES for dy in OFFS for dx in OFFS]
        minA, best = self._pass(I, coarse, minA, best)
        a, k, (x0, y0, w, h) = best; cx, cy = x0 + w / 2, y0 + h / 2          # raffinamento fine attorno al migliore
        fine = [(cx - w * f / 2 + dx * STEP2 * GW, cy - h * f / 2 + dy * STEP2 * GH, w * f, h * f)
                for f in (0.96, 1.0, 1.04) for dy in (-1, 0, 1) for dx in (-1, 0, 1)]
        minA, best = self._pass(I, fine, minA, best)
        a, k, (x0, y0, w, h) = best
        others = np.delete(minA, k); a2 = int(others.min()) if len(others) else 99
        ph = int(phash_small(box_resize(I, x0, y0, x0 + w, y0 + h, 32, 32)), 2)
        dh = int(dhash_small(box_resize(I, x0, y0, x0 + w, y0 + h, 9, 8)), 2)
        return k, ham(dh, int(self.d[k])), ham(ph, int(self.p[k])), a, a2


def simulate(card, rng, scale=1.0, empty=False, pose=None):
    """fotografa la carta nel canvas di lavoro; pose fissa la posa per generare 2 frame consecutivi della stessa scena"""
    W, H = int(WW * scale), int(WH * scale)
    bg = np.full((H, W, 3), rng.integers(30, 190), np.uint8)
    bg = np.clip(bg.astype(np.int16) + rng.normal(0, 10, bg.shape), 0, 255).astype(np.uint8)
    out = bg
    if not empty:
        if pose is None:
            pose = dict(s=rng.uniform(0.9, 1.1), ox=rng.uniform(-.06, .06), oy=rng.uniform(-.06, .06),
                        ang=rng.uniform(-3, 3), jit=rng.uniform(-.03, .03, (4, 2)), glare=rng.random() < .3,
                        gx=rng.uniform(-.2, .2), gy=rng.uniform(-.3, .3), ga=rng.uniform(0, 180))
        w, h = GW * pose["s"] * scale, GH * pose["s"] * scale
        cx = W / 2 + pose["ox"] * GW * scale; cy = H / 2 + pose["oy"] * GH * scale
        ang = np.deg2rad(pose["ang"]); R = np.array([[np.cos(ang), -np.sin(ang)], [np.sin(ang), np.cos(ang)]])
        pts = np.array([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]])
        dst = (pts @ R.T + [cx, cy] + pose["jit"] * [w, h]).astype(np.float32)
        ch, cw = card.shape[:2]; src = np.array([[0, 0], [cw, 0], [cw, ch], [0, ch]], np.float32)
        Mx = cv2.getPerspectiveTransform(src, dst)
        warped = cv2.warpPerspective(card, Mx, (W, H))
        mask = cv2.warpPerspective(np.full((ch, cw), 255, np.uint8), Mx, (W, H))
        out = np.where(mask[..., None] > 0, warped, bg)
        if pose["glare"]:                                       # riflesso su carta foil
            ov = out.copy()
            cv2.ellipse(ov, (int(cx + pose["gx"] * w), int(cy + pose["gy"] * h)),
                        (int(w * .25), int(h * .12)), pose["ga"], 0, 360, (255, 255, 255), -1)
            out = cv2.addWeighted(out, .7, ov, .3, 0)
    out = np.clip(out.astype(np.float32) * rng.uniform(.7, 1.3) + rng.uniform(-30, 30), 0, 255)
    out = cv2.GaussianBlur(out, (0, 0), rng.uniform(.4, 1.4))
    out = np.clip(out + rng.normal(0, rng.uniform(2, 8), out.shape), 0, 255).astype(np.uint8)
    ok, enc = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, int(rng.integers(60, 90))])
    return cv2.imdecode(enc, 1), pose

def accept(r, t=T):                              # r = (k, d, p, a, a2)
    return r[3] <= t["a"] and r[1] + r[2] <= t["pd"] and r[4] - r[3] >= t["m"]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=150); ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(); rng = np.random.default_rng(args.seed)
    cards = json.load(open(os.path.join(HERE, "docs", "db.json"), encoding="utf-8"))["cards"]
    cards = [c for c in cards if all(os.path.exists(os.path.join(IMGDIR, f"{im[0]}.jpg")) for im in c[6])]
    idx = rng.permutation(len(cards)); unknown = [cards[i] for i in idx[:30]]; known = [cards[i] for i in idx[30:]]
    db = DB(known); print(f"db: {len(known)} carte note ({len(db.img)} immagini), {len(unknown)} tenute fuori come sconosciute")
    img = lambda c: cv2.imread(os.path.join(IMGDIR, f"{c[6][0][0]}.jpg"))

    def pair(c, empty=False):                    # due frame consecutivi della stessa scena (rumore diverso)
        f1, pose = simulate(img(c), rng, empty=empty); f2, _ = simulate(img(c), rng, empty=empty, pose=pose)
        return db.search(gray(f1)), db.search(gray(f2))

    pos = []                                     # ((r1, r2), id atteso)
    for i in range(args.n):
        c = known[int(rng.integers(len(known)))]; pos.append((pair(c), c[0]))
    neg_unk = [pair(c) for c in unknown for _ in range(2)]; neg_empty = [pair(known[0], empty=True) for _ in range(30)]
    neg = neg_unk + neg_empty
    right = lambda r, cid: db.cards[db.card[r[0]]][0] == cid

    def score(t):
        tp1 = sum(1 for (r1, r2), cid in pos if accept(r1, t) and right(r1, cid)) / len(pos)
        tp2 = sum(1 for (r1, r2), cid in pos if accept(r1, t) and accept(r2, t) and r1[0] == r2[0] and right(r1, cid)) / len(pos)
        wrong = sum(1 for (r1, r2), cid in pos if accept(r1, t) and not right(r1, cid))
        fp1 = sum(1 for r1, r2 in neg if accept(r1, t)) + sum(1 for r1, r2 in neg if accept(r2, t))
        fp2 = sum(1 for r1, r2 in neg_unk if accept(r1, t) and accept(r2, t) and r1[0] == r2[0])
        fp2e = sum(1 for r1, r2 in neg_empty if accept(r1, t) and accept(r2, t) and r1[0] == r2[0])
        return tp1, tp2, wrong, fp1, fp2, fp2e
    print(f"sweep soglie ({len(pos)} positivi, {len(neg)} negativi: {len(neg_unk)} sconosciute + {len(neg_empty)} vuote)")
    print(f"   a   p+d  marg | foto: ok%  scambi | live(2 frame): ok%  | FP foto(/{2*len(neg)})  FP live sconosciute(/{len(neg_unk)})  vuote(/{len(neg_empty)})")
    for ta in (16, 20):
        for tpd in (34, 40, 46):
            for m in (2, 4, 6):
                tp1, tp2, wrong, fp1, fp2, fp2e = score(dict(a=ta, pd=tpd, m=m))
                print(f"  {ta:2d}  {tpd:3d}   {m:d}   |     {100*tp1:3.0f}    {wrong:2d}    |       {100*tp2:3.0f}       |   {fp1:3d}              {fp2:3d}                  {fp2e:3d}")
    A = np.array([r1[1:] for (r1, r2), cid in pos if right(r1, cid)]); B = np.array([r1[1:] for r1, r2 in neg_unk]); E = np.array([r1[1:] for r1, r2 in neg_empty])
    print(f"carta giusta:  a med/max {np.median(A[:,2]):.0f}/{A[:,2].max()}  p+d {np.median(A[:,0]+A[:,1]):.0f}/{(A[:,0]+A[:,1]).max()}  margine med/min {np.median(A[:,3]-A[:,2]):.0f}/{(A[:,3]-A[:,2]).min()}")
    print(f"sconosciute:   a med/min {np.median(B[:,2]):.0f}/{B[:,2].min()}  p+d {np.median(B[:,0]+B[:,1]):.0f}/{(B[:,0]+B[:,1]).min()}  margine med/max {np.median(B[:,3]-B[:,2]):.0f}/{(B[:,3]-B[:,2]).max()}")
    print(f"vuote:         a med/min {np.median(E[:,2]):.0f}/{E[:,2].min()}  p+d {np.median(E[:,0]+E[:,1]):.0f}/{(E[:,0]+E[:,1]).min()}  margine med/max {np.median(E[:,3]-E[:,2]):.0f}/{(E[:,3]-E[:,2]).max()}")
    tp1, tp2, wrong, fp1, fp2, fp2e = score(T)
    print(f"REGOLA SCELTA {T}: foto {100*tp1:.0f}% ok, {wrong} scambi, {fp1} FP su {2*len(neg)} | live {100*tp2:.0f}% ok, FP {fp2} sconosciute + {fp2e} vuote")
    for i, (r1, r2) in enumerate(neg_unk):
        if accept(r1) and accept(r2) and r1[0] == r2[0]:
            print(f"   FP live: sconosciuta '{unknown[i//2][1]}' scambiata per '{db.cards[db.card[r1[0]]][1]}' (d,p,a,a2)={r1[1:]}")

    tdir = os.path.join(HERE, "data", "test"); os.makedirs(tdir, exist_ok=True); exp = []
    for j in range(6):
        c = known[int(rng.integers(len(known)))]; im, _ = simulate(img(c), rng, scale=2.0)
        cv2.imwrite(os.path.join(tdir, f"photo_{j}.jpg"), im)
        im = cv2.imread(os.path.join(tdir, f"photo_{j}.jpg"))          # rilegge il jpeg come fara' il browser
        r = db.search(gray(cv2.resize(im, (WW, WH), interpolation=cv2.INTER_AREA)))
        exp.append({"file": f"photo_{j}.jpg", "id": c[0], "name": c[1], "py_imgId": db.img[r[0]], "py_dpa": list(r[1:]), "py_ok": accept(r)})
    json.dump(exp, open(os.path.join(tdir, "expected.json"), "w"), indent=1)
    print(f"foto di prova: {tdir}")

    assert tp1 >= 0.9, "riconoscimento da foto sotto il 90%"
    assert wrong == 0, "carte note scambiate per altre carte"
    assert fp2e == 0, "inquadrature vuote accettate: stringere le soglie"
    assert fp2 <= 2, "troppe carte sconosciute accettate (ammesse solo gemelle con la stessa illustrazione)"
    print("test_match OK")


if __name__ == "__main__":
    main()
