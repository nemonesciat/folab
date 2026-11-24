"""Inside the great Vespid hive (the user, 23 Nov 2026: "interior images of wasp nests with honeycomb network, layers,
maybe incorporate glowing green honeycombs, eggs, veins ... make it light the inside of the cave up too"): a place of the
mod's own behind the great hive's salvaged door, laid by FOLab's cave planner (kocave.make: the game's cave kit, walked,
a way out at the kit's own cave mouth) and then made a nest:

- **Re-dressed.** Every cave piece it uses is copied as a model of the mod's own (`hive\\cave\\`) with the kit's rock
  pictures swapped for FOLab's (`CAVE_TEXTURES`): walls of swirled paper, scallop over scallop as a nest's inside is
  (`wall_picture`), green veins in their glow pictures, paper drips for the stalactites, a floor of dropped paper and
  larva casings. A STAT of the mod's own for each.
- **Comb.** Stacks of comb tiers (`comb_desc`, as a nest built in a hollow tree: tier over tier on stalks), the cells lit
  green from within and pale eggs in some (hiveset.comb), stood on the floor the walk found, `COMB_EVERY` squares apart,
  more in the queen's chamber; each with the game's green cave light (`LIGHT`) by it, so the comb lights the tunnels.
- **Who.** The queen in the square furthest from the mouth, her chamber's cache (`CHAMBER`) beside her; Vespids on the way in.
- **The way out** linked both ways to the great hive's door outside (vespidhives: OffDoorMetalDoor01EXTERIOR in its mouth).

    pictures()                    {path: bytes}: the cave's pictures
    piece_files(gd, keys)         {path: bytes} and {piece key: its copy's model path}
    plan(gd, seed)                the cave (kocave.make) with its comb, lights, queen, cache and Vespids
    ops(gd, cave, ...)            ops for the place, its pieces, things and the door links
"""
import functools
import math
import random

import hiveset

TEX = hiveset.TEX
CAVE_MESH = 'meshes\\folab\\hive\\cave\\%s'
# the kit's pictures -> FOLab's (by the name's start, case aside); normal maps likewise; '_p' (parallax) left as it is
CAVE_TEXTURES = {
    'textures\\dungeons\\caves\\caverockwall': 'cave_wall',
    'textures\\dungeons\\caves\\cavedetails': 'cave_wall',
    'textures\\dungeons\\caves\\cavestalactite': 'cave_drip',
    'textures\\dungeons\\caves\\cavesandyfloor': 'cave_floor',
    'textures\\dungeons\\caves\\cavesmoothfloor': 'cave_floor',
    'textures\\dungeons\\caves\\cavesulfurrockwall': 'cave_wall',      # (the kit's sulfur pieces: yellow, otherwise the same)
    'textures\\dungeons\\caves\\cavesulfurdetails': 'cave_wall',
    'textures\\dungeons\\caves\\cavesulfurstalactite': 'cave_drip',
    'textures\\dungeons\\caves\\cavesulfursandyfloor': 'cave_floor',
    'textures\\dungeons\\caves\\cavesulfursmoothfloor': 'cave_floor',
}
GLOWING = ('cave_wall', 'cave_drip')
GLOW_MULT = 1.0
SIZE = (9, 7)                   # (squares of 512: the cave planner's area)
COMB_EVERY = 3                  # (squares between comb stacks on the way in)
CHAMBER_COMBS = 3
LIGHT = 'NVCaveLightGreen'
CELL_FROM = 'BrocFlowerCave'    # (a game cave's place record: its lighting and sounds, made the nest's)
NAME = 'The Great Hive'
DOOR = 'OffDoorMetalDoor01EXTERIOR'
VESPIDS = 5
SEED = 50
# every other hive's small inside (the user, 23 Nov 2026: "all the hives were to be dungeons ... one big big dungeon and
# the other small, but they should all be locations"): sizes by the hive's number, each a little different
SMALL_SIZES = [(4, 3), (5, 3), (4, 4), (5, 4), (3, 5), (5, 3), (4, 4), (4, 5)]
SMALL_NAME = 'Vespid Nest'
SMALL = {'comb_every': 2, 'chamber_combs': 1, 'vespids': 2}
GREAT = {'comb_every': COMB_EVERY, 'chamber_combs': CHAMBER_COMBS, 'vespids': VESPIDS}
_SHARED = {}                    # (the kit index, its survey, the planner's stores: built once a run, for every cave)


