"""Painting new land the way the land round it is painted: which ground textures the game shows at each steepness,
learnt from the cells nearby, laid on reshaped ground by its new slopes.

A quarter of a cell shows its base texture with up to six painted layers over it, each as strongly as its points say
(land.py). What shows at a point is worked out the same way the game lays them: the base, then each layer over what's
below in turn. Learning counts, for each band of steepness, how much each texture shows there in the game's own land;
painting gives each point the band's mix for its new slope, keeps what was there where the ground didn't change, on
roads and paths, and toward the edge of the area (so it blends into the cells round it), then lays the result back as
a base and layers, the textures that show most in each quarter first."""
import math

import land
import tes4

BANDS = [4, 9, 16, 25, 35, 90]           # steepness bands, in degrees (up to)
KEEP_WORDS = ('road', 'asphalt', 'path', 'pave', 'concrete', 'sidewalk', 'parking')
MAX_LAYERS = 6
Q = 17


def band(deg):
    for i, top in enumerate(BANDS):
        if deg <= top:
            return i
    return len(BANDS) - 1


def slope(h, gr, gc):
    """Steepness in degrees at land point (gr, gc) of a cell's 33 x 33 heights."""
    at = lambda r, c: h[min(32, max(0, r)) * 33 + min(32, max(0, c))]
    dx = (at(gr, gc + 1) - at(gr, gc - 1)) / (128 * (2 if 0 < gc < 32 else 1))
    dy = (at(gr + 1, gc) - at(gr - 1, gc)) / (128 * (2 if 0 < gr < 32 else 1))
    return math.degrees(math.atan(math.hypot(dx, dy)))


def shows(quarter, k):
    """{texture key: how much of it shows} at point k of a quarter."""
    out = {quarter.get('bkey'): 1.0} if quarter.get('bkey') else {}
    for l in quarter['layers']:
        a = l['a'][k]
        if a <= 0 or not l.get('key'):
            continue
        for t in out:
            out[t] *= (1 - a)
        out[l['key']] = out.get(l['key'], 0.0) + a
    return out


def learn(gd, world, cx, cy, reach=4, tex_cache=None):
    """[{texture key: share} for each band], and {texture key: picture} for the textures seen."""
    tex_cache = tex_cache if tex_cache is not None else {}
    sums = [dict() for _ in BANDS]
    pics = {}
    for dx in range(-reach, reach + 1):
        for dy in range(-reach, reach + 1):
            e = gd.land_at(world, cx + dx, cy + dy)
            if not e:
                continue
            L = land.decode(gd, e, tex_cache)
            if not L.get('h'):
                continue
            for q, quarter in enumerate(L['q']):
                if quarter.get('bkey'):
                    pics[quarter['bkey']] = quarter['base']
                for l in quarter['layers']:
                    pics[l['key']] = l['tex']
                qx, qy = q & 1, q >> 1
                for r in range(0, Q, 2):
                    for c in range(0, Q, 2):
                        b = sums[band(slope(L['h'], qy * 16 + r, qx * 16 + c))]
                        for t, v in shows(quarter, r * Q + c).items():
                            b[t] = b.get(t, 0.0) + v
    keep = {t for t in pics if _is_road(gd, t)}
    model = []
    for b in sums:
        b = {t: v for t, v in b.items() if t and t not in keep}
        tot = sum(b.values()) or 1.0
        top = sorted(b.items(), key=lambda kv: -kv[1])[:4]
        tt = sum(v for _t, v in top) or 1.0
        model.append({t: v / tt for t, v in top} if top else {})
        _ = tot
    # (an empty band takes its neighbour's mix)
    for i in range(len(model)):
        if not model[i]:
            near = [j for j in sorted(range(len(model)), key=lambda j: abs(j - i)) if model[j]]
            model[i] = dict(model[near[0]]) if near else {}
    return model, pics


def _is_road(gd, key):
    try:
        e = gd.edid(gd.from_key(key)).lower()
    except (ValueError, KeyError):
        return False
    return any(w in e for w in KEEP_WORDS)


def paint(gd, L, h_old, model, pics, weight):
    """L's quarters painted for its heights L['h']: weight(gr, gc) -> 0-1, how much the new paint counts at a land
    point (the area's edge fading it out). Returns new quarters."""
    h = L['h']
    out = []
    roads = {}
    for q, quarter in enumerate(L['q']):
        qx, qy = q & 1, q >> 1
        want = []
        for k in range(Q * Q):
            r, c = divmod(k, Q)
            gr, gc = qy * 16 + r, qx * 16 + c
            old = shows(quarter, k)
            top = max(old.items(), key=lambda kv: kv[1])[0] if old else None
            if top is not None and top not in roads:
                roads[top] = _is_road(gd, top)
            changed = abs(h[gr * 33 + gc] - h_old[gr * 33 + gc]) > 8
            w = weight(gr, gc) if changed and not (top and roads[top]) else 0.0
            if w <= 0:
                want.append(old)
                continue
            new = model[band(slope(h, gr, gc))]
            mix = {t: v * (1 - w) for t, v in old.items()}
            for t, v in new.items():
                mix[t] = mix.get(t, 0.0) + v * w
            want.append(mix)
        out.append(_lay(want, pics, quarter))
    return out


def _lay(want, pics, quarter):
    """Base and layers that show `want` (a {texture: share} per point) as nearly as the slots allow."""
    tot = {}
    for m in want:
        for t, v in m.items():
            tot[t] = tot.get(t, 0.0) + v
    order = [t for t, _v in sorted(tot.items(), key=lambda kv: -kv[1]) if t][:MAX_LAYERS + 1]
    if not order:
        return quarter
    base, rest = order[0], order[1:]
    layers = [{'key': t, 'tex': pics.get(t) or _pic_of(quarter, t), 'a': [0.0] * (Q * Q)} for t in rest]
    for k, m in enumerate(want):
        # the base under all; each layer over what's below, so that each shows its share
        below = m.get(base, 0.0)
        for l in layers:
            v = m.get(l['key'], 0.0)
            l['a'][k] = round(v / (below + v), 3) if below + v > 1e-6 else 0.0
            below += v
    layers = [l for l in layers if any(a > 0.0005 for a in l['a'])]
    return {'base': pics.get(base) or _pic_of(quarter, base), 'bkey': base, 'layers': layers}


def _pic_of(quarter, key):
    if quarter.get('bkey') == key:
        return quarter.get('base')
    return next((l['tex'] for l in quarter['layers'] if l.get('key') == key), None)
