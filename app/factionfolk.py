"""People of Waikiki's own to wear its armour and dress (the user, 21 Nov 2026: "We should definitely add Huang anf other
types of people. try to add new assets into the world where we can, guns and armor and clothes etc."). Who, where and how
many are the user's answers of the same day (one question at a time):

- The Huáng at Waimānalo (docs/waikiki-story-plan.md, settlers.py), named on screen in pinyin: ten Shouwei (guards) in
  the Lamellar Armor with the Type 81, Type 79 or QSZ-92 at Makapuʻu Gate, the Border Post, the Settlers' Watchtower on
  Kamehame Ridge and along the road of gates; twelve Nongmin (townsfolk), men in the Changshan and women in the Silk
  Gown, in the courtyards; three Zhanglao (elders) in the Official's Robe on the freighter's deck. A faction of their
  own, neutral to the Castaway: attack one and the rest turn.
- The Kahuna's Guard: six at the Royal Hawaiian, the Ali'i Feather Cloak and Mahiole, the leiomano (the biggest a pōhaku
  maul). Court Fighters: eight in the Koa Fighting Armor with the newa or hoe paddle, four at the Kahuna's toll post on
  the old freeway (two on its planking, two below) and two each round the Moana and the Kilauea. The court's faction.
- Pirate Captains: three in the Officer's Coat with a Pip-Boy (the game's PipBoyNPC), two at the Kāhala Hotel and one at
  Koko Marina; a copy of the mod's pirate (its look, factions, guns), so hostile as the pirates are.

Faces: each person is a record of the mod's own whose look comes from one of the game's ordinary people by template
(traits only, 0x01: race, face, voice), so the game's own painted face goes with it; a copied face of a new form ID would
have none. Name, numbers, factions, inventory and AI are the record's own.

Two greetings only, the guards' (both sides): what anyone else says is the game's generic talk for its voice.
Loot and stores (`trade_ops`): the Huáng's duffle bags and footlockers may hold a Changshan or Silk Gown; the Waikiki
gunsmith sells the court's clubs, the trader a Koa Fighting Armor and an Officer's Coat now and then.

`ops(gd, pr)` -> (ops, report); `apply(server)` one Undo. Spots are found as waikikilife's (`Spots`: open dry ground, no
roof, apart from anyone already standing there) and only over a navmesh (`_on_mesh`); the deck spots are worked out from
the freighter's and the freeway section's frames and have none (her deck and the toll post's planking were never
navmeshed): those people stand where they are put. Nobody walks far: guards stand (DefaultStayAtEditorLocation), townsfolk and fighters wander 512."""
import json
import math
import struct

import recordio
import waikikilife as WL
from castawayquest import _game_form

USE_TRAITS = 0x01
STAY, SANDBOX = WL.STAY, WL.SANDBOX
QUEST = WL.QUEST                                     # (the Waikiki people's talk quest holds the guards' greetings)

