"""Waikiki's robots (the user, 25 Nov 2026: "Robots should be seen on Waikiki as well, maybe as part of the hotel staff and
security. Whatever is typical for a fallout setting"; docs/waikiki-speech-science.md, "Robots and machines").

The court holds Waikiki's hotels (the concept map), so its robots are the hotels' old staff, kept running: Mister Handy
butlers, bellhops, housekeepers and waiters on the Royal Hawaiian's and the Moana's court floors, Protectron doormen at the
three hotels' fronts and the court's toll post, eyebots over the Kalakaua strip. All in the Kahuna's Court, friendly,
unaggressive. In the ruins, the city's own pre-war machines still at it: security Protectrons holding the American Savings
Bank (a security terminal there shuts them down: terminals.py), a crazed Mister Handy in each of three ruined hotels.
Those keep the game's RobotFaction and attack on sight; they go only where no one else stands. None in Huáng land.

Every robot is a CREA of the mod's own, a copy of the game's (`KINDS`): its script and template dropped, its factions,
aggression and package set here. Every spot is on a navmesh (the mod's, else the game's), clear of doors (`DOOR_CLEAR`),
of anyone standing (`APART`), of idle markers and furniture (`SEAT_CLEAR`); outside, not inside a closed building
(waikikilife.Spots, indoors) and not in another's footprint.

    plan(gd, pr)        {'spots': [...], 'skipped': [...]} where each robot goes and why some don't
    bank_fix_ops(gd, pr) the installed bank terminal's shut-down made KillActor (SetUnconscious isn't in nv-rs by name)
    ops(gd, pr, P)      (ops, report): one Undo; every key taken first (refs that a script names are 'place' ops)
    build(server)       applies it as one Undo, "Waikiki's robots" (pr.apply: server.edit can't file 'place' ops)
"""
import json
import math
import struct

import recordio

LABEL = "Waikiki's robots"
COURT_FACTION = 'FOLabKahunaCourtFaction'
ROBOT_FACTION = 'RobotFaction'
# kind: game CREA copied, editor ID, name, court (else the game's RobotFaction, hostile), aggression, confidence, package
KINDS = {
    'butler': ('REPCONMrHandy', 'FOLabRobotButler', 'Butler Bot', True, 0, 3, 'DefaultSandboxEditorLocation512'),
    'bellhop': ('REPCONMrHandy', 'FOLabRobotBellhop', 'Bellhop Bot', True, 0, 3, 'DefaultSandboxEditorLocation512'),
    'housekeeper': ('REPCONMrHandy', 'FOLabRobotHousekeeper', 'Housekeeping Bot', True, 0, 3, 'DefaultSandboxEditorLocation512'),
    'waiter': ('REPCONMrHandy', 'FOLabRobotWaiter', 'Waiter Bot', True, 0, 3, 'DefaultSandboxEditorLocation512'),
    'doorman': ('VCrTier0CrProtectron', 'FOLabRobotDoorman', 'Court Doorman', True, 0, 4, 'DefaultStayAtEditorLocation'),
    'eyebot': ('SSHQEyebot', 'FOLabRobotCourtEyebot', 'Court Eyebot', True, 0, 2, 'DefaultSandboxEditorLocation1024'),
    'bank_guard': ('VCrTier0CrProtectron', 'FOLabRobotBankSecurity', 'Bank Security', False, 2, 4, 'DefaultWanderEditorLocation512'),
    'crazed': ('CrMisterHandyNV', 'FOLabRobotCrazedBellhop', 'Malfunctioning Bellhop', False, 2, 4, 'DefaultSandboxEditorLocation1024'),
}
# inside: (place editor ID, the robots there). Court floors first, then the ruins (hostile: only where nobody stands).
INSIDE = [
    ('FOLabRoyalHawaiianFloor1', ('butler', 'butler', 'bellhop')),        # The Court
    ('FOLabRoyalHawaiianFloor2', ('doorman',)),                           # The Court's Stores
    ('FOLabRoyalHawaiianFloor3', ('housekeeper',)),                       # The Court's Floor 1
    ('FOLabRoyalHawaiianFloor4', ('housekeeper',)),
    ('FOLabRoyalHawaiianFloor5', ('housekeeper',)),
    ('FOLabRoyalHawaiianFloor6', ('butler', 'doorman')),                  # The Kahuna's Floor
    ('FOLabMoanaFloor1', ('waiter', 'waiter')),                           # Function Rooms
    ('FOLabMoanaFloor2', ('waiter',)),                                    # Kitchens and Service
    ('FOLabMoanaFloor3', ('housekeeper', 'bellhop')),                     # Guest Floor
    ('FOLabMoanaFloor4', ('butler',)),                                    # Top Floor
    ('FOLabWaikikiHouse967', ('bank_guard', 'bank_guard')),               # American Savings Bank
    ('FOLabWaikikiWorks01', ('crazed',)),                                 # Ala Moana Hotel
    ('FOLabWaikikiWorks06', ('crazed',)),                                 # Hilton Garden Inn Waikiki Beach
    ('FOLabWaikikiWorks04', ('crazed',)),                                 # The Ritz-Carlton
]
BANK = 'FOLabWaikikiHouse967'
# outside: (hotel or post, kind, how many, rings searched, the side toward the street (x, y) or None)
OUTSIDE = [('royal_hawaiian', 'doorman', 2, (700, 850, 1000, 1200, 1400), (0.0, 1.0)),
           ('moana', 'doorman', 1, (900, 1100, 1300, 1600), None),
           ('kilauea', 'doorman', 1, (900, 1100, 1300, 1600), None),
           ('toll', 'doorman', 1, (1300, 1500, 1800, 2200), None),
           ('strip', 'eyebot', 2, (300, 500, 700, 900, 1200), None)]
