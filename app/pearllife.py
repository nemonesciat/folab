"""The Pink Pearl's people, lines and days (the user in the Pearl, 26 Nov 2026: "none of the npcs have lines. or anything to
do"). The three activities' people (pinkpearl.py) spoke only their quests' lines, and only while each quest stood at that
point; every one of them stood still on its spot. After this step everyone in the Pearl and at the boatyard has something to
say at any point of the quests, and a day:

- **Lines** (quest `QUEST`, start-enabled, priority `PRIORITY`, under the activities' 55 so their lines come first): a greeting
  of their own wherever the quests leave them none (the storm crew between storms, the guard once the boy is free, the
  boatyard hand once his crate is settled, his two crewmen, who had none), and two top-level topics for everyone, "What is
  this place?" and "Any work around here?". Work points at the activities before they start: the boatyard hand's crate
  while you haven't met him, the boy upstairs while he's held, the storm crew's cards and trade otherwise. All voiced.
- **New people** (`NEW`: a face each nobody in the mod wears): the Pearl Barkeep behind the lobby's bar (sells as Goodsprings'
  saloon does, from a copy of its chest buried under him; "Let's trade." opens the barter window), an Off-Watch Sailor
  drinking in the lounge, and two Boat Lodgers on Guest Floor 1, who sleep in its beds.
- **Days** (`DAYS`): packages of the step's own, the game's sandbox and sleep packages copied and placed by the place's own
  things, all walked to on the place's navmesh (`reach`). The storm crew sandbox round their fire and card table (the couch
  by the table seats the dealer), the scavenger sleeps in a Top Floor bed at night, the lodgers in theirs, the barkeep keeps
  the bar by day (offering his services) and sits in the lounge at night. No package runs (`RUN` cleared) and every target is
  in the person's own place (the lifts are load doors: nobody is sent across one). The guard keeps his post and his bed
  (the boy quest needs him there) and the held boy his shackle.
- The scavenger's empty faction (a SNAM naming nothing, from pinkpearl's `_person` for a person of no faction) goes.

    plan(gd, pr)       {'rows', 'skipped', 'spots'}
    apply(pr, gd, P)   one Undo (VOICE: this step's lines)
    talks()            every person has a greeting at every point of the quests (the activities' lines and these)
"""
import json
import math

import recordio
import pinkpearl as PP

LABEL = "The Pink Pearl's people: lines and days"
QUEST, QUEST_NAME = 'FOLabPearlLife', 'Pink Pearl People'
VOICE = [QUEST]
PRIORITY = 40
TOPICS = {'where': ('FOLabPearlLifeWhere', 'What is this place?'), 'work': ('FOLabPearlLifeWork', 'Any work around here?'),
          'trade': ('FOLabPearlLifeTrade', "Let's trade.")}
RUN = 0x2000                    # (PKDT's Always Run: never set)
SERVICES = 0x1                  # (PKDT's Offers Services: the barkeep's day at the bar)
NO_SLEEP = 0x2                  # (a sandbox's No Sleeping)
BAR_FROM, BAR_CHEST = 'GSTrudy', 'VendorContainerTrudy'
BARTER_GOLD = 400
REACH = 160.0                   # (walked ground this near a day's target's middle: a bed's or a counter's side)
CHEST_UNDER = 400

# who: key -> (editor ID, name, sex, wears, place)
NEW = {
    'barkeep': ('FOLabPearlBarkeep', 'Pearl Barkeep', 'M', ('OutfitPrewarCasualwear', 'Weap10mmPistol'), 'lobby'),
    'drinker': ('FOLabPearlDrinker', 'Off-Watch Sailor', 'F', ('ArmorLeather', 'WeapNVMachete'), 'lobby'),
    'lodger1': ('FOLabPearlLodger1', 'Boat Lodger', 'M', ('ArmorLeather', 'Weap10mmPistol'), 'g1'),
    'lodger2': ('FOLabPearlLodger2', 'Boat Lodger', 'F', ('OutfitMerc02|ArmorLeather', 'Weap10mmPistol'), 'g1'),
}
RACES = ('Asian', 'Caucasian', 'Hispanic', 'AfricanAmerican')

