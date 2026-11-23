"""Who is aboard the big ships and what is locked (the user's answers, 22 Nov 2026, docs/waikiki-decisions.md), laid over
the places flotillainside.py made, as they stand in the mod:

The Flotilla's ship, hostile ground, a dungeon:
    pirates       the mod's own (peopledress), by room (`CREW`), on the places' navmeshes
    the store     the quartermaster's store below decks locked (its door off the passage, and the ladderway between it and
                  the house, both sides): the key is on the Quartermaster, who sits in the house's card room
    the pens      the after end made cells of the game's jail bars (`CELLS`), a barred door each, locked, their key on the
                  pens' guard; captives inside (`CAPTIVES`), in the game's FiendFriendFaction so the pirates (Fiends by
                  faction) leave them be. They do nothing when let out but wander: what they should do is the user's
    the captain   one of the Flotilla's own, in the captain's cabin: a copy of the mod's pirate in the Officer's Coat with
                  a Pip-Boy as the three Pirate Captains wear: Captain Iolana "Io" Kanahele, the user's name for her
    loot          by depth, lootplace's way (`BANDS`: the house and boats easy, below decks middling, the hold, pens and
                  store hard): empty containers filled, boxes locked, finds against the store's and the hold's walls

The settlers' freighter, open to a stranger:
    the elders    the three Zhanglao taken off her deck and put in her house (mess, mess, master's cabin)
    the hold      locked (needs its key): the house's ladderway and the deck hatch, both sides. The key is on the elder
                  in the master's cabin (the user, 22 Nov 2026: taken from the body or picked from the pocket)
    owned         both places the Huang's (the cell's owner), so taking is stealing

`ops(gd, pr, captain_name)` -> (ops, report), then `navmesh_ops` for the pens (its cells are new walls). One Undo by the
caller. Nothing here is seen in game."""
import json
import math
import struct

import recordio
import factionfolk as FF
import lootplace
import peopledress

S = 256.0
CAPTAIN_EDID, QM_EDID, GUARD_EDID = 'FOLabFlotillaCaptain', 'FOLabFlotillaQuartermaster', 'FOLabFlotillaPenGuard'
CAPTAIN_NAME = 'Captain Iolana "Io" Kanahele'   # (the user's, 22 Nov 2026: a woman)
CAPTAIN_FROM = 'FOLabPirateVJackalGangSpawnFemale'      # (the mod's pirate who is a woman)
STORE_KEY = ('FOLabFlotillaStoreKey', "Quartermaster's Store Key")
PENS_KEY = ('FOLabFlotillaPensKey', 'Pens Key')
HOLD_KEY = ('FOLabFreighterHoldKey', 'Freighter Hold Key')
PIRATE = 'FOLabPirateLvlFiend2GunVarNV'
PIRATES = ('FOLabPirateLvlFiend2GunVarNV', 'FOLabPirateLvlFiend2RifleVarNV', 'FOLabPirateLvlFiend2MeleeVarNV', 'FOLabPirateLvlRaider1GunVar',
           'FOLabPirateLvlRaider1MeleeVar', 'FOLabPirateVViperGangSpawnGunA', 'FOLabPirateVJackalGangSpawnMale', 'FOLabPirateVJackalGangSpawnFemale')
CAPTAIN_WEAR = ('FOLabOfficersCoat', 'PipBoyNPC')
PLACES = {'house': 'FOLabFlotillaHouse', 'below': 'FOLabFlotillaBelowDecks', 'hold': 'FOLabFlotillaHold', 'pens': 'FOLabFlotillaPens',
          'boat1': 'FOLabFlotillaBoatForward', 'boat2': 'FOLabFlotillaBoatAft', 's_house': 'FOLabFreighterHouse', 's_hold': 'FOLabFreighterHold'}