DOOR_CLEAR = 300.0          # (no robot this near a door: its arrival is about there)
APART = 220.0               # (from anyone standing, and from each other)
SEAT_CLEAR = 100.0          # (from beds, chairs and idle markers: people's spots)
MIN_TRI = 1500.0            # (navmesh triangles smaller than this are slivers by walls)
TERMINAL = """Terminal: FOLabBankSecurityTerminal
Name: American Savings Bank Security
Model: desk
Lock: average
Welcome:
  AMERICAN SAVINGS BANK - WAIKIKI BRANCH
  BRANCH SECURITY NETWORK
  Automated guards: ACTIVE
== Shut down the security robots
Script:
  FOLabBankGuard01REF.KillActor
  FOLabBankGuard02REF.KillActor
Says: Security robots powered down.
== Read the last alert
Says:
  ALERT 10-23-2077 09:47
  Lockdown ordered. Staff to evacuate by the rear exit.
  Automated guards hold the floor until relieved.
"""
GUARD_REFS = ('FOLabBankGuard01REF', 'FOLabBankGuard02REF')


def _game(gd, edid, tag):
    from castawayquest import _game_form
    return _game_form(gd, edid, tag)


def _tag(gd, pr, base):
    if base.startswith('+'):
        return (pr.records.get(base) or {}).get('type', '')
    try:
        return gd.forms[gd.from_key(base)][1].tag
    except (KeyError, ValueError):
        return ''


ACTOR_TAGS = ('NPC_', 'CREA', 'LVLN', 'LVLC')


def robot_record(gd, pr, kind):
    """The kind's CREA: the game's robot copied, its script, template and factions dropped, ours set."""
    import api_characters as ac
    import factionfolk as ff
    src, edid, name, court, aggr, conf, package = KINDS[kind]
    f = _game(gd, src, 'CREA')
    rec = recordio.load(gd, f)
    rec['src'] = ''
    rec['copied_from'] = gd.key(f)
    rec['subs'] = [s for s in rec['subs'] if s['tag'] not in ('SCRI', 'TPLT', 'SNAM', 'PKID')]
    recordio.set_field(rec, 'EDID', edid, label='Editor ID')
    if any(s['tag'] == 'FULL' for s in rec['subs']):
        recordio.set_field(rec, 'FULL', name)
    else:
        ac.insert(rec, {'tag': 'FULL', 'label': 'Name', 'kind': 'z', 'value': name})
    fac = ff._mod_key(pr, COURT_FACTION, 'FACT') if court else gd.key(_game(gd, ROBOT_FACTION, 'FACT'))
    if not fac:
        raise ValueError('the mod has no %s (factionfolk first)' % COURT_FACTION)
    ac.insert(rec, ff._set_link(ff._sub('CREA', 'SNAM', struct.pack('<IB3s', 0, 0, b'\0\0\0')), fac))
    ac.insert(rec, {'tag': 'PKID', 'label': 'AI package', 'kind': 'F', 'value': gd.key(ac._find(gd, 'PACK', package))})
    ff._set_num(rec, 'AIDT', 'Aggression', aggr)
    ff._set_num(rec, 'AIDT', 'Confidence', conf)
    ff._set_num(rec, 'AIDT', 'Assistance', 2 if court else 1)
    ff._set_num(rec, 'AIDT', 'Services', 0)
    flags = ff._num(rec, 'ACBS', 'Flags') & ~0x20               # (not unique)
    ff._set_num(rec, 'ACBS', 'Flags', flags)
    return rec


