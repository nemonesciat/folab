"""Perks of the island's own (docs/waikiki-speech-science.md section J, system 13; the user, 25 Nov 2026: all five).

Each is a PERK of the mod's own (laid out as the game's: EDID, FULL, DESC, ICON, the skill it asks as GetPermanentActorValue
conditions, DATA level, one rank, playable), with no entry points of its own: what each does is built from things nv-rs
runs as the game does (conditions, scripts, the game's own spell), so nothing waits on a perk entry point.

- **Kahuna's Ear** (Speech 50, level 8): every Speech check of the mod's (`EAR_HINTS`, by topic) says what a pass gives
  ("Show me what the ship carries. (the hold key)"). Each check line is copied as the first of its topic for those with
  the perk (HasPerk), with its own prompt; the words, the check and what it does are the line's own, and its voice files
  are the original's (copied under the copy's form ID: the same words, the same speaker).
- **Salvager** (Science 50, level 8): the mod's robots (robots.py's records) leave parts when they die (an OnDeath script:
  2 Scrap Electronics, and a Sensor Module one time in two), only with the perk. The maintenance panels' shut-down counts.
- **Storm-Wise** (Survival 40, level 6): the barometers read exactly without Science 40 (barometer.py's script asks
  HasPerk too; made again here when the barometers are in, and barometer.py asks it when this is in first).
- **Reef Diver** (Survival 50, level 8): each time you go into the water, 60 seconds of breathing under it (`DIVE`): the quest
  FOLabReefDiver gives the game's water breathing spell (the Rebreather's) and takes it away when the time is up or you
  leave the water, never while a rebreather is worn. (Longer breath itself is the game's breath timer, not readable to a
  perk without an extender.)
- **Island Tongue** (Speech 40, level 6): the Huang's Speech checks are `TONGUE` easier (Zhao Lei's mend 55 to 40, the
  elder's hold 85 to 70): those lines copied first in their topics, the checks lowered, for those with the perk.
- **[proposal]** The levels, names and words are this step's own.

    plan(gd, pr)       (rows, skipped)
    apply(pr, gd, P)   one Undo; then the copies' voice files (copied, not spoken) and their voices.json entries
"""
import json
import os
import re
import shutil

import recordio

LABEL = 'Perks of the island'
SPEECH, SCIENCE, SURVIVAL = 43, 40, 44
GETPERMAV, HASPERK, GETAV = 495, 449, 14
PERKS = {   # key: (editor ID, name, skill, at least, level, icon from the game's perk, what it says)
    'ear': ('FOLabPerkKahunasEar', "Kahuna's Ear", SPEECH, 50, 8, 'TerrifyingPresence',
            "You hear what people want before they say it. When you try to talk your way through, you know what it would get you."),
    'salvager': ('FOLabPerkSalvager', 'Salvager', SCIENCE, 50, 8, 'RoboticsExpert',
                 "The island's old machines are full of parts if you know where to look. Robots you bring down leave Scrap "
                 "Electronics, and sometimes a Sensor Module."),
    'storm': ('FOLabPerkStormWise', 'Storm-Wise', SURVIVAL, 40, 6, 'Survivalist',
              "You've lived through enough island storms to read a barometer as well as any scientist."),
    'reef': ('FOLabPerkReefDiver', 'Reef Diver', SURVIVAL, 50, 8, 'Swift Learner',
             "You learned to dive on the reef. Each time you go into the water you can stay under for a minute longer."),
    'tongue': ('FOLabPerkIslandTongue', 'Island Tongue', SPEECH, 40, 6, 'LadyKiller',
               "You've picked up enough of the Huang's ways and words that they listen. Talking with them is easier."),
}
EAR_HINTS = {   # topic editor ID: what a pass gives
    'FOLabSpeechComber': 'a share of the find', 'FOLabSpeechLeilani': 'the truth', 'FOLabSpeechDoctor': 'more medicine',
    'FOLabSpeechGate': 'the courtyards', 'FOLabSpeechLinda': 'Huang clothes', 'FOLabSpeechLiuwei': 'thirty more rounds',
    'FOLabSpeechWatchman': 'koa armour', 'FOLabPirateDealsDeal': 'trade, pirate fame', 'FOLabPirateDealsGuest': 'no toll, court fame',
    'FOLabParleyPersuade': 'through, no fight', 'FOLabParleyIntimidate': 'through, and they fear you',
    'FOLabParleyPlead': 'through, but they think you soft', 'FOLabParleyYieldJoin': 'a follower',
    'FOLabHuangStandingMend': 'less infamy with the Huang', 'FOLabHuangStandingHold': 'the hold key',
}
TONGUE_TOPICS = ('FOLabHuangStandingMend', 'FOLabHuangStandingHold')
TONGUE = 15
DIVE = 60.0
SPELL, MASKS = 'VMS15WaterBreathingActual', ('VMS15Rebreather', 'FOLabRebreather')
SALVAGE = [('ScrapElectronics', 2, 100), ('SensorModule', 1, 50)]
ROBOT_WORD = re.compile(r'^FOLabRobot')
REEF_QUEST, REEF_SCRIPT, SALVAGE_SCRIPT = 'FOLabReefDiver', 'FOLabReefDiverScript', 'FOLabSalvagerScript'


