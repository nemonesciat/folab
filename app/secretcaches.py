"""The four secrets (the user, 25 Nov 2026: "keep all four secrets"; docs/waikiki-speech-science.md table G). Each is a
terminal whose entries say what's decided and point to something you can go and get; its result scripts do it (proven in
nv-rs). One step a site (`SITES`):

- **radar** (pick 6): the radar dome on Waiʻalae Nui (decided: a crashed Vertibird with Vault-Tec delivery papers aboard).
  - A Radar Station Terminal by the wreck, locked average (Science 50): the watch log of the day it came down, the
    delivery manifest to Vault 50 at Kaʻau Crater.
  - "Release the cargo pod seal" opens the undelivered cargo pod beside the wreck.
- **kahunapalms:** the Manager's Terminal in Kahuna Palms' lobby, locked easy (Science 25): staff notices, and the
  penthouse safe's combination. Its item opens the safe, which stands in the penthouse (the tower's small world, by
  the penthouse lift).
- **alewa:** the Wall Watch Terminal at Alewa Fort, locked hard (Science 75). It holds his scouts' reports from past
  the wall, the salvage sent to the ship, and the hint about the guns (decided: he may know the big guns can't fire).
  Its item opens a salvage cache kept back from the ship, stood by the wall.
- **heights:** an Estate Terminal at the Heights, locked average (Science 50): a Vault-Tec reservation letter (decided:
  they paid for places in the Vault and were shut out), and the estate plan's service road to the Vault's back door
  (decided: a back door off the settlers' cliff trail).
  - Its item reveals a map marker at that door (ShowMap; the marker is placed hidden).

Where: terminals and caches on a navmesh (outside, factionfolk's search: open ground, not inside a building, clear of
anyone standing), clear of doors and arrivals (robots.DOOR_CLEAR) and of the crest trail's signposts (`TRAIL_CLEAR`).
Caches are locked "needs a key" with no key: the terminal or a lockpick won't do, only the terminal's script.

    plan(gd, pr, site)    {'rows', 'skipped'}
    ops(gd, pr, P)        (ops, report)
"""
import math

import recordio

TRAIL_POST, TRAIL_CLEAR = 'NVDLC02signPostTall', 300.0
SAFE_LOCK = {'level': 255}
SITES = {
    'radar': {
        'label': "The radar dome's undelivered cargo",
        'anchor': ('ref', 'NVNavarroVertibirdSTATIC', 'Radar Dome', 3000.0),
        'terminal_near': (300, 450, 600, 800), 'cache_near': (250, 350, 450, 600, 800, 1000, 1200),
        'cache': ('FOLabVertibirdCargo', 'Vault-Tec Cargo Pod', 'FOLabFootlocker01MilitaryNVIsland|Footlocker01Military',
                  [('Stimpak', 4), ('RadAway', 2), ('RadX', 2), ('Morphine', 1)]),
        'text': """Terminal: FOLabRadarDomeTerminal
Name: Radar Station Terminal
Model: desk
Lock: average
Welcome:
  WAIALAE NUI RADAR STATION
  AIR WATCH LOG
== Watch log, 10-23-2077
Says:
  Contact: Vertibird, Vault-Tec charter, inbound low over the ridge.
  Contact lost.
  Rescue: none sent. All stations on alert.
== Delivery manifest
Says:
  VAULT-TEC CORPORATION
  Deliver to: VAULT 50, KA'AU CRATER, OAHU
  Contents: medical stores.
  Cargo pod sealed. Release by station code.
== Release the cargo pod seal
Unlocks: {cache}
Says: Cargo pod seal released.
"""},
    'kahunapalms': {
        'label': "Kahuna Palms' penthouse safe",
        'anchor': ('place', 'FOLabKahunaPalmsFloor1'),
        'cache_at': ('ref', 'FOLabKahunaPalmsPenthouseLiftREF', 3720.0, (300.0, 1500.0)),
        'cache': ('FOLabKahunaPalmsPenthouseSafe', 'Penthouse Safe', 'LootSafeFloorOffice', [('Stimpak', 2)]),
        'text': """Terminal: FOLabKahunaPalmsManager
Name: Manager's Terminal
Model: desk
Lock: easy
Welcome:
  KAHUNA PALMS
  MANAGER'S OFFICE
== Notice to staff
Says:
  The tower closes to guests today. Staff to the shelters.
  Lock the front doors behind you.
== Penthouse safe
Says:
  Combination kept here for the penthouse guest. Do not give it out.
== Release the penthouse safe
Unlocks: {cache}
Says: Penthouse safe unlocked.
"""},
    'alewa': {
        'label': "Alewa Fort's salvage cache",
        'anchor': ('marker', 'Alewa Fort'),
        'terminal_near': (300, 450, 600, 800), 'cache_by': ('NVMcCarranWall', (200, 300, 400, 550)),
        'cache': ('FOLabAlewaSalvageCache', 'Salvage Cache', 'FOLabFootlocker01MilitaryNVIsland|Footlocker01Military',
                  [('Ammo556mm', 60), ('Stimpak', 2)]),
        'text': """Terminal: FOLabAlewaWallWatch
Name: Wall Watch Terminal
Model: desk
Lock: hard
Welcome:
  ALEWA FORT
  WALL WATCH
== Scouts' reports
Says:
  Past the wall: ruins, quiet by day. Nothing moves that we want to meet by night.
  Salvage brought in: plating, cable, rounds. Sent to the ship.
== The big guns
Says:
  Asked the ship again for shells for the big guns. None sent.
  None ever asked for, either. Make of that what you like.
== Kept back
Says:
  Not everything goes to the ship. A cache by the wall, on our side.
== Release the salvage cache
Unlocks: {cache}
Says: Salvage cache unlocked.
"""},
    'heights': {
        'label': "The Heights' estate plan",
        'anchor': ('marker', 'The Heights'),
        'terminal_near': (300, 450, 600, 800),
        'reveal': ('CaveDoor01', "Ka'au Crater", 30000.0, 'FOLabVaultServiceDoorMarker', 'Vault Service Door'),
        'text': """Terminal: FOLabHeightsEstate
Name: Estate Terminal
Model: desk
Lock: average
Welcome:
  THE HEIGHTS
  ESTATE OFFICE
== Letter from Vault-Tec
Says:
  Dear resident,
  Your family's place in Vault 50 is assured. When the sirens sound, go to Ka'au Crater.
  Thank you for choosing Vault-Tec.
== Estate plan: utility easement
Script: ShowMap FOLabVaultServiceDoorMarker
Says:
  Service road: from the ridge to the Ka'au facility's service door, north face.
  Marked on your map.
"""},
}