# ---------- pictures (numpy, PIL: a build step) ----------

def _wrap_noise(rnd, n, cells):
    return hiveset._noise(rnd, n, n, cells, cells)


@functools.lru_cache(maxsize=None)
def wall_picture(size=1024, seed=11):
    """(rgb, height, glow): a nest's inside wall, scallop over scallop of fine-striped paper (each scallop a fan of
    arcs round its own middle, its lower edge dark), green veins running over them. Tiles both ways."""
    import numpy as np
    rnd = random.Random(seed)
    n = size
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    rgb = np.full((n, n, 3), 90.0, np.float32)
    ht = np.full((n, n), 0.4, np.float32)
    pal = np.array(hiveset.PAPER, np.float32)
    # scallops laid as shingles, the higher first, each lower one over those above it: each an oval whose fine stripes
    # are arcs about a point above it (a fan), wavering, its rim a little darker
    wob = _wrap_noise(rnd, n, 24)
    spots = sorted([(rnd.uniform(0, n), rnd.uniform(0, n), rnd.uniform(0.06, 0.12) * n) for _k in range(170)], key=lambda t: t[1])
    for cx, cy, rad in spots:
        dx = (xx - cx + n / 2) % n - n / 2
        dy = (yy - cy + n / 2) % n - n / 2
        oval = (dx / (rad * 1.25)) ** 2 + (dy / rad) ** 2
        inside = oval < 1
        if not inside.any():
            continue
        fy = dy + rad * 0.9                               # (the fan's point, above the oval)
        d = np.hypot(dx, fy) + 0.06 * rad * (wob - 0.5) * 6
        stripes = np.floor(d / rad * rnd.uniform(14, 22)).astype(int)
        cols = pal[np.array([rnd.randrange(len(pal)) for _ in range(32)])]
        col = cols[stripes % 32] * (0.86 + 0.2 * (1 - np.sqrt(np.clip(oval, 0, 1))))[..., None]
        edge = np.clip((np.sqrt(np.clip(oval, 0, 1)) - 0.86) / 0.14, 0, 1)
        col = col * (1 - 0.45 * edge[..., None])
        rgb[inside] = col[inside]
        ht[inside] = (0.4 + 0.35 * (1 - oval) - 0.25 * edge)[inside]
    fibre = _wrap_noise(rnd, n, 128)
    rgb *= (0.88 + 0.2 * fibre)[..., None]
    # veins: wandering lines over it all, wrapping round the picture's edges
    from PIL import Image, ImageDraw, ImageFilter
    v = Image.new('L', (n, n), 0)
    dr = ImageDraw.Draw(v)
    for _k in range(7):
        x, y = rnd.uniform(0, n), rnd.uniform(0, n)
        ang = rnd.uniform(0, math.tau)
        w, b = rnd.uniform(2, 3.5), rnd.uniform(90, 150)
        for _s in range(rnd.randint(20, 45)):
            ang += rnd.uniform(-0.5, 0.5)
            nx, ny = x + 22 * math.cos(ang), y + 22 * math.sin(ang)
            for ox in (-n, 0, n):
                for oy in (-n, 0, n):
                    dr.line([(x + ox, y + oy), (nx + ox, ny + oy)], fill=int(b), width=int(round(w)))
            x, y = nx % n, ny % n
            w = max(1.5, w * 0.97)
            if rnd.random() < 0.08:                     # (a branch)
                ang += rnd.choice((-1, 1)) * 0.9
    vein = np.asarray(v.filter(ImageFilter.GaussianBlur(1.5)), np.float32) / 255.0
    glow = vein[..., None] * np.array(hiveset.GLOW, np.float32)[None, None, :]
    rgb = rgb * (1 - 0.25 * vein[..., None]) + 0.12 * glow
    ht -= 0.1 * vein
    return np.clip(rgb, 0, 255), np.clip(ht, 0, 1), np.clip(glow, 0, 255)


