"""First bearings (the user, 26 Nov 2026 ~07:20: "there should be some more stuff that happens right near the start ... on the
road at that refugee camp, someone should approach you and start a quest or something. give a warning about the flotilla?
the hotel? is that safe or hostile? what is the deal here? there needs to be a little flow from the beginning to the
first bearings").

A surfer of the camp on the way down from Hanauma Bay to the Pink Pearl (`CAMP_AT`: the camp with people the user walks into) walks up the
first time you come near (`HAIL_NEAR`: the quest's script asks for the talk, StartConversation, again every `RETRY` seconds
of play, `TRIES` times, never in combat) and says where you are. What's true, as the plugin has it:
- **the Pink Pearl** down the shore is the boat crews' hotel and their trade ground: its people (FOLabPirateTraders) don't
  fight anyone not their enemy, so keep your weapon down and they deal; work there (the boatyard hand's crate, storm nights);
- **the Flotilla** out on the water attacks on sight (the Fiends' factions) and takes people (decided): stay off its boats;
- **Waikiki** west along the coast road, the court's peace (no raids: the king's bargain, decided);
- **Kuliʻouʻou**, the first camp up the road (people are sold there: decided);
- **the beachcomber** at Hanauma, if you haven't met him ("What the Sea Brought In" not begun).
Each shows its map marker (ShowMap): the Pearl, Koko Marina, Kuliʻouʻou's camp, the Royal Hawaiian.

How you answer (the hail's choices): curious, wary, rude (a short warning and done), Intimidate (FOLabTraitThreat
`THREAT`: frightened, everything at once and what kala they have), Speech (FOLabTraitTalk `TALK`: they ask a favour
straight out, and pay more). Traits come first: Dread Name, frightened and brief; Captain's Kin, sent to Waikiki; Raised
on the Boats, warned the Flotilla will want you back.

The errand (stage 20): the camp has no clean water. Ways through: bring `WATER_N` Purified Water (`PAY` kala, `PAY_TALK`
if Speech asked; the Pink Pearl sells water); Barter `BARTER` for `PAY_BARTER`; Survival `SURVIVAL`, show them how to catch
and boil rain (`PAY_TAUGHT` and their thanks); refuse (the quest closes). Done, they send you on: the boatyard hand at Koko
Marina ("The Boatyard's Cells"), the beachcomber if not met ("What the Sea Brought In"), Kuliʻouʻou ("The First Place on the
Way"). Nothing about them is new.

Koko Marina Refugee Camp, named on the map and empty, gets `REFUGEES` of the mod's own (faces nobody wears, the island
surfers' clothing lists), sandboxing by its fire, saying what the island's people say: People worth talking to's island
lines copied with them as speakers (the same compiled lines; only their voices are new: VOICE_ONLY).

    plan(gd, pr)       {'rows', 'skipped', 'spots'}
    apply(pr, gd, P)   one Undo (VOICE, VOICE_ONLY: only this step's new lines)
    routes()           every way through, on the lines' own conditions and end scripts and the quest script's steps
"""
import json
import math
import re

import recordio

LABEL = 'First bearings'
QUEST, QUEST_NAME, SCRIPT = 'FOLabFirstBearings', 'First Bearings', 'FOLabFirstBearingsScript'
PERSON, PERSON_NAME = 'FOLabBearingsSurfer', 'Surfer'
REF = 'FOLabBearingsSurferREF'
SURFER = 'FOLabSurferVSpawnProspectorAll'     # (the island's surfers: their clothing lists are what these wear)
REFUGEES = [('FOLabKokoRefugee1', 'M'), ('FOLabKokoRefugee2', 'F'), ('FOLabKokoRefugee3', 'M'), ('FOLabKokoRefugee4', 'F')]
REFUGEE_NAME, REFUGEE_CAMP = 'Refugee', 'Koko Marina Refugee Camp'
TALK_QUEST, ISLAND = 'FOLabPeopleTalk', 'island'     # (People worth talking to: its island lines, copied to the refugees)
VOICE = [QUEST, TALK_QUEST]
VOICE_ONLY = None
REUSE_FROM = r'D:\FOLab-held\home14'     # (the rehearsal's FOLab home: its takes, by line words, onto these lines)
CAMP = 'the surfer camp above the Pink Pearl'
CAMP_AT = (84500.0, -31400.0)   # (the story session's pick, 26 Nov: the last camp before the shore and the hotel, coming down
                                #  from the start; FOLab's tarp shelter, bedrolls, a crafting campfire; no map marker)
CANDIDATES = {'tarp above the Pearl': (84747, -31500), 'tarp past the Pearl': (82094, -38277), 'Koko Marina Refugee Camp': (91776, -28452)}
START = 'WaikikiNewGameStart'
HAIL_NEAR, RETRY, TRIES = 1500, 6, 3
WATER, WATER_N = 'WaterPurified', 3
KALA = 'Caps001'
PAY, PAY_TALK, PAY_BARTER, PAY_TAUGHT, SCARED = 25, 35, 40, 10, 10
THREAT, TALK, BARTER, SURVIVAL = 40, 35, 40, 40
TALK_G, THREAT_G = 'FOLabTraitTalk', 'FOLabTraitThreat'
TRAITS = {'dread': 'FOLabTraitDreadName', 'kin': 'FOLabTraitCaptainsKin', 'boats': 'FOLabTraitRaisedOnTheBoats'}
SEA = 'FOLabSeaBroughtIn'
PEARL_KEEP = 'FOLabPearlBarkeep'
MARKERS = {'pearl': 'Pink Pearl Hotel', 'marina': 'Koko Marina', 'camp': "Kuliouou Squatters' Camp", 'west': 'The Royal Hawaiian'}

