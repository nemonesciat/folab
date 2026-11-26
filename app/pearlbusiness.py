"""The Pearl's business (the user, 26 Nov 2026 ~07:40: "add a couple quests in the pearl that reflect all this too. why they
are there. who owns them. who the flotilla is ... could be a first 'in' with pirates, or a first way to make them mad, or a
way to unlock a ride to waikiki after a quest ... and what relation does that camp have?"). Built after First bearings
(firstbearings.py), so the surfer who hails you on the road is the camp's voice here.

What is invented here (lean; each in docs/waikiki-decisions.md, "built 26 Nov, user may change"):
- **The Keeper.** The Pink Pearl is kept for the boat crews by Mele Kalani, the Keeper (`KEEPER`), in the lobby's office.
  She takes a cut of every deal under its roof and holds its one rule: no blood under this roof. That's why it's neutral
  (decided: the pirates' trade grounds deal fairly, nobody fights there).
- **The camp's fish.** The surfer camp on the road above the Pearl sells its fish to the Pearl's kitchen.
- **Kai.** Flotilla catchers took Kai, the camp surfer's brother, before tribute day (decided: the Flotilla takes people,
  the catchers work before tribute day). He's in the Flotilla's pens (`BROTHER`) until `TRIBUTE_DAYS` pass.
- **The ransom.** The Keeper can send word out to the Flotilla and buy a captive back.
- **The hunters.** After a breakout, Flotilla hunters walk the coast road (`HUNTERS`, under a parent switched on then).

1. **The Keeper's Scales** (`QUESTS['scales']`): the fish stopped coming. Ask the camp why; then any of:
   - bring `FISH_N` Raw Reef Fish yourself;
   - Speech `TALK` (FOLabTraitTalk): talk the surfer round (fish buys cells for a ransom);
   - Intimidate `THREAT` (FOLabTraitThreat; Dread Name always): frighten the camp into fishing;
   - bring Kai home (The Taken, any way): the fish comes back by itself.
   The Keeper pays `PAY` cells, pirate fame and standing, and opens her boats to you (`ride`): the pirates' line from
   Koko Marina (Hawaiʻi Kai) to the Kāhala, and on by the court's boats to Waikiki. The line stays yours while your pirate
   fame is at least your infamy (ferries.py's own rule gains this: `ride_ok`); turn them against you and the boatman
   refuses, until it mends. No new stop: Koko Marina's is a short walk from the Pearl.
2. **Taken Before Tribute Day** (`QUESTS['taken']`), begun when the surfer tells you about Kai:
   - ransom through the Keeper: `RANSOM` cells; Barter `BARTER`, `RANSOM_BARTER`; Raised on the Boats `RANSOM_BOATS`
     ("boat-born vouch for their own"); Captain's Kin pays double; Dread Name, she sends word for nothing (afraid), and the
     crews remember (infamy). Paid, pirate fame;
   - break him out of the pens: the pen key (the guard's) or Lockpick `PICK` at his cage, then tell him to swim for it:
     pirate infamy, standing down, the hunters out on the road;
   - leave him: after `TRIBUTE_DAYS` he's gone up the mountain.
   Home, his sister gives `REWARD` and the camp's thanks.
Hooks: the Keeper on the Pearl's own business (the boatyard's crate, the boy on the second floor, storm nights) says only
what those quests hold.

    plan(gd, pr)       {'rows', 'skipped', 'spots'}
    apply(pr, gd, P)   one Undo (VOICE)
    routes()           every way through
"""
import json
import math
import re

import recordio

LABEL = "The Pearl's business: the Keeper's scales, taken before tribute day"
QUESTS = {'scales': 'FOLabPearlScales', 'taken': 'FOLabPearlTaken'}
NAMES = {'scales': "The Keeper's Scales", 'taken': 'Taken Before Tribute Day'}
VOICE = list(QUESTS.values())
VOICE_ONLY = None
REUSE_FROM = r'D:\FOLab-held\home14'     # (the rehearsal's FOLab home: its takes, by line words, onto these lines)
KEEPER, KEEPER_NAME = 'FOLabPearlKeeper', 'Mele Kalani'
BROTHER, BROTHER_NAME = 'FOLabPearlTakenKai', 'Kai'
SURFER = 'FOLabBearingsSurfer'                      # (First bearings' surfer: Kai's sister)
REF = {'keeper': 'FOLabPearlKeeperREF', 'kai': 'FOLabPearlTakenKaiREF', 'kai_home': 'FOLabPearlKaiHomeREF',
       'surfer': 'FOLabBearingsSurferREF', 'hunters': 'FOLabFlotillaHuntersREF', 'pen_guard': None}
PENS, LOBBY = 'FOLabFlotillaPens', 'FOLabPinkPearlFloor1'
PEN_KEY_FROM = 'FOLabFlotillaPenGuard'
HUNTER_BASE, HUNTERS = 'FOLabPirateLvlFiend2GunVarNV', 3
CELL, KALA, FISH, MEAL = 'AmmoSmallEnergyCell', 'Caps001', 'FOLabRawReefFish', 'FOLabGrilledReefFish'
FISH_N, PAY, TALK, THREAT = 5, 20, 50, 55
RANSOM, RANSOM_BARTER, RANSOM_BOATS, BARTER, PICK = 60, 45, 30, 50, 50
TRIBUTE_DAYS = 5
REWARD = [(MEAL, 3), (KALA, 20)]
TALK_G, THREAT_G = 'FOLabTraitTalk', 'FOLabTraitThreat'
TRAITS = {'dread': 'FOLabTraitDreadName', 'kin': 'FOLabTraitCaptainsKin', 'boats': 'FOLabTraitRaisedOnTheBoats', 'soft': 'FOLabTraitSoftTouch'}
REP, NAME_Q = 'FOLabRepPirates', 'FOLabNameOnWater'
PEARL = {'cells': 'FOLabPearlCells', 'boy': 'FOLabPearlBoy', 'storm': 'FOLabPearlStorm'}
FERRY_Q = 'FOLabFerryLines'

