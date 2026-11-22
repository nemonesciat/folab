"""The hotels planned their own ways: the Royal Hawaiian as the Kahuna's court (hotelcourt: a fortress, every guard post and the
throne room the only way on but for a locked servants' way, one level a floor, the throne at the throne room's far end) and the
Kilauea as a labyrinth (hotelmaze: ways round and stairs within a floor). Both big, every floor walked with everything in it."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata  # noqa: E402
import hotelcourt as HC  # noqa: E402
import hotelfloors as HF  # noqa: E402
import hotelmaze as HM  # noqa: E402
import kitdress  # noqa: E402
import kitplan  # noqa: E402
import project  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


gd = gamedata.GameData()
ks, survey, store, cache = HF.kits(gd)

pr = project.Project.create('Court')
m = HC.make(gd, pr, 1)
floors = m['_floors']
check('the court: six floors, three of them the court\'s quarters', [F.kind for F in floors] == list(HC.KINDS), [F.kind for F in floors])
check('… big floors: at least 12 rooms each', all(len(F.plan.rooms()) >= 12 for F in floors), [len(F.plan.rooms()) for F in floors])
check('… one level a floor, but for a servants\' stair', all(len({c[2] for c in F.plan.squares() if not any(F.plan.owners[F.plan.cells[c]].get('servants') for _ in [0])}) == 1 for F in floors),
      [len({c[2] for c in F.plan.squares()}) for F in floors])
servants = lambda F: [o['n'] for o in F.plan.owners if o.get('servants')]
check('… the fortress holds: guard posts and the throne room are the only way on, but for the servants\' way', all(HC.holds(F.plan, servants(F)) for F in floors))
check('… without that, the servants\' way would go round a guard post: every floor has one', all(servants(F) for F in floors))
check('… every guard post\'s far door is locked, and the servants\' way', all(F.report['gates locked'] >= 1 and F.report["servants' way doors"] >= 1 for F in floors),
      [(F.report['gates locked'], F.report["servants' way doors"]) for F in floors])
court = floors[0]
throne = next(o for o in court.plan.rooms() if o['purpose'] == 'throne room')
check('… the throne stands in the throne room', throne.get('throne') and any(it.key for it in court.items if not it.key.startswith('$') and gd.describe(gd.from_key(it.key))[1] == 'Throne01'))
check('… the lift up is in the Kahuna\'s private room on the court floor and his suite at the top',
      court.plan.owners[court.lift[0].owner]['purpose'] == 'private room' and floors[-1].plan.owners[floors[-1].lift[0].owner]['purpose'] == 'private room')
check('… the top floor\'s lift is on a key that lies on it', floors[-1].report['key in'] is not None)
walked = []
for F in floors:
    w = kitplan.walk_check(gd, F.ts, F.plan, F.made, cache, extra=kitdress.item_refs(gd, [it for it in F.items if not it.key.startswith('$')]))
    walked.append(not w['missing'] and not w['escaped'])
check('… every floor walks from its way in to every square, with its things in', all(walked), walked)
check('… the floors are joined both ways', sum(1 for o in m['ops'] if o['op'] == 'tel') == 2 * (len(floors) - 1))

pr2 = project.Project.create('Maze')
m = HM.make(gd, pr2, 1)
floors = m['_floors']
check('the labyrinth: four floors', len(floors) == 4)
check('… big floors: at least 16 rooms each', all(len(F.plan.rooms()) >= 16 for F in floors), [len(F.plan.rooms()) for F in floors])
check('… stairs within a floor, on most floors', sum(1 for F in floors if len({c[2] for c in F.plan.squares()}) > 2) >= 3, [len({c[2] for c in F.plan.squares()}) for F in floors])
check('… the lift is far in: four rooms or more from the way in, on most floors', sum(1 for F in floors if HC._route(F.plan).get(F.lift[0].owner, 0) >= 4) >= 3,
      [HC._route(F.plan).get(F.lift[0].owner) for F in floors])
check('… some rooms wrecked', sum(F.report['wrecked'] for F in floors) >= 4)
walked = []
for F in floors:
    w = kitplan.walk_check(gd, F.ts, F.plan, F.made, cache, extra=kitdress.item_refs(gd, [it for it in F.items if not it.key.startswith('$')]))
    walked.append(not w['missing'] and not w['escaped'])
check('… every floor walks, with its things in', all(walked), walked)
