"""Boat travel (boatferry.py) made in a small mod of its own, with the boats' and arrival markers' spots given (spots()
needs Waikiki; it was rehearsed on a copy of it): one Undo, keys as reserved, both scripts compiled, each stop's menu
offering the other stops then "Stay ashore" with the trip script sending each button where the menu says, rides of at
least an hour, written and read back as the game reads it. Nothing goes near the real game."""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import api_scripts  # noqa: E402
import boatferry as B  # noqa: E402
import browse  # noqa: E402
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import project  # noqa: E402
import server  # noqa: E402
import tes4  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Boat Travel')
api_scripts.setup(lambda: server.GD, lambda: server.PR, lambda: server.BR, lambda: server.state())

world = next(w for c, w in G.ext_cells.items() if G.edid(w) == 'WastelandNV')
grid = G.grid(world)
cell = lambda x, y: G.key(grid[(int(x // 4096), int(y // 4096))])
x0, y0 = -18 * 4096.0 + 2000, 2000.0
spots = [(x0 + k * 30000.0, y0) for k in range(len(B.STOPS))]
where = {'world': world,
         'boat': [(cell(x, y), [x, y, 12.0, 0.0, 0.0, 1.0]) for x, y in spots],
         'land': [(cell(x, y + 400), [x, y + 400, 9000.0, 0.0, 0.0, 0.0]) for x, y in spots]}

# ---- the menus and the trip script agree ----
src = B.quest_source(where)
ok = True
for i in range(1, len(B.STOPS) + 1):
    names = [B.STOPS[j - 1][1] for _b, j in B.others(i)]
    for b, j in B.others(i):
        if 'if here == %d && button == %d\r\n\t\t\tset dest to %d' % (i, b, j) not in src:
            ok = False
    ok = ok and len(names) == len(B.STOPS) - 1 and B.STOPS[i - 1][1] not in names
check('each menu offers the other stops, each button sends you to its stop', ok)
check('"Stay ashore" (the last button) goes nowhere', 'button == %d' % (len(B.STOPS) - 1) not in src)
check('the move is two seconds into the fade, controls back after',
      src.index('ApplyImageSpaceModifier ' + B.FADE) < src.index('player.MoveTo') < src.index('EnablePlayerControls'))
check('time passes on every ride, at least an hour', all(B.hours(where, i, j) >= 1 for i in range(1, 6) for _b, j in B.others(i)))
check('only the game\'s own commands (no extender)', not re.search(r'(?i)\b(let|eval|IsKeyPressed|IsControlPressed|SetPosEx)\b', src + B.boat_source()))

# ---- one Undo, keys as reserved ----
o, rep = B.ops(G, pr, where)
n0, r0 = len(pr.undo_stack), len(pr.records)
made = server.edit('boat travel', o)['made']
want = [rep['keys'][k] for k in B.key_order()]
check('one Undo step', len(pr.undo_stack) == n0 + 1)
check('keys as reserved', made[:len(want)] == want, (made[:3], want[:3]))
check('records: activator, 2 scripts, quest, %d messages' % (len(B.STOPS) + 1), len(pr.records) - r0 == 4 + len(B.STOPS) + 1)
try:
    B.ops(G, pr, where)
    check('a second run refuses', False)
except ValueError:
    check('a second run refuses', True)

# ---- written and read back ----
out = os.path.join(os.environ.get('FOLAB_HOME', '.'), 'boats.esp')
espwrite.write(G, pr, out, reuse=False) if 'reuse' in espwrite.write.__code__.co_varnames else espwrite.write(G, pr, out)
p = tes4.PluginFile(out)
seen, boat_id, boats, persistent = {}, None, 0, 0
recs = [r for r in ((i[0] if isinstance(i, tuple) else i) for i in p.walk()) if hasattr(r, 'tag')]
for r in recs:
    if r.tag in ('ACTI', 'SCPT', 'QUST', 'MESG', 'REFR'):
        f = tes4.subrecord_dict(p.data(r))
        e = tes4.zstr(f.get('EDID', b''))
        seen[e] = (r.tag, f)
        if e == B.EDIDS['boat']:
            boat_id = r.formid
        if e.startswith('FOLabFerryLand') and r.flags & 0x400:
            persistent += 1
for r in recs:
    if r.tag == 'REFR' and boat_id is not None and struct.unpack('<I', tes4.subrecord_dict(p.data(r))['NAME'])[0] == boat_id:
        boats += 1
tag, boat = seen.get(B.EDIDS['boat'], (None, {}))
check('the boat is an activator with the game boat\'s model, a script and the prompt "Sail"',
      tag == 'ACTI' and tes4.zstr(boat.get('MODL', b'')).lower() == 'vehicles\\boat03a.nif' and 'SCRI' in boat and tes4.zstr(boat.get('XATO', b'')) == 'Sail')
check('%d boats placed' % len(B.STOPS), boats == len(B.STOPS), boats)
check('%d arrival markers, persistent' % len(B.STOPS), persistent == len(B.STOPS), persistent)
q = seen.get(B.EDIDS['quest'], (None, {}))[1]
check('the trip quest is not start-enabled', q and not (q['DATA'][0] & 1))
menu1 = next(r for r in recs if r.tag == 'MESG' and tes4.zstr(tes4.subrecord_dict(p.data(r)).get('EDID', b'')) == B.menu_edid(1))
m = [tes4.zstr(v) for t, v in tes4.iter_subrecords(p.data(menu1)) if t == 'ITXT']
check('menu 1 reads as written', m == [s[1] for s in B.STOPS[1:]] + [B.STAY], m)
p.close()
