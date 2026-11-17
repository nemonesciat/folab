"""More of the city: three hotels unlike the seven already standing, and five landmarks a city of the fifties had
and the war left, all in `texwear`'s worn paint.

Hotels (set 'resort', each with a far model):
- Lani Moku: a Y of three wings of rooms round a six-sided core, eighteen floors over a glazed podium, a neon star on
  a mast over the core.
- Coral Crescent: nine floors bent in an arc round the beach it looks onto, an arcade of columns at its foot, a
  pylon sign with a starburst at one end.
- Tradewinds Motor Lodge: two floors round three sides of a courtyard with a pool gone green, a walkway along the
  upper rooms with stairs at the corners, tiled roofs, a boomerang sign by the road.

Landmarks (set 'resort'):
- a Ferris wheel on its A-frames, two gondolas gone and one fallen;
- a water tower with the city's name painted round its tank;
- a band shell of five arches stepping back over a stage, benches in front;
- a civil-defence siren on a pole with a fallout-shelter sign;
- a giant tiki, a roadside attraction ten metres tall.

Frame as every piece of `modelsets`: the middle of the foot at the origin, z up, front towards -y (a hotel's sea side,
the wheel's and the shell's open side, the lodge's courtyard), 70 units a metre, FLOOR = 256. Registered into
`modelsets` at import as coastset is; nothing imports this module yet (see `resortplace` for where each goes). Names
on signs are made up for the place."""
import math

import modelsets
import texpaint as tp
import texwear as tw
import waikikiset
from modelsets import FLOOR, limb, look

SEAFOAM = (150, 200, 178)
PEACH = (226, 190, 160)
YELLOW = (226, 184, 48)

SIGN_LINES = ['LANI MOKU', 'CORAL CRESCENT', 'TRADEWINDS', 'MOTOR LODGE', 'NO VACANCY', 'SKY WHEEL', 'TICKETS', 'BIG KAHUNA']


def _signs():
    grounds = [tp.CREAM, (238, 128, 108), tp.TURQUOISE, tp.CREAM, (30, 30, 30), tp.YELLOW, tp.WHITE, tp.CORAL]
    inks = [tp.TEAL_INK, tp.WHITE, tp.WHITE, tp.RED, (230, 70, 60), tp.RED, tp.TEAL_INK, tp.CREAM]
    edges = [tp.CORAL, tp.CREAM, tp.YELLOW, tp.TURQUOISE, (90, 90, 90), tp.RED, tp.CORAL, tp.YELLOW]
    return tw.sign_aged([{'box': (0, n / 8.0, 1, (n + 1) / 8.0), 'lines': [t], 'ground': grounds[n], 'ink': inks[n], 'edge': edges[n]}
                         for n, t in enumerate(SIGN_LINES)], w=1024, h=1024, seed=650, bulbs=True)


modelsets.TEXTURES.update({
    'resort/lanai_seafoam': lambda: tw.facade_sheet(front=SEAFOAM, bays=tw.FRONT_BAYS, floors=tw.FRONT_BAYS, size=tw.FRONT_SIZE, seed=600),
    'resort/lanai_open': lambda: tw.facade_sheet(bays=tw.FRONT_BAYS, floors=tw.FRONT_BAYS, size=tw.FRONT_SIZE, seed=601),
    'resort/window_peach': lambda: tw.facade_sheet(wall=PEACH, kind='window', bays=tw.FRONT_BAYS, floors=tw.FRONT_BAYS, size=tw.FRONT_SIZE, seed=602, under=(196, 214, 204)),
    'resort/window_cream': lambda: tw.facade_sheet(kind='window', bays=tw.FRONT_BAYS, floors=tw.FRONT_BAYS, size=tw.FRONT_SIZE, seed=603),
    'resort/motel': lambda: tw.facade_sheet(wall=tp.CREAM, front=tp.TURQUOISE, kind='motel', bays=tw.FRONT_BAYS, floors=tw.FRONT_BAYS, size=tw.FRONT_SIZE, seed=604),
    'resort/far_seafoam': lambda: tw.far_sheet(front=SEAFOAM, size=128, seed=605),
    'resort/far_open': lambda: tw.far_sheet(size=128, seed=606),
    'resort/far_peach': lambda: tw.far_sheet(wall=PEACH, size=128, seed=607),
    'resort/far_cream': lambda: tw.far_sheet(size=128, seed=608),
    'resort/render_white': lambda: tw.render(tp.CONCRETE_WHITE, size=512, seed=610),
    'resort/render_peach': lambda: tw.render(PEACH, under=(196, 214, 204), size=512, seed=611),
    'resort/render_cream': lambda: tw.render(tp.CREAM, under=(150, 200, 190), size=512, seed=612, peel=0.5),
    'resort/concrete': lambda: tw.concrete(size=512, seed=613),
    'resort/terrazzo': lambda: tw.terrazzo(size=256, seed=614),
    'resort/tar': lambda: tw.tar_roof(size=512, seed=615),
    'resort/clay': lambda: tw.clay_tiles(size=512, seed=616),
    'resort/lava': lambda: tw.lava(size=512, seed=617),
    'resort/blocks': lambda: tw.breeze_blocks(size=256, seed=618),
    'resort/glass': lambda: tw.glass_curtain(size=256, seed=619, panes=(2, 1), broken=0.35),
    'resort/steel_red': lambda: tw.steel(tp.RED, size=256, seed=620, rust=0.5),
    'resort/steel_white': lambda: tw.steel(tp.WHITE, size=256, seed=621, rust=0.45, flake=0.4),
    'resort/steel_yellow': lambda: tw.steel(YELLOW, size=256, seed=622, rust=0.4),
    'resort/steel_grey': lambda: tw.steel((120, 124, 120), size=256, seed=623, rust=0.6),
    'resort/wood': lambda: tw.wood(None, size=256, seed=624),
    'resort/wood_turq': lambda: tw.wood(tp.TURQUOISE, size=256, seed=625, paint_left=0.6),
    'resort/tiki': lambda: tw_tiki(),
    'resort/pool': lambda: tw.pool_murky(size=256, seed=626),
    'resort/shelter': lambda: tw.shelter_sign(size=256, seed=627),
    'resort/signs': _signs,
    'resort/tank': lambda: tw.painted_letters('WAIKIKI       WAIKIKI', wall=(190, 192, 184), ink=(40, 78, 110), w=1024, h=256, seed=628),
    'resort/far_white': lambda: tw.far_plain(tp.CONCRETE_WHITE, seed=630),
    'resort/far_peach_plain': lambda: tw.far_plain(PEACH, seed=631),
    'resort/far_glass': lambda: tw.far_plain((40, 62, 64), seed=632),
    'resort/far_red': lambda: tw.far_plain(tp.RED, seed=633),
    'resort/far_rust': lambda: tw.far_plain(tw.RUST, seed=634),
    'resort/far_clay': lambda: tw.far_plain((170, 88, 60), seed=635),
    'resort/far_tar': lambda: tw.far_plain((70, 68, 64), seed=636),
    'resort/far_wood': lambda: tw.far_plain(tw.SILVER_WOOD, seed=637),
})


