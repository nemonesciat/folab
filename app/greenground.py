"""Green ground where green belongs, for a world made from a map: by the land point, from what the map says each is,
and with grass only where the game's own rule for grass cannot carry it onto a road or a beach.

A map-made world's ground is painted by slope with what the Mojave shows at each steepness (mapworld.py), and only
what the map names (a park, a beach, a road) gets its own texture: so everything the map says nothing of comes out
desert. Right for Nevada, wrong for an island. And its lawns are laid without the game's grass.

What the user wants (after playing three wrong tries): green ground with the game's 3D grass standing on it wherever
that makes sense, and never anywhere else: it "ruins the experience on asphalt and sand", and between buildings.

HOW GRASS GROWS is in grassrule.py (read out of the game's own code after the third try): sixteen samples a quarter,
each reading the 3 x 3 points round it and spreading what it finds over a patch 512 units square; a grass-bearing
BASE grows wherever the layers over it are thin. So a layer faded towards a road still carries blades onto it, which
is what the third try did. Hence:

  two grounds for one look: the picture with a grass (FOLabGroundJungleGrass; for lawns the game's LGrassGreenSuburbs)
      and the same picture with none (FOLabGroundJungleGrassPlain; the game's LGrassGreenSuburbsNoGrass, which the map
      step's lawns already are);
  the fade to other ground is made with the one that grows nothing, rising over GRADE points from the edge;
  the grass-bearing one goes down patch by patch, a patch being a sample's own 512 units: only where every point from
      four before the sample to four after it (the patch and 256 units beyond it all round) may have grass, and then
      at one strength, HOLD, on the whole patch; anywhere else it is exactly nothing. It is never a base.

What may be painted, by the point, from osmcover.MapCover: the map's parks and lawns, golf course, woods, scrub, bare
rock, and ground the map says nothing of (osmcover leaves that unsaid only 5 points, 640 units, from every road and
building). Sheer ground gets mossy rock and no grass. Never touched, to the point: roads, paving, the lived-in ground
round buildings (yard), the beach, the sea bed, and farmland and wetland.

It always starts from the paint the world was made with (the plugin's own land) over the heights as they are now, so
it can be run again, and run over an earlier repaint it puts back what that one should not have touched. One Undo.
`report` counts by kind of ground; `check` runs grassrule over a world's land and says where grass is predicted that
this step put there within 256 units of ground that may have none (it must be nowhere: tests/test_modelmake.py)."""
import collections
import math
import zlib

import groundtex
import land
import recordio

WILD = ('trees', 'scrub', 'rock')       # and unsaid ground: FOLab's own ground
LAWN = ('grass', 'golf')                # the game's lawn, with its grass
LAWN_GRASS = 'LGrassGreenSuburbs'       # (the picture the map step's lawns already have, as the game ships it with grass)
SHEER = 34.0                # degrees: steeper than this, mossy rock and no grass
GRADE = 3                   # points over which green comes up to full from the edge of what it may not touch
HOLD = 0.9                  # the strength a grass-bearing layer has on a patch it may have: well over any threshold; elsewhere 0
CLEAR = 4                   # a patch may have grass only if every point this far from its sample, each way, may (the patch is 2)
MAX_LAYERS = 6              # (what the writer puts in a quarter)


def _steep_at(h, i, j):
    """How steep the ground is at a point of a cell's 33 x 33, in degrees."""
    a = h[j * land.SIDE + i]
    b = h[j * land.SIDE + i + 1] if i + 1 < land.SIDE else h[j * land.SIDE + i - 1]
    c = h[(j + 1) * land.SIDE + i] if j + 1 < land.SIDE else h[(j - 1) * land.SIDE + i]
    return math.degrees(math.atan(math.hypot(b - a, c - a) / land.STEP))


