"""Waikiki at night: torches, lanterns, strings of lanterns and of bulbs, oil lamps and fire pits where people are (the
user, 21 Nov 2026: "especially the ideas with lights. tiki torches, lanterns, strings of lanterns or lights, etc. a reason
for power to be useful"). Ideas for what power could mean in play: docs/waikiki-night-lights.md.

PIECES. FOLab's own (modelsets, set 'night': meshes\\folab\\night, textures\\folab\\night), each in two versions: the lit
one (its bulbs, glass, paper and coals glowing: a glow picture in the texture set's third slot and the material's
emissive, nifmake's way, as modelsets.neon) and its day twin (`_day`: the same model, nothing glowing). Flames are the
game's own animated fire stood with the lit torches and fire pits (`FLAMES`), never drawn cards (modelsets.drawn_fires). Hung pieces
(lanterns, oil lamps) have their origin at the hook, the body below; strings run from their origin along +x to the far
hook (`string`: a catenary sized to the gap, made per gap). Nothing here is big enough for the far view: no far models,
as the game's own lamps have none (and nothing see-through goes into one).

ON AT DUSK. Every lit piece and every light is a child of one persistent disabled marker, FOLabNightLights (enable
parent); every day twin is its child the opposite way. FOLabNightLightsQuest's script enables the marker from `DUSK`
to `DAWN` and disables it by day, so by day the twins stand, unlit and costing no light.

POWER. Places with power (`POWERED`: the Royal Hawaiian, the Kahuna's court; the Moana; the Kilauea) get strings of
bulbs on poles and a generator to run them; everywhere else lights with fire: torches, fire pits, paper lanterns,
oil lamps.

BUDGET. Real lights (the game's LIGH) cost the most: none within `LIGHT_APART` of another (the world's own counted),
at most `CELL_LIGHTS` new ones in a cell; a lit piece that can't have one still glows. Draws: at most `CELL_DRAWS` new
draws (shapes) a cell.

`plan(gd, pr, world, cover)` -> (ops, report), one Undo; it writes the pieces' files into the mod's own folder (as
every set does) and nothing else."""
import math
import random

import modelmake
import modelsets
import texpaint as tp
from modelsets import look

SET = 'night'
DUSK, DAWN = 19.0, 6.0          # (game hours: the island's sun sets near seven)
MARKER = 'FOLabNightLights'
SCRIPT = 'FOLabNightLightsScript'
QUEST = 'FOLabNightLightsQuest'
LIGHT_APART = 900.0             # (waikikiset's: no two lights nearer)
CELL_LIGHTS = 4
CELL_DRAWS = 90
POWERED = ('royal_hawaiian', 'moana', 'kilauea')
PAPER = ((214, 58, 44), (236, 222, 190), (232, 150, 58))      # red, white, amber


# ---------- pictures ----------

def paper(colour, size=128, ribs=8, seed=900):
    """Lantern paper over bamboo ribs: the paper a little mottled, the ribs across it darker; its glow picture the
    paper lit from inside (bright, warmer at the middle), the ribs dark against it."""
    rnd = random.Random(seed)
    spots = [(rnd.random() * size, rnd.random() * size, 4 + rnd.random() * 10) for _ in range(30)]
    c, g = tp.Canvas(size, size), tp.Canvas(size, size)

    def rib(y):
        return abs(((y / size) * ribs) % 1.0 - 0.5) > 0.44

    def fn(x, y):
        m = 1.0 - 0.06 * sum(1 for sx, sy, r in spots if (x - sx) ** 2 + (y - sy) ** 2 < r * r)
        if rib(y):
            return (tuple(v * 0.45 for v in colour), 0.8)
        return (tuple(v * m for v in colour), 0.5)

    def gfn(x, y):
        if rib(y):
            return ((30, 18, 8), 0.5)
        t = 1.0 - min(1.0, abs(y - size / 2.0) / (size / 2.0))
        warm = (255, 214, 150)
        return (tuple(0.55 * colour[i] + 0.45 * warm[i] * (0.7 + 0.3 * t) for i in range(3)), 0.5)
    c.paint(fn)
    g.paint(gfn)
    c.glow = g
    return c


def glass(size=64, seed=905):
    """A lamp chimney's glass, smoked at the top; its glow the flame's light through it."""
    c, g = tp.Canvas(size, size), tp.Canvas(size, size)
    c.paint(lambda x, y: (tp._mix((250, 220, 160), (120, 96, 70), max(0.0, 1 - y / (size * 0.35)) * 0.8), 0.5))
    g.paint(lambda x, y: (tp._mix((255, 210, 130), (60, 40, 20), max(0.0, 1 - y / (size * 0.35))), 0.5))
    c.glow = g
    return c


def bulb(size=32, seed=906):
    """A bulb: warm white glass, its glow nearly white."""
    c, g = tp.Canvas(size, size), tp.Canvas(size, size)
    c.paint(lambda x, y: ((246, 236, 206), 0.5))
    g.paint(lambda x, y: ((255, 236, 190), 0.5))
    c.glow = g
    return c


def embers(size=64, seed=907):
    """Coals in a fire pit: black and grey ash with red-orange coals; the coals glow."""
    rnd = random.Random(seed)
    n = tp.Noise(seed, 6)
    c, g = tp.Canvas(size, size), tp.Canvas(size, size)
    hot = lambda x, y: max(0.0, n.at(x * 6.0 / size, y * 6.0 / size) - 0.55) * 3.0
    c.paint(lambda x, y: (tp._mix((40, 36, 34), (230, 90, 30), min(1.0, hot(x, y))), 0.4 + 0.2 * rnd.random()))
    g.paint(lambda x, y: (tp._mix((0, 0, 0), (255, 110, 30), min(1.0, hot(x, y))), 0.5))
    c.glow = g
    return c


modelsets.TEXTURES.update({
    'night/paper_red': lambda: paper(PAPER[0], seed=901),
    'night/paper_white': lambda: paper(PAPER[1], seed=902),
    'night/paper_amber': lambda: paper(PAPER[2], seed=903),
    'night/glass': lambda: glass(),
    'night/bulb': lambda: bulb(),
    'night/embers': lambda: embers(),
    'night/enamel_green': lambda: tp.painted_metal((70, 104, 78), seed=908, rust=0.3),
    'night/cable': lambda: tp.painted_metal((30, 30, 30), size=32, seed=909, rust=0.05),
})