@functools.lru_cache(maxsize=None)
def drip_picture(size=512, seed=12):
    """(rgb, height, glow): paper hanging in drips and rags, darker, a few glowing threads down it."""
    import numpy as np
    rnd = random.Random(seed)
    n = size
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    s = (yy / n + 0.05 * np.sin(xx / n * math.tau * 3)) * 20
    pal = np.array(hiveset.PAPER, np.float32) * 0.75
    rgb = pal[np.floor(s).astype(int) % len(pal)] * (0.85 + 0.25 * _wrap_noise(rnd, n, 64))[..., None]
    lines = (np.abs(((xx / n * 7) % 1.0) - 0.5) < 0.012).astype(np.float32) * (0.5 + 0.5 * _wrap_noise(rnd, n, 6))
    glow = lines[..., None] * np.array(hiveset.GLOW, np.float32)[None, None, :]
    return np.clip(rgb + 0.3 * glow, 0, 255), 0.4 + 0.2 * _wrap_noise(rnd, n, 32), np.clip(glow, 0, 255)


@functools.lru_cache(maxsize=None)
def floor_picture(size=1024, seed=13):
    """(rgb, height, None): a nest's floor: dark earth under dropped paper, shed larva casings, pale grubs' skins."""
    import numpy as np
    rnd = random.Random(seed)
    n = size
    tone = _wrap_noise(rnd, n, 16)
    rgb = np.array((62, 54, 44), np.float32) * (0.7 + 0.5 * tone)[..., None]
    ht = 0.3 + 0.2 * tone
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    pal = np.array(hiveset.PAPER, np.float32)
    for _k in range(900):
        cx, cy = rnd.uniform(0, n), rnd.uniform(0, n)
        r = rnd.uniform(4, 18)
        x0, x1, y0, y1 = int(cx - r - 1), int(cx + r + 2), int(cy - r - 1), int(cy + r + 2)
        ys, xs = np.mgrid[y0:y1, x0:x1]
        a = rnd.uniform(0, math.pi)
        u = (xs - cx) * math.cos(a) + (ys - cy) * math.sin(a)
        v = -(xs - cx) * math.sin(a) + (ys - cy) * math.cos(a)
        casing = rnd.random() < 0.35
        m = (u / r) ** 2 + (v / (r * (0.45 if casing else 0.8))) ** 2 < 1
        col = np.array((214, 206, 178), np.float32) if casing else pal[rnd.randrange(len(pal))]
        ys, xs = ys[m] % n, xs[m] % n
        rgb[ys, xs] = col * rnd.uniform(0.75, 1.05)
        ht[ys, xs] = 0.55
    return np.clip(rgb, 0, 255), np.clip(ht, 0, 1), None


PICTURES = {'cave_wall': wall_picture, 'cave_drip': drip_picture, 'cave_floor': floor_picture}


def pictures():
    import numpy as np
    import dds
    out = {}
    for name, fn in PICTURES.items():
        rgb, ht, glow = fn()
        col, nor = hiveset._canvas(rgb, ht).files(game=True, shine=10)
        out[TEX % name], out[TEX % (name + '_n')] = col, nor
        if glow is not None:
            h, w = ht.shape
            g = np.concatenate([glow.astype(np.uint8), np.full((h, w, 1), 255, np.uint8)], axis=2)
            out[TEX % (name + '_g')] = dds.compress(dds.encode(w, h, g.tobytes()))
    return out


# ---------- the kit's pieces, re-dressed ----------

def _ours(path):
    """FOLab's picture for one of the kit's (and its normal map for its normal map), or None."""
    p = path.lower().replace('/', '\\')
    for start, name in CAVE_TEXTURES.items():
        if p.startswith(start):
            if p.endswith('_p.dds'):
                return None
            return TEX % (name + '_n') if p.endswith('_n.dds') else TEX % name
    return None


def redress(data):
    """A cave piece's model with the kit's pictures swapped for the nest's and its walls' glow put in."""
    import nifglow
    import nifwrite
    changes = {}
    for t in nifwrite.textures_in(data):
        new = _ours(t['path'])
        if new:
            changes[t['path']] = new
    if not changes:
        return data
    out = nifwrite.retexture(data, changes)
    for name in GLOWING:
        if TEX % name in changes.values():
            out, _lit = nifglow.light_up(out, TEX % name, TEX % (name + '_g'), mult=GLOW_MULT)
    return out