# a day: [(kind, target, hour, hours, radius, flags)], tried in order (hour -1: any time, the last of each is that).
# Targets: 'bar' (the lobby's bar counter), 'lounge' (the lobby couch nearest it), 'fire', 'table' (the storm crew's),
# 'bed1'/'bed2' (Guest Floor 1's beds farthest from the strongbox), 'scav_bed' (the Top Floor bed nearest the scavenger).
DAYS = {
    'barkeep': [('sandbox', 'bar', 8, 18, 192, SERVICES | NO_SLEEP), ('sandbox', 'lounge', -1, 0, 256, NO_SLEEP)],
    'drinker': [('sandbox', 'bar', 18, 8, 256, NO_SLEEP), ('sandbox', 'lounge', -1, 0, 448, NO_SLEEP)],
    'lodger1': [('sleep', 'bed1', 23, 8, 96, 0), ('sandbox', 'bed1', -1, 0, 640, NO_SLEEP)],
    'lodger2': [('sleep', 'bed2', 0, 8, 96, 0), ('sandbox', 'bed2', -1, 0, 640, NO_SLEEP)],
    'scav': [('sleep', 'scav_bed', 1, 7, 96, 0)],                   # (then his own sandbox, as before)
    'boss': [('sandbox', 'fire', -1, 0, 320, NO_SLEEP)],
    'dealer': [('sandbox', 'table', -1, 0, 200, NO_SLEEP)],
    'deck1': [('sandbox', 'fire', -1, 0, 480, NO_SLEEP)],
    'deck2': [('sandbox', 'fire', -1, 0, 480, NO_SLEEP)],
}
REPLACE = ('boss', 'dealer', 'deck1', 'deck2')      # (their StayAtEditorLocation goes; the others keep what they had after these)
PLACE_OF = {'barkeep': 'lobby', 'drinker': 'lobby', 'lodger1': 'g1', 'lodger2': 'g1', 'scav': 'top',
            'boss': 'lobby', 'dealer': 'lobby', 'deck1': 'lobby', 'deck2': 'lobby'}

