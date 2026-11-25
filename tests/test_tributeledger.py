"""The court's tribute ledger (tributeledger.py) in a small mod of its own, from a plan in a game room standing in for the
Royal Hawaiian's stores: the ledger's quest, the terminal (average) whose quota page sets FOLabTributeLedger.read, its
pages saying what's decided (the Holdouts' taxes due) and not which valley stops paying. Written and read back."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import browse  # noqa: E402
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import health  # noqa: E402
import project  # noqa: E402
import robots  # noqa: E402
import server  # noqa: E402
import tes4  # noqa: E402
import tributeledger as TL  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Ledger Test')
room = G.key(next(f for f, (i, r) in G.forms.items() if r.tag == 'CELL' and G.edid(f) == 'CrimsonCaravanBarracks01'))
spot = robots.inside_spots(G, pr, room, ('butler',))[0][0][1]
undo0 = len(pr.undo_stack)
o, rep = TL.ops(G, pr, ([{'what': 'ledger', 'cell': room, 'place': 'x', 'spot': spot, 'near': {}}], []))
pr.apply(TL.LABEL, o)
check('one Undo, one terminal at Science 50', len(pr.undo_stack) == undo0 + 1 and rep['terminals'][0]['science'] == 50)
check('the text: the Holdouts owe, no valley named as stopping', 'TAXES DUE' in TL.TEXT and 'stopped paying' not in TL.TEXT.lower())
os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'Ledger Test.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
mine = {tes4.zstr(g.fields(f).get('EDID', b'')): f for f, (n, r) in g.forms.items() if n == i}
sd = list(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine['FOLabTributeLedgerTerminal']][1])))
check('the quota page sets the ledger read', [v for k, v in sd if k == 'SCTX'] == [b'set FOLabTributeLedger.read to 1']
      and struct.unpack('<I', next(v for k, v in sd if k == 'SCRO'))[0] == g.forms[mine[TL.QUEST]][1].formid)
check('three pages', sum(1 for k, _ in sd if k == 'ITXT') == 3)
s = health.check_file(g, out)['summary']
check('the plugin passes health with no errors', s.get('error', 0) == 0, s)
