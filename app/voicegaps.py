"""Every voiced line of the mod, in every folder its speakers may look in (the user, 23 Nov 2026: "some nameless NPCs had
lines, but they weren't voiced ... Albright had voices. So do the Kahuna's Guard").

The game looks for a line's sound under the voice type the SPEAKER has as it stands in the world. A person of the mod's
own whose look is a levelled list of the game's (template flag Use Traits) speaks as whatever voice type the list gave
them, so a crowd's line needs its .ogg and .lip in every folder that list can give (peopletalk.folders). Lines voiced
before peopletalk went into one folder only: the first speaker's own record's.

`gaps` walks every INFO of the mod's own and lists each response's missing folders. Who can say a line, from its
conditions on the subject: its speaker field, each GetIsID == 1 (OR'd or not), each GetInFaction == 1 (the mod's own
people of that faction, by SNAM); GetIsVoiceType == 1 keeps only those folders. A line naming nobody is counted as
`anyone` and left: no folder list can be said for it. `fill` speaks what's missing as peopletalk does: the folder the
line's own speaker uses keeps the voices.json choice; another folder of the same person and sex keeps it too; any other
(a crowd's other voice types, the other sex) gets a voice of its own from the line and folder (own_default). Lines in
Mandarin (huangland: voices.json 'lang' zh) are counted and left to huangtalk."""
import json
import os
import shutil

import recordio

GET_IS_ID, GET_IN_FACTION, GET_IS_VOICE_TYPE = 72, 71, 427


def _members(pr):
    """{faction key: [the mod's own NPC_ keys with that faction in their SNAM]}"""
    out = {}
    for k, r in pr.records.items():
        if r.get('type') != 'NPC_' or not k.startswith('+'):
            continue
        for s in r.get('subs', ()):
            if s['tag'] != 'SNAM':
                continue
            v = s.get('value') if 'value' in s else next((f.get('value') for f in s.get('fields', ())
                                                          if 'faction' in f.get('name', '').lower()), None)
            if isinstance(v, str):
                out.setdefault(v, []).append(k)
    return out


def _yes(c):
    return c.get('op') == '=' and c.get('value') == 1 and not c.get('run') and isinstance(c.get('p1'), str)


def speakers(plain, members):
    """(keys who can say it, voice type keys it is kept to or None)"""
    keys = [plain['speaker']] if plain.get('speaker') else []
    only = []
    for c in plain['conditions']:
        if not _yes(c):
            continue
        if c['fn'] == GET_IS_ID:
            keys.append(c['p1'])
        elif c['fn'] == GET_IN_FACTION:
            keys += members.get(c['p1'], [])
        elif c['fn'] == GET_IS_VOICE_TYPE:
            only.append(c['p1'])
    return list(dict.fromkeys(keys)), only or None


def gaps(gd, pr, voices=None, root=None, older_than=None):
    """(missing, report): missing is [{line, number, path (no extension), folder, female, primary, keys}]. root: another
    assets folder to look in; older_than: a file newer than this time counts as missing (how things stood then)."""
    import api_voices as av
    import library
    import peopletalk as PT
    import questrec as qr
    import voicegen
    voices = voices if voices is not None else av.load(pr)
    root = root or library.assets_dir(pr)
    members = _members(pr)
    fold = {}
    missing = []
    rep = {'lines': 0, 'responses': 0, 'folders looked in': 0, 'anyone': 0, 'no quest or topic': 0, 'mandarin missing': 0,
           'lines with a gap': 0, 'never voiced': 0}
    for k, rec in sorted(pr.records.items()):
        if rec.get('type') != 'INFO' or av.own_id(pr, k) is None:
            continue
        plain = qr.info_plain(json.loads(json.dumps(rec)))
        topic = plain.get('topic') or qr.line_topic(gd, pr, k, rec)
        if not plain.get('quest') or not topic:
            rep['no quest or topic'] += 1
            continue
        keys, only = speakers(plain, members)
        if not keys:
            rep['anyone'] += 1
            continue
        rep['lines'] += 1
        ks = tuple(keys)
        if ks not in fold:
            fold[ks] = PT.folders(gd, pr, ks)
        want = dict(fold[ks])
        if only:
            names = {av.edid(gd, pr, v).lower() for v in only}
            want = {f: fem for f, fem in want.items() if f in names}
        info = av.line_info(gd, pr, k, voices)
        primary = None if info['problem'] else (info['voice_type_edid'] or '').lower()
        if primary and primary not in want:
            want[primary] = bool(voices and info.get('choice') and voicegen.is_female(info['choice']['voice']))
        q, t = av.edid(gd, pr, plain['quest']), av.edid(gd, pr, topic)
        done = voices['lines'].get(k, {})
        gap = False
        for r in plain['responses']:
            rep['responses'] += 1
            had = done.get(str(r['number'])) or {}
            for f, female in sorted(want.items()):
                rep['folders looked in'] += 1
                rel = voicegen.voice_path(pr.plugin, f, q, t, av.own_id(pr, k), r['number'])
                base = os.path.join(root, rel)
                if all(os.path.isfile(base + e) and (older_than is None or os.path.getmtime(base + e) < older_than)
                       for e in ('.ogg', '.lip')):
                    continue
                gap = True
                if had.get('lang') == 'zh':
                    rep['mandarin missing'] += 1
                    continue
                missing.append({'line': k, 'number': r['number'], 'text': r['text'], 'path': rel, 'folder': f, 'female': female,
                                'primary': f == primary, 'keys': list(ks), 'mood': [av._mood_key(r)[0], int(r.get('strength', 50))]})
        if gap:
            rep['lines with a gap'] += 1
            if not done:
                rep['never voiced'] += 1
    rep['responses x folders missing'] = len(missing)
    return missing, rep


