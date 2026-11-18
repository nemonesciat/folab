"""Waikiki's own historic buildings, as FOLab's own landmarks, each where the map has the real one (the game's Vegas
buildings stood in for them before):

- The Royal Hawaiian (1927, "the Pink Palace of the Pacific"): a long pink Spanish-Moorish hotel of six floors, wings
  coming forward to the sea round a lawn of coconut palms, a tower over the middle with an open belvedere of arches
  under a little dome, an arcaded loggia along the garden, tiled hip roofs, an arched carriage porch on the town side.
- The Moana (1901, "the First Lady of Waikiki"): a white colonial hotel, a five-floor middle block with verandas up its
  sea side, a two-floor portico of columns on the town side under a balustraded balcony, lower wings round the
  Banyan Court, a great banyan in it.
- The Waikiki Natatorium War Memorial (1927): a triumphal arch with colonnaded wings on the park side, and behind them
  out over the sea a saltwater pool walled round down to the sea bed, bleachers down one side: the pool long since green.
  Stood with its origin on the shore line, the pool to the sea.
- Battery Randolph (1911, the Army Museum at Fort DeRussy): a long low casemate of reinforced concrete, steel doors in
  its face, two great guns on its roof behind ring walls, the earth banked against its sea side in one slope, a stair up.

All in `texwear`'s worn paint, two centuries after the bombs: `period_sheet` (a historic face, bay by bay: arched or
sash windows, louvred shutters closed or open or gone, boarded, the paint peeling to the coat under it), `arch_board`
(a board of round arches, see-through where the arches are open), `balustrade` (balusters and rails, see-through
between), `fluted` (a painted column's flutes). Names on signs are the real places'.

Frame as every modelsets piece: the foot's middle at the origin, z up, front towards -y: the SEA SIDE for all four
(the hotels' famous faces, the pool, the guns), 70 units a metre, FLOOR 256. Registered into modelsets at import
(set 'resort', as The Kilauea, so what keeps off the resort's records keeps off these); `landmarks.SETS` stands them."""
import math
import random

import modelsets
import resortset
import texpaint as tp
import texwear as tw
import waikikiset
from modelsets import FLOOR, limb, look
from texwear import Field, Picture, Wear, grade, mix, mul, smooth

PINK = (226, 150, 150)          # the Royal Hawaiian's pink, before two centuries of sun
PINK_UNDER = (214, 196, 170)
MOANA_WHITE = (236, 232, 218)
MOANA_UNDER = (206, 200, 180)
STONE = (204, 196, 174)         # the Natatorium's cast stone
BATTERY = (150, 148, 138)       # Randolph's concrete
SHUTTER_GREEN = (82, 108, 80)
SHUTTER_BROWN = (118, 84, 54)


# ---------- its own pictures ----------

SHEET_STATES = (('louvred', 6), ('glass', 5), ('open', 3), ('gone', 2), ('boarded', 2), ('hanging', 1))


