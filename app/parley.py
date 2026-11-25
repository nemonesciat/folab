"""Parley on the road (docs/waikiki-speech-science.md, section J system 1, F1's kinds of talk; the user, 25 Nov 2026: "it
would be nice to have the option to use it if you were low on bullets or stimpacks, or didn't feel like dealing with
pirates ... it has to have a tradeoff when used all the time").

**Who:** pirate groups on the coast road in the pirates' land, by the concept map (territory.py).
- Roadside pairs activity.py stood there are kept and become parley groups. Pairs standing in another side's land (all
  six on 25 Nov 2026 stood in the court's, by the wall) are taken out.
- `SITES` groups in all: the rest are new, a leader and crew, on the coast road. They stand on a navmesh, `SITE_APART`
  apart, clear of doors, the trail's signposts, the Kahala's hotel and the two pirate traders (`CLEAR_OF`), and
  `START_CLEAR` from Hanauma.
- One of each pair is the group's leader: a record of its own (its own voice), with a script that stops you
  (StartConversation) when you come within `HAIL` and the group hasn't let you by today.
- The other is crew in FOLabParleyPirates: neutral to you until it comes to a fight, allied to the Fiends, tied to the
  Pirates' reputation (killing them is infamy), helping its leader.

**What you can do** (F1's kinds, each with its cost on the pirates' hidden score, repstanding.py):

| Choice | Check | Pass | Fail |
|---|---|---|---|
| "I'm with the trade ground. Let me by." | Speech 40 (persuade) | waved through; standing kept | they fight |
| "Step aside, or you go in the water." | Speech 55, or 40 with a weapon out (intimidate) | they back off; feared +5 | they fight |
| "Fine. Take it." | 1 Stimpak, 2 if they think you a soft touch (pay) | through; soft touch -5 | nothing to give: they fight |
| "Please. I've got nothing worth taking." | Speech 25 (plead) | through, mocked; soft touch -8 | they fight |
| "No." | - | they fight | - |

- **The corners of the score:**
  - feared (the top band): the leader waves you through with no toll;
  - a soft touch (the two low bands): the toll is doubled and they sneer.
- **Winning the fight raises the score** (repstanding counts their dead; the step adds the new records to its count).
- **Once a group lets you by, it leaves you alone that game day.**

All lines are voiced in the step (VOICE). None says goodbye (a closing line's script may not run).

    plan(gd, pr)       {'rows': [{'leader', 'crew', 'p'}], 'skipped'}
    apply(pr, gd, P)   one Undo: records, the swaps, the lines; FOLabNameOnWater's count made again
"""
import json
import math
import struct

import recordio

LABEL = 'Parley on the road'
VOICE = ['FOLabParley']
QUEST, FACTION = 'FOLabParley', ('FOLabParleyPirates', 'Pirates')
ROADSIDE = 'FOLabPirateRoadside'
PAIR = 900.0                    # (two roadside pirates this near are one group)
HAIL = 600.0
GO_ON = 1                       # (game days a group leaves you alone once it let you by)
SPEECH, STRENGTH = 43, 5        # (actor values the conditions compare)
PERSUADE, INTIMIDATE, INTIMIDATE_ARMED, PLEAD = 40, 55, 40, 25
FEAR, PAID, BEGGED = 5, -5, -8
WORDS = {
    'hold': "Hold there! Road toll. Pay up, or swim.",
    'hold_soft': "Look who it is. Toll's doubled for you, soft touch.",
    'hold_feared': "You. Go on through. No toll for you.",
    'persuade': "I'm with the trade ground. Let me by.",
    'persuade_yes': "[SUCCEEDED] Trade ground, huh. Fine. Move along.",
    'persuade_no': "[FAILED] Nobody here knows you. Get them!",
    'intimidate': "Step aside, or you go in the water.",
    'intimidate_yes': "[SUCCEEDED] Easy. Easy. Road's yours.",
    'intimidate_no': "[FAILED] Big talk. Let's see you swim.",
    'pay': "Fine. Take it.",
    'pay_one': "Smart. Go on.",
    'pay_two': "Two. That's the soft touch rate. Go on.",
    'pay_none': "You've got nothing? Then you've got trouble.",
    'plead': "Please. I've got nothing worth taking.",
    'plead_yes': "[SUCCEEDED] Ha! Go on, beggar. Tell your friends.",
    'plead_no': "[FAILED] Then you're worth nothing to us either.",
    'refuse': "No.",
    'refuse_yes': "Wrong answer.",
}


def _mod_key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and recordio.field(r, 'EDID') == edid), None)


