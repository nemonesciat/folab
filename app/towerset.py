"""The city's great tower, of FOLab's own: The Kilauea, a hotel and casino of the atomic age as tall and as grand as
the Strip's Lucky 38 (which stood here before: the Lucky 38 is the Strip's own and read as a piece of Vegas dropped on
the beach), with a volcano for a crown.

From the ground up: a plinth of lava rock; the casino, a glass drum under a frieze of glass mosaic in the colours of a
lava flow, a butterfly canopy over its drive; a ribbed shaft of rooms, three buttress fins stepping in up its sides
like the flanks of a mountain, the front one carrying the name down a blade of marquee bulbs; a flared gold crown with
the observation deck's ring of glass under its brim; a second band of mosaic; a cone of glazed red tiles going up to
a crater where a flame of amber glass stands lit; a spire.

Its own worn pictures (texwear's layers): `mosaic` (small glass tiles, grout, tiles fallen to the bed), `shaft`
(concrete ribs, gold spandrels, each of 128 windows its own state), `gold` (anodised panels, seams and rivets, dulled
brown and run with verdigris), `amber` (leaded glass in a web of lead, some panes gone). Everything else is
resortset's. Frame as every modelsets piece: the foot's middle at the origin, z up, front (the drive, the blade's
fin) towards -y, 70 units a metre. Registered into modelsets at import (set 'resort'); `landmarks.SETS['kilauea']`
stands it."""
import math
import random

import modelsets
import resortset
import texpaint as tp
import texwear as tw
import waikikiset
from modelsets import look
from texwear import Field, Cells, Picture, Wear, grade, mix, mul, smooth

GOLD = (176, 140, 72)
LAVA_TILES = [(44, 38, 36), (116, 32, 24), (176, 62, 30), (220, 120, 40), (236, 190, 82), (222, 132, 44), (184, 70, 32), (122, 36, 26)]


# ---------- its own pictures ----------

def mosaic(size=512, seed=700, across=32, palette=LAVA_TILES):
    """A frieze of small glass tiles set in waves of a lava flow's colours (each tile one colour, a shade its own),
    the grout gone dark, whole patches of tiles fallen to the combed mortar bed behind; rain dirt run down from the
    top. Repeats at its edges."""
    c = Picture(size, size, gloss=90)
    wr = Wear(size, size, seed, grime=0.9, rain=1.0, ledges=(0.0,), bleach=0.15)
    lost = Field(size, size, seed + 10, cells=6, octaves=4)
    rnd = random.Random(seed)
    t = size / float(across)
    shade = [rnd.uniform(-0.09, 0.09) for _ in range(across * across)]
    dull = [rnd.random() for _ in range(across * across)]
    for y in range(size):
        j = int(y / t)
        v = (y % t) / t
        for x in range(size):
            i = int(x / t)
            u = (x % t) / t
            p = y * size + x
            f = wr.fine.v[p]
            cx, cy = (i + 0.5) / across, (j + 0.5) / across
            band = (cy * 3 + 0.16 * math.sin(2 * math.pi * cx * 2) + 0.07 * math.sin(2 * math.pi * (cx * 3 + cy))) % 1.0
            k = j * across + i
            col = mul(palette[int(band * len(palette)) % len(palette)], 1 + shade[k])
            h, g, depth = 0.55 + 0.1 * (1 - 2 * max(abs(u - 0.55), abs(v - 0.55))), 120 if dull[k] > 0.3 else 50, 0.0
            if u < 0.1 or v < 0.1:                                  # the grout, dirt in it
                col, h, g, depth = mul((136, 128, 114), 0.75 + 0.25 * f), 0.35, 8, 0.5
            centre = lost.v[int((j + 0.5) * t) % size * size + int((i + 0.5) * t) % size]
            if centre > 0.74:                                        # fallen: the bed, combed, a tile's ghost in it
                col = mul((150, 144, 130), 0.7 + 0.2 * f + 0.1 * math.sin((x + y) * 1.3))
                h, g, depth = 0.25, 6, 0.6
                if centre < 0.77 and (u < 0.2 or v < 0.2):
                    col = mul(col, 0.7)                              # (the edge of what is still there)
            c.rgb[p], c.ht[p], c.gloss[p] = grade(wr.on(x, y, col, depth)), h, g
    return c


