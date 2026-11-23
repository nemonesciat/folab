"""Talk between the songs: short spoken bulletins on a station of the mod's own (radio.py), some of them about what the
player has done.

How the game does news, read from Radio New Vegas (quest RadioNewVegas, its lines by topic):
- The station's lines chain through choices (TCLT): RadioHello's greetings (set bDoTransition) choose RNVNewsIntro, which
  chooses RNVNewsStory; a story chooses RNVNewsTransition (only while bDoTransition is 1, which it clears) or RNVNewsPost
  (only once it's 0); the post chooses a song intro (RNVMusicIntroGeneric, or RNVMusicIntroSpecific naming the song to
  come), and the intro chooses RNVMusic. Every song line chooses RNVMusic again, and counts nTracksPlayed; songs are
  barred once it reaches 3, so the chain runs dry and the station starts over at RadioHello.
- A story is one of RNVNewsStory's 70 random lines that holds: its conditions are what has happened (GetQuestCompleted,
  GetDead on a placed person, the story globals VStoryEvent*, which the quests' own scripts set), so the news follows the
  player. A story too long for one line sets nStory and chooses RNVNewsStory2, whose lines wait on that number (and a
  third part, RNVNewsStory3, the same way). Of the game's radio lines, 145 ask GetQuestCompleted and 79 GetDead.
- A spoken line names no sound; the game plays its voice file by name, as any dialogue
  (sound\\voice\\<plugin>\\<the station's voice type>\\<quest>_<topic>_<line's form ID>_<n>.ogg, with its .lip). Mr. New
  Vegas has a voice type of his own (MaleUniqueMrNewVegas); Mojave Music Radio, which never speaks, the game's
  MaleAdult01Default.

What this does instead, on a station radio.py made (every song a line in RadioHello, picked at random, the last three
barred), so nothing about how songs are picked changes and no topic of the mod's own is needed:
- The station's script gains `short iSince`, songs since it last talked. Every song adds one to it; songs are barred
  while it is at `every` or more (the gate, radio.line_conditions), and talk lines wait for exactly that. A talk line
  sets it back to 0. So the station plays `every` songs, says one thing, plays `every` songs.
- A talk line is a line in RadioHello like a song's (random, run immediately, the same response numbers) with no sound,
  its words in NAM1, and its conditions: the gate, then what it's about (FACTS, in plain words), then how often (`times`:
  a variable of its own, iHeard<n>, counted up by the line, the line barred once it reaches that).
- The station must always have something to say when talk is due, or it goes quiet: at least one line about nothing in
  particular (an ident) with no facts and no `times`. `check` says so.
- Its voice is voicegen's (Chatterbox where it's there, else Kokoro), into the path the game looks for, under the
  station's voice type. The voice chosen is kept per station in voices.json's 'npc' (api_voices), as a character's.

Mandarin (lang 'zh'; Haixin Dongtai is the Huáng's and speaks Chinese, the user, 21 Nov 2026): the line is written in
pinyin, one response a sentence. What shows is the pinyin without tones (g2pzh.shown: the game's fonts are cp1252 and
have no Chinese characters or tone marks); the pinyin with tone numbers is kept in the response's notes as 'zh:...'
(NAM2), and the English for the user in its edits (NAM3); the game shows neither. It is voiced by Kokoro's Chinese voices
(g2pzh's sounds; ZH_DEFAULT, or the station's kept 'zh_voice'), not Chatterbox, whose installed model speaks English.

Facts (each {'kind', ...}; all of a line's must hold):
    {'kind': 'stage', 'quest': key, 'stage': n}        GetStageDone quest n == 1  (the quest reached that stage)
    {'kind': 'not_stage', 'quest': key, 'stage': n}    GetStageDone quest n == 0  (not yet)
    {'kind': 'done', 'quest': key}                     GetQuestCompleted quest == 1
    {'kind': 'found', 'marker': ref key}               GetMapMarkerVisible == 1, run on the map marker (as the game's 28)
    {'kind': 'dead', 'ref': ref key}                   GetDead == 1, run on that placed person (as the game's 647)
    {'kind': 'alive', 'ref': ref key}                  GetDead == 0"""
import json
import os
import re

import questrec as qr
import radio
import recordio
import scriptc

SINCE = 'iSince'
HEARD = 'iHeard%d'
ZH_DEFAULT = 'zm_yunjian'         # Kokoro's Chinese voices: zf_xiaobei, zf_xiaoni, zf_xiaoxiao, zf_xiaoyi, zm_yunjian, zm_yunxi, zm_yunxia, zm_yunyang
EVERY = 3                       # songs between talk, unless a station says otherwise
FN = {'stage': 59, 'done': 546, 'found': 492, 'dead': 46, 'qvar': radio.GET_QUEST_VARIABLE}
REFERENCE = 2                   # CTDA "run on": a chosen reference


