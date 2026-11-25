"""Rumours (docs/waikiki-speech-science.md section J, system 3): Waikiki's locals answer "Heard anything?" with one rumour
a talk, each told once. The harder ones take more Speech to get out of them. Each points to a decided place and marks it
on your map (ShowMap of its map marker).

`RUMOURS`: (map marker's name, Speech, what they say). Only decided places and facts:
- Kahuna Palms (the ghouls' tower, the court wants it back);
- Makapu'u Gate (the Huang's one gate for trade);
- the Kahala's trade ground (where the two sides meet and trade);
- the Radar Dome (a crashed Vertibird);
- the Heights (paid for the Vault, shut out);
- the Watcher's Hut (a man who counts who goes up the Palolo road and sells it);
- Ka'au Crater (the Vault's lights at night);
- Loa Gate (a city of scoundrels in the hills, more men than it looks).

**Who tells them:** the locals of Waikiki (`TELLERS`: waikikilife's locals, activity's market-goers, stallholders and
fishers), each line said by any of them (GetIsID, OR'd). With none left that you can get, "Nothing worth telling."

**Map markers:** each rumour's marker is given an editor ID (persistent) so ShowMap can name it. The lines are voiced in
the step (VOICE: every voice-type folder the tellers may use).

    plan(gd, pr)       {'rows': [rumours with their marker refs], 'skipped'}
    apply(pr, gd, P)   one Undo
"""
import json
import re

import recordio

LABEL = 'Rumours in Waikiki'
VOICE = ['FOLabRumours']
QUEST = 'FOLabRumours'
TELLERS = ('FOLabWaikikiLocal', 'FOLabWaikikiLocal2', 'FOLabMarketGoer', 'FOLabMarketSeller', 'FOLabPierFisher')
RUMOURS = [
    ('Kahuna Palms', 25, "The round hotel at the west end of the strip? Full of the dead that walk. The court wants it back."),
    ("Makapu'u Gate", 25, "The Huang trade at Makapuu Gate, out east. Polite, if you're polite. Don't touch anything."),
    ('Kahala Reef', 40, "Pirates trade outside the Kahala's walls. Nobody fights on the trade ground. That's the rule, they say."),
    ('Radar Dome', 40, "There's an old radar dome up on the Waialae Nui ridge. One of those flying machines came down there before the war."),
    ('The Heights', 55, "The ghouls up in the Heights paid for places in the Vault, way back. Never got in. They're still sore about it."),
    ("Watcher's Hut", 55, "There's a man in a hut up on St. Louis Heights. Counts who gets marched up the Palolo road. Sells what he sees."),
    ("Ka'au Crater", 70, "See those lights up the mountain at night? Ka'au. That's the Vault. Nobody goes up there. Not on purpose."),
    ('Loa Gate', 70, "Loa Gate, up in the hills. Scoundrels from every side. More men up there than anybody likes to say."),
]
ASK = "Heard anything?"
NOTHING = "Nothing worth telling. Ask me another day."


def _mod_key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and recordio.field(r, 'EDID') == edid), None)


def _edid_of(name):
    return 'FOLabMarker%sREF' % re.sub(r'[^A-Za-z0-9]', '', name)


def plan(gd, pr):
    tellers = [k for k in (_mod_key(pr, e, 'NPC_') for e in TELLERS) if k]
    if not tellers:
        return {'rows': [], 'skipped': [('rumours', 'none of the tellers is in the mod')]}
    markers = {}
    for ck, c in pr.cells.items():
        for rk, r in (c.get('refs') or {}).items():
            m = r.get('marker')
            name = m.get('name') if isinstance(m, dict) else m
            if name and not r.get('removed'):
                markers.setdefault(str(name), (ck, rk, r.get('edid')))
    rows, skipped = [], []
    for name, speech, words in RUMOURS:
        if name not in markers:
            skipped.append((name, 'no map marker of that name'))
            continue
        ck, rk, edid = markers[name]
        rows.append({'name': name, 'speech': speech, 'words': words, 'cell': ck, 'ref': rk, 'edid': edid or _edid_of(name), 'named': bool(edid)})
    return {'rows': rows, 'tellers': tellers, 'skipped': skipped}


def _cond(fn, op, value, p1=0, p2=0, run=0, orr=False):
    return {'or': orr, 'use_target': False, 'op': op, 'fn': fn, 'p1': p1, 'p2': p2, 'run': run, 'ref': '', 'value': float(value)}