SHAFT_STATES = (('dark', 6), ('sky', 3), ('curtain', 3), ('broken', 2), ('gone', 1), ('boarded', 1))


def shaft(size=1024, seed=720, ribs=16, floors=8):
    """The tower's rooms between concrete ribs: a rib, then a window a floor tall with a gold spandrel panel over it,
    each of ribs x floors windows its own (dark, the sky in it, curtains, cracked, gone, boarded); rust from the
    spandrels' bolts, rain from every floor."""
    c = Picture(size, size, gloss=30)
    cw, ch = size / float(ribs), size / float(floors)
    rnd = random.Random(seed)
    picks = [k for k, n in SHAFT_STATES for _ in range(n)]
    state = [[rnd.choice(picks) for _ in range(ribs)] for _ in range(floors)]
    pane = [[rnd.uniform(0.85, 1.2) for _ in range(ribs)] for _ in range(floors)]
    irons = [(int(i * cw + cw * (0.4 + 0.45 * k)), int(j * ch + ch * 0.2)) for j in range(floors) for i in range(ribs) for k in (0, 1) if rnd.random() < 0.5]
    wr = Wear(size, size, seed, grime=1.0, rain=1.1, ledges=[j / float(floors) for j in range(floors)], irons=irons, bleach=0.15)
    glassn = Field(size, size, seed + 11, cells=40, octaves=2)
    crk = tw.cracks(size, size, seed + 12, count=14, long=0.2, width=1.2)
    rib_col = tp._faded((200, 194, 180), 0.1)
    for y in range(size):
        j = int(y / ch)
        v = (y % ch) / ch
        for x in range(size):
            i = int(x / cw)
            u = (x % cw) / cw
            p = y * size + x
            f, m = wr.fine.v[p], wr.mid.v[p]
            st = state[j][i]
            if u < 0.3:                                             # the rib, standing out, its sides in shade
                col, h, g, depth = mul(rib_col, 0.9 + 0.12 * m + 0.06 * (f - 0.5)), 0.72, 18, 0.0
                if u < 0.04 or u > 0.26:
                    col, h, depth = mul(col, 0.72), 0.6, 0.3
                if crk[p] > 0.05:
                    col, h, depth = mix(col, mul(tw.GRIME, 0.6), crk[p]), 0.6, 1.0
            elif v < 0.24:                                          # the gold spandrel over the window
                col, h, g, depth = mul(GOLD, 0.8 + 0.2 * m), 0.55, 70, 0.2
                if v < 0.02 or v > 0.22 or abs((u - 0.3) / 0.7 - 0.5) < 0.008:
                    col, h, g = mul(col, 0.55), 0.45, 20
                if wr.big.v[p] > 0.58:
                    col, g = mix(col, (104, 82, 50), 0.6), 25                      # dulled
                if wr.runs.v[p] > 0.62:
                    col = mix(col, (96, 140, 118), 0.4)                           # verdigris run
            else:
                gu, gv = (u - 0.3) / 0.7, (v - 0.24) / 0.76
                if gu < 0.04 or gu > 0.96 or abs(gv - 0.55) < 0.015:
                    col, h, g, depth = mul(tp.ALUMINIUM, 0.65 + 0.3 * f), 0.5, 60, 0.4
                else:
                    glare = 0.8 + 0.5 * max(0.0, 1 - abs((gu - gv * 0.4) - 0.3) * 5)
                    col = mul(tp.GLASS_DARK, glare * pane[j][i] * (0.85 + 0.3 * glassn.v[p]))
                    col = mix(col, (150, 160, 158), (0.45 if st == 'sky' else 0.22) * (1 - gv) ** 2)
                    h, g, depth = 0.3, 140, 0.5
                    if st == 'curtain' and (gu > 0.6 or gu < 0.15):
                        col, g = mix(col, mul((190, 172, 140), 0.65 + 0.2 * math.sin(gu * 70)), 0.6), 50
                    elif st == 'broken':
                        rr = math.hypot(gu - 0.6, gv - 0.35)
                        a = math.atan2(gv - 0.35, gu - 0.6)
                        if rr < 0.4 and abs(math.sin(a * 3.5 + i + 3 * rr)) < 0.03 / max(rr, 0.06):
                            col = mix(col, (206, 208, 200), 0.5)
                    elif st == 'gone':
                        col, h, g = mul((18, 18, 17), 0.8 + 0.4 * f), 0.1, 0
                    elif st == 'boarded':
                        k = int(gu * 3)
                        col = mul(mix(tw.SILVER_WOOD, (150, 128, 96), (k * 0.41) % 1), 0.75 + 0.3 * wr.runs.v[p])
                        h, g = (0.3, 10) if (gu * 3) % 1 < 0.06 else (0.6, 10)
            c.rgb[p], c.ht[p], c.gloss[p] = grade(wr.on(x, y, col, depth)), h, g
    return c


