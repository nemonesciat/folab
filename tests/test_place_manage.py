"""Managing places from the Places list: rename, copy, delete a place of your own, put a game place back. Each one undoes, and what's
left still saves as a plugin that loads. Nothing goes near the real game."""
import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import browse
import espwrite
import gamedata
import project
import recordio
import server
import tes4


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % detail if detail else ''))


G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Places')
shop = next(c for c in G.interiors if G.edid(c) == '2EOVault21GiftShop')
shop_key = G.key(shop)
door_base = next(G.key(f) for f, (i, r) in G.forms.items() if r.tag == 'DOOR' and G.edid(f) == 'VDoorSliding02')
coc = next(G.key(f) for f, (i, r) in G.forms.items() if r.tag == 'STAT' and G.edid(f) == 'COCMarkerHeading')


def snapshot():
    return json.dumps([pr.cells, pr.records, pr.navmesh, pr.cellinfo], sort_keys=True)


def plugin_ok(name):
    out = os.path.join(project.HOME, name + '.esp')
    espwrite.write(G, pr, out)
    return sorted({r.tag for r, _g in tes4.PluginFile(out).walk()})


# a place of your own, with a door linked to another of your own
room = server.new_place({'from': shop_key, 'name': 'First', 'edid': 'FirstRoom'})['made'][0]
other = server.new_place({'from': shop_key, 'name': 'Second', 'edid': 'SecondRoom'})['made'][0]
d1 = pr.apply('door', [{'op': 'add', 'cell': room, 'base': door_base, 'p': [0, 0, 0, 0, 0, 0]}])[0]
d2 = pr.apply('door', [{'op': 'add', 'cell': other, 'base': door_base, 'p': [0, 0, 0, 0, 0, 0]}])[0]
pr.apply('link', [{'op': 'tel', 'cell': room, 'ref': d1, 'tel': {'door': d2, 'p': [0, 0, 0, 0, 0, 0]}},
                  {'op': 'tel', 'cell': other, 'ref': d2, 'tel': {'door': d1, 'p': [0, 0, 0, 0, 0, 0]}}])
pr.apply('details', [{'op': 'cellinfo', 'cell': room, 'info': {}}])
pr.apply('mesh', [{'op': 'navmesh', 'cell': room, 'mesh': {'verts': [], 'tris': [], 'doors': [], 'sig': ''}}])

# rename
got = server.place_rename({'id': room, 'name': 'Renamed', 'edid': 'RenamedRoom'})
check('renamed: its name and editor ID change', recordio.field(pr.records[room], 'FULL') == 'Renamed' and recordio.field(pr.records[room], 'EDID') == 'RenamedRoom' and got['edid'] == 'RenamedRoom')
got = server.place_rename({'id': room, 'name': 'Renamed', 'edid': 'RenamedRoom'})
check('keeping its own editor ID is no clash', got['edid'] == 'RenamedRoom')
got = server.place_rename({'id': room, 'name': 'Renamed', 'edid': 'SecondRoom'})
check('another place\'s editor ID gets a number', got['edid'] == 'SecondRoom2', got['edid'])
pr.undo()
check('undo brings the name back', recordio.field(pr.records[room], 'EDID') == 'RenamedRoom')
for bad, call in (('game place', lambda: server.place_rename({'id': shop_key, 'name': 'x', 'edid': 'x'})), ('missing place', lambda: server.place_rename({'id': '+FFFFFF', 'name': 'x', 'edid': 'x'}))):
    try:
        call()
        check('renaming a %s is refused' % bad, False)
    except ValueError:
        check('renaming a %s is refused' % bad, True)

# a copy of your own place
copied = server.new_place({'from': room, 'name': 'Copy', 'edid': 'CopyRoom', 'copy': True})['made'][0]
check('a copy of a place of your own has its things', len(pr.cells[copied]['refs']) == len(pr.cells[room]['refs']), str(len(pr.cells[copied]['refs'])))
check('… and the copy\'s doors aren\'t linked', not any(r.get('tel') for r in pr.cells[copied]['refs'].values()))
pr.undo()

# what deleting would touch
k = server.place_check(room)
check('the question first: its things, navmesh and the door led to it', k['things'] == 2 and k['navmesh'] and k['doors'] == 1, str(k))

# delete
before = snapshot()
server.place_delete(room)
check('deleted: the place, its things, navmesh, details all gone', room not in pr.records and room not in pr.cells and room not in pr.navmesh and room not in pr.cellinfo)
check('… and the door elsewhere no longer leads there', not pr.cells[other]['refs'][d2].get('tel'))
check('… the other place keeps its door', d2 in pr.cells[other]['refs'])
check('it still saves', 'CELL' in plugin_ok('after delete'))
pr.undo()
check('one undo brings it all back', snapshot() == before)
for call in (lambda: server.place_delete(shop_key),):
    try:
        call()
        check('a game place can\'t be deleted', False)
    except ValueError:
        check('a game place can\'t be deleted', True)

# a game place put back
game_ref = next(G.key(r['ref']) for r in G.refs(shop) if r['pos'] and not r['leads'])
g_door = next(G.key(r['ref']) for r in G.refs(shop) if r['leads'])
pr.apply('changes', [{'op': 'move', 'cell': shop_key, 'ref': game_ref, 'p': [1, 2, 3, 0, 0, 0]},
                     {'op': 'add', 'cell': shop_key, 'base': coc, 'p': [0, 0, 0, 0, 0, 0]},
                     {'op': 'tel', 'cell': shop_key, 'ref': g_door, 'tel': {'door': d2, 'p': [0, 0, 0, 0, 0, 0]}},
                     {'op': 'tel', 'cell': other, 'ref': d2, 'tel': {'door': g_door, 'p': [0, 0, 0, 0, 0, 0]}}])
before = snapshot()
server.place_put_back(shop_key)
check('put back: nothing of the mod left in it', shop_key not in pr.cells)
check('… a door the mod led to its door is unlinked', not pr.cells[other]['refs'][d2].get('tel'))
pr.undo()
check('undo brings the changes back', snapshot() == before)
try:
    server.place_put_back(other)
    check('a place of your own has nothing to put back', False)
except ValueError:
    check('a place of your own has nothing to put back', True)
