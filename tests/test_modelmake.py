import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
"""Models made from nothing: the beach kiosk and umbrella are built, read back through FOLab's own readers of meshes and
of collision, laid out block for block as a static of the game's is, and put in a mod as files and a record."""
import math
import struct

import dds, gamedata, hkshape, library, modelmake, modelsets, nif, nifmake, project, recordio


def check(what, ok, got=None):
    print(('PASS ' if ok else 'FAIL ') + what + ('' if ok or got is None else '  ' + repr(got)))


def in_game():
    """What the game's own folder holds of FOLab's models (a mod put in the game by the user's choice may have some)."""
    out = []
    for kind in ('meshes', 'textures'):
        for d, _dirs, files in os.walk(os.path.join(gamedata.find_data_dir() or '', kind, 'folab')):
            out += [(os.path.join(d, f), os.path.getmtime(os.path.join(d, f))) for f in files]
    return sorted(out)


game_before = in_game()

# --- strips ---
quad = [0, 1, 2, 0, 2, 3]
s = nifmake.strip(quad)
check('two triangles that share an edge are one run of four corners', len(s) == 4)
lone = [0, 1, 2, 3, 4, 5, 6, 7, 8]
s = nifmake.strip(lone)
back = []
for k in range(len(s) - 2):
    a, b, c = s[k:k + 3]
    if len({a, b, c}) == 3:
        back.append((a, b, c) if k % 2 == 0 else (a, c, b))
turn = lambda t: min((t[i], t[(i + 1) % 3], t[(i + 2) % 3]) for i in range(3))
check('triangles apart are joined without any turning over', sorted(turn(t) for t in back) == [(0, 1, 2), (3, 4, 5), (6, 7, 8)])

