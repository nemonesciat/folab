"""Lights back on and power cells (generators.py) in a small mod of its own, from a given plan: stand-in night-light
pieces and a local to copy, then one site as one Undo: a generator activator whose script fixes it at Science 55 with 2
Scrap Electronics (switching on its marker), then charges drained cells by its menu; lights, a trader with a merchant
chest and a bedroll under the marker, placed off; the trader's lines. Written and read back."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import browse  # noqa: E402
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import generators as GN  # noqa: E402
import health  # noqa: E402
import project  # noqa: E402
import server  # noqa: E402
import tes4  # noqa: E402
from kuliouquest import _person  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Generator Test')
world = next(w for c, w in G.ext_cells.items() if G.edid(w) == 'WastelandNV')
x0, y0 = -18 * 4096.0 + 2000, 2000.0


def stat(name):
    return {'type': 'STAT', 'flags': 0, 'src': '', 'subs': [
        {'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': 'FOLabNight' + name},
        {'tag': 'OBND', 'label': 'Bounds', 'kind': 'struct', 'fields': [{'name': n, 'code': 'h', 'value': v} for n, v in
                                                                         zip(('X1', 'Y1', 'Z1', 'X2', 'Y2', 'Z2'), (-40, -40, 0, 40, 40, 80))]},
        {'tag': 'MODL', 'label': 'Model', 'kind': 'z', 'value': 'folab\\night\\%s.nif' % name}]}
server.edit('stand-ins', [{'op': 'record_new', 'record': stat(n)} for n in ('generator', 'pole_bulbs_600', 'lantern_post')] +
            [{'op': 'record_new', 'record': _person(G, pr, GN.TRADER_FROM, 'Waikiki Local', 'NVProspectorMale')}])
P = {'world': G.key(world), 'skipped': [], 'rows': [{'site': 'The Tanks', 'near': {}, 'spots': {
    'generator': (x0, y0, 9000.0, 0.0), 'trader': (x0 + 300, y0, 9000.0, 0.0), 'bed': (x0, y0 + 400, 9000.0, 0.0)},
    'lights': [(p, (x0 + dx, y0 + dy, 9000.0, 0.0)) for p, dx, dy in GN.LIGHTS]}]}
undo0 = len(pr.undo_stack)
rep = GN.apply(pr, G, P)
check('one Undo, two trader lines', len(pr.undo_stack) == undo0 + 1 and rep['lines'] == 2, rep)
os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'Generator Test.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
mine = {tes4.zstr(g.fields(f).get('EDID', b'')): f for f, (n, r) in g.forms.items() if n == i}
src = dict(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine['FOLabGeneratorTheTanksScript']][1])))['SCTX']
check('fixed at Science 55 with 2 Scrap Electronics, its marker on', b'GetActorValue Science >= 55' in src and b'ScrapElectronics >= 2' in src
      and b'FOLabPowerTheTanksMarker.Enable' in src)
check('its menu charges drained cells, more at Science 75', b'GetButtonPressed' in src and b'AddItem AmmoMicroFusionCell n' in src
      and b'Science >= 75' in src)
m = list(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine['FOLabGeneratorMenuMsg']][1])))
check('the menu has two buttons', sum(1 for t, _v in m if t == 'ITXT') == 2)
off = 0
marker = None
for c, rr in g.cell_refs.items():
    for f, (n, r) in rr.items():
        if n != i:
            continue
        d = dict(tes4.iter_subrecords(g.plugins[n].data(r)))
        if tes4.zstr(d.get('EDID', b'')) == 'FOLabPowerTheTanksMarker':
            marker = (r.formid, bool(r.flags & 0x800))
        if 'XESP' in d:
            off += 1
check('the marker starts off', marker and marker[1], marker)
check('lights, their lights, trader and bed under it (8)', off == 8, off)
h = health.check_file(g, out)
bad = [(x['kind'], x['count']) for x in h['groups'] if x['sev'] == 'error' and x['kind'] != 'mesh']
check('the plugin passes health, but for the stand-in models (no files)', not bad, bad)
