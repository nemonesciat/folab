"""Standing with the Huáng, and the freighter's hold (docs/waikiki-speech-science.md pick 7; decided: you can get on with
them to an extent but are never fully accepted, and lose standing to become unwelcome, then hostile; the hold stays
locked and an elder holds its key; taking from it is stealing).

- **Reputations tied to their factions** (the game's way: a faction's WMI1 names its reputation):
  - FOLabHuangFaction to FOLabRepHuang, FOLabKahunaCourtFaction to FOLabRepCourt, FOLabPirateTraders to FOLabRepPirates;
  - so crimes against their people count against you there, as in New Vegas.
- **Fame for helping them:** the quest FOLabHuangStanding adds 1 Huang fame once for each of Silk for Waikiki, Pests in
  the Maize, Oil for the Gate Guns and Through Makapuʻu Gate, when it's complete.
- **Face** (repstanding.py's hidden Huang score): +5 for each of their quests done and for the hold's pass, -5 for
  begging forgiveness at the gate. So this step comes after repstanding's.
- **Mending it by talk:** Zhao Lei, the Makapuʻu gate guard (broken English), hears "[Speech 55] Forgive the barbarian.
  I keep to the road." while you have infamy with the Huang.
  - A pass takes 1 infamy away (RemoveReputation), once a game day.
  - A fail can be tried again.
- **The hold:** the elder FOLabHuangElder01 hears "[Speech 85] Show me what the ship carries."
  - One time only. A pass hands you the Freighter Hold Key "as a guest" (taking from the hold is still stealing).
  - He answers in Mandarin, subtitled (the user, 25 Nov 2026: "Mandarin, subtitled"): pinyin with the meaning in brackets,
    as the other Huang lines; voiced in his own Mandarin voice (`ZH`).

    plan(gd, pr)    (rows, skipped)
    apply(pr, gd, P) one Undo (records, then the lines compiled against them)
"""
import json

import recordio

LABEL = 'Standing with the Huang, and the freighter\'s hold'
VOICE = ['FOLabHuangStanding']       # (its lines are voiced in the step: voicelines.py)
QUEST, SCRIPT = 'FOLabHuangStanding', 'FOLabHuangStandingScript'
LINKS = {'FOLabHuangFaction': 'FOLabRepHuang', 'FOLabKahunaCourtFaction': 'FOLabRepCourt', 'FOLabPirateTraders': 'FOLabRepPirates'}
HELPED = ['FOLabHuangSilk', 'FOLabHuangPests', 'FOLabHuangOil', 'FOLabMakapuuGate']
GUARD, ELDER, KEY = 'FOLabMakapuuGuard', 'FOLabHuangElder01', 'FOLabFreighterHoldKey'
MEND_SPEECH, HOLD_SPEECH = 55, 85
FACE = 5                    # (the Huang's face score (repstanding.py): up for their quests and the hold, down for begging)
WORDS = {'mend': "Forgive the barbarian. I keep to the road.",
         'mend_yes': "[SUCCEEDED] Hm. Barbarian learn manners. Road is open again.",
         'mend_no': "[FAILED] No. You go now.",
         'hold': "Show me what the ship carries.",
         'hold_yes': ("You ask as a guest asks. Here is the key. A guest looks. A guest does not take.",
                      "Nǐ xiàng kèrén yíyàng wèn. Zhè shì yàoshi. Kèrén zhǐ kàn, bù ná."),
         'hold_no': ("The hold is ours. It stays closed to you.", "Huòcāng shì wǒmen de. Duì nǐ bù kāi.")}
# (the elder speaks Mandarin, subtitled: the user, 25 Nov 2026. Shown as huangland's SAID lines are, pinyin with the meaning
#  in brackets; spoken from the toned pinyin in his own Mandarin voice: ZH, which the step's voicing reads.)
TAGS = {'hold_yes': '[SUCCEEDED] ', 'hold_no': '[FAILED] '}


def elder_line(k):
    import huangland
    english, pinyin = WORDS[k]
    return TAGS[k] + huangland.shown(english, pinyin)


ZH = {}                                 # (filled below: a shown line's words -> the pinyin said)


def _mod_key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and recordio.field(r, 'EDID') == edid), None)


def plan(gd, pr):
    rows, skipped = [], []
    for fac, rep in LINKS.items():
        f, r = _mod_key(pr, fac, 'FACT'), _mod_key(pr, rep, 'REPU')
        (rows.append({'what': 'link', 'faction': f, 'rep': r, 'names': (fac, rep)}) if f and r else
         skipped.append(('link', '%s or %s not in the mod' % (fac, rep))))
    quests = [q for q in HELPED if _mod_key(pr, q, 'QUST')]
    rows.append({'what': 'fame', 'quests': quests})
    for who, edid in (('mend', GUARD), ('hold', ELDER)):
        k = _mod_key(pr, edid, 'NPC_')
        (rows.append({'what': who, 'npc': k, 'edid': edid}) if k else skipped.append((who, edid + ' not in the mod')))
    if not _mod_key(pr, KEY, 'KEYM'):
        skipped.append(('hold', KEY + ' not in the mod'))
    return rows, skipped


def _cond(fn, op, value, p1=0, p2=0, run=0):
    return {'or': False, 'use_target': False, 'op': op, 'fn': fn, 'p1': p1, 'p2': p2, 'run': run, 'ref': '', 'value': float(value)}


