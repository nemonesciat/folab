"""Surfing and fishing on Waikiki (the user, 21 Nov 2026 night: "surfers out on the breaks with boards, boards leaning on
shacks... fishing spots on piers and reefs: people fishing, and a way for the player to catch fish to cook").

Surfing: FOLab's own surfboard (`board`, a rocked, rounded plank, painted, a box of collision; two colourways), stood up in
the sand beside surfers on Waikiki's beaches (a local with the sandbox package, watching the sea), and leant against
the lifeguard towers. **Not done: surfers out on the breaks.** The game has no paddling or riding animation and an actor
in deep water swims, so a surfer on a board out at sea can't be made with what the game has. Nor a board you carry
(a held board would need its own animation set): asked for "if simple", it isn't.

Fishing: the player catches fish at a fishing spot (an activator: the game's bucket, named "Fishing Spot") at pier ends
and on rocky shore outside the towns; its script gives a Raw Reef Fish seven times in ten, at most once each two hours
of game time, else nothing. Raw Reef Fish (a copy of the game's lakelurk meat, renamed) cooks at any campfire into
Grilled Reef Fish (a copy of the grilled mantis leg) by a recipe of its own in the game's cooking (a copy of the grilled
mantis leg's, one fish in). The game has no fish model: the meat's and the grilled leg's stand in.

    ops(gd, pr, ctx=None)     (ops, files, report): records with their keys taken as planned (activity._Reserve), the
                              surfboard's model and pictures as {path: bytes} for the mod's own files
    apply(server)             one Undo, the files written among the mod's own
Needs numpy/PIL for the board's pictures (DEV_ONLY, as garmentprint): imported where used."""
import json
import math
import struct

import recordio

BOARD_LONG, BOARD_WIDE, BOARD_THICK, ROCKER = 210.0, 54.0, 7.0, 9.0
COLOURS = {'Red': ((214, 64, 52), (250, 240, 220)), 'Teal': ((40, 150, 160), (250, 214, 90))}
FISH_EVERY = 0.08                       # (days of game time between catches at one spot: about two hours)
FISH_CHANCE = 70
BEACH_MOST, LEAN_MOST, FISH_PIER_MOST, FISH_SHORE_MOST = 5, 6, 8, 6
STAND_UP = 80.0                         # (a board on its tail: its middle this over the sand, ~25 of the tail sunk)
SCRIPT = '''scn FOLabFishingSpotScript
float nextcatch
Begin OnActivate
\tif IsActionRef player == 1
\t\tif GameDaysPassed >= nextcatch
\t\t\tset nextcatch to GameDaysPassed + %s
\t\t\tif GetRandomPercent < %d
\t\t\t\tplayer.AddItem FOLabRawReefFish 1
\t\t\tendif
\t\tendif
\tendif
End
''' % (FISH_EVERY, FISH_CHANCE)


# ---------- the surfboard ----------

def _outline(t):
    """Half the board's width at t (-1 tail .. 1 nose): a rounded nose, a squarer tail."""
    if t >= 0:
        return BOARD_WIDE / 2 * max(0.0, 1 - t ** 2.4) ** 0.55
    return BOARD_WIDE / 2 * max(0.0, 1 - (-t) ** 4.0) ** 0.5 * (0.85 + 0.15 * (1 + t))