SITES = 6                       # (parley groups on the pirates' coast road)
SITE_APART = 9000.0
CLEAR_OF = (('FOLabHotelKahalaReef', 3000.0), ('FOLabPirateTraderKahala', 3000.0), ('FOLabPirateTraderMarina', 3000.0))
MARKERS_CLEAR = (("Makapu'u Gate", 9000.0), ("Settlers' Watchtower", 9000.0), ('Border Post', 9000.0), ("Crow's Nest", 3000.0),
                 ('Koko Marina', 3000.0), ('Kahala Reef', 3000.0))   # (off the Huang's posts, and not on the pirates' own camps)
START_CLEAR = 15000.0           # (from where the game starts: nothing hostile near Hanauma)
CREW_TOO = 1                    # (crew with each new leader)


def _ed(pr, b):
    return recordio.field(pr.records[b], 'EDID') if b in pr.records else ''


def plan(gd, pr):
    """The roadside pairs (activity.py's): kept and made parley groups where they stand in the pirates' land (the concept
    map), taken out where they don't. New groups on the coast road in the pirates' land make up `SITES`."""
    import factionfolk as ff
    import robots
    import secretcaches
    import territory
    import waikikilife as WL
    base = _mod_key(pr, ROADSIDE, 'NPC_')
    mk = ff._markers(pr)
    if 'The Royal Hawaiian' not in mk:
        return {'rows': [], 'skipped': [('parley', 'no Royal Hawaiian marker (the world)')]}
    world = gd.ext_cells[gd.from_key(mk['The Royal Hawaiian'][0])]
    T = territory.Map(gd, world)
    if not T.ok:
        return {'rows': [], 'skipped': [('parley', "the concept map can't be read (PIL)")]}
    refs = [(ck, rk, r['p']) for ck, c in pr.cells.items() if not ck.startswith('+')
            for rk, r in (c.get('refs') or {}).items() if base and r.get('base') == base and not r.get('removed') and r.get('p')]
    refs.sort(key=lambda t: (round(t[2][0]), round(t[2][1])))
    rows, used, remove = [], set(), []
    for ck, rk, p in refs:
        if rk in used:
            continue
        mate = next(((c2, r2, p2) for c2, r2, p2 in refs if r2 not in used and r2 != rk and math.hypot(p2[0] - p[0], p2[1] - p[1]) < PAIR), None)
        used.add(rk)
        crew = []
        if mate:
            used.add(mate[1])
            crew.append((mate[0], mate[1]))
        if T.holder(p[0], p[1]) == 'pirates':
            rows.append({'leader': (ck, rk), 'crew': crew, 'p': [round(v) for v in p[:3]]})
        else:
            remove.append({'refs': [(ck, rk)] + crew, 'p': [round(v) for v in p[:3]], 'holder': T.holder(p[0], p[1])})
    road = [r['p'] for _c, _k, r in secretcaches._outside_refs(gd, pr, lambda r: 'road' in _ed(pr, r.get('base', '')).lower()
                                                               and _ed(pr, r.get('base', '')).startswith('FOLab'))]
    clear = []
    for e, d in CLEAR_OF:
        k = _mod_key(pr, e)
        if k:
            clear += [(r['p'], d) for _c, _k, r in secretcaches._outside_refs(gd, pr, lambda r, k=k: r.get('base') == k)]
    start = mk.get('Hanauma Bay', (None, None))[1]
    posts = [r['p'] for _c, _k, r in secretcaches._outside_refs(gd, pr, lambda r: _ed(pr, r.get('base', '')) == secretcaches.TRAIL_POST)]
    sp = WL.Spots(gd, pr, world)
    sp.taken = ff._standing(gd, pr)
    sp.gd, sp.pr, sp.grid = gd, pr, gd.grid(world)
    taken = [r['p'][:2] for r in rows]
    away = [(mk[n][1], d) for n, d in MARKERS_CLEAR if n in mk]
    # (the road's points in the pirates' land, clear of what they must stay off; then picked far apart, the farthest from
    #  those taken first, so the groups spread over the Kahala and Hawaii Kai rather than bunching at one end)
    cands = [p for p in road if T.holder(p[0], p[1]) == 'pirates'
             and not (start and math.hypot(p[0] - start[0], p[1] - start[1]) < START_CLEAR)
             and not any(math.hypot(p[0] - q[0], p[1] - q[1]) < d for q, d in clear + away)]
    while cands and len(rows) < SITES:
        p = max(cands, key=lambda p: min((math.hypot(p[0] - a, p[1] - b) for a, b in taken), default=-math.hypot(p[0], p[1])))
        cands.remove(p)
        x, y = p[0], p[1]
        if any(math.hypot(x - a, y - b) < SITE_APART for a, b in taken):
            continue
        doors = robots._outside_doors(gd, pr, sp.grid, {'a': (x, y)})
        spots = [s for s in ff._near(sp, x, y, 4, radii=(350, 500, 650), turns=10)
                 if secretcaches._clear(gd, pr, sp, s[0], s[1], doors, posts) and T.holder(s[0], s[1]) == 'pirates']
        if len(spots) < 1 + CREW_TOO:
            continue
        rows.append({'new': [(round(s[0], 1), round(s[1], 1), round(s[2] + 4, 1), round(math.atan2(x - s[0], y - s[1]), 4))
                             for s in spots[:1 + CREW_TOO]],
                     'p': [round(x), round(y), round(p[2])],
                     'near': {'door': round(min((math.hypot(x - d[0], y - d[1]) for d in doors), default=1e9)),
                              'start': round(math.hypot(x - start[0], y - start[1])) if start else None,
                              'markers': {n: round(math.hypot(x - q[0], y - q[1])) for (q, _d), (n, _dd) in zip(away, MARKERS_CLEAR) if n in mk}}})
        taken.append((x, y))
    skipped = [] if len(rows) >= SITES else [('parley', 'room for %d of %d groups' % (len(rows), SITES))]
    return {'rows': rows, 'remove': remove, 'skipped': skipped, 'world': gd.key(world)}