def piece_files(gd, keys):
    """({path: bytes}, {piece key: (copy's model path under meshes, its editor ID)}) for the kit's pieces `keys`."""
    import recordio
    files, models = {}, {}
    for k in sorted(set(keys)):
        f = gd.from_key(k)
        model = recordio.field(recordio.load(gd, f), 'MODL')
        if not model:
            continue
        data = gd.read_file('meshes' + chr(92) + model)
        name = model.replace('/', '\\').rsplit('\\', 1)[-1]
        path = CAVE_MESH % name
        files[path] = redress(data)
        lod = model[:-4] + '_lod.nif'
        models[k] = (path, 'FOLabHive' + gd.edid(f))
    return files, models


# ---------- comb ----------

def comb_desc(name='FOLabVespidComb', seed=1, tiers=8):
    """A stack of comb tiers on stalks, as a nest grows in a hollow: each tier a broad, shallow disc of comb (cells lit
    from within, eggs), paper round its rim, a paper stalk to the next; 8 tiers about 40 apart, about 340 tall. Solid at its stalk only, so it never shuts a tunnel."""
    rnd = random.Random(seed)
    comb = {'tex': TEX % 'comb', 'normal': TEX % 'comb_n', 'glow': TEX % 'comb_g', 'glow_mult': 1.5, 'tile': 460, 'gloss': 60.0}   # (cells about half a metre: giant wasps)
    paper = {'tex': TEX % 'paper', 'normal': TEX % 'paper_n', 'tile': 128}
    parts, z = [], 0.0
    parts.append({'shape': 'cylinder', 'r': 16, 'r2': 12, 'h': 330, 'sides': 8, 'look': 'paper', 'at': [0, 0, 0], 'solid': True, 'material': 'organic'})
    # (tiers packed close, as a nest's are: the user, 23 Nov 2026, 'closer together and more tightly packed')
    for k in range(tiers):
        z += 18.0 + rnd.uniform(18, 24)
        r = rnd.uniform(120, 150) * (1.08 - 0.05 * k)
        parts.append({'shape': 'cylinder', 'r': r, 'r2': r, 'h': 18, 'sides': 20, 'look': 'paper', 'cap_look': 'comb', 'at': [rnd.uniform(-10, 10), rnd.uniform(-10, 10), z],
                      'solid': False})                # (only the stalk is solid: a stack never shuts a tunnel)
    return {'name': name, 'looks': {'comb': comb, 'paper': paper}, 'parts': parts, 'ground': True}


def comb_model():
    import modelmake
    made = modelmake.make(comb_desc())
    path = CAVE_MESH % 'vespid_comb.nif'
    return {'nif': made['nif'], 'mesh': path, 'box': made['box']}


# ---------- the cave ----------

