#!/usr/bin/env python3
"""Hamburger Weihnachtsmarkt als Partikelszene.

Erzeugt ein TikTok Video (9:16, 15 s, 30 fps) mit Code Intro,
Partikelaufbau von Rathaus, Lichterbaum, Karussell und Buden,
fliegendem Weihnachtsmann, Feuerwerk, Schnee und Glockenspiel.

Aufruf:  python3 hamburg_weihnachtsmarkt.py
Ergebnis: out/hamburg_weihnachtsmarkt.mp4
"""
import math
import os
import re
import subprocess
import sys
import wave
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 720, 1280, 30
DUR = 12.0
INTRO = 0.0                      # Code Intro (3.0 = an, 0 = aus)
SQ = 0.85                        # Szene stauchen: Platz fuer Schrift
GREETING = ("Merry Christmas", "Schnucki")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
FONT = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Regular.ttf"
SCRIPT = os.path.join(HERE, "fonts", "GreatVibes-Regular.ttf")
FONT_B = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf"

# Label IDs der Szenenmaske
(FACADE, ROOF, WINDOW, CLOCK, GOLD, TREEFILL, STAR, CAR_RED, CAR_CREAM,
 CAR_INNER, B_RED, B_GREEN, B_WOOD, B_LIT, SNOW, GROUND, CROWD, HAT) = range(1, 19)

# Label: (Farbe, Helligkeit, Streuung, Funkeln)
PALETTE = {
    FACADE:    ((205, 150, 90), 0.42, 0.30, 0.00),
    ROOF:      ((60, 170, 140), 0.62, 0.25, 0.00),
    WINDOW:    ((255, 200, 105), 1.00, 0.15, 0.12),
    CLOCK:     ((255, 240, 210), 0.95, 0.05, 0.00),
    GOLD:      ((255, 200, 80), 1.00, 0.15, 0.25),
    TREEFILL:  ((255, 190, 90), 0.20, 0.60, 0.70),
    STAR:      ((255, 240, 170), 1.40, 0.05, 0.25),
    CAR_RED:   ((225, 40, 45), 0.85, 0.15, 0.00),
    CAR_CREAM: ((255, 232, 195), 0.80, 0.10, 0.00),
    CAR_INNER: ((255, 165, 80), 0.32, 0.45, 0.10),
    B_RED:     ((195, 35, 40), 0.70, 0.20, 0.00),
    B_GREEN:   ((40, 125, 70), 0.75, 0.20, 0.00),
    B_WOOD:    ((160, 95, 50), 0.60, 0.25, 0.00),
    B_LIT:     ((255, 165, 70), 0.85, 0.30, 0.10),
    SNOW:      ((235, 242, 255), 0.85, 0.10, 0.00),
    GROUND:    ((45, 85, 205), 0.42, 0.55, 0.00),
    CROWD:     ((40, 45, 90), 0.22, 0.30, 0.00),
    HAT:       ((230, 45, 50), 0.45, 0.20, 0.00),
}
GOODS = np.array([(255, 170, 70), (255, 120, 60), (255, 220, 140),
                  (230, 80, 60), (255, 200, 90), (120, 200, 120)], float)

TREE_TOP, TREE_BASE, TREE_X, TREE_R = 500, 1080, 540, 152
CAR_X = 165


def sample(lbl, spacing=4, jitter=0.6, seed=0):
    """Rastert eine Labelmaske zu Partikeln (x, y, Farbe, Funkeln)."""
    a = np.asarray(lbl)
    r = np.random.default_rng(seed)
    ys, xs = np.mgrid[0:a.shape[0]:spacing, 0:a.shape[1]:spacing]
    lab = a[ys, xs]
    m = lab > 0
    lab = lab[m]
    n = lab.size
    x = xs[m] + r.uniform(-jitter, jitter, n)
    y = ys[m] + r.uniform(-jitter, jitter, n)
    col = np.zeros((n, 3))
    tw = np.zeros(n)
    for k, (rgb, bri, var, twk) in PALETTE.items():
        s = lab == k
        c = s.sum()
        if not c:
            continue
        base = np.array(rgb, float)
        if k == B_LIT:
            base = GOODS[r.integers(0, len(GOODS), c)]
        f = bri * (1 - var + var * r.random(c))
        col[s] = base * f[:, None]
        tw[s] = twk
    return x, y, col, tw


