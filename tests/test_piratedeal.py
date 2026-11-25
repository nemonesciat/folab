"""Pirates who deal, the toll post and the reputations (piratedeal.py) in a small mod of its own, from a given plan: three
REPU records, the traders' faction allied to the Fiends, a pirate swapped to a dealing copy (its own faction, not its
template's, helping nobody), a trader with a buried merchant chest, the toll's fighter; lines with the Speech skill whose
result scripts open barter, add fame and take the toll. Written and read back. Nothing near the real game."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import browse  # noqa: E402
import espwrite  # noqa: E402
import factionfolk as ff  # noqa: E402
import gamedata  # noqa: E402
import health  # noqa: E402
import piratedeal as PD  # noqa: E402
import project  # noqa: E402
import recordio  # noqa: E402
import server  # noqa: E402
import tes4  # noqa: E402
from kuliouquest import _person  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Pirate Test')
world = next(w for c, w in G.ext_cells.items() if G.edid(w) == 'WastelandNV')
grid = G.grid(world)
cell = lambda x, y: G.key(grid[(int(x // 4096), int(y // 4096))])
x0, y0 = -18 * 4096.0 + 2000, 2000.0
dock = _person(G, pr, PD.TRADER_FROM, 'Pirate', 'NVProspectorMale')
fighter = _person(G, pr, 'FOLabCourtFighter01', 'Court Fighter', 'NVProspectorMale')
made = server.edit('stand-ins', [{'op': 'record_new', 'record': dock}, {'op': 'record_new', 'record': fighter}])['made']
server.edit('placed', [{'op': 'add', 'cell': cell(x0, y0), 'base': made[0], 'p': [x0, y0, 9000.0, 0, 0, 0], 's': 1.0}])
pirate_ref = next(k for k, r in pr.cells[cell(x0, y0)]['refs'].items() if r['base'] == made[0])
P = {'world': G.key(world), 'skipped': [], 'rows': [
    {'what': 'deal', 'at': 'kahala', 'cell': cell(x0, y0), 'ref': pirate_ref, 'base': made[0], 'edid': PD.TRADER_FROM},
    {'what': 'trader', 'at': 'kahala', 'p': (x0 + 500, y0, 9000.0, 0.0), 'from_ground': 200, 'door': 900},
    {'what': 'toll', 'fighters': [made[1]]}]}
undo0 = len(pr.undo_stack)
rep = PD.apply(pr, G, P)
check('one Undo', len(pr.undo_stack) == undo0 + 1)
check('records made', rep['made'][:4] == ['FOLabRepCourt', 'FOLabRepPirates', 'FOLabRepHuang', 'FOLabPirateTraders'] and len(rep['made']) == 7, rep['made'])
check('the pirate swapped to its dealing copy', pr.cells[cell(x0, y0)]['refs'][pirate_ref]['base'] == next(
    k for k, r in pr.records.items() if recordio.field(r, 'EDID') == PD.TRADER_FROM + 'Deals'))
copy = next(r for r in pr.records.values() if recordio.field(r, 'EDID') == PD.TRADER_FROM + 'Deals')
facs = [next(f['value'] for f in s['fields'] if f.get('name') == 'Faction') for s in copy['subs'] if s['tag'] == 'SNAM']
check('its own faction, not its template\'s, helping nobody', facs == [rep['keys']['faction']] and not ff._num(copy, 'ACBS', 'Template flags') & 0x04
      and ff._num(copy, 'AIDT', 'Assistance') == 0)
check('8 lines for one trader and one fighter', rep['lines'] == 8, rep['lines'])
try:
    PD.ops(G, pr, P)
    check('a second go refused', False)
except ValueError:
    check('a second go refused', True)
os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'Pirate Test.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
mine = {tes4.zstr(g.fields(f).get('EDID', b'')): f for f, (n, r) in g.forms.items() if n == i}
fac = dict(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine['FOLabPirateTraders']][1])))
fiends = G.forms[next(f for f, (n, r) in G.forms.items() if r.tag == 'FACT' and G.edid(f) == PD.FIENDS)][1].formid
check('the traders\' faction allied to the Fiends', struct.unpack_from('<I', fac['XNAM'], 0)[0] == fiends and struct.unpack_from('<I', fac['XNAM'], 8)[0] == 2)
check('three reputations', all(e in mine for e in ('FOLabRepCourt', 'FOLabRepPirates', 'FOLabRepHuang')))
q = g.forms[mine[PD.QUEST]][1].formid
srcs = []
for f, (k, r) in g.forms.items():
    if k == i and r.tag == 'INFO':
        sd = list(tes4.iter_subrecords(g.plugins[k].data(r)))
        if struct.unpack('<I', dict(sd)['QSTI'])[0] == q:
            srcs.append((b''.join(v for t, v in sd if t == 'SCTX'), 'KNAM' in dict(sd), dict(sd)['DATA'][2] & 1))
check('the deal opens barter and adds pirate fame', any(b'ShowBarterMenu' in s and b'AddReputation FOLabRepPirates 1 1' in s and kn for s, kn, _b in srcs))
check('the toll: guest adds court fame; paying takes a stimpak', any(b'AddReputation FOLabRepCourt 1 1' in s for s, _k, _b in srcs)
      and any(b'player.RemoveItem Stimpak 1' in s for s, _k, _b in srcs))
check('no line says goodbye', not any(b for _s, _k, b in srcs))
trader = [r for c in g.cell_refs.values() for f, (n, r) in c.items() if n == i and r.tag == 'ACHR'
          and g.edid(g.to_global(n, struct.unpack('<I', dict(tes4.iter_subrecords(g.plugins[n].data(r)))['NAME'])[0])) == 'FOLabPirateTraderKahala']
check('the trader stands with a merchant chest', len(trader) == 1 and 'XMRC' in dict(tes4.iter_subrecords(g.plugins[i].data(trader[0]))))
s = health.check_file(g, out)['summary']
check('the plugin passes health with no errors', s.get('error', 0) == 0, s)