def ops(gd, pr, P=None):
    import repstanding
    _zh()
    import api_quests as aq
    import api_scripts
    import questrec as qr
    from activity import _new_key
    if _mod_key(pr, QUEST, 'QUST'):
        raise ValueError('the mod already has %s (Undo first)' % QUEST)
    rows, skipped = P or plan(gd, pr)
    out, rep = [], {'made': [], 'linked': [], 'fame_for': [], 'skipped': skipped}
    for r in rows:
        if r['what'] == 'link':
            rec = json.loads(json.dumps(pr.records[r['faction']]))
            rec['subs'] = [s for s in rec['subs'] if s['tag'] != 'WMI1']
            rec['subs'].append({'tag': 'WMI1', 'label': 'Reputation', 'kind': 'F', 'value': r['rep']})     # (after DATA, as the game's)
            out.append({'op': 'record', 'key': r['faction'], 'record': rec})
            rep['linked'].append('%s -> %s' % r['names'])
    quests = next(r['quests'] for r in rows if r['what'] == 'fame')
    rep['fame_for'] = quests
    quest_key, script_key = _new_key(pr), _new_key(pr)
    quest = qr.quest_record({'edid': QUEST, 'script': script_key, 'name': '', 'flags': {'start_enabled': True},
                             'priority': 55, 'delay': 5.0, 'stages': [], 'objectives': []})
    L = ['scn %s' % SCRIPT] + ['short counted%d' % n for n in range(len(quests))] + ['short mendday', 'short mended', 'short askedhold', '',
                                                                                    'Begin GameMode']
    for n, q in enumerate(quests):
        L += ['\tif counted%d == 0 && GetQuestCompleted %s' % (n, q), '\t\tset counted%d to 1' % n, '\t\tAddReputation FOLabRepHuang 1 1',
              '\t\t' + repstanding.bump('huang', FACE), '\tendif']
    L += ['\tif mended && GameDaysPassed > mendday', '\t\tset mended to 0', '\tendif', 'End', '']
    sc = api_scripts.scripts()
    c = sc.compile('\n'.join(L), script_key, 'quest', {quest_key: quest})
    if not hasattr(c, 'subrecords'):
        raise ValueError('the standing script: %s' % (c,))
    srec = sc._record_of(c, SCRIPT)
    out += [{'op': 'record', 'key': script_key, 'record': srec}, {'op': 'record', 'key': quest_key, 'record': quest}]
    rep['made'] += [QUEST, SCRIPT]
    index, last = {}, None
    for sub in srec['subs']:
        if sub['tag'] == 'SLSD':
            last = next(f['value'] for f in sub['fields'] if f.get('name') == 'Index')
        elif sub['tag'] == 'SCVR' and last is not None:
            index[sub['value'].lower()] = last
    topics = {}
    for k in ('mend', 'hold'):
        if any(r['what'] == k for r in rows):
            topics[k] = _new_key(pr)
            out.append({'op': 'record', 'key': topics[k], 'record': qr.topic_record({
                'edid': 'FOLabHuangStanding%s' % k.capitalize(), 'name': WORDS[k], 'priority': 50.0, 'kind': 0,
                'flags': {'top_level': True}, 'quests': [{'quest': quest_key, 'links': []}]})})
    speech = gd.key(next(f for f, (i, r) in gd.forms.items() if r.tag == 'AVIF' and gd.edid(f) == 'AVSpeech'))
    huang_rep = _mod_key(pr, 'FOLabRepHuang', 'REPU')
    lines = []

    def line(topic, who, words, conds, end):
        l = aq.new_line_plain(gd, pr, topic, quest_key, who, words, conditions=conds)
        if words in ZH:                    # (one response: its subtitle and the Mandarin said must stay together)
            l['responses'] = [dict(l['responses'][0], text=words, number=1)]
        l['skill'] = speech
        if end:
            l['end'] = {'source': end, 'parts': None}
        lines.append(l)
    for r in rows:
        if r['what'] == 'mend' and huang_rep:
            base = [_cond(573, '>=', 1, huang_rep, 0, 0), _cond(79, '=', 0, quest_key, index['mended'])]     # (has infamy; not today)
            line(topics['mend'], r['npc'], WORDS['mend_yes'], base + [_cond(14, '>=', MEND_SPEECH, 43, 0, 1)],
                 'RemoveReputation FOLabRepHuang 0 1\nset %s.mended to 1\nset %s.mendday to GameDaysPassed\n%s'
                 % (QUEST, QUEST, repstanding.bump('huang', -FACE)))
            line(topics['mend'], r['npc'], WORDS['mend_no'], base + [_cond(14, '<', MEND_SPEECH, 43, 0, 1)], '')
        if r['what'] == 'hold' and _mod_key(pr, KEY, 'KEYM'):
            base = [_cond(79, '=', 0, quest_key, index['askedhold'])]
            line(topics['hold'], r['npc'], elder_line('hold_yes'), base + [_cond(14, '>=', HOLD_SPEECH, 43, 0, 1)],
                 'player.AddItem %s 1\nset %s.askedhold to 1\n%s' % (KEY, QUEST, repstanding.bump('huang', FACE)))
            line(topics['hold'], r['npc'], elder_line('hold_no'), base + [_cond(14, '<', HOLD_SPEECH, 43, 0, 1)],
                 'set %s.askedhold to 1' % QUEST)                                                        # (one time: it decides the hold)
    rep['lines'] = len(lines)
    rep['keys'] = {'quest': quest_key, 'script': script_key, 'topics': topics}
    return out, rep, lines


def apply(pr, gd, P=None):
    import api_quests as aq
    o, rep, lines = ops(gd, pr, P)
    pr.apply(LABEL, o)
    pr.apply(LABEL, [{'op': 'record_new', 'record': aq._compiled_line(gd, pr, l)} for l in lines], merge=True)
    return rep


def _zh():
    for k in ('hold_yes', 'hold_no'):
        ZH[elder_line(k)] = WORDS[k][1]


try:
    _zh()
except Exception:                      # (g2pzh unavailable at import: filled when the step runs)
    pass