# >>> CODE-INTRO
def build_static():
    """Rathaus, Lichterbaum, Karussell, Buden als Maske."""
    lbl = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(lbl)

    # Rathaus: Fassade, Kupferdach, Gauben, Fenster
    d.rectangle([30, 690, 690, 1070], fill=FACADE)
    d.polygon([(30, 690), (62, 628), (658, 628), (690, 690)],
              fill=ROOF)
    for x in (88, 152, 216, 504, 568, 632):
        d.polygon([(x - 22, 632), (x, 592), (x + 22, 632)], fill=ROOF)
        d.rectangle([x - 5, 608, x + 5, 626], fill=WINDOW)
    for y0, y1 in ((712, 750), (790, 846), (874, 930), (958, 1010)):
        for x in range(50, 680, 42):
            if not 296 < x < 404:
                d.rectangle([x, y0, x + 18, y1], fill=WINDOW)

    # Rathausturm mit Uhr und Kupferspitze
    d.rectangle([318, 362, 402, 1070], fill=FACADE)
    for y0 in range(470, 900, 82):
        d.rectangle([334, y0, 348, y0 + 52], fill=WINDOW)
        d.rectangle([372, y0, 386, y0 + 52], fill=WINDOW)
    d.rectangle([340, 950, 380, 1070], fill=WINDOW)
    d.ellipse([331, 381, 389, 439], fill=GOLD)
    d.ellipse([337, 387, 383, 433], fill=CLOCK)
    d.line([(360, 410), (360, 392)], fill=0, width=3)
    d.line([(360, 410), (374, 417)], fill=0, width=3)
    d.polygon([(310, 364), (410, 364), (392, 300), (328, 300)],
              fill=ROOF)
    d.rectangle([334, 250, 386, 300], fill=ROOF)
    for x in (341, 356, 371):
        d.rectangle([x, 262, x + 8, 290], fill=WINDOW)
    d.polygon([(328, 252), (392, 252), (372, 220), (348, 220)],
              fill=ROOF)
    d.polygon([(350, 222), (370, 222), (360, 146)], fill=ROOF)
    d.ellipse([354, 134, 366, 146], fill=GOLD)

    # Lichterbaum vor dem Rathaus
    d.polygon([(TREE_X, TREE_TOP), (TREE_X - TREE_R, TREE_BASE),
               (TREE_X + TREE_R, TREE_BASE)], fill=TREEFILL)
    star = []
    for i in range(10):
        r = 26 if i % 2 == 0 else 11
        a = -math.pi / 2 + i * math.pi / 5
        star.append((TREE_X + r * math.cos(a),
                     TREE_TOP - 8 + r * math.sin(a)))
    d.polygon(star, fill=STAR)

    # Karussell mit gestreiftem Dach
    for k in range(12):
        xa, xb = 40 + 250 * k / 12, 40 + 250 * (k + 1) / 12
        c = CAR_RED if k % 2 else CAR_CREAM
        d.polygon([(CAR_X, 858), (xa, 932), (xb, 932)], fill=c)
    d.rectangle([38, 930, 292, 944], fill=GOLD)
    d.ellipse([CAR_X - 6, 842, CAR_X + 6, 854], fill=GOLD)
    d.line([(CAR_X, 820), (CAR_X, 842)], fill=GOLD, width=2)
    d.polygon([(CAR_X, 820), (CAR_X, 834), (CAR_X + 18, 826)],
              fill=CAR_RED)
    d.rectangle([50, 944, 280, 1066], fill=CAR_INNER)
    d.rectangle([CAR_X - 8, 944, CAR_X + 8, 1066], fill=GOLD)
    d.rectangle([36, 1062, 294, 1072], fill=GOLD)

    # Buden mit Schnee auf dem Dach
    roofs = (B_RED, B_GREEN, B_RED, B_WOOD, B_GREEN, B_RED, B_GREEN)
    for i, x0 in enumerate(range(-40, W, 128)):
        edge = [(x0, 1104), (x0 + 64, 1060), (x0 + 128, 1104)]
        d.polygon(edge, fill=roofs[i % len(roofs)])
        d.line(edge, fill=SNOW, width=4)
        d.rectangle([x0 + 6, 1104, x0 + 122, 1116], fill=B_WOOD)
        d.rectangle([x0 + 6, 1116, x0 + 122, 1156], fill=B_LIT)

    # Boden und Menschenmenge
    d.rectangle([0, 1156, W, H], fill=GROUND)
    r = np.random.default_rng(7)
    for _ in range(46):
        x, y = r.uniform(0, W), r.uniform(1168, 1205)
        s = r.uniform(9, 13)
        d.ellipse([x - s * 1.8, y + s, x + s * 1.8, y + s * 4],
                  fill=CROWD)
        d.ellipse([x - s, y - s, x + s, y + s], fill=CROWD)
        if r.random() < 0.25:
            d.polygon([(x - s, y - s * 0.4), (x + s, y - s * 0.4),
                       (x + s * 0.3, y - s * 2.2)], fill=HAT)
    return lbl


def lichterbaum(t):
    """Rotierende Lichterketten des Tannenbaums."""
    k = np.arange(40)[:, None]
    u = np.linspace(0.03, 1, 86)[None, :]
    th = 2 * np.pi * k / 40 + 0.35 * t
    x = TREE_X + TREE_R * u * np.sin(th)
    y = TREE_TOP + (TREE_BASE - TREE_TOP) * u + 0 * th
    depth = (np.cos(th) + 1) / 2 + 0 * u
    twinkle = 0.7 + 0.3 * np.sin(9 * t + 37 * k + 113 * u)
    b = (0.3 + 0.9 * depth) * twinkle
    return x.ravel(), y.ravel(), b.ravel()
# <<< CODE-INTRO


def booth_bulbs():
    xs, ys = [], []
    for x0 in range(-40, W, 128):
        for s in np.arange(0, 1.0001, 1 / 13):
            xs += [x0 + 64 * s, x0 + 64 + 64 * s]
            ys += [1104 - 44 * s + 7, 1060 + 44 * s + 7]
    for x in np.arange(42, 290, 9):
        xs.append(x)
        ys.append(937)
    return np.array(xs), np.array(ys)


BULB_COLS = np.array([(255, 60, 60), (255, 210, 90), (80, 200, 255),
                      (90, 230, 120), (255, 255, 230)], float)


def horse_template():
    im = Image.new("L", (40, 34), 0)
    d = ImageDraw.Draw(im)
    d.ellipse([4, 12, 30, 24], fill=1)            # Rumpf
    d.polygon([(26, 14), (31, 3), (37, 5), (34, 14)], fill=1)  # Hals/Kopf
    d.line([(8, 22), (5, 32)], fill=1, width=2)   # Beine
    d.line([(26, 22), (30, 32)], fill=1, width=2)
    d.line([(5, 15), (0, 22)], fill=1, width=2)   # Schweif
    a = np.asarray(im)
    ys, xs = np.nonzero(a[::2, ::2])
    return xs * 2 - 18.0, ys * 2 - 17.0


