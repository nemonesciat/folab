"""Models of FOLab's own making, by theme: the first set is a late-fifties Hawaiian beach.

The game's pieces are the Mojave's; a Waikiki needs its own. A piece here is a description (`modelmake`: boxes,
cylinders, cones) over textures drawn in code (`texpaint`), so nothing is fetched and nothing is anyone else's work:
what `put` writes may go out with a mod. To add a piece: a function returning its description, and a line in `PIECES`;
a new texture is a line in `TEXTURES`. Sizes are game units, 70 to the metre; a piece's front is towards -y and it
stands on z 0.

`put` writes a piece's mesh and textures among the mod's own files (`library.assets_dir`: meshes\\folab\\<set>\\,
textures\\folab\\<set>\\) and gives the op that makes its STAT; `post` is /api/models/."""
import math
import os
import random

import library
import modelmake
import recordio
import texpaint as tp

SET = 'beach'

TEXTURES = {
    'planks_turquoise': lambda: tp.planks(tp.TURQUOISE, seed=11),
    'planks_cream': lambda: tp.planks(tp.CREAM, seed=12, wear=0.16),
    'planks_coral': lambda: tp.planks(tp.CORAL, seed=13),
    'concrete': lambda: tp.concrete(seed=14),
    'metal_white': lambda: tp.painted_metal(tp.WHITE, seed=15),
    'parasol_coral': lambda: tp.parasol(tp.CORAL, tp.CREAM, seed=16),
    'cloth_coral': lambda: tp.cloth_stripes(tp.CORAL, tp.CREAM, seed=17),
    'kiosk_signs': lambda: tp.sign([
        {'box': (0, 0, 1, 0.5), 'lines': ['SURF & SNACKS'], 'ground': tp.CREAM, 'ink': tp.TEAL_INK, 'edge': tp.CORAL},
        {'box': (0, 0.5, 0.5, 1), 'lines': ['SHAVE ICE', 'COLD DRINKS', 'BOARD RENTAL'], 'ground': tp.WHITE,
         'inks': [tp.RED, tp.TEAL_INK, tp.TEAL_INK], 'edge': tp.TURQUOISE},
        {'box': (0.5, 0.5, 1, 1), 'lines': ['ALOHA'], 'ground': tp.YELLOW, 'ink': tp.RED, 'edge': tp.WHITE}], seed=18),
    'surf_red': lambda: tp.surfboard(tp.RED, tp.CREAM, seed=19),
    'surf_teal': lambda: tp.surfboard(tp.TURQUOISE, tp.YELLOW, seed=20),
    # growing things: the leaf pictures are see-through round the leaf
    'palm_frond': lambda: tp.palm_frond(seed=30),
    'palm_frond_dry': lambda: tp.palm_frond(seed=36, dry=0.7),
    'banana_leaf': lambda: tp.broad_leaf(seed=31),
    'hibiscus': lambda: tp.bush(seed=32),
    'dune_grass': lambda: tp.grass(seed=33),
    'palm_bark': lambda: tp.bark_rings(seed=34),
    'stalk': lambda: tp.stalk(seed=35),
    'bamboo': lambda: tp.stalk(colour=(196, 170, 104), seed=37),
    # a jungle
    'jungle/canopy': lambda: tp.foliage(size=512, seed=40, leaves=2400, leaf=0.034),
    'jungle/canopy_dark': lambda: tp.foliage(size=512, seed=47, leaves=2400, leaf=0.04, slim=0.62, dark=(26, 60, 34), light=(84, 132, 60)),
    'jungle/thicket': lambda: tp.foliage(size=512, seed=48, shape='dome', leaves=2200, leaf=0.045, slim=0.6, light=tp.LEAF_LIGHT, stems=6),
    'jungle/undergrowth': lambda: tp.foliage(size=256, seed=49, shape='dome', leaves=700, leaf=0.075, slim=0.7, dark=(40, 88, 40), light=(124, 172, 78), flowers=5, bloom=(232, 120, 60)),
    'jungle/bamboo_leaves': lambda: tp.foliage(size=256, seed=50, leaves=800, leaf=0.085, slim=0.2, dark=(64, 104, 44), light=(150, 180, 84)),
    'jungle/fern': lambda: tp.fern_frond(seed=41),
    'jungle/taro': lambda: tp.stalk_leaf(seed=42),
    'jungle/ti_red': lambda: tp.lance_leaf(seed=43),
    'jungle/ti_green': lambda: tp.lance_leaf(colour=(70, 128, 54), rib=(190, 200, 96), seed=51),
    'jungle/vines': lambda: tp.vines(seed=44),
    'jungle/heliconia': lambda: tp.heliconia(seed=45),
    'jungle/bark': lambda: tp.bark_furrowed(seed=46),
    'jungle/fibre': lambda: tp.bark_rings(colour=(86, 64, 46), rings=12, seed=52),
    'jungle/cane': lambda: tp.stalk(colour=(128, 150, 74), seed=53),
    'jungle/spray': lambda: tp.leaf_spray(seed=90),
    'jungle/spray_bush': lambda: tp.leaf_spray(seed=94, dark=(36, 82, 38), light=(116, 166, 72), leaf=0.1, slim=0.5),
    'jungle/spray_broad': lambda: tp.leaf_spray(seed=95, dark=(30, 74, 36), light=(98, 150, 64), leaf=0.13, slim=0.62),
    'jungle/spray_hibiscus': lambda: tp.leaf_spray(seed=96, dark=(34, 86, 40), light=(108, 160, 70), leaf=0.1, slim=0.55, flowers=7),
    'jungle/spray_dark': lambda: tp.leaf_spray(seed=91, dark=(24, 58, 32), light=(78, 126, 56), leaf=0.085, slim=0.5),
    'jungle/spray_light': lambda: tp.leaf_spray(seed=92, dark=(52, 96, 40), light=(140, 178, 78), leaf=0.07),
    'jungle/grass_tuft': lambda: tp.grass(seed=93, colour=(96, 142, 60)),
    # hotels
    'hotel/lanai': lambda: tp.facade_lanai(seed=60),
    'hotel/lanai_turquoise': lambda: tp.facade_lanai(front=tp.TURQUOISE, seed=70),
    'hotel/lanai_coral': lambda: tp.facade_lanai(front=tp.CORAL, seed=71),
    'hotel/arch': lambda: tp.facade_arch(seed=63),
    'hotel/stucco_pink': lambda: tp.stucco(tp.PINK, seed=62),
    'hotel/stucco_white': lambda: tp.stucco(tp.CONCRETE_WHITE, seed=72),
    'hotel/blocks': lambda: tp.breeze_blocks(seed=61),
    'hotel/lava': lambda: tp.lava_rock(seed=64),
    'hotel/shopfront': lambda: tp.shopfront(seed=65),
    'hotel/signs': lambda: tp.sign([
        {'box': (0, 0, 1, 0.25), 'lines': ['MAKAI TOWER'], 'ground': tp.CONCRETE_WHITE, 'ink': tp.TEAL_INK, 'edge': tp.TURQUOISE},
        {'box': (0, 0.25, 1, 0.5), 'lines': ['BLUE LAGOON'], 'ground': tp.TURQUOISE, 'ink': tp.WHITE, 'edge': tp.CORAL},
        {'box': (0, 0.5, 1, 0.75), 'lines': ['PINK PEARL HOTEL'], 'ground': tp.CREAM, 'ink': tp.RED, 'edge': tp.PINK},
        {'box': (0, 0.75, 1, 1), 'lines': ['KAHUNA PALMS'], 'ground': tp.YELLOW, 'ink': tp.RED, 'edge': tp.WHITE}], w=512, h=512, seed=73),
    # (as they read from across the bay: what the far models wear)
    'hotel/far_cream': lambda: tp.far_facade(seed=66),
    'hotel/far_turquoise': lambda: tp.far_facade(front=tp.TURQUOISE, seed=67),
    'hotel/far_coral': lambda: tp.far_facade(front=tp.CORAL, seed=68),
    'hotel/far_pink': lambda: tp.far_facade(wall=tp.PINK, seed=69),
    'hotel/far_plain_pink': lambda: tp.stucco(tp.PINK, size=32, seed=74),
    'hotel/far_plain_white': lambda: tp.stucco(tp.CONCRETE_WHITE, size=32, seed=75),
    'hotel/far_plain_lava': lambda: tp.stucco(tp.LAVA, size=32, seed=76),
    'hotel/far_plain_glass': lambda: tp.stucco((40, 62, 64), size=32, seed=77),
    'hotel/far_plain_coral': lambda: tp.stucco(tp.CORAL, size=32, seed=78),
}

# The hotels' and the shore's pictures in texwear's worn paint (same names, purpose and layout: the models are as they
# were). The coast's are put in by coastset, after its own.
import texwear  # noqa: E402
TEXTURES.update({k: v for k, v in texwear.UPGRADE().items() if not k.startswith('coast/')})


def tex_path(name, normal=False):
    """Where a texture goes: in the beach set's folder, or for 'jungle/canopy' and the like in that set's."""
    folder, _s, name = name.rpartition('/')
    return 'textures\\folab\\%s\\%s%s.dds' % (folder or SET, name, '_n' if normal else '')


def look(name, **how):
    """A look over one of the set's textures. how: tile, turned, region (see modelmake)."""
    return dict(how, tex=tex_path(name), normal=tex_path(name, True))


# ---------- the pieces ----------

def kiosk():
    """A walk-up stand: plank walls to the back and sides, a counter across the front, a butterfly roof (two slopes
    falling to the middle) on four posts with its sign standing in the dip, a pylon at one corner, two boards for hire
    leaning on the side."""
    looks = {
        'wall': look('planks_turquoise', tile=96), 'trim': look('planks_cream', tile=96), 'beam': look('planks_cream', tile=96, turned=True),
        'roof': look('planks_coral', tile=128), 'floor': look('concrete', tile=160), 'white': look('metal_white', tile=48),
        'sign': look('kiosk_signs', region=(0, 0, 1, 0.5)), 'menu': look('kiosk_signs', region=(0, 0.5, 0.5, 1)),
        'aloha': look('kiosk_signs', region=(0.5, 0.5, 1, 1)), 'pylon': look('planks_coral', tile=96),
        'board_a': look('surf_red'), 'board_b': look('surf_teal')}
    parts = [
        {'shape': 'slab', 'size': [250, 170, 6], 'at': [0, 0, 0], 'look': 'floor', 'material': 'stone'},
        {'shape': 'box', 'size': [230, 6, 164], 'at': [0, 72, 6], 'look': 'wall'},
        {'shape': 'box', 'size': [6, 138, 164], 'at': [-112, 0, 6], 'look': 'wall'},
        {'shape': 'box', 'size': [6, 138, 164], 'at': [112, 0, 6], 'look': 'wall'},
        {'shape': 'box', 'size': [218, 6, 68], 'at': [0, -72, 6], 'look': 'wall'},
        {'shape': 'slab', 'size': [238, 34, 4], 'at': [0, -80, 74], 'look': 'beam'},                      # the counter
        {'shape': 'slab', 'size': [200, 22, 3], 'at': [0, 58, 96], 'look': 'beam', 'solid': False},      # a shelf behind
        {'shape': 'box', 'size': [92, 2, 46], 'at': [0, 68, 108], 'look': 'trim', 'faces': {'front': 'menu'}, 'solid': False},
        {'shape': 'box', 'size': [8, 190, 8], 'at': [0, -8, 170], 'look': 'trim', 'solid': False},        # under the roof's dip
    ]
    for x in (-112, 112):
        for y in (-72, 72):
            parts.append({'shape': 'box', 'size': [8, 8, 195], 'at': [x, y, 6], 'look': 'trim'})
    # the roof: each half 12 degrees down towards the middle
    for side in (-1, 1):
        parts.append({'shape': 'slab', 'size': [131, 196, 5], 'at': [side * 63.5, -10, 191], 'turn': [0, -side * 12, 0],
                      'look': 'roof', 'faces': {'bottom': 'trim'}})
    parts += [
        {'shape': 'box', 'size': [156, 4, 38], 'at': [0, -100, 195], 'look': 'trim', 'faces': {'front': 'sign', 'back': 'sign'}},
        # the pylon, leaning out, with its board
        {'shape': 'box', 'size': [7, 7, 262], 'at': [-131, -90, 0], 'turn': [0, -5, 0], 'look': 'pylon'},
        {'shape': 'box', 'size': [56, 4, 28], 'at': [-150, -90, 236], 'look': 'white', 'faces': {'front': 'aloha', 'back': 'aloha'}, 'solid': False},
        # boards: a flat round stretched long, stood nearly on end against the wall
        {'shape': 'cylinder', 'r': 1, 'h': 1, 'sides': 16, 'scale': [11, 82, 2.6], 'turn': [80, 0, 90], 'at': [131, 22, 88],
         'look': 'white', 'cap_look': 'board_a'},
        {'shape': 'cylinder', 'r': 1, 'h': 1, 'sides': 16, 'scale': [10, 74, 2.6], 'turn': [77, 0, 90], 'at': [134, -24, 80],
         'look': 'white', 'cap_look': 'board_b'},
    ]
    return {'name': 'FOLabBeachKiosk', 'looks': looks, 'parts': parts}