def period_sheet(wall=PINK, under=PINK_UNDER, trim=None, kind='arched', bays=8, floors=8, size=1024, seed=900, shutter=SHUTTER_GREEN, grime=0.75):
    """bays x floors of a historic face on one picture, each bay its own. kind 'arched': a round-headed window in a
    raised surround, a sill; 'sash': a tall window of small panes between two shutters, a lintel over it, a string
    course at each floor; 'bunker': a steel door in a concrete bay, its lintel's shadow. Each bay picks a state (its
    louvred shutters closed, glass whole, shutters open on the dark room, the glass gone, boarded, a shutter hanging
    off one hinge); paint peels to the coat under it and the render; rain has run down from every sill."""
    S = size
    cw, ch = S / float(bays), S / float(floors)
    rnd = random.Random(seed)
    picks = [k for k, n in SHEET_STATES for _ in range(n)]
    state = [[rnd.choice(picks) for _ in range(bays)] for _ in range(floors)]
    pane = [[rnd.uniform(0.85, 1.15) for _ in range(bays)] for _ in range(floors)]
    lost = [[{rnd.randrange(12) for _ in range(rnd.randrange(0, 4))} for _ in range(bays)] for _ in range(floors)]
    which = [[rnd.random() < 0.5 for _ in range(bays)] for _ in range(floors)]
    trim = trim or mix(wall, (240, 236, 224), 0.5)
    sill = 0.86 if kind != 'bunker' else 0.99
    irons = [(int(i * cw + cw * 0.5), int(j * ch + ch * (0.12 if kind == 'bunker' else sill))) for j in range(floors) for i in range(bays) if rnd.random() < 0.5]
    wr = Wear(S, S, seed, grime=grime, rain=1.1, ledges=[(j + sill) / floors for j in range(floors)] + [j / float(floors) for j in range(floors)], irons=irons, bleach=0.2)
    peel = Field(S, S, seed + 10, cells=8, octaves=4, fall=0.55)
    glassn = Field(S, S, seed + 11, cells=32, octaves=2)
    crk = tw.cracks(S, S, seed + 12, count=10, long=0.25, width=1.2)
    c = Picture(S, S, gloss=18)
    top, old, tr = tp._faded(wall, 0.12), tp._faded(under, 0.2), tp._faded(trim, 0.12)
    sh = tp._faded(shutter, 0.25)
    for y in range(S):
        j = int(y / ch)
        v = (y % ch) / ch
        for x in range(S):
            i = int(x / cw)
            u = (x % cw) / cw
            p = y * S + x
            f, m = wr.fine.v[p], wr.mid.v[p]
            st = state[j][i]
            g, depth = 18, 0.0
            col, h = mul(top, 0.93 + 0.1 * m), 0.5
            pv = peel.v[p]
            if pv > 0.7:
                col, h = (mul(old, 0.88), 0.47) if pv < 0.77 else (mul(tw.RENDER, 0.8 + 0.2 * f), 0.42)
            # where the opening is, in the bay: (gu, gv) 0-1 across it, None outside
            gu = gv = None
            if kind == 'arched':
                cx, cy, r = 0.5, 0.42, 0.19
                d = math.hypot(u - cx, v - cy)
                if (abs(u - cx) < r and cy <= v < sill) or (v < cy and d < r):
                    gu, gv = (u - (cx - r)) / (2 * r), (v - (cy - r)) / (sill - cy + r)
                elif (abs(u - cx) < r + 0.045 and cy <= v < sill) or (v < cy and d < r + 0.045):
                    col, h, depth = mul(tr, 0.92 + 0.1 * m), 0.62, 0.1          # the raised surround
                    if v < cy and abs(u - cx) < 0.025:
                        col, h = mul(tr, 1.04), 0.68                            # its keystone
                if sill <= v < sill + 0.04 and abs(u - cx) < r + 0.07:
                    col, h = mul(tr, 0.9 + 0.1 * f), 0.7                        # the sill
            elif kind == 'sash':
                if v < 0.045:
                    col, h = mul(tr, 0.9 + 0.08 * m), 0.66                      # the string course
                if 0.34 < u < 0.66 and 0.22 <= v < 0.82:
                    gu, gv = (u - 0.34) / 0.32, (v - 0.22) / 0.6
                elif 0.3 < u < 0.7 and 0.17 <= v < 0.22:
                    col, h = mul(tr, 0.95), 0.66                                # the lintel
                elif 0.31 < u < 0.69 and 0.82 <= v < 0.86:
                    col, h = mul(tr, 0.9 + 0.1 * f), 0.7                        # the sill
                elif (0.2 < u <= 0.34 or 0.66 <= u < 0.8) and 0.22 <= v < 0.82 and st in ('glass', 'open', 'hanging'):
                    left = u < 0.5                                              # a shutter opened back to the wall
                    if not (st == 'hanging' and left != which[j][i]) and not (st == 'open' and which[j][i] and left):
                        k = int(((v - 0.22) / 0.6) * 18)
                        col = mul(sh, 0.7 + 0.35 * math.sin((((v - 0.22) / 0.6) * 18 % 1) * math.pi))
                        h, g = 0.6, 14
                        if k in lost[j][i]:
                            col, h = mul(tw.GRIME, 0.7), 0.4
                        if pv > 0.66:
                            col = mix(col, tw.SILVER_WOOD, 0.6)
            else:                                                               # a bunker's bay
                if 0.24 < u < 0.76 and 0.42 <= v:
                    gu, gv = (u - 0.24) / 0.52, (v - 0.42) / 0.58
                elif 0.2 < u < 0.8 and 0.36 <= v < 0.42:
                    col, h, depth = mul(col, 0.62), 0.55, 0.6                   # the lintel's shadow
                if abs(u - 0.02) < 0.02 or abs(u - 0.98) < 0.02:
                    col, h, depth = mul(col, 0.8), 0.45, 0.4                    # the joint between pours
            if gu is not None:
                depth = 0.7
                if kind == 'bunker':
                    if st in ('gone', 'open'):
                        col, h, g = mul((20, 19, 17), 0.8 + 0.4 * f), 0.1, 0     # the door gone, the dark inside
                    else:
                        col = mix(mul((92, 96, 84), 0.8 + 0.2 * m), tw.RUST, 0.35 + 0.5 * smooth(0.4, 0.8, wr.big.v[p]))
                        h, g = 0.5, 30
                        if gu < 0.04 or gu > 0.96 or gv < 0.03 or abs(gv - 0.5) < 0.012:
                            col, h = mul(col, 0.6), 0.42                         # the door's frame, its rail
                        if (abs(gu - 0.1) < 0.02 or abs(gu - 0.9) < 0.02) and (gv * 20) % 1 < 0.3:
                            col, h, g = mul(tw.RUST_LIGHT, 0.9), 0.7, 40         # rivets
                        if st == 'boarded' and 0.3 < gu < 0.7 and 0.2 < gv < 0.32:
                            col, h = mul((210, 200, 170), 0.8), 0.55             # a stencilled plate
                elif st in ('glass', 'hanging') or (kind == 'sash' and st == 'open'):
                    bars = (gu * 3) % 1 < 0.06 or (gv * 4) % 1 < 0.05 or gu < 0.04 or gu > 0.96
                    if bars:
                        col, h, g = mul((210, 204, 188), 0.75 + 0.2 * f), 0.55, 30      # the glazing bars
                    else:
                        glare = 0.8 + 0.5 * max(0.0, 1 - abs((gu - gv * 0.4) - 0.3) * 5)
                        col = mul(tp.GLASS_DARK, glare * pane[j][i] * (0.85 + 0.3 * glassn.v[p]))
                        col = mix(col, (150, 160, 158), 0.28 * (1 - gv) ** 2)
                        h, g = 0.3, 140
                        if (gu * 3 + gv * 4 + i + j) % 7 < 0.6 and st == 'hanging':
                            col, h, g = mul((18, 18, 17), 1.0), 0.1, 0       # a pane gone
                elif st == 'louvred':
                    k = int(gv * 22)
                    col = mul(sh, 0.62 + 0.4 * math.sin((gv * 22 % 1) * math.pi))
                    h, g = 0.35 + 0.3 * math.sin((gv * 22 % 1) * math.pi), 12
                    if k % 12 in lost[j][i]:
                        col, h = mul((20, 19, 17), 1.0), 0.1                     # a slat gone
                    if abs(gu - 0.5) < 0.02:
                        col, h = mul(sh, 0.5), 0.3
                    if pv > 0.64:
                        col = mix(col, tw.SILVER_WOOD, 0.55)                     # its paint gone to grey wood
                elif st == 'boarded':
                    k = int(gu * 4)
                    e = gu * 4 - k
                    col = mul(mix(tw.SILVER_WOOD, (150, 128, 96), (k * 0.37) % 1), 0.75 + 0.3 * wr.runs.v[p])
                    h, g = 0.6, 10
                    if e < 0.05 or e > 0.95:
                        col, h = mul(col, 0.4), 0.3
                else:                                                            # the dark room, a curtain's ghost
                    col, h, g = mul((22, 20, 18), 0.8 + 0.4 * f), 0.1, 0
                    if st == 'open' and 0.6 < gu < 0.8:
                        col = mix(col, (120, 104, 80), 0.5 * (0.5 + 0.5 * math.sin(gu * 60)))
            if crk[p] > 0.05 and gu is None:
                col, h, depth = mix(col, mul(tw.GRIME, 0.6), crk[p]), 0.45, 1.0
            c.rgb[p], c.ht[p], c.gloss[p] = grade(wr.on(x, y, col, depth)), h, g
    return c


