"""Pictures for signs, in the manner of the beach signs, menus and matchbooks of the period: flat colours, a dark line round
each shape, one light stroke for the shine. Palm trees, cocktail umbrellas, parrots, hibiscus, surfboards, waves, a
setting sun, a tiki face. Each is drawn on a signpaint picture (a texwear.Picture with signpaint's helpers) at x, y
(its foot or its middle, as each says) and a size in pixels; `neon=` draws its lines as glowing tubes instead.

Painted pictures don't glow; neon ones light in the glow picture, as the letters do."""
import math

import signpaint as sp
import texwear as tw

INK = (34, 26, 24)          # (the outline colour: near black, warm)
RED, ORANGE, YELLOW = (214, 58, 44), (236, 128, 40), (246, 204, 70)
GREEN, LEAF, TEAL = (60, 132, 66), (96, 168, 72), (44, 150, 150)
BLUE, SKY, CREAM = (40, 92, 176), (120, 190, 220), (244, 234, 210)
PINK, BROWN, WHITE = (238, 104, 140), (120, 76, 44), (250, 248, 240)


def _ellipse(cx, cy, rx, ry, turn=0.0, n=36):
    c, s = math.cos(math.radians(turn)), math.sin(math.radians(turn))
    out = []
    for k in range(n + 1):
        a = 2 * math.pi * k / n
        x, y = rx * math.cos(a), ry * math.sin(a)
        out.append((cx + x * c - y * s, cy + x * s + y * c))
    return out


def _line(c, pts, width, colour, closed=False):
    """A painted stroke along pts."""
    pts = list(pts) + ([pts[0]] if closed else [])
    m = sp.Mask(c.w, c.h)
    for a, b in zip(pts, pts[1:]):
        m.capsule(a, b, width / 2.0)
    for p in range(c.w * c.h):
        k = m.v[p]
        if k > 0:
            c.rgb[p] = tw.mix(c.rgb[p], colour, k)
            if c.a is not None:
                c.a[p] = max(c.a[p], k)


def shape(c, poly, colour, line=None, ink=INK):
    """Filled in colour, outlined in ink `line` pixels wide (none if 0)."""
    sp.fill(c, poly, colour)
    if line:
        _line(c, poly, line, ink, closed=True)


def _leaf(x, y, ang, ln, wd, bend=0.25, notches=0):
    """A long leaf from (x, y) along ang (degrees, y down), bowed; notches: cuts along it (a palm frond's leaflets)."""
    pts_a, pts_b = [], []
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    n = 14
    for k in range(n + 1):
        t = k / n
        along = ln * t
        off = ln * bend * math.sin(math.pi * t * 0.9)        # (the droop)
        cx, cy = x + ca * along - sa * off, y + sa * along + ca * off
        half = wd * math.sin(math.pi * min(1.0, t * 1.15)) * (0.55 if notches and k % 2 else 1.0)
        pts_a.append((cx - sa * half, cy + ca * half))
        pts_b.append((cx + sa * half, cy - ca * half))
    return pts_a + pts_b[::-1]


# ---------- the pictures ----------