W = {
    'hail': "Hey! You came over the hill from the bay? You look half drowned. Hold up. You'll want to know where you are before you walk into it.",
    'hail_dread': "Please. I don't want trouble. I'll tell you anything you want, just keep that away from me.",
    'hail_kin': "Wait. You've got the look of a captain's people. Then don't stop here. Go west to Waikiki. The court will want to see you.",
    'hail_boats': "You've got the walk of the boats. Listen to me. The Flotilla will want you back. Boat-born don't get to leave.",
    'where': "Where am I?",
    'where_r': "Koko Head. The coast road runs by this camp, west to Waikiki and east round to the Huang. Ask what you need to.",
    'wary': "Stay back. What do you want?",
    'wary_r': "Easy. I'm not with the boats. Just surf and fish, same as everybody at this fire. Ask, and I'll tell you what I know.",
    'rude': "Out of my way.",
    'rude_r': "Fine. Walk into the Flotilla's arms, then. Waikiki's west, if you live that long.",
    'threat': "Talk. Fast.",
    'threat_yes': "All right! The hotel down the shore's the boat crews', neutral if you're peaceful. The Flotilla takes people. Waikiki's west. Here, it's all the kala I have.",
    'threat_no': "You don't scare me. I've seen pirates up close. Ask nicely, or don't ask.",
    'need': "You look like you need something.",
    'need_r': "Sharp eyes. We've no clean water at this camp. Bring us three bottles and I'll pay what we've got, and more for asking kindly.",
    'pearl': "The hotel down the shore?",
    'pearl_r': "The Pink Pearl. The boat crews' hotel, and their trade ground. Keep your weapon down and they'll deal with you. Draw it and they won't.",
    'pearl_work': "There's work round there. The boatyard hand at Koko Marina has lost something. When a big storm comes, the crews pile into the Pearl.",
    'boats': "The boats out on the water?",
    'boats_r': "The Flotilla. Ships lashed together out past the reef. Stay off its boats and out of its camps. It takes people. It doesn't give them back.",
    'west': "Which way is safe?",
    'west_r': "West, along the coast road, past Koko Marina, all the way to Waikiki. The court keeps the peace there. Nobody raids Waikiki.",
    'camp': "Where can I rest?",
    'camp_r': "Kuliouou, up the coast road. The first camp. Watch who you trust there. People get sold out of that camp.",
    'comber': "Anyone else round here?",
    'comber_r': "Old Walt walks the tide line at Hanauma, back the way you came. He finds what the sea brings in. Go and talk to him.",
    'comber_met': "You've met old Walt, then. He's all right. Talks to the sea more than to people.",
    'work': "Any work?",
    'work_r': "Us, for one. We've no clean water at this camp. Bring three bottles and I'll pay you twenty five kala.",
    'work_where': "The Pink Pearl sells water, if you've kala. Or there's some in every ruin, if you look.",
    'water': "Here's your water.",
    'water_r': "Clean water. Thank you. Here, it's yours. If you want real work, the boatyard hand at Koko Marina's always asking.",
    'barter': "Water's worth more than twenty five kala.",
    'barter_yes': "It is out here. Forty, then, and that's everything. Thank you.",
    'barter_no': "Twenty five's all we can spare. Take it or keep the water.",
    'teach': "Better. I'll show you how to catch the rain and boil it.",
    'teach_r': "Huh. That's more than three bottles' worth. Here, take this, and mahalo. Kuliouou's up the road when you're ready.",
    'refuse': "Find your own water.",
    'refuse_r': "Right. Everybody's on their own out here. Go on, then.",
    'after': "Thanks again for the water. Mind the boats.",
    'after_no': "You again. Road's that way.",
    'again': "Back again? Ask what you need.",
    'where_dread': "Koko Head. The pink hotel down the shore is the boat crews', neutral. The Flotilla takes people. Waikiki's west. Please. That's all I know.",
}
MSG = {}
TOPICS = ['hail', 'where', 'wary', 'rude', 'threat', 'need', 'pearl', 'boats', 'west', 'camp', 'comber', 'work', 'water', 'barter', 'teach', 'refuse']
HUB = ['pearl', 'boats', 'west', 'camp', 'comber', 'work']
ERRAND = ['water', 'barter', 'teach', 'refuse']


def topic_edid(t):
    return 'FOLabBearings' + t.capitalize()


