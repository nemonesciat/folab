"""Aboard the ships (shipcrew.py): on a small mod with both ships' places, the mod's pirates, the Huang and three elders
on deck, `ops` puts the crew on the navmeshes, locks the store with the quartermaster's key, makes the pens cells with
captives inside, moves the elders into the freighter's house, locks her hold; one Undo."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import actors  # noqa: E402
import factionfolk as FF  # noqa: E402
import flotillainside as fi  # noqa: E402
import gamedata  # noqa: E402
import project  # noqa: E402
import recordio  # noqa: E402
import shipcrew  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


gd = gamedata.GameData()
form = lambda tag, edid: next(f for f, (_i, r) in gd.forms.items() if r.tag == tag and gd.edid(f) == edid)


def copy(tag, of, edid):
    rec = recordio.load(gd, form(tag, of))
    rec['src'] = ''
    recordio.set_field(rec, 'EDID', edid, label='Editor ID')
    return {'op': 'record_new', 'record': rec, 'name': edid}


world = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
grid = gd.grid(world)
mid = min(grid, key=lambda k: abs(k[0]) + abs(k[1]))
ship = (mid[0] * 4096.0 + 2048, mid[1] * 4096.0 + 2048, -280.0, 0.6)
pr = project.Project.create('Ship Crew')
ops = [copy('NPC_', 'VStreetNCRGambler01' if False else gd.edid(sorted(f for fs in FF.faces(gd).values() for f in fs)[0]), e) for e in shipcrew.PIRATES if 'Female' not in e]
woman = next(f for (race, sex), fs in sorted(FF.faces(gd).items(), key=str) if sex == 'F' for f in fs)
ops.append(copy('NPC_', gd.edid(woman), shipcrew.CAPTAIN_FROM))
ops.append(copy('ARMO', 'ArmorLeather', 'FOLabOfficersCoat'))
ops.append({'op': 'record_new', 'record': FF._faction(gd, *FF.FACTIONS['huang']), 'name': 'huang'})
ops += [copy('NPC_', gd.edid(woman), 'FOLabHuangElder%02d' % n) for n in (1, 2, 3)]
cell = gd.key(grid[mid])
ops += [{'op': 'add', 'cell': cell, 'base': '$FOLabHuangElder%02d' % n, 'p': [ship[0] + 100 * n, ship[1], 300.0, 0, 0, 0], 's': 1} for n in (1, 2, 3)]
pr.apply('people', ops)
for which in fi.SHIPS:
    o, _rep = fi.board(gd, pr, world, ship, which=which)
    pr.apply('inside', o)
    nav, _n = fi.navmesh_ops(gd, pr, dict(pr.names), which)
    pr.apply('inside', nav, merge=True)

ops, rep = shipcrew.ops(gd, pr, world)
pr.apply('aboard', ops)
nav, nrep = shipcrew.navmesh_ops(gd, pr)
pr.apply('aboard', nav, merge=True)
got = shipcrew.check(gd, pr)
PL = shipcrew.places(pr)
edid = lambda k: recordio.field(pr.records[k], 'EDID') if k in pr.records else gd.edid(gd.from_key(k))
want = sum(n for rooms in shipcrew.CREW.values() for n in rooms.values())
check('nobody is short of a place to stand', not rep['short'], rep['short'])
check('the crew by room, the captain and the quartermaster in the house, five captives in the pens',
      got['people'] == {'house': 6, 'below': 6, 'hold': 3, 'pens': 6, 'boat1': 2, 'boat2': 1, 's_house': 3} and rep['people'] == want + 2 + 5, got['people'])
cap = pr.records[FF._mod_key(pr, shipcrew.CAPTAIN_EDID, 'NPC_')]
check('the captain has the user\'s name and is a woman', recordio.field(cap, 'FULL') == shipcrew.CAPTAIN_NAME and 'Iolana' in shipcrew.CAPTAIN_NAME
      and bool(FF._num(cap, 'ACBS', 'Flags') & actors.FEMALE), recordio.field(cap, 'FULL'))
key = FF._mod_key(pr, shipcrew.STORE_KEY[0], 'KEYM')
qm = pr.records[FF._mod_key(pr, shipcrew.QM_EDID, 'NPC_')]
holds = lambda rec, k: any(s['tag'] == 'CNTO' and any(f.get('value') == k for f in s['fields']) for s in rec['subs'])
locked = {(k, round(r['p'][0]), round(r['p'][1])): r['props']['lock'] for k, ck in PL.items() for r in pr.cells[ck]['refs'].values() if (r.get('props') or {}).get('lock') and r.get('tel') or
          (r.get('props') or {}).get('lock') and edid(r['base']) == 'UtlDoor01'}
check('the store\'s door and the ladderway at both ends need the key the Quartermaster carries',
      all(locked.get(d, {}).get('key') == key and locked[d]['level'] == 255 for d in (('below', 128, -768), ('below', 896, -768), ('house', 0, 1920))) and holds(qm, key),
      sorted(locked))
cells = [r for r in pr.cells[PL['pens']]['refs'].values() if edid(r['base']) == shipcrew.JAIL_DOOR]
pkey = FF._mod_key(pr, shipcrew.PENS_KEY[0], 'KEYM')
guard = FF._mod_key(pr, shipcrew.GUARD_EDID, 'NPC_')
check('three barred doors in the pens, locked, their key on the guard who stands there', len(cells) == 3 and all(r['props']['lock']['key'] == pkey for r in cells)
      and holds(pr.records[guard], pkey) and any(r['base'] == guard for r in pr.cells[PL['pens']]['refs'].values()))
check('every captive stands on the pens\' navmesh, behind the bars', got['captives'] == 5 == got['captives_on_mesh'] and not nrep['doors_missed']
      and all(r['p'][1] > shipcrew.BARS_Y + 40 for r in pr.cells[PL['pens']]['refs'].values() if (edid(r['base']) or '').startswith('FOLabFlotillaCaptive')))
check('no cage or mattress left in the bars\' way', not any(('Cage' in (edid(r['base']) or '') or 'Mattress' in (edid(r['base']) or '')) and abs(r['p'][1] - shipcrew.BARS_Y) < 60
                                                             for r in pr.cells[PL['pens']]['refs'].values()))
elders = [(ck, r) for ck, c in pr.cells.items() for r in c['refs'].values() if (edid(r['base']) or '').startswith('FOLabHuangElder')]
check('the three elders are in the freighter\'s house and nowhere else', len(elders) == 3 and all(ck == PL['s_house'] for ck, _r in elders), [ck for ck, _r in elders])
hold = [l for (k, _x, _y), l in locked.items() if k in ('s_house', 's_hold')]
deck = [r for ck, c in pr.cells.items() if not ck.startswith('+') for r in c['refs'].values() if (r.get('props') or {}).get('lock')]
hkey = FF._mod_key(pr, shipcrew.HOLD_KEY[0], 'KEYM')
with_key = [recordio.field(pr.records[r['base']], 'EDID') for _ck, r in elders if holds(pr.records[r['base']], hkey)]
check("the freighter's hold needs its key from the house, from inside and from her deck; one elder, in the master's cabin, carries it", len(hold) == 3 and len(deck) == 1
      and all(l['level'] == 255 and l['key'] == hkey for l in hold + [r['props']['lock'] for r in deck]) and len(with_key) == 1 == sum(holds(r, hkey) for r in pr.records.values())
      and all(r['p'][1] > 800 for _ck, r in elders if holds(pr.records[r['base']], hkey)), (len(hold), len(deck), with_key))
check('her house\'s own doors are open to a stranger', not any((r.get('props') or {}).get('lock') for r in pr.cells[PL['s_house']]['refs'].values()
                                                             if r.get('tel') and round(r['p'][1]) != 1664))
huang = FF._mod_key(pr, FF.FACTIONS['huang'][0], 'FACT')
check('both her places are the Huang\'s', all(pr.cellinfo.get(PL[k], {}).get('XOWN') == huang for k in ('s_house', 's_hold')))
check('loot in the Flotilla only: finds in the store and the hold, none aboard the freighter', rep['finds'].get('finds', 0) >= 6
      and not any(o['op'] in ('add', 'swap') and o['cell'] == PL['s_hold'] for o in ops), rep['finds'].get('finds'))
try:
    shipcrew.ops(gd, pr, world)
    twice = ''
except ValueError as e:
    twice = str(e)
check('asked again, it says they are aboard', 'already' in twice, twice)
pr.undo()
check('one Undo takes all of it out', not FF._mod_key(pr, shipcrew.CAPTAIN_EDID, 'NPC_') and not any((r.get('props') or {}).get('lock') for c in pr.cells.values() for r in c['refs'].values())
      and len([1 for c in pr.cells.values() for r in c['refs'].values() if (edid(r['base']) or '').startswith('FOLabHuangElder')]) == 3 and not pr.cellinfo.get(PL['s_house'])
      and not any(holds(r, hkey) for r in pr.records.values()))