# rooms as flotillainside lays them: (i0, j0, squares across, squares along), on the kit's 256-unit squares
ROOMS = {'house': {'mess': (1, -7, 3, 4), 'galley': (1, -3, 3, 3), 'cards': (1, 0, 3, 3), 'cabin': (1, 3, 3, 5), 'hall': (0, -6, 1, 12)},
         'below': {'berth1': (1, -8, 3, 4), 'store': (1, -4, 3, 3), 'brig': (1, -1, 3, 3), 'still': (1, 2, 3, 3), 'berth2': (1, 5, 3, 4), 'hall': (0, -7, 1, 14)},
         'hold': {'hold': (-2, -4, 5, 8)}, 'pens': {'front': (-2, -3, 5, 3)},
         'boat1': {'cabin': (-1, -2, 3, 4)}, 'boat2': {'cabin': (-1, -2, 3, 4)},
         's_house': {'mess': (1, -6, 3, 4), 'cabin': (1, 4, 3, 3)}, 's_hold': {'hold': (-2, -4, 5, 8)}}
# pirates by room: how many
CREW = {'house': {'mess': 2, 'galley': 1, 'hall': 1}, 'below': {'berth1': 2, 'still': 1, 'berth2': 2, 'hall': 1}, 'hold': {'hold': 3},
        'pens': {'front': 1}, 'boat1': {'cabin': 2}, 'boat2': {'cabin': 1}}
APART = 150.0               # (people this far from each other)
BANDS = {'house': 0, 'boat1': 0, 'boat2': 0, 'below': 1, 'hold': 2, 'pens': 2}
LOOT_NAMES = {'house': 'house', 'below': 'fort', 'hold': 'hold', 'pens': 'pens', 'boat1': 'boat', 'boat2': 'boat'}   # (lootplace.place_kind: below decks as a held place)
FINDS = {('below', 'store'): ['guns', 'ammo', 'military', 'medicine', 'explosives'], ('hold', 'hold'): ['bag', 'food', 'ammo', 'safe']}
# the pens' cells, in the place's own frame (the room: x -640..640, y -896..640): bars across at BARS_Y, panels 256 long
BARS_Y = 128.0
PANELS = [(-512.0, 'JailCellMid01'), (-256.0, 'JailCellDoorway01'), (0.0, 'JailCellDoorway01'), (256.0, 'JailCellDoorway01'), (512.0, 'JailCellMid01')]
DIVIDERS = [(-128.0, 256.0), (-128.0, 512.0), (128.0, 256.0), (128.0, 512.0)]
JAIL_DOOR = 'JailDoor01'    # (the game hangs it at the doorway piece's own spot and turn: FreesideMickandRalphs)
CELL_LOCK = 50
CAPTIVES = [(-460.0, 330.0, 2.6), (-300.0, 500.0, 3.4), (0.0, 420.0, 3.14), (300.0, 500.0, 2.9), (460.0, 330.0, 3.7)]
MATTRESSES = [(-430.0, 540.0, 1.57), (0.0, 560.0, 1.57), (430.0, 540.0, 1.57)]
CAPTIVE = {'name': 'Captive', 'races': ('Hispanic', 'Asian', 'Caucasian', 'AfricanAmerican'), 'sexes': 'MFMFM', 'level': 2, 'aggression': 0,
           'confidence': 0, 'faction': '', 'package': FF.SANDBOX}
CAPTIVE_FACTION = 'FiendFriendFaction'      # (the game's: the Fiends' faction holds it a friend)
CAPTIVE_WEAR = ('FOLabSurferBodyList', 'OutfitNVSlave1')     # (the first there is: as the island's people dress, else the game's rags)
ELDERS = [('mess', 0), ('mess', 1), ('cabin', 0)]
NEEDS_KEY = 255


def _rect(room):
    i0, j0, w, h = room
    return (i0 - 0.5) * S, (j0 - 0.5) * S, (i0 + w - 0.5) * S, (j0 + h - 0.5) * S


def places(pr):
    """{key: the place's cell key} of the ships' places the mod has."""
    by = {recordio.field(r, 'EDID'): k for k, r in pr.records.items() if r.get('type') == 'CELL'}
    return {k: by[e] for k, e in PLACES.items() if e in by}