def _mod_key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and recordio.field(r, 'EDID') == edid), None)


def _ed(gd, pr, b):
    if b.startswith('+'):
        return recordio.field(pr.records[b], 'EDID') if b in pr.records else ''
    try:
        return gd.edid(gd.from_key(b)) or ''
    except (KeyError, ValueError):
        return ''


def _game(gd, edid, tag):
    from castawayquest import _game_form
    return _game_form(gd, edid, tag)


def _outside_refs(gd, pr, pred):
    for ck, c in pr.cells.items():
        if ck.startswith('+'):
            continue
        for rk, r in (c.get('refs') or {}).items():
            if not r.get('removed') and r.get('p') and pred(r):
                yield ck, rk, r


def _spots_for(gd, pr, world):
    import factionfolk as ff
    import waikikilife as WL
    sp = WL.Spots(gd, pr, gd.from_key(world) if isinstance(world, str) else world)
    sp.taken = ff._standing(gd, pr)
    sp.gd, sp.pr, sp.grid = gd, pr, gd.grid(gd.from_key(world) if isinstance(world, str) else world)
    return sp


def _clear(gd, pr, sp, x, y, doors, posts):
    import robots
    return (min((math.hypot(x - d[0], y - d[1]) for d in doors), default=1e9) >= robots.DOOR_CLEAR and
            min((math.hypot(x - p[0], y - p[1]) for p in posts), default=1e9) >= TRAIL_CLEAR)


def _outside(gd, pr, sp, x0, y0, radii, doors, posts, avoid=()):
    import factionfolk as ff
    for s in ff._near(sp, x0, y0, 12, radii=radii, turns=16):
        if _clear(gd, pr, sp, s[0], s[1], doors, posts) and all(math.hypot(s[0] - a[0], s[1] - a[1]) >= 200 for a in avoid):
            return (round(s[0], 1), round(s[1], 1), round(s[2], 1), round(s[3] + math.pi, 4)), {
                'door': round(min((math.hypot(s[0] - d[0], s[1] - d[1]) for d in doors), default=1e9)),
                'trail': round(min((math.hypot(s[0] - p[0], s[1] - p[1]) for p in posts), default=1e9))}
    return None, None


