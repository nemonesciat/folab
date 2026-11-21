"""Signs with period lettering, and the glow maps that light only what should light (the game's way: a sign's colour picture
and beside it a `_g` picture, black where nothing glows, slot 2 of its texture set; nifmake's `glow`).

The letters are texpaint's block capitals as a skeleton, drawn as a sign-writer or a neon bender would:
  - `tube`: neon. The skeleton rounded (corner cutting) and drawn as a glass tube of one width; by day pale tinted
    glass with a highlight down it and a dark shadow on the board behind, in the glow map a hot core with a soft halo.
  - `deco`: the 1920s-30s hotels' painted and raised letters. Condensed, thick uprights and hairline crossbars (a pen
    held flat), an outline and a drop shadow, a light line inside each stroke.
  - `brush`: the broad-nib pen held at a slant, as hand-painted shop and bar boards; letters lean a little.
  - `chisel`: carved into a board (tiki bars): wedge-ended strokes cut in, their sides catching light and shade.
Each style comes with a board (`Board`): enamel, painted stucco, koa, milk glass. `sign` paints one; it returns the
colour picture (a texwear.Picture, files() as any of FOLab's) and the glow picture (`glow_files` for its DDS).

Night in the game is the colour picture lit by the moon plus the glow map times the material's emissive colour and its
multiplier (the Strip's neon runs 4 to 25: nifmake `glow_mult`). `preview` draws a sign as day, night and through a
storm's haze, for looking at before anything is built."""
import math
import random

import texpaint as tp
import texwear as tw

# ---------- strokes ----------


def _round(path, times=2):
    """Corner cutting (Chaikin): a polyline's corners rounded, its ends kept. A closed path (first == last) stays closed."""
    closed = len(path) > 2 and tuple(path[0]) == tuple(path[-1])
    for _ in range(times):
        out = [] if closed else [path[0]]
        for a, b in zip(path, path[1:]):
            out += [(a[0] * 0.75 + b[0] * 0.25, a[1] * 0.75 + b[1] * 0.25), (a[0] * 0.25 + b[0] * 0.75, a[1] * 0.25 + b[1] * 0.75)]
        if closed:
            out.append(out[0])
        else:
            out.append(path[-1])
        path = out
    return path