def lit(name, mult, alpha=False, **how):
    """A look lit by its picture's own glow (night) - `day` takes it off."""
    d = dict(look(name, alpha=alpha, **how), glow=modelsets.glow_path(name), glow_mult=mult)
    return d


def _looks(**more):
    import waikikiset  # noqa: F401  (its pictures: flame, thatch, bamboo)
    import citypieces  # noqa: F401
    import bambooset  # noqa: F401
    base = {'cane': look('bamboo/cane', tile=60), 'rust': look('city/rust', tile=64), 'thatch': look('waikiki/thatch', tile=160),
            'cord': look('night/cable', tile=32), 'stone': look('hotel/lava', tile=80), 'log': look('palm_bark', tile=60),
            'wood': look('planks_cream', tile=96)}
    base.update(more)
    return base


def day(desc):
    """The day twin: parts marked 'night' gone (flames), every look's glow taken off."""
    looks = {}
    for k, v in desc['looks'].items():
        looks[k] = {f: x for f, x in v.items() if f not in ('glow', 'glow_mult')}
    parts = [p for p in desc['parts'] if not p.get('night')]
    used = {p.get('look') for p in parts} | {v for p in parts for v in (p.get('faces') or {}).values()}
    return dict(desc, name=desc['name'] + 'Day', looks={k: v for k, v in looks.items() if k in used}, parts=parts)


# ---------- the pieces ----------

def paper_lantern(n=0, cord=24.0):
    """A round paper lantern on a cord from its hook: ribbed paper (red, white, amber), a bamboo cap and foot."""
    name = ('red', 'white', 'amber')[n]
    looks = _looks(paper=lit('night/paper_' + name, 2.5))
    r, h = 24.0, 56.0
    top = -cord
    parts = [{'shape': 'cylinder', 'r': 0.8, 'h': cord, 'sides': 4, 'at': [0, 0, -cord], 'look': 'cord', 'solid': False},
             {'shape': 'cylinder', 'r': 8, 'h': 5, 'sides': 8, 'at': [0, 0, top - 5], 'look': 'cane', 'solid': False},
             {'shape': 'ball', 'r': r, 'sides': 12, 'rings': 7, 'scale': [1, 1, h / (2 * r)], 'at': [0, 0, top - 5 - h / 2], 'look': 'paper', 'solid': False},
             {'shape': 'cylinder', 'r': 9, 'h': 4, 'sides': 8, 'at': [0, 0, top - 8 - h], 'look': 'cane', 'solid': False}]
    return {'name': 'FOLabNightPaperLantern' + name.title(), 'looks': looks, 'parts': parts, 'ground': False}


def oil_lamp(cord=16.0):
    """A hurricane lamp hung by its bail: a tin font, a glass chimney with the flame's light in it, a tin cap."""
    looks = _looks(glass=lit('night/glass', 3.0), tin=look('city/rust', tile=32))
    z = -cord
    parts = [{'shape': 'cylinder', 'r': 0.7, 'h': cord, 'sides': 4, 'at': [0, 0, z], 'look': 'cord', 'solid': False},
             {'shape': 'cone', 'r': 9, 'h': 7, 'sides': 8, 'at': [0, 0, z - 7], 'look': 'tin', 'under': True, 'solid': False},
             {'shape': 'cylinder', 'r': 6.5, 'r2': 5, 'h': 22, 'sides': 10, 'at': [0, 0, z - 29], 'look': 'glass', 'solid': False},
             {'shape': 'cylinder', 'r': 9, 'r2': 7, 'h': 9, 'sides': 10, 'at': [0, 0, z - 38], 'look': 'tin', 'solid': False}]
    for sx in (-1, 1):                                        # (the wire guard either side)
        parts.append({'shape': 'cylinder', 'r': 0.6, 'h': 34, 'sides': 3, 'at': [sx * 9.5, 0, z - 38], 'look': 'tin', 'solid': False})
    return {'name': 'FOLabNightOilLamp', 'looks': looks, 'parts': parts, 'ground': False}


def lantern_post():
    """A bamboo post with an arm and an oil lamp hung from it: for paths, piers and doorways."""
    lamp = oil_lamp()
    looks = _looks(glass=lamp['looks']['glass'], tin=lamp['looks']['tin'])
    tall = 230.0
    parts = [{'shape': 'cylinder', 'r': 4.5, 'r2': 3.8, 'h': tall, 'sides': 7, 'look': 'cane', 'material': 'wood'},
             {'shape': 'cylinder', 'r': 2.4, 'h': 52, 'sides': 6, 'turn': [0, 90, 0], 'at': [0, 0, tall - 12], 'look': 'cane', 'solid': False}]
    for p in lamp['parts']:
        ax, ay, az = p.get('at', (0, 0, 0))
        parts.append(dict(p, at=[ax + 46, ay, az + tall - 14]))
    return {'name': 'FOLabNightLanternPost', 'looks': looks, 'parts': parts}


def torch(tall=170.0):
    """A tiki torch (waikikiset's) with no flame of its own: the game's animated fire burns in its cup at night (`FLAMES`).
    Its drawn flame cards read in game as a still, glowing shape with bars along the cards' tops (the user, 22 Nov 2026:
    "it looks like a glitchy lava lamp")."""
    import waikikiset
    d = waikikiset.tiki_torch(tall)
    parts = [p for p in d['parts'] if p.get('look') != 'fire']
    return dict(d, name='FOLabNightTikiTorch%d' % round(tall), parts=parts, looks={k: v for k, v in d['looks'].items() if k != 'fire'})


def fire_pit():
    """A ring of lava stones round a bed of coals (glowing at night), logs leant together over it; the flames are the
    game's animated fire (`FLAMES`), night only."""
    looks = _looks(coals=lit('night/embers', 2.0))
    parts = [{'shape': 'cylinder', 'r': 50, 'h': 3, 'sides': 12, 'at': [0, 0, -1], 'look': 'coals', 'solid': False}]
    rnd = random.Random(911)
    for k in range(11):
        a = k * math.tau / 11
        s = 0.9 + 0.3 * rnd.random()
        parts.append({'shape': 'ball', 'r': 15 * s, 'sides': 7, 'rings': 4, 'scale': [1.2, 1, 0.75], 'turn': [0, 0, math.degrees(a)],
                      'at': [math.cos(a) * 62, math.sin(a) * 62, -3], 'look': 'stone', 'material': 'stone'})
    for k in range(4):                                        # (logs leant into a cone over the coals)
        a = k * math.tau / 4 + 0.4
        parts.append({'shape': 'cylinder', 'r': 5, 'h': 64, 'sides': 6, 'turn': [0, -58, math.degrees(a)],
                      'at': [math.cos(a) * 30, math.sin(a) * 30, 0], 'look': 'log', 'solid': False})
    # (the fire itself is the game's, `FLAMES`: drawn cards read as a still shape with bars along their tops)
    return {'name': 'FOLabNightFirePit', 'looks': looks, 'parts': parts}


