"""A place of the mod's own checked as someone walking it finds it: check(gd, pr, place key) -> {'reached', 'open_edges',
'holes' (open edges not at a door: the doorway behind a door is open to a walk, which can't see doors), 'no_ceiling' (walked
floor with nothing drawn over it), 'ways_in', 'unreached_ways' (arrivals the walk from the first doesn't come to), 'spots'}.

The walk is kitplan.Walk from the first way in's arrival, over the place's real collision, eroded as its navmesh is made."""
import math
import sys

import kitplan
import navbuild
import navgen
import walkcheck

UP_LO, UP_HI = 96.0, 700.0       # (over head height: what one stands on, a heap, may bring the ceiling within 160)
AT_DOOR = 200.0
LOOSE_NEAR = 150.0
LOOSE_WORDS = ('rubble', 'pile', 'debris', 'junk', 'trash', 'sandbag')     # (big but loose: what lies in a room)


def _drawn_field(gd, refs, v):
    seen = navgen.Field(v, -1.0)
    cache = {}
    for r in refs:
        if r['type'] != 'REFR':
            continue
        it = {'pos': r['pos'], 'rot': r['rot'], 'scale': r.get('scale', 1.0)}
        if r.get('model'):
            it['model'] = r['model']
        elif r.get('bkey') and not r['bkey'].startswith('+'):
            it['base'] = r['bkey']
        else:
            continue
        _solid, drawn = walkcheck._solid_and_drawn(gd, it, cache)
        if drawn:
            navgen._lay_ref(seen, walkcheck._ref(it), drawn)
    return seen


def arrivals(pr, ck):
    """Where you arrive in a place: every link from elsewhere to a door standing in it."""
    mine = (pr.cells.get(ck) or {}).get('refs', {})
    out = []
    for ock, c in pr.cells.items():
        if ock == ck:
            continue
        for rk, r in (c.get('refs') or {}).items():
            t = r.get('tel')
            if t and t.get('door') in mine:
                out.append(tuple(t['p'][:3]))
    return out


BIG = 240.0             # (a piece of the building: a kit's room, wall or floor piece is a square of 256 or a wall that tall)


def _built(gd, r):
    """Is a placed thing part of the building (a kit piece), not what stands in it (rubble, furniture, clutter)?"""
    import struct
    if r.get('door'):
        return True
    if r['base'] is None or r['base'] not in gd.forms:
        return False
    tag = gd.forms[r['base']][1].tag
    if tag == 'DOOR':
        return True
    if tag != 'STAT':
        return False
    if any(w in (gd.edid(r['base']) or '').lower() for w in LOOSE_WORDS):
        return False
    ob = gd.fields(r['base']).get('OBND')
    if not ob or len(ob) < 12:
        return False
    x0, y0, z0, x1, y1, z1 = struct.unpack('<6h', ob[:12])
    s = r.get('scale', 1.0)
    w, d, h = (x1 - x0) * s, (y1 - y0) * s, (z1 - z0) * s
    return (w >= BIG and d >= BIG) or (max(w, d) >= BIG and h >= BIG)


def check(gd, pr, ck, structure=False):
    """structure: walk the building alone (its kit pieces and doors), so clutter one could stand on (a heap of rubble with
    the ceiling low over it) doesn't read as a hole or a missing ceiling."""
    refs = [r for r in navbuild.place_refs(gd, pr, ck) if r['base'] is not None or r['type'] != 'REFR' or r.get('model') or r.get('door')]
    if structure:
        refs = [r for r in refs if _built(gd, r)]
    ways = arrivals(pr, ck)
    if not ways:
        return {'reached': 0, 'open_edges': 0, 'holes': 0, 'no_ceiling': 0, 'ways_in': 0, 'unreached_ways': 0, 'spots': [], 'why': 'no way in'}
    s = ways[0]
    w = kitplan.Walk(gd, refs, (s[0], s[1], s[2] + 8), erode=True)
    v = w.voxel
    doors = [r['pos'] for r in refs if r.get('door') or (r['base'] is not None and r['base'] in gd.forms and gd.forms[r['base']][1].tag == 'DOOR')]
    edges = w.open_edges()
    holes = [e for e in edges if not any(math.hypot(e[0] - d[0], e[1] - d[1]) < AT_DOOR and abs(e[2] - d[2]) < 200 for d in doors)]
    if holes:
        # (a hole only if it is still there with the loose things beside it left out: the rim of a heap of rubble one can
        # climb on reads as an edge over nothing, and isn't the building's)
        loose = [r for r in refs if not _built(gd, r) and any(math.hypot(r['pos'][0] - e[0], r['pos'][1] - e[1]) < LOOSE_NEAR for e in holes)]
        if loose:
            ids = {id(r) for r in loose}
            w2 = kitplan.Walk(gd, [r for r in refs if id(r) not in ids], (s[0], s[1], s[2] + 8), erode=True)
            again = w2.open_edges()
            holes = [e for e in holes if any(math.hypot(e[0] - f[0], e[1] - f[1]) < 48 and abs(e[2] - f[2]) < 48 for f in again)]
    seen = _drawn_field(gd, refs, v)
    g = w.graph
    sky, spots = 0, []
    for i in w.reached:
        iy, ix, z = g.p[i][0], g.p[i][1], g.p[i][2]
        if not any(c[1] >= z + UP_LO and c[0] <= z + UP_HI for c in seen.cols.get((iy, ix), ())):
            sky += 1
            if len(spots) < 6:
                spots.append(('no ceiling', round(ix * v), round(iy * v), round(z)))
    for e in holes[:6]:
        spots.append(('hole', round(e[0]), round(e[1]), round(e[2])))
    reached_cols = {(g.p[i][0], g.p[i][1]) for i in w.reached}
    unreached = 0
    for a in ways[1:]:
        cx, cy = int(a[0] // v), int(a[1] // v)
        if not any((cy + dy, cx + dx) in reached_cols for dx in range(-8, 9) for dy in range(-8, 9)):
            unreached += 1
    return {'reached': len(w.reached), 'open_edges': len(edges), 'holes': len(holes), 'no_ceiling': sky, 'ways_in': len(ways),
            'unreached_ways': unreached, 'spots': spots}
