"""A hotel's floors (hotelfloors): each of the three hotels builds its floors from its kit, every floor walks from its way
in to every square with everything stood in it, the floors are joined by their doors both ways (the lift up to the next
floor's way in and back), the way in from the lobby and the lift to the penthouse are left for the lobby to link, the
penthouse lift is locked on a key of the mod's own that lies on the top floor, there is something to find and locks on
every floor, nothing comes from an add-on but the kit's own file and nothing has a script but a bed's or a workbench's;
and for one hotel the navmeshes are made and the floors populated, nobody hostile near a door you arrive by."""
import collections
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata  # noqa: E402
import hotelfloors as HF  # noqa: E402
import kitdress  # noqa: E402
import kitplan  # noqa: E402
import project  # noqa: E402
import recordio  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


gd = gamedata.GameData()
pr = project.Project.create('Hotels')
layouts = {}
for hotel, H in HF.HOTELS.items():
    if H['kit'] not in HF.kits(gd)[0]:
        print('SKIP %s: these game files lack its kit' % hotel)
        continue
    m = HF.make(gd, pr, hotel, seed=1)
    n = len(H['floors'])
    check('%s: a place for each of its %d floors' % (hotel, n), len(m['places']) == n and len(m['_floors']) == n, m['places'])
    rows = m['report']
    check('%s: every floor has rooms, something to find and a lock' % hotel,
          all(r['rooms'] and r['finds'] >= 1 and r['locked rooms'] + r['locked finds'] >= 1 for r in rows),
          [(r['kind'], r['finds'], r['locked rooms'], r['locked finds']) for r in rows])
    check('%s: the top floor\'s lift is locked on the penthouse key, which lies on that floor' % hotel, rows[-1]['key in'] is not None, rows[-1]['key in'])
    # (everything still walks with all of it stood in it)
    ks, survey, store, cache = HF.kits(gd)
    walked = []
    for F in m['_floors']:
        w = kitplan.walk_check(gd, F.ts, F.plan, F.made, cache, extra=kitdress.item_refs(gd, [it for it in F.items if not it.key.startswith('$')]))
        walked.append(not w['missing'] and not w['escaped'])
    check('%s: every floor walks from its way in to every square, with its things in' % hotel, all(walked), walked)
    files, scripted = set(), collections.Counter()
    for o in m['ops']:
        if o['op'] == 'add' and not o['base'].startswith('$'):
            f = gd.from_key(o['base'])
            files.add(gd.names[f >> 24])
            if 'SCRI' in gd.fields(f) and HF._script_of(gd, f) not in HF.HARMLESS:
                scripted[gd.edid(f)] += 1
    kit_files = {gd.names[gd.from_key(mm.key) >> 24] for F in m['_floors'] for mm in F.made}
    check('%s: nothing from an add-on but its kit\'s own file' % hotel, files <= kit_files | {'falloutnv.esm'}, sorted(files))
    check('%s: nothing with a script of its own place\'s' % hotel, not scripted, scripted.most_common(5))
    tels = [o for o in m['ops'] if o['op'] == 'tel']
    check('%s: the floors are joined both ways' % hotel, len(tels) == 2 * (n - 1), len(tels))
    layouts[hotel] = [r['seed'] for r in rows]
    pr.apply('floors ' + hotel, m['ops'])
    names = dict(pr.names)
    cells = [names.get(p) for p in m['places']]
    check('%s: each floor is a place of the mod\'s own, named for the hotel' % hotel,
          all(c and pr.records.get(c, {}).get('type') == 'CELL' and H['label'] in (recordio.field(pr.records[c], 'FULL') or '') for c in cells))
    door = lambda place, d: pr.cells[names[place]]['refs'].get(names.get(d))
    ok = True
    for a, b in zip(m['places'], m['places'][1:]):
        up, down = door(a, a + '_up'), door(b, b + '_in')
        ok = ok and up and down and up['tel']['door'] == names[b + '_in'] and down['tel']['door'] == names[a + '_up']
    check('%s: each lift leads to the next floor\'s way in, and that back to it' % hotel, ok)
    e, t = m['entry'], m['top']
    entry, top = door(e['place'], e['door']), door(t['place'], t['door'])
    check('%s: the way in from the lobby and the lift to the penthouse are there, leading nowhere yet' % hotel,
          entry is not None and top is not None and not entry.get('tel') and not top.get('tel') and entry.get('persistent') and top.get('persistent'))
    key = names.get(m['key'])
    lock = ((top or {}).get('props') or {}).get('lock') or {}
    keys = [r for r in pr.cells[names[t['place']]]['refs'].values() if r.get('base') == key]
    check('%s: the penthouse key is a record of the mod\'s own, the lift\'s lock names it, and it lies on the top floor' % hotel,
          key and pr.records[key]['type'] == 'KEYM' and lock.get('key') == key and lock.get('level') == 255 and len(keys) == 1, (key, lock, len(keys)))
    if hotel == 'royal_hawaiian':
        nav, rep = HF.navmesh_ops(gd, pr, m, names)
        check('the Royal Hawaiian: a navmesh for every floor', len(nav) == n, {k: (v if isinstance(v, str) else 'ok') for k, v in rep.items()})
        pr.apply('navmeshes', nav, merge=True)
        ppl, rep = HF.people_ops(gd, pr, m, names)
        placed = {k: (v['placed'] if isinstance(v, dict) else 0) for k, v in rep.items()}
        check('the Royal Hawaiian: every floor is held by someone, more higher up', all(placed.values()) and placed[m['places'][-1]] >= placed[m['places'][0]], placed)
        near = 0
        for o in ppl:
            if o.get('op') != 'add':
                continue
            place = next(p for p in m['places'] if names[p] == o['cell'])
            for spot in m['arrive'][place].values():
                if math.dist(o['p'][:2], spot[:2]) < HF.KEEP_CLEAR - 1 and abs(o['p'][2] - spot[2]) < 200:
                    near += 1
        check('the Royal Hawaiian: nobody stands near a door you arrive by', near == 0, near)
        pr.apply('people', ppl, merge=True)
check('each hotel\'s floors are its own, not another\'s', len({tuple(v) for v in layouts.values()}) == len(layouts), layouts)