def arch_board(n, W, H, pier=0.0, colour=PINK, trim=None, w=1024, h=256, seed=940):
    """A board W x H units with n round arches springing from its foot (the piers stand under it, `pier` wide), the
    arches see-through: a moulded band round each, a keystone, the paint peeled. Fitted once over the board's face."""
    c = Picture(w, h, clear=colour, gloss=18)
    wr = Wear(w, h, seed, grime=1.0, rain=1.0, ledges=(0.0,), bleach=0.15)
    peel = Field(w, h, seed + 1, cells=6, octaves=4)
    bay = W / float(n)
    r = (bay - pier) / 2.0
    band = min(14.0, r * 0.12)
    trim = tp._faded(trim or mix(colour, (240, 236, 224), 0.5), 0.12)
    top = tp._faded(colour, 0.12)
    for y in range(h):
        Y = (y + 0.5) / h * H
        for x in range(w):
            X = (x + 0.5) / w * W
            k = min(n - 1, int(X / bay))
            lx = X - (k + 0.5) * bay
            d = math.hypot(lx, H - Y)
            p = y * w + x
            if d < r:
                c.a[p] = 0.0
                continue
            col, ht, depth = mul(top, 0.93 + 0.1 * wr.mid.v[p]), 0.5, 0.0
            if d < r + band:
                col, ht, depth = mul(trim, 0.9 + 0.12 * wr.fine.v[p]), 0.62 + 0.1 * math.sin((d - r) / band * math.pi), 0.2
            elif d < r + band * 2.2 and abs(lx) < band * 0.9:
                col, ht = mul(trim, 1.02), 0.7                                   # the keystone
            if Y < H * 0.1:
                col, ht = mul(trim, 0.9), 0.66                                   # a band along its top
            if peel.v[p] > 0.74:
                col = mul(tw.RENDER, 0.8 + 0.2 * wr.fine.v[p])
            c.a[p] = 1.0
            c.rgb[p], c.ht[p] = grade(wr.on(x, y, col, depth)), ht
    return c


def balustrade(size=256, colour=MOANA_WHITE, seed=960, posts=6, globes=False):
    """Balusters between a top rail and a bottom one, see-through between; one or two balusters gone, the paint
    flaking to grey wood or render, rust where a pin shows."""
    c = Picture(size, size, clear=colour, gloss=20)
    wr = Wear(size, size, seed, grime=1.0, rain=0.8, ledges=(0.12,))
    rnd = random.Random(seed)
    gone = {rnd.randrange(posts)}
    peel = Field(size, size, seed + 1, cells=6, octaves=4)
    top = tp._faded(colour, 0.12)
    for y in range(size):
        v = y / float(size)
        for x in range(size):
            u = x / float(size)
            p = y * size + x
            k = int(u * posts)
            lu = u * posts - k - 0.5
            solid = v < 0.12 or v > 0.9
            if not solid and k not in gone:
                t = (v - 0.12) / 0.78
                half = 0.12 + 0.12 * math.sin(math.pi * min(1.0, t * 1.3)) ** 2 - (0.05 if 0.1 < t < 0.16 or 0.86 < t < 0.92 else 0)
                solid = abs(lu) < half
            if not solid:
                c.a[p] = 0.0
                continue
            col = mul(top, 0.9 + 0.12 * wr.mid.v[p] - (0.12 if v < 0.12 and v > 0.1 else 0))
            if peel.v[p] > 0.7:
                col = mul(tw.SILVER_WOOD, 0.85 + 0.2 * wr.fine.v[p])
            c.a[p] = 1.0
            c.rgb[p], c.ht[p] = grade(wr.on(x, y, col, 0.2)), 0.6
    return c


def fluted(colour=MOANA_WHITE, size=128, seed=980, flutes=8):
    """A painted column's shaft: flutes running up it, the paint gone in islands to grey render, grime in the flutes."""
    c = Picture(size, size, gloss=24)
    wr = Wear(size, size, seed, grime=0.8, rain=0.9, ledges=(0.0,))
    peel = Field(size, size, seed + 1, cells=4, octaves=4)
    top = tp._faded(colour, 0.12)
    for y in range(size):
        for x in range(size):
            p = y * size + x
            s = math.cos((x / float(size) * flutes) % 1.0 * 2 * math.pi)
            col = mul(top, 0.78 + 0.22 * (0.5 + 0.5 * s))
            if peel.v[p] > 0.72:
                col = mul(tw.RENDER, 0.8 + 0.2 * wr.fine.v[p])
            c.rgb[p], c.ht[p] = grade(wr.on(x, y, col, 0.5 - 0.5 * s)), 0.5 + 0.2 * s
    return c


def _lawn(size=512, seed=990):
    """The hotel lawn gone to a hayfield: tall grass laid by the wind, dry in patches, bare earth showing."""
    c = tp.ground_grass(size=size, seed=seed)
    dry = Field(size, size, seed + 1, cells=5, octaves=4)
    for p in range(size * size):
        col = c.rgb[p]
        if dry.v[p] > 0.6:
            col = mix(col, (150, 136, 84), smooth(0.6, 0.85, dry.v[p]) * 0.8)
        if dry.v[p] > 0.86:
            col = mix(col, (112, 94, 70), 0.6)
        c.rgb[p] = grade(col, sat=0.7)
    p2 = Picture(size, size)
    p2.rgb, p2.ht = c.rgb, c.ht
    return p2


def _letters(words, wall, ink, seed):
    return lambda: tw.painted_letters(words, wall=wall, ink=ink, w=1024, h=128, seed=seed)


# what each picture is, by the boards that use it: (n, W, H, pier)
RH_LOGGIA = (9, 2400, 150, 60)
RH_PORCH = (3, 1000, 170, 80)
RH_PORCH_SIDE = (2, 600, 170, 80)
RH_BELVEDERE = (3, 640, 230, 60)
NAT_ARCH = (1, 420, 600, 0)
NAT_WING = (3, 1100, 190, 120)