def palm(c, x, y, size, lean=12.0, neon=None, g=None, colours=(BROWN, GREEN, LEAF)):
    """A coconut palm, its foot at (x, y), `size` tall, leaning `lean` degrees; its trunk curving, a crown of fronds
    drooping, coconuts under them."""
    trunk_c, frond_c, light_c = colours
    pts = []
    for k in range(13):
        t = k / 12
        pts.append((x + math.sin(math.radians(lean)) * size * 0.78 * t + size * 0.08 * math.sin(math.pi * t), y - size * 0.78 * t))
    top = pts[-1]
    if neon:
        sp.tube_path(c, g, pts, max(2.0, size / 40), neon, round_=0)
        for ang in (-170, -140, -105, -60, -25, 5, 30):
            leaf = _leaf(top[0], top[1], ang, size * 0.42, size * 0.05, bend=0.35 if abs(ang + 90) > 40 else 0.1)
            mid = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in zip(leaf[:15], leaf[::-1][:15])]
            sp.tube_path(c, g, mid, max(2.0, size / 45), neon, round_=0)
        return
    # the trunk: a tapering band with rings
    left, right = [], []
    for k, (px, py) in enumerate(pts):
        wd = size * (0.05 - 0.025 * k / 12)
        left.append((px - wd, py))
        right.append((px + wd, py))
    shape(c, left + right[::-1], trunk_c, line=max(2, size / 70))
    for k in range(1, 12):
        px, py = pts[k]
        wd = size * (0.05 - 0.025 * k / 12)
        _line(c, [(px - wd, py), (px + wd, py - size * 0.012)], max(1.5, size / 110), INK)
    # coconuts, then fronds over them
    for dx, dy in ((-0.03, 0.03), (0.025, 0.035), (0.0, 0.055)):
        shape(c, _ellipse(top[0] + dx * size, top[1] + dy * size, size * 0.028, size * 0.028), (110, 84, 40), line=max(1.5, size / 110))
    for ang, ln in ((-175, 0.42), (-140, 0.46), (-100, 0.34), (-60, 0.44), (-20, 0.46), (10, 0.4), (35, 0.3), (160, 0.3)):
        leaf = _leaf(top[0], top[1], ang, size * ln, size * 0.06, bend=0.32 if abs(ang + 90) > 40 else 0.12)
        shape(c, leaf, frond_c, line=max(2, size / 80))
        mid = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in zip(leaf[:15], leaf[::-1][:15])]
        _line(c, mid[:13], max(1.5, size / 110), light_c)
        for j in range(3, 13, 2):                   # (the leaflets: short strokes off the rib, toward the tip)
            (ax, ay), (bx2, by2) = leaf[j], leaf[-1 - j]
            mx2, my2 = mid[j]
            _line(c, [(mx2, my2), (ax * 0.7 + mx2 * 0.3, ay * 0.7 + my2 * 0.3)], max(1.0, size / 160), INK)
            _line(c, [(mx2, my2), (bx2 * 0.7 + mx2 * 0.3, by2 * 0.7 + my2 * 0.3)], max(1.0, size / 160), INK)


def umbrella(c, x, y, size, colours=(PINK, YELLOW, TEAL, ORANGE), tilt=-18.0, neon=None, g=None):
    """A cocktail umbrella, its tip at (x, y), tilted (degrees): a shallow cone of panels in turns of colour seen a little
    from below, a scalloped rim, the stick down to the drink."""
    t = math.radians(tilt)
    rot = lambda px, py: (x + px * math.cos(t) - py * math.sin(t), y + px * math.sin(t) + py * math.cos(t))
    r = size / 2.0
    drop, tip = r * 0.42, r * 0.18                  # (how far the rim hangs under the tip; how far the rim's ellipse is deep)
    rim_at = lambda a, sag=1.0: (r * sag * math.cos(math.radians(a)), drop + tip * sag * math.sin(math.radians(a)))
    if neon:
        rim = [rot(*rim_at(a)) for a in range(0, 181, 10)]
        sp.tube_path(c, g, [rot(0, 0)] + rim + [rot(0, 0)], max(2.0, size / 40), neon, round_=0)
        sp.tube_path(c, g, [rot(0, -r * 0.08), rot(0, size * 1.05)], max(2.0, size / 45), neon, round_=0)
        return
    _line(c, [rot(0, -r * 0.1), rot(0, size * 1.1)], max(2, size / 36), (226, 212, 180))
    panels = 8
    for k in range(panels):                         # (the near half of the cone, its panels from one side to the other)
        a0, a1 = 180.0 * k / panels, 180.0 * (k + 1) / panels
        edge = [rot(*rim_at(a0 + (a1 - a0) * j / 6, 1 - 0.08 * math.sin(math.pi * j / 6))) for j in range(7)]
        shape(c, [rot(0, 0)] + edge, colours[k % len(colours)], line=max(1.5, size / 70))
    shape(c, _ellipse(*rot(0, -r * 0.04), size * 0.03, size * 0.03), CREAM, line=max(1, size / 90))