HORSE_X, HORSE_Y = horse_template()
HORSE_COLS = np.array([(255, 250, 240), (230, 60, 60), (90, 150, 255),
                       (255, 205, 90), (255, 250, 240), (120, 220, 140),
                       (230, 60, 60), (255, 205, 90)], float)


def karussell(t):
    xs, ys, cs = [], [], []
    for k in range(8):
        a = 2 * np.pi * k / 8 + 1.1 * t
        depth = math.cos(a)
        b = 0.35 + 0.65 * (depth + 1) / 2
        hx = CAR_X + 100 * math.sin(a)
        hy = 1008 + 9 * math.sin(2 * a + 3 * t)
        sgn = 1 if depth >= 0 else -1           # Laufrichtung
        xs.append(hx + sgn * HORSE_X * (0.75 + 0.25 * b))
        ys.append(hy + HORSE_Y * (0.75 + 0.25 * b))
        cs.append(np.repeat(HORSE_COLS[k][None] * b, len(HORSE_X), 0))
        py = np.linspace(946, hy - 10, 14)
        xs.append(np.full(14, hx))
        ys.append(py)
        cs.append(np.repeat(np.array([[255, 200, 80]]) * b * 0.8, 14, 0))
    return np.concatenate(xs), np.concatenate(ys), np.concatenate(cs)


def sleigh_template():
    """Schlitten mit Weihnachtsmann und vier Rentieren (Seitenansicht)."""
    im = Image.new("L", (330, 100), 0)
    d = ImageDraw.Draw(im)
    for i in range(4):
        x = 22 + i * 52
        d.ellipse([x, 44, x + 36, 60], fill=1)
        d.polygon([(x + 6, 48), (x - 2, 30), (x - 10, 32),
                   (x - 2, 50)], fill=1)
        d.line([(x - 4, 31), (x, 14), (x + 6, 10)], fill=2, width=2)
        d.line([(x - 2, 22), (x - 10, 14)], fill=2, width=2)
        d.line([(x + 6, 58), (x - 2, 72)], fill=1, width=2)
        d.line([(x + 12, 58), (x + 16, 74)], fill=1, width=2)
        d.line([(x + 28, 58), (x + 22, 72)], fill=1, width=2)
        d.line([(x + 32, 58), (x + 42, 70)], fill=1, width=2)
        if i == 0:
            d.ellipse([x - 14, 30, x - 7, 37], fill=9)     # rote Nase
    d.line([(46, 48), (250, 58)], fill=3, width=2)           # Zügel
    d.polygon([(232, 56), (318, 56), (322, 40), (310, 44),
               (300, 78), (240, 78)], fill=4)                # Schlitten
    d.line([(222, 86), (316, 86), (326, 76)], fill=5, width=3)
    d.line([(250, 78), (250, 86)], fill=5, width=2)
    d.line([(296, 78), (296, 86)], fill=5, width=2)
    d.ellipse([266, 22, 298, 58], fill=6)                    # Mantel
    d.ellipse([270, 10, 290, 30], fill=10)                   # Gesicht
    d.polygon([(268, 22), (292, 22), (286, 34), (274, 34)], fill=7)
    d.polygon([(270, 12), (290, 12), (300, 2)], fill=6)      # Mütze
    d.ellipse([297, 0, 303, 6], fill=7)
    d.ellipse([296, 26, 322, 52], fill=8)                    # Sack
    a = np.asarray(im)
    ys, xs = np.nonzero(a[::2, ::2])
    lab = a[::2, ::2][ys, xs]
    pal = {1: (175, 110, 60), 2: (230, 200, 150), 3: (255, 210, 90),
           4: (235, 40, 40), 5: (255, 205, 80), 6: (240, 45, 50),
           7: (255, 255, 255), 8: (160, 105, 55), 9: (255, 30, 30),
           10: (255, 200, 170)}
    bri = {9: 1.8, 3: 0.8}
    col = np.array([np.array(pal[v]) * bri.get(v, 1.0) for v in lab], float)
    return 330 - xs * 2.0, ys * 2.0, col   # gespiegelt: fliegt nach rechts


SL_X, SL_Y, SL_C = sleigh_template()
SLEIGH_T0, SLEIGH_T1 = 5.0, 10.2      # Szenenzeit


def sleigh_pos(ts):
    u = (ts - SLEIGH_T0) / (SLEIGH_T1 - SLEIGH_T0)
    x = -340 + (W + 380) * u
    y = 430 + 40 * math.sin(u * math.pi * 1.5) - 30 * u
    return x, y


# Feuerwerk: (Explosionszeit Szene, x, y, Farbe, Partikel)
FIREWORKS = [
    (2.5, 130, 480, (255, 70, 70), 300),
    (4.0, 600, 430, (255, 205, 90), 320),
    (5.5, 110, 400, (90, 150, 255), 300),
    (7.0, 610, 530, (110, 255, 150), 300),
    (9.6, 140, 530, (255, 110, 200), 340),
    (9.9, 590, 410, (255, 215, 120), 420),
]