# what each says: the activities' state as (quest, variable, op, value), as pinkpearl's lines_spec has it
MET0 = ('cells', 'met', '==', 0)
HELD = [('boy', 'started', '==', 1), ('boy', 'freed', '==', 0)]
W = {
    'barkeep_hi': "Drinks, a bed, talk. Talk's free. Mostly.",
    'barkeep_where': "The Pink Pearl. The boats' hotel, south of the marina. Crews sleep it off here between tides.",
    'barkeep_crate': "The boatyard hand at the marina lost a crate. He's been asking everyone who comes through. He'll pay, if you find it.",
    'barkeep_boy': "There's a Kuliouou boy kept on the second guest floor till his boat sails. Not my business. Could be yours.",
    'barkeep_storm': "When a big storm comes in, the marina's crews run in here. Cards and trade in the lobby, then. Otherwise it's quiet.",
    'barkeep_trade': "Have a look.",
    'drinker_hi': "One more and I'm back on the water. Maybe two.",
    'drinker_where': "Best roof between the marina and Kuliouou. Pink as a sunburn, and the beds don't leak.",
    'drinker_crate': "Down at the yard the hand's lost a crate, and he won't shut up about it. Ask him.",
    'drinker_boy': "Some crew's got a boy shackled upstairs, waiting on a boat. Second guest floor. I don't go up there.",
    'drinker_storm': "Wait for a storm. The boss sits by the fire and buys salvage, and the dealer takes your cells at cards.",
    'lodger1_hi': "Off watch. Tide's wrong till morning. Let a man rest.",
    'lodger1_where': "Guest floor one. The boats' crews bunk here between runs. Nobody asks what you carry.",
    'lodger1_crate': "The boatyard hand's short a crate. Somebody in this hotel took it, he reckons. Wasn't me.",
    'lodger1_work': "Work? Go down to the marina when a boat's in. They always need hands.",
    'lodger2_hi': "Looking for a bed? Find your own. This floor's spoken for.",
    'lodger2_where': "The Pearl's rooms. Not a door left on any of them, so keep your hands where I can see them.",
    'lodger2_boy': "There's a boy on the floor above, waiting on his boat. His guard sleeps nights. Not that I'd know.",
    'lodger2_work': "The crews run in when the weather turns. Come back in a storm, there's cards.",
    'scav_where': "The Pearl's top floor. The boats sleep downstairs. Up here nobody bothers me.",
    'scav_crate': "Work? Ask the boats. They've always got something gone missing.",
    'scav_work': "Nothing for you up here.",
    'guard_free': "You've had your boy. Leave me be.",
    'guard_where': "Guest floor two. Nothing up here for you. Move along.",
    'guard_work': "My work's the boy. Yours is somewhere else.",
    'boss_off': "Storm's blown out. We'll be back on the water by morning.",
    'boss_where': "The Pink Pearl. When a big blow comes in, every crew in the marina runs for these walls.",
    'boss_work': "Bring me storm salvage when it's blowing. Scrap metal. I pay in cells.",
    'dealer_off': "No storm, no game. Come back when it blows.",
    'dealer_where': "The lobby's the best table on the island when the wind's up.",
    'dealer_work': "Three hands a storm, ten cells a hand. That's all the work I offer.",
    'deck1_off': "Calm out there now. Shame. I was winning.",
    'deck1_where': "Pink Pearl. Our storm hole.",
    'deck1_work': "Ask the boss. He buys storm salvage.",
    'deck2_off': "Wind's dropping. Back to the boats soon.",
    'deck2_where': "Every crew in the marina knows these walls. The roof's held through worse.",
    'deck2_work': "The boss buys scrap when it's blowing. And keep your cells off the dealer's table.",
    'hand_after': "Yard's busy. Unless you've come to work, mind the hulls.",
    'hand_where': "Koko Marina. The boats' yard. The crews sleep at the Pink Pearl, just south.",
    'crew1_met0': "Talk to the hand. He's the one with the trouble.",
    'crew1_hi': "Mind the hulls.",
    'crew1_where': "Koko Marina. The Pink Pearl's just south of here, if you need a bed.",
    'crew2_met0': "Hand's lost his crate. Ask him, not me.",
    'crew2_hi': "Back to work. These hulls don't scrape themselves.",
    'crew2_where': "The boats' yard. Every crew on this coast hauls out here.",
}


def lines_spec():
    """[(who, topic, words key, conditions)]: in the order the game tries them; topic 'G' is the greeting. A condition is
    (quest, variable, op, value) on one of the activities' quests ('cells', 'boy', 'storm')."""
    L = []
    line = lambda who, topic, words, conds=(): L.append((who, topic, words, list(conds)))
    for who in ('barkeep', 'drinker'):
        line(who, 'G', who + '_hi')
        line(who, 'where', who + '_where')
        line(who, 'work', who + '_crate', [MET0])
        line(who, 'work', who + '_boy', HELD)
        line(who, 'work', who + '_storm')
    line('barkeep', 'trade', 'barkeep_trade')
    line('lodger1', 'G', 'lodger1_hi')
    line('lodger1', 'where', 'lodger1_where')
    line('lodger1', 'work', 'lodger1_crate', [MET0])
    line('lodger1', 'work', 'lodger1_work')
    line('lodger2', 'G', 'lodger2_hi')
    line('lodger2', 'where', 'lodger2_where')
    line('lodger2', 'work', 'lodger2_boy', HELD)
    line('lodger2', 'work', 'lodger2_work')
    line('scav', 'where', 'scav_where')
    line('scav', 'work', 'scav_crate', [MET0])
    line('scav', 'work', 'scav_work')
    line('guard', 'G', 'guard_free', [('boy', 'freed', '>', 0)])
    line('guard', 'where', 'guard_where')
    line('guard', 'work', 'guard_work')
    for who in PP.STORM_CREW:
        line(who, 'G', who + '_off')                 # (the activity's greetings hold only while a storm is on)
        line(who, 'where', who + '_where')
        line(who, 'work', who + '_work')
    line('hand', 'G', 'hand_after')                  # (his crate settled: the activity's greetings leave him none)
    line('hand', 'where', 'hand_where')
    for who in ('crew1', 'crew2'):
        line(who, 'G', who + '_met0', [MET0])
        line(who, 'G', who + '_hi')
        line(who, 'where', who + '_where')
    return L


