"""The island set (islandset.py): every piece builds and checks, stands in the game piece's footprint, draws in no more
shapes than that piece (one sheet a piece, a second only for what glows), is never see-through, and the shelter has a solid
far model; each find builds as a loose thing and its record is the game's like item with its own name and model."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata  # noqa: E402
import islandset as I  # noqa: E402
import modelsets  # noqa: E402
import nif  # noqa: E402
import nifmake  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


modelsets._all_sets()
gd = gamedata.GameData()
game = {}
for f, (_i, rec) in gd.forms.items():
    e = gd.edid(f)
    if e in I.REPLACES and rec.tag in ('STAT', 'MSTT', 'SCOL') and e not in game:
        fl = gd.fields(f)
        model = fl['MODL'].rstrip(b'\0').decode('latin-1')
        sh = nif.mesh_from_nif(gd.read_file(gamedata.GameData.model_path(rec.tag, model)))
        pts = [s['p'][k:k + 3] for s in sh for k in range(0, len(s['p']), 3)]
        game[e] = {'shapes': len(sh), 'box': [min(p[i] for p in pts) for i in range(3)] + [max(p[i] for p in pts) for i in range(3)]}
check('every game piece the set stands in for is in the game', set(game) == set(I.REPLACES), set(I.REPLACES) - set(game))

FLAT = ('sleeping_mat', 'palm_litter')          # (lying flat on the ground: nothing to bump into)
SEE_THROUGH = ('net_line',)                     # (a net has holes)
made = {}
for k in I.PIECES:
    m = made[k] = modelsets.build(k)
    wrong = nifmake.check(m['nif'], m['shapes'], m['solids'])
    shapes = nif.mesh_from_nif(m['nif'])
    check('%s builds, every block checked' % k, not wrong, wrong[:2])
    check('%s is see-through nowhere' % k, k in SEE_THROUGH or not [s for s in shapes if s.get('alpha')])
    check('%s has something solid' % k, k in FLAT or len(m['solids']) > 0)
    check('%s\'s own pictures go with it' % k, all(t in m['files'] for t in m['textures']))
    for e, p in I.REPLACES.items():
        if p != k:
            continue
        g = game[e]
        lift = I.LIFT.get(e, 0.0)
        b = m['box']
        # (the footprint within a fifth of the game's each way and 40 units; the clothesline's poles are lower than Bitter Springs')
        near = all(abs(b[i] - g['box'][i]) <= max(40.0, 0.2 * (g['box'][i % 3 + 3] - g['box'][i % 3])) for i in (0, 1, 3, 4))
        foot = abs((b[2] + lift) - g['box'][2]) <= 30 if k != 'clothesline' else b[2] <= 5
        check('%s stands in %s\'s footprint' % (k, e), near and foot, (b, g['box'], lift))
        check('%s draws in no more shapes than %s' % (k, e), len(shapes) <= max(g['shapes'], 2), (len(shapes), g['shapes']))
far = made['tarp_shelter'].get('far')
check('the shelter has a far model, much lighter, solid', bool(far) and far['triangles'] < made['tarp_shelter']['triangles'] / 3
      and not [s for s in nif.mesh_from_nif(far['nif']) if s.get('alpha')], far and far['triangles'])

for k, (name, _fn, base, value, weight, _m, _mat) in I.ITEMS.items():
    m = I.build_item(k)
    rec = I.item_record(gd, k, m)
    subs = {s['tag']: s for s in rec['subs']}
    check('%s builds as a loose thing with its pictures' % k, m['nif'][:20].startswith(b'Gamebryo') and all(t in m['files'] for t in m['textures']))
    check('%s\'s record is %s\'s, named and modelled its own' % (k, base), subs['FULL']['value'] == name and subs['MODL']['value'] == m['mesh'][7:]
          and subs['EDID']['value'].startswith('FOLabItem') and 'MODT' not in subs, [subs['EDID']['value'], subs['MODL']['value']])
    v = [q['value'] for q in (subs.get('ENIT') or subs['DATA'])['fields'] if q.get('name') == 'Value']
    check('%s is worth %d' % (k, value), v == [value], v)