def fill(gd, pr, missing, progress=None):
    """Speaks each missing file (see the docstring). The primary folder's take is noted in voices.json, as voice_line does."""
    import api_voices as av
    import library
    import voicegen
    voices = av.load(pr)
    engine = av.engine_of(voices)
    root = library.assets_dir(pr)
    made, done, copied, problems = {}, 0, 0, []
    for n, m in enumerate(missing):
        info = av.line_info(gd, pr, m['line'], voices)
        c = info.get('choice') or {'voice': av.DEFAULT['female' if m['female'] else 'male'], 'speed': av.PACE, 'pitch': 0.0,
                                   'lively': av.LIVELY}
        if not m['primary'] and (len(m['keys']) > 1 or voicegen.is_female(c['voice']) != m['female']):
            c = dict(c, **(voices['type'].get(_vt_key(gd, pr, m['folder'])) or av.own_default('%s %s' % (m['line'], m['folder']), m['female'])))
        mood = m['mood']
        base = os.path.join(root, m['path'])
        key = (m['text'], c['voice'], float(c['speed']), float(c['pitch']), float(c['lively']), tuple(mood))
        try:
            if key in made:
                os.makedirs(os.path.dirname(base), exist_ok=True)
                for ext in ('.ogg', '.lip'):
                    shutil.copyfile(made[key] + ext, base + ext)
                copied += 1
            else:
                if engine == 'chatterbox':
                    voicegen.write_line(base, m['text'], c['voice'], float(c['speed']), float(c['pitch']), float(c['lively']),
                                        engine='chatterbox', feeling=av.feeling_of(mood[0], mood[1]))
                else:
                    times, up, tune = av.mood_of(mood[0], mood[1])
                    voicegen.write_line(base, m['text'], c['voice'], float(c['speed']) * times, float(c['pitch']) + up,
                                        float(c['lively']) * tune)
                made[key] = base
                done += 1
        except Exception as e:                                      # (one bad line doesn't stop the rest)
            problems.append((m['line'], m['folder'], repr(e)[:200]))
            continue
        if m['primary']:
            voices['lines'].setdefault(m['line'], {})[str(m['number'])] = {
                'text': m['text'], 'voice': c['voice'], 'speed': c['speed'], 'pitch': c['pitch'], 'lively': c['lively'],
                'path': m['path'], 'mood': mood, 'engine': engine}
        if progress and n % 25 == 0:
            progress('%d of %d: %d spoken, %d copied' % (n, len(missing), done, copied))
            av.save(pr, voices)
    av.save(pr, voices)
    library.publish(pr)
    return {'voiced': done, 'copied': copied, 'problems': problems}


_VT = {}


def _vt_key(gd, pr, folder):
    """The voice type key whose editor ID is this folder name (for a choice kept by voice type)."""
    if not _VT:
        for f, (_i, r) in gd.forms.items():
            if r.tag == 'VTYP':
                _VT[(gd.edid(f) or '').lower()] = gd.key(f)
        for k, r in pr.records.items():
            if r.get('type') == 'VTYP':
                _VT[(recordio.field(r, 'EDID') or '').lower()] = k
    return _VT.get(folder)
