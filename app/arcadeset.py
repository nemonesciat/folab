"""The Kilauea's arcade: FOLab's own upright arcade cabinets and pachinko machines in place of the Tops' slot machines its
casino floor was furnished with (the user, 25 Nov 2026: "let's leave the machines for now but maybe turn them into arcade
and pachinko machines, however you think it should be"). Hawaiʻi never had casinos; it had arcades, and a big Japanese
community that played pachinko. Set 'arcade' of modelsets (meshes\\folab\\arcade, textures\\folab\\arcade).

Made in the frames of what they replace (`REPLACES`), so a swap is a ref's base and nothing else:
- `SlotMachineTableCluster06` (a bank: a counter 174 x 38, 49.3 high, two machines on it at x -21 and +23, front -y;
  the Kilauea stands them back to back in pairs 87 apart, a single machine on each end slot at x -61.6 and +69, four
  stools in front at y -50): `pachinko_bank` (a lacquered counter, the two machines on it, ball lenders between) or
  `arcade_bank` (two upright cabinets standing on the floor where the counter was; nothing in front of y -29, nothing
  behind y +40, so a pair back to back clears). `_3` versions carry a third machine on the empty left slot.
- the single slot machines (`SlotMachine04StaticTOPS`, `05`: 40 x 34 x 60, standing on the counter, 49 over the floor):
  `pachinko_a` / `pachinko_b` (on the counter) or `arcade_a` / `_b` / `_c` (their feet 49 under their origin, on the
  floor beside the bank's two).

Each piece is one picture sheet drawn here (numpy and PIL: a build step run from the developer's Python, as garmentprint
and armourset; DEV_ONLY in packaging): colour, relief (heights) and gloss per pixel (lacquer, chrome, glass, rubber,
paper each shine as they do), and a glow picture lit only where light comes from (the marquee's backlit plastic, the
screen, the coin lights, the pachinko's lamps). Shade is baked into the model's corners as every FOLab model's
(modelmake), edges rounded; every part closed. Glass over a pachinko board is its own see-through shape.

Playable: the step makes each swapped ref's base an ACTI that opens the game's slot machine menu on a casino record of
FOLab's own (`casino`: its reel symbols FOLab's, its money the island's), as the game's own slot machines do."""
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import modelsets
import texpaint as tp
import texwear as tw

SET = 'arcade'
S = 1024                    # (a sheet's size)


# ---------- drawing in numpy ----------

def noise(h, w, cells, seed, octaves=4, rough=0.5):
    """Smooth value noise 0-1 over an h x w picture, `cells` blobs across at the coarsest."""
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        n = max(2, int(cells * 2 ** o))
        g = rng.random((max(2, int(n * h / max(w, 1))) + 1, n + 1))
        img = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        out += amp * np.asarray(img, float) / 255.0
        tot += amp
        amp *= rough
    return np.clip(out / tot, 0, 1)


def mask(w, h, draw, ss=4, blur=0):
    """0-1 coverage of what draw(ImageDraw, k) draws (k: the supersampling, multiply coordinates by it), w x h."""
    im = Image.new('L', (w * ss, h * ss), 0)
    draw(ImageDraw.Draw(im), ss)
    im = im.resize((w, h), Image.LANCZOS)
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(im, float) / 255.0


def poly(pts, k):
    return [(x * k, y * k) for x, y in pts]


def mix(a, b, t):
    t = np.asarray(t, float)
    if t.ndim == 2:
        t = t[..., None]
    return a * (1 - t) + np.asarray(b, float) * t


# A 5 x 7 pixel font for screens and score counters (FOLab's own)
FONT = {
    '0': '01110 10001 10011 10101 11001 10001 01110', '1': '00100 01100 00100 00100 00100 00100 01110',
    '2': '01110 10001 00001 00110 01000 10000 11111', '3': '11110 00001 00001 01110 00001 00001 11110',
    '4': '00010 00110 01010 10010 11111 00010 00010', '5': '11111 10000 11110 00001 00001 10001 01110',
    '6': '00110 01000 10000 11110 10001 10001 01110', '7': '11111 00001 00010 00100 01000 01000 01000',
    '8': '01110 10001 10001 01110 10001 10001 01110', '9': '01110 10001 10001 01111 00001 00010 01100',
    'A': '01110 10001 10001 11111 10001 10001 10001', 'B': '11110 10001 10001 11110 10001 10001 11110',
    'C': '01110 10001 10000 10000 10000 10001 01110', 'D': '11110 10001 10001 10001 10001 10001 11110',
    'E': '11111 10000 10000 11110 10000 10000 11111', 'F': '11111 10000 10000 11110 10000 10000 10000',
    'G': '01110 10001 10000 10111 10001 10001 01111', 'H': '10001 10001 10001 11111 10001 10001 10001',
    'I': '01110 00100 00100 00100 00100 00100 01110', 'K': '10001 10010 10100 11000 10100 10010 10001',
    'L': '10000 10000 10000 10000 10000 10000 11111', 'M': '10001 11011 10101 10101 10001 10001 10001',
    'N': '10001 11001 10101 10011 10001 10001 10001', 'O': '01110 10001 10001 10001 10001 10001 01110',
    'P': '11110 10001 10001 11110 10000 10000 10000', 'R': '11110 10001 10001 11110 10100 10010 10001',
    'S': '01111 10000 10000 01110 00001 00001 11110', 'T': '11111 00100 00100 00100 00100 00100 00100',
    'U': '10001 10001 10001 10001 10001 10001 01110', 'V': '10001 10001 10001 10001 10001 01010 00100',
    'W': '10001 10001 10001 10101 10101 10101 01010', 'Y': '10001 10001 01010 00100 00100 00100 00100',
    'Z': '11111 00001 00010 00100 01000 10000 11111', '-': '00000 00000 00000 11111 00000 00000 00000',
    ':': '00000 01100 01100 00000 01100 01100 00000', '!': '00100 00100 00100 00100 00100 00000 00100',
    '.': '00000 00000 00000 00000 00000 01100 01100', ' ': '00000 00000 00000 00000 00000 00000 00000',
    'J': '00111 00010 00010 00010 00010 10010 01100', 'Q': '01110 10001 10001 10001 10101 10010 01101',
    "'": '00100 00100 01000 00000 00000 00000 00000', 'X': '10001 10001 01010 00100 01010 10001 10001',
}


def pixtext(grid, text, x, y, colour, scale=1):
    """Pixel letters into a small screen grid (H, W, 3), top left at x, y."""
    for ch in text.upper():
        rows = FONT.get(ch, FONT[' ']).split()
        for j, row in enumerate(rows):
            for i, b in enumerate(row):
                if b == '1':
                    grid[y + j * scale:y + (j + 1) * scale, x + i * scale:x + (i + 1) * scale] = colour
        x += 6 * scale
    return x


def text_wide(text, scale=1):
    return len(text) * 6 * scale - scale


def stamp(rgb, text, x, y, high, colour, centre=False, wide=None):
    """Pixel letters stamped at a whole number of pixels a dot (never shrunk: a shrunk letter loses its strokes), about
    `high` pixels tall, top left at (x, y) or centred on x. Returns the mask stamped."""
    h, w = rgb.shape[:2]
    k = max(1, int(round(high / 7.0)))
    wide = wide or w * 0.9
    while k > 1 and text_wide(text, k) > wide:
        k -= 1
    small = np.zeros((7 * k + 2, text_wide(text, k) + 2, 3))
    pixtext(small, text, 1, 1, (255, 255, 255), scale=k)
    m = small[..., 0] / 255.0
    if centre:
        x = int(x - m.shape[1] / 2.0)
    x, y = int(x), int(y)
    x1, y1 = min(w, x + m.shape[1]), min(h, y + m.shape[0])
    mm = np.zeros((h, w))
    mm[y:y1, x:x1] = m[:y1 - y, :x1 - x]
    rgb[:] = mix(rgb, colour, mm)
    return mm


class Sheet:
    """One piece's picture: colour (0-255), heights (0-1, 0.5 flat), gloss (0-255) and glow, S x S."""

    def __init__(self, w=S, h=S):
        self.w, self.h = w, h
        self.rgb = np.zeros((h, w, 3))
        self.ht = np.full((h, w), 0.5)
        self.gloss = np.full((h, w), 30.0)
        self.glow = np.zeros((h, w, 3))
        self.a = None

    def uv(self, box):
        x0, y0, x1, y1 = box
        return (x0 / float(self.w), y0 / float(self.h), x1 / float(self.w), y1 / float(self.h))

    def picture(self):
        """A texwear.Picture with its glow, as modelsets.TEXTURES gives."""
        pic = tw.Picture(self.w, self.h)
        rgb = np.clip(self.rgb, 0, 255)
        pic.rgb = [tuple(p) for p in rgb.reshape(-1, 3).tolist()]
        pic.ht = np.clip(self.ht, 0, 1).ravel().tolist()
        pic.gloss = [int(v) for v in np.clip(self.gloss, 0, 255).ravel()]
        if self.a is not None:
            pic.a = np.clip(self.a, 0, 1).ravel().tolist()
        if self.glow.max() > 1:
            g = tw.Picture(self.w, self.h, gloss=0)
            g.rgb = [tuple(p) for p in np.clip(self.glow, 0, 255).reshape(-1, 3).tolist()]
            pic.glow = g
        else:
            pic.glow = None
        return pic


def sub(sh, box):
    """Views of a sheet's arrays inside box (x0, y0, x1, y1): (rgb, ht, gloss, glow)."""
    x0, y0, x1, y1 = box
    return sh.rgb[y0:y1, x0:x1], sh.ht[y0:y1, x0:x1], sh.gloss[y0:y1, x0:x1], sh.glow[y0:y1, x0:x1]


# ---------- surfaces ----------

def paint_panel(sh, box, colour, seed, gloss=46, chips=0.5, grime=0.6, under=(60, 56, 52), scuffs=1.0, laminate=False):
    """Painted (or laminated) board: the colour a little uneven, chips through to what is under, grime gathered toward
    the edges, scuffs and fine scratches, the gloss worn off where hands and feet went."""
    rgb, ht, gl, _g = sub(sh, box)
    h, w = ht.shape
    n1 = noise(h, w, 4, seed)
    n2 = noise(h, w, 24, seed + 1, octaves=3)
    base = np.asarray(colour, float) * (0.92 + 0.12 * n1[..., None]) * (0.97 + 0.06 * n2[..., None])
    if laminate:                                    # (woodgrain-printed laminate under the colour's sheen)
        g = noise(h, max(2, w // 8), 3, seed + 9, octaves=4)
        g = np.asarray(Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), float) / 255
        base = base * (0.9 + 0.16 * np.sin(g[..., None] * 40.0) * 0.5)
    yy, xx = np.mgrid[0:h, 0:w]
    edge = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy)) / float(max(8, min(w, h) * 0.12))
    edge = np.clip(edge, 0, 1)
    dirt = (1 - edge) * grime * (0.5 + 0.5 * n2)
    base = mix(base, (46, 40, 34), np.clip(dirt * 0.55, 0, 1))
    chip = np.clip((noise(h, w, 14, seed + 2, octaves=3) - (1 - 0.16 * chips)) * 14, 0, 1) * (0.4 + 0.6 * (1 - edge))
    base = mix(base, under, chip)
    rgb[:] = base
    ht[:] = 0.5 + 0.04 * (n2 - 0.5) - 0.06 * chip
    gl[:] = gloss * (0.7 + 0.3 * n1) * (1 - 0.8 * chip) * (1 - 0.4 * dirt)
    rnd = random.Random(seed + 3)
    if scuffs:
        sm = mask(w, h, lambda d, k: [d.line(poly([(a, b), (a + rnd.uniform(-60, 60), b + rnd.uniform(-8, 8))], k), fill=255, width=max(1, int(k * rnd.uniform(0.6, 1.6))))
                                      for a, b in [(rnd.uniform(0, w), rnd.uniform(0, h)) for _ in range(int(14 * scuffs * w * h / 65536.0) + 2)]])
        rgb[:] = mix(rgb, np.minimum(255, rgb * 1.25 + 12), sm * 0.7)
        ht[:] -= sm * 0.05
        gl[:] *= 1 - 0.5 * sm


def chrome(sh, box, seed, tint=(206, 210, 214), pitted=0.4):
    """Chromed metal: bright, a soft reflection band, pits and rust spots where the plate has gone."""
    rgb, ht, gl, _g = sub(sh, box)
    h, w = ht.shape
    yy = np.linspace(0, 1, h)[:, None]
    band = 0.75 + 0.45 * np.exp(-((yy - 0.35) / 0.12) ** 2) - 0.25 * np.exp(-((yy - 0.75) / 0.15) ** 2)
    n = noise(h, w, 12, seed, octaves=3)
    pit = np.clip((noise(h, w, 40, seed + 1, octaves=2) - (1 - 0.1 * pitted)) * 12, 0, 1)
    rgb[:] = mix(np.asarray(tint, float) * band[..., None] * (0.94 + 0.08 * n[..., None]), (120, 78, 52), pit)
    ht[:] = 0.5 - 0.1 * pit
    gl[:] = 230 * (1 - 0.8 * pit)


def rubber(sh, box, seed, colour=(26, 24, 24)):
    rgb, ht, gl, _g = sub(sh, box)
    h, w = ht.shape
    n = noise(h, w, 20, seed, octaves=3)
    rgb[:] = np.asarray(colour, float) * (0.85 + 0.3 * n[..., None])
    ht[:] = 0.5 + 0.08 * (n - 0.5)
    gl[:] = 14


def plastic(sh, box, colour, seed, gloss=110, glow=0.0, ring=True):
    """Moulded plastic (buttons, a joystick's ball, lamp lenses): a bright rim of light, a highlight, worn where pressed."""
    rgb, ht, gl, gw = sub(sh, box)
    h, w = ht.shape
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot((xx - w / 2.0) / (w / 2.0), (yy - h / 2.0) / (h / 2.0))
    n = noise(h, w, 6, seed, octaves=2)
    col = np.asarray(colour, float) * (0.8 + 0.25 * (1 - r)[..., None]) * (0.95 + 0.1 * n[..., None])
    hl = np.exp(-(((xx - w * 0.36) / (w * 0.12)) ** 2 + ((yy - h * 0.32) / (h * 0.1)) ** 2))
    rgb[:] = np.minimum(255, col + 120 * hl[..., None])
    ht[:] = 0.5 + 0.1 * (1 - np.clip(r, 0, 1))
    gl[:] = gloss
    if glow:
        gw[:] = np.asarray(colour, float) * glow * (0.6 + 0.4 * (1 - np.clip(r, 0, 1)))[..., None]


# ---------- pictures on the sheets (marquees, side art, screens) ----------

SUNSET = [(30, 24, 60), (120, 40, 90), (232, 92, 60), (252, 178, 72), (255, 226, 140)]


def gradient(h, w, stops, vertical=True):
    t = np.linspace(0, 1, h if vertical else w)
    cols = np.array(stops, float)
    k = (len(stops) - 1) * t
    i = np.clip(k.astype(int), 0, len(stops) - 2)
    f = (k - i)[:, None]
    row = cols[i] * (1 - f) + cols[i + 1] * f
    return np.repeat(row[:, None, :], w, 1) if vertical else np.repeat(row[None, :, :], h, 0)


def letters_mask(words, w, h, box, style='deco'):
    """FOLab's sign lettering (signpaint) as numpy masks: (ink, core) 0-1, h x w, the words fitted in box."""
    import signpaint as sp
    m, thick = sp.letters(words, style, box, w, h)
    ink = np.array(m['ink'].v, float).reshape(h, w)
    core = np.array(m['core'].v, float).reshape(h, w)
    return np.clip(ink, 0, 1), np.clip(core, 0, 1), thick


def shape_mask(w, h, polys, ss=4):
    return mask(w, h, lambda d, k: [d.polygon(poly(p, k), fill=255) for p in polys], ss)


def ellipse_mask(w, h, cx, cy, rx, ry, ss=4):
    return mask(w, h, lambda d, k: d.ellipse((k * (cx - rx), k * (cy - ry), k * (cx + rx), k * (cy + ry)), fill=255), ss)