def plan(gd, seed=SEED, kits=None, survey=None, store=None, cache=None, size=SIZE, fill=None):
    """The cave: kocave.make's answer with 'combs' [(x, y, z, rz)], 'lights' [(x, y, z)], 'queen' (x, y, z, rz),
    'chamber' (x, y, z, rz), 'vespids' [(x, y, z, rz)], all in the place's own frame; None if no cave walked."""
    import kitdress as D
    import kitindex as K
    import kitplan as P
    import kocave
    fill = fill or GREAT
    if 'kits' not in _SHARED:
        _SHARED['kits'] = kits or K.build(gd)
        _SHARED['survey'] = survey or D.survey(gd, _SHARED['kits'], only={kocave.KIT})
        _SHARED['store'], _SHARED['cache'] = {}, {}
    kits, survey = _SHARED['kits'], _SHARED['survey']
    store = _SHARED['store'] if store is None else store
    cache = _SHARED['cache'] if cache is None else cache
    g = kocave.make(gd, kits, size[0], size[1], seed, store, cache, survey)
    if not g:
        return None
    rnd = random.Random(seed)
    st = g['ts'].step
    squares = {m.cell[:2] for m in g['made']}
    zs = {m.cell[:2]: m.z for m in g['made']}
    start = g['exit'][0].cell[:2]
    far, todo = {start: 0}, [start]
    while todo:
        c = todo.pop(0)
        for dx, dy in P.DX:
            nb = (c[0] + dx, c[1] + dy)
            if nb in squares and nb not in far:
                far[nb] = far[c] + 1
                todo.append(nb)
    order = sorted(far, key=lambda c: -far[c])
    arrive = kocave.inside_arrival(g)
    w = P.Walk(gd, P.as_refs(gd, g['made']) + D.item_refs(gd, g['items']), arrive[:3], cache=cache, erode=True)
    v = w.voxel

    def floor(x, y, reach=6):
        cx, cy = int(math.floor(x / v)), int(math.floor(y / v))
        best = None
        for iy in range(cy - reach, cy + reach + 1):
            for ix in range(cx - reach, cx + reach + 1):
                for i in w.graph.by.get((iy, ix), ()):
                    if i in w.reached:
                        d = (ix - cx) ** 2 + (iy - cy) ** 2
                        if best is None or d < best[0]:
                            best = (d, w.graph.p[i][2], ix * v + v / 2, iy * v + v / 2)
        return best

    def spot(c, off=(0.0, 0.0)):
        got = floor(c[0] * st + off[0], c[1] * st + off[1])
        return (round(got[2], 1), round(got[3], 1), round(got[1], 1)) if got else None
    out = dict(g, combs=[], lights=[], vespids=[])
    q = spot(order[0])
    out['queen'] = (q[0], q[1], q[2] + 10, rnd.uniform(0, math.tau)) if q else None
    ch = spot(order[0], (140.0, 90.0)) or q
    out['chamber'] = (ch[0], ch[1], ch[2], rnd.uniform(0, math.tau)) if ch else None
    # comb: in the chamber's squares, then every COMB_EVERY squares along the way, against the side away from the walk
    chamber = [c for c in order if far[c] >= far[order[0]] - 1][:fill['chamber_combs'] + 1]
    along = [c for c in order[len(chamber):] if far[c] % fill['comb_every'] == 0 and far[c] > 1]
    for c in chamber[1:] + along:
        s = spot(c, (rnd.uniform(-150, 150), rnd.uniform(-150, 150)))
        if s:
            out['combs'].append((s[0], s[1], s[2], rnd.uniform(0, math.tau)))
            out['lights'].append((s[0], s[1], s[2] + 180.0))
    out['lights'].append((q[0], q[1], q[2] + 220.0) if q else None)
    out['lights'] = [l for l in out['lights'] if l]
    mid = [c for c in order if 0.3 * far[order[0]] <= far[c] <= 0.75 * far[order[0]]]
    rnd.shuffle(mid)
    for c in mid[:fill['vespids']]:
        s = spot(c)
        if s:
            out['vespids'].append((s[0], s[1], s[2] + 20.0, rnd.uniform(0, math.tau)))
    out['arrive'] = arrive
    # (where the walk reached, a man's chest high: where the leak check looks out from)
    got = sorted(w.reached)
    rnd.shuffle(got)
    out['reached_points'] = [(w.graph.p[i][1] * v + v / 2, w.graph.p[i][0] * v + v / 2, w.graph.p[i][2] + 110.0) for i in got[:400]]   # (places are (iy, ix, z, ...))
    return out


def cell_record(gd, edid='FOLabVespidGreatHive', full=NAME):
    """The place's record: a game cave's (its lighting, sound, flags), named the nest's."""
    import json
    import recordio
    f = min(f for f, (_i, r) in gd.forms.items() if r.tag == 'CELL' and gd.edid(f) == CELL_FROM)
    rec = json.loads(json.dumps(recordio.load(gd, f)))
    rec['src'] = ''
    rec['subs'] = [s for s in rec['subs'] if s['tag'] not in ('XOWN', 'XRNK', 'XEZN')]
    recordio.set_field(rec, 'EDID', edid, label='Editor ID')
    recordio.set_field(rec, 'FULL', full, label='Name')
    return rec


# ---------- the ops ----------

TAG = 'vhcave'


def piece_records(gd, caves, comb_mesh, comb_box):
    """(ops making a STAT of the mod's own for every kit piece any of `caves` uses, re-dressed, and the comb's;
    {piece key: '$name'})."""
    import json
    import recordio
    import vespidhives as VH
    keys = sorted({m.key for c in caves for m in c['made']})
    _files, models = piece_files(gd, keys)
    ops, names = [], {}
    for i, (k, (path, edid)) in enumerate(sorted(models.items())):
        rec = json.loads(json.dumps(recordio.load(gd, gd.from_key(k))))
        rec['src'] = ''
        rec['subs'] = [s_ for s_ in rec['subs'] if s_['tag'] not in ('MODT',)]
        recordio.set_field(rec, 'EDID', edid, label='Editor ID')
        recordio.set_field(rec, 'MODL', path[7:], label='Model')
        name = '%sp%d' % (TAG, i)
        ops.append({'op': 'record_new', 'record': rec, 'name': name})
        names[k] = '$' + name
    ops.append({'op': 'record_new', 'record': VH._stat('FOLabVespidComb', comb_mesh[7:], comb_box), 'name': TAG + 'comb'})
    return ops, names