# who: name on screen, how many, face pool (races, sexes in turn), what they wear (armourset keys or game ARMO), what they
# carry (weapon editor IDs in turn), faction, package, level, aggression, confidence
GROUPS = {
    'huang_guard': {'name': 'Shouwei', 'count': 10, 'races': ('Asian',), 'sexes': 'MMMMFMMMMF',
                    'wear': {'M': ['FOLabHuangLamellar'], 'F': ['FOLabHuangLamellar']},
                    'arms': ['FOLabWeapTYPE81', 'FOLabWeapTYPE79', 'FOLabWeapTYPE81', 'FOLabWeapQSZ92'], 'ammo': 60,
                    'faction': 'huang', 'package': STAY, 'level': 12, 'aggression': 1, 'confidence': 3},
    'huang_folk': {'name': 'Nongmin', 'count': 12, 'races': ('Asian',), 'sexes': 'MF',
                   'wear': {'M': ['FOLabChangshan'], 'F': ['FOLabSilkGown']}, 'arms': [], 'ammo': 0,
                   'faction': 'huang', 'package': SANDBOX, 'level': 4, 'aggression': 0, 'confidence': 1},
    'huang_elder': {'name': 'Zhanglao', 'count': 3, 'races': ('AsianOld', 'Asian'), 'sexes': 'MMF',
                    'wear': {'M': ['FOLabOfficialsRobe'], 'F': ['FOLabOfficialsRobe']}, 'arms': ['FOLabWeapQSZ92'], 'ammo': 30,
                    'faction': 'huang', 'package': STAY, 'level': 10, 'aggression': 0, 'confidence': 2},
    'kahuna_guard': {'name': "Kahuna's Guard", 'count': 6, 'races': ('Hispanic', 'Asian', 'AfricanAmerican'), 'sexes': 'M',
                     'wear': {'M': ['FOLabAhuula', 'FOLabMahiole']},
                     'arms': ['FOLabWeapLeiomano', 'FOLabWeapLeiomano', 'FOLabWeapMaul', 'FOLabWeapLeiomano', 'FOLabWeapLeiomano', 'FOLabWeapLeiomano'],
                     'ammo': 0, 'faction': 'court', 'package': STAY, 'level': 12, 'aggression': 1, 'confidence': 3},
    'court_fighter': {'name': 'Court Fighter', 'count': 8, 'races': ('Hispanic', 'Asian', 'AfricanAmerican', 'Caucasian'), 'sexes': 'MMMF',
                      'wear': {'M': ['FOLabKoaArmor'], 'F': ['FOLabKoaArmor']}, 'arms': ['FOLabWeapNewa', 'FOLabWeapHoe'], 'ammo': 0,
                      'faction': 'court', 'package': SANDBOX, 'level': 8, 'aggression': 1, 'confidence': 3},
}
FACTIONS = {'huang': ('FOLabHuangFaction', 'Huang'), 'court': ('FOLabKahunaCourtFaction', "The Kahuna's Court")}
FACE_FROM = ('VStreetNCRTraveler', 'VStreetNCRGambler', 'VVault21NCRGambler', 'VVault21NCRTraveler', 'VStreetNCRTrooper')
CAPTAIN = {'edid': 'FOLabPirateCaptain', 'name': 'Pirate Captain', 'from': 'FOLabPirateLvlFiend2GunVarNV',
           'wear': ['FOLabOfficersCoat', 'PipBoyNPC']}
GREET = {'huang_guard': "Barbarian. Walk the road. Touch nothing.",
         'kahuna_guard': "This is the Kahuna's house. State your business or keep walking."}

# where (story plan; settlers.py, overpassposts.py, pirates.py for the spots)
MARKERS = {'makapuu': "Makapu'u Gate", 'border': 'Border Post', 'watch': "Settlers' Watchtower", 'royal': 'The Royal Hawaiian',
           'marina': 'Koko Marina'}
TOLL_SECTION = (-101619.4, 11308.1)                 # (overpassposts.POSTS['court'])
TOLL_DECK = 2048.0 + 40.0                           # (DECK_UP + PLANK_TOP over the section's origin)
TOLL_ON_DECK = [(450.0, -150.0), (1050.0, 150.0)]   # (on the planking, in the section's frame)
DECK_SPOTS = [(525.0, -1150.0), (-525.0, -150.0), (525.0, 850.0)]   # (the freighter's frame: between her hatches)
KAHALA = 'FOLabHotelKahalaReef'


def _sub(rtype, tag, data):
    import schema
    return schema.decode_sub(rtype, tag, data)


def _set_link(sub, value, name=None):
    if 'fields' not in sub:
        sub['value'] = value
        return sub
    for f in sub['fields']:
        if f.get('code') == 'F' and (name is None or f.get('name') == name):
            f['value'] = value
            return sub
    raise ValueError('no link in %s' % sub['tag'])


def _set_field(sub, name, value):
    for f in sub['fields']:
        if f.get('name') == name:
            f['value'] = value


def _mod_key(pr, edid, tag=None):
    for k, r in pr.records.items():
        if (tag is None or r.get('type') == tag) and recordio.field(r, 'EDID') == edid:
            return k
    return None


def _item(gd, pr, edid):
    k = _mod_key(pr, edid)
    if k:
        return k
    return gd.key(_game_form(gd, edid, 'ARMO'))


# ---------- faces ----------

def faces(gd):
    """{(race, 'M'|'F'): [game NPC_ form]} of the game's ordinary people with no template and a painted face of their own."""
    import actors
    races = {f: gd.edid(f) for f, (_i, r) in gd.forms.items() if r.tag == 'RACE'}
    out = {}
    for f, (_i, r) in gd.forms.items():
        if r.tag != 'NPC_' or (f >> 24) != 0:
            continue
        e = gd.edid(f) or ''
        if not e.startswith(FACE_FROM) or e.endswith(('Dead', 'DEAD')):
            continue
        rec = recordio.load(gd, f)
        if recordio.field(rec, 'TPLT'):
            continue
        race = races.get(gd.from_key(recordio.field(rec, 'RNAM') or '') if recordio.field(rec, 'RNAM') else None)
        sex = 'F' if _num(rec, 'ACBS', 'Flags') & actors.FEMALE else 'M'
        out.setdefault((race, sex), []).append(f)
    for v in out.values():
        v.sort()
    return out


