"""Daylight under buildings: every building the mod placed, FOLab's own sets as much as the game's, measured for land falling away
from under its walls, and fixed by raising the land up to its foot. Never by letting the building down: on a slope that sinks
the high side's platform into the dirt (the user tried it, 23 Nov 2026).

groundfit.fit and close_gaps only knew the buildings in townbuild's catalogue (the game's own, measured where its land meets
their walls). Here a building is any of those, any piece from the game's architecture folders at least BIG across (not street
dressing), or any piece of FOLab's own building sets (FOLAB_SETS: hotels, restyle, the resort and its landmarks, settler,
bamboo, coast, Huáng, ...). Its foot is its model's lowest point (OBND): the same from the project or a built plugin.

measure(): for each, the land just outside its walls (OUT past them, RING points a side), and how far its foot stands over the
lowest of it. Points over water (a pier, a stilt house) and inside another building's box (a row joined wall to wall) don't
count. A gap over GAP is daylight.
fix(): the land within HOLD of its walls (and under it) raised to its foot, eased back over EASE_PER x the rise (EASE_MIN to
EASE_MAX), only ever up, never a road's ground, another building's or under water; things that stood on the raised ground
rise with it (buildings and road pieces never move). Returns ops, one Undo.

`py -3 app/floatfit.py [--home H] [--plugin built.esp]`: the count, from the mod as it is or from a built plugin alone."""
import math
import struct

GAP = 24.0              # land this far under a wall's foot, just outside it, is daylight under the building
DONE = 8.0              # after fix, no wall stands over its land by more than this
OUT = 32.0              # how far past the walls the land is read
RING = 9                # points a side
BIG = 256.0             # a game architecture piece this wide or more is a building
HOLD = 224.0            # past the walls, the land at the foot (every land point round a spot OUT past a wall: no low point between)
EASE_PER, EASE_MIN, EASE_MAX = 3.0, 256.0, 1024.0
ROAD_REACH = 32.0       # (a road piece's ground, and this far past its box, stays as it is)
ON_GROUND = 80.0
BURY_OTHER = 96.0       # the land may come this far up a lower neighbour's wall (as a hillside buries a house's uphill side)
STEP = 8.0
FOLAB_SETS = ('waikiki', 'settler', 'bamboo', 'restyle', 'resort', 'hotel', 'hotels', 'coast', 'huang', 'tower', 'towers',
              'historic', 'landmark', 'landmarks', 'vault50', 'kit', 'kits')
NOT_BUILDINGS = ('ship', 'freighter', 'boat', 'barge', 'bridge', 'buoy', 'raft', 'canoe', 'kayak', 'fence', 'lamp', 'pole',
                 'sign', 'bulb', 'rain', 'storm', 'rail', 'surfboard', 'lounger', 'cart', 'beam', 'scaffold', 'tank', 'windmill',
                 'rack', 'stall', 'screen', 'siren', 'planter', 'fuselag', 'guardtower', 'vault22', 'stilt', 'ladder', 'deck',
                 'walkway', 'platform')    # (on legs, or off the ground by design)


def _local(p, x, y):
    cs, sn = math.cos(p[5]), math.sin(p[5])
    dx, dy = x - p[0], y - p[1]
    return dx * cs - dy * sn, dx * sn + dy * cs


def _world(p, lx, ly):
    cs, sn = math.cos(p[5]), math.sin(p[5])
    return p[0] + lx * cs + ly * sn, p[1] - lx * sn + ly * cs


def _box_dist(o, s, lx, ly):
    ax = max(o[0] * s - lx, 0.0, lx - o[3] * s)
    ay = max(o[1] * s - ly, 0.0, ly - o[4] * s)
    return math.hypot(ax, ay)