modelsets.TEXTURES.update({
    'hist/rh_wall': lambda: period_sheet(PINK, PINK_UNDER, kind='arched', bays=8, floors=8, size=1024, seed=900, shutter=SHUTTER_GREEN),
    'hist/rh_plain': lambda: tw.render(PINK, under=PINK_UNDER, size=512, seed=901, peel=0.35),
    'hist/rh_tiles': lambda: tw.clay_tiles(size=512, seed=902, colour=(176, 92, 64)),
    'hist/rh_loggia': lambda: arch_board(*RH_LOGGIA, colour=PINK, seed=903),
    'hist/rh_porch': lambda: arch_board(*RH_PORCH, colour=PINK, seed=904),
    'hist/rh_porch_side': lambda: arch_board(*RH_PORCH_SIDE, colour=PINK, w=512, seed=905),
    'hist/rh_belvedere': lambda: arch_board(*RH_BELVEDERE, colour=PINK, w=512, seed=906),
    'hist/rh_sign': _letters('ROYAL HAWAIIAN', PINK, (120, 40, 44), 907),
    'hist/mo_wall': lambda: period_sheet(MOANA_WHITE, MOANA_UNDER, trim=(250, 248, 238), kind='sash', bays=8, floors=8, size=1024, seed=920, shutter=SHUTTER_GREEN, grime=0.5),
    'hist/mo_plain': lambda: tw.render(MOANA_WHITE, under=MOANA_UNDER, size=512, seed=921, peel=0.3),
    'hist/mo_column': lambda: fluted(MOANA_WHITE, seed=922),
    'hist/mo_rail': lambda: balustrade(256, MOANA_WHITE, seed=923),
    'hist/mo_roof': lambda: tw.clay_tiles(size=512, seed=924, colour=(104, 110, 104)),
    'hist/mo_sign': _letters('MOANA HOTEL', MOANA_WHITE, (60, 80, 64), 925),
    'hist/nat_stone': lambda: tw.concrete(STONE, size=512, seed=940, boards=0, spalls=0.2),
    'hist/nat_arch': lambda: arch_board(*NAT_ARCH, colour=STONE, w=256, h=512, seed=941),
    'hist/nat_wing': lambda: arch_board(*NAT_WING, colour=STONE, seed=942),
    'hist/nat_sign': _letters('WAIKIKI WAR MEMORIAL', STONE, (90, 84, 70), 943),
    'hist/nat_rail': lambda: balustrade(256, STONE, seed=944, posts=5),
    'hist/bat_wall': lambda: period_sheet(BATTERY, (120, 118, 108), trim=BATTERY, kind='bunker', bays=4, floors=2, size=512, seed=960),
    'hist/bat_concrete': lambda: tw.concrete(BATTERY, size=512, seed=961, boards=6, spalls=0.45),
    'hist/bat_earth': lambda: tp.ground_yard(size=512, seed=962),
    'hist/bat_gun': lambda: tw.steel((84, 88, 70), size=256, seed=963, rust=0.6),
    'hist/bat_sign': _letters('BATTERY RANDOLPH 1911', BATTERY, (40, 40, 36), 964),
    'hist/lawn': _lawn,
    'hist/far_pink': lambda: tw.far_sheet(wall=PINK, bays=8, floors=8, size=128, seed=980),
    'hist/far_pink_plain': lambda: tw.far_plain(PINK, seed=981),
    'hist/far_tiles': lambda: tw.far_plain((150, 80, 58), seed=982),
    'hist/far_moana': lambda: tw.far_sheet(wall=MOANA_WHITE, bays=8, floors=8, size=128, seed=983),
    'hist/far_moana_plain': lambda: tw.far_plain(MOANA_WHITE, seed=984),
    'hist/far_moana_roof': lambda: tw.far_plain((98, 104, 98), seed=985),
    'hist/far_stone': lambda: tw.far_plain(STONE, seed=986),
    'hist/far_battery': lambda: tw.far_plain(BATTERY, seed=987),
    'hist/far_earth': lambda: tw.far_plain((112, 104, 78), seed=988),
})


def _looks():
    out = resortset._looks()
    out.update({
        'rh_wall': look('hist/rh_wall', tile=tw.FRONT_TILE, far='hist/far_pink'),
        'rh_plain': look('hist/rh_plain', tile=512, far='hist/far_pink_plain'),
        'rh_tiles': look('hist/rh_tiles', tile=400, far='hist/far_tiles'),
        'rh_loggia': dict(look('hist/rh_loggia'), alpha=True),
        'rh_porch': dict(look('hist/rh_porch'), alpha=True),
        'rh_porch_side': dict(look('hist/rh_porch_side'), alpha=True),
        'rh_belvedere': dict(look('hist/rh_belvedere'), alpha=True),
        'rh_sign': look('hist/rh_sign'),
        'mo_wall': look('hist/mo_wall', tile=tw.FRONT_TILE, far='hist/far_moana'),
        'mo_plain': look('hist/mo_plain', tile=512, far='hist/far_moana_plain'),
        'mo_column': look('hist/mo_column', tile=160),
        'mo_rail': dict(look('hist/mo_rail', tile=96), alpha=True),
        'mo_roof': look('hist/mo_roof', tile=400, far='hist/far_moana_roof'),
        'mo_sign': look('hist/mo_sign'),
        'nat_stone': look('hist/nat_stone', tile=512, far='hist/far_stone'),
        'nat_arch': dict(look('hist/nat_arch'), alpha=True),
        'nat_wing': dict(look('hist/nat_wing'), alpha=True),
        'nat_sign': look('hist/nat_sign'),
        'nat_rail': dict(look('hist/nat_rail', tile=110), alpha=True),
        'bat_wall': look('hist/bat_wall', tile=1024, far='hist/far_battery'),
        'bat_concrete': look('hist/bat_concrete', tile=512, far='hist/far_battery'),
        'bat_earth': look('hist/bat_earth', tile=512, far='hist/far_earth'),
        'bat_gun': look('hist/bat_gun', tile=256),
        'bat_sign': look('hist/bat_sign'),
        'lawn': look('hist/lawn', tile=600),
        'dark': look('resort/tar', tile=512),
    })
    return out


# ---------- helpers ----------

def _box(parts, size, at, look_name, far=False, solid=True, material='stone', turn=None, **faces):
    p = {'shape': 'box', 'size': list(size), 'at': list(at), 'look': look_name, 'material': material, 'solid': solid, 'far': far}
    if faces:
        p['faces'] = faces
    if turn is not None:
        p['turn'] = [0, 0, turn]
    parts.append(p)
    return p


def _hip(parts, half, at, look_name, h, far=True, top=0.0):
    """A square hip roof (a pyramid, or cut flat at `top` of its half-width) over a square `half` units each way."""
    p = {'shape': 'cylinder', 'r': half * math.sqrt(2) + 30, 'r2': top * math.sqrt(2), 'h': h, 'sides': 4, 'turn': [0, 0, 45],
         'at': list(at), 'look': look_name, 'material': 'stone', 'solid': False, 'far': far}
    if top <= 0:
        p['shape'] = 'cone'
    parts.append(p)