def umbrella():
    """A hotel beach's parasol: a weighted foot, a white pole, a wide canopy in panels of coral and cream with a
    striped edge hanging from its rim. The rim is over a head's height, so people walk under it."""
    looks = {'foot': look('concrete', tile=96), 'pole': look('metal_white', tile=32), 'canopy': look('parasol_coral'),
             'edge': look('cloth_coral', tile=88)}
    parts = [
        {'shape': 'cylinder', 'r': 17, 'r2': 14, 'h': 6, 'sides': 12, 'at': [0, 0, 0], 'look': 'foot', 'material': 'stone'},
        {'shape': 'cylinder', 'r': 2.2, 'h': 172, 'sides': 8, 'at': [0, 0, 6], 'look': 'pole', 'material': 'metal'},
        {'shape': 'cylinder', 'r': 5, 'h': 7, 'sides': 8, 'at': [0, 0, 143], 'look': 'pole', 'solid': False},          # the hub
        {'shape': 'cone', 'r': 112, 'h': 30, 'sides': 16, 'at': [0, 0, 150], 'look': 'canopy', 'paint': 'above', 'under': True,
         'material': 'cloth'},
        {'shape': 'cylinder', 'r': 112, 'h': 9, 'sides': 16, 'at': [0, 0, 141], 'look': 'edge', 'caps': False, 'under': True, 'solid': False},
        {'shape': 'cone', 'r': 4, 'h': 9, 'sides': 8, 'at': [0, 0, 178], 'look': 'pole', 'solid': False},
    ]
    return {'name': 'FOLabBeachUmbrella', 'looks': looks, 'parts': parts}


def palm(name, tall=640, lean=22, fronds=21, seed=1):
    """A coconut palm: a ringed trunk that leaves the ground leaning (towards +x) and straightens as it climbs, a head
    of long leaves from upright young ones to old ones hanging brown, nuts under them. Only the trunk is solid."""
    rnd = random.Random(seed)
    looks = {'bark': look('palm_bark', tile=56), 'leaf': look('palm_frond', alpha=True), 'dry': look('palm_frond_dry', alpha=True),
             'nut': look('stalk', tile=48)}
    parts = []
    x = z = 0.0
    n = 8
    for k in range(n):
        tilt = lean * (1 - k / (n - 1.0)) ** 1.3                # degrees off upright: most at the foot
        r0, r1 = 14.5 - 5.5 * k / n, 14.5 - 5.5 * (k + 1) / n
        parts.append({'shape': 'cylinder', 'r': r0 * (1.25 if k == 0 else 1), 'r2': r1, 'h': tall / n * 1.05, 'sides': 9, 'at': [x, 0, z],
                      'turn': [0, tilt, 0], 'look': 'bark', 'caps': k == n - 1})
        x += math.sin(math.radians(tilt)) * tall / n
        z += math.cos(math.radians(tilt)) * tall / n
    parts.append({'shape': 'ball', 'r': 13, 'sides': 8, 'rings': 4, 'at': [x, 0, z - 16], 'look': 'bark', 'solid': False})
    for i in range(fronds):
        age = i / (fronds - 1.0)                                # 0 the newest leaf, 1 the oldest
        parts.append({'shape': 'frond', 'long': rnd.uniform(205, 250) * (0.8 + 0.2 * math.sin(math.pi * min(1, age + 0.25))), 'wide': 66,
                      'up': 68 - 95 * age + rnd.uniform(-8, 8), 'droop': rnd.uniform(50, 85), 'fold': 24, 'segments': 6,
                      'turn': [0, 0, i * 137.5 + rnd.uniform(-12, 12)], 'at': [x, 0, z + 2 - 10 * age], 'look': 'dry' if age > 0.85 else 'leaf'})
    for i in range(4):
        a = math.radians(i * 95 + rnd.uniform(0, 40))
        parts.append({'shape': 'ball', 'r': 6.5, 'sides': 7, 'rings': 4, 'scale': [1, 1, 1.2], 'solid': False, 'look': 'nut',
                      'at': [x + math.cos(a) * 13, math.sin(a) * 13, z - 26 - rnd.uniform(0, 6)]})
    return {'name': name, 'looks': looks, 'parts': parts}


def banana():
    """A banana plant: a soft green stem and a fountain of broad torn leaves."""
    rnd = random.Random(5)
    looks = {'stem': look('stalk', tile=48), 'leaf': look('banana_leaf', alpha=True)}
    parts = [{'shape': 'cylinder', 'r': 9.5, 'r2': 6, 'h': 128, 'sides': 8, 'look': 'stem', 'material': 'organic'}]
    for i in range(8):
        age = i / 7.0
        parts.append({'shape': 'frond', 'long': rnd.uniform(120, 165), 'wide': rnd.uniform(44, 56), 'up': 78 - 60 * age + rnd.uniform(-6, 6),
                      'droop': rnd.uniform(60, 105), 'fold': 10, 'segments': 6, 'turn': [0, 0, i * 137.5 + rnd.uniform(-15, 15)],
                      'at': [0, 0, 124 - 14 * age], 'look': 'leaf'})
    return {'name': 'FOLabBeachBanana', 'looks': looks, 'parts': parts}


def crossed(name, texture, wide, tall, cards=3, top=False, seed=1):
    """A plant of flat pictures crossing through its middle, looked at from any side: a shrub, a tuft. Nothing solid:
    people walk through it."""
    rnd = random.Random(seed)
    looks = {'plant': look(texture, alpha=True)}
    parts = [{'shape': 'card', 'size': [wide * rnd.uniform(0.9, 1.05), tall * rnd.uniform(0.9, 1.05)], 'turn': [rnd.uniform(-6, 6), 0, k * 180.0 / cards + rnd.uniform(-8, 8)],
              'look': 'plant'} for k in range(cards)]
    if top:                                     # two lying back, so there are leaves seen from above as well
        parts += [{'shape': 'card', 'size': [wide * 0.8, tall * 0.8], 'turn': [58, 0, a], 'at': [0, 0, tall * 0.18], 'look': 'plant'} for a in (40, 220)]
    return {'name': name, 'looks': looks, 'parts': parts}


def tiki_torch():
    """A bamboo torch stuck in the sand, its bowl woven round the top. Not lit: a flame is a light and an effect,
    which a mesh from here doesn't hold yet."""
    looks = {'cane': look('bamboo', tile=40), 'bowl': look('palm_bark', tile=40)}
    parts = [{'shape': 'cylinder', 'r': 2.6, 'r2': 2.2, 'h': 138, 'sides': 7, 'turn': [0, 3, 0], 'look': 'cane'},
             {'shape': 'cylinder', 'r': 3.2, 'r2': 9, 'h': 18, 'sides': 8, 'at': [7, 0, 132], 'turn': [0, 3, 0], 'look': 'bowl', 'solid': False},
             {'shape': 'cylinder', 'r': 3.4, 'h': 4, 'sides': 7, 'at': [7.6, 0, 144], 'look': 'cane', 'solid': False}]
    return {'name': 'FOLabBeachTikiTorch', 'looks': looks, 'parts': parts}


# ---------- a jungle ----------
# What makes a wood read as jungle and not as plants on green ground: a roof of leaves overhead (trees whose crowns
# are seen from under, and meet), things hanging from it (vines, a banyan's roots), a middle storey at head height that
# stops the eye (thickets, tree ferns, bamboo), and the ground itself hidden (ferns, taro, undergrowth, logs).

def limb(a, b, r0, r1, look, sides=7, solid=False, caps=False):
    """A bough from a to b, r0 thick at a and r1 at b."""
    d = [b[i] - a[i] for i in range(3)]
    ln = math.sqrt(sum(v * v for v in d)) or 1.0
    return {'shape': 'cylinder', 'r': r0, 'r2': r1, 'h': ln, 'sides': sides, 'at': [round(v, 1) for v in a], 'look': look, 'caps': caps, 'solid': solid,
            'turn': [0, math.degrees(math.acos(max(-1.0, min(1.0, d[2] / ln)))), math.degrees(math.atan2(d[1], d[0]))]}


def leaves(at, r, look, rnd, flat=2, look2=None):
    """A bough's end in leaf: sprays (texpaint.leaf_spray) fanning from the point every way, some standing, most leaning
    out, some hanging, so the crown has depth and gaps and is closed seen from under. (It was pictures of a round mass
    of leaves standing through each other: a tree of overlapping discs.) look2: every other spray in a second look."""
    x, y, z = at
    parts = []
    # (two more leaning sprays than at first, so a crown is fuller from the side; its inside is shaded by shade.py)
    lean = [rnd.uniform(-20, 20), rnd.uniform(10, 30)] + [rnd.uniform(48, 86) for _ in range(5 + flat)] + [rnd.uniform(96, 124) for _ in range(2)]
    start = rnd.uniform(0, 360)
    for k, tilt in enumerate(lean):
        parts.append({'shape': 'card', 'size': [r * rnd.uniform(1.15, 1.5), r * rnd.uniform(1.25, 1.6)], 'at': [x, y, z],
                      'turn': [tilt, 0, start + k * 360.0 / len(lean) * 2.6 + rnd.uniform(-20, 20)], 'look': look2 if look2 and k % 2 else look})
    return parts


def jungle_tree(name, seed=1, tall=900, spread=1000, girth=30, limbs=5, vines=6, roots=0, straight=False, leaf='canopy'):
    """A forest tree: a furrowed mossy trunk with fins at its foot, boughs forking out to a crown of leaf masses that is
    closed seen from under, vines hanging from the boughs. roots: a banyan's, dropping from the boughs to the ground.
    straight: a tall bare trunk with its crown far up. Only the trunk is solid."""
    rnd = random.Random(seed)
    looks = {'bark': look('jungle/bark', tile=110), 'leaf': look('jungle/spray' if leaf == 'canopy' else 'jungle/spray_dark', alpha=True),
             'leaf2': look('jungle/spray_light' if leaf == 'canopy' else 'jungle/spray', alpha=True), 'vine': look('jungle/vines', alpha=True)}
    fork = tall * (0.66 if straight else 0.4)
    top = (rnd.uniform(-0.05, 0.05) * tall, rnd.uniform(-0.05, 0.05) * tall, fork)
    parts = [limb((0, 0, -10), top, girth * 1.15, girth * 0.8, 'bark', sides=10, solid=True)]
    for k in range(5):                          # fins at the foot: a cone squeezed thin
        parts.append({'shape': 'cone', 'r': 1, 'h': 1, 'sides': 6, 'scale': [girth * rnd.uniform(2.0, 2.8), girth * 0.42, fork * rnd.uniform(0.22, 0.34)],
                      'turn': [0, 0, k * 72 + rnd.uniform(-20, 20)], 'at': [0, 0, -8], 'look': 'bark', 'solid': False})
    ends, mids = [], []
    for i in range(limbs):
        a = math.radians(i * 360.0 / limbs + rnd.uniform(-22, 22))
        reach, h = spread / 2 * rnd.uniform(0.6, 0.95), tall * rnd.uniform(0.74, 0.93)
        mid = (top[0] + math.cos(a) * reach * 0.5, top[1] + math.sin(a) * reach * 0.5, fork + (h - fork) * 0.62)
        end = (top[0] + math.cos(a) * reach, top[1] + math.sin(a) * reach, h)
        b = a + math.radians(rnd.uniform(35, 70)) * rnd.choice((-1, 1))
        end2 = (mid[0] + math.cos(b) * reach * 0.55, mid[1] + math.sin(b) * reach * 0.55, tall * rnd.uniform(0.8, 0.97))
        parts += [limb(top, mid, girth * 0.5, girth * 0.33, 'bark'), limb(mid, end, girth * 0.33, girth * 0.1, 'bark', sides=6),
                  limb(mid, end2, girth * 0.26, girth * 0.08, 'bark', sides=6)]
        ends += [end, end2, (mid[0], mid[1], mid[2] + spread * 0.1)]
        mids += [mid, ((mid[0] + end[0]) / 2, (mid[1] + end[1]) / 2, (mid[2] + end[2]) / 2)]
    ends.append((top[0], top[1], tall * 0.96))
    for e in ends:
        parts += leaves(e, spread * rnd.uniform(0.18, 0.25), 'leaf', rnd, look2='leaf2')
    for _ in range(vines):
        e = rnd.choice(mids + ends)
        ln = rnd.uniform(0.25, 0.6) * e[2]
        parts.append({'shape': 'card', 'size': [rnd.uniform(60, 110), ln], 'at': [e[0] + rnd.uniform(-40, 40), e[1] + rnd.uniform(-40, 40), e[2] - ln - 10],
                      'turn': [0, 0, rnd.uniform(0, 360)], 'look': 'vine'})
    for _ in range(roots):
        m = rnd.choice(mids)
        foot = (m[0] + rnd.uniform(-45, 45), m[1] + rnd.uniform(-45, 45), -8)
        parts.append(limb((m[0] + rnd.uniform(-15, 15), m[1] + rnd.uniform(-15, 15), m[2]), foot, rnd.uniform(2.5, 4.5), rnd.uniform(4, 7), 'bark', sides=5))
    return {'name': name, 'looks': looks, 'parts': parts}