def _key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and recordio.field(r, 'EDID') == edid), None)


def _game(gd, tag, edid):
    return next((f for f, (_i, r) in gd.forms.items() if r.tag == tag and gd.edid(f) == edid), None)


def _cond(fn, op, value, p1=0, p2=0, run=0):
    return {'or': False, 'use_target': False, 'op': op, 'fn': fn, 'p1': p1, 'p2': p2, 'run': run, 'ref': '', 'value': float(value)}


def _speech_cond(c):
    return int(c['fn']) == GETAV and str(c.get('p1')).split('.')[0] == str(SPEECH)


def plan(gd, pr):
    import questrec as qr
    rows, skipped = [], []
    if _key(pr, PERKS['ear'][0], 'PERK'):
        return rows, [('perks', 'already in the mod (Undo first)')]
    topics = {k: recordio.field(r, 'EDID') for k, r in pr.records.items() if r.get('type') == 'DIAL'}
    checks = []
    for k, rec in sorted(pr.records.items()):
        if rec.get('type') != 'INFO' or topics.get(rec.get('topic')) not in EAR_HINTS:
            continue
        if any(_speech_cond(c) for c in qr.info_plain(rec)['conditions']):
            checks.append({'line': k, 'topic': rec['topic'], 'topic_edid': topics[rec['topic']]})
    rows.append({'what': 'perks', 'perks': [p[0] for p in PERKS.values()]})
    rows.append({'what': 'ear', 'lines': len(checks), 'checks': checks})
    missing = sorted(set(EAR_HINTS) - set(topics.values()))
    if missing:
        skipped.append(('ear', 'topics not in the mod: %s' % ', '.join(missing)))
    robots = [k for k, r in pr.records.items() if r.get('type') == 'CREA' and ROBOT_WORD.match(recordio.field(r, 'EDID') or '')]
    rows.append({'what': 'salvager', 'robots': robots})
    rows.append({'what': 'storm', 'barometer': bool(_key(pr, 'FOLabBarometerScript', 'SCPT'))})
    rows.append({'what': 'reef'})
    return rows, skipped


def perk_record(gd, key):
    import questrec as qr
    edid, name, skill, least, level, icon_from, words = PERKS[key]
    f = _game(gd, 'PERK', icon_from) or _game(gd, 'PERK', 'Educated')
    icon = recordio.field(recordio.load(gd, f), 'ICON') if f else ''
    subs = [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': edid},
            {'tag': 'FULL', 'label': 'Name', 'kind': 'z', 'value': name},
            {'tag': 'DESC', 'label': 'Description', 'kind': 'z', 'value': words}]
    if icon:
        subs.append({'tag': 'ICON', 'label': 'Icon', 'kind': 'z', 'value': icon})
    subs.append(qr.condition_sub(_cond(GETPERMAV, '>=', least, skill)))
    subs.append({'tag': 'DATA', 'label': 'Data', 'kind': 'struct', 'fields': [
        {'name': 'Trait', 'code': 'B', 'value': 0}, {'name': 'Level', 'code': 'B', 'value': level},
        {'name': 'Ranks', 'code': 'B', 'value': 1}, {'name': 'Playable', 'code': 'B', 'value': 1},
        {'name': 'Hidden', 'code': 'B', 'value': 0}]})
    return {'type': 'PERK', 'flags': 0, 'src': '', 'subs': subs}