def outline_of(m, px):
    """A dark line round a shape px wide (the period's printed outline)."""
    im = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(px * 2 + 1))
    return np.clip(np.asarray(im, float) / 255.0 - m, 0, 1)


def lay(rgb, m, colour, line=None, line_px=3):
    """A flat printed shape onto rgb, with a dark outline."""
    if line is not None:
        rgb[:] = mix(rgb, line, outline_of(m, line_px))
    rgb[:] = mix(rgb, colour, m)


def wave_curl(w, h, x0, base, high, lean=1.0):
    """A big breaking wave: the face rising from the left to a crest that curls over to the right, as a polygon."""
    pts = []
    for j in range(25):
        t = j / 24.0
        pts.append((x0 + high * 1.6 * t * lean, base - high * (t ** 1.6)))
    cx, cy, r = x0 + high * 1.6 * lean, base - high * 0.62, high * 0.38
    for j in range(1, 26):
        a = -90 + 12 * j
        rr = r * (1 - 0.55 * j / 25)
        pts.append((cx + rr * math.cos(math.radians(a)) * lean, cy + rr * math.sin(math.radians(a))))
    pts.append((cx - r * 0.2 * lean, base))
    return pts


def palm_shape(x, y, size, lean=0.15, seed=1):
    """A palm's trunk (a curving band) and fronds (long leaves), as polygons: trunk first."""
    rnd = random.Random(seed)
    trunk_l, trunk_r = [], []
    top = None
    for j in range(13):
        t = j / 12.0
        cx = x + size * lean * (t ** 1.6) * 3
        cy = y - size * t
        wd = size * (0.06 - 0.025 * t)
        trunk_l.append((cx - wd, cy))
        trunk_r.append((cx + wd, cy))
        top = (cx, cy)
    out = [trunk_l + trunk_r[::-1]]
    for k in range(7):
        a = math.radians(-160 + k * 50 + rnd.uniform(-10, 10))
        ln = size * rnd.uniform(0.45, 0.62)
        pts_up, pts_dn = [], []
        for j in range(9):
            t = j / 8.0
            px = top[0] + math.cos(a) * ln * t
            py = top[1] + math.sin(a) * ln * t + ln * 0.35 * t * t
            wd = ln * 0.09 * math.sin(math.pi * min(1, t * 1.1))
            pts_up.append((px, py - wd))
            pts_dn.append((px, py + wd))
        out.append(pts_up + pts_dn[::-1])
    return out


def surfer_shape(x, y, s, facing=1):
    """A surfer standing on a board, crouched, arms out: polygons (board, body), feet at (x, y), s tall."""
    f = facing
    board = [(x - 0.75 * s * f, y + 0.02 * s), (x + 0.8 * s * f, y - 0.08 * s), (x + 0.9 * s * f, y - 0.02 * s),
             (x - 0.7 * s * f, y + 0.08 * s)]
    body = [(x - 0.22 * s * f, y), (x - 0.1 * s * f, y - 0.35 * s), (x - 0.05 * s * f, y - 0.62 * s), (x - 0.42 * s * f, y - 0.55 * s),
            (x - 0.44 * s * f, y - 0.6 * s), (x - 0.02 * s * f, y - 0.72 * s), (x + 0.02 * s * f, y - 0.86 * s),
            (x + 0.12 * s * f, y - 0.86 * s), (x + 0.12 * s * f, y - 0.72 * s), (x + 0.46 * s * f, y - 0.7 * s),
            (x + 0.47 * s * f, y - 0.64 * s), (x + 0.12 * s * f, y - 0.6 * s), (x + 0.14 * s * f, y - 0.38 * s), (x + 0.26 * s * f, y)]
    head = (x + 0.07 * s * f, y - 0.93 * s, 0.07 * s)
    return board, body, head


def shark_shape(x, y, s, facing=1):
    f = facing
    body = [(x - 0.5 * s * f, y), (x - 0.25 * s * f, y - 0.14 * s), (x + 0.1 * s * f, y - 0.16 * s), (x + 0.42 * s * f, y - 0.06 * s),
            (x + 0.5 * s * f, y + 0.02 * s), (x + 0.36 * s * f, y + 0.08 * s), (x, y + 0.1 * s), (x - 0.34 * s * f, y + 0.06 * s)]
    fin = [(x - 0.05 * s * f, y - 0.15 * s), (x - 0.12 * s * f, y - 0.42 * s), (x + 0.12 * s * f, y - 0.15 * s)]
    tail = [(x - 0.46 * s * f, y + 0.01 * s), (x - 0.7 * s * f, y - 0.24 * s), (x - 0.6 * s * f, y + 0.02 * s), (x - 0.7 * s * f, y + 0.2 * s)]
    pec = [(x + 0.05 * s * f, y + 0.06 * s), (x - 0.12 * s * f, y + 0.26 * s), (x + 0.15 * s * f, y + 0.08 * s)]
    return [body, fin, tail, pec]


def volcano_shape(x, y, wd, high):
    return [(x - wd / 2, y), (x - wd * 0.1, y - high), (x - wd * 0.04, y - high * 0.94), (x + wd * 0.04, y - high * 0.96),
            (x + wd * 0.1, y - high), (x + wd / 2, y)]


# The three cabinets' games (the user may rename them: they are only the cabinets' paint)
GAMES = {
    'a': {'title': 'SURF RIDER', 'body': (30, 128, 132), 'trim': (240, 196, 72), 'ink': (250, 214, 80), 'outline': (150, 30, 36),
          'ground': [(14, 40, 80), (24, 92, 150), (240, 120, 70), (252, 196, 96)]},
    'b': {'title': 'SHARK ATTACK', 'body': (180, 44, 40), 'trim': (232, 232, 220), 'ink': (246, 246, 236), 'outline': (20, 30, 70),
          'ground': [(8, 20, 46), (14, 60, 108), (30, 120, 150), (80, 180, 190)]},
    'c': {'title': 'VOLCANO RUN', 'body': (34, 34, 38), 'trim': (232, 120, 40), 'ink': (255, 150, 44), 'outline': (40, 10, 10),
          'ground': [(20, 6, 20), (90, 20, 30), (200, 60, 30), (250, 160, 60)]},
}