def _cond(fn, value, op='=', p1='', p2=0, run=0, ref=''):
    return {'or': False, 'use_target': False, 'op': op, 'fn': fn, 'p1': p1, 'p2': p2, 'run': run, 'ref': ref, 'value': float(value)}


def fact_condition(f):
    k = f['kind']
    if k in ('stage', 'not_stage'):
        return _cond(FN['stage'], 1 if k == 'stage' else 0, p1=f['quest'], p2=int(f['stage']))
    if k == 'done':
        return _cond(FN['done'], 1, p1=f['quest'])
    if k == 'found':
        return _cond(FN['found'], 1, run=REFERENCE, ref=f['marker'])
    if k in ('dead', 'alive'):
        return _cond(FN['dead'], 1 if k == 'dead' else 0, run=REFERENCE, ref=f['ref'])
    raise radio.RadioProblem('A talk line can hang on a quest stage, a quest done, a place found or someone dead, not %r.' % k)


def fact_of(c):
    """The plain fact a condition is, or None (the gate, the times count)."""
    fn, v = c['fn'], c.get('value')
    if fn == FN['stage']:
        return {'kind': 'stage' if v == 1 else 'not_stage', 'quest': c['p1'], 'stage': int(c['p2'])}
    if fn == FN['done']:
        return {'kind': 'done', 'quest': c['p1']}
    if fn == FN['found']:
        return {'kind': 'found', 'marker': c['ref']}
    if fn == FN['dead']:
        return {'kind': 'dead' if v == 1 else 'alive', 'ref': c['ref']}
    return None


# ---------- the station's script ----------
def _script_key(pr, quest):
    return recordio.field(pr.records[quest], 'SCRI')


def script_vars(pr, quest, extra=None):
    """[(number, name, is integer)] of the station's script."""
    import api_scripts
    k = _script_key(pr, quest)
    return api_scripts.vars_of((extra or {}).get(k) or pr.records[k])


def gate_of(pr, quest, extra=None):
    """{'var', 'name', 'every'} when the station talks, else None. 'every' is read back from its talk lines."""
    var = next((n for n, name, _i in script_vars(pr, quest, extra) if name.lower() == SINCE.lower()), None)
    if var is None:
        return None
    for k, r in pr.records.items():
        if r['type'] == 'INFO' and recordio.field(r, 'QSTI') == quest:
            for c in qr.info_plain(r)['conditions']:
                if c['fn'] == FN['qvar'] and c['p2'] == var and c['op'] == '>=':
                    return {'var': var, 'name': SINCE, 'every': int(c['value'])}
    return None


def script_op(gd, pr, quest, more):
    """(key, record) of the station's script with variables `more` added (old ones keep their numbers)."""
    import api_scripts
    key = _script_key(pr, quest)
    rec = pr.records[key]
    have = script_vars(pr, quest)
    names = {n.lower() for _k, n, _i in have}
    add = [m for m in more if m.lower() not in names]
    if not add:
        return key, rec
    src = api_scripts.source_of(rec).rstrip('\n') + '\n' + ''.join('short %s\n' % m for m in add)
    edid = recordio.field(rec, 'EDID')
    _type, count = api_scripts.header_of(rec)
    c = scriptc.compile_script(src, scriptc.GameForms(gd), scriptc.SCRIPT_QUEST, old_vars=have, old_count=count)
    import schema
    new = {'type': 'SCPT', 'flags': rec.get('flags', 0), 'src': rec.get('src', ''),
           'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': edid}] + schema.decode_record('SCPT', c.subrecords(lambda _fid: 0))}
    return key, new


# ---------- talk lines ----------
def talk_source(quest_edid, heard=None):
    q = quest_edid
    out = 'set %s.%s to 0' % (q, SINCE)
    if heard:
        out += '\r\nset %s.%s to %s.%s + 1' % (q, heard, q, heard)
    return out


def talk_of(gd, pr, quest):
    """A station's talk lines: [{'key', 'text', 'facts', 'times', 'heard'}] in the order they were made."""
    out = []
    names = {n: name for n, name, _i in script_vars(pr, quest)}
    for k, r in sorted(pr.records.items()):
        if r['type'] != 'INFO' or recordio.field(r, 'QSTI') != quest:
            continue
        l = qr.info_plain(r)
        src = (l.get('begin') or {}).get('source', '')
        if not re.search(r'\.%s\s+to\s+0' % SINCE, src, re.I):
            continue
        times, heard, facts = 0, None, []
        for c in l['conditions']:
            f = fact_of(c)
            if f:
                facts.append(f)
            elif c['fn'] == FN['qvar'] and c['op'] == '<':
                times, heard = int(c['value']), names.get(c['p2'])
        zh = [x['notes'][3:] for x in l['responses'] if (x.get('notes') or '').startswith('zh:')]
        out.append({'key': k, 'text': ' '.join(x['text'] for x in l['responses']), 'facts': facts, 'times': times, 'heard': heard,
                    'responses': len(l['responses']), 'lang': 'zh' if zh else 'en', 'said': ' '.join(zh),
                    'gloss': l['responses'][0].get('edits', '') if zh else ''})
    return out