def tw_tiki():
    """`texpaint.tiki_face` carved deeper and worn: the wood silvered, the cuts dark with dirt, moss low down."""
    base = tp.tiki_face(w=256, h=512, seed=640, colour=(118, 96, 74))
    c = tw.Picture(256, 512, gloss=14)
    wr = tw.Wear(256, 512, 641, grime=0.9, rain=1.0, ledges=(0.0, 0.25), low_dust=0.3)
    moss = tw.Field(256, 512, 642, cells=4, octaves=4)
    for p in range(256 * 512):
        x, y = p % 256, p // 256
        col = tw.mix(base.rgb[p], tw.SILVER_WOOD, 0.35)
        depth = 1.0 if base.ht[p] < 0.4 else 0.0
        if y > 400 and moss.v[p] > 0.55:
            col = tw.mix(col, (70, 92, 46), 0.6)
        c.rgb[p], c.ht[p] = tw.grade(wr.on(x, y, col, depth)), base.ht[p]
    return c


def _sign(n, turned=False):
    return look('resort/signs', region=(0, n / 8.0, 1, (n + 1) / 8.0), turned=turned)


def _looks():
    out = {
        'lanai_s': look('resort/lanai_seafoam', tile=tw.FRONT_TILE, far='resort/far_seafoam'),
        'lanai': look('resort/lanai_open', tile=tw.FRONT_TILE, far='resort/far_open'),
        'win_peach': look('resort/window_peach', tile=tw.FRONT_TILE, far='resort/far_peach'),
        'win': look('resort/window_cream', tile=tw.FRONT_TILE, far='resort/far_cream'),
        'motel': look('resort/motel', tile=tw.FRONT_TILE, far='resort/far_cream'),
        'white': look('resort/render_white', tile=512, far='resort/far_white'),
        'peach': look('resort/render_peach', tile=512, far='resort/far_peach_plain'),
        'cream': look('resort/render_cream', tile=512, far='resort/far_white'),
        'concrete': look('resort/concrete', tile=512, far='resort/far_white'),
        'terrazzo': look('resort/terrazzo', tile=256),
        'tar': look('resort/tar', tile=512, far='resort/far_tar'),
        'clay': look('resort/clay', tile=384, far='resort/far_clay'),
        'lava': look('resort/lava', tile=400, far='resort/far_tar'),
        'blocks': look('resort/blocks', tile=256),
        'glass': dict(look('resort/glass', tile=320, far='resort/far_glass'), gloss=60),
        'red': look('resort/steel_red', tile=192, far='resort/far_red'),
        'steel': look('resort/steel_white', tile=192, far='resort/far_white'),
        'yellow': look('resort/steel_yellow', tile=192, far='resort/far_red'),
        'grey': look('resort/steel_grey', tile=192, far='resort/far_rust'),
        'wood': look('resort/wood', tile=192, far='resort/far_wood'),
        'door': look('resort/wood_turq', tile=128),
        'pool': dict(look('resort/pool', tile=400), gloss=80),
        'shelter': look('resort/shelter'),
        'tank': look('resort/tank', far='resort/far_white'),
        'tiki_head': look('resort/tiki', region=(0, 0, 1, 0.74)),
        'tiki_body': look('resort/tiki', region=(0, 0.7, 1, 1)),
        'tiki_nose': look('resort/tiki', region=(0.36, 0.38, 0.64, 0.5)),
        'neon': waikikiset.lit('waikiki/neon_red', 4.0),
        'bulb': waikikiset.lit('waikiki/lamp_glass', 3.0),
    }
    for n in range(8):
        out['sign%d' % n] = _sign(n)
        out['sign%d_up' % n] = _sign(n, True)
    return out