def plan(gd, pr, site):
    import factionfolk as ff
    import robots
    S = SITES[site]
    rows, skipped = [], []
    mk = ff._markers(pr)
    posts = [r['p'] for _c, _k, r in _outside_refs(gd, pr, lambda r: _ed(gd, pr, r.get('base', '')) == TRAIL_POST)]
    kind = S['anchor'][0]
    if kind == 'place':
        ck = next((k for k, r in pr.records.items() if r.get('type') == 'CELL' and recordio.field(r, 'EDID') == S['anchor'][1]), None)
        if not ck:
            return {'rows': [], 'skipped': [(site, S['anchor'][1] + ' not in the mod')]}
        doors, actors, seats = robots._things(gd, pr, ck)
        desks = [r['p'] for r in pr.cells[ck]['refs'].values() if not r.get('removed') and r.get('p') and 'desk' in _ed(gd, pr, r.get('base', '')).lower()]
        near = max(desks, key=lambda p: min((robots._d(p, d) for d in doors), default=0)) if desks else None
        got, why = robots.inside_spots(gd, pr, ck, ('butler',))
        if near:
            tris = robots._tris(gd, pr, ck)
            free = [p for p in tris if 80 <= math.dist(p[:2], near[:2]) <= 600
                    and min((robots._d(p, d) for d in doors), default=1e9) >= robots.DOOR_CLEAR
                    and min((robots._d(p, a) for a in actors), default=1e9) >= robots.APART
                    and min((robots._d(p, s) for s in seats), default=1e9) >= robots.SEAT_CLEAR]
            if free:
                b = min(free, key=lambda p: (math.dist(p[:2], near[:2]), p))
                got = [('t', (round(b[0], 1), round(b[1], 1), round(b[2] + 4, 1), round(math.atan2(near[0] - b[0], near[1] - b[1]), 4)), {'by the desk': True})]
        if not got:
            return {'rows': [], 'skipped': [(site, why or 'no spot')]}
        rows.append({'what': 'terminal', 'cell': ck, 'p': got[0][1], 'near': got[0][2]})
    else:
        if kind == 'marker':
            if S['anchor'][1] not in mk:
                return {'rows': [], 'skipped': [(site, 'no map marker ' + S['anchor'][1])]}
            ack, ap = mk[S['anchor'][1]]
        else:
            _k, edid, marker, reach = S['anchor']
            if marker not in mk:
                return {'rows': [], 'skipped': [(site, 'no map marker ' + marker)]}
            mx, my = mk[marker][1][:2]
            refs = sorted(_outside_refs(gd, pr, lambda r: _ed(gd, pr, r.get('base', '')) == edid),
                          key=lambda t: math.hypot(t[2]['p'][0] - mx, t[2]['p'][1] - my))
            if not refs or math.hypot(refs[0][2]['p'][0] - mx, refs[0][2]['p'][1] - my) > reach:
                return {'rows': [], 'skipped': [(site, 'no %s near %s' % (edid, marker))]}
            ack, ap = refs[0][0], refs[0][2]['p']
        world = gd.key(gd.ext_cells[gd.from_key(ack)])
        sp = _spots_for(gd, pr, world)
        doors = robots._outside_doors(gd, pr, sp.grid, {'a': (ap[0], ap[1])})
        tp, tn = _outside(gd, pr, sp, ap[0], ap[1], S['terminal_near'], doors, posts)
        if not tp:
            return {'rows': [], 'skipped': [(site, 'no clear spot for the terminal')]}
        rows.append({'what': 'terminal', 'world': world, 'p': tp, 'near': tn})
        if 'cache_near' in S:
            cp, cn = _outside(gd, pr, sp, ap[0], ap[1], S['cache_near'], doors, posts, avoid=[tp])
            (rows.append({'what': 'cache', 'world': world, 'p': cp, 'near': cn}) if cp else skipped.append((site, 'no spot for the cache')))
        if 'cache_by' in S:
            word, radii = S['cache_by']
            walls = sorted(_outside_refs(gd, pr, lambda r: _ed(gd, pr, r.get('base', '')).startswith(word)),
                           key=lambda t: math.hypot(t[2]['p'][0] - ap[0], t[2]['p'][1] - ap[1]))
            if walls:
                wp = walls[0][2]['p']
                # (on the fort's side of the wall: of the spots round the wall piece, the nearest the fort)
                import factionfolk as ff2
                cands = [s for s in ff2._near(sp, wp[0], wp[1], 12, radii=radii, turns=16)
                         if _clear(gd, pr, sp, s[0], s[1], doors, posts) and math.hypot(s[0] - tp[0], s[1] - tp[1]) >= 200]
                if cands:
                    s = min(cands, key=lambda s: math.hypot(s[0] - ap[0], s[1] - ap[1]))
                    rows.append({'what': 'cache', 'world': world, 'p': (round(s[0], 1), round(s[1], 1), round(s[2], 1), round(s[3], 4)),
                                 'near': {'wall': round(math.hypot(s[0] - wp[0], s[1] - wp[1])), 'fort': round(math.hypot(s[0] - ap[0], s[1] - ap[1]))}})
            if not any(r['what'] == 'cache' for r in rows):
                skipped.append((site, 'no spot for the cache by the wall'))
        if 'reveal' in S:
            edid, marker, reach, medid, mname = S['reveal']
            if marker in mk:
                kx, ky = mk[marker][1][:2]
                doors2 = sorted(_outside_refs(gd, pr, lambda r: _ed(gd, pr, r.get('base', '')) == edid and bool(r.get('tel'))),
                                key=lambda t: math.hypot(t[2]['p'][0] - kx, t[2]['p'][1] - ky))
                if doors2 and math.hypot(doors2[0][2]['p'][0] - kx, doors2[0][2]['p'][1] - ky) <= reach:
                    dck, _drk, dr = doors2[0]
                    rows.append({'what': 'marker', 'cell': dck, 'p': tuple(round(v, 1) for v in dr['p'][:3]), 'type': mk[marker] and _marker_type(pr, marker)})
            if not any(r['what'] == 'marker' for r in rows):
                skipped.append((site, 'the Vault\'s back door not found'))
    if 'cache_at' in S:
        _k, ref_edid, z, (lo, hi) = S['cache_at']
        hit = next(((ck, rk, r) for ck, c in pr.cells.items() for rk, r in (c.get('refs') or {}).items() if r.get('edid') == ref_edid), None)
        if hit:
            ck, _rk, r = hit
            tris = robots._tris(gd, pr, ck)
            free = [p for p in tris if lo <= math.dist(p[:2], r['p'][:2]) <= hi and abs(p[2] - z) < 150]
            doors, actors, seats = robots._things(gd, pr, ck)
            free = [p for p in free if min((robots._d(p, d) for d in doors), default=1e9) >= robots.DOOR_CLEAR
                    and min((robots._d(p, a) for a in actors), default=1e9) >= robots.APART
                    and min((robots._d(p, s) for s in seats), default=1e9) >= robots.SEAT_CLEAR]
            if free:
                b = min(free, key=lambda p: (math.dist(p[:2], r['p'][:2]), p))
                rows.append({'what': 'cache', 'cell': ck, 'p': (round(b[0], 1), round(b[1], 1), round(b[2], 1), 0.0),
                             'near': {'lift': round(math.dist(b[:2], r['p'][:2]))}})
        if not any(row['what'] == 'cache' for row in rows):
            skipped.append((site, 'no navmesh spot in the penthouse for the safe'))
    return {'rows': rows, 'skipped': skipped, 'site': site}


