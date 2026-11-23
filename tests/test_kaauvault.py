"""The Vault in Kaʻau Crater, inside (kaauvault.py), a plan as a picture (planpic.py), and a generated place as a drawing
to change and build again (kitplan.drawing_of, plan_from_drawing). Walked on the real collision shapes, read from the
game's files; nothing goes near the game or a mod."""
import collections
import os
import random
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata
import kitdress as D
import kitindex as K
import kitlife as L
import kitplan as P
import kaauvault as KV
import planpic


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % detail if detail else ''))


VAULT = 'dungeons' + chr(92) + 'vault'
G = gamedata.GameData()
kits = K.build(G)
sv = D.survey(G, kits, only={VAULT})
store = {}

# ---------- what it's made of ----------
told = L.things_of(G)
want = {t[0] for s in KV.SCENES.values() for t in s} | {e for v in KV.STORY['finds'].values() for e in v}
gone = sorted(e for e in want if e not in told.keys)
check('every thing the Vault\'s rooms use is in the game', not gone, gone)
check('… and has a mesh to stand it by', not [e for e in want if e in told.keys and told.keys[e][1] != 'light' and not told.size(e)])
check('every scene a room names exists', all(n in L.SCENES for k, v in KV.STORY.items() if isinstance(v, tuple) for n in v))
check('its story is never drawn for an ordinary vault', all(L.STORIES[KV.STORY_KEY].get(k) for k in ('given', 'kept')))
prog = KV.program(4, random.Random(1))
names = [s.name for s in prog]
check('only decided rooms unless asked: no reclamation plant or holding rooms', not {'the reclamation plant', 'the holding rooms'} & set(names))
check('… asked, they come in', {'the reclamation plant', 'the holding rooms'} <= {s.name for s in KV.program(4, random.Random(1), proposed=True)})
check('the user\'s answers (22 Nov): the council chamber, kitchens and cold store, servants\' quarters, a back door room',
      {'the council chamber', 'the kitchens', 'the cold store', "the servants' quarters", 'the back door'} <= set(names) and sum(s.back for s in prog) == 1)
check('… no back door unless wanted', not any(s.back for s in KV.program(4, random.Random(1), back=False)))
check('the reactor is laid last, at the end of the power wing', prog[-1].purpose == 'reactor' and prog[-1].wing == 'power')

# ---------- a layout ----------
for seed in (1, 2):
    g = KV.make(G, kits, 3, seed, store, {}, sv)
    check('seed %d: a layout walks' % seed, g is not None)
    if not g:
        continue
    plan = g['plan']
    low = min(c[2] for c in plan.squares())
    reactor = next(o for o in plan.rooms() if o['purpose'] == 'reactor')
    check('seed %d: the reactor is the deepest room (%d levels)' % (seed, len({c[2] for c in plan.squares()})), min(c[2] for c in reactor['cells']) == low)
    check('seed %d: its own story, nothing wrecked' % seed, plan.story == KV.STORY_KEY and not any(o.get('wrecked') for o in plan.rooms()))
    rooms = collections.Counter(o.get('name') for o in plan.rooms())
    check('seed %d: the rooms keep their names (%d founders\' suites)' % (seed, rooms["a founders' suite"]),
          rooms["a founders' suite"] >= KV.SUITES and all(rooms[n] for n in ('the feast hall', 'the Pip-Boy workshop', 'the cell charging room', 'the clinic', 'the armoury')))
    scenes = collections.Counter(s for o in plan.rooms() for s in o.get('scenes', []))
    check('seed %d: dressed as the Vault, not as a vault people left' % seed, scenes['suite'] and scenes['banquet'] and not (scenes['last stand'] or scenes['lay down']))
    check('seed %d: the council needs a key, left in another room' % seed, plan.locks['key'] and plan.locks['rooms'] >= 2 and plan.locks.get('office') == 'The council chamber')
    backs = [it for it in g['items'] if it.what == 'exit']
    check('seed %d: two ways out, the gear door\'s and a back door (in its own room)' % seed, plan.back and len(backs) == 2 and sum(1 for it in backs if it.link == 'back') == 1
          and plan.owners[plan.cells[plan.back[0]]].get('name') == 'the back door')
    check('seed %d: lit and clean: no rubble, nothing dirty or broken, no failing lights' % seed, not [it for it in g['items'] if D.dirty(sv[VAULT], it)])
    meat = G.key(told.keys['HumanFlesh'][0])
    check('seed %d: the eating shown plainly: meat in the kitchens and on the feast hall\'s plates' % seed,
          scenes['butchery'] and scenes['banquet'] and sum(1 for it in g['items'] if it.key == meat) >= 4)
    check('seed %d: no gap to fall down, furnished or not' % seed, not g['walk']['edges'] and not P.walk_check(G, P.tiles_for(G, kits, VAULT, store, sv), plan, g['made'], {})['edges'])
    pic = planpic.svg(plan, g['items'], 'test')
    check('seed %d: its picture names its rooms and shows every level' % seed, pic.startswith('<svg') and 'the feast hall' in pic and
          all('Level %d<' % lv in pic for lv in {c[2] for c in plan.squares()}))
out = KV.ops(G, kits, 3, 1, [0, 0, 0], store, {}, sv)
check('as changes for a mod: the key\'s record first (the Council Key), the rest after', out.get('ops') and out['ops'][0]['op'] == 'record_new' and
      any(o.get('base') == '$made' for o in out['ops']) and any(sb.get('value') == KV.KEY_NAME for sb in out['ops'][0]['record']['subs']))
check('… the back door\'s door is marked for linking', sum(1 for o in out['ops'] if o.get('exit') == 'back') == 1 and sum(1 for o in out['ops'] if o.get('exit') is True) == 1)

