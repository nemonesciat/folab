"""Two kinds of standing with each side, and island titles (the user, 25 Nov 2026: "all three sides, rename the titles for
the island"; docs/waikiki-speech-science.md section J).

**Axis one: liked or hated.** New Vegas's own fame and infamy on the three REPU (piratedeal.REPS), shown on the Pip-Boy's
reputation page.
- The page's title for each mix of fame (0-3) and infamy (0-3) is a game setting, `sRepTitlePos<n>Neg<n>` and its
  `...Desc`. They're defaults in the exe, so FalloutNV.esm overrides only one.
- nv-rs reads them as the exe does (tesreputation.rs, GetReputationTitle: a 4 x 4 table of setting names).
- They're renamed here for the island (`TITLES`). Waikiki has no Mojave factions, so changing them for everything is fine.

**Axis two: how each side sees you, hidden as a score** (-100 to 100, in the quest FOLabNameOnWater, "Your Name on the
Water"). It shows as one line per side among that quest's objectives, which change with the score's band
(SetObjectiveDisplayed):
- **Pirates:** feared (up) or a soft touch (down). Killing pirates raises it (2 a pirate, counted by GetDeadCount over
  the pirate records); paying the toll lowers it (5).
- **The court:** favour (up) or suspicion (down). Passing as the Kahuna's guest at the toll raises it (3).
- **The Huang:** face (up) or disgrace (down). Each of their quests done raises it (5); passing the hold check raises it
  (5); begging forgiveness at the gate lowers it (5). Those two hooks are in huangstanding.py, which this step comes
  before.

Other steps change a score with `set FOLabNameOnWater.<side> to FOLabNameOnWater.<side> + n` (`bump`). What the corners
change in play (tolls waived, ambushes, prices) comes with the parley step (section J, system 1).

    ops(gd, pr)       (ops, report): one Undo (records), with `patch_ops` for pick 4's installed toll lines
"""
import json

import recordio

LABEL = 'Island titles, and how each side sees you'
QUEST, SCRIPT = 'FOLabNameOnWater', 'FOLabNameOnWaterScript'
QUEST_NAME = 'Your Name on the Water'
LEVELS = ('None', 'One', 'Two', 'Three')
# (fame, infamy): (title, what the page says of it). The game's are in brackets.
TITLES = {
    (0, 0): ('Malihini', "A newcomer. Nobody here knows your name yet."),                                   # (Neutral)
    (1, 0): ('Welcome Guest', "People here are glad enough to see you."),                                   # (Accepted)
    (2, 0): ('Good Friend', "People here like you, and say so."),                                           # (Liked)
    (3, 0): ('Island Legend', "They tell stories about you here, and the stories are good."),               # (Idolized)
    (0, 1): ('Watched', "People here keep an eye on you."),                                                 # (Shunned)
    (0, 2): ('Bad News', "People here would rather you went somewhere else."),                              # (Hated)
    (0, 3): ('Island Nightmare', "People here bar their doors when they hear you're coming."),              # (Vilified)
    (1, 1): ('Mixed Plate', "A little good, a little bad. People haven't made up their minds."),            # (Mixed)
    (2, 1): ('Kolohe', "A rascal, but a likeable one. People smile and count their things."),             # (Smiling Troublemaker)
    (3, 1): ('Lovable Rascal', "People love you, and forgive you more than they should."),                  # (Good-Natured Rascal)
    (1, 2): ('Beach Punk', "People think you're trouble with a little good in you, somewhere."),            # (Sneering Punk)
    (2, 2): ('Wild Card', "Nobody here can say what you'll do next."),                                      # (Unpredictable)
    (3, 2): ('Rogue Wave', "Feared and loved in the same breath."),                                         # (Dark Hero)
    (1, 3): ('Kind Shark', "Most people fear you, but some say you've done them good."),                    # (Merciful Thug)
    (2, 3): ('Devil with Aloha', "Most people say you're the devil himself, but they admit you've helped."), # (Soft-Hearted Devil)
    (3, 3): ('Big Wave', "Too big for anyone here to love or hate by halves."),                             # (Wild Child)
}
# side: (score variable, its five lines from the lowest band to the highest)
SIDES = {
    'pirates': ("The pirates call you prey.", "The pirates think you're an easy mark.",
                "The pirates don't know what to make of you.", "The pirates give you room.", "The pirates fear your name."),
    'court': ("The court watches you closely.", "The court is wary of you.", "The court hardly knows you.",
              "The court looks on you kindly.", "The court trusts you near the Kahuna."),
    'huang': ("The Huang say you have no face.", "The Huang think little of you.", "The Huang have no opinion of you.",
              "The Huang say you keep your word.", "The Huang give you face."),
}
BANDS = (-50, -15, 15, 50)      # (a score at or under -50 is the lowest band; over 50 the highest)
OBJ = {'pirates': 10, 'court': 20, 'huang': 30}
KILL = 2                        # (pirates' score for each pirate killed)
TOLL_PAID, GUEST = -5, 3
NOT_PIRATES = ('Deals', 'Trader')