def _arcade(parts, n, W, H, pier, x, y, z0, z1, board, pier_look, depth=60, along='x', board_depth=30):
    """Piers from z0 to the springing z1 and a board of arches over them: along x at y (or along y at x)."""
    bay = W / float(n)
    for k in range(n + 1):
        o = -W / 2.0 + k * bay
        o = max(-W / 2.0 + pier / 2.0, min(W / 2.0 - pier / 2.0, o))
        at = [x + o, y, z0] if along == 'x' else [x, y + o, z0]
        _box(parts, [pier, depth, z1 - z0] if along == 'x' else [depth, pier, z1 - z0], at, pier_look)
    size = [W, board_depth, H] if along == 'x' else [board_depth, W, H]
    side = {'front': board, 'back': board, 'left': pier_look, 'right': pier_look, 'bottom': None} if along == 'x' else \
           {'left': board, 'right': board, 'front': pier_look, 'back': pier_look, 'bottom': None}
    _box(parts, size, [x, y, z1], pier_look, solid=False, **side)


def _with_trees(desc, trees):
    """The building with trees of the set's own about it: trees [(piece, x, y, turn, size)]."""
    items = [(desc, 0, 0, 0, 1.0)] + [(modelsets.PIECES[p]['describe'](), x, y, t, s) for p, x, y, t, s in trees]
    out = modelsets.combine(desc['name'], items)
    for k, v in desc.items():
        if k not in ('looks', 'parts', 'name'):
            out[k] = v
    return out


# ---------- The Royal Hawaiian ----------

RH_W, RH_D, RH_FLOORS = 4000, 800, 6
RH_WING = 5


def royal_hawaiian(open_=False):
    """The Royal Hawaiian: see the module's docstring. Sea side (the lawn, the wings, the loggia) to -y. open_: its lobby
    and the lookout in its tower inside (hotelinside.py), for the hotel's own small world."""
    P = []
    import hotelinside as hi
    LH = hi.LH
    H6, H5 = RH_FLOORS * FLOOR, RH_WING * FLOOR
    # the lawn between the wings, and the main block
    _box(P, [RH_W + 200, 1500, 8], [0, -1150, 0], 'lawn', material='dirt', top='lawn', front='lawn', back=None, left='lawn', right='lawn', bottom=None)
    if open_:
        _box(P, [RH_W, RH_D, H6 - LH], [0, 0, LH], 'rh_wall', far=True, top='tar', bottom='rhl_ceiling')
        hi.rh_lobby(P)
    else:
        # (the lobby as the town sees it, hotelinside: what stops you as it always was, drawn by nothing)
        _box(P, [RH_W, RH_D, H6], [0, 0, 0], 'tar', far=True, top='tar', **hi.NO_FACES)
        _box(P, [RH_W, RH_D, H6 - LH], [0, 0, LH], 'rh_wall', far=True, solid=False, top=None, bottom='rhl_ceiling_lit')
        hi.skin(P, [RH_W, RH_D, LH], [0, 0, 0], 'rh_hide_front', 'rh_hide_end')
        hi.shown(P, hi.rh_lobby)
        hi.lamps(P, [(x, 0) for x in (-1500, -900, -300, 300, 900, 1500)], LH - 30)
    _box(P, [RH_W + 40, RH_D + 40, 36], [0, 0, H6], 'rh_plain', far=True, top='rh_tiles')       # the coping
    # its two ends rise a floor under hip roofs of tile
    for sx in (-1, 1):
        _box(P, [700, RH_D, FLOOR], [sx * (RH_W / 2 - 350), 0, H6 + 36], 'rh_wall', far=True)
        _hip(P, 370, [sx * (RH_W / 2 - 350), 0, H6 + 36 + FLOOR], 'rh_tiles', 260)
    # the wings forward to the sea, each ending in a pavilion under a hip roof
    for sx in (-1, 1):
        wx = sx * (RH_W / 2 - 400)
        _box(P, [800, 1300, H5], [wx, -(RH_D / 2 + 650), 0], 'rh_wall', far=True, top='tar')
        _box(P, [840, 1340, 36], [wx, -(RH_D / 2 + 650), H5], 'rh_plain', far=True, top='rh_tiles')
        _hip(P, 420, [wx, -(RH_D / 2 + 1300 - 420), H5 + 36], 'rh_tiles', 300)
    # the tower over the middle: rooms to the eighth floor, an open belvedere of arches, a cornice, a dome
    T = 640
    tz = 8 * FLOOR
    ty = -(RH_D / 2 - 200)                           # (its middle: it stands a little out of the sea face)
    if open_:
        _box(P, [T, T, tz - LH], [0, ty, LH], 'rh_wall', far=True, top='tar', bottom='rhl_ceiling')
    else:
        _box(P, [T, T, tz], [0, ty, 0], 'tar', far=True, top='tar', **hi.NO_FACES)
        _box(P, [T, T, tz - LH], [0, ty, LH], 'rh_wall', far=True, solid=False, top=None, bottom='rhl_ceiling_lit')
        hi.skin(P, [T, hi.TOWER_BAY, LH], [0, -(RH_D / 2 + hi.TOWER_BAY / 2.0), 0], 'rh_hide_end', 'rh_hide_end')
        hi.lamps(P, [(0, -(RH_D / 2 + 20))], LH - 30)
    n, W, H, pier = RH_BELVEDERE
    spring = tz + 260
    if open_:
        hi.rh_belvedere(P, T, ty, tz, H)
    else:
        _box(P, [T - 160, T - 160, 260 + H], [0, ty, tz], 'dark', far=True, solid=False)   # the dark room inside
    posts = set()
    for k in range(4):
        o = round(-T / 2.0 + pier / 2.0 + (T - pier) * k / 3.0, 1)
        e = T / 2.0 - pier / 2.0
        posts |= {(o, -e), (o, e), (-e, o), (e, o)}
    for px, py in sorted(posts):
        _box(P, [pier, pier, 260], [px, ty + py, tz], 'rh_plain')
    for sy in (-1, 1):
        _box(P, [W, 30, H], [0, ty + sy * (T / 2.0 - 30), spring], 'rh_plain', solid=False, front='rh_belvedere', back='rh_belvedere', bottom=None, left=None, right=None)
        _box(P, [W, 30, H], [sy * (T / 2.0 - 30), ty, spring], 'rh_plain', solid=False, turn=90, front='rh_belvedere', back='rh_belvedere', bottom=None, left=None, right=None)
    cz = spring + H
    _box(P, [T + 80, T + 80, 50], [0, ty, cz], 'rh_plain', far=True, top='rh_tiles')
    P.append({'shape': 'cylinder', 'r': 250, 'h': 90, 'sides': 12, 'at': [0, ty, cz + 50], 'look': 'rh_plain', 'material': 'stone', 'far': True})
    P.append({'shape': 'ball', 'r': 250, 'sides': 12, 'rings': 6, 'scale': [1, 1, 0.75], 'at': [0, ty, cz - 50], 'look': 'rh_tiles', 'material': 'stone', 'far': True})
    P.append({'shape': 'cylinder', 'r': 18, 'r2': 4, 'h': 260, 'sides': 6, 'at': [0, ty, cz + 320], 'look': 'grey', 'solid': False, 'far': True})
    # the loggia along the garden, between the wings: piers, arches, its roof a terrace
    n, W, H, pier = RH_LOGGIA
    ly = -(RH_D / 2 + 240)
    _box(P, [W, 260, 10], [0, -(RH_D / 2 + 130), 0], 'terrazzo')
    _arcade(P, n, W, H, pier, 0, ly, 0, 320, 'rh_loggia', 'rh_plain')
    _box(P, [W + 40, 280, 30], [0, -(RH_D / 2 + 130), 320 + H], 'rh_plain', far=True, top='rh_tiles')
    # the carriage porch on the town side: three arches to the drive, two each side
    n, W, H, pier = RH_PORCH
    py0 = RH_D / 2 + 600
    _arcade(P, n, W, H, pier, 0, py0, 0, 320, 'rh_porch', 'rh_plain')
    for sx in (-1, 1):
        n2, W2, H2, pier2 = RH_PORCH_SIDE
        _arcade(P, n2, W2, H2, pier2, sx * (W / 2 - 15), RH_D / 2 + 300, 0, 320, 'rh_porch_side', 'rh_plain', along='y')
    _box(P, [W + 60, 660, 40], [0, RH_D / 2 + 300, 320 + H], 'rh_plain', far=True, top='rh_tiles')
    _box(P, [900, 16, 110], [0, py0 + 40, 320 + H + 40], 'rh_plain', solid=False, back='rh_sign')
    # palms on the lawn and by the drive
    trees = [('palm_tall', x, y, t, s) for x, y, t, s in
             ((-900, -1250, 20, 1.15), (-300, -1700, 140, 1.0), (500, -1350, 260, 1.2), (900, 1250, 170, 1.1))]
    lk = _looks()
    lk.update(hi.looks() if open_ else hi.shown_looks())
    return _with_trees({'name': 'FOLabLandmarkRoyalHawaiian' + ('Open' if open_ else ''), 'looks': lk, 'parts': P}, trees)


