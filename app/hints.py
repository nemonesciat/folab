"""Hints for Waikiki's collectibles (the user, 25 Nov 2026: "Yes, add some hints, this could make terminal hacking more useful,
speech as well"; docs/waikiki-decisions.md). collectibles.py places them; this says where, in the island's own words.

- **Science** (`TERMINALS`): an entry on terminals already in the mod, readable once hacked. Pre-war terminals hint only at
  the hula dolls (pre-war dashboard kitsch); the court's and the ship's post-war ones may hint at charms too. Where natural,
  its result script ShowMaps the area (`map`: a map marker, given an editor ID and kept loaded as rumours' are).
- **Speech** (`PEOPLE`): a Speech check with people who'd know, one topic a group (`TOPICS`). Hula hints from locals, jade
  hints from the Huang (their topic opens only once you've found your first charm: the set is secret), the court's from
  a guard and the Kahuna Palms watchman. A pass tells the hint (and may ShowMap); a fail can be tried again with more Speech.
- **Found already, not hinted:** every hint line and entry has GetQuestVariable FOLabCollectibles <its item> == 0.
- Every new line voiced in its speaker's own voice (voicelines, `VOICE`). Placement doesn't change.
- Every item has at least one hint (`covered`). The words are this step's own, in-world: pre-war logs, court scouts,
  locals' gossip, the Huang's guarded talk (Zhao Lei's broken English).

    plan(gd, pr)       (rows, skipped)
    apply(pr, gd, P)   one Undo (records, then the lines compiled against them)
"""
import json
import re

import recordio

LABEL = 'Hints for the collectibles'
QUEST, QSCRIPT = 'FOLabHints', 'FOLabHintsScript'
VOICE = [QUEST]
COLLECT = 'FOLabCollectibles'
GETISID, GETAV, GETQV, SPEECH_AV = 72, 14, 79, 43
# item: ('hula', SPECIAL) or ('jade', skill), as collectibles.SPOTS
TERMINALS = [   # (terminal editor ID, item, entry title, entry text, map marker or None)
    ('FOLabRadarDomeTerminal', ('hula', 'Agility'), 'Traffic note, 10-21-2077',
     "Sedan abandoned at the Pali switchback below the checkpoint, doors open. A hula girl still bobbing on the dashboard.\n"
     "Towing requested. None sent.", 'Pali Checkpoint'),
    ('FOLabMissouriFireControl', ('hula', 'Strength'), 'Turret Two',
     "Turret Two's mascot is back on the ammunition crate. The dancing girl stays: the crew say she's good for the guns.", None),
    ('FOLabMissouriFireControl', ('hula', 'Intelligence'), 'Pilot House',
     "Somebody keeps putting a hula doll on the Pilot House console. She can stay. She's the only one aboard who doesn't argue.", None),
    ('FOLabMissouriPowerLog', ('jade', 'Repair'), 'Trade',
     "Traded wire to a Huang canoe for a green stone charm. Left it on the console stack in the Engine Room.\n"
     "They said it's bad luck to sell it on.", None),
    ('FOLabMissouriPowerLog', ('jade', 'Explosives'), 'Second charm',
     "The other green charm, the one with the red cord, is in a locker on the 2nd Deck. Nobody takes it ashore.", None),
    ('FOLabKahunaPalmsManager', ('hula', 'Charisma'), 'Prize',
     "The slot machine prize, a dashboard hula girl, is on the slot table on the top floor. Do not let guests take it home.", None),
    ('FOLabHeightsEstate', ('hula', 'Perception'), 'Groundskeeper',
     "Junior has left his hula doll on the sandbags at the Diamond Head lookout again, 'for the view'.\n"
     "Please collect it before the inspection.", 'Diamond Head Lookout'),
    ('FOLabAlewaWallWatch', ('jade', 'EnergyWeapons'), 'Scouts, the coast',
     "Scouts by the wrecked freighter saw something green in the sand beside the hull. Huang make, by the cord. Left it.",
     'Wrecked freighter'),
    ('FOLabTributeLedgerTerminal', ('hula', 'Luck'), 'Kahala boats',
     "Kahala boats searched for tribute: no goods. One rowboat on the shore carried a hula doll. Not tribute. Left it.", 'Kahala Reef'),
]
TOPICS = {'local': "Seen anything odd lying around?", 'huang': "The green charms. Tell me about them.",
          'court': "Anything strange in the hotels?"}
