"""How far each shape of a model casts in nv-rs's sun shadows, worked out as nv-rs works it out.

nv-rs (the Rust port, `crates/d3d9-wgpu/src/sun_shadow.rs`) adds sun shadows the original game never had. It looks at
each draw (one shape of a mesh) by its triangles alone and sorts it:

  * a geometry wider than many cables side by side (its area over its longest side at least `MANY_CABLES` x
    `THIN_WIDTH` x pi) is one caster, never split;
  * else it is split into connected pieces (corners welded by place; triangles with no area join nothing), each a
    strand with a width (twice its corners' mean distance from its centreline) and a length. A strand under
    `THIN_WIDTH` wide and over `THIN_LENGTH` widths long is a round cable; a flat strip under `RIBBON_WIDTH` wide
    and over `RIBBON_LENGTH` widths long is a ribbon.
  * Round cables cast in every cascade, out to `FAR`, as a line of their own (the coverage maps), whether the draw is
    alpha-tested or not. Alpha-tested draws (cut-outs: leaves, fences) cast only out to `CUTOUT_FAR`; a cut-out's
    ribbons too. Anything else opaque casts to `FAR`.

So a plant whose leaves are cut-outs and whose stems are opaque tubes a few units thick casts, past `CUTOUT_FAR`, its
bare stems as long dark lines with no leaves round them (Hanauma Bay, 19 Nov 2026: bamboo and thicket stems drew
lines across the beach and the water with the sun low). `report` says per shape what nv-rs makes of it; `faults`
names the ones that cast as bare lines.

The centreline here is the piece's main axis (its corners' principal direction), not nv-rs's walk over the surface:
the two agree on straight pieces (stems, canes, poles, strips), which is what this is for."""
import math

import nif

THIN_WIDTH = 7.0
THIN_LENGTH = 20.0
RIBBON_WIDTH = 64.0
RIBBON_LENGTH = 8.0
FLAT = 2.5
MANY_CABLES = 16.0
BITS = 0.1
FAR = 10000.0           # (game units: about 143 m)
CUTOUT_FAR = 3150.0     # (the first three of four cascades: about 45 m, as its PLAYTESTING notes say)
WELD = 0.01