# ---------- where ----------

def _ref_of(pr, edid):
    for ck, c in pr.cells.items():
        for rk, r in (c.get('refs') or {}).items():
            if r.get('edid') == edid and not r.get('removed'):
                return ck, rk, r
    return None, None, None


def _mesh_reach(pr, ck, a, b, near=300.0, reach=REACH):
    """Whether the place's own navmesh walks from the ground by a to within `reach` of b (a bed or a counter cuts its own
    hole in the mesh: what counts is that the ground walked from a comes up to it). The floors stack at the same x, y, so
    only the one place's mesh is looked at."""
    m = (pr.navmesh or {}).get(ck)
    if not m:
        return False
    v, T = m['verts'], m['tris']
    mid = [((v[t[0]][0] + v[t[1]][0] + v[t[2]][0]) / 3, (v[t[0]][1] + v[t[1]][1] + v[t[2]][1]) / 3) for t in T]
    near_a = [(math.hypot(c[0] - a[0], c[1] - a[1]), i) for i, c in enumerate(mid)]
    d, s = min(near_a)
    if d > near:
        return False
    seen, todo = {s}, [s]
    while todo:
        i = todo.pop()
        if _to_tri(b, [v[k] for k in T[i][:3]]) <= reach:
            return True
        tri = T[i]
        for e in range(3):
            n = tri[3 + e]
            if n in (65535, None) or tri[6] >> e & 1:
                continue
            if n not in seen:
                seen.add(n)
                todo.append(n)
    return False


def _to_tri(p, tri):
    """How far p is from a triangle, seen from above."""
    (ax, ay), (bx, by), (cx, cy) = [(q[0], q[1]) for q in tri]
    x, y = p[0], p[1]
    d1 = (x - bx) * (ay - by) - (ax - bx) * (y - by)
    d2 = (x - cx) * (by - cy) - (bx - cx) * (y - cy)
    d3 = (x - ax) * (cy - ay) - (cx - ax) * (y - ay)
    if not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0)):
        return 0.0

    def seg(ux, uy, wx, wy):
        L = (wx - ux) ** 2 + (wy - uy) ** 2
        t = 0.0 if not L else max(0.0, min(1.0, ((x - ux) * (wx - ux) + (y - uy) * (wy - uy)) / L))
        return math.hypot(x - ux - t * (wx - ux), y - uy - t * (wy - uy))
    return min(seg(ax, ay, bx, by), seg(bx, by, cx, cy), seg(cx, cy, ax, ay))


