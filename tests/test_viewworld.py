"""Rooms with a view (viewworld): a small world set under another as the game sets the Lucky 38's top floors under the
Mojave: added straight to a mod's own source plugin with nothing else in it changed, its ground the parent's to the
unit, its water cell for cell, set under the parent as every one of the game's is (PNAM 4), and the parent's things
round it copied in as they stand (no actors, nothing initially off, doors locked). Then the far view drawn for it from
the parent (lodgen and lodobj with `like`)."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
os.environ.setdefault('FOLAB_NO_GAME_WRITES', '1')
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import project  # noqa: E402
import roadgen  # noqa: E402
import server  # noqa: E402
import viewworld  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


server.not_while_playing = lambda: None
server.GD = gamedata.GameData()
server.BR = None
pr = project.Project.create('Views')
server.load_game(pr)
server.PR = pr
gd = server.GD
# (a mod opened from a plugin: its own plugin made with every game file as a master, as a new world makes it)
w = espwrite.Writer(gd, pr)
w.force_all = True
folder = os.path.join(project.PROJECTS_DIR, 'Views source')
os.makedirs(folder, exist_ok=True)
with open(os.path.join(folder, 'Views.esp'), 'wb') as f:
    f.write(w.build())
pr.source = 'Views source/Views.esp'
pr.save()
server.load_game(pr)
gd = server.GD
P = next(x for x in gd.worlds() if gd.edid(x) == 'WastelandNV')
# (Goodsprings: land, things, no water; and somewhere wet: Lake Mead's shore)
cx, cy = -18, 0
before = open(pr.source_path(), 'rb').read()
wid = viewworld.add_world(gd, pr, P, 'FOLabTestView', 'A View', cx, cy, reach=1)
after = open(pr.source_path(), 'rb').read()
check('the world goes into the mod\'s own plugin, which only grows', len(after) > len(before) and after[:4] == b'TES4')
pr.save()
server.GD.stale = True
server.load_game(pr)
gd = server.GD
P = next(x for x in gd.worlds() if gd.edid(x) == 'WastelandNV')
C = next((x for x in gd.worlds() if gd.edid(x) == 'FOLabTestView'), None)
check('the new world loads', C is not None)
f = gd.fields(C)
parent = gd.to_global(gd.forms[C][0], struct.unpack('<I', f['WNAM'])[0]) if 'WNAM' in f else None
check('set under its parent, with the parent\'s map, as the game sets its own', parent == P and f.get('PNAM') == b'\x04\x00' and f['DATA'][0] == viewworld.FLAGS,
      (gd.edid(parent) if parent else None, f.get('PNAM'), f.get('DATA')))
check('its cells are the ones round the spot', sorted(gd.grid(C)) == sorted((x, y) for x in range(cx - 1, cx + 2) for y in range(cy - 1, cy + 2)), len(gd.grid(C)))
gp, gc = roadgen.Ground(gd, pr, P), roadgen.Ground(gd, pr, C)
diff = max(abs((gp.at(x, y) or 0) - (gc.at(x, y) or 0)) for x in range((cx - 1) * 4096 + 64, (cx + 2) * 4096 - 64, 700)
           for y in range((cy - 1) * 4096 + 64, (cy + 2) * 4096 - 64, 700))
check('its ground is the parent\'s to the unit', diff < 1.0, diff)


def level(world, k):
    c = gd.grid(world)[k]
    ff = gd.fields(c)
    if not (ff.get('DATA') or b'\0')[0] & 2:
        return None
    x = ff.get('XCLW')
    h = struct.unpack('<f', x)[0] if x else None
    return 'world' if h is None or h > 1e30 else round(h)
wet = [(k, level(P, k), level(C, k)) for k in gd.grid(C)]
check('its water cell for cell as the parent\'s', all(a == b or (a is None and b is not None and b < -1000) for _k, a, b in wet), wet[:3])
stage = viewworld.stage_ops(gd, pr, P, C, cx, cy, reach=1)
kinds = {}
for o in stage:
    t = gd.forms[gd.from_key(o['base'])][1].tag if o['base'][:1] not in ('+', '$') else 'own'
    kinds[t] = kinds.get(t, 0) + 1
check('the parent\'s things round it come in, only what\'s seen', len(stage) > 200 and set(kinds) <= set(viewworld.KEEP) | {'own'}, kinds)
check('each where it stands, in the small world\'s cell under it', all(o['cell'] == gd.key(gd.grid(C)[(int(o['p'][0] // 4096), int(o['p'][1] // 4096))]) for o in stage))
doors = [o for o in stage if gd.forms[gd.from_key(o['base'])][1].tag == 'DOOR']
check('doors come in locked, leading nowhere', all(o['extra']['props']['lock']['level'] == 255 for o in doors), len(doors))
pr.apply('view', stage)
check('the copies are the mod\'s own', all(any(rk.startswith('+') for rk in pr.cells.get(o['cell'], {}).get('refs', {})) for o in stage[:20]))