def base_info(gd, pr, key):
    """(type, editor ID, model, OBND or None) of a base as the mod leaves it."""
    import recordio
    rec = pr.records.get(key) if pr else None
    if rec:
        ob = None
        for s in rec.get('subs', []):
            if s.get('tag') == 'OBND':
                try:
                    ob = [int(f['value']) for f in s['fields'] if 'name' in f][:6]
                except (KeyError, TypeError, ValueError):
                    ob = None
        return rec['type'], recordio.field(rec, 'EDID') or '', recordio.field(rec, 'MODL') or '', ob
    try:
        fid = gd.from_key(key)
    except (ValueError, KeyError):
        return '', '', '', None
    if fid not in gd.forms:
        return '', '', '', None
    btype, edid, _name, model = gd.describe(fid)
    o = gd.fields(fid).get('OBND')
    ob = list(struct.unpack_from('<6h', o)) if o and len(o) >= 12 else None
    return btype, edid or '', gd.model_path(btype, model) if model else '', ob


def kind(btype, edid, model, ob, s=1.0):
    """'building', 'road' or None."""
    m = (model or '').lower().replace('\\', '/')
    e = (edid or '').lower()
    if not ob or btype not in ('STAT', 'SCOL', 'ACTI', 'FURN', 'TERM', 'CONT'):
        return None
    if e.startswith(('folabroad', 'wastelandroad')) or '/sidewalk/' in m or m.rsplit('/', 1)[-1].startswith('road_') or \
            ('/landscape/roads/' in m and 'chunk' not in e):
        return 'road'
    if any(w in e for w in NOT_BUILDINGS):
        return None
    wide = max(ob[3] - ob[0], ob[4] - ob[1]) * s
    parts = m.split('/')
    if 'folab' in parts:
        i = parts.index('folab')
        folder = parts[i + 1] if i + 1 < len(parts) - 1 else ''
        return 'building' if folder in FOLAB_SETS and wide >= 128 else None
    if '/architecture/' in m and '/streetdressing/' not in m and 'vine' not in e and 'rubble' not in e and 'litter' not in e and wide >= BIG:
        return 'building'
    return None


def things(gd, pr, world):
    """Every thing standing in the world's cells as the mod leaves it: {key, ck, p, s, base, kind, edid, ob, mine (the mod's own)}."""
    out, cache = [], {}
    grid = gd.grid(world)
    for c in grid.values():
        ck = gd.key(c)
        mine = (pr.cells.get(ck) or {}).get('refs', {}) if pr else {}
        rows = []
        for r in gd.refs(c):
            if not r['pos'] or r['base'] not in gd.forms:
                continue
            k = gd.key(r['ref'])
            ch = mine.get(k) or {}
            if ch.get('removed'):
                continue
            rows.append((k, ch.get('base') or gd.key(r['base']), ch.get('p') or list(r['pos']) + list(r['rot']), ch.get('s', r['scale']), bool(ch)))
        for k, ch in mine.items():
            if k.startswith('+') and not ch.get('removed') and ch.get('p') and ch.get('base'):
                rows.append((k, ch['base'], ch['p'], ch.get('s', 1.0), True))
        for k, base, p, s, own in rows:
            if base not in cache:
                cache[base] = base_info(gd, pr, base)
            btype, edid, model, ob = cache[base]
            s = float(s or 1.0)
            out.append({'key': k, 'ck': ck, 'p': list(p), 's': s, 'base': base, 'edid': edid, 'ob': ob, 'kind': kind(btype, edid, model, ob, s), 'mine': own})
    return out