def _fronds(rnd, n, at, long, wide, look_name, up=(62, -8), droop=(60, 95), fold=12, segments=5):
    """n leaves round a point, the newest standing and the oldest lying out."""
    out = []
    for i in range(n):
        age = i / max(1.0, n - 1.0)
        out.append({'shape': 'frond', 'long': rnd.uniform(*long), 'wide': wide * rnd.uniform(0.9, 1.1), 'up': up[0] + (up[1] - up[0]) * age + rnd.uniform(-7, 7),
                    'droop': rnd.uniform(*droop), 'fold': fold, 'segments': segments, 'turn': [0, 0, i * 137.5 + rnd.uniform(-14, 14)],
                    'at': [at[0], at[1], at[2] - 6 * age], 'look': look_name})
    return out


def tree_fern(name, tall=170, seed=1):
    """A tree fern: a dark fibrous trunk and a wheel of great fern leaves at head height and over."""
    rnd = random.Random(seed)
    looks = {'trunk': look('jungle/fibre', tile=40), 'leaf': look('jungle/fern', alpha=True)}
    top = (rnd.uniform(-14, 14), rnd.uniform(-14, 14), tall)
    parts = [limb((0, 0, -6), top, 12, 9.5, 'trunk', sides=8, solid=True, caps=True)]
    parts += _fronds(rnd, 13, top, (170, 220), 74, 'leaf')
    return {'name': name, 'looks': looks, 'parts': parts}


def rosette(name, texture, n, long, wide, up=(66, 12), droop=(50, 80), fold=14, seed=1):
    """Leaves from one point on the ground: a fern, a taro. Nothing solid."""
    rnd = random.Random(seed)
    return {'name': name, 'looks': {'leaf': look(texture, alpha=True)}, 'parts': _fronds(rnd, n, (0, 0, 3), long, wide, 'leaf', up, droop, fold)}


def ti_plant(name, texture, seed=1):
    """A ti plant: a few bare canes, each with a tuft of long leaves at its top."""
    rnd = random.Random(seed)
    looks = {'cane': look('jungle/cane', tile=32), 'leaf': look(texture, alpha=True)}
    parts = []
    for k in range(3):
        a = math.radians(k * 120 + rnd.uniform(-30, 30))
        top = (math.cos(a) * rnd.uniform(8, 26), math.sin(a) * rnd.uniform(8, 26), rnd.uniform(60, 125))
        parts.append(limb((math.cos(a) * 4, math.sin(a) * 4, -3), top, 2.6, 2.0, 'cane', sides=5))
        parts += _fronds(rnd, 9, top, (48, 70), 16, 'leaf', up=(78, -15), droop=(35, 70), fold=10, segments=3)
    return {'name': name, 'looks': looks, 'parts': parts}


def heliconia():
    """A stand of heliconia: paddle leaves like a banana's, and among them the hanging red flowers."""
    rnd = random.Random(9)
    looks = {'leaf': look('banana_leaf', alpha=True), 'flower': look('jungle/heliconia', alpha=True)}
    parts = _fronds(rnd, 9, (0, 0, 4), (120, 175), 46, 'leaf', up=(84, 58), droop=(30, 60), fold=10)
    parts += [{'shape': 'card', 'size': [150, 165], 'turn': [rnd.uniform(-5, 5), 0, k * 60 + rnd.uniform(-10, 10)], 'look': 'flower'} for k in range(3)]
    return {'name': 'FOLabJungleHeliconia', 'looks': looks, 'parts': parts}


def bamboo():
    """A clump of bamboo: canes leaning out from one foot, eight metres up, leaves in their tops. Its middle is solid."""
    rnd = random.Random(10)
    looks = {'cane': look('jungle/cane', tile=44), 'leaf': look('jungle/spray_light', alpha=True)}
    parts = [{'shape': 'cylinder', 'r': 34, 'h': 220, 'sides': 8, 'look': None, 'material': 'wood'}]      # (only to walk into: nothing drawn)
    for k in range(16):
        a, d = math.radians(k * 137.5), rnd.uniform(6, 40)
        foot = (math.cos(a) * d, math.sin(a) * d, -4)
        tall = rnd.uniform(380, 580)
        top = (foot[0] * rnd.uniform(2.6, 4.2) + rnd.uniform(-20, 20), foot[1] * rnd.uniform(2.6, 4.2) + rnd.uniform(-20, 20), tall)
        parts.append(limb(foot, top, rnd.uniform(2.8, 3.8), 1.6, 'cane', sides=5))
        for t in (0.62, 0.84, 1.0)[k % 2:]:
            p = tuple(foot[i] + (top[i] - foot[i]) * t for i in range(3))
            parts += leaves(p, rnd.uniform(60, 85), 'leaf', rnd, flat=0)[::2]
    return {'name': 'FOLabJungleBamboo', 'looks': looks, 'parts': parts}


def shrub(name, looks, stems=7, tall=(110, 170), lean=(15, 50), spray=(55, 80), sprays=2, seed=1, solid=False):
    """A shrub as a tree's crown is made: stems fanning out of one root, each ending in leafy sprays (texpaint.leaf_spray)
    that fan every way, more along the way up, so it has depth and gaps from any side and reads as a bush of branches in
    leaf, not as pictures of a bush standing through each other (what the user called flat discs). looks: {'stem',
    'leaf', 'leaf2'}. Nothing solid unless asked: one pushes through a bush."""
    rnd = random.Random(seed)
    parts = []
    for k in range(stems):
        a = math.radians(k * 360.0 / stems + rnd.uniform(-20, 20))
        tilt = math.radians(rnd.uniform(*lean))
        h = rnd.uniform(*tall)
        end = (math.cos(a) * math.sin(tilt) * h, math.sin(a) * math.sin(tilt) * h, math.cos(tilt) * h)
        parts.append(limb((0, 0, -4), end, rnd.uniform(2.2, 3.4), 1.2, 'stem', sides=4))
        parts += leaves(end, rnd.uniform(*spray), 'leaf', rnd, flat=1, look2='leaf2')
        for t in [0.55, 0.8][:max(0, sprays - 1)]:
            mid = tuple(v * t for v in end)
            parts += leaves(mid, rnd.uniform(*spray) * 0.8, 'leaf', rnd, flat=0, look2='leaf2')[::2] + leaves(mid, rnd.uniform(*spray) * 0.6, 'leaf2', rnd, flat=0)[1::3]
    return {'name': name, 'looks': looks, 'parts': parts}


def _bush_looks(leaf, leaf2):
    return {'stem': look('jungle/cane', tile=32), 'leaf': look(leaf, alpha=True), 'leaf2': look(leaf2, alpha=True)}


def thicket():
    """A wall of green higher than a head, to stop the eye: three shrubs grown into each other, ferns at their feet.
    Nothing solid: you push through it."""
    rnd = random.Random(11)
    items = [(shrub('a', _bush_looks('jungle/spray_bush', 'jungle/spray_dark'), stems=8, tall=(170, 250), lean=(10, 45), spray=(70, 100), sprays=3, seed=31),
              -110, 0, 0, 1.0),
             (shrub('b', _bush_looks('jungle/spray_broad', 'jungle/spray_bush'), stems=7, tall=(150, 220), lean=(15, 50), spray=(70, 95), sprays=3, seed=32),
              110, 40, 120, 1.0),
             (shrub('c', _bush_looks('jungle/spray_dark', 'jungle/spray_broad'), stems=6, tall=(130, 200), lean=(15, 55), spray=(60, 90), sprays=2, seed=33),
              10, -110, 240, 0.9)]
    desc = combine('FOLabJungleThicket', items)
    for k in range(4):
        a = math.radians(k * 90 + rnd.uniform(-20, 20))
        for q in _fronds(rnd, 4, (math.cos(a) * 150, math.sin(a) * 150, 4), (80, 120), 44, 'fern', up=(60, 20)):
            desc['parts'].append(q)
    desc['looks']['fern'] = look('jungle/fern', alpha=True)
    return desc


def _old_thicket():
    """A wall of green higher than a head, to stop the eye: leaf masses standing through each other, ferns at its
    foot. Nothing solid: you push through it."""
    rnd = random.Random(11)
    looks = {'mass': look('jungle/thicket', alpha=True), 'fern': look('jungle/fern', alpha=True)}
    parts = [{'shape': 'card', 'size': [330 * rnd.uniform(0.85, 1.1), 255 * rnd.uniform(0.85, 1.1)], 'turn': [rnd.uniform(-7, 7), 0, k * 45 + rnd.uniform(-10, 10)],
              'at': [rnd.uniform(-30, 30), rnd.uniform(-30, 30), -6], 'look': 'mass'} for k in range(4)]
    parts += [{'shape': 'card', 'size': [280, 280], 'turn': [72, 0, a], 'at': [140 * math.sin(math.radians(a)) * 0.6, -140 * math.cos(math.radians(a)) * 0.6, 120], 'look': 'mass'}
              for a in (20, 200)]
    for k in range(5):
        a = math.radians(k * 72 + rnd.uniform(-20, 20))
        parts += _fronds(rnd, 4, (math.cos(a) * 120, math.sin(a) * 120, 4), (80, 120), 44, 'fern', up=(60, 20))
    return {'name': 'FOLabJungleThicket', 'looks': looks, 'parts': parts}


def undergrowth():
    """What hides the ground: knee-high shrubs with broad leaves and a flower or two, ferns through them."""
    rnd = random.Random(12)
    items = [(shrub('a', _bush_looks('jungle/spray_broad', 'jungle/spray_bush'), stems=4, tall=(55, 95), lean=(25, 60), spray=(50, 70), sprays=1, seed=41), -40, 0, 0, 1.0),
             (shrub('b', _bush_looks('jungle/spray_bush', 'jungle/spray_hibiscus'), stems=3, tall=(45, 80), lean=(25, 60), spray=(45, 65), sprays=1, seed=42), 60, 30, 150, 1.0)]
    desc = combine('FOLabJungleUndergrowth', items)
    desc['looks']['fern'] = look('jungle/fern', alpha=True)
    desc['parts'] += _fronds(rnd, 6, (rnd.uniform(-40, 40), rnd.uniform(-40, 40), 3), (70, 110), 42, 'fern', up=(55, 15))
    return desc


def _old_undergrowth():
    """What hides the ground: knee-high leaves with a flower or two, and ferns through them."""
    rnd = random.Random(12)
    looks = {'mass': look('jungle/undergrowth', alpha=True), 'fern': look('jungle/fern', alpha=True)}
    parts = [{'shape': 'card', 'size': [230 * rnd.uniform(0.85, 1.1), 105], 'turn': [rnd.uniform(-8, 8), 0, k * 60 + rnd.uniform(-12, 12)], 'at': [0, 0, -4], 'look': 'mass'}
             for k in range(3)]
    parts += [{'shape': 'card', 'size': [200, 200], 'turn': [80, 0, 30], 'at': [-50, 87, 40], 'look': 'mass'}]
    parts += _fronds(rnd, 6, (rnd.uniform(-40, 40), rnd.uniform(-40, 40), 3), (70, 110), 42, 'fern', up=(55, 15))
    return {'name': 'FOLabJungleUndergrowth', 'looks': looks, 'parts': parts}


def mossy_log():
    """A fallen trunk going back to the ground, ferns growing out of it."""
    rnd = random.Random(13)
    looks = {'bark': look('jungle/bark', tile=90), 'fern': look('jungle/fern', alpha=True)}
    parts = [limb((-125, 0, 13), (125, 14, 17), 17, 13, 'bark', sides=9, solid=True, caps=True)]
    for x in (-70, 10, 85):
        parts += _fronds(rnd, 4, (x, rnd.uniform(-6, 6), 26), (45, 70), 30, 'fern', up=(70, 25))
    return {'name': 'FOLabJungleLog', 'looks': looks, 'parts': parts}


# ---------- hotels: the skyline ----------
# Late-fifties resort towers, each its own design. A floor is 256 units and so is a room's bay, which is what one
# square of a facade picture shows (texpaint.facade_lanai), so a face of whole floors and bays needs no fitting.
# Every floor's slab really sticks out (the lanais), which is what makes a tower read from below. Parts marked 'far'
# are the masses that make the far model (<file>_lod.nif, which lodobj shows beyond the loaded cells: without it a
# tower would only appear as you walked up to it). Nobody goes in yet: the lobby doors are painted.

FLOOR = 256.0