def _block(parts, x, y, z, wide, deep, floors, front, back, turn=0.0, lanai=70, ends='white', top='tar', bottom=None, slabs=True):
    """A block of rooms, its slab at every floor reaching out front and back."""
    parts.append({'shape': 'box', 'size': [wide, deep, floors * FLOOR], 'at': [x, y, z], 'turn': [0, 0, turn], 'look': ends,
                  'faces': {'front': front, 'back': back, 'top': top, 'bottom': bottom}, 'material': 'stone', 'far': True})
    if slabs:
        for f in range(1, floors + 1):
            parts.append({'shape': 'slab', 'size': [wide + 24, deep + 2 * lanai, 12], 'at': [x, y, z + f * FLOOR - 12], 'turn': [0, 0, turn],
                          'look': 'concrete', 'solid': False})
        modelsets.lanai_detail(parts, x, y, z, wide, deep, floors, turn, lanai, look_name='concrete', rail='steel')
    if top == 'tar':
        modelsets.roof_plant(parts, x, y, z + floors * FLOOR, wide, deep, turn, seed=int(wide + floors), body='concrete', metal='steel')


def _star(parts, x, y, z, r, look_name, rays=4, far=False):
    """A googie starburst: thin rays crossing at a point, in the plane facing -y."""
    for k in range(rays):
        a = 180.0 * k / rays
        parts.append({'shape': 'box', 'size': [2 * r, 10, 16], 'at': [x, y, z - 8], 'turn': [0, a, 0], 'look': look_name, 'solid': False, 'far': far})


# ---------- hotels ----------

def lani_moku():
    """Three wings of rooms round a six-sided core, eighteen floors over a two-floor glazed podium of lava rock and
    glass, a neon star on a mast over the core and the name across the sea wing's roof."""
    parts = []
    up, floors = 2 * FLOOR, 18
    top = up + floors * FLOOR
    parts.append({'shape': 'cylinder', 'r': 2100, 'h': up, 'sides': 6, 'turn': [0, 0, 30], 'look': 'glass', 'cap_look': 'terrazzo', 'material': 'stone', 'far': True})
    parts.append({'shape': 'cylinder', 'r': 2200, 'h': 40, 'sides': 6, 'at': [0, 0, up], 'turn': [0, 0, 30], 'look': 'concrete', 'solid': False})
    for k in range(6):                          # lava-rock piers round the podium
        a = math.radians(30 + 60 * k)
        parts.append({'shape': 'box', 'size': [260, 260, up], 'at': [math.cos(a) * 1900, math.sin(a) * 1900, 0], 'turn': [0, 0, 60 * k], 'look': 'lava', 'material': 'stone'})
    parts.append({'shape': 'cylinder', 'r': 440, 'h': top + 380, 'sides': 6, 'at': [0, 0, up], 'look': 'white', 'cap_look': 'tar', 'material': 'stone', 'far': True})
    for k in range(3):
        a = -90 + 120 * k
        L, d = 1792.0, 512.0
        cx, cy = math.cos(math.radians(a)) * (340 + L / 2), math.sin(math.radians(a)) * (340 + L / 2)
        _block(parts, cx, cy, up, L, d, floors, 'lanai_s' if k == 0 else 'lanai', 'win_peach', turn=a, ends='peach')
        # a fin of pierced block up each wing's end, standing off it
        ex, ey = math.cos(math.radians(a)) * (340 + L + 30), math.sin(math.radians(a)) * (340 + L + 30)
        parts.append({'shape': 'box', 'size': [24, 380, floors * FLOOR - 128], 'at': [ex, ey, up + 64], 'turn': [0, 0, a], 'look': 'blocks', 'solid': False})
        # plant on the wing's roof
        px, py = math.cos(math.radians(a)) * 1100, math.sin(math.radians(a)) * 1100
        parts.append({'shape': 'box', 'size': [300, 220, 180], 'at': [px, py, top], 'turn': [0, 0, a], 'look': 'grey', 'faces': {'top': 'tar'}, 'material': 'metal'})
    # the name over the sea wing, both ways
    parts.append({'shape': 'box', 'size': [1500, 24, 300], 'at': [0, -1600, top + 20], 'look': 'steel', 'faces': {'front': 'sign0', 'back': 'sign0'}, 'solid': False, 'far': True})
    for x in (-600, 600):
        parts.append({'shape': 'box', 'size': [20, 20, 40], 'at': [x, -1600, top], 'look': 'grey', 'solid': False})
    # the mast and its star
    mast = top + 380
    parts.append({'shape': 'cylinder', 'r': 26, 'r2': 14, 'h': 1000, 'sides': 6, 'at': [0, 0, mast], 'look': 'steel', 'solid': False, 'far': True})
    _star(parts, 0, -30, mast + 1000, 260, 'neon', rays=4, far=True)
    parts.append({'shape': 'ball', 'r': 34, 'sides': 6, 'rings': 3, 'at': [0, -30, mast + 966], 'look': 'neon', 'solid': False})
    # the drive's canopy, out of the podium towards the sea
    parts.append({'shape': 'slab', 'size': [900, 1100, 20], 'at': [0, -2500, 420], 'look': 'concrete', 'faces': {'bottom': 'white'}, 'solid': False})
    for x in (-380, 380):
        parts.append({'shape': 'box', 'size': [30, 30, 420], 'at': [x, -2950, 0], 'look': 'grey'})
    return {'name': 'FOLabHotelLaniMoku', 'looks': _looks(), 'parts': parts}


CRESCENT_R = 3600.0
CRESCENT_STEP = 8.6        # degrees of the arc to one segment
CRESCENT_N = 9