def firework(ts, fw, idx):
    te, cx, cy, rgb, n = fw
    r = np.random.default_rng(100 + idx)
    launch = te - 0.55
    if ts < launch or ts > te + 2.6:
        return None
    if ts < te:                                   # Rakete steigt
        p = (ts - launch) / 0.55
        e = 1 - (1 - p) ** 2
        y0 = 1150
        k = np.arange(10)
        yy = y0 + (cy - y0) * np.clip(e - k * 0.03, 0, 1)
        xx = np.full(10, cx) + r.normal(0, 1, 10)
        c = np.repeat(np.array([[255, 220, 170]]), 10, 0) * \
            np.exp(-k / 3)[:, None]
        return xx, yy, c
    t = ts - te
    v = r.normal(size=(n, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    sp = 185 * (0.92 + 0.08 * r.random(n))
    drag = 2.2
    dist = sp * (1 - math.exp(-drag * t)) / drag
    x = cx + v[:, 0] * dist
    y = cy + v[:, 1] * dist + 22 * t * t
    fade = math.exp(-t / 0.85)
    flick = 1.0 if t < 1.0 else (0.5 + 0.5 * (r.random(n) > 0.5))
    if t < 0.12:
        fade *= 1.8
    c = 1.7 * np.array(rgb, float)[None] * (0.6 + 0.4 * (v[:, 2:3] + 1) / 2)
    c = c * (fade * flick if np.isscalar(flick) else
             (fade * flick)[:, None])
    return x, y, c


SNOW_R = np.random.default_rng(42)
SNOW_N = 650
SNOW_X0 = SNOW_R.uniform(0, W, SNOW_N)
SNOW_Y0 = SNOW_R.uniform(0, H, SNOW_N)
SNOW_V = SNOW_R.uniform(35, 95, SNOW_N)
SNOW_PH = SNOW_R.uniform(0, 6.3, SNOW_N)
SNOW_B = SNOW_R.uniform(0.35, 0.95, SNOW_N)

STAR_R = np.random.default_rng(3)
_sx = STAR_R.uniform(0, W, 600)
_sy = STAR_R.uniform(40, 615, 600)
_keep = ~((_sx > 300) & (_sx < 420) & (_sy > 130))
_keep &= ~((_sx > 380) & (_sx < 700) & (_sy > TREE_TOP - 40))
STARS_X, STARS_Y = _sx[_keep][:240], _sy[_keep][:240]
STARS_PH = STAR_R.uniform(0, 6.3, STARS_X.size)


# ------------------------------------------------------------- Rendering
KERNEL = [(0, 0, 1.0), (1, 0, .55), (-1, 0, .55), (0, 1, .55),
          (0, -1, .55), (1, 1, .25), (-1, 1, .25), (1, -1, .25),
          (-1, -1, .25)]


def splat(canvas, x, y, col, kernel=KERNEL):
    xi = np.round(x).astype(np.int64)
    yi = np.round(y).astype(np.int64)
    idx, wts = [], []
    for dx, dy, w in kernel:
        xx, yy = xi + dx, yi + dy
        m = (xx >= 0) & (xx < W) & (yy >= 0) & (yy < H)
        idx.append(yy[m] * W + xx[m])
        wts.append(col[m] * w)
    idx = np.concatenate(idx)
    wts = np.concatenate(wts)
    flat = canvas.reshape(-1, 3)
    for c in range(3):
        flat[:, c] += np.bincount(idx, weights=wts[:, c],
                                  minlength=W * H)


def sky():
    g = np.linspace(0, 1, H)[:, None]
    top = np.array([3, 5, 18], float)
    low = np.array([14, 24, 58], float)
    bg = top + (low - top) * np.clip(g / 0.55, 0, 1) ** 1.4
    return np.repeat(bg[:, None, :], W, 1)


SKY = sky()
SMALL = [(0, 0, 1.0), (1, 0, .5), (0, 1, .5), (1, 1, .3)]

# Szene vorbereiten
ST_X, ST_Y, ST_C, ST_TW = sample(build_static(), spacing=4, seed=5)
_r = np.random.default_rng(11)
ST_PH = _r.uniform(0, 6.3, ST_X.size)
ST_F = _r.uniform(1.5, 5.0, ST_X.size)
BU_X, BU_Y = booth_bulbs()


def scene_targets(ts):
    tx, ty, tb = lichterbaum(ts)
    tc = np.array([255, 205, 115], float)[None] * tb[:, None]
    white = (np.arange(tb.size) % 11) == 0
    tc[white] = np.array([255, 245, 225]) * tb[white, None]
    kx, ky, kc = karussell(ts)
    tw = 1 - ST_TW * (0.5 + 0.5 * np.sin(ST_F * ts + ST_PH))
    sc = ST_C * tw[:, None]
    phase = (np.arange(BU_X.size) / 5 + ts * 2.2).astype(int)
    on = 0.45 + 0.55 * ((np.arange(BU_X.size) + int(ts * 6)) % 3 == 0)
    bc = BULB_COLS[phase % len(BULB_COLS)] * on[:, None]
    x = np.concatenate([ST_X, tx, kx, BU_X])
    y = H - (H - np.concatenate([ST_Y, ty, ky, BU_Y])) * SQ
    c = np.concatenate([sc, tc, kc, bc])
    return x, y, c


N_SCENE = scene_targets(0)[0].size
_r = np.random.default_rng(21)
_ty0 = scene_targets(0)[1]
B_SX = _r.uniform(-80, W + 80, N_SCENE)
B_SY = H + _r.uniform(30, 500, N_SCENE)
B_DELAY = 0.05 + 1.0 * np.clip((H - _ty0) / H, 0, 1) + \
    _r.uniform(0, 0.25, N_SCENE)
B_FLY = 0.8


def greeting_particles():
    """Schnoerkelschrift als Maske, gerastert zu feinen Goldpunkten."""
    im = Image.new("L", (W, 330), 0)
    d = ImageDraw.Draw(im)
    lines = ((GREETING[0], 104, 42), (GREETING[1], 132, 148))
    for txt, size, y in lines:
        f = ImageFont.truetype(SCRIPT, size)
        w = f.getlength(txt)
        d.text(((W - w) / 2, y), txt, font=f, fill=255)
    a = np.asarray(im)
    r = np.random.default_rng(33)
    ys, xs = np.mgrid[0:a.shape[0]:2, 0:W:2]
    m = a[ys, xs] > 90
    x = xs[m] + r.uniform(-0.4, 0.4, m.sum())
    y = ys[m] + r.uniform(-0.4, 0.4, m.sum())
    line2 = y > 175
    # Schreibreihenfolge: erst Zeile 1, dann Zeile 2, je links nach rechts
    order = np.where(line2, 1.0 + x / W, x / W)
    return x, y, order, r.uniform(0, 6.3, x.size)


GR_X, GR_Y, GR_ORD, GR_PH = greeting_particles()
GR_T0, GR_SPEED = 2.1, 1.35          # Start (Szenenzeit), Sek. pro Zeile


def draw_greeting(canvas, ts):
    reveal = (ts - GR_T0) / GR_SPEED
    if reveal <= 0:
        return
    age = reveal - GR_ORD
    m = age > 0
    if not m.any():
        return
    a = age[m]
    gold = np.array([255, 212, 130], float)
    tw = 0.82 + 0.18 * np.sin(3.0 * ts + GR_PH[m])
    flash = 1 + 2.5 * np.exp(-a * 9)
    c = gold[None] * (tw * flash)[:, None] * 0.75
    c += np.array([255, 255, 255]) * (np.exp(-a * 9) * 0.6)[:, None]
    splat(canvas, GR_X[m], GR_Y[m], c, SMALL)
    # Funkelnde Schreibspitze
    if reveal < 2.0:
        front = (np.abs(GR_ORD - reveal) < 0.012)
        if front.any():
            fx, fy = GR_X[front].mean(), GR_Y[front].mean()
            rr = np.random.default_rng(int(ts * 1000))
            sx = fx + rr.normal(0, 9, 40)
            sy = fy + rr.normal(0, 9, 40)
            sc = np.repeat(np.array([[255, 240, 200]]), 40, 0) * \
                rr.uniform(0.4, 1.6, (40, 1))
            splat(canvas, sx, sy, sc, SMALL)


def render_scene(ts):
    canvas = np.zeros((H, W, 3), np.float64)

    # Sterne
    sb = 0.35 + 0.35 * np.sin(2.3 * ts + STARS_PH)
    sc = np.repeat(np.array([[230, 235, 255]]), STARS_X.size, 0) * \
        sb[:, None] * min(1, ts / 0.8)
    splat(canvas, STARS_X, STARS_Y, sc, SMALL)

    # Szene mit Aufbauanimation
    x, y, c = scene_targets(ts)
    p = np.clip((ts - B_DELAY) / B_FLY, 0, 1)
    e = 1 - (1 - p) ** 3
    x = B_SX + (x - B_SX) * e
    y = B_SY + (y - B_SY) * e
    fly = (p > 0) & (p < 1)
    boost = 1 + 1.6 * (1 - e) * fly
    c = c * boost[:, None]
    c[fly] = c[fly] * 0.6 + np.array([200, 220, 255]) * 0.4 * \
        (1 - e[fly])[:, None]
    splat(canvas, x, y, c)

    # Fliegender Weihnachtsmann mit Sternenspur
    if SLEIGH_T0 - 0.2 < ts < SLEIGH_T1 + 1.5:
        trail_x, trail_y, trail_c = [], [], []
        for k in range(1, 40):
            tk = ts - k * 0.035
            if not SLEIGH_T0 <= tk <= SLEIGH_T1:
                continue
            sx, sy = sleigh_pos(tk)
            rr = np.random.default_rng(int(tk * 1000) % 99991)
            m = 6
            trail_x.append(sx + 70 + rr.normal(0, 6 + k * 0.5, m))
            trail_y.append(sy + 80 + rr.normal(0, 4 + k * 0.3, m) +
                           k * 1.2)
            fade = math.exp(-k / 14)
            trail_c.append(np.array([[255, 225, 150]] * m) * fade *
                           rr.uniform(0.4, 1.2, (m, 1)))
        if trail_x:
            splat(canvas, np.concatenate(trail_x),
                  np.concatenate(trail_y), np.concatenate(trail_c), SMALL)
        if SLEIGH_T0 <= ts <= SLEIGH_T1:
            sx, sy = sleigh_pos(ts)
            bob = 2.5 * math.sin(ts * 9)
            splat(canvas, sx + SL_X, sy + SL_Y + bob, SL_C)

    # Feuerwerk
    for i, fw in enumerate(FIREWORKS):
        res = firework(ts, fw, i)
        if res is not None:
            splat(canvas, *res)

    draw_greeting(canvas, ts)

    # Schnee
    sx = SNOW_X0 + 12 * np.sin(0.9 * ts + SNOW_PH)
    sy = (SNOW_Y0 + SNOW_V * ts) % H
    scol = np.repeat(np.array([[230, 238, 255]]), SNOW_N, 0) * \
        (SNOW_B * min(1, ts / 1.0))[:, None]
    splat(canvas, sx, sy, scol, SMALL)

    return canvas


def bloom(canvas):
    img = Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8))
    q = img.resize((W // 4, H // 4), Image.BILINEAR)
    g1 = q.filter(ImageFilter.GaussianBlur(4)).resize((W, H),
                                                      Image.BILINEAR)
    h = img.resize((W // 2, H // 2), Image.BILINEAR)
    g2 = h.filter(ImageFilter.GaussianBlur(2)).resize((W, H),
                                                      Image.BILINEAR)
    return np.asarray(g1, float) * 1.5 + np.asarray(g2, float) * 0.7


def title_bar(img):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 34], fill=(40, 40, 44))
    f = ImageFont.truetype(FONT, 14)
    d.text((12, 9), "Figure 1  ·  Hamburger Weihnachtsmarkt",
           font=f, fill=(200, 200, 205))
    for i, c in enumerate([(120, 120, 125)] * 2 + [(220, 80, 80)]):
        cx = W - 80 + i * 26
        if i == 0:
            d.line([(cx - 6, 17), (cx + 6, 17)], fill=c, width=2)
        elif i == 1:
            d.rectangle([cx - 6, 11, cx + 6, 23], outline=c, width=2)
        else:
            d.line([(cx - 6, 11), (cx + 6, 23)], fill=c, width=2)
            d.line([(cx - 6, 23), (cx + 6, 11)], fill=c, width=2)
    return img


def frame_scene(ts, t_abs):
    canvas = render_scene(ts)
    out = SKY + canvas + bloom(canvas)
    if ts < 0.12:                                  # Startblitz
        out += (0.12 - ts) / 0.12 * 120
    fade = np.clip((DUR - t_abs) / 0.35, 0, 1)
    out = np.clip(out * fade, 0, 255).astype(np.uint8)
    img = Image.fromarray(out)
    return title_bar(img) if INTRO > 0 else img


# ------------------------------------------------------------ Code Intro
def code_lines():
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    a = src.index("# >>> CODE-INTRO") + len("# >>> CODE-INTRO\n")
    b = src.index("# <<< CODE-INTRO")
    return src[a:b].rstrip("\n").split("\n")


KW_PURPLE = {"for", "in", "if", "else", "return", "import", "from",
             "while", "not", "and", "or", "with", "as", "elif"}
KW_BLUE = {"def", "class", "None", "True", "False", "lambda"}
TOKEN = re.compile(r'(#.*$)|("[^"]*"|\'[^\']*\')|(\b\d+\.?\d*\b)|'
                   r'([A-Za-z_]\w*)|(\s+)|(.)')
C_DEF = (212, 212, 212)


def highlight(line):
    """Liefert (Text, Farbe) Segmente im VS Code Dark Stil."""
    segs = []
    for m in TOKEN.finditer(line):
        s = m.group(0)
        if m.group(1):
            c = (106, 153, 85)
        elif m.group(2):
            c = (206, 145, 120)
        elif m.group(3):
            c = (181, 206, 168)
        elif m.group(4):
            rest = line[m.end():]
            if s in KW_PURPLE:
                c = (197, 134, 192)
            elif s in KW_BLUE:
                c = (86, 156, 214)
            elif rest.startswith("("):
                c = (220, 220, 170)
            elif s.isupper() or s in ("np", "math", "Image", "ImageDraw"):
                c = (78, 201, 176) if not s.isupper() else (100, 190, 255)
            else:
                c = (156, 220, 254)
        else:
            c = C_DEF
        segs.append((s, c))
    return segs


LINES = code_lines()
SEGS = [highlight(l) for l in LINES]
TOTAL_CHARS = sum(len(l) + 1 for l in LINES)
TYPE_END = 2.15
CMD = "python3 hamburg_weihnachtsmarkt.py"
CMD_T0, CMD_T1, ENTER_T = 2.22, 2.55, 2.62


def frame_intro(t):
    img = Image.new("RGB", (W, H), (30, 30, 30))
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, 15)
    fs = ImageFont.truetype(FONT, 13)
    cw = f.getlength("M")
    lh = 22
    # Tab Leiste
    d.rectangle([0, 0, W, 38], fill=(37, 37, 38))
    d.rectangle([0, 0, 280, 38], fill=(30, 30, 30))
    d.line([(0, 0), (280, 0)], fill=(0, 122, 204), width=2)
    d.text((14, 11), "hamburg_weihnachtsmarkt.py", font=fs,
           fill=(230, 230, 230))
    d.text((300, 11), "README.md", font=fs, fill=(140, 140, 140))
    # Terminal Bereich
    term = t >= TYPE_END
    bottom = 1000 if term else H - 24
    n = int(TOTAL_CHARS * min(1.0, t / TYPE_END))
    # Cursor Position bestimmen
    cnt, cur_line, cur_col = 0, 0, 0
    for i, l in enumerate(LINES):
        if cnt + len(l) + 1 > n:
            cur_line, cur_col = i, n - cnt
            break
        cnt += len(l) + 1
    else:
        cur_line, cur_col = len(LINES) - 1, len(LINES[-1])
    vis = (bottom - 50) // lh
    first = max(0, cur_line - vis + 3)
    y = 48
    typed = 0
    for i, segs in enumerate(SEGS):
        line_len = len(LINES[i]) + 1
        if i < first:
            typed += line_len
            continue
        if y > bottom - lh:
            break
        if i > cur_line:
            break
        d.text((8, y), f"{i + 1:>3}", font=f,
               fill=(200, 200, 200) if i == cur_line else (100, 100, 100))
        x = 58
        budget = cur_col if i == cur_line else line_len
        for s, c in segs:
            if budget <= 0:
                break
            part = s[:budget]
            d.text((x, y), part, font=f, fill=c)
            x += cw * len(part)
            budget -= len(part)
        if i == cur_line and not term:
            d.rectangle([x, y + 1, x + 2, y + 19], fill=(220, 220, 220))
        y += lh
    # Statusleiste
    d.rectangle([0, H - 24, W, H], fill=(0, 122, 204))
    d.text((10, H - 20), "main   Python 3.12   UTF-8   Ln %d, Col %d" %
           (cur_line + 1, cur_col + 1), font=fs, fill=(255, 255, 255))
    if term:
        d.rectangle([0, 1000, W, H - 24], fill=(24, 24, 24))
        d.line([(0, 1000), (W, 1000)], fill=(70, 70, 70), width=1)
        d.text((14, 1010), "TERMINAL", font=fs, fill=(230, 230, 230))
        d.line([(14, 1030), (82, 1030)], fill=(230, 230, 230), width=1)
        d.text((110, 1010), "PROBLEME   AUSGABE", font=fs,
               fill=(120, 120, 120))
        k = int(len(CMD) * np.clip((t - CMD_T0) / (CMD_T1 - CMD_T0), 0, 1))
        d.text((14, 1046), "~/hamburg $ ", font=f, fill=(90, 200, 120))
        px = 14 + cw * len("~/hamburg $ ")
        d.text((px, 1046), CMD[:k], font=f, fill=(220, 220, 220))
        if t < ENTER_T:
            if int(t * 6) % 2 == 0 or t < CMD_T1:
                cx = px + cw * k
                d.rectangle([cx, 1047, cx + cw, 1065], fill=(200, 200, 200))
        else:
            d.text((14, 1072), "Baue %d Partikel ..." % N_SCENE, font=f,
                   fill=(180, 180, 180))
            if t > ENTER_T + 0.18:
                d.text((14, 1096), "Rathaus  Lichterbaum  Karussell  "
                       "Buden", font=f, fill=(180, 180, 180))
            if t > ENTER_T + 0.28:
                d.text((14, 1120), "▶ Fenster wird geöffnet",
                       font=f, fill=(255, 205, 90))
    return img


# ----------------------------------------------------------------- Audio
SR = 44100


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def add(buf, start, sig, pan=0.5, gain=1.0):
    i = int(start * SR)
    if i >= buf.shape[0]:
        return
    sig = sig[: buf.shape[0] - i]
    buf[i:i + sig.size, 0] += sig * gain * math.cos(pan * math.pi / 2)
    buf[i:i + sig.size, 1] += sig * gain * math.sin(pan * math.pi / 2)


def glock(f, dur=2.2):
    t = np.arange(int(dur * SR)) / SR
    s = (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.9) +
         0.45 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / 0.25) +
         0.22 * np.sin(2 * np.pi * f * 5.40 * t) * np.exp(-t / 0.09) +
         0.10 * np.sin(2 * np.pi * f * 8.93 * t) * np.exp(-t / 0.04))
    att = np.clip(t / 0.002, 0, 1)
    return s * att