def _pieces(p, idx):
    """Connected pieces of a shape's triangles: [[triangle number, ...], ...], corners welded by place."""
    key = {}
    weld = []
    for k in range(0, len(p), 3):
        q = (round(p[k] / WELD), round(p[k + 1] / WELD), round(p[k + 2] / WELD))
        weld.append(key.setdefault(q, len(key)))
    parent = list(range(len(key)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    tris = []
    for t in range(0, len(idx), 3):
        a, b, c = (weld[i] for i in idx[t:t + 3])
        if _area(p, idx[t:t + 3]) <= 1e-9:
            continue
        tris.append(t // 3)
        for x, y in ((a, b), (b, c)):
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[rx] = ry
    out = {}
    for t in tris:
        out.setdefault(find(weld[idx[3 * t]]), []).append(t)
    return list(out.values())


def _area(p, tri):
    a, b, c = (p[3 * i:3 * i + 3] for i in tri)
    u = [b[k] - a[k] for k in range(3)]
    v = [c[k] - a[k] for k in range(3)]
    n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    return 0.5 * math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2])


def strand(p, idx, tris):
    """{'width', 'length', 'area'} of one piece."""
    corners = sorted({i for t in tris for i in idx[3 * t:3 * t + 3]})
    pts = [tuple(p[3 * i:3 * i + 3]) for i in corners]
    m = [sum(q[k] for q in pts) / len(pts) for k in range(3)]
    d = [[q[k] - m[k] for k in range(3)] for q in pts]
    cov = [[sum(v[a] * v[b] for v in d) for b in range(3)] for a in range(3)]
    ax = [1.0, 0.7, 0.3]
    for _ in range(60):                         # (the main axis by power iteration)
        ax = [sum(cov[a][b] * ax[b] for b in range(3)) for a in range(3)]
        ln = math.sqrt(sum(v * v for v in ax)) or 1.0
        ax = [v / ln for v in ax]
    along = [sum(v[k] * ax[k] for k in range(3)) for v in d]
    off = [math.sqrt(max(0.0, sum(v[k] * v[k] for k in range(3)) - s * s)) for v, s in zip(d, along)]
    return {'width': 2 * sum(off) / len(off), 'length': max(along) - min(along), 'area': sum(_area(p, idx[3 * t:3 * t + 3]) for t in tris)}


def thin(s):
    return s['width'] < THIN_WIDTH and s['length'] > THIN_LENGTH * s['width']


def ribbon(s):
    return s['width'] < RIBBON_WIDTH and s['length'] > RIBBON_LENGTH * s['width'] and s['area'] < FLAT * s['length'] * s['width']


def shape_cast(shape):
    """What nv-rs makes of one shape (nif.mesh_from_nif's, placed=True): {'cutout', 'split', 'cables', 'pieces',
    'reach', 'line_reach'}. reach: how far its body casts; line_reach: how far its round cables cast as lines (0: none)."""
    p, idx = shape['p'], shape['i']
    cutout = shape.get('alpha') == 'test'
    out = {'cutout': cutout, 'split': False, 'cables': 0, 'pieces': 0, 'reach': CUTOUT_FAR if cutout else FAR, 'line_reach': 0.0}
    if not idx:
        out['reach'] = 0.0
        return out
    xs = [p[k::3] for k in range(3)]
    long = max(max(x) - min(x) for x in xs)
    area = sum(_area(p, idx[t:t + 3]) for t in range(0, len(idx), 3))
    if area / max(long, 1e-6) >= MANY_CABLES * THIN_WIDTH * math.pi:
        return out
    out['split'] = True
    strands = [strand(p, idx, t) for t in _pieces(p, idx)]
    out['pieces'] = len(strands)
    cables = [s for s in strands if thin(s)]
    out['cables'] = len(cables)
    out['narrow'] = round(sum(s['area'] for s in strands if s['width'] < THIN_WIDTH) / max(1e-9, sum(s['area'] for s in strands)), 3)
    out['widths'] = sorted(round(s['width'], 1) for s in cables)[:6]
    if cables:
        out['line_reach'] = FAR                 # (round cables cast in every cascade, cut-out or not)
        lines = [s for s in strands if thin(s) or ribbon(s)]
        if sum(s['area'] for s in strands if s not in lines) <= BITS * sum(s['area'] for s in strands):
            out['reach'] = 0.0 if all(thin(s) for s in lines) else out['reach']    # (all cables: nothing but the lines)
    return out


def report(nif_bytes):
    """[(texture, triangles, shape_cast), ...] for a mesh."""
    return [(s['tex'], len(s['i']) // 3, shape_cast(s)) for s in nif.mesh_from_nif(nif_bytes)]


def faults(nif_bytes):
    """Shapes of a model with see-through leaves that cast farther than its leaves as bare sticks: round cables (cast as
    lines out to FAR whatever the draw), or a shape more than BITS of whose area is opaque pieces under THIN_WIDTH
    thick (short stems: cast hard out to FAR; a trunk's few twigs are not that). [(texture, cables, narrow share)]. A model with no cut-outs (a pole, a sign) is left alone: its lines are what it is."""
    rep = report(nif_bytes)
    if not any(c['cutout'] for _t, _n, c in rep):
        return []
    return [(t, c['cables'], c.get('narrow', 0)) for t, _n, c in rep
            if c['line_reach'] > CUTOUT_FAR or (c['reach'] > CUTOUT_FAR and c.get('narrow', 0) > BITS)]


if __name__ == '__main__':
    import sys
    for f in sys.argv[1:]:
        print(f)
        for t, n, c in report(open(f, 'rb').read()):
            print('  %5d tris %-7s reach %5.0f lines %5.0f  %3d cables of %3d pieces %s  %s' % (
                n, 'cut-out' if c['cutout'] else 'opaque', c['reach'], c['line_reach'], c['cables'], c['pieces'], c.get('widths', ''), t))