def coral_crescent():
    """Nine floors in nine segments bent round an arc whose middle is out towards the sea, so the whole hotel embraces
    the beach in front; an arcade of columns along its foot, the rooms' lanais all facing in; a pylon sign with a
    starburst at its west end; a folded canopy on the roof's middle."""
    parts = []
    R, floors = CRESCENT_R, 9
    ground = FLOOR + 64
    w = 2 * R * math.sin(math.radians(CRESCENT_STEP / 2)) + 30
    for k in range(CRESCENT_N):
        th = 90 + (k - (CRESCENT_N - 1) / 2.0) * CRESCENT_STEP
        cx, cy = R * math.cos(math.radians(th)), -R + R * math.sin(math.radians(th))
        turn = th - 90
        _block(parts, cx, cy, ground, w, 560, floors, 'lanai', 'win', turn=turn, ends='cream')
        # the arcade under it: the ground floor set back, columns along the front
        ix, iy = cx + math.cos(math.radians(th)) * 60, cy + math.sin(math.radians(th)) * 60
        parts.append({'shape': 'box', 'size': [w, 440, ground], 'at': [ix, iy, 0], 'turn': [0, 0, turn], 'look': 'cream', 'faces': {'front': 'glass', 'top': None},
                      'material': 'stone', 'far': True})
        fx, fy = cx - math.cos(math.radians(th)) * 250, cy - math.sin(math.radians(th)) * 250
        for s in (-0.5, 0.0):
            tx, ty = math.cos(math.radians(turn)) * w * s, math.sin(math.radians(turn)) * w * s
            parts.append({'shape': 'cylinder', 'r': 26, 'h': ground, 'sides': 8, 'at': [fx + tx, fy + ty, 0], 'look': 'white', 'material': 'stone'})
    # the ends: blank walls of pierced block, and the pylon at the west end
    for end in (-1, 1):
        th = 90 + end * ((CRESCENT_N - 1) / 2.0 + 0.5) * CRESCENT_STEP
        ex, ey = R * math.cos(math.radians(th)), -R + R * math.sin(math.radians(th))
        parts.append({'shape': 'box', 'size': [30, 620, floors * FLOOR + ground], 'at': [ex, ey, 0], 'turn': [0, 0, th - 90], 'look': 'blocks', 'faces': {'top': 'concrete'},
                      'material': 'stone', 'far': True})
    th = 90 + ((CRESCENT_N - 1) / 2.0 + 1.6) * CRESCENT_STEP
    px, py = (R + 300) * math.cos(math.radians(th)), -R + (R + 300) * math.sin(math.radians(th)) - 400
    tall = 3000.0
    parts.append({'shape': 'box', 'size': [160, 700, tall], 'at': [px, py, 0], 'look': 'steel', 'faces': {'left': 'sign1_up', 'right': 'sign1_up', 'top': 'red'},
                  'material': 'metal', 'far': True})
    parts.append({'shape': 'cylinder', 'r': 60, 'h': 900, 'sides': 8, 'at': [px, py, tall], 'look': 'red', 'solid': False, 'far': True})
    _star(parts, px, py - 20, tall + 900, 380, 'yellow', rays=6, far=True)
    parts.append({'shape': 'ball', 'r': 60, 'sides': 8, 'rings': 4, 'at': [px, py - 20, tall + 840], 'look': 'neon', 'solid': False})
    # the folded canopy over the middle three segments' roof
    roof = ground + floors * FLOOR
    for k in range(6):
        x = -900 + 360 * k
        parts.append({'shape': 'slab', 'size': [380, 900, 14], 'at': [x, -40, roof + 220], 'turn': [0, (16 if k % 2 else -16), 0], 'look': 'white',
                      'faces': {'bottom': 'red'}, 'solid': False, 'far': True})
    for x in (-900, 900):
        for y in (-380, 300):
            parts.append({'shape': 'box', 'size': [24, 24, 230], 'at': [x, y, roof], 'look': 'grey', 'solid': False})
    return {'name': 'FOLabHotelCoralCrescent', 'looks': _looks(), 'parts': parts}


def _ramp(parts, x0, y0, x1, y1, z0, z1, wide, look_name):
    """A stair as a walkable slope from (x0, y0, z0) to (x1, y1, z1), `wide` across, its top edge meeting z1."""
    run = math.hypot(x1 - x0, y1 - y0)
    a = math.atan2(z1 - z0, run)
    yaw = math.degrees(math.atan2(y1 - y0, x1 - x0)) - 90
    L = math.hypot(run, z1 - z0)
    t = 16.0
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    mz = (z0 + z1) / 2 - t / math.cos(a) / 2
    parts.append({'shape': 'slab', 'size': [wide, L, t], 'at': [mx, my, mz], 'turn': [math.degrees(a), 0, yaw], 'look': look_name, 'material': 'stone'})


