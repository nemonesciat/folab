"""Where a new game of the mod's own can start, through the server as the page does it (newgame.py): outside, where the
marker goes in the world's always-loaded cell; in a place of the mod's own, on its floor; and what opens once you've
arrived: an opening message of the mod's own, the Pip-Boy handed over while the last thing is open, or not at all when
nothing opens. Nothing goes near the real game."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import api_scripts  # noqa: E402
import browse  # noqa: E402
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import health  # noqa: E402
import newgame  # noqa: E402
import project  # noqa: E402
import server  # noqa: E402
import tes4  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Own Game')
writes = 0


def written():
    global writes
    writes += 1
    out = os.path.join(project.BUILD_DIR, 'Own Game %d.esp' % writes)
    os.makedirs(project.BUILD_DIR, exist_ok=True)
    espwrite.write(G, pr, out)
    g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
    return g, len(g.plugins) - 1, out


def script_text():
    return api_scripts.source_of(pr.records[pr.newgame['made']['script']]).replace('\r', '')


def scro(g, i):
    f = next(f for f, (k, r) in g.forms.items() if k == i and r.tag == 'SCPT')
    return [g.to_global(i, struct.unpack('<I', d)[0]) for t, d in tes4.iter_subrecords(g.plugins[i].data(g.forms[f][1])) if t == 'SCRO']


# ---------- outside ----------
cell =next(c for c, w in G.ext_cells.items() if G.edid(w) == 'WastelandNV' and G.cell_grid(c) == (-18, 0))
x, y = G.cell_grid(cell)
spot = [(x + 0.5) * 4096, (y + 0.5) * 4096, 9000.0, 0.7]
out = server.new_game({'on': True, 'cell': G.key(cell), 'p': spot})
check('outside: the page hears it is on, in the world', out['newgame']['settings']['on'] and out['newgame']['world'] == G.key(G.ext_cells[cell]))
g, i, path = written()
refs = [(cf, rf) for cf, rs in g.cell_refs.items() for rf in rs if rf >> 24 == i and g.cell_refs[cf][rf][1].tag == 'REFR']
check('outside: one marker, in the world\'s always-loaded cell', len(refs) == 1 and refs[0][0] == g.world_persistent.get(g.ext_cells[cell]), refs)
entry = g.cell_refs[refs[0][0]][refs[0][1]]
fl = g.ref_fields(entry)[1]
check('it is persistent, named, and where it was asked', entry[1].flags & tes4.PERSISTENT and tes4.zstr(fl.get('EDID', b'')) == 'OwnGameNewGameStart'
      and [round(v, 1) for v in struct.unpack('<6f', fl['DATA'])[:3]] == [round(v, 1) for v in spot[:3]])
check('the script names it', refs[0][1] in scro(g, i))
check('the plugin passes the health check', health.check_file(G, path)['summary']['error'] == 0, health.check_file(G, path)['summary'])
pr.undo()
check('one Undo takes the outdoor start away', not pr.newgame and not pr.records and not any(c.get('refs') for c in pr.cells.values()))

# ---------- a place of the mod's own ----------
shop = G.key(next(c for c in G.interiors if G.edid(c) == '2EOVault21GiftShop'))
room = server.new_place({'from': shop, 'name': 'Where It Begins', 'edid': 'OwnGameStartRoom', 'copy': True})['made'][0]
out = server.new_game({'on': True, 'cell': room, 'p': [0.0, 0.0, 5000.0, 0.0]})
check('own place: the page names it', out['newgame']['place'] == 'Where It Begins', out['newgame']['place'])
mk = pr.newgame['made']['marker']
check('the marker is in that place', mk[0] == room and mk[1] in pr.cells[room]['refs'])
check('and stands on its floor, not up where the view was', pr.cells[room]['refs'][mk[1]]['p'][:3] != [0.0, 0.0, 5000.0], pr.cells[room]['refs'][mk[1]]['p'])
g, i, path = written()
own = next(f for f, (k, r) in g.forms.items() if k == i and r.tag == 'CELL')
marker = [rf for rf, e in g.cell_refs[own].items() if tes4.zstr(g.ref_fields(e)[1].get('EDID', b'')) == 'OwnGameNewGameStart']
check('written: the marker is in the mod\'s own place, kept loaded, and the script names it',
      len(marker) == 1 and g.cell_refs[own][marker[0]][1].flags & tes4.PERSISTENT and marker[0] in scro(g, i))
check('the plugin passes the health check', health.check_file(G, path)['summary']['error'] == 0, health.check_file(G, path)['summary'])

# ---------- an opening message ----------
words = 'You wake with sand in your mouth.\nNobody is coming.'
server.new_game({'message': words})
made = pr.newgame['made']
text = script_text()
check('a message of the mod\'s own is made', pr.records[made['message']]['type'] == 'MESG' and 'OwnGameNewGameMessage' in str(pr.records[made['message']]))
check('the script shows it once you have arrived, before the screens', 0 < text.find('player.MoveTo') < text.find('ShowMessage OwnGameNewGameMessage') < text.find('GetPlayerName'))
g, i, path = written()
mf = next(f for f, (k, r) in g.forms.items() if k == i and r.tag == 'MESG')
mfl = g.fields(mf)
check('written as a message box with its words', tes4.zstr(mfl['DESC']) == words and struct.unpack('<I', mfl['DNAM'])[0] == 1 and mf in scro(g, i))
server.new_game({'message': 'Changed.'})
check('changing the words keeps the same record', pr.newgame['made']['message'] == made['message'] and 'Changed.' in str(pr.records[made['message']]))

# ---------- nothing but the message: the Pip-Boy goes on while it is open ----------
out = server.new_game({'steps': []})
text = script_text()
check('no screens: the Pip-Boy is handed over while the message is open',
      'GetPlayerName' not in text and 0 < text.find('ShowMessage') < text.find('begin MenuMode') < text.find('player.EquipItem PipBoy') and not out['newgame']['pipboy_gap'])
out = server.new_game({'message': ''})
text = script_text()
check('no screens and no message: nothing to put it on in, so it is not tried, and the page says so',
      'EquipItem' not in text and 'begin MenuMode' not in text and 'ResetPipboyManager' not in text and out['newgame']['pipboy_gap'])
check('and the message record is gone', 'message' not in pr.newgame['made'] and not any(r['type'] == 'MESG' for r in pr.records.values()))
g, i, path = written()
check('that still writes a plugin that passes the health check', health.check_file(G, path)['summary']['error'] == 0)
out = server.new_game({'pipboy': False})
check('without the Pip-Boy there is nothing missing', not out['newgame']['pipboy_gap'] and 'player.RemoveItem PipBoy 1 1' in script_text())

# ---------- the white the game begins in ----------
server.new_game({'pipboy': True, 'steps': ['name']})
text = script_text()
check('the white is cleared once, on arriving, so Doc Mitchell\'s house stays behind it',
      text.count('RemoveImageSpaceModifier WhiteISFX') == 1 and text.find('player.MoveTo') < text.find('RemoveImageSpaceModifier WhiteISFX') < text.find('GetPlayerName'))

server.new_game({'on': False})
check('off: the marker, script, quest and message all go', not any(c.get('refs') and any(r.get('edid') for r in c['refs'].values()) for c in pr.cells.values())
      and not any(r['type'] in ('SCPT', 'QUST', 'MESG') for r in pr.records.values()))
