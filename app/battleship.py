"""A battleship of FOLab's own: the USS Missouri (BB-63), the Iowa-class battleship that lies in Pearl Harbor, as she
would be two centuries after the bombs: her haze grey gone chalky and rust-run, the teak of her decks silvered and
here and there gone through to the steel, still whole.

As she was last refitted (the 1980s), from the bow: a long flared bow with the stem raked forward, anchors and their
chains on the forecastle, the breakwater; turrets One and Two (Two firing over One), three 16-inch guns each; the
superstructure in levels, the armoured conning tower at its front under the pilot house and its bridge wings, the
fire-control tower stepping up to the main battery director, the foremast with its radars; the first funnel, the
mainmast, the second funnel; the Tomahawk launchers and Harpoon canisters amidships, ten twin 5-inch mounts on the
01 level, four Phalanx guns; the after director; turret Three facing aft; the fantail with its crane. "63" on both
bows. The surrender deck's plaque on the 01 level, starboard, beside turret Two.

Sizes as the ship's (270 m long, 33 m in the beam, 70 units a metre). Frame: the middle of the ship at the origin,
the waterline at z 0, the bow towards -y (so port is +x, starboard -x). The decks are solid and walked on: the hull
is one convex piece per section (modelmake's 'hull'), every level a box, ladders between levels as ramps under steps.
`SPOTS` is where the way aboard and the doors go (shipinside.py uses them).

Its own worn pictures: `hull_plates` (haze grey strakes, welds, primer and rust through the paint, rust run from the
scuppers), `boot` (the black band at the waterline, salt), `antifoul` (the red under the water, weed, barnacles),
`teak` (planks, caulking, butts, boards gone to the steel), `steel_deck`, `armour`, `bridge_windows`, `hull_number`
(see-through but for the numbers), `plaque`."""
import math
import random

import modelsets
import texpaint as tp
import texwear as tw
from modelsets import look
from texwear import Field, Cells, Picture, Wear, grade, mix, mul, smooth

HAZE = (122, 128, 132)              # haze grey, as the Navy painted her
DECK_GREY = (86, 90, 92)
TEAK = (150, 128, 96)
SET = 'ship'
COOL = dict(sat=0.72, warm=(1.0, 0.995, 0.985))     # (the Fallout grade, but her grey kept grey: haze grey read as brown with the warm cast)


# ---------- her pictures ----------

STREAKS = 40                # (rust runs a picture: from scuppers, fixings, the plates' seams)


def hull_plates(size=1024, seed=900, colour=HAZE, strakes=6, butts=3, rust=0.7, grime_low=True):
    """The ship's side as she looks after two centuries: strakes of plate with their butts staggered, each plate in its
    own grey (touched up over the years in paint that never matched, in ragged patches), welds standing proud with a
    shadow under them; broad rust runs down from scuppers, fixings and the seams, fading as they go; rust blooming
    along the welds and the paint peeled to red primer and rusting in patches; grime gathering low down. Strong enough
    to read in the game's light (a first, faint version read as no texture at all in the game: its brightness varied
    by 9 in 255, the Kilauea's by 36)."""
    c = Picture(size, size, gloss=28)
    rnd = random.Random(seed)
    sh = size / float(strakes)
    sw = size / float(butts)
    offs = [rnd.uniform(0, sw) for _ in range(strakes)]
    tint = [rnd.choice((-0.24, -0.15, -0.07, 0.0, 0.06, 0.13, 0.2)) for _ in range(strakes * butts)]
    touch = Field(size, size, seed + 12, cells=6, octaves=4, fall=0.55)    # (ragged touched-up patches)
    flake = Field(size, size, seed + 10, cells=8, octaves=5, fall=0.62)
    blotch = Field(size, size, seed + 13, cells=3, octaves=4)
    streak = Field(size, size, seed + 14, cells=24, octaves=2, stretch=(1.0, 0.06))
    pits = Cells(size, size, seed + 11, n=48)
    wr = Wear(size, size, seed, grime=0.7, rain=0.0)
    run = [0.0] * (size * size)
    for _ in range(STREAKS):
        x0 = rnd.uniform(0, size)
        y0 = int(rnd.randrange(strakes) * sh + 4) if rnd.random() < 0.7 else rnd.uniform(0, size)
        long, wide = rnd.uniform(0.3, 0.95) * size, rnd.uniform(5.0, 15.0)
        strong = rnd.uniform(0.45, 0.95)
        for k in range(int(long)):
            t = k / long
            half = wide * (0.35 + 0.65 * min(1.0, t * 5)) * (1.0 - 0.3 * t)
            fade = (1 - t) ** 1.4 * strong
            yy = int(y0 + k) % size
            for dx in range(-int(half) - 2, int(half) + 3):
                xx = int(x0 + dx) % size
                q = yy * size + xx
                cover = fade * max(0.0, 1 - (abs(dx) / (half + 1.0)) ** 2) * (0.55 + 0.45 * streak.v[q])
                if cover > run[q]:
                    run[q] = cover
    top = tp._faded(colour, 0.03)
    ft = 1 - rust * 0.3
    for y in range(size):
        k = int(y / sh)
        v = y - k * sh
        vv = y / float(size)
        for x in range(size):
            p = y * size + x
            f, m = wr.fine.v[p], wr.mid.v[p]
            u = (x + offs[k]) % size
            j = int(u / sw)
            shade = 0.86 + tint[(k * butts + j) % len(tint)] + 0.3 * (blotch.v[p] - 0.5) + 0.14 * (m - 0.5) + 0.1 * (f - 0.5)
            tv = touch.v[p]
            if tv > 0.68:
                shade += 0.16 if (k + j) % 2 else -0.2                       # (a touched-up patch, ragged)
            col = mul(top, shade)
            h, g, depth = 0.5 + 0.03 * f, 30, 0.0
            if v < 3 or (u % sw) < 3:                                       # a weld, standing proud
                col, h = mul(col, 1.14), 0.66
            elif v < 8 or (u % sw) < 8:
                col, h, depth = mul(col, 0.5), 0.42, 0.5                     # (its shadow, dirt in it)
                if flake.v[p] > 0.52:
                    col = mix(col, tw.RUST_DARK, 0.75)                        # rust bloom along the seam
            fv = flake.v[p]
            if fv > ft:
                inner = (fv - ft) / (1 - ft)
                if inner < 0.1:
                    col, h = mul(tw.PRIMER, 0.8 + 0.3 * f), 0.47
                else:
                    col = mix(tw.PRIMER, mix(tw.RUST, tw.RUST_DARK if pits.d1[p] < 0.3 else tw.RUST_LIGHT, f), min(1.0, inner * 2.5))
                    h, g, depth = 0.42 + 0.12 * f, 6, 0.3
            elif fv > ft - 0.04:
                col = mix(col, tw.RUST, 0.45)
            r = run[p]
            if r > 0.02:
                col = mix(col, mix(tw.RUST, tw.RUST_DARK, 0.35 + 0.35 * f), min(0.9, r * 1.2))
            if grime_low:
                col = mix(col, mul(tw.GRIME, 0.85), 0.4 * smooth(0.55, 1.0, vv) * (0.6 + 0.4 * m))
            if m > 0.78:
                col = mix(col, tw.SALT, 0.22 * (m - 0.78) / 0.22)
            c.rgb[p], c.ht[p], c.gloss[p] = grade(wr.on(x, y, col, depth), **COOL), h, g
    return c


def boot(size=512, seed=920):
    """The boot topping: black paint at the waterline, a crust of salt on its upper half, rust bleeding through."""
    c = Picture(size, size, gloss=20)
    wr = Wear(size, size, seed, grime=0.3, rain=0.8, ledges=(0.0,))
    salt = Field(size, size, seed + 10, cells=8, octaves=4, stretch=(3.0, 0.4))
    rust = Field(size, size, seed + 11, cells=6, octaves=5)
    for y in range(size):
        for x in range(size):
            p = y * size + x
            f = wr.fine.v[p]
            col, h = mul((40, 40, 42), 0.85 + 0.3 * f), 0.5
            if salt.v[p] > 0.55:
                col, h = mix(col, tw.SALT, 0.55 * smooth(0.55, 0.8, salt.v[p])), 0.56
            if rust.v[p] > 0.74:
                col, h = mix(col, tw.RUST_DARK, 0.7), 0.46
            c.rgb[p], c.ht[p] = grade(wr.on(x, y, col)), h
    return c