def place_ops(gd, cave, tag, edid, full, names, queen_key, queen_parent, vespid_key, chamber_key, outside_door, outside_arrival,
              finds=None):
    """Ops for one hive's inside: its place (named '$tag'), its pieces, things, comb, lights, queen (her enable parent
    `queen_parent`: the hive's life, which her death switches off), cache and Vespids, and the two door links.
    outside_door: (its cell, '$name' of the hive's door outside). finds: (honey, royal jelly or None) by the combs."""
    import vespidhives as VH
    light = gd.key(VH._game(gd, 'LIGH', LIGHT))
    cell = '$' + tag
    ops = [{'op': 'record_new', 'record': cell_record(gd, edid, full), 'name': tag}]
    for m in cave['made']:
        ops.append({'op': 'add', 'cell': cell, 'base': names.get(m.key, m.key), 'p': [m.x, m.y, m.z, 0.0, 0.0, m.turn * math.pi / 2], 's': 1.0})
    for it in cave['items']:
        o = {'op': 'add', 'cell': cell, 'base': it.key, 'p': list(it.p), 's': it.s}
        if it.what == 'exit':
            o['name'] = tag + 'x'
        elif it.extra:
            o['extra'] = it.extra
        ops.append(o)
    for x, y, z, rz in cave['combs']:
        ops.append({'op': 'add', 'cell': cell, 'base': '$' + TAG + 'comb', 'p': [x, y, z - 4.0, 0.0, 0.0, round(rz, 4)], 's': 1.0})
    if finds:
        honey, royal = finds
        for i, (x, y, z, rz) in enumerate(cave['combs']):
            if (royal and i < 2) or i % 2 == 0:
                ops.append({'op': 'add', 'cell': cell, 'base': royal if (royal and i < 2) else honey,
                            'p': [round(x + 70 * math.cos(rz), 1), round(y + 70 * math.sin(rz), 1), z + 2.0, 0.0, 0.0, 0.0], 's': 1.0})
    for x, y, z in cave['lights']:
        ops.append({'op': 'add', 'cell': cell, 'base': light, 'p': [x, y, z, 0.0, 0.0, 0.0], 's': 1.0})
    if cave['queen']:
        ops.append({'op': 'add', 'cell': cell, 'base': queen_key, 'p': [cave['queen'][0], cave['queen'][1], cave['queen'][2], 0.0, 0.0, round(cave['queen'][3], 4)],
                    's': 1.0, 'extra': {'props': {'parent': {'ref': queen_parent, 'opposite': False, 'popin': False}}}})
    if cave['chamber']:
        x, y, z, rz = cave['chamber']
        ops.append({'op': 'add', 'cell': cell, 'base': chamber_key, 'p': [x, y, z + 1.0, 0.0, 0.0, round(rz, 4)], 's': 1.0})
    for x, y, z, rz in cave['vespids']:
        ops.append({'op': 'add', 'cell': cell, 'base': vespid_key, 'p': [x, y, z, 0.0, 0.0, round(rz, 4)], 's': 1.0})
    links = [{'op': 'tel', 'cell': outside_door[0], 'ref': outside_door[1], 'tel': {'door': '$' + tag + 'x', 'p': cave['arrive']}},
             {'op': 'tel', 'cell': cell, 'ref': '$' + tag + 'x', 'tel': {'door': outside_door[1], 'p': outside_arrival}}]
    return ops + links


# ---------- closed, as a solid is ----------

LEAK_RAYS = 96                  # (directions from each point: a sphere's worth)
LEAK_POINTS = 60                # (points through the walked space, at chest height)
LEAK_FAR = 6000.0               # (a ray that meets nothing this far out has left the place)