def _hotel_looks():
    return {
        # (the lanai pictures are eight bays by eight floors, each room its own: texwear.facade_sheet, FRONT_TILE)
        'lanai': look('hotel/lanai', tile=2048, far='hotel/far_cream'), 'lanai_t': look('hotel/lanai_turquoise', tile=2048, far='hotel/far_turquoise'),
        'lanai_c': look('hotel/lanai_coral', tile=2048, far='hotel/far_coral'), 'arch': look('hotel/arch', tile=256, far='hotel/far_pink'),
        'pink': look('hotel/stucco_pink', tile=512, far='hotel/far_plain_pink'), 'white': look('hotel/stucco_white', tile=512, far='hotel/far_plain_white'),
        'blocks': look('hotel/blocks', tile=128), 'lava': look('hotel/lava', tile=300, far='hotel/far_plain_lava'),
        'shop': look('hotel/shopfront', tile=300, far='hotel/far_plain_glass'), 'slab': look('hotel/stucco_white', tile=512),
        'deck': look('concrete', tile=256, far='hotel/far_plain_white'), 'coral': look('planks_coral', tile=160, far='hotel/far_plain_coral'),
        'awning': look('cloth_coral', tile=180),
        'sign_makai': look('hotel/signs', region=(0, 0, 1, 0.25)), 'sign_blue': look('hotel/signs', region=(0, 0.25, 1, 0.5)),
        'sign_blue_up': look('hotel/signs', region=(0, 0.25, 1, 0.5), turned=True),
        'sign_pink': look('hotel/signs', region=(0, 0.5, 1, 0.75)), 'sign_kahuna': look('hotel/signs', region=(0, 0.75, 1, 1))}


BAY = 256.0            # (a room's width on the fronts: texwear.facade_sheet's bays, FRONT_TILE over FRONT_BAYS)


def lanai_detail(parts, x, y, z, wide, deep, floors, turn=0.0, lanai=70, look_name='white', rail='white', sides=(-1, 1)):
    """What makes a block of rooms read as rooms from the street: a wall between each room's lanai and the next (a fin
    as deep as the lanai, up the whole front), and a railing along every floor's lanai, top rail and middle rail. Nothing
    solid. sides: -1 the front, 1 the back."""
    c, sn = math.cos(math.radians(turn)), math.sin(math.radians(turn))
    at = lambda lx, ly, lz: [round(x + lx * c - ly * sn, 1), round(y + lx * sn + ly * c, 1), round(lz, 1)]
    bays = max(1, int(round(wide / BAY)))
    step = wide / bays
    for sd in sides:
        for k in range(bays + 1):
            parts.append({'shape': 'box', 'size': [10, lanai, floors * FLOOR], 'at': at(-wide / 2 + k * step, sd * (deep / 2 + lanai / 2), z),
                          'turn': [0, 0, turn], 'look': look_name, 'solid': False, 'bevel': 0})
        for f in range(1, floors):
            for hgt, thick in ((92, 7), (48, 4)):
                parts.append({'shape': 'box', 'size': [wide, thick, thick], 'at': at(0, sd * (deep / 2 + lanai - 4), z + f * FLOOR + hgt),
                              'turn': [0, 0, turn], 'look': rail, 'solid': False})


def roof_plant(parts, x, y, z, wide, deep, turn=0.0, seed=1, body='white', metal='white', far=False):
    """What stands on a hotel's flat roof: the lift's motor room, water tanks on legs, cooling plant, vent stacks, a
    parapet round the edge. In the roof's frame (wide along x, deep along y), turned by `turn`."""
    rnd = random.Random(seed)
    c, sn = math.cos(math.radians(turn)), math.sin(math.radians(turn))
    at = lambda lx, ly, lz: [round(x + lx * c - ly * sn, 1), round(y + lx * sn + ly * c, 1), round(lz, 1)]
    for sd in (-1, 1):                                       # (the parapet)
        parts.append({'shape': 'box', 'size': [wide, 18, 70], 'at': at(0, sd * (deep / 2 - 9), z), 'turn': [0, 0, turn], 'look': body, 'solid': False})
        parts.append({'shape': 'box', 'size': [18, deep - 36, 70], 'at': at(sd * (wide / 2 - 9), 0, z), 'turn': [0, 0, turn], 'look': body, 'solid': False})
    room = min(420, wide * 0.3)
    mx = rnd.uniform(-0.25, 0.25) * wide
    parts.append({'shape': 'box', 'size': [room, min(360, deep * 0.6), 240], 'at': at(mx, 0, z), 'turn': [0, 0, turn], 'look': body, 'far': far})
    spots = []
    for _ in range(int(max(2, wide / 600))):
        for _try in range(12):
            px, py = rnd.uniform(-0.42, 0.42) * wide, rnd.uniform(-0.3, 0.3) * deep
            if abs(px - mx) > room / 2 + 160 and all(abs(px - a) > 260 for a, _b in spots):
                spots.append((px, py))
                break
    for n, (px, py) in enumerate(spots):
        if n % 3 == 0:                                       # a water tank on four legs
            for lx, ly in ((-50, -50), (50, -50), (50, 50), (-50, 50)):
                parts.append({'shape': 'box', 'size': [8, 8, 110], 'at': at(px + lx, py + ly, z), 'turn': [0, 0, turn], 'look': metal, 'solid': False})
            parts.append({'shape': 'cylinder', 'r': 90, 'h': 150, 'sides': 14, 'at': at(px, py, z + 110), 'look': metal, 'solid': False})
            parts.append({'shape': 'cone', 'r': 96, 'h': 30, 'sides': 14, 'at': at(px, py, z + 260), 'look': metal, 'solid': False})
        else:                                                # a cooling unit, its fan on top
            parts.append({'shape': 'box', 'size': [170, 110, 90], 'at': at(px, py, z), 'turn': [0, 0, turn + rnd.choice((0, 90))], 'look': metal, 'solid': False})
            parts.append({'shape': 'cylinder', 'r': 38, 'h': 10, 'sides': 12, 'at': at(px, py, z + 90), 'look': body, 'solid': False})
        parts.append({'shape': 'cylinder', 'r': 10, 'h': 120, 'sides': 6, 'at': at(px + 120, py - 60, z), 'look': metal, 'solid': False})


def _slab_tower(parts, x, y, z, wide, deep, floors, front, back, turn=0.0, lanai=70, ends='white'):
    """A block of rooms: its mass, and a slab at every floor reaching out front and back."""
    parts.append({'shape': 'box', 'size': [wide, deep, floors * FLOOR], 'at': [x, y, z], 'turn': [0, 0, turn], 'look': ends,
                  'faces': {'front': front, 'back': back, 'top': 'deck', 'bottom': None}, 'material': 'stone', 'far': True})
    for f in range(1, floors + 1):
        parts.append({'shape': 'slab', 'size': [wide + 24, deep + 2 * lanai, 12], 'at': [x, y, z + f * FLOOR - 12], 'turn': [0, 0, turn], 'look': 'slab',
                      'solid': False})
    lanai_detail(parts, x, y, z, wide, deep, floors, turn, lanai)
    roof_plant(parts, x, y, z + floors * FLOOR, wide, deep, turn, seed=int(wide + floors))


def makai_tower():
    """A slab sixteen floors over a lava-rock lobby: turquoise lanai fronts to the sea, railings behind, screens of
    pierced block up its ends, its name on the roof, a butterfly canopy over the drive."""
    parts = [
        {'shape': 'box', 'size': [3300, 1500, 300], 'at': [0, 0, 0], 'look': 'lava', 'faces': {'front': 'shop', 'top': 'deck'}, 'material': 'stone', 'far': True},
        {'shape': 'slab', 'size': [3420, 1620, 16], 'at': [0, 0, 300], 'look': 'slab', 'solid': False}]
    base, top = 316, 316 + 16 * FLOOR
    _slab_tower(parts, 0, 200, base, 2304, 560, 16, 'lanai_t', 'lanai')
    for side in (-1, 1):
        parts += [{'shape': 'box', 'size': [40, 780, 16 * FLOOR + 140], 'at': [side * 1174, 200, base], 'look': 'white', 'solid': False},
                  {'shape': 'box', 'size': [10, 256, 16 * FLOOR], 'at': [side * 1158, 200, base], 'look': 'blocks', 'solid': False}]
    parts += [
        {'shape': 'box', 'size': [900, 420, 210], 'at': [-420, 200, top], 'look': 'white', 'far': True},
        {'shape': 'box', 'size': [1536, 24, 384], 'at': [250, -40, top + 150], 'look': 'white', 'faces': {'front': 'sign_makai', 'back': 'sign_makai'}, 'solid': False, 'far': True},
        {'shape': 'box', 'size': [20, 20, 150], 'at': [-350, -40, top], 'look': 'white', 'solid': False},
        {'shape': 'box', 'size': [20, 20, 150], 'at': [850, -40, top], 'look': 'white', 'solid': False}]
    for side in (-1, 1):                        # the canopy over the drive: two wings falling to the middle, on leaning posts
        parts.append({'shape': 'slab', 'size': [560, 760, 16], 'at': [side * 272, -1130, 372], 'turn': [0, -side * 11, 0], 'look': 'white', 'faces': {'bottom': 'coral'}})
        for y in (-1400, -860):
            parts.append({'shape': 'box', 'size': [22, 22, 430], 'at': [side * 380, y, 0], 'turn': [0, side * 8, 0], 'look': 'coral'})
    return {'name': 'FOLabHotelMakaiTower', 'looks': _hotel_looks(), 'parts': parts}


def kahuna_palms():
    """A round tower of fourteen floors on a drum of lava rock, a ring of lanai at every floor, and on top a glazed
    restaurant like a saucer under a coral roof and a spire."""
    parts = [{'shape': 'cylinder', 'r': 1050, 'h': 280, 'sides': 24, 'look': 'lava', 'cap_look': 'deck', 'material': 'stone', 'far': True}]
    base, top = 280, 280 + 14 * FLOOR
    parts.append({'shape': 'cylinder', 'r': 652, 'h': 14 * FLOOR, 'sides': 24, 'at': [0, 0, base], 'look': 'lanai', 'cap_look': 'deck', 'material': 'stone', 'far': True})
    for f in range(1, 15):
        parts.append({'shape': 'cylinder', 'r': 730, 'h': 12, 'sides': 24, 'at': [0, 0, base + f * FLOOR - 12], 'look': 'slab', 'solid': False})
    parts += [
        {'shape': 'cylinder', 'r': 250, 'h': 230, 'sides': 12, 'at': [0, 0, top], 'look': 'white', 'far': True},
        {'shape': 'cylinder', 'r': 760, 'r2': 1000, 'h': 60, 'sides': 24, 'at': [0, 0, top + 230], 'look': 'white', 'far': True},
        {'shape': 'cylinder', 'r': 990, 'h': 190, 'sides': 24, 'at': [0, 0, top + 290], 'look': 'shop', 'cap_look': 'white', 'far': True},
        {'shape': 'cone', 'r': 1090, 'h': 150, 'sides': 24, 'at': [0, 0, top + 480], 'look': 'coral', 'far': True},
        {'shape': 'cone', 'r': 16, 'h': 760, 'sides': 6, 'at': [0, 0, top + 600], 'look': 'white', 'solid': False, 'far': True}]
    for a in (0, 180):
        c, s = math.cos(math.radians(a - 90)), math.sin(math.radians(a - 90))
        parts.append({'shape': 'box', 'size': [1100, 20, 275], 'at': [c * 1010, s * 1010, top + 250], 'turn': [0, 0, a], 'look': 'white',
                      'faces': {'front': 'sign_kahuna'}, 'solid': False})
    return {'name': 'FOLabHotelKahunaPalms', 'looks': _hotel_looks(), 'parts': parts}


def pink_pearl():
    """The old grand hotel: six floors of pink stucco and round-headed windows round a forecourt, a tower with a
    pointed coral roof at each end, a striped awning over the door."""
    tall = 6 * FLOOR
    parts = [{'shape': 'box', 'size': [2816, 768, tall], 'at': [0, 384, 0], 'look': 'pink', 'faces': {'front': 'arch', 'back': 'arch', 'top': 'deck'}, 'material': 'stone', 'far': True},
             {'shape': 'slab', 'size': [2880, 830, 44], 'at': [0, 384, tall], 'look': 'white', 'solid': False}]
    for side in (-1, 1):
        parts += [
            {'shape': 'box', 'size': [768, 1280, tall], 'at': [side * 1024, -640, 0], 'look': 'pink',
             'faces': {'front': 'arch', 'left': 'arch', 'right': 'arch', 'top': 'deck'}, 'material': 'stone', 'far': True},
            {'shape': 'slab', 'size': [830, 1340, 44], 'at': [side * 1024, -640, tall], 'look': 'white', 'solid': False},
            # the end towers, three floors higher, each under a four-sided roof with a lantern on it
            {'shape': 'box', 'size': [704, 704, 9 * FLOOR], 'at': [side * 1630, 384, 0], 'look': 'pink',
             'faces': {'front': 'arch', 'back': 'arch', 'left': 'arch', 'right': 'arch'}, 'material': 'stone', 'far': True},
            {'shape': 'cone', 'r': 560, 'h': 470, 'sides': 4, 'at': [side * 1630, 384, 9 * FLOOR], 'turn': [0, 0, 45], 'look': 'coral', 'far': True},
            {'shape': 'box', 'size': [150, 150, 200], 'at': [side * 1630, 384, 9 * FLOOR + 330], 'look': 'white', 'solid': False},
            {'shape': 'cone', 'r': 130, 'h': 190, 'sides': 4, 'at': [side * 1630, 384, 9 * FLOOR + 530], 'turn': [0, 0, 45], 'look': 'coral', 'solid': False}]
    parts += [
        {'shape': 'slab', 'size': [1300, 520, 14], 'at': [0, -250, 330], 'turn': [9, 0, 0], 'look': 'awning', 'solid': False},
        {'shape': 'box', 'size': [1400, 20, 200], 'at': [0, -12, tall + 44], 'look': 'white', 'faces': {'front': 'sign_pink'}, 'solid': False}]
    for k in range(5):
        parts.append({'shape': 'cylinder', 'r': 14, 'h': 300, 'sides': 8, 'at': [-600 + 300 * k, -470, 0], 'look': 'white'})
    return {'name': 'FOLabHotelPinkPearl', 'looks': _hotel_looks(), 'parts': parts}