def _door(pr, ck, x, y, tol=8.0):
    for rk, r in pr.cells[ck]['refs'].items():
        p = r.get('p')
        if p and not r.get('removed') and abs(p[0] - x) < tol and abs(p[1] - y) < tol and abs(p[2]) < 20:
            return rk
    raise ValueError('no door at %d, %d in %s' % (x, y, ck))


def _tris(pr, ck):
    nav = pr.navmesh.get(ck) or {}
    V = nav.get('verts') or []
    return [(V[t[0]], V[t[1]], V[t[2]]) for t in nav.get('tris') or []]


def _under(tris, x, y):
    """The navmesh's height under (x, y), or None."""
    for a, b, c in tris:
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if not d:
            continue
        l1 = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / d
        l2 = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / d
        l3 = 1 - l1 - l2
        if min(l1, l2, l3) >= -0.01:
            return l1 * a[2] + l2 * b[2] + l3 * c[2]
    return None


def spots(tris, rect, n, taken, doors=(), clear=170.0):
    """n places to stand in a room: middles of its navmesh's biggest triangles, APART from each other, off its doorways."""
    x0, y0, x1, y1 = rect
    got = []
    cand = []
    for a, b, c in tris:
        mx, my, mz = (a[0] + b[0] + c[0]) / 3, (a[1] + b[1] + c[1]) / 3, (a[2] + b[2] + c[2]) / 3
        if not (x0 + 40 < mx < x1 - 40 and y0 + 40 < my < y1 - 40):
            continue
        area = abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2
        cand.append((-area, mx, my, mz))
    for _a, mx, my, mz in sorted(cand):
        if len(got) >= n:
            break
        if any(math.hypot(mx - d[0], my - d[1]) < clear for d in doors):
            continue
        if any(math.hypot(mx - t[0], my - t[1]) < APART for t in taken):
            continue
        taken.append((mx, my))
        got.append((mx, my, mz))
    return got


def _copy_pirate(gd, pr, edid, name, wear=(), carries=(), level=None, source=None):
    """A person of the Flotilla's own: a copy of the mod's pirate (its look, factions, guns), named, given things."""
    import api_characters as ac
    src = FF._mod_key(pr, source or PIRATE, 'NPC_')
    if not src:
        raise ValueError('the mod has no %s (peopledress pirates first)' % (source or PIRATE))
    rec = json.loads(json.dumps(pr.records[src]))
    rec['src'] = ''
    rec['copied_from'] = src
    recordio.set_field(rec, 'EDID', edid, label='Editor ID')
    recordio.set_field(rec, 'FULL', name)
    if wear:
        body = FF._mod_key(pr, 'FOLabPirateBodyList', 'LVLI')
        rec['subs'] = [s for s in rec['subs'] if not (s['tag'] == 'CNTO' and any(f.get('code') == 'F' and f.get('value') == body for f in s['fields']))]
    for key in [FF._item(gd, pr, e) for e in wear] + list(carries):
        s = FF._sub('NPC_', 'CNTO', struct.pack('<Ii', 0, 1))
        FF._set_link(s, key)
        ac.insert(rec, s)
    if level:
        FF._set_num(rec, 'ACBS', 'Level', max(level, FF._num(rec, 'ACBS', 'Level')))
    return rec


def _game(gd, edid, tags):
    for f, (_i, r) in gd.forms.items():
        if r.tag in tags and gd.edid(f) == edid:
            return f
    return None


def _faces_used(gd, pr):
    out = set()
    for r in pr.records.values():
        if r.get('type') == 'NPC_':
            t = recordio.field(r, 'TPLT')
            if t and not str(t).startswith('+'):
                out.add(gd.from_key(t))
    return out


def _lock(ck, rk, key='', level=NEEDS_KEY):
    return {'op': 'props', 'cell': ck, 'ref': rk, 'props': {'lock': {'level': level, 'key': key, 'leveled': False}}}