def gold(size=256, seed=740, panels=4):
    """Gold-anodised aluminium cladding two centuries on: panels with dark seams and rivets along them, the gold
    gone brown in patches and chalky in others, green verdigris run down from every seam."""
    c = Picture(size, size, gloss=70)
    step = size / float(panels)
    wr = Wear(size, size, seed, grime=0.6, rain=1.0, ledges=[k / float(panels) for k in range(panels)])
    ox = Field(size, size, seed + 10, cells=4, octaves=5, fall=0.6)
    chalk = Field(size, size, seed + 11, cells=10, octaves=3)
    rnd = random.Random(seed)
    tint = [rnd.uniform(-0.07, 0.07) for _ in range(panels * panels)]
    for y in range(size):
        for x in range(size):
            p = y * size + x
            f = wr.fine.v[p]
            i, j = int(x / step), int(y / step)
            u, v = x % step, y % step
            col = mul(GOLD, 0.88 + tint[j * panels + i] + 0.12 * wr.mid.v[p] + 0.06 * (f - 0.5))
            h, g, depth = 0.55 + 0.03 * f, 80, 0.0
            if ox.v[p] > 0.6:
                col, g = mix(col, (104, 80, 48), smooth(0.6, 0.8, ox.v[p]) * 0.8), 30
            if chalk.v[p] > 0.74:
                col, g = mix(col, (196, 182, 150), 0.5), 15
            if u < 2 or v < 2:                                  # a seam
                col, h, g, depth = mul(col, 0.45), 0.35, 20, 0.8
            elif (u < 7 or v < 7) and math.hypot((u if u < 7 else 3.5) - 4.5, (v if v < 7 else (v % 14)) - 4.5) < 1.8 and (v % 14 < 7 if u < 7 else u % 14 < 7):
                col, h, g = mul(col, 1.15), 0.72, 110            # a rivet
            if wr.rain_at(x, y) > 0.35:
                col = mix(col, (92, 136, 116), 0.45 * wr.rain_at(x, y))
            c.rgb[p], c.ht[p], c.gloss[p] = grade(wr.on(x, y, col, depth)), h, g
    return c


def amber(size=256, seed=760):
    """Leaded amber glass, the flame's: panes from orange to yellow, brighter at their middles, in a web of lead,
    one in eight gone dark."""
    c = Picture(size, size, gloss=150)
    cl = Cells(size, size, seed, n=9, jitter=1.0)
    rnd = random.Random(seed)
    tones = [(244, 150, 40), (252, 196, 74), (226, 96, 32), (250, 170, 56)]
    which = [rnd.randrange(len(tones)) for _ in range(81)]
    gone = {k for k in range(81) if rnd.random() < 0.12}
    grime = Field(size, size, seed + 1, cells=4, octaves=4)
    for p in range(size * size):
        e = cl.edge(p)
        k = cl.id[p]
        if e < 0.07:
            col, h, g = mul((54, 52, 48), 0.8 + 0.4 * grime.v[p]), 0.7, 40
        elif k in gone:
            col, h, g = (24, 20, 16), 0.2, 0
        else:
            col = mul(tones[which[k]], 0.75 + 0.35 * min(1.0, e * 2.2))
            col = mix(col, (90, 70, 40), 0.3 * smooth(0.55, 0.9, grime.v[p]))
            h, g = 0.5, 150
        c.rgb[p], c.ht[p], c.gloss[p] = grade(col, sat=0.9, lift=4.0), h, g
    return c