def _marker_type(pr, name):
    for c in pr.cells.values():
        for r in (c.get('refs') or {}).values():
            m = r.get('marker')
            if isinstance(m, dict) and m.get('name') == name:
                return m.get('type', 0)
    return 0


def _cache_record(gd, pr, edid, name, src, items):
    import factionfolk as ff
    import api_characters as ac
    import struct
    rec = None
    for one in src.split('|'):                    # (the mod's island look first, else the game's)
        k = _mod_key(pr, one, 'CONT')
        if k:
            rec = __import__('json').loads(__import__('json').dumps(pr.records[k]))
            break
        try:
            rec = recordio.load(gd, _game(gd, one, 'CONT'))
            break
        except ValueError:
            continue
    if rec is None:
        raise ValueError('no container to copy for %s (%s)' % (edid, src))
    rec['src'] = ''
    recordio.set_field(rec, 'EDID', edid, label='Editor ID')
    recordio.set_field(rec, 'FULL', name) if any(s['tag'] == 'FULL' for s in rec['subs']) else \
        ac.insert(rec, {'tag': 'FULL', 'label': 'Name', 'kind': 'z', 'value': name})
    have = []
    for item, n in items:
        f = next((gd.key(f) for f, (i, r) in gd.forms.items() if gd.edid(f) == item and r.tag in ('ALCH', 'AMMO', 'MISC', 'WEAP', 'ARMO', 'LVLI')), None) \
            or _mod_key(pr, item)
        if f:
            s = ff._sub('CONT', 'CNTO', struct.pack('<Ii', 0, n))
            ff._set_link(s, f)
            ac.insert(rec, s)
            have.append(item)
    return rec, have


