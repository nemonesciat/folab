"""Island skill books (skillbooks.py) in a small mod of its own: a stand-in Radar Dome cargo pod (a container of the mod's
own) and the game's toolbox placed in a room standing in for the freighter's hold; one Undo makes the two books (the
game's skill books copied, their skills kept), adds the Science book to the pod and swaps the toolbox for a copy of its own
holding the Speech book. Written and read back."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import browse  # noqa: E402
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import health  # noqa: E402
import project  # noqa: E402
import recordio  # noqa: E402
import server  # noqa: E402
import skillbooks as SB  # noqa: E402
import tes4  # noqa: E402
from activity import _new_key  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Books Test')
key = lambda e, tag: G.key(next(f for f, (i, r) in G.forms.items() if r.tag == tag and G.edid(f) == e))
pod = recordio.load(G, G.from_key(key('Footlocker01Military', 'CONT')))
pod['src'] = ''
recordio.set_field(pod, 'EDID', 'FOLabVertibirdCargo', label='Editor ID')
pk, room, box = _new_key(pr), key('CrimsonCaravanBarracks01', 'CELL'), key('ToolboxContainer', 'CONT')
rk = _new_key(pr)
pr.apply('stand-ins', [{'op': 'record', 'key': pk, 'record': pod},
                       {'op': 'place', 'cell': room, 'key': rk, 'ref': {'base': box, 'p': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 's': 1.0}}])
rows, skipped = SB.plan(G, pr)
check('the pod found; the hold not in this mod', [r['skill'] for r in rows] == ['science'] and skipped and skipped[0][0] == 'speech', skipped)
rows.append({'skill': 'speech', 'how': 'swap', 'cell': room, 'ref': rk, 'from': box, 'where': 'FOLabFreighterHold'})
undo0 = len(pr.undo_stack)
ops, rep = SB.ops(G, pr, (rows, []))
pr.apply(SB.LABEL, ops)
check('one Undo, two books and the hold\'s toolbox', len(pr.undo_stack) == undo0 + 1 and len(rep['made']) == 3, rep['made'])
check('the toolbox swapped for the copy', pr.cells[room]['refs'][rk]['base'] != box)
check('made again, it refuses', bool(SB.plan(G, pr)[1]) and not SB.plan(G, pr)[0])
os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'Books Test.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
mine = {tes4.zstr(g.fields(f).get('EDID', b'')): f for f, (n, r) in g.forms.items() if n == i}
sub = lambda e: list(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine[e]][1])))
for skill, (_src, edid, title, _w) in SB.BOOKS.items():
    d = dict(sub(edid))
    check('%s: its title and the game\'s skill kept' % edid, d['FULL'] == title.encode() + b'\x00'
          and struct.unpack('<b', d['DATA'][1:2])[0] == {'speech': 11, 'science': 8}[skill])
held = lambda e: [struct.unpack('<I', v[:4])[0] & 0xFFFFFF for t, v in sub(e) if t == 'CNTO']
check('the pod holds the Science book', mine['FOLabBookObservatory'] & 0xFFFFFF in held('FOLabVertibirdCargo'))
check('the hold\'s toolbox holds the Speech book', mine['FOLabBookTalkStory'] & 0xFFFFFF in held(SB.HOLD_BOX))
h = health.check_file(g, out)
bad = [(x['kind'], x['count']) for x in h['groups'] if x['sev'] == 'error']
check('the plugin passes health', not bad, bad)