def lines_spec():
    """[(topic, words key, conditions, end, skill, choices, goodbye)]: in the order the game tries them; 'G' is the greeting.
    Conditions: ('v', var, op, value) on the quest's own variables, ('perk', trait, 1), ('glob', name, op, v),
    ('skill', name, op, v), ('items', item, op, v), ('sea', op, v) GetStage of What the Sea Brought In, ('keep',) the
    Pearl's barkeep is in the mod (plan)."""
    q = QUEST
    L = []
    line = lambda topic, words, conds=(), end='', skill=None, choices=(), bye=False: L.append((topic, words, list(conds), end, skill, list(choices), bye))
    met = 'set %s.met to 1' % q
    show = lambda *ks: '\n'.join('ShowMap %s' % ('{%s}' % k) for k in ks)
    pay = lambda n: 'player.AddItem %s %d' % (KALA, n)
    first = ['where', 'wary', 'rude', 'threat', 'need']
    # the hail: traits first
    line('hail', 'hail_dread', [('perk', 'dread', 1)], met, None, ['where', 'need'])
    line('hail', 'hail_kin', [('perk', 'kin', 1)], met + '\n' + show('west'), None, first)
    line('hail', 'hail_boats', [('perk', 'boats', 1)], met, None, first)
    line('hail', 'hail', [], met, None, first)
    # how you answer
    line('where', 'where_dread', [('perk', 'dread', 1)], show('pearl', 'west', 'camp'), None, [], True)
    line('where', 'where_r', [], '', None, HUB)
    line('wary', 'wary_r', [], '', None, HUB)
    line('rude', 'rude_r', [], 'set %s.rude to 1\n%s' % (q, show('west')), None, [], True)
    line('threat', 'threat_yes', [('perk', 'dread', 1)], 'set %s.scared to 1\n%s\n%s' % (q, pay(SCARED), show('pearl', 'west', 'camp')), 'Speech', [], True)
    line('threat', 'threat_yes', [('glob', THREAT_G, '>=', THREAT)], 'set %s.scared to 1\n%s\n%s' % (q, pay(SCARED), show('pearl', 'west', 'camp')), 'Speech', [], True)
    line('threat', 'threat_no', [], '', 'Speech', HUB)
    line('need', 'need_r', [('glob', TALK_G, '>=', TALK), ('v', 'errand', '==', 0)], 'set %s.errand to 1\nset %s.kindly to 1' % (q, q), 'Speech', ['water', 'barter', 'teach', 'refuse'])
    line('need', 'threat_no', [], '', 'Speech', HUB)
    # bearings
    line('pearl', 'pearl_r', [], show('pearl', 'marina'), None, ['boats', 'west', 'camp', 'work'])
    line('boats', 'boats_r', [], '', None, ['pearl', 'west', 'camp', 'comber'])
    line('west', 'west_r', [], show('west', 'marina'), None, ['pearl', 'camp', 'work'])
    line('camp', 'camp_r', [], show('camp'), None, ['pearl', 'west', 'comber', 'work'])
    line('comber', 'comber_r', [('sea', '==', 0)], '', None, ['pearl', 'work'])
    line('comber', 'comber_met', [], '', None, ['pearl', 'work'])
    line('work', 'work_where', [('v', 'errand', '==', 1), ('keep',)], '', None, ['water', 'barter', 'teach', 'refuse'])
    line('work', 'pearl_work', [('v', 'errand', '>=', 2)], show('marina'), None, ['pearl', 'west'])
    line('work', 'work_r', [('v', 'errand', '==', 0)], 'set %s.errand to 1' % q, None, ['water', 'barter', 'teach', 'refuse'])
    line('work', 'work_r', [('v', 'errand', '==', 1)], '', None, ['water', 'barter', 'teach', 'refuse'])
    # the errand
    have = ('items', WATER, '>=', WATER_N)
    give = 'player.RemoveItem %s %d\n' % (WATER, WATER_N)
    line('water', 'water_r', [('v', 'errand', '==', 1), have, ('v', 'kindly', '==', 1)], give + pay(PAY_TALK) + '\nset %s.errand to 2' % q + '\n' + show('marina'))
    line('water', 'water_r', [('v', 'errand', '==', 1), have], give + pay(PAY) + '\nset %s.errand to 2' % q + '\n' + show('marina'))
    line('water', 'work_where', [('v', 'errand', '==', 1)], '', None, ['teach', 'refuse'])
    line('barter', 'barter_yes', [('v', 'errand', '==', 1), have, ('skill', 'Barter', '>=', BARTER)],
         give + pay(PAY_BARTER) + '\nset %s.errand to 3' % q + '\n' + show('marina'), 'Barter')
    line('barter', 'barter_no', [('v', 'errand', '==', 1)], '', 'Barter', ['water', 'teach', 'refuse'])
    line('teach', 'teach_r', [('v', 'errand', '==', 1), ('skill', 'Survival', '>=', SURVIVAL)], pay(PAY_TAUGHT) + '\nset %s.errand to 4' % q + '\n' + show('camp'), 'Survival')
    line('teach', 'barter_no', [('v', 'errand', '==', 1)], '', 'Survival', ['water', 'refuse'])
    line('refuse', 'refuse_r', [('v', 'errand', '==', 1)], 'set %s.errand to 5' % q, None, [], True)
    # talking again
    line('G', 'after', [('v', 'errand', '>=', 2), ('v', 'errand', '<=', 4)], '', None, ['pearl', 'boats', 'west', 'camp', 'comber'])
    line('G', 'after_no', [('v', 'errand', '==', 5)], '', None, ['west'])
    line('G', 'after_no', [('v', 'rude', '==', 1), ('v', 'errand', '==', 0)], '', None, ['west', 'work'])
    line('G', 'again', [], met, None, HUB)
    return L