W = {
    # the Keeper
    'k_hi': "You're new. This is the Pink Pearl. My roof, the crews' trade ground. One rule under it: no blood. Keep it and you're welcome.",
    'k_hi_kin': "A captain's people, under my roof. You're welcome as long as you keep the rule. No blood.",
    'k_hi_dread': "I know your name. Everyone does. Keep it outside, and we'll get along.",
    'k_back': "Back again. Keep the rule and the Pearl keeps you.",
    'who': "Who are you?",
    'who_r': "Mele Kalani. I keep the Pearl for the crews. Every deal under this roof, I take my cut, and nobody bleeds. That's why it works.",
    'rule': "Why's nobody fighting here?",
    'rule_r': "Because it's the crews' trade ground, and trade grounds deal fair. Break that and every boat on the coast is against you.",
    'flotilla': "What's the Flotilla?",
    'flotilla_r': "The boats lashed together out past the reef. They take people. I don't ask where they go, and you'd be wise not to either.",
    'pearl_biz': "What else goes on here?",
    'pearl_biz_r': "The boatyard's lost crate is the yard's business. Whoever's kept on the second floor, that's the crews' business. Storm nights, they all pile in.",
    'work': "Any work?",
    'work_r': "The surfers up the road bring my kitchen fish. They've stopped. Find out why and get it coming again, and I'll make it worth your while.",
    'fish': "Here's fish for your kitchen.",
    'fish_r': "Five good ones. That'll do till they're fishing again. You've earned this, and my boats.",
    'done_r': "The fish is coming again. Here, cells, and my word: the boats at Koko Marina will carry you to the Kahala, and back. Keep on the right side of the crews.",
    'told': "They stopped because the Flotilla took the surfer's brother.",
    'told_r': "Did they. The Flotilla's water is its own. But I can send word out, and a price can bring a captive home. Ask me when you've the cells.",
    'ransom': "Send word. I'll pay to bring Kai home.",
    'ransom_r': "Sixty cells. I'll send word tonight, and the boy walks home tomorrow.",
    'ransom_boats': "Boat-born, are you? Then the crews will hear you vouch. Thirty cells, and he walks home.",
    'ransom_kin': "For a captain's people? The boats remember. A hundred and twenty.",
    'ransom_dread': "For you? I'll send word for nothing. I'd rather not have you owing me. Or me owing you.",
    'ransom_no': "Sixty cells. Come back when you have them.",
    'haggle': "Sixty's steep for one boy.",
    'haggle_yes': "Forty five, then. You'd make a fair trader.",
    'haggle_no': "Sixty. The Flotilla sets the price, not me.",
    'broke_r': "So that was you, in the pens. The rule's under my roof, not out on their water. But the crews will want you, and they'll come looking.",
    # the surfer (Kai's sister)
    's_why': "The Keeper wants to know why the fish stopped.",
    's_why_r': "Because my brother's out on the Flotilla. Catchers took Kai off the beach before tribute day. I'm not fishing for the Pearl while he's in their pens.",
    's_talk': "Fish buys cells. Cells buy him back.",
    's_talk_yes': "You're right. I hate it, but you're right. We'll fish. Tell the Keeper.",
    's_talk_no': "Fish for the people who sell him? No.",
    's_threat': "Fish, or I'll make you.",
    's_threat_yes': "All right! We'll fish. Just go.",
    's_threat_no': "Hit me, then. It won't put fish on her plate.",
    's_home': "Kai's home. Here, it's all we can give. And the Pearl gets its fish again.",
    's_gone': "Tribute day's past. Kai's gone up the mountain. Don't talk to me.",
    's_cold': "We're fishing. Like you wanted.",
    # Kai in the pens
    'kai_hi': "Who are you? You're not one of them. Get me out of here. Please.",
    'kai_go': "Swim for it. Back to your sister's camp.",
    'kai_go_r': "I'm going. Tell her I'm coming.",
    'kai_locked': "The door's locked. Find the key, or pick it.",
    'kai_home': "I'm home. Thank you.",
}
TOPICS = {'who': 'scales', 'rule': 'scales', 'flotilla': 'scales', 'pearl_biz': 'scales', 'work': 'scales', 'fish': 'scales',
          'told': 'taken', 'ransom': 'taken', 'haggle': 'taken', 's_why': 'scales', 's_talk': 'scales', 's_threat': 'scales',
          'kai_go': 'taken'}


TOP = ('s_why', 'told')                 # (asked of the surfer in any talk once the Keeper's asked; Kai told the Keeper)


def topic_edid(t):
    return 'FOLabPearlBiz' + ''.join(p.capitalize() for p in t.split('_'))