def tradewinds_lodge():
    """Two floors of rooms round three sides of a courtyard opening to the road (its front, -y): a walkway along the
    upper rooms on posts, a stair at each front corner, tiled roofs over everything, a pool gone green in the middle
    with its coping, the office at the front of the east wing under a butterfly roof, and by the road a boomerang
    sign with its name, MOTOR LODGE and NO VACANCY lit."""
    parts = []
    H = 2 * FLOOR
    back_y, arm_x, arm_len, d = 1100.0, 1300.0, 2000.0, 480.0
    # the back block and the two arms: rooms face the courtyard
    parts.append({'shape': 'box', 'size': [2 * arm_x + d, d, H], 'at': [0, back_y, 0], 'look': 'cream', 'faces': {'front': 'motel', 'top': None}, 'material': 'stone', 'far': True})
    for side in (-1, 1):
        parts.append({'shape': 'box', 'size': [d, arm_len, H], 'at': [side * arm_x, back_y - d / 2 - arm_len / 2, 0], 'look': 'cream',
                      'faces': {('right' if side < 0 else 'left'): 'motel', 'top': None}, 'material': 'stone', 'far': True})
    # the upper walkway round the courtyard, its rail, its posts
    walk, t = 200.0, 14.0
    parts.append({'shape': 'slab', 'size': [2 * arm_x - d, walk, t], 'at': [0, back_y - d / 2 - walk / 2, FLOOR - t], 'look': 'concrete', 'material': 'stone'})
    parts.append({'shape': 'box', 'size': [2 * arm_x - d, 8, 90], 'at': [0, back_y - d / 2 - walk + 4, FLOOR], 'look': 'grey', 'solid': True, 'material': 'metal'})
    for side in (-1, 1):
        x = side * (arm_x - d / 2 - walk / 2)
        parts.append({'shape': 'slab', 'size': [walk, arm_len - 340, t], 'at': [x, back_y - d / 2 - walk - (arm_len - 340) / 2, FLOOR - t], 'look': 'concrete', 'material': 'stone'})
        parts.append({'shape': 'box', 'size': [8, arm_len - 340, 90], 'at': [x - side * (walk / 2 - 4), back_y - d / 2 - walk - (arm_len - 340) / 2, FLOOR], 'look': 'grey',
                      'material': 'metal'})
        for k in range(6):
            yy = back_y - d / 2 - walk - k * (arm_len - 340) / 5.0
            parts.append({'shape': 'box', 'size': [16, 16, FLOOR - t], 'at': [x - side * (walk / 2 - 10), yy, 0], 'look': 'grey', 'solid': False})
        # the stair up at the front end of each walkway, coming down towards the road
        y_top = back_y - d / 2 - walk - (arm_len - 340)
        _ramp(parts, x, y_top - 600, x, y_top + 2, 0, FLOOR, walk - 20, 'concrete')
    for k in range(7):
        xx = -(arm_x - d / 2) + k * (2 * arm_x - d) / 6.0
        parts.append({'shape': 'box', 'size': [16, 16, FLOOR - t], 'at': [xx, back_y - d / 2 - walk + 10, 0], 'look': 'grey', 'solid': False})
    # tiled roofs, eaves out over the walkway
    import coastset                              # (its pitched roof, read only)
    coastset._gable(parts, 0, back_y - 80, H, d + 2 * walk + 120, 2 * arm_x + d + 120, 200, 'clay', yaw=90, far=True, solid=True)
    for side in (-1, 1):
        coastset._gable(parts, side * (arm_x - 80), back_y - d / 2 - arm_len / 2 - 60, H, d + 2 * walk + 80, arm_len - 120, 200, 'clay', far=True, solid=True)
    # the pool: coping round an oval of green water
    cx, cy, rx, ry = 0.0, -150.0, 760.0, 420.0
    parts.append({'shape': 'cylinder', 'r': 1.0, 'h': 4, 'sides': 20, 'at': [cx, cy, 46], 'scale': [rx, ry, 1], 'look': 'pool', 'cap_look': 'pool', 'solid': False})
    n = 20
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        x0, y0, x1, y1 = cx + rx * math.cos(a0), cy + ry * math.sin(a0), cx + rx * math.cos(a1), cy + ry * math.sin(a1)
        ln = math.hypot(x1 - x0, y1 - y0)
        parts.append({'shape': 'box', 'size': [ln + 14, 60, 60], 'at': [(x0 + x1) / 2, (y0 + y1) / 2, 0], 'turn': [0, 0, math.degrees(math.atan2(y1 - y0, x1 - x0))],
                      'look': 'terrazzo', 'material': 'stone'})
    parts.append({'shape': 'slab', 'size': [2 * arm_x - d - 40, 1500, 6], 'at': [0, -100, 0], 'look': 'terrazzo', 'solid': False})
    # the office at the front of the east wing, its butterfly roof
    ox, oy = arm_x, back_y - d / 2 - arm_len - 260
    parts.append({'shape': 'box', 'size': [d + 120, 520, 300], 'at': [ox, oy, 0], 'look': 'cream', 'faces': {'front': 'glass', 'left': 'glass', 'top': 'tar'}, 'material': 'stone', 'far': True})
    for s in (-1, 1):
        parts.append({'shape': 'slab', 'size': [(d + 300) / 2, 760, 14], 'at': [ox + s * (d + 300) / 4, oy, 330], 'turn': [0, s * 10, 0], 'look': 'white', 'faces': {'bottom': 'door'},
                      'solid': False, 'far': True})
    # the boomerang sign by the road
    sx, sy = -arm_x - 200, back_y - d / 2 - arm_len - 700
    parts.append({'shape': 'cylinder', 'r': 34, 'h': 1400, 'sides': 8, 'at': [sx, sy, 0], 'look': 'red', 'material': 'metal', 'far': True})
    parts.append({'shape': 'box', 'size': [1100, 30, 260], 'at': [sx + 150, sy, 1400], 'turn': [0, -14, 0], 'look': 'steel', 'faces': {'front': 'sign2', 'back': 'sign2'},
                  'solid': False, 'far': True})
    parts.append({'shape': 'box', 'size': [1000, 30, 200], 'at': [sx + 100, sy, 1150], 'turn': [0, 12, 0], 'look': 'steel', 'faces': {'front': 'sign3', 'back': 'sign3'},
                  'solid': False, 'far': True})
    parts.append({'shape': 'box', 'size': [700, 24, 140], 'at': [sx, sy, 700], 'look': 'grey', 'faces': {'front': 'sign4', 'back': 'sign4'}, 'solid': False})
    _star(parts, sx + 700, sy - 20, 1780, 160, 'yellow', rays=4)
    return {'name': 'FOLabHotelTradewinds', 'looks': _looks(), 'parts': parts}


# ---------- landmarks ----------

WHEEL_R = 1100.0
WHEEL_HUB = 1300.0


