"""What the Scatter brush puts down: the plants, rocks, trees and junk the game itself placed round a spot, learnt
from the cells near it, each with how often it's used there, the sizes it comes in, how deep it sits in the ground
(rocks are sunk, plants stand on it) and whether it leans with the slope."""
import struct

import land

SETS = [('plants', 'Plants'), ('rocks', 'Rocks'), ('trees', 'Trees'), ('junk', 'Junk & tumbleweeds')]
PLANT_WORDS = ('bush', 'shrub', 'agave', 'cactus', 'yucca', 'nettle', 'plant', 'weed', 'grass', 'flower', 'brush',
               'fern', 'creosote', 'sage', 'mesquite', 'datura')


def kind(btype, edid, model):
    """Which set a base form belongs to, or None (buildings, markers, things that do something)."""
    if btype not in ('STAT', 'MSTT') or not model:
        return None
    m, e = model.lower().replace('/', '\\'), edid.lower()
    if 'marker' in e or 'collision' in e or 'fx' in e[:3]:
        return None
    if 'tumbleweed' in e:
        return 'junk'
    if any(w in e or w in m for w in PLANT_WORDS):
        return 'plants'
    if 'tree' in e or '\\trees\\' in '\\' + m:
        return 'trees'
    if ('rock' in m or 'boulder' in e) and 'cliff' not in e and 'cliff' not in m:
        return 'rocks'
    if 'tumbleweed' in e or '\\junk\\' in m or 'debris' in m or 'woodplanks' in e or 'rubble' in e:
        return 'junk'
    return None


def learn(gd, world, cx, cy, reach=3, top=12):
    """{set: [{key, edid, model, n, smin, smax, dz, tilt}]} from the cells within reach of (cx, cy)."""
    grid = gd.grid(world)
    seen = {}
    heights = {}

    def ground(x, y):
        k = (int(x // 4096), int(y // 4096))
        if k not in heights:
            e = gd.land_at(world, *k)
            heights[k] = land.heights_of(dict(land.tes4.iter_subrecords(gd.plugins[e[0]].data(e[1])))['VHGT']) if e else None
        h = heights[k]
        if not h:
            return None
        fx, fy = (x - k[0] * 4096) / 128, (y - k[1] * 4096) / 128
        c0, r0 = min(31, int(fx)), min(31, int(fy))
        tx, ty = fx - c0, fy - r0
        p = lambda r, c: h[r * 33 + c]
        return (p(r0, c0) * (1 - tx) + p(r0, c0 + 1) * tx) * (1 - ty) + (p(r0 + 1, c0) * (1 - tx) + p(r0 + 1, c0 + 1) * tx) * ty

    for dx in range(-reach, reach + 1):
        for dy in range(-reach, reach + 1):
            c = grid.get((cx + dx, cy + dy))
            if c is None:
                continue
            for r in gd.refs(c):
                if not r['pos'] or r['base'] not in gd.forms or r['pos'][2] < -20000:
                    continue
                btype, edid, _n, model = gd.describe(r['base'])
                k = kind(btype, edid, model)
                if not k:
                    continue
                s = seen.setdefault(r['base'], {'kind': k, 'edid': edid, 'model': gd.model_path(btype, model), 'type': btype,
                                                 'n': 0, 'scales': [], 'dz': [], 'tilt': 0.0})
                s['n'] += 1
                s['scales'].append(r['scale'])
                g = ground(*r['pos'][:2])
                if g is not None:
                    s['dz'].append(r['pos'][2] - g)
                s['tilt'] = max(s['tilt'], abs(r['rot'][0]), abs(r['rot'][1]))
    out = {k: [] for k, _l in SETS}
    for fid, s in seen.items():
        dz = sorted(s['dz'])
        out[s['kind']].append({'key': gd.key(fid), 'edid': s['edid'], 'model': s['model'], 'type': s['type'], 'n': s['n'],
                               'smin': round(min(s['scales']), 2), 'smax': round(max(s['scales']), 2),
                               'dz': round(dz[len(dz) // 2], 1) if dz else 0.0, 'tilt': round(min(s['tilt'], 0.6), 2)})
    for k in out:
        out[k].sort(key=lambda b: -b['n'])
        out[k] = out[k][:top]
    return out
