"""Terminals in the court district's offices, clinics and security places (docs/waikiki-speech-science.md pick 3, table F;
the user, 25 Nov 2026: "we need many more doors locked behind terminals").

The court district (Waikiki and Kaimukī, west of `COURT_EAST`; the Kāhala and everything east is the pirates' and
others', the concept map) kept its offices and named places as the game lent them. Their locked safes, gun cabinets and
medicine lockers (the loot work's) each get a terminal in the same place that opens them. It's a second way past the
lock, not instead of it: lockpicks still work.
- **Difficulty:** the terminal's lock follows the thing's lock. Up to 50 is the game's "easy" (Science 25, tier 1); over
  50 is "average" (Science 50, tier 3). The game has five hacking levels, so the six tiers fall on the nearest.
- **Words:** pre-war and plain, by the kind of place (`KINDS`): a notice or a log, and "Release ..." for each locked
  thing. Its result script (`<ref>.Unlock`) is proven in nv-rs.
- **Where:** each terminal stands on the place's navmesh, near the first thing it opens, clear of doors and arrivals,
  anyone standing, and seats (robots.inside_spots' rules).
- **The locked things** get an editor ID and are made persistent (`ref_set`), so the script can name them.

    plan(gd, pr)    [{'cell', 'place', 'kind', 'targets': [(ref key, base edid, lock)], 'spot', 'lock'}], skipped
    ops(gd, pr, P)  (ops, report): one Undo
"""
import math
import re

import recordio

LABEL = 'Terminals in the court district'
COURT_EAST = -61440.0           # (cell -15: east of it, the Kāhala's pirates and the lands that pay both)
WANT = re.compile(r'Safe|GunCabinet|FirstAid|Drugs|Hospital|AmmoBox|Footlocker|Locker', re.I)
RANK = ('Safe', 'GunCabinet', 'Drugs', 'Hospital', 'FirstAid', 'AmmoBox', 'Footlocker', 'Locker')
MOST = 2                        # (locked things one terminal opens)
NEAR = (80.0, 900.0)            # (the terminal this near the first thing it opens)
WORD = {'Safe': 'the wall safe', 'GunCabinet': 'the gun cabinet', 'Drugs': 'the drug locker', 'Hospital': 'the medical locker',
        'FirstAid': 'the first aid cabinet', 'AmmoBox': 'the ammunition box', 'Footlocker': 'the footlocker', 'Locker': 'the locker'}
KINDS = {
    'clinic': (re.compile(r'medical|clinic|health|hospital|pharm|dental', re.I), 'PATIENT RECORDS AND PHARMACY',
               ('Pharmacy notice', 'Controlled stock is counted at every shift change. Keys and codes stay with the duty '
                'nurse.\nCivil defence drill moved to Thursday.')),
    'security': (re.compile(r'security|police|guard', re.I), 'SECURITY OFFICE',
                 ('Armoury log', 'Weapons signed out must be signed back in before end of watch.\nAll staff: Condition '
                  'Red procedures are in the binder by the door.')),
    'lab': (re.compile(r'science|laboratory|lab\b|library|school|educat', re.I), 'DEPARTMENT OFFICE',
            ('Department notice', 'Lab keys are not to be lent to students.\nThe shelter in the basement is for staff '
             'and students only.')),
    'apartments': (re.compile(r'apartment|manor|gardens|hale|cove|vista|skyrise|towers|ohua|villa', re.I), "RESIDENT MANAGER'S OFFICE",
                   ('Notice to residents', 'Lanai doors lock at 6 pm. Rent is due on the first.\nResidents are reminded '
                    'that the shelter is two blocks inland.')),
    'office': (re.compile(r'.'), 'TENANT NETWORK',
               ('Building notice', 'Elevator maintenance Tuesday.\nAll tenants: in an alert, leave by the stairs and go '
                'inland. Do not wait for the elevator.')),
}


def _short(s):
    return re.sub(r'[^A-Za-z0-9]', '', s)[:24]


def _base_edid(gd, pr, base):
    if base.startswith('+'):
        return recordio.field(pr.records.get(base) or {'subs': []}, 'EDID') or ''
    try:
        return gd.edid(gd.from_key(base)) or ''
    except (KeyError, ValueError):
        return ''


def _rank(edid):
    return next((n for n, w in enumerate(RANK) if w.lower() in edid.lower()), len(RANK))


def _word(edid):
    return next((WORD[w] for w in RANK if w.lower() in edid.lower()), 'the lock')


def _ways_in(pr):
    """{place key: (x, y) of the outside door leading into it}."""
    import robots
    arrive = robots.arrivals(pr)
    where = {}
    for ck, c in pr.cells.items():
        if not ck.startswith('+'):
            for rk, r in (c.get('refs') or {}).items():
                t = r.get('tel')
                if t and t.get('door') and r.get('p'):
                    where[t['door']] = (r['p'][0], r['p'][1])
    out = {}
    for ck, c in pr.cells.items():
        if ck.startswith('+'):
            for rk in (c.get('refs') or {}):
                if rk in where:
                    out.setdefault(ck, where[rk])
    return out


def kind_of(full):
    return next(k for k, (rx, *_r) in KINDS.items() if rx.search(full or ''))