def ferris_wheel():
    """A Ferris wheel facing -y on two A-frames: twin rims joined by ties, twelve spokes to each, gondolas hanging
    from every other joint (two gone, one fallen on the platform), a few bulbs still lit; a platform and a ticket
    booth under it, the name on a board across the way in."""
    parts = []
    R, hz, n = WHEEL_R, WHEEL_HUB, 24
    pts = [(R * math.cos(2 * math.pi * k / n), R * math.sin(2 * math.pi * k / n)) for k in range(n)]
    for y in (-110, 110):
        for k in range(n):
            (x0, z0), (x1, z1) = pts[k], pts[(k + 1) % n]
            rim = limb((x0, y, hz + z0), (x1, y, hz + z1), 14, 14, 'red', sides=5)
            rim['far'] = True
            parts.append(rim)
        for k in range(0, n, 2):
            x0, z0 = pts[k]
            parts.append(limb((0, y, hz), (x0, y, hz + z0), 9, 7, 'steel', sides=4))
    for k in range(0, n, 2):
        x0, z0 = pts[k]
        parts.append(limb((x0, -110, hz + z0), (x0, 110, hz + z0), 7, 7, 'steel', sides=4))
    gone = {3, 8}
    for g, k in enumerate(range(1, n, 2)):
        if g in gone:
            continue
        x0, z0 = pts[k]
        parts.append(limb((x0, 0, hz + z0 - 10), (x0, 0, hz + z0 - 70), 5, 5, 'grey', sides=4))
        lk = 'red' if g % 2 else 'yellow'
        parts.append({'shape': 'box', 'size': [150, 120, 120], 'at': [x0, 0, hz + z0 - 200], 'look': lk, 'faces': {'top': 'grey'}, 'solid': False})
        parts.append({'shape': 'cone', 'r': 110, 'h': 60, 'sides': 6, 'at': [x0, 0, hz + z0 - 75], 'look': 'steel', 'solid': False})
    for k in (0, 5, 9, 14, 20):                  # the bulbs still burning
        x0, z0 = pts[k]
        parts.append({'shape': 'ball', 'r': 18, 'sides': 5, 'rings': 3, 'at': [x0 * 1.02, -130, hz + z0 * 1.02 - 18], 'look': 'bulb', 'solid': False})
    # hub and axle
    parts.append({'shape': 'cylinder', 'r': 90, 'h': 420, 'sides': 10, 'at': [0, 210, hz], 'turn': [90, 0, 0], 'look': 'grey', 'material': 'metal', 'far': True})
    # the A-frames
    for y, sy in ((-210, -1), (210, 1)):
        for x in (-760, 760):
            leg = limb((x, y + sy * 260, 0), (0, y, hz), 30, 24, 'red', sides=6, solid=True)
            leg['far'] = True
            parts.append(leg)
        parts.append(limb((-470, y + sy * 160, 500), (470, y + sy * 160, 500), 12, 12, 'red', sides=5))
    # the platform, booth, a fallen gondola on it
    parts.append({'shape': 'slab', 'size': [2200, 1100, 40], 'at': [0, -100, 0], 'look': 'concrete', 'material': 'stone'})
    parts.append({'shape': 'box', 'size': [300, 260, 260], 'at': [-1250, -700, 0], 'look': 'cream', 'faces': {'front': 'glass', 'top': 'tar'}, 'material': 'stone'})
    parts.append({'shape': 'box', 'size': [320, 20, 90], 'at': [-1250, -840, 260], 'look': 'steel', 'faces': {'front': 'sign6'}, 'solid': False})
    parts.append({'shape': 'box', 'size': [150, 120, 120], 'at': [620, -480, 40], 'turn': [8, 22, 35], 'look': 'yellow', 'material': 'metal'})
    for x in (-700, 700):
        parts.append({'shape': 'box', 'size': [30, 30, 520], 'at': [x, -820, 0], 'look': 'red', 'material': 'metal'})
    parts.append({'shape': 'box', 'size': [1500, 20, 220], 'at': [0, -820, 520], 'look': 'steel', 'faces': {'front': 'sign5', 'back': 'sign5'}, 'solid': False, 'far': True})
    return {'name': 'FOLabParkSkyWheel', 'looks': _looks(), 'parts': parts}


TANK_AT = 1700.0