def lines_spec():
    """[(who, topic, words, conds, end, skill, choices, goodbye)]. Conditions: ('q', which, var, op, v), ('perk', t, 1),
    ('glob', g, op, v), ('skill', s, op, v), ('items', item, op, v), ('dead', who). Speakers: keeper, surfer, kai, kai_home."""
    L = []
    line = lambda who, topic, words, conds=(), end='', skill=None, choices=(), bye=False: L.append((who, topic, words, list(conds), end, skill, list(choices), bye))
    s, t = QUESTS['scales'], QUESTS['taken']
    qv = lambda w, var, op, v: ('q', w, var, op, v)
    ss = lambda var, v=1: 'set %s.%s to %s' % (s, var, v)
    st = lambda var, v=1: 'set %s.%s to %s' % (t, var, v)
    menu = ['who', 'rule', 'flotilla', 'pearl_biz', 'work', 'fish', 'told', 'ransom']
    # the Keeper's greetings
    line('keeper', 'G', 'k_back', [qv('scales', 'met', '==', 1)], '', None, menu)
    line('keeper', 'G', 'k_hi_dread', [('perk', 'dread', 1)], ss('met'), None, menu)
    line('keeper', 'G', 'k_hi_kin', [('perk', 'kin', 1)], ss('met'), None, menu)
    line('keeper', 'G', 'k_hi', [], ss('met'), None, menu)
    line('keeper', 'who', 'who_r', [], '', None, ['rule', 'flotilla', 'work'])
    line('keeper', 'rule', 'rule_r', [], '', None, ['flotilla', 'work'])
    line('keeper', 'flotilla', 'flotilla_r', [], '', None, ['work', 'told'])
    line('keeper', 'pearl_biz', 'pearl_biz_r', [], '', None, ['work'])
    # the work, and its end at the Keeper
    line('keeper', 'work', 'done_r', [qv('scales', 'fishing', '==', 1), qv('scales', 'paid', '==', 0)],
         ss('paid') + '\nplayer.AddItem %s %d\n%s' % (CELL, PAY, ss('ride')), None, ['flotilla'])
    line('keeper', 'work', 'work_r', [qv('scales', 'paid', '==', 0)], ss('asked'), None, ['fish', 'told'])
    line('keeper', 'work', 'k_back', [], '', None, ['flotilla'])
    line('keeper', 'fish', 'fish_r', [qv('scales', 'asked', '==', 1), qv('scales', 'paid', '==', 0), ('items', FISH, '>=', FISH_N)],
         'player.RemoveItem %s %d\n%s\nplayer.AddItem %s %d\n%s' % (FISH, FISH_N, ss('paid'), CELL, PAY, ss('ride')))
    line('keeper', 'told', 'told_r', [qv('taken', 'learned', '==', 1), qv('taken', 'told', '==', 0)], st('told'), None, ['ransom', 'haggle'])
    # the ransom
    free = qv('taken', 'freed', '==', 0)
    told = qv('taken', 'told', '==', 1)
    line('keeper', 'ransom', 'ransom_dread', [told, free, ('perk', 'dread', 1)], st('freed', 2))
    line('keeper', 'ransom', 'ransom_kin', [told, free, ('perk', 'kin', 1), ('items', CELL, '>=', 2 * RANSOM)],
         'player.RemoveItem %s %d\n%s' % (CELL, 2 * RANSOM, st('freed', 1)))
    line('keeper', 'ransom', 'ransom_kin', [told, free, ('perk', 'kin', 1)], '', None, ['haggle'])
    line('keeper', 'ransom', 'ransom_boats', [told, free, ('perk', 'boats', 1), ('items', CELL, '>=', RANSOM_BOATS)],
         'player.RemoveItem %s %d\n%s' % (CELL, RANSOM_BOATS, st('freed', 1)))
    line('keeper', 'ransom', 'ransom_r', [told, free, ('items', CELL, '>=', RANSOM)], 'player.RemoveItem %s %d\n%s' % (CELL, RANSOM, st('freed', 1)))
    line('keeper', 'ransom', 'ransom_no', [told, free], '', None, ['haggle'])
    line('keeper', 'haggle', 'haggle_yes', [told, free, ('perk', 'kin', 0), ('skill', 'Barter', '>=', BARTER), ('items', CELL, '>=', RANSOM_BARTER)],
         'player.RemoveItem %s %d\n%s' % (CELL, RANSOM_BARTER, st('freed', 1)), 'Barter')
    line('keeper', 'haggle', 'haggle_no', [told, free], '', 'Barter', ['ransom'])
    line('keeper', 'G', 'broke_r', [qv('taken', 'freed', '==', 3), qv('taken', 'heard', '==', 0)], st('heard'), None, menu)
    # the surfer: why, and getting the fish going
    line('surfer', 's_why', 's_why_r', [qv('scales', 'asked', '==', 1)], st('learned'), None, ['s_talk', 's_threat'])
    line('surfer', 's_talk', 's_talk_yes', [qv('scales', 'fishing', '==', 0), ('glob', TALK_G, '>=', TALK)], ss('fishing'), 'Speech')
    line('surfer', 's_talk', 's_talk_no', [], '', 'Speech', ['s_threat'])
    line('surfer', 's_threat', 's_threat_yes', [qv('scales', 'fishing', '==', 0), ('perk', 'dread', 1)], ss('fishing') + '\n' + ss('scared'), 'Speech')
    line('surfer', 's_threat', 's_threat_yes', [qv('scales', 'fishing', '==', 0), ('glob', THREAT_G, '>=', THREAT)], ss('fishing') + '\n' + ss('scared'), 'Speech')
    line('surfer', 's_threat', 's_threat_no', [], '', 'Speech')
    line('surfer', 'G', 's_home', [qv('taken', 'home', '==', 1), qv('taken', 'thanked', '==', 0)],
         st('thanked') + '\n' + '\n'.join('player.AddItem %s %d' % r for r in REWARD) + '\n' + ss('fishing'))
    line('surfer', 'G', 's_gone', [qv('taken', 'gone', '==', 1)], '', None, [], True)
    line('surfer', 'G', 's_cold', [qv('scales', 'scared', '==', 1)], '', None, ['s_why'])
    # Kai in the pens
    line('kai', 'G', 'kai_hi', [free], '', None, ['kai_go'])
    line('kai', 'kai_go', 'kai_go_r', [free, ('items', 'pen key', '>=', 1)], st('freed', 3), None, [], True)
    line('kai', 'kai_go', 'kai_go_r', [free, ('skill', 'Lockpick', '>=', PICK)], st('freed', 3), 'Lockpick', [], True)
    line('kai', 'kai_go', 'kai_locked', [free], '', 'Lockpick')
    line('kai_home', 'G', 'kai_home', [])
    return L


def scales_script():
    q, t = QUESTS['scales'], QUESTS['taken']
    return '\n'.join([
        'scn FOLabPearlScalesScript',
        'short met', 'short asked', 'short fishing', 'short paid', 'short ride', 'short scared', 'short done', '',
        'Begin GameMode',
        '\tif asked == 1', '\t\tif GetStage %s < 10' % q, '\t\t\tSetStage %s 10' % q, '\t\tendif', '\tendif',
        '\tif fishing == 1', '\t\tif GetStage %s < 20' % q, '\t\t\tSetStage %s 20' % q, '\t\tendif', '\tendif',
        '\tif paid == 1', '\t\tif done == 0', '\t\t\tset done to 1', '\t\t\tSetStage %s 100' % q, '\t\tendif', '\tendif',
        'End', ''])


def taken_script():
    q, r = QUESTS['taken'], REF
    return '\n'.join([
        'scn FOLabPearlTakenScript',
        'short learned', 'short told', 'short freed', 'short home', 'short gone', 'short thanked', 'short heard', 'short done', 'float due', '',
        'Begin GameMode',
        '\tif learned == 1', '\t\tif GetStage %s < 10' % q, '\t\t\tSetStage %s 10' % q, '\t\t\tset due to GameDaysPassed + %d' % TRIBUTE_DAYS, '\t\tendif', '\tendif',
        # (freed, any way: he walks home; 1 ransom, 2 ransom by fear, 3 breakout)
        '\tif freed > 0', '\t\tif home == 0', '\t\t\tset home to 1', '\t\t\t%s.Disable' % r['kai'], '\t\t\t%s.Enable' % r['kai_home'],
        '\t\t\tset %s.fishing to 1' % QUESTS['scales'],          # (Kai home: the camp fishes again by itself)
        '\t\t\tif freed == 3', '\t\t\t\t%s.Enable' % r['hunters'], '\t\t\t\tSetStage %s 30' % q,
        '\t\t\telseif freed == 2', '\t\t\t\tSetStage %s 22' % q, '\t\t\telse', '\t\t\t\tSetStage %s 20' % q, '\t\t\tendif', '\t\tendif', '\tendif',
        '\tif thanked == 1', '\t\tif done == 0', '\t\t\tset done to 1', '\t\t\tSetStage %s 100' % q, '\t\tendif', '\tendif',
        # (left: tribute day comes and he's gone)
        '\tif learned == 1', '\t\tif freed == 0', '\t\t\tif gone == 0', '\t\t\t\tif GameDaysPassed >= due',
        '\t\t\t\t\tset gone to 1', '\t\t\t\t\t%s.Disable' % r['kai'], '\t\t\t\t\tSetStage %s 90' % q, '\t\t\t\tendif', '\t\t\tendif', '\t\tendif', '\tendif',
        'End', ''])


def _stage(n, log, src=''):
    return {'index': n, 'entries': [{'flags': {}, 'conditions': [], 'next': '', 'log': log, 'script': {'source': src, 'parts': None}}]}