class Mask:
    """How much of each pixel a shape covers, 0-1."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.v = [0.0] * (w * h)

    def capsule(self, a, b, ra, rb=None, soft=1.0):
        """A stroke from a to b, radius ra at a and rb at b, round ends."""
        rb = ra if rb is None else rb
        r = max(ra, rb) + soft
        w, v = self.w, self.v
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = dx * dx + dy * dy
        x0, x1 = max(0, int(min(a[0], b[0]) - r - 1)), min(w, int(max(a[0], b[0]) + r + 2))
        for y in range(max(0, int(min(a[1], b[1]) - r - 1)), min(self.h, int(max(a[1], b[1]) + r + 2))):
            row = y * w
            for x in range(x0, x1):
                t = ((x - a[0]) * dx + (y - a[1]) * dy) / ln if ln else 0.0
                t = 0.0 if t < 0 else 1.0 if t > 1 else t
                d = math.hypot(x - a[0] - t * dx, y - a[1] - t * dy)
                c = (ra + (rb - ra) * t - d) / soft + 0.5
                if c > 0:
                    c = 1.0 if c > 1 else c
                    if c > v[row + x]:
                        v[row + x] = c

    def shifted(self, dx, dy):
        out = Mask(self.w, self.h)
        w, h = self.w, self.h
        for y in range(h):
            sy = y - dy
            if 0 <= sy < h:
                for x in range(w):
                    sx = x - dx
                    if 0 <= sx < w:
                        out.v[y * w + x] = self.v[sy * w + sx]
        return out

    def blurred(self, r, passes=3):
        """A soft copy (box blur `passes` times, radius r): a halo."""
        w, h = self.w, self.h
        v = list(self.v)
        n = 2 * r + 1
        for _ in range(passes):
            for y in range(h):              # along rows
                row = v[y * w:(y + 1) * w]
                acc = sum(row[0:r + 1]) + row[0] * r
                out = []
                for x in range(w):
                    out.append(acc / n)
                    acc += row[min(w - 1, x + r + 1)] - row[max(0, x - r)]
                v[y * w:(y + 1) * w] = out
            for x in range(w):              # down columns
                col = v[x::w]
                acc = sum(col[0:r + 1]) + col[0] * r
                for y in range(h):
                    v[y * w + x] = acc / n
                    acc += col[min(h - 1, y + r + 1)] - col[max(0, y - r)]
        out = Mask(w, h)
        out.v = v
        return out


# the styles: how the skeleton becomes strokes. wide: letter width against texpaint's; slant: lean (x per y);
# nib: None for an even stroke, else (angle of the pen's edge in degrees, thinnest part of the full width); round:
# corner cutting passes; space: gap between letters in skeleton units
STYLES = {
    'tube': {'wide': 1.0, 'slant': 0.0, 'nib': None, 'round': 0, 'space': 3.0, 'weight': 0.085, 'waist': 0.5},
    # (neon run down the middle of deco letters, as channel letters are lit: laid out exactly as 'deco', so over them)
    'deco_tube': {'wide': 0.78, 'slant': 0.0, 'nib': None, 'round': 0, 'space': 2.0, 'weight': 0.045, 'waist': 0.38, 'fit': 0.19, 'tube': True},
    'deco': {'wide': 0.78, 'slant': 0.0, 'nib': (0.0, 0.34), 'round': 0, 'space': 2.0, 'weight': 0.19, 'waist': 0.38},
    'brush': {'wide': 0.92, 'slant': 0.17, 'nib': (35.0, 0.28), 'round': 0, 'space': 2.2, 'weight': 0.17, 'waist': 0.5},
    'chisel': {'wide': 0.9, 'slant': 0.0, 'nib': (90.0, 0.5), 'round': 0, 'space': 2.4, 'weight': 0.17, 'waist': 0.55},
}
_FONTS = {}


def _strokes(words, style):
    """[polyline in glyph units (cap height signfont.CAP)]: the words as the style draws them; and the line's width."""
    import signfont
    st = STYLES[style]
    font = _FONTS.get(st['waist']) or _FONTS.setdefault(st['waist'], signfont.glyphs(st['waist']))
    cap = signfont.CAP
    out, x = [], 0.0
    for ch in words.upper():
        if ch == ' ':
            x += 4.5 * st['wide'] + st['space']
            continue
        wd, paths = font.get(ch, (0.0, []))
        for s in paths:
            p = [(x + px * st['wide'] + (cap - py) * st['slant'], py) for px, py in s]
            out.append(_round(p, st['round']) if len(p) > 2 and st['round'] else p)
        x += wd * st['wide'] + st['space']
    return out, x - st['space']


def letters(words, style, box, w, h):
    """Masks of the words fitted in box (x0, y0, x1, y1 in pixels) as `style` draws them: {'ink': the letters,
    'core': the middle of each stroke (a tube's hot line, a deco stroke's inner line), 'cut': for chisel, which side of
    each stroke faces up-left (0-1)}; and the stroke width in pixels."""
    st = STYLES[style]
    paths, line_w = _strokes(words, style)
    x0, y0, x1, y1 = box
    cap = 10.0
    fit = st.get('fit', st['weight'])
    unit = min((x1 - x0) / (line_w + cap * fit + cap * st['slant']), (y1 - y0) / (cap + cap * fit))
    ox = x0 + ((x1 - x0) - (line_w + cap * st['slant']) * unit) / 2
    oy = y0 + ((y1 - y0) - cap * unit) / 2
    thick = cap * st['weight'] * unit
    ink, core, lit = Mask(w, h), Mask(w, h), Mask(w, h)
    for path in paths:
        P = [(ox + px * unit, oy + py * unit) for px, py in path]
        for a, b in zip(P, P[1:]):
            r = thick / 2
            if st['nib']:
                ang, thin = st['nib']
                dx, dy = b[0] - a[0], b[1] - a[1]
                ln = math.hypot(dx, dy) or 1.0
                nx, ny = math.cos(math.radians(ang)), -math.sin(math.radians(ang))
                across = abs(dx * ny - dy * nx) / ln      # (how far the stroke runs across the pen's edge)
                r = thick / 2 * (thin + (1 - thin) * across)
            ink.capsule(a, b, r)
            core.capsule(a, b, max(0.8, r * 0.28))
            if style == 'chisel':                       # (the side of the cut that faces the light: up and left)
                dx, dy = b[0] - a[0], b[1] - a[1]
                ln = math.hypot(dx, dy) or 1.0
                px, py = -dy / ln, dx / ln
                if px + py > 0:
                    px, py = -px, -py
                lit.capsule((a[0] + px * r * 0.45, a[1] + py * r * 0.45), (b[0] + px * r * 0.45, b[1] + py * r * 0.45), r * 0.5)
    return {'ink': ink, 'core': core, 'lit': lit}, thick


