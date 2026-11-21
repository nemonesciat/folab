import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
"""Repeated rooms made their own (roomvary.py): three copies of one game place, as a city's buildings get when the game
has too few of a kind to lend; the first left as it is, the others with things swapped for others of their kind and
size, a few loose things taken out, and a light of their own; doors and the way out untouched; a second run does
nothing; one Undo. Never starts the game."""
import json
import gamedata, project, recordio, roomvary, townbuild, espwrite, navbuild


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)


# ---------- the pure parts ----------
check('nouns: what a thing is, from its editor ID', roomvary.nouns('OfficeChairRuined01R') == {'chair'} and roomvary.nouns('MetalShelf01') == {'shelf'}
      and roomvary.nouns('WallHall1Way01') == frozenset())
check('a swap fits where the thing stood, or not', roomvary._fits((-20, -20, 0, 20, 20, 40), (-22, -18, 0, 21, 20, 44))
      and not roomvary._fits((-20, -20, 0, 20, 20, 40), (-40, -20, 0, 40, 20, 40)))
check("a quest's things, a vault's and a faction's aren't swapped in",
      all(roomvary.NOT_IN.search(e) for e in ('MS17FinSheetMusicBook', 'VBedSingle01', 'EnclaveBedL01', 'SafehouseFootlocker', 'RCPauliesFilingCabinet'))
      and not any(roomvary.NOT_IN.search(e) for e in ('OfficeChairRuined01R', 'TVSetDirty', 'NVBedTwin01L', 'MetalShelf02')))

# ---------- three copies of one place ----------
gd = gamedata.GameData()
pr = project.Project.create('Room Vary')
place = townbuild.grand_inside(gd, 'NiptonGeneralStore')
check('a game place to copy', bool(place))
ops = []
for tag in ('ra', 'rb', 'rc'):
    o, kept, _doors = townbuild.inside_ops(gd, place, tag, 'FOLabVary' + tag, 'Store')
    ops += o
pr.apply('Three stores', ops)
keys = sorted((k for k, r in pr.records.items() if k.startswith('+') and r.get('type') == 'CELL'), key=lambda k: int(k[1:], 16))
check('three places made', len(keys) == 3)
sw = roomvary.Swaps(gd)
groups = roomvary.twins(gd, pr, sw)
check('they are known for copies of one place', groups == [keys])
before = json.loads(json.dumps({k: pr.cells[k] for k in keys}))
lit_before = json.loads(json.dumps({k: pr.records[k] for k in keys}))
rep = roomvary.vary(gd, pr, sw=sw)
check('the second and third are made their own: %s' % rep, rep['places'] == 2 and rep['swapped'] > 0 and rep['lit'] == 2)
check('the first is left as it is', pr.cells[keys[0]] == before[keys[0]] and pr.records[keys[0]] == lit_before[keys[0]])


def base_of(k, rk, cells):
    return cells[k]['refs'][rk]['base']


bad, doors_moved, loose_only = [], 0, True
for k in keys[1:]:
    for rk, ch in before[k]['refs'].items():
        now = pr.cells[k]['refs'].get(rk)
        old_fid = gd.from_key(ch['base'])
        tag = gd.forms[old_fid][1].tag
        if now is None:
            loose_only &= sw.loose(old_fid)
            continue
        if tag == 'DOOR' or 'tel' in ch:
            doors_moved += now != ch
            continue
        if now['base'] != ch['base']:
            new_fid = gd.from_key(now['base'])
            a, b = sw.info[old_fid], sw.info.get(new_fid)
            if not b or a[0] != b[0] or not roomvary._fits(a[1], b[1]) or roomvary.NOT_IN.search(gd.edid(new_fid)) or now['p'] != ch['p']:
                bad.append((gd.edid(old_fid), gd.edid(new_fid)))
check('every swap is the same kind of thing, the same size, from the same game file, where the first stood: %s' % bad[:3], not bad)
check('doors and the way out stay as they were', doors_moved == 0)


def twins_in(k):
    rows = [(r['base'], r['p'][:3]) for r in pr.cells[k]['refs'].values() if 'base' in r and not r.get('removed')]
    return sum(1 for i, (b, p) in enumerate(rows) for b2, q in rows[i + 1:] if b == b2 and sum((x - y) ** 2 for x, y in zip(p, q)) < 16)


