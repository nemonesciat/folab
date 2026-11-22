"""FOLab's straw hats (hats.py): each worn model is laid out as the game's gambler fedora (skinned wholly to
Bip01 Head, in the body's space; rigid on that quarter-turned bone the boater lay on its side) and reads back as built; each dropped one has a box on the clutter layer; the game's head fits inside both
crowns; the ops make two ARMO of the mod's own after the Rattan Cowboy Hat and put them in the surfers' head list in its
place, which the written plugin shows."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import hats  # noqa: E402
import hkshape  # noqa: E402
import library  # noqa: E402
import nif  # noqa: E402
import nifmake  # noqa: E402
import peopledress  # noqa: E402
import project  # noqa: E402
import tes4  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


gd = gamedata.GameData()
head = hats.head_points(gd)
check('the game\'s head measured from its bone: its top 15 over it', 14.5 < max(p[2] for p in head) < 15.5, max(p[2] for p in head))
for name in hats.HATS:
    m = hats.build(name)
    body = [dict(sh, p=[v + nifmake.HEAD_AT[k % 3] for k, v in enumerate(sh['p'])]) for sh in m['shapes']]
    check('%s: the worn model reads back as built, in the body\'s space at the head' % name, nifmake.check(m['worn'], body) == [])
    n = nif.Nif(m['worn'])
    root = n.block(0)
    extras = [(n.string(struct.unpack_from('<i', m['worn'], n.offsets[e])[0]), n.string(struct.unpack_from('<i', m['worn'], n.offsets[e] + 4)[0])) for e in root['extra']]
    check('%s: worn as the game\'s gambler fedora is (a NiNode, no Prn, no collision, a Bip01 Head node of its own)' % name,
          n.types[0] == 'NiNode' and extras == [] and root['collision'] == -1 and 'bhkRigidBody' not in n.types
          and any(t == 'NiNode' and n.block(i)['name'] == 'Bip01 Head' for i, t in enumerate(n.types)), (n.types[0], extras))
    shapes_ = [i for i, t in enumerate(n.types) if t == 'NiTriStrips']
    skins = [n.block(i)['skin'] for i in shapes_]
    fed = gd.read_file('meshes\\armor\\headgear\\gambler\\gambler_fedora_01.nif')
    fn = nif.Nif(fed)
    fbone = struct.unpack_from('<12f', fed, fn.offsets[fn.types.index('NiSkinData')] + 57)
    same = True
    for sk in skins:
        o = n.offsets[sk]
        sd, part, rt, nb = struct.unpack_from('<iiiI', m['worn'], o)
        bone = struct.unpack_from('<i', m['worn'], o + 16)[0]
        mine = struct.unpack_from('<12f', m['worn'], n.offsets[sd] + 57)
        same &= nb == 1 and n.block(bone)['name'] == 'Bip01 Head' and all(abs(a - b) < 0.01 for a, b in zip(mine, fbone))
    check('%s: every shape skinned wholly to Bip01 Head with the fedora\'s bind (never rigid on the quarter-turned bone)' % name,
          skins and all(k >= 0 for k in skins) and same)
    import outfitjoin
    check('%s: every triangle drawn from its partition' % name, all(k > 0 for _nm, k in outfitjoin.drawn(m['worn'])))
    check('%s: nothing empty for the game to draw' % name, outfitjoin.empty_parts(m['worn']) == [])
    got = hkshape.collision_shapes(m['go'])
    check('%s: the dropped model reads back, a box on the clutter layer' % name,
          nifmake.check(m['go'], m['go_shapes'])[1:] == [] and len(got) == 1 and got[0]['layer'] == 4, [g['layer'] for g in got])
    lo = min(m['go_shapes'][0]['p'][2::3])
    check('%s: dropped, it rests on its brim at the origin' % name, abs(lo) < 0.01, lo)
    room = hats.clearance(name, head)
    check('%s: the game\'s head inside the crown' % name, room > 0.05, round(room, 2))
    P = [p for s in m['shapes'] for p in zip(s['p'][0::3], s['p'][1::3], s['p'][2::3])]
    check('%s: worn above the ears (nothing under z 4) and as wide as a hat (11-15 to a side)' % name,
          min(p[2] for p in P) > 4 and 11 < max(p[0] for p in P) < 15, (round(min(p[2] for p in P), 1), round(max(p[0] for p in P), 1)))
    for path, data in m['files'].items():
        if path.endswith('.dds'):
            check('%s: %s is a texture' % (name, path.split('\\')[-1]), data[:4] == b'DDS ')

# ---- into a small mod with a surfers' head list holding the Rattan Cowboy Hat ----
pr = project.Project.create('Hats Test')
cowboy = gd.key(hats._game(gd, hats.GAME_HAT, 'ARMO'))
shades = gd.key(hats._game(gd, 'GlassesShades', 'ARMO'))
pr.apply('list', [{'op': 'record_new', 'record': peopledress._lvli(gd, 'FOLabSurferHeadList', 45, [(cowboy, 1)])},
                  {'op': 'record_new', 'record': peopledress._lvli(gd, 'FOLabSurferEyesList', 35, [(shades, 1)])}])
first = pr.next_id
ops, rep = hats.ops(gd, pr)
made = pr.apply('hats', ops)
check('the hats got the keys they were planned with', made[:2] == ['+%06X' % first, '+%06X' % (first + 1)], made)
try:
    hats.ops(gd, pr)
    check('making the hats again is refused', False)
except ValueError:
    check('making the hats again is refused', True)
path = pr.plugin_path()
espwrite.write(gd, pr, path)
gd2 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [path])
me = len(gd2.plugins) - 1
raw = lambda fid: list(tes4.iter_subrecords(gd2.plugins[gd2.forms[fid][0]].data(gd2.forms[fid][1])))
root = library.assets_dir(pr)
armo = {gd2.edid(f): dict(raw(f)) for f, e in gd2.forms.items() if e[1].tag == 'ARMO' and (f >> 24) == me}
check('two hats of the mod\'s own', sorted(armo) == ['FOLabBoater', 'FOLabLauhala'], sorted(armo))
game = dict(raw(gd.from_key(cowboy)))
for e, d in armo.items():
    models = [tes4.zstr(d[t]) for t in ('MODL', 'MOD2')]
    check('%s: its models among the mod\'s files, worn where the Rattan Cowboy Hat is' % e,
          all(os.path.exists(os.path.join(root, 'meshes', m)) for m in models) and d['BMDT'] == game['BMDT'] and d['DATA'] == game['DATA']
          and not any(t in d for t in ('MODT', 'MO2T', 'MODD')), models)
    check('%s: named for what it is' % e, tes4.zstr(d['FULL']) in hats.HATS.values(), tes4.zstr(d['FULL']))
lst = next(f for f, e in gd2.forms.items() if e[1].tag == 'LVLI' and gd2.edid(f) == 'FOLabSurferHeadList')
items = [gd2.edid(gd2.to_global(me, struct.unpack_from('<I', x, 4)[0])) for t, x in raw(lst) if t == 'LVLO']
check('the surfers\' head list holds the two hats, not the Rattan Cowboy Hat', sorted(items) == ['FOLabBoater', 'FOLabLauhala'], items)
check('its chance of no hat kept', dict(raw(lst))['LVLD'][0] == 45)