# ---------- boards ----------

def outline(shape, box):
    """The board's outline (a closed list of points) for shape: 'rect', 'rounded', 'arch' (round top), 'shield' (a point
    at the foot), 'arrow' (pointing right, notched tail), 'oval'."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    if shape == 'rounded':
        return rounded(x0, y0, x1, y1, min(w, h) * 0.18)
    if shape == 'arch':
        top = [(x0 + w / 2 + w / 2 * math.cos(math.radians(a)), y0 + h * 0.32 + h * 0.32 * math.sin(math.radians(a))) for a in range(180, 361, 6)]
        return top + [(x1, y1), (x0, y1), top[0]]
    if shape == 'shield':
        side = y0 + h * 0.55
        foot = [(x0 + w / 2 + w / 2 * math.cos(math.radians(a)), side + (y1 - side) * math.sin(math.radians(a))) for a in range(0, 181, 6)]
        return [(x0, y0), (x1, y0), (x1, side)] + foot + [(x0, side), (x0, y0)]
    if shape == 'arrow':
        tip, notch = h * 0.5, h * 0.3
        return [(x0, y0), (x1 - tip, y0), (x1, y0 + h / 2), (x1 - tip, y1), (x0, y1), (x0 + notch, y0 + h / 2), (x0, y0)]
    if shape == 'oval':
        return [(x0 + w / 2 + w / 2 * math.cos(math.radians(a)), y0 + h / 2 + h / 2 * math.sin(math.radians(a))) for a in range(0, 361, 4)]
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]


def _inside(poly, x, y):
    j, yes = len(poly) - 1, False
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            yes = not yes
        j = i
    return yes


def _board(c, kind, ground, box, seed, shape='rect', rim_colour=(150, 146, 136)):
    """The board behind the letters, painted into Picture c over box in `shape`. Outside it the picture is clear (a
    cut-out board), unless it is a plain rectangle filling the picture. Returns its outline."""
    x0, y0, x1, y1 = [int(v) for v in box]
    w, h = c.w, c.h
    poly = outline(shape, (x0, y0, x1, y1))
    cut = shape != 'rect' or (x0, y0, x1, y1) != (0, 0, w, h)
    if cut and c.a is None:
        c.a = [0.0] * (w * h)
    fld = tw.Field(w, h, seed, cells=6, octaves=4)
    fine = tw.Field(w, h, seed + 1, cells=48, octaves=2, stretch=(4, 1) if kind == 'koa' else (1, 1))
    for y in range(max(0, y0), min(h, y1)):
        for x in range(max(0, x0), min(w, x1)):
            if cut and not _inside(poly, x + 0.5, y + 0.5):
                continue
            p = y * w + x
            f, g = fld.v[p], fine.v[p]
            if kind == 'enamel':                        # (porcelain enamel on steel: smooth, chipped to dark iron)
                col, ht, gl = tw.mul(ground, 0.94 + 0.1 * f), 0.5, 90
                if f > 0.83 and g > 0.6:
                    col, ht, gl = tw.mix((58, 44, 36), (120, 64, 40), g), 0.45, 10
            elif kind == 'stucco':
                col, ht, gl = tw.mul(ground, 0.88 + 0.18 * f + 0.06 * (g - 0.5)), 0.5 + 0.06 * g, 16
            elif kind == 'koa':                         # (oiled koa gone grey on top in the sun)
                grain = 0.5 + 0.5 * math.sin((y + 18 * f) * 0.9 + g * 3)
                col = tw.mix(ground, tw.mul(ground, 0.62), grain * 0.6)
                col = tw.mix(col, (150, 140, 124), 0.35 * tw.smooth(0.45, 0.8, f))
                ht, gl = 0.5 + 0.05 * grain, 20
            else:                                       # 'glass': milk glass, lit from behind at night
                col, ht, gl = tw.mul(ground, 0.95 + 0.06 * f), 0.5, 120
            c.rgb[p], c.ht[p], c.gloss[p] = col, ht, gl
            if cut:
                c.a[p] = 1.0
    # a rolled metal rim (a wooden one on koa) along the outline
    rim = max(3.0, min(x1 - x0, y1 - y0) / 30.0)
    m = Mask(w, h)
    for a, b in zip(poly, poly[1:]):
        m.capsule(a, b, rim)
    rc = tw.mul(ground, 0.55) if kind == 'koa' else rim_colour
    for p in range(w * h):
        k = m.v[p]
        if k > 0:
            lit = 1.15 if p // w < (y0 + y1) / 2 else 0.72
            c.rgb[p] = tw.mix(c.rgb[p], tw.mul(rc, lit), k)
            c.ht[p], c.gloss[p] = 0.62, (70 if kind != 'koa' else 20)
            if cut:
                c.a[p] = max(c.a[p], k)
    return poly


def niho(c, poly, size, colour, inset=None):
    """The shark-tooth border of Polynesian carving (niho mano): a row of triangles just inside the outline, cut in and
    stained."""
    inset = size * 1.2 if inset is None else inset
    w = c.w
    mx = sum(q[0] for q in poly) / len(poly)
    my = sum(q[1] for q in poly) / len(poly)
    tris = []
    for a, b in zip(poly, poly[1:]):
        ln = math.hypot(b[0] - a[0], b[1] - a[1])
        if ln < size:
            continue
        ux, uy = (b[0] - a[0]) / ln, (b[1] - a[1]) / ln
        nx, ny = -uy, ux
        if (mx - a[0]) * nx + (my - a[1]) * ny < 0:
            nx, ny = -nx, -ny
        n = int(ln // size)
        for k in range(n):
            t0 = (ln - n * size) / 2 + k * size
            bx0, by0 = a[0] + ux * t0 + nx * inset, a[1] + uy * t0 + ny * inset
            bx1, by1 = bx0 + ux * size, by0 + uy * size
            tris.append([(bx0, by0), (bx1, by1), ((bx0 + bx1) / 2 + nx * size * 0.9, (by0 + by1) / 2 + ny * size * 0.9)])
    for t in tris:
        fill(c, t, colour, 0.8, ht=0.38)


def fill(c, poly, colour, amount=1.0, ht=None, glow=None, g=None):
    """A filled shape (points, closed or not) painted on Picture c; with glow, lit in glow Picture g too."""
    pts = list(poly) + ([poly[0]] if tuple(poly[0]) != tuple(poly[-1]) else [])
    w = c.w
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    for y in range(max(0, int(min(ys))), min(c.h, int(max(ys)) + 1)):
        for x in range(max(0, int(min(xs))), min(w, int(max(xs)) + 1)):
            if _inside(pts, x + 0.5, y + 0.5):
                p = y * w + x
                c.rgb[p] = tw.mix(c.rgb[p], colour, amount)
                if ht is not None:
                    c.ht[p] = ht
                if c.a is not None:
                    c.a[p] = 1.0
                if glow and g is not None:
                    g.rgb[p] = glow


def _tube_masks(c, g, ink_m, core_m, thick, ink):
    """Neon tubes (ink_m their glass, core_m their hot middle) laid on Picture c; their light into glow Picture g."""
    w, h = c.w, c.h
    sh = ink_m.shifted(int(thick * 0.6), int(thick * 0.9)).blurred(max(1, int(thick * 0.5)), 2)
    halo = ink_m.blurred(max(3, int(thick * 3.2)))           # (wide: the user's 'brighter, bigger glow' to carry through storm fog)
    pale = tw.mix(ink, (240, 240, 236), 0.55)
    for p in range(w * h):
        s = sh.v[p]
        if s > 0.01:
            c.rgb[p] = tw.mul(c.rgb[p], 1 - 0.5 * s)
        k = ink_m.v[p]
        if k > 0:
            col = tw.mix(tw.mul(pale, 0.8), (250, 250, 246), core_m.v[p] * 0.8)
            c.rgb[p] = tw.mix(c.rgb[p], col, k)
            c.ht[p] = 0.5 + 0.3 * k
            c.gloss[p] = 200
        a = max(k, min(0.62, halo.v[p] * 1.1))
        if a > 0.004:
            # (glow map: white-hot core, the tube's own colour through the glass, a faint halo on the board)
            hot = tw.mix(ink, (255, 255, 255), core_m.v[p] * 0.7)
            add = tw.mul(hot if k > 0.2 else ink, a)
            o = g.rgb[p]
            g.rgb[p] = (max(o[0], add[0]), max(o[1], add[1]), max(o[2], add[2]))


def tube_path(c, g, points, thick, ink, closed=False, round_=3):
    """A neon tube along points (pixels): a border, an arrow, a star's rays."""
    pts = list(points) + ([points[0]] if closed else [])
    pts = _round(pts, round_) if round_ and len(pts) > 2 else pts
    ink_m, core_m = Mask(c.w, c.h), Mask(c.w, c.h)
    for a, b in zip(pts, pts[1:]):
        ink_m.capsule(a, b, thick / 2)
        core_m.capsule(a, b, max(0.8, thick * 0.14))
    _tube_masks(c, g, ink_m, core_m, thick, ink)