def quest_script():
    q, r = QUEST, REF
    return '\n'.join([
        'scn %s' % SCRIPT,
        'short met', 'short asked', 'short tries', 'float hailwait', 'short errand', 'short kindly', 'short rude', 'short scared', 'short done', '',
        'Begin GameMode',
        # (the hail: once, near, out of combat, asked again a few times if it doesn't come)
        '\tif met == 0', '\t\tif %s.GetDead == 0' % r, '\t\t\tif player.IsInCombat == 0', '\t\t\t\tif player.GetDistance %s < %d' % (r, HAIL_NEAR),
        '\t\t\t\t\tif hailwait > 0', '\t\t\t\t\t\tset hailwait to hailwait - GetSecondsPassed', '\t\t\t\t\telseif tries < %d' % TRIES,
        '\t\t\t\t\t\tset tries to tries + 1', '\t\t\t\t\t\tset hailwait to %d' % RETRY,
        '\t\t\t\t\t\t%s.StartConversation player %s' % (r, topic_edid('hail')),
        '\t\t\t\t\tendif', '\t\t\t\tendif', '\t\t\tendif', '\t\tendif', '\tendif',
        '\tif met == 1', '\t\tif GetStage %s < 10' % q, '\t\t\tSetStage %s 10' % q, '\t\tendif', '\tendif',
        '\tif errand == 1', '\t\tif GetStage %s < 20' % q, '\t\t\tSetStage %s 20' % q, '\t\tendif', '\tendif',
        '\tif done == 0', '\t\tif errand >= 2', '\t\t\tset done to 1',
        '\t\t\tif errand == 5', '\t\t\t\tSetStage %s 90' % q, '\t\t\telse', '\t\t\t\tSetStage %s 100' % q, '\t\t\tendif', '\t\tendif',
        '\t\tif errand == 0', '\t\t\tif scared == 1', '\t\t\t\tset done to 1', '\t\t\t\tSetStage %s 95' % q, '\t\t\tendif', '\t\tendif', '\tendif',
        'End', ''])


def _stage(n, log, src=''):
    return {'index': n, 'entries': [{'flags': {}, 'conditions': [], 'next': '', 'log': log, 'script': {'source': src, 'parts': None}}]}


def quest_plain(qkey, skey, ref_key):
    obj = lambda n, on=1: 'SetObjectiveDisplayed %s %d %d\n' % (QUEST, n, on)
    done = lambda n: 'SetObjectiveCompleted %s %d 1\n' % (QUEST, n)
    stages = [
        _stage(10, "A surfer at the camp on the coast road told me where I am: the Pink Pearl down the shore is the boat crews' "
                   "hotel and neutral ground, the Flotilla out on the water takes people, Waikiki lies west under the court's "
                   "peace, and Kuliouou is the first camp up the road."),
        _stage(20, "The surfers' camp on the coast road has no clean water. They asked me to bring three bottles of purified water.", obj(10)),
        _stage(90, "I told the surfers to find their own water.", obj(10, 0) + 'CompleteQuest %s\n' % QUEST),
        _stage(95, "I frightened the surfer into telling me everything, and into handing over their kala.", 'CompleteQuest %s\n' % QUEST),
        _stage(100, "The surfers' camp has water now. If I want work, the boatyard hand at Koko Marina is always asking.",
               done(10) + 'CompleteQuest %s\n' % QUEST),
    ]
    return {'edid': QUEST, 'name': QUEST_NAME, 'script': skey, 'flags': {'start_enabled': True}, 'priority': 55, 'delay': 1.0,
            'stages': stages, 'objectives': [{'index': 10, 'text': "Bring three bottles of purified water to the surfers' camp",
                                              'targets': [{'target': ref_key, 'flags': 0, 'conditions': []}] if ref_key else []}],
            'conditions': []}


# ---------- where ----------

def _markers(pr):
    out = {}
    for ck, c in pr.cells.items():
        for rk, r in (c.get('refs') or {}).items():
            m = r.get('marker')
            name = m.get('name') if isinstance(m, dict) else m
            if name and not r.get('removed') and r.get('p'):
                out.setdefault(str(name), (ck, rk, r.get('edid'), r['p']))
    return out


def marker_edid(name):
    return 'FOLabMarker%sREF' % re.sub(r'[^A-Za-z0-9]', '', name)


def _mod_key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and recordio.field(r, 'EDID') == edid), None)


