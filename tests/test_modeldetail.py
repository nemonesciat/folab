import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
"""FOLab's own models as the game's are made (measured over its buildings, plants and clutter): edges rounded off, shade
baked into the corners' colours, normal maps as strong as the game's and half the colour picture's size; and the
Missouri's ladders walked from her quarterdeck to her bridge wings."""
import math

import battleship, dds, modelmake, modelsets, nif, nifmake, shade, texpaint, walkcheck


def check(what, ok, got=None):
    print(('PASS ' if ok else 'FAIL ') + what + ('' if ok or got is None else '  ' + repr(got)))


LOOKS = {'a': {'tex': 'textures\\folab\\t\\a.dds', 'normal': 'textures\\folab\\t\\a_n.dds', 'tile': 64}}

# --- rounded edges ---
box = {'name': 'T', 'looks': LOOKS, 'parts': [{'shape': 'box', 'size': [200, 100, 80], 'look': 'a'}], 'shade': False}
sharp = modelmake.make(dict(box, bevel=0))
round_ = modelmake.make(dict(box, bevel=6))
check('a sharp box is twelve triangles', sharp['triangles'] == 12, sharp['triangles'])
check('a rounded box: six faces drawn in, a strip on each edge, a face at each corner (44 triangles)', round_['triangles'] == 44, round_['triangles'])
check('rounding keeps the box its size', round_['box'] == sharp['box'], (round_['box'], sharp['box']))
check('it reads back as it was made', nifmake.check(round_['nif'], round_['shapes'], round_['solids']) == [])
s = round_['shapes'][0]
normals = {tuple(round(v, 3) for v in s['n'][k:k + 3]) for k in range(0, len(s['n']), 3)}
check('a rounded box\'s corners keep their faces\' normals, so the light turns smoothly over its edges', len(normals) == 6, normals)
check('its collision is the whole box still', len(round_['solids']) == 1 and len(round_['solids'][0]['points']) == 8)
auto = modelmake.make(dict(box))
check('by default a box is rounded by a tenth of its thinnest side', auto['triangles'] == 44)
thin = modelmake.make({'name': 'T', 'looks': LOOKS, 'parts': [{'shape': 'box', 'size': [4, 400, 4], 'look': 'a'}], 'shade': False})
check('a rail too thin to round is left sharp', thin['triangles'] == 12, thin['triangles'])
cyl = modelmake.make({'name': 'T', 'looks': LOOKS, 'parts': [{'shape': 'cylinder', 'r': 60, 'h': 120, 'sides': 12, 'look': 'a'}], 'shade': False})
check('a cylinder is rounded where its side meets its ends (side, two bands, two caps)', cyl['triangles'] == 12 * 2 * 3 + 2 * 10, cyl['triangles'])

# --- a stretched many-sided part lies square (the Missouri's houses lay skewed) ---
oct_ = modelmake._parts({'name': 'T', 'looks': LOOKS, 'parts': [{'shape': 'cylinder', 'r': 100, 'h': 10, 'sides': 8, 'phase': 22.5, 'scale': [3, 10, 1], 'look': 'a'}]}, None, 0)
p = oct_.by_look['a']['p']
xs = [round(p[k], 1) for k in range(0, len(p), 3)]
ys = [round(p[k + 1], 1) for k in range(0, len(p), 3)]
far_y = [x for x, y in zip(xs, ys) if abs(y - max(ys)) < 0.5]
check('a stretched eight-sided house is the same both sides and flat at its ends', abs(max(xs) + min(xs)) < 0.5 and abs(max(far_y) + min(far_y)) < 0.5 and max(far_y) > 50, (max(xs), min(xs), far_y))

# --- shade baked into the corners ---
house = {'name': 'TShade', 'looks': LOOKS, 'parts': [{'shape': 'box', 'size': [600, 600, 300], 'look': 'a'},
                                                    {'shape': 'box', 'size': [200, 200, 200], 'at': [0, 0, 300], 'look': 'a'}]}