def blue_lagoon():
    """Three wings of rooms fanning from a lift tower, each shorter than the last, coral lanai fronts one side and
    turquoise the other; the tower carries the name down a blade twenty metres tall."""
    parts = [{'shape': 'cylinder', 'r': 1500, 'h': 36, 'sides': 24, 'look': 'deck', 'material': 'stone'},
             {'shape': 'cylinder', 'r': 340, 'h': 21 * FLOOR, 'sides': 12, 'at': [0, 0, 36], 'look': 'white', 'cap_look': 'deck', 'material': 'stone', 'far': True},
             {'shape': 'cylinder', 'r': 470, 'h': 290, 'sides': 12, 'at': [0, 0, 36], 'look': 'shop', 'cap_look': 'white', 'far': True}]
    for k, floors in enumerate((19, 16, 13)):
        a = 90 + k * 120
        d = 300 + 896
        _slab_tower(parts, math.cos(math.radians(a)) * d, math.sin(math.radians(a)) * d, 36, 1792, 520, floors, 'lanai_c', 'lanai_t', turn=a)
    top = 36 + 21 * FLOOR
    parts += [{'shape': 'box', 'size': [44, 384, 1536], 'at': [0, -150, top - 500], 'look': 'white', 'faces': {'left': 'sign_blue_up', 'right': 'sign_blue_up'}, 'solid': False, 'far': True},
              {'shape': 'cone', 'r': 340, 'h': 120, 'sides': 12, 'at': [0, 0, top], 'look': 'coral', 'solid': False}]
    return {'name': 'FOLabHotelBlueLagoon', 'looks': _hotel_looks(), 'parts': parts}


def far_of(desc):
    """A piece's far model: only its masses, each look as its far picture laid once over a face, nothing solid. None
    for a piece with nothing marked 'far'."""
    parts = [dict(p, solid=False, far_only=False) for p in desc['parts'] if p.get('far') or p.get('far_only')]
    if not parts:
        return None
    # each look's own picture, repeated as on the model itself but never more than FAR_REPEAT times across a face (the
    # distant blocks bake a picture's repeats into its square of their sheet, at most lodobj.MAX_REPEAT): a hotel's front
    # reads as its windows from afar. Its 'far' picture only where it asks for one ('far_keep'): the far pictures were
    # flat swatches, and the skyline was plain blocks in the game (17 Nov 2026).
    reach = {}
    for p in parts:
        sc = max(abs(v) for v in p.get('scale', (1, 1, 1)))
        if p['shape'] in ('box', 'slab'):
            ext = max(p['size']) * sc
        elif p['shape'] in ('cylinder', 'cone'):
            r = max(float(p.get('r', 0)), float(p.get('r2', p.get('r', 0))))
            ext = max(2 * math.pi * r, float(p.get('h', 0))) * sc
        elif p['shape'] == 'ball':
            ext = 2 * math.pi * float(p['r']) * sc
        elif p['shape'] == 'hull':
            ys = [s['y'] for s in p['stations']]
            ext = (max(ys) - min(ys)) * sc
        else:
            ext = 0.0
        names = [p.get('look'), p.get('cap_look'), p.get('under_look'), p.get('deck_look'), p.get('end_look')]
        names += list((p.get('faces') or {}).values()) + [lk for _z, lk in (p.get('bands') or ())]
        for n in names:
            if n is not None:
                reach[n] = max(reach.get(n, 0.0), ext)
    looks = {}
    for k, v in desc['looks'].items():
        if v.get('far') and v.get('far_keep'):
            looks[k] = dict({f: v[f] for f in ('region', 'turned') if f in v}, tex=tex_path(v['far']), normal=tex_path(v['far'], True))
            continue
        looks[k] = {f: v[f] for f in ('tex', 'normal', 'region', 'turned', 'alpha') if f in v}
        if v.get('tile'):
            # (one repeat kept for a face whose picture starts part way through one: a round cap's is laid from its middle)
            looks[k]['tile'] = max(float(v['tile']), reach.get(k, 0.0) / (FAR_REPEAT - 1))
    # (masses only: no rounded edges or baked shade, which the distant blocks' one picture can't hold)
    return {'name': desc['name'] + 'Far', 'looks': looks, 'parts': parts, 'bevel': 0, 'shade': False}


FAR_REPEAT = 4          # (lodobj.MAX_REPEAT)


def combine(name, items):
    """Several pieces as one model: items [(description, x, y, turn in degrees, size)]. One thing for the game to hold
    where there would have been many: how a jungle's floor is covered without a thing for every fern."""
    looks, parts = {}, []
    for n, (desc, x, y, yaw, size) in enumerate(items):
        for k, v in desc['looks'].items():
            looks['%d_%s' % (n, k)] = v
        c, sn = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        for part in desc['parts']:
            q = dict(part)
            for f in ('look', 'cap_look', 'under_look'):
                if q.get(f) is not None:
                    q[f] = '%d_%s' % (n, q[f])
            if q.get('faces'):
                q['faces'] = {side: (None if v is None else '%d_%s' % (n, v)) for side, v in q['faces'].items()}      # (None: a face left out)
            ax, ay, az = q.get('at', (0, 0, 0))
            q['at'] = [x + (ax * c - ay * sn) * size, y + (ax * sn + ay * c) * size, az * size]
            t = q.get('turn', (0, 0, 0))
            q['turn'] = [t[0], t[1], t[2] + yaw]                    # (the turn about z is the last one made, so this adds)
            q['scale'] = [v * size for v in q.get('scale', (1, 1, 1))]
            parts.append(q)
    return {'name': name, 'looks': looks, 'parts': parts}


def slope_cover(name, seed=1, across=820, things=15):
    """Twelve metres of low green in one piece, for a mountainside: small ferns, knee-high leaves, tufts of grass, a ti
    plant or two. Nothing over a metre and a half, nothing solid."""
    rnd = random.Random(seed)
    kinds = [(lambda: rosette('f', 'jungle/fern', 9, (60, 100), 38, seed=5), 5, (0.6, 1.2)), (undergrowth, 3, (0.45, 0.8)),
             (lambda: crossed('g', 'jungle/grass_tuft', 112, 56, seed=4), 5, (1.0, 2.2)), (lambda: ti_plant('r', 'jungle/ti_green', seed=8), 1, (0.7, 1.0)),
             (lambda: rosette('t', 'jungle/taro', 6, (90, 130), 70, up=(80, 50), droop=(45, 75), fold=12, seed=6), 1, (0.6, 0.9))]
    items = []
    for k in range(things):
        pick = rnd.random() * sum(w for _f, w, _s in kinds)
        for fn, w, size in kinds:
            pick -= w
            if pick <= 0:
                break
        a, d = math.radians(k * 137.5 + rnd.uniform(-25, 25)), across / 2 * math.sqrt((k + 0.5) / things)
        items.append((fn(), math.cos(a) * d, math.sin(a) * d, rnd.uniform(0, 360), rnd.uniform(*size)))
    return combine(name, items)


def jungle_floor(name, seed=1, across=660, things=9):
    """Ten metres of jungle floor in one piece: undergrowth, ferns, taro, ti and heliconia through each other. Nothing
    solid."""
    rnd = random.Random(seed)
    kinds = [(undergrowth, 4), (lambda: rosette('f', 'jungle/fern', 11, (80, 125), 44, seed=5), 3),
             (lambda: rosette('t', 'jungle/taro', 9, (140, 200), 96, up=(82, 52), droop=(45, 75), fold=12, seed=6), 2),
             (lambda: ti_plant('r', 'jungle/ti_red', seed=7), 1), (heliconia, 1)]
    items = []
    for k in range(things):
        pick = rnd.random() * sum(w for _f, w in kinds)
        for fn, w in kinds:
            pick -= w
            if pick <= 0:
                break
        a, d = math.radians(k * 137.5 + rnd.uniform(-25, 25)), across / 2 * math.sqrt((k + 0.5) / things)
        items.append((fn(), math.cos(a) * d, math.sin(a) * d, rnd.uniform(0, 360), rnd.uniform(0.85, 1.6)))
    return combine(name, items)


PIECES = {
    'kiosk': {'label': 'Beach kiosk', 'edid': 'FOLabBeachKiosk', 'file': 'kiosk', 'describe': kiosk},
    'umbrella': {'label': 'Beach umbrella', 'edid': 'FOLabBeachUmbrella', 'file': 'umbrella', 'describe': umbrella},
    'palm_tall': {'label': 'Coconut palm, tall', 'edid': 'FOLabBeachPalmTall', 'file': 'palm_tall',
                  'describe': lambda: palm('FOLabBeachPalmTall', tall=660, lean=24, fronds=22, seed=1)},
    'palm_young': {'label': 'Coconut palm, young', 'edid': 'FOLabBeachPalmYoung', 'file': 'palm_young',
                   'describe': lambda: palm('FOLabBeachPalmYoung', tall=400, lean=12, fronds=19, seed=2)},
    'banana': {'label': 'Banana plant', 'edid': 'FOLabBeachBanana', 'file': 'banana', 'describe': banana},
    'hibiscus': {'label': 'Hibiscus bush', 'edid': 'FOLabBeachHibiscus', 'file': 'hibiscus',
                 'describe': lambda: shrub('FOLabBeachHibiscus', _bush_looks('jungle/spray_hibiscus', 'jungle/spray_bush'), stems=8, tall=(95, 140), lean=(15, 50),
                                           spray=(48, 66), sprays=2, seed=3)},
    'dune_grass': {'label': 'Dune grass', 'edid': 'FOLabBeachDuneGrass', 'file': 'dune_grass',
                   'describe': lambda: crossed('FOLabBeachDuneGrass', 'dune_grass', 112, 56, seed=4)},
    'tiki_torch': {'label': 'Tiki torch', 'edid': 'FOLabBeachTikiTorch', 'file': 'tiki_torch', 'describe': tiki_torch},
    # a jungle (set 'jungle': its own folders)
    'jungle_tree': {'label': 'Jungle tree, spreading', 'set': 'jungle', 'file': 'tree_spreading',
                    'describe': lambda: jungle_tree('FOLabJungleTree', seed=1, tall=900, spread=1050, girth=30, limbs=5, vines=7)},
    'jungle_banyan': {'label': 'Banyan', 'set': 'jungle', 'file': 'banyan',
                      'describe': lambda: jungle_tree('FOLabJungleBanyan', seed=2, tall=780, spread=1250, girth=44, limbs=6, vines=9, roots=14, leaf='dark')},
    'jungle_tall': {'label': 'Jungle tree, tall', 'set': 'jungle', 'file': 'tree_tall',
                    'describe': lambda: jungle_tree('FOLabJungleTall', seed=3, tall=1500, spread=760, girth=36, limbs=5, vines=5, straight=True)},
    'tree_fern': {'label': 'Tree fern', 'set': 'jungle', 'file': 'tree_fern', 'describe': lambda: tree_fern('FOLabJungleTreeFern', 170, seed=4)},
    'ground_fern': {'label': 'Fern', 'set': 'jungle', 'file': 'fern', 'describe': lambda: rosette('FOLabJungleFern', 'jungle/fern', 11, (80, 125), 44, seed=5)},
    'taro': {'label': 'Giant taro', 'set': 'jungle', 'file': 'taro',
             'describe': lambda: rosette('FOLabJungleTaro', 'jungle/taro', 9, (140, 200), 96, up=(82, 52), droop=(45, 75), fold=12, seed=6)},
    'ti_red': {'label': 'Ti plant, red', 'set': 'jungle', 'file': 'ti_red', 'describe': lambda: ti_plant('FOLabJungleTiRed', 'jungle/ti_red', seed=7)},
    'ti_green': {'label': 'Ti plant, green', 'set': 'jungle', 'file': 'ti_green', 'describe': lambda: ti_plant('FOLabJungleTiGreen', 'jungle/ti_green', seed=8)},
    'heliconia': {'label': 'Heliconia', 'set': 'jungle', 'file': 'heliconia', 'describe': heliconia},
    'bamboo': {'label': 'Bamboo', 'set': 'jungle', 'file': 'bamboo', 'describe': bamboo},
    'thicket': {'label': 'Thicket', 'set': 'jungle', 'file': 'thicket', 'describe': thicket},
    'undergrowth': {'label': 'Undergrowth', 'set': 'jungle', 'file': 'undergrowth', 'describe': undergrowth},
    'mossy_log': {'label': 'Fallen log', 'set': 'jungle', 'file': 'log', 'describe': mossy_log},
    'jungle_floor_a': {'label': 'Jungle floor', 'set': 'jungle', 'file': 'floor_a', 'describe': lambda: jungle_floor('FOLabJungleFloorA', seed=21)},
    'jungle_floor_b': {'label': 'Jungle floor, more taro', 'set': 'jungle', 'file': 'floor_b', 'describe': lambda: jungle_floor('FOLabJungleFloorB', seed=22, across=560, things=8)},
    'slope_cover_a': {'label': 'Slope cover', 'set': 'jungle', 'file': 'slope_a', 'describe': lambda: slope_cover('FOLabJungleSlopeA', seed=23)},
    'slope_cover_b': {'label': 'Slope cover, ferny', 'set': 'jungle', 'file': 'slope_b', 'describe': lambda: slope_cover('FOLabJungleSlopeB', seed=24, across=700, things=13)},
    # hotels (set 'hotel'): each with a far model, for the skyline
    'makai_tower': {'label': 'Makai Tower', 'set': 'hotel', 'file': 'makai_tower', 'describe': makai_tower},
    'kahuna_palms': {'label': 'Kahuna Palms', 'set': 'hotel', 'file': 'kahuna_palms', 'describe': kahuna_palms},
    'pink_pearl': {'label': 'Pink Pearl Hotel', 'set': 'hotel', 'file': 'pink_pearl', 'describe': pink_pearl},
    'blue_lagoon': {'label': 'Blue Lagoon', 'set': 'hotel', 'file': 'blue_lagoon', 'describe': blue_lagoon},
}
for _k, _v in PIECES.items():
    _v.setdefault('set', SET)
    _v.setdefault('edid', _v['describe']()['name'] if _v['set'] != SET else None)