def plan(gd, pr):
    """The refugee's spot: open ground by the camp's fire, on the ground, clear of the road, doors and people."""
    import activity
    rows, skipped, S = [], [], {}
    if _mod_key(pr, QUEST, 'QUST'):
        skipped.append('the mod has %s already' % QUEST)
    for e in [SEA, TALK_G, THREAT_G] + list(TRAITS.values()):
        if not _mod_key(pr, e):
            skipped.append('no %s in the mod' % e)
    M = _markers(pr)
    for k, name in MARKERS.items():
        if name not in M:
            skipped.append('no map marker %s' % name)
    ctx = activity.Ctx(gd, pr)
    roads = [p for e, v in ctx.refs.items() if e.startswith(('FOLabRoad', 'NVRoad', 'Road')) for _c, p in v]
    for name, (x0, y0) in CANDIDATES.items():
        d = min((math.hypot(p[0] - x0, p[1] - y0) for p in roads), default=None)
        rows.append({'camp': name, 'to the nearest road piece': round(d) if d is not None else None})
    cx, cy = CAMP_AT
    fires = [p for e in ('CampfireCrafting03', 'Barrel02Fire256', 'FOLabNightFirePit', 'FOLabNightFirePitDay', 'CampfireCrafting01')
             for _c, p in ctx.refs.get(e, ()) if math.hypot(p[0] - cx, p[1] - cy) < 1500]
    fires.sort(key=lambda p: math.hypot(p[0] - cx, p[1] - cy))
    at = fires[0] if fires else (cx, cy)
    got = ctx.around(at[0], at[1], 1, radii=(220, 300, 400, 550, 700))
    if not got:
        skipped.append('no free ground by the camp\'s fire')
    else:
        x, y, z = got[0][:3]
        S['refugee'] = {'world': (x, y, z), 'rz': math.atan2(at[0] - x, at[1] - y), 'fire': at[:3]}
        rows.append({'refugee': [round(v) for v in (x, y, z)], 'fire': [round(v) for v in at[:3]], 'camp marker': [round(cx), round(cy)]})
    sk, srk, _e, sp = next(((ck, rk, r.get('edid'), r['p']) for ck, c in pr.cells.items() for rk, r in (c.get('refs') or {}).items()
                            if r.get('edid') == START and r.get('p')), (None, None, None, None))
    if sp and 'refugee' in S:
        rows.append({'from the start': round(math.hypot(sp[0] - S['refugee']['world'][0], sp[1] - S['refugee']['world'][1]))})
    S['world'] = ctx.world
    # Koko Marina Refugee Camp, named on the map and empty: refugees of the mod's own by its fires
    if not _mod_key(pr, TALK_QUEST, 'QUST'):
        skipped.append('no %s (People worth talking to first: the refugees take its island lines)' % TALK_QUEST)
    if REFUGEE_CAMP in M:
        rx, ry = M[REFUGEE_CAMP][3][:2]
        rf = [p for e in ('CampfireCrafting03', 'Barrel02Fire256', 'CampfireCrafting01', 'FOLabNightFirePit') for _c, p in ctx.refs.get(e, ())
              if math.hypot(p[0] - rx, p[1] - ry) < 1500]
        rf.sort(key=lambda p: math.hypot(p[0] - rx, p[1] - ry))
        at2 = rf[0] if rf else (rx, ry)
        got = ctx.around(at2[0], at2[1], len(REFUGEES), radii=(200, 280, 360, 450, 550, 700))
        if len(got) < len(REFUGEES):
            skipped.append('room for only %d refugees by %s' % (len(got), REFUGEE_CAMP))
        else:
            S['refugees'] = [{'world': tuple(g[:3]), 'rz': math.atan2(at2[0] - g[0], at2[1] - g[1])} for g in got[:len(REFUGEES)]]
            rows.append({'refugees': [[round(v) for v in g[:3]] for g in got[:len(REFUGEES)]], 'fire': [round(v) for v in at2[:3]]})
    else:
        skipped.append('no map marker %s' % REFUGEE_CAMP)
    S['markers'] = {k: {'name': n, 'cell': M[n][0], 'ref': M[n][1], 'edid': M[n][2] or marker_edid(n), 'named': bool(M[n][2])}
                    for k, n in MARKERS.items() if n in M}
    S['keep'] = bool(_mod_key(pr, PEARL_KEEP, 'NPC_'))
    return {'rows': rows, 'skipped': skipped, 'spots': S}


# ---------- the step ----------

def _cond(fn, op, value, p1=0, p2=0, run=0, orr=False):
    op = '=' if op == '==' else op
    return {'or': orr, 'use_target': False, 'op': op, 'fn': fn, 'p1': p1, 'p2': p2, 'run': run, 'ref': '', 'value': float(value)}