def antifoul(size=512, seed=930):
    """The bottom's red anti-fouling, faded to brick, under weed, a crust of barnacles and the reef's coral growing on
    her where she sits (two centuries aground)."""
    c = Picture(size, size, gloss=8)
    wr = Wear(size, size, seed, grime=0.5, rain=0.0)
    weed = Field(size, size, seed + 10, cells=5, octaves=5)
    barn = Cells(size, size, seed + 11, n=140)
    coral = Field(size, size, seed + 12, cells=4, octaves=5)
    knob = Cells(size, size, seed + 13, n=400)
    for y in range(size):
        for x in range(size):
            p = y * size + x
            f = wr.fine.v[p]
            col, h = mul((120, 52, 42), 0.8 + 0.3 * f), 0.5
            if weed.v[p] > 0.5:
                col = mix(col, (52, 70, 44), smooth(0.5, 0.75, weed.v[p]) * 0.8)
            if barn.d1[p] < 0.2 and barn.id[p] % 3 != 0:
                col, h = mul((176, 168, 150), 0.7 + 0.3 * (0.2 - barn.d1[p]) / 0.2), 0.7 - barn.d1[p]
            if coral.v[p] > 0.6:                        # coral: pale, knobbly, here and there a pink or ochre head
                k = knob.d1[p]
                tone = ((196, 186, 168), (190, 140, 140), (176, 150, 96))[knob.id[p] % 3]
                col, h = mul(tone, 0.6 + 0.5 * max(0.0, 0.3 - k) / 0.3), 0.5 + max(0.0, 0.3 - k)
            c.rgb[p], c.ht[p] = grade(wr.on(x, y, col)), h
    return c


def teak(size=512, seed=940, planks=48, gone=0.05):
    """Her teak deck: planks along the ship (up the picture), black caulking between, butt joints staggered; the wood
    silvered, stained under every fitting, worn through in a few boards to the steel deck under them, rusty."""
    c = Picture(size, size, gloss=12)
    rnd = random.Random(seed)
    pw = size / float(planks)
    lengths = [rnd.uniform(0.2, 0.5) * size for _ in range(planks)]
    starts = [rnd.uniform(0, size) for _ in range(planks)]
    tint = [[rnd.uniform(-0.09, 0.09) for _ in range(8)] for _ in range(planks)]
    lost = [[rnd.random() < gone for _ in range(8)] for _ in range(planks)]
    wr = Wear(size, size, seed, grime=0.8, rain=0.0)
    grain = Field(size, size, seed + 10, cells=2, octaves=4, stretch=(0.25, 6.0))
    stain = Field(size, size, seed + 11, cells=5, octaves=4)
    for y in range(size):
        for x in range(size):
            p = y * size + x
            i = int(x / pw)
            u = x - i * pw
            along = (y + starts[i]) % size
            j = int(along / lengths[i]) % 8
            at_butt = (along % lengths[i]) < 1.2
            g = grain.v[p]
            col = mul(mix(tw.SILVER_WOOD, TEAK, 0.25 + tint[i][j]), 0.8 + 0.25 * (0.5 + 0.5 * math.sin(g * 30)))
            h, gl = 0.5 + 0.08 * g, 12
            if lost[i][j]:
                col, h, gl = mix(mul(DECK_GREY, 0.8), tw.RUST, 0.5 + 0.4 * wr.fine.v[p]), 0.3, 6
            if u < 1.3 or at_butt:
                col, h = mul((24, 22, 20), 0.9 + 0.2 * wr.fine.v[p]), 0.32              # the caulking
            if stain.v[p] > 0.72:
                col = mix(col, (70, 60, 48), 0.5 * smooth(0.72, 0.9, stain.v[p]))
            c.rgb[p], c.ht[p], c.gloss[p] = grade(wr.on(x, y, col)), h, gl
    return c


def steel_deck(size=512, seed=950, colour=DECK_GREY):
    """The superstructure's decks: grey steel plates welded edge to edge, rust run and blooming at the seams, the paint
    worn through (tw.steel alone read as flat in the game)."""
    return hull_plates(size=size, seed=seed, colour=colour, strakes=4, butts=4, rust=0.75, grime_low=False)


def armour(size=512, seed=960, colour=HAZE, panels=2):
    """A turret's or the conning tower's armour: few, thick plates with deep seams, the paint chalky, rust only at the
    seams and the bolt heads."""
    c = Picture(size, size, gloss=24)
    step = size / float(panels)
    irons = [(int(i * step + step * 0.5), int(j * step + 6)) for i in range(panels) for j in range(panels)]
    wr = Wear(size, size, seed, grime=0.8, rain=1.0, ledges=[k / float(panels) for k in range(panels)], irons=irons, bleach=0.2)
    chalk = Field(size, size, seed + 10, cells=6, octaves=4)
    for y in range(size):
        for x in range(size):
            p = y * size + x
            u, v = x % step, y % step
            f = wr.fine.v[p]
            col, h, depth = mul(tp._faded(colour, 0.05), 0.9 + 0.1 * wr.mid.v[p] + 0.05 * (f - 0.5)), 0.55, 0.0
            if chalk.v[p] > 0.66:
                col = mix(col, (190, 188, 180), 0.25)
            if u < 3 or v < 3:
                col, h, depth = mix(mul(col, 0.5), tw.RUST_DARK, 0.4), 0.3, 1.0
            elif (u < 14 or v < 14) and (int(u + v) % 24 < 5) and (u < 9 or v < 9):
                col, h = mix(col, tw.RUST, 0.5), 0.7                  # a bolt head
            c.rgb[p], c.ht[p] = grade(wr.on(x, y, col, depth), **COOL), h
    return c


def bridge_windows(size=512, seed=970, across=4, blown=False):
    """The pilot house's windows, two rows to the picture: dark glass in heavy frames, a few panes cracked or gone,
    the grey round them run with rust from the frames' corners. blown: every pane gone or a few shards, soot over the
    frames (the blast came in through them)."""
    c = Picture(size, size, gloss=30)
    rnd = random.Random(seed)
    cw = size / float(across)
    rows = ((0.08, 0.36), (0.58, 0.86))
    kinds = ('gone', 'gone', 'gone', 'cracked') if blown else ('dark', 'dark', 'dark', 'sky', 'cracked', 'gone')
    state = [[rnd.choice(kinds) for _ in range(across)] for _ in rows]
    soot = Field(size, size, seed + 20, cells=4, octaves=4)
    irons = [(int(i * cw + cw * 0.12), int(r[1] * size)) for r in rows for i in range(across)]
    wr = Wear(size, size, seed, grime=0.8, rain=1.0, ledges=[r[1] for r in rows], irons=irons)
    for y in range(size):
        vv = y / float(size)
        for x in range(size):
            p = y * size + x
            i = int(x / cw)
            u = (x % cw) / cw
            f = wr.fine.v[p]
            col, h, g, depth = mul(HAZE, 0.92 + 0.1 * wr.mid.v[p]), 0.55, 28, 0.0
            for r, (v0, v1) in enumerate(rows):
                if v0 <= vv <= v1 and 0.1 < u < 0.9:
                    gu, gv = (u - 0.1) / 0.8, (vv - v0) / (v1 - v0)
                    if gu < 0.06 or gu > 0.94 or gv < 0.08 or gv > 0.92:
                        col, h, depth = mul((70, 72, 74), 0.9 + 0.2 * f), 0.62, 0.4
                    else:
                        st = state[r][i]
                        col = mul(tp.GLASS_DARK, 0.9 + 0.4 * max(0.0, 1 - abs(gu - gv * 0.5 - 0.2) * 4))
                        col = mix(col, (150, 160, 160), 0.3 * (1 - gv) ** 2 if st == 'sky' else 0.1)
                        h, g = 0.35, 140
                        if st == 'gone':
                            col, h, g = mul((14, 14, 14), 0.8 + 0.4 * f), 0.1, 0
                        elif st == 'cracked' and abs(math.sin(math.atan2(gv - 0.4, gu - 0.6) * 3 + i)) < 0.05:
                            col = mix(col, (200, 204, 200), 0.6)
            if blown and soot.v[p] > 0.4:
                col = mix(col, SOOT, 0.75 * smooth(0.4, 0.65, soot.v[p]))
            c.rgb[p], c.ht[p], c.gloss[p] = grade(wr.on(x, y, col, depth), **COOL), h, g
    return c


