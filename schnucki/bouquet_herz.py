#!/usr/bin/env python3
"""Rotierender 3D ASCII Blumenstrauss mit rotierendem roten Herz ("Schnucki").

Start im Terminal:   python3 bouquet_herz.py
Als Video rendern:   python3 bouquet_herz.py --video schnucki.mp4 [--seconds 14]
Anderer Name:        python3 bouquet_herz.py --name "Mausi"
"""
import argparse
import math
import random
import shutil
import subprocess
import sys
import time

SHADES = ".,-~:;=!*#$@"

PAL = {
    "pink":   [125, 162, 199, 206, 213, 219],
    "red":    [88, 124, 160, 196, 203, 210],
    "purple": [54, 91, 128, 134, 171, 177],
    "yellow": [136, 178, 220, 226, 228, 229],
    "orange": [130, 166, 202, 208, 214, 215],
    "white":  [242, 246, 250, 253, 255, 231],
    "green":  [22, 28, 34, 40, 76, 118],
    "stem":   [22, 22, 28, 34, 34, 40],
    "wrap":   [96, 139, 182, 225, 224, 231],
    "ribbon": [89, 125, 161, 197, 204, 211],
    "heart":  [52, 88, 124, 160, 196, 203],
    "core":   [94, 130, 136, 172, 178, 220],
}

LIGHT = (0.35, 0.65, -0.68)
_l = math.sqrt(sum(c * c for c in LIGHT))
LIGHT = tuple(c / _l for c in LIGHT)

FONT = {
    "A": ["###", "#.#", "###", "#.#", "#.#"], "B": ["##.", "#.#", "##.", "#.#", "##."],
    "C": ["###", "#..", "#..", "#..", "###"], "D": ["##.", "#.#", "#.#", "#.#", "##."],
    "E": ["###", "#..", "##.", "#..", "###"], "F": ["###", "#..", "##.", "#..", "#.."],
    "G": ["###", "#..", "#.#", "#.#", "###"], "H": ["#.#", "#.#", "###", "#.#", "#.#"],
    "I": ["###", ".#.", ".#.", ".#.", "###"], "J": ["..#", "..#", "..#", "#.#", "###"],
    "K": ["#.#", "#.#", "##.", "#.#", "#.#"], "L": ["#..", "#..", "#..", "#..", "###"],
    "M": ["#.#", "###", "###", "#.#", "#.#"], "N": ["##.", "#.#", "#.#", "#.#", "#.#"],
    "O": ["###", "#.#", "#.#", "#.#", "###"], "P": ["###", "#.#", "###", "#..", "#.."],
    "Q": ["###", "#.#", "#.#", "###", "..#"], "R": ["###", "#.#", "##.", "#.#", "#.#"],
    "S": ["###", "#..", "###", "..#", "###"], "T": ["###", ".#.", ".#.", ".#.", ".#."],
    "U": ["#.#", "#.#", "#.#", "#.#", "###"], "V": ["#.#", "#.#", "#.#", "#.#", ".#."],
    "W": ["#.#", "#.#", "###", "###", "#.#"], "X": ["#.#", "#.#", ".#.", "#.#", "#.#"],
    "Y": ["#.#", "#.#", ".#.", ".#.", ".#."], "Z": ["###", "..#", ".#.", "#..", "###"],
    "Ä": ["#.#", "...", "###", "#.#", "#.#"], "Ö": ["#.#", "...", "###", "#.#", "###"],
    "Ü": ["#.#", "...", "#.#", "#.#", "###"], " ": ["...", "...", "...", "...", "..."],
    "!": [".#.", ".#.", ".#.", "...", ".#."], "?": ["###", "..#", ".##", "...", ".#."],
}


def norm(v):
    l = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2) or 1.0
    return (v[0] / l, v[1] / l, v[2] / l)


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