def _signs():
    return tw.sign_aged([{'box': (0, 0, 1, 0.5), 'lines': ['KILAUEA'], 'ground': tp.RED, 'ink': tp.CREAM, 'edge': resortset.YELLOW},
                         {'box': (0, 0.5, 1, 1), 'lines': ['CASINO'], 'ground': tp.CREAM, 'ink': tp.RED, 'edge': tp.RED}],
                        w=1024, h=512, seed=780, bulbs=True)


modelsets.TEXTURES.update({
    'resort/kil_mosaic': lambda: mosaic(seed=700),
    'resort/kil_shaft': lambda: shaft(seed=720),
    'resort/kil_gold': lambda: gold(seed=740),
    'resort/kil_amber': lambda: amber(seed=760),
    'resort/kil_tiles': lambda: tw.clay_tiles(size=512, seed=770, colour=(132, 40, 28)),
    'resort/kil_fins': lambda: tw.concrete((200, 194, 180), size=512, seed=775, boards=8, spalls=0.35),
    'resort/kil_signs': _signs,
    'resort/kil_far_shaft': lambda: tw.far_sheet(wall=(200, 194, 180), bays=16, floors=8, size=128, seed=785),
    'resort/kil_far_mosaic': lambda: tw.far_plain((176, 84, 40), seed=786),
    'resort/kil_far_gold': lambda: tw.far_plain((150, 118, 64), seed=787),
    'resort/kil_far_tiles': lambda: tw.far_plain((112, 40, 30), seed=788),
})


def _looks():
    out = resortset._looks()
    out.update({
        'mosaic': dict(look('resort/kil_mosaic', tile=640, far='resort/kil_far_mosaic'), gloss=60),
        'shaft': look('resort/kil_shaft', tile=2048, far='resort/kil_far_shaft'),
        'gold': dict(look('resort/kil_gold', tile=512, far='resort/kil_far_gold'), gloss=50),
        'tiles': look('resort/kil_tiles', tile=420, far='resort/kil_far_tiles'),
        'fins': look('resort/kil_fins', tile=700, far='resort/far_white'),
        'flame': waikikiset.lit('resort/kil_amber', 3.0),
        'blade': modelsets.neon('resort/kil_signs', 8.0, region=(0, 0, 1, 0.5), turned=True),     # (its neon: signsheets.kil_signs)
        'casino': modelsets.neon('resort/kil_signs', 8.0, region=(0, 0.5, 1, 1)),
    })
    out['deck_glass'] = dict(out['glass'])
    return out


# ---------- the tower ----------

PLINTH, DRUM, FRIEZE = 140, 900, 260
LIFT_AT, LIFT_K = 436, 1 / 0.8         # (the lifts on the core, -y, as hotelinside.KIL_DOORS; the frames fit the door at the Kilauea's 0.8)
SHAFT_R, SHAFT_H = 1100, 4900
FIN_STEPS, FIN_STEP = 8, 600
CROWN = SHAFT_H


def _ring(parts, r, h, z, look_name, sides=24, cap=None, r2=None, solid=False, far=False, caps=True):
    p = {'shape': 'cylinder', 'r': r, 'h': h, 'sides': sides, 'at': [0, 0, z], 'look': look_name, 'material': 'stone', 'solid': solid, 'far': far}
    if r2 is not None:
        p['r2'] = r2
    if cap is not None:
        p['cap_look'] = cap
    if not caps:
        p['caps'] = False
    parts.append(p)


def _glass_wall(parts, r, h, z, n=24):
    """What stops you at a round wall of glass: n boxes round its chords, nothing to see (the glass is its own part)."""
    chord = 2 * r * math.sin(math.pi / n) + 12
    for k in range(n):
        a = 360.0 / n * (k + 0.5)
        parts.append({'shape': 'box', 'size': [chord, 30, h], 'at': [math.cos(math.radians(a)) * r, math.sin(math.radians(a)) * r, z],
                      'turn': [0, 0, a + 90], 'look': None, 'material': 'glass', 'solid': True,      # (no look: nothing draws it)
                      'faces': {f: None for f in ('front', 'back', 'left', 'right', 'top', 'bottom')}})


