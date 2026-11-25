"""The Kilauea's arcade (arcadeset.py): every piece builds, every block checked, closed (modelmake and as built), within
a thing's triangles; the banks stand in the Tops' slot bank's frame (front -y, the counter's height, nothing past y +43.5
where the bank behind begins); singles fit their slot; only the pachinko glass is see-through and it is blended; the
lit looks glow; the casino's DATA reads both ways over every game casino; the slot menu's model is the game's with only
its pictures re-pointed; the activator's script compiles."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata  # noqa: E402
import arcadeset as A  # noqa: E402
import modelmake  # noqa: E402
import modelsets  # noqa: E402
import nif  # noqa: E402
import nifmake  # noqa: E402
import nifwrite  # noqa: E402
import schema  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


gd = gamedata.GameData()
for k in A.PIECES:
    desc = modelsets.PIECES[k]['describe']()
    check('%s is closed as described' % k, not modelmake.open_edges(desc), modelmake.open_edges(desc)[:2])
    m = modelsets.build(k)
    wrong = nifmake.check(m['nif'], m['shapes'], m['solids'])
    check('%s builds, every block checked' % k, not wrong, wrong[:2])
    shapes = nif.mesh_from_nif(m['nif'])
    check('%s is closed as built' % k, nifmake.open_edges(shapes) < 0.5, nifmake.open_edges(shapes))
    check('%s within a thing\'s triangles' % k, m['triangles'] <= 7000, m['triangles'])
    see = [s for s in shapes if s.get('alpha')]
    check('%s: only glass is see-through, blended' % k, all(s['alpha'] == 'blend' and 'glass' in s['tex'] for s in see), [s['tex'] for s in see])
    check('%s glows somewhere' % k, any(s.get('glow') for s in shapes))
    b = m['box']
    if 'bank' in k:
        check('%s keeps to the bank\'s frame' % k, b[1] >= -32 and b[4] <= A.SPINE + 1 and b[2] >= 0 and -89 <= b[0] and b[3] <= 89, b)
    else:
        check('%s fits a slot' % k, b[3] - b[0] <= 41 and b[2] >= 0, b)
    check('%s draws in at most %d shapes' % (k, 8), len(shapes) <= 8, len(shapes))

check('the pachinko bank\'s counter is the Tops\' height', abs(A.COUNTER_H - 49.3) < 0.01)
n, per = schema.checkall(gd, ['CSNO'])
check('every game casino\'s DATA reads and writes back', per['CSNO']['DATA'][1] == 0 and per['CSNO']['DATA'][0] == n['CSNO'], dict(per['CSNO']))

files = A.menu_files(gd)
model = files[A.MENU_MODEL]
game = gd.read_file(A.GAME_MENU_MODEL)
before = nifwrite.textures_in(game)
after = nifwrite.textures_in(model)
diff = [(a['path'], b['path']) for a, b in zip(before, after) if a['path'] != b['path']]
check('the slot menu model is the game\'s with only pictures re-pointed', len(before) == len(after) and diff and
      all(b.lower().startswith('textures\\folab\\arcade\\menu\\') for _a, b in diff) and
      all(a['label'] == 'Picture' for a, b in zip(before, after) if a['path'] != b['path']), diff)
check('every picture the menu names is made', all(b.lower() in {k.lower() for k in files} for _a, b in diff))
check('seven reel symbols', all((A.MENU + 'symbol%d.dds' % k) in files for k in range(1, 8)))

import api_scripts  # noqa: E402
import questrec as qr  # noqa: E402
import project  # noqa: E402


class _Pr:                                  # (just enough of a mod for the casino record: no records of its own)
    records = {}


quest = qr.quest_record({'edid': A.QUEST_EDID, 'name': '', 'flags': {}, 'priority': 0, 'stages': [], 'objectives': []})
cas, money = A.casino(gd, _Pr(), '+000801')
check('the casino takes caps until the island\'s money is in the mod', money == 'Caps001')
check('the casino names FOLab\'s symbols and menu model', [s['value'] for s in cas['subs'] if s['tag'] == 'MOD2'] == [A.MENU_MODEL[7:]] and
      sorted(s['value'] for s in cas['subs'] if s['tag'] == 'ICON') == sorted(A.symbol_paths()))