def parrot(c, x, y, size, facing=1, colours=(RED, YELLOW, BLUE), neon=None, g=None):
    """A macaw on a perch, its feet at (x, y), `size` tall, looking along facing (1 right, -1 left): red body, a wing of
    yellow over blue, a long tail, a hooked pale beak, a white eye patch."""
    body_c, mid_c, wing_c = colours
    f = facing
    P = lambda px, py: (x + f * px * size, y - py * size)
    if neon:
        body = [P(*q) for q in ((0.02, 0.0), (0.1, 0.25), (0.12, 0.55), (0.08, 0.78), (0.0, 0.86), (-0.08, 0.8), (-0.06, 0.55), (-0.12, 0.25), (-0.28, -0.15))]
        sp.tube_path(c, g, body, max(2.0, size / 40), neon)
        sp.tube_path(c, g, [P(0.08, 0.8), P(0.16, 0.76), P(0.13, 0.68)], max(2.0, size / 45), neon, round_=0)
        return
    tail = [P(-0.02, 0.32), P(-0.08, 0.3), P(-0.34, -0.22), P(-0.26, -0.24), P(0.04, 0.28)]
    shape(c, tail, wing_c, line=max(2, size / 70))
    shape(c, [P(-0.05, 0.3), P(-0.2, -0.12), P(-0.14, -0.13), P(0.02, 0.3)], body_c, line=max(1.5, size / 90))
    body = [P(*q) for q in ((0.0, 0.3), (0.09, 0.4), (0.12, 0.56), (0.1, 0.7), (0.04, 0.82), (-0.04, 0.84), (-0.1, 0.76),
                            (-0.11, 0.6), (-0.09, 0.42))]
    shape(c, body, body_c, line=max(2, size / 70))
    wing = [P(*q) for q in ((-0.02, 0.66), (0.06, 0.6), (0.06, 0.46), (-0.02, 0.32), (-0.13, 0.22), (-0.1, 0.42), (-0.1, 0.58))]
    shape(c, wing, wing_c, line=max(1.5, size / 80))
    shape(c, [P(*q) for q in ((-0.02, 0.66), (0.06, 0.6), (0.05, 0.52), (-0.04, 0.5), (-0.1, 0.56))], mid_c, line=max(1.5, size / 90))
    shape(c, [P(0.02, 0.72), P(0.08, 0.76), P(0.08, 0.68), P(0.02, 0.66)], WHITE, line=max(1, size / 110))       # (the face patch)
    shape(c, _ellipse(*P(0.05, 0.73), size * 0.012, size * 0.012), INK)
    shape(c, [P(0.08, 0.79), P(0.16, 0.76), P(0.15, 0.66), P(0.11, 0.69), P(0.09, 0.72)], (232, 222, 196), line=max(1.5, size / 90))
    _line(c, [P(-0.2, 0.31), P(0.2, 0.31)], max(3, size / 28), BROWN)                                          # (the perch)
    for dx in (-0.03, 0.03):
        _line(c, [P(dx, 0.34), P(dx + 0.02, 0.3)], max(1.5, size / 80), INK)


def hibiscus(c, x, y, r, colour=RED, centre=YELLOW, turn=0.0, neon=None, g=None):
    """A hibiscus flower seen face on: five broad petals, a long stamen."""
    if neon:
        for k in range(5):
            a = turn + 72 * k
            sp.tube_path(c, g, _ellipse(x + math.cos(math.radians(a)) * r * 0.5, y + math.sin(math.radians(a)) * r * 0.5, r * 0.5, r * 0.36, a, 18),
                         max(2.0, r / 14), neon, round_=0)
        return
    for k in range(5):
        a = turn + 72 * k
        shape(c, _ellipse(x + math.cos(math.radians(a)) * r * 0.52, y + math.sin(math.radians(a)) * r * 0.52, r * 0.52, r * 0.42, a), colour, line=max(1.5, r / 22))
    shape(c, _ellipse(x, y, r * 0.2, r * 0.2), tw.mul(colour, 0.55))
    sx, sy = x + math.cos(math.radians(turn - 30)) * r * 0.9, y + math.sin(math.radians(turn - 30)) * r * 0.9
    _line(c, [(x, y), (sx, sy)], max(2, r / 14), centre)
    shape(c, _ellipse(sx, sy, r * 0.08, r * 0.08), centre)