def apply(pr, gd, P=None):
    import api_quests as aq
    import api_scripts
    import factionfolk as ff
    import missouriguns
    import pinkpearl as PP
    import questrec as qr
    import scriptc
    import tes4
    from activity import _new_key
    P = P or plan(gd, pr)
    if P['skipped']:
        raise ValueError('; '.join(P['skipped']))
    S = P['spots']
    out, rep = [], {'made': []}
    marks = S['markers']
    for m in marks.values():
        if not m['named']:
            out.append({'op': 'ref_set', 'cell': m['cell'], 'ref': m['ref'], 'set': {'edid': m['edid'], 'persistent': True}})
    # the refugee: a woman's face nobody in the mod wears, the game's wanderer's clothes, sandboxing by the camp's fire
    faces = missouriguns.women_faces(gd, pr)
    face = next((f for race in ('Caucasian', 'Hispanic', 'Asian', 'AfricanAmerican') for f in faces.get(race, ())), None)
    if face is None:
        raise ValueError('no free woman\'s face left')
    g = dict(ff.GROUPS['court_fighter'])
    g['package'] = 'DefaultSandboxEditorLocation512'
    sk = _mod_key(pr, SURFER, 'NPC_')
    items = [(next(f['value'] for f in x['fields'] if f.get('name') == 'Item'), 1) for x in pr.records[sk]['subs']
             if x['tag'] == 'CNTO'] if sk else []
    items = items or [(it, 1) for it in (PP._item_key(gd, pr, n) for n in ('OutfitWastelandWanderer|OutfitPrewarCasualwear',)) if it]
    npc = ff.person(gd, pr, face, PERSON, PERSON_NAME, g, items, [], '')
    npc['subs'] = [s for s in npc['subs'] if not (s['tag'] == 'SNAM' and not next((f.get('value') for f in s.get('fields', ()) if f.get('name') == 'Faction'), None))]
    ff._set_num(npc, 'AIDT', 'Aggression', 0)
    ff._set_num(npc, 'AIDT', 'Confidence', 1)
    npc_key = _new_key(pr)
    out.append({'op': 'record', 'key': npc_key, 'record': npc})
    world = S['world']
    grid = gd.grid(world if not isinstance(world, str) else gd.from_key(world))
    x, y, z = S['refugee']['world']
    ck = gd.key(grid[(int(math.floor(x / 4096.0)), int(math.floor(y / 4096.0)))])
    ref_key = _new_key(pr)
    out.append({'op': 'place', 'cell': ck, 'key': ref_key, 'ref': {'base': npc_key, 'p': [round(x, 1), round(y, 1), round(z, 1), 0.0, 0.0, round(S['refugee']['rz'], 4)],
                                                                  's': 1.0, 'persistent': True, 'edid': REF}})
    rep['made'] += [PERSON, REF]
    # the refugees: faces nobody wears, the island's clothes, sandboxing by their camp's fire
    import heldwatch
    pools = {'M': heldwatch.men_faces(gd, pr), 'F': faces}
    used = {gd.key(face)}
    refugee_keys = []
    for n, (edid, sex) in enumerate(REFUGEES):
        order = ('Hispanic', 'Asian', 'AfricanAmerican', 'Caucasian')[n % 4:] + ('Hispanic', 'Asian', 'AfricanAmerican', 'Caucasian')[:n % 4]
        f = next((f for race in order for f in pools[sex].get(race, ()) if gd.key(f) not in used), None)
        if f is None:
            raise ValueError('no free face left for %s' % edid)
        used.add(gd.key(f))
        r = ff.person(gd, pr, f, edid, REFUGEE_NAME, g, items, [], '')
        r['subs'] = [x for x in r['subs'] if not (x['tag'] == 'SNAM' and not next((y.get('value') for y in x.get('fields', ()) if y.get('name') == 'Faction'), None))]
        ff._set_num(r, 'AIDT', 'Aggression', 0)
        ff._set_num(r, 'AIDT', 'Confidence', 1)
        k = _new_key(pr)
        out.append({'op': 'record', 'key': k, 'record': r})
        refugee_keys.append(k)
        sp = S['refugees'][n]
        rx, ry, rz = sp['world']
        rck = gd.key(grid[(int(math.floor(rx / 4096.0)), int(math.floor(ry / 4096.0)))])
        out.append({'op': 'place', 'cell': rck, 'key': _new_key(pr), 'ref': {'base': k, 'p': [round(rx, 1), round(ry, 1), round(rz, 1), 0.0, 0.0, round(sp['rz'], 4)],
                                                                            's': 1.0, 'persistent': True}})
    rep['made'] += [e for e, _s in REFUGEES]
    rep['faces'] = sorted(used)
    # the quest, its script, the topics
    sc = api_scripts.scripts()
    qkey, skey = _new_key(pr), _new_key(pr)
    plain = quest_plain(qkey, skey, ref_key)
    stub = qr.quest_record(dict(plain, stages=[], objectives=[]))
    known = {qkey: stub, npc_key: npc, ref_key: {'type': 'ACHR', 'flags': tes4.PERSISTENT, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': REF}]}}
    tkeys = {}
    for t in TOPICS:
        k = _new_key(pr)
        words = W[t] if t in W else t
        rec = qr.topic_record({'edid': topic_edid(t), 'name': W.get(t, t) if t != 'hail' else '', 'priority': 50.0, 'kind': 0,
                               'quests': [{'quest': qkey, 'links': []}]})
        tkeys[t] = k
        known[k] = rec
        out.append({'op': 'record', 'key': k, 'record': rec})
        del words
    c = sc.compile(quest_script(), skey, 'quest', known)
    if not hasattr(c, 'subrecords'):
        raise ValueError('%s: %s' % (SCRIPT, c))
    srec = sc._record_of(c, SCRIPT)
    known[skey] = srec
    out += [{'op': 'record', 'key': skey, 'record': srec}, {'op': 'record', 'key': qkey, 'record': stub}]
    rep['made'] += [QUEST, SCRIPT] + [topic_edid(t) for t in TOPICS]
    V = PP._vars(srec)
    # conditions
    av = lambda n: {'Speech': 43, 'Barter': 32, 'Survival': 44}[n]
    avk = lambda e: gd.key(next(f for f, (i, r) in gd.forms.items() if r.tag == 'AVIF' and gd.edid(f) == e))
    SKILL = {'Speech': avk('AVSpeech'), 'Barter': avk('AVBarter'), 'Survival': avk('AVThrowing')}
    water = gd.key(next(f for f, (i, r) in gd.forms.items() if (f >> 24) == 0 and r.tag == 'ALCH' and gd.edid(f) == WATER))

    def conds(cs):
        o = []
        for c in cs:
            k = c[0]
            if k == 'v':
                o.append(_cond(79, c[2], c[3], qkey, V[c[1]]))
            elif k == 'perk':
                o.append(_cond(449, '==', c[2], _mod_key(pr, TRAITS[c[1]], 'PERK'), 0, 1))
            elif k == 'glob':
                o.append(_cond(74, c[2], c[3], _mod_key(pr, c[1], 'GLOB')))
            elif k == 'skill':
                o.append(_cond(14, c[2], c[3], av(c[1]), 0, 1))
            elif k == 'items':
                o.append(_cond(47, c[2], c[3], water, 0, 1))
            elif k == 'sea':
                o.append(_cond(58, c[1], c[2], _mod_key(pr, SEA, 'QUST')))
        return o
    lines = []
    for topic, words, cs, end, skill, choices, bye in lines_spec():
        if any(c[0] == 'keep' for c in cs) and not S['keep']:
            continue
        tp = qr.GREETING if topic == 'G' else tkeys[topic]
        l = aq.new_line_plain(gd, pr, tp, qkey, npc_key, W[words], goodbye=bye, conditions=conds(cs))
        if skill:
            l['skill'] = SKILL[skill]
        if end:
            for k, m in marks.items():
                end = end.replace('{%s}' % k, m['edid'])
            l['end'] = {'source': end, 'parts': None}
        l['choices'] = [tkeys[t] for t in choices]
        l.setdefault('begin', None)
        l.setdefault('end', None)
        lines.append(l)
    forms = PP._forms(gd, pr, {k: v for k, v in known.items() if k == ref_key}, {x['key']: x['record'] for x in out if x['op'] == 'record'})
    names = {m['edid'] for m in marks.values()}
    for m in marks.values():
        forms.own[m['edid'].lower()] = (m['ref'], {'type': 'REFR', 'flags': tes4.PERSISTENT,
                                                   'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': m['edid']}]})
    forms.is_map_marker = lambda f: f.rec is not None and recordio.field(f.rec, 'EDID') in names
    plain_find = forms.find_edid

    def find_edid(name, plain_find=plain_find):
        hit = forms.own.get(name.lower())
        if hit and not hit[0].startswith('+'):
            return scriptc.Form(forms, gd.from_key(hit[0]), 'REFR', True, None, hit[1])
        return plain_find(name)
    forms.find_edid = find_edid
    full = json.loads(json.dumps(plain))
    errors = aq.compile_quest(full, forms)
    if errors:
        raise ValueError('%s: %s' % (QUEST, errors))
    compiled = []
    for l in lines:
        errors = aq.compile_line(l, forms)
        if errors:
            raise ValueError('%s: %s (%s)' % (errors[0]['where'], errors[0]['message'], l['responses'][0]['text'][:40]))
        compiled.append(qr.info_record(l))
    # the refugees say what the island's people say: People worth talking to's island lines, copied with them as speakers
    import worthtalk
    island = set(worthtalk._speakers(gd, pr)[ISLAND]['all'])
    tq = _mod_key(pr, TALK_QUEST, 'QUST')
    copies = []
    for k, r in sorted(pr.records.items()):
        if r.get('type') != 'INFO':
            continue
        pl = qr.info_plain(json.loads(json.dumps(r)))
        if pl.get('quest') != tq:
            continue
        who = [c for c in pl['conditions'] if c['fn'] == 72]
        if not who or not {c['p1'] for c in who} <= island:
            continue
        rest = [c for c in pl['conditions'] if c['fn'] != 72]
        pl['conditions'] = [_cond(72, '==', 1, rk, orr=n < len(refugee_keys) - 1) for n, rk in enumerate(refugee_keys)] + rest
        rec = qr.info_record(pl)
        rec.pop('src', None)
        rec['src'] = ''
        copies.append(rec)
    before = {k for k, r in pr.records.items() if r.get('type') == 'INFO'}
    pr.apply(LABEL, out)
    pr.apply(LABEL, [{'op': 'record', 'key': qkey, 'record': qr.quest_record(full)}] + [{'op': 'record_new', 'record': r} for r in compiled + copies], merge=True)
    global VOICE_ONLY
    VOICE_ONLY = sorted(k for k, r in pr.records.items() if r.get('type') == 'INFO' and k not in before) or ['+NOTHING']
    rep['refugee lines'] = len(copies)
    # the rehearsal's takes, by each line's words (worthtalk.reuse): only what had none is left to voice
    import os
    here = os.path.normcase(os.path.abspath(os.path.dirname(os.path.dirname(worthtalk.library_dir(pr)))))
    if REUSE_FROM and os.path.isdir(REUSE_FROM) and os.path.normcase(os.path.abspath(REUSE_FROM)) != here:
        got = worthtalk.reuse(gd, pr, REUSE_FROM, VOICE, only=set(VOICE_ONLY))
        rep['reused'] = {k: v for k, v in got.items() if k != 'missing'}
        VOICE_ONLY = got['missing'] or ['+NOTHING']
        rep['voice_still'] = len(got['missing'])
    rep.update({'lines': len(compiled), 'refugee at': [round(v) for v in S['refugee']['world']], 'face': gd.key(face),
                'markers': sorted(m['edid'] for m in marks.values())})
    rep['made'] += ['%d lines' % len(compiled)]
    return rep