# ---------------------------------------------------------------- Modell
def build_bouquet(rng):
    """Liefert Punkte (x, y, z, nx, ny, nz, palette, beidseitig, wachstum)."""
    pts = []
    tie = (0.0, -0.55, 0.0)
    colors = ["red", "pink", "purple", "yellow", "orange", "white", "red", "pink", "yellow", "purple", "orange", "white"]
    heads = []
    # Blueten auf einer Kuppel verteilen
    n = len(colors)
    for i in range(n):
        if i == 0:
            phi, theta = 0.0, 0.0
        else:
            phi = 0.55 + 0.35 * (i % 2)
            theta = i * 2.399963  # goldener Winkel
        cx = 0.85 * math.sin(phi) * math.cos(theta)
        cz = 0.85 * math.sin(phi) * math.sin(theta)
        cy = 0.5 + 0.45 * math.cos(phi) + rng.uniform(-0.05, 0.05)
        heads.append(((cx, cy, cz), colors[i], rng.choice([5, 6, 8]), rng.uniform(0.27, 0.33)))

    for (c, col, petals, R) in heads:
        nrm = norm((c[0] * 2.2, 0.75, c[2] * 2.2))
        up = (0, 1, 0) if abs(nrm[1]) < 0.95 else (1, 0, 0)
        u = norm(cross(nrm, up))
        v = cross(nrm, u)
        steps = 70
        for a in range(steps):
            th = 2 * math.pi * a / steps
            rmax = R * (0.45 + 0.55 * abs(math.cos(petals * th / 2)))
            k = 0.0
            while k <= rmax:
                cup = 0.25 * (k / R) ** 2  # leicht gewoelbte Bluete
                px = c[0] + u[0] * k * math.cos(th) + v[0] * k * math.sin(th) - nrm[0] * cup * R
                py = c[1] + u[1] * k * math.cos(th) + v[1] * k * math.sin(th) - nrm[1] * cup * R
                pz = c[2] + u[2] * k * math.cos(th) + v[2] * k * math.sin(th) - nrm[2] * cup * R
                pal = "core" if k < R * 0.28 else col
                pts.append((px, py, pz, nrm[0], nrm[1], nrm[2], pal, True, 0.55 + 0.45 * (k / R)))
                k += 0.022
        # Stiel: Bluete -> Bindestelle -> unten
        bottom = (c[0] * 0.18, -1.3, c[2] * 0.18)
        for seg, (p0, p1) in enumerate(((c, tie), (tie, bottom))):
            L = math.dist(p0, p1)
            m = max(2, int(L / 0.02))
            for j in range(m):
                t = j / m
                x = p0[0] + (p1[0] - p0[0]) * t
                y = p0[1] + (p1[1] - p0[1]) * t
                z = p0[2] + (p1[2] - p0[2]) * t
                nn = norm((x, 0.2, z))
                pts.append((x, y, z, nn[0], nn[1], nn[2], "stem", True, (y + 1.3) / 2.2 * 0.5))

    # Blaetter
    for i in range(7):
        th = i * 2 * math.pi / 7 + 0.3
        base = (0.18 * math.cos(th), 0.0 + 0.1 * (i % 3), 0.18 * math.sin(th))
        d = norm((math.cos(th), 0.55, math.sin(th)))
        side = norm(cross(d, (0, 1, 0)))
        nn = norm(cross(d, side))
        Lf, Wf = 0.55, 0.13
        s = 0.0
        while s <= Lf:
            w = Wf * math.sin(math.pi * s / Lf)
            q = -w
            while q <= w:
                x = base[0] + d[0] * s + side[0] * q
                y = base[1] + d[1] * s + side[1] * q - 0.25 * s * s
                z = base[2] + d[2] * s + side[2] * q
                pts.append((x, y, z, nn[0], nn[1], nn[2], "green", True, 0.35 + 0.2 * s))
                q += 0.02
            s += 0.02

    # Papier: Kegel, vorne offen
    y = -0.75
    while y <= 0.12:
        t = (y + 0.75) / 0.87
        r = 0.12 + 0.5 * t
        a = 0.0
        while a < 2 * math.pi:
            if not (-1.4 < (a - 1.5 * math.pi) < 1.4):  # Oeffnung nach vorne
                x, z = r * math.cos(a), r * math.sin(a)
                nn = norm((math.cos(a), -0.5, math.sin(a)))
                fold = "wrap" if int(a * 6) % 2 == 0 else "pink"
                pts.append((x, y, z, nn[0], nn[1], nn[2], fold, True, t * 0.5))
            a += 0.022 / max(r, 0.15)
        y += 0.022

    # Schleife
    for i in range(160):
        a = 2 * math.pi * i / 160
        for dy in (-0.03, 0.0, 0.03):
            x, z = 0.15 * math.cos(a), 0.15 * math.sin(a)
            pts.append((x, -0.55 + dy, z, math.cos(a), 0, math.sin(a), "ribbon", False, 0.3))
    for sgn in (-1, 1):
        for i in range(120):
            a = 2 * math.pi * i / 120
            x = sgn * (0.17 + 0.14 * (1 - math.cos(a)))
            y = -0.55 + 0.08 * math.sin(a)
            pts.append((x, y, -0.16, 0, 0, -1, "ribbon", True, 0.3))
        for i in range(40):
            t = i / 40
            pts.append((sgn * 0.1 * t, -0.58 - 0.3 * t, -0.16, 0, 0, -1, "ribbon", True, 0.3))
    return pts