def quests_plain(keys, skeys, targets, have):
    pf = (lambda n: 'AddReputation %s 1 %d\n' % (REP, n)) if have.get('rep') else (lambda n: '')
    pi = (lambda n: 'AddReputation %s 0 %d\n' % (REP, n)) if have.get('rep') else (lambda n: '')
    bump = (lambda n: 'set %s.pirates to %s.pirates %s %d\n' % (NAME_Q, NAME_Q, '+' if n >= 0 else '-', abs(n))) if have.get('names') else (lambda n: '')
    s, t = QUESTS['scales'], QUESTS['taken']
    obj = lambda q, n, on=1: 'SetObjectiveDisplayed %s %d %d\n' % (q, n, on)
    done = lambda q, n: 'SetObjectiveCompleted %s %d 1\n' % (q, n)
    tgt = lambda n: [{'target': targets[n], 'flags': 0, 'conditions': []}] if targets.get(n) else []
    S = [_stage(10, "Mele Kalani, who keeps the Pink Pearl for the boat crews, says the surfers up the road have stopped bringing her "
                    "kitchen fish. She wants to know why, and the fish coming again.", obj(s, 10)),
         _stage(20, "The surfers are fishing for the Pearl again.", done(s, 10) + obj(s, 20)),
         _stage(100, "The Keeper paid me, and opened her boats to me: from Koko Marina to the Kahala and back, while I stay on the "
                     "right side of the crews.", done(s, 20) + pf(1) + bump(5) + 'CompleteQuest %s\n' % s)]
    T = [_stage(10, "Flotilla catchers took Kai, the camp surfer's brother, off the beach before tribute day. He's in the Flotilla's "
                    "pens. On tribute day he goes up the mountain.", obj(t, 10)),
         _stage(20, "I paid the Flotilla's price through the Keeper. Kai is walking home.", done(t, 10) + obj(t, 20) + pf(1) + bump(3)),
         _stage(22, "The Keeper sent word for nothing, afraid of my name. Kai is walking home. The crews will remember how.",
                done(t, 10) + obj(t, 20) + pi(1)),
         _stage(30, "I got Kai out of the Flotilla's pens. He's swimming home. The crews will come looking for me.",
                done(t, 10) + obj(t, 20) + pi(2) + bump(-10)),
         _stage(90, "Tribute day came. Kai has gone up the mountain.", obj(t, 10, 0) + 'CompleteQuest %s\n' % t),
         _stage(100, "Kai is home at the surfers' camp. His sister thanked me.", done(t, 20) + 'CompleteQuest %s\n' % t)]
    objectives = {'scales': [{'index': 10, 'text': "Find out why the surfers stopped bringing fish", 'targets': tgt('surfer')},
                             {'index': 20, 'text': "Tell the Keeper at the Pink Pearl", 'targets': tgt('keeper')}],
                  'taken': [{'index': 10, 'text': "Get Kai out of the Flotilla's pens before tribute day", 'targets': tgt('kai')},
                            {'index': 20, 'text': "See Kai home at the surfers' camp", 'targets': tgt('surfer')}]}
    return {w: {'edid': QUESTS[w], 'name': NAMES[w], 'script': skeys[w], 'flags': {'start_enabled': True}, 'priority': 55, 'delay': 1.0,
                'stages': S if w == 'scales' else T, 'objectives': objectives[w], 'conditions': []} for w in QUESTS}


# ---------- the pirates' boats: ferries.py's rule, with the Keeper's word ----------

def ride_ok():
    """What the ferry quest's script tests for the pirates' line, added to ferries.py's own: the Keeper's word, while your
    fame with the pirates is at least your infamy."""
    return '(%s.ride == 1 && GetReputationThreshold %s 1 >= GetReputationThreshold %s 0)' % (QUESTS['scales'], REP, REP)


def ferry_source(pr):
    """The installed ferry quest script's source with the pirates' rule widened; (key, old source, new source)."""
    import ferries
    import money
    qk = next((k for k, r in pr.records.items() if r.get('type') == 'QUST' and recordio.field(r, 'EDID') == FERRY_Q), None)
    if not qk:
        return None, None, None
    sk = recordio.field(pr.records[qk], 'SCRI')
    sub = next(s for s in pr.records[sk]['subs'] if s['tag'] == 'SCTX')
    src = bytes.fromhex(sub['value']).decode('cp1252')
    nq, nv = money._var_index(pr, NAME_Q)
    dq, dv = money._var_index(pr, 'FOLabPirateDeals')
    band = lambda side, op, n: ('FOLabNameOnWater.band%s %s %d' % (side, op, n)) if nq and ('band' + side) in nv else None
    pirate_ok = ' || '.join(x for x in ([band('pirates', '>=', 2)] + ['FOLabPirateDeals.%s == 1' % v for v in ('dealkahala', 'dealmarina') if dq and v in dv]) if x) or '1'
    old = '(%s) == 0' % pirate_ok
    if old not in src:
        raise ValueError("the ferry script's pirate rule isn't as ferries.py writes it: %r" % old)
    del ferries
    return sk, src, src.replace(old, '(%s || %s) == 0' % (pirate_ok, ride_ok()))


# ---------- where ----------

def _mod_key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and recordio.field(r, 'EDID') == edid), None)


def _ref_of(pr, edid):
    for ck, c in pr.cells.items():
        for rk, r in (c.get('refs') or {}).items():
            if r.get('edid') == edid and not r.get('removed'):
                return ck, rk, r
    return None, None, None