def generator():
    """A small petrol generator on a skid: the engine block, a fuel tank over it, a muffler, a frame of tube, a cable
    coiled beside. What the strings of bulbs run off."""
    looks = _looks(paint=look('night/enamel_green', tile=48), metal=look('city/rust', tile=48))
    parts = [{'shape': 'box', 'size': [130, 70, 8], 'at': [0, 0, 0], 'look': 'metal', 'material': 'metal'},
             {'shape': 'box', 'size': [70, 54, 48], 'at': [-18, 0, 8], 'look': 'paint', 'material': 'metal'},
             {'shape': 'box', 'size': [40, 50, 40], 'at': [42, 0, 8], 'look': 'metal', 'solid': False},
             {'shape': 'cylinder', 'r': 22, 'h': 76, 'sides': 10, 'turn': [0, 90, 0], 'at': [-38, 0, 74], 'look': 'paint', 'solid': False},
             {'shape': 'cylinder', 'r': 7, 'h': 40, 'sides': 8, 'turn': [90, 0, 0], 'at': [40, 20, 54], 'look': 'metal', 'solid': False}]
    for x in (-62, 62):
        for y in (-32, 32):
            parts.append({'shape': 'cylinder', 'r': 2.5, 'h': 96, 'sides': 6, 'at': [x, y, 8], 'look': 'metal', 'solid': False})
    for x in (-62, 62):
        parts.append({'shape': 'cylinder', 'r': 2.5, 'h': 64, 'sides': 6, 'turn': [90, 0, 0], 'at': [x, 32, 104], 'look': 'metal', 'solid': False})
    parts.append({'shape': 'cylinder', 'r': 24, 'r2': 24, 'h': 10, 'sides': 12, 'at': [0, 70, 0], 'look': 'cord', 'solid': False})
    return {'name': 'FOLabNightGenerator', 'looks': looks, 'parts': parts}


def sag_of(L):
    return max(14.0, 0.07 * L)


def _wire(parts, pts, r=0.9, look_name='cord'):
    for (x0, z0), (x1, z1) in zip(pts, pts[1:]):
        parts.append({'shape': 'box', 'size': [math.hypot(x1 - x0, z1 - z0) + 0.5, r * 2, r * 2], 'at': [(x0 + x1) / 2, 0, (z0 + z1) / 2 - r],
                      'turn': [0, -math.degrees(math.atan2(z1 - z0, x1 - x0)), 0], 'look': look_name, 'solid': False})


def _catenary(L, dz, sag, n):
    """n + 1 points (x, z) of a cord from (0, 0) to (L, dz) hanging `sag` below the straight line at its middle (a
    parabola: near enough a catenary at these sags)."""
    return [(L * k / n, dz * k / n - 4 * sag * (k / n) * (1 - k / n)) for k in range(n + 1)]