# ---------- The Moana ----------

MO_W, MO_D, MO_FLOORS = 1800, 900, 5


def moana(open_=False):
    """The Moana: see the module's docstring. Sea side (the verandas, the Banyan Court) to -y. open_: its lobby and the
    pavilion on its roof inside (hotelinside.py), for the hotel's own small world."""
    P = []
    H5, H4 = MO_FLOORS * FLOOR, 4 * FLOOR
    import hotelinside as hi
    if open_:
        _box(P, [MO_W, MO_D, H5 - hi.LH], [0, 0, hi.LH], 'mo_wall', far=True, top='tar', bottom='rhl_ceiling')
        hi.mo_lobby(P)
    else:
        # (the lobby as the town sees it, hotelinside: what stops you as it always was, drawn by nothing)
        _box(P, [MO_W, MO_D, H5], [0, 0, 0], 'tar', far=True, top='tar', **hi.NO_FACES)
        _box(P, [MO_W, MO_D, H5 - hi.LH], [0, 0, hi.LH], 'mo_wall', far=True, solid=False, top=None, bottom='rhl_ceiling_lit')
        hi.skin(P, [MO_W, MO_D, hi.LH], [0, 0, 0], 'mo_hide_front', 'mo_hide_end')
        hi.shown(P, hi.mo_lobby)
        hi.lamps(P, [(x, 0) for x in (-400, 0, 400)], hi.LH)
    _box(P, [MO_W + 40, MO_D + 40, 30], [0, 0, H5], 'mo_plain', far=True)
    for sy in (-1, 1):                                                          # balustrades round its roof
        _box(P, [MO_W, 12, 90], [0, sy * (MO_D / 2 + 6), H5 + 30], 'mo_rail', solid=False, top='mo_plain', bottom=None, left=None, right=None)
    # the pavilion on its roof under a hip roof
    if open_:
        hi.mo_pavilion(P, H5 + 30)
    else:
        _box(P, [700, 700, FLOOR], [0, 0, H5 + 30], 'mo_wall', far=True, top='tar')
    _hip(P, 370, [0, 0, H5 + 30 + FLOOR], 'mo_roof', 300)
    # wings either side, then forward to the sea round the court
    for sx in (-1, 1):
        _box(P, [1300, 800, H4], [sx * (MO_W / 2 + 650), 0, 0], 'mo_wall', far=True, top='tar')
        _box(P, [1340, 840, 30], [sx * (MO_W / 2 + 650), 0, H4], 'mo_plain', far=True)
        _box(P, [800, 1300, H4], [sx * (MO_W / 2 + 900), -(400 + 650), 0], 'mo_wall', far=True, top='tar')
        _box(P, [840, 1340, 30], [sx * (MO_W / 2 + 900), -(400 + 650), H4], 'mo_plain', far=True)
        _hip(P, 420, [sx * (MO_W / 2 + 900), -(400 + 1300 - 420), H4 + 30], 'mo_roof', 280)
    # verandas up the sea side of the middle block: a floor, posts, a balustrade, each floor
    vy = -(MO_D / 2 + 110)
    for k in range(MO_FLOORS):
        _box(P, [MO_W, 220, 20], [0, vy, k * FLOOR], 'mo_plain', top='wood' if k else 'terrazzo')
        if k:
            _box(P, [MO_W, 10, 90], [0, vy - 105, k * FLOOR + 20], 'mo_rail', solid=False, top='mo_plain', bottom=None, left=None, right=None)
        for i in range(7):
            x = -MO_W / 2 + 20 + i * (MO_W - 40) / 6.0
            P.append({'shape': 'cylinder', 'r': 14, 'h': FLOOR - 20, 'sides': 6, 'at': [x, vy - 95, k * FLOOR + 20], 'look': 'mo_plain', 'caps': False, 'material': 'wood'})
    _box(P, [MO_W, 220, 20], [0, vy, H5 - 20], 'mo_plain', solid=False)
    # the portico on the town side: six columns two floors tall, the balcony over them, steps up
    py = MO_D / 2 + 300
    _box(P, [1400, 600, 40], [0, MO_D / 2 + 300, 0], 'terrazzo')
    for k in range(2):                                                          # (two steps down from the porch to the drive)
        _box(P, [1000, 90, 27 - 14 * k], [0, MO_D / 2 + 645 + 90 * k, 0], 'terrazzo')
    for i in range(6):
        x = -625 + i * 250
        _box(P, [110, 110, 30], [x, py + 220, 40], 'mo_plain')
        P.append({'shape': 'cylinder', 'r': 40, 'r2': 34, 'h': 2 * FLOOR - 70, 'sides': 10, 'at': [x, py + 220, 70], 'look': 'mo_column', 'caps': False, 'material': 'stone'})
        _box(P, [120, 120, 40], [x, py + 220, 2 * FLOOR], 'mo_plain', solid=False)
    _box(P, [1440, 620, 90], [0, py - 10, 2 * FLOOR + 40], 'mo_plain', far=True, back='mo_sign')
    for sx in (-1, 1):
        _box(P, [10, 600, 90], [sx * 715, py - 10, 2 * FLOOR + 130], 'mo_rail', solid=False, top='mo_plain', bottom=None, front=None, back=None)
    _box(P, [1440, 10, 90], [0, py + 295, 2 * FLOOR + 130], 'mo_rail', solid=False, top='mo_plain', bottom=None, left=None, right=None)
    # the Banyan Court: its lawn and its tree
    _box(P, [MO_W, 1300, 8], [0, -(MO_D / 2 + 220 + 650), 0], 'lawn', material='dirt', bottom=None)
    trees = [('jungle_banyan', 0, -(MO_D / 2 + 900), 30, 1.6), ('palm_tall', 650, -(MO_D / 2 + 1450), 230, 1.1), ('palm_young', -800, MO_D / 2 + 700, 50, 1.0)]
    lk = _looks()
    lk.update(hi.looks() if open_ else hi.shown_looks())
    return _with_trees({'name': 'FOLabLandmarkMoana' + ('Open' if open_ else ''), 'looks': lk, 'parts': P}, trees)