NOTHING = {'local': "Nothing new. You've seen what I've seen.", 'huang': "Nothing more.", 'court': "Nothing to report."}
FAILS = {'local': "[FAILED] Odd? This whole island's odd. Ask me something useful.",
         'huang': "[FAILED] Charms? Ask someone else.", 'court': "[FAILED] The court's business is the court's."}
# who: (group, NPC_ editor ID or ('ref', its ref's editor ID), Speech, [(item, words, map marker or None)])
PEOPLE = [
    ('local', ('ref', 'FOLabBeachcomberREF'), 25, [
        (('hula', 'Endurance'), "[SUCCEEDED] Somebody camped deep in that lava tube, Pele's Pipe. Left a little hula girl on a crate at "
                                "the very end. Didn't have the heart to take her.", "Pele's Pipe")]),
    ('local', 'FOLabWaikikiTrader', 40, [
        (('jade', 'Barter'), "[SUCCEEDED] The Huang keep a green charm on the long table in their granary. For luck in trade, Lin "
                             "Meihua says. Don't tell her I told you.", None)]),
    ('local', 'FOLabPirateTraderKahala', 40, [
        (('hula', 'Luck'), "[SUCCEEDED] There's a rowboat on the Kahala shore with a dancing doll in it. Nobody'll move her. Bad luck, "
                           "the crews say.", 'Kahala Reef')]),
    ('local', 'FOLabPirateTraderMarina', 40, [
        (('jade', 'EnergyWeapons'), "[SUCCEEDED] Green stone by the wrecked freighter? Seen it. Left it. Huang things have a way of "
                                    "being missed.", 'Wrecked freighter')]),
    ('huang', 'FOLabMakapuuGuard', 55, [
        (('jade', 'Speech'), "[SUCCEEDED] Green charm in hold. On big crate. Elders' word only.", None),
        (('jade', 'Lockpick'), "[SUCCEEDED] Elders' hall. In cabinet. One charm. You not hear from me.", None)]),
    ('huang', ('ref', 'FOLabHuangOilGiverREF'), 40, [
        (('jade', 'Medicine'), "[SUCCEEDED] The family in the first home keeps one on their shelf, by the medicines.", None),
        (('jade', 'Survival'), "[SUCCEEDED] The third home has one too, on the same kind of shelf. The grandmother's.", None)]),
    ('huang', ('ref', 'FOLabHuangSilkGiverREF'), 55, [
        (('jade', 'Unarmed'), "[SUCCEEDED] One went with a man who hid in the lava tube. He left it on the floor at the very end when "
                              "he went.", "Pele's Pipe"),
        (('jade', 'Science'), "[SUCCEEDED] We traded one to the Vault, long ago. They keep it on a dresser, deep inside.", "Ka'au Crater")]),
    ('court', ('ref', 'FOLabKPWatchmanREF'), 40, [
        (('jade', 'Guns'), "[SUCCEEDED] Fourth floor of the ghouls' tower. A green charm on a dining table. I saw it and didn't go "
                           "back for it.", 'Kahuna Palms')]),
    ('court', 'FOLabKahunaGuard01', 55, [
        (('jade', 'Sneak'), "[SUCCEEDED] The Kilauea maze, fourth floor: a green charm in a locker cabinet.", None),
        (('jade', 'MeleeWeapons'), "[SUCCEEDED] Third floor of the Kilauea, on a dining table. Bring the court a share of whatever "
                                   "else you find up there.", None)]),
]


def _key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and r.get('subs')
                 and recordio.field(r, 'EDID') == edid), None)


def _person(pr, how):
    if isinstance(how, tuple):
        return next((r.get('base') for c in pr.cells.values() for r in (c.get('refs') or {}).values()
                     if r.get('edid') == how[1] and not r.get('removed')), None)
    return _key(pr, how, 'NPC_')


def _var(item):
    import collectibles as C
    kind, stat = item
    return '%s%d' % (kind, (C.SPECIAL if kind == 'hula' else C.SKILLS).index(stat) + 1)


def covered(rows=None):
    """Items no hint names: of the tables, or of a plan's rows (what the mod has)."""
    import collectibles as C
    if rows is None:
        have = {t[1] for t in TERMINALS} | {h[0] for p in PEOPLE for h in p[3]}
    else:
        have = {tuple(r['item']) for r in rows if r['what'] == 'term'} | {tuple(h['item']) for r in rows if r['what'] == 'person'
                                                                           for h in r['hints']}
    return [(k, s) for k, ss in (('hula', C.SPECIAL), ('jade', C.SKILLS)) for s in ss if (k, s) not in have]