def rounded(x0, y0, x1, y1, r, steps=6):
    """A rounded rectangle's outline (closed), for a tube border."""
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for k in range(steps + 1):
            a = math.radians(a0 + 90 * k / steps)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts + [pts[0]]


def star(c, g, x, y, r, ink, rays=8, thick=None):
    """A starburst of tubes: rays from a hub, long and short by turns."""
    thick = thick or max(2.0, r / 9)
    for k in range(rays):
        a = math.pi * 2 * k / rays
        ln = r if k % 2 == 0 else r * 0.55
        tube_path(c, g, [(x + math.cos(a) * r * 0.18, y + math.sin(a) * r * 0.18), (x + math.cos(a) * ln, y + math.sin(a) * ln)], thick, ink, round_=0)


def words_on(c, g, words, style, box, ink, outline=None, shadow=True, wear=0.5, seed=1200, glow=False, ink2=None):
    """`words` in `style` fitted in box on Picture c (its glow, if any, into g). ink2: the letters' lower half in another
    shade (the sign-writer's split, light over dark)."""
    w, h = c.w, c.h
    m, thick = letters(words, style, box, w, h)
    ink_m, core_m = m['ink'], m['core']
    if STYLES[style].get('tube') or style == 'tube':
        _tube_masks(c, g, ink_m, core_m, thick, ink)
        return
    rnd = random.Random(seed)
    flake = tw.Field(w, h, seed + 7, cells=16, octaves=4)
    sh = ink_m.shifted(int(thick * 0.35), int(thick * 0.35)) if shadow and style != 'chisel' else None
    ol = ink_m.blurred(max(1, int(thick * 0.12)), 1) if outline else None
    x0, y0, x1, y1 = [int(v) for v in box]
    for y in range(max(0, y0 - 4), min(h, y1 + 8)):
        for x in range(max(0, x0 - 4), min(w, x1 + 8)):
            p = y * w + x
            if sh is not None and sh.v[p] > 0:
                c.rgb[p] = tw.mix(c.rgb[p], (30, 24, 22), 0.85 * sh.v[p])
            if ol is not None and ol.v[p] > 0.02:
                c.rgb[p] = tw.mix(c.rgb[p], outline, min(1.0, ol.v[p] * 3))
            k = ink_m.v[p]
            if k <= 0:
                continue
            if style == 'chisel':
                # (cut in, then painted: the paint's colour, the cut's sides catching the light up and left and shaded down
                # and right, a dark line where the cut meets the face)
                lit = m['lit'].v[p]
                col = tw.mul(ink, 0.62 + 0.62 * lit) if ink else tw.mul(c.rgb[p], 0.55 + 0.75 * lit)
                edge = 1.0 - min(1.0, core_m.v[p] * 2.5 + lit)
                col = tw.mix(col, (40, 22, 14), 0.35 * edge * (1 - k * 0.3))
                c.rgb[p] = tw.mix(c.rgb[p], col, k)
                c.ht[p] = 0.5 - 0.25 * k + 0.1 * lit
                continue
            peel = flake.v[p] > 1 - 0.18 * wear and rnd.random() < 0.9
            col = ink if ink2 is None else (ink if y < (y0 + y1) / 2 + 2 else ink2)
            if style == 'deco':                         # (a light line inside each stroke: the raised letter's edge)
                col = tw.mix(ink, (255, 250, 236), 0.45 * core_m.v[p])
            if peel:
                col = tw.mix(col, c.rgb[p], 0.8)
            c.rgb[p] = tw.mix(c.rgb[p], col, k)
            c.ht[p] = 0.5 + 0.12 * k
            if glow and g:
                g.rgb[p] = tw.mul(ink, k * (0.25 if peel else 1.0))