m = modelmake.make(house)
back = nif.mesh_from_nif(m['nif'])
check('a shaded model carries a colour at every corner, read back from its file', back and all(len(b.get('c', ())) == len(b['p']) for b in back))
s = m['shapes'][0]
low = [sum(s['c'][4 * (k // 3):4 * (k // 3) + 3]) / 3 for k in range(0, len(s['p']), 3) if s['p'][k + 2] < 20 and s['n'][k + 2] < 0.5]
roof = [sum(s['c'][4 * (k // 3):4 * (k // 3) + 3]) / 3 for k in range(0, len(s['p']), 3) if s['p'][k + 2] > 299 and s['n'][k + 2] > 0.9
        and max(abs(s['p'][k]), abs(s['p'][k + 1])) > 250]
corner = [sum(s['c'][4 * (k // 3):4 * (k // 3) + 3]) / 3 for k in range(0, len(s['p']), 3) if s['p'][k + 2] > 299 and s['n'][k + 2] > 0.9
          and max(abs(s['p'][k]), abs(s['p'][k + 1])) < 110]
check('walls are darker where they meet the ground than the open roof', low and roof and sum(low) / len(low) < sum(roof) / len(roof) - 0.15,
      (sum(low) / len(low), sum(roof) / len(roof)))
check('the roof is darker in the corner against the block on it', corner and sum(corner) / len(corner) < sum(roof) / len(roof) - 0.1,
      (sum(corner) / len(corner), sum(roof) / len(roof)))
check('faces were cut finer to hold the shade, within what was allowed', 12 * 2 < m['triangles'] <= 44 * 2 + max(300, 600 * modelmake.SHADE_MORE_A_UNIT) + 50, m['triangles'])
mean = shade.bake([dict(x) for x in m['shapes']])
check('a building\'s mean shade is about the game\'s (0.61 to 0.75 over its buildings)', 0.55 < mean < 0.85, mean)

# --- normal maps ---
c = texpaint.Canvas(512, 512)
for i in range(512 * 512):
    c.rgb[i] = (120 + 40 * ((i // 37) % 2), 120, 120)
col, nor = c.files(game=True)
ni, ci = dds.info(nor), dds.info(col)
check('a picture 512 across has its normal map at half its size, as the game\'s', ni['w'] == 256 and ci['w'] == 512, (ci, ni))
import texwear
col2, nor2 = texwear.steel(colour=(92, 96, 98), size=256, seed=975, rust=0.5, flake=0.3, gloss=30).files(game=True)
old = texwear.steel(colour=(92, 96, 98), size=256, seed=975, rust=0.5, flake=0.3, gloss=30).files()[1]


def lean(data):
    w, h, px = dds.decode(data, want=256)[:3]
    t = [math.degrees(math.acos(max(-1, min(1, (px[k + 2] / 127.5 - 1) / (math.sqrt(sum((px[k + j] / 127.5 - 1) ** 2 for j in range(3))) or 1)))))
         for k in range(0, w * h * 4, 4 * 11)]
    return sum(t) / len(t)
check("the ship's painted steel now leans the light as the game's do (5 to 12 degrees on average; it was about 2)", 5 <= lean(nor2) <= 14 and lean(old) < 4, (lean(old), lean(nor2)))
check('the shader shines by the normal map\'s fourth number, as most of the game\'s buildings', b'\x01\x00\x00\x82' in m['nif'])

# --- far models: masses only ---
modelsets._all_sets()
desc = modelsets.PIECES['makai_tower']['describe']()
far = modelsets.far_of(desc)
fm = modelmake.make(far)
check('a far model has no baked shade and no rounding', not any(s.get('c') for s in fm['shapes']) and far['bevel'] == 0)

# --- the Missouri ---
d = battleship.missouri()
mm = modelmake.make(d)
check('the Missouri: under the game\'s biggest building pieces (33,748 triangles; she is 270 m)', mm['triangles'] < 36000, mm['triangles'])
check('no shape of hers over 65,535 corners', all(len(s['p']) // 3 < 65535 for s in mm['shapes']))
Z = d['levels']
sol = [s for s in mm['solids'] if any(-2600 < q[1] < 3700 for q in s['points']) and max(q[2] for q in s['points']) > 300]
w_ = walkcheck.Walk(sol, margin=40.0, ground=-5000.0)
dz = battleship.deck_z(3400)
start = [(i, j, z) for (i, j), zs in w_.stand.items() for z in zs if abs(z - dz) < 25 and 3250 < w_.y0 + j * walkcheck.STEP < 3600]
seen, todo = set(start), list(start)
while todo:
    i, j, z = todo.pop()
    a = (w_.x0 + i * walkcheck.STEP, w_.y0 + j * walkcheck.STEP)
    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        n = (i + di, j + dj)
        for z2 in w_.stand.get(n, ()):
            if (n[0], n[1], z2) in seen or z2 - z > walkcheck.CLIMB or z - z2 > walkcheck.DROP:
                continue
            if w_._blocked(a, z, (w_.x0 + n[0] * walkcheck.STEP, w_.y0 + n[1] * walkcheck.STEP), z2):
                continue
            seen.add((n[0], n[1], z2))
            todo.append((n[0], n[1], z2))
got = {}
for name, lv in (('01', Z[0]), ('02', Z[1]), ('03', Z[2]), ('bridge wings', Z[2] + 4)):
    got[name] = sum(1 for (i, j), zs in w_.stand.items() for z in zs if abs(z - lv) <= 12 and (i, j, z) in seen)
check('her ladders walk from the quarterdeck to the 01, 02 and 03 levels and the bridge wings', all(v > 300 for v in got.values()), got)