def heart_xy(t):
    x = 16 * math.sin(t) ** 3
    y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
    return x / 17.0, y / 17.0


def build_heart():
    pts = []
    T = 0.42
    for i in range(240):
        t = 2 * math.pi * i / 240
        hx, hy = heart_xy(t)
        r = 0.0
        while r <= 1.0:
            zz = T * math.sqrt(max(0.0, 1 - r * r))
            for s in (1, -1):
                nn = norm((r * hx * 0.9, r * hy * 0.9, s * zz / T))
                pts.append((r * hx, r * hy + 0.1, s * zz, nn[0], nn[1], nn[2]))
            r += 0.03
    return pts, T


# ---------------------------------------------------------------- Renderer
class Scene:
    def __init__(self, W, H, name):
        rng = random.Random(7)
        self.W, self.H, self.name = W, H, name
        self.bouquet = build_bouquet(rng)
        self.heart, self.T = build_heart()
        self.D = 6.0
        # Szene: Strauss y -1.3..1.0, Herz darueber
        self.heart_y = 2.0
        self.heart_s = 0.75
        top, bot = self.heart_y + 1.0 * self.heart_s, -1.35
        self.cy = (top + bot) / 2
        span = top - bot
        self.K = min(0.94 * H * self.D / span, 0.94 * W * self.D / (2 * 2.2))
        # Konturradius je Winkel fuer exakte Oberflaechentiefe
        n = 720
        self.rb = [0.0] * n
        for k in range(4000):
            hx, hy = heart_xy(2 * math.pi * k / 4000)
            i = int((math.atan2(hy, hx) + math.pi) / (2 * math.pi) * n) % n
            self.rb[i] = max(self.rb[i], math.hypot(hx, hy))
        for i in range(n):
            if self.rb[i] == 0.0:
                self.rb[i] = self.rb[i - 1]
        self.text_pts = self.build_text()
        self.stars = [(rng.randrange(W), rng.randrange(H), rng.random() * 6.28) for _ in range(W * H // 90)]

    def build_text(self):
        """Name als 3x5 Blockschrift, Punkte in Herzkoordinaten. Leer, wenn das Herz zu klein ist."""
        word = self.name.upper()
        colw = self.D / (2 * self.K) / self.heart_s  # Zeichenzelle in Herzkoordinaten
        rowh = self.D / self.K / self.heart_s
        px_w = 2  # ein Fontpixel = 2 Spalten x 1 Zeile
        total_cols = len(word) * 4 * px_w - px_w
        if total_cols * colw > 1.55:  # passt nicht sauber auf das Herz
            return []
        pts = []
        x_start = -total_cols * colw / 2
        y_top = 0.30
        for li, ch in enumerate(word):
            glyph = FONT.get(ch, FONT["?"])
            for gy, row in enumerate(glyph):
                for gx, bit in enumerate(row):
                    if bit != "#":
                        continue
                    for sub in range(px_w * 2):
                        cx = (li * 4 + gx) * px_w + sub * 0.5
                        x = x_start + cx * colw
                        y = y_top - gy * rowh
                        pts.append((x, y, 1))
                        pts.append((-x, y, -1))  # Rueckseite gespiegelt, damit lesbar
        return pts

    def heart_r(self, x, y):
        """Relativer Radius eines Punktes innerhalb der Herzkontur (0 Mitte, 1 Rand)."""
        ang = math.atan2(y, x)
        i = int((ang + math.pi) / (2 * math.pi) * len(self.rb)) % len(self.rb)
        return min(1.0, math.hypot(x, y) / self.rb[i])

    def project(self, x, y, z):
        zc = z + self.D
        ooz = 1.0 / zc
        return int(self.W / 2 + 2 * self.K * x * ooz), int(self.H / 2 - self.K * (y - self.cy) * ooz), ooz

    def frame(self, t):
        W, H = self.W, self.H
        chars = [[" "] * W for _ in range(H)]
        cols = [[0] * W for _ in range(H)]
        zb = [[0.0] * W for _ in range(H)]

        for (sx, sy, ph) in self.stars:
            b = math.sin(t * 2 + ph)
            if b > 0.6:
                chars[sy][sx] = "*" if b > 0.92 else "."
                cols[sy][sx] = 240 + int(b * 10)

        grow = min(1.0, t / 3.0)
        A = t * 0.9
        ca, sa = math.cos(A), math.sin(A)
        tilt = 0.38
        ct, st = math.cos(tilt), math.sin(tilt)
        lx, ly, lz = LIGHT
        for (x, y, z, nx, ny, nz, pal, two, g) in self.bouquet:
            if g > grow * 1.05:
                continue
            x1, z1 = x * ca + z * sa, -x * sa + z * ca
            y2, z2 = y * ct - z1 * st, y * st + z1 * ct
            nx1, nz1 = nx * ca + nz * sa, -nx * sa + nz * ca
            ny2, nz2 = ny * ct - nz1 * st, ny * st + nz1 * ct
            px, py, ooz = self.project(x1, y2, z2)
            if 0 <= px < W and 0 <= py < H and ooz > zb[py][px]:
                L = nx1 * lx + ny2 * ly + nz2 * lz
                L = abs(L) if two else max(L, 0.0)
                L = 0.15 + 0.85 * L
                zb[py][px] = ooz
                chars[py][px] = SHADES[min(11, int(L * 11.99))]
                p = PAL[pal]
                cols[py][px] = p[min(len(p) - 1, int(L * len(p)))]

        # Herz: erscheint nach dem Strauss, schlaegt und dreht sich
        hgrow = min(1.0, max(0.0, (t - 2.5) / 1.2))
        if hgrow > 0:
            beat = 1 + 0.09 * max(0.0, math.sin(t * 5.5)) ** 6
            S = self.heart_s * beat * (0.4 + 0.6 * hgrow) if hgrow < 1 else self.heart_s * beat
            B = -t * 1.6
            cb, sb = math.cos(B), math.sin(B)
            for (x, y, z, nx, ny, nz) in self.heart:
                x1, z1 = x * cb + z * sb, -x * sb + z * cb
                nx1, nz1 = nx * cb + nz * sb, -nx * sb + nz * cb
                px, py, ooz = self.project(x1 * S, y * S + self.heart_y, z1 * S)
                if 0 <= px < W and 0 <= py < H and ooz > zb[py][px]:
                    L = max(0.0, nx1 * lx + ny * ly + nz1 * lz)
                    L = 0.2 + 0.8 * L
                    zb[py][px] = ooz
                    chars[py][px] = SHADES[min(11, int(L * 11.99))]
                    cols[py][px] = PAL["heart"][min(5, int(L * 6))]
            # Schriftzug auf Vorder und Rueckseite
            fac = cb  # >0: Vorderseite zur Kamera, <0: Rueckseite
            if self.text_pts:
                for (x, y, side) in self.text_pts:
                    if side * fac < 0.2:
                        continue
                    r = self.heart_r(x, y - 0.1)
                    zf = -side * (self.T * math.sqrt(max(0.0, 1 - r * r)) + 0.04)  # Kamera blickt auf z<0
                    x1, z1 = x * cb + zf * sb, -x * sb + zf * cb
                    px, py, ooz = self.project(x1 * S, y * S + self.heart_y, z1 * S)
                    if 0 <= px < W and 0 <= py < H and ooz > zb[py][px] - 0.01:
                        zb[py][px] = ooz
                        chars[py][px] = "\u2588"
                        cols[py][px] = 231 if abs(fac) > 0.6 else 224
            elif abs(fac) > 0.35:
                side = 1 if fac > 0 else -1
                px, py, _ = self.project(0.0, self.heart_y + 0.12 * S, -side * self.T * S * abs(cb))
                txt = self.name
                x0 = px - len(txt) // 2
                for i, ch in enumerate(txt):
                    if 0 <= x0 + i < W and 0 <= py < H:
                        chars[py][x0 + i] = ch
                        cols[py][x0 + i] = 231
        return chars, cols


def to_ansi(chars, cols):
    out = []
    for row, crow in zip(chars, cols):
        last = None
        line = []
        for ch, c in zip(row, crow):
            if ch != " " and c != last:
                line.append(f"\x1b[38;5;{c}m")
                last = c
            line.append(ch)
        out.append("".join(line))
    return "\x1b[H" + "\n".join(out) + "\x1b[0m"


def xterm_rgb(c):
    base = [(0, 0, 0), (128, 0, 0), (0, 128, 0), (128, 128, 0), (0, 0, 128), (128, 0, 128), (0, 128, 128), (192, 192, 192),
            (128, 128, 128), (255, 0, 0), (0, 255, 0), (255, 255, 0), (0, 0, 255), (255, 0, 255), (0, 255, 255), (255, 255, 255)]
    if c < 16:
        return base[c]
    if c < 232:
        c -= 16
        lv = [0, 95, 135, 175, 215, 255]
        return lv[c // 36], lv[(c // 6) % 6], lv[c % 6]
    g = 8 + (c - 232) * 10
    return g, g, g


def run_terminal(name):
    size = shutil.get_terminal_size((120, 40))
    sc = Scene(size.columns, size.lines - 1, name)
    sys.stdout.write("\x1b[2J\x1b[?25l")
    t0 = time.time()
    try:
        while True:
            t = time.time() - t0
            sys.stdout.write(to_ansi(*sc.frame(t)))
            sys.stdout.flush()
            time.sleep(max(0.0, 1 / 30 - (time.time() - t0 - t)))
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\x1b[0m\x1b[?25h\n")


def run_video(path, name, seconds, fps=30, W=144, H=128):
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 9)
    cw, chh = 5, 10
    img_w, img_h = 720, 1280
    sc = Scene(W, H, name)
    ox, oy = (img_w - W * cw) // 2, (img_h - H * chh) // 2
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{img_w}x{img_h}",
                             "-r", str(fps), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", path],
                            stdin=subprocess.PIPE)
    rgb = {}
    for f in range(int(seconds * fps)):
        chars, cols = sc.frame(f / fps)
        im = Image.new("RGB", (img_w, img_h), (12, 10, 20))
        d = ImageDraw.Draw(im)
        for y in range(H):
            for x in range(W):
                ch = chars[y][x]
                if ch != " ":
                    c = cols[y][x]
                    if c not in rgb:
                        rgb[c] = xterm_rgb(c)
                    d.text((ox + x * cw, oy + y * chh), ch, fill=rgb[c], font=font)
        proc.stdin.write(im.tobytes())
    proc.stdin.close()
    proc.wait()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="Schnucki")
    ap.add_argument("--video")
    ap.add_argument("--seconds", type=float, default=14)
    a = ap.parse_args()
    if a.video:
        run_video(a.video, a.name, a.seconds)
    else:
        run_terminal(a.name)