check('no swap stands one thing twice in a spot', all(twins_in(k) <= twins_in(keys[0]) for k in keys[1:]))
check('only loose things are taken out', loose_only)


def colours(rec):
    x = next(s for s in rec['subs'] if s['tag'] == 'XCLL')['fields']
    return [f['value'] for f in x if 'name' in f][:9]


def inherit(rec):
    s = next((s for s in rec['subs'] if s['tag'] == 'LNAM'), None)
    return int(s['fields'][0]['value']) if s else 0


check('each has a light of its own', len({json.dumps(colours(pr.records[k])) for k in keys}) == 3)
check('and no longer takes its colours from the template', all(not inherit(pr.records[k]) & roomvary.INHERIT_COLOURS for k in keys[1:]))
nav_ok = all(pr.navmesh[k]['sig'] == navbuild.signature(navbuild.place_refs(gd, pr, k)) for k in keys if k in pr.navmesh)
check('a navmesh that was current still is', nav_ok)
again = roomvary.vary(gd, pr, apply=False, sw=sw)
check('a second run leaves them alone', again['places'] == 0)
data = espwrite.Writer(gd, pr).build()
check('the mod is written', len(data) > 1000)
pr.undo()
check('one Undo puts them back', all(pr.cells[k] == before[k] for k in keys))

# ---------- a building's own pieces stay as the game has them ----------
# (the user's look in nv-rs, 20 Nov 2026: copies of the game's houses stood with a wall open onto white. The house's whole
# inside, UshomIntLight01, had been swapped for UshomIntLight02 of another shape: 'Light' read as a lamp)
shell = next(f for f, (i, r) in gd.forms.items() if r.tag == 'STAT' and gd.edid(f) == 'UshomIntLight01')
other = next(f for f, (i, r) in gd.forms.items() if r.tag == 'STAT' and gd.edid(f) == 'UshomIntLight02')
lamp = next(f for f, (i, r) in gd.forms.items() if r.tag == 'STAT' and gd.edid(f) == 'OffRmLight01')
check("a house's whole inside is part of the building, a ceiling lamp isn't",
      roomvary.building_piece('UshomIntLight01', roomvary._bounds(gd, shell)) and not roomvary.building_piece('OffRmLight01', roomvary._bounds(gd, lamp)))
check('so nothing swaps it, or is swapped for it', shell not in sw.info and other not in sw.info and lamp in sw.info)
house = townbuild.grand_inside(gd, 'NiptonHouse3')
check('a game house to copy', bool(house))
pr2 = project.Project.create('Room Vary Houses')
ops = []
for tag in ('ha', 'hb'):
    ops += townbuild.inside_ops(gd, house, tag, 'FOLabVary' + tag, 'House')[0]
pr2.apply('Two houses', ops)
hk = sorted((k for k, r in pr2.records.items() if k.startswith('+') and r.get('type') == 'CELL'), key=lambda k: int(k[1:], 16))
shell_key = gd.key(shell)
held = [(k, rk) for k in hk for rk, ch in pr2.cells[k]['refs'].items() if ch.get('base') == shell_key]
check('each copy has the house', len(held) == 2)
roomvary.vary(gd, pr2, sw=sw)
check('making the second its own leaves the house as it is', all(pr2.cells[k]['refs'][rk]['base'] == shell_key for k, rk in held))
# (what an earlier run did: the second's house swapped for another)
pr2.apply('An old swap', [{'op': 'swap', 'cell': held[1][0], 'ref': held[1][1], 'base': gd.key(other)}])
found = roomvary.mend(gd, pr2)
check('mend puts the house back as the game has it: %s' % found,
      pr2.cells[held[1][0]]['refs'][held[1][1]]['base'] == shell_key and list(found) == [held[1][0]])
check('and finds nothing more on a second run', roomvary.mend(gd, pr2, apply=False) == {})
pr2.undo()
check('one Undo takes the mend back', pr2.cells[held[1][0]]['refs'][held[1][1]]['base'] == gd.key(other))