def plan(gd, pr):
    import robots
    rows, skipped, S = [], [], {'targets': {}}
    places = PP._places(pr)
    missing = [v for v in PP.FLOORS.values() if v not in places]
    if missing:
        return {'rows': [], 'skipped': ['the Pink Pearl\'s places are not in the mod: %s' % ', '.join(missing)], 'spots': {}}
    ck = {k: places[v] for k, v in PP.FLOORS.items()}
    S['cells'] = ck
    for q in list(PP.QUESTS.values()) + ['FOLabPirateTraders']:
        if not PP._mod_key(pr, q):
            skipped.append('no %s (the Pink Pearl activities first)' % q)
    if PP._mod_key(pr, QUEST, 'QUST'):
        skipped.append('the mod has %s already' % QUEST)
    T = S['targets']

    def things(floor, words):
        return [(rk, r) for rk, r in PP._refs(gd, pr, ck[floor], words)]
    # the bar: the lobby's counter with no cash register on it, farthest from the front door
    desks = things('lobby', ('OfficeReceptionDesk',))
    tills = [r['p'] for _k, r in things('lobby', ('CashRegister',))]
    door = next((r['p'] for _k, r in things('lobby', ('HotelDoor',))), (0, 0, 0))
    bars = [(k, r) for k, r in desks if all(math.hypot(r['p'][0] - t[0], r['p'][1] - t[1]) > 80 for t in tills)]
    if bars:
        k, r = max(bars, key=lambda kr: math.hypot(kr[1]['p'][0] - door[0], kr[1]['p'][1] - door[1]))
        T['bar'] = ('lobby', k, r['p'])
    couches = things('lobby', ('SubCouch',))
    if couches and 'bar' in T:
        bp = T['bar'][2]
        k, r = min(couches, key=lambda kr: math.hypot(kr[1]['p'][0] - bp[0], kr[1]['p'][1] - bp[1]))
        T['lounge'] = ('lobby', k, r['p'])
    for name, edid in (('fire', 'FOLabPearlStormFireRef'), ('table', 'FOLabPearlStormTableRef')):
        c, k, r = _ref_of(pr, edid)
        if k:
            T[name] = ('lobby', k, r['p'])
    beds = things('g1', ('HotelBed',))
    _c, _k, box = _ref_of(pr, PP.REF['box'])
    if box and len(beds) >= 2:
        beds.sort(key=lambda kr: -math.hypot(kr[1]['p'][0] - box['p'][0], kr[1]['p'][1] - box['p'][1]))
        T['bed1'] = ('g1', beds[0][0], beds[0][1]['p'])
        T['bed2'] = ('g1', beds[1][0], beds[1][1]['p'])
    _c, _k, scav = _ref_of(pr, PP.REF['scav'])
    tbeds = things('top', ('HotelBed',))
    if scav and tbeds:
        k, r = min(tbeds, key=lambda kr: math.hypot(kr[1]['p'][0] - scav['p'][0], kr[1]['p'][1] - scav['p'][1]))
        T['scav_bed'] = ('top', k, r['p'])
    for want in ('bar', 'lounge', 'fire', 'table', 'bed1', 'bed2', 'scav_bed'):
        if want not in T:
            skipped.append('no %s in the Pearl' % want)
        else:
            rows.append({'target': want, 'place': PP.FLOORS[T[want][0]], 'ref': T[want][1], 'p': [round(v) for v in T[want][2][:3]]})
    # the new people's spots: free navmesh ground near what their day is about (clear of doors, people and seats)
    taken = {}
    for who, (_e, _n, _s, _w, floor) in NEW.items():
        target = T.get(DAYS[who][0][1])
        if not target:
            continue
        tris = robots._tris(gd, pr, ck[floor])
        doors, actors, seats = robots._things(gd, pr, ck[floor])
        tp = target[2]
        best = None
        for clear in (1.0, 0.66):
            for p in tris:
                d = math.hypot(p[0] - tp[0], p[1] - tp[1])
                if d < 90 or d > 600:
                    continue
                if (min((robots._d(p, q) for q in doors), default=1e9) < robots.DOOR_CLEAR * clear or
                        min((robots._d(p, q) for q in actors + taken.get(floor, [])), default=1e9) < robots.APART * clear or
                        min((robots._d(p, q) for q in seats), default=1e9) < robots.SEAT_CLEAR * clear):
                    continue
                if best is None or d < best[0]:
                    best = (d, p)
            if best:
                break
        if not best:
            skipped.append('%s: no free ground near the %s' % (who, DAYS[who][0][1]))
            continue
        p = best[1]
        rz = math.atan2(tp[0] - p[0], tp[1] - p[1])
        taken.setdefault(floor, []).append(p)
        S[who] = {'cell': ck[floor], 'p': (round(p[0], 1), round(p[1], 1), round(p[2] + 4, 1), round(rz, 4))}
        rows.append({'who': who, 'place': PP.FLOORS[floor], 'p': [round(v) for v in p[:3]], 'from target': round(best[0])})
    # every day's target walked to on the person's own place's mesh
    reach = {}
    for who, day in DAYS.items():
        if who in NEW:
            spot = S.get(who, {}).get('p')
        else:
            _c, _k, r = _ref_of(pr, PP.REF[who])
            spot = r['p'] if r else None
        for kind, tgt, *_ in day:
            if not spot or tgt not in T:
                continue
            ok = T[tgt][0] == PLACE_OF[who] and _mesh_reach(pr, ck[PLACE_OF[who]], spot, T[tgt][2])
            reach['%s -> %s' % (who, tgt)] = ok
            if not ok:
                skipped.append('%s can\'t walk to the %s' % (who, tgt))
    rows.append({'reach': reach})
    S['reach'] = reach
    return {'rows': rows, 'skipped': skipped, 'spots': S}