def plan(gd, pr):
    import robots
    ways = _ways_in(pr)
    out, skipped = [], []
    words = re.compile(r'office|clinic|medical|health|pharm|hospital|security|police|science|library|school', re.I)
    for ck, rec in sorted(pr.records.items()):
        if rec.get('type') != 'CELL' or not ck.startswith('+'):
            continue
        e, full = recordio.field(rec, 'EDID') or '', recordio.field(rec, 'FULL') or ''
        if not (e.startswith('FOLabWaikikiOffices') or words.search(full)) or 'kahala' in full.lower():
            continue
        if ck not in ways or ways[ck][0] >= COURT_EAST:
            skipped.append((e, full, 'outside the court district' if ck in ways else 'no way in from outside'))
            continue
        locked = []
        for rk, r in (pr.cells.get(ck) or {}).get('refs', {}).items():
            lock = (r.get('props') or {}).get('lock')
            if r.get('removed') or not lock or lock.get('level', 0) >= 255 or robots._tag(gd, pr, r.get('base', '')) != 'CONT':
                continue
            be = _base_edid(gd, pr, r['base'])
            if WANT.search(be):
                locked.append((_rank(be), rk, be, int(lock.get('level', 0)), r['p']))
        if not locked:
            continue
        locked.sort(key=lambda t: (t[0], t[1]))
        targets = locked[:MOST]
        spot = _spot(gd, pr, ck, targets[0][4])
        if not spot:
            skipped.append((e, full, 'no clear navmesh spot near the lock'))
            continue
        lvl = max(t[3] for t in targets)
        out.append({'cell': ck, 'place': e, 'full': full, 'kind': kind_of(full),
                    'targets': [(rk, be, lv) for _r, rk, be, lv, _p in targets], 'spot': spot,
                    'lock': 'easy' if lvl <= 50 else 'average', 'way_in': ways[ck]})
    return out, skipped


def _spot(gd, pr, ck, near):
    import robots
    tris = robots._tris(gd, pr, ck)
    doors, actors, seats = robots._things(gd, pr, ck)
    d = robots._d
    free = [p for p in tris if NEAR[0] <= math.dist(p[:2], near[:2]) <= NEAR[1]
            and min((d(p, x) for x in doors), default=1e9) >= robots.DOOR_CLEAR
            and min((d(p, a) for a in actors), default=1e9) >= robots.APART
            and min((d(p, s) for s in seats), default=1e9) >= robots.SEAT_CLEAR]
    if not free:
        return None
    best = min(free, key=lambda p: (math.dist(p[:2], near[:2]), p))
    rz = math.atan2(near[0] - best[0], near[1] - best[1])          # (facing what it opens)
    return (round(best[0], 1), round(best[1], 1), round(best[2], 1), round(rz, 4))


def text_of(row, ref_edids):
    rx, welcome, (title, words) = KINDS[row['kind']]
    name = row['full'] if row['full'] not in ('Offices', '') else 'Building'
    lines = ['Terminal: FOLabTerm%s' % _short(row['place'][len('FOLabWaikiki'):] or row['place']),
             'Name: %s Terminal' % name[:40], 'Model: desk', 'Lock: %s' % row['lock'], 'Welcome:',
             '  %s' % name.upper()[:60], '  %s' % welcome, '== %s' % title, 'Says:']
    lines += ['  ' + l for l in words.split('\n')]
    for (rk, be, lv), ref in zip(row['targets'], ref_edids):
        lines += ['== Release %s' % _word(be), 'Unlocks: %s' % ref, 'Says: %s unlocked.' % _word(be)[4:].capitalize()]
    return '\n'.join(lines) + '\n'


def ops(gd, pr, P=None):
    import terminals
    from activity import _new_key
    if any((recordio.field(r, 'EDID') or '').startswith('FOLabTerm') and r.get('type') == 'TERM' for r in pr.records.values()):
        raise ValueError('the mod has court-district terminals already (Undo first)')
    rows, skipped = P if P else plan(gd, pr)
    out, rep = [], {'terminals': [], 'skipped': skipped}
    names = []
    for row in rows:
        refs = []
        for n, (rk, be, lv) in enumerate(row['targets']):
            e = 'FOLabTermLock%s%dREF' % (_short(row['place'][len('FOLabWaikiki'):]), n + 1)
            refs.append(e)
            names.append((row['cell'], rk, e))
        row['refs'] = refs
    for ck, rk, e in names:
        out.append({'op': 'ref_set', 'cell': ck, 'ref': rk, 'set': {'edid': e, 'persistent': True}})
    forms = terminals.mod_forms(gd, pr)
    for ck, rk, e in names:
        forms.own[e.lower()] = (rk, {'type': 'REFR', 'flags': 0x400, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': e}]})
    places = []
    for row in rows:
        spec = terminals.plan(text_of(row, row['refs']))
        t_ops, t_keys = terminals.ops(gd, pr, spec, forms)
        for o in t_ops:                              # (each key taken now, as reserved: the next terminal's come after)
            k = _new_key(pr)
            assert k == t_keys[recordio.field(o['record'], 'EDID')], (k, o['record'])
            out.append({'op': 'record', 'key': k, 'record': o['record']})
        for e, k in t_keys.items():
            forms.own[e.lower()] = (k, {'type': 'TERM', 'flags': 0, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': e}]})
        x, y, z, rz = row['spot']
        places.append({'op': 'place', 'cell': row['cell'], 'key': None, 'ref': {'base': t_keys[spec['edid']], 'p': [x, y, z, 0.0, 0.0, rz], 's': 1.0}})
        rep['terminals'].append({'place': row['place'], 'name': row['full'], 'kind': row['kind'], 'lock': row['lock'],
                                 'science': terminals.science_needed(spec), 'opens': [be for _rk, be, _lv in row['targets']],
                                 'spot': row['spot']})
    for pl in places:
        pl['key'] = _new_key(pr)
    return out + places, rep
