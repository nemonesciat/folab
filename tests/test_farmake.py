"""Far versions for what had none (the user, 24 Nov 2026: "all missing things need far off versions so there arent gaps in
the exploration experience"): a game model's far version made from its own mesh is closed, small and coloured from its
own pictures on the shared palette; FOLab's big pieces with nothing marked far get one of their own parts, closed;
heaps and lava rocks one from the mesh; lodobj finds a game model's far version where FOLab keeps it; what is thin,
flat or a plant is not wanted."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import dds  # noqa: E402
import farmake  # noqa: E402
import gamedata  # noqa: E402
import lodobj  # noqa: E402
import modelsets  # noqa: E402
import nif  # noqa: E402
import nifmake  # noqa: E402

bad = 0


def check(what, ok, detail=''):
    global bad
    bad += not ok
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


# --- the palette ---
files = farmake.palette_files()
w, h, px = dds.decode(files[farmake.PALETTE], 256)[:3]
check('the palette is one 256 square picture', (w, h) == (256, 256), (w, h))
for rgb in ((160, 80, 64), (90, 90, 92), (70, 86, 110), (180, 170, 120), (86, 100, 60), (54, 51, 50)):    # (what the
    # far versions are made of: brick, grey, slate, sand, olive, basalt. The palette has no strong colours: those models
    # keep their own pictures, modelsets.auto_far)
    u, v = farmake.swatch_uv(rgb)
    o = (int(v * 256) * 256 + int(u * 256)) * 4
    got = tuple(px[o:o + 3])
    check('a colour lands on a swatch near it: %s' % (rgb,), sum(abs(a - b) for a, b in zip(got, rgb)) < 90, got)

# --- game models from their own meshes ---
gd = gamedata.GameData()


def read(path):
    low = path.lower()
    if low in files:
        return files[low]
    try:
        return gd.read_file(low if low.startswith(('textures\\', 'meshes\\')) else 'textures\\' + low)
    except Exception:
        return None


for model in ('vehicles\\truckarmy02static.nif', 'architecture\\wasteland\\woodshack01.nif', 'clutter\\slavepens\\nvslavepit01.nif'):
    shapes = nif.mesh_from_nif(gd.read_file('meshes\\' + model))
    own = sum(len(q['i']) // 3 for q in shapes)
    hi = max(max(q['p'][2::3]) for q in shapes)
    got = farmake.make('T', shapes, read, farmake.budget_for(own, hi))
    check('%s: a far version, closed, a tenth of its triangles or less' % model,
          got and got['open'] == 0 and got['triangles'] <= max(20, own // 10) + 4, got and (got['triangles'], own, got['open']))
    box = lambda S: [f(f(q['p'][a::3]) for q in S if q['p']) for f in (min, max) for a in range(3)]
    b0, b1 = box([q for q in shapes if q.get('alpha') != 'blend']), box(got['shapes'])
    check('%s: as big as the model over the ground' % model, all(abs(b1[k] - b0[k]) < 0.2 * (b0[k + 3] - b0[k]) + 8 for k in (0, 1)) and
          abs(b1[5] - b0[5]) < 0.15 * (b0[5] - b0[2]) + 8, (b0, b1))
    tex = {q['tex'] for q in got['shapes']}
    check('%s: drawn on the palette only' % model, tex == {farmake.PALETTE}, tex)
# (26 Nov 2026: Boat01's radio mast drew its far version up to a point, a tan pyramid by the Flotilla)
boat = nif.mesh_from_nif(gd.read_file('meshes\\vehicles\\boat01a.nif'))
bf = farmake.make('T', boat, read, farmake.budget_for(sum(len(q['i']) // 3 for q in boat), 671))
top = max(max(q['p'][2::3]) for q in bf['shapes'])
check('a boat\'s far version leaves its mast out: no higher than its cabin (356)', bf['open'] == 0 and top < 380, top)
check('a mast is slight; a hull is not', len(farmake.unslight(farmake.triangles(boat, farmake.Pictures(read)))) <
      len(farmake.triangles(boat, farmake.Pictures(read))))
pen = farmake.make('T', nif.mesh_from_nif(gd.read_file('meshes\\clutter\\slavepens\\nvslavepit01.nif')), read, 120)
check('a pen is solids round its walls, not one block over its yard', len(farmake.solids(farmake.triangles(
    nif.mesh_from_nif(gd.read_file('meshes\\clutter\\slavepens\\nvslavepit01.nif')), farmake.Pictures(read)), 120)) > 1)

# --- what is wanted ---
check('a truck is wanted', farmake.wanted('truckarmy02Static', 'vehicles\\truckarmy02static.nif', (692, 245, 284), 1.0))
check('a car hulk is not (the game shows none far off)', not farmake.wanted('Car03HulkBodyStatic', 'vehicles\\x.nif', (552, 208, 107), 1.0))
check('a rubble pile is (wide)', farmake.wanted('RubblePile02', 'architecture\\urban\\rubblepiles\\rubblepile02.nif', (732, 889, 158), 1.0))
check('a clothesline is not (thin)', not farmake.wanted('VBitterSpringsClotheslineShort', 'scol\\x.nif', (750, 50, 430), 1.0))
check('a scaffold is not (a solid would misdraw it)', not farmake.wanted('ScaffoldDestroyed01', 'architecture\\urban\\scaffoldingkit\\scaffolddestroyed01.nif', (298, 377, 1053), 1.0))
check('a small rock scaled up is', farmake.wanted('FOLabIslandLavaRockA', 'folab\\island\\lava_rock_a.nif', (140, 140, 112), 3.0))
check('kept apart from the game\'s own paths', farmake.far_path('Vehicles\\Boat01A.nif') == 'meshes\\folab\\far\\vehicles\\boat01a_lod.nif')

# --- FOLab's own pieces ---
modelsets._all_sets()
farmake.city_piece('folab\\city\\ramp2_704_32.nif')
for piece in ('motel_sign_0', 'lifeguard_tower', 'ramp2_704_32', 'heap_a', 'lava_rock_b'):
    made = modelsets.build(piece)
    far = made.get('far')
    gap = far and nifmake.open_edges(nif.mesh_from_nif(far['nif']))
    check('%s: a far version beside it, closed, under a sixth of its triangles' % piece,
          far and gap == 0 and far['triangles'] * 6 <= made['triangles'] + 60 and (made['mesh'][:-4] + '_lod.nif') in made['files'],
          far and (far['triangles'], made['triangles'], gap))
made = modelsets.build('clothesline')
check('a clothesline gets none (thin)', not made.get('far'))
check('a heap\'s far version names the palette and the palette goes with it', farmake.PALETTE in modelsets.build('heap_b')['files'])

# --- lodobj finds a game model's far version where FOLab keeps it ---


class G:
    def __init__(self, have):
        self.have = have

    def read_file(self, path):
        return self.have.get(path.lower())


truck = farmake.make('T', nif.mesh_from_nif(gd.read_file('meshes\\vehicles\\truckarmy02static.nif')), read, 46)
st = lodobj.StandIns(G({farmake.far_path('vehicles\\truckarmy02static.nif'): truck['nif']}))
check('lodobj reads a game model\'s far version from FOLab\'s folder', bool(st.of_model('vehicles\\truckarmy02static.nif')))
check('and names where it is', st.path_of('Vehicles\\TruckArmy02Static.nif') == farmake.far_path('vehicles\\truckarmy02static.nif'))
check('a model with neither has none', st.of_model('vehicles\\nothing.nif') is None and st.path_of('vehicles\\nothing.nif') is None)

print('%d failed' % bad if bad else 'all passed')
sys.exit(1 if bad else 0)