def _cond(fn, op, value, p1=0, p2=0, run=0, orr=False):
    return {'or': orr, 'use_target': False, 'op': op, 'fn': fn, 'p1': p1, 'p2': p2, 'run': run, 'ref': '', 'value': float(value)}


def _vars(srec):
    out, last = {}, None
    for sub in srec['subs']:
        if sub['tag'] == 'SLSD':
            last = next(f['value'] for f in sub['fields'] if f.get('name') == 'Index')
        elif sub['tag'] == 'SCVR' and last is not None:
            out[sub['value'].lower()] = last
    return out


def ops(gd, pr, P=None):
    import api_characters as ac
    import api_quests as aq
    import api_scripts
    import factionfolk as ff
    import piratedeal
    import questrec as qr
    import repstanding as RS
    from activity import _new_key
    if _mod_key(pr, QUEST, 'QUST'):
        raise ValueError('the mod already has %s (Undo first)' % QUEST)
    P = P or plan(gd, pr)
    rows = P['rows']
    if not rows:
        raise ValueError('nothing to parley with: %s' % P['skipped'])
    grid = gd.grid(gd.from_key(P['world'])) if P.get('world') else None
    cell = lambda x, y: gd.key(grid[(int(x // 4096), int(y // 4096))])
    stand_q = _mod_key(pr, RS.QUEST, 'QUST')
    stand_s = _mod_key(pr, RS.SCRIPT, 'SCPT')
    if not stand_q or not stand_s:
        raise ValueError('the standing step (repstanding) first')
    out, rep = [], {'made': [], 'groups': len(rows), 'skipped': P['skipped']}

    def record(k, rec):
        out.append({'op': 'record', 'key': k, 'record': rec})
        rep['made'].append(recordio.field(rec, 'EDID'))
        return k
    # the faction: neutral to you, allied to the Fiends, the Pirates' reputation
    fac = ff._faction(gd, *FACTION)
    fac['subs'].insert(2, {'tag': 'XNAM', 'label': 'Relation', 'kind': 'struct', 'fields': [
        {'name': 'Faction', 'code': 'F', 'value': gd.key(piratedeal._game(gd, piratedeal.FIENDS, 'FACT'))},
        {'name': 'Modifier', 'code': 'i', 'value': 0}, {'name': 'Group combat reaction', 'code': 'I', 'value': 2}]})
    rep_p = _mod_key(pr, piratedeal.REPS['pirates'][0], 'REPU')
    if rep_p:
        fac['subs'].append({'tag': 'WMI1', 'label': 'Reputation', 'kind': 'F', 'value': rep_p})
    fac_key = record(_new_key(pr), fac)
    base = _mod_key(pr, ROADSIDE, 'NPC_')

    def pirate(edid, name, script=None):
        rec = json.loads(json.dumps(pr.records[base]))
        rec['src'] = ''
        recordio.set_field(rec, 'EDID', edid, label='Editor ID')
        recordio.set_field(rec, 'FULL', name) if any(s['tag'] == 'FULL' for s in rec['subs']) else \
            ac.insert(rec, {'tag': 'FULL', 'label': 'Name', 'kind': 'z', 'value': name})
        rec['subs'] = [s for s in rec['subs'] if s['tag'] not in ('SNAM', 'SCRI')]
        ff._set_num(rec, 'ACBS', 'Template flags', ff._num(rec, 'ACBS', 'Template flags') & ~0x04 & ~0x200)   # (own factions, own script)
        ac.insert(rec, ff._set_link(ff._sub('NPC_', 'SNAM', struct.pack('<IB3s', 0, 0, b'\0\0\0')), fac_key))
        if script:
            ac.insert(rec, {'tag': 'SCRI', 'label': 'Script', 'kind': 'F', 'value': script})
        ff._set_num(rec, 'AIDT', 'Aggression', 1)
        ff._set_num(rec, 'AIDT', 'Assistance', 1)
        return rec
    crew_key = record(_new_key(pr), pirate(ROADSIDE + 'Parley', 'Pirate'))
    # the quest: one variable a group (the day it next stops you)
    quest_key, qscript_key = _new_key(pr), _new_key(pr)
    quest = qr.quest_record({'edid': QUEST, 'script': qscript_key, 'name': '', 'flags': {'start_enabled': True},
                             'priority': 60, 'delay': 5.0, 'stages': [], 'objectives': []})
    sc = api_scripts.scripts()
    qsrc = '\n'.join(['scn FOLabParleyScript'] + ['float until%d' % n for n in range(len(rows))] + ['', 'Begin GameMode', 'End', ''])
    c = sc.compile(qsrc, qscript_key, 'quest', {quest_key: quest})
    if not hasattr(c, 'subrecords'):
        raise ValueError('the parley script: %s' % (c,))
    qrec = sc._record_of(c, 'FOLabParleyScript')
    record(qscript_key, qrec)
    record(quest_key, quest)
    qvars = _vars(qrec)
    svars = _vars(pr.records[stand_s])
    # each group's leader: a record of its own, its script stopping you
    hold = _new_key(pr)
    record(hold, qr.topic_record({'edid': 'FOLabParleyHold', 'name': '', 'priority': 50.0, 'kind': 0,
                                  'quests': [{'quest': quest_key, 'links': []}]}))
    choice = {}
    for k in ('persuade', 'intimidate', 'pay', 'plead', 'refuse'):
        choice[k] = _new_key(pr)
        record(choice[k], qr.topic_record({'edid': 'FOLabParley%s' % k.capitalize(), 'name': WORDS[k], 'priority': 50.0, 'kind': 0,
                                           'quests': [{'quest': quest_key, 'links': []}]}))
    leaders = []
    for n, row in enumerate(rows):
        lscript, lkey = _new_key(pr), _new_key(pr)
        src = '\n'.join(['scn FOLabParleyLeader%02dScript' % (n + 1), '', 'Begin GameMode',
                         '\tif GetDead == 0 && GetDistance player < %d && GameDaysPassed > %s.until%d' % (HAIL, QUEST, n),
                         '\t\tif IsInCombat == 0', '\t\t\tset %s.until%d to GameDaysPassed + %d' % (QUEST, n, GO_ON),
                         '\t\t\tStartConversation player FOLabParleyHold', '\t\tendif', '\tendif', 'End', ''])
        cc = sc.compile(src, lscript, 'object', {quest_key: quest, qscript_key: qrec, hold: {'type': 'DIAL', 'subs': [
            {'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': 'FOLabParleyHold'}]}})
        if not hasattr(cc, 'subrecords'):
            raise ValueError('a leader\'s script: %s' % (cc,))
        record(lscript, sc._record_of(cc, 'FOLabParleyLeader%02dScript' % (n + 1)))
        record(lkey, pirate('FOLabParleyLeader%02d' % (n + 1), 'Road Boss', lscript))
        leaders.append(lkey)
        if row.get('new'):                      # (a new group on the coast road)
            for j, (x, y, z, rz) in enumerate(row['new']):
                out.append({'op': 'place', 'cell': cell(x, y), 'key': _new_key(pr),
                            'ref': {'base': lkey if j == 0 else crew_key, 'p': [x, y, z, 0.0, 0.0, rz], 's': 1.0}})
        else:
            out.append({'op': 'swap', 'cell': row['leader'][0], 'ref': row['leader'][1], 'base': lkey})
            for ck, rk in row['crew']:
                out.append({'op': 'swap', 'cell': ck, 'ref': rk, 'base': crew_key})
    for g in P.get('remove', ()):               # (roadside pairs out of the pirates' land: taken out)
        for ck, rk in g['refs']:
            out.append({'op': 'remove', 'cell': ck, 'ref': rk})
    rep['removed'] = sum(len(g['refs']) for g in P.get('remove', ()))
    rep['new_groups'] = sum(1 for r in rows if r.get('new'))
    # FOLabNameOnWater counts these pirates' dead too: its script made again (its variables keep their numbers)
    pirates = sorted(set(RS.pirate_bases(pr)) | {ROADSIDE + 'Parley'} | {'FOLabParleyLeader%02d' % (n + 1) for n in range(len(rows))})
    extra = {k: r for r in [] for k in ()}
    for o in out:
        if o['op'] == 'record':
            extra[o['key']] = o['record']
    c2 = sc.compile(RS.script_source(pirates), stand_s, 'quest', extra)
    if not hasattr(c2, 'subrecords'):
        raise ValueError('the standing script again: %s' % (c2,))
    out.append({'op': 'record', 'key': stand_s, 'record': sc._record_of(c2, RS.SCRIPT)})
    # the lines, per leader (each says its own; a day's passage set on that group's variable)
    speech = gd.key(next(f for f, (i, r) in gd.forms.items() if r.tag == 'AVIF' and gd.edid(f) == 'AVSpeech'))
    stim = gd.key(piratedeal._game(gd, 'Stimpak', 'ALCH'))
    band = lambda op, v: _cond(79, op, v, stand_q, svars['bandpirates'])
    lines = []

    def line(topic, who, words, conds=(), end='', skill=False, choices=()):
        l = aq.new_line_plain(gd, pr, topic, quest_key, who, words, conditions=list(conds))
        if skill:
            l['skill'] = speech
        if end:
            l['end'] = {'source': end, 'parts': None}
        l['choices'] = list(choices)
        lines.append(l)
    fight = 'StartCombat player'
    for n, who in enumerate(leaders):
        all5 = [choice[k] for k in ('persuade', 'intimidate', 'pay', 'plead', 'refuse')]
        line(hold, who, WORDS['hold_feared'], [band('>=', 4)])
        line(hold, who, WORDS['hold_soft'], [band('<=', 1)], choices=all5)
        line(hold, who, WORDS['hold'], [], choices=all5)
        sp = lambda op, v: _cond(14, op, v, SPEECH, 0, 1)
        line(choice['persuade'], who, WORDS['persuade_yes'], [sp('>=', PERSUADE)], skill=True)
        line(choice['persuade'], who, WORDS['persuade_no'], [sp('<', PERSUADE)], fight, skill=True)
        line(choice['intimidate'], who, WORDS['intimidate_yes'], [sp('>=', INTIMIDATE)], RS.bump('pirates', FEAR), skill=True)
        line(choice['intimidate'], who, WORDS['intimidate_yes'], [sp('>=', INTIMIDATE_ARMED), _cond(101, '=', 1, 0, 0, 1)],
             RS.bump('pirates', FEAR), skill=True)
        line(choice['intimidate'], who, WORDS['intimidate_no'], [], fight, skill=True)
        line(choice['pay'], who, WORDS['pay_two'], [band('<=', 1), _cond(47, '>=', 2, stim, 0, 1)],
             'player.RemoveItem Stimpak 2\n' + RS.bump('pirates', PAID))
        line(choice['pay'], who, WORDS['pay_one'], [band('>', 1), _cond(47, '>=', 1, stim, 0, 1)],
             'player.RemoveItem Stimpak 1\n' + RS.bump('pirates', PAID))
        line(choice['pay'], who, WORDS['pay_none'], [], fight)
        line(choice['plead'], who, WORDS['plead_yes'], [sp('>=', PLEAD)], RS.bump('pirates', BEGGED), skill=True)
        line(choice['plead'], who, WORDS['plead_no'], [sp('<', PLEAD)], fight, skill=True)
        line(choice['refuse'], who, WORDS['refuse_yes'], [], fight)
    rep['lines'] = len(lines)
    rep['leaders'] = len(leaders)
    rep['pirates_counted'] = len(pirates)
    return out, rep, lines


def apply(pr, gd, P=None):
    import api_quests as aq
    o, rep, lines = ops(gd, pr, P)
    pr.apply(LABEL, o)
    pr.apply(LABEL, [{'op': 'record_new', 'record': aq._compiled_line(gd, pr, l)} for l in lines], merge=True)
    return rep
