"""Speech checks with the people Waikiki's quests already have (docs/waikiki-speech-science.md, pick 2 and section A; the
user, 25 Nov 2026: "Speech should get you through many checks and encounters").

Each check is a topic of its own on one person, shown in their talk once their quest is done (GetQuestCompleted). It's
the game's way, proven in nv-rs by FOLab Skill Proof on 25 Nov:
  - two lines under one prompt, both carrying the Speech skill (KNAM);
  - the pass line's condition is GetActorValue Speech >= N on the player, the fail line's < N;
  - the engine writes "[Speech n/N]" in front, and each line's own result script does what follows (a reward in goods,
    while money is undecided).
A pass sets the check's variable in the quest FOLabSpeechChecks, so the topic goes. An ordinary check can be tried again
after a fail, once your Speech is higher (the user: "retry allowed for some checks"). A one-time check (`once`: it decides
how a side treats you, or what you're told) sets its variable on a fail too.

`SPECS`: who (an NPC_'s editor ID, or a placed ref's editor ID whose base is taken), after (the quest), Speech needed,
the prompt, what the person says on pass and on fail, the pass's result script, once. All lines are silent (their words
on screen).

    ops(gd, pr)       (ops, report): one Undo; refuses if the mod has FOLabSpeechChecks
    build(server)     applies it as "Speech checks in Waikiki's quests"
"""
import recordio

QUEST = 'FOLabSpeechChecks'
SCRIPT = 'FOLabSpeechChecksScript'
LABEL = "Speech checks in Waikiki's quests"
SPEECH_AV = 43                  # (the Speech actor value; the game's checks compare it, condition function 14)
AV_SPEECH = 'AVSpeech'          # (the skill a check line names: KNAM)

# key: (who, after, Speech, prompt, pass words, fail words, pass result script, once)
SPECS = {
    'comber': ('FOLabBeachcomber', 'FOLabSeaBroughtIn', 25, "Half? I swam out to that wreck for it.",
               "[SUCCEEDED] Ha. Fair enough. Take this too, and don't tell anyone I'm soft.",
               "[FAILED] Half's what you get. I found you, didn't I?",
               'player.AddItem LootDuffleBag25 1', False),
    'leilani': ('FOLabKuliWoman', 'FOLabFirstPlace', 40, "Who does Kuliouou really pay?",
                "[SUCCEEDED] Both. The Kahuna's collectors on tribute day, the pirates whenever they like. People taken "
                "from here go to the old freeway over the Palolo road. Up from there, nobody says.",
                "[FAILED] Who doesn't? Eat something. You look like the sea's still in you.",
                '', True),
    'doctor': ('FOLabWaikikiDoctor', 'FOLabDoctorsStock', 40, "Some of that stock was worth more than five stimpaks.",
               "[SUCCEEDED] You're right, and I hate that you're right. Here.",
               "[FAILED] Five stimpaks is five lives. Don't haggle with a doctor.",
               'player.AddItem Stimpak 2\nplayer.AddItem Morphine 1', False),
    'gate': ('FOLabMakapuuGuard', 'FOLabMakapuuGate', 55, "Let me walk the courtyards, not only the road.",
             "[SUCCEEDED] The mandate is on your arm. The courtyards, then. Touch nothing.",
             "[FAILED] The road. Only the road.",
             '', True),
    'linda': ('FOLabWaikikiTrader', 'FOLabHuangSilk', 55, "I carried the Huang's silk for you. That's worth something.",
              "[SUCCEEDED] It is. One of theirs I kept back. Don't tell Lin Meihua.",
              "[FAILED] You were paid. I don't pay twice.",
              'player.AddItem FOLabClothesHuang 1', False),
    'liuwei': ('FOLabHuangOilGiverREF', 'FOLabHuangOil', 40, "Sixty rounds is thin for two repair kits.",
               "[SUCCEEDED] ...Thirty more. The gate remembers.",
               "[FAILED] Sixty is what the gate gives.",
               'player.AddItem Ammo556mm 30', False),
    'watchman': ('FOLabKPWatchman', 'FOLabKahunaPalms', 55, "People are moving back into the tower because of me.",
                 "[SUCCEEDED] They are. The court should see you look the part. Koa, the way the court wears it.",
                 "[FAILED] The court thanks you. That's all the court does.",
                 'player.AddItem FOLabKoaArmor 1', False),
}


def _mod_key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and recordio.field(r, 'EDID') == edid), None)


def who_npc(pr, who):
    """The NPC_ key a check is said by: the record of that editor ID, or the base of the placed ref named so."""
    k = _mod_key(pr, who, 'NPC_')
    if k:
        return k
    for c in pr.cells.values():
        for r in (c.get('refs') or {}).values():
            if r.get('edid') == who and not r.get('removed') and r.get('base'):
                return r['base']
    return None