# ---------- spots inside ----------
def _tris(gd, pr, ck):
    import navbuild
    sh = navbuild.shape(gd, pr, ck)
    v, t = sh['verts'], sh['tris']
    out = []
    for i in range(0, len(t), 3):
        a, b, c = [(v[3 * t[i + j]], v[3 * t[i + j] + 1], v[3 * t[i + j] + 2]) for j in range(3)]
        area = abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2
        if area >= MIN_TRI and max(a[2], b[2], c[2]) - min(a[2], b[2], c[2]) < 40:
            out.append(((a[0] + b[0] + c[0]) / 3, (a[1] + b[1] + c[1]) / 3, (a[2] + b[2] + c[2]) / 3))
    return out


_ARRIVE = {}


def arrivals(pr):
    """{door ref key: where its link puts you}: a door's 'tel' gives the arrival at the door it names."""
    got = _ARRIVE.get(id(pr))
    if got is None:
        got = _ARRIVE[id(pr)] = {}
        for c in pr.cells.values():
            for r in (c.get('refs') or {}).values():
                t = r.get('tel')
                if t and t.get('door') and t.get('p') and not r.get('removed'):
                    got[t['door']] = t['p']
    return got


def _things(gd, pr, ck):
    import indoors
    doors, actors, seats = [], [], []
    arrive = arrivals(pr)
    for rk in (pr.cells.get(ck) or {}).get('refs', {}):
        if rk in arrive:
            doors.append(arrive[rk])            # (an arrival counts as a door: nobody stands where you come in)
    for _rk, b, p, _s in indoors.placed(gd, pr, ck):
        t = _tag(gd, pr, b)
        if t == 'DOOR':
            doors.append(p)
        elif t in ACTOR_TAGS:
            actors.append(p)
        elif t in ('FURN', 'IDLM'):
            seats.append(p)
    return doors, actors, seats


def _d(p, q):
    return math.dist(p[:3], q[:3])


