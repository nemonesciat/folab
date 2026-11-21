"""No two neighbouring trees alike (treevary.py): FOLab's jungle trees spread over their kinds' variants.

Every spreading jungle tree, banyan and tall jungle tree a city's dressing stood was one of three models, so a grove read as
clones, near and above all far off (the user, 21 Nov 2026: "they all look like the same exact tree"). modelsets has two
more of each (`VARIANTS`: other seeds and proportions, the same trunk thickness, so the trunk's collision and the navmesh
round it are as they were), each with its own far model made from its own leaves (plantfar), so what is seen far off is
always what stands there when you come near.

`ops` swaps each of the mod's own trees of a kind for one of the kind's models by where it stands (the first model keeps
a third), records for the variants first; `matches` checks every far model against its own tree (crown's width, height
and middle within MATCH of the near leaves'); `spread` says how many of each a mod has."""
import math

import modelsets as ms

VARIANTS = {'jungle_tree': ('jungle_tree', 'jungle_tree_b', 'jungle_tree_c'),
            'jungle_banyan': ('jungle_banyan', 'jungle_banyan_b', 'jungle_banyan_c'),
            'jungle_tall': ('jungle_tall', 'jungle_tall_b', 'jungle_tall_c')}
MATCH = 0.2             # a far crown within this share of its near crown's width and height (and its middle within it)


def which(kinds, x, y):
    """The one of `kinds` a tree standing at (x, y) is: the same spot always gives the same, neighbours differ."""
    h = (int(round(x)) * 73856093 ^ int(round(y)) * 19349663) & 0xFFFFFFFF
    return kinds[(h >> 4) % len(kinds)]


def ops(gd, pr):
    """(ops, report): the variants' records (and their files, written into the mod's own as modelsets.put does), then a
    swap of each of the mod's own trees whose turn it is to be another of its kind."""
    import plantfar  # noqa: F401  (the far models: put through plantfar's build)
    out, made = [], {}
    keys = {}
    for kinds in VARIANTS.values():
        for p in kinds:
            o, info = ms.put(pr, p)
            if o:
                o[0]['name'] = 'tree_' + p
                out += o
                keys[p] = '$tree_' + p
            else:
                keys[p] = info['key']
    by_key = {}
    for kind, kinds in VARIANTS.items():
        for p in kinds:
            if not keys[p].startswith('$'):
                by_key[keys[p]] = kind
    rep = {k: {p: 0 for p in kinds} for k, kinds in VARIANTS.items()}
    for ck, c in pr.cells.items():
        for rk, r in (c.get('refs') or {}).items():
            kind = by_key.get(r.get('base'))
            if not kind or not rk.startswith('+') or r.get('removed') or not r.get('p'):
                continue
            want = which(VARIANTS[kind], r['p'][0], r['p'][1])
            rep[kind][want] += 1
            if keys[want] != r['base']:
                out.append({'op': 'swap', 'cell': ck, 'ref': rk, 'base': keys[want]})
                made[want] = made.get(want, 0) + 1
    return out, {'kinds': rep, 'swapped': sum(made.values()), 'cells': sorted({o['cell'] for o in out if o['op'] == 'swap'})}


def _box(shapes, keep):
    xs, ys, zs = [], [], []
    for s in shapes:
        if not keep(s):
            continue
        p = s['p']
        xs += p[0::3]
        ys += p[1::3]
        zs += p[2::3]
    if not xs:
        return None
    return min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)


def matches(pieces=None):
    """{piece: (ok, numbers)}: each tree's far crown against its near crown (the see-through leaves)."""
    import plantfar
    import nif
    out = {}
    for kinds in VARIANTS.values():
        for p in (pieces or kinds):
            if p not in kinds:
                continue
            m = plantfar.build(p)
            near = nif.mesh_from_nif(m['files'][m['mesh']])
            far = nif.mesh_from_nif(m['files'][m['mesh'][:-4] + '_lod.nif'])
            a = _box(near, lambda s: bool(s.get('alpha')) and 'vine' not in (s.get('tex') or '').lower())     # (leaves, not the hanging vines)
            b = _box(far, lambda s: 'canopy_far' in (s.get('tex') or '').lower())
            if not a or not b:
                out[p] = (False, {'near': a, 'far': b})
                continue
            w0, w1 = max(a[3] - a[0], a[4] - a[1]), max(b[3] - b[0], b[4] - b[1])
            h0, h1 = a[5] - a[2], b[5] - b[2]
            mid = math.hypot((a[0] + a[3] - b[0] - b[3]) / 2, (a[1] + a[4] - b[1] - b[4]) / 2)
            top = abs(a[5] - b[5])
            nums = {'width': (round(w0), round(w1)), 'height': (round(h0), round(h1)), 'middle_off': round(mid), 'top_off': round(top)}
            ok = abs(w1 - w0) <= MATCH * w0 and abs(h1 - h0) <= MATCH * max(h0, 200.0) and mid <= MATCH * w0 and top <= MATCH * max(h0, 200.0)
            out[p] = (ok, nums)
    return out