def surfboard(c, x, y, length, turn=-70.0, colour=TEAL, stripe=CREAM, neon=None, g=None):
    """A longboard standing on its tail at (x, y), turned (degrees from pointing right), a stripe down it."""
    t = math.radians(turn)
    pts = []
    for k in range(25):
        u = k / 24
        half = length * 0.13 * math.sin(math.pi * u) ** 0.6 * (0.9 if u < 0.5 else 1.0)
        pts.append((u * length, half))
    outline = pts + [(px, -py) for px, py in pts[::-1]]
    R = lambda px, py: (x + px * math.cos(t) - py * math.sin(t), y + px * math.sin(t) + py * math.cos(t))
    if neon:
        sp.tube_path(c, g, [R(*q) for q in outline], max(2.0, length / 60), neon, round_=0)
        return
    shape(c, [R(*q) for q in outline], colour, line=max(2, length / 80))
    _line(c, [R(length * 0.08, 0), R(length * 0.92, 0)], max(2, length / 40), stripe)


def waves(c, x0, x1, y, high, colour=TEAL, crest=CREAM, curls=4, neon=None, g=None):
    """A row of breaking waves along y from x0 to x1, high pixels tall: each a swell rising to a crest that curls forward
    and down in a spiral, foam along its top."""
    step = (x1 - x0) / curls
    for k in range(curls):
        bx = x0 + k * step
        cx, cy, cr = bx + step * 0.72, y - high * 0.55, high * 0.45
        rise = [(bx + (cx - bx) * u, y - (y - (cy - cr)) * (u ** 1.8)) for u in [j / 12 for j in range(13)]]
        spiral = []
        for j in range(1, 23):
            a = -90 + 18 * j                             # (round forward and down, the radius shrinking as it goes)
            r = cr * (1 - 0.68 * j / 22)
            spiral.append((cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))))
        if neon:
            sp.tube_path(c, g, rise + spiral, max(2.0, high / 14), neon, round_=0)
            continue
        body = [(bx, y)] + rise + spiral[:9] + [(cx + cr * 0.55, y)]
        shape(c, body, colour, line=max(2, high / 18))
        _line(c, spiral, max(2, high / 12), tw.mul(colour, 0.55))
        _line(c, rise[7:] + spiral[:7], max(2, high / 10), crest)
        for j in range(3):                               # (spray off the crest)
            shape(c, _ellipse(cx + cr * (0.7 + 0.3 * j), cy - cr * (0.75 + 0.25 * j), high * 0.035, high * 0.035), crest)


def sunset(c, x, y, r, colour=ORANGE, band=YELLOW, bars=4, neon=None, g=None):
    """A setting sun, its middle on the horizon at (x, y): a half disc cut by bars, rays fanning out."""
    half = [(x + r * math.cos(math.radians(a)), y + r * math.sin(math.radians(a))) for a in range(180, 361, 6)]
    if neon:
        sp.tube_path(c, g, half + [half[0]], max(2.0, r / 16), neon, round_=0)
        for a in range(190, 360, 20):
            sp.tube_path(c, g, [(x + r * 1.2 * math.cos(math.radians(a)), y + r * 1.2 * math.sin(math.radians(a))),
                                (x + r * 1.55 * math.cos(math.radians(a)), y + r * 1.55 * math.sin(math.radians(a)))], max(2.0, r / 18), neon, round_=0)
        return
    for a in range(190, 360, 20):
        _line(c, [(x + r * 1.18 * math.cos(math.radians(a)), y + r * 1.18 * math.sin(math.radians(a))),
                  (x + r * 1.6 * math.cos(math.radians(a)), y + r * 1.6 * math.sin(math.radians(a)))], max(2, r / 12), band)
    shape(c, half + [half[0]], colour, line=max(2, r / 20))
    for k in range(1, bars + 1):
        yy = y - r * k / (bars + 1) * 0.9
        _line(c, [(x - r, yy), (x + r, yy)], max(1.5, r / 16 * (1.2 - k / (bars + 1))), band)