# ---------- The Natatorium ----------

NAT_POOL_W, NAT_POOL_D = 3000, 1300
NAT_DEEP = 420          # (how far its sea walls go down below the shore it stands on)
NAT_WALK = 266.0        # (the walk over the bleachers' top rows: 6 over the walls' tops, which are walked on too)
NAT_STEPS, NAT_STEPS_W, NAT_STEPS_FOOT = 14, 400.0, 760.0      # (up through the arch: from the street at y 760 to the walk)
NAT_SEA = -1560.0       # (the sea wall's middle, front to back; its top 260 over the origin, 200 wide)
NAT_SIDE = 1600.0       # (the pool's side walls' middles, across)


def natatorium():
    """The Natatorium: see the module's docstring. Pool and sea to -y, the arch to the park at +y."""
    P = []
    fy = 300                                                                      # the arch's middle, front to back
    # the arch: two piers, the board of the arch over the opening, an attic with the name, urns
    n, W, H, pier = NAT_ARCH
    for sx in (-1, 1):
        _box(P, [260, 320, 1000], [sx * (W / 2 + 130), fy, 0], 'nat_stone', far=True)
    _box(P, [W, 320, H], [0, fy, 1000 - H], 'nat_stone', far=True, solid=False, front='nat_arch', back='nat_arch', bottom=None, left=None, right=None)
    _box(P, [W + 520, 340, 60], [0, fy, 1000], 'nat_stone', far=True)
    _box(P, [W + 400, 300, 180], [0, fy, 1060], 'nat_stone', far=True, back='nat_sign', front='nat_sign')
    for sx in (-1, 1):
        P.append({'shape': 'cylinder', 'r': 50, 'r2': 70, 'h': 120, 'sides': 8, 'at': [sx * (W / 2 + 130), fy, 1240], 'look': 'nat_stone', 'material': 'stone'})
    # colonnaded wings either side, a pavilion at each end
    n, W2, H2, pier2 = NAT_WING
    for sx in (-1, 1):
        wx = sx * (W / 2 + 260 + W2 / 2)
        _box(P, [W2, 20, 420], [wx, fy - 150, 0], 'dark', solid=False)                     # (the shade behind the arches)
        _arcade(P, n, W2, H2, pier2, wx, fy + 120, 0, 420, 'nat_wing', 'nat_stone', depth=80)
        _box(P, [W2 + 20, 320, 50], [wx, fy, 420 + H2], 'nat_stone', far=True)
        _box(P, [W2, 10, 80], [wx, fy + 150, 470 + H2], 'nat_rail', solid=False, top='nat_stone', bottom=None, left=None, right=None)
        _box(P, [320, 360, 760], [sx * (W / 2 + 260 + W2 + 160), fy, 0], 'nat_stone', far=True)
    # the pool out over the sea: deck walls round it, bleachers along its town side, the water gone green
    py0 = fy - 160                                                                # (the pool's town edge)
    py = py0 - NAT_POOL_D / 2.0 - 300
    # (its walls go down to the sea bed: the arch stands on the shore, the pool out over the water)
    _box(P, [NAT_POOL_W + 400, 200, 260 + NAT_DEEP], [0, py0 - NAT_POOL_D - 400, -NAT_DEEP], 'nat_stone', far=True)       # the sea wall
    for sx in (-1, 1):
        _box(P, [200, NAT_POOL_D + 600, 260 + NAT_DEEP], [sx * (NAT_POOL_W / 2 + 100), py - 0, -NAT_DEEP], 'nat_stone', far=True)
    for k in range(4):                                                            # the bleachers stepping down to the water
        _box(P, [NAT_POOL_W, 75, 260 - 55 * k + NAT_DEEP], [0, py0 - 37 - 75 * k, -NAT_DEEP], 'nat_stone', far=(k == 0))
    _box(P, [NAT_POOL_W, NAT_POOL_D, 30], [0, py0 - 300 - NAT_POOL_D / 2.0, -40], 'nat_stone', solid=False, top='pool', bottom=None, far=True)
    _box(P, [NAT_POOL_W + 400, 12, 80], [0, py0 - NAT_POOL_D - 306, 260], 'nat_rail', solid=False, top='nat_stone', bottom=None, left=None, right=None)
    # the way through (to the battleship: shipway.py): steps up through the arch from the street to a walk along the top
    # of the bleachers, which meets the tops of the pool's side walls; they lead to the sea wall, where the pier starts
    run = NAT_STEPS_FOOT - py0
    for k in range(NAT_STEPS):
        t0 = k / float(NAT_STEPS)
        y1 = NAT_STEPS_FOOT - run * t0
        _box(P, [NAT_STEPS_W, run / NAT_STEPS + 1, NAT_WALK * (k + 1) / NAT_STEPS + 40], [0, y1 - run / NAT_STEPS / 2.0, -40], 'nat_stone', far=False)
    _box(P, [NAT_POOL_W + 400, py0 + 8, 20], [0, (py0 + 8) / 2.0, NAT_WALK - 20], 'nat_stone', far=True)       # (the walk: over the top rows)
    trees =[('palm_tall', -1700, fy + 650, 20, 1.1), ('palm_young', 1750, fy + 700, 150, 1.0)]
    return _with_trees({'name': 'FOLabLandmarkNatatorium', 'looks': _looks(), 'parts': P}, trees)