# ---------- the step ----------

def _pack(gd, src, edid, hour, hours, target, radius, flags):
    import api_characters as ac
    import piratedeal
    rec = recordio.load(gd, piratedeal._game(gd, src, 'PACK'))
    rec.pop('copied_from', None)
    rec['src'] = ''
    recordio.set_field(rec, 'EDID', edid, label='Editor ID')
    for s in rec['subs']:
        if s['tag'] == 'PSDT':
            for f in s['fields']:
                if f.get('name') == 'Time':
                    f['value'] = int(hour)
                elif f.get('name') == 'Duration':
                    f['value'] = int(hours)
        elif s['tag'] == 'PKDT':
            for f in s['fields']:
                if f.get('name') == 'Flags':
                    f['value'] = (int(f['value']) & ~RUN) | (flags & SERVICES)
                elif f.get('name') == 'Type flags' and src.startswith('DefaultSandbox'):
                    f['value'] = int(f['value']) | (flags & NO_SLEEP)
    ac.set_place(rec, 0, target, radius)
    return rec


def _new_person(gd, pr, who, face, faction, pkids):
    import factionfolk as ff
    edid, name, _sex, wears, _floor = NEW[who]
    g = dict(ff.GROUPS['court_fighter'])
    g['package'] = 'DefaultStayAtEditorLocation'
    items = [(it, 1) for it in (PP._item_key(gd, pr, n) for n in wears) if it]
    rec = ff.person(gd, pr, face, edid, name, g, items, [], faction)
    ff._set_num(rec, 'AIDT', 'Aggression', 1)
    ff._set_num(rec, 'AIDT', 'Confidence', 3)
    _set_pkids(rec, pkids)
    return rec


def _set_pkids(rec, pkids, keep=()):
    import api_characters as ac
    at = next((i for i, s in enumerate(rec['subs']) if s['tag'] == 'PKID'), None)
    rec['subs'] = [s for s in rec['subs'] if s['tag'] != 'PKID']
    subs = [{'tag': 'PKID', 'label': 'AI package', 'kind': 'F', 'value': k} for k in list(pkids) + list(keep)]
    if at is None:
        for s in subs:
            ac.insert(rec, s)
    else:
        rec['subs'][at:at] = subs


def _pick_faces(gd, pr):
    pools = PP._faces(gd, pr)
    used, out = set(), {}
    for n, k in enumerate(NEW):
        sex = NEW[k][2]
        order = RACES[n % len(RACES):] + RACES[:n % len(RACES)]
        face = next((f for race in order for f in pools[sex].get(race, ()) if gd.key(f) not in used), None)
        if face is None:
            raise ValueError('no free face left for %s' % NEW[k][0])
        used.add(gd.key(face))
        out[k] = face
    return out


def _quest_vars(pr):
    """{which: (quest key, {variable: index})} of the activities' quests."""
    out = {}
    for w, edid in PP.QUESTS.items():
        q = PP._mod_key(pr, edid, 'QUST')
        s = recordio.field(pr.records[q], 'SCRI')
        out[w] = (q, PP._vars(pr.records[s]))
    return out


def _person_key(pr, who, new):
    if who in new:
        return new[who]
    return PP._mod_key(pr, PP.PEOPLE[who][0], 'NPC_')