# ---------- a generated place as a drawing ----------
g = P.vault_place(G, kits, 3, 5, store, {}, None)
d = P.drawing_of(g['plan'])
part = sum(1 for o in g['plan'].rooms() if o.get('part_of') is not None)
check('a generated vault as a drawing: every room but the balconies\' (part of the tall room)', len(d['rooms']) + d['left_out'] == len(g['plan'].rooms()) - part)
boxes = [(r['level'], x, y) for r in d['rooms'] for x in range(r['x'], r['x'] + r['w']) for y in range(r['y'], r['y'] + r['h'])]
check('… no two rooms overlap, the way in first', len(boxes) == len(set(boxes)) and d['rooms'][0]['purpose'] == 'entrance')
check('… every room linked to something', {i for l in d['links'] for i in l} == set(range(len(d['rooms']))))
out = P.drawn(G, kits, VAULT, d['rooms'], d['links'], 1, [0, 0, 0], store, {}, None)
check('… and built again from the drawing', out.get('ops'), out.get('note', ''))
# a hand drawing with a link that can't be made: built, and said
rooms = [{'x': 0, 'y': 0, 'w': 4, 'h': 3, 'level': 0}, {'x': 4, 'y': 0, 'w': 3, 'h': 3, 'level': 0}, {'x': 7, 'y': 0, 'w': 3, 'h': 3, 'level': 0}]
ts = P.tiles_for(G, kits, VAULT, store, None)
plan, said = P.plan_from_drawing(ts, rooms, [[0, 1], [1, 2], [0, 2]], 1)
check('a drawing builds, and says any link it couldn\'t make', plan is not None and isinstance(said, list), said)
plan, said = P.plan_from_drawing(ts, rooms + [{'x': 0, 'y': 3, 'w': 3, 'h': 3, 'level': 0, 'name': 'the cupboard'}], [[0, 1], [1, 2]], 1)
check('… a room nobody linked is joined to the nearest that\'s reached, and said', plan is not None and any('joined to' in s for s in said), said)
check('… a drawn room keeps its name', plan is not None and any(o.get('name') == 'the cupboard' for o in plan.rooms()))

# ---------- checks while drawing, plans kept by name ----------
import kitdrawings  # noqa: E402
ok = kitdrawings.check(ts, rooms[:2], [[0, 1]])
check('a drawing checked without its pieces: two rooms, both reached', ok['ok'] and ok['reached'] == 2 and not ok['problems'], ok)
bad = kitdrawings.check(ts, [rooms[0], rooms[0]], [])
check('… overlapping rooms are a problem, said', not bad['ok'] and any('overlap' in p for p in bad['problems']), bad)
narrow = kitdrawings.check(ts, [{'x': 0, 'y': 0, 'w': 1, 'h': 4}], [])
check('… so is a room too narrow', not narrow['ok'] and any('narrow' in p for p in narrow['problems']), narrow)
check('… and nothing drawn', not kitdrawings.check(ts, [], [])['ok'])
kept = kitdrawings.save('The Vault, first go', {'rooms': rooms[:2], 'links': [[0, 1]], 'kit': VAULT})
check('a drawing kept by name, listed with its room count', any(p['name'] == 'The Vault, first go' and p['rooms'] == 2 for p in kept), kept)
back = kitdrawings.load('The Vault, first go')
check('… loaded back as it was', back['rooms'] == rooms[:2] and back['links'] == [[0, 1]] and back['kit'] == VAULT)
check('… kept under FOLab\'s home, not in a mod', os.path.isfile(os.path.join(kitdrawings.PLANS_DIR, 'The Vault, first go.json')))
check('… and deleted', not any(p['name'] == 'The Vault, first go' for p in kitdrawings.remove('The Vault, first go')))
try:
    kitdrawings.save('  ', {'rooms': rooms[:1]})
    check('a plan needs a name', False)
except ValueError:
    check('a plan needs a name', True)

# ---------- its number on the gear door (vaultnumber.py): Vault 50 ----------
import dds  # noqa: E402
import vaultnumber as VN  # noqa: E402
check('its name is Vault 50', KV.NAME == 'Vault 50')
w, h, px = dds.decode(G.read_file(VN.SHEET), VN.SIZE)[:3]
figs = VN.figures(bytearray(px))
check('the game\'s stencil figures read off the hatch strips: 0 to 5, 7, 8, 9', set('0123457 89'.replace(' ', '')) <= set(figs), str(sorted(figs)))
data, drawn = VN.sheet(G, '50')
w2, h2, px2 = dds.decode(data, VN.SIZE)[:3]
x0, y0, x1, y1 = VN.PLATE
changed = sum(1 for y in range(y0, y1) for x in range(x0, x1) if px[(y * VN.SIZE + x) * 4:(y * VN.SIZE + x) * 4 + 3] != px2[(y * VN.SIZE + x) * 4:(y * VN.SIZE + x) * 4 + 3])
outside = sum(1 for y in range(0, 700, 7) for x in range(0, VN.SIZE, 7) if px[(y * VN.SIZE + x) * 4:(y * VN.SIZE + x) * 4 + 3] != px2[(y * VN.SIZE + x) * 4:(y * VN.SIZE + x) * 4 + 3])
check('the gear door\'s plate shows 50: figures drawn on it, the rest of the sheet as it was', drawn > 1000 and changed > 1000 and outside == 0, str((drawn, changed, outside)))
old_doors = {G.key(f) for f, (_i, r) in G.forms.items() if r.tag == 'DOOR' and G.edid(f) in KV.CLEAN_DOORS}
check('no door showing another vault\'s number (the ruined sliding door swapped for the plain one)', not any(o.get('base') in old_doors for o in KV.ops(G, kits, 3, 1, [0, 0, 0], store, {}, sv)['ops']))
