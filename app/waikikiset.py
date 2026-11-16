"""Waikiki in the late fifties, gone to seed: the beach's, the hotels', the streets' and the harbour's own things.

Pieces of `modelsets` like any other (set 'waikiki': meshes\\folab\\waikiki, textures\\folab\\waikiki), registered here
at import so modelsets needs no edit, as citypieces does. Each is a description over modelmake's parts. Frame: the
middle of the thing's foot at the origin, z up, its front towards -y (where one stands to use it), 70 units a metre.

Names on signs are made up for the place (no real business's), the textures drawn in texpaint. Anything made to be
climbed or walked into (the lifeguard tower, the hale, the stage) is walked by walkcheck in tests/test_modelmake.py.

LIGHT. What is lit glows as the game's own lamps and neon do (a glow map, effects\\white.dds, in the third texture slot;
the material's emissive white, its multiplier how bright: nifmake), and casts light by one of the game's own lights
placed with it: `LIGHTS` says which and where in the piece's frame, `lights(...)` gives the ops. The game's: a
flickering fire (FireBrightOrange) for torches, the old street lamp's (OVStreetLightOld), neon red and green, a warm
lamp (ExtLightWarm02). Lights cost the game dearly, so whatever stands them keeps them apart (LIGHT_APART)."""
import math
import random

import citypieces
import modelsets
import texpaint as tp
from modelsets import limb, look

SET = 'waikiki'
SIGNS = [('BUS', ()), ('SURF SHOP', ('BOARDS', 'WAX')), ('FRESH POI', ()), ('LEIS', ('50 CENTS',)),
         ('SHAVE ICE', ('ALL FLAVORS',)), ('FRUIT', ('PINEAPPLE',)), ('FRESH FISH', ()), ('LIFEGUARD', ('ON DUTY',))]