# ---------- the run-through ----------

class Game:
    def __init__(self, **kw):
        self.q = {'met': 0, 'errand': 0, 'kindly': 0, 'rude': 0, 'scared': 0, 'done': 0}
        self.perks, self.globs, self.skills, self.items = set(), {TALK_G: 0, THREAT_G: 0}, {'Barter': 0, 'Survival': 0}, {WATER: 0, KALA: 0}
        self.sea, self.keep, self.stage, self.shown = 0, True, 0, []
        self.__dict__.update(kw)

    def holds(self, c):
        ops = {'==': lambda a, b: a == b, '>=': lambda a, b: a >= b, '<=': lambda a, b: a <= b, '<': lambda a, b: a < b, '>': lambda a, b: a > b}
        k = c[0]
        if k == 'v':
            return ops[c[2]](self.q[c[1]], c[3])
        if k == 'perk':
            return (c[1] in self.perks) == bool(c[2])
        if k == 'glob':
            return ops[c[2]](self.globs[c[1]], c[3])
        if k == 'skill':
            return ops[c[2]](self.skills[c[1]], c[3])
        if k == 'items':
            return ops[c[2]](self.items[c[1]], c[3])
        if k == 'sea':
            return ops[c[1]](self.sea, c[2])
        if k == 'keep':
            return self.keep
        raise KeyError(k)

    def run(self, src):
        for s in src.split('\n'):
            s = s.strip()
            m = re.match(r'set %s\.(\w+) to (\d+)' % QUEST, s)
            if m:
                self.q[m.group(1)] = int(m.group(2))
            elif s.startswith('player.AddItem'):
                _p, it, n = s.split()
                self.items[it] = self.items.get(it, 0) + int(n)
            elif s.startswith('player.RemoveItem'):
                _p, it, n = s.split()
                self.items[it] -= int(n)
            elif s.startswith('ShowMap'):
                self.shown.append(s.split()[1].strip('{}'))

    def script(self):
        """The quest script's steps after a talk (the hail itself is the topic asked for)."""
        q = self.q
        if q['met'] == 1 and self.stage < 10:
            self.stage = 10
        if q['errand'] == 1 and self.stage < 20:
            self.stage = 20
        if q['done'] == 0:
            if q['errand'] >= 2:
                q['done'] = 1
                self.stage = 90 if q['errand'] == 5 else 100
            elif q['errand'] == 0 and q['scared'] == 1:
                q['done'] = 1
                self.stage = 95

    def say(self, topic):
        """The line the game picks in a topic, its end run; (words, choices, goodbye)."""
        for t, w, cs, end, _sk, choices, bye in lines_spec():
            if t == topic and all(self.holds(c) for c in cs):
                if end:
                    self.run(end)
                self.script()
                return w, choices, bye
        return None, [], True