def ops(gd, pr, P):
    import terminals
    from activity import _new_key
    site = P['site']
    S = SITES[site]
    text = S['text']
    if any(recordio.field(r, 'EDID') == text.split('\n')[0].split(': ')[1] for r in pr.records.values()):
        raise ValueError('the mod already has this terminal (Undo first)')
    rows = {r['what']: r for r in P['rows']}
    if 'terminal' not in rows or ('cache' in S and 'cache' not in rows) or ('reveal' in S and 'marker' not in rows):
        raise ValueError('%s: the plan is short: %s' % (site, P['skipped']))
    grid = lambda w: gd.grid(gd.from_key(w))
    cell_of = lambda row: row.get('cell') or gd.key(grid(row['world'])[(int(row['p'][0] // 4096), int(row['p'][1] // 4096))])
    out, rep = [], {'made': [], 'site': site, 'skipped': P['skipped']}
    forms = terminals.mod_forms(gd, pr)
    cache_ref = None
    if 'cache' in S:
        edid, name, src, items = S['cache']
        rec, have = _cache_record(gd, pr, edid, name, src, items)
        ck = _new_key(pr)
        out.append({'op': 'record', 'key': ck, 'record': rec})
        cache_ref = edid + 'REF'
        rk = _new_key(pr)
        x, y, z, rz = rows['cache']['p']
        out.append({'op': 'place', 'cell': cell_of(rows['cache']), 'key': rk,
                    'ref': {'base': ck, 'p': [x, y, z, 0.0, 0.0, rz], 's': 1.0, 'persistent': True, 'edid': cache_ref,
                            'props': {'lock': dict(SAFE_LOCK)}}})
        forms.own[cache_ref.lower()] = (rk, {'type': 'REFR', 'flags': 0x400, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': cache_ref}]})
        rep['made'].append(edid)
        rep['cache'] = {'p': rows['cache']['p'], 'near': rows['cache'].get('near'), 'items': have}
    if 'reveal' in S:
        _e, _m, _r, medid, mname = S['reveal']
        mk = _new_key(pr)
        x, y, z = rows['marker']['p']
        out.append({'op': 'place', 'cell': rows['marker']['cell'], 'key': mk,
                    'ref': {'base': 'FalloutNV.esm:000010', 'p': [x, y, z, 0.0, 0.0, 0.0], 's': 1.0, 'persistent': True, 'edid': medid,
                            'marker': {'name': mname, 'type': rows['marker'].get('type', 0), 'flags': 2}}})
        forms.own[medid.lower()] = (mk, {'type': 'REFR', 'flags': 0x400, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': medid}]})
        was = forms.is_map_marker                 # (ShowMap wants a map marker: the compiler is told this one is)
        forms.is_map_marker = lambda f, was=was: (f.rec is not None and recordio.field(f.rec, 'EDID') == medid) or was(f)
        rep['made'].append(medid)
        rep['marker'] = rows['marker']['p']
    spec = terminals.plan(text.replace('{cache}', cache_ref or ''))
    t_ops, t_keys = terminals.ops(gd, pr, spec, forms)
    for o in t_ops:
        k = _new_key(pr)
        assert k == t_keys[recordio.field(o['record'], 'EDID')]
        out.append({'op': 'record', 'key': k, 'record': o['record']})
    x, y, z, rz = rows['terminal']['p']
    out.append({'op': 'place', 'cell': cell_of(rows['terminal']), 'key': _new_key(pr),
                'ref': {'base': t_keys[spec['edid']], 'p': [x, y, z - 4, 0.0, 0.0, rz], 's': 1.0}})
    rep['terminals'] = [{'edid': spec['edid'], 'science': terminals.science_needed(spec), 'p': rows['terminal']['p'],
                         'near': rows['terminal'].get('near')}]
    rep['made'].append(spec['edid'])
    return out, rep


def step(site):
    """A module-like object for skillsteps_into_waikiki.py: plan, ops, LABEL for one site."""
    class _Step:
        LABEL = SITES[site]['label']

        @staticmethod
        def plan(gd, pr):
            return plan(gd, pr, site)

        @staticmethod
        def ops(gd, pr, P=None):
            return ops(gd, pr, P or plan(gd, pr, site))
    return _Step
