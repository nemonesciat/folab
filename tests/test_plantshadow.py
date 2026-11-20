import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
"""FOLab's plants as nv-rs's sun shadows take them (shadowcast), and their see-through pictures as the game filters them.

Hanauma Bay, 19 Nov 2026: in nv-rs the user saw thin black lines across the ground and the water. The bamboo's and the
bushes' stems were opaque tubes 3 to 5 units thick, which nv-rs casts as cables out to 140 m, while their leaves (cut-outs)
cast only to 45 m: past that, the bare stems' shadows. Stems are now 'stick' parts (crossed see-through strips, at least
STICK_LEAST wide), which cast with the leaves."""
import math

import dds, modelmake, modelsets, nif, shadowcast, texpaint


def check(what, ok, got=None):
    print(('PASS ' if ok else 'FAIL ') + what + ('' if ok or got is None else '  ' + repr(got)))


# --- the checker itself: an opaque thin tube in a model with leaves is what cast the lines ---
leafy = {'name': 'T', 'shade': False,
         'looks': {'stem': {'tex': 'textures\\t\\stem.dds', 'tile': 32}, 'leaf': {'tex': 'textures\\t\\leaf.dds', 'alpha': True}},
         'parts': [{'shape': 'cylinder', 'r': 2.5, 'r2': 1.5, 'h': 400, 'sides': 5, 'caps': False, 'solid': False, 'look': 'stem', 'at': [k * 30, 0, 0]} for k in range(6)]
         + [{'shape': 'card', 'size': [120, 120], 'at': [0, 0, 380], 'look': 'leaf'}]}
f = shadowcast.faults(modelmake.make(leafy)['nif'])
check('six opaque stems 4 thick under leaves are cables nv-rs casts as bare lines', len(f) == 1 and f[0][1] == 6, f)
pole = dict(leafy, parts=leafy['parts'][:6])
check('the same stems with no leaves (poles) are what they are: no fault', shadowcast.faults(modelmake.make(pole)['nif']) == [])
trunk = dict(leafy, parts=[{'shape': 'cylinder', 'r': 14, 'h': 300, 'sides': 8, 'look': 'stem', 'solid': False}] + leafy['parts'][6:])
check('a trunk 28 thick under leaves casts as a trunk: no fault', shadowcast.faults(modelmake.make(trunk)['nif']) == [])

# --- a stick ---
sticky = dict(leafy, looks=dict(leafy['looks'], stem={'tex': 'textures\\t\\stem.dds', 'alpha': True, 'tile': 32, 'band': texpaint.STICK_BAND}),
              parts=[dict(p, shape='stick') for p in leafy['parts'][:6]] + leafy['parts'][6:])
made = modelmake.make(sticky)
check('the same stems as sticks: no fault', shadowcast.faults(made['nif']) == [], shadowcast.faults(made['nif']))
st = [s for s in nif.mesh_from_nif(made['nif']) if 'stem' in s['tex']][0]
check('a stick is drawn as a cut-out', st['alpha'] == 'test')
check('three strips of two sides each a stem 2.5 thick and over (12 triangles a stem)', len(st['i']) // 3 == 6 * 12, len(st['i']) // 3)
pts = [st['p'][k:k + 3] for k in range(0, len(st['p']), 3)]
foot = [p for p in pts if abs(p[2]) < 1e-3 and abs(p[0]) < 20]
wide = max(math.hypot(a[0] - b[0], a[1] - b[1]) for a in foot for b in foot)
check('its strips are at least STICK_LEAST wide (nv-rs takes under 7 for a cable)', wide >= modelmake.STICK_LEAST - 1e-6, wide)
us = st['uv'][0::2]
check('its picture stays within one repeat across (no stem showing twice)', 0 <= min(us) and max(us) <= 1, (min(us), max(us)))
b0, b1 = texpaint.STICK_BAND
a = (b1 - b0) * modelmake.STICK_LEAST / (4 * 1.5) * 2       # (the u-span the top, 1.5 thick, shows over a strip 9 wide)
check('it shows as much of the stem band as the stem is thick', abs((max(us) - min(us)) - min(a, 2 * min((b0 + b1) / 2, 1 - (b0 + b1) / 2))) < 1e-3, max(us) - min(us))
try:
    modelmake.make(dict(leafy, parts=[dict(leafy['parts'][0], shape='stick')]))
    check('a stick with an opaque look is refused', False)
except Exception as e:
    check('a stick with an opaque look is refused', 'see-through' in str(e), str(e))

# --- the stem picture ---
c = texpaint.stick(rings=2)
lo, hi = int(c.w * b0), int(c.w * b1)
check('the stem picture shows only down its band', all(c.a[y * c.w + x] == (1.0 if lo <= x < hi else 0.0) for y in (0, 77, 200) for x in range(c.w)))

# --- see-through pictures: the clear parts take the leaf's colour; far copies stay as full and as bright ---
leaf = texpaint.Canvas(64, 64, clear=(0, 0, 0))
for k in range(40):
    leaf.blade((8 + (k * 13) % 48, 60), (10 + (k * 29) % 44, 6), 5, (90, 160, 60))
rgb = texpaint.bled(leaf)
clear = [rgb[i] for i in range(64 * 64) if leaf.a[i] == 0]
check('clear pixels take the leaves\' colour, not the black they were filled with', clear and min(sum(p) / 3 for p in clear) > 60, min(sum(p) / 3 for p in clear))
data = texpaint.colour_map(leaf)
full = sum(1 for a in dds.decode(data, want=64)[2][3::4] if a >= texpaint.CUT) / 4096.0
w, h, small = dds.decode(data, want=8)[:3]
cover = sum(1 for a in small[3::4] if a >= texpaint.CUT) / float(w * h)
check('an eighth-size copy is as full as the picture (within 12 points)', abs(cover - full) < 0.12, (full, cover))
shown = [small[i:i + 3] for i in range(0, len(small), 4) if small[i + 3] >= texpaint.CUT]
g = sum(p[1] for p in shown) / len(shown)
check('and as bright: its leaves\' green within 8%% of theirs (%.0f)' % g, abs(g - 160) / 160 < 0.08, g)
plain = dds.encode(4, 4, bytes(range(64)))
check('a picture with no cut keeps its old copies byte for byte', plain == dds.encode(4, 4, bytes(range(64)), cut=None))

# --- every plant of FOLab's with stems: nothing casting past its leaves, nothing untextured, no slivers ---
for piece in ('bamboo', 'thicket', 'hibiscus', 'ti_green', 'slope_cover_a'):
    data = modelsets.build(piece)['nif']
    f = shadowcast.faults(data)
    shapes = nif.mesh_from_nif(data)
    sliver = 0
    for s in shapes:
        p, I = s['p'], s['i']
        for k in range(0, len(I), 3):
            P = [p[3 * i:3 * i + 3] for i in I[k:k + 3]]
            L = max(math.dist(P[0], P[1]), math.dist(P[1], P[2]), math.dist(P[2], P[0]))
            ar = shadowcast._area(p, I[k:k + 3])
            sliver += ar < 1e-6 or (L > 40 and 2 * ar / L < 1.5)
    check('%s: casts nothing past its leaves, every shape textured, no slivers' % piece, not f and all(s['tex'] for s in shapes) and not sliver, (f, sliver))