def _talk_plain(gd, quest, text, conds, lang='en', gloss=''):
    """The line's plain form. Mandarin (lang 'zh', text in pinyin): one response a sentence, shown as plain pinyin (the
    game's fonts have no tone marks), the pinyin with tone numbers kept in the response's notes (NAM2, 'zh:' first) for
    the voice, and the English beside it in its edits field (NAM3), which the game never shows."""
    import api_quests
    l = radio.line_plain(gd, quest, 0, '', '')
    base = l['responses'][0]
    if lang == 'zh':
        import g2pzh
        g2pzh.sounds(text)                      # (a word that isn't pinyin is refused here, before anything is made)
        parts = [p.strip() for p in re.findall(r'[^.!?]+[.!?]?', text) if p.strip()]
        l['responses'] = [dict(base, sound='', number=n + 1, text=g2pzh.shown(p), notes='zh:' + g2pzh.numbered(p),
                               edits=gloss if n == 0 else '') for n, p in enumerate(parts)]
    else:
        l['responses'] = [dict(base, sound='', text=r['text'], number=r['number']) for r in api_quests.split_responses(text)]
    l['conditions'] = conds
    return l


def add_talk(gd, pr, edit, key, text, facts=(), times=0, every=None, lang='en', gloss=''):
    """A talk line on a station (one Undo). The first one starts the station talking: its script gains iSince and every
    song line the gate."""
    import api_quests
    st = radio.station(gd, pr, key)
    text = re.sub(r'\s+', ' ', text or '').strip()
    if not text:
        raise radio.RadioProblem('Write what the station says.')
    if '{' in text or '}' in text:
        raise radio.RadioProblem('Braces are what a song line\'s words are kept in: leave them out of talk.')
    quest = st['quest']
    quest_edid = recordio.field(pr.records[quest], 'EDID')
    gate = gate_of(pr, quest)
    every = int(every or (gate or {}).get('every') or EVERY)
    if every < 1:
        raise radio.RadioProblem('Talk comes after at least one song.')
    have = [n for _k, n, _i in script_vars(pr, quest)]
    heard = None
    want = [SINCE]
    if times:
        k = 1
        while (HEARD % k).lower() in {h.lower() for h in have}:
            k += 1
        heard = HEARD % k
        want.append(heard)
    skey, srec = script_op(gd, pr, quest, want)
    extra = {skey: srec}
    var = {name.lower(): n for n, name, _i in script_vars(pr, quest, extra)}
    new_gate = {'var': var[SINCE.lower()], 'name': SINCE, 'every': every}
    ops = [{'op': 'record', 'key': skey, 'record': srec}] if srec is not pr.records[skey] else []
    if gate != new_gate:
        ops += radio._relined(gd, pr, quest, radio._depth(len(st['tracks'])), gate=new_gate, extra=extra)
        for t in talk_of(gd, pr, quest):          # (talk made before with another 'every')
            r = pr.records[t['key']]
            l = qr.info_plain(r)
            for c in l['conditions']:
                if c['fn'] == FN['qvar'] and c['op'] == '>=':
                    c['value'] = float(every)
            rec = qr.info_record(l)
            rec['topic'] = r.get('topic') or l['topic']
            ops.append({'op': 'record', 'key': t['key'], 'record': rec})
    conds = [_cond(FN['qvar'], every, '>=', quest, new_gate['var'])] + [fact_condition(f) for f in facts or ()]
    if heard:
        conds.append(_cond(FN['qvar'], int(times), '<', quest, var[heard.lower()]))
    try:
        plain = _talk_plain(gd, quest, text, conds, lang, gloss)
    except ValueError as e:
        raise radio.RadioProblem("That isn't pinyin FOLab can read: %s" % e)
    src = talk_source(quest_edid, heard)
    plain['begin'] = {'source': src, 'parts': api_quests.compile_parts(src, radio._forms(gd, pr, extra))}
    plain['end'] = qr.empty_script()
    rec = qr.info_record(plain)
    rec['topic'] = plain['topic']
    ops.append({'op': 'record_new', 'record': rec})
    out = edit('Talk on %s' % st['name'], ops)
    out['station'] = key
    return out