def _masked(nav, rect):
    """The navmesh with every triangle outside the room walled off from lootplace's wall search (its open edges only
    count in the room)."""
    x0, y0, x1, y1 = rect
    V = nav['verts']
    tris = []
    for t in nav['tris']:
        mx = (V[t[0]][0] + V[t[1]][0] + V[t[2]][0]) / 3
        my = (V[t[0]][1] + V[t[1]][1] + V[t[2]][1]) / 3
        t = list(t)
        if not (x0 < mx < x1 and y0 < my < y1):
            t[3:6] = [0, 0, 0]
        tris.append(t)
    return dict(nav, tris=tris)


def ops(gd, pr, world=None, captain_name=None, seed=22):
    """(ops, report). Raises ValueError when the ships' places aren't there or this was done before."""
    PL = places(pr)
    lacking = sorted(set(PLACES) - set(PL))
    if lacking:
        raise ValueError('The mod lacks the ships\' places (%s): flotillainside first.' % ', '.join(lacking))
    if FF._mod_key(pr, CAPTAIN_EDID, 'NPC_'):
        raise ValueError('The ships already have their people (Undo first).')
    world = world or next(w for w in gd.worlds() if gd.edid(w) == 'FOLabWaikiki')
    rep = {'pirates': {}, 'short': {}, 'locked': [], 'captives': 0, 'elders': 0}
    keys = peopledress._Keys(pr)
    out = []
    tris = {k: _tris(pr, ck) for k, ck in PL.items()}
    doors = {k: [r['p'][:2] for r in pr.cells[ck]['refs'].values() if r.get('p') and (r.get('tel') or lootplace._base_type(gd, pr, r['base']) == 'DOOR')]
             for k, ck in PL.items()}
    taken = {k: [] for k in PL}
    add = lambda ck, base, x, y, z, rz, **extra: out.append(dict({'op': 'add', 'cell': ck, 'base': base, 's': 1.0,
                                                                 'p': [round(x, 1), round(y, 1), round(z, 1), 0.0, 0.0, round(rz % math.tau, 4)]}, **extra))

    # ----- records -----
    store_key = keys.add(lootplace.key_record(gd, *STORE_KEY))
    pens_key = keys.add(lootplace.key_record(gd, *PENS_KEY))
    hold_key = keys.add(lootplace.key_record(gd, *HOLD_KEY))
    captain = keys.add(_copy_pirate(gd, pr, CAPTAIN_EDID, captain_name or CAPTAIN_NAME, wear=CAPTAIN_WEAR, level=16, source=CAPTAIN_FROM))
    qm = keys.add(_copy_pirate(gd, pr, QM_EDID, 'Quartermaster', carries=[store_key], level=12))
    guard = keys.add(_copy_pirate(gd, pr, GUARD_EDID, 'Pirate', carries=[pens_key]))
    friend = _game(gd, CAPTIVE_FACTION, ('FACT',))
    if friend is None:
        raise ValueError('The game files lack %s.' % CAPTIVE_FACTION)
    wear = next((k for k in (FF._mod_key(pr, e) or (_game(gd, e, ('ARMO', 'LVLI')) and gd.key(_game(gd, e, ('ARMO', 'LVLI')))) for e in CAPTIVE_WEAR) if k), None)
    pool, used = FF.faces(gd), _faces_used(gd, pr)
    captives = []
    for n in range(len(CAPTIVES)):
        sex = CAPTIVE['sexes'][n % len(CAPTIVE['sexes'])]
        face = None
        for k in range(len(CAPTIVE['races'])):
            free = [f for f in pool.get((CAPTIVE['races'][(n + k) % len(CAPTIVE['races'])], sex), []) if f not in used]
            if free:
                face = free[(n * 5) % len(free)]
                break
        if face is None:
            rep['short']['captives'] = 'no face left for the %dth' % (n + 1)
            break
        used.add(face)
        captives.append(keys.add(FF.person(gd, pr, face, 'FOLabFlotillaCaptive%02d' % (n + 1), CAPTIVE['name'], CAPTIVE, [(wear, 1)] if wear else [], None, gd.key(friend))))
    out += keys.ops
    pirates = [k for k in (FF._mod_key(pr, e, 'NPC_') for e in PIRATES) if k]

    # ----- the Flotilla's crew -----
    n_p = 0
    for place, rooms in CREW.items():
        ck = PL[place]
        for room, want in rooms.items():
            got = spots(tris[place], _rect(ROOMS[place][room]), want, taken[place], doors[place])
            if len(got) < want:
                rep['short']['%s %s' % (place, room)] = '%d of %d' % (len(got), want)
            for x, y, z in got:
                who = guard if place == 'pens' else pirates[n_p % len(pirates)]
                add(ck, who, x, y, z + 4, (n_p * 2.4) % math.tau)
                n_p += 1
            rep['pirates']['%s %s' % (place, room)] = len(got)
    for who, place, room, tag in ((captain, 'house', 'cabin', 'captain'), (qm, 'house', 'cards', 'quartermaster')):
        got = spots(tris[place], _rect(ROOMS[place][room]), 1, taken[place], doors[place])
        if not got:
            raise ValueError('nowhere to stand for the %s' % tag)
        add(PL[place], who, got[0][0], got[0][1], got[0][2] + 4, math.pi)
        rep[tag] = [round(v) for v in got[0]]

    # ----- the store locked -----
    below, house = PL['below'], PL['house']
    for ck, x, y, what in ((below, 128, -768, 'the store\'s door'), (below, 896, -768, 'the store\'s ladderway'), (house, 0, 1920, 'the house\'s ladderway')):
        out.append(_lock(ck, _door(pr, ck, x, y), store_key))
        rep['locked'].append(what)

    # ----- the pens: cells, captives -----
    pens = PL['pens']
    forms = {e: _game(gd, e, ('STAT', 'DOOR')) for e in {e for _x, e in PANELS} | {'JailCellMid01', JAIL_DOOR, 'BedMattress01Static'}}
    if None in forms.values():
        raise ValueError('The game files lack the jail\'s pieces (%s).' % ', '.join(sorted(e for e, f in forms.items() if f is None)))
    gone = 0
    for rk, r in sorted(pr.cells[pens]['refs'].items()):
        p = r.get('p')
        if not p or r.get('removed') or p[1] < BARS_Y - 60:
            continue
        e = lootplace.settleup._edid(gd, pr, r['base']) or ''
        if 'Cage' in e or 'Mattress' in e:
            out.append({'op': 'remove', 'cell': pens, 'ref': rk})
            gone += 1
    for x, e in PANELS:
        add(pens, gd.key(forms[e]), x, BARS_Y, 0.0, math.pi / 2)
        if e == 'JailCellDoorway01':
            add(pens, gd.key(forms[JAIL_DOOR]), x, BARS_Y, 0.0, math.pi / 2,
                extra={'props': {'lock': {'level': CELL_LOCK, 'key': pens_key, 'leveled': False}}})
    for x, y in DIVIDERS:
        add(pens, gd.key(forms['JailCellMid01']), x, y, 0.0, 0.0)
    for x, y, rz in MATTRESSES:
        add(pens, gd.key(forms['BedMattress01Static']), x, y, 7.0, rz)
    for n, who in enumerate(captives):
        x, y, rz = CAPTIVES[n]
        add(pens, who, x, y, 4.0, rz)
    rep.update({'captives': len(captives), 'cells': sum(1 for _x, e in PANELS if e == 'JailCellDoorway01'), 'cages_out': gone, 'captives_wear': wear})

    # ----- the freighter: the elders inside, the hold locked, both places the Huang's -----
    sh, so = PL['s_house'], PL['s_hold']
    elder = {k for k, r in pr.records.items() if (recordio.field(r, 'EDID') or '').startswith('FOLabHuangElder')}
    standing = sorted((r['base'], ck, rk) for ck, c in pr.cells.items() if not ck.startswith('+')
                      for rk, r in c['refs'].items() if r.get('base') in elder and not r.get('removed'))
    for (base, ck, rk), (room, _n) in zip(standing, ELDERS):
        got = spots(tris['s_house'], _rect(ROOMS['s_house'][room]), 1, taken['s_house'], doors['s_house'])
        if not got:
            rep['short']['elder'] = 'nowhere in the %s' % room
            continue
        out.append({'op': 'remove', 'cell': ck, 'ref': rk})
        add(sh, base, got[0][0], got[0][1], got[0][2] + 4, math.pi)
        rep['elders'] += 1
        if room == 'cabin':                           # (the hold's key: on the elder in the master's cabin)
            import api_characters as ac
            rec = json.loads(json.dumps(pr.records[base]))
            c = FF._sub('NPC_', 'CNTO', struct.pack('<Ii', 0, 1))
            FF._set_link(c, hold_key)
            ac.insert(rec, c)
            out.append({'op': 'record', 'key': base, 'record': rec})
            rep['hold_key_on'] = recordio.field(rec, 'EDID')
    if 'hold_key_on' not in rep:
        raise ValueError("No elder for the master's cabin, so nobody to hold the freighter's hold key.")
    hatch = _door(pr, so, 640, -256)
    for ck, rk, what in ((sh, _door(pr, sh, 0, 1664), 'the freighter house\'s ladderway'), (so, _door(pr, so, 0, 896), 'the freighter hold\'s ladderway'),
                         (so, hatch, 'the freighter hold\'s hatch, inside')):
        out.append(_lock(ck, rk, hold_key))
        rep['locked'].append(what)
    for ck, c in pr.cells.items():
        if ck.startswith('+'):
            continue
        for rk, r in c['refs'].items():
            if (r.get('tel') or {}).get('door') == hatch and not r.get('removed'):
                out.append(_lock(ck, rk, hold_key))
                rep['locked'].append('the freighter\'s deck hatch')
    huang = FF._mod_key(pr, FF.FACTIONS['huang'][0], 'FACT')
    if huang:
        for ck in (sh, so):
            out.append({'op': 'cellinfo', 'cell': ck, 'info': dict(getattr(pr, 'cellinfo', {}).get(ck) or {}, XOWN=huang)})
        rep['owned'] = 2

    # ----- loot by depth (lootplace's way), the Flotilla only -----
    P = lootplace.Plan(gd, pr, world, seed)
    cells = {PL[k]: k for k in BANDS}
    I = lootplace.Inside(P, lambda ck: BANDS[cells[ck]])
    I.run(sorted(cells), {ck: LOOT_NAMES[k] for ck, k in cells.items()})
    for (place, room), kinds in FINDS.items():
        ck = PL[place]
        whole = pr.navmesh[ck]
        pr.navmesh[ck] = _masked(whole, _rect(ROOMS[place][room]))
        try:
            I.walls(ck, kinds, BANDS[place] if room != 'store' else 2, LOOT_NAMES[place])
        finally:
            pr.navmesh[ck] = whole
    out += P.ops
    rep['loot'] = dict(I.rep)
    rep['finds'] = dict(P.report)
    rep['people'] = n_p + 2 + len(captives)
    rep['records'] = len(keys.ops)
    return out, rep


def navmesh_ops(gd, pr):
    """After ops are applied: the pens' navmesh again (its cells are new walls and doors). (ops, report)"""
    import navbuild
    ck = places(pr)['pens']
    data, r = navbuild.generate(gd, pr, ck)
    return [{'op': 'navmesh', 'cell': ck, 'mesh': data}], r


def check(gd, pr):
    """What stands, read back: {captives on the pens' navmesh, people by place, locks}."""
    PL = places(pr)
    tris = _tris(pr, PL['pens'])
    actor = {k for k, r in pr.records.items() if r.get('type') == 'NPC_'}
    rep = {'people': {}, 'locks': 0, 'captives_on_mesh': 0, 'captives': 0}
    for k, ck in PL.items():
        for r in pr.cells[ck]['refs'].values():
            if r.get('base') in actor:
                rep['people'][k] = rep['people'].get(k, 0) + 1
                if (recordio.field(pr.records[r['base']], 'EDID') or '').startswith('FOLabFlotillaCaptive'):
                    rep['captives'] += 1
                    rep['captives_on_mesh'] += _under(tris, r['p'][0], r['p'][1]) is not None
            if (r.get('props') or {}).get('lock'):
                rep['locks'] += 1
    return rep