def play(game, steps):
    """Walk a route: the hail, then each topic (each must be offered by the line before). (log, ok)."""
    log = []
    w, offered, bye = game.say('hail')
    log.append(w)
    for t in steps:
        if t == 'TALK':                                 # (walk away and talk again: the greeting)
            w, offered, bye = game.say('G')
            log.append(w)
            continue
        if t not in offered:
            return log + ['%s not offered' % t], False
        w, offered, bye = game.say(t)
        log.append(w)
        if w is None:
            return log + ['%s said nothing' % t], False
    return log, True


ROUTES = {
    # (game settings, route, what must hold after)
    'curious, the bearings, water': (dict(items={WATER: 3, KALA: 0}), ['where', 'pearl', 'boats', 'west', 'camp', 'work', 'water'],
                                     lambda g: g.stage == 100 and g.items[KALA] == PAY and {'pearl', 'west', 'camp', 'marina'} <= set(g.shown)),
    'wary, then the work, barter': (dict(items={WATER: 3, KALA: 0}, skills={'Barter': 50, 'Survival': 0}), ['wary', 'work', 'barter'],
                                    lambda g: g.stage == 100 and g.items[KALA] == PAY_BARTER and g.items[WATER] == 0),
    'barter too low, then water': (dict(items={WATER: 3, KALA: 0}), ['wary', 'work', 'barter', 'water'],
                                   lambda g: g.stage == 100 and g.items[KALA] == PAY),
    'survival: teach them': (dict(skills={'Barter': 0, 'Survival': 45}), ['where', 'work', 'teach'],
                             lambda g: g.stage == 100 and g.items[KALA] == PAY_TAUGHT and g.q['errand'] == 4),
    'no water yet, told where': (dict(), ['where', 'work', 'water'], lambda g: g.stage == 20),
    'no water: refuse': (dict(), ['where', 'work', 'refuse'], lambda g: g.stage == 90),
    'speech: they ask straight out, pay more': (dict(globs={TALK_G: 40, THREAT_G: 0}, items={WATER: 3, KALA: 0}), ['need', 'water'],
                                                lambda g: g.stage == 100 and g.items[KALA] == PAY_TALK),
    'speech too low': (dict(), ['need', 'pearl'], lambda g: g.stage == 10),
    'rude': (dict(), ['rude'], lambda g: g.stage == 10 and g.q['rude'] == 1 and 'west' in g.shown),
    'rude, then back for work': (dict(items={WATER: 3, KALA: 0}), ['rude', 'TALK', 'work', 'water'], lambda g: g.stage == 100),
    'intimidate': (dict(globs={TALK_G: 0, THREAT_G: 50}), ['threat'],
                   lambda g: g.stage == 95 and g.items[KALA] == SCARED and {'pearl', 'west', 'camp'} <= set(g.shown)),
    'intimidate fails': (dict(), ['threat', 'boats'], lambda g: g.stage == 10 and g.items[KALA] == 0),
    'dread name: frightened, brief': (dict(perks={'dread'}), ['where'], lambda g: g.stage == 10 and {'pearl', 'west', 'camp'} <= set(g.shown)),
    'dread name: the favour asked anyway': (dict(perks={'dread'}, globs={TALK_G: 40, THREAT_G: 0}, items={WATER: 3, KALA: 0}), ['need', 'water'],
                                            lambda g: g.stage == 100),
    "captain's kin: sent to Waikiki": (dict(perks={'kin'}), ['where', 'west'], lambda g: g.shown[0] == 'west' and g.stage == 10),
    'raised on the boats: warned': (dict(perks={'boats'}), ['where', 'boats'], lambda g: g.stage == 10),
    'beachcomber not met: told of him': (dict(sea=0), ['where', 'camp', 'comber'], lambda g: True),
    'beachcomber met': (dict(sea=30), ['where', 'camp', 'comber'], lambda g: True),
    'done, talking again': (dict(items={WATER: 3, KALA: 0}), ['where', 'work', 'water', 'TALK', 'pearl'], lambda g: g.stage == 100),
}


def routes():
    R = {}
    for name, (kw, steps, after) in ROUTES.items():
        g = Game(**json.loads(json.dumps({k: (sorted(v) if isinstance(v, set) else v) for k, v in kw.items()})))
        if 'perks' in kw:
            g.perks = set(kw['perks'])
        log, ok = play(g, steps)
        ok = ok and after(g)
        if name.startswith('dread name: frightened'):
            ok = ok and log[0] == 'hail_dread'
        if name.startswith("captain's kin"):
            ok = ok and log[0] == 'hail_kin'
        if name.startswith('raised on the boats'):
            ok = ok and log[0] == 'hail_boats'
        if name == 'beachcomber not met: told of him':
            ok = ok and log[-1] == 'comber_r'
        if name == 'beachcomber met':
            ok = ok and log[-1] == 'comber_met'
        R[name] = (log, ok)
    return R