def plan(gd, pr):
    import activity
    import robots
    rows, skipped, S = [], [], {}
    for q in QUESTS.values():
        if _mod_key(pr, q, 'QUST'):
            skipped.append('the mod has %s already' % q)
    for e in [SURFER, PEN_KEY_FROM, HUNTER_BASE, FISH, MEAL, TALK_G, THREAT_G, REP, NAME_Q, FERRY_Q, 'FOLabPirateTraders'] + list(TRAITS.values()):
        if not _mod_key(pr, e):
            skipped.append('no %s in the mod (First bearings, the Flotilla, the ferries first)' % e)
    places = {recordio.field(r, 'EDID'): k for k, r in pr.records.items() if r.get('type') == 'CELL' and k.startswith('+')}
    if LOBBY not in places or PENS not in places:
        skipped.append('no %s or %s' % (LOBBY, PENS))
        return {'rows': rows, 'skipped': skipped, 'spots': S}
    # the Keeper by the lobby's office desk (the desk with a lamp farthest from the front door)
    lobby = places[LOBBY]
    refs = (pr.cells.get(lobby) or {}).get('refs') or {}
    ed = lambda b: (recordio.field(pr.records[b], 'EDID') if b in pr.records else (gd.edid(gd.from_key(b)) if not b.startswith('+') else '')) or ''
    door = next((r['p'] for r in refs.values() if not r.get('removed') and 'HotelDoor' in ed(r.get('base', ''))), (0, 0, 0))
    desks = [(k, r) for k, r in refs.items() if not r.get('removed') and r.get('p') and 'HotelDesk' in ed(r.get('base', ''))]
    if not desks:
        skipped.append('no office desk in the lobby')
    else:
        dk, dr = max(desks, key=lambda kr: math.hypot(kr[1]['p'][0] - door[0], kr[1]['p'][1] - door[1]))
        tris = robots._tris(gd, pr, lobby)
        doors, actors, seats = robots._things(gd, pr, lobby)
        dp = dr['p']
        ok = [p for p in tris if 80 < math.hypot(p[0] - dp[0], p[1] - dp[1]) < 500 and min((robots._d(p, a) for a in actors), default=1e9) > 220
              and min((robots._d(p, d) for d in doors), default=1e9) > 250]
        if not ok:
            skipped.append('no free floor by the office desk')
        else:
            p = min(ok, key=lambda p: math.hypot(p[0] - dp[0], p[1] - dp[1]))
            S['keeper'] = {'cell': lobby, 'p': (round(p[0], 1), round(p[1], 1), round(p[2] + 4, 1), round(math.atan2(door[0] - p[0], door[1] - p[1]), 4)), 'desk': dk}
            rows.append({'keeper': [round(v) for v in p[:3]], 'desk': [round(v) for v in dp[:3]]})
    # Kai in the pens, behind the cage doors among the captives
    pens = places[PENS]
    caps = [r['p'] for r in ((pr.cells.get(pens) or {}).get('refs') or {}).values() if not r.get('removed') and 'Captive' in ed(r.get('base', ''))]
    if not caps:
        skipped.append('no captives in the pens')
    else:
        free = [(x, 400.0) for x in (-150.0, 150.0, -380.0, 380.0)]
        spot = next(((x, y) for x, y in free if min(math.hypot(x - c[0], y - c[1]) for c in caps) > 120), None)
        if not spot:
            skipped.append('no room among the captives')
        else:
            S['kai'] = {'cell': pens, 'p': (spot[0], spot[1], 4.0, math.pi)}
            rows.append({'kai': spot})
    # Kai at home by his sister, the hunters on the road below the camp
    sc, sk, sr = _ref_of(pr, REF['surfer'])
    if not sr:
        skipped.append('no %s (First bearings first)' % REF['surfer'])
    else:
        ctx = activity.Ctx(gd, pr)
        got = ctx.around(sr['p'][0], sr['p'][1], 1, radii=(180, 250, 350))
        if got:
            S['kai_home'] = {'world': tuple(got[0][:3])}
        hunt = ctx.around(sr['p'][0] - 2500, sr['p'][1] + 2500, HUNTERS, radii=(300, 500, 700, 900, 1200))
        if len(hunt) < HUNTERS:
            skipped.append('no room for the hunters on the road')
        else:
            S['hunters'] = [tuple(h[:3]) for h in hunt[:HUNTERS]]
            rows.append({'hunters': [[round(v) for v in h] for h in S['hunters']]})
        S['world'] = ctx.world
    try:
        _sk, old, new = ferry_source(pr)
        rows.append({'ferry rule widened': bool(new and new != old)})
    except ValueError as e:
        skipped.append(str(e))
    return {'rows': rows, 'skipped': skipped, 'spots': S}


# ---------- the step ----------

def _cond(fn, op, value, p1=0, p2=0, run=0, orr=False):
    op = '=' if op == '==' else op
    return {'or': orr, 'use_target': False, 'op': op, 'fn': fn, 'p1': p1, 'p2': p2, 'run': run, 'ref': '', 'value': float(value)}