class Land:
    """The world's land points as the mod leaves them, to read and raise."""

    def __init__(self, gd, pr, world):
        import roadgen
        self.gd, self.pr, self.world = gd, pr, world
        self.grid = gd.grid(world)
        self.G = roadgen.Ground(gd, pr, world)
        self.h, self.new = {}, {}
        self.wet = {}

    def cell(self, k):
        if k not in self.h:
            h = self.G.cell(k)
            self.h[k] = list(h) if h else None
        return self.h[k]

    def point(self, gx, gy):
        k = (gx // 32, gy // 32)
        h = self.new.get(k) or self.cell(k)
        return None if h is None else h[(gy - k[1] * 32) * 33 + (gx - k[0] * 32)]

    def at(self, x, y):
        k = (int(x // 4096), int(y // 4096))
        h = self.new.get(k) or self.cell(k)
        if not h:
            return None
        fx, fy = (x - k[0] * 4096) / 128, (y - k[1] * 4096) / 128
        c0, r0 = min(31, int(fx)), min(31, int(fy))
        tx, ty = fx - c0, fy - r0
        p = lambda r, c: h[r * 33 + c]
        return (p(r0, c0) * (1 - tx) + p(r0, c0 + 1) * tx) * (1 - ty) + (p(r0 + 1, c0) * (1 - tx) + p(r0 + 1, c0 + 1) * tx) * ty

    def water(self, x, y):
        k = (int(x // 4096), int(y // 4096))
        if k not in self.wet:
            self.wet[k] = self.G.water(x, y)
        return self.wet[k]

    def raise_point(self, gx, gy, z):
        """A land point up to z (never down), in every cell that has it."""
        cx, cy = gx // 32, gy // 32
        c, r = gx - cx * 32, gy - cy * 32
        at = [(cx, cy, r, c)]
        if c == 0:
            at.append((cx - 1, cy, r, 32))
        if r == 0:
            at.append((cx, cy - 1, 32, c))
        if c == 0 and r == 0:
            at.append((cx - 1, cy - 1, 32, 32))
        for x, y, rr, cc in at:
            if (x, y) not in self.new:
                h = self.cell((x, y))
                if h is None:
                    continue
                self.new[(x, y)] = list(h)
            i = rr * 33 + cc
            if z > self.new[(x, y)][i]:
                self.new[(x, y)][i] = z


def catalogue_mids(gd):
    """No catalogue: townbuild's is measured afresh for each set of loaded plugins (the mod's own placements among them), so the
    mod's project and its built plugin would disagree by its numbers. A building's foot is its own model's lowest point."""
    return {}


def foot_of(b, mids):
    o, s = b['ob'], b['s']
    mid = mids.get(b['base'])
    return b['p'][2] + (mid if mid is not None else o[2]) * s


def _boxes_near(items):
    """Buckets of 2048 units: what's near a spot, quickly."""
    near = {}
    for b in items:
        o, s = b['ob'], b['s']
        rad = math.hypot(max(abs(o[0]), abs(o[3])), max(abs(o[1]), abs(o[4]))) * s
        for i in range(int((b['p'][0] - rad) // 2048), int((b['p'][0] + rad) // 2048) + 1):
            for j in range(int((b['p'][1] - rad) // 2048), int((b['p'][1] + rad) // 2048) + 1):
                near.setdefault((i, j), []).append(b)
    return near


def _inside_any(near, x, y, but=None, pad=0.0):
    for b in near.get((int(x // 2048), int(y // 2048)), ()):
        if b is but:
            continue
        if _box_dist(b['ob'], b['s'], *_local(b['p'], x, y)) <= pad:
            return b
    return None


def ring(b, out=OUT):
    p, o, s = b['p'], b['ob'], b['s']
    for i in range(RING):
        f = i / (RING - 1)
        for lx, ly in ((o[0] * s + (o[3] - o[0]) * s * f, o[1] * s - out), (o[0] * s + (o[3] - o[0]) * s * f, o[4] * s + out),
                       (o[0] * s - out, o[1] * s + (o[4] - o[1]) * s * f), (o[3] * s + out, o[1] * s + (o[4] - o[1]) * s * f)):
            yield _world(p, lx, ly)


def own_world(gd, pr, world):
    """A world of the mod's own plugin: every building in it is the mod's, not only those its project holds."""
    plugin = getattr(pr, 'plugin', None)
    return bool(plugin) and gd.names[world >> 24] == plugin.lower()


def measure(gd, pr, world, L=None, items=None, mids=None, only_mine=None):
    """[{key, ck, name, gap, at (x, y), b}] for every building, worst first. only_mine: just those the project holds (by
    default in the game's own worlds; in the mod's own worlds every building is the mod's)."""
    if only_mine is None:
        only_mine = not own_world(gd, pr, world)
    items = items if items is not None else things(gd, pr, world)
    mids = mids if mids is not None else catalogue_mids(gd)
    L = L or Land(gd, pr, world)
    builds = [b for b in items if b['kind'] == 'building' and (b['mine'] or not only_mine)]
    near = _boxes_near([b for b in items if b['kind'] == 'building'])
    rnear = _boxes_near([b for b in items if b['kind'] == 'road'])
    out = []
    for b in builds:
        foot = foot_of(b, mids)
        worst, at = 0.0, None
        for x, y in ring(b):
            if _inside_any(near, x, y, but=b):
                continue
            g = L.at(x, y)
            if g is None:
                continue
            w = L.water(x, y)
            if w is not None and g < w:
                continue                                   # (over water: a pier, a house on stilts)
            road = _inside_any(rnear, x, y)
            if road is not None:
                g = max(g, road['p'][2] + road['ob'][5] * road['s'])     # (a road piece there: its top is what meets the wall)
            if foot - g > worst:
                worst, at = foot - g, (round(x), round(y))
        out.append({'key': b['key'], 'ck': b['ck'], 'name': b['edid'], 'gap': round(worst, 1), 'at': at, 'b': b})
    out.sort(key=lambda r: -r['gap'])
    return out


def _raise_round(L, row, mids, rnear, bnear, feet):
    """The land round one building raised to its foot: within HOLD of its walls (and under it) flat at the foot, eased back over
    EASE_PER x the gap. Never a road's ground; under another building only if its foot stands as high; never down."""
    b = row['b']
    o, s, p = b['ob'], b['s'], b['p']
    foot = math.ceil(foot_of(b, mids) / STEP) * STEP
    ease = max(EASE_MIN, min(EASE_MAX, EASE_PER * row['gap']))
    rad = math.hypot(max(abs(o[0]), abs(o[3])), max(abs(o[1]), abs(o[4]))) * s + HOLD + ease
    for gy in range(int((p[1] - rad) // 128), int((p[1] + rad) // 128) + 2):
        for gx in range(int((p[0] - rad) // 128), int((p[0] + rad) // 128) + 2):
            x, y = gx * 128.0, gy * 128.0
            d = _box_dist(o, s, *_local(p, x, y))
            if d > HOLD + ease:
                continue
            now = L.point(gx, gy)
            if now is None or now >= foot:
                continue
            w = L.water(x, y)
            if w is not None and now < w and d > HOLD:
                continue                               # (under water past the footing: left to the lake or the sea)
            if _inside_any(rnear, x, y, pad=ROAD_REACH):
                continue                               # (a road's ground)
            if d <= HOLD:
                want = foot
            else:
                u = (d - HOLD) / ease
                want = foot + (now - foot) * (u * u * (3 - 2 * u))
            want = math.ceil(want / STEP) * STEP
            other = _inside_any(bnear, x, y, but=b)
            if other is not None and feet.get(id(other), -1e9) + BURY_OTHER < want:
                continue                               # (it would bury another building's foot)
            if want > now + 0.5:
                L.raise_point(gx, gy, want)


def fix(gd, pr, world, progress=None):
    """(ops, report): the land raised to every gapped building's foot, things on that ground lifted with it."""
    items = things(gd, pr, world)
    mids = catalogue_mids(gd)
    L = Land(gd, pr, world)
    first = measure(gd, pr, world, L, items, mids)
    before = sum(1 for r in first if r['gap'] > GAP)
    builds = [b for b in items if b['kind'] == 'building']
    roads = [b for b in items if b['kind'] == 'road']
    bnear, rnear = _boxes_near(builds), _boxes_near(roads)
    feet = {id(b): foot_of(b, mids) for b in builds}
    rows = [r for r in first if r['gap'] > DONE]
    for _pass in range(2):
        for n, row in enumerate(rows):
            if progress and n % 50 == 0:
                progress('Raising the land to the buildings', n, len(rows))
            _raise_round(L, row, mids, rnear, bnear, feet)
        rows = [r for r in measure(gd, pr, world, L, items, mids) if r['gap'] > DONE]
    import land
    import server
    ops, changed = [], []
    for k, h in sorted(L.new.items()):
        if h == L.cell(k):
            continue
        c = L.grid[k]
        ck = gd.key(c)
        form = dict(pr.land[ck]) if ck in pr.land else land.decode(gd, gd.land[c], server._land_tex)
        form = {n: form[n] for n in ('h', 'c', 'q') if n in form}
        form['h'] = [float(v) for v in h]
        ops.append({'op': 'land', 'cell': ck, 'land': form})
        changed.append(k)
    # things that stood on ground that rose rise with it (never a building or a road piece)
    lifted = 0
    if changed:
        old = Land(gd, pr, world)
        moved = set(changed)
        for t in items:
            if t['kind'] in ('building', 'road'):
                continue
            k = (int(t['p'][0] // 4096), int(t['p'][1] // 4096))
            if k not in moved:
                continue
            a, n_ = old.at(t['p'][0], t['p'][1]), L.at(t['p'][0], t['p'][1])
            if a is None or n_ is None or n_ - a < 2 or abs(t['p'][2] - a) > ON_GROUND:
                continue
            ops.append({'op': 'move', 'cell': t['ck'], 'ref': t['key'], 'p': [t['p'][0], t['p'][1], round(t['p'][2] + n_ - a, 1)] + list(t['p'][3:])})
            lifted += 1
    after = [r for r in measure(gd, pr, world, L, items, mids) if r['gap'] > DONE]
    report = {'gapped_before': before, 'left_over_done': len(after), 'land_cells': len(changed), 'lifted': lifted,
              'cells': [list(k) for k in changed],
              'left': [{'name': r['name'], 'gap': r['gap'], 'at': r['at'], 'why': why(r, L, rnear, bnear)} for r in after[:300]]}
    return ops, report


def why(row, L, rnear, bnear):
    """Why a building still has daylight under it after fix: what holds the land at its worst spot."""
    if not row['at']:
        return 'unknown'
    x, y = row['at']
    if _inside_any(rnear, x, y, pad=ROAD_REACH):
        return 'a road runs along that wall'
    if _inside_any(bnear, x, y, but=row['b'], pad=HOLD):
        return 'another building stands against that wall'
    w = L.water(x, y)
    if w is not None and (L.at(x, y) or 0) < w + 64:
        return 'water beside it'
    return 'land between its points'


if __name__ == '__main__':
    import os
    import sys
    args = sys.argv[1:]
    opt = lambda n, d=None: args[args.index(n) + 1] if n in args else d
    if opt('--home'):
        os.environ['FOLAB_HOME'] = opt('--home')
    os.environ.setdefault('FOLAB_NO_GAME_WRITES', '1')
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.stdout.reconfigure(encoding='utf-8')
    import gamedata
    import project
    import server
    server.not_while_playing = lambda: None
    plugin = opt('--plugin')
    if plugin:
        # (a built plugin alone, on the game files: what the game will load)
        server.GD = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [plugin])

        class _Empty:
            records, cells, land, water = {}, {}, {}, {}
        pr = _Empty()
        gd = server.GD
    else:
        server.GD = gamedata.GameData(); server.BR = None
        pr = project.Project.open(opt('--mod', 'Waikiki')); server.load_game(pr); server.PR = pr
        gd = server.GD
    total = 0
    for w in gd.worlds():
        if not gd.grid(w):
            continue
        if plugin and gd.names[w >> 24] != os.path.basename(plugin).lower():
            continue
        rows = measure(gd, pr, w, only_mine=not plugin)
        bad = [r for r in rows if r['gap'] > GAP]
        if not rows:
            continue
        total += len(bad)
        print('%s: %d buildings, %d with daylight under a wall (over %d units); worst: %s' % (
            gd.edid(w), len(rows), len(bad), GAP, ', '.join('%s %d at %s' % (r['name'], r['gap'], r['at']) for r in bad[:8])))
    print('TOTAL buildings with daylight under a wall: %d' % total)