def _num(rec, tag, name):
    s = next((s for s in rec['subs'] if s['tag'] == tag), None)
    return next((f['value'] for f in s['fields'] if f.get('name') == name), 0) if s else 0


def _set_num(rec, tag, name, value):
    _set_field(next(s for s in rec['subs'] if s['tag'] == tag), name, value)


# ---------- records ----------

def _faction(gd, edid, name):
    return {'type': 'FACT', 'flags': 0, 'src': '', 'subs': [
        {'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': edid},
        {'tag': 'FULL', 'label': 'Name', 'kind': 'z', 'value': name},
        {'tag': 'DATA', 'label': 'Flags', 'kind': 'struct', 'fields': [{'name': 'Flags', 'code': 'B', 'value': 0},
                                                                         {'name': 'Flags 2', 'code': 'B', 'value': 0}, {'pad': '0000'}]}]}


def _ammo_of(gd, pr, weap_key):
    rec = pr.records.get(weap_key) if weap_key.startswith('+') else recordio.load(gd, gd.from_key(weap_key))
    return recordio.field(rec, 'NAM0') if rec else None


def person(gd, pr, face, edid, name, g, items, arms, faction):
    """One NPC_: the face's record, its look by template (traits), the rest its own."""
    import api_characters as ac
    rec = recordio.load(gd, face)
    rec['src'] = ''
    rec['copied_from'] = gd.key(face)
    rec['subs'] = [s for s in rec['subs'] if s['tag'] not in ('SCRI', 'PKID', 'CNTO', 'SNAM', 'TPLT', 'EITM', 'COED')]
    recordio.set_field(rec, 'EDID', edid, label='Editor ID')
    if any(s['tag'] == 'FULL' for s in rec['subs']):
        recordio.set_field(rec, 'FULL', name)
    else:
        ac.insert(rec, {'tag': 'FULL', 'label': 'Name', 'kind': 'z', 'value': name})
    ac.insert(rec, _set_link(_sub('NPC_', 'TPLT', struct.pack('<I', 0)), gd.key(face)))
    flags = _num(rec, 'ACBS', 'Flags') & ~0x20                      # (not unique: several may share a face's look)
    _set_num(rec, 'ACBS', 'Flags', flags)
    _set_num(rec, 'ACBS', 'Template flags', USE_TRAITS)
    _set_num(rec, 'ACBS', 'Level', g['level'])
    _set_num(rec, 'ACBS', 'Disposition', 35)
    ac.insert(rec, _set_link(_sub('NPC_', 'SNAM', struct.pack('<IB3s', 0, 0, b'\0\0\0')), faction))
    for key, count in items:
        s = _sub('NPC_', 'CNTO', struct.pack('<Ii', 0, count))
        _set_link(s, key)
        ac.insert(rec, s)
    ac.insert(rec, {'tag': 'PKID', 'label': 'AI package', 'kind': 'F', 'value': gd.key(ac._find(gd, 'PACK', g['package']))})
    _set_num(rec, 'AIDT', 'Aggression', g['aggression'])
    _set_num(rec, 'AIDT', 'Confidence', g['confidence'])
    _set_num(rec, 'AIDT', 'Assistance', 2 if g['faction'] else 0)    # (helps friends and allies)
    _set_num(rec, 'AIDT', 'Services', 0)
    return rec


def captain(gd, pr):
    """The Pirate Captain: a copy of the mod's pirate with the Officer's Coat and a Pip-Boy in place of its body list."""
    src_key = _mod_key(pr, CAPTAIN['from'], 'NPC_')
    if not src_key:
        raise ValueError('the mod has no %s (peopledress pirates first)' % CAPTAIN['from'])
    rec = json.loads(json.dumps(pr.records[src_key]))
    rec['src'] = ''
    rec['copied_from'] = src_key
    recordio.set_field(rec, 'EDID', CAPTAIN['edid'], label='Editor ID')
    recordio.set_field(rec, 'FULL', CAPTAIN['name'])
    body = _mod_key(pr, 'FOLabPirateBodyList', 'LVLI')
    keep = []
    for s in rec['subs']:
        if s['tag'] == 'CNTO' and any(f.get('code') == 'F' and f.get('value') == body for f in s['fields']):
            continue
        keep.append(s)
    rec['subs'] = keep
    import api_characters as ac
    for e in CAPTAIN['wear']:
        s = _sub('NPC_', 'CNTO', struct.pack('<Ii', 0, 1))
        _set_link(s, _item(gd, pr, e))
        ac.insert(rec, s)
    _set_num(rec, 'ACBS', 'Level', max(12, _num(rec, 'ACBS', 'Level')))
    return rec