def string(kind, L, dz=0.0):
    """A string hung from (0, 0, 0) to (L, 0, dz): bulbs ('bulbs', every ~55) or small paper lanterns in turn red,
    white, amber ('paper', every ~85), on a cord sagging `sag_of(L)`."""
    sag = sag_of(L)
    n = max(4, int(round(L / 40.0)))
    pts = _catenary(L, dz, sag, n)
    parts = []
    _wire(parts, pts)
    if kind == 'bulbs':
        looks = _looks(bulb=lit('night/bulb', 3.0))
        step = 55.0
    else:
        looks = _looks(**{'p%d' % i: lit('night/paper_' + c, 2.5) for i, c in enumerate(('red', 'white', 'amber'))})
        step = 85.0
    m = max(2, int(L // step))
    for k in range(1, m):
        t = k / float(m)
        x, z = L * t, dz * t - 4 * sag * t * (1 - t)
        if kind == 'bulbs':
            parts.append({'shape': 'cylinder', 'r': 1.6, 'h': 4, 'sides': 6, 'at': [x, 0, z - 5], 'look': 'cord', 'solid': False})
            parts.append({'shape': 'ball', 'r': 3.6, 'sides': 6, 'rings': 4, 'scale': [1, 1, 1.3], 'at': [x, 0, z - 9], 'look': 'bulb', 'solid': False})
        else:
            parts.append({'shape': 'cylinder', 'r': 0.5, 'h': 8, 'sides': 3, 'at': [x, 0, z - 8], 'look': 'cord', 'solid': False})
            parts.append({'shape': 'ball', 'r': 11, 'sides': 8, 'rings': 5, 'scale': [1, 1, 1.25], 'at': [x, 0, z - 22], 'look': 'p%d' % (k % 3), 'solid': False})
    return {'name': 'FOLabNightString%s%dx%d' % (kind.title(), round(L), round(dz)), 'looks': looks, 'parts': parts, 'ground': False}


POLE = 300.0


def pole_string(kind, L):
    """A string between two poles of its own (bamboo for paper, a dressed pole with its cable down for bulbs), for open
    ground: a hotel's lawn, a market, a camp."""
    d = string(kind, L)
    looks = dict(d['looks'])
    parts = []
    for p in d['parts']:
        ax, ay, az = p.get('at', (0, 0, 0))
        parts.append(dict(p, at=[ax - L / 2, ay, az + POLE - 10]))
    pole = 'cane' if kind == 'paper' else 'wood'
    for x in (-L / 2, L / 2):
        parts.append({'shape': 'cylinder', 'r': 6 if pole == 'wood' else 5, 'r2': 5 if pole == 'wood' else 4, 'h': POLE, 'sides': 7, 'at': [x, 0, -20], 'look': pole, 'material': 'wood'})
    if kind == 'bulbs':                                     # (its cable down the first pole, off along the ground)
        parts.append({'shape': 'cylinder', 'r': 1.1, 'h': POLE - 10, 'sides': 4, 'at': [-L / 2 + 7, 0, -10], 'look': 'cord', 'solid': False})
    return {'name': 'FOLabNightPoleString%s%d' % (kind.title(), round(L)), 'looks': looks, 'parts': parts}


# ---------- registration ----------

FIXED = {
    'paper_lantern_red': ('Paper lantern, red (hung)', lambda: paper_lantern(0)),
    'paper_lantern_white': ('Paper lantern, white (hung)', lambda: paper_lantern(1)),
    'paper_lantern_amber': ('Paper lantern, amber (hung)', lambda: paper_lantern(2)),
    'oil_lamp': ('Oil lamp (hung)', oil_lamp),
    'lantern_post': ('Lantern post', lantern_post),
    'torch': ('Tiki torch (on at dusk)', torch),
    'fire_pit': ('Fire pit', fire_pit),
    'generator': ('Generator', generator),
    'pole_bulbs_600': ('Bulbs on poles, 600', lambda: pole_string('bulbs', 600.0)),
    'pole_bulbs_900': ('Bulbs on poles, 900', lambda: pole_string('bulbs', 900.0)),
    'pole_paper_500': ('Paper lanterns on poles, 500', lambda: pole_string('paper', 500.0)),
    'pole_paper_800': ('Paper lanterns on poles, 800', lambda: pole_string('paper', 800.0)),
}
# piece: [(the game's light, x, y, z in the piece's frame)]
LIGHTS = {
    'torch': [('FireBrightOrange', 0, 0, 200)],
    'fire_pit': [('FireBrightOrange', 0, 0, 80)],
    'lantern_post': [('LamplightWarm', 46, 0, 180)],
    'oil_lamp': [('LamplightWarm', 0, 0, -40)],
    'paper_lantern_red': [('LamplightWarm', 0, 0, -55)], 'paper_lantern_white': [('LamplightWarm', 0, 0, -55)],
    'paper_lantern_amber': [('LamplightWarm', 0, 0, -55)],
    'pole_bulbs_600': [('ExtLightWarm02', 0, 0, 250)], 'pole_bulbs_900': [('ExtLightWarm02', 0, 0, 250)],
    'pole_paper_500': [('LamplightWarm', 0, 0, 240)], 'pole_paper_800': [('LamplightWarm', 0, 0, 240)],
}
# piece: [(the game's fire, x, y, z, scale in the piece's frame)]: its own animated fire (an add-on node: the master
# particle system MPSFireSmall01, with its crackle), as the game stands it on its own fire pits (FXFireSmall01 at the
# base of the flames: 10 to 20 over the ground at Honest Hearts' campfires, scale 0.5 to 1; 0.4 the smallest it uses).
# Lit only (a child of the marker), so by day the cold torch and pit.
FLAMES = {
    'torch': [('FXFireSmall01', 0, 0, 180, 0.35)],
    'fire_pit': [('FXFireSmall01', 0, 0, 8, 0.8)],
}
FLAME_DRAWS = 2                 # (the master particle system's two)
UNLIT = ('generator',)          # (no day twin: nothing on it glows)


def _register(key, label, fn):
    """key and key_day into modelsets' pieces (the day twin unless UNLIT)."""
    full = 'night_' + key
    if full in modelsets.PIECES:
        return full
    desc = fn()
    modelsets.PIECES[full] = {'label': label, 'set': SET, 'file': key, 'describe': fn, 'edid': desc['name']}
    if key not in UNLIT and not key.startswith('_'):
        modelsets.PIECES[full + '_day'] = {'label': label + ' (by day)', 'set': SET, 'file': key + '_day',
                                           'describe': lambda fn=fn: day(fn()), 'edid': desc['name'] + 'Day'}
    return full


for _k, (_label, _fn) in FIXED.items():
    _register(_k, _label, _fn)


def string_piece(kind, L, dz):
    """The piece of a string hung between two hooks L apart, the far one dz higher (L to 10, dz to 10)."""
    L, dz = int(round(L / 10.0) * 10), int(round(dz / 10.0) * 10)
    return _register('string_%s_%d_%d' % (kind, L, dz), 'String of %s, %d' % ('bulbs' if kind == 'bulbs' else 'paper lanterns', L),
                     lambda: string(kind, L, dz)), L, dz


def known(pr):
    """Every string the mod already has a record of, registered (so remake and the like find them)."""
    import re
    import recordio
    for rec in pr.records.values():
        if rec.get('type') != 'STAT':
            continue
        m = re.match(r'FOLabNightString(Bulbs|Paper)(\d+)x(-?\d+)(Day)?$', recordio.field(rec, 'EDID') or '')
        if m:
            string_piece(m.group(1).lower(), int(m.group(2)), int(m.group(3)))


# where things hang on the pieces of other sets, in their frames: [(x, y, z of the hook)] (bamboo: bambooset's eaves)
HANGS = {
    # (huts: at the eave's own edge, 60 past the walls, so the lantern hangs below the straw fringe, not in it: in the
    # first pictures, 22 Nov 2026, lanterns hung nearer the wall showed only as slivers under the fringe)
    'bamboo_hut': [(-200, -258, 200), (200, -258, 200)],
    'bamboo_hut_small': [(-150, -218, 200), (150, -218, 200)],
    'bamboo_market_stall': [(-115, -120, 194), (115, -120, 194)],
    'bamboo_cookhouse': [(-160, 0, 178), (160, 0, 178)],
    'tiki_bar': [(-215, -232, 248), (215, -232, 248)],
    # (treevillage: the hut's front wall on the deck at y 0, eaves at RISE + 184; oil lamps, short enough to hang over
    # head height on the walked deck: the bamboo session, 22 Nov 2026)
    'bamboo_treehouse': [(-200, -58, 584), (200, -58, 584)],
}
# strings along a piece's front, hook to hook: (x0, y0, z0, x1, y1, z1)
ALONG = {
    'bamboo_cookhouse': (-320, -220, 194, 320, -220, 194),
}
DOOR_TORCH = {'bamboo_hut': (150, -320), 'bamboo_hut_small': (130, -280)}     # (a torch beside the doorway, on the ground)


# ---------- the dusk switch ----------

def script_source(marker=MARKER):
    return ('scn %s\n\nfloat fQuestDelayTime\n\nBegin GameMode\n'
            '\tset fQuestDelayTime to 10\n'
            '\tif GameHour >= %s || GameHour < %s\n'
            '\t\tif %s.GetDisabled\n\t\t\t%s.Enable\n\t\tendif\n'
            '\telse\n'
            '\t\tif %s.GetDisabled == 0\n\t\t\t%s.Disable\n\t\tendif\n'
            '\tendif\nEnd\n') % (SCRIPT, _f(DUSK), _f(DAWN), marker, marker, marker, marker)


def _f(v):
    return ('%.1f' % v).rstrip('0').rstrip('.')


def switch_ops(gd, pr, cell, at):
    """(ops, marker key): the marker (persistent, disabled, at `at` in `cell`), the script, the quest: the first three
    things made, so their keys are the mod's next three."""
    import api_scripts
    import newgame
    import questrec as qr
    import stormsched
    keys = ['+%06X' % (pr.next_id + k) for k in range(3)]
    mk, sk, qk = keys
    marker = gd.key(stormsched._game_form(gd, 'STAT', 'XMarker'))
    extra = {mk: {'type': 'REFR', 'flags': newgame.PERSISTENT, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': MARKER}]}}
    quest = qr.quest_record({'edid': QUEST, 'script': sk, 'name': '', 'flags': {'start_enabled': True},
                             'priority': 0, 'delay': 10.0, 'stages': [], 'objectives': []})
    extra[qk] = quest
    sc = api_scripts.scripts()
    c = sc.compile(script_source(), sk, 'quest', extra)
    if not hasattr(c, 'subrecords'):
        raise ValueError('the night lights script does not compile: %s' % (c,))
    ops = [{'op': 'add', 'cell': cell, 'base': marker, 'p': [round(at[0], 1), round(at[1], 1), round(at[2] - 300, 1), 0.0, 0.0, 0.0], 's': 1.0,
            'extra': {'persistent': True, 'edid': MARKER, 'props': {'disabled': True}}},
           {'op': 'record_new', 'record': sc._record_of(c, SCRIPT)},
           {'op': 'record_new', 'record': quest}]
    return ops, mk


# ---------- placing ----------

def _turn(lx, ly, rz):
    c, s = math.cos(rz), math.sin(rz)
    return lx * c + ly * s, -lx * s + ly * c


def fire_keys(gd):
    """{editor ID: key} of the game's fires FLAMES names."""
    want = {e for rows in FLAMES.values() for e, *_r in rows}
    return {gd.edid(f): gd.key(f) for f, (_i, r) in gd.forms.items() if r.tag == 'MSTT' and gd.edid(f) in want}


def flame_ops(fire_key, ck, marker, x, y, z, rz, short, cell_of):
    """The game's fires for a lit piece `short` standing at x, y, z turned rz: add ops, children of the marker."""
    out = []
    for edid, lx, ly, lz, sc in FLAMES.get(short, ()):
        if edid not in fire_key:
            continue
        tx, ty = _turn(lx, ly, rz)
        out.append({'op': 'add', 'cell': cell_of(x + tx, y + ty) or ck, 'base': fire_key[edid], 's': sc,
                    'p': [round(x + tx, 1), round(y + ty, 1), round(z + lz, 1), 0.0, 0.0, round(rz % math.tau, 4)],
                    'extra': {'props': {'parent': {'ref': marker, 'opposite': False, 'popin': False}}}})
    return out


class Lighter:
    """Puts night pieces down: each lit piece with its day twin, its light if the budget allows, all under the marker."""

    def __init__(self, gd, pr, world, cover, marker):
        import roadgen
        import waikikiplace as WP
        self.gd, self.pr, self.world = gd, pr, world
        self.taken = WP.Taken(gd, pr, world)
        self.ground = roadgen.Ground(gd, pr, world)
        self.S = WP.Stander(gd, pr, world, cover, self.taken, self.ground)
        self.marker = marker
        self.grid = gd.grid(world)
        self.ops, self.first = [], []
        self.keys, self.draws_of = {}, {}
        self.cell_lights, self.cell_draws = {}, {}
        self.by, self.lit, self.unlit = {}, 0, 0
        want = {e for rows in LIGHTS.values() for e, *_r in rows}
        self.light_key = {gd.edid(f): gd.key(f) for f, (_i, r) in gd.forms.items() if r.tag == 'LIGH' and gd.edid(f) in want}
        self.fire_key = fire_keys(gd)
        self.flames = 0
        self.lights = self._lights_now()

    def _lights_now(self):
        """Where the world's lights stand already (the mod's and its plugin's), by square."""
        out = []
        for cell in self.grid.values():
            ck = self.gd.key(cell)
            c = self.pr.cells.get(ck)
            refs = [r for r in (c['refs'].values() if c else []) if not r.get('removed') and r.get('base')]
            try:
                refs += [{'base': self.gd.key(r['base']), 'p': list(r['pos'])} for r in self.gd.refs(cell) if r['base'] and r['pos']]
            except Exception:
                pass
            for r in refs:
                if self.taken.kind_of(r['base'])[0] == 'LIGH':
                    out.append((r['p'][0], r['p'][1]))
        return out

    def key(self, piece):
        if piece not in self.keys:
            got, info = modelsets.put(self.pr, piece)
            self.first.extend(got)
            self.keys[piece] = info['key'] or '$model_' + piece
            self.draws_of[piece] = len(modelmake.make(modelsets.PIECES[piece]['describe']())['shapes'])
        return self.keys[piece]

    def cell_of(self, x, y):
        c = self.grid.get((int(x // 4096), int(y // 4096)))
        return self.gd.key(c) if c is not None else None

    def put(self, piece, x, y, z, rz, foot=True):
        """Stand `piece` (a modelsets key) and its twin; False when the cell's draws are spent."""
        ck = self.cell_of(x, y)
        if ck is None:
            return False
        k = self.key(piece)
        if self.cell_draws.get(ck, 0) + self.draws_of[piece] > CELL_DRAWS:
            return False
        p = [round(x, 1), round(y, 1), round(z, 1), 0.0, 0.0, round(rz % math.tau, 4)]
        twin = piece + '_day' if piece + '_day' in modelsets.PIECES else None
        par = lambda opp: {'props': {'parent': {'ref': self.marker, 'opposite': opp, 'popin': False}}}
        self.ops.append({'op': 'add', 'cell': ck, 'base': k, 'p': p, 's': 1.0, 'extra': par(False) if twin else {}})
        if twin:
            self.ops.append({'op': 'add', 'cell': ck, 'base': self.key(twin), 'p': list(p), 's': 1.0, 'extra': par(True)})
        self.cell_draws[ck] = self.cell_draws.get(ck, 0) + self.draws_of[piece]
        short = piece[len('night_'):]
        got = flame_ops(self.fire_key, ck, self.marker, x, y, z, rz, short, self.cell_of)
        self.ops.extend(got)
        self.flames += len(got)
        self.cell_draws[ck] += FLAME_DRAWS * len(got)
        for edid, lx, ly, lz in LIGHTS.get(short, ()) if not short.startswith('string_') else self._string_light(short):
            if edid not in self.light_key:
                continue
            tx, ty = _turn(lx, ly, rz)
            wx, wy = x + tx, y + ty
            lc = self.cell_of(wx, wy) or ck
            if self.cell_lights.get(lc, 0) >= CELL_LIGHTS or any(math.hypot(wx - a, wy - b) < LIGHT_APART for a, b in self._near(wx, wy)):
                self.unlit += 1
                continue
            self.ops.append({'op': 'add', 'cell': lc, 'base': self.light_key[edid], 's': 1.0,
                             'p': [round(wx, 1), round(wy, 1), round(z + lz, 1), 0.0, 0.0, 0.0], 'extra': par(False)})
            self.lights.append((wx, wy))
            self.cell_lights[lc] = self.cell_lights.get(lc, 0) + 1
            self.lit += 1
        if foot:
            b = self.S.box(piece)
            self.taken.put(x, y, rz, (b[0], b[1], b[3], b[4]))
        self.by[short] = self.by.get(short, 0) + 1
        return True

    def _near(self, x, y):
        return [q for q in self.lights if abs(q[0] - x) < LIGHT_APART and abs(q[1] - y) < LIGHT_APART]

    def _string_light(self, short):
        kind, L, dz = short.split('_')[1], float(short.split('_')[2]), float(short.split('_')[3])
        return [('ExtLightWarm02' if kind == 'bulbs' else 'LamplightWarm', L / 2, 0, dz / 2 - sag_of(L) - 40)]

    def try_stand(self, piece, x, y, rz):
        """On the ground where it fits (waikikiplace's checks: clear, dry, off the road, not too steep)."""
        z = self.S.fits(piece, x, y, rz)
        return z is not None and self.put(piece, x, y, z, rz)

    def ring(self, piece, x, y, r0, r1, n, rng, face_in=True, tries=40):
        """n of `piece` round (x, y) between r0 and r1, each turned to face the middle (or along the ring)."""
        done = 0
        for _t in range(tries):
            if done >= n:
                break
            a = rng.random() * math.tau
            d = r0 + (r1 - r0) * rng.random()
            px, py = x + math.cos(a) * d, y + math.sin(a) * d
            rz = math.atan2(-(x - px), -(y - py)) % math.tau if face_in else (-a) % math.tau
            if self.try_stand(piece, px, py, rz):
                done += 1
        return done

    def hang(self, piece, wx, wy, wz, rz):
        """A hung piece at a hook (no footprint: it hangs over what's there)."""
        return self.put(piece, wx, wy, wz, rz, foot=False)

    def strung(self, kind, a, b):
        """A string from hook a to hook b (world points)."""
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        if L < 150:
            return False
        piece, _L, _dz = string_piece(kind, L, b[2] - a[2])
        return self.put(piece, a[0], a[1], a[2], math.atan2(-dy, dx), foot=False)


def _all_refs(gd, pr, world):
    """Every thing standing in the world as {'base', 'p', 's'}: the world's plugin's refs with the mod's changes laid over
    (a removed one left out), and the mod's own."""
    for cell in gd.grid(world).values():
        c = pr.cells.get(gd.key(cell))
        mine = c['refs'] if c else {}
        try:
            for r in gd.refs(cell):
                if not (r['base'] and r['pos'] and r['rot']):
                    continue
                d = {'base': gd.key(r['base']), 'p': list(r['pos']) + list(r['rot']), 's': r.get('scale') or 1.0}
                ch = mine.get(gd.key(r['ref']))
                if ch:
                    if ch.get('removed'):
                        continue
                    d.update({k: ch[k] for k in ('base', 'p', 's') if ch.get(k) is not None})
                yield d
        except Exception:
            pass
        for k, r in mine.items():
            if k.startswith('+') and not r.get('removed') and r.get('base') and r.get('p'):
                yield r


def _refs_of(gd, pr, world, edids, kinds=None):
    """[(edid, x, y, z, rz, s)] of things with these editor IDs standing in the world (the mod's and its plugin's)."""
    import waikikiplace as WP
    t = kinds or WP.Taken.__new__(WP.Taken)
    if not kinds:
        t.gd, t.pr, t._box = gd, pr, {}
    out = []
    for r in _all_refs(gd, pr, world):
        e = t.kind_of(r['base'])[1]
        if e in edids:
            p = r['p']
            out.append((e, p[0], p[1], p[2], p[5] if len(p) > 5 else 0.0, float(r.get('s') or 1.0)))
    return out


CAMP_WORDS = ("Squatters' Camp", 'Refugee Camp', 'The Holdouts', "Watcher's Hut", 'Waystation', 'Hale Malia', 'Tradewinds',
              'Moana Kai', 'Loa Gate', 'Alewa Fort', 'Border Post', "Makapu'u Gate", "Settlers' Watchtower", "Crow's Nest",
              'Pacific Heights Beacon', 'The Heights', 'Koko Marina')
RAIDERS = 'Raider Camp'


def plan(gd, pr, world, cover, seed=7, progress=None):
    """(ops, report): night lights over the world, one Undo (see the module's docstring)."""
    import api_maps
    rng = random.Random(seed)
    known(pr)
    landmarks = (api_maps._kept(pr, 'landmarks.json').get(gd.edid(world)) or {}).get('stood') or []
    hotels = api_maps._kept(pr, 'hotels.json').get(gd.edid(world)) or []
    powered = [h for h in landmarks if h.get('set') in POWERED]
    first = powered[0] if powered else (hotels[0] if hotels else None)
    grid = gd.grid(world)
    if first:
        at = (first['x'], first['y'], 0.0)
    else:
        at = (0.0, 0.0, 0.0)
    cell = grid.get((int(at[0] // 4096), int(at[1] // 4096))) or next(iter(grid.values()))
    head, marker = switch_ops(gd, pr, gd.key(cell), at)
    # (their keys are the next three: modelsets.put's records come after them, so the pieces' keys go by name)
    pr_next = pr.next_id
    pr.next_id += 3                       # (only while planning: the ops are applied against the mod as it was)
    try:
        L = Lighter(gd, pr, world, cover, marker)
        report = _place(L, gd, pr, world, rng, powered, hotels, progress)
    finally:
        pr.next_id = pr_next
    report.update({'marker': marker, 'pieces': dict(sorted(L.by.items())), 'lights': L.lit, 'unlit': L.unlit, 'flames': L.flames,
                   'cells': len(L.cell_draws), 'draws_most': max(L.cell_draws.values()) if L.cell_draws else 0,
                   'refs': sum(1 for o in L.ops if o['op'] == 'add')})
    return head + L.first + L.ops, report


def _place(L, gd, pr, world, rng, powered, hotels, progress):
    rep = {'powered': [h['set'] for h in powered], 'camps': 0, 'bamboo': 0, 'bars': 0, 'hotels': 0, 'piers': 0}
    say = progress or (lambda *_a: None)
    # --- powered: bulbs on poles and a generator, lanterns on posts ---
    say('Powered places')
    for h in powered:
        x, y = h['x'], h['y']
        L.ring('night_generator', x, y, 1300, 3600, 1, rng, face_in=False, tries=200)
        L.ring('night_pole_bulbs_900', x, y, 1200, 4200, 3, rng, face_in=False, tries=400)
        L.ring('night_pole_bulbs_600', x, y, 1100, 4200, 3, rng, face_in=False, tries=400)
        L.ring('night_lantern_post', x, y, 1100, 2800, 4, rng, tries=80)
    # --- FOLab's other hotels: fire ---
    say('Hotels')
    for h in hotels:
        x, y = h['x'], h['y']
        n = L.ring('night_pole_paper_800', x, y, 900, 2400, 1, rng, face_in=False, tries=80)
        n += L.ring('night_torch', x, y, 800, 2200, 3, rng, tries=60)
        rep['hotels'] += n > 0
    # --- tiki bars and the bamboo village: hung from their eaves ---
    say('Bars and the bamboo village')
    import waikikiset  # noqa: F401
    import bambooset  # noqa: F401
    import treevillage  # noqa: F401
    want = {modelsets.PIECES[k]['edid']: k for k in HANGS.keys() | ALONG.keys() | DOOR_TORCH.keys() if k in modelsets.PIECES}
    for e, x, y, z, rz, s in _refs_of(gd, pr, world, set(want)):
        piece = want[e]
        hooks = [(x + _turn(hx * s, hy * s, rz)[0], y + _turn(hx * s, hy * s, rz)[1], z + hz * s) for hx, hy, hz in HANGS.get(piece, ())]
        kinds = ['night_oil_lamp'] if piece in ('bamboo_market_stall', 'bamboo_cookhouse', 'bamboo_treehouse') else \
            ['night_paper_lantern_red', 'night_paper_lantern_white', 'night_paper_lantern_amber']
        for i, (hx, hy, hz) in enumerate(hooks):
            L.hang(kinds[(i + int(abs(x))) % len(kinds)], hx, hy, hz, rz)
        if piece in ALONG:
            a0 = ALONG[piece]
            pa = (x + _turn(a0[0] * s, a0[1] * s, rz)[0], y + _turn(a0[0] * s, a0[1] * s, rz)[1], z + a0[2] * s)
            pb = (x + _turn(a0[3] * s, a0[4] * s, rz)[0], y + _turn(a0[3] * s, a0[4] * s, rz)[1], z + a0[5] * s)
            L.strung('paper', pa, pb)
        if piece in DOOR_TORCH:
            tx, ty = _turn(DOOR_TORCH[piece][0] * s, DOOR_TORCH[piece][1] * s, rz)
            L.try_stand('night_torch', x + tx, y + ty, rz)
        if piece == 'tiki_bar':
            rep['bars'] += 1
            L.ring('night_pole_paper_500', x, y, 500, 1200, 1, rng, face_in=False)
        elif piece == 'bamboo_cookhouse':
            L.ring('night_fire_pit', x, y, 450, 900, 1, rng)
        rep['bamboo'] += piece.startswith('bamboo')
    # strings between neighbouring huts' nearest hooks
    huts = [(x, y, z, rz, s, e) for e, x, y, z, rz, s in _refs_of(gd, pr, world, {modelsets.PIECES[k]['edid'] for k in ('bamboo_hut', 'bamboo_hut_small')})]
    used = set()
    for i, a in enumerate(huts):
        best = None
        for j, b in enumerate(huts):
            if j <= i or j in used or i in used:
                continue
            d = math.hypot(a[0] - b[0], a[1] - b[1])
            if 600 < d < 1300 and (best is None or d < best[0]):
                best = (d, j)
        if best:
            b = huts[best[1]]
            pa = _nearest_hook(a, b)
            pb = _nearest_hook(b, a)
            if L.strung('paper', pa, pb):
                used |= {i, best[1]}
    # --- camps and settlements: a fire pit, torches round it, a lantern post or two ---
    say('Camps')
    for name, x, y in _markers(pr):
        if RAIDERS in name:
            fire_n, torch_n, post_n = 1, 1, 0
        elif any(w in name for w in CAMP_WORDS):
            fire_n, torch_n, post_n = 1, 3, 2
        else:
            continue
        got = L.ring('night_fire_pit', x, y, 250, 1100, fire_n, rng)
        L.ring('night_torch', x, y, 500, 1400, torch_n, rng)
        L.ring('night_lantern_post', x, y, 600, 1600, post_n, rng)
        rep['camps'] += got > 0
    # --- the harbour's piers: oil lamps on posts along the planking ---
    say('Piers')
    rep['piers'] = _piers(L, gd, pr, world, rng)
    return rep


def _nearest_hook(a, b):
    """Of hut a's hooks (as HANGS, plus its back corners), the one nearest hut b."""
    x, y, z, rz, s, e = a
    piece = 'bamboo_hut' if e == modelsets.PIECES['bamboo_hut']['edid'] else 'bamboo_hut_small'
    pts = HANGS[piece] + [(hx, -hy, hz) for hx, hy, hz in HANGS[piece]]
    best = None
    for hx, hy, hz in pts:
        tx, ty = _turn(hx * s, hy * s, rz)
        q = (x + tx, y + ty, z + hz * s)
        d = math.hypot(q[0] - b[0], q[1] - b[1])
        if best is None or d < best[0]:
            best = (d, q)
    return best[1]


def _markers(pr):
    out = []
    for c in pr.cells.values():
        for r in (c.get('refs') or {}).values():
            m = r.get('marker')
            if m and not r.get('removed') and m.get('name'):
                out.append((m['name'], r['p'][0], r['p'][1]))
    return sorted(out)


PIER_WORDS = ('dock', 'pier', 'boardwalk')
PIER_NOT = ('pylon', 'post', 'piling', 'rope')
PIER_APART = 900.0
PIER_MOST = 40


def _piers(L, gd, pr, world, rng):
    """Lantern posts on the piers' planking (the game's dock pieces, wherever the harbour step stood them), one at a
    piece's corner every PIER_APART or more."""
    stood = []
    found = []
    t = L.taken
    for r in _all_refs(gd, pr, world):
        tag, e, box = t.kind_of(r['base'])
        if tag == 'STAT' and box and any(w in e.lower() for w in PIER_WORDS) and not any(w in e.lower() for w in PIER_NOT):
            found.append((r, box))
    rng.shuffle(found)
    for r, box in found:
        if len(stood) >= PIER_MOST:
            break
        x, y, z = r['p'][:3]
        if any(math.hypot(x - a, y - b) < PIER_APART for a, b in stood):
            continue
        s = float(r.get('s') or 1.0)
        rz = r['p'][5] if len(r['p']) > 5 else 0.0
        tx, ty = _turn((box[3] - 18) * s, (box[4] - 18) * s, rz)       # (at a corner, out of the way along the planking)
        if L.put('night_lantern_post', x + tx, y + ty, z + box[5] * s, rz, foot=False):
            stood.append((x, y))
    return len(stood)


# ---------- the game's fire in place of the flame cards (22 Nov 2026), for a mod that has its night lights already ----------

def flame_fix(gd, pr):
    """(ops, report): every piece of the mod's that had flames drawn on cards, its files written again without them
    (modelsets.put: same paths, same records; modelsets.drawn_fires), and the game's animated fire added where they
    were: at every lit night torch and fire pit (`FLAMES`), a child of the marker as the piece, and on the pieces that
    burn day and night (waikikiset's tiki torches, gate and planters, restyle's beach bar: `modelsets.fires_of`), with
    no parent. Nothing for a piece that has its fire already."""
    import recordio
    marker = _marker_key(pr)
    if marker is None:
        raise ValueError('the mod has no %s: run plan first' % MARKER)
    modelsets._all_sets()
    fire_key = fire_keys(gd)
    game_fire = fire_key[modelsets.GAME_FIRE]
    night, always = {}, {}
    for piece in modelsets.PIECES:
        k = modelsets.record_of(pr, piece)
        if not k:
            continue
        short = piece[len('night_'):] if piece.startswith('night_') else None
        if short in FLAMES:
            night[k] = short
        spots = modelsets.fires_of(piece)
        if spots:
            always[k] = (piece, spots)
        if (short and short.removesuffix('_day') in FLAMES) or spots:
            modelsets.put(pr, piece)                       # (its model again, the cards out)
    have = []
    for c in pr.cells.values():
        for r in (c.get('refs') or {}).values():
            if not r.get('removed') and r.get('base') == game_fire and r.get('p'):
                have.append(tuple(r['p'][:3]))
    near = lambda o: any(abs(o['p'][0] - h[0]) < 4 and abs(o['p'][1] - h[1]) < 4 and abs(o['p'][2] - h[2]) < 8 for h in have)
    ops, rep = [], {'torch': 0, 'fire_pit': 0, 'always': {}, 'had': 0, 'no_place': 0}
    for ck, c in pr.cells.items():
        for rk, r in list((c.get('refs') or {}).items()):
            base = r.get('base')
            if r.get('removed') or (base not in night and base not in always):
                continue
            pl = list(r['p']) if r.get('p') else _game_place(gd, rk)
            if pl is None:
                rep['no_place'] += 1
                continue
            x, y, z, _a, _b, rz = pl[:6]
            if base in night:
                got = flame_ops(fire_key, ck, marker, x, y, z, rz, night[base], lambda *_a: None)
                what = night[base]
            else:
                piece, spots = always[base]
                sc = float(r.get('s') or (pl[6] if len(pl) > 6 else 1.0))
                got = []
                for lx, ly, lz, fs in spots:
                    tx, ty = _turn(lx * sc, ly * sc, rz)
                    got.append({'op': 'add', 'cell': ck, 'base': game_fire, 's': round(fs * sc, 3),
                                'p': [round(x + tx, 1), round(y + ty, 1), round(z + lz * sc, 1), 0.0, 0.0, round(rz % math.tau, 4)]})
                what = piece
            if any(near(o) for o in got):
                rep['had'] += 1
                continue
            ops.extend(got)
            have.extend(tuple(o['p'][:3]) for o in got)
            if what in ('torch', 'fire_pit'):
                rep[what] += 1
            else:
                rep['always'][what] = rep['always'].get(what, 0) + 1
    rep['refs'] = len(ops)
    rep['records'] = sorted(recordio.field(pr.records[k], 'EDID') for k in set(night) | set(always))
    return ops, rep


def _game_place(gd, rk):
    """[x, y, z, rx, ry, rz, scale] of a game ref the mod changed without moving (a swap of its base)."""
    import struct
    try:
        f = gd.fields(gd.from_key(rk))
    except Exception:
        return None
    if 'DATA' not in f or len(f['DATA']) < 24:
        return None
    sc = struct.unpack('<f', f['XSCL'])[0] if 'XSCL' in f and len(f['XSCL']) >= 4 else 1.0
    return list(struct.unpack_from('<6f', f['DATA'])) + [sc]


def _marker_key(pr):
    """The ref key (as an enable parent names it) of the mod's FOLabNightLights."""
    for ck, c in pr.cells.items():
        for rk, r in (c.get('refs') or {}).items():
            if not r.get('removed') and (r.get('edid') == MARKER or (r.get('extra') or {}).get('edid') == MARKER):
                return rk
    return None