def reef_source(have_mask):
    worn = ' && '.join('player.GetEquipped %s == 0' % m for m in have_mask) or '1'
    return '\n'.join([
        'scn %s' % REEF_SCRIPT, '', 'short diving', 'float left', '', 'Begin GameMode',
        '\tif player.HasPerk %s == 0' % PERKS['reef'][0], '\t\treturn', '\tendif',
        '\tif player.IsSwimming',
        '\t\tif diving == 0', '\t\t\tset diving to 1', '\t\t\tset left to %s' % DIVE,
        '\t\t\tif %s' % worn, '\t\t\t\tplayer.AddSpell %s' % SPELL, '\t\t\tendif',
        '\t\telseif diving == 1', '\t\t\tset left to left - GetSecondsPassed',
        '\t\t\tif left <= 0', '\t\t\t\tset diving to 2',
        '\t\t\t\tif %s' % worn, '\t\t\t\t\tplayer.RemoveSpell %s' % SPELL, '\t\t\t\tendif', '\t\t\tendif',
        '\t\tendif',
        '\telseif diving',
        '\t\tif diving == 1 && %s' % worn, '\t\t\tplayer.RemoveSpell %s' % SPELL, '\t\tendif', '\t\tset diving to 0',
        '\tendif', 'End', ''])


def salvage_source():
    L = ['scn %s' % SALVAGE_SCRIPT, '', 'Begin OnDeath', '\tif player.HasPerk %s' % PERKS['salvager'][0]]
    for item, n, chance in SALVAGE:
        if chance >= 100:
            L.append('\t\tAddItem %s %d' % (item, n))
        else:
            L += ['\t\tif GetRandomPercent < %d' % chance, '\t\t\tAddItem %s %d' % (item, n), '\t\tendif']
    return '\n'.join(L + ['\tendif', 'End', ''])


def ops(gd, pr, P=None):
    import api_characters as ac
    import api_quests as aq
    import api_scripts
    import questrec as qr
    from activity import _new_key
    rows, skipped = P or plan(gd, pr)
    if not rows:
        raise ValueError('nothing to do: %s' % (skipped,))
    R = {r['what']: r for r in rows}
    out, made, extra = [], [], {}
    keys = {}
    for k in PERKS:
        keys[k] = _new_key(pr)
        extra[keys[k]] = perk_record(gd, k)
        out.append({'op': 'record', 'key': keys[k], 'record': extra[keys[k]]})
        made.append(PERKS[k][0])
    sc = api_scripts.scripts()
    # Salvager: the robots' death script
    sk = _new_key(pr)
    c = sc.compile(salvage_source(), sk, 'object', extra)
    if not hasattr(c, 'subrecords'):
        raise ValueError('the salvager script: %s' % (c,))
    out.append({'op': 'record', 'key': sk, 'record': sc._record_of(c, SALVAGE_SCRIPT)})
    made.append(SALVAGE_SCRIPT)
    for rk in R['salvager']['robots']:
        rec = json.loads(json.dumps(pr.records[rk]))
        rec['subs'] = [s for s in rec['subs'] if s['tag'] != 'SCRI']
        ac.insert(rec, {'tag': 'SCRI', 'label': 'Script', 'kind': 'F', 'value': sk})
        out.append({'op': 'record', 'key': rk, 'record': rec})
    # Reef Diver: its quest
    qk, qsk = _new_key(pr), _new_key(pr)
    quest = qr.quest_record({'edid': REEF_QUEST, 'script': qsk, 'name': '', 'flags': {'start_enabled': True},
                             'priority': 10, 'delay': 0.5, 'stages': [], 'objectives': []})
    masks = [m for m in MASKS if _game(gd, 'ARMO', m) is not None or _key(pr, m, 'ARMO')]
    c = sc.compile(reef_source(masks), qsk, 'quest', dict(extra, **{qk: quest}))
    if not hasattr(c, 'subrecords'):
        raise ValueError('the reef diver script: %s' % (c,))
    out += [{'op': 'record', 'key': qsk, 'record': sc._record_of(c, REEF_SCRIPT)}, {'op': 'record', 'key': qk, 'record': quest}]
    made += [REEF_QUEST, REEF_SCRIPT]
    # Storm-Wise: the barometers' script made again with it, when they're in
    if R['storm']['barometer']:
        import barometer
        bsk = _key(pr, barometer.SCRIPT, 'SCPT')
        c = sc.compile(barometer.source(_has_wrack(pr), storm_wise=True), bsk, 'quest', extra)
        if not hasattr(c, 'subrecords'):
            raise ValueError('the barometer script: %s' % (c,))
        out.append({'op': 'record', 'key': bsk, 'record': sc._record_of(c, barometer.SCRIPT)})
        made.append(barometer.SCRIPT)
    # Kahuna's Ear and Island Tongue: the check lines copied first in their topics
    copies = []
    for ch in R['ear']['checks']:
        rec = pr.records[ch['line']]
        seq = qr.line_seq(ch['line'], rec)
        topic_name = recordio.field(pr.records[ch['topic']], 'FULL') or ''
        hint = EAR_HINTS[ch['topic_edid']]
        sets = [('ear', [keys['ear']], 0, '%s (%s)' % (topic_name, hint), -0.1)]
        if ch['topic_edid'] in TONGUE_TOPICS:
            sets = [('tongue_ear', [keys['tongue'], keys['ear']], TONGUE, '%s (%s)' % (topic_name, hint), -0.3),
                    ('tongue', [keys['tongue']], TONGUE, None, -0.2)] + sets
        for name, perks_needed, easier, prompt, before in sets:
            l = qr.info_plain(json.loads(json.dumps(rec)))
            l['topic'] = rec['topic']
            for c in l['conditions']:
                if easier and _speech_cond(c):
                    c['value'] = float(c['value']) - easier
            l['conditions'] += [_cond(HASPERK, '=', 1, p, 0, 1) for p in perks_needed]
            if prompt:
                l['prompt'] = prompt
            new = aq._compiled_line(gd, pr, l)
            new['topic'] = rec['topic']
            new['seq'] = seq + before
            nk = _new_key(pr)
            copies.append({'of': ch['line'], 'key': nk, 'set': name})
            out.append({'op': 'record', 'key': nk, 'record': new})
    return out, {'made': made, 'perks': {k: v[0] for k, v in PERKS.items()}, 'robots': len(R['salvager']['robots']),
                 'barometer': R['storm']['barometer'], 'copies': copies, 'skipped': skipped}