def apply(pr, gd, P=None):
    import api_quests as aq
    import api_scripts
    import factionfolk as ff
    import heldwatch
    import missouriguns
    import pinkpearl as PP
    import piratedeal
    import questrec as qr
    import tes4
    from activity import _new_key
    P = P or plan(gd, pr)
    if P['skipped']:
        raise ValueError('; '.join(P['skipped']))
    S = P['spots']
    out, rep = [], {'made': []}

    def record(rec, k=None):
        k = k or _new_key(pr)
        out.append({'op': 'record', 'key': k, 'record': rec})
        rep['made'].append(recordio.field(rec, 'EDID'))
        return k

    def place(base, cell, p, edid=None, props=None, world=None):
        k = _new_key(pr)
        if world:
            x, y, z = world
            grid = gd.grid(S['world'] if not isinstance(S['world'], str) else gd.from_key(S['world']))
            cell = gd.key(grid[(int(math.floor(x / 4096.0)), int(math.floor(y / 4096.0)))])
            p = (x, y, z, 0.0)
        ref = {'base': base, 'p': [round(p[0], 1), round(p[1], 1), round(p[2], 1), 0.0, 0.0, p[3]], 's': 1.0, 'persistent': True}
        if edid:
            ref['edid'] = edid
        if props:
            ref['props'] = props
        out.append({'op': 'place', 'cell': cell, 'key': k, 'ref': ref})
        return k
    traders = _mod_key(pr, 'FOLabPirateTraders', 'FACT')
    # the Keeper (a woman), Kai (a man): faces nobody wears
    wf, mf = missouriguns.women_faces(gd, pr), heldwatch.men_faces(gd, pr)
    keeper_face = next(f for race in ('Asian', 'Hispanic', 'AfricanAmerican', 'Caucasian') for f in wf.get(race, ()))
    kai_face = next(f for race in ('Asian', 'Hispanic', 'Caucasian', 'AfricanAmerican') for f in mf.get(race, ()))
    g = dict(ff.GROUPS['court_fighter'])
    g['package'] = 'DefaultSandboxEditorLocation256'
    wear = lambda names: [(it, 1) for it in (PP._item_key(gd, pr, n) for n in names) if it]
    keeper = ff.person(gd, pr, keeper_face, KEEPER, KEEPER_NAME, g, wear(('OutfitMerc02|OutfitPrewarCasualwear', 'Weap10mmPistol')), [], traders)
    ff._set_num(keeper, 'AIDT', 'Aggression', 1)
    keeper_key = record(keeper)
    g2 = dict(g, package='DefaultStayAtEditorLocation')
    sk = _mod_key(pr, 'FOLabSurferVSpawnProspectorAll', 'NPC_')
    clothes = [(next(f['value'] for f in x['fields'] if f.get('name') == 'Item'), 1) for x in pr.records[sk]['subs'] if x['tag'] == 'CNTO'] if sk else []
    kai = ff.person(gd, pr, kai_face, BROTHER, BROTHER_NAME, g2, clothes, [], '')
    kai['subs'] = [x for x in kai['subs'] if not (x['tag'] == 'SNAM' and not next((y.get('value') for y in x.get('fields', ()) if y.get('name') == 'Faction'), None))]
    ff._set_num(kai, 'AIDT', 'Aggression', 0)
    ff._set_num(kai, 'AIDT', 'Confidence', 0)
    kai_key = record(kai)
    # placed: the Keeper by her desk, Kai in the pens and (off) at home, the hunters (off) under their parent
    refs = {}
    refs['keeper'] = place(keeper_key, S['keeper']['cell'], S['keeper']['p'], REF['keeper'])
    refs['kai'] = place(kai_key, S['kai']['cell'], S['kai']['p'], REF['kai'])
    refs['kai_home'] = place(kai_key, None, None, REF['kai_home'], {'enabled': False}, world=S['kai_home']['world'])
    xm = gd.key(piratedeal._game(gd, 'XMarker', 'STAT'))
    h0 = S['hunters'][0]
    refs['hunters'] = place(xm, None, None, REF['hunters'], {'enabled': False}, world=h0)
    hunter = _mod_key(pr, HUNTER_BASE, 'NPC_')
    for h in S['hunters']:
        place(hunter, None, None, None, {'parent': {'ref': refs['hunters'], 'opposite': False}, 'enabled': True}, world=h)
    rep['made'] += [REF['keeper'], REF['kai'], REF['kai_home'], REF['hunters']]
    # quests, scripts, topics
    sc = api_scripts.scripts()
    keys = {w: _new_key(pr) for w in QUESTS}
    skeys = {w: _new_key(pr) for w in QUESTS}
    _c, surfer_ref, _r = _ref_of(pr, REF['surfer'])
    targets = {'surfer': surfer_ref, 'keeper': refs['keeper'], 'kai': refs['kai']}
    have = {'rep': bool(_mod_key(pr, REP, 'REPU')), 'names': bool(_mod_key(pr, NAME_Q, 'QUST'))}
    plains = quests_plain(keys, skeys, targets, have)
    stubs = {w: qr.quest_record(dict(plains[w], stages=[], objectives=[])) for w in QUESTS}
    ext = {k: {'type': 'ACHR' if k != refs['hunters'] else 'REFR', 'flags': tes4.PERSISTENT,
               'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': REF[n]}]} for n, k in refs.items()}
    known = dict(ext)
    known.update({keys[w]: stubs[w] for w in QUESTS})
    known.update({x['key']: x['record'] for x in out if x['op'] == 'record'})
    tkeys = {}
    for t, w in TOPICS.items():
        k = _new_key(pr)
        rec = qr.topic_record({'edid': topic_edid(t), 'name': W[t] if t in W else t, 'priority': 50.0, 'kind': 0,
                               'flags': {'top_level': t in TOP}, 'quests': [{'quest': keys[w], 'links': []}]})
        tkeys[t] = k
        known[k] = rec
        out.append({'op': 'record', 'key': k, 'record': rec})
    srecs = {}
    for w, src in (('scales', scales_script()), ('taken', taken_script())):   # (taken sets scales' fishing)
        c = sc.compile(src, skeys[w], 'quest', known)
        if not hasattr(c, 'subrecords'):
            raise ValueError('%s: %s' % (src.split('\n')[0], c))
        srecs[w] = sc._record_of(c, src.split('\n')[0][4:])
        known[skeys[w]] = srecs[w]
    out += [{'op': 'record', 'key': skeys[w], 'record': srecs[w]} for w in QUESTS]
    out += [{'op': 'record', 'key': keys[w], 'record': stubs[w]} for w in QUESTS]
    rep['made'] += list(QUESTS.values())
    V = {w: PP._vars(srecs[w]) for w in QUESTS}
    # the pirates' boats: the ferry script recompiled with the Keeper's word in its rule
    fsk, _old, fnew = ferry_source(pr)
    # conditions and lines
    pen_key = next((x['fields'] for x in pr.records[_mod_key(pr, PEN_KEY_FROM, 'NPC_')]['subs'] if x['tag'] == 'CNTO'
                    and (pr.records.get(next(f['value'] for f in x['fields'] if f.get('name') == 'Item')) or {}).get('type') == 'KEYM'), None)
    pen_key = next(f['value'] for f in pen_key if f.get('name') == 'Item') if pen_key else None
    AVI = {'Barter': 32, 'Lockpick': 36, 'Speech': 43}
    avk = lambda e: gd.key(next(f for f, (i, r) in gd.forms.items() if r.tag == 'AVIF' and gd.edid(f) == e))
    SKILL = {'Barter': avk('AVBarter'), 'Lockpick': avk('AVLockpick'), 'Speech': avk('AVSpeech')}
    item = lambda e: pen_key if e == 'pen key' else (_mod_key(pr, e) or gd.key(next(f for f, (i, r) in gd.forms.items() if (f >> 24) == 0 and gd.edid(f) == e and r.tag in ('AMMO', 'ALCH', 'MISC'))))

    def conds(cs):
        o = []
        for c in cs:
            k = c[0]
            if k == 'q':
                o.append(_cond(79, c[3], c[4], keys[c[1]], V[c[1]][c[2]]))
            elif k == 'perk':
                o.append(_cond(449, '==', c[2], _mod_key(pr, TRAITS[c[1]], 'PERK'), 0, 1))
            elif k == 'glob':
                o.append(_cond(74, c[2], c[3], _mod_key(pr, c[1], 'GLOB')))
            elif k == 'skill':
                o.append(_cond(14, c[2], c[3], AVI[c[1]], 0, 1))
            elif k == 'items':
                it = item(c[1])
                if it is None:
                    o.append(_cond(14, '>=', 101, AVI['Lockpick'], 0, 1))      # (no pen key known: never)
                else:
                    o.append(_cond(47, c[2], c[3], it, 0, 1))
        return o
    surfer_key = _mod_key(pr, SURFER, 'NPC_')
    who_key = {'keeper': keeper_key, 'surfer': surfer_key, 'kai': kai_key, 'kai_home': kai_key}
    lines = []
    for who, topic, words, cs, end, skill, choices, bye in lines_spec():
        tp = qr.GREETING if topic == 'G' else tkeys[topic]
        quest = keys[TOPICS[topic]] if topic != 'G' else keys['taken' if who in ('kai', 'kai_home') or words in ('s_home', 's_gone', 'broke_r') else 'scales']
        l = aq.new_line_plain(gd, pr, tp, quest, who_key[who], W[words], goodbye=bye, conditions=conds(cs))   # (Kai in the pens and at home: one record, only one of them on at a time)
        if skill:
            l['skill'] = SKILL[skill]
        if end:
            l['end'] = {'source': end, 'parts': None}
        l['choices'] = [tkeys[t] for t in choices]
        l.setdefault('begin', None)
        l.setdefault('end', None)
        lines.append(l)
    forms = PP._forms(gd, pr, ext, {x['key']: x['record'] for x in out if x['op'] == 'record'})
    compiled_q = {}
    for w in QUESTS:
        full = json.loads(json.dumps(plains[w]))
        errors = aq.compile_quest(full, forms)
        if errors:
            raise ValueError('%s: %s' % (QUESTS[w], errors))
        compiled_q[w] = full
    compiled = []
    for l in lines:
        errors = aq.compile_line(l, forms)
        if errors:
            raise ValueError('%s: %s (%s)' % (errors[0]['where'], errors[0]['message'], l['responses'][0]['text'][:40]))
        compiled.append(qr.info_record(l))
    fknown = dict(known)                       # (the ferries' arrival markers are named refs: stand-ins, as ferries.py compiles with)
    for _ck, c in pr.cells.items():
        for rk, r in (c.get('refs') or {}).items():
            if (r.get('edid') or '').startswith('FOLabFerry') and not r.get('removed'):
                fknown[rk] = {'type': 'REFR', 'flags': tes4.PERSISTENT, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': r['edid']}]}
    fc = sc.compile(fnew, fsk, 'quest', fknown)
    if not hasattr(fc, 'subrecords'):
        raise ValueError('the ferry script with the Keeper\'s word: %s' % (fc,))
    frec = sc._record_of(fc, recordio.field(pr.records[fsk], 'EDID'))
    if PP._vars(frec) != PP._vars(pr.records[fsk]):
        raise ValueError('the ferry script\'s variables moved: a save would lose its place')
    before = {k for k, r in pr.records.items() if r.get('type') == 'INFO'}
    pr.apply(LABEL, out)
    pr.apply(LABEL, [{'op': 'record', 'key': keys[w], 'record': qr.quest_record(compiled_q[w])} for w in QUESTS] +
             [{'op': 'record', 'key': fsk, 'record': frec}] + [{'op': 'record_new', 'record': r} for r in compiled], merge=True)
    # the rehearsal's takes, by each line's words (worthtalk.reuse): only what had none is left to voice
    import os
    import worthtalk
    global VOICE_ONLY
    VOICE_ONLY = sorted(k for k, r in pr.records.items() if r.get('type') == 'INFO' and k not in before) or ['+NOTHING']
    here = os.path.normcase(os.path.abspath(os.path.dirname(os.path.dirname(worthtalk.library_dir(pr)))))
    if REUSE_FROM and os.path.isdir(REUSE_FROM) and os.path.normcase(os.path.abspath(REUSE_FROM)) != here:
        got = worthtalk.reuse(gd, pr, REUSE_FROM, VOICE, only=set(VOICE_ONLY))
        rep['reused'] = {k: v for k, v in got.items() if k != 'missing'}
        VOICE_ONLY = got['missing'] or ['+NOTHING']
        rep['voice_still'] = len(got['missing'])
    rep.update({'lines': len(compiled), 'keeper at': S['keeper']['p'][:3], 'kai in the pens at': S['kai']['p'][:3],
                'pen key': pen_key, 'ferry rule': ride_ok(), 'faces': [gd.key(keeper_face), gd.key(kai_face)]})
    return rep


# ---------- the run-through ----------

class Game:
    def __init__(self, **kw):
        self.q = {'scales': {v: 0 for v in ('met', 'asked', 'fishing', 'paid', 'ride', 'scared', 'done')},
                  'taken': {v: 0 for v in ('learned', 'told', 'freed', 'home', 'gone', 'thanked', 'heard', 'done')}}
        self.perks, self.globs, self.skills = set(), {TALK_G: 0, THREAT_G: 0}, {'Barter': 0, 'Lockpick': 0}
        self.items = {CELL: 0, FISH: 0, 'pen key': 0, MEAL: 0, KALA: 0}
        self.stage = {'scales': 0, 'taken': 0}
        self.days, self.due, self.fame, self.infamy, self.hunters, self.kai_home = 0, None, 0, 0, False, False
        self.__dict__.update(kw)

    def holds(self, c):
        ops = {'==': lambda a, b: a == b, '>=': lambda a, b: a >= b, '<=': lambda a, b: a <= b, '<': lambda a, b: a < b, '>': lambda a, b: a > b}
        k = c[0]
        if k == 'q':
            return ops[c[3]](self.q[c[1]][c[2]], c[4])
        if k == 'perk':
            return (c[1] in self.perks) == bool(c[2])
        if k == 'glob':
            return ops[c[2]](self.globs[c[1]], c[3])
        if k == 'skill':
            return ops[c[2]](self.skills[c[1]], c[3])
        if k == 'items':
            return ops[c[2]](self.items[c[1]], c[3])
        raise KeyError(k)

    def run(self, src):
        for s in src.split('\n'):
            s = s.strip()
            m = re.match(r'set (\w+)\.(\w+) to (-?\d+)', s)
            if m:
                w = next(k for k, v in QUESTS.items() if v == m.group(1))
                self.q[w][m.group(2)] = int(m.group(3))
            elif s.startswith('player.AddItem'):
                _p, it, n = s.split()
                self.items[it] = self.items.get(it, 0) + int(n)
            elif s.startswith('player.RemoveItem'):
                _p, it, n = s.split()
                self.items[it] -= int(n)

    def script(self):
        S, T = self.q['scales'], self.q['taken']
        if S['asked'] == 1 and self.stage['scales'] < 10:
            self.stage['scales'] = 10
        if S['fishing'] == 1 and self.stage['scales'] < 20:
            self.stage['scales'] = 20
        if S['paid'] == 1 and S['done'] == 0:
            S['done'] = 1
            self.stage['scales'] = 100
            self.fame += 1
        if S['fishing'] == 0 and T['home'] == 1:
            S['fishing'] = 1
        if T['learned'] == 1 and self.stage['taken'] < 10:
            self.stage['taken'] = 10
            self.due = self.days + TRIBUTE_DAYS
        if T['freed'] > 0 and T['home'] == 0:
            T['home'] = 1
            self.kai_home = True
            if T['freed'] == 3:
                self.hunters = True
                self.stage['taken'] = 30
                self.infamy += 2
            elif T['freed'] == 2:
                self.stage['taken'] = 22
                self.infamy += 1
            else:
                self.stage['taken'] = 20
                self.fame += 1
        if T['thanked'] == 1 and T['done'] == 0:
            T['done'] = 1
            self.stage['taken'] = 100
        if T['learned'] == 1 and T['freed'] == 0 and T['gone'] == 0 and self.due is not None and self.days >= self.due:
            T['gone'] = 1
            self.stage['taken'] = 90

    def ride(self):
        """ferries.py's pirates' rule, the Keeper's word added (ride_ok)."""
        return self.q['scales']['ride'] == 1 and self.fame >= self.infamy

    def say(self, who, topic):
        for w, t, words, cs, end, _sk, choices, bye in lines_spec():
            if w == who and t == topic and all(self.holds(c) for c in cs):
                if end:
                    self.run(end)
                self.script()
                return words, choices
        return None, []


def play(g, steps):
    log, offered, who = [], [], None
    for st in steps:
        if isinstance(st, tuple):                   # ('talk', who): open a conversation; ('days', n); ('give', item, n)
            if st[0] == 'talk':
                who = st[1]
                w, offered = g.say(who, 'G')
                log.append(w)
                if w is None:
                    return log + ['%s has no greeting' % who], False
            elif st[0] == 'days':
                g.days += st[1]
                g.script()
            elif st[0] == 'give':
                g.items[st[1]] = g.items.get(st[1], 0) + st[2]
            elif st[0] == 'ask':                    # (a topic asked at the surfer: her topics are offered by the Keeper's errand)
                who = 'surfer'
                w, offered = g.say('surfer', st[1])
                log.append(w)
                if w is None:
                    return log + ['surfer silent on %s' % st[1]], False
            continue
        if st not in offered:
            return log + ['%s not offered (%s)' % (st, offered)], False
        w, offered = g.say(who, st)
        log.append(w)
        if w is None:
            return log + ['%s said nothing' % st], False
    return log, True


def _routes():
    meet = [('talk', 'keeper'), 'work']
    learn = meet + [('ask', 's_why')]
    tell = learn + [('talk', 'keeper'), 'told']
    return {
        'scales: bring fish': (dict(items={CELL: 0, FISH: 5, 'pen key': 0, MEAL: 0, KALA: 0}), meet + ['fish'],
                               lambda g: g.stage['scales'] == 100 and g.items[CELL] == PAY and g.ride()),
        'scales: talk the surfer round': (dict(globs={TALK_G: 60, THREAT_G: 0}), learn + [('ask', 's_talk'), ('talk', 'keeper'), 'work'],
                                          lambda g: g.stage['scales'] == 100 and g.ride() and g.stage['taken'] == 10),
        'scales: talk fails, threaten': (dict(globs={TALK_G: 0, THREAT_G: 60}), learn + [('ask', 's_talk'), ('ask', 's_threat'), ('talk', 'keeper'), 'work'],
                                         lambda g: g.stage['scales'] == 100 and g.q['scales']['scared'] == 1),
        'scales: dread name frightens the camp': (dict(perks={'dread'}), learn + [('ask', 's_threat'), ('talk', 'keeper'), 'work'],
                                                  lambda g: g.stage['scales'] == 100),
        'taken: ransom': (dict(items={CELL: 60, FISH: 0, 'pen key': 0, MEAL: 0, KALA: 0}), tell + ['ransom', ('talk', 'surfer')],
                          lambda g: g.stage['taken'] == 100 and g.items[CELL] == 0 and g.items[MEAL] == 3 and g.q['scales']['fishing'] == 1),
        'taken: ransom, then the Keeper pays for the fish': (dict(items={CELL: 60, FISH: 0, 'pen key': 0, MEAL: 0, KALA: 0}),
                                                             tell + ['ransom', ('talk', 'surfer'), ('talk', 'keeper'), 'work'],
                                                             lambda g: g.stage['scales'] == 100 and g.ride()),
        'taken: ransom haggled': (dict(items={CELL: 45, FISH: 0, 'pen key': 0, MEAL: 0, KALA: 0}, skills={'Barter': 55, 'Lockpick': 0}),
                                  tell + ['haggle', ('talk', 'surfer')], lambda g: g.stage['taken'] == 100 and g.items[CELL] == 0),
        'taken: raised on the boats vouch': (dict(perks={'boats'}, items={CELL: 30, FISH: 0, 'pen key': 0, MEAL: 0, KALA: 0}),
                                             tell + ['ransom', ('talk', 'surfer')], lambda g: g.stage['taken'] == 100 and g.items[CELL] == 0),
        "taken: captain's kin pays double": (dict(perks={'kin'}, items={CELL: 120, FISH: 0, 'pen key': 0, MEAL: 0, KALA: 0}),
                                             tell + ['ransom'], lambda g: g.stage['taken'] == 20 and g.items[CELL] == 0),
        "taken: captain's kin short, no haggling": (dict(perks={'kin'}, items={CELL: 60, FISH: 0, 'pen key': 0, MEAL: 0, KALA: 0}, skills={'Barter': 90, 'Lockpick': 0}),
                                                    tell + ['ransom', 'haggle'], lambda g: g.stage['taken'] == 10),
        'taken: dread name, sent for nothing': (dict(perks={'dread'}), tell + ['ransom'], lambda g: g.stage['taken'] == 22 and g.infamy == 1),
        'taken: no cells': (dict(), tell + ['ransom', 'haggle'], lambda g: g.stage['taken'] == 10),
        'taken: breakout with the key': (dict(items={CELL: 0, FISH: 0, 'pen key': 1, MEAL: 0, KALA: 0}), learn + [('talk', 'kai'), 'kai_go', ('talk', 'keeper')],
                                         lambda g: g.stage['taken'] == 30 and g.hunters and not g.ride()),
        'taken: breakout by lockpick, then home': (dict(skills={'Barter': 0, 'Lockpick': 60}), learn + [('talk', 'kai'), 'kai_go', ('talk', 'surfer')],
                                                   lambda g: g.stage['taken'] == 100 and g.hunters),
        'taken: the cage is locked': (dict(), learn + [('talk', 'kai'), 'kai_go'], lambda g: g.stage['taken'] == 10),
        'taken: left, tribute day': (dict(), learn + [('days', TRIBUTE_DAYS), ('talk', 'surfer')], lambda g: g.stage['taken'] == 90),
        'the ride closes when they turn on you, opens when it mends': (dict(items={CELL: 0, FISH: 5, 'pen key': 0, MEAL: 0, KALA: 0}), meet + ['fish'],
                                                                       lambda g: (g.ride(), setattr(g, 'infamy', 3), not g.ride(), setattr(g, 'fame', 3), g.ride())[::2] == (True, True, True)),
        'the Keeper on the Pearl and the Flotilla': (dict(), [('talk', 'keeper'), 'who', 'rule', 'flotilla', 'work'], lambda g: g.stage['scales'] == 10),
        'the Keeper on the Pearl\'s other business': (dict(), [('talk', 'keeper'), 'pearl_biz', 'work'], lambda g: True),
    }


def routes():
    R = {}
    for name, (kw, steps, after) in _routes().items():
        g = Game()
        for k, v in kw.items():
            if k == 'perks':
                g.perks = set(v)
            elif isinstance(v, dict):
                getattr(g, k).update(v)
            else:
                setattr(g, k, v)
        log, ok = play(g, steps)
        try:
            ok = ok and bool(after(g))
        except Exception as e:                  # noqa: BLE001
            log.append(repr(e))
            ok = False
        R[name] = (log, ok)
    return R