def board_shapes(tex, normal):
    """The board lying flat, its tail at y = -BOARD_LONG/2, nose at +, deck up (z), bottom at z = 0 in the middle."""
    S, R = 40, 8                            # (stations along, points across each face)
    P, N, UV, I = [], [], [], []

    def vert(x, y, z, nx, ny, nz, u, v):
        P.extend((x, y, z)); N.extend((nx, ny, nz)); UV.extend((u, v))
        return len(P) // 3 - 1
    rows_top, rows_bot = [], []
    for k in range(S + 1):
        t = -1 + 2 * k / S
        y = t * BOARD_LONG / 2
        z0 = ROCKER * t * t
        w = max(_outline(t), 0.6)
        top, bot = [], []
        for j in range(R + 1):
            s = -1 + 2 * j / R
            x = s * w
            crown = BOARD_THICK * (1 - 0.35 * s * s)
            top.append(vert(x, y, z0 + crown, 0, 0, 1, (s + 1) / 2 * 0.5, (t + 1) / 2))
            bot.append(vert(x, y, z0, 0, 0, -1, 0.5 + (s + 1) / 2 * 0.5, (t + 1) / 2))
        rows_top.append(top); rows_bot.append(bot)
    for k in range(S):
        for j in range(R):
            a, b, c, d = rows_top[k][j], rows_top[k][j + 1], rows_top[k + 1][j + 1], rows_top[k + 1][j]
            I.extend((a, b, c, a, c, d))
            a, b, c, d = rows_bot[k][j], rows_bot[k][j + 1], rows_bot[k + 1][j + 1], rows_bot[k + 1][j]
            I.extend((a, c, b, a, d, c))
    for k in range(S):                      # (the rails: each edge's top and bottom joined)
        for j in (0, R):
            a, b, c, d = rows_top[k][j], rows_top[k + 1][j], rows_bot[k + 1][j], rows_bot[k][j]
            I.extend((a, d, c, a, c, b) if j == 0 else (a, b, c, a, c, d))
    # (normals: each corner the mean of its triangles' faces, so the rails and the crown shade round)
    acc = [[0.0, 0.0, 0.0] for _ in range(len(P) // 3)]
    for n in range(0, len(I), 3):
        a, b, c = I[n:n + 3]
        ax, ay, az = P[3 * a:3 * a + 3]
        u = [P[3 * b + q] - (ax, ay, az)[q] for q in range(3)]
        v = [P[3 * c + q] - (ax, ay, az)[q] for q in range(3)]
        f = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        for q in (a, b, c):
            for m in range(3):
                acc[q][m] += f[m]
    N = []
    for v in acc:
        L = math.sqrt(sum(x * x for x in v)) or 1.0
        N.extend(x / L for x in v)
    return [{'p': P, 'n': N, 'uv': UV, 'i': I, 'tex': tex, 'normal': normal, 'gloss': 30.0}]


def board_picture(colour, stripe):
    """The deck (left half) and the bottom (right half): the colour, a stripe down the middle, a lighter rail band."""
    from PIL import Image, ImageDraw
    w, h = 256, 512
    im = Image.new('RGB', (w, h), colour)
    d = ImageDraw.Draw(im)
    for half in (0, w // 2):
        d.rectangle((half + w // 4 - 6, 0, half + w // 4 + 6, h), fill=stripe)          # (the stringer stripe)
        d.rectangle((half, 0, half + 8, h), fill=tuple(min(255, c + 40) for c in colour))
        d.rectangle((half + w // 2 - 8, 0, half + w // 2, h), fill=tuple(min(255, c + 40) for c in colour))
    for y in range(int(h * 0.55), int(h * 0.75), 3):                                     # (wax worn on the deck)
        d.line((10, y, w // 2 - 10, y), fill=tuple(min(255, c + 25) for c in colour))
    return im


def board_files(slug):
    """{path: bytes} for each colourway: the model, its picture, a flat normal map."""
    import dds
    import nifmake
    from PIL import Image
    out = {}
    paths = {}
    flat = Image.new('RGBA', (64, 64), (128, 128, 255, 255))
    normal = 'textures\\folab\\%s\\surf\\board_n.dds' % slug
    out[normal] = dds.compress(dds.encode(64, 64, flat.tobytes()))
    for word, (colour, stripe) in COLOURS.items():
        tex = 'textures\\folab\\%s\\surf\\board_%s.dds' % (slug, word.lower())
        im = board_picture(colour, stripe).convert('RGBA')
        out[tex] = dds.compress(dds.encode(im.size[0], im.size[1], im.tobytes()))
        shapes = board_shapes(tex, normal)
        x0, x1 = -BOARD_WIDE / 2, BOARD_WIDE / 2
        y0, y1 = -BOARD_LONG / 2, BOARD_LONG / 2
        box = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (0.0, BOARD_THICK + ROCKER)]
        faces = [[0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4], [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]]
        rel = 'meshes\\folab\\%s\\surf\\surfboard_%s.nif' % (slug, word.lower())
        out[rel] = nifmake.build('FOLabSurfboard' + word, shapes, [{'points': box, 'faces': faces, 'material': 'wood'}])
        paths[word] = rel
    return out, paths


# ---------- records ----------

def _game(gd, tag, edid):
    f = next((f for f, (_i, r) in gd.forms.items() if r.tag == tag and gd.edid(f) == edid), None)
    if f is None:
        raise ValueError('the game has no %s %s' % (tag, edid))
    return f


def _copy(gd, tag, edid, new_edid, name=None):
    import api_characters as ac
    rec = recordio.load(gd, _game(gd, tag, edid))
    rec['src'] = ''
    rec['copied_from'] = gd.key(_game(gd, tag, edid))
    recordio.set_field(rec, 'EDID', new_edid, label='Editor ID')
    if name is not None:
        if any(s['tag'] == 'FULL' for s in rec['subs']):
            recordio.set_field(rec, 'FULL', name)
        else:
            ac.insert(rec, {'tag': 'FULL', 'label': 'Name', 'kind': 'z', 'value': name})
    return rec


def _stat(gd, edid, model):
    """A STAT of the mod's own: the game's bench's record with the board's model and bounds."""
    rec = _copy(gd, 'STAT', 'Bench01', edid)
    bounds = {'X1': -int(BOARD_WIDE / 2), 'Y1': -int(BOARD_LONG / 2), 'Z1': 0,
              'X2': int(BOARD_WIDE / 2), 'Y2': int(BOARD_LONG / 2), 'Z2': int(BOARD_THICK + ROCKER)}
    for sub in rec['subs']:
        if sub['tag'] == 'OBND':
            for f in sub['fields']:
                f['value'] = bounds.get(f.get('name'), f['value'])
        if sub['tag'] == 'MODL':
            sub['value'] = model[7:]                # (models are named from meshes\)
    rec['subs'] = [sub for sub in rec['subs'] if sub['tag'] not in ('MODT', 'MODS', 'MODD', 'SCRI')]
    return rec


# ---------- where ----------

def _shore(ctx, x, y):
    """Whether open dry ground at (x, y) has the sea within 400 to some side (and which way: a heading to it)."""
    for a in range(0, 360, 30):
        r = math.radians(a)
        for d in (250, 400):
            g = ctx.sp.G.at(x + d * math.sin(r), y + d * math.cos(r))
            if g is not None and g < 0:
                return r
    return None


def ops(gd, pr, ctx=None):
    import activity as A
    import api_scripts
    import library
    ctx = ctx or A.Ctx(gd, pr)
    if 'FOLabRawReefFish' in ctx.edids:
        raise ValueError('the mod already has the fishing (Undo it first)')
    o = A.Out(ctx)
    rep = {'beach': [], 'lean': [], 'fish': [], 'not done': ['surfers out on the breaks (no paddling or riding animation: an actor in deep water swims)',
                                                              'a board you can carry (it would need a held animation set)']}
    slug = library.slug(pr.name)
    files, models = board_files(slug)
    boards = {w: o.keys.add(_stat(gd, 'FOLabSurfboard' + w, m)) for w, m in models.items()}
    # the fish, the grilled fish, the recipe
    raw = _copy(gd, 'ALCH', 'LakelurkMeat', 'FOLabRawReefFish', 'Raw Reef Fish')
    raw_key = o.keys.add(raw)
    grilled = _copy(gd, 'ALCH', 'NVGrilledMantis', 'FOLabGrilledReefFish', 'Grilled Reef Fish')
    grilled_key = o.keys.add(grilled)
    rcpe = _copy(gd, 'RCPE', 'RecipeGrilledMantisLeg', 'FOLabRecipeGrilledReefFish', 'Grilled Reef Fish')
    count = next(sub for sub in rcpe['subs'] if sub['tag'] == 'RCQY')
    head = [sub for sub in rcpe['subs'] if sub['tag'] in ('EDID', 'FULL', 'DATA')]
    rcpe['subs'] = head + [dict(next(sub for sub in rcpe['subs'] if sub['tag'] == 'RCIL'), value=raw_key), json.loads(json.dumps(count)),
                           dict(next(sub for sub in rcpe['subs'] if sub['tag'] == 'RCOD'), value=grilled_key), json.loads(json.dumps(count))]
    o.keys.add(rcpe)
    # the fishing spot: its script compiled against the fish not yet in the mod
    script_key = A._new_key(pr)
    sc = api_scripts.scripts()
    c = sc.compile(SCRIPT, script_key, 'object', {raw_key: raw})
    if not hasattr(c, 'subrecords'):
        raise ValueError('the fishing script does not compile: %s' % (c,))
    o.ops.append({'op': 'record', 'key': script_key, 'record': sc._record_of(c, 'FOLabFishingSpotScript')})
    spot = _copy(gd, 'ACTI', 'BisonSteveSign', 'FOLabFishingSpot', 'Fishing Spot')
    for s in spot['subs']:
        if s['tag'] == 'MODL':
            s['value'] = gd.describe(_game(gd, 'MSTT', 'Bucket01'))[3]
        if s['tag'] == 'SCRI':
            s['value'] = script_key
    bucket = recordio.load(gd, _game(gd, 'MSTT', 'Bucket01'))
    spot['subs'] = [next((b for b in bucket['subs'] if b['tag'] == 'OBND'), s) if s['tag'] == 'OBND' else s for s in spot['subs']]
    spot_key = o.keys.add(spot)
    # surfers and boards on Waikiki's beaches
    mx, my = ctx.mid
    tries = 0
    for r in range(4000, int(ctx.WAIKIKI_R * 1.4), 700):
        for k in range(36):
            if len(rep['beach']) >= BEACH_MOST:
                break
            a = math.radians(k * 10 + r % 13)
            x, y = mx + r * math.sin(a), my + r * math.cos(a)
            if any(math.hypot(x - p[0], y - p[1]) < 1500 for p in rep['beach']):
                continue
            sea = _shore(ctx, x, y)
            if sea is None:
                continue
            s = ctx.spot(x, y, apart=200.0)
            if not s:
                continue
            word = list(COLOURS)[len(rep['beach']) % len(COLOURS)]
            bx, by = x + 70 * math.cos(sea), y - 70 * math.sin(sea)
            bz = ctx.sp.G.at(bx, by) or s[2]
            if o.add(boards[word], bx, by, bz + STAND_UP, sea, 'board in the sand'):
                o.ops[-1]['p'][3] = -1.35            # (stood on its tail, leaning a little back, its tail in the sand)
            o.marker('watch', s[0], s[1], s[2], sea)
            o.person('surfer', s[0], s[1], s[2], sea)
            rep['beach'].append([round(x), round(y)])
    # boards leant on the lifeguard towers
    for p in ctx.of('FOLabWaikikiLifeguardTower')[:LEAN_MOST]:
        s = ctx.around(p[0], p[1], 1, radii=(160, 220, 280), turns=12, apart=80.0)
        if not s:
            continue
        x, y, z = s[0]
        towards = A.facing((x, y), p[:2])
        if o.add(boards[list(COLOURS)[len(rep['lean']) % 2]], x, y, z + STAND_UP, towards + math.pi, 'board on a tower'):
            o.ops[-1]['p'][3] = -1.30
        rep['lean'].append([round(x), round(y)])
    # fishing spots: pier ends (the fishers' piers and others), then rocky shore outside the towns
    for g in A.clusters(ctx.of(*A.DOCK), reach=700.0):
        if len([f for f in rep['fish'] if f[2] == 'pier']) >= FISH_PIER_MOST or len(g) < 6:
            continue
        gx, gy = A.middle_of(g)
        if not ctx.safe_from(gx, gy) and math.hypot(gx - mx, gy - my) > ctx.WAIKIKI_R:
            continue
        land = min(g, key=lambda p: -(ctx.sp.G.at(p[0], p[1]) or -9999))
        far = sorted(g, key=lambda p: -math.hypot(p[0] - land[0], p[1] - land[1]))
        for p in far[:6]:
            d = ctx.deck(p)
            if d:
                o.add(spot_key, d[0], d[1], d[2], A.facing(land[:2], d[:2]), 'fishing spot')
                rep['fish'].append([round(d[0]), round(d[1]), 'pier'])
                break
    people = [p for n, ps in ctx.refs.items() if n.startswith('FOLab') for _c, p in ps]
    for cx, cy in sorted(ctx.grid):
        if len([f for f in rep['fish'] if f[2] == 'shore']) >= FISH_SHORE_MOST:
            break
        x, y = (cx + 0.5) * 4096.0, (cy + 0.5) * 4096.0
        if not ctx.safe_from(x, y) or any(math.hypot(x - f[0], y - f[1]) < 12000 for f in rep['fish']):
            continue
        if any(math.hypot(x - p[0], y - p[1]) < 1500 for p in people[::5]):
            continue
        sea = _shore(ctx, x, y)
        if sea is None:
            continue
        s = ctx.spot(x, y, apart=200.0)
        if s:
            o.add(spot_key, s[0], s[1], s[2], sea, 'fishing spot')
            rep['fish'].append([round(x), round(y), 'shore'])
    out, rep = o.done(rep)
    return out, files, rep


def apply(server, ctx=None):
    import library
    o, files, rep = ops(server.GD, server.PR, ctx)
    root = library.assets_dir(server.PR)
    for rel, data in files.items():
        library._put(root, rel, data)
    server.PR.apply('Surfing and fishing', o)
    return rep