def _from_the_rest(cover, may):
    """For each point of the cover that may be painted, how many points it is from one that may not (up to GRADE); 0 for
    the rest. A bytearray laid out as cover.kind."""
    A, D = cover.A, cover.D
    dist = bytearray(A * D)
    todo = collections.deque()
    for s in range(A * D):
        if cover.kind[s] not in may:
            todo.append((s, 0))
        else:
            dist[s] = GRADE
    seen = bytearray(1 if cover.kind[s] not in may else 0 for s in range(A * D))
    while todo:
        s, d = todo.popleft()
        if d >= GRADE - 1:
            continue
        x, y = s % A, s // A
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < A and 0 <= ny < D:
                t = ny * A + nx
                if not seen[t]:
                    seen[t] = 1
                    dist[t] = d + 1
                    todo.append((t, d + 1))
    return dist


def regreen(gd, pr, world, cover, progress=None, only=None):
    """(ops, report): the records of FOLab's ground textures the mod hasn't yet (first: see groundtex), then a 'land'
    op for every cell whose paint changes. cover: the world's osmcover.MapCover. only: the cells to do, as (x, y)."""
    import osmcover
    cache, name_of = {}, {}
    by_name = {gd.edid(f): f for f, (_i, r) in gd.forms.items() if r.tag == 'LTEX'}
    first, keys = groundtex.put(gd, pr)
    tex = {key: groundtex.path(n) for n, key in keys.items()}
    lawn = gd.key(by_name[LAWN_GRASS]) if LAWN_GRASS in by_name else None
    if lawn:
        tex[lawn] = land.texture_of_fid(gd, by_name[LAWN_GRASS], cache)
    grassy = {keys['grass']} | ({lawn} if lawn else set())
    import grassrule
    ours = set(keys.values()) | ({lawn} if lawn else set())
    names = ['unsaid'] + list(osmcover.ORDER)
    wild_codes = {osmcover.CODE[k] for k in WILD} | {0}
    lawn_codes = {osmcover.CODE[k] for k in LAWN}
    may = wild_codes | lawn_codes
    A, D, gx0, gy0 = cover.A, cover.D, cover.gx0, cover.gy0
    grade = _from_the_rest(cover, may)
    grid = gd.grid(world)
    ops, cells = [], 0
    by_kind = {n: {'points': 0, 'changed': 0, 'grass': 0} for n in names}
    quarters_done = {'whole': 0, 'part': 0, 'left': 0}

    for count, (k, cell) in enumerate(sorted((k, c) for k, c in grid.items() if only is None or k in only)):
        if progress and count % 32 == 0:
            progress('Painting the ground', count, len(grid))
        ckey = gd.key(cell)
        mine = pr.land.get(ckey)
        e = gd.land_at(world, *k)
        if not mine and not e:
            continue
        made = land.decode(gd, e, cache) if e else mine
        form = dict(mine or made)
        h = form.get('h')
        if not h:
            continue
        quarters = []
        for qn, q0 in enumerate(made['q']):
            q = dict(q0, layers=[dict(l) for l in q0['layers']])
            px, py = (qn % 2) * 16, (qn // 2) * 16
            n_pts = land.QSIDE * land.QSIDE
            kinds, a_wild, a_lawn, a_rock = [None] * n_pts, [0.0] * n_pts, [0.0] * n_pts, [0.0] * n_pts
            b_wild, b_lawn, flat = [0.0] * n_pts, [0.0] * n_pts, [False] * n_pts
            for j in range(land.QSIDE):
                for i in range(land.QSIDE):
                    x, y = k[0] * 32 + px + i - gx0, k[1] * 32 + py + j - gy0
                    if not (0 <= x < A and 0 <= y < D):
                        continue
                    n = j * land.QSIDE + i
                    kd = cover.kind[y * A + x]
                    kinds[n] = kd
                    if kd not in may or h[(py + j) * land.SIDE + px + i] < 8:
                        continue                                # (not ours, or under the sea)
                    v = min(1.0, grade[y * A + x] / float(GRADE))
                    if kd in lawn_codes:
                        a_lawn[n] = v
                        flat[n] = True
                    elif _steep_at(h, px + i, py + j) >= SHEER:
                        a_rock[n] = v
                    else:
                        a_wild[n] = v
                        flat[n] = True
            # grass, a patch at a time: a sample's patch may have it only if it and 256 units round it are all ground
            # that may, and none of the patch itself is sheer or under water
            for sy in grassrule.SAMPLES:
                for sx in grassrule.SAMPLES:
                    cx, cy = k[0] * 32 + px + sx - gx0, k[1] * 32 + py + sy - gy0
                    if not (CLEAR <= cx < A - CLEAR and CLEAR <= cy < D - CLEAR):
                        continue
                    if any(cover.kind[(cy + dy) * A + cx + dx] not in may for dy in range(-CLEAR, CLEAR + 1) for dx in range(-CLEAR, CLEAR + 1)):
                        continue
                    spots = [(sy + dy) * land.QSIDE + sx + dx for dy in range(-2, 3) for dx in range(-2, 3)]
                    if not all(flat[n] for n in spots):
                        continue
                    to = b_lawn if kinds[sy * land.QSIDE + sx] in lawn_codes else b_wild
                    for n in spots:
                        to[n] = HOLD
            # (wild all through: its desert paint may go. A lawn keeps the paint it was made with: only grass is added to it)
            all_ours = all(kd in wild_codes for kd in kinds) and all(max(u, r) >= 1.0 for u, r in zip(a_wild, a_rock))
            if max(a_wild) <= 0 and max(b_lawn) <= 0 and max(a_rock) <= 0:
                quarters_done['left'] += 1
            else:
                gx, gy = k[0] * 32 + px, k[1] * 32 + py
                patch = lambda salt, share: [a_wild[j * land.QSIDE + i] if zlib.crc32(b'%d,%d,%d' % ((gx + i) // 3, (gy + j) // 3, salt)) % 100 < share else 0.0
                                             for j in range(land.QSIDE) for i in range(land.QSIDE)]
                # the look, in grounds that grow nothing; then the grass; then patches of moss and forest floor
                want = [(keys['grass_plain'], a_wild), (keys['mossy_rock'], a_rock), (keys['grass'], b_wild)] + ([(lawn, b_lawn)] if lawn else []) \
                    + [(keys['moss'], patch(1, 30)), (keys['litter'], patch(2, 22))]     # (the patches last: they go first if there is no room)
                want = [(key, a) for key, a in want if max(a) > 0]
                # (what covers most goes first, so a crowded quarter loses its patches before its green; the patches stay last)
                main = sorted([w for w in want if w[0] not in (keys['moss'], keys['litter'])], key=lambda w: -sum(w[1]))
                want = main + [w for w in want if w[0] in (keys['moss'], keys['litter'])]
                if all_ours:
                    # ours at every point: the desert's paint goes, a plain green under everything
                    q['bkey'], q['base'] = keys['grass_plain'], tex[keys['grass_plain']]
                    q['layers'] = []
                    quarters_done['whole'] += 1
                else:
                    q['layers'] = [l for l in q['layers'] if l['key'] not in ours]
                    # room for ours: a layer of the desert's that shows only on points that are ours to paint may go
                    # (taking it away changes nothing anywhere else); the faintest first
                    mine_pts = [max(u, w, r) > 0 for u, w, r in zip(a_wild, b_lawn, a_rock)]
                    spare = sorted((l for l in q['layers'] if all(m or v <= 0 for m, v in zip(mine_pts, l['a']))), key=lambda l: sum(l['a']))
                    while spare and len(q['layers']) + len(want) > MAX_LAYERS:
                        q['layers'].remove(spare.pop(0))
                    quarters_done['part'] += 1
                for key, a in want:
                    if len(q['layers']) < MAX_LAYERS:
                        q['layers'].append({'tex': tex[key], 'key': key, 'a': a})
            # what changed at each point, and where grass was laid
            was = {l['key']: l['a'] for l in q0['layers']}
            now_l = {l['key']: l['a'] for l in q['layers']}
            base_changed = q.get('bkey') != q0.get('bkey')
            for n, kd in enumerate(kinds):
                if kd is None:
                    continue
                row = by_kind[names[kd]]
                row['points'] += 1
                if base_changed or any(abs(a[n] - was.get(key, a_zero)[n]) > 1e-6 for key, a in now_l.items()) or any(a[n] > 0 and key not in now_l for key, a in was.items()):
                    row['changed'] += 1
                if any(now_l.get(g, a_zero)[n] > 0 for g in grassy) or q.get('bkey') in grassy:
                    row['grass'] += 1
            quarters.append(q)
        now = (mine or made)['q']
        same = lambda u, v: u.get('bkey') == v.get('bkey') and [(l['key'], l['a']) for l in u['layers']] == [(l['key'], l['a']) for l in v['layers']]
        if not all(same(u, v) for u, v in zip(quarters, now)):
            form['q'] = quarters
            ops.append({'op': 'land', 'cell': ckey, 'land': form})
            cells += 1
    allowed = set(WILD) | set(LAWN) | {'unsaid'}
    report = {'cells': cells, 'of': len(grid), 'records': len(first), 'quarters': quarters_done,
              'by_kind': {n: v for n, v in by_kind.items() if v['points']},
              'changed_where_forbidden': sum(v['changed'] for n, v in by_kind.items() if n not in allowed),
              'grass_where_forbidden': sum(v['grass'] for n, v in by_kind.items() if n not in allowed)}
    return (first + ops if ops else []), report


a_zero = [0.0] * (land.QSIDE * land.QSIDE)


def check(gd, pr, world, cover, t=None):
    """The game's grass rule run over a world's land as the mod has it: {'near': points within 256 units of ground that
    may have no grass, 'before': of those, where the world's first paint already stands grass, 'after': where it does
    now, 'ours': where grass stands from what this step laid (must be 0), 'grown': points with grass now, by kind}."""
    import grassrule
    import osmcover
    t = grassrule.T if t is None else t
    dens = grassrule.densities(gd, pr)
    by_name = {gd.edid(f): f for f, (_i, r) in gd.forms.items() if r.tag == 'LTEX'}
    mine = {key for key, r in pr.records.items() if r.get('type') == 'LTEX' and (recordio.field(r, 'EDID') or '').startswith('FOLabGround')}
    if LAWN_GRASS in by_name:
        mine.add(gd.key(by_name[LAWN_GRASS]))
    may = {osmcover.CODE[k] for k in WILD + LAWN} | {0}
    names = ['unsaid'] + list(osmcover.ORDER)
    A, D, gx0, gy0 = cover.A, cover.D, cover.gx0, cover.gy0
    near = bytearray(A * D)                     # within two points of a point that may have no grass
    for s_ in range(A * D):
        if cover.kind[s_] not in may:
            x, y = s_ % A, s_ // A
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    if 0 <= x + dx < A and 0 <= y + dy < D:
                        near[(y + dy) * A + x + dx] = 1
    out = {'near': 0, 'before': 0, 'after': 0, 'ours': 0, 'grown': {}, 'threshold': t}
    cache = {}
    for k, cell in gd.grid(world).items():
        e = gd.land_at(world, *k)
        now = pr.land.get(gd.key(cell))
        if not e and not now:
            continue
        made = land.decode(gd, e, cache) if e else now
        now = now or made
        for qn in range(4):
            px, py = (qn % 2) * 16, (qn // 2) * 16
            was_g = grassrule.predict(made['q'][qn], dens, t)
            now_g = grassrule.predict(now['q'][qn], dens, t) if now is not made else was_g
            our_g = grassrule.predict(now['q'][qn], dens, t, only=mine) if now is not made else None
            for j in range(land.QSIDE):
                for i in range(land.QSIDE):
                    x, y = k[0] * 32 + px + i - gx0, k[1] * 32 + py + j - gy0
                    if not (0 <= x < A and 0 <= y < D):
                        continue
                    n = j * land.QSIDE + i
                    if now_g[n] > 0:
                        kd = names[cover.kind[y * A + x]]
                        out['grown'][kd] = out['grown'].get(kd, 0) + 1
                    if near[y * A + x]:
                        out['near'] += 1
                        out['before'] += was_g[n] > 0
                        out['after'] += now_g[n] > 0
                        out['ours'] += bool(our_g and our_g[n] > 0)
    return out