def hull_number(w=512, h=256, seed=980, text='63'):
    """'63' as the Navy paints it on the bow: white with a black shadow, the paint worn; the rest see-through."""
    c = Picture(w, h, clear=HAZE, gloss=30)
    fail = Field(w, h, seed, cells=8, octaves=4)
    high = h * 0.78
    tw_ = c.text_wide(text, high)
    x0, y0 = (w - tw_) / 2, (h - high) / 2
    worn = lambda x, y: 0.0 if fail.at(int(x), int(y)) > 0.8 else 1.0
    c.text(text, x0 + high * 0.07, y0 + high * 0.05, high * 0.95, (20, 20, 22), thick=high / 4.6, worn=worn)
    c.text(text, x0, y0, high * 0.95, (226, 224, 214), thick=high / 5.6, worn=worn)
    for p in range(w * h):
        c.rgb[p] = grade(c.rgb[p])
    return c


def plaque(w=256, h=128, seed=990):
    """The surrender plaque let into the deck: bronze gone dark, the raised words still bright where feet have
    rubbed them."""
    c = Picture(w, h, gloss=90)
    wr = Wear(w, h, seed, grime=0.6, rain=0.0)
    for p in range(w * h):
        x, y = p % w, p // w
        f = wr.fine.v[p]
        col = mul((92, 70, 40), 0.85 + 0.3 * f)
        if x < 6 or y < 6 or x > w - 7 or y > h - 7:
            col = mul((150, 118, 64), 0.9 + 0.2 * f)
        if wr.mid.v[p] > 0.7:
            col = mix(col, (80, 120, 100), 0.4)
        c.rgb[p], c.ht[p] = col, 0.45
    c.text('SURRENDER', w * 0.12, h * 0.18, h * 0.26, (214, 182, 112), thick=3)
    c.text('2 SEP 1945', w * 0.14, h * 0.58, h * 0.22, (200, 170, 104), thick=3)
    for p in range(w * h):
        c.rgb[p] = grade(c.rgb[p], sat=0.8)
    return c


# ---------- what the bomb did (see-through pictures laid over her own: modelmake looks with alpha) ----------

SOOT = (34, 30, 27)
UNBURNT = (150, 154, 156)           # (her paint where something stood between it and the flash: paler than the rest)