# For a map made into a world (osmdress): which of the game's plants each piece stands in for, wherever the scatter
# would have put that plant. game editor ID, lowered: [(piece, smallest, biggest, sunk by)]. The pieces are life-size,
# so their sizes stay near 1. What has no piece yet (Zion's broadleaf trees, ferns, cacti) stays the game's.
STAND_IN = {
    'nvqueenpalm01': [('palm_tall', 0.85, 1.25, 6), ('palm_tall', 0.85, 1.25, 6), ('palm_young', 0.9, 1.3, 5)],
    'nvdatepalm01': [('palm_tall', 0.8, 1.1, 6), ('palm_young', 0.9, 1.3, 5)],
    'nvdatepalm02': [('palm_young', 0.9, 1.4, 5)],
    'nvdatepalm03': [('palm_young', 0.8, 1.2, 5)],
    'nvsagopalm01': [('palm_young', 0.45, 0.7, 4)],
    'nvsagopalm02': [('palm_young', 0.45, 0.7, 4)],
    'nvgoldfingerbanana': [('banana', 0.9, 1.5, 2)],
    'euonymusbush01': [('hibiscus', 0.7, 1.2, 3)],
    'nvfalsespireaplant': [('hibiscus', 0.6, 1.0, 3)],
    'v22grass': [('dune_grass', 1.0, 2.2, 2)],
}


def swaps(pr):
    """What osmdress.ops takes as `swaps`, and the ops that must go before its own in the same apply: every piece that
    stands in for something is written among the mod's files, and its record made if the mod hasn't it (named, so the
    scatter's ops say '$model_<piece>' for a record made in the same Undo)."""
    first, key_of = [], {}
    for piece in sorted({p for rows in STAND_IN.values() for p, *_r in rows}):
        ops, info = put(pr, piece)
        first += ops
        key_of[piece] = info['key'] or '$model_' + piece
    return first, {edid: [(key_of[p], a, b, sink) for p, a, b, sink in rows] for edid, rows in STAND_IN.items()}


# A set's plants over and above what the scatter puts down (the game's stay as they are). set: ground kind (osmcover's):
# (how many spots a cell all of that ground gets, [(piece, how often, smallest, biggest, sunk by, how many together at most)]).
EXTRA = {
    'beach': {
        'sand': (9.0, [('palm_tall', 4, 0.85, 1.25, 6, 3), ('palm_young', 3, 0.8, 1.3, 5, 2), ('dune_grass', 7, 1.0, 2.2, 2, 5), ('hibiscus', 1, 0.7, 1.1, 3, 2),
                       ('banana', 1, 0.9, 1.3, 2, 2)]),
        'grass': (10.0, [('palm_tall', 3, 0.85, 1.25, 6, 2), ('palm_young', 3, 0.8, 1.3, 5, 2), ('banana', 3, 0.9, 1.5, 2, 4), ('hibiscus', 4, 0.7, 1.3, 3, 3)]),
        'trees': (8.0, [('banana', 4, 1.0, 1.6, 2, 4), ('palm_tall', 3, 0.9, 1.3, 6, 2), ('palm_young', 2, 0.8, 1.3, 5, 2), ('hibiscus', 2, 0.8, 1.3, 3, 3)]),
        'golf': (5.0, [('palm_tall', 4, 0.9, 1.25, 6, 3), ('palm_young', 2, 0.8, 1.2, 5, 1), ('hibiscus', 2, 0.7, 1.1, 3, 3)]),
        'yard': (6.0, [('hibiscus', 4, 0.7, 1.2, 3, 2), ('banana', 2, 0.9, 1.4, 2, 2), ('palm_young', 2, 0.7, 1.2, 5, 1), ('palm_tall', 1, 0.8, 1.1, 6, 1)]),
        'paved': (1.5, [('dune_grass', 3, 0.8, 1.5, 2, 2), ('palm_young', 1, 0.6, 1.0, 5, 1)]),
    },
    # A wood becomes jungle: crowns that meet overhead (a tree's is 15 metres across: a cell 58 metres square is roofed by
    # a dozen), a middle storey to stop the eye, the ground hidden. Thinner where the map says only grass or scrub: the
    # jungle coming back. Each thing is one more for the game to hold: see JUNGLE_LIMIT.
    'jungle': {
        'trees': (75.0, [('jungle_floor_a', 12, 0.9, 1.3, 3, 2), ('jungle_floor_b', 12, 0.9, 1.3, 3, 2), ('thicket', 10, 0.8, 1.4, 6, 2),
                         ('jungle_tree', 5, 0.8, 1.25, 8, 1), ('jungle_banyan', 3, 0.8, 1.15, 8, 1), ('jungle_tall', 3, 0.8, 1.2, 8, 1),
                         ('tree_fern', 7, 0.8, 1.6, 4, 3), ('undergrowth', 4, 0.8, 1.6, 4, 2), ('taro', 3, 0.8, 1.6, 2, 2),
                         ('ti_red', 2, 0.9, 1.5, 2, 2), ('ti_green', 2, 0.9, 1.5, 2, 2), ('heliconia', 3, 0.8, 1.4, 2, 2),
                         ('bamboo', 3, 0.8, 1.2, 4, 2), ('mossy_log', 2, 0.8, 1.3, 3, 1)]),
        # (a park or a slope of scrub two hundred years untended is jungle too, a little more open: the map's own woods
        # are few in a town, and osmdress plants grass nearly as thick as woods for the same reason)
        'grass': (55.0, [('jungle_floor_a', 10, 0.9, 1.3, 3, 2), ('jungle_floor_b', 10, 0.9, 1.3, 3, 2), ('thicket', 8, 0.8, 1.3, 6, 2),
                         ('jungle_tree', 5, 0.8, 1.2, 8, 1), ('jungle_banyan', 3, 0.8, 1.15, 8, 1), ('jungle_tall', 1, 0.8, 1.1, 8, 1),
                         ('tree_fern', 5, 0.8, 1.5, 4, 2), ('undergrowth', 4, 0.8, 1.5, 4, 2), ('taro', 3, 0.8, 1.5, 2, 2), ('ti_red', 2, 0.9, 1.4, 2, 2),
                         ('heliconia', 3, 0.8, 1.3, 2, 2), ('bamboo', 2, 0.8, 1.1, 4, 1), ('mossy_log', 1, 0.8, 1.2, 3, 1)]),
        'golf': (30.0, [('jungle_floor_a', 8, 0.9, 1.2, 3, 1), ('jungle_floor_b', 8, 0.9, 1.2, 3, 1), ('jungle_tree', 4, 0.8, 1.2, 8, 1), ('jungle_banyan', 3, 0.8, 1.1, 8, 1),
                        ('thicket', 5, 0.8, 1.2, 6, 2), ('tree_fern', 3, 0.8, 1.4, 4, 2), ('heliconia', 3, 0.8, 1.3, 2, 2), ('bamboo', 2, 0.8, 1.1, 4, 1)]),
        'scrub': (50.0, [('jungle_floor_a', 8, 0.8, 1.2, 3, 2), ('jungle_floor_b', 6, 0.8, 1.2, 3, 1), ('thicket', 8, 0.7, 1.3, 6, 2), ('undergrowth', 5, 0.8, 1.4, 4, 2),
                         ('ground_fern', 4, 0.9, 1.8, 2, 3), ('tree_fern', 4, 0.8, 1.4, 4, 2), ('ti_green', 2, 0.9, 1.4, 2, 2), ('jungle_tree', 3, 0.7, 1.05, 8, 1),
                         ('jungle_banyan', 1, 0.7, 1.0, 8, 1), ('bamboo', 1, 0.8, 1.1, 4, 1), ('mossy_log', 1, 0.8, 1.2, 3, 1)]),
        'rock': (22.0, [('thicket', 5, 0.7, 1.2, 6, 2), ('undergrowth', 6, 0.8, 1.4, 4, 3), ('ground_fern', 6, 0.9, 1.8, 2, 4), ('tree_fern', 3, 0.8, 1.3, 4, 2),
                        ('jungle_floor_a', 4, 0.8, 1.1, 3, 1), ('ti_green', 2, 0.9, 1.4, 2, 2), ('jungle_tree', 2, 0.7, 1.0, 8, 1)]),
        'yard': (10.0, [('taro', 3, 0.8, 1.3, 2, 2), ('ti_red', 2, 0.9, 1.3, 2, 2), ('ti_green', 2, 0.9, 1.3, 2, 2), ('heliconia', 2, 0.8, 1.2, 2, 2),
                       ('ground_fern', 3, 0.9, 1.5, 2, 3), ('undergrowth', 2, 0.7, 1.1, 4, 2)]),
    },
}
# The low green of a mountainside and of open country, over and above the jungle's trees and floor: small ferns, tufts
# of grass, knee-high leaves, in patches twelve metres across that are one thing each (slope_cover), laid along the slope.
# A set of its own so that a world already planted as jungle can have it added.
EXTRA['mountain'] = {
    'grass': (30.0, [('slope_cover_a', 5, 0.9, 1.4, 3, 2), ('slope_cover_b', 5, 0.9, 1.4, 3, 2), ('ground_fern', 3, 0.8, 1.6, 2, 4), ('ti_green', 1, 0.8, 1.2, 2, 2)]),
    'scrub': (34.0, [('slope_cover_a', 5, 0.9, 1.4, 3, 2), ('slope_cover_b', 5, 0.9, 1.4, 3, 2), ('ground_fern', 3, 0.8, 1.6, 2, 4)]),
    'rock': (34.0, [('slope_cover_a', 5, 0.8, 1.3, 3, 2), ('slope_cover_b', 5, 0.8, 1.3, 3, 2), ('ground_fern', 4, 0.8, 1.6, 2, 4)]),
    'trees': (20.0, [('slope_cover_a', 5, 0.9, 1.4, 3, 2), ('slope_cover_b', 5, 0.9, 1.4, 3, 2)]),
}
# ground the map says nothing of, away from every road and building: for the beach set a yard, as osmdress takes it;
# for the jungle open country gone back to forest, which on an island is most of a mountain
EXTRA_UNSAID = {'beach': 'yard', 'jungle': 'grass', 'mountain': 'grass'}
EXTRA_OUT = (60.0, 260.0)   # how far from the first the rest of a group stand
# pieces that are a patch of ground cover: on a slope they are laid along it, or their downhill side hangs in the air
LAID = ('jungle_floor_a', 'jungle_floor_b', 'slope_cover_a', 'slope_cover_b', 'undergrowth', 'thicket', 'mossy_log')
EXTRA_LIMIT = {'beach': 30000, 'jungle': 40000, 'mountain': 30000}       # (things a set may add to one world: each is memory in the game)