# --- the two pieces ---
gd = gamedata.GameData()
game = nif.Nif(gd.read_file('meshes\\clutter\\junk\\nvsandwichboard02.nif'))
want_tris = {'kiosk': 336, 'umbrella': 210}
made = {}
check('the set lists its pieces', set(modelsets.PIECES) >= {'kiosk', 'umbrella', 'palm_tall', 'banana', 'hibiscus', 'dune_grass'})
for piece in ('kiosk', 'umbrella'):
    m = made[piece] = modelsets.build(piece)
    data = m['nif']
    check('%s: reads back as what was asked for (corners, facing, textures, collision)' % piece, nifmake.check(data, m['shapes'], m['solids']) == [])
    back = nif.mesh_from_nif(data)
    plain = modelmake.make(dict(modelsets.PIECES[piece]['describe'](), shade=False, bevel=0))
    check('%s: %d triangles as drawn, sharp and unshaded; all of them read back as built' % (piece, want_tris[piece]),
          plain['triangles'] == want_tris[piece] and sum(len(s['i']) // 3 for s in back) == m['triangles'] <= modelmake.MOST_THING, (plain['triangles'], m['triangles']))
    names = sorted({s['tex'] for s in back})
    check('%s: its textures are the set\'s own' % piece, names and all(t.startswith('textures\\folab\\beach\\') and t in m['files'] for t in names))
    n = nif.Nif(data)
    for i in range(len(n.types)):
        n.block(i)                              # (raises if a block isn't exactly its size in the table)
    check('%s: every block is the size the file says' % piece, n.offsets[-1] + n.sizes[-1] + 8 == len(data))
    sets = [n.block(i)['textures'] for i, t in enumerate(n.types) if t == 'BSShaderTextureSet']
    check('%s: each shape has a colour texture and a normal map' % piece,
          all(len(t) == 6 and t[1] == t[0][:-4] + '_n.dds' and t[1] in m['files'] for t in sets))
    # laid out as the game lays out a static with a list of convex solids
    mine = [t for t in n.types]
    per_shape = ['NiTriStrips', 'BSShaderPPLightingProperty', 'BSShaderTextureSet', 'NiMaterialProperty', 'NiTriStripsData']
    start = mine.index('NiTriStrips')
    check('%s: the game\'s order of blocks' % piece, mine[:2] == game.types[:2] == ['BSFadeNode', 'BSXFlags']
          and mine[start - 3:start] == ['bhkListShape', 'bhkRigidBody', 'bhkCollisionObject'] == game.types[5:8]
          and set(mine[2:start - 3]) == {'bhkConvexVerticesShape'}
          and mine[start:] == per_shape * len(back) and game.types[8:] == per_shape)
    body = mine.index('bhkRigidBody')
    theirs = game.types.index('bhkRigidBody')
    a = data[n.offsets[body]:n.offsets[body] + n.sizes[body]]
    b = game.data[game.offsets[theirs]:game.offsets[theirs] + game.sizes[theirs]]
    # (the game's spare bytes hold whatever was in memory: compare what is read)
    said = lambda d: (d[4:8], d[12], d[16:28], d[28], d[30:32], d[36:40], d[44], d[46:48], d[52:64], d[68:216], d[228:236])
    check('%s: its body says what the game\'s static body says' % piece, len(a) == len(b) == 236 and said(a) == said(b))
    shapes = hkshape.collision_shapes(data)
    check('%s: the collision reader takes it: %d solid parts on the static layer' % (piece, len(m['solids'])),
          len(shapes) == len(m['solids']) and all(s['layer'] in hkshape.LAYERS_SOLID and s['i'] for s in shapes))
    for rel, d in m['files'].items():
        if rel.endswith('.dds'):
            i = dds.info(d)
            if not i or i['w'] & (i['w'] - 1) or i['h'] & (i['h'] - 1) or i['mips'] < 5 or not dds.decode(d, 16):
                check('%s: %s is a texture the game can take' % (piece, rel), False)
    check('%s: %d textures drawn, sides powers of two, smaller copies and all' % (piece, len(m['files']) - 1), len(m['files']) > 4)

k = made['kiosk']
check('the kiosk stands on the ground, 3 to 4 metres across', k['box'][2] in (-1, 0) and 210 < k['box'][4] - k['box'][1] + 40 and 300 < k['box'][3] - k['box'][0] < 360)
u = made['umbrella']
sh = hkshape.collision_shapes(u['nif'])
canopy = max(sh, key=lambda s: max(s['v'][0::3]))
check('the umbrella\'s canopy is solid only over head height', min(canopy['v'][2::3]) > 140)
pole = [s for s in sh if s is not canopy and max(s['v'][2::3]) > 100]
check('and under it only the pole is in the way', len(pole) == 1 and max(abs(v) for v in pole[0]['v'][0::3]) < 4)

# --- growing things: leaves see-through where their picture is ---
yucca = nif.Nif(gd.read_file('meshes\\landscape\\trees\\nvbananayucca.nif'))
theirs = next(yucca.data[yucca.offsets[i] + 12:yucca.offsets[i] + 15] for i, t in enumerate(yucca.types) if t == 'NiAlphaProperty')
want = {'palm_tall': (8, 2), 'palm_young': (8, 2), 'banana': (1, 1), 'hibiscus': (0, 2), 'dune_grass': (0, 1), 'tiki_torch': (1, 0)}
for piece, (solid, leafy) in want.items():
    m = made[piece] = modelsets.build(piece)
    data = m['nif']
    n = nif.Nif(data)
    for i in range(len(n.types)):
        n.block(i)
    back = nif.mesh_from_nif(data)
    check('%s: reads back as asked, %d triangles, %d solid parts' % (piece, m['triangles'], solid),
          nifmake.check(data, m['shapes'], m['solids']) == [] and len(hkshape.collision_shapes(data)) == solid == len(m['solids'])
          and sum(len(s['i']) // 3 for s in back) == m['triangles'] and n.offsets[-1] + n.sizes[-1] + 8 == len(data))
    cut = [s for s in back if s['alpha'] == 'test']
    check('%s: %d see-through shapes, each over a picture that is see-through' % (piece, leafy), len(cut) == leafy and all(
        min(dds.decode(m['files'][s['tex']], 64)[2][3::4]) == 0 and max(dds.decode(m['files'][s['tex']], 64)[2][3::4]) == 255 for s in cut))
    if leafy:
        mine = [data[n.offsets[i] + 12:n.offsets[i] + 15] for i, t in enumerate(n.types) if t == 'NiAlphaProperty']
        check('%s: cut out the way the game cuts its plants\' leaves' % piece, len(mine) == leafy and struct.unpack('<HB', mine[0])[0] == struct.unpack('<HB', theirs)[0] == 4844)
    if not solid:
        check('%s: nothing to walk into, so no collision blocks at all' % piece, not any(t.startswith('bhk') or t == 'BSXFlags' for t in n.types))
tall = made['palm_tall']
trunk = hkshape.collision_shapes(tall['nif'])
check('a palm is 9 metres or so and only its trunk stops you', 600 < tall['box'][5] < 800 and max(max(abs(v) for v in s['v'][1::3]) for s in trunk) < 20)
leaf = next(s for s in nif.mesh_from_nif(made['banana']['nif']) if s['alpha'])
P = lambda i: leaf['p'][3 * i:3 * i + 3]
seen = {}
for i in range(0, len(leaf['i']), 3):
    t = leaf['i'][i:i + 3]
    seen.setdefault(frozenset(tuple(round(c, 1) for c in P(k)) for k in t), []).append(t)
check('every leaf is there twice, once for each side', all(len(v) == 2 for v in seen.values()))

# --- parts ---
one = modelmake.make({'name': 'T', 'looks': {'a': {'tex': 'textures\\a.dds', 'tile': 64}, 'b': {'tex': 'textures\\b.dds', 'region': (0, 0, 0.5, 1)}},
                      'parts': [{'shape': 'box', 'size': [10, 20, 30], 'at': [100, 0, 0], 'look': 'a', 'faces': {'front': 'b'}}], 'shade': False, 'bevel': 0})
back = {s['tex']: s for s in nif.mesh_from_nif(one['nif'])}
b = back['textures\\b.dds']
check('a box has six faces, the one named apart in its own look', len(back['textures\\a.dds']['i']) == 30 and len(b['i']) == 6)
check('a fitted face shows its region once', sorted(set(b['uv'][0::2])) == [0.0, 0.5] and sorted(set(b['uv'][1::2])) == [0.0, 1.0])
check('the front is the side towards -y', set(b['p'][1::3]) == {-10.0} and one['box'] == [95, -10, 0, 105, 10, 30])
check('one solid part is a convex shape on its own, as the game\'s are', 'bhkListShape' not in nif.Nif(one['nif']).types
      and nifmake.check(one['nif'], one['shapes'], one['solids']) == [])
thin = nifmake.hull([(0, 0, 0), (70, 0, 0), (70, 70, 0), (0, 70, 0), (0, 0, 1), (70, 0, 1), (70, 70, 1), (0, 70, 1)],
                    [[3, 2, 1, 0], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]])
check('a solid too thin for Havok\'s usual radius gets a smaller one', 0 < thin[2] < nifmake.HULL_RADIUS and min(p[2] for p in thin[0]) > 0 and max(p[2] for p in thin[0]) < 1 / 7.0)

# --- in a mod ---
pr = project.Project.create('Model Test')
gd.overlay = library.Overlay(lambda: pr)
ops, info = modelsets.put(pr, 'kiosk')
check('a piece asks for one new record', [o['op'] for o in ops] == ['record_new'] and info['key'] is None)
keys = pr.apply('Make kiosk', ops)
rec = pr.records[keys[0]]
check('a static of the mod\'s own, drawn with the mod\'s own mesh', rec['type'] == 'STAT' and recordio.field(rec, 'EDID') == 'FOLabBeachKiosk'
      and recordio.field(rec, 'MODL') == 'folab\\beach\\kiosk.nif')
check('the game\'s files are looked for in the mod first', gd.find_file('meshes\\folab\\beach\\kiosk.nif') == 'your mod'
      and gd.read_file('meshes\\folab\\beach\\kiosk.nif') == k['nif'] and all(gd.find_file(f) == 'your mod' for f in info['files']))
check('its bounds are the mesh\'s', library.bounds_of(k['nif']) == info['box'])
ops2, info2 = modelsets.put(pr, 'kiosk')
check('asked for again, the same record serves', ops2 == [] and info2['key'] == keys[0])
check('nothing was written into the game', in_game() == game_before)

# --- on a map: the set's plants where the scatter would have put the Mojave's ---
import osmcover, osmdress, roadgen  # noqa: E402

world = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
grid = gd.grid(world)
g0 = roadgen.Ground(gd, None, world)
flat = lambda k: None not in [g0.cell((k[0] + dx, k[1] + dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1)] and min(g0.cell(k)) > 2000
xy = next(k for k in sorted(grid) if flat(k))
x, y = xy[0] * 4096.0 + 2048, xy[1] * 4096.0 + 2048


class Cover:
    """All of it one kind of ground."""
    def __init__(self, kind):
        self.gx0, self.gy0 = int(x // 128) - 60, int(y // 128) - 60
        self.A = self.D = 121
        self.kind = bytearray([osmcover.ORDER.index(kind) + 1]) * (self.A * self.D)
        self.built = bytearray(self.A * self.D)


pm = project.Project.create('Beach Map')
gd.overlay = library.Overlay(lambda: pm)
first, sw = modelsets.swaps(pm)
check('every stand-in piece is written and asks for its record', sorted(o['name'] for o in first) == ['model_banana', 'model_dune_grass', 'model_hibiscus', 'model_palm_tall', 'model_palm_young']
      and all(gd.find_file('meshes\\folab\\beach\\%s.nif' % f) == 'your mod' for f in ('palm_tall', 'palm_young', 'banana', 'hibiscus', 'dune_grass')))
plain, _rep = osmdress.ops(gd, pm, world, Cover('yard'), [], 5)
ours, rep = osmdress.ops(gd, pm, world, Cover('yard'), [], 5, swaps=sw)
game_key = {gd.edid(f).lower(): gd.key(f) for f, (_i, r) in gd.forms.items() if gd.edid(f).lower() in modelsets.STAND_IN}
was = [o for o in plain if o['base'] in game_key.values()]
left = [o for o in ours if o['base'] in game_key.values()]
new = [o for o in ours if o['base'].startswith('$model_')]
check('a yard had the Mojave\'s palms, banana plants and grass', len(was) > 20, len(was))
check('with the set, each of those is one of ours and none is left', not left and len(new) == rep['by'].get('Swapped') >= len(was) * 0.6, (len(left), len(new), len(was)))
check('life-size: no palm blown up as the game\'s small plants are', all(0.4 <= o['s'] <= 2.3 for o in new) and all(o['s'] <= 1.4 for o in new if 'palm' in o['base']))
made_keys = pm.apply('Things on the ground', first + ours)
placed = [r for c in pm.cells.values() for r in c['refs'].values() if isinstance(r, dict) and str(r.get('base', '')).startswith('+')]
own = {k for k, r in pm.records.items() if recordio.field(r, 'EDID').startswith('FOLabBeach')}
check('in the mod they are things of its own five new records, all in one Undo', len(own) == 5 and len(placed) == len(new) and {r['base'] for r in placed} <= own
      and not any(str(r.get('base', '')).startswith('$') for c in pm.cells.values() for r in c['refs'].values() if isinstance(r, dict)), (len(own), len(placed), len(new)))
pm.undo()
check('and one Undo takes plants and records away again', not any(k.startswith('+') for k in pm.records))

# --- or added to the game's plants, which stay ---
pe = project.Project.create('Beach Extra')
gd.overlay = library.Overlay(lambda: pe)
more, erep = modelsets.extra(gd, pe, world, Cover('sand'), 5)
adds = [o for o in more if o['op'] == 'add']
check('a beach gets the set\'s plants: palms and dune grass most', erep['plants'] == len(adds) > 40 and erep['records'] == 5
      and erep['by'].get('Dune grass', 0) > erep['by'].get('Banana plant', 0) and erep['by'].get('Coconut palm, tall', 0) > 5, erep)
check('all on the map\'s ground, on the land', all(abs(o['p'][0] - x) < 61 * 128 and abs(o['p'][1] - y) < 61 * 128 and o['p'][2] > 0 for o in adds))
check('none on a road', modelsets.extra(gd, pe, world, Cover('asphalt'), 5)[1]['plants'] == 0)
both = plain + more
pe.apply('Things on the ground', both)
refs = [r for c in pe.cells.values() for r in c['refs'].values() if isinstance(r, dict) and r.get('base')]
check('with the game\'s plants beside them, none taken away', sum(1 for r in refs if r['base'] in game_key.values()) == len(was)
      and sum(1 for r in refs if r['base'].startswith('+')) == len(adds), (len(refs), len(was), len(adds)))

# --- a jungle: its pieces, and a wood planted thick with them ---
jungle = [k for k, v in modelsets.PIECES.items() if v['set'] == 'jungle']
bad = []
for piece in jungle:
    m = made[piece] = modelsets.build(piece)
    wrong = nifmake.check(m['nif'], m['shapes'], m['solids'])
    if wrong or not m['mesh'].startswith('meshes\\folab\\jungle\\') or not any(s.get('alpha') for s in m['shapes']) or m['triangles'] > modelmake.MOST_THING:
        bad.append((piece, wrong, m['triangles']))
check('%d jungle pieces build and read back, each with leaves, none over MOST_THING triangles' % len(jungle), len(jungle) >= 15 and not bad, bad)
check('editor IDs all their own', len({v['edid'] for v in modelsets.PIECES.values()}) == len(modelsets.PIECES) and all(v['edid'] for v in modelsets.PIECES.values()))
big = made['jungle_tree']
check('a forest tree: 13 metres up, its crown 15 across, only the trunk in the way', 850 < big['box'][5] < 1300 and big['box'][3] - big['box'][0] > 1000 and len(big['solids']) == 1)
crown = [s for s in big['shapes'] if s.get('alpha')]
flat = sum(1 for s in crown for i in range(0, len(s['n']), 3) if abs(s['n'][i + 2]) > 0.9)
check('its crown has leaves facing down as well as sideways: a roof seen from under', flat > 60, flat)
floor = made['jungle_floor_a']
check('a floor piece is many plants as one thing, nothing solid, eight metres across',
      floor['triangles'] > 2000 and not floor['solids'] and floor['box'][3] - floor['box'][0] > 550 and len(floor['shapes']) <= 6, (floor['triangles'], floor['box']))
pj = project.Project.create('Jungle Map')
gd.overlay = library.Overlay(lambda: pj)
jops, jrep = modelsets.extra(gd, pj, world, Cover('trees'), 5, which='jungle')
jadds = [o for o in jops if o['op'] == 'add']
by = jrep['by']
canopy = by.get('Jungle tree, spreading', 0) + by.get('Banyan', 0) + by.get('Jungle tree, tall', 0)
ground = by.get('Jungle floor', 0) + by.get('Jungle floor, more taro', 0)
cells = 121 * 128 / 4096.0
check('a wood gets a roof: a dozen great trees a cell', 7 * cells ** 2 < canopy < 20 * cells ** 2, (canopy, cells))
check('and a floor: pieces enough to hide most of the ground', ground * 600 * 600 > 0.5 * (121 * 128) ** 2, ground)
check('about a hundred things a cell, not thousands', 60 * cells ** 2 < len(jadds) < 150 * cells ** 2, len(jadds))
check('the beach set is a different planting', {o['base'] for o in jadds}.isdisjoint({o['base'] for o in adds}) and modelsets.extra(gd, pj, world, Cover('sand'), 5, which='jungle')[1]['plants'] == 0)

# --- hotels: towers with a far model each, for the skyline ---
import lodobj  # noqa: E402
hotels = [k for k, v in modelsets.PIECES.items() if v['set'] == 'hotel']
bad = []
for piece in hotels:
    m = made[piece] = modelsets.build(piece)
    far_rel = m['mesh'][:-4] + '_lod.nif'
    wrong = nifmake.check(m['nif'], m['shapes'], m['solids']) + (nifmake.check(m['files'][far_rel], m['far']['shapes'], []) if far_rel in m['files'] else ['no far model'])
    if wrong or m['box'][5] < 2500 or not 4 <= len(m['solids']) <= 40 or m['far']['triangles'] > m['triangles'] or any(max(sh['uv'][a::2]) - math.floor(min(sh['uv'][a::2])) > modelsets.FAR_REPEAT + 0.001 for sh in m['far']['shapes'] for a in (0, 1)):
        bad.append((piece, wrong, m['box'], len(m['solids'])))
check('%d hotels build, each over 35 metres, solid, with a far model of their own pictures, repeated no more than the distant blocks bake (FAR_REPEAT)' % len(hotels), len(hotels) == 4 and not bad, bad)
ph = project.Project.create('Hotel Test')
gd.overlay = library.Overlay(lambda: ph)
hops, hinfo = modelsets.put(ph, 'makai_tower')
hkey = ph.apply('A hotel', hops)[0]
got = lodobj.StandIns(gd, ph).of(hkey)
check('the far-view maker finds a hotel\'s far model beside its mesh', bool(got) and sum(len(sh['i']) // 3 for sh in got) == made['makai_tower']['far']['triangles'])
tower = made['makai_tower']
floors = sorted({round(p[2]) for sld in [tower['shapes']] for sh in sld for p in [sh['p'][k:k + 3] for k in range(0, len(sh['p']), 3)]})
check('sixteen floors of lanai slabs stand out from its face', sum(1 for z in floors if (z - 316) % 256 == 0 and 316 < z <= 316 + 16 * 256) == 16)
half = modelsets.extra(gd, pj, world, Cover('trees'), 5, which='jungle', thick=0.5)[1]['plants']
check('planted half as thick when asked', 0.35 * len(jadds) < half < 0.65 * len(jadds), (half, len(jadds)))

# --- green ground: by the land point, from what the map says each is; nothing where it doesn't belong ---
import espwrite, greenground, groundtex, land, tes4, tempfile  # noqa: E402
pg = project.Project.create('Green Ground')
gd.overlay = library.Overlay(lambda: pg)
painted = lambda k: all(gd.land_at(world, k[0] + dx, k[1] + dy) and land.decode(gd, gd.land_at(world, k[0] + dx, k[1] + dy), {})['q'][0]['bkey']
                        for dx in (0, 1) for dy in (0, 1))
gk = next(k for k in sorted(grid, key=lambda k: abs(k[0]) + abs(k[1])) if painted(k))      # (the map's far edges have heights and no paint)
four = {(gk[0] + dx, gk[1] + dy) for dx in (0, 1) for dy in (0, 1)}


class Mixed:
    """A map over those four cells: scrub to the west, a road up the middle, a town's yard and paving east of it, a park
    in the south-west corner, a beach along the north."""
    def __init__(self):
        self.gx0, self.gy0 = gk[0] * 32 - 8, gk[1] * 32 - 8
        self.A = self.D = 81
        C = osmcover.CODE
        self.kind = bytearray(self.A * self.D)
        for yy in range(self.D):
            for xx in range(self.A):
                kd = C['scrub'] if xx < 36 else C['asphalt'] if xx < 42 else C['yard'] if xx < 60 else C['paved']
                if xx < 20 and yy < 20:
                    kd = C['grass']
                if yy > 70:
                    kd = C['sand']
                self.kind[yy * self.A + xx] = kd


mixed = Mixed()
gops, grep_ = greenground.regreen(gd, pg, world, mixed, only=four)
news = [o for o in gops if o['op'] == 'record_new']
lands = [o for o in gops if o['op'] == 'land']
check('five kinds of ground, a texture set and a landscape texture each, before any land', [o['record']['type'] for o in news] == ['TXST', 'LTEX'] * 5
      and gops[:10] == news and 1 <= len(lands) == grep_['cells'] <= 4, (len(news), len(lands)))     # (a cell that is all town isn't touched)
bk = grep_['by_kind']
check('roads, paving, yards and the beach are not touched: not one point', grep_['changed_where_forbidden'] == 0 and grep_['grass_where_forbidden'] == 0
      and all(bk[n]['changed'] == 0 and bk[n]['grass'] == 0 for n in ('asphalt', 'yard', 'paved', 'sand')), bk)
check('scrub is painted nearly all over, and has grass in its middle, away from the road', bk['scrub']['changed'] > 0.85 * bk['scrub']['points']
      and 0 < bk['scrub']['grass'] < 0.8 * bk['scrub']['points'], bk)
madek = pg.apply('Green ground', gops)
ltex = {k: r for k, r in pg.records.items() if r['type'] == 'LTEX'}
check('each landscape texture names the set made just before it', len(ltex) == 5 and all(
    recordio.field(pg.records[recordio.field(r, 'TNAM')], 'EDID') == recordio.field(r, 'EDID') + 'Set' for r in ltex.values()))
check('only one of them grows grass', sorted(recordio.field(r, 'EDID') for k, r in ltex.items() if groundtex.grows(pg, k)) == ['FOLabGroundJungleGrass'])
# point by point against the world's first paint, not trusting the report
C = osmcover.CODE
grows_ = lambda key: key and (groundtex.grows(pg, key) if key.startswith('+') else 'GNAM' in gd.fields(gd.from_key(key)))
bad_change = bad_grass = edge_full = 0
for kk in four:
    cellk = gd.key(grid[kk])
    was = land.decode(gd, gd.land_at(world, *kk), {})
    now = pg.land.get(cellk) or was             # (a cell with nothing to paint is left out altogether)
    for qn in range(4):
        a_, b_ = was['q'][qn], now['q'][qn]
        wl, nl = {l['key']: l['a'] for l in a_['layers']}, {l['key']: l['a'] for l in b_['layers']}
        for j in range(17):
            for i in range(17):
                gx, gy = kk[0] * 32 + (qn % 2) * 16 + i - mixed.gx0, kk[1] * 32 + (qn // 2) * 16 + j - mixed.gy0
                if not (0 <= gx < mixed.A and 0 <= gy < mixed.D):
                    continue
                kd, n_ = mixed.kind[gy * mixed.A + gx], j * 17 + i
                if kd in (C['asphalt'], C['yard'], C['paved'], C['sand']):
                    if a_.get('bkey') != b_.get('bkey') or any(abs(v[n_] - wl.get(key, [0.0] * 289)[n_]) > 1e-6 for key, v in nl.items()) \
                            or any(v[n_] > 0 and key not in nl for key, v in wl.items()):
                        bad_change += 1
                    if (grows_(b_.get('bkey')) and b_.get('bkey') != a_.get('bkey')) or any(grows_(key) and key not in wl and v[n_] > 0 for key, v in nl.items()):
                        bad_grass += 1
                elif kd == C['scrub'] and gx == 35 and any(v[n_] >= 1.0 for key, v in nl.items() if key.startswith('+')):
                    edge_full += 1
check('checked point by point against the first paint: nothing changed and no grass laid where it may not', bad_change == 0 and bad_grass == 0, (bad_change, bad_grass))
check('green comes up softly beside the road: never at full strength on the point next to it', edge_full == 0, edge_full)
# the game's own rule for grass (grassrule.py), on a quarter made up for it: sixteen samples, each a 3 x 3, spread over a patch
import grassrule  # noqa: E402
gdens = lambda key: {'G': [1.0], 'thin': [0.25]}.get(key, [])
blank = lambda: [0.0] * 289
road = blank()
for j_ in range(17):
    for i_ in range(7, 10):
        road[j_ * 17 + i_] = 1.0                    # a road up the middle, three points wide, at full strength
thin = [0.4 * v for v in road]                      # the same road, faded
g1 = grassrule.predict({'bkey': 'G', 'layers': [{'key': 'R', 'a': road}]}, gdens)
check('a grassy base under a road at full strength: grass both sides, none on the road\'s middle', g1[8 * 17 + 2] > 0 and g1[8 * 17 + 14] > 0 and g1[8 * 17 + 8] == 0, (g1[8 * 17 + 2], g1[8 * 17 + 8]))
g2 = grassrule.predict({'bkey': 'G', 'layers': [{'key': 'R', 'a': thin}]}, gdens)
check('under a faded road the base grows straight through it', g2[8 * 17 + 8] > 0)
lay = blank()
for j_ in range(0, 5):
    for i_ in range(0, 5):
        lay[j_ * 17 + i_] = 0.9                     # a grass-bearing layer on one sample's patch only
g3 = grassrule.predict({'bkey': 'B', 'layers': [{'key': 'G', 'a': lay}]}, gdens)
check('a grass layer held on one patch grows on that patch and not a point beyond it', all(g3[j_ * 17 + i_] > 0 for j_ in range(1, 4) for i_ in range(1, 4))
      and all(g3[j_ * 17 + i_] == 0 for j_ in range(17) for i_ in range(17) if i_ > 4 or j_ > 4))
ramp = blank()
for j_ in range(17):
    for i_ in range(17):
        ramp[j_ * 17 + i_] = max(0.0, min(1.0, (i_ - 4) / 3.0))     # the third try's mistake: rising from a road's edge at column 4
g4 = grassrule.predict({'bkey': 'B', 'layers': [{'key': 'G', 'a': ramp}]}, gdens)
check('a grass layer that rises from the road\'s edge puts grass on the edge: why the third try failed', g4[8 * 17 + 4] > 0)
check('a grass too sparse for the threshold never grows', not any(grassrule.predict({'bkey': 'thin', 'layers': []}, gdens)))
gc = greenground.check(gd, pg, world, mixed)
check('by that rule, on the map made up above: no grass from this step within 256 units of road, yard, paving or beach', gc['ours'] == 0 and gc['near'] > 1000 and gc['after'] <= gc['before']
      and sum(gc['grown'].values()) > 0, gc)
check('whatever the threshold really is', all(greenground.check(gd, pg, world, mixed, t_)['ours'] == 0 for t_ in (0.05, 0.5, 0.85)))
check('their pictures are the mod\'s own files, repeating squares', all(gd.find_file(groundtex.path(n)) == 'your mod' and dds.info(gd.read_file(groundtex.path(n)))['w'] == 512 for n in groundtex.GROUNDS))
again, rep2 = greenground.regreen(gd, pg, world, mixed, only=four)
check('done twice, nothing more changes', again == [] and rep2['cells'] == 0)
out = os.path.join(tempfile.mkdtemp(), 'green.esp')
espwrite.write(gd, pg, out)
pf = tes4.PluginFile(out)
ids, used_ids = {}, set()
for item in pf.walk():
    rec = item[0] if isinstance(item, tuple) else item
    if isinstance(rec, tes4.Record) and rec.tag == 'LTEX':
        ids[rec.formid] = tes4.zstr(dict(pf.fields(rec))['EDID'])
    elif isinstance(rec, tes4.Record) and rec.tag == 'LAND':
        used_ids |= {struct.unpack_from('<I', d)[0] for t, d in tes4.iter_subrecords(pf.data(rec)) if t in ('BTXT', 'ATXT')}
pf.close()
check('written to a plugin: the land names the mod\'s own ground records', len(ids) == 5 and len(used_ids & set(ids)) >= 2, (len(ids), len(used_ids)))
# --- a city to climb: ramps made to a roof's height, walkways, and roofs measured from the game's buildings ---
import citypieces, rooftops, townbuild  # noqa: E402
name, real = citypieces.ramp_tower(790, 60)
m = modelsets.build(name)
check('a way up is made to measure: 790 asked, the next step of 64 made, a drop of 64 behind the parapet', real == 832 and name == 'ramp2_832_64'
      and nifmake.check(m['nif'], m['shapes'], m['solids']) == [] and m['mesh'].startswith('meshes\\folab\\city\\'))
ramps = [sld for sld in m['solids'] if max(p[2] for p in sld['points']) - min(p[2] for p in sld['points']) > 100]
steep = max(math.degrees(math.atan2(max(p[2] for p in sld['points']) - min(p[2] for p in sld['points']) - 8,
                                    max(max(p[0] for p in sld['points']) - min(p[0] for p in sld['points']), max(p[1] for p in sld['points']) - min(p[1] for p in sld['points'])))) for sld in ramps)
check('every ramp is one you can walk: under 32 degrees, and the top is at the height asked', len(ramps) >= 4 and steep < 32 and abs(max(p[2] for sld in m['solids'] for p in sld['points']) - 832) < 6, (len(ramps), steep))
check('its top reaches over the wall, past the tower\'s own face', m['box'][4] > 150 and m['box'][1] < -200)
bname, blong = citypieces.bridge(700)
bm = modelsets.build(bname)
check('a walkway of the length asked, solid to walk on', blong == 704 and nifmake.check(bm['nif'], bm['shapes'], bm['solids']) == [] and bm['box'][3] - bm['box'][0] >= 704 and len(bm['solids']) >= 2)
lname, _lh = citypieces.lookout(768)
lm = modelsets.build(lname)
check('a lookout: ramps up, a hut with walls to lean on', nifmake.check(lm['nif'], lm['shapes'], lm['solids']) == [] and lm['box'][5] > 1000 and len(lm['solids']) >= 8)
cat = townbuild.load(gd, server.kits_folder()) if False else None
office = next((f for f, (_i, r) in gd.forms.items() if r.tag == 'STAT' and gd.edid(f) == 'NVOfficeBldg03'), None)
ranch = next((f for f, (_i, r) in gd.forms.items() if r.tag == 'STAT' and gd.edid(f) == 'WoodShack01'), None)
model_of = lambda f: gd.fields(f)['MODL'][:-1].decode('cp1252')
ob = library.bounds_of(gd.read_file('meshes\\' + model_of(office)))
roof = rooftops.roof_of(gd, model_of(office), ob)
check('an office block has a roof to stand on: its floor, its outline, its parapet', roof and 250 < roof['z'] < ob[5] and roof['rect'][2] - roof['rect'][0] > 1000 and 0 <= roof['parapet'] <= 160, roof)
sb = library.bounds_of(gd.read_file('meshes\\' + model_of(ranch)))
check('a shack with a pitched roof has none', rooftops.roof_of(gd, model_of(ranch), sb) is None)
import navgen  # noqa: E402
tip = navgen._turn(0.0, rooftops.PITCH_SIGN * 0.3, 0.7)
check('a walkway tipped towards a higher roof has that end up, whichever way it lies', tip[2][0] > 0.2)
tname, treal = citypieces.ramp_tower(700, 32, tight=True)
tm = modelsets.build(tname)
check('a tight tower for a short wall: shorter along the wall, still walkable', nifmake.check(tm['nif'], tm['shapes'], tm['solids']) == []
      and tm['box'][3] - tm['box'][0] < m['box'][3] - m['box'][0] - 100 and citypieces.tower_size(True)[0] < citypieces.tower_size(False)[0])
sname, sreach, sup = citypieces.shanty(3, 1)
sm = modelsets.build(sname)
# every piece made to be climbed is walked, over its own collision, from the ground to every floor it has
import walkcheck  # noqa: E402
check('a shanty of three floors has its ramps in front, its floors behind, and is shot from at every storey',
      nifmake.check(sm['nif'], sm['shapes'], sm['solids']) == [] and len({sh['tex'] for sh in sm['shapes']}) >= 3 and sm['box'][3] - sm['box'][0] >= 2 * sreach - 2)
not_walked = []
for desc, levels in ([(citypieces.describe_tower(h, d, tight=t), [h] + ([h - d] if d else [])) for h in (192, 384, 576, 832, 1088, 1344, 1728) for d in (0, 64, 160) for t in (False, True)]
                     + [(citypieces.describe_tower(h, hut=True), [h]) for h in (640, 768, 896)]
                     + [(citypieces.describe_shanty(lv, sd), [256 * k for k in range(1, lv + 1)]) for lv in (2, 3, 4) for sd in (1, 2, 5)]):
    f = walkcheck.Walk(modelmake.make(desc)['solids']).floors(levels, band=4)
    if not all(p_ and r_ > 0.9 * p_ for p_, r_ in f):
        not_walked.append((desc['name'], f))
check('every ramp tower, lookout and shanty is walked from the ground to every floor', not not_walked, not_walked)
blocked = {'name': 'B', 'looks': {'p': {'tex': 'a.dds'}}, 'parts': [{'shape': 'slab', 'size': [900, 300, 8], 'look': 'p'}, {'shape': 'slab', 'size': [300, 300, 8], 'at': [0, 0, 120], 'look': 'p'}]}
check('the walk check finds a floor with no headroom over it, and a floor no way up reaches',
      walkcheck.Walk(modelmake.make(blocked)['solids']).floors([128], band=4)[0][1] == 0)
lm2 = modelsets.build(citypieces.leanto(2))
check('a lean-to: three walls and a roof, open in front', nifmake.check(lm2['nif'], lm2['shapes'], lm2['solids']) == [] and len(lm2['solids']) == 3 and 150 < lm2['box'][5] < 260)
import waikikiset  # noqa: E402
bad = []
for piece in waikikiset.PIECES:
    wm = modelsets.build(piece)
    if nifmake.check(wm['nif'], wm['shapes'], wm['solids']) or wm['triangles'] > modelmake.MOST_THING:
        bad.append((piece, wm['triangles']))
check('every Waikiki piece builds, every block checked, none over MOST_THING triangles', not bad, bad)
walk_bad = []
for piece, deck in (('lifeguard_tower', 210), ('hale', 24), ('hula_stage', 40)):
    f = walkcheck.Walk(modelsets.build(piece)['solids']).floors([deck], band=4)[0]
    if not f[0] or f[1] < 0.9 * f[0]:
        walk_bad.append((piece, f))
check('the lifeguard tower, the hale and the hula stage are walked up from the ground', not walk_bad, walk_bad)
torch = modelsets.build('tiki_torch_lit')
check("a lit piece glows the game's way: white.dds in the glow slot", waikikiset.GLOW.encode() in torch['nif'])
sign = modelsets.build('motel_sign_0')
mesh = nif.mesh_from_nif(sign['nif'])
board = [sh for sh in mesh if 'motels' in sh['tex'].lower()][0]
pylon_front = -25.0
check("a motel sign's board stands wholly in front of its pylons", max(board['p'][1::3]) < pylon_front - 10, max(board['p'][1::3]))
gdw = gamedata.GameData()
lops = waikikiset.lights(gdw, None, 'tiki_gate', 100.0, 200.0, 0.0, 0.0, cell='+000800')
check("a piece's lights come as adds of the game's own lights, where the piece stands", len(lops) == 2 and all(o['op'] == 'add' for o in lops), lops)
import landmarks, waikikiplace  # noqa: E402,E401
sq = lambda x, y, r: [(x - r, y - r), (x + r, y - r), (x + r, y + r), (x - r, y + r)]
check('two footprints that meet overlap, two apart do not, a turned one is caught at its corner',
      waikikiplace._overlap(sq(0, 0, 50), sq(90, 0, 50)) and not waikikiplace._overlap(sq(0, 0, 50), sq(120, 0, 50))
      and waikikiplace._overlap([(100, 0), (171, 71), (100, 142), (29, 71)], sq(0, 71, 50)))
fx, fy = landmarks._turn(0.0, -1.0, waikikiplace.facing(0.6, 0.8))
check('facing turns a piece so its front looks the way asked', abs(fx - 0.6) < 1e-6 and abs(fy - 0.8) < 1e-6, (fx, fy))
lx, ly = landmarks._turn(-1.0, 0.0, waikikiplace.facing(-0.8, 0.6))
check("a street lamp turned to a road's way has its arm out over the road", abs(lx - 0.6) < 1e-6 and abs(ly - 0.8) < 1e-6, (lx, ly))
import coastset  # noqa: E402
bad, built = [], {}
for piece in list(coastset.HOTELS) + list(coastset.PIECES):
    built[piece] = cm = modelsets.build(piece)
    if nifmake.check(cm['nif'], cm['shapes'], cm['solids']) or cm['triangles'] > modelmake.MOST_BUILDING:
        bad.append((piece, cm['triangles'], nifmake.check(cm['nif'], cm['shapes'], cm['solids'])))
check('every coast piece and new hotel builds, every block checked, none over MOST_BUILDING triangles', not bad, bad)
nofar = [p for p in list(coastset.HOTELS) + ['lighthouse', 'signal_mast', 'wreck', 'aquarium', 'groin_pavilion'] if not built[p].get('far')]
check('every hotel and every one-off that reads from far off has a far model', not nofar, nofar)
hb = {p: modelsets.build(p)['box'] for p in ('makai_tower', 'blue_lagoon', 'kahuna_palms', 'pink_pearl')}
check('Moana Kai is the tallest hotel, Kahala Reef the longest and lowest of them',
      built['moana_kai']['box'][5] > max(b[5] for b in hb.values()) and built['kahala_reef']['box'][3] - built['kahala_reef']['box'][0] > max(b[3] - b[0] for b in hb.values())
      and built['kahala_reef']['box'][5] < min(b[5] for b in hb.values()))
walk_bad = []
for piece, deck in (('groin_walk', 0), ('groin_pavilion', 0), ('kahala_reef', 120)):
    f = walkcheck.Walk(built[piece]['solids']).floors([deck], band=4)[0]
    if not f[0] or f[1] < 0.6 * f[0]:
        walk_bad.append((piece, f))
check("the groin's walk, the pavilion's deck and the resort's terrace (up its ramps) are walked", not walk_bad, walk_bad)
wd = walkcheck.Walk(built['wreck']['solids']).floors([coastset.WRECK_HIGH], band=4)[0]
check("the wreck has a deck to stand on (got to from the water, so not walked from the ground)", wd[0] > 3000, wd)
gb = built['groin_walk']['box']
check("a length of groin is GROIN_STEP long, its top at its origin, its sides reaching far under",
      abs(gb[4] - gb[1] - coastset.GROIN_STEP) < 1 and gb[2] <= -coastset.GROIN_DOWN + 1 and gb[5] <= 41, gb)
lt = waikikiset.lights(gdw, None, 'lighthouse', 0.0, 0.0, 0.0, 0.0, cell='+000800')
check('the lighthouse and the mast are lit by the game\'s own lights', len(lt) == 1 and len(waikikiset.lights(gdw, None, 'signal_mast', 0.0, 0.0, 0.0, 0.0, cell='+000800')) == 1)
import coastplace  # noqa: E402
import tempfile  # noqa: E402
_osm = os.path.join(tempfile.mkdtemp(), 'coast.osm')
with open(_osm, 'w', encoding='utf-8') as f_:
    f_.write('<osm><node id="1" lat="21.255" lon="-157.81"><tag k="man_made" v="lighthouse"/><tag k="name" v="Point Light"/></node>'
             '<node id="2" lat="21.27" lon="-157.82"/><node id="3" lat="21.271" lon="-157.823"/>'
             '<node id="4" lat="21.28" lon="-157.80"><tag k="tourism" v="hotel"/><tag k="name" v="The Kahala"/></node>'
             '<node id="5" lat="21.26" lon="-157.83"><tag k="natural" v="reef"/></node>'
             '<way id="9"><nd ref="2"/><nd ref="3"/><tag k="man_made" v="groyne"/><tag k="name" v="Kapahulu Groin"/></way></osm>')
om = coastplace.osm_marks(_osm)
check('the coast reads its marks from a map: a lighthouse, a named hotel, a reef, a groyne as a line',
      len(om['lighthouse']) == 1 and om['hotel'][0][2] == 'The Kahala' and len(om['reef']) == 1 and len(om['groyne']) == 1 and len(om['groyne'][0][0]) == 2
      and not om['aquarium'], om)
check('and still nothing written into the game', in_game() == game_before)