def water_tower():
    """The city's water tower: a tank on four splayed legs braced in X, the city's name painted round it, a pointed
    roof and finial, a catwalk round its foot, a ladder up the front leg, the riser down the middle."""
    parts = []
    z, r = TANK_AT, 430.0
    parts.append({'shape': 'cylinder', 'r': r, 'h': 560, 'sides': 16, 'at': [0, 0, z], 'look': 'tank', 'cap_look': 'steel', 'material': 'metal', 'far': True})
    parts.append({'shape': 'cone', 'r': r + 20, 'h': 200, 'sides': 16, 'at': [0, 0, z + 560], 'look': 'steel', 'far': True})
    parts.append({'shape': 'ball', 'r': 26, 'sides': 6, 'rings': 3, 'at': [0, 0, z + 750], 'look': 'grey', 'solid': False})
    parts.append({'shape': 'cylinder', 'r': 0.0, 'r2': r, 'h': 220, 'sides': 16, 'at': [0, 0, z - 220], 'look': 'steel', 'cap_look': None, 'material': 'metal', 'far': True})
    parts.append({'shape': 'cylinder', 'r': 560, 'h': 12, 'sides': 16, 'at': [0, 0, z - 12], 'look': 'grey', 'material': 'metal'})
    for k in range(16):
        a = 2 * math.pi * (k + 0.5) / 16
        parts.append({'shape': 'box', 'size': [225, 6, 80], 'at': [math.cos(a) * 552, math.sin(a) * 552, z], 'turn': [0, 0, math.degrees(a) + 90], 'look': 'grey', 'solid': False})
    foot, head = 560.0, 300.0
    corners = [(sx, sy) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    for k, (sx, sy) in enumerate(corners):
        leg = limb((sx * foot, sy * foot, 0), (sx * head, sy * head, z - 12), 26, 22, 'grey', sides=6, solid=True)
        leg['far'] = True
        parts.append(leg)
        parts.append({'shape': 'box', 'size': [140, 140, 60], 'at': [sx * foot, sy * foot, 0], 'look': 'concrete', 'material': 'stone'})
        nx, ny = corners[(k + 1) % 4]
        for z0, z1 in ((80, z * 0.5), (z * 0.5, z - 40)):
            f0, f1 = z0 / z, z1 / z
            ax, ay = sx * (foot + (head - foot) * f0), sy * (foot + (head - foot) * f0)
            bx, by = nx * (foot + (head - foot) * f1), ny * (foot + (head - foot) * f1)
            cx_, cy_ = sx * (foot + (head - foot) * f1), sy * (foot + (head - foot) * f1)
            dx_, dy_ = nx * (foot + (head - foot) * f0), ny * (foot + (head - foot) * f0)
            parts.append(limb((ax, ay, z0), (bx, by, z1), 6, 6, 'grey', sides=3))
            parts.append(limb((dx_, dy_, z0), (cx_, cy_, z1), 6, 6, 'grey', sides=3))
        parts.append(limb((sx * (foot + (head - foot) * 0.5), sy * (foot + (head - foot) * 0.5), z * 0.5),
                          (nx * (foot + (head - foot) * 0.5), ny * (foot + (head - foot) * 0.5), z * 0.5), 8, 8, 'grey', sides=4))
    parts.append({'shape': 'cylinder', 'r': 60, 'h': z - 220, 'sides': 8, 'look': 'grey', 'material': 'metal'})
    # the ladder up the front, to the catwalk
    for x in (-24, 24):
        parts.append({'shape': 'box', 'size': [6, 6, z], 'at': [x, -foot + 60, 0], 'turn': [-math.degrees(math.atan2(foot - head, z)) * 0.0, 0, 0], 'look': 'grey', 'solid': False})
    for k in range(1, int(z / 120)):
        parts.append({'shape': 'box', 'size': [54, 5, 5], 'at': [0, -foot + 60, k * 120], 'look': 'grey', 'solid': False})
    return {'name': 'FOLabParkWaterTower', 'looks': _looks(), 'parts': parts}


def band_shell():
    """A band shell as Waikiki's: five arches of render nested one inside the next, each smaller one set back under the
    one before and overlapping it, the step between them closed by a ring facing the stage, so the whole is one solid
    stepped roof open only at the front; closed behind; the stage's front of concrete with steps up each side; rows of
    benches in front facing the stage, an aisle up the middle."""
    parts = []
    rings, n = 5, 14
    base = 110.0
    deep, step, inset = 300.0, 220.0, 150.0      # (each arch's depth, how far back the next one is, how much smaller)
    for k in range(rings):
        R, y = 1500.0 - inset * k, 180.0 + step * k
        seg = 2 * R * math.sin(math.pi / n / 2) + 24
        for j in range(n):
            th = 180.0 * (j + 0.5) / n
            ct, st = math.cos(math.radians(th)), math.sin(math.radians(th))
            parts.append({'shape': 'slab', 'size': [seg, deep, 30], 'at': [R * ct, y, base + R * st], 'turn': [0, 90 - th, 0], 'look': 'white', 'material': 'stone',
                          'solid': j not in (0, n - 1), 'far': True})
            if k < rings - 1:                       # (the step down to the next arch: a ring at this one's back, facing the stage)
                r0 = R - inset - 10
                parts.append({'shape': 'box', 'size': [seg, 30, inset + 40], 'at': [r0 * ct, y + deep / 2 - 15, base + r0 * st], 'turn': [0, 90 - th, 0],
                              'look': 'white', 'material': 'stone', 'solid': False, 'far': True})
    # the back, closed in steps under the smallest arch
    Rb, yb = 1500.0 - 150.0 * (rings - 1), 180.0 + 220.0 * (rings - 1) + 130
    strips = 10
    for j in range(strips):
        x0 = -Rb + 2 * Rb * j / strips
        xm = x0 + Rb / strips
        hgt = math.sqrt(max(0.0, Rb * Rb - xm * xm)) + 40
        parts.append({'shape': 'box', 'size': [2 * Rb / strips + 4, 30, hgt], 'at': [xm, yb, base], 'look': 'white', 'material': 'stone', 'far': True})
    # the stage
    parts.append({'shape': 'box', 'size': [3200, 1500, base], 'at': [0, 450, 0], 'look': 'concrete', 'faces': {'top': 'wood'}, 'material': 'stone', 'far': True})
    for sx in (-1, 1):
        _ramp(parts, sx * 1400, -700, sx * 1400, -300 + 2, 0, base, 300, 'concrete')
    # the benches, facing the stage (it is towards +y: their backs are on the -y side)
    for row in range(7):
        y = -900 - 260 * row
        for x in (-1000, 1000):
            parts.append({'shape': 'box', 'size': [1500, 90, 44], 'at': [x, y, 0], 'look': 'wood', 'material': 'wood'})
            parts.append({'shape': 'box', 'size': [1500, 20, 60], 'at': [x, y - 50, 44], 'look': 'wood', 'solid': False})
    return {'name': 'FOLabParkBandShell', 'looks': _looks(), 'parts': parts}


def cd_siren():
    """A civil-defence siren on a wooden pole: a squat yellow motor housing with two horns flaring out either way,
    a control box half way up, the fallout-shelter sign at eye height."""
    parts = [{'shape': 'cylinder', 'r': 18, 'r2': 13, 'h': 1050, 'sides': 8, 'look': 'wood', 'material': 'wood', 'far': True},
             {'shape': 'box', 'size': [260, 14, 14], 'at': [0, 0, 960], 'look': 'wood', 'solid': False},
             {'shape': 'cylinder', 'r': 70, 'h': 120, 'sides': 10, 'at': [0, 0, 1050], 'look': 'yellow', 'material': 'metal', 'far': True},
             {'shape': 'cone', 'r': 78, 'h': 50, 'sides': 10, 'at': [0, 0, 1170], 'look': 'yellow', 'solid': False},
             {'shape': 'box', 'size': [110, 60, 150], 'at': [0, -30, 420], 'look': 'grey', 'material': 'metal'},
             {'shape': 'box', 'size': [180, 8, 180], 'at': [0, -22, 150], 'look': 'grey', 'faces': {'front': 'shelter'}, 'solid': False}]
    for side in (-1, 1):
        parts.append({'shape': 'cylinder', 'r': 34, 'r2': 76, 'h': 150, 'sides': 10, 'at': [side * 50, 0, 1110], 'turn': [0, side * 90, 0], 'look': 'yellow',
                      'caps': False, 'under': True, 'under_look': 'grey', 'solid': False, 'far': True})
    return {'name': 'FOLabParkSiren', 'looks': _looks(), 'parts': parts}


def giant_tiki():
    """A roadside giant: a carved tiki ten metres tall on a plinth of lava rock, its face to the road, a crest of
    boards on its head, the attraction's name on a board at its feet."""
    parts = [{'shape': 'box', 'size': [600, 600, 140], 'look': 'lava', 'faces': {'top': 'concrete'}, 'material': 'stone', 'far': True},
             {'shape': 'box', 'size': [300, 260, 300], 'at': [0, 0, 140], 'look': 'wood', 'faces': {'front': 'tiki_body', 'back': 'tiki_body'}, 'material': 'wood', 'far': True},
             {'shape': 'box', 'size': [400, 340, 420], 'at': [0, -20, 440], 'look': 'wood', 'faces': {'front': 'tiki_head', 'back': 'tiki_head'}, 'material': 'wood', 'far': True},
             {'shape': 'box', 'size': [440, 380, 40], 'at': [0, -20, 520], 'look': 'wood', 'solid': False},
             {'shape': 'box', 'size': [90, 70, 120], 'at': [0, -215, 640], 'look': 'wood', 'faces': {'front': 'tiki_nose'}, 'solid': False},
             {'shape': 'box', 'size': [380, 330, 40], 'at': [0, -20, 860], 'look': 'wood', 'material': 'wood', 'far': True}]
    for side in (-1, 1):                         # arms held to the belly
        parts.append({'shape': 'box', 'size': [60, 120, 240], 'at': [side * 170, -40, 180], 'turn': [0, side * 8, 0], 'look': 'wood', 'solid': False})
    for k in range(5):
        a = -40 + 20 * k
        parts.append({'shape': 'box', 'size': [60, 30, 300], 'at': [math.sin(math.radians(a)) * 120, -20, 890], 'turn': [0, a, 0], 'look': 'door', 'solid': False, 'far': True})
    parts.append({'shape': 'box', 'size': [520, 20, 120], 'at': [0, -380, 40], 'look': 'steel', 'faces': {'front': 'sign7'}, 'solid': False})
    for x in (-220, 220):
        parts.append({'shape': 'box', 'size': [16, 16, 120], 'at': [x, -380, 0], 'look': 'grey', 'solid': False})
    return {'name': 'FOLabParkGiantTiki', 'looks': _looks(), 'parts': parts}


HOTELS = {
    'lani_moku': ('Lani Moku', lani_moku),
    'coral_crescent': ('Coral Crescent', coral_crescent),
    'tradewinds_lodge': ('Tradewinds Motor Lodge', tradewinds_lodge),
}
PIECES = {
    'sky_wheel': ('Ferris wheel', ferris_wheel),
    'water_tower': ('Water tower', water_tower),
    'band_shell': ('Band shell', band_shell),
    'cd_siren': ('Civil-defence siren', cd_siren),
    'giant_tiki': ('Giant tiki', giant_tiki),
}
waikikiset.LIGHTS.update({
    'lani_moku': [('NVLightNeonRed', 0, -30, 2 * FLOOR + 18 * FLOOR + 1380), ('ExtLightWarm02', 0, -2500, 380)],
    'coral_crescent': [('ExtLightWarm02', 0, -300, 280)],
    'tradewinds_lodge': [('NVLightNeonRed', -1500, -2080, 760), ('ExtLightWarm02', 1300, -1500, 300)],
    'sky_wheel': [('ExtLightWarm02', -1250, -800, 300), ('ExtLightWarm02', 0, -130, WHEEL_HUB)],
    'band_shell': [('ExtLightWarm02', 0, 300, 900)],
})
for _k, (_label, _fn) in HOTELS.items():
    modelsets.PIECES.setdefault(_k, {'label': _label, 'set': 'resort', 'file': _k, 'describe': _fn, 'edid': _fn()['name']})
for _k, (_label, _fn) in PIECES.items():
    modelsets.PIECES.setdefault(_k, {'label': _label, 'set': 'resort', 'file': _k, 'describe': _fn, 'edid': _fn()['name']})