def ops(gd, pr, P=None):
    import api_quests as aq
    import api_scripts
    import parley
    import questrec as qr
    from activity import _new_key
    if _mod_key(pr, QUEST, 'QUST'):
        raise ValueError('the mod already has %s (Undo first)' % QUEST)
    P = P or plan(gd, pr)
    rows = P['rows']
    if not rows:
        raise ValueError('nothing to tell: %s' % P['skipped'])
    out, rep = [], {'made': [], 'rumours': len(rows), 'skipped': P['skipped']}
    for r in rows:
        if not r['named']:
            out.append({'op': 'ref_set', 'cell': r['cell'], 'ref': r['ref'], 'set': {'edid': r['edid'], 'persistent': True}})
    sc = api_scripts.scripts()
    quest_key, qs_key = _new_key(pr), _new_key(pr)
    quest = qr.quest_record({'edid': QUEST, 'script': qs_key, 'name': '', 'flags': {'start_enabled': True},
                             'priority': 45, 'delay': 5.0, 'stages': [], 'objectives': []})
    c = sc.compile('\n'.join(['scn FOLabRumoursScript'] + ['short told%d' % n for n in range(len(rows))] + ['', 'Begin GameMode', 'End', '']),
                   qs_key, 'quest', {quest_key: quest})
    if not hasattr(c, 'subrecords'):
        raise ValueError('the rumours script: %s' % (c,))
    qrec = sc._record_of(c, 'FOLabRumoursScript')
    out += [{'op': 'record', 'key': qs_key, 'record': qrec}, {'op': 'record', 'key': quest_key, 'record': quest}]
    rep['made'] += [QUEST, 'FOLabRumoursScript']
    qv = parley._vars(qrec)
    topic = _new_key(pr)
    out.append({'op': 'record', 'key': topic, 'record': qr.topic_record({'edid': 'FOLabRumoursAsk', 'name': ASK, 'priority': 50.0, 'kind': 0,
                                                                        'flags': {'top_level': True},
                                                                        'quests': [{'quest': quest_key, 'links': []}]})})
    speech = gd.key(next(f for f, (i, rr) in gd.forms.items() if rr.tag == 'AVIF' and gd.edid(f) == 'AVSpeech'))
    tellers = P['tellers']
    who = [_cond(72, '=', 1, k, 0, 0, orr=(n < len(tellers) - 1)) for n, k in enumerate(tellers)]     # (any teller: OR'd)
    lines = []
    for n, r in enumerate(rows):
        l = aq.new_line_plain(gd, pr, topic, quest_key, None, r['words'], conditions=who + [
            _cond(79, '=', 0, quest_key, qv['told%d' % n]), _cond(14, '>=', r['speech'], 43, 0, 1)])
        l['skill'] = speech if r['speech'] > 25 else ''
        l['end'] = {'source': 'set %s.told%d to 1\nShowMap %s' % (QUEST, n, r['edid']), 'parts': None}
        lines.append(l)
    l = aq.new_line_plain(gd, pr, topic, quest_key, None, NOTHING, conditions=list(who))
    lines.append(l)
    rep['lines'] = len(lines)
    rep['markers'] = {r['name']: r['edid'] for r in rows}
    rep['_markers'] = [(r['ref'], r['edid']) for r in rows]
    return out, rep, lines


def apply(pr, gd, P=None):
    import api_quests as aq
    o, rep, lines = ops(gd, pr, P)
    pr.apply(LABEL, o)
    names = {e for _rk, e in rep.pop('_markers')}
    forms = aq.ModForms(gd, pr)
    import tes4
    for ck, c in pr.cells.items():                     # (the markers by their new names, map markers to the compiler)
        for rk, r in (c.get('refs') or {}).items():
            if r.get('edid') in names:
                forms.own[r['edid'].lower()] = (rk, {'type': 'REFR', 'flags': tes4.PERSISTENT,
                                                     'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': r['edid']}]})
    forms.is_map_marker = lambda f: f.rec is not None and recordio.field(f.rec, 'EDID') in names
    plain = forms.find_edid
    import scriptc

    def find_edid(name, plain=plain):            # (a marker the source plugin placed has the plugin's key, not the mod's '+')
        hit = forms.own.get(name.lower())
        if hit and not hit[0].startswith('+'):
            return scriptc.Form(forms, gd.from_key(hit[0]), 'REFR', True, None, hit[1])
        return plain(name)
    forms.find_edid = find_edid
    recs = []
    for l in lines:
        l.setdefault('begin', None)
        l.setdefault('end', None)
        errors = aq.compile_line(l, forms)
        if errors:
            raise ValueError('a rumour line: %s' % errors[0])
        import questrec as qr
        recs.append({'op': 'record_new', 'record': qr.info_record(l)})
    pr.apply(LABEL, recs, merge=True)
    return rep