# ---------- spots ----------

def _markers(pr):
    out = {}
    for ck, c in pr.cells.items():
        for rk, r in (c.get('refs') or {}).items():
            m = r.get('marker')
            name = m.get('name') if isinstance(m, dict) else m
            if name and not r.get('removed') and r.get('p'):
                out.setdefault(str(name), (ck, r['p']))
    return out


def _refs_of(pr, base):
    return [(ck, r['p']) for ck, c in pr.cells.items() for r in (c.get('refs') or {}).values()
            if r.get('base') == base and not r.get('removed') and r.get('p')]


def _standing(gd, pr):
    """Where actors of the mod's own already stand outside (kept clear)."""
    actor = {k for k, r in pr.records.items() if r.get('type') in ('NPC_', 'CREA', 'LVLN', 'LVLC')}
    out = []
    for ck, c in pr.cells.items():
        if ck.startswith('+'):
            continue
        for r in (c.get('refs') or {}).values():
            if r.get('base') in actor and not r.get('removed') and r.get('p'):
                out.append((r['p'][0], r['p'][1]))
    return out


def _frame(p, x, y):
    rz = p[5] if len(p) > 5 else 0.0
    c, s = math.cos(rz), math.sin(rz)
    return p[0] + x * c + y * s, p[1] - x * s + y * c, rz


MESH_NEAR = 60.0                                    # (a ground spot counts only with a navmesh triangle this near under it)