def var(k):
    """The quest variable of a check (its key alone may be another form's name: 'doctor')."""
    return 'said' + k


def script_source():
    return '\n'.join(['scn %s' % SCRIPT] + ['short %s' % var(k) for k in SPECS] + ['', 'Begin GameMode', 'End', ''])


def _cond(fn, op, value, p1=0, p2=0, run=0):
    return {'or': False, 'use_target': False, 'op': op, 'fn': fn, 'p1': p1, 'p2': p2, 'run': run, 'ref': '', 'value': float(value)}


def ops(gd, pr):
    import api_quests as aq
    import api_scripts
    import questrec as qr
    if _mod_key(pr, QUEST, 'QUST'):
        raise ValueError('the mod already has %s: the checks look done (Undo first)' % QUEST)
    rep = {'checks': {}, 'missing': {}}
    ready = {}
    for k, (who, after, n, *_rest) in SPECS.items():
        npc, quest = who_npc(pr, who), _mod_key(pr, after, 'QUST')
        if not npc or not quest:
            rep['missing'][k] = 'no %s' % ('speaker ' + who if not npc else 'quest ' + after)
            continue
        ready[k] = (npc, quest)
    order = ['script', 'quest'] + ['topic_' + k for k in ready]
    keys = dict(zip(order, aq._reserve(pr, len(order))))
    quest = qr.quest_record({'edid': QUEST, 'script': keys['script'], 'name': '', 'flags': {'start_enabled': True},
                             'priority': 55, 'delay': 5.0, 'stages': [], 'objectives': []})
    sc = api_scripts.scripts()
    c = sc.compile(script_source(), keys['script'], 'quest', {keys['quest']: quest})
    if not hasattr(c, 'subrecords'):
        raise ValueError('the checks\' script: %s' % (c,))
    srec = sc._record_of(c, SCRIPT)
    index, last = {}, None
    for sub in srec['subs']:                     # (a quest variable is named in a condition by its number)
        if sub['tag'] == 'SLSD':
            last = next(f['value'] for f in sub['fields'] if f.get('name') == 'Index')
        elif sub['tag'] == 'SCVR' and last is not None:
            index[sub['value'].lower()] = last
    out = [{'op': 'record_new', 'record': srec}, {'op': 'record_new', 'record': quest}]
    for k in ready:
        out.append({'op': 'record_new', 'record': qr.topic_record({
            'edid': 'FOLabSpeech%s' % k.capitalize(), 'name': SPECS[k][3], 'priority': 50.0, 'kind': 0,
            'flags': {'top_level': True}, 'quests': [{'quest': keys['quest'], 'links': []}]})})
    applied_before = list(out)
    lines = []
    speech = gd.key(next(f for f, (i, r) in gd.forms.items() if r.tag == 'AVIF' and gd.edid(f) == AV_SPEECH))
    for k, (npc, after_q) in ready.items():
        who, after, n, prompt, yes, no, give, once = SPECS[k]
        base = [_cond(79, '=', 0, keys['quest'], index[var(k)]), _cond(546, '=', 1, after_q)]   # (not done yet; their quest done)
        done = 'set %s.%s to 1' % (QUEST, var(k))
        for words, op, script in ((yes, '>=', (give + '\n' if give else '') + done), (no, '<', done if once else '')):
            l = aq.new_line_plain(gd, pr, keys['topic_' + k], keys['quest'], npc, words, conditions=base + [_cond(14, op, n, SPEECH_AV, 0, 1)])
            l['skill'] = speech
            if script:
                l['end'] = {'source': script, 'parts': None}
            lines.append(l)
        rep['checks'][k] = {'speech': n, 'once': once, 'reward': give or '(words)', 'npc': npc}
    return applied_before, lines, keys, rep


def line_ops(gd, pr, lines):
    """The lines compiled once the quest and its script are in the mod (their result scripts set its variables)."""
    import api_quests as aq
    return [{'op': 'record_new', 'record': aq._compiled_line(gd, pr, l)} for l in lines]


def build(server):
    """Applies it: the quest, its script and topics, then the lines (compiled against them), one Undo."""
    gd, pr = server.GD, server.PR
    first, lines, keys, rep = ops(gd, pr)
    got = pr.apply(LABEL, first)
    want = [keys[k] for k in ['script', 'quest'] + [k for k in keys if k.startswith('topic_')]]
    assert got == want, ('keys not as reserved', got, want)
    pr.apply(LABEL, line_ops(gd, pr, lines), merge=True)
    rep['keys'] = keys
    return rep