def _drawn(gd, cave):
    """Every triangle the game draws in the place's pieces, placed: (a, b, c) arrays of corners."""
    import numpy as np
    import nif
    import recordio
    tris = []
    seen = {}
    for m in cave['made']:
        if m.key not in seen:
            model = recordio.field(recordio.load(gd, gd.from_key(m.key)), 'MODL')
            seen[m.key] = nif.mesh_from_nif(gd.read_file('meshes' + chr(92) + model))
        rz = m.turn * math.pi / 2
        c, s = math.cos(rz), math.sin(rz)
        for sh in seen[m.key]:
            P = np.array(sh['p'], np.float64).reshape(-1, 3)
            Q = np.stack([m.x + P[:, 0] * c + P[:, 1] * s, m.y - P[:, 0] * s + P[:, 1] * c, m.z + P[:, 2]], 1)
            I = np.array(sh['i']).reshape(-1, 3)
            tris.append(Q[I])
    T = np.concatenate(tris)
    return T[:, 0], T[:, 1], T[:, 2]


def leaks(gd, cave, points=LEAK_POINTS, rays=LEAK_RAYS, seed=1):
    """[(point, direction)] of rays from inside the place that meet nothing the game draws within LEAK_FAR: where it
    isn't closed. Points: where the walk reached, a man's chest high; directions spread over a whole sphere. Both faces of
    a triangle count (seen from inside or out, a wall shuts the view)."""
    import numpy as np
    a, b, c = _drawn(gd, cave)
    e1, e2 = b - a, c - a
    rnd = random.Random(seed)
    w = cave['walk']
    pts = []
    import kitplan as P
    reached = cave.get('reached_points') or []
    if not reached:
        st = cave['ts'].step
        for m in cave['made']:
            pts.append((m.x, m.y, m.z + 110.0))
    else:
        pts = reached
    rnd.shuffle(pts)
    pts = pts[:points]
    # (directions: a Fibonacci sphere)
    k = np.arange(rays) + 0.5
    phi = np.arccos(1 - 2 * k / rays)
    th = math.pi * (1 + 5 ** 0.5) * k
    D = np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], 1)
    out = []
    for p in pts:
        o = np.array(p, np.float64)
        for d in D:
            pv = np.cross(d, e2)
            det = (e1 * pv).sum(1)
            ok = np.abs(det) > 1e-9
            inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
            tv = o - a
            u = (tv * pv).sum(1) * inv
            qv = np.cross(tv, e1)
            v = (qv * d).sum(1) * inv
            t = (e2 * qv).sum(1) * inv
            hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-3) & (t < LEAK_FAR)
            if not hit.any():
                out.append((tuple(round(x, 1) for x in p), tuple(round(x, 3) for x in d)))
    return out


def closed_plan(gd, seed=SEED, tries=4, progress=None, size=SIZE, fill=None):
    """A plan that walks (plan) and is closed as a solid (no ray from inside leaves it: `leaks`), trying further seeds;
    None if none of `tries` is. The answer carries 'leaks' (0) and 'seed'."""
    for k in range(tries):
        cave = plan(gd, seed + 7 * k, size=size, fill=fill)
        if cave is None:
            continue
        lk = leaks(gd, cave)
        if progress:
            progress('cave %dx%d seed %d: %d leaking rays' % (size[0], size[1], seed + 7 * k, len(lk)))
        if not lk:
            cave['leaks'], cave['seed'] = 0, seed + 7 * k
            return cave
    return None


def refresh_comb(gd, pr):
    """For a mod that already has the Vespids: the comb's model and pictures written afresh among the mod's own files
    (hiveset.comb, comb_desc) and the ops that bring its STAT's bounds in line ([] if they already are). Nothing else
    changes."""
    import copy
    import hiveset
    import library
    import recordio
    root = library.assets_dir(pr)
    made = comb_model()
    library._put(root, made['mesh'], made['nif'])
    files = [made['mesh']]
    for path, data in hiveset.texture_files().items():
        if 'comb' in path.lower():
            library._put(root, path, data)
            files.append(path)
    key = next((k for k, r in pr.records.items() if r.get('type') == 'STAT' and recordio.field(r, 'EDID') == 'FOLabVespidComb'), None)
    ops = []
    if key:
        rec = copy.deepcopy(pr.records[key])
        for sub in rec['subs']:
            if sub['tag'] == 'OBND':
                vals = [int(v) for v in made['box']]
                if [f['value'] for f in sub['fields']] != vals:
                    for f, v in zip(sub['fields'], vals):
                        f['value'] = v
                    ops.append({'op': 'record', 'key': key, 'record': rec})
    return ops, files