modelsets.TEXTURES.update({
    'waikiki/thatch': lambda: tp.thatch(seed=110),
    'waikiki/wicker': lambda: tp.wicker(seed=111),
    'waikiki/tiki': lambda: tp.tiki_face(seed=112),
    'waikiki/tiki_wood': lambda: tp.bark_rings(colour=tp.TIKI_WOOD, rings=3, seed=119),
    'waikiki/net': lambda: tp.net(seed=113),
    'waikiki/koa': lambda: tp.koa_hull(seed=114),
    'waikiki/hull_white': lambda: tp.koa_hull(seed=120, paint=tp.WHITE),
    'waikiki/hull_teal': lambda: tp.koa_hull(seed=121, paint=tp.TURQUOISE),
    'waikiki/pineapples': lambda: tp.pineapples(seed=115),
    'waikiki/husk': lambda: tp.husk(seed=116),
    'waikiki/leis': lambda: tp.leis(seed=117),
    'waikiki/motels': lambda: tp.googie([('MAHALO', ('MOTOR INN', 'VACANCY')), ('SEA BREEZE', ('MOTEL', 'POOL  TV')),
                                         ('KONA KAI', ('COURTS',)), ('TIKI ROOM', ('COCKTAILS',))], seed=118),
    'waikiki/signs': lambda: tp.sign([{'box': ((n % 4) * 0.25, (n // 4) * 0.5, (n % 4) * 0.25 + 0.25, (n // 4) * 0.5 + 0.5),
                                       'lines': [big] + list(small), 'ground': (tp.CREAM, tp.TURQUOISE, tp.YELLOW, tp.WHITE)[n % 4],
                                       'ink': (tp.RED, tp.WHITE, tp.TEAL_INK, tp.RED)[n % 4], 'edge': (tp.CORAL, tp.CREAM, tp.CORAL, tp.TURQUOISE)[n % 4]}
                                      for n, (big, small) in enumerate(SIGNS)], w=1024, h=512, seed=122),
    'waikiki/canvas_blue': lambda: tp.cloth_stripes(tp.TURQUOISE, tp.CREAM, seed=123),
    'waikiki/canvas_yellow': lambda: tp.cloth_stripes(tp.YELLOW, tp.WHITE, seed=124),
    'waikiki/enamel_teal': lambda: tp.painted_metal((84, 150, 146), seed=125, rust=0.25),
    'waikiki/enamel_cream': lambda: tp.painted_metal(tp.CREAM, seed=126, rust=0.2),
    'waikiki/flame': lambda: tp.flame(seed=127),
    'waikiki/lamp_glass': lambda: tp.lit_glass(seed=128),
    'waikiki/neon_red': lambda: tp.lit_glass(colour=(255, 70, 80), seed=129),
    'waikiki/neon_teal': lambda: tp.lit_glass(colour=(90, 255, 220), seed=130),
})
GLOW = 'textures\\effects\\white.dds'           # (the game's own: what its street light glows with)
LIGHT_APART = 900.0                                 # no two of the lights this places nearer than this
# piece: [(the game's light, x, y, z in the piece's frame)]
LIGHTS = {}


def lit(name, mult=2.0, alpha=False):
    """A look that glows."""
    return dict(look(name, alpha=alpha), glow=GLOW, glow_mult=mult)


def lights(gd, pr, piece, x, y, z, rz, s=1.0, cell=None):
    """The ops that stand a piece's lights where it stands (x, y, z, turned rz, size s): one add a light."""
    import landmarks
    want = {e for rows in LIGHTS.values() for e, *_r in rows}
    key = {gd.edid(f): gd.key(f) for f, (_i, r) in gd.forms.items() if r.tag == 'LIGH' and gd.edid(f) in want} if want else {}
    out = []
    for edid, lx, ly, lz in LIGHTS.get(piece, ()):
        if edid not in key:
            continue
        tx, ty = landmarks._turn(lx * s, ly * s, rz)
        out.append({'op': 'add', 'cell': cell, 'base': key[edid], 'p': [round(x + tx, 1), round(y + ty, 1), round(z + lz * s, 1), 0.0, 0.0, 0.0], 's': 1.0})
    return out


def _sign(n):
    """The look of one of SIGNS' boards."""
    return look('waikiki/signs', region=((n % 4) * 0.25, (n // 4) * 0.5, (n % 4) * 0.25 + 0.25, (n // 4) * 0.5 + 0.5))


def _motel(n):
    return look('waikiki/motels', region=((n % 2) * 0.5, (n // 2) * 0.5, (n % 2) * 0.5 + 0.5, (n // 2) * 0.5 + 0.5))


def _base_looks():
    return {'wood': look('planks_cream', tile=96), 'teal': look('planks_turquoise', tile=96), 'coral': look('planks_coral', tile=96),
            'pole': look('metal_white', tile=48), 'rust': look('city/rust', tile=64), 'tin': look('city/tin', tile=192),
            'bamboo': look('bamboo', tile=40), 'thatch': look('waikiki/thatch', tile=160), 'wicker': look('waikiki/wicker', tile=48),
            'concrete': look('concrete', tile=160)}


# ---------- the beach ----------

def lifeguard_tower():
    """A lifeguard's stand: a platform two storeys up on four splayed legs, a rail to lean on along the front and the
    sides, a shade roof on posts, a ramp up the back to step on from; a sign on the front rail. A perch over the sand."""
    looks = dict(_base_looks(), sign=_sign(7), plank=look('city/planks', tile=128, turned=True))
    parts = []
    up, half = 210.0, 120.0
    parts.append({'shape': 'slab', 'size': [2 * half, 2 * half, 10], 'at': [0, 0, up - 10], 'look': 'wood', 'material': 'wood'})
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(limb((sx * (half + 30), sy * (half + 30), 0), (sx * (half - 10), sy * (half - 10), up), 7, 6, 'teal', sides=4, solid=True))
    # rails: the front and the left; the back half of the right is the way in off the ramp
    parts.append({'shape': 'box', 'size': [2 * half, 8, 96], 'at': [0, -half + 4, up], 'look': 'teal', 'faces': {'front': 'sign'}, 'material': 'wood'})
    parts.append({'shape': 'box', 'size': [8, 2 * half, 96], 'at': [-half + 4, 0, up], 'look': 'teal', 'material': 'wood'})
    parts.append({'shape': 'box', 'size': [2 * half, 8, 96], 'at': [0, half - 4, up], 'look': 'teal', 'material': 'wood'})
    parts.append({'shape': 'box', 'size': [8, half - 20, 96], 'at': [half - 4, -half / 2 - 10, up], 'look': 'teal', 'material': 'wood'})
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append({'shape': 'box', 'size': [7, 7, 210], 'at': [sx * (half - 6), sy * (half - 6), up], 'look': 'pole', 'solid': False})
    parts.append({'shape': 'slab', 'size': [2 * half + 70, 2 * half + 70, 6], 'at': [0, 0, up + 206], 'turn': [-6, 0, 0], 'look': 'coral', 'faces': {'bottom': 'wood'}, 'solid': False})
    run = up / math.tan(math.radians(27))                        # the ramp: off the right side, down to the sand behind
    citypieces._ramp(parts, half, half + run, half / 2, up, 0.0)
    return {'name': 'FOLabWaikikiLifeguardTower', 'looks': looks, 'parts': parts}


def outrigger(rack=False):
    """An outrigger canoe: a long dug-out hull of koa, a float on two booms off its left side; on the sand, or up on a
    rack of two A-frames out of the tide's reach."""
    looks = dict(_base_looks(), koa=look('waikiki/koa', tile=220), hull=look('waikiki/hull_teal', tile=220))
    parts = []
    z = 120.0 if rack else 0.0
    if rack:
        for x in (-170, 170):
            for sy in (-1, 1):
                parts.append({'shape': 'box', 'size': [10, 10, 135], 'at': [x, sy * 40, 0], 'turn': [-sy * 14, 0, 0], 'look': 'wood'})
            parts.append({'shape': 'box', 'size': [12, 130, 10], 'at': [x, 0, 112], 'look': 'wood'})
    parts.append({'shape': 'ball', 'r': 1, 'sides': 12, 'rings': 6, 'scale': [330, 30, 27], 'at': [0, 0, z - 6], 'look': 'hull', 'material': 'wood'})
    parts.append({'shape': 'slab', 'size': [520, 44, 4], 'at': [0, 0, z + 40], 'look': 'koa', 'solid': False})
    parts.append({'shape': 'ball', 'r': 1, 'sides': 8, 'rings': 4, 'scale': [190, 11, 11], 'at': [0, -230, z - 2], 'look': 'koa', 'material': 'wood'})
    for x in (-110, 120):
        parts.append({'shape': 'box', 'size': [9, 240, 9], 'at': [x, -115, z + 44], 'turn': [-8, 0, 0], 'look': 'koa', 'solid': False})
    return {'name': 'FOLabWaikikiOutrigger' + ('Rack' if rack else ''), 'looks': looks, 'parts': parts}


def board_rack(seed=1):
    """A rack of surfboards for hire: two posts and rails, five boards leaning on it, nose up."""
    rnd = random.Random(seed)
    looks = dict(_base_looks(), red=look('surf_red'), teal_board=look('surf_teal'))
    parts = [{'shape': 'box', 'size': [10, 10, 180], 'at': [x, 30, 0], 'look': 'wood'} for x in (-200, 200)]
    parts += [{'shape': 'box', 'size': [420, 8, 10], 'at': [0, 30, z], 'look': 'wood'} for z in (90, 165)]
    for k in range(5):
        x = -160 + 80 * k + rnd.uniform(-10, 10)
        parts.append({'shape': 'cylinder', 'r': 1, 'h': 1, 'sides': 14, 'scale': [11, 82, 2.6], 'turn': [74 + rnd.uniform(-4, 4), 0, 0],
                      'at': [x, -10, 84], 'look': 'pole', 'cap_look': 'red' if k % 2 else 'teal_board', 'solid': False})
    return {'name': 'FOLabWaikikiBoardRack%d' % seed, 'looks': looks, 'parts': parts}


def lounger(stripes='waikiki/canvas_blue', seed=1):
    """A slatted wooden beach lounger, its back up, a striped pad on it."""
    looks = dict(_base_looks(), pad=look(stripes, tile=120))
    parts = [{'shape': 'box', 'size': [6, 6, 32], 'at': [x, y, 0], 'look': 'wood', 'solid': False} for x in (-30, 30) for y in (-80, 80)]
    parts.append({'shape': 'slab', 'size': [70, 120, 6], 'at': [0, 30, 32], 'look': 'wood', 'faces': {'top': 'pad'}, 'material': 'wood'})
    parts.append({'shape': 'slab', 'size': [70, 80, 6], 'at': [0, -52, 32], 'turn': [-38, 0, 0], 'look': 'wood', 'faces': {'top': 'pad'}, 'material': 'wood'})
    return {'name': 'FOLabWaikikiLounger%d' % seed, 'looks': looks, 'parts': parts}


def cabana(stripes='waikiki/canvas_blue'):
    """A striped beach cabana: canvas on three sides, a canvas roof with a valance, open to the sea (the front)."""
    looks = dict(_base_looks(), canvas=look(stripes, tile=110))
    w, d, h = 240.0, 220.0, 200.0
    parts = [{'shape': 'box', 'size': [8, 8, h + 20], 'at': [x, y, 0], 'look': 'pole', 'solid': False} for x in (-w / 2, w / 2) for y in (-d / 2, d / 2)]
    parts.append({'shape': 'box', 'size': [w, 4, h], 'at': [0, d / 2, 0], 'look': 'canvas', 'material': 'cloth'})
    parts += [{'shape': 'box', 'size': [4, d, h], 'at': [x, 0, 0], 'look': 'canvas', 'material': 'cloth'} for x in (-w / 2, w / 2)]
    parts.append({'shape': 'cone', 'r': (w + 40) / math.sqrt(2), 'h': 50, 'sides': 4, 'turn': [0, 0, 45], 'scale': [1, d / w, 1], 'at': [0, 0, h + 16],
                  'look': 'canvas', 'under': True, 'solid': False})
    parts.append({'shape': 'box', 'size': [w + 20, 3, 34], 'at': [0, -d / 2 - 8, h - 18], 'look': 'canvas', 'solid': False})
    parts.append({'shape': 'slab', 'size': [w - 20, d - 20, 3], 'at': [0, 0, 0], 'look': 'wood', 'solid': False})
    return {'name': 'FOLabWaikikiCabana' + ('Yellow' if 'yellow' in stripes else 'Blue'), 'looks': looks, 'parts': parts}


def volleyball():
    """A beach volleyball net slung between two posts, sagging."""
    looks = dict(_base_looks(), net=look('waikiki/net', tile=128, alpha=True))
    parts = [{'shape': 'cylinder', 'r': 5, 'h': 250, 'sides': 8, 'at': [x, 0, 0], 'look': 'pole', 'material': 'metal'} for x in (-430, 430)]
    parts.append({'shape': 'card', 'size': [850, 92], 'at': [0, 0, 150], 'look': 'net'})
    parts.append({'shape': 'box', 'size': [860, 3, 3], 'at': [0, 0, 243], 'look': 'pole', 'solid': False})
    return {'name': 'FOLabWaikikiVolleyball', 'looks': looks, 'parts': parts}


# ---------- hotel grounds and the strip ----------

def googie_sign(n=0):
    """A motel's sign of the period: two pylons leaning apart from one plinth, a V, and the name board bolted across
    their fronts: it stands a hand's breadth clear of them on four brackets (one top and bottom where it crosses each
    pylon), so its face is plainly in front and plainly held. (A board flush on the pylons, or one they went through,
    looked pushed into them.) A neon tube round the board's face, an arrow hung under it on two rods, a starburst on
    top of the taller pylon."""
    looks = dict(_base_looks(), board=_motel(n), blade=look(('waikiki/enamel_teal', 'waikiki/enamel_cream')[n % 2], tile=96),
                 steel=look('metal_white', tile=48), arrow=look(('planks_coral', 'planks_turquoise')[n % 2], tile=96),
                 neon=lit(('waikiki/neon_red', 'waikiki/neon_teal')[n % 2], 4.0))
    lean, deep = 9.0, 50.0                                      # degrees each pylon leans out; their depth front to back
    tan = math.tan(math.radians(lean))
    bw, bh, bz, bt, gap = 460.0, 280.0, 560.0, 30.0, 22.0       # the board: width, height, foot, thickness; its gap off the pylons
    by = -deep / 2 - gap - bt / 2                               # the board's middle, front to back
    parts = [{'shape': 'box', 'size': [200, 110, 50], 'look': 'concrete', 'material': 'stone'}]
    for sx, tall in ((-1, 980.0), (1, 1080.0)):
        parts.append({'shape': 'box', 'size': [40, deep, tall], 'at': [sx * 40, 0, 50], 'turn': [0, sx * lean, 0], 'look': 'blade', 'material': 'metal'})
        for z in (bz + 40, bz + bh - 70):                       # the brackets: from the pylon's face to the board's back
            parts.append({'shape': 'box', 'size': [34, gap + 4, 30], 'at': [sx * (40 + (z + 15 - 50) * tan), -deep / 2 - gap / 2, z], 'look': 'steel', 'material': 'metal'})
    parts.append({'shape': 'box', 'size': [bw, bt, bh], 'at': [0, by, bz], 'look': 'blade', 'faces': {'front': 'board', 'back': 'board'}, 'material': 'metal'})
    yn = by - bt / 2 - 3                                        # the neon, just proud of the board's face
    parts += [{'shape': 'box', 'size': [bw + 8, 4, 6], 'at': [0, yn, z], 'look': 'neon', 'solid': False} for z in (bz - 4, bz + bh - 2)]
    parts += [{'shape': 'box', 'size': [6, 4, bh + 2], 'at': [x, yn, bz - 4], 'look': 'neon', 'solid': False} for x in (-bw / 2, bw / 2)]
    # the arrow: a bar under the board hung on two rods, its head a flattened cone pointing along it
    az = bz - 90
    parts += [{'shape': 'box', 'size': [8, 8, 46], 'at': [x, by, az + 44], 'look': 'steel', 'solid': False} for x in (-100, 100)]
    parts.append({'shape': 'box', 'size': [300, 22, 46], 'at': [0, by, az], 'look': 'arrow', 'solid': False})
    parts.append({'shape': 'cone', 'r': 1, 'h': 1, 'sides': 3, 'scale': [40, 12, 70], 'turn': [0, 90, 0], 'at': [150, by, az + 23], 'look': 'arrow', 'solid': False})
    tx = 40 + math.sin(math.radians(lean)) * 1080 + 10           # the taller pylon's top
    tz = 50 + math.cos(math.radians(lean)) * 1080
    parts.append({'shape': 'ball', 'r': 16, 'sides': 8, 'rings': 4, 'at': [tx, 0, tz + 10], 'look': 'neon', 'solid': False})
    for k in range(8):
        parts.append({'shape': 'box', 'size': [150, 5, 5], 'at': [tx, 0, tz + 26], 'turn': [0, k * 22.5, 0], 'look': 'neon', 'solid': False})
    return {'name': 'FOLabWaikikiMotelSign%d' % n, 'looks': looks, 'parts': parts}


def tiki(tall=260.0, n=0):
    """A carved tiki post, its face to the front, a crest on top."""
    looks = {'face': look('waikiki/tiki'), 'wood': look('waikiki/tiki_wood', tile=90)}
    w = 72.0 if tall > 200 else 56.0
    parts = [{'shape': 'box', 'size': [w, w, tall], 'look': 'wood', 'faces': {'front': 'face'}, 'material': 'wood'},
             {'shape': 'box', 'size': [w + 16, w + 16, 14], 'at': [0, 0, tall], 'look': 'wood', 'solid': False},
             {'shape': 'cone', 'r': w * 0.55, 'h': 40, 'sides': 4, 'turn': [0, 0, 45], 'at': [0, 0, tall + 14], 'look': 'wood', 'solid': False}]
    return {'name': 'FOLabWaikikiTiki%d' % round(tall), 'looks': looks, 'parts': parts}


def tiki_bar():
    """A thatched tiki bar: a steep four-sided roof of thatch on bamboo posts, a bar counter faced with bamboo along the
    front with stools before it, a back shelf, the bar's sign hung under the eaves."""
    looks = dict(_base_looks(), sign=_motel(3))
    parts = []
    for x in (-260, 260):
        for y in (-200, 200):
            parts.append({'shape': 'cylinder', 'r': 7, 'h': 250, 'sides': 6, 'at': [x, y, 0], 'look': 'bamboo', 'material': 'wood'})
    parts.append({'shape': 'cone', 'r': 430, 'h': 190, 'sides': 4, 'turn': [0, 0, 45], 'scale': [1, 0.82, 1], 'at': [0, 0, 240], 'look': 'thatch', 'under': True, 'solid': False})
    parts.append({'shape': 'box', 'size': [440, 60, 108], 'at': [0, -120, 0], 'look': 'bamboo', 'faces': {'top': 'wood'}, 'material': 'wood'})
    parts.append({'shape': 'slab', 'size': [480, 90, 6], 'at': [0, -125, 108], 'look': 'wood', 'solid': False})
    parts.append({'shape': 'box', 'size': [440, 40, 180], 'at': [0, 175, 0], 'look': 'wood', 'material': 'wood'})
    parts.append({'shape': 'box', 'size': [300, 8, 90], 'at': [0, -215, 180], 'look': 'wood', 'faces': {'front': 'sign'}, 'solid': False})
    for k in range(4):
        x = -165 + 110 * k
        parts.append({'shape': 'cylinder', 'r': 4, 'h': 66, 'sides': 6, 'at': [x, -215, 0], 'look': 'bamboo', 'solid': False})
        parts.append({'shape': 'cylinder', 'r': 20, 'h': 6, 'sides': 10, 'at': [x, -215, 66], 'look': 'wicker', 'material': 'wood'})
    return {'name': 'FOLabWaikikiTikiBar', 'looks': looks, 'parts': parts}


def lanai_set(seed=1):
    """A round table, four rattan chairs round it, a little striped umbrella through its middle."""
    rnd = random.Random(seed)
    looks = dict(_base_looks(), canopy=look('parasol_coral'))
    parts = [{'shape': 'cylinder', 'r': 8, 'h': 66, 'sides': 8, 'look': 'pole', 'solid': False},
             {'shape': 'cylinder', 'r': 50, 'h': 5, 'sides': 14, 'at': [0, 0, 66], 'look': 'wood', 'material': 'wood'},
             {'shape': 'cylinder', 'r': 2.5, 'h': 205, 'sides': 6, 'at': [0, 0, 0], 'look': 'pole', 'solid': False},
             {'shape': 'cone', 'r': 105, 'h': 32, 'sides': 12, 'at': [0, 0, 180], 'look': 'canopy', 'paint': 'above', 'under': True, 'solid': False}]
    for k in range(4):
        a = math.radians(k * 90 + rnd.uniform(-12, 12))
        x, y = math.cos(a) * 95, math.sin(a) * 95
        face = math.degrees(math.atan2(-y, -x))
        parts.append({'shape': 'box', 'size': [48, 48, 40], 'at': [x, y, 0], 'turn': [0, 0, face], 'look': 'wicker', 'material': 'wood'})
        bx, by = x + math.cos(a) * 26, y + math.sin(a) * 26
        parts.append({'shape': 'box', 'size': [8, 50, 46], 'at': [bx, by, 40], 'turn': [0, 0, face], 'look': 'wicker', 'solid': False})
    return {'name': 'FOLabWaikikiLanaiSet%d' % seed, 'looks': looks, 'parts': parts}


def hula_stage():
    """A low wooden stage for the hotel's show: steps up the front, a thatch backdrop, a tiki torch at each front
    corner, a tiki carving each side of the back."""
    looks = _base_looks()
    parts = [{'shape': 'box', 'size': [640, 400, 40], 'look': 'wood', 'faces': {'top': 'wood'}, 'material': 'wood'},
             {'shape': 'box', 'size': [220, 50, 27], 'at': [0, -225, 0], 'look': 'wood', 'material': 'wood'},
             {'shape': 'box', 'size': [220, 50, 13], 'at': [0, -275, 0], 'look': 'wood', 'material': 'wood'},     # (two steps up)
             {'shape': 'box', 'size': [640, 20, 230], 'at': [0, 190, 40], 'look': 'thatch', 'material': 'wood'}]
    for x in (-300, 300):
        parts.append({'shape': 'cylinder', 'r': 3, 'h': 160, 'sides': 6, 'at': [x, -180, 40], 'look': 'bamboo', 'solid': False})
        parts.append({'shape': 'cylinder', 'r': 4, 'r2': 10, 'h': 18, 'sides': 8, 'at': [x, -180, 200], 'look': 'thatch', 'solid': False})
    desc = {'name': 'FOLabWaikikiHulaStage', 'looks': looks, 'parts': parts}
    for x in (-260, 260):
        for q in tiki(160.0)['parts']:
            q = dict(q, at=[x + q.get('at', (0, 0, 0))[0], 150 + q.get('at', (0, 0, 0))[1], 40 + q.get('at', (0, 0, 0))[2]],
                     look={'wood': 'tiki_wood', 'face': 'tiki_face'}[q['look']], faces={'front': 'tiki_face'} if q.get('faces') else None)
            if q['faces'] is None:
                q.pop('faces')
            parts.append(q)
    looks.update(tiki_face=look('waikiki/tiki'), tiki_wood=look('waikiki/tiki_wood', tile=90))
    return desc


# ---------- streets and markets ----------

def bus_shelter():
    """A thatched bus shelter: a lean roof of thatch on bamboo posts, a bench, the stop's board."""
    looks = dict(_base_looks(), sign=_sign(0))
    parts = [{'shape': 'cylinder', 'r': 6, 'h': h, 'sides': 6, 'at': [x, y, 0], 'look': 'bamboo', 'material': 'wood'}
             for x in (-200, 200) for y, h in ((-70, 240), (70, 215))]
    parts.append({'shape': 'slab', 'size': [480, 230, 8], 'at': [0, 0, 222], 'turn': [-7, 0, 0], 'look': 'thatch', 'under': True, 'solid': False})
    parts.append({'shape': 'cone', 'r': 1, 'h': 1, 'sides': 4})                     # (placeholder removed below)
    parts.pop()
    parts.append({'shape': 'slab', 'size': [360, 50, 6], 'at': [0, 40, 44], 'look': 'wood', 'material': 'wood'})
    parts += [{'shape': 'box', 'size': [6, 40, 44], 'at': [x, 40, 0], 'look': 'wood', 'solid': False} for x in (-160, 160)]
    parts.append({'shape': 'box', 'size': [8, 8, 260], 'at': [260, -110, 0], 'look': 'pole', 'solid': False})
    parts.append({'shape': 'box', 'size': [110, 6, 70], 'at': [260, -114, 260], 'look': 'pole', 'faces': {'front': 'sign', 'back': 'sign'}, 'solid': False})
    return {'name': 'FOLabWaikikiBusShelter', 'looks': looks, 'parts': parts}


def _awning(parts, w, d, z, look_name, y=0.0):
    parts += [{'shape': 'box', 'size': [5, 5, z], 'at': [x, yy, 0], 'look': 'pole', 'solid': False} for x in (-w / 2, w / 2) for yy in (y - d / 2, y + d / 2)]
    parts.append({'shape': 'slab', 'size': [w + 30, d + 30, 4], 'at': [0, y, z], 'turn': [-8, 0, 0], 'look': look_name, 'under': True, 'solid': False})


def lei_stand():
    """A lei seller's stand: a counter, leis hung in loops across the front of a frame, a striped awning, the board."""
    looks = dict(_base_looks(), leis=look('waikiki/leis', alpha=True), canvas=look('waikiki/canvas_yellow', tile=110), sign=_sign(3))
    parts = [{'shape': 'box', 'size': [240, 80, 96], 'at': [0, 20, 0], 'look': 'coral', 'faces': {'top': 'wood'}, 'material': 'wood'}]
    _awning(parts, 280, 200, 215, 'canvas', y=30)
    parts.append({'shape': 'box', 'size': [280, 4, 4], 'at': [0, -70, 200], 'look': 'pole', 'solid': False})
    parts.append({'shape': 'card', 'size': [270, 110], 'at': [0, -72, 92], 'look': 'leis'})
    parts.append({'shape': 'box', 'size': [130, 4, 50], 'at': [0, -22, 96], 'look': 'wood', 'faces': {'front': 'sign'}, 'solid': False})
    return {'name': 'FOLabWaikikiLeiStand', 'looks': looks, 'parts': parts}


def shave_ice_cart():
    """A shave-ice cart on bicycle wheels: a white box with a striped awning on poles, a handle to push it, the board."""
    looks = dict(_base_looks(), canvas=look('waikiki/canvas_blue', tile=110), sign=_sign(4), body=look('waikiki/enamel_cream', tile=96))
    parts = [{'shape': 'box', 'size': [190, 90, 80], 'at': [0, 0, 34], 'look': 'body', 'faces': {'front': 'sign'}, 'material': 'metal'}]
    for x in (-60, 60):
        parts.append({'shape': 'cylinder', 'r': 30, 'h': 6, 'sides': 12, 'turn': [90, 0, 0], 'at': [x, -48, 30], 'look': 'rust', 'solid': False})
        parts.append({'shape': 'cylinder', 'r': 30, 'h': 6, 'sides': 12, 'turn': [90, 0, 0], 'at': [x, 54, 30], 'look': 'rust', 'solid': False})
    parts.append({'shape': 'box', 'size': [80, 6, 6], 'at': [135, 0, 96], 'look': 'pole', 'solid': False})
    _awning(parts, 200, 110, 200, 'canvas')
    return {'name': 'FOLabWaikikiShaveIceCart', 'looks': looks, 'parts': parts}


def fruit_stall():
    """A roadside fruit stall: a trestle table, crates of pineapples on it and under it, a heap of coconuts, a tin
    awning on poles, the board."""
    rnd = random.Random(5)
    looks = dict(_base_looks(), fruit=look('waikiki/pineapples'), husk=look('waikiki/husk', tile=60), sign=_sign(5))
    parts = [{'shape': 'slab', 'size': [320, 120, 6], 'at': [0, 0, 80], 'look': 'wood', 'material': 'wood'}]
    parts += [{'shape': 'box', 'size': [6, 110, 80], 'at': [x, 0, 0], 'look': 'wood', 'solid': False} for x in (-140, 140)]
    for k, (x, z) in enumerate(((-100, 86), (0, 86), (100, 86), (-60, 0), (70, 0))):
        parts.append({'shape': 'box', 'size': [86, 64, 34], 'at': [x, 0, z], 'look': 'wood', 'faces': {'top': 'fruit'}, 'material': 'wood'})
    for _ in range(9):
        a, d = rnd.uniform(0, math.tau), rnd.uniform(0, 45)
        parts.append({'shape': 'ball', 'r': 13, 'sides': 7, 'rings': 4, 'at': [230 + math.cos(a) * d, -10 + math.sin(a) * d, rnd.choice((0, 0, 18))], 'look': 'husk', 'solid': False})
    _awning(parts, 360, 180, 210, 'tin', y=30)
    parts.append({'shape': 'box', 'size': [130, 4, 50], 'at': [0, -64, 86], 'look': 'wood', 'faces': {'front': 'sign'}, 'solid': False})
    return {'name': 'FOLabWaikikiFruitStall', 'looks': looks, 'parts': parts}


def street_lamp():
    """A street lamp of the time: a tapered pole, an arm reaching over the road, a coolie-hat shade (not lit)."""
    looks = dict(_base_looks(), paint=look('waikiki/enamel_teal', tile=64))
    parts = [{'shape': 'cylinder', 'r': 9, 'r2': 5, 'h': 560, 'sides': 8, 'look': 'paint', 'material': 'metal'},
             {'shape': 'box', 'size': [190, 8, 8], 'at': [-90, 0, 556], 'turn': [0, -6, 0], 'look': 'paint', 'solid': False},
             {'shape': 'cone', 'r': 38, 'h': 22, 'sides': 12, 'at': [-180, 0, 540], 'look': 'paint', 'under': True, 'solid': False},
             {'shape': 'ball', 'r': 11, 'sides': 8, 'rings': 4, 'at': [-180, 0, 524], 'look': 'bulb', 'solid': False}]
    looks['bulb'] = lit('waikiki/lamp_glass', 3.0)
    return {'name': 'FOLabWaikikiStreetLamp', 'looks': looks, 'parts': parts}


def sandwich_board(n=1):
    """A painted A-board on the pavement."""
    looks = dict(_base_looks(), sign=_sign(n))
    parts = [{'shape': 'box', 'size': [80, 4, 110], 'at': [0, y, 0], 'turn': [t, 0, 0], 'look': 'wood', 'faces': {'front': 'sign', 'back': 'sign'}, 'material': 'wood'}
             for y, t in ((-18, 9), (18, -9))]
    return {'name': 'FOLabWaikikiBoard%d' % n, 'looks': looks, 'parts': parts}


# ---------- the harbour and the old town ----------

def hale():
    """A hale: a one-room thatched house on a low platform, walls of woven mat, a doorway in the front with a step up,
    a steep four-sided roof of thatch. You walk in."""
    looks = _base_looks()
    w, d, up = 460.0, 380.0, 24.0
    parts = [{'shape': 'box', 'size': [w + 40, d + 40, up], 'look': 'wood', 'material': 'wood'},
             {'shape': 'box', 'size': [140, 60, 12], 'at': [0, -(d + 40) / 2 - 30, 0], 'look': 'wood', 'material': 'wood'}]     # (a step a body takes)
    wall = 200.0
    parts.append({'shape': 'box', 'size': [w, 8, wall], 'at': [0, d / 2, up], 'look': 'wicker', 'material': 'wood'})
    parts += [{'shape': 'box', 'size': [8, d, wall], 'at': [x, 0, up], 'look': 'wicker', 'material': 'wood'} for x in (-w / 2, w / 2)]
    door = 120.0
    for sx in (-1, 1):                                          # the front, a doorway in its middle
        parts.append({'shape': 'box', 'size': [(w - door) / 2, 8, wall], 'at': [sx * (w + door) / 4, -d / 2, up], 'look': 'wicker', 'material': 'wood'})
    parts.append({'shape': 'box', 'size': [door + 20, 8, 30], 'at': [0, -d / 2, up + wall - 30], 'look': 'wood', 'solid': False})
    parts.append({'shape': 'cone', 'r': (w + 120) / math.sqrt(2), 'h': 300, 'sides': 4, 'turn': [0, 0, 45], 'scale': [1, (d + 120) / (w + 120), 1],
                  'at': [0, 0, up + wall - 10], 'look': 'thatch', 'under': True, 'solid': False})
    return {'name': 'FOLabWaikikiHale', 'looks': looks, 'parts': parts}


def sampan():
    """A fishing sampan: a beamy wooden hull painted and worn, a little wheelhouse with a tin roof aft, a mast forward.
    It floats: stand it with its origin at the water's surface."""
    looks = dict(_base_looks(), hull=look('waikiki/hull_white', tile=260), deck=look('planks_cream', tile=96))
    parts = [{'shape': 'ball', 'r': 1, 'sides': 12, 'rings': 6, 'scale': [400, 110, 90], 'at': [0, 0, -120], 'look': 'hull', 'material': 'wood'},
             {'shape': 'slab', 'size': [640, 170, 6], 'at': [0, 0, 20], 'look': 'deck', 'material': 'wood'},
             {'shape': 'box', 'size': [180, 140, 170], 'at': [-150, 0, 26], 'look': 'teal', 'material': 'wood'},
             {'shape': 'slab', 'size': [210, 170, 6], 'at': [-150, 0, 196], 'turn': [0, 4, 0], 'look': 'tin', 'solid': False},
             {'shape': 'cylinder', 'r': 5, 'h': 420, 'sides': 6, 'at': [160, 0, 26], 'look': 'wood', 'solid': False},
             {'shape': 'box', 'size': [4, 4, 300], 'at': [160, 0, 140], 'turn': [0, 60, 0], 'look': 'wood', 'solid': False}]
    return {'name': 'FOLabWaikikiSampan', 'looks': looks, 'parts': parts}


def net_rack():
    """A rack of poles with fishing nets hung over it to dry, a float or two caught in them."""
    looks = dict(_base_looks(), net=look('waikiki/net', tile=128, alpha=True))
    parts = [{'shape': 'box', 'size': [9, 9, 220], 'at': [x, 0, 0], 'look': 'wood'} for x in (-220, 0, 220)]
    parts.append({'shape': 'box', 'size': [470, 8, 8], 'at': [0, 0, 212], 'look': 'wood', 'solid': False})
    for sy in (-1, 1):
        parts.append({'shape': 'card', 'size': [450, 200], 'at': [0, sy * 22, 6], 'turn': [sy * 6, 0, 0], 'look': 'net'})
    parts += [{'shape': 'ball', 'r': 9, 'sides': 8, 'rings': 4, 'at': [x, -26, z], 'look': 'coral', 'solid': False} for x, z in ((-120, 120), (90, 70), (170, 150))]
    return {'name': 'FOLabWaikikiNetRack', 'looks': looks, 'parts': parts}


def crab_pots():
    """Crab pots stacked on the dock: frames of wood with netting, three high."""
    looks = dict(_base_looks(), net=look('waikiki/net', tile=64, alpha=True))
    parts = []
    for k, (x, y, z) in enumerate(((0, 0, 0), (75, 10, 0), (36, 4, 52))):
        parts.append({'shape': 'box', 'size': [70, 56, 50], 'at': [x, y, z], 'look': 'net', 'material': 'wood'})
        for dx in (-33, 33):
            parts.append({'shape': 'box', 'size': [4, 58, 4], 'at': [x + dx, y, z + 48], 'look': 'wood', 'solid': False})
    return {'name': 'FOLabWaikikiCrabPots', 'looks': looks, 'parts': parts}


def tiki_torch(tall=170.0):
    """A tiki torch alight: a bamboo pole, a woven bowl, the flame over it."""
    looks = dict(_base_looks(), fire=lit('waikiki/flame', 4.0, alpha=True))
    parts = [{'shape': 'cylinder', 'r': 3, 'r2': 2.4, 'h': tall, 'sides': 6, 'look': 'bamboo', 'material': 'wood'},
             {'shape': 'cylinder', 'r': 4, 'r2': 10, 'h': 20, 'sides': 8, 'at': [0, 0, tall - 6], 'look': 'thatch', 'solid': False},
             {'shape': 'card', 'size': [26, 46], 'at': [0, 0, tall + 12], 'look': 'fire'},
             {'shape': 'card', 'size': [26, 46], 'at': [0, 0, tall + 12], 'turn': [0, 0, 90], 'look': 'fire'}]
    return {'name': 'FOLabWaikikiTikiTorch%d' % round(tall), 'looks': looks, 'parts': parts}


def tiki_gate():
    """A tiki gateway, for a bar's or a hotel's way in: two tall carvings either side, a thatched lintel across, a
    torch burning on each post's outer side."""
    desc = {'name': 'FOLabWaikikiTikiGate', 'looks': dict(_base_looks(), tiki_face=look('waikiki/tiki'), tiki_wood=look('waikiki/tiki_wood', tile=90),
                                                         fire=lit('waikiki/flame', 4.0, alpha=True)), 'parts': []}
    parts = desc['parts']
    for x in (-210, 210):
        parts.append({'shape': 'box', 'size': [80, 80, 330], 'at': [x, 0, 0], 'look': 'tiki_wood', 'faces': {'front': 'tiki_face', 'back': 'tiki_face'}, 'material': 'wood'})
        for q in tiki_torch(190.0)['parts']:
            a = q.get('at', (0, 0, 0))
            parts.append(dict(q, at=[x + (1 if x > 0 else -1) * 85 + a[0], a[1], a[2]]))
    parts.append({'shape': 'box', 'size': [560, 110, 60], 'at': [0, 0, 330], 'look': 'tiki_wood', 'material': 'wood'})
    parts.append({'shape': 'cone', 'r': 330, 'h': 90, 'sides': 4, 'turn': [0, 0, 45], 'scale': [1, 0.3, 1], 'at': [0, 0, 386], 'look': 'thatch', 'under': True, 'solid': False})
    return desc


def bamboo_fence(long=400.0):
    """A run of bamboo fence: canes side by side, lashed to two rails."""
    looks = _base_looks()
    parts = [{'shape': 'box', 'size': [long, 10, 10], 'at': [0, 6, z], 'look': 'bamboo', 'solid': False} for z in (40, 110)]
    n = int(long // 9)
    for k in range(n):
        h = 130 + (k * 37 % 11) - 5
        parts.append({'shape': 'cylinder', 'r': 4.5, 'h': h, 'sides': 5, 'at': [-long / 2 + (k + 0.5) * long / n, 0, 0], 'look': 'bamboo', 'solid': False})
    parts.append({'shape': 'box', 'size': [long, 10, 135], 'at': [0, 0, 0], 'look': None, 'material': 'wood'})     # (one to walk into: nothing drawn)
    return {'name': 'FOLabWaikikiBambooFence%d' % round(long), 'looks': looks, 'parts': parts}


def lava_planter():
    """A planter walled in lava rock, ti plants in it, a tiki torch at each end: what stood at every hotel's door."""
    looks = dict(_base_looks(), lava=look('hotel/lava', tile=160), soil=look('waikiki/husk', tile=60))
    parts = [{'shape': 'box', 'size': [440, 110, 62], 'look': 'lava', 'faces': {'top': 'soil'}, 'material': 'stone'}]
    desc = {'name': 'FOLabWaikikiLavaPlanter', 'looks': looks, 'parts': parts}
    for x in (-250, 250):
        for q in tiki_torch(150.0)['parts']:
            a = q.get('at', (0, 0, 0))
            parts.append(dict(q, at=[x + a[0], a[1], a[2]]))
    looks.update(fire=lit('waikiki/flame', 4.0, alpha=True))
    for k, x in enumerate((-130, 0, 130)):
        ti = modelsets.ti_plant('t', 'jungle/ti_red' if k % 2 else 'jungle/ti_green', seed=60 + k)
        for name_, v in ti['looks'].items():
            looks['ti%d_%s' % (k, name_)] = v
        for q in ti['parts']:
            a = q.get('at', (0, 0, 0))
            parts.append(dict(q, at=[x + a[0] * 0.8, a[1] * 0.8, 62 + a[2] * 0.8], scale=[v * 0.8 for v in q.get('scale', (1, 1, 1))], look='ti%d_%s' % (k, q['look'])))
    return desc


def puffer_lamp():
    """A puffer-fish lamp, the tiki bar's: a round spiny float with a light inside, hung from a bracket on a post."""
    looks = dict(_base_looks(), glow=lit('waikiki/lamp_glass', 3.0))
    parts = [{'shape': 'cylinder', 'r': 5, 'h': 300, 'sides': 6, 'look': 'bamboo', 'material': 'wood'},
             {'shape': 'box', 'size': [90, 6, 6], 'at': [-45, 0, 290], 'look': 'bamboo', 'solid': False},
             {'shape': 'box', 'size': [2, 2, 40], 'at': [-88, 0, 250], 'look': 'rust', 'solid': False},
             {'shape': 'ball', 'r': 28, 'sides': 10, 'rings': 6, 'at': [-88, 0, 196], 'look': 'glow', 'solid': False}]
    for k in range(10):                                         # spines
        a = math.radians(k * 36)
        parts.append({'shape': 'cone', 'r': 4, 'h': 18, 'sides': 4, 'turn': [70, 0, k * 36], 'at': [-88 + math.cos(a) * 26, math.sin(a) * 26, 222], 'look': 'thatch', 'solid': False})
    return {'name': 'FOLabWaikikiPufferLamp', 'looks': looks, 'parts': parts}


def string_lights(long=800.0):
    """A string of bulbs slung between two posts, sagging, over a lanai or a bar's yard."""
    looks = dict(_base_looks(), bulb=lit('waikiki/lamp_glass', 3.0))
    parts = [{'shape': 'cylinder', 'r': 6, 'h': 330, 'sides': 6, 'at': [x, 0, 0], 'look': 'wood', 'material': 'wood'} for x in (-long / 2, long / 2)]
    n = 16
    for k in range(n + 1):
        t = k / float(n)
        x, z = -long / 2 + long * t, 320 - 70 * math.sin(math.pi * t)
        if 0 < k < n:
            parts.append({'shape': 'ball', 'r': 6, 'sides': 6, 'rings': 3, 'at': [x, 0, z - 14], 'look': 'bulb', 'solid': False})
        if k < n:
            x2, z2 = -long / 2 + long * (k + 1) / n, 320 - 70 * math.sin(math.pi * (k + 1) / n)
            parts.append({'shape': 'box', 'size': [math.hypot(x2 - x, z2 - z), 1.5, 1.5], 'at': [(x + x2) / 2, 0, (z + z2) / 2], 'turn': [0, -math.degrees(math.atan2(z2 - z, x2 - x)), 0], 'look': 'rust', 'solid': False})
    return {'name': 'FOLabWaikikiStringLights%d' % round(long), 'looks': looks, 'parts': parts}


PIECES = {
    # the beach
    'lifeguard_tower': ('Lifeguard tower', lifeguard_tower),
    'outrigger': ('Outrigger canoe', lambda: outrigger(False)),
    'outrigger_rack': ('Outrigger canoe on its rack', lambda: outrigger(True)),
    'board_rack': ('Surfboard rack', lambda: board_rack(1)),
    'lounger_blue': ('Beach lounger', lambda: lounger('waikiki/canvas_blue', 1)),
    'lounger_yellow': ('Beach lounger, yellow', lambda: lounger('waikiki/canvas_yellow', 2)),
    'cabana_blue': ('Cabana', lambda: cabana('waikiki/canvas_blue')),
    'cabana_yellow': ('Cabana, yellow', lambda: cabana('waikiki/canvas_yellow')),
    'volleyball': ('Volleyball net', volleyball),
    # hotel grounds and the strip
    'motel_sign_0': ('Motel sign, Mahalo Motor Inn', lambda: googie_sign(0)),
    'motel_sign_1': ('Motel sign, Sea Breeze', lambda: googie_sign(1)),
    'motel_sign_2': ('Motel sign, Kona Kai Courts', lambda: googie_sign(2)),
    'motel_sign_3': ('Bar sign, Tiki Room', lambda: googie_sign(3)),
    'tiki_tall': ('Tiki carving, tall', lambda: tiki(260.0)),
    'tiki_short': ('Tiki carving', lambda: tiki(160.0)),
    'tiki_bar': ('Tiki bar', tiki_bar),
    'lanai_set': ('Lanai table and chairs', lambda: lanai_set(1)),
    'hula_stage': ('Hula stage', hula_stage),
    # streets and markets
    'bus_shelter': ('Bus shelter', bus_shelter),
    'lei_stand': ('Lei stand', lei_stand),
    'shave_ice_cart': ('Shave ice cart', shave_ice_cart),
    'fruit_stall': ('Fruit stall', fruit_stall),
    'street_lamp': ('Street lamp', street_lamp),
    'board_surf': ('A-board, surf shop', lambda: sandwich_board(1)),
    'board_poi': ('A-board, fresh poi', lambda: sandwich_board(2)),
    # the harbour
    'hale': ('Hale', hale),
    'sampan': ('Sampan', sampan),
    'net_rack': ('Net rack', net_rack),
    'crab_pots': ('Crab pots', crab_pots),
    # tiki, and what lights the night
    'tiki_torch_lit': ('Tiki torch, lit', lambda: tiki_torch(170.0)),
    'tiki_gate': ('Tiki gateway', tiki_gate),
    'bamboo_fence': ('Bamboo fence', lambda: bamboo_fence(400.0)),
    'lava_planter': ('Lava rock planter with torches', lava_planter),
    'puffer_lamp': ('Puffer fish lamp', puffer_lamp),
    'string_lights': ('String of lights', lambda: string_lights(800.0)),
}
LIGHTS.update({
    'tiki_torch_lit': [('FireBrightOrange', 0, 0, 200)],
    'tiki_gate': [('FireBrightOrange', -295, 0, 220), ('FireBrightOrange', 295, 0, 220)],
    'lava_planter': [('FireBrightOrange', 0, 0, 190)],
    'puffer_lamp': [('ExtLightWarm02', -88, 0, 190)],
    'string_lights': [('ExtLightWarm02', 0, 0, 230)],
    'street_lamp': [('OVStreetLightOld', -180, 0, 500)],
    'motel_sign_0': [('NVLightNeonRed', 0, -150, 700)], 'motel_sign_1': [('StripLightKeyNeutral', 0, -150, 700)],
    'motel_sign_2': [('NVLightNeonRed', 0, -150, 700)], 'motel_sign_3': [('StripLightKeyNeutral', 0, -150, 700)],     # (the game's own, not a DLC's)
    'tiki_bar': [('ExtLightWarm02', 0, -60, 200)],
})
for _k, (_label, _fn) in PIECES.items():
    modelsets.PIECES.setdefault(_k, {'label': _label, 'set': SET, 'file': _k, 'describe': _fn, 'edid': _fn()['name']})