def _markers(pr):
    import rumours
    out = {}
    for ck, c in pr.cells.items():
        for rk, r in (c.get('refs') or {}).items():
            m = r.get('marker')
            name = m.get('name') if isinstance(m, dict) else m
            if name and not r.get('removed'):
                out.setdefault(str(name), (ck, rk, r.get('edid') or rumours._edid_of(str(name)), bool(r.get('edid'))))
    return out


def plan(gd, pr):
    rows, skipped = [], []
    if _key(pr, QUEST, 'QUST'):
        return rows, [(QUEST, 'already in the mod (Undo first)')]
    if not _key(pr, COLLECT, 'QUST'):
        return rows, [(COLLECT, 'not in the mod (collectibles first)')]
    mk = _markers(pr)
    for term, item, title, text, m in TERMINALS:
        k = _key(pr, term, 'TERM')
        if not k:
            skipped.append((term, 'not in the mod'))
            continue
        rows.append({'what': 'term', 'term': k, 'edid': term, 'item': list(item), 'title': title, 'text': text,
                     'map': mk.get(m) if m else None})
    for group, who, speech, hints in PEOPLE:
        k = _person(pr, who)
        if not k:
            skipped.append((str(who), 'not in the mod'))
            continue
        rows.append({'what': 'person', 'group': group, 'npc': k, 'who': str(who), 'speech': speech,
                     'hints': [{'item': list(i), 'words': w, 'map': mk.get(m) if m else None} for i, w, m in hints]})
    for m in {t[4] for t in TERMINALS if t[4]} | {h[2] for p in PEOPLE for h in p[3] if h[2]}:
        if m not in mk:
            skipped.append((m, 'no map marker of that name: its hint gives no map'))
    return rows, skipped


def _marker_forms(gd, forms, marks):
    """forms with the map markers a hint ShowMaps ({ref key: editor ID}) as persistent stand-ins the compiler takes for map
    markers (rumours' way; a marker the source plugin placed keeps the plugin's key)."""
    import scriptc
    import tes4
    for key, edid in marks.items():
        forms.own[edid.lower()] = (key, {'type': 'REFR', 'flags': tes4.PERSISTENT, 'subs': [
            {'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': edid}]})
    names = set(marks.values())
    was = forms.is_map_marker
    forms.is_map_marker = lambda f, was=was: (f.rec is not None and recordio.field(f.rec, 'EDID') in names) or was(f)
    plain = forms.find_edid

    def find_edid(name, plain=plain):
        hit = forms.own.get(name.lower())
        if hit and not hit[0].startswith('+'):
            return scriptc.Form(forms, gd.from_key(hit[0]), 'REFR', True, None, hit[1])
        return plain(name)
    forms.find_edid = find_edid
    return forms


def _cond(fn, op, value, p1=0, p2=0, run=0):
    return {'or': False, 'use_target': False, 'op': op, 'fn': fn, 'p1': p1, 'p2': p2, 'run': run, 'ref': '', 'value': float(value)}


def _vars(srec):
    index, last = {}, None
    for sub in srec['subs']:
        if sub['tag'] == 'SLSD':
            last = next(f['value'] for f in sub['fields'] if f.get('name') == 'Index')
        elif sub['tag'] == 'SCVR' and last is not None:
            index[sub['value'].lower()] = last
    return index