def celesta(f, dur=2.5):
    t = np.arange(int(dur * SR)) / SR
    s = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t))
    return s * np.exp(-t / 0.8) * np.clip(t / 0.01, 0, 1)


def lowpass(x, n):
    k = np.ones(n) / n
    return np.convolve(x, k, mode="same")


def jingle(r):
    t = np.arange(int(0.18 * SR)) / SR
    s = np.zeros_like(t)
    for _ in range(6):
        f = r.uniform(3200, 9000)
        s += np.sin(2 * np.pi * f * t + r.uniform(0, 6)) * \
            np.exp(-t / r.uniform(0.03, 0.09))
    s += r.normal(0, 0.4, t.size) * np.exp(-t / 0.02)
    return s / 6


def build_audio():
    n = int(DUR * SR)
    dry = np.zeros((n, 2))
    wet = np.zeros((n, 2))
    r = np.random.default_rng(9)

    M = INTRO - 3.0                     # Musik relativ zum Szenenstart
    # Tastaturklicks waehrend des Tippens
    t = 0.05
    while t < TYPE_END and INTRO > 0:
        c = r.normal(0, 1, 500) * np.exp(-np.arange(500) / 60)
        c = c - lowpass(c, 6)
        add(dry, t, c, r.uniform(0.35, 0.65), 0.10)
        t += r.uniform(0.035, 0.075)
    t = CMD_T0
    while t < CMD_T1 and INTRO > 0:
        c = r.normal(0, 1, 500) * np.exp(-np.arange(500) / 60)
        add(dry, t, c - lowpass(c, 6), 0.5, 0.10)
        t += r.uniform(0.03, 0.05)
    c = r.normal(0, 1, 900) * np.exp(-np.arange(900) / 120)
    if INTRO > 0:
        add(dry, ENTER_T, lowpass(c, 3), 0.5, 0.28)

    # Rauschen beim Partikelaufbau
    wl = int(1.9 * SR)
    tt = np.arange(wl) / SR
    nz = r.normal(0, 1, wl)
    sw = lowpass(nz, 40) * 0.6 + lowpass(nz, 6) * 0.4 * tt / 1.9
    env = np.sin(np.pi * np.clip(tt / 1.9, 0, 1)) ** 2
    add(dry, INTRO, sw * env, 0.5, 0.22)

    # Aufsteigendes Glitzern (G Dur Pentatonik)
    pent = [67, 69, 71, 74, 76, 79, 81, 83, 86, 88, 91, 93]
    for i in range(20):
        tn = INTRO + 0.1 + i * 0.085
        m = pent[min(len(pent) - 1, i * len(pent) // 20)] + 12
        add(wet, tn, glock(midi(m), 1.2), r.uniform(0.2, 0.8),
            0.05 + 0.08 * i / 20)

    # O Tannenbaum (traditionell, gemeinfrei) als Glockenspiel
    mel = [(62, 1), (67, .75), (67, .25), (67, 1.5), (69, .5),
           (71, .75), (71, .25), (71, 1.5), (71, .5),
           (69, .5), (71, .5), (72, 1), (66, 1), (69, 1), (67, 2)]
    beat, t = 0.5, 5.0 + M
    for m, b in mel:
        add(wet, t, glock(midi(m + 12), 2.5), 0.5, 0.42)
        t += b * beat
    chords = [(5.5, (55, 59, 62)), (7.0, (55, 59, 62)),
              (8.5, (48, 52, 55)), (9.5, (50, 54, 57)),
              (10.5, (43, 55, 59, 62))]
    for tc, notes in chords:
        tc += M
        for j, m in enumerate(notes):
            add(wet, tc + j * 0.012, celesta(midi(m + 12), 2.2),
                0.35 + 0.3 * j / max(1, len(notes) - 1), 0.12)
        add(wet, tc, celesta(midi(notes[0]), 1.8), 0.5, 0.18)
    # Schlussarpeggio und Akkord
    for i, m in enumerate([67, 71, 74, 79, 83, 86]):
        add(wet, 11.6 + M + i * 0.16, glock(midi(m + 12), 2.4),
            0.3 + 0.08 * i, 0.32)
    for j, m in enumerate([55, 59, 62, 67, 71, 74]):
        add(wet, 12.6 + M + j * 0.02, celesta(midi(m + 12), 2.6),
            0.3 + 0.08 * j, 0.14)
    add(wet, 12.6 + M, glock(midi(91), 2.4), 0.5, 0.3)

    # Schlittenglocken, Panorama folgt dem Schlitten
    t = INTRO + SLEIGH_T0
    while t < INTRO + SLEIGH_T1:
        ts = t - INTRO
        sx, _ = sleigh_pos(ts)
        pan = float(np.clip((sx + 165) / W, 0.05, 0.95))
        u = (ts - SLEIGH_T0) / (SLEIGH_T1 - SLEIGH_T0)
        g = 0.2 * math.sin(math.pi * u) ** 0.7
        add(dry, t, jingle(r), pan, g)
        t += 0.125 if int(t / 0.125) % 4 != 3 else 0.25

    # Feuerwerk: Abschuss, Knall, Knistern
    for te, cx, cy, _, _ in FIREWORKS:
        pan = cx / W
        L = int(0.5 * SR)
        tt = np.arange(L) / SR
        wh = r.normal(0, 1, L) * (tt / 0.5) ** 2
        add(dry, INTRO + te - 0.55, wh - lowpass(wh, 4), pan, 0.04)
        L = int(0.9 * SR)
        tt = np.arange(L) / SR
        boom = (np.sin(2 * np.pi * 55 * tt) * np.exp(-tt / 0.22) +
                lowpass(r.normal(0, 1, L), 25) * 3 * np.exp(-tt / 0.12))
        add(dry, INTRO + te, boom, pan, 0.35)
        add(wet, INTRO + te, boom, pan, 0.10)
        for _ in range(45):
            ct = INTRO + te + r.uniform(0.25, 1.5)
            cl = r.normal(0, 1, 160) * np.exp(-np.arange(160) / 25)
            add(dry, ct, cl, float(np.clip(pan + r.normal(0, 0.1),
                                           0, 1)), r.uniform(0.03, 0.09))

    # Hall per FFT Faltung
    ir_len = int(1.8 * SR)
    ti = np.arange(ir_len) / SR
    out = dry.copy()
    for ch in range(2):
        ir = r.normal(0, 1, ir_len) * np.exp(-ti / 0.5)
        ir = lowpass(ir, 3)
        ir /= np.sqrt(np.sum(ir ** 2))
        m = n + ir_len
        size = 1 << (m - 1).bit_length()
        conv = np.fft.irfft(np.fft.rfft(wet[:, ch], size) *
                            np.fft.rfft(ir, size), size)[:n]
        out[:, ch] += wet[:, ch] * 0.85 + conv * 0.35
    fade = np.clip((DUR - np.arange(n) / SR) / 0.6, 0, 1)
    out *= fade[:, None]
    out = np.tanh(out / np.max(np.abs(out)) * 1.1) * 0.89
    return out


def write_wav(path, data):
    pcm = (np.clip(data, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# ------------------------------------------------------------------ Main
def render_frame(i):
    t = i / FPS
    if t < INTRO:
        img = frame_intro(t)
    else:
        img = frame_scene(t - INTRO, t)
    img.save(os.path.join(OUT, "frames", "%04d.jpg" % i), quality=94)
    return i


def main():
    os.makedirs(os.path.join(OUT, "frames"), exist_ok=True)
    nframes = int(DUR * FPS)
    only = sys.argv[1:]
    if only:                                       # Vorschau einzelner Frames
        for s in only:
            render_frame(int(float(s) * FPS))
        return
    print("Partikel in der Szene:", N_SCENE)
    write_wav(os.path.join(OUT, "audio.wav"), build_audio())
    with Pool(os.cpu_count()) as p:
        for k, _ in enumerate(p.imap_unordered(render_frame,
                                               range(nframes))):
            if k % 50 == 0:
                print("Frame", k, "/", nframes, flush=True)
    mp4 = os.path.join(OUT, "hamburg_weihnachtsmarkt.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-framerate", str(FPS),
        "-i", os.path.join(OUT, "frames", "%04d.jpg"),
        "-i", os.path.join(OUT, "audio.wav"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "17",
        "-preset", "slow", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart", mp4], check=True)
    print("Fertig:", mp4)


if __name__ == "__main__":
    main()