# ---------- Battery Randolph ----------

BAT_W, BAT_D, BAT_H = 4200, 1200, 520


def battery_randolph():
    """Battery Randolph: see the module's docstring. The guns and the bank of earth to the sea at -y."""
    P = []
    _box(P, [BAT_W, BAT_D, BAT_H], [0, 0, 0], 'bat_concrete', far=True, back='bat_wall', left='bat_wall', right='bat_wall')
    _box(P, [BAT_W + 60, BAT_D + 60, 40], [0, 0, BAT_H], 'bat_concrete', far=True)
    _box(P, [1500, 12, 140], [0, BAT_D / 2 + 6, BAT_H - 200], 'bat_concrete', solid=False, back='bat_sign', front=None)
    # the bank of earth against its sea side: one slope from the roof's edge down into the ground
    th, L, T = math.radians(22), 1800, 320
    top = (-(BAT_D / 2), BAT_H + 40)
    at = (top[0] - (math.cos(th) * L / 2 - math.sin(th) * T), top[1] - (math.sin(th) * L / 2 + math.cos(th) * T))
    P.append({'shape': 'box', 'size': [BAT_W + 200, L, T], 'at': [0, round(at[0], 1), round(at[1], 1)], 'turn': [math.degrees(th), 0, 0], 'look': 'bat_earth',
              'material': 'dirt', 'far': True})
    # the two guns behind their ring walls, a stair up to them, an observation post between
    for sx in (-1, 1):
        gx = sx * 1150
        P.append({'shape': 'cylinder', 'r': 450, 'h': 140, 'sides': 16, 'at': [gx, -100, BAT_H + 40], 'look': 'bat_concrete', 'caps': False, 'under': True, 'solid': False})
        P.append({'shape': 'cylinder', 'r': 470, 'h': 20, 'sides': 16, 'at': [gx, -100, BAT_H + 170], 'look': 'bat_concrete', 'caps': False, 'solid': False})
        P.append({'shape': 'cylinder', 'r': 220, 'h': 30, 'sides': 12, 'at': [gx, -100, BAT_H + 40], 'look': 'bat_gun', 'material': 'metal'})
        _box(P, [280, 420, 220], [gx, -60, BAT_H + 70], 'bat_gun', material='metal')
        P.append(dict(limb([gx, -120, BAT_H + 230], [gx, -120 - 1400 * math.cos(math.radians(12)), BAT_H + 230 + 1400 * math.sin(math.radians(12))], 46, 34, 'bat_gun', sides=10, solid=True, caps=True),
                      material='metal', far=True))
    for k in range(11):                                                         # the stair, up the town side at one end
        _box(P, [260, 60 * (11 - k), 51], [-BAT_W / 2 + 300, BAT_D / 2 + 30 * (11 - k), 51 * k], 'bat_concrete')
    _box(P, [360, 360, 300], [300, 200, BAT_H + 40], 'bat_concrete', far=True, front='bat_wall')
    _box(P, [300, 10, 40], [300, 20, BAT_H + 260], 'dark', solid=False)            # its slit
    return {'name': 'FOLabLandmarkBatteryRandolph', 'looks': _looks(), 'parts': P}


PIECES = {'royal_hawaiian': ('The Royal Hawaiian', royal_hawaiian), 'royal_hawaiian_open': ('The Royal Hawaiian, open', lambda: royal_hawaiian(open_=True)),
          'moana': ('The Moana', moana), 'moana_open': ('The Moana, open', lambda: moana(open_=True)),
          'natatorium': ('Waikiki Natatorium', natatorium), 'battery_randolph': ('Battery Randolph', battery_randolph)}
_RH_LIGHTS = [('ExtLightWarm02', 0, RH_D / 2 + 300, 300), ('ExtLightWarm02', -600, -(RH_D / 2 + 200), 280), ('ExtLightWarm02', 600, -(RH_D / 2 + 200), 280),
              ('ExtLightWarm02', 0, -(RH_D / 2 - 520), 8 * FLOOR + 200)]
waikikiset.LIGHTS.update({
    'royal_hawaiian': _RH_LIGHTS, 'royal_hawaiian_open': _RH_LIGHTS,
    'moana': [('ExtLightWarm02', 0, MO_D / 2 + 300, 2 * FLOOR - 40), ('ExtLightWarm02', 0, -(MO_D / 2 + 600), 320)],
    'moana_open': [('ExtLightWarm02', 0, MO_D / 2 + 300, 2 * FLOOR - 40), ('ExtLightWarm02', 0, -(MO_D / 2 + 600), 320)],
    'natatorium': [('ExtLightWarm02', 0, 300, 700)],
    'battery_randolph': [('ExtLightWarm02', 0, BAT_D / 2 + 200, 420)],
})
for _k, (_label, _fn) in PIECES.items():
    modelsets.PIECES.setdefault(_k, {'label': _label, 'set': 'resort', 'file': _k, 'describe': _fn, 'edid': 'FOLabLandmark' + ''.join(w.title() for w in _k.split('_'))})