def ops(gd, pr, P=None):
    import api_quests as aq
    import api_scripts
    import questrec as qr
    import terminals
    from activity import _new_key
    rows, skipped = P or plan(gd, pr)
    if not rows:
        raise ValueError('nothing to do: %s' % (skipped,))
    out, extra, rep = [], {}, {'made': [], 'entries': 0, 'checks': 0, 'skipped': skipped, 'missing': []}
    cq = _key(pr, COLLECT, 'QUST')
    cv = _vars(pr.records[recordio.field(pr.records[cq], 'SCRI')])
    # the markers a hint maps, named and kept loaded
    named = {}
    for r in rows:
        for m in ([r['map']] if r['what'] == 'term' else [h['map'] for h in r['hints']]):
            if m and not m[3] and m[1] not in named:
                out.append({'op': 'ref_set', 'cell': m[0], 'ref': m[1], 'set': {'edid': m[2], 'persistent': True}})
                named[m[1]] = m[2]
    marks = {r['map'][1]: r['map'][2] for r in rows if r['what'] == 'term' and r['map']}
    marks.update({h['map'][1]: h['map'][2] for r in rows if r['what'] == 'person' for h in r['hints'] if h['map']})
    forms = _marker_forms(gd, terminals.mod_forms(gd, pr), marks)
    # Science: entries on the terminals, each shown while its item isn't found
    terms = {}
    for r in rows:
        if r['what'] != 'term':
            continue
        rec = terms.setdefault(r['term'], json.loads(json.dumps(pr.records[r['term']])))
        src = 'ShowMap %s' % r['map'][2] if r['map'] else ''
        rec['subs'] += [terminals._z('ITXT', 'Menu item text', r['title']), terminals._z('RNAM', 'Result text', terminals._crlf(r['text'])),
                        {'tag': 'ANAM', 'label': 'Menu item flags', 'kind': 'struct', 'fields': [{'name': 'Flags', 'code': 'B', 'value': 0}]}]
        rec['subs'] += terminals._script_parts(src, forms)
        rec['subs'].append(qr.condition_sub(_cond(GETQV, '=', 0, cq, cv[_var(tuple(r['item']))])))
        rep['entries'] += 1
    for k, rec in terms.items():
        out.append({'op': 'record', 'key': k, 'record': rec})
    # Speech: the quest and a topic a group
    qk, qsk = _new_key(pr), _new_key(pr)
    quest = qr.quest_record({'edid': QUEST, 'script': qsk, 'name': '', 'flags': {'start_enabled': True}, 'priority': 45, 'delay': 30.0,
                             'stages': [], 'objectives': []})
    sc = api_scripts.scripts()
    c = sc.compile('scn %s\nshort started\nBegin GameMode\nset started to 1\nEnd\n' % QSCRIPT, qsk, 'quest', {qk: quest})
    if not hasattr(c, 'subrecords'):
        raise ValueError('the hints quest script: %s' % (c,))
    out += [{'op': 'record', 'key': qsk, 'record': sc._record_of(c, QSCRIPT)}, {'op': 'record', 'key': qk, 'record': quest}]
    rep['made'] += [QUEST, QSCRIPT]
    topics = {}
    for g, words in TOPICS.items():
        topics[g] = _new_key(pr)
        out.append({'op': 'record', 'key': topics[g], 'record': qr.topic_record({
            'edid': 'FOLabHint' + g.capitalize(), 'name': words, 'priority': 50.0, 'kind': 0, 'flags': {'top_level': True},
            'quests': [{'quest': qk, 'links': []}]})})
        rep['made'].append('FOLabHint' + g.capitalize())
    speech = gd.key(next(f for f, (_i, r) in gd.forms.items() if r.tag == 'AVIF' and gd.edid(f) == 'AVSpeech'))
    lines = []

    def line(topic, who, words, conds, end, skill=True):
        l = aq.new_line_plain(gd, pr, topic, qk, who, words, conditions=conds)
        if skill:
            l['skill'] = speech
        if end:
            l['end'] = {'source': end, 'parts': None}
        lines.append(l)
    for r in rows:
        if r['what'] != 'person':
            continue
        g = r['group']
        secret = [_cond(GETQV, '>=', 1, cq, cv['jadecount'])] if g == 'huang' else []
        for h in r['hints']:
            unfound = [_cond(GETQV, '=', 0, cq, cv[_var(tuple(h['item']))])]
            line(topics[g], r['npc'], h['words'], secret + unfound + [_cond(GETAV, '>=', r['speech'], SPEECH_AV, 0, 1)],
                 'ShowMap %s' % h['map'][2] if h['map'] else '')
            line(topics[g], r['npc'], FAILS[g], secret + unfound + [_cond(GETAV, '<', r['speech'], SPEECH_AV, 0, 1)], '')
            rep['checks'] += 1
        line(topics[g], r['npc'], NOTHING[g], secret, '', skill=False)      # (all theirs found: last in the topic)
    rep['lines'] = len(lines)
    rep['uncovered'] = covered(rows)
    rep['missing'] = [('no hint', i) for i in rep['uncovered']]
    rep['keys'] = {'quest': qk}
    rep['_marks'] = marks
    return out, rep, lines


def apply(pr, gd, P=None):
    import api_quests as aq
    import questrec as qr
    o, rep, lines = ops(gd, pr, P)
    pr.apply(LABEL, o)
    forms = _marker_forms(gd, aq.ModForms(gd, pr), rep.pop('_marks'))
    recs = []
    for l in lines:
        l.setdefault('begin', None)
        l.setdefault('end', None)
        errors = aq.compile_line(l, forms)
        if errors:
            raise ValueError('a hint line: %s' % errors[0])
        recs.append({'op': 'record_new', 'record': qr.info_record(l)})
    pr.apply(LABEL, recs, merge=True)
    return rep