def bump(side, n):
    """A line of script changing one side's score."""
    return 'set %s.%s to %s.%s + %d' % (QUEST, side, QUEST, side, n) if n >= 0 else \
        'set %s.%s to %s.%s - %d' % (QUEST, side, QUEST, side, -n)


def _gmst(edid, text):
    return {'type': 'GMST', 'flags': 0, 'src': '', 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': edid},
                                                            {'tag': 'DATA', 'label': 'Value', 'kind': 'z', 'value': text}]}


def titles():
    """[(setting, text)] of every title and its description."""
    out = []
    for (pos, neg), (t, d) in sorted(TITLES.items()):
        name = 'sRepTitlePos%sNeg%s' % (LEVELS[pos], LEVELS[neg])
        out += [(name, t), (name + 'Desc', d)]
    return out


def pirate_bases(pr):
    return sorted(recordio.field(r, 'EDID') for r in pr.records.values()
                  if r.get('type') == 'NPC_' and 'Pirate' in (recordio.field(r, 'EDID') or '')
                  and not any(w in (recordio.field(r, 'EDID') or '') for w in NOT_PIRATES))


def script_source(pirates):
    L = ['scn %s' % SCRIPT, 'short pirates', 'short court', 'short huang', 'short bandpirates', 'short bandcourt', 'short bandhuang',
         'short started', 'short kills', 'short now', 'short band', '', 'Begin GameMode',
         '\tif started == 0', '\t\tset started to 1', '\t\tSetStage %s 10' % QUEST]
    for side in SIDES:
        L += ['\t\tset band%s to 2' % side, '\t\tSetObjectiveDisplayed %s %d 1' % (QUEST, OBJ[side] + 2)]
    L += ['\tendif', '\tset now to 0']
    for e in pirates:
        L.append('\tset now to now + GetDeadCount %s' % e)
    L += ['\tif now > kills', '\t\tset pirates to pirates + (now - kills) * %d' % KILL, '\t\tset kills to now', '\tendif']
    for side in SIDES:
        L += ['\tif %s > 100' % side, '\t\tset %s to 100' % side, '\telseif %s < -100' % side, '\t\tset %s to -100' % side, '\tendif',
              '\tif %s <= %d' % (side, BANDS[0]), '\t\tset band to 0', '\telseif %s <= %d' % (side, BANDS[1]), '\t\tset band to 1',
              '\telseif %s < %d' % (side, BANDS[2]), '\t\tset band to 2', '\telseif %s < %d' % (side, BANDS[3]), '\t\tset band to 3',
              '\telse', '\t\tset band to 4', '\tendif',
              '\tif band != band%s' % side]
        for b in range(5):
            L += ['\t\tif band%s == %d' % (side, b), '\t\t\tSetObjectiveDisplayed %s %d 0' % (QUEST, OBJ[side] + b), '\t\tendif']
        for b in range(5):
            L += ['\t\tif band == %d' % b, '\t\t\tSetObjectiveDisplayed %s %d 1' % (QUEST, OBJ[side] + b), '\t\tendif']
        L += ['\t\tset band%s to band' % side, '\tendif']
    L += ['End', '']
    return '\n'.join(L)