def weather(c, wear=0.5, seed=1203):
    wr = tw.Wear(c.w, c.h, seed, grime=0.6 * wear, rain=0.8 * wear, bleach=0.2 * wear)
    for p in range(c.w * c.h):
        c.rgb[p] = wr.on(p % c.w, p // c.w, c.rgb[p])


def blank(w, h, board='enamel', ground=(40, 52, 60), seed=1200, box=None, shape='rect', rim=(150, 146, 136)):
    """(colour Picture with a board painted, black glow Picture) to lay words, tubes, stars and pictures on. The board's
    outline is kept as c.outline."""
    c = tw.Picture(w, h, gloss=24)
    c.outline = _board(c, board, ground, box or (0, 0, w, h), seed, shape, rim)
    g = tw.Picture(w, h, gloss=0)
    g.rgb = [(0, 0, 0)] * (w * h)
    return c, g


def lit_any(g):
    return any(px != (0, 0, 0) for px in g.rgb)


def sign(words, style='tube', board='enamel', ground=(40, 52, 60), ink=(255, 80, 96), w=1024, h=256, seed=1200,
         outline=None, shadow=True, wear=0.5, box=None, glow=False):
    """(colour Picture, glow Picture or None): `words` in `style` on a `board` of `ground` colour filling w x h (or box).
    ink: the letters' paint, or a tube's light. outline: a colour drawn round each letter (deco, brush). wear: 0-1 how
    far the weather has got. glow: whether painted letters light too (tubes always do)."""
    bx = box or (0, 0, w, h)
    c, g = blank(w, h, board, ground, seed, bx)
    pad = (bx[3] - bx[1]) * 0.16
    if style != 'tube':
        words_on(c, g, words, style, (bx[0] + pad, bx[1] + pad, bx[2] - pad, bx[3] - pad), ink, outline, shadow, wear, seed, glow)
        weather(c, wear, seed + 3)
    else:
        weather(c, wear * 0.6, seed + 3)
        words_on(c, g, words, style, (bx[0] + pad, bx[1] + pad, bx[2] - pad, bx[3] - pad), ink)
    return c, (g if lit_any(g) else None)


def glow_files(g):
    """The glow picture's DDS (colour only, as the game's _g pictures)."""
    import dds
    cl = lambda v: 0 if v < 0 else 255 if v > 255 else int(v + 0.5)
    raw = bytearray()
    for r, gg, b in g.rgb:
        raw += bytes((cl(r), cl(gg), cl(b), 255))
    return dds.compress(dds.encode(g.w, g.h, bytes(raw)))


# ---------- looking at one ----------

def preview(c, g, mult=4.0, fog=(118, 122, 128), fog_amount=0.55, night_sky=(16, 20, 32)):
    """RGB rows of three looks one above the other: day (the colour picture as graded), night (moonlight on it plus the
    glow times mult, a little bloom), storm (night through haze of fog_amount)."""
    w, h = c.w, c.h
    day = [tw.grade(col) for col in c.rgb]
    if g:
        bloom = Mask(w, h)
        bloom.v = [sum(px) / 765.0 for px in g.rgb]
        bloom = bloom.blurred(max(2, h // 40))
    night, storm = [], []
    for p in range(w * h):
        base = tw.mul(c.rgb[p], 0.1)
        base = (base[0] * 0.8, base[1] * 0.9, base[2] * 1.3)
        if g:
            gl = g.rgb[p]
            b = bloom.v[p] * 0.6 * mult
            col = (base[0] + gl[0] * mult * 0.35 + b * 60, base[1] + gl[1] * mult * 0.35 + b * 55, base[2] + gl[2] * mult * 0.35 + b * 55)
        else:
            col = base
        night.append(col)
        storm.append(tw.mix(col, tw.mul(fog, 0.35), fog_amount) if not g else
                     tw.mix(col, tw.mul(fog, 0.35), fog_amount * (1 - min(0.6, bloom.v[p] * mult * 0.3))))
    return [day, night, storm]


def png(rows_sets, w, path, gap=8, back=(24, 24, 24)):
    """Writes several w-wide pictures (lists of RGB) one above the other to a PNG."""
    import meshthumb
    cl = lambda v: 0 if v < 0 else 255 if v > 255 else int(v + 0.5)
    out = bytearray()
    hs = 0
    for k, rows in enumerate(rows_sets):
        for col in rows:
            out += bytes((cl(col[0]), cl(col[1]), cl(col[2]), 255))
        hs += len(rows) // w
        if k < len(rows_sets) - 1:
            out += bytes((back[0], back[1], back[2], 255)) * (w * gap)
            hs += gap
    with open(path, 'wb') as f:
        f.write(meshthumb.png_rgba(w, hs, bytes(out)))