def apply(pr, gd, P=None):
    import api_quests as aq
    import piratedeal
    import questrec as qr
    import waikikilife
    from activity import _new_key
    P = P or plan(gd, pr)
    if P['skipped']:
        raise ValueError('; '.join(P['skipped']))
    S, T = P['spots'], P['spots']['targets']
    out, rep = [], {'made': [], 'skipped': []}

    def record(rec, k=None):
        k = k or _new_key(pr)
        out.append({'op': 'record', 'key': k, 'record': rec})
        rep['made'].append(recordio.field(rec, 'EDID'))
        return k
    traders = PP._mod_key(pr, 'FOLabPirateTraders', 'FACT')
    # the days' packages, one per (who, step), shared where two have the same day
    packs, shared = {}, {}
    for who, day in DAYS.items():
        for n, (kind, tgt, hour, hours, radius, flags) in enumerate(day):
            sig = (kind, tgt, hour, hours, radius, flags)
            if sig not in shared:
                src = 'DefaultSleepAlways256' if kind == 'sleep' else 'DefaultSandboxEditorLocation256'
                edid = 'FOLabPearl%s%s%sR%d' % (kind.capitalize(), ''.join(p.capitalize() for p in tgt.split('_')),
                                               '' if hour < 0 else '%02dx%d' % (hour, hours), radius)
                shared[sig] = record(_pack(gd, src, edid, hour, hours, T[tgt][1], radius, flags))
            packs.setdefault(who, []).append(shared[sig])
    # the new people
    faces = _pick_faces(gd, pr)
    new = {}
    for who in NEW:
        new[who] = record(_new_person(gd, pr, who, faces[who], traders, packs[who]))
    import api_characters as ac
    bk = next(o['record'] for o in out if o['op'] == 'record' and o['key'] == new['barkeep'])
    trudy = recordio.load(gd, piratedeal._game(gd, BAR_FROM, 'NPC_'))
    ac.set_num(bk, 'AIDT', 'Services', int(ac.num(trudy, 'AIDT', 'Services')) or 0x14)
    ac.set_num(bk, 'ACBS', 'Barter gold', BARTER_GOLD)
    chest = recordio.load(gd, piratedeal._game(gd, BAR_CHEST, 'CONT'))
    chest.pop('copied_from', None)
    chest['src'] = ''
    recordio.set_field(chest, 'EDID', 'FOLabPearlBarChest', label='Editor ID')
    chest_key = record(chest)
    # the activities' people: their days first, and the scavenger's empty faction out
    for who in ('scav', 'boss', 'dealer', 'deck1', 'deck2'):
        k = PP._mod_key(pr, PP.PEOPLE[who][0], 'NPC_')
        rec = json.loads(json.dumps(pr.records[k]))
        had = [s['value'] for s in rec['subs'] if s['tag'] == 'PKID']
        keep = [] if who in REPLACE else had
        _set_pkids(rec, packs[who], keep)
        if who == 'scav':
            rec['subs'] = [s for s in rec['subs'] if not (s['tag'] == 'SNAM' and not _snam_faction(s))]
        out.append({'op': 'record', 'key': k, 'record': rec})
        rep['made'].append(PP.PEOPLE[who][0] + ' (its day)')
    # placed: the new people, the bar's chest under the barkeep
    chest_ref = _new_key(pr)
    bx, by, bz, _rz = S['barkeep']['p']
    out.append({'op': 'place', 'cell': S['barkeep']['cell'], 'key': chest_ref,
                'ref': {'base': chest_key, 'p': [bx, by, round(bz - CHEST_UNDER, 1), 0.0, 0.0, 0.0], 's': 1.0, 'persistent': True}})
    for who in NEW:
        x, y, z, rz = S[who]['p']
        ref = {'base': new[who], 'p': [x, y, z, 0.0, 0.0, rz], 's': 1.0, 'persistent': True, 'edid': NEW[who][0] + 'Ref'}
        if who == 'barkeep':
            ref['merchant'] = chest_ref
        out.append({'op': 'place', 'cell': S[who]['cell'], 'key': _new_key(pr), 'ref': ref})
    # the quest and its topics
    qkey = _new_key(pr)
    quest = qr.quest_record({'edid': QUEST, 'script': '', 'name': QUEST_NAME, 'flags': {'start_enabled': True}, 'priority': PRIORITY,
                             'delay': None, 'stages': [], 'objectives': []})
    out.append({'op': 'record', 'key': qkey, 'record': quest})
    tkeys = {}
    for t, (edid, prompt) in TOPICS.items():
        tkeys[t] = record(qr.topic_record({'edid': edid, 'name': prompt, 'priority': 50.0, 'kind': 0, 'flags': {'top_level': True},
                                           'quests': [{'quest': qkey, 'links': []}]}))
    V = _quest_vars(pr)
    lines = []
    for who, topic, words, conds in lines_spec():
        tp = qr.GREETING if topic == 'G' else tkeys[topic]
        cc = [PP._cond(79, op, v, V[w][0], V[w][1][var]) for w, var, op, v in conds]
        l = aq.new_line_plain(gd, pr, tp, qkey, _person_key(pr, who, new), W[words], conditions=cc)
        if topic == 'trade':
            l['end'] = {'source': 'ShowBarterMenu', 'parts': None}
        l.setdefault('begin', None)
        l.setdefault('end', None)
        lines.append(l)
    forms = PP._forms(gd, pr, {}, {x['key']: x['record'] for x in out if x['op'] == 'record'})
    compiled = []
    for l in lines:
        errors = aq.compile_line(l, forms)
        if errors:
            raise ValueError('%s: %s (%s)' % (errors[0]['where'], errors[0]['message'], l['responses'][0]['text'][:40]))
        compiled.append(qr.info_record(l))
    pr.apply(LABEL, out + [{'op': 'record_new', 'record': r} for r in compiled])
    rep.update({'lines': len(compiled), 'new people': {w: NEW[w][0] for w in NEW}, 'packages': len(shared),
                'faces': {w: gd.key(faces[w]) for w in NEW}, 'reach': S.get('reach')})
    del waikikilife
    return rep