def _round(r, deg):
    return math.cos(math.radians(deg)) * r, math.sin(math.radians(deg)) * r


def kilauea(open_=False):
    """The Kilauea: see the module's docstring. open_: for its own small world (viewworld.py), the casino and the
    observation deck inside: their glass seen through from both sides, a lift core in the middle of each."""
    import hotelinside
    parts = []
    # the plinth and its lava-rock planters
    _ring(parts, 3500, PLINTH, 0, 'lava', cap='terrazzo', solid=True, far=True)
    for k in range(12):
        a = math.radians(15 + 30 * k)
        parts.append({'shape': 'box', 'size': [320, 320, 220], 'at': [math.cos(a) * 3260, math.sin(a) * 3260, PLINTH], 'turn': [0, 0, 15 + 30 * k],
                      'look': 'lava', 'faces': {'top': 'tar'}, 'material': 'stone'})
    # the casino: glass all round, the frieze over it, a deck on its roof
    if open_:
        _ring(parts, 2900, DRUM, PLINTH, 'kil_clear', far=True, caps=False)
        parts[-1]['under'] = True
        _glass_wall(parts, 2900, DRUM, PLINTH)
        _ring(parts, 2890, 4, PLINTH + DRUM - 46, 'kil_ceiling', cap='kil_ceiling')
        _ring(parts, 420, DRUM, PLINTH, 'gold', sides=12, solid=True)            # (the lift core)
        hotelinside.lift_frame(parts, 0, -LIFT_AT, PLINTH, 180, 'gold', LIFT_K, back=60)
    else:
        # (the casino as the town sees it, hotelinside: what stops you as it always was, drawn by nothing but its floor
        # and roof; the open piece's glass, ceiling and lift core in front of it, lit, and its slot machines lit)
        import hotelinside as hi
        # (its far picture in the far model only: in the model itself it lay on the glass and flickered, 17 Nov 2026;
        # what stops you is the glass's own walls, nothing to see, and its roof a slab a hair wider than the glass)
        _ring(parts, 2900, DRUM, PLINTH, 'kil_hide', cap='terrazzo')
        parts[-1].update(far_only=True)
        _glass_wall(parts, 2900, DRUM, PLINTH)
        _ring(parts, 2906, 16, PLINTH + DRUM - 16, 'terrazzo', cap='terrazzo', solid=True)      # (thinner doesn't close as a solid)

        def room(P):
            _ring(P, 2900, DRUM, PLINTH, 'kil_clear', caps=False)
            P[-1]['under'] = True
            _ring(P, 2890, 4, PLINTH + DRUM - 46, 'kil_ceiling', cap='kil_ceiling')
            _ring(P, 420, DRUM, PLINTH, 'gold', sides=12)
            hi.lift_frame(P, 0, -LIFT_AT, PLINTH, 180, 'gold', LIFT_K, back=60)
            for r in (2200, 1500):
                _ring(P, r, 190, PLINTH, 'kil_slots', sides=48, caps=False)
                P[-1]['under'] = True
        hi.shown(parts, room)
        hi.lamps(parts, [_round(1100, d) for d in (90, 210, 330)] + [(0, -1200), (0, 1200)], PLINTH + DRUM - 46)
    _ring(parts, 2960, FRIEZE, PLINTH + DRUM - 40, 'mosaic', cap='terrazzo', far=True)
    _ring(parts, 3080, 36, PLINTH + DRUM + FRIEZE - 60, 'gold', cap='gold')
    deck = PLINTH + DRUM + FRIEZE - 40
    for k in range(24):                                     # gold mullions down the glass
        a = math.radians(7.5 + 15 * k)
        parts.append({'shape': 'box', 'size': [60, 60, DRUM - 40], 'at': [math.cos(a) * 2910, math.sin(a) * 2910, PLINTH], 'turn': [0, 0, 7.5 + 15 * k],
                      'look': 'gold', 'solid': False})
    # its name over the drive
    parts.append({'shape': 'box', 'size': [1800, 40, 400], 'at': [0, -3010, PLINTH + DRUM - 30], 'look': 'gold', 'faces': {'front': 'casino'}, 'solid': False, 'far': True})
    # the butterfly canopy over the drive, on a spine and two gold posts
    for side in (-1, 1):
        parts.append({'shape': 'slab', 'size': [1300, 1700, 28], 'at': [side * 640, -3900, 640 + 110], 'turn': [0, -side * 9.0, 0], 'look': 'white',
                      'faces': {'bottom': 'gold'}, 'solid': False})
    parts.append({'shape': 'box', 'size': [120, 1700, 60], 'at': [0, -3900, 620], 'look': 'gold', 'solid': False})
    for y in (-3250, -4550):
        parts.append({'shape': 'cylinder', 'r': 50, 'h': 620, 'sides': 8, 'at': [0, y, 0], 'look': 'gold', 'material': 'metal'})
    # the shaft and a slab ring every four floors
    _ring(parts, SHAFT_R, SHAFT_H - deck, deck, 'shaft', sides=12, cap='tar', solid=True, far=True)
    for z in range(deck + 1024, SHAFT_H, 1024):
        _ring(parts, SHAFT_R + 60, 24, z, 'concrete', sides=12)
    # three fins stepping in up its flanks, one to the front
    for a in (270.0, 30.0, 150.0):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        for k in range(FIN_STEPS):
            r_out = 3350 - k * 285
            r_in = SHAFT_R - 60
            z0 = PLINTH + k * FIN_STEP
            mid = (r_in + r_out) / 2.0
            parts.append({'shape': 'box', 'size': [r_out - r_in, 280, FIN_STEP + (0 if k < FIN_STEPS - 1 else 300)], 'at': [ca * mid, sa * mid, z0], 'turn': [0, 0, a],
                          'look': 'fins', 'faces': {'right': 'gold' if k % 2 else 'fins', 'top': 'tar'}, 'material': 'stone', 'far': True})
    # the blade with the name, off the front fin, on brackets
    blade_in, blade_z0, blade_h = 2800, PLINTH + 2 * FIN_STEP + 140, 3600
    parts.append({'shape': 'box', 'size': [44, 520, blade_h], 'at': [0, -(blade_in + 260), blade_z0], 'look': 'gold',
                  'faces': {'left': 'blade', 'right': 'blade'}, 'solid': False, 'far': True})
    for k in range(4):
        z = blade_z0 + 300 + k * 1000
        r_fin = 3350 - (int((z - PLINTH) // FIN_STEP)) * 285
        parts.append({'shape': 'box', 'size': [30, blade_in - r_fin + 20, 40], 'at': [0, -(r_fin + blade_in) / 2.0, z], 'look': 'grey', 'solid': False})
    # the crown: a gold flare, the observation ring under its brim, mosaic, the volcano, its flame and spire
    z = CROWN
    _ring(parts, SHAFT_R, 600, z, 'gold', r2=1950, caps=False, far=True)
    z += 600
    if open_:
        _ring(parts, 1950, 480, z, 'kil_clear', far=True, caps=False)
        parts[-1]['under'] = True
        _glass_wall(parts, 1950, 480, z)
        _ring(parts, 1950, 24, z - 12, 'gold', cap='terrazzo', solid=True)         # (its floor)
        _ring(parts, 1945, 4, z + 470, 'kil_ceiling', cap='kil_ceiling')
        _ring(parts, 420, 480, z, 'gold', sides=12, solid=True)
        hotelinside.lift_frame(parts, 0, -LIFT_AT, z + 12, 180, 'gold', LIFT_K, back=60)     # (on the deck's floor)
    else:
        _ring(parts, 1950, 480, z, 'deck_glass', cap='terrazzo', solid=True, far=True)
    for k in range(24):
        a = math.radians(15 * k)
        parts.append({'shape': 'box', 'size': [50, 50, 480], 'at': [math.cos(a) * 1960, math.sin(a) * 1960, z], 'turn': [0, 0, 15 * k], 'look': 'gold', 'solid': False})
    z += 480
    _ring(parts, 2220, 90, z, 'gold', r2=2100, far=True)
    z += 90
    _ring(parts, 1550, 340, z, 'mosaic', cap='tar', far=True)
    z += 340
    _ring(parts, 1550, 1000, z, 'tiles', r2=500, cap='lava', sides=16, far=True)
    z += 1000
    _ring(parts, 560, 130, z, 'lava', cap='lava', sides=12, far=True)
    z += 130
    flame = z
    parts.append({'shape': 'cone', 'r': 320, 'h': 1350, 'sides': 10, 'at': [0, 0, z - 40], 'look': 'flame', 'solid': False, 'far': True})
    for k in range(3):
        a = 90 + 120 * k
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        parts.append({'shape': 'cone', 'r': 200, 'h': 850, 'sides': 8, 'at': [ca * 260, sa * 260, z - 40], 'turn': [-sa * 14, ca * 14, 0],
                      'look': 'flame', 'solid': False, 'far': True})
    parts.append({'shape': 'cylinder', 'r': 46, 'r2': 8, 'h': 1000, 'sides': 6, 'at': [0, 0, z + 900], 'look': 'gold', 'solid': False, 'far': True})
    lk = _looks()
    lk['kil_clear'] = dict(look('hist/rhl_glass', tile=400), alpha='blend')      # (blended glass: nifmake.ALPHA_BLEND)
    lk['kil_ceiling'] = look('hist/rhl_ceiling', tile=512)
    lk['lobby_lamp'] = hotelinside._lamp_look()       # (over the lifts)
    if open_:
        hotelinside.looks()                 # (its pictures registered)
    else:
        lk.update({k: v for k, v in hotelinside.shown_looks().items() if k not in lk})
    return {'name': 'FOLabLandmarkKilauea' + ('Open' if open_ else ''), 'looks': lk, 'parts': parts, 'flame': flame, 'deck': deck}


STEPS_N, STEPS_RISE, STEPS_TREAD, STEPS_WIDE, STEPS_INTO = 7, 15.4, 34, 420, 120


def kilauea_steps():
    """Steps from the street up the Kilauea's plinth at its door (the user, 22 Nov 2026: "the kilauea needs stairs leading
    up its platform by the door"). Its frame: the plinth's face along x at y 0, the steps coming down towards -y (front),
    z 0 the street; STEPS_N risers of STEPS_RISE (the plinth stands 140 x 0.8 = 112 over its foot, 107 over the street there),
    each a solid block from a little under the street, the top one reaching STEPS_INTO into the plinth."""
    parts = []
    for k in range(STEPS_N):
        out = (STEPS_N - k) * STEPS_TREAD
        y0, y1 = -out, STEPS_INTO
        parts.append({'shape': 'box', 'size': [STEPS_WIDE, y1 - y0, (k + 1) * STEPS_RISE + 16], 'at': [0, (y0 + y1) / 2.0, -16],
                      'look': 'lava', 'faces': {'top': 'terrazzo'}, 'material': 'stone', 'solid': True})
    lk = _looks()
    return {'name': 'FOLabKilaueaSteps', 'looks': {k: lk[k] for k in ('lava', 'terrazzo')}, 'parts': parts}


PIECES = {'kilauea': ('The Kilauea', kilauea), 'kilauea_open': ('The Kilauea, open', lambda: kilauea(open_=True)),
          'kilauea_steps': ('The Kilauea\'s steps', kilauea_steps)}
_flame = kilauea()['flame']
waikikiset.LIGHTS.update({
    'kilauea': [('NVLightNeonRed', 0, 0, _flame + 500), ('StripLightKeyNeutral', 0, -3100, PLINTH + 2 * FIN_STEP + 1900),
                ('ExtLightWarm02', 0, -3900, 560), ('ExtLightWarm02', 0, -3300, PLINTH + DRUM)],
})
waikikiset.LIGHTS['kilauea_open'] = waikikiset.LIGHTS['kilauea']
for _k, (_label, _fn) in PIECES.items():
    modelsets.PIECES.setdefault(_k, {'label': _label, 'set': 'resort', 'file': _k, 'describe': _fn, 'edid': _fn()['name']})