def inside_spots(gd, pr, ck, kinds, taken=()):
    """[(kind, (x, y, z, rz), why)] for the robots of one place; [] with the reason when it can't take them."""
    tris = _tris(gd, pr, ck)
    if not tris:
        return [], 'no navmesh'
    doors, actors, seats = _things(gd, pr, ck)
    hostile = any(not KINDS[k][3] for k in kinds)
    if hostile and actors:
        return [], '%d people or creatures stand there already' % len(actors)
    stood = list(taken)
    out = []
    for kind in kinds:
        def ok(p):
            return (min((_d(p, d) for d in doors), default=1e9) >= DOOR_CLEAR and
                    min((_d(p, a) for a in actors + stood), default=1e9) >= APART and
                    min((_d(p, s) for s in seats), default=1e9) >= SEAT_CLEAR)
        free = [p for p in tris if ok(p)]
        if not free:
            break
        near_door = lambda p: min((_d(p, d) for d in doors), default=1e9)
        if kind == 'doorman':
            best = min(free, key=lambda p: (near_door(p), p))                     # (by a door: the floor's way in)
        elif kind in ('bank_guard', 'crazed'):
            best = max(free, key=lambda p: (round(near_door(p) / 200), -p[0], -p[1]))   # (deep in, away from the way in)
        else:
            best = max(free, key=lambda p: (sum(1 for s in seats if _d(p, s) < 512), -near_door(p) // 400, p[0], p[1]))
        face = min(doors, key=lambda d: _d(best, d)) if doors else None
        rz = math.atan2(face[0] - best[0], face[1] - best[1]) if face else 0.0
        out.append((kind, (round(best[0], 1), round(best[1], 1), round(best[2] + 4, 1), round(rz, 4)),
                    {'door': round(near_door(best)), 'person': round(min((_d(best, a) for a in actors), default=1e9)),
                     'seat': round(min((_d(best, s) for s in seats), default=1e9))}))
        stood.append(best)
    return out, '' if len(out) == len(kinds) else 'room for %d of %d' % (len(out), len(kinds))


# ---------- the plan ----------
def _places(pr):
    return {recordio.field(r, 'EDID'): k for k, r in pr.records.items() if r.get('type') == 'CELL' and k.startswith('+')}


def plan(gd, pr):
    import factionfolk as ff
    import waikikilife as WL
    places = _places(pr)
    spots, skipped = [], []
    for edid, kinds in INSIDE:
        ck = places.get(edid)
        if not ck:
            skipped.append((edid, 'not in the mod'))
            continue
        got, why = inside_spots(gd, pr, ck, kinds)
        for kind, p, near in got:
            spots.append({'kind': kind, 'cell': ck, 'place': edid, 'full': recordio.field(pr.records[ck], 'FULL'), 'p': p, 'near': near})
        if why:
            skipped.append((edid, why))
    # outside: factionfolk's search (open ground, on a navmesh, not in a building, clear of anyone standing)
    mk = ff._markers(pr)
    if 'The Royal Hawaiian' not in mk:
        skipped.append(('outside', 'no Royal Hawaiian map marker'))
        return {'spots': spots, 'skipped': skipped}
    world = gd.ext_cells[gd.from_key(mk['The Royal Hawaiian'][0])]
    sp = WL.Spots(gd, pr, world)
    sp.taken = ff._standing(gd, pr)
    sp.gd, sp.pr, sp.grid = gd, pr, gd.grid(world)
    hot, _mid = WL.middle(pr)
    sec = ff._toll_section(gd, pr)
    where = dict((k, tuple(v[:2])) for k, v in hot.items())
    if sec:
        where['toll'] = (sec[0], sec[1])
    if 'royal_hawaiian' in where and 'moana' in where:
        where['strip'] = tuple((a + b) / 2 for a, b in zip(where['royal_hawaiian'], where['moana']))
    doors_out = _outside_doors(gd, pr, sp.grid, where)
    for name, kind, n, radii, side in OUTSIDE:
        if name not in where:
            skipped.append((name, 'not found'))
            continue
        x, y = where[name]
        got = [s for s in ff._near(sp, x, y, n * 4, radii=radii, turns=20, side=side)
               if min((math.hypot(s[0] - d[0], s[1] - d[1]) for d in doors_out), default=1e9) >= DOOR_CLEAR][:n]
        for (px, py, pz, rz) in got:
            ck = gd.key(sp.grid[(int(px // 4096), int(py // 4096))])
            spots.append({'kind': kind, 'cell': ck, 'place': name, 'full': 'outside', 'p': (round(px, 1), round(py, 1), round(pz + 4, 1), round(rz, 4)),
                          'near': {'door': round(min((math.hypot(px - d[0], py - d[1]) for d in doors_out), default=1e9))}})
        if len(got) < n:
            skipped.append((name, 'room for %d of %d' % (len(got), n)))
    return {'spots': spots, 'skipped': skipped, 'world': gd.key(world)}


def _outside_doors(gd, pr, grid, where):
    import indoors
    out = []
    seen = set()
    for x, y in where.values():
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                c = grid.get((int(x // 4096) + dx, int(y // 4096) + dy))
                if c is None or c in seen:
                    continue
                seen.add(c)
                for _rk, b, p, _s in indoors.placed(gd, pr, gd.key(c)):
                    if _tag(gd, pr, b) == 'DOOR':
                        out.append(p)
    return out


# ---------- the ops ----------
def ops(gd, pr, P=None):
    """(ops, report) for one Undo. Refs are 'place' ops with their keys taken first; the bank's terminal comes after."""
    import terminals
    from activity import _Reserve, _new_key
    if any((recordio.field(r, 'EDID') or '') == KINDS['butler'][1] for r in pr.records.values()):
        raise ValueError('the mod already has %s: the robots look done (Undo first)' % KINDS['butler'][1])
    P = P or plan(gd, pr)
    res = _Reserve(pr)
    keys = {}
    for kind in sorted({s['kind'] for s in P['spots']}):
        keys[kind] = res.add(robot_record(gd, pr, kind))
    places = []
    guards = 0
    bank_cell = None
    for s in P['spots']:
        ref = {'base': keys[s['kind']], 'p': [float(v) for v in s['p'][:3]] + [0.0, 0.0, float(s['p'][3])], 's': 1.0}
        if s['kind'] == 'bank_guard' and guards < len(GUARD_REFS):
            ref.update({'persistent': True, 'edid': GUARD_REFS[guards]})
            guards += 1
            bank_cell = s['cell']
        places.append({'op': 'place', 'cell': s['cell'], 'key': _new_key(pr), 'ref': ref})
    out = res.ops + places
    rep = {'records': keys, 'placed': len(places), 'by_kind': {}, 'skipped': P['skipped']}
    for s in P['spots']:
        rep['by_kind'][s['kind']] = rep['by_kind'].get(s['kind'], 0) + 1
    if guards == len(GUARD_REFS) and bank_cell:
        # the bank's security terminal: deep in, clear of the guards; its script names them (stand-ins for the compiler)
        tref = _new_key(pr)
        spot = _terminal_spot(gd, pr, bank_cell, [s['p'] for s in P['spots'] if s['cell'] == bank_cell])
        if spot:
            forms = terminals.mod_forms(gd, pr)
            for pl in places:
                if pl['ref'].get('edid'):
                    forms.own[pl['ref']['edid'].lower()] = (pl['key'], {'type': 'REFR', 'flags': 0x400, 'subs': [
                        {'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': pl['ref']['edid']}]})
            spec = terminals.plan(TERMINAL)
            t_ops, t_keys = terminals.ops(gd, pr, spec, forms)
            out += t_ops
            out.append({'op': 'place', 'cell': bank_cell, 'key': tref,
                        'ref': {'base': t_keys[spec['edid']], 'p': [spot[0], spot[1], spot[2] - 4, 0.0, 0.0, spot[3]], 's': 1.0}})
            rep['terminal'] = {'cell': bank_cell, 'p': spot, 'science': terminals.science_needed(spec)}
        else:
            rep['terminal'] = 'no spot'
    return out, rep


def _terminal_spot(gd, pr, ck, robots):
    got, _why = inside_spots(gd, pr, ck, ('crazed',), taken=[tuple(r[:3]) for r in robots])
    return got[0][1] if got else None


def build(server):
    gd, pr = server.GD, server.PR
    o, rep = ops(gd, pr)
    pr.apply(LABEL, o)                  # (not server.edit: its cell filing takes a 'place' op's ref for a key)
    return rep


def bank_fix_ops(gd, pr):
    """The bank terminal as it stands in a mod, its shut-down by KillActor: SetUnconscious isn't in nv-rs's source by name,
    KillActor is (the robots go down for good, their parts to loot). The record is made again from TERMINAL, same key."""
    import terminals
    key = next((k for k, r in pr.records.items() if r.get('type') == 'TERM' and recordio.field(r, 'EDID') == 'FOLabBankSecurityTerminal'), None)
    if not key:
        return [], 'no bank terminal in the mod'
    rec = pr.records[key]
    if any(s['tag'] == 'SCTX' and b'KillActor' in bytes.fromhex(s['value']) for s in rec['subs'] if s.get('kind') == 'raw'):
        return [], 'already KillActor'
    forms = terminals.mod_forms(gd, pr)
    spec = terminals.plan(TERMINAL)
    made = terminals.records(gd, forms, spec, {spec['edid']: key})
    new = made['terminal']
    new['flags'] = rec.get('flags', 0)
    return [{'op': 'record', 'key': key, 'record': new}], 'made KillActor'


def step(name):
    """A step for skillsteps_into_waikiki.py ('robots:bankfix')."""
    class _BankFix:
        LABEL = 'The bank terminal shuts its robots down by KillActor'

        @staticmethod
        def plan(gd, pr):
            return {'rows': [{'bank terminal': bank_fix_ops(gd, pr)[1]}], 'skipped': []}

        @staticmethod
        def ops(gd, pr, P=None):
            o, said = bank_fix_ops(gd, pr)
            if not o:
                raise ValueError(said)
            return o, {'made': ['FOLabBankSecurityTerminal'], 'said': said}
    return _BankFix