def extra(gd, pr, world, cover, seed=1, progress=None, which='beach', thick=1.0):
    """A set's plants (which: 'beach' or 'jungle') over a world made from a map, by what the map says each spot is: (ops, report). The ops start
    with the records the mod hasn't yet (and the pieces' files are written), then one add a plant; for the same apply
    as the rest of the dressing. Nothing on roads, under water, or off the map; what lands inside a building is the
    caller's to take out, as with everything else scattered."""
    import random
    import osmcover
    import osmdress
    import roadgen
    # thick: every kind of ground gets that many times its spots (0.5: half as thick, for a world already planted heavily)
    table = {k: (d * thick, rows) for k, (d, rows) in EXTRA[which].items()}
    rng = random.Random(seed * 7919 + 11 + sum(ord(c) for c in which) * (which != 'beach'))
    first, key_of = [], {}
    for piece in sorted({p for _d, rows in table.values() for p, *_r in rows}):
        ops, info = put(pr, piece)
        first += ops
        key_of[piece] = info['key'] or '$model_' + piece
    grid = gd.grid(world)
    ground = roadgen.Ground(gd, pr, world)
    A, D, gx0, gy0 = cover.A, cover.D, cover.gx0, cover.gy0

    def kind_at(x, y):
        gx, gy = int(round(x / 128.0)) - gx0, int(round(y / 128.0)) - gy0
        if not (0 <= gx < A and 0 <= gy < D):
            return None
        v = cover.kind[gy * A + gx]
        return osmcover.ORDER[v - 1] if v else EXTRA_UNSAID[which]

    cells = sorted({(gx // 32, gy // 32) for gx in range(gx0, gx0 + A, 16) for gy in range(gy0, gy0 + D, 16)} & set(grid))
    rng.shuffle(cells)                          # (so a limit met leaves no side of the map bare)
    top = max(d for d, _r in table.values())
    out, by = [], {}
    for n, (cx, cy) in enumerate(cells):
        if len(out) >= EXTRA_LIMIT[which]:
            break
        if progress and n % 64 == 0:
            progress('Planting the %s set' % which, n, len(cells))
        for _ in range(int(top) + (rng.random() < top - int(top))):
            x, y = (cx + rng.random()) * 4096.0, (cy + rng.random()) * 4096.0
            k = kind_at(x, y)
            if k not in table:
                continue
            density, rows = table[k]
            if rng.random() > density / top:
                continue
            pick = rng.random() * sum(r[1] for r in rows)
            for piece, w, smin, smax, sink, most in rows:
                pick -= w
                if pick <= 0:
                    break
            for m in range(1 + int(rng.random() ** 2 * most)):
                px, py = x, y
                if m:
                    a, d = rng.uniform(0, math.tau), rng.uniform(*EXTRA_OUT)
                    px, py = x + math.sin(a) * d, y + math.cos(a) * d
                    if kind_at(px, py) != k:
                        continue
                cell = grid.get((int(px // 4096), int(py // 4096)))
                z = ground.at(px, py)
                if cell is None or z is None or z < 8:
                    continue
                scale = rng.uniform(smin, smax)
                rx, ry, rz = 0.0, 0.0, rng.uniform(0, math.tau)
                if piece in LAID:
                    rx, ry, rz = osmdress.lie(ground, 'pile', px, py, rz, scale * 3)     # ('pile': one of the names that lie)
                out.append({'op': 'add', 'cell': gd.key(cell), 'base': key_of[piece], 's': round(scale, 3),
                            'p': [round(px, 1), round(py, 1), round(z - sink * scale, 1), round(rx, 4), round(ry, 4), round(rz, 4)]})
                by[PIECES[piece]['label']] = by.get(PIECES[piece]['label'], 0) + 1
    return first + out, {'plants': len(out), 'by': by, 'records': len(first)}


# ---------- a skyline: the hotels stood along the shore of a world made from a map ----------
SKYLINE = ('makai_tower', 'blue_lagoon', 'kahuna_palms', 'pink_pearl')
SHORE = (700.0, 3200.0)     # how far from the sea a hotel wants to be: on the strip behind the beach, not in the surf
APART = 7000.0              # between one hotel and the next: a skyline is towers with sky between them
SHORE_WIDE = (500.0, 8000.0)   # and where to look when the strip has no room
APART_NEAR = 4500.0
STEP_OVER = 300.0           # ground that rises more than this across a hotel's footprint and the strip levelled round it is no
#                             place for one (900 was allowed: a hotel was cut into the side of Diamond Head)
BIG = 350.0                 # a thing of the mod's this long or more is a building: a hotel may not stand half through one
DOOR_NEAR = 900.0           # a building this near a door that leads somewhere is taken to be that door's building
KEEP_OFF = 250.0            # how far a hotel's footprint keeps from a door that leads somewhere, and from a landmark's
RESEAT = 4.0                # a thing on ground moved by this much or more is moved with it
MARK_ROOM = 2600.0          # round each place a landmark was stood (maps\\landmarks.json): its pieces spread about that far


def _best_site(spots, wx, stood, apart, shore, to_sea, in_the_way, batch, box, landmarks, refused, piece):
    """The cheapest place and turn among these spots: (cost, x, y, turn, ground height) or None."""
    best = None
    for x, y in spots:
        if wx is None and any(math.hypot(x - sx, y - sy) < apart for _p, sx, sy, _r in stood):
            continue
        d, (ux, uy) = to_sea(x, y)
        if wx is None and (d is None or not shore[0] <= d <= shore[1]):
            continue
        for k in range(8):
            rz = k * math.pi / 4
            why = in_the_way(x, y, rz, box)
            if why:
                if wx is not None and why not in [r[1] for r in refused if r[0] == piece]:
                    refused.append((piece, why))
                continue
            bad = batch._score(x, y, rz, box)
            if bad is None:
                continue
            m = landmarks.MARGIN         # (the strip levelled round it counts: that is where the cut into a hillside shows)
            hs = [batch.height(x + tx, y + ty) for tx, ty in (landmarks._turn(box[0] - m + (box[2] - box[0] + 2 * m) * u / 4.0, box[1] - m + (box[3] - box[1] + 2 * m) * v / 4.0, rz)
                                                             for u in range(5) for v in range(5))]
            if None in hs or min(hs) < 8 or (wx is None and max(hs) - min(hs) > STEP_OVER):
                continue
            fx, fy = landmarks._turn(0.0, -1.0, rz)        # (which way its front looks, turned as the game turns things)
            cost = bad + 25.0 * (1 - (fx * ux + fy * uy)) + (abs(d - 1500.0) / 300.0 if d else 0.0) + (max(hs) - min(hs)) / 60.0
            if best is None or cost < best[0]:
                best = (cost, x, y, rz, sorted(hs)[len(hs) // 2])
    return best


class Obstacles:
    """What a big thing of the mod's own (a hotel, a landmark of the coast) may not stand on, in a world.

    Clearing a footprint takes out whatever the mod has there, which is right for a shack or a palm; but a building
    someone can go into is more than what stands outside: behind its door are a place of its own, that place's navmesh
    and a door leading back, all naming the door outside. Take the door and the mod can no longer be saved (it was: a
    build with 300 such buildings). So nothing goes where a linked door is, and nothing on a landmark either.
    own: also keep off what the mod has made of its own that is big (the hotels and the coast's things, by
    maps\\hotels.json and maps\\coast.json, and what was borrowed from another game: the carrier), which are never
    cleared."""

    def __init__(self, gd, pr, world, own=False):
        import landmarks
        import townbuild
        self.landmarks = landmarks
        grid = gd.grid(world)
        self.doors = doors = []
        for cell in grid.values():
            c = pr.cells.get(gd.key(cell))
            for rk, r in (c['refs'].items() if c else ()):
                if r.get('tel') and r.get('p') and not r.get('removed'):
                    doors.append((r['p'][0], r['p'][1]))
        self.marks = [(mx, my, math.hypot(max(abs(x0), abs(x1)), max(abs(y0), abs(y1)))) for mx, my, _rz, x0, y0, x1, y1 in landmarks.standing(gd, pr, world)]
        try:                                    # (where the landmarks step says it stood each: a set is many pieces, not all big)
            import api_maps
            kept = api_maps._kept(pr, 'landmarks.json').get(gd.edid(world)) or {}
            self.marks += [(float(m['x']), float(m['y']), MARK_ROOM) for m in (kept.get('stood') if isinstance(kept, dict) else kept) or [] if 'x' in m and 'y' in m]
        except Exception:
            pass
        if own:
            for x, y, _rz, x0, y0, x1, y1 in footprints(pr, gd, world):
                self.marks.append((x, y, math.hypot(max(abs(x0), abs(x1)), max(abs(y0), abs(y1)))))
        # every building the mod has standing: where, how turned, how big, and whether someone can go into it
        sizes, self.bigs = {}, []
        for cell in grid.values():
            ck = gd.key(cell)
            c = pr.cells.get(ck)
            for rk, r in (c['refs'].items() if c else ()):
                q, base = r.get('p'), r.get('base')
                if not rk.startswith('+') or not q or not base or r.get('removed'):
                    continue
                if base not in sizes:
                    o = None
                    try:
                        if not str(base).startswith('+'):
                            o = townbuild.obnd(gd, base)
                        elif own:
                            o = self._own_bounds(pr, base)
                    except Exception:
                        o = None
                    sizes[base] = o if o and max(o[3] - o[0], o[4] - o[1]) >= BIG else None
                o = sizes[base]
                if o:
                    sc = float(r.get('s') or 1.0)
                    keep = str(base).startswith('+')    # (the mod's own: kept, never cleared)
                    self.bigs.append((q[0], q[1], q[5] if len(q) > 5 else 0.0, (o[0] * sc, o[1] * sc, o[3] * sc, o[4] * sc), ck, rk,
                                      keep or any(math.hypot(dx - q[0], dy - q[1]) < DOOR_NEAR for dx, dy in doors)))
        # (by square, so that a search over thousands of spots doesn't look at every building for each)
        self.by, self.big_r = {}, 0.0
        for n, (bx, by, _r, bb, _c, _k, _l) in enumerate(self.bigs):
            self.by.setdefault((int(bx // self.SQ), int(by // self.SQ)), []).append(n)
            self.big_r = max(self.big_r, math.hypot(max(abs(bb[0]), abs(bb[2])), max(abs(bb[1]), abs(bb[3]))))

    SQ = 2048.0

    def _near(self, x, y, reach):
        r = reach + self.big_r
        for i in range(int((x - r) // self.SQ), int((x + r) // self.SQ) + 1):
            for j in range(int((y - r) // self.SQ), int((y + r) // self.SQ) + 1):
                for n in self.by.get((i, j), ()):
                    yield self.bigs[n]

    @staticmethod
    def _own_bounds(pr, base):
        """A record of the mod's own that is a big thing to keep off: a hotel's, a coast piece's, or one from another
        game (not under meshes\\folab); not the plants', which are cleared like anything else."""
        rec = pr.records.get(base)
        if not rec or rec.get('type') != 'STAT':
            return None
        model = (recordio.field(rec, 'MODL') or '').lower()
        if model.startswith('folab\\') and not model.startswith(('folab\\hotel\\', 'folab\\coast\\', 'folab\\resort\\')):
            return None
        for sub in rec['subs']:
            if sub['tag'] == 'OBND':
                return [f['value'] for f in sub['fields'] if 'name' in f]
        return None

    def through(self, x, y, rz, box):
        """The buildings a thing standing so would stand partly through: [(cell, ref, someone can go in, or it is kept)]."""
        landmarks = self.landmarks
        reach = math.hypot(max(abs(box[0]), abs(box[2])), max(abs(box[1]), abs(box[3])))
        out = []
        for bx, by, brz, bb, ck, rk, linked in self._near(x, y, reach):
            br = math.hypot(max(abs(bb[0]), abs(bb[2])), max(abs(bb[1]), abs(bb[3])))
            if math.hypot(bx - x, by - y) > reach + br:
                continue
            hit = False
            for u in (0.0, 0.5, 1.0):               # the building's outline against the box
                for v in (0.0, 0.5, 1.0):
                    tx, ty = landmarks._turn(bb[0] + (bb[2] - bb[0]) * u, bb[1] + (bb[3] - bb[1]) * v, brz)
                    lx, ly = landmarks._turn(bx + tx - x, by + ty - y, -rz)
                    if box[0] - 60 <= lx <= box[2] + 60 and box[1] - 60 <= ly <= box[3] + 60:
                        hit = True
                    tx, ty = landmarks._turn(box[0] + (box[2] - box[0]) * u, box[1] + (box[3] - box[1]) * v, rz)     # and the other way round
                    lx, ly = landmarks._turn(x + tx - bx, y + ty - by, -brz)
                    if bb[0] <= lx <= bb[2] and bb[1] <= ly <= bb[3]:
                        hit = True
            if hit:
                out.append((ck, rk, linked))
        return out

    def in_the_way(self, x, y, rz, box):
        if any(linked for _c, _r, linked in self.through(x, y, rz, box)):
            return 'a building with a way in'
        reach = math.hypot(max(abs(box[0]), abs(box[2])), max(abs(box[1]), abs(box[3]))) + KEEP_OFF
        for mx, my, mr in self.marks:
            if math.hypot(mx - x, my - y) < reach + mr:
                return 'a landmark'
        for dx, dy in self.doors:
            if abs(dx - x) < reach and abs(dy - y) < reach:
                lx, ly = self.landmarks._turn(dx - x, dy - y, -rz)
                if box[0] - KEEP_OFF <= lx <= box[2] + KEEP_OFF and box[1] - KEEP_OFF <= ly <= box[3] + KEEP_OFF:
                    return 'a building with a way in'
        return None


def reseat(gd, pr, grid, batch):
    """'move' ops for what stands on ground a batch moved: levelling reaches a margin past each footprint, and a bush
    left where it was would hang in the air over ground brought down (or be buried under ground brought up)."""
    seats = []
    for k in batch.forms:
        ck = gd.key(grid[k])
        c = pr.cells.get(ck)
        for rk, r in (c['refs'].items() if c else ()):
            q = r.get('p')
            if not rk.startswith('+') or not q or r.get('removed') or (ck, rk) in batch.gone:
                continue
            was, now = batch.ground.at(q[0], q[1]), batch.height(q[0], q[1])
            if was is None or now is None or abs(now - was) < RESEAT:
                continue
            seats.append({'op': 'move', 'cell': ck, 'ref': rk, 'p': [q[0], q[1], round(q[2] + now - was, 1)] + list(q[3:])})
    return seats


def skyline(gd, pr, world, cover, roads=(), count=4, seed=1, progress=None, sites=None):
    """(ops, report): hotels stood in a world, each on ground levelled for it, facing the sea, what the mod had standing
    there cleared. sites: [(piece, x, y)] to say where; otherwise the best places near the shore are found, clear of
    roads and of each other. The pieces' files (far models too) are written, and their records made if the mod hasn't
    them. Run it after everything else that stands things: only this knows where the hotels are."""
    import landmarks
    import osmcover
    batch = landmarks.Batch(gd, pr, world, roads, seed)
    A, D, gx0, gy0 = cover.A, cover.D, cover.gx0, cover.gy0
    sea_code, road_code = osmcover.CODE['seabed'], osmcover.CODE['asphalt']
    sea = [((gx0 + x) * 128.0, (gy0 + y) * 128.0) for y in range(0, D, 6) for x in range(0, A, 6) if cover.kind[y * A + x] == sea_code]

    def to_sea(x, y):
        """How far the sea is from a spot, and which way."""
        best = None
        for sx, sy in sea:
            d = (sx - x) ** 2 + (sy - y) ** 2
            if best is None or d < best[0]:
                best = (d, sx, sy)
        if best is None:
            return None, (0.0, -1.0)
        d = math.sqrt(best[0]) or 1.0
        return d, ((best[1] - x) / d, (best[2] - y) / d)

    grid = gd.grid(world)
    obs = Obstacles(gd, pr, world)
    through, in_the_way = obs.through, obs.in_the_way

    first, adds, stood, refused = [], [], [], []
    want = list(sites) if sites else [(SKYLINE[k % len(SKYLINE)], None, None) for k in range(count)]
    for n, (piece, wx, wy) in enumerate(want):
        if progress:
            progress('Standing the hotels', n, len(want))
        ops, info = put(pr, piece)
        first += ops
        key = info['key'] or '$model_' + piece
        b = info['box']
        box = (b[0], b[1], b[3], b[4])
        best = None
        # where to look: the strip behind the beach first; if a built-up town leaves no room there, more finely and
        # further inland, with the towers allowed nearer each other
        for step, shore, apart in ((8, SHORE, APART), (4, SHORE_WIDE, APART_NEAR)):
            if best is not None:
                break
            if wx is not None:
                spots = [(wx, wy)] if step == 8 else []
            else:
                spots = [((gx0 + x) * 128.0, (gy0 + y) * 128.0) for y in range(8, D - 8, step) for x in range(8, A - 8, step)
                         if cover.kind[y * A + x] not in (sea_code, road_code)]
            best = _best_site(spots, wx, stood, apart, shore, to_sea, in_the_way, batch, box, landmarks, refused, piece)
        if best is None:
            continue
        _c, x, y, rz, z = best
        z = max(24.0, round(z / 8) * 8.0)
        batch.clear(x, y, rz, box)
        for ck, rk, _linked in through(x, y, rz, box):          # a building it would stand half through goes whole
            if (ck, rk) not in batch.gone:
                batch.gone.add((ck, rk))
                batch.ops.append({'op': 'remove', 'cell': ck, 'ref': rk})
        batch.level(x, y, rz, box, z)
        cell = grid.get((int(x // 4096), int(y // 4096)))
        if cell is None:
            continue
        adds.append({'op': 'add', 'cell': gd.key(cell), 'base': key, 'p': [round(x, 1), round(y, 1), z, 0.0, 0.0, round(rz, 4)], 's': 1.0})
        batch.made.append((x, y, rz, box))
        stood.append((piece, x, y, rz))
    seats = reseat(gd, pr, grid, batch)
    # (and to be sure of it: nothing taken out may be a door something still leads to)
    gone = {(o['cell'], o['ref']) for o in batch.ops if o['op'] == 'remove'}
    for ck, c in pr.cells.items():
        for rk, r in c['refs'].items():
            if (ck, rk) in gone and r.get('tel'):
                raise ValueError('A hotel would have taken out a door that leads somewhere (%s): nothing was changed.' % rk)
    return first + batch.done() + adds + seats, {'hotels': [{'piece': p, 'label': PIECES[p]['label'], 'x': round(x), 'y': round(y), 'turn': round(rz, 3)} for p, x, y, rz in stood],
                                         'reseated': len(seats),
                                         'no_room': [PIECES[p]['label'] for p, _x, _y in want if p not in [q[0] for q in stood]], 'refused': refused,
                                         'asked': len(want), 'cleared': sum(1 for o in batch.ops if o['op'] == 'remove'), 'levelled': len(batch.forms)}


_drawn = {}             # texture name -> (colour DDS, normal DDS): each is drawn once a run


def texture_files(name):
    if name not in _drawn:
        _drawn[name] = TEXTURES[name]().files(game=True)       # (relief and size as the game's: texpaint.normal_map)
    return _drawn[name]


def build(piece):
    """A piece made: `modelmake.make`'s answer with 'mesh' (its path under Data) and 'files' {path: bytes}, the mesh
    and every texture it names."""
    what = PIECES[piece]
    desc = what['describe']()
    made = modelmake.make(desc)
    made['mesh'] = 'meshes\\folab\\%s\\%s.nif' % (what['set'], what['file'])
    files = {made['mesh']: made['nif']}
    far = far_of(desc)
    if far:                                     # (beside the model, as the game keeps its own: lodobj looks for it there)
        made['far'] = modelmake.make(far)
        files[made['mesh'][:-4] + '_lod.nif'] = made['far']['nif']
        made['textures'] = sorted(set(made['textures']) | set(made['far']['textures']))
    for name in list(TEXTURES):                 # (drawing one may bring in a set that adds more)
        if tex_path(name) in made['textures']:
            files[tex_path(name)], files[tex_path(name, True)] = texture_files(name)
    missing = [t for t in made['textures'] if t not in files]
    if missing:
        raise ValueError('%s names textures the set doesn\'t draw: %s' % (piece, ', '.join(missing)))
    made['files'] = files
    return made


VWD = 0x8000           # (a static's 'visible when distant': the game's own carry it where they have a far model, 485 of 571)


def _static(edid, model, box, flags=0):
    return {'type': 'STAT', 'flags': flags, 'src': '', 'subs': [
        {'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': edid},
        {'tag': 'OBND', 'label': 'Bounds', 'kind': 'struct', 'fields': [{'name': n, 'code': 'h', 'value': int(v)} for n, v in zip(('X1', 'Y1', 'Z1', 'X2', 'Y2', 'Z2'), box)]},
        {'tag': 'MODL', 'label': 'Model', 'kind': 'z', 'value': model}]}


def record_of(pr, piece):
    """The mod's record for a piece, if it has one."""
    edid = PIECES[piece]['edid']
    for key, rec in pr.records.items():
        if key.startswith('+') and rec.get('type') == 'STAT' and recordio.field(rec, 'EDID') == edid:
            return key
    return None


def put(pr, piece):
    """A piece among the mod's own files (written afresh: a piece redesigned replaces the old one), and the ops that
    make its record: none when the mod has it already. Returns (ops, {'key' or None, 'mesh', 'files', 'box', ...})."""
    made = build(piece)
    root = library.assets_dir(pr)
    for rel, data in made['files'].items():
        full = os.path.join(root, rel)
        if not os.path.isfile(full) or open(full, 'rb').read() != data:
            library._put(root, rel, data)
    key = record_of(pr, piece)
    what = PIECES[piece]
    ops = [] if key else [{'op': 'record_new', 'record': _static(what['edid'], made['mesh'][7:], made['box'], VWD if made.get('far') else 0), 'name': 'model_' + piece}]
    return ops, {'key': key, 'piece': piece, 'label': what['label'], 'edid': what['edid'], 'mesh': made['mesh'],
                 'files': sorted(made['files']), 'box': made['box'], 'triangles': made['triangles'], 'solids': len(made['solids'])}


_foot = {}


def footprints(pr, gd, world):
    """Where the hotels stand in a world, as boxes for landmarks.clear_of ((x, y, turn, x0, y0, x1, y1), a little over
    each one's footprint): what is planted afterwards keeps out of them."""
    import api_maps
    _all_sets()
    out = []
    # (and the coast's own things, maps\\coast.json: coastplace; the city's landmarks, maps\\resort.json: resortplace)
    for h in [h for f in ('hotels.json', 'coast.json', 'resort.json') for h in (api_maps._kept(pr, f).get(gd.edid(world)) or [])]:
        if h.get('piece') not in PIECES:
            continue
        if h['piece'] not in _foot:
            _foot[h['piece']] = modelmake.make(PIECES[h['piece']]['describe']())['box']
        b = _foot[h['piece']]
        out.append((h['x'], h['y'], h.get('turn', 0.0), b[0] - 120, b[1] - 120, b[3] + 120, b[4] + 120))
    return out


def distant_ops(pr):
    """Ops that mark the mod's records of every piece with a far model 'visible when distant' (VWD), as the game marks its
    own: records made before put set it had none."""
    import copy
    _all_sets()
    ops = []
    for piece, what in PIECES.items():
        key = record_of(pr, piece)
        if not key or pr.records[key].get('flags', 0) & VWD:
            continue
        if far_of(what['describe']()) is None:
            continue
        rec = copy.deepcopy(pr.records[key])
        rec['flags'] = rec.get('flags', 0) | VWD
        ops.append({'op': 'record', 'key': key, 'record': rec})
    return ops


def remake(pr, which=None):
    """The files of every piece the mod already has a record for, written afresh (which: only that set's): after a
    piece is redesigned, what is already placed in the mod takes the new look. No ops: the records stay as they are,
    but for their bounds, which go by the new mesh."""
    done = []
    for piece, what in PIECES.items():
        if which and what['set'] != which:
            continue
        key = record_of(pr, piece)
        if not key:
            continue
        _ops, info = put(pr, piece)
        for sub in pr.records[key]['subs']:
            if sub['tag'] == 'OBND':
                for f, v in zip([f for f in sub['fields'] if 'name' in f], info['box']):
                    f['value'] = int(v)
        done.append(piece)
    return done


def _all_sets():
    """The sets that register their pieces here when imported (they import this module, so not at its top)."""
    import citypieces  # noqa: F401
    import waikikiset  # noqa: F401
    import coastset  # noqa: F401
    import resortset  # noqa: F401
    import towerset  # noqa: F401
    import historicset  # noqa: F401
    import battleship  # noqa: F401
    import shipinside  # noqa: F401


def get(path, q):
    _all_sets()
    if path == 'list':
        return {'set': SET, 'pieces': [{'piece': k, 'label': v['label'], 'edid': v['edid']} for k, v in PIECES.items()]}
    raise FileNotFoundError(path)


def post(path, body, srv):
    _all_sets()
    """POST /api/models/<path>. make {piece}: the piece's files into the mod and its record, one Undo; answers with
    the record's key, ready to place."""
    if not srv.PR:
        raise ValueError('Start a mod first: the model is kept with it.')
    if path == 'remake':
        return {'remade': remake(srv.PR, body.get('set')), 'state': srv.state()}
    if path == 'make':
        piece = body.get('piece')
        if piece not in PIECES:
            raise ValueError('No piece called %s: there are %s.' % (piece, ', '.join(PIECES)))
        ops, info = put(srv.PR, piece)
        out = srv.edit('Make ' + info['label'], ops) if ops else {'state': srv.state()}
        info['key'] = info['key'] or out['made'][0]
        out['model'] = info
        return out
    raise FileNotFoundError(path)