def _has_wrack(pr):
    sk = _key(pr, 'FOLabStormScript', 'SCPT')
    return bool(sk) and any(s['tag'] == 'SCVR' and s['value'].lower() == 'wrack' for s in pr.records[sk]['subs'])


def voice_copies(gd, pr, copies):
    """Each copied line's voice files from its original's (every voice folder that has them), and its voices.json entry."""
    import api_voices as av
    import library
    root = library.assets_dir(pr)
    V = av.load(pr)
    got, missing = 0, []
    folders = os.path.join(root, 'sound', 'voice')
    # (FOLAB_VOICE_FROM: other homes' voice folders to read originals from, for a rehearsal on a copy without the assets)
    sources = [folders] + [os.path.join(x, 'sound', 'voice') for x in os.environ.get('FOLAB_VOICE_FROM', '').split(';') if x]
    index = {}
    for src in sources:
        for dirpath, _dirs, files in os.walk(src):
            for f in files:
                m = re.search(r'_([0-9a-f]{8})_\d+\.(ogg|lip)$', f.lower())
                if m:
                    index.setdefault(m.group(1), {}).setdefault((os.path.relpath(dirpath, src).lower(), f.lower()), os.path.join(dirpath, f))
    for cp in copies:
        old_id = '%08x' % (int(cp['of'].lstrip('+'), 16) & 0xFFFFFF)
        new_id = '%08x' % (int(cp['key'].lstrip('+'), 16) & 0xFFFFFF)
        found = 0
        for (rel, f), path in (index.get(old_id) or {}).items():
            dst = os.path.join(folders, rel)
            os.makedirs(dst, exist_ok=True)
            shutil.copy2(path, os.path.join(dst, f.replace('_%s_' % old_id, '_%s_' % new_id)))
            found += 1
        got += found
        if not found:
            missing.append(cp['of'])
        for n, e in (V['lines'].get(cp['of']) or {}).items():
            e2 = dict(e)
            if e2.get('path'):
                e2['path'] = e2['path'].lower().replace('_%s_' % old_id, '_%s_' % new_id)
            V['lines'].setdefault(cp['key'], {})[n] = e2
    av.save(pr, V)
    return {'files': got, 'lines_without_files': missing}


def apply(pr, gd, P=None):
    import peopletalk
    o, rep = ops(gd, pr, P)
    pr.apply(LABEL, o)
    rep['voice'] = voice_copies(gd, pr, rep['copies'])
    plan = [{'line': c['key'], 'number': n + 1, 'unit': c['key'], 'keys': _speakers(pr, c['key'])}
            for c in rep['copies'] for n in range(len(_responses(pr, c['key'])))]
    rep['missing'] = peopletalk.unvoiced(gd, pr, plan)
    rep['copies'] = len(rep['copies'])
    return rep


def _responses(pr, key):
    import questrec as qr
    return qr.info_plain(pr.records[key])['responses']


def _speakers(pr, key):
    import questrec as qr
    return [c['p1'] for c in qr.info_plain(pr.records[key])['conditions'] if int(c['fn']) == 72 and c['op'] == '=' and c['p1']]