def remove_talk(gd, pr, edit, key, line):
    """Takes a talk line off; the last one takes the gate off the songs too (its variables stay in the script)."""
    st = radio.station(gd, pr, key)
    talk = talk_of(gd, pr, st['quest'])
    if line not in {t['key'] for t in talk}:
        raise radio.RadioProblem('That line isn\'t on the station any more.')
    ops = [{'op': 'record_revert', 'key': line}]
    if len(talk) == 1:
        ops += radio._relined(gd, pr, st['quest'], radio._depth(len(st['tracks'])), gate=None)
    out = edit('Take talk off %s' % st['name'], ops)
    out['station'] = key
    return out


def check(gd, pr, key):
    """What would leave the station quiet or odd, in plain words."""
    st = radio.station(gd, pr, key)
    talk = talk_of(gd, pr, st['quest'])
    out = []
    if talk and not any(not t['facts'] and not t['times'] for t in talk):
        out.append('Every talk line waits on something, or runs out: add one that can always be said (the station\'s name, '
                   'the time of day), or the station goes quiet when talk is due and there\'s no news.')
    if talk and len(st['tracks']) < 2:
        out.append('With one song the station plays it, talks, and plays it again.')
    return out


# ---------- voices ----------
def voice_type_of(gd, pr, station_key):
    rec = pr.records[station_key]
    vt = recordio.field(rec, 'VNAM')
    import api_voices
    return vt, api_voices.edid(gd, pr, vt) if vt else ''


def voice_paths(gd, pr, key, line):
    """[(response number, what is said, path without extension)] of a talk line (Mandarin: its pinyin with tones)."""
    import api_voices
    import voicegen
    st = radio.station(gd, pr, key)
    _vt, vt_edid = voice_type_of(gd, pr, key)
    q = recordio.field(pr.records[st['quest']], 'EDID')
    topic = api_voices.edid(gd, pr, radio.patterns(gd)['topic'])
    l = qr.info_plain(pr.records[line])
    local = api_voices.own_id(pr, line)
    return [(r['number'], r['notes'] if (r.get('notes') or '').startswith('zh:') else r['text'],
             voicegen.voice_path(pr.plugin, vt_edid, q, topic, local, r['number'])) for r in l['responses']]


def voice_talk(gd, pr, key, line, voice=None, engine=None):
    """Speaks a talk line into the mod's own files; returns [(path, seconds)]. voice: a Kokoro voice or blend; else the
    station's kept choice, else api_voices' default man's."""
    import api_voices
    import library
    import voicegen
    voices = api_voices.load(pr)
    c = dict(voices['npc'].get(key) or {})
    if voice:
        c['voice'] = voice
    c.setdefault('voice', api_voices.DEFAULT['male'])
    zh_voice = (voice if voice and voice[:3] in ('zf_', 'zm_') else None) or c.get('zh_voice') or ZH_DEFAULT
    if c['voice'][:3] in ('zf_', 'zm_'):        # (a Chinese voice given for the station: English lines keep the default)
        c['voice'] = api_voices.DEFAULT['male']
    c.setdefault('speed', api_voices.PACE)
    c.setdefault('pitch', 0.0)
    c.setdefault('lively', api_voices.LIVELY)
    engine = engine or api_voices.engine_of(voices)
    root = library.assets_dir(pr)
    out = []
    kept = voices['lines'].setdefault(line, {})
    for n, text, rel in voice_paths(gd, pr, key, line):
        base = os.path.join(root, rel)
        if text.startswith('zh:'):
            secs = voicegen.write_line(base, text[3:], zh_voice, float(c['speed']), lang='zh')
            kept[str(n)] = {'text': text, 'voice': zh_voice, 'speed': c['speed'], 'path': rel, 'mood': [0, 50], 'engine': 'kokoro', 'lang': 'zh'}
        else:
            secs = voicegen.write_line(base, text, c['voice'], float(c['speed']), float(c['pitch']), float(c['lively']), engine=engine)
            kept[str(n)] = {'text': text, 'voice': c['voice'], 'speed': c['speed'], 'pitch': c['pitch'], 'lively': c['lively'], 'path': rel,
                            'mood': [0, 50], 'engine': engine}
        out.append((rel, secs))
    api_voices.save(pr, voices)
    return out


def listing(gd, pr, key):
    st = radio.station(gd, pr, key)
    gate = gate_of(pr, st['quest'])
    talk = talk_of(gd, pr, st['quest'])
    for t in talk:
        t['voiced'] = all(os.path.isfile(os.path.join(__import__('library').assets_dir(pr), rel + '.ogg'))
                          for _n, _t, rel in voice_paths(gd, pr, key, t['key']))
    return {'every': (gate or {}).get('every'), 'talk': talk, 'warnings': check(gd, pr, key)}