def marquee(sh, box, game, seed):
    """The lit sign over the screen: the game's name in FOLab's deco letters, its picture, printed on plastic lit from
    behind (the whole of it glows, the letters and bright paint most), a little sun-faded and cracked at a corner."""
    rgb, ht, gl, gw = sub(sh, box)
    h, w = ht.shape
    G = GAMES[game]
    rgb[:] = gradient(h, w, G['ground'])
    if game == 'a':
        sun = ellipse_mask(w, h, w * 0.82, h * 0.78, h * 0.42, h * 0.42)
        lay(rgb, sun, (255, 214, 110))
        for k in range(4):
            yy = h * (0.6 + 0.08 * k)
            rgb[int(yy):int(yy + h * 0.025)] = mix(rgb[int(yy):int(yy + h * 0.025)], G['ground'][1], sun[int(yy):int(yy + h * 0.025)] * 0.85)
        wave = shape_mask(w, h, [wave_curl(w, h, w * 0.02, h * 1.02, h * 0.9)])
        lay(rgb, wave, (40, 150, 170), (12, 30, 50), 3)
        foam = shape_mask(w, h, [wave_curl(w, h, w * 0.06, h * 0.95, h * 0.7)]) * (1 - shape_mask(w, h, [wave_curl(w, h, w * 0.02, h * 1.1, h * 0.72)]))
        lay(rgb, foam, (236, 244, 240))
        b, body, head = surfer_shape(w * 0.17, h * 0.42, h * 0.38, 1)
        lay(rgb, shape_mask(w, h, [b]), (240, 70, 60), (20, 20, 30), 2)
        lay(rgb, shape_mask(w, h, [body]) + ellipse_mask(w, h, head[0], head[1], head[2], head[2]), (34, 26, 30))
        for k, px in enumerate((0.9, 0.97)):
            for p in palm_shape(w * px, h * 1.02, h * 0.9, lean=-0.06 if k else 0.04, seed=seed + k):
                lay(rgb, shape_mask(w, h, [p]), (26, 30, 34))
    elif game == 'b':
        for k in range(8):                              # (light rays down through the water)
            x = w * (0.1 + 0.11 * k)
            ray = shape_mask(w, h, [[(x, 0), (x + w * 0.03, 0), (x + w * 0.09, h), (x + w * 0.05, h)]])
            rgb[:] = mix(rgb, (140, 210, 220), ray * 0.18)
        for p in shark_shape(w * 0.18, h * 0.56, h * 1.1, 1):
            lay(rgb, shape_mask(w, h, [p]), (96, 112, 130), (10, 16, 30), 3)
        jaw = shape_mask(w, h, [[(w * 0.18 + h * 0.36, h * 0.6), (w * 0.18 + h * 0.52, h * 0.57), (w * 0.18 + h * 0.4, h * 0.66)]])
        lay(rgb, jaw, (240, 236, 226), (90, 10, 20), 2)
        eye = ellipse_mask(w, h, w * 0.18 + h * 0.3, h * 0.5, h * 0.022, h * 0.022)
        lay(rgb, eye, (10, 10, 12))
        diver = shape_mask(w, h, [[(w * 0.86, h * 0.3), (w * 0.95, h * 0.42), (w * 0.93, h * 0.47), (w * 0.84, h * 0.36)]]) + \
            ellipse_mask(w, h, w * 0.85, h * 0.29, h * 0.06, h * 0.06)
        lay(rgb, np.clip(diver, 0, 1), (230, 200, 40), (10, 10, 20), 2)
        for k in range(9):
            rr = h * (0.015 + 0.012 * (k % 3))
            lay(rgb, ellipse_mask(w, h, w * (0.8 - 0.012 * k), h * (0.25 - 0.026 * k), rr, rr) * (1 - ellipse_mask(w, h, w * (0.8 - 0.012 * k), h * (0.25 - 0.026 * k), rr * 0.6, rr * 0.6)), (200, 240, 250))
    else:
        v = shape_mask(w, h, [volcano_shape(w * 0.84, h * 1.0, h * 1.5, h * 0.75)])
        lay(rgb, v, (40, 20, 22), (10, 4, 6), 2)
        for k in range(6):                              # (lava down its side)
            a = -0.5 + k * 0.2
            lava = shape_mask(w, h, [[(w * 0.84 + h * 0.02, h * 0.27), (w * 0.84 + h * a * 0.7, h), (w * 0.84 + h * (a * 0.7 + 0.05), h), (w * 0.84 + h * 0.05, h * 0.28)]]) * v
            lay(rgb, lava, (255, 120, 30))
        glowtop = ellipse_mask(w, h, w * 0.84, h * 0.2, h * 0.3, h * 0.22, ss=2)
        rgb[:] = mix(rgb, (255, 180, 80), np.asarray(Image.fromarray((glowtop * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(h * 0.08)), float) / 255 * 0.8)
        road = shape_mask(w, h, [[(w * 0.0, h), (w * 0.32, h), (w * 0.2, h * 0.62), (w * 0.15, h * 0.62)]])
        lay(rgb, road, (50, 46, 50))
        for k in range(4):
            y0 = h * (0.66 + 0.09 * k)
            lay(rgb, shape_mask(w, h, [[(w * (0.17 + 0.0 * k), y0), (w * 0.185, y0), (w * (0.19 + 0.008 * k), y0 + h * 0.05), (w * (0.17 + 0.006 * k), y0 + h * 0.05)]]), (250, 220, 90))
        car = [(w * 0.05, h * 0.95), (w * 0.07, h * 0.82), (w * 0.12, h * 0.78), (w * 0.2, h * 0.8), (w * 0.24, h * 0.95)]
        lay(rgb, shape_mask(w, h, [car]), (220, 40, 36), (20, 10, 10), 3)
    # the name, centred, deco letters with an outline and a drop shadow, a light line inside
    ink, core, thick = letters_mask(G['title'], w, h, (w * 0.2, h * 0.08, w * 0.8, h * 0.92), 'deco')
    shadow = np.roll(np.roll(ink, int(thick * 0.4), 0), int(thick * 0.4), 1)
    rgb[:] = mix(rgb, (14, 10, 12), shadow * 0.8)
    rgb[:] = mix(rgb, G['outline'], np.clip(outline_of(ink, max(2, int(thick * 0.22))) * 1.2, 0, 1))
    rgb[:] = mix(rgb, mix(np.broadcast_to(np.asarray(G['ink'], float), rgb.shape), (255, 252, 236), core * 0.5), ink)
    # backlit: the plastic glows with its print, the letters most; faded by the sun from the top, a crack at a corner
    fade = noise(h, w, 3, seed + 5)
    rgb[:] = mix(rgb, (226, 220, 206), (0.12 + 0.1 * fade) * np.linspace(1, 0.4, h)[:, None])
    crack = mask(w, h, lambda d, k: d.line(poly([(w * 0.97, 0), (w * 0.93, h * 0.3), (w * 0.95, h * 0.45), (w * 0.9, h * 0.7)], k), fill=255, width=2 * k))
    rgb[:] = mix(rgb, (30, 26, 24), crack * 0.8)
    gw[:] = rgb * (0.38 + 0.35 * ink[..., None]) * (1 - 0.6 * crack[..., None])
    ht[:] = 0.5 + 0.03 * ink - 0.1 * crack
    gl[:] = 120 - 60 * fade


# Hand-drawn pixel sprites for the screens: a letter a colour ('.' clear)
SPRITES = {
    'surfer': ("......hh........\n"
               ".....hhkh.......\n"
               ".....kkkk.......\n"
               "......kk........\n"
               "....kkkkkk......\n"
               "..kkk.kk.kkk....\n"
               ".kk...kk...kk...\n"
               "......kk........\n"
               ".....rrrr.......\n"
               ".....rr.rr......\n"
               "....kk...kk.....\n"
               "...kk.....kk....\n"
               "..bbbbbbbbbbbbb.\n"
               ".bsssssssssssssb\n"
               "..bbbbbbbbbbbbb."),
    'shark': ("..............g.................\n"
              ".............gg.................\n"
              "............ggg.................\n"
              "...........gggg.................\n"
              "g.......ggggggggggggg...........\n"
              "gg....gggggggggggggggggg........\n"
              ".ggggggggggggggggggggggggggg....\n"
              "..gggggggggggggggggggggggg.ewgg.\n"
              ".ggggggwwwwwwwwwwwwwwwwwwwwwwggg\n"
              "gg....wwwwwwwwwwwwwwwwwwwwtwtw..\n"
              "g........wwwwwwwgg.wwwwwwwww....\n"
              "................gg..............\n"),
    'diver': ("...yyy..........\n"
              "..yccy..........\n"
              "..yyyykkkkkkk...\n"
              "...kkkkkkkkkkkf.\n"
              ".....kk....kkff.\n"),
    'car': ("....rrrrrrrr....\n"
            "...rcccccccccr...\n"
            "..rcccccccccccr..\n"
            ".rrrrrrrrrrrrrrr.\n"
            "rrwwrrrrrrrrrwwrr\n"
            "rrrrrrrrrrrrrrrrr\n"
            "kkk.kkkkkkkkk.kkk\n"
            "kkk...........kkk\n"),
    'fish': ("..oo..\n"
             ".oooo.o\n"
             "ooeoooo\n"
             ".oooo.o\n"
             "..oo..\n"),
}
PALETTE = {'h': (70, 40, 20), 'k': (232, 170, 120), 'r': (230, 50, 50), 'b': (250, 244, 214), 's': (240, 60, 60),
           'g': (120, 138, 156), 'w': (236, 236, 230), 'e': (10, 10, 10), 't': (250, 250, 250), 'y': (250, 210, 40),
           'c': (140, 220, 250), 'f': (40, 40, 60), 'o': (255, 150, 40)}


def sprite(grid, name, x, y, flip=False, colours=None):
    rows = SPRITES[name].strip('\n').split('\n')
    pal = dict(PALETTE, **(colours or {}))
    H, W = grid.shape[:2]
    for j, row in enumerate(rows):
        row = row[::-1] if flip else row
        for i, ch in enumerate(row):
            if ch != '.' and 0 <= y + j < H and 0 <= x + i < W:
                grid[y + j, x + i] = pal[ch]


def screen(sh, box, game, seed):
    """The game on the screen, as a raster of fat pixels: its picture, a score along the top, scan lines, the glass's
    curve darkening the corners and a reflection across it. It glows."""
    rgb, ht, gl, gw = sub(sh, box)
    h, w = ht.shape
    H, W = 96, 128                                  # (the game's own pixels)
    g = np.zeros((H, W, 3))
    rnd = random.Random(seed)
    if game == 'a':
        g[:60] = gradient(60, W, [(20, 24, 70), (110, 50, 110), (240, 110, 70), (255, 200, 110)])
        for k in range(5):                         # (the sun on the horizon, banded)
            pass
        sun = ellipse_mask(W, H, 30, 60, 16, 16, ss=1) > 0.5
        bands = (np.arange(H)[:, None] % 4 == 0) & (np.arange(H)[:, None] > 50)
        g[sun & ~bands & (np.arange(H)[:, None] < 60)] = (255, 226, 120)
        for y in range(60, H):                     # (the sea, darker toward us, rows of chop)
            t = (y - 60) / 36.0
            g[y] = (16 + 10 * t, 70 + 40 * (1 - t), 120 + 30 * (1 - t))
            for x in range(rnd.randrange(4), W, 9 + y % 5):
                g[y, x:x + 3] = (60, 150, 180)
        # the wave: a wall rising on the right, its lip curling over to the left, foam at the lip
        for y in range(18, H):
            lip = 64 + (y - 18) * 0.25
            g[y, int(lip):] = (24 + y // 2, 110 + y // 3, 150 + y // 4)
            if y < 40:
                g[y, int(lip):int(lip) + 6] = (220, 244, 246)
        for x in range(56, W):                     # (the lip thrown forward)
            top = 18 + int(6 * math.sin((x - 56) / 22.0))
            g[top:top + 4, x] = (230, 248, 250)
        for k in range(30):
            g[rnd.randrange(40, H), rnd.randrange(70, W)] = (160, 220, 230)
        sprite(g, 'surfer', 46, 50)
        pixtext(g, 'SC 004250', 3, 3, (255, 255, 255))
        pixtext(g, 'HI 18900', 76, 3, (255, 220, 80))
        for k in range(3):                         # (boards left)
            g[88:90, 4 + 8 * k:10 + 8 * k] = (250, 244, 214)
    elif game == 'b':
        g[:] = gradient(H, W, [(30, 110, 150), (14, 60, 110), (8, 24, 56)])
        g[:8] = (90, 170, 200)                     # (the surface, light on it)
        for x in range(0, W, 6):
            g[7 + (x // 6) % 2, x:x + 4] = (200, 240, 250)
        for k in range(6):                         # (rays)
            x0 = 10 + 22 * k
            for y in range(8, 70):
                xx = int(x0 + y * 0.3)
                if xx < W:
                    g[y, xx:xx + 2] = np.minimum(255, g[y, xx:xx + 2] + 18)
        g[84:] = (190, 164, 104)                   # (sand, with weed and a rock)
        for x in range(0, W, 2):
            g[84 + (x * 13) % 3, x] = (160, 136, 86)
        for x in range(4, W, 14):
            for y in range(72, 84):
                g[y, x + int(2 * math.sin(y / 2.0))] = (40, 130, 70)
        sprite(g, 'shark', 18, 44)
        sprite(g, 'diver', 92, 30)
        for k in range(3):
            sprite(g, 'fish', 70 + 10 * k, 66 + 4 * (k % 2))
        for k in range(10):
            bx, by = 96 + rnd.randrange(-3, 3), 26 - 2 * k
            if by > 9:
                g[by, bx] = (220, 250, 255)
        pixtext(g, 'SC 001370', 3, 12, (255, 255, 255))
        pixtext(g, 'AIR', 84, 12, (255, 255, 255))
        g[13:18, 104:124] = (40, 40, 40)
        g[13:18, 104:118] = (60, 220, 90)
    else:
        g[:50] = gradient(50, W, [(20, 6, 30), (90, 20, 40), (220, 80, 40), (255, 170, 70)])
        for k in range(40):
            g[rnd.randrange(0, 20), rnd.randrange(W)] = (255, 240, 220)
        vm = shape_mask(W, H, [volcano_shape(92, 50, 80, 36)], ss=1) > 0.5
        g[vm] = (54, 26, 30)
        for k in range(4):
            lm = shape_mask(W, H, [[(92, 15), (78 + 9 * k, 50), (81 + 9 * k, 50), (93, 16)]], ss=1) > 0.4
            g[lm & vm] = (255, 120 + 20 * k, 30)
        for k in range(12):
            g[rnd.randrange(4, 14), 88 + rnd.randrange(9)] = (255, 200, 80)
        g[40:50, :40] = (30, 50, 30)               # (the jungle on the left)
        for x in range(0, 40, 3):
            g[36 + x % 4:40, x:x + 2] = (40, 70, 40)
        for y in range(50, H):                     # (the road to the volcano)
            t = (y - 50) / float(H - 50)
            half = 6 + 66 * t
            g[y] = (36, 70, 36) if (int(t * t * 40) % 2) else (44, 84, 40)
            g[y, max(0, int(64 - half)):min(W, int(64 + half))] = (84, 84, 90)
            g[y, max(0, int(64 - half)):max(0, int(64 - half)) + 2] = (230, 230, 230) if int(t * t * 40) % 2 else (220, 40, 40)
            g[y, min(W - 2, int(64 + half) - 2):min(W, int(64 + half))] = (230, 230, 230) if int(t * t * 40) % 2 else (220, 40, 40)
            if int(t * t * 24) % 2 == 0:
                g[y, int(63 - 1.5 * t):int(65 + 1.5 * t)] = (250, 230, 120)
        sprite(g, 'car', 56, 80, colours={'c': (140, 200, 240)})
        pixtext(g, 'TIME 41', 3, 3, (255, 255, 120))
        pixtext(g, 'SC 007700', 70, 3, (255, 255, 255))
    big = np.asarray(Image.fromarray(np.clip(g, 0, 255).astype(np.uint8)).resize((w, h), Image.NEAREST), float)
    soft = np.asarray(Image.fromarray(big.astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.0)), float)
    yy, xx = np.mgrid[0:h, 0:w]
    scan = 0.7 + 0.3 * np.cos(((yy + 0.5) % (h / float(H))) / (h / float(H)) * np.pi) ** 2
    r = np.hypot((xx - w / 2.0) / (w / 2.0), (yy - h / 2.0) / (h / 2.0))
    vign = np.clip(1.12 - 0.5 * r ** 3, 0, 1)
    pic = soft * scan[..., None] * vign[..., None]
    bloom = np.asarray(Image.fromarray(np.clip(pic, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(5)), float)
    pic = np.clip(pic + 0.22 * bloom, 0, 255)
    refl = np.exp(-((xx / float(w) - 0.2 - yy / float(h) * 0.3) / 0.07) ** 2) * 0.12
    dust = noise(h, w, 30, seed + 4, octaves=2)
    rgb[:] = np.clip(pic * 0.85 + 40 * refl[..., None] + 8 + 10 * (dust[..., None] - 0.5), 0, 255)
    gw[:] = pic * 0.9
    ht[:] = 0.5
    gl[:] = 210 - 60 * dust


def grad_fill(rgb, m, top, bottom, y0=None, y1=None):
    """A shape filled with a colour running from top to bottom (airbrushed, as cabinet art was)."""
    h = rgb.shape[0]
    y0 = 0 if y0 is None else y0
    y1 = h if y1 is None else y1
    t = np.clip((np.arange(h) - y0) / float(max(1, y1 - y0)), 0, 1)[:, None, None]
    col = np.asarray(top, float) * (1 - t) + np.asarray(bottom, float) * t
    rgb[:] = rgb * (1 - m[..., None]) + col * m[..., None]


def side_art(sh, box, game, seed):
    """The cabinet's side: airbrushed art on the paint, a band of the game's colours along it (no words: one side reads
    mirrored). The art is drawn as it stands: the picture's top is the cabinet's top, its left the front on the right side."""
    rgb, ht, gl, _g = sub(sh, box)
    h, w = ht.shape
    G = GAMES[game]
    paint_panel(sh, box, G['body'], seed, gloss=52, chips=0.35, laminate=False)
    line = (16, 14, 18)
    if game == 'a':
        # a sunset band across the top half, the sun sinking into it; under it a great wave curling toward the front
        band = mask(w, h, lambda d, k: d.rectangle((0, k * h * 0.08, k * w, k * h * 0.5), fill=255))
        grad_fill(rgb, band, (40, 30, 80), (250, 150, 80), int(h * 0.08), int(h * 0.5))
        sun = ellipse_mask(w, h, w * 0.6, h * 0.42, w * 0.3, w * 0.3) * band
        grad_fill(rgb, sun, (255, 236, 150), (250, 150, 70), int(h * 0.3), int(h * 0.5))
        for k in range(4):
            yy = int(h * (0.38 + 0.03 * k))
            rgb[yy:yy + int(h * 0.008) + 1] = mix(rgb[yy:yy + int(h * 0.008) + 1], (240, 120, 80), sun[yy:yy + int(h * 0.008) + 1])
        for k, px in enumerate((0.12, 0.2)):        # (palms against the sky)
            for p in palm_shape(w * px, h * 0.5, h * 0.3, lean=0.05 + 0.04 * k, seed=seed + k):
                lay(rgb, shape_mask(w, h, [p]) * band, (30, 22, 40))
        rgb[int(h * 0.5):int(h * 0.51)] = G['trim']
        wave = shape_mask(w, h, [wave_curl(w, h, w * 1.05, h * 1.0, h * 0.42, lean=-1.0)])
        grad_fill(rgb, wave, (40, 170, 180), (10, 60, 90), int(h * 0.55), h)
        rgb[:] = mix(rgb, line, outline_of(wave, 2))
        lip = shape_mask(w, h, [wave_curl(w, h, w * 1.05, h * 0.98, h * 0.38, lean=-1.0)]) * (1 - shape_mask(w, h, [wave_curl(w, h, w * 1.1, h * 1.02, h * 0.36, lean=-1.0)]))
        rgb[:] = mix(rgb, (240, 250, 248), lip * 0.95)
        b, body, head = surfer_shape(w * 0.42, h * 0.74, h * 0.16, -1)
        lay(rgb, shape_mask(w, h, [b]), (240, 70, 60), line, 2)
        lay(rgb, np.clip(shape_mask(w, h, [body]) + ellipse_mask(w, h, head[0], head[1], head[2], head[2]), 0, 1), (30, 24, 28))
    elif game == 'b':
        deep = mask(w, h, lambda d, k: d.rectangle((0, k * h * 0.06, k * w, k * h * 0.94), fill=255))
        grad_fill(rgb, deep, (40, 140, 170), (6, 20, 50), int(h * 0.06), int(h * 0.94))
        for k in range(6):
            x = w * (0.05 + 0.18 * k)
            ray = shape_mask(w, h, [[(x, h * 0.06), (x + w * 0.06, h * 0.06), (x + w * 0.3, h * 0.94), (x + w * 0.2, h * 0.94)]])
            rgb[:] = mix(rgb, (150, 220, 230), ray * deep * 0.14)
        for p in shark_shape(w * 0.55, h * 0.46, w * 1.0, -1):
            m = shape_mask(w, h, [p])
            grad_fill(rgb, m, (150, 162, 176), (226, 226, 220), int(h * 0.36), int(h * 0.56))
            rgb[:] = mix(rgb, line, outline_of(m, 2))
        jaw = shape_mask(w, h, [[(w * 0.55 - w * 0.36, h * 0.48), (w * 0.55 - w * 0.5, h * 0.45), (w * 0.55 - w * 0.4, h * 0.53)]])
        lay(rgb, jaw, (130, 20, 30), line, 1)
        lay(rgb, ellipse_mask(w, h, w * 0.55 - w * 0.3, h * 0.43, w * 0.015, w * 0.015), (8, 8, 10))
        for k in range(12):
            r = w * (0.008 + 0.006 * (k % 3))
            cx, cy = w * (0.12 + 0.02 * (k % 4)), h * (0.4 - 0.025 * k)
            lay(rgb, ellipse_mask(w, h, cx, cy, r, r) * (1 - ellipse_mask(w, h, cx, cy, r * 0.6, r * 0.6)), (210, 244, 250))
        rgb[int(h * 0.94):int(h * 0.96)] = G['trim']
        rgb[int(h * 0.04):int(h * 0.06)] = G['trim']
    else:
        sky = mask(w, h, lambda d, k: d.rectangle((0, k * h * 0.06, k * w, k * h * 0.7), fill=255))
        grad_fill(rgb, sky, (24, 8, 30), (240, 110, 40), int(h * 0.06), int(h * 0.7))
        glowm = np.asarray(Image.fromarray((ellipse_mask(w, h, w * 0.5, h * 0.36, w * 0.5, w * 0.4, ss=2) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(w * 0.15)), float) / 255
        rgb[:] = mix(rgb, (255, 170, 70), glowm * sky * 0.6)
        v = shape_mask(w, h, [volcano_shape(w * 0.5, h * 0.7, w * 1.4, h * 0.3)])
        grad_fill(rgb, v, (70, 36, 34), (24, 14, 16), int(h * 0.4), int(h * 0.7))
        rgb[:] = mix(rgb, line, outline_of(v, 2))
        for k in range(5):
            a = -0.5 + 0.25 * k
            lava = shape_mask(w, h, [[(w * 0.48, h * 0.41), (w * (0.5 + a * 0.6), h * 0.7), (w * (0.53 + a * 0.6), h * 0.7), (w * 0.52, h * 0.41)]]) * v
            grad_fill(rgb, lava, (255, 230, 120), (240, 70, 20), int(h * 0.41), int(h * 0.7))
        for k in range(30):
            rr = random.Random(seed + k)
            cx, cy, r = w * rr.uniform(0.3, 0.7), h * rr.uniform(0.1, 0.36), w * rr.uniform(0.006, 0.014)
            lay(rgb, ellipse_mask(w, h, cx, cy, r, r), (255, 190, 80))
        rgb[int(h * 0.7):int(h * 0.72)] = G['trim']
        road = shape_mask(w, h, [[(w * 0.5, h * 0.72), (w * 0.56, h * 0.72), (w * 1.0, h * 0.96), (w * 0.2, h * 0.96)]])
        lay(rgb, road, (60, 56, 60), line, 2)
    # the paint wears through where hips and hands rub, along the front edge (left of the picture), and is grimy low down
    yy, xx = np.mgrid[0:h, 0:w]
    rub = np.clip(1 - np.abs(yy / float(h) - 0.55) / 0.2, 0, 1) * np.clip(1 - xx / (w * 0.2), 0, 1) * noise(h, w, 10, seed + 8)
    rgb[:] = mix(rgb, tw.mul(G['body'], 0.8), np.clip(rub * 0.7, 0, 1))
    low = np.clip((yy / float(h) - 0.85) / 0.15, 0, 1) * noise(h, w, 16, seed + 9)
    rgb[:] = mix(rgb, (40, 34, 28), low * 0.5)
    ht[:] -= 0.03 * rub


def coin_door(sh, box, seed, lit=(255, 90, 40)):
    """The coin door: black steel, two lit coin slots with their reject buttons, a lock, a sticker saying what to put
    in, scratched round the slots by a thousand tokens."""
    rgb, ht, gl, gw = sub(sh, box)
    h, w = ht.shape
    paint_panel(sh, box, (36, 36, 38), seed, gloss=60, chips=0.2, grime=0.8, under=(120, 116, 110), scuffs=2.0)
    for k, cy in enumerate((0.24, 0.5)):
        lens = mask(w, h, lambda d, kk: d.rounded_rectangle((kk * w * 0.3, kk * h * (cy - 0.07), kk * w * 0.7, kk * h * (cy + 0.07)), radius=kk * 6, fill=255))
        slot = mask(w, h, lambda d, kk: d.rectangle((kk * w * 0.47, kk * h * (cy - 0.05), kk * w * 0.53, kk * h * (cy + 0.05)), fill=255))
        bezel = outline_of(lens, 3)
        rgb[:] = mix(rgb, (190, 194, 198), bezel)
        rgb[:] = mix(rgb, (200, 60, 30), lens)
        rgb[:] = mix(rgb, (12, 8, 8), slot)
        gw[:] += np.asarray(lit, float) * (lens * (1 - slot))[..., None] * 0.9
        gl[:] = np.where(lens > 0.3, 150, gl)
        gl[:] = np.where(bezel > 0.3, 220, gl)
        ht[:] += 0.12 * bezel - 0.2 * slot
        scratch = ellipse_mask(w, h, w * 0.5, h * cy, w * 0.3, h * 0.1) * noise(h, w, 30, seed + k, octaves=2)
        rgb[:] = mix(rgb, (150, 150, 146), np.clip(scratch * 1.4 - 0.4, 0, 1) * (1 - lens))
    lock = ellipse_mask(w, h, w * 0.5, h * 0.72, w * 0.08, w * 0.08)
    rgb[:] = mix(rgb, (200, 190, 150), lock)
    rgb[:] = mix(rgb, (20, 20, 20), ellipse_mask(w, h, w * 0.5, h * 0.72, w * 0.02, w * 0.04))
    ht[:] += 0.15 * lock
    gl[:] = np.where(lock > 0.3, 200, gl)
    st = mask(w, h, lambda d, kk: d.rectangle((kk * w * 0.18, kk * h * 0.82, kk * w * 0.82, kk * h * 0.95), fill=255))
    rgb[:] = mix(rgb, (230, 220, 180), st)
    stamp(rgb, '1 TOKEN', w * 0.5, h * 0.845, h * 0.08, (200, 30, 30), centre=True, wide=w * 0.6)
    gl[:] = np.where(st > 0.3, 20, gl)


def panel_top(sh, box, game, seed):
    """The control panel's top: printed overlay in the game's colours, worn pale round the stick and buttons, burns
    from cigarettes set down on its edge, 1 PLAYER and 2 PLAYERS by the start buttons."""
    rgb, ht, gl, _g = sub(sh, box)
    h, w = ht.shape
    G = GAMES[game]
    paint_panel(sh, box, tw.mul(G['body'], 0.7), seed, gloss=70, chips=0.2, scuffs=2.0, under=(30, 30, 30))
    stripe = mask(w, h, lambda d, k: d.rectangle((0, k * h * 0.78, k * w, k * h * 0.9), fill=255))
    rgb[:] = mix(rgb, G['trim'], stripe)
    for cx, rx in ((0.22, 0.07), (0.6, 0.04), (0.72, 0.04), (0.84, 0.04)):        # (worn pale round the stick and buttons)
        rub = ellipse_mask(w, h, w * cx, h * 0.45, w * rx, h * 0.22, ss=2) * noise(h, w, 16, seed + int(cx * 10))
        rub = np.asarray(Image.fromarray((rub * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3)), float) / 255
        rgb[:] = mix(rgb, tw.mul(G['body'], 1.25), np.clip(rub * 0.8, 0, 0.5))
        gl[:] *= 1 - 0.5 * np.clip(rub, 0, 1)
    rnd = random.Random(seed)
    for _ in range(3):
        bx, by = rnd.uniform(0.05, 0.95) * w, h * rnd.uniform(0.86, 0.97)
        burn = ellipse_mask(w, h, bx, by, w * 0.035, h * 0.07, ss=2)
        rgb[:] = mix(rgb, (30, 20, 16), burn * 0.85)
        ht[:] -= burn * 0.12
    for k, word in enumerate(('1 PLAYER', '2 PLAYERS')):
        stamp(rgb, word, w * (0.27 + 0.42 * k), h * 0.04, h * 0.1, (250, 246, 230), centre=True, wide=w * 0.38)


def bezel(sh, box, game, seed):
    """The screen's bezel: glossy black card printed with how to play, a coloured frame round the screen's window."""
    rgb, ht, gl, _g = sub(sh, box)
    h, w = ht.shape
    G = GAMES[game]
    n = noise(h, w, 8, seed)
    rgb[:] = (18 + 8 * n)[..., None] * np.ones(3)
    win = mask(w, h, lambda d, k: d.rounded_rectangle((k * w * 0.1, k * h * 0.12, k * w * 0.9, k * h * 0.78), radius=k * 18, fill=255))
    frame = outline_of(win, 8)
    rgb[:] = mix(rgb, G['trim'], frame)
    ht[:] += 0.06 * frame
    for k, line in enumerate(('STICK STEERS', 'BUTTON JUMPS')):
        stamp(rgb, line, w * 0.5, h * (0.82 + 0.07 * k), h * 0.045, tuple(G['ink']), centre=True)
    gl[:] = 150


def back_panel(sh, box, seed):
    """The back: plain-painted hardboard, a vent of slots, a printed label and a power cord's grommet, dust."""
    rgb, ht, gl, _g = sub(sh, box)
    h, w = ht.shape
    paint_panel(sh, box, (52, 46, 40), seed, gloss=20, chips=0.3, grime=1.0, under=(110, 86, 60), scuffs=0.5)
    for k in range(9):
        y = h * (0.1 + 0.035 * k)
        vent = mask(w, h, lambda d, kk: d.rounded_rectangle((kk * w * 0.25, kk * y, kk * w * 0.75, kk * (y + h * 0.018)), radius=kk * 3, fill=255))
        rgb[:] = mix(rgb, (8, 8, 8), vent)
        ht[:] -= 0.2 * vent
    lab = mask(w, h, lambda d, k: d.rectangle((k * w * 0.3, k * h * 0.55, k * w * 0.7, k * h * 0.66), fill=255))
    rgb[:] = mix(rgb, (220, 210, 180), lab)
    stamp(rgb, 'KILAUEA', w * 0.5, h * 0.585, h * 0.05, (60, 40, 30), centre=True, wide=w * 0.36)
    grom = ellipse_mask(w, h, w * 0.5, h * 0.85, w * 0.05, w * 0.05)
    rgb[:] = mix(rgb, (14, 14, 14), grom)


# ---------- the arcade cabinet's sheet ----------
# (x0, y0, x1, y1) in pixels of the 1024 sheet
A_MARQUEE = (0, 0, 1024, 256)
A_SCREEN = (0, 256, 512, 640)
A_SIDE = (512, 256, 768, 768)
A_PANEL = (768, 256, 1024, 384)
A_DOOR = (768, 384, 896, 640)
A_BODY = (896, 384, 1024, 512)
A_BLACK = (896, 512, 1024, 640)
A_BEZEL = (0, 640, 512, 1024)
A_BACK = (768, 640, 1024, 1024)
A_CHROME = (512, 896, 768, 1024)
A_BTN = [(512 + 32 * k, 768, 544 + 32 * k, 800) for k in range(8)]       # (button and ball colours)
A_TRIM = (512, 800, 768, 832)
A_KICK = (512, 832, 768, 896)

BUTTONS = [(220, 40, 40), (240, 200, 40), (40, 100, 220), (250, 250, 240), (40, 180, 80), (230, 120, 30), (200, 200, 210), (20, 20, 22)]


def arcade_sheet(game):
    seed = {'a': 3100, 'b': 3200, 'c': 3300}[game]
    G = GAMES[game]
    sh = Sheet()
    paint_panel(sh, A_BODY, G['body'], seed + 1, gloss=50, laminate=True)
    paint_panel(sh, A_BLACK, (24, 24, 26), seed + 2, gloss=40, chips=0.2, under=(80, 80, 80))
    paint_panel(sh, A_TRIM, G['trim'], seed + 3, gloss=120, chips=0.3, grime=0.3)
    rubber(sh, A_KICK, seed + 4, (30, 28, 28))
    chrome(sh, A_CHROME, seed + 5)
    for k, box in enumerate(A_BTN):
        plastic(sh, box, BUTTONS[k], seed + 10 + k, glow=0.0)
    marquee(sh, A_MARQUEE, game, seed + 20)
    screen(sh, A_SCREEN, game, seed + 30)
    side_art(sh, A_SIDE, game, seed + 40)
    panel_top(sh, A_PANEL, game, seed + 50)
    coin_door(sh, A_DOOR, seed + 60)
    bezel(sh, A_BEZEL, game, seed + 70)
    back_panel(sh, A_BACK, seed + 80)
    return sh


_sheets = {}


def _sheet_of(name, fn):
    if name not in _sheets:
        _sheets[name] = fn()
    return _sheets[name]


# ---------- shapes ----------

def _rot(turn):
    rx, ry, rz = (math.radians(a) for a in turn)
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    return ((cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx),
            (sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx),
            (-sy, cy * sx, cy * cx))


class Frame:
    """A turned frame (as modelmake turns a part) at a point: where its own points land."""

    def __init__(self, at, turn=(0, 0, 0)):
        self.at, self.turn, self.R = list(at), list(turn), _rot(turn)

    def p(self, x, y, z):
        R = self.R
        return [round(self.at[i] + R[i][0] * x + R[i][1] * y + R[i][2] * z, 3) for i in range(3)]


def box(P, size, at, look, turn=(0, 0, 0), faces=None, solid=False, material='wood', bevel=None):
    p = {'shape': 'box', 'size': [float(v) for v in size], 'at': [float(v) for v in at], 'look': look, 'solid': solid,
         'material': material}
    if any(turn):
        p['turn'] = list(turn)
    if faces:
        p['faces'] = faces
    if bevel is not None:
        p['bevel'] = bevel
    P.append(p)
    return p


def cyl(P, r, h, at, look, turn=(0, 0, 0), sides=12, r2=None, solid=False):
    p = {'shape': 'cylinder', 'r': r, 'h': h, 'sides': sides, 'at': [float(v) for v in at], 'look': look, 'solid': solid}
    if r2 is not None:
        p['r2'] = r2
    if any(turn):
        p['turn'] = list(turn)
    P.append(p)
    return p


def collide(P, x0, y0, z0, x1, y1, z1, material='wood'):
    """A box of collision alone."""
    P.append({'shape': 'box', 'size': [x1 - x0, y1 - y0, z1 - z0], 'at': [(x0 + x1) / 2.0, (y0 + y1) / 2.0, z0], 'look': None,
              'faces': {f: None for f in ('front', 'back', 'left', 'right', 'top', 'bottom')}, 'solid': True, 'material': material})


# ---------- an upright arcade cabinet ----------
# Front -y, x across, standing on z `foot`. 39 wide (the bank's slots are 40.6 apart at the closest), 122 tall
# (1.75 m), from y -29 (the control panel's lip) to +40 (half way to the bank behind).
CAB_W = 39.0
CAB_BACK = 40.0
CAB_TOP = 121.0
SIDE_T = 1.5


def cabinet(P, game, x=0.0, foot=0.0, looks=None):
    """An upright cabinet's parts into P, its middle at x, standing on z foot. looks: the look names on its sheet."""
    L = looks
    hx = CAB_W / 2
    ix = hx - SIDE_T                                # (inside the side panels)
    z = lambda v: foot + v
    # the body: lower box (coin door on its front), upper box behind the screen and marquee
    box(P, (2 * ix, CAB_BACK + 14, 60), (x, (CAB_BACK - 14) / 2.0, z(0)), L['body'], faces={'front': L['black'], 'back': L['back_low'], 'bottom': L['black']})
    box(P, (2 * ix, CAB_BACK + 8, 58), (x, (CAB_BACK - 8) / 2.0, z(60)), L['black'], faces={'back': L['back_high'], 'top': L['body']})
    # kick plate at the foot, coin door proud of the front
    box(P, (2 * ix, 1.2, 7), (x, -14.4, z(0)), L['kick'])
    box(P, (15, 1.4, 26), (x, -14.6, z(14)), L['black'], faces={'front': L['door']}, bevel=0.4)
    for sx in (-1, 1):                              # (the door's hinges and the token box's handle)
        cyl(P, 0.6, 3, (x + sx * 7.2, -15.4, z(17 + (sx + 1) * 9)), L['chrome'], sides=8)
    # the control panel: a slab sloping up toward the screen, its lip over the front
    pf = Frame((x, -20.0, z(59.5)), (10, 0, 0))
    box(P, (2 * ix + 0.6, 17.5, 5.5), pf.at, L['black'], turn=pf.turn, faces={'top': L['panel']}, bevel=0.8)
    box(P, (2 * ix + 0.8, 1.2, 4.6), pf.p(0, -8.9, 0.4), L['trim'], turn=pf.turn, bevel=0.3)      # (the lip's moulding)
    # the stick: a round plate, a shaft, a ball
    js = pf.p(-9.5, -1.0, 5.5)
    cyl(P, 2.6, 0.5, js, L['chrome'], turn=pf.turn, sides=14)
    cyl(P, 0.55, 5.0, pf.p(-9.5, -1.0, 6.0), L['chrome'], turn=pf.turn, sides=8)
    ball_at = pf.p(-9.5, -1.0, 10.4)
    P.append({'shape': 'ball', 'r': 1.9, 'at': ball_at, 'look': L['btn0'], 'sides': 12, 'rings': 7, 'solid': False})
    # buttons: three big in an arc, two small start buttons near the screen
    for k, (bx, by) in enumerate(((1.0, 1.5), (5.4, 0.4), (9.8, 1.5))):
        cyl(P, 1.9, 0.6, pf.p(bx, by, 5.5), L['black'], turn=pf.turn, sides=14)                   # (its bezel)
        cyl(P, 1.5, 1.3, pf.p(bx, by, 5.6), L['btn%d' % (k + 1)], turn=pf.turn, sides=14)
    for k, bx in enumerate((-4.0, 1.0)):
        cyl(P, 0.9, 0.9, pf.p(bx, 6.5, 5.5), L['btn%d' % (5 + k)], turn=pf.turn, sides=10)
    # the screen: a bezel leaning back, the tube's glass bulging a little in front of it
    bf = Frame((x, -13.0, z(66.5)), (-14, 0, 0))
    box(P, (2 * ix, 2.4, 37), bf.at, L['black'], turn=bf.turn, faces={'front': L['bezel']}, bevel=0.3)
    rows = []
    for j in range(5):
        v = j / 4.0
        row = []
        for i in range(6):
            u = i / 5.0
            bulge = 0.9 * math.sin(math.pi * u) * math.sin(math.pi * v)
            row.append(tuple(bf.p(-13.4 + 26.8 * u, -1.25 - 0.05 - bulge, 33.0 - 22.4 * v)))
        rows.append(row)
    P.append({'shape': 'sheet', 'rows': rows, 'look': L['screen'], 'under_look': L['black'], 'thick': 0.6, 'solid': False})
    # the marquee, lit, in chrome strips, and the cap over it all
    box(P, (2 * ix, 9.5, 14.5), (x, -8.0, z(104.5)), L['black'], faces={'front': L['marquee']}, bevel=0.2)
    box(P, (2 * ix, 1.0, 1.2), (x, -12.9, z(103.6)), L['chrome'], bevel=0.2)
    box(P, (2 * ix, 1.0, 1.2), (x, -12.9, z(118.8)), L['chrome'], bevel=0.2)
    box(P, (CAB_W + 0.4, CAB_BACK + 14.6, 2.2), (x, (CAB_BACK - 14.6) / 2.0, z(CAB_TOP - 1.2)), L['body'], faces={'front': L['trim']}, bevel=0.6)
    # the side panels, shaped as a cabinet's are: the lower box, the wing round the control panel, a cheek beside the
    # screen leaning back with it, the marquee's cheek standing forward again, the back of the upper part; the side art
    # one picture over all of them (each part shows its own piece of it)
    sf = Frame((0, -14.0, z(60.0)), (-14, 0, 0))
    for sx in (-1, 1):
        face = 'right' if sx > 0 else 'left'
        cx = x + sx * (hx - SIDE_T / 2)
        box(P, (SIDE_T, CAB_BACK + 14, 60), (cx, (CAB_BACK - 14) / 2.0, z(0)), L['body'], faces={face: L['side_low_' + face]}, bevel=0.3)
        box(P, (SIDE_T, CAB_BACK + 4, CAB_TOP - 60), (cx, (CAB_BACK - 4) / 2.0, z(60)), L['body'], faces={face: L['side_high_' + face]}, bevel=0.3)
        cf = Frame([cx, sf.at[1], sf.at[2]], sf.turn)
        box(P, (SIDE_T, 12.0, 44.0), cf.p(0, 6.0, 0), L['body'], turn=sf.turn, faces={face: L['side_cheek_' + face]}, bevel=0.3)
        box(P, (SIDE_T, 11.0, CAB_TOP - 102.5), (cx, -8.5, z(102.5)), L['body'], faces={face: L['side_marq_' + face]}, bevel=0.3)
        wf = Frame(pf.p(sx * (hx - SIDE_T / 2), 0, -3.0), (10, 0, 0))
        box(P, (SIDE_T, 18.5, 10.5), wf.at, L['body'], turn=wf.turn, bevel=0.3)
        # T-moulding along every front edge, proud of the panel
        tx = cx
        box(P, (SIDE_T + 0.5, 1.0, 58.0), (tx, -14.3, z(0.5)), L['trim'], bevel=0.25)
        box(P, (SIDE_T + 0.5, 19.0, 1.0), wf.p(0, 0, 10.5), L['trim'], turn=wf.turn, bevel=0.25)
        box(P, (SIDE_T + 0.5, 1.0, 43.0), cf.p(0, -0.3, 0.5), L['trim'], turn=sf.turn, bevel=0.25)
        box(P, (SIDE_T + 0.5, 1.0, CAB_TOP - 102.0), (tx, -14.3, z(102.0)), L['trim'], bevel=0.25)
    # (what stops you: the cabinet's box, and the panel's lip)
    collide(P, x - hx, -14.5, foot, x + hx, CAB_BACK, foot + CAB_TOP + 1)
    collide(P, x - hx, -29.0, foot + 56, x + hx, -14.5, foot + 70)
    return P


def side_regions(sheet_box, face, y0, y1, z0, z1, Y0=-14.0, Y1=CAB_BACK, Z0=0.0, Z1=CAB_TOP, w=S, h=S):
    """The part of the side art (laid over y Y0..Y1, z Z0..Z1 of the cabinet's side) a side box's face shows, as a
    region: right faces read front to back, left faces back to front (as modelmake lays a box's faces)."""
    sx0, sy0, sx1, sy1 = sheet_box
    if face == 'right':
        u0, u1 = (y0 - Y0) / (Y1 - Y0), (y1 - Y0) / (Y1 - Y0)
    else:
        u0, u1 = (Y1 - y1) / (Y1 - Y0), (Y1 - y0) / (Y1 - Y0)
    v0, v1 = (Z1 - z1) / (Z1 - Z0), (Z1 - z0) / (Z1 - Z0)
    px = lambda u: (sx0 + (sx1 - sx0) * u) / float(w)
    py = lambda v: (sy0 + (sy1 - sy0) * v) / float(h)
    return (px(u0), py(v0), px(u1), py(v1))


def arcade_looks(game):
    """The looks of one cabinet's sheet: all one picture with its glow (one shape for the game to draw), chrome and
    plastic shinier (a shape of their own: the gloss is the material's)."""
    name = 'arcade/cab_' + game
    nl = lambda box, **how: dict(modelsets.neon(name, mult=GLOW_MULT, region=_uv(box)), **how)
    L = {'body': 'body', 'black': 'black', 'back_low': 'back_low', 'back_high': 'back_high', 'kick': 'kick', 'door': 'door',
         'chrome': 'chrome', 'panel': 'panel', 'trim': 'trim', 'bezel': 'bezel', 'screen': 'screen', 'marquee': 'marquee'}
    looks = {'body': nl(A_BODY), 'black': nl(A_BLACK), 'kick': nl(A_KICK), 'door': nl(A_DOOR), 'panel': nl(A_PANEL),
             'trim': nl(A_TRIM), 'bezel': nl(A_BEZEL), 'screen': nl(A_SCREEN), 'marquee': nl(A_MARQUEE),
             'back_low': nl((A_BACK[0], A_BACK[1] + 192, A_BACK[2], A_BACK[3])), 'back_high': nl((A_BACK[0], A_BACK[1], A_BACK[2], A_BACK[1] + 192)),
             'chrome': dict(nl(A_CHROME), gloss=80.0)}
    for k in range(8):
        L['btn%d' % k] = 'btn%d' % k
        looks['btn%d' % k] = dict(nl(A_BTN[k]), gloss=80.0)
    for face in ('left', 'right'):
        for part, (y0, y1, z0, z1) in (('low', (-14.0, CAB_BACK, 0.0, 60.0)), ('high', (-4.0, CAB_BACK, 60.0, CAB_TOP)),
                                       ('cheek', (-14.0, -2.0, 60.0, 103.0)), ('marq', (-14.0, -3.0, 102.5, CAB_TOP))):
            key = 'side_%s_%s' % (part, face)
            L[key] = key
            looks[key] = dict(modelsets.neon(name, mult=GLOW_MULT), region=side_regions(A_SIDE, face, y0, y1, z0, z1))
    return L, looks


GLOW_MULT = 3.0


def _uv(box, w=S, h=S):
    x0, y0, x1, y1 = box
    return (x0 / float(w), y0 / float(h), x1 / float(w), y1 / float(h))


def arcade_cabinet(game, lift=0.0):
    """One cabinet as a piece: standing on z -lift (a single in a bank's end slot stands 49 over the floor)."""
    L, looks = arcade_looks(game)
    P = cabinet([], game, 0.0, -lift, L)
    return {'name': 'FOLabArcade' + {'a': 'SurfRider', 'b': 'SharkAttack', 'c': 'VolcanoRun'}[game] + ('' if not lift else 'Single'),
            'looks': looks, 'parts': P}


modelsets.TEXTURES.update({
    'arcade/cab_a': lambda: arcade_sheet('a').picture(),
    'arcade/cab_b': lambda: arcade_sheet('b').picture(),
    'arcade/cab_c': lambda: arcade_sheet('c').picture(),
})


# ---------- pachinko ----------
# A machine of the sixties and seventies as Japanese Hawaiʻi played them: a lacquered wooden case, a lit header, the
# playfield behind glass (a printed board, brass pins in their rows round a chrome guide rail, tulip pockets, a centre
# piece with lamps, a windmill or two), a chrome tray of steel balls under it and the firing handle at the lower right.
# Front -y, standing on z 0 (the counter's top), 39 wide (a slot), 62 high (88 cm), y -13 (the tray's lip) to +12.

PA_W, PA_H = 39.0, 62.0
PA_FRONT = -3.0                         # (the frame's face)
PA_BOARD = -1.2                         # (the playfield's face, behind the glass)
PA_WIN = (-16.0, 13.0, 16.0, 52.5)      # (the window onto the playfield: x0, z0, x1, z1)

P_FACE = (0, 0, 640, 1024)              # (the machine's whole front, drawn as one: x -19.5..19.5, z 0..62)
P_WOOD = (640, 0, 1024, 256)
P_CHROME = (640, 256, 1024, 384)
P_BALLS = (640, 384, 1024, 512)
P_COUNTER = (640, 512, 1024, 640)
P_TOP = (640, 640, 1024, 704)
P_BLACK = (640, 704, 768, 832)
P_LAMP = (768, 704, 896, 832)
P_BRASS = (896, 704, 1024, 832)
P_RED = (640, 832, 768, 960)
P_FEATURE = (768, 832, 1024, 960)
P_KICK = (640, 960, 1024, 1024)

BOARDS = {
    'a': {'title': 'PACHINKO', 'name': 'LUCKY KOI', 'case': (150, 34, 28), 'board': [(20, 60, 120), (30, 110, 160), (60, 160, 170)],
          'ink': (255, 214, 90), 'header': (30, 20, 18), 'lamp': (255, 70, 50)},
    'b': {'title': 'PACHINKO', 'name': 'SAKURA', 'case': (40, 36, 34), 'board': [(250, 214, 220), (240, 160, 170), (190, 90, 120)],
          'ink': (255, 240, 220), 'header': (130, 20, 40), 'lamp': (255, 200, 60)},
}


def pins(w, h, seed, keep_out):
    """Where the pins stand, as a pachinko board lays them: arcs of pins down from the top, staggered rows over the
    field, sweeps down the sides toward the out hole; keep_out (cx, cy, r) left clear."""
    rnd = random.Random(seed)
    out = []
    cx = w / 2.0

    def ok(x, y):
        if x < w * 0.06 or x > w * 0.94 or y < h * 0.05 or y > h * 0.96:
            return False
        if math.hypot((x - cx) / (w * 0.47), (y - h * 0.52) / (h * 0.5)) > 0.96:
            return False
        return all(math.hypot(x - a, y - b) > r for a, b, r in keep_out)
    for row in range(5):                                # (the top arcs, under the rail)
        r = w * (0.4 - 0.05 * row)
        n = 18 - 2 * row
        for k in range(n):
            a = math.pi * (0.15 + 0.7 * k / (n - 1))
            out.append((cx - r * math.cos(a), h * 0.47 - r * math.sin(a) * 0.95 + row * 2))
    for row in range(16):                               # (the field: staggered rows)
        y = h * (0.3 + 0.042 * row)
        step = w * 0.07
        off = step / 2 if row % 2 else 0
        for k in range(16):
            x = w * 0.08 + off + k * step
            if abs(x - cx) < w * 0.12 and row < 8 and rnd.random() < 0.6:
                continue
            out.append((x + rnd.uniform(-1, 1), y + rnd.uniform(-1, 1)))
    for side in (-1, 1):                                # (the sweeps toward the bottom)
        for k in range(10):
            t = k / 9.0
            out.append((cx + side * w * (0.42 - 0.3 * t), h * (0.78 + 0.14 * t)))
    return [(x, y) for x, y in out if ok(x, y)]


def playfield(sh, box, kind, seed):
    """The board under the glass: printed art, the chrome guide rail round it, brass pins with their shadows, the
    pockets' gold rims, the out hole."""
    rgb, ht, gl, gw = sub(sh, box)
    h, w = ht.shape
    B = BOARDS[kind]
    rgb[:] = gradient(h, w, B['board'])
    rnd = random.Random(seed)
    if kind == 'a':                                     # (koi round a lotus pond)
        for k in range(14):
            cx, cy, r = rnd.uniform(0.1, 0.9) * w, rnd.uniform(0.15, 0.95) * h, rnd.uniform(0.04, 0.08) * w
            pad = ellipse_mask(w, h, cx, cy, r, r * 0.8) * (1 - shape_mask(w, h, [[(cx, cy), (cx + r * 1.2, cy - r * 0.3), (cx + r * 1.2, cy + r * 0.2)]]))
            lay(rgb, pad, (60, 130, 70), (20, 50, 30), 1)
        for k in range(5):
            cx, cy, s, f = rnd.uniform(0.2, 0.8) * w, rnd.uniform(0.25, 0.9) * h, rnd.uniform(0.12, 0.2) * w, rnd.choice((-1, 1))
            body = [(cx - s * 0.5 * f, cy), (cx - s * 0.2 * f, cy - s * 0.16), (cx + s * 0.3 * f, cy - s * 0.1), (cx + s * 0.5 * f, cy),
                    (cx + s * 0.3 * f, cy + s * 0.1), (cx - s * 0.2 * f, cy + s * 0.14)]
            tail = [(cx - s * 0.45 * f, cy), (cx - s * 0.75 * f, cy - s * 0.2), (cx - s * 0.65 * f, cy), (cx - s * 0.75 * f, cy + s * 0.2)]
            col = rnd.choice([(250, 120, 40), (250, 250, 240), (240, 200, 60)])
            m = shape_mask(w, h, [body, tail])
            lay(rgb, m, col, (40, 20, 20), 1)
            spots = ellipse_mask(w, h, cx + s * 0.05 * f, cy - s * 0.04, s * 0.12, s * 0.06) * m
            rgb[:] = mix(rgb, (220, 40, 30), spots)
        lotus = ellipse_mask(w, h, w * 0.5, h * 0.88, w * 0.12, h * 0.04)
        lay(rgb, lotus, (250, 170, 200), (120, 40, 70), 2)
    else:                                               # (blossom over a red bridge, the sun on the sea)
        sun = ellipse_mask(w, h, w * 0.5, h * 0.62, w * 0.28, w * 0.28)
        lay(rgb, sun, (240, 60, 70))
        sea = mask(w, h, lambda d, k: d.rectangle((0, k * h * 0.7, k * w, k * h), fill=255))
        grad_fill(rgb, sea, (60, 120, 170), (20, 50, 100), int(h * 0.7), h)
        for k in range(6):
            yy = h * (0.73 + 0.04 * k)
            xs = np.arange(-w * 0.05, w * 1.05, w * 0.12) + (k % 2) * w * 0.06
            wv = mask(w, h, lambda d, kk: [d.arc((kk * (x - w * 0.06), kk * (yy - h * 0.012), kk * (x + w * 0.06), kk * (yy + h * 0.012)), 180, 360, fill=255, width=kk * 2) for x in xs])
            rgb[:] = mix(rgb, (230, 240, 250), wv * 0.8)
        bridge = mask(w, h, lambda d, k: d.arc((k * w * 0.1, k * h * 0.56, k * w * 0.9, k * h * 0.86), 180, 360, fill=255, width=k * 10))
        lay(rgb, bridge, (200, 40, 40), (40, 10, 10), 1)
        for k in range(4):                              # (branches)
            pts = [(0 if k < 2 else w, h * (0.08 + 0.12 * k))]
            for j in range(6):
                px, py = pts[-1]
                pts.append((px + (1 if k < 2 else -1) * w * 0.07, py + rnd.uniform(-1, 1) * h * 0.02))
            br = mask(w, h, lambda d, kk: d.line(poly(pts, kk), fill=255, width=kk * 4))
            rgb[:] = mix(rgb, (70, 40, 34), br)
        for k in range(60):
            cx, cy, r = rnd.uniform(0, 1) * w, rnd.uniform(0, 0.55) * h, rnd.uniform(0.012, 0.03) * w
            petal = ellipse_mask(w, h, cx, cy, r, r)
            lay(rgb, petal, (255, 230, 236) if k % 3 else (250, 180, 200), (190, 90, 120) if k % 5 == 0 else None, 1)
    # the guide rail: a chrome band round the field, open at its lower left where the balls come up
    yy, xx = np.mgrid[0:h, 0:w]
    rr = np.hypot((xx - w / 2.0) / (w * 0.48), (yy - h * 0.52) / (h * 0.5))
    rail = np.clip(1 - np.abs(rr - 0.985) / 0.018, 0, 1)
    rail[(yy > h * 0.8) & (xx < w * 0.5)] *= 0
    outside = np.clip((rr - 1.0) * 40, 0, 1)
    rgb[:] = mix(rgb, tw.mul(B['board'][0], 0.6), outside)
    rgb[:] = mix(rgb, (220, 226, 230), rail)
    ht[:] = 0.5 + 0.25 * rail
    gl[:] = np.where(rail > 0.3, 230, 120)
    # the pins (the centre piece, pockets and windmills are the model's, their places kept clear)
    keep = [(w * 0.5, h * 0.42, w * 0.17), (w * 0.5, h * 0.76, w * 0.07), (w * 0.26, h * 0.64, w * 0.06), (w * 0.74, h * 0.64, w * 0.06),
            (w * 0.2, h * 0.4, w * 0.05), (w * 0.8, h * 0.4, w * 0.05), (w * 0.5, h * 0.94, w * 0.07)]
    pp = pins(w, h, seed + 1, keep)
    shadow = mask(w, h, lambda d, k: [d.ellipse((k * (x + 1), k * (y + 1), k * (x + 5), k * (y + 5)), fill=255) for x, y in pp])
    rgb[:] = mix(rgb, (10, 10, 20), shadow * 0.55)
    head = mask(w, h, lambda d, k: [d.ellipse((k * (x - 2.2), k * (y - 2.2), k * (x + 2.2), k * (y + 2.2)), fill=255) for x, y in pp])
    shine = mask(w, h, lambda d, k: [d.ellipse((k * (x - 1.4), k * (y - 1.4), k * (x + 0.2), k * (y + 0.2)), fill=255) for x, y in pp])
    rgb[:] = mix(rgb, (190, 150, 70), head)
    rgb[:] = mix(rgb, (255, 236, 180), shine * 0.9)
    ht[:] += 0.4 * head
    gl[:] = np.where(head > 0.3, 210, gl)
    out_hole = ellipse_mask(w, h, w * 0.5, h * 0.95, w * 0.06, h * 0.022)
    lay(rgb, out_hole, (10, 10, 10), (200, 200, 200), 2)
    stamp(rgb, 'OUT', w * 0.5, h * 0.905, h * 0.025, (250, 250, 250), centre=True)
    for cx, cy in ((0.26, 0.64), (0.74, 0.64), (0.5, 0.76)):       # (gold rims printed under each pocket)
        rim = ellipse_mask(w, h, w * cx, h * cy + h * 0.02, w * 0.055, h * 0.015)
        lay(rgb, rim, (230, 190, 80), (60, 40, 20), 1)
    rgb[:] = mix(rgb, (200, 190, 170), np.clip(outside * noise(h, w, 10, seed + 7) * 0.4, 0, 1))


def wood_lacquer(sh, box, colour, seed, gloss=90):
    """Lacquered wood: grain under a coloured lacquer, the lacquer rubbed thin on the edges and crazed."""
    rgb, ht, gl, _g = sub(sh, box)
    h, w = ht.shape
    paint_panel(sh, box, colour, seed, gloss=gloss, chips=0.25, grime=0.5, under=(120, 80, 44), scuffs=0.6)
    g = noise(h, max(2, w // 6), 4, seed + 4, octaves=4)
    g = np.asarray(Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), float) / 255
    grain = 0.5 + 0.5 * np.sin(g * 60.0)
    rgb[:] = rgb * (0.86 + 0.18 * grain[..., None])
    ht[:] += 0.03 * (grain - 0.5)


def face(sh, box, kind, seed):
    """The machine's front as one picture: the header (dark, the name in lit tubes, lamps along it), the frame's
    stiles in the case's lacquer with a chrome bead round the window, the lower panel behind the trays with the
    board's name on a plate; the window shows the playfield (drawn there too)."""
    rgb, ht, gl, gw = sub(sh, box)
    h, w = ht.shape
    B = BOARDS[kind]
    wood_lacquer(sh, box, B['case'], seed)
    fx = lambda x: (x + PA_W / 2) / PA_W * w
    fz = lambda z: (PA_H - z) / PA_H * h
    hd = mask(w, h, lambda d, k: d.rectangle((k * fx(-18), k * fz(61.4), k * fx(18), k * fz(54.0)), fill=255))
    rgb[:] = mix(rgb, B['header'], hd)
    gl[:] = np.where(hd > 0.5, 140, gl)
    import signpaint as sp
    hx0, hy0, hx1, hy1 = fx(-14), fz(61.0), fx(14), fz(54.6)
    m, thick = sp.letters(B['title'], 'tube', (hx0, hy0 + (hy1 - hy0) * 0.08, hx1, hy1 - (hy1 - hy0) * 0.1), w, h)
    ink = np.clip(np.array(m['ink'].v, float).reshape(h, w), 0, 1)
    core = np.clip(np.array(m['core'].v, float).reshape(h, w), 0, 1)
    halo = np.asarray(Image.fromarray((ink * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(4)), float) / 255
    tube = np.asarray(B['ink'], float)
    rgb[:] = mix(rgb, mix(np.broadcast_to(tube * 0.8, rgb.shape), (255, 255, 250), core), ink)
    gw[:] += tube * (ink * 0.9 + halo * 0.35)[..., None] + 255 * core[..., None] * 0.3
    ht[:] += 0.15 * ink
    for k in range(9):                                  # (lamps along the header's foot, every other one lit)
        lx, lz = fx(-16 + 4 * k), fz(54.7)
        lamp = ellipse_mask(w, h, lx, lz, w * 0.011, w * 0.011)
        rgb[:] = mix(rgb, B['lamp'], lamp)
        gw[:] += np.asarray(B['lamp'], float) * lamp[..., None] * (1.0 if k % 2 else 0.35)
    wx0, wz0, wx1, wz1 = PA_WIN
    surround = mask(w, h, lambda d, k: d.rectangle((k * fx(wx0 - 1.6), k * fz(wz1 + 1.6), k * fx(wx1 + 1.6), k * fz(wz0 - 1.6)), fill=255))
    inner = mask(w, h, lambda d, k: d.rectangle((k * fx(wx0), k * fz(wz1), k * fx(wx1), k * fz(wz0)), fill=255))
    bead = np.clip(surround - inner, 0, 1)
    rgb[:] = mix(rgb, (214, 218, 222), bead)
    ht[:] += 0.2 * bead
    gl[:] = np.where(bead > 0.5, 230, gl)
    lp = mask(w, h, lambda d, k: d.rectangle((k * fx(-18), k * fz(11.5), k * fx(18), k * fz(1.0)), fill=255))
    rgb[:] = mix(rgb, tw.mul(B['case'], 0.55), lp)
    plate = mask(w, h, lambda d, k: d.rounded_rectangle((k * fx(-9), k * fz(10.8), k * fx(9), k * fz(8.2)), radius=k * 4, fill=255))
    rgb[:] = mix(rgb, (200, 196, 180), plate)
    gl[:] = np.where(plate > 0.5, 200, gl)
    stamp(rgb, B['name'], fx(0), fz(10.5), (fz(8.2) - fz(10.8)) * 0.6, (60, 30, 20), centre=True, wide=(fx(9) - fx(-9)) * 0.9)
    sub_box = (int(box[0] + fx(wx0)), int(box[1] + fz(wz1)), int(box[0] + fx(wx1)), int(box[1] + fz(wz0)))
    playfield(sh, sub_box, kind, seed + 50)
    return sub_box


def ball_heap(sh, box, seed):
    """A tray full of steel balls seen from above: balls packed in rows, each with its highlight and a dark gap round
    it, some dull with handling."""
    rgb, ht, gl, _g = sub(sh, box)
    h, w = ht.shape
    rgb[:] = (40, 40, 44)
    ht[:] = 0.3
    gl[:] = 60
    rnd = random.Random(seed)
    r = 9.0
    yy, xx = np.mgrid[0:h, 0:w]
    for j, y in enumerate(np.arange(r, h + r, r * 1.73)):
        for x in np.arange(r if j % 2 == 0 else r * 2, w + r, r * 2):
            cx, cy = x + rnd.uniform(-1, 1), y + rnd.uniform(-1, 1)
            y0, y1, x0, x1 = max(0, int(cy - r - 1)), min(h, int(cy + r + 2)), max(0, int(cx - r - 1)), min(w, int(cx + r + 2))
            if y0 >= y1 or x0 >= x1:
                continue
            Y, X = yy[y0:y1, x0:x1], xx[y0:y1, x0:x1]
            d = np.hypot(X - cx, Y - cy) / r
            m = d < 1
            tone = rnd.uniform(0.75, 1.0)
            col = (150 + 90 * np.sqrt(np.clip(1 - d, 0, 1))) * tone
            hl = np.exp(-(((X - cx + r * 0.35) / (r * 0.25)) ** 2 + ((Y - cy + r * 0.35) / (r * 0.25)) ** 2))
            reg = rgb[y0:y1, x0:x1]
            reg[m] = (np.stack([col, col, col * 1.02], -1) + 80 * hl[..., None])[m]
            hreg = ht[y0:y1, x0:x1]
            hreg[m] = np.maximum(hreg[m], (0.3 + 0.6 * np.sqrt(np.clip(1 - d ** 2, 0, 1)))[m])
            gl[y0:y1, x0:x1][m] = 240
    rgb[:] = np.clip(rgb, 0, 255)


def counter_front(sh, box, seed, case):
    """The counter under a pachinko bank: lacquered panels, a token slot and lit sign under each machine, a brass kick
    plate scuffed by shoes."""
    rgb, ht, gl, gw = sub(sh, box)
    h, w = ht.shape
    wood_lacquer(sh, box, case, seed, gloss=80)
    for k, cx in enumerate((-61.6, -21.0, 23.0, 69.0)):     # (the bank's four slots across its 174)
        px = (cx + 87.1) / 174.2 * w
        panel = mask(w, h, lambda d, kk: d.rounded_rectangle((kk * (px - w * 0.1), kk * h * 0.12, kk * (px + w * 0.1), kk * h * 0.7), radius=kk * 4, fill=255))
        rgb[:] = mix(rgb, tw.mul(case, 0.6), outline_of(panel, 2))
        ht[:] -= 0.06 * outline_of(panel, 2)
        sign = mask(w, h, lambda d, kk: d.rounded_rectangle((kk * (px - w * 0.04), kk * h * 0.18, kk * (px + w * 0.04), kk * h * 0.3), radius=kk * 2, fill=255))
        rgb[:] = mix(rgb, (250, 220, 140), sign)
        gw[:] += np.asarray((255, 200, 110), float) * sign[..., None] * 0.8
        slot = mask(w, h, lambda d, kk: d.rectangle((kk * (px - w * 0.012), kk * h * 0.38, kk * (px + w * 0.012), kk * h * 0.52), fill=255))
        rgb[:] = mix(rgb, (200, 200, 196), outline_of(slot, 2))
        rgb[:] = mix(rgb, (8, 8, 8), slot)
    kick = mask(w, h, lambda d, k: d.rectangle((0, k * h * 0.82, k * w, k * h), fill=255))
    rgb[:] = mix(rgb, (180, 140, 70), kick)
    scuff = kick * noise(h, w, 30, seed + 3, octaves=2)
    rgb[:] = mix(rgb, (110, 86, 50), np.clip(scuff * 1.5 - 0.5, 0, 1))
    gl[:] = np.where(kick > 0.5, 180, gl)


def feature(sh, box, kind, seed):
    """The centre piece's face: gold plastic moulding round a lamp-lit window with the board's emblem, lamps round it."""
    rgb, ht, gl, gw = sub(sh, box)
    h, w = ht.shape
    B = BOARDS[kind]
    rgb[:] = gradient(h, w, [(250, 220, 120), (200, 140, 40), (150, 90, 20)])
    win = ellipse_mask(w, h, w * 0.5, h * 0.5, w * 0.32, h * 0.36)
    rgb[:] = mix(rgb, B['lamp'], win)
    emblem = ellipse_mask(w, h, w * 0.5, h * 0.5, w * 0.16, h * 0.2)
    rgb[:] = mix(rgb, (255, 250, 230), emblem)
    gw[:] += np.asarray(B['lamp'], float) * win[..., None] * 0.9 + 200 * emblem[..., None]
    for k in range(8):
        a = 2 * math.pi * k / 8
        lamp = ellipse_mask(w, h, w * (0.5 + 0.42 * math.cos(a)), h * (0.5 + 0.42 * math.sin(a)), w * 0.04, w * 0.04)
        rgb[:] = mix(rgb, (255, 250, 200), lamp)
        gw[:] += 230 * lamp[..., None]
    ht[:] = 0.5 + 0.2 * (1 - win)
    gl[:] = 200


def pachinko_sheet(kind):
    seed = {'a': 4100, 'b': 4200}[kind]
    B = BOARDS[kind]
    sh = Sheet()
    face(sh, P_FACE, kind, seed)
    wood_lacquer(sh, P_WOOD, B['case'], seed + 1)
    chrome(sh, P_CHROME, seed + 2)
    ball_heap(sh, P_BALLS, seed + 3)
    counter_front(sh, P_COUNTER, seed + 4, (110, 24, 20))
    wood_lacquer(sh, P_TOP, (60, 36, 24), seed + 5, gloss=110)
    rubber(sh, P_BLACK, seed + 6, (24, 22, 22))
    plastic(sh, P_LAMP, B['lamp'], seed + 7, glow=0.9)
    chrome(sh, P_BRASS, seed + 8, tint=(214, 174, 90), pitted=0.2)
    plastic(sh, P_RED, (220, 40, 50), seed + 9)
    feature(sh, P_FEATURE, kind, seed + 10)
    rubber(sh, P_KICK, seed + 11, (30, 26, 24))
    return sh


def pachinko_glass(size=128, seed=4900):
    """The playfield's glass: nearly clear, a sheen across it and a little grime at its edges (blended)."""
    sh = Sheet(size, size)
    yy, xx = np.mgrid[0:size, 0:size]
    n = noise(size, size, 4, seed)
    streak = np.exp(-((xx / float(size) - 0.25 - yy / float(size) * 0.5) / 0.05) ** 2) + 0.6 * np.exp(-((xx / float(size) - 0.45 - yy / float(size) * 0.5) / 0.02) ** 2)
    edge = np.clip(1 - np.minimum(np.minimum(xx, size - 1 - xx), np.minimum(yy, size - 1 - yy)) / (size * 0.12), 0, 1)
    sh.rgb[:] = mix(np.full((size, size, 3), (210, 226, 230), float), (150, 140, 120), edge * 0.6)
    sh.a = np.clip(0.06 + 0.18 * streak + 0.12 * edge * n, 0, 0.4)
    sh.gloss[:] = 250
    pic = sh.picture()
    pic.plain_halving = True
    return pic


def pachinko_looks(kind):
    name = 'arcade/pachi_' + kind
    nl = lambda box, **how: dict(modelsets.neon(name, mult=GLOW_MULT, region=_uv(box)), **how)
    looks = {k: nl(b) for k, b in (('wood', P_WOOD), ('balls', P_BALLS), ('counter', P_COUNTER), ('top', P_TOP), ('black', P_BLACK),
                                   ('lamp', P_LAMP), ('red', P_RED), ('feature', P_FEATURE), ('kick', P_KICK))}
    looks['chrome'] = dict(nl(P_CHROME), gloss=80.0)
    looks['brass'] = dict(nl(P_BRASS), gloss=80.0)
    looks['glass'] = dict(modelsets.look('arcade/pachi_glass'), alpha='blend', gloss=90.0)
    return looks


def face_region(x0, z0, x1, z1):
    """The face picture's part over the machine's (x0..x1, z0..z1) front."""
    fx0, fy0, fx1, fy1 = P_FACE
    px = lambda x: (fx0 + (x + PA_W / 2) / PA_W * (fx1 - fx0)) / S
    py = lambda z: (fy0 + (PA_H - z) / PA_H * (fy1 - fy0)) / S
    return (px(x0), py(z1), px(x1), py(z0))


def pachinko(P, looks, kind, x=0.0, foot=0.0):
    """A machine's parts into P, its middle at x, standing on z foot."""
    name = 'arcade/pachi_' + kind
    z = lambda v: foot + v
    hx = PA_W / 2

    def fl(x0, z0, x1, z1):                             # (a look showing the face picture over that part of the front)
        key = 'face%s_%d_%d_%d_%d' % (kind, round(x0 * 10), round(z0 * 10), round(x1 * 10), round(z1 * 10))
        looks[key] = dict(modelsets.neon(name, mult=GLOW_MULT), region=face_region(x0, z0, x1, z1))
        return key
    wx0, wz0, wx1, wz1 = PA_WIN
    # the case, behind everything, its sides and top lacquered wood
    box(P, (PA_W, 12.0, PA_H), (x, 6.0, z(0)), 'wood', faces={'front': fl(-hx, 0, hx, PA_H)})
    # the frame round the window, standing proud of the board: header, stiles, the lower panel
    for (x0, z0, x1, z1) in ((-hx, wz1, hx, PA_H), (-hx, wz0, wx0, wz1), (wx1, wz0, hx, wz1), (-hx, 0.0, hx, wz0)):
        box(P, (x1 - x0, 1.8, z1 - z0), (x + (x0 + x1) / 2, PA_FRONT + 0.9, z(z0)), 'wood', faces={'front': fl(x0, z0, x1, z1)}, bevel=0.35)
    # the playfield, recessed behind the frame's face
    box(P, (wx1 - wx0, 1.0, wz1 - wz0), (x + (wx0 + wx1) / 2, PA_BOARD + 0.5, z(wz0)), 'wood', faces={'front': fl(wx0, wz0, wx1, wz1)}, bevel=0.0)
    # on it: the centre piece (gold moulding, lamps), tulip pockets, windmills, steel balls among the pins
    fw, fh = 9.0, 8.0
    cz = wz0 + (wz1 - wz0) * (1 - 0.42)
    box(P, (fw, 2.2, fh), (x, PA_BOARD - 1.1, z(cz - fh / 2)), 'brass', faces={'front': 'feature'}, bevel=0.6)
    cyl(P, 1.0, 1.2, (x, PA_BOARD - 1.1, z(cz + fh / 2)), 'lamp', sides=10)
    for px, pz in ((-0.24, 0.36), (0.24, 0.36), (0.0, 0.24)):
        tx, tz = x + px * (wx1 - wx0), z(wz0 + (wz1 - wz0) * pz)
        cyl(P, 1.4, 1.2, (tx, PA_BOARD, tz), 'red', turn=(90, 0, 0), r2=1.0, sides=10)            # (the tulip's cup)
        cyl(P, 0.5, 2.0, (tx - 1.1, PA_BOARD - 0.5, tz + 0.2), 'red', turn=(0, -28, 0), sides=6)   # (its two petals)
        cyl(P, 0.5, 2.0, (tx + 1.1, PA_BOARD - 0.5, tz + 0.2), 'red', turn=(0, 28, 0), sides=6)
    for px in (-0.3, 0.3):
        wxp, wzp = x + px * (wx1 - wx0), z(wz0 + (wz1 - wz0) * 0.6)
        cyl(P, 1.5, 0.4, (wxp, PA_BOARD, wzp), 'brass', turn=(90, 0, 0), sides=6)                 # (the windmill's star)
        cyl(P, 0.35, 0.8, (wxp, PA_BOARD - 0.2, wzp), 'chrome', turn=(90, 0, 0), sides=6)
    rnd = random.Random(7 if kind == 'a' else 9)
    for k in range(6):
        bx = x + rnd.uniform(wx0 + 3, wx1 - 3)
        bz = z(rnd.uniform(wz0 + 3, wz1 - 6))
        P.append({'shape': 'ball', 'r': 0.6, 'at': [bx, PA_BOARD - 0.6, bz], 'look': 'chrome', 'sides': 8, 'rings': 5, 'solid': False})
    # the glass over the window
    box(P, (wx1 - wx0 + 0.6, 0.3, wz1 - wz0 + 0.6), (x + (wx0 + wx1) / 2, PA_FRONT + 0.3, z(wz0 - 0.3)), 'glass', bevel=0.0)
    # the trays: the upper one (balls to play) bulging out with a rolled lip, the lower one (winnings) under it
    box(P, (32.0, 9.0, 4.0), (x - 1.0, PA_FRONT - 4.5, z(7.2)), 'chrome', faces={'top': 'balls'}, bevel=1.2)
    box(P, (33.0, 1.4, 1.4), (x - 1.0, PA_FRONT - 9.0, z(10.6)), 'chrome', bevel=0.5)
    for k in range(9):                                  # (a few balls standing proud of the heap)
        P.append({'shape': 'ball', 'r': 0.65, 'at': [x - 14 + 3.3 * k, PA_FRONT - 4.5 + (k % 3 - 1) * 1.6, z(10.9)], 'look': 'chrome',
                  'sides': 8, 'rings': 5, 'solid': False})
    box(P, (24.0, 7.0, 3.0), (x - 4.0, PA_FRONT - 3.5, z(1.2)), 'chrome', faces={'top': 'balls'}, bevel=0.9)
    # the firing handle at the lower right: a black knob on a chrome boss, its lever
    cyl(P, 1.6, 2.0, (x + 15.0, PA_FRONT, z(4.8)), 'chrome', turn=(90, 0, 0), sides=12)
    cyl(P, 2.6, 2.4, (x + 15.0, PA_FRONT - 2.0, z(4.8)), 'black', turn=(90, 0, 0), sides=14)
    cyl(P, 0.5, 3.0, (x + 13.5, PA_FRONT - 4.0, z(4.8)), 'chrome', turn=(0, 90, 0), sides=6)
    # the call lamp on top
    cyl(P, 2.2, 1.0, (x, 6.0, z(PA_H)), 'black', sides=12)
    cyl(P, 1.8, 3.0, (x, 6.0, z(PA_H + 1.0)), 'lamp', sides=12, r2=1.6)
    collide(P, x - hx, PA_FRONT - 9.5, foot, x + hx, 12.0, foot + PA_H + 4)
    return P


def pachinko_machine(kind):
    """One machine as a piece: on the counter (a bank's end slot)."""
    looks = pachinko_looks(kind)
    P = pachinko([], looks, kind)
    return {'name': 'FOLabPachinko' + {'a': 'LuckyKoi', 'b': 'Sakura'}[kind], 'looks': looks, 'parts': P}


modelsets.TEXTURES.update({
    'arcade/pachi_a': lambda: pachinko_sheet('a').picture(),
    'arcade/pachi_b': lambda: pachinko_sheet('b').picture(),
    'arcade/pachi_glass': pachinko_glass,
})


# ---------- the banks (in the frame of the Tops' SlotMachineTableCluster06) ----------
# The cluster: a counter x -87.1..87.1, y -19.1..19.1, 49.3 high, its machines at x -21.0 and +22.9; the singles the
# Kilauea stood on its end slots at x -61.6 and +69.0 (the step stands them exactly there: same refs). Back to back
# in pairs 87 apart, so a bank may reach y +43.5 behind (half way to the other's middle).
SLOTS = (-61.6, -21.0, 22.9, 69.0)
COUNTER_H = 49.3
SPINE = 43.4


def pachinko_bank(kinds=('a', 'b'), left=None):
    """A pachinko island's half: the lacquered counter with ashtrays on its ledge, the machines on it, a spine behind
    them up to the lamp strip along the island's top (it meets the spine of the bank behind)."""
    name = 'arcade/pachi_' + kinds[0]
    looks = pachinko_looks(kinds[0])
    nl = lambda b: dict(modelsets.neon(name, mult=GLOW_MULT, region=_uv(b)))
    looks['counter_front'] = nl(P_COUNTER)
    P = []
    # the counter: front panels, a wooden top a little proud, a kick at the foot
    box(P, (174.2, 38.2, COUNTER_H - 2.0), (0, 0, 0), 'wood', faces={'front': 'counter_front', 'top': 'top'}, bevel=0.0)
    box(P, (176.0, 40.0, 2.2), (0, 0, COUNTER_H - 2.2), 'top', bevel=0.6)
    box(P, (173.0, 1.0, 5.0), (0, -19.4, 0), 'kick', bevel=0.3)
    # the spine behind the machines, up past them, the lamp strip on top
    top = COUNTER_H + PA_H + 6.0
    box(P, (174.2, SPINE - 12.0, top - COUNTER_H), (0, (12.0 + SPINE) / 2.0, COUNTER_H), 'wood', bevel=0.0)
    box(P, (176.0, SPINE - 6.0, 4.0), (0, (6.0 + SPINE) / 2.0, top), 'wood', faces={'front': 'lamp'}, bevel=0.8)   # (to the island's middle line: the cap behind meets it)
    box(P, (176.0, 2.0, 1.2), (0, 5.0, top + 4.0), 'chrome', bevel=0.4)
    # machines on the counter
    slots = [(SLOTS[1], kinds[0]), (SLOTS[2], kinds[1 % len(kinds)])]
    if left:
        slots.insert(0, (SLOTS[0], left))
    for x, k in slots:
        if k != kinds[0]:
            for nm, lk in pachinko_looks(k).items():
                looks[nm + '_' + k] = lk
            sub_looks = {nm: nm + '_' + k for nm in pachinko_looks(k)}
            Q = pachinko([], looks, k, x, COUNTER_H)
            for p in Q:                                 # (the other board's looks)
                if p.get('look') in sub_looks:
                    p['look'] = sub_looks[p['look']]
                if p.get('faces'):
                    p['faces'] = {f: sub_looks.get(v, v) for f, v in p['faces'].items()}
            P += Q
        else:
            pachinko(P, looks, k, x, COUNTER_H)
    # ashtrays on the ledge between machines, a little chrome bowl each
    for x in (-82.0, -41.3, 1.0, 46.0, 82.0):
        cyl(P, 2.4, 1.2, (x, -16.0, COUNTER_H), 'chrome', sides=14)
        cyl(P, 1.6, 0.3, (x, -16.0, COUNTER_H + 1.1), 'black', sides=12)
    collide(P, -87.1, -19.1, 0, 87.1, 19.1, COUNTER_H)
    collide(P, -87.1, 12.0, COUNTER_H, 87.1, SPINE, top + 4)
    return {'name': 'FOLabPachinkoBank' + ''.join(kinds).upper() + (left or '').upper(), 'looks': looks, 'parts': P}


def arcade_bank(games=('a', 'b'), left=None):
    """An arcade row's half: upright cabinets standing on the floor where the counter was, backs to the row behind."""
    looks = {}
    P = []
    slots = [(SLOTS[1], games[0]), (SLOTS[2], games[1])]
    if left:
        slots.insert(0, (SLOTS[0], left))
    for x, g in slots:
        L, lk = arcade_looks(g)
        L = {k: v + '_' + g for k, v in L.items()}
        looks.update({k + '_' + g: v for k, v in lk.items()})
        cabinet(P, g, x, 0.0, L)
    return {'name': 'FOLabArcadeBank' + ''.join(games).upper() + (left or '').upper(), 'looks': looks, 'parts': P}


# ---------- the slot menu, reskinned (the casino record names its pictures: nothing of the game's is changed) ----------
# The game's slot menu shows the casino's MOD2 model (a slot machine whose reels the engine spins, its reel models fixed)
# and draws the reels with the casino's seven ICON pictures. FOLab's casino gives it island symbols, a brass token for
# the coin and the minigame machine in the arcade's lacquer and gold (the game's model, its textures re-pointed).
MENU = 'textures\\folab\\arcade\\menu\\'
MENU_MODEL = 'meshes\\folab\\arcade\\menu_slot.nif'
GAME_MENU_MODEL = 'meshes\\terminals\\NV_SlotMachine\\NV_SlotMachine-Minigame-Generic.NIF'
SYMBOLS = ('hibiscus', 'aloha', 'seven', 'pineapple', 'coconuts', 'koi', 'surfboard')     # (in the game's order: bell, bar, 7, ...)


def _dds(rgb, a=None):
    import dds
    h, w = rgb.shape[:2]
    rgba = np.concatenate([np.clip(rgb, 0, 255), (np.ones((h, w, 1)) * 255 if a is None else np.clip(a, 0, 1)[..., None] * 255)], 2)
    return dds.compress(dds.encode(w, h, rgba.astype(np.uint8).tobytes()))


def symbol(name, w=128, h=64, seed=5100):
    """One reel's picture: a symbol printed on the reel's cream paper, as the game's are."""
    rgb = np.ones((h, w, 3)) * (234, 228, 210)
    n = noise(h, w, 8, seed)
    rgb *= (0.94 + 0.08 * n)[..., None]
    line = (30, 22, 20)
    cx, cy = w / 2.0, h / 2.0
    if name == 'hibiscus':
        for k in range(5):
            a = math.radians(-90 + 72 * k)
            lay(rgb, ellipse_mask(w, h, cx + 11 * math.cos(a), cy + 11 * math.sin(a), 10, 10), (220, 40, 50), line, 1)
        lay(rgb, ellipse_mask(w, h, cx, cy, 6, 6), (120, 10, 30), line, 1)
        lay(rgb, mask(w, h, lambda d, k: d.line(poly([(cx, cy), (cx + 16, cy - 14)], k), fill=255, width=2 * k)), (250, 210, 60))
    elif name == 'aloha':
        bar = mask(w, h, lambda d, k: d.rounded_rectangle((k * 14, k * 18, k * (w - 14), k * (h - 18)), radius=k * 4, fill=255))
        lay(rgb, bar, (24, 22, 24), line, 1)
        stamp(rgb, 'ALOHA', cx, cy - 7, 14, (250, 210, 80), centre=True, wide=w * 0.7)
    elif name == 'seven':
        seven = [(cx - 14, cy - 22), (cx + 16, cy - 22), (cx + 16, cy - 15), (cx - 2, cy + 24), (cx - 12, cy + 24), (cx + 5, cy - 14), (cx - 14, cy - 14)]
        lay(rgb, shape_mask(w, h, [seven]), (210, 30, 30), (200, 150, 40), 3)
        rgb[:] = mix(rgb, line, outline_of(shape_mask(w, h, [seven]), 1) * 0.0)
    elif name == 'pineapple':
        lay(rgb, ellipse_mask(w, h, cx, cy + 6, 12, 17), (230, 170, 40), line, 1)
        for j in range(-2, 3):
            lay(rgb, mask(w, h, lambda d, k: d.line(poly([(cx - 12, cy - 6 + 8 * j), (cx + 12, cy + 10 + 8 * j)], k), fill=255, width=k)) * ellipse_mask(w, h, cx, cy + 6, 12, 17), (150, 100, 20))
        for k in range(5):
            a = math.radians(-150 + 30 * k)
            lay(rgb, shape_mask(w, h, [[(cx - 3, cy - 10), (cx + 18 * math.cos(a), cy - 10 + 18 * math.sin(a)), (cx + 3, cy - 10)]]), (60, 140, 60), line, 1)
    elif name == 'coconuts':
        for dx in (-9, 9):
            lay(rgb, ellipse_mask(w, h, cx + dx, cy + 6, 10, 10), (110, 70, 40), line, 1)
            lay(rgb, ellipse_mask(w, h, cx + dx - 3, cy + 3, 2, 2), (40, 24, 16))
        lay(rgb, shape_mask(w, h, [[(cx - 20, cy - 8), (cx, cy - 20), (cx + 20, cy - 8), (cx, cy - 12)]]), (60, 140, 60), line, 1)
    elif name == 'koi':
        body = [(cx - 22, cy), (cx - 8, cy - 10), (cx + 12, cy - 7), (cx + 22, cy), (cx + 12, cy + 7), (cx - 8, cy + 9)]
        tail = [(cx - 20, cy), (cx - 32, cy - 10), (cx - 28, cy), (cx - 32, cy + 10)]
        lay(rgb, shape_mask(w, h, [body, tail]), (245, 120, 40), line, 1)
        lay(rgb, ellipse_mask(w, h, cx + 2, cy - 2, 6, 4), (240, 240, 230))
        lay(rgb, ellipse_mask(w, h, cx + 15, cy - 2, 1.5, 1.5), (10, 10, 10))
    else:
        board = [(cx - 30, cy + 8), (cx - 20, cy), (cx + 26, cy - 10), (cx + 32, cy - 8), (cx + 24, cy + 2), (cx - 22, cy + 12)]
        lay(rgb, shape_mask(w, h, [board]), (40, 160, 170), line, 1)
        lay(rgb, mask(w, h, lambda d, k: d.line(poly([(cx - 22, cy + 7), (cx + 26, cy - 5)], k), fill=255, width=2 * k)), (240, 70, 60))
    # (the symbol filling its reel as the game's do: the middle drawn larger)
    mid = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).crop((int(w * 0.15), int(h * 0.12), int(w * 0.85), int(h * 0.88)))
    rgb = np.asarray(mid.resize((w, h), Image.LANCZOS), float)
    return _dds(rgb)


def token(w=128, h=128, seed=5200):
    """The coin the menu shows: a brass token, a volcano struck in its middle, a rim of beads, worn bright on the high
    parts (stand-in for the island's kālā until its own picture is drawn)."""
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot(xx - w / 2.0, yy - h / 2.0) / (w / 2.0)
    n = noise(h, w, 10, seed)
    rgb = np.ones((h, w, 3)) * (196, 150, 70) * (0.85 + 0.25 * n)[..., None]
    rim = np.clip(1 - np.abs(r - 0.88) / 0.06, 0, 1)
    rgb = mix(rgb, (240, 210, 130), rim)
    for k in range(36):
        a = 2 * math.pi * k / 36
        rgb = mix(rgb, (250, 226, 150), ellipse_mask(w, h, w / 2 + 0.76 * w / 2 * math.cos(a), h / 2 + 0.76 * h / 2 * math.sin(a), 2.2, 2.2))
    v = shape_mask(w, h, [volcano_shape(w / 2, h * 0.66, w * 0.6, h * 0.34)])
    rgb = mix(rgb, (236, 200, 120), v)
    rgb = mix(rgb, (110, 70, 30), outline_of(v, 2))
    for k in range(3):
        rgb = mix(rgb, (110, 70, 30), ellipse_mask(w, h, w / 2 + (k - 1) * 8, h * 0.24 - abs(k - 1) * 3, 3, 3))
    stamp(rgb, '1', w / 2, h * 0.7, 14, (110, 70, 30), centre=True)
    a = (r <= 1.0).astype(float)
    return _dds(rgb, a)


def minigame_face(gd):
    """The game's minigame machine's face picture recoloured to the arcade's red lacquer and gold (the game's picture
    is the start: its parts stay where the model's corners expect them)."""
    import dds
    data = gd.read_file('textures\\terminals\\nv_slotmachine\\NV_SlotMachine-Minigame01.dds')
    w, h, px = dds.decode(data)[:3]
    img = np.frombuffer(px, np.uint8).reshape(h, w, 4).astype(float)
    rgb = img[..., :3]
    lum = rgb.mean(2, keepdims=True) / 255.0
    sat = (rgb.max(2) - rgb.min(2))[..., None] / 255.0
    red = np.asarray((170, 36, 30), float) * (0.5 + 0.9 * lum)
    gold = np.asarray((236, 190, 90), float) * (0.5 + 0.7 * lum)
    lacquer = np.asarray((120, 26, 22), float) * (0.4 + 1.1 * lum)
    out = np.where(sat > 0.25, red, mix(mix(rgb, lacquer, 0.55), gold, np.clip((lum - 0.55) * 2, 0, 1) * 0.6))
    return _dds(out, img[..., 3] / 255.0)


def menu_files(gd):
    """{path: bytes}: the reel symbols, the token, the minigame machine's face and its model re-pointed to them."""
    import nifwrite
    out = {}
    for k, s in enumerate(SYMBOLS):
        out[MENU + 'symbol%d.dds' % (k + 1)] = symbol(s, seed=5100 + k)
    out[MENU + 'token.dds'] = token()
    out[MENU + 'face.dds'] = minigame_face(gd)
    model = gd.read_file(GAME_MENU_MODEL)
    changes = {}
    for t in nifwrite.textures_in(model):
        low = t['path'].lower()
        if t['label'] != 'Picture':
            continue                                    # (their normal maps stay the game's)
        if 'minigame01' in low:
            changes[t['path']] = MENU[9:] + 'face.dds' if not low.startswith('textures') else MENU + 'face.dds'
        elif 'coin01' in low:
            changes[t['path']] = MENU[9:] + 'token.dds' if not low.startswith('textures') else MENU + 'token.dds'
    out[MENU_MODEL] = nifwrite.retexture(model, changes)
    return out


def symbol_paths():
    """The casino's seven ICON paths (as the game writes them: under textures\\, without the folder)."""
    return ['folab\\arcade\\menu\\symbol%d.dds' % (k + 1) for k in range(7)]


# ---------- the pieces ----------
TITLES = {'a': 'Surf Rider', 'b': 'Shark Attack', 'c': 'Volcano Run'}
PIECES = {
    'arcade_a': ('Arcade cabinet, Surf Rider', lambda: arcade_cabinet('a'), 'Surf Rider'),
    'arcade_b': ('Arcade cabinet, Shark Attack', lambda: arcade_cabinet('b'), 'Shark Attack'),
    'arcade_c': ('Arcade cabinet, Volcano Run', lambda: arcade_cabinet('c'), 'Volcano Run'),
    'arcade_bank': ('Arcade row (Surf Rider, Shark Attack)', lambda: arcade_bank(('a', 'b')), 'Arcade games'),
    'arcade_bank3': ('Arcade row (Surf Rider, Shark Attack, Volcano Run)', lambda: arcade_bank(('b', 'c'), left='a'), 'Arcade games'),
    'pachinko_a': ('Pachinko, Lucky Koi', lambda: pachinko_machine('a'), 'Pachinko'),
    'pachinko_b': ('Pachinko, Sakura', lambda: pachinko_machine('b'), 'Pachinko'),
    'pachinko_bank': ('Pachinko bank (two)', lambda: pachinko_bank(('a', 'b')), 'Pachinko'),
    'pachinko_bank3': ('Pachinko bank (three)', lambda: pachinko_bank(('b', 'a'), left='a'), 'Pachinko'),
}
for _k, (_label, _fn, _full) in PIECES.items():
    modelsets.PIECES.setdefault(_k, {'label': _label, 'set': SET, 'file': _k, 'describe': _fn, 'edid': _fn()['name'], 'no_far': True})


# ---------- the step: the Kilauea's slot machines swapped, playable ----------
CLUSTER = 'SlotMachineTableCluster06'
SINGLES = ('SlotMachine04StaticTOPS', 'SlotMachine05StaticTOPS')
WORLD = 'FOLabKilaueaWorld'
CASINO_EDID = 'FOLabKilaueaArcade'
SCRIPT_EDID = 'FOLabKilaueaArcadeScript'
QUEST_EDID = 'FOLabKilaueaArcadeWinnings'
CASINO_NAME = 'Kilauea Arcade'
CASINO_FROM = 'TheTopsCasinoData'
SLOT_FROM = 'vTopsSlot01'
PROMPT = 'Play'
MONEY = ('FOLabKala', 'FOLabKalaToken', 'Kala')     # (the island's money's editor ID, when it is in the mod; else caps)
SCRIPT = ('scn %s\r\n\r\nbegin OnActivate\r\n\r\n\tif IsActionRef player\r\n\t\tShowSlotMachineMenuParams %s 1 25 0\r\n'
          '\tendif\r\n\r\nend\r\n')


def _money(gd, pr):
    """(key, editor ID) of what the machines take: the island's kālā token when the mod has it, else caps."""
    import recordio
    for want in MONEY:
        for k, r in pr.records.items():
            if (recordio.field(r, 'EDID') or '').lower() == want.lower():
                return k, want
    f = next(f for f, (_i, r) in gd.forms.items() if r.tag == 'MISC' and gd.edid(f) == 'Caps001')
    return gd.key(f), 'Caps001'


def _game(gd, edid, tag):
    return next(f for f, (_i, r) in gd.forms.items() if r.tag == tag and gd.edid(f) == edid)


def placed(gd, pr):
    """The Kilauea casino's clusters and singles: [{'cell', 'ref', 'edid', 'p'}]."""
    import indoors
    w = next(x for x in gd.worlds() if gd.edid(x) == WORLD)
    cells = set(v for v in gd.grid(w).values())
    out = []
    for cf in cells:
        ck = gd.key(cf)
        for rk, base, p, _s in indoors.placed(gd, pr, ck):
            rec = pr.records.get(base)
            if rec:
                continue
            try:
                ed = gd.edid(gd.from_key(base))
            except (KeyError, ValueError):
                continue
            if ed == CLUSTER or ed in SINGLES:
                out.append({'cell': ck, 'ref': rk, 'edid': ed, 'p': list(p)})
    return out


def _local(c, p):
    dx, dy = p[0] - c['p'][0], p[1] - c['p'][1]
    zr = c['p'][5]
    return dx * math.cos(zr) - dy * math.sin(zr), dx * math.sin(zr) + dy * math.cos(zr)


def _world(c, lx, ly, lz):
    zr = c['p'][5]
    return [round(c['p'][0] + lx * math.cos(zr) + ly * math.sin(zr), 3), round(c['p'][1] - lx * math.sin(zr) + ly * math.cos(zr), 3),
            round(c['p'][2] + lz, 3), c['p'][3], c['p'][4], c['p'][5]]


def plan(gd, pr):
    """Which bank each cluster becomes and where each single goes: islands (back-to-back pairs) alternate pachinko and
    arcade round the ring; a cluster with no machine on its left slot becomes a bank of three."""
    things = placed(gd, pr)
    clusters = [t for t in things if t['edid'] == CLUSTER]
    singles = [t for t in things if t['edid'] in SINGLES]
    if not clusters:
        raise ValueError('no Tops slot banks in %s: done already?' % WORLD)
    # (each single to the cluster it stands on, its slot)
    on = {}
    for s in singles:
        c = min(clusters, key=lambda c: math.hypot(c['p'][0] - s['p'][0], c['p'][1] - s['p'][1]))
        lx, _ly = _local(c, s['p'])
        on.setdefault(c['ref'], []).append((0 if lx < 0 else 3, s))
    # (islands: each cluster with the one 87 behind it)
    pairs, seen = [], set()
    for c in sorted(clusters, key=lambda c: c['ref']):
        if c['ref'] in seen:
            continue
        o = min((x for x in clusters if x is not c and x['ref'] not in seen), key=lambda x: math.hypot(x['p'][0] - c['p'][0], x['p'][1] - c['p'][1]))
        seen |= {c['ref'], o['ref']}
        pairs.append((c, o))
    mx = sum(c['p'][0] for c in clusters) / len(clusters)
    my = sum(c['p'][1] for c in clusters) / len(clusters)
    pairs.sort(key=lambda pr_: math.atan2((pr_[0]['p'][1] + pr_[1]['p'][1]) / 2 - my, (pr_[0]['p'][0] + pr_[1]['p'][0]) / 2 - mx))
    rows = []
    for i, pair in enumerate(pairs):
        kind = 'pachinko' if i % 2 == 0 else 'arcade'
        for j, c in enumerate(pair):
            mine = dict(on.get(c['ref'], []))
            bank = kind + ('_bank' if 0 in mine else '_bank3')
            rows.append({'cluster': c, 'bank': bank, 'kind': kind})
            for slot, s in sorted(mine.items()):
                if kind == 'pachinko':
                    piece = 'pachinko_b' if (slot == 0) != (j == 1) else 'pachinko_a'
                    p = _world(c, SLOTS[slot], 0.0, COUNTER_H)
                else:
                    piece = ('arcade_c' if slot == 0 else ('arcade_c' if bank == 'arcade_bank' else 'arcade_a'))
                    p = _world(c, SLOTS[slot], 0.0, 0.0)
                rows.append({'single': s, 'piece': piece, 'p': p, 'moved': round(math.hypot(p[0] - s['p'][0], p[1] - s['p'][1]), 2),
                             'dz': round(p[2] - s['p'][2], 2)})
    return rows


def acti(edid, name, box, model, script_key):
    """An activator laid out as the game's slot machines are (vTopsSlot01: EDID, OBND, FULL, MODL, SCRI, XATO)."""
    return {'type': 'ACTI', 'flags': 0, 'src': '', 'subs': [
        {'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': edid},
        {'tag': 'OBND', 'label': 'Bounds', 'kind': 'struct', 'fields': [{'name': n, 'code': 'h', 'value': int(v)} for n, v in zip(('X1', 'Y1', 'Z1', 'X2', 'Y2', 'Z2'), box)]},
        {'tag': 'FULL', 'label': 'Name', 'kind': 'z', 'value': name},
        {'tag': 'MODL', 'label': 'Model', 'kind': 'z', 'value': model},
        {'tag': 'SCRI', 'label': 'Script', 'kind': 'F', 'value': script_key},
        {'tag': 'XATO', 'label': 'Activation prompt', 'kind': 'z', 'value': PROMPT}]}


def casino(gd, pr, quest_key):
    """FOLab's casino record: the Tops' (its odds, decks and limits) with FOLab's name, reel symbols, minigame machine,
    the island's money and a quest of its own for the winnings' stages."""
    import copy
    import recordio
    rec = copy.deepcopy(recordio.load(gd, _game(gd, CASINO_FROM, 'CSNO')))
    money, money_edid = _money(gd, pr)
    syms = symbol_paths()
    n_icon, n_modl = 0, 0
    for s in rec['subs']:
        if s['tag'] == 'EDID':
            s['value'] = CASINO_EDID
        elif s['tag'] == 'FULL':
            s['value'] = CASINO_NAME
        elif s['tag'] == 'ICON':
            k = int(s['value'].lower().split('symbol')[1][0])          # (the game's own order of symbols kept)
            s['value'] = syms[k - 1]
            n_icon += 1
        elif s['tag'] in ('MOD2',) or (s['tag'] == 'MODL' and 'slotmachine' in s['value'].lower()):
            s['value'] = MENU_MODEL[7:]
            n_modl += 1
        elif s['tag'] == 'DATA':
            for f in s['fields']:
                if f.get('name') == 'Currency':
                    f['value'] = money
                elif f.get('name') == 'Winnings quest':
                    f['value'] = quest_key
    rec['src'] = ''
    rec['flags'] = 0
    assert n_icon == 7 and n_modl == 2, (n_icon, n_modl)
    return rec, money_edid


def put_files(pr, gd, pieces):
    """Every piece's mesh and pictures and the menu's files among the mod's own files (only what differs is written).
    Returns {piece: made} and the paths written."""
    import os
    import library
    root = library.assets_dir(pr)
    made, wrote = {}, []
    files = menu_files(gd)
    import hotelinside                                  # (the closed Kilauea's ring of machines seen through its glass
    if pieces:                                          # from the city: arcade cabinets now, hotelinside.slot_row)
        c, n = modelsets.texture_files('resort/kil_slots')
        files[modelsets.tex_path('resort/kil_slots')], files[modelsets.tex_path('resort/kil_slots', True)] = c, n
    for piece in pieces:
        m = modelsets.build(piece)
        made[piece] = m
        files.update(m['files'])
    for rel, data in files.items():
        full = os.path.join(root, rel)
        if not os.path.isfile(full) or open(full, 'rb').read() != data:
            library._put(root, rel, data)
            wrote.append(rel)
    return made, wrote


def ops(gd, pr, made=None):
    """(ops, report): the records (script, winnings quest, casino, an activator a piece) and every swap and move, one
    Undo. made: put_files's answer (the pieces' bounds)."""
    import recordio
    import api_quests as aq
    import api_scripts
    import questrec as qr
    if any(recordio.field(r, 'EDID') == CASINO_EDID for r in pr.records.values()):
        raise ValueError('the mod has its arcade already')
    rows = plan(gd, pr)
    pieces = sorted({r['bank'] for r in rows if 'bank' in r} | {r['piece'] for r in rows if 'piece' in r})
    if made is None:
        made = {p: modelsmake_box(p) for p in pieces}
    order = ['script', 'quest', 'casino'] + pieces
    keys = dict(zip(order, aq._reserve(pr, len(order))))
    quest = qr.quest_record({'edid': QUEST_EDID, 'name': '', 'flags': {}, 'priority': 0, 'stages': [], 'objectives': []})
    cas, money = casino(gd, pr, keys['quest'])
    extra = {keys['quest']: quest, keys['casino']: cas}
    sc = api_scripts.scripts()
    comp = sc.compile(SCRIPT % (SCRIPT_EDID, CASINO_EDID), keys['script'], 'object', extra)
    if not hasattr(comp, 'subrecords'):
        raise ValueError('the arcade script does not compile: %s' % (comp,))
    script = sc._record_of(comp, SCRIPT_EDID)
    by_key = {'script': script, 'quest': quest, 'casino': cas}
    for p in pieces:
        m = made[p]
        box = m['box'] if isinstance(m, dict) else m
        by_key[p] = acti(modelsets.PIECES[p]['edid'], PIECES[p][2], box, 'folab\\arcade\\%s.nif' % p, keys['script'])
    out = [{'op': 'record_new', 'record': by_key[k]} for k in order]
    for r in rows:
        if 'bank' in r:
            c = r['cluster']
            out.append({'op': 'swap', 'cell': c['cell'], 'ref': c['ref'], 'base': keys[r['bank']]})
        else:
            s = r['single']
            out.append({'op': 'swap', 'cell': s['cell'], 'ref': s['ref'], 'base': keys[r['piece']]})
            out.append({'op': 'move', 'cell': s['cell'], 'ref': s['ref'], 'p': r['p']})
    import collections
    rep = {'keys': keys, 'money': money, 'script_bytes': len(comp.data),
           'banks': dict(collections.Counter(r['bank'] for r in rows if 'bank' in r)),
           'singles': dict(collections.Counter(r['piece'] for r in rows if 'piece' in r)),
           'moved_most': max([r['moved'] for r in rows if 'moved' in r] or [0]),
           'dz': sorted({r['dz'] for r in rows if 'dz' in r})}
    return out, rep


def modelsmake_box(piece):
    import modelmake
    return modelmake.make(modelsets.PIECES[piece]['describe']())['box']