def _on_mesh(sp, x, y, z):
    """Whether a navmesh (the mod's, else the game's) lies within MESH_NEAR of (x, y, z): people stand where they can walk."""
    import navbuild
    if not hasattr(sp, 'meshes'):
        sp.meshes = {}
    c = sp.grid.get((int(x // 4096), int(y // 4096)))
    if c is None:
        return False
    ck = sp.gd.key(c)
    if ck not in sp.meshes:
        sh = navbuild.shape(sp.gd, sp.pr, ck)
        v, t = sh['verts'], sh['tris']
        sp.meshes[ck] = [tuple((v[3 * t[i + j]], v[3 * t[i + j] + 1], v[3 * t[i + j] + 2]) for j in range(3)) for i in range(0, len(t), 3)]
    for a, b, c in sp.meshes[ck]:
        if max(a[0], b[0], c[0]) < x or min(a[0], b[0], c[0]) > x or max(a[1], b[1], c[1]) < y or min(a[1], b[1], c[1]) > y:
            continue
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if not d:
            continue
        l1 = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / d
        l2 = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / d
        l3 = 1 - l1 - l2
        if min(l1, l2, l3) >= -0.01 and abs(l1 * a[2] + l2 * b[2] + l3 * c[2] - z) < MESH_NEAR:
            return True
    return False


def _near(sp, x, y, want, radii=(250, 400, 550, 700, 900), turns=12, side=None):
    out = []
    for r in radii:
        for t in range(turns):
            a = (t + 0.37 * (r // 150)) * 2 * math.pi / turns
            px, py = x + r * math.sin(a), y + r * math.cos(a)
            if side and (px - x) * side[0] + (py - y) * side[1] < 0:
                continue
            z = sp.stand(px, py, apart=180.0)
            if z is not None and not _on_mesh(sp, px, py, z):
                sp.taken.pop()
                z = None
            if z is not None:
                out.append((px, py, z, math.atan2(px - x, py - y)))      # (facing out, away from what they guard)
                if len(out) >= want:
                    return out
    return out


def plan(gd, pr):
    """{group: [(x, y, z, rz)]} and the world."""
    import roadgen
    mk = _markers(pr)
    need = [v for v in MARKERS.values() if v not in mk]
    if need:
        raise ValueError('no map marker for %s' % ', '.join(need))
    world = gd.ext_cells[gd.from_key(mk[MARKERS['royal']][0])]
    sp = WL.Spots(gd, pr, world)
    sp.taken = _standing(gd, pr)
    sp.gd, sp.pr, sp.grid = gd, pr, gd.grid(world)
    got = {k: [] for k in list(GROUPS) + ['captain']}
    xy = lambda name: mk[MARKERS[name]][1][:2]
    # the Huáng
    gates = {n: _refs_of(pr, _mod_key(pr, 'FOLabSettlerGate%d' % n, 'STAT')) for n in (5, 3, 1)}
    for name, n in (('makapuu', 2), ('border', 2), ('watch', 2)):
        got['huang_guard'] += _near(sp, *xy(name), n)
    road = [p for n in (5, 3, 1) for _ck, p in gates[n] if math.hypot(p[0] - 85000, p[1] - 74500) < 8000]
    for p, n in zip(road, (2, 1, 1)):
        got['huang_guard'] += _near(sp, p[0], p[1], n)
    screens = [p for _ck, p in _refs_of(pr, _mod_key(pr, 'FOLabSettlerScreen', 'STAT'))]
    for p in screens:
        got['huang_folk'] += _near(sp, p[0], p[1], 2, radii=(350, 500, 650, 800))
    ship = _refs_of(pr, _mod_key(pr, 'FOLabSettlerFreighter', 'STAT'))
    if ship:
        import settlerset
        p = ship[0][1]
        s = p[6] if len(p) > 6 else 1.0
        for dx, dy in DECK_SPOTS:
            x, y, rz = _frame(p, dx, dy)
            got['huang_elder'].append((x, y, p[2] + settlerset.F_DECK * s, rz + (math.pi / 2 if dx > 0 else -math.pi / 2)))
    # the court
    rx, ry = xy('royal')
    got['kahuna_guard'] = _near(sp, rx, ry, 6, radii=(700, 850, 1000, 1200, 1400), turns=20, side=(0.0, 1.0))
    sec = _toll_section(gd, pr)
    if sec:
        for dx, dy in TOLL_ON_DECK:
            x, y, rz = _frame(sec, dx, dy)
            got['court_fighter'].append((x, y, sec[2] + TOLL_DECK, rz))
        got['court_fighter'] += _near(sp, sec[0], sec[1], 2, radii=(1300, 1500, 1800, 2200))
    hot, _mid = WL.middle(pr)
    for k in ('moana', 'kilauea'):
        if k in hot:
            got['court_fighter'] += _near(sp, hot[k][0], hot[k][1], 2, radii=(900, 1100, 1300, 1600))
    short = GROUPS['court_fighter']['count'] - len(got['court_fighter'])
    if short > 0:                                    # (a hotel with no open ground round it: the rest by the court)
        got['court_fighter'] += _near(sp, rx, ry, short, radii=(1600, 1900, 2200, 2600), turns=20)
    # the captains
    kahala = _refs_of(pr, _mod_key(pr, KAHALA, 'STAT'))
    if kahala:
        got['captain'] += _near(sp, kahala[0][1][0], kahala[0][1][1], 2, radii=(1200, 1500, 1800, 2200), turns=16)
    got['captain'] += _near(sp, *xy('marina'), 1, radii=(300, 500, 800))
    return {'spots': got, 'world': world, 'sp': sp}


def _toll_section(gd, pr):
    best = None
    try:
        base = gd.key(_game_form(gd, 'OverpassSectionLo01', 'STAT'))
    except ValueError:
        return None
    for _ck, p in _refs_of(pr, base):
        d = math.hypot(p[0] - TOLL_SECTION[0], p[1] - TOLL_SECTION[1])
        if d < 3000 and (best is None or d < best[0]):
            best = (d, p)
    return best[1] if best else None


# ---------- loot and stores ----------

def trade_ops(gd, pr, clothes_key):
    """Record ops: the Huáng's containers given the clothes list, the gunsmith the court's clubs, the trader the armour."""
    out, rep = [], {}
    adds = {'FOLabNVDuffleBagRandomLootHuang': [(clothes_key, 1)], 'FOLabFootlocker01HospitalHuang': [(clothes_key, 1)],
            'FOLabWaikikiGunsmithChest': [(_mod_key(pr, 'FOLabClubsCourt', 'LVLI'), 2)],
            'FOLabWaikikiTraderChest': [(_item(gd, pr, 'FOLabKoaArmor'), 1), (_item(gd, pr, 'FOLabOfficersCoat'), 1)]}
    import api_characters as ac
    for edid, items in adds.items():
        k = _mod_key(pr, edid, 'CONT')
        if not k or not all(i for i, _n in items):
            rep[edid] = 'not in the mod'
            continue
        rec = json.loads(json.dumps(pr.records[k]))
        for key, count in items:
            s = _sub('CONT', 'CNTO', struct.pack('<Ii', 0, count))
            _set_link(s, key)
            ac.insert(rec, s)
        out.append({'op': 'record', 'key': k, 'record': rec})
        rep[edid] = len(items)
    return out, rep


# ---------- all of it ----------

def ops(gd, pr, P=None):
    import api_quests as aq
    import peopledress
    import questrec as qr
    taken = {(recordio.field(r, 'EDID') or '').lower() for r in pr.records.values()}
    if FACTIONS['huang'][0].lower() in taken:
        raise ValueError('the mod already has %s: these people look done (Undo first)' % FACTIONS['huang'][0])
    P = P or plan(gd, pr)
    grid = gd.grid(P['world'])
    cell = lambda x, y: gd.key(grid[(int(x // 4096), int(y // 4096))])
    keys = peopledress._Keys(pr)
    rep = {'groups': {}, 'short': {}}
    fac = {k: keys.add(_faction(gd, e, n)) for k, (e, n) in FACTIONS.items()}
    clothes = keys.add(peopledress._lvli(gd, 'FOLabClothesHuang', 50, [(_item(gd, pr, 'FOLabChangshan'), 1), (_item(gd, pr, 'FOLabSilkGown'), 1)]))
    pool = faces(gd)
    used = set()
    people = {}
    for g_key, g in GROUPS.items():
        people[g_key] = []
        for n in range(g['count']):
            sex = g['sexes'][n % len(g['sexes'])]
            face = None
            for k in range(len(g['races'])):
                race = g['races'][(n + k) % len(g['races'])]
                free = [f for f in pool.get((race, sex), []) if f not in used]
                if free:
                    face = free[(n * 7) % len(free)]
                    break
            if face is None:
                raise ValueError('no face left for %s (%s)' % (g_key, sex))
            used.add(face)
            items = [(_item(gd, pr, e), 1) for e in g['wear'][sex]]
            if g['arms']:
                w = _mod_key(pr, g['arms'][n % len(g['arms'])], 'WEAP')
                if not w:
                    raise ValueError('the mod has no %s' % g['arms'][n % len(g['arms'])])
                items.append((w, 1))
                ammo = _ammo_of(gd, pr, w) if g['ammo'] else None
                if ammo:
                    items.append((ammo, g['ammo']))
            edid = 'FOLab%s%02d' % (''.join(w.capitalize() for w in g_key.split('_')), n + 1)
            people[g_key].append(keys.add(person(gd, pr, face, edid, g['name'], g, items, None, fac[g['faction']])))
    cap = keys.add(captain(gd, pr))
    out = list(keys.ops)
    # placed
    placed = 0
    for g_key, refs in list(people.items()) + [('captain', [cap])]:
        spots = P['spots'].get(g_key, [])
        want = GROUPS[g_key]['count'] if g_key in GROUPS else 3
        if len(spots) < want:
            rep['short'][g_key] = '%d of %d spots' % (len(spots), want)
        for n, (x, y, z, rz) in enumerate(spots[:want]):
            out.append({'op': 'add', 'cell': cell(x, y), 'base': refs[n % len(refs)],
                        'p': [round(x, 1), round(y, 1), round(z + 4, 1), 0.0, 0.0, round(rz, 4)], 's': 1.0})
            placed += 1
        rep['groups'][g_key] = {'records': len(refs), 'placed': min(len(spots), want), 'first': refs[0]}
    # the guards' greetings (in the Waikiki people's quest)
    quest = _mod_key(pr, QUEST, 'QUST')
    greeting = gd.key(_game_form(gd, 'GREETING', 'DIAL'))
    lines = []
    if quest:
        for g_key, words in GREET.items():
            for who in people[g_key]:
                lines.append(dict(aq.new_line_plain(gd, pr, greeting, quest, who, words), begin=None, end=None))
        out += [{'op': 'record_new', 'record': qr.info_record(l)} for l in lines]
    t_ops, rep['trade'] = trade_ops(gd, pr, clothes)
    out += t_ops
    rep.update({'factions': fac, 'clothes_list': clothes, 'captain': cap, 'placed': placed, 'greetings': len(lines),
                'keys_from': '+%06X' % pr.next_id, 'records': len(keys.ops)})
    return out, rep


def apply(server):
    gd, pr = server.GD, server.PR
    o, rep = ops(gd, pr)
    server.edit('The Huang, the Kahuna\'s guard, court fighters, pirate captains', o)
    return rep
