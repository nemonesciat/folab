"""Pirates out of Waikiki's lands (pirateclear.py) in a small mod of its own, from a given plan (the plan reads Waikiki's
concept map): a pirate removed, a gore prop removed, a parley group (a named leader and crew) moved into another cell
under the same keys, its names and extras kept; one Undo; written and read back. Also that refs something names are
found (`_named_keys`)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import browse  # noqa: E402
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import pirateclear as PC  # noqa: E402
import project  # noqa: E402
import server  # noqa: E402
import tes4  # noqa: E402
from activity import _new_key  # noqa: E402
from kuliouquest import _person  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Clear Test')
world = next(w for c, w in G.ext_cells.items() if G.edid(w) == 'WastelandNV')
grid = G.grid(world)
a, b = G.key(grid[(-18, 0)]), G.key(grid[(-17, 0)])
key = lambda e, tag: G.key(next(f for f, (i, r) in G.forms.items() if r.tag == tag and G.edid(f) == e))
pk, lk = _new_key(pr), _new_key(pr)
gore = key('RaiderCorpseDressingChain', 'STAT')
x0, y0 = -18 * 4096.0 + 1000, 1000.0
refs = {n: _new_key(pr) for n in ('pirate', 'gore', 'leader', 'crew')}
pr.apply('stand-ins', [{'op': 'record', 'key': pk, 'record': _person(G, pr, 'FOLabPirateLvlWastelander', 'FOLabPirateLvlWastelander', 'NVProspectorMale')},
                       {'op': 'record', 'key': lk, 'record': _person(G, pr, 'FOLabParleyLeader05', 'FOLabParleyLeader05', 'NVProspectorMale')},
                       {'op': 'place', 'cell': a, 'key': refs['pirate'], 'ref': {'base': pk, 'p': [x0, y0, 9000.0, 0, 0, 0], 's': 1.0}},
                       {'op': 'place', 'cell': a, 'key': refs['gore'], 'ref': {'base': gore, 'p': [x0 + 200, y0, 9000.0, 0, 0, 0], 's': 1.0}},
                       {'op': 'place', 'cell': a, 'key': refs['leader'], 'ref': {'base': lk, 'p': [x0, y0 + 2000, 9000.0, 0, 0, 0], 's': 1.0}},
                       {'op': 'place', 'cell': a, 'key': refs['crew'], 'ref': {'base': pk, 'p': [x0 + 100, y0 + 2000, 9000.0, 0, 0, 0], 's': 1.0,
                                                                               'edid': 'FOLabParleyCrew051REF', 'persistent': True}}])
named = PC._named_keys(pr)
check('a ref nothing names isn\'t named', refs['pirate'] not in named)
x1 = -17 * 4096.0 + 1500
rows = [{'what': 'remove', 'cell': a, 'ref': refs['pirate'], 'edid': 'FOLabPirateLvlWastelander', 'holder': 'court', 'p': [x0, y0, 9000]},
        {'what': 'prop', 'cell': a, 'ref': refs['gore'], 'edid': 'RaiderCorpseDressingChain'},
        {'what': 'move', 'refs': [(a, refs['leader']), (a, refs['crew'])], 'edid': 'FOLabParleyLeader05', 'from': [x0, y0 + 2000, 9000],
         'to': [(x1, 1500.0, 9000.0, 1.0), (x1 + 150, 1500.0, 9000.0, 1.0)], 'near': {}}]
undo0 = len(pr.undo_stack)
ops, rep = PC.ops(G, pr, (rows, []))
pr.apply(PC.LABEL, ops)
check('one Undo', len(pr.undo_stack) == undo0 + 1)
check('the pirate and the gore gone', refs['pirate'] not in (pr.cells.get(a) or {}).get('refs', {}) and refs['gore'] not in (pr.cells.get(a) or {}).get('refs', {}))
moved = (pr.cells.get(b) or {}).get('refs', {})
check('the group moved to the next cell under the same keys', refs['leader'] in moved and refs['crew'] in moved
      and refs['leader'] not in (pr.cells.get(a) or {}).get('refs', {}))
check('the crew keeps its name and persistence', moved[refs['crew']].get('edid') == 'FOLabParleyCrew051REF' and moved[refs['crew']].get('persistent'))
check('report', rep['removed'] == 1 and rep['props'] == {'RaiderCorpseDressingChain': 1} and len(rep['moved']) == 1, rep)
pr.undo()
check('Undo puts them back', refs['pirate'] in (pr.cells.get(a) or {}).get('refs', {}) and refs['leader'] in (pr.cells.get(a) or {}).get('refs', {})
      and refs['leader'] not in (pr.cells.get(b) or {}).get('refs', {}))
pr.redo()
os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'Clear Test.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
crew = [r for c, rr in g.cell_refs.items() for f, (n, r) in rr.items() if n == i
        and tes4.zstr(dict(tes4.iter_subrecords(g.plugins[n].data(r))).get('EDID', b'')) == 'FOLabParleyCrew051REF']
check('written: the crew in the plugin once, persistent', len(crew) == 1 and crew[0].flags & 0x400)