def tiki_face(c, x, y, size, wood=(150, 96, 56), neon=None, g=None):
    """A tiki's face, its middle at (x, y): a tall head, a wide mouth with teeth, big round eyes, a crest."""
    w, h = size * 0.62, size
    head = [(x - w / 2, y + h / 2), (x - w / 2, y - h * 0.32), (x - w * 0.3, y - h / 2), (x + w * 0.3, y - h / 2), (x + w / 2, y - h * 0.32), (x + w / 2, y + h / 2)]
    if neon:
        sp.tube_path(c, g, head + [head[0]], max(2.0, size / 40), neon, round_=0)
        for ex in (-1, 1):
            sp.tube_path(c, g, _ellipse(x + ex * w * 0.22, y - h * 0.12, w * 0.14, w * 0.14, n=18), max(2.0, size / 45), neon, round_=0)
        sp.tube_path(c, g, _ellipse(x, y + h * 0.24, w * 0.34, h * 0.1, n=24), max(2.0, size / 45), neon, round_=0)
        return
    shape(c, head + [head[0]], wood, line=max(2, size / 60))
    for k in range(5):                                          # (the crest)
        cx = x - w * 0.4 + w * 0.2 * k
        shape(c, [(cx - w * 0.08, y - h * 0.5), (cx, y - h * 0.66), (cx + w * 0.08, y - h * 0.5)], tw.mul(wood, 0.8), line=max(1.5, size / 80))
    _line(c, [(x - w * 0.42, y - h * 0.3), (x - w * 0.05, y - h * 0.22)], max(2, size / 30), tw.mul(wood, 0.6))
    _line(c, [(x + w * 0.42, y - h * 0.3), (x + w * 0.05, y - h * 0.22)], max(2, size / 30), tw.mul(wood, 0.6))
    for ex in (-1, 1):
        shape(c, _ellipse(x + ex * w * 0.22, y - h * 0.1, w * 0.15, w * 0.15), CREAM, line=max(2, size / 60))
        shape(c, _ellipse(x + ex * w * 0.22, y - h * 0.1, w * 0.06, w * 0.06), INK)
    shape(c, [(x - w * 0.08, y - h * 0.05), (x + w * 0.08, y - h * 0.05), (x + w * 0.14, y + h * 0.1), (x - w * 0.14, y + h * 0.1)], tw.mul(wood, 0.78), line=max(1.5, size / 80))
    mouth = _ellipse(x, y + h * 0.26, w * 0.36, h * 0.12)
    shape(c, mouth, (60, 28, 22), line=max(2, size / 60))
    for k in range(6):
        tx = x - w * 0.27 + w * 0.108 * k
        shape(c, [(tx - w * 0.04, y + h * 0.2), (tx + w * 0.04, y + h * 0.2), (tx, y + h * 0.27)], CREAM)


def ribbon(c, box, colour=CREAM, fold=None):
    """A ribbon banner across box (x0, y0, x1, y1): the band, its ends folded back behind and cut in a swallowtail; words
    go on the band (box itself)."""
    x0, y0, x1, y1 = box
    h = y1 - y0
    fold = tw.mul(colour, 0.68) if fold is None else fold
    for s_ in (-1, 1):
        ex = x0 if s_ < 0 else x1
        tail = [(ex, y0 + h * 0.3), (ex + s_ * h * 0.6, y0 + h * 0.3), (ex + s_ * h * 0.38, y0 + h * 0.8), (ex + s_ * h * 0.6, y1 + h * 0.3), (ex, y1 + h * 0.3)]
        shape(c, tail, fold, line=max(2, h / 14))
        shape(c, [(ex, y1), (ex, y1 + h * 0.3), (ex - s_ * h * 0.25, y1)], tw.mul(fold, 0.6), line=max(1.5, h / 18))
    band = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    shape(c, band, colour, line=max(2, h / 14))