def _snam_faction(s):
    if 'fields' in s:
        return next((f.get('value') for f in s['fields'] if f.get('name') == 'Faction'), '')
    return s.get('value')


# ---------- who has something to say ----------

def talks():
    """[(who, state)] where someone of the Pearl or the boatyard would have no greeting: the activities' greetings
    (pinkpearl.lines_spec) and this step's, tried over every state the quests' variables they test can be in."""
    import itertools
    mine = [(w, cs) for w, t, _k, cs in lines_spec() if t == 'G']
    theirs = []
    for who, topic, _w, conds, _e, _s, _c in PP.lines_spec():
        if topic != 'G':
            continue
        cs = [(c[1], c[2], c[3], c[4]) for c in conds if c[0] == 'q']
        if any(c[0] != 'q' for c in conds):             # (an item, a skill or a perk: may not hold)
            continue
        theirs.append((who, cs))
    values = {('cells', 'met'): (0, 1), ('cells', 'resolved'): (0, 1, 2), ('boy', 'started'): (0, 1),
              ('boy', 'freed'): (-1, 0, 1, 4), ('boy', 'sailed'): (0, 1), ('boy', 'rewarded'): (0, 1), ('storm', 'on'): (0, 1)}
    names = list(values)
    ops = {'==': lambda a, b: a == b, '!=': lambda a, b: a != b, '>': lambda a, b: a > b, '<': lambda a, b: a < b,
           '>=': lambda a, b: a >= b, '<=': lambda a, b: a <= b}
    holds = lambda cs, st: all(ops[op](st.get((w, var), 0), v) for w, var, op, v in cs)
    who_all = set(PP.PEOPLE) | set(NEW)
    silent = []
    for combo in itertools.product(*(values[n] for n in names)):
        st = dict(zip(names, combo))
        for who in sorted(who_all):
            if who == 'guard' and (st[('boy', 'started')] == 0 or st[('boy', 'freed')] == -1):
                continue                                # (he's switched on with the quest and off when the boat sails)
            if not any(holds(cs, st) for w, cs in mine + theirs if w == who):
                silent.append((who, st))
    return silent