def ops(gd, pr, P=None):
    import api_scripts
    import questrec as qr
    from activity import _new_key
    if any(recordio.field(r, 'EDID') == QUEST for r in pr.records.values()):
        raise ValueError('the mod already has %s (Undo first)' % QUEST)
    out, rep = [], {'made': [], 'titles': titles(), 'sides': SIDES}
    for name, text in titles():
        out.append({'op': 'record', 'key': _new_key(pr), 'record': _gmst(name, text)})
    rep['made'] += [n for n, _t in titles()]
    quest_key, script_key = _new_key(pr), _new_key(pr)
    objectives = [{'index': OBJ[side] + b, 'text': text, 'targets': []} for side, lines in SIDES.items() for b, text in enumerate(lines)]
    quest = qr.quest_record({'edid': QUEST, 'script': script_key, 'name': QUEST_NAME, 'flags': {'start_enabled': True},
                             'priority': 10, 'delay': 5.0, 'objectives': objectives,
                             'stages': [{'index': 10, 'entries': [{'flags': {'complete': False}, 'conditions': [], 'next': '',
                                                                   'log': "What people on the island say of me, among the pirates, "
                                                                          "the court and the Huang."}]}]})
    pirates = pirate_bases(pr)
    sc = api_scripts.scripts()
    c = sc.compile(script_source(pirates), script_key, 'quest', {quest_key: quest})
    if not hasattr(c, 'subrecords'):
        raise ValueError('the standing script: %s' % (c,))
    out += [{'op': 'record', 'key': script_key, 'record': sc._record_of(c, SCRIPT)}, {'op': 'record', 'key': quest_key, 'record': quest}]
    rep['made'] += [QUEST, SCRIPT]
    rep['pirates_counted'] = pirates
    return out, rep


def patch_ops(gd, pr):
    """Pick 4's toll lines (installed) told about the scores: paying lowers the pirates', a guest's pass raises the court's.
    Their result scripts compiled again; nothing else in the lines changes."""
    import api_quests as aq
    import questrec as qr
    out, n = [], 0
    deals = next((k for k, r in pr.records.items() if r.get('type') == 'QUST' and recordio.field(r, 'EDID') == 'FOLabPirateDeals'), None)
    if not deals:
        return out, 0
    for k, rec in sorted(pr.records.items()):
        if rec.get('type') != 'INFO':
            continue
        l = qr.info_plain(json.loads(json.dumps(rec)))
        if l['quest'] != deals or not l.get('end'):
            continue
        src = l['end']['source']
        add = bump('pirates', TOLL_PAID) if 'RemoveItem Stimpak 1' in src else bump('court', GUEST) if 'FOLabRepCourt' in src else None
        if not add or QUEST in src:
            continue
        l['end'] = {'source': src.rstrip() + '\n' + add, 'parts': None}
        new = aq._compiled_line(gd, pr, l)
        for x in ('seq', 'copied_from', 'topic'):
            if x in rec:
                new[x] = rec[x]
        out.append({'op': 'record', 'key': k, 'record': new})
        n += 1
    return out, n


def apply(pr, gd, P=None):
    o, rep = ops(gd, pr, P)
    pr.apply(LABEL, o)
    p, n = patch_ops(gd, pr)
    if p:
        pr.apply(LABEL, p, merge=True)
    rep['toll_lines_told'] = n
    return rep


def plan(gd, pr):
    return {'rows': [{'titles': len(TITLES), 'pirate records counted': len(pirate_bases(pr))}], 'skipped': []}