def cocktail(c, x, y, size, glass=TEAL, drink=PINK, cherry=RED, brolly=YELLOW, neon=None, g=None):
    """A cocktail glass, its foot at (x, y), `size` tall: a wide V bowl on a stem, the drink in it, a cherry on a pick and a
    paper umbrella stuck in at a slant, sparkles off the rim. neon: {'glass', 'drink', 'cherry', 'brolly', 'spark'} colours
    for tubes (any left out are not drawn)."""
    w = size * 0.78
    rim_y, bowl_y = y - size, y - size * 0.45
    bowl = [(x - w / 2, rim_y), (x + w / 2, rim_y), (x, bowl_y)]
    stem = [(x, bowl_y), (x, y - size * 0.06)]
    foot = [(x - w * 0.3, y), (x + w * 0.3, y)]
    level = rim_y + size * 0.12
    liquid = [(x - w / 2 * (1 - (level - rim_y) / (bowl_y - rim_y)), level), (x + w / 2 * (1 - (level - rim_y) / (bowl_y - rim_y)), level), (x, bowl_y - size * 0.02)]
    pick = [(x + w * 0.05, level + size * 0.1), (x + w * 0.34, rim_y - size * 0.12)]
    cher = (x + w * 0.37, rim_y - size * 0.14)
    if neon:
        th = max(2.0, size / 34)
        if neon.get('glass'):
            sp.tube_path(c, g, bowl + [bowl[0]], th, neon['glass'], round_=0)
            sp.tube_path(c, g, stem, th, neon['glass'], round_=0)
            sp.tube_path(c, g, [foot[0], (x, y - size * 0.05), foot[1]], th, neon['glass'], round_=0)
        if neon.get('drink'):
            sp.tube_path(c, g, liquid[:2], th, neon['drink'], round_=0)
        if neon.get('cherry'):
            sp.tube_path(c, g, pick, th * 0.8, neon['cherry'], round_=0)
            sp.tube_path(c, g, _ellipse(cher[0], cher[1], size * 0.07, size * 0.07, n=16), th, neon['cherry'], round_=0)
        if neon.get('brolly'):
            umbrella(c, x - w * 0.18, rim_y - size * 0.16, size * 0.42, tilt=-28, neon=neon['brolly'], g=g)
        if neon.get('spark'):
            for sx, sy, r in ((x - w * 0.5, rim_y + size * 0.22, size * 0.07), (x + w * 0.62, rim_y + size * 0.3, size * 0.06)):
                for a in (0, 90):
                    ca, sa_ = math.cos(math.radians(a)), math.sin(math.radians(a))
                    sp.tube_path(c, g, [(sx - ca * r, sy - sa_ * r), (sx + ca * r, sy + sa_ * r)], th * 0.8, neon['spark'], round_=0)
        return
    umbrella(c, x - w * 0.18, rim_y - size * 0.16, size * 0.42, tilt=-28)
    shape(c, liquid, drink, line=max(1.5, size / 70))
    _line(c, bowl + [bowl[0]], max(2, size / 50), glass)
    _line(c, stem, max(3, size / 30), glass)
    _line(c, foot, max(3, size / 30), glass)
    _line(c, pick, max(1.5, size / 80), (226, 212, 180))
    shape(c, _ellipse(cher[0], cher[1], size * 0.07, size * 0.07), cherry, line=max(1.5, size / 70))


def bus(c, x, y, length, colour=(60, 120, 150), trim=CREAM):
    """A bus from the side as a stop's sign shows one, its wheels' foot at (x, y): a rounded body, a row of windows, two
    wheels."""
    L, H = length, length * 0.42
    x0, y0 = x - L / 2, y - H
    shape(c, sp.rounded(x0, y0, x0 + L, y - H * 0.18, H * 0.22), colour, line=max(2, L / 60))
    for k in range(5):
        wx = x0 + L * (0.08 + 0.17 * k)
        shape(c, sp.rounded(wx, y0 + H * 0.14, wx + L * 0.13, y0 + H * 0.46, 3), trim, line=max(1.5, L / 90))
    _line(c, [(x0 + L * 0.04, y - H * 0.34), (x0 + L * 0.96, y - H * 0.34)], max(2, L / 50), trim)
    for wx in (x0 + L * 0.24, x0 + L * 0.76):
        shape(c, _ellipse(wx, y - H * 0.16, H * 0.16, H * 0.16), INK)
        shape(c, _ellipse(wx, y - H * 0.16, H * 0.06, H * 0.06), (160, 160, 150))