def scorch(w=512, h=512, seed=1300, shadows=None, person=False):
    """Paint burnt by the flash: soot in drifts, blistered paint bubbled and split, bare steel rusting where it flaked;
    ragged at its edges (see-through there). shadows: flash shadows on it, pale where something stood in the way:
    'rails' (stanchions and two lifelines across its lower part), 'barrel' (a long gun's shadow, slanting), with person
    one human shape among them."""
    c = Picture(w, h, clear=SOOT, gloss=6)
    edge = Field(w, h, seed, cells=4, octaves=5, fall=0.6)
    blis = Cells(w, h, seed + 1, n=160)
    flake = Field(w, h, seed + 2, cells=10, octaves=4)
    fine = Field(w, h, seed + 3, cells=32, octaves=2)
    rnd = random.Random(seed)
    pale = set()
    if shadows:
        for kind in shadows:
            if kind == 'rails':
                for k in range(int(w / 70)):
                    x0 = int(30 + k * 70 + rnd.uniform(-6, 6))
                    for y in range(int(h * 0.45), h):
                        for x in range(x0, x0 + 7):
                            pale.add(y * w + x)
                for yy in (0.55, 0.75):
                    y0 = int(h * yy)
                    for y in range(y0, y0 + 5):
                        for x in range(w):
                            pale.add(y * w + x)
            elif kind == 'barrel':
                for t in range(0, int(w * 0.9)):
                    cx, cy = int(w * 0.05) + t, int(h * 0.3 + t * 0.12)
                    r = 14 - t * 6.0 / w
                    for y in range(int(cy - r), int(cy + r)):
                        if 0 <= y < h and 0 <= cx < w:
                            pale.add(y * w + cx)
        if person:
            px, py, s = w * 0.62, h * 0.2, h * 0.009         # (a man walking, 1.8 m on a picture of a few metres)
            for p in range(w * h):
                x, y = (p % w - px) / s, (p // w - py) / s
                head = (x - 0) ** 2 + (y - 6) ** 2 < 9
                body = -3.5 < x < 3.5 and 9 < y < 36
                legs = (abs(x + 1.8 - (y - 36) * 0.18) < 1.6 or abs(x - 1.8 + (y - 36) * 0.22) < 1.6) and 36 <= y < 62
                arm = abs(x - 4.5 - (y - 12) * 0.25) < 1.3 and 12 < y < 32
                if head or body or legs or arm:
                    pale.add(p)
    for p in range(w * h):
        x, y = p % w, p // w
        a = smooth(0.24, 0.42, edge.v[p])                 # (ragged: the burn's edge eats in from nothing)
        if a <= 0.0:
            continue
        col, ht = mul(SOOT, 0.8 + 0.5 * fine.v[p]), 0.5
        if blis.d1[p] < 0.12:                             # a blister, light on its top, a dark split in it
            col, ht = mul((96, 84, 70), 0.7 + 0.4 * (0.12 - blis.d1[p]) / 0.12), 0.5 + (0.12 - blis.d1[p]) * 3
            if blis.d1[p] < 0.03:
                col, ht = (18, 16, 14), 0.3
        if flake.v[p] > 0.7:
            col, ht = mix(col, tw.RUST, smooth(0.7, 0.85, flake.v[p])), 0.42
        if p in pale:
            col, ht, a = mul(UNBURNT, 0.9 + 0.15 * fine.v[p]), 0.52, 1.0
        c.rgb[p], c.ht[p], c.a[p] = grade(col, **COOL), ht, 1.0 if a > 0.5 else 0.0
    return c


def burnt_teak(w=512, h=512, seed=1320):
    """Her planking where it burned: charred black and split along the grain, in patches; elsewhere see-through."""
    c = Picture(w, h, clear=(20, 18, 16), gloss=4)
    edge = Field(w, h, seed, cells=3, octaves=5, fall=0.6)
    grain = Field(w, h, seed + 1, cells=2, octaves=4, stretch=(0.25, 6.0))
    for p in range(w * h):
        x = p % w
        if edge.v[p] < 0.45:
            continue
        g = grain.v[p]
        col = mul((26, 22, 18), 0.7 + 0.6 * g)
        if x % 11 < 1 or abs(math.sin(g * 40)) < 0.05:
            col = (8, 8, 8)
        if edge.v[p] < 0.5:
            col = mix(col, (96, 80, 60), 0.6)              # (scorched brown at the edge)
        c.rgb[p], c.ht[p], c.a[p] = col, 0.4 + 0.2 * g, 1.0
    return c


def holed(w=512, h=512, seed=1340):
    """A hole torn in her plating: black inside, the steel round it bent inwards and rusted; see-through outside."""
    c = Picture(w, h, clear=(10, 10, 10), gloss=4)
    rim = Field(w, h, seed, cells=6, octaves=4)
    for p in range(w * h):
        x, y = (p % w) / float(w) - 0.5, (p // w) / float(h) - 0.55
        r = math.hypot(x * 1.3, y) + 0.12 * (rim.v[p] - 0.5)
        if r < 0.24:
            c.rgb[p], c.ht[p], c.a[p] = (6, 6, 6), 0.0, 1.0
        elif r < 0.36:
            t = (r - 0.24) / 0.12
            c.rgb[p], c.ht[p], c.a[p] = mix(tw.RUST_DARK, tw.RUST, t), 0.2 + 0.5 * t, 1.0
    return c


def droppings(w=256, h=256, seed=1360):
    """Two centuries of seabirds: white streaks run down from a ledge, thick at the top; see-through between."""
    c = Picture(w, h, clear=(220, 218, 206), gloss=10)
    rnd = random.Random(seed)
    for _ in range(26):
        x0, ln, wd = rnd.uniform(0, w), rnd.uniform(0.2, 0.9) * h, rnd.uniform(2, 7)
        for y in range(int(ln)):
            ww = wd * (1 - y / ln) + 1
            for x in range(int(x0 - ww), int(x0 + ww)):
                if 0 <= x < w:
                    p = y * w + x
                    c.rgb[p], c.ht[p], c.a[p] = mul((222, 220, 208), 0.85 + 0.15 * rnd.random()), 0.6, 1.0
    for x in range(w):
        for y in range(int(6 + 4 * math.sin(x * 0.2))):
            c.rgb[y * w + x], c.a[y * w + x] = (226, 224, 212), 1.0
    return c


modelsets.TEXTURES.update({
    'ship/scorch': lambda: scorch(seed=1300),
    'ship/scorch_rails': lambda: scorch(seed=1301, shadows=('rails',)),
    'ship/scorch_person': lambda: scorch(seed=1302, shadows=('rails', 'barrel'), person=True),
    'ship/burnt_teak': burnt_teak,
    'ship/holed': holed,
    'ship/droppings': droppings,
    'ship/windows_blown': lambda: bridge_windows(seed=971, blown=True),
})


modelsets.TEXTURES.update({
    'ship/hull': lambda: hull_plates(seed=900),
    'ship/super': lambda: hull_plates(size=512, seed=905, colour=(130, 136, 140), strakes=4, butts=2, rust=0.4),
    'ship/boot': boot,
    'ship/antifoul': antifoul,
    'ship/teak': teak,
    'ship/steel_deck': steel_deck,
    'ship/armour': armour,
    'ship/gun': lambda: armour(size=256, seed=965, panels=1),
    'ship/dark': lambda: tw.steel(colour=(92, 96, 98), size=256, seed=975, rust=0.5, flake=0.3, gloss=30),
    'ship/soot': lambda: tw.steel(colour=(30, 28, 26), size=256, seed=976, rust=0.6, flake=0.2, gloss=8),
    'ship/rust': lambda: tw.hull_rust(size=256, seed=977, paint=(60, 60, 62), band=(60, 60, 62)),
    'ship/white': lambda: tw.steel(colour=(214, 214, 206), size=256, seed=978, rust=0.25, flake=0.2, gloss=40),
    'ship/canvas': lambda: tw.render(colour=(150, 146, 128), size=256, seed=979, peel=0.1),
    'ship/windows': bridge_windows,
    'ship/number': hull_number,
    'ship/plaque': plaque,
    # (her far-off pictures: her own, small, not flat colours: seen from across the bay she was a grey smear)
    'ship/far_hull': lambda: hull_plates(size=128, seed=985, strakes=3, butts=2),
    'ship/far_deck': lambda: teak(size=128, seed=986, planks=16),
    'ship/far_dark': lambda: tw.steel(colour=(84, 88, 90), size=64, seed=987, rust=0.4, flake=0.2),
})


def _looks():
    return {
        'hull': look('ship/hull', tile=1200, far='ship/far_hull'),
        'boot': look('ship/boot', tile=512, far='ship/far_dark'),
        'bottom': look('ship/antifoul', tile=512, far='ship/far_dark'),
        'teak': look('ship/teak', tile=640, far='ship/far_deck'),
        'deck': look('ship/steel_deck', tile=512, far='ship/far_dark'),
        'super': look('ship/super', tile=640, far='ship/far_hull'),
        'armour': look('ship/armour', tile=700, far='ship/far_hull'),
        'gun': look('ship/gun', tile=400, far='ship/far_hull'),
        'dark': look('ship/dark', tile=256, far='ship/far_dark'),
        'soot': look('ship/soot', tile=256, far='ship/far_dark'),
        'rust': look('ship/rust', tile=256, far='ship/far_dark'),
        'white': look('ship/white', tile=256, far='ship/far_hull'),
        'canvas': look('ship/canvas', tile=256, far='ship/far_hull'),
        'windows': look('ship/windows', tile=480, far='ship/far_dark'),
        'number': dict(look('ship/number'), alpha=True),
        'plaque': look('ship/plaque'),
        'windows_blown': look('ship/windows_blown', tile=480, far='ship/far_dark'),
        'scorch': dict(look('ship/scorch'), alpha=True),
        'scorch_rails': dict(look('ship/scorch_rails'), alpha=True),
        'scorch_person': dict(look('ship/scorch_person'), alpha=True),
        'burnt_teak': dict(look('ship/burnt_teak'), alpha=True),
        'holed': dict(look('ship/holed'), alpha=True),
        'droppings': dict(look('ship/droppings'), alpha=True),
    }


# ---------- her lines ----------

LONG, HALF = 18900.0, 9450.0        # 270 m
BEAM = 1170.0                       # half her beam at the deck
KEEL = -650.0                       # (her draught as she lies now, lighter than in service)

# the levels of her section, top down: z (None: the deck's), width at the middle, where its stem is (0 at the bow),
# how full it grows (a bigger power is finer), and how much it falls in at the stern
_LEVELS = [(None, 1170, 0.0, 0.55, 0.55), ('knuckle', 1162, 0.008, 0.7, 0.6), (60.0, 1155, 0.022, 0.85, 0.66), (-15.0, 1150, 0.026, 0.9, 0.7),
           (-330.0, 1138, 0.04, 1.1, 0.82), (-560.0, 1040, 0.055, 1.4, 0.92), ('keel', 620, 0.075, 1.8, 1.0), ('keel', 0, 0.075, 1.0, 1.0)]
_STATIONS = [0, 0.004, 0.01, 0.018, 0.026, 0.035, 0.047, 0.06, 0.075, 0.095, 0.12, 0.15, 0.185, 0.22, 0.26, 0.3, 0.34, 0.4, 0.48,
             0.56, 0.64, 0.7, 0.75, 0.79, 0.83, 0.87, 0.905, 0.935, 0.96, 0.98, 0.993, 1.0]


def deck_z(y):
    """The main deck's height at y: the sheer rising to the bow."""
    s = min(1.0, max(0.0, (y + HALF) / LONG))
    return 420.0 + 380.0 * (1 - s) ** 2.2


def _keel(s):
    return KEEL if s < 0.8 else KEEL + (KEEL * -0.62) * ((s - 0.8) / 0.2) ** 1.5


def _width(s, level):
    z, w, stem, power, fall = level
    if s <= stem:
        return 0.0
    t = min(1.0, (s - stem) / (0.36 - stem))
    out = w * math.sin(t * math.pi / 2) ** power
    if s > 0.74:                                    # (the rounded stern, falling in more below)
        r = (s - 0.74) / 0.26
        out *= math.sqrt(max(0.0, 1 - (r * (0.9 + 0.08 * fall)) ** 2)) * (1 - 0.25 * fall * r)
    return out


def section(s):
    """Her section at s (0 bow, 1 stern): [(across, z)] from the deck edge to the keel's middle."""
    y = -HALF + s * LONG
    dz = deck_z(y)
    out = []
    for lv in _LEVELS:
        z = lv[0]
        z = dz if z is None else 0.55 * dz + 0.45 * 60 if z == 'knuckle' else _keel(s) if z == 'keel' else z
        out.append((round(_width(s, lv), 1), round(z, 1)))
    return out


def half_beam(y, z=None):
    """How far out her side is at y, at height z (the deck's when None)."""
    s = min(1.0, max(0.0, (y + HALF) / LONG))
    sec = section(s)
    if z is None:
        return sec[0][0]
    for (a0, z0), (a1, z1) in zip(sec, sec[1:]):
        if z1 <= z <= z0:
            return a0 + (a1 - a0) * ((z0 - z) / (z0 - z1) if z0 != z1 else 0)
    return sec[0][0]


def hull_part():
    return {'shape': 'hull', 'stations': [{'y': -HALF + s * LONG, 'pts': section(s)} for s in _STATIONS],
            'bands': [(-1e9, 'bottom'), (-15.0, 'boot'), (60.0, 'hull')], 'deck_look': 'teak', 'end_look': 'hull', 'material': 'metal', 'far': True}


# ---------- what stands on her ----------

def _box(parts, size, at, look_, turn=None, faces=None, solid=True, far=False, material='metal'):
    p = {'shape': 'box', 'size': [round(v, 1) for v in size], 'at': [round(v, 1) for v in at], 'look': look_, 'solid': solid, 'far': far, 'material': material}
    if turn:
        p['turn'] = turn
    if faces:
        p['faces'] = faces
    parts.append(p)
    return p


def _cyl(parts, r, h, at, look_, r2=None, sides=12, turn=None, scale=None, solid=False, far=False, cap=None, caps=True):
    p = {'shape': 'cylinder', 'r': r, 'h': h, 'sides': sides, 'at': [round(v, 1) for v in at], 'look': look_, 'solid': solid, 'far': far, 'material': 'metal'}
    if r2 is not None:
        p['r2'] = r2
    if turn:
        p['turn'] = turn
    if scale:
        p['scale'] = scale
    if cap:
        p['cap_look'] = cap
    if not caps:
        p['caps'] = False
    parts.append(p)
    return p


def _house(parts, y0, y1, wide, z0, high, look_='super', top='deck', far=True, faces=None):
    f = {'top': top}
    f.update(faces or {})
    return _box(parts, [wide, y1 - y0, high], [0, (y0 + y1) / 2, z0], look_, faces=f, far=far)


FUNNEL1, MAINMAST, FUNNEL2 = 250.0, 770.0, 1270.0     # (along her: all three on 03 aft, -410 to 1700. The after funnel
                                                    # stood at 1620 and reached 90 past 03 aft's end, over the roof below)
GUN_LONG = 1650.0          # (a 16-inch/50: 20 m of barrel, the last 18 out of the turret)


def _round_house(parts, y0, y1, wide, z0, high, look_='super', top='deck', far=True, sides=8):
    """A level of the superstructure with its corners cut: an eight-sided house from y0 to y1 (its flats fore, aft and
    to the sides), as the Iowas' are, rounded rather than boxed."""
    k = 1 / math.cos(math.pi / sides)
    # (the ring turned by 'phase' before it is stretched: turned after, as it was, every house lay skewed across the deck
    # and its ladders ran into the next one's walls)
    p = _cyl(parts, 100, high, [0, (y0 + y1) / 2, z0], look_, sides=sides, scale=[wide / 200 * k, (y1 - y0) / 200 * k, 1],
                solid=True, far=far, cap=top)
    p['phase'] = (90.0 - 180.0 / sides) % (360.0 / sides)      # (a flat to the fore and aft, whatever the number of sides)
    return p


def _trained(parts, first, y, deg):
    """The parts from index `first` on turned by deg about the upright through (0, y): a turret trained round."""
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    for p in parts[first:]:
        x0, y0, z0 = p['at']
        dy = y0 - y
        p['at'] = [round(x0 * c - dy * s, 1), round(y + x0 * s + dy * c, 1), z0]
        t = list(p.get('turn') or [0, 0, 0])
        p['turn'] = [t[0], t[1], t[2] + deg]


def turret(parts, y, z0, aft=False, elev=5.0, train=0.0, droop=None):
    """A 16-inch turret on its barbette: the gun house, its rangefinder's hoods, three guns and their canvas. train:
    the house turned that many degrees (towards port when positive); droop: the gun (0, 1, 2 from starboard) whose
    barrel hangs down."""
    d = 1 if aft else -1
    _cyl(parts, 540, z0 - deck_z(y) + 20, [0, y, deck_z(y) - 20], 'armour', sides=20, solid=True, far=True)
    first = len(parts)
    _box(parts, [880, 900, 260], [0, y + d * 80, z0], 'armour', faces={'top': 'deck'}, far=True)
    _box(parts, [800, 220, 230], [0, y - d * 470, z0], 'armour', turn=[-d * 22, 0, 0], faces={'top': 'armour'}, far=True)
    _cyl(parts, 440, 252, [0, y + d * 520, z0], 'armour', sides=16, scale=[1.0, 0.55, 1.0], solid=True, far=True, cap='deck')
    for sx in (-1, 1):
        _box(parts, [90, 240, 70], [sx * 400, y + d * 380, z0 + 260], 'armour', solid=False)
    for k, gx in enumerate((-220, 0, 220)):
        el = -6.0 if k == droop else elev
        base = [gx, y - d * 520, z0 + 130]
        _cyl(parts, 86, 130, base, 'canvas', sides=12, turn=[90 - el, 0, 180 if aft else 0])
        _cyl(parts, 58, GUN_LONG, base, 'gun', r2=33, sides=12, turn=[90 - el, 0, 180 if aft else 0], far=True)
        reach = GUN_LONG * math.sin(math.radians(90 - el))
        _cyl(parts, 40, 70, [gx, y - d * (520 + reach - 50), z0 + 130 + GUN_LONG * math.cos(math.radians(90 - el)) - 3], 'gun', sides=12, turn=[90 - el, 0, 180 if aft else 0])
    if train:
        _trained(parts, first, y, train)


def twin_five(parts, x, y, z, face, askew=None):
    """A twin 5-inch/38 mount: its rounded house and two barrels; face: the way the guns point (degrees, 0 = forward).
    askew (roll, pitch): knocked off its roller path by the blast, the house leaning, one barrel bent down."""
    tilt = askew or (0.0, 0.0)
    _box(parts, [300, 340, 160], [x, y, z - (10 if askew else 0)], 'armour', turn=[tilt[1], tilt[0], face], faces={'top': 'deck'})
    a = math.radians(face)
    for k, gx in enumerate((-70, 70)):
        ox, oy = gx * math.cos(a), gx * math.sin(a)
        fx, fy = -math.sin(a) * -170, math.cos(a) * -170
        down = (k == 1 and askew) and 18 or 0
        _cyl(parts, 13, 420, [x + ox + fx, y + oy + fy, z + 90], 'gun', sides=8, turn=[85 + down + tilt[1], tilt[0], face])


def ciws(parts, x, y, z, wrecked=False):
    """A Phalanx: its pedestal, the white dome, the gun under it. wrecked: the dome and gun gone, the mount burnt."""
    if wrecked:
        _cyl(parts, 70, 90, [x, y, z], 'soot', sides=10, solid=True)
        _cyl(parts, 40, 50, [x, y, z + 90], 'soot', sides=8, turn=[12, 8, 0])
        return
    _cyl(parts, 70, 90, [x, y, z], 'deck', sides=10, solid=True)
    _cyl(parts, 64, 90, [x, y, z + 90], 'white', sides=12)
    _box(parts, [16, 16, 16], [x, y, z + 180], 'white', solid=False)
    p = {'shape': 'ball', 'r': 66, 'sides': 10, 'rings': 5, 'at': [x, y, z + 140], 'look': 'white', 'solid': False}
    parts.append(p)
    _cyl(parts, 9, 160, [x, y - 50, z + 150], 'dark', sides=6, turn=[80, 0, 0])


LADDER_RUN = 1.25      # (along for each unit up: 39 degrees. At 1.05 (44) the ramps were steeper than walkcheck's 40, and
                        # nothing walked her levels)


def ladder(parts, x, y_foot, z_foot, y_top, z_top, wide=110, x_top=None):
    """An inclined ladder from (x, y_foot, z_foot) up to (x_top, y_top, z_top) (x_top: x, a ladder along the ship): treads
    and rails to see, a ramp under them to walk."""
    x_top = x if x_top is None else x_top
    dx, dy, rise = x_top - x, y_top - y_foot, z_top - z_foot
    run = math.hypot(dx, dy)
    ln = math.hypot(run, rise)
    pitch = math.degrees(math.atan2(rise, run))
    yaw = math.degrees(math.atan2(-dx, dy))         # (the ladder's own +y turned to run from its foot to its top)
    mid = ((x + x_top) / 2, (y_foot + y_top) / 2, (z_foot + z_top) / 2)
    # (the ramp: a slab along the slope, its middle under the treads' line)
    _box(parts, [wide, ln, 30], [mid[0], mid[1], mid[2] - 30], 'dark', turn=[pitch, 0, yaw], solid=True)
    steps = max(2, int(rise / 22))
    for k in range(steps):
        t = (k + 0.5) / steps
        _box(parts, [wide - 8, 26, 4], [x + dx * t, y_foot + dy * t, z_foot + rise * t + 1], 'deck', turn=[0, 0, yaw], solid=False)
    across = (dy / run, -dx / run)                  # (square to the ladder, level)
    for sx in (-1, 1):
        _box(parts, [5, ln, 5], [mid[0] + sx * across[0] * wide / 2, mid[1] + sx * across[1] * wide / 2, mid[2] + 80], 'dark', turn=[pitch, 0, yaw], solid=False)


STANCHION_APART = 110.0


def rails(parts, gaps=()):
    """Lifelines and stanchions round the main deck's edge, but at the gaps (a gangway's, (y0, y1)): solid, waist high."""
    st = [-HALF + s * LONG for s in _STATIONS]
    cuts = sorted(set(st) | {g for gap in gaps for g in gap})          # (a gap's ends are where a rail stops, wherever they fall)
    for sgn in (-1, 1):
        for a, b in zip(cuts, cuts[1:]):
            if b - a < 1 or any(g0 - 0.5 <= a and b <= g1 + 0.5 for g0, g1 in gaps):
                continue
            xa, xb = sgn * (half_beam(a) - 12), sgn * (half_beam(b) - 12)
            za, zb = deck_z(a), deck_z(b)
            if abs(xa) < 30 and abs(xb) < 30:
                continue
            dx, dy, dz = xb - xa, b - a, zb - za
            ln = math.sqrt(dx * dx + dy * dy + dz * dz)
            yaw = math.degrees(math.atan2(-dx, dy))
            pitch = math.degrees(math.atan2(dz, math.hypot(dx, dy)))
            for hgt in (38, 72):
                _box(parts, [4, ln, 4], [(xa + xb) / 2, (a + b) / 2, (za + zb) / 2 + hgt], 'white', turn=[pitch, 0, yaw], solid=False)
            _box(parts, [30, ln, 90], [(xa + xb) / 2, (a + b) / 2, (za + zb) / 2 - 10], None, turn=[pitch, 0, yaw], solid=True)   # (what stops a walker)
            _cyl(parts, 4, 76, [xa, a, za], 'white', sides=5)
            for k in range(1, int(ln / STANCHION_APART)):            # (a stanchion every metre and a half between)
                t = k / int(ln / STANCHION_APART)
                _cyl(parts, 3, 76, [xa + dx * t, a + dy * t, za + dz * t], 'white', sides=4)


def missouri():
    """The Missouri: see the module's docstring."""
    parts = [hull_part()]
    Z1 = deck_z(-2150) + 270                        # the 01 level's roof
    Z2 = Z1 + 260
    Z3 = Z2 + 250
    Z4 = Z3 + 240
    Z5 = Z4 + 250
    Z6 = Z5 + 250
    Z7 = Z6 + 250
    Z8 = Z7 + 250
    # turrets One and Two forward, Three aft
    turret(parts, -3970, deck_z(-3970) + 90, droop=1)                 # (One: her middle gun hangs, its elevating gear gone)
    turret(parts, -2760, deck_z(-2760) + 330, train=90.0)             # (Two: trained hard to port, towards the flash)
    turret(parts, 4540, deck_z(4540) + 90, aft=True)
    # the superstructure in levels
    base = deck_z(3000) - 40
    _house(parts, -2150, 3000, 1640, base, Z1 - base)                 # 01
    _round_house(parts, -2100, 1900, 1150, Z1, Z2 - Z1, sides=10)                          # 02
    _round_house(parts, -2050, -760, 880, Z2, Z3 - Z2)                                    # 03 (its after end clear of 03 aft: a ladder between)
    _cyl(parts, 330, Z4 - Z2 + 20, [0, -1780, Z2 - 10], 'armour', sides=16, scale=[1.25, 1.0, 1.0], solid=True, far=True, cap='deck')   # conning tower
    _round_house(parts, -2100, -1100, 820, Z3, Z4 - Z3, look_='windows_blown', sides=12)  # 04: the pilot house, its windows blown in
    _box(parts, [1700, 260, 22], [0, -1700, Z3 - 18], 'deck', faces={'top': 'teak'})        # bridge wings (4 over 03's roof: walked onto, no step)
    for sx in (-1, 1):
        _box(parts, [8, 260, 70], [sx * 850, -1700, Z3 + 4], 'white', solid=True)
        # (a catwalk from 03's roof by the bridge door forward to each wing, beside the pilot house: without it the way
        # was the 30 between the pilot house and 03's edge, narrower than anyone, and walkcheck reached neither wing)
        _box(parts, [200, 540, 22], [sx * 520, -1330, Z3 - 18], 'deck', faces={'top': 'teak'})
        _box(parts, [8, 540, 70], [sx * 616, -1330, Z3 + 4], 'white', solid=True)
    # the fire-control tower: four levels narrowing, a platform round each, the main battery director on top
    for z0, z1, y0, y1, w in ((Z4, Z5, -1760, -1120, 720), (Z5, Z6, -1720, -1160, 620), (Z6, Z7, -1680, -1200, 540), (Z7, Z8, -1640, -1240, 460)):
        _round_house(parts, y0, y1, w, z0, z1 - z0)
        _box(parts, [w + 220, y1 - y0 + 160, 16], [0, (y0 + y1) / 2, z1 - 12], 'deck', solid=False)   # (its top 4 over the level's roof: one flush with it flickered)
        for sx in (-1, 1):
            _box(parts, [4, y1 - y0 + 160, 4], [sx * (w / 2 + 108), (y0 + y1) / 2, z1 + 60], 'white', solid=False)
        _box(parts, [w + 220, 4, 4], [0, y0 - 78, z1 + 60], 'white', solid=False)
    _cyl(parts, 160, 260, [0, -1150, Z4], 'super', sides=12, solid=False)      # (the trunk at the tower's back)
    _box(parts, [440, 460, 210], [0, -1460, Z8], 'armour', faces={'top': 'deck'}, far=True)     # the main battery director
    _box(parts, [1000, 90, 90], [0, -1440, Z8 + 110], 'dark', solid=False, far=True)
    _box(parts, [320, 30, 160], [0, -1400, Z8 + 210], 'dark', solid=False)
    # the foremast: its tripod bent back by the blast, the pole leaning far aft over the funnel, its yards and radars gone
    _cyl(parts, 34, 420, [0, -1200, Z8], 'dark', sides=8, far=True)
    _cyl(parts, 34, 1250, [0, -1200, Z8 + 410], 'rust', sides=8, turn=[-38, 0, 0], far=True)
    for sx in (-1, 1):
        _cyl(parts, 22, 700, [sx * 260, -1200, Z6], 'dark', sides=6, turn=[-8, sx * -9, 0])
        _cyl(parts, 22, 520, [sx * 150, -1200 + 700 * math.sin(math.radians(8)), Z6 + 690], 'rust', sides=6, turn=[-55, sx * -20, 0])
    _box(parts, [600, 24, 24], [0, -1200 + 780 * math.sin(math.radians(38)) + 30, Z8 + 410 + 780 * math.cos(math.radians(38))], 'rust', turn=[0, 14, 0], solid=False)
    _round_house(parts, -410, 1700, 760, Z2, Z3 - Z2)                                      # 03 aft, round the funnels (the 02 level's end clear aft of it)
    # the first funnel, the mainmast, the second funnel
    _cyl(parts, 340, 1150, [0, FUNNEL1, Z3 - 10], 'super', sides=16, scale=[0.78, 1.35, 1.0], far=True, cap='soot', solid=True)
    _cyl(parts, 346, 150, [0, FUNNEL1, Z3 + 1010], 'soot', sides=16, scale=[0.78, 1.35, 1.0], caps=False)   # (open: its cap is funnel_cap's)
    for sx in (-1, 1):                                                                   # searchlight platforms on its sides
        _box(parts, [220, 260, 16], [sx * 380, FUNNEL1, Z3 + 600], 'deck', solid=False)
        _cyl(parts, 50, 70, [sx * 400, FUNNEL1, Z3 + 616], 'dark', sides=8)
    # the mainmast: snapped off above 03 aft and fallen to starboard, across the roof's edge and out over her side
    _cyl(parts, 34, 250, [0, MAINMAST, Z3], 'dark', sides=8, far=True)
    _cyl(parts, 34, 2400, [0, MAINMAST + 20, Z3 + 250], 'rust', sides=8, turn=[0, -121.5, 0], far=True)
    for sx in (-1, 1):
        _cyl(parts, 22, 380, [sx * 300, MAINMAST, Z3], 'dark', sides=6, turn=[0, sx * -11, 0])
    _box(parts, [520, 420, 20], [-1380, MAINMAST + 60, Z3 - 560], 'rust', turn=[8, -40, 6], solid=False)     # (its platform, hanging off it)
    _cyl(parts, 326, 1000, [0, FUNNEL2, Z3 - 10], 'super', sides=16, scale=[0.78, 1.3, 1.0], far=True, cap='soot', solid=True)
    _cyl(parts, 332, 140, [0, FUNNEL2, Z3 + 860], 'soot', sides=16, scale=[0.78, 1.3, 1.0], caps=False)
    # the after superstructure and director
    _round_house(parts, 1900, 3050, 1000, Z1, 250)
    _box(parts, [360, 380, 420], [0, 2650, Z1 + 250], 'armour', faces={'top': 'deck'}, far=True)
    _box(parts, [760, 80, 70], [0, 2650, Z1 + 560], 'dark', solid=False)
    # ten twin 5-inch mounts on the 01 level, five a side
    for k, y in enumerate((-1500, -950, -400, 150, 700)):
        for sx in (-1, 1):
            face = sx * (-25 if k < 2 else -70 if k < 4 else -110)
            if sx > 0:                                  # (the port mounts, the flash's side: knocked off their roller paths)
                face += (37, -52, 24, 61, -33)[k]
            twin_five(parts, sx * 740, y, Z1, face, askew=((7, -4), (-5, 6), (9, 3), (-6, -7), (4, 8))[k] if sx > 0 else None)
    # Tomahawk launchers and Harpoon canisters amidships, four Phalanx (all on what is under them: the after Phalanx
    # stood half off the 02 level's end, over a ladder, and read as a funnel hanging in the air)
    for sx in (-1, 1):
        # (narrow, against the director's sides: 30 from it, they shut the roof's after part off, but for a ledge)
        # (the Tomahawk boxes crushed down and burnt out; the Harpoon canisters burst, two of each four thrown askew)
        _box(parts, [150, 300, 80], [sx * 256, 2620, Z1 + 250], 'soot', turn=[sx * 6, 0, sx * 4], faces={'front': 'soot'})
        for k in range(4):
            if k == 3 and sx > 0:
                continue
            _cyl(parts, 32, 520, [sx * (380 + k * 70), 1250 + (k % 2) * 40, Z2 + 30], 'soot', sides=8,
                 turn=[90 + (k % 2) * 12, 0, (k % 2) * sx * 18], caps=True)
        ciws(parts, sx * 520, -1050, Z2, wrecked=True)
        ciws(parts, sx * 240, 2150, Z1 + 250, wrecked=True)
    # the way up, walked: deck to 01 at its after end; 01 up the after superstructure's side onto its roof (10 under the
    # 02 level, which it meets: step on forward); 02 up to 03 between the two 03 houses; the bridge wings are 03's level.
    # (before, the 01-02 ladder's foot was inside the after superstructure and the 02-03 one's inside 03 aft)
    for sx in (-1, 1):
        # (its foot on the deck where it is, the sheer falling aft; its top 10 inside the 01 level's end, so the ramp's cut
        # end is in the level, not a lip in the air at its edge)
        foot = 2990 + (Z1 - deck_z(3000)) * LADDER_RUN
        ladder(parts, sx * 520, foot, deck_z(foot) - 2, 2990, Z1)
        # (01 up to the after superstructure's roof: along its side, foot on open 01 deck aft, top on a landing that
        # reaches over the roof's edge. It ran across her before, its foot on the 01 level's last 20 units, and nobody
        # could get onto it: laddercheck found no deck under its foot)
        ladder(parts, sx * 562, 2300 + 250 * LADDER_RUN, Z1, 2300, Z1 + 250)
        _box(parts, [150, 130, 20], [sx * 545, 2245, Z1 + 230], 'deck', solid=True)
    ladder(parts, 0, -770 + (Z3 - Z2) * LADDER_RUN, Z2, -770, Z3, wide=130)     # (its top 10 inside 03, which ends at -760)
    # the forecastle: anchor chains to the windlasses, the breakwater, bitts, the jackstaff
    for sx in (-1, 1):
        _box(parts, [36, 1500, 14], [sx * 230, -7550, deck_z(-7550) + 1], 'rust', turn=[-3.5, 0, sx * -5], solid=False)
        _cyl(parts, 80, 70, [sx * 290, -6750, deck_z(-6750)], 'dark', sides=12, cap='deck', solid=True)
        _box(parts, [900, 40, 140], [sx * 380, -5600, deck_z(-5600) - 10], 'super', turn=[0, 0, sx * 28], faces={'top': 'deck'})
        for y in (-8300, -6200, -4700, 6000, 7600):
            hb = half_beam(y) - 110
            for dy in (-40, 40):
                _cyl(parts, 22, 50, [sx * hb, y + dy, deck_z(y)], 'dark', sides=8)
        # the anchors in their hawse pipes, the numbers on the bows
        ya, za = -8150, deck_z(-8150) - 260
        xa = half_beam(ya, za)
        lean = math.degrees(math.atan2(half_beam(ya) - half_beam(ya, 60.0), deck_z(ya) - 60.0))
        taper = math.degrees(math.atan2(half_beam(ya + 300, za) - half_beam(ya - 300, za), 600))
        _box(parts, [40, 120, 200], [sx * (xa + 8), ya, za - 100], 'rust', turn=[0, sx * lean, sx * -taper], solid=False)
        yn, zn = -7300, deck_z(-7300) - 520
        # (laid on her side as it leans there: at 0.6 of the lean its top half was inside her flare, 18 Nov 2026)
        _side_decal(parts, yn, zn, zn + 420, 900, 'number', sx, off=6.0)
        parts[-1]['far'] = True
    _cyl(parts, 8, 650, [0, -9380, deck_z(-9380)], 'dark', sides=5)
    _cyl(parts, 8, 600, [0, 9380, deck_z(9380)], 'dark', sides=5)
    # the fantail: the crane toppled to starboard, its post lying across the deck, the boom along it aft
    dz = deck_z(8300)
    _cyl(parts, 70, 90, [0, 8300, dz], 'super', sides=10, solid=True)                          # (the stump of its post)
    _cyl(parts, 70, 520, [-40, 8300, dz + 70], 'rust', sides=10, turn=[0, -90, 0])              # (the post, lying)
    _box(parts, [150, 150, 90], [-610, 8310, dz], 'rust', turn=[0, 0, 23], solid=False)          # (its turntable)
    _box(parts, [70, 800, 70], [-300, 8760, dz + 4], 'rust', turn=[2, 6, -4], solid=False)     # (the boom, along the deck)
    # the surrender plaque, starboard on the 01 level beside turret Two
    _box(parts, [150, 100, 3], [-720, -2000, Z1], 'plaque', solid=False)
    fittings(parts, Z1, Z2, Z3)
    damage(parts, Z1, Z2, Z3, Z8)
    rails(parts, gaps=(SPOTS['gangway_gap'],))
    _door_frame(parts, SPOTS['qd'][0], SPOTS['qd'][1], SPOTS['qd'][2])
    _door_frame(parts, SPOTS['bridge'][0], SPOTS['bridge'][1], Z3)
    return {'name': 'FOLabShipMissouri', 'looks': _looks(), 'parts': parts, 'levels': [Z1, Z2, Z3, Z4, Z5, Z6, Z7, Z8]}


# where the way aboard comes up the side (the quarterdeck, aft of the superstructure), and the doors in (all in her frame)
SPOTS = {
    'gangway_gap': (3300.0, 3700.0),
    'gangway_y': 3500.0,
    'qd': (300.0, 3000.0, deck_z(3000.0)),        # (the door in from the quarterdeck: on the 01 level's after face)
    'bridge': (0.0, -1100.0),                      # (the pilot house's after face, on the 03 level's roof)
}


def funnel_cap(parts, y, z_top, r, scale, floor):
    """A funnel's top as hers are: a lip round the rim, a grating across the opening, the exhaust pipes standing up out
    of it, black with soot."""
    _cyl(parts, r + 12, 14, [0, y, z_top], 'soot', sides=16, scale=scale, caps=False)
    _cyl(parts, r + 4, 4, [0, y, floor + 2], 'soot', sides=16, scale=scale, cap='soot', caps=True)     # (the dark inside, down in the band)
    for gx in (-0.45, 0.0, 0.45):
        _box(parts, [8, 2 * r * scale[1] * 0.9, 10], [gx * r * scale[0], y, z_top - 12], 'dark', solid=False)
    for px, py_, pr in ((-0.35, -0.35, 52), (0.35, -0.35, 52), (0.0, 0.3, 64), (-0.3, 0.55, 34), (0.3, 0.55, 34)):
        _cyl(parts, pr, 150, [px * r * scale[0], y + py_ * r * scale[1], z_top - 40], 'soot', sides=10, cap='soot')
        _cyl(parts, pr + 6, 10, [px * r * scale[0], y + py_ * r * scale[1], z_top + 100], 'rust', sides=10, caps=False)


def fittings(parts, Z1, Z2, Z3):
    """What a real deck is cluttered with: mushroom vents and hatches on the forecastle and fantail, life-raft canisters
    in racks along the 01 level's sides, pipes run along its walls; and the funnels' caps."""
    for y, x in ((-6300, 600), (-5000, 680), (-4700, 300), (5600, 700), (6500, 600), (7200, 480), (6900, 0)):
        for sx in ((-1, 1) if x else (1,)):
            z = deck_z(y)
            _cyl(parts, 24, 62, [sx * x, y, z], 'dark', sides=10)
            _cyl(parts, 44, 16, [sx * x, y, z + 62], 'deck', sides=12, solid=False)              # (its mushroom cap)
    for y, x in ((-6200, 380), (-4900, 0), (5300, 380), (6100, 0), (7700, 380)):
        for sx in ((-1, 1) if x else (1,)):
            z = deck_z(y)
            _box(parts, [130, 170, 22], [sx * x, y, z], 'dark', faces={'top': 'deck'})          # a hatch, dogged down
            _box(parts, [16, 120, 10], [sx * x - 70 * sx, y, z], 'rust', solid=False)          # (its hinges)
    for sx in (-1, 1):
        for y in (-1800, -1150, -500, 150, 800, 1450):
            z = deck_z(y)
            x = sx * 885
            _box(parts, [70, 300, 10], [x, y, z], 'dark', solid=False)
            for px in (-130, 130):
                _box(parts, [8, 8, 150], [x, y + px, z], 'dark', solid=False)
            for k, (cz, cy) in enumerate(((40, -70), (40, 70), (104, -70), (104, 70))):
                if (y + k * 37) % 5 == 1:
                    continue                                                                       # (one gone, here and there)
                _cyl(parts, 30, 120, [x, y + cy + 60, z + cz - 30 + 30], 'white', sides=10, turn=[90, 0, 0])
        for zz in (150, 192):
            _cyl(parts, 6, 5000, [sx * 826, 2900, deck_z(2900) + zz], 'dark', sides=6, turn=[90, 0, 0], caps=False)
        for y in range(-2000, 2900, 450):
            _box(parts, [12, 10, 70], [sx * 824, y, deck_z(y) + 140], 'dark', solid=False)
    funnel_cap(parts, FUNNEL1, Z3 + 1160, 340, (0.78, 1.35, 1.0), Z3 + 1140)
    funnel_cap(parts, FUNNEL2, Z3 + 1000, 326, (0.78, 1.3, 1.0), Z3 + 990)


def _side_decal(parts, y, z0, z1, long, look_, sx=1, off=4.0):
    """A see-through picture laid on her side at y, from z0 up to z1, `long` along her: a sheet leaning and tapering
    as her side does there, `off` proud of it (as the hull number is laid)."""
    zm = (z0 + z1) / 2.0
    x = half_beam(y, z0) + off                      # (its foot on her side at z0; turned about the foot, its top meets her at z1)
    lean = math.degrees(math.atan2(half_beam(y, z1) - half_beam(y, z0), z1 - z0))
    taper = math.degrees(math.atan2(half_beam(y + long / 2, zm) - half_beam(y - long / 2, zm), long))
    # (a turn about y takes up to +x: so +lean leans a port sheet out with her flare. -lean, as the hull number had it,
    # leaned its top into her and only its lower half showed)
    _box(parts, [2, long, z1 - z0], [sx * x, y, z0], None, turn=[0, sx * lean, sx * -taper],
         faces={'right' if sx > 0 else 'left': look_}, solid=False)


def _wall_decal(parts, x, y, z0, z1, long, look_, sx=1):
    """A see-through picture on an upright wall that faces out to sx at x (the 01 level's sides)."""
    _box(parts, [2, long, z1 - z0], [x + sx * 3, y, z0], None, faces={'right' if sx > 0 else 'left': look_}, solid=False)


def _deck_decal(parts, x, y, wide, long, look_):
    """A see-through picture lying on the main deck, along its sheer, 4 over it."""
    pitch = math.degrees(math.atan2(deck_z(y + long / 2) - deck_z(y - long / 2), long))
    _box(parts, [wide, long, 2], [x, y, deck_z(y) + 3], None, turn=[pitch, 0, 0], faces={'top': look_}, solid=False)


def damage(parts, Z1, Z2, Z3, Z8):
    """What the flash and the blast did, laid over her as pictures: her port side (the bomb's, ahead and to port)
    scorched from the bow to amidships, worst forward, with flash shadows of the rails on the 01 level's side and one of
    a man; her forecastle's teak burnt on the port side; a hole torn in her port bow at the waterline; two centuries of
    seabirds on the director and the tower."""
    for y, ln in ((-7400, 500), (-6900, 500), (-6400, 500), (-5900, 500), (-5300, 700), (-4600, 700), (-3900, 700),
                  (-3200, 700), (-2500, 700), (-1800, 700), (-1100, 700), (-400, 700)):
        top = deck_z(y) - 30 if y > -6600 else deck_z(-7300) - 530     # (under her number at the bow: it stays legible)
        _side_decal(parts, y, 80.0, top, ln, 'scorch')
    for y, ln, look_ in ((-1900, 500, 'scorch_rails'), (-1300, 600, 'scorch_person'), (-600, 700, 'scorch_rails'), (100, 600, 'scorch')):
        _wall_decal(parts, 820.0, y, deck_z(y) + 10, Z1 - 10, ln, look_)
    for y in (-6600, -5900, -5200):
        _deck_decal(parts, 0.35 * half_beam(y) + 140, y, 0.5 * half_beam(y), 650, 'burnt_teak')
    _side_decal(parts, -6900, -250.0, 150.0, 520, 'holed', off=9.0)
    for sx in (-1, 1):
        _wall_decal(parts, sx * 220.0, -1460, Z8 + 60, Z8 + 210, 420, 'droppings', sx)
        _wall_decal(parts, sx * 360.0, -1440, Z8 - 240, Z8 - 20, 520, 'droppings', sx)


def _door_frame(parts, x, y, z):
    """A bulkhead door's frame stood proud of an after face at y (the door stands in it, facing aft)."""
    for sx in (-1, 1):
        _box(parts, [18, 22, 210], [x + sx * 84, y + 8, z], 'dark', solid=False)
    _box(parts, [186, 22, 20], [x, y + 8, z + 204], 'dark', solid=False)

PIECES = {'missouri': ('USS Missouri', missouri)}
import waikikiset  # noqa: E402
waikikiset.LIGHTS.update({
    # (deck lights at the gangway and the quarterdeck, one under the bridge wings, a red one high on the foremast)
    'missouri': [('ExtLightWarm02', 900, 3500, 640), ('ExtLightWarm02', -900, 3500, 640), ('ExtLightWarm02', 0, 3150, 700),
                 ('ExtLightWarm02', 0, -1500, 1500), ('NVLightNeonRed', 0, -1200, 4900)],
})
for _k, (_label, _fn) in PIECES.items():
    modelsets.PIECES.setdefault(_k, {'label': _label, 'set': SET, 'file': _k, 'describe': _fn, 'edid': _fn()['name']})
