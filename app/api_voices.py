"""Voiced lines in the dialogue editor: every /api/voice/ route (server.py hands them over).

A line of the mod's own is spoken by its speaker's voice (voicegen.py: Kokoro, then the .lip from the same timings) into
the mod's own files at the path the game looks for (voicegen.voice_path), one .ogg and .lip per response. Nothing in the
plugin changes: the game finds the files by the line's quest, topic, form ID and response number.

What's kept, in projects/<mod> voices/voices.json (a folder: every .json directly in projects/ is listed as a mod), not
in the mod's own file and not in Undo (these are choices about sound, not edits to the plugin):
    {"npc":  {"<NPC key>": {"voice": "am_onyx*0.7+am_michael*0.3", "speed": 1.0, "pitch": 0.0, "lively": 1.3}},
     "type": {"<voice type key>": {...}},
     "lines": {"<INFO key>": {"<response number>": {"text": ..., "voice": ..., "speed": ..., "pitch": ..., "path": ...}}}}
A character's own choice wins, then its voice type's, then one of their own (`own_default`: a blend from their key). A
voice is one of Kokoro's or a blend of two (voicegen.blend); `lively` is how far its tune goes (voicefx). Each
response's emotion (the menu beside its words, which also sets the face) nudges speed, pitch and tune (`MOODS`), more at
a higher strength. A line whose words, emotion or voice changed since it was voiced is out of date (`state`).

Kokoro's voices: English ones only here (American and British). The model is the user's own download (voicegen.find_model)."""
import json
import os

import library
import project
import questrec as qr
import recordio

VOICES = [  # (Kokoro's name, what the page calls it)
    ('am_michael', 'Michael (American man)'), ('am_adam', 'Adam (American man)'), ('am_echo', 'Echo (American man)'),
    ('am_eric', 'Eric (American man)'), ('am_fenrir', 'Fenrir (American man)'), ('am_liam', 'Liam (American man)'),
    ('am_onyx', 'Onyx (American man)'), ('am_puck', 'Puck (American man)'), ('am_santa', 'Santa (American man)'),
    ('bm_george', 'George (British man)'), ('bm_daniel', 'Daniel (British man)'), ('bm_fable', 'Fable (British man)'),
    ('bm_lewis', 'Lewis (British man)'),
    ('af_heart', 'Heart (American woman)'), ('af_bella', 'Bella (American woman)'), ('af_alloy', 'Alloy (American woman)'),
    ('af_aoede', 'Aoede (American woman)'), ('af_jessica', 'Jessica (American woman)'), ('af_kore', 'Kore (American woman)'),
    ('af_nicole', 'Nicole (American woman)'), ('af_nova', 'Nova (American woman)'), ('af_river', 'River (American woman)'),
    ('af_sarah', 'Sarah (American woman)'), ('af_sky', 'Sky (American woman)'),
    ('bf_emma', 'Emma (British woman)'), ('bf_alice', 'Alice (British woman)'), ('bf_isabella', 'Isabella (British woman)'),
    ('bf_lily', 'Lily (British woman)'),
]
DEFAULT = {'male': 'am_michael', 'female': 'af_heart'}
# A character nobody chose a voice for gets one of their own (`own_default`): a blend of two of Kokoro's voices of their
# sex and a pitch a little off, both from their key, so two characters left alone don't sound alike.
BLEND_FROM = {'male': ['am_michael', 'am_adam', 'am_echo', 'am_eric', 'am_fenrir', 'am_liam', 'am_onyx', 'am_puck',
                       'bm_george', 'bm_daniel', 'bm_fable', 'bm_lewis'],
              'female': ['af_heart', 'af_bella', 'af_aoede', 'af_jessica', 'af_kore', 'af_nicole', 'af_nova', 'af_river',
                         'af_sarah', 'af_sky', 'bf_emma', 'bf_alice', 'bf_isabella', 'bf_lily']}
LIVELY = 1.3            # Kokoro speaks evenly: a tune this much wider by default (voicefx.contour)
PACE = 0.9              # Kokoro's own pace is hurried for the game's people: a little slower by default
# A response's emotion (TRDT, the face the game shows) nudges its voice too: (speed times, pitch in semitones, tune
# times) at full strength (100), scaled by the response's strength. Kokoro has no emotion of its own: this is the nudge
# it can take. By the game's emotion numbers: 0 Neutral, 1 Anger, 2 Disgust, 3 Fear, 4 Sad, 5 Happy, 6 Surprise, 7 Pained.
MOODS = {1: (1.12, -0.5, 1.35), 2: (0.92, -1.0, 1.1), 3: (1.15, 1.5, 1.3), 4: (0.85, -1.5, 0.65), 5: (1.08, 1.0, 1.3),
         6: (1.05, 2.0, 1.45), 7: (0.88, -1.0, 0.8)}


def mood_of(emotion, strength):
    """(speed times, pitch semitones, tune times) a response's emotion adds; (1, 0, 1) for Neutral."""
    m = MOODS.get(int(emotion or 0))
    if not m:
        return 1.0, 0.0, 1.0
    f = max(0, min(100, int(strength if strength is not None else 50))) / 100.0
    return 1.0 + (m[0] - 1.0) * f, m[1] * f, 1.0 + (m[2] - 1.0) * f


def own_default(who, female):
    """A voice of their own for a character nobody chose one for: {'voice': blend, 'pitch': ...}, from their key."""
    import zlib
    pool = BLEND_FROM['female' if female else 'male']
    h = zlib.crc32((who or '').encode('utf-8'))
    a = pool[h % len(pool)]
    b = pool[(h // len(pool)) % (len(pool) - 1)]
    b = b if b != a else pool[-1]
    w = 0.55 + ((h >> 12) % 30) / 100.0
    return {'voice': '%s*%.2f+%s*%.2f' % (a, w, b, 1 - w), 'pitch': ((h >> 20) % 13 - 6) / 6.0}


def valid_voice(voice):
    import voicegen
    names = dict(VOICES)
    parts = voicegen.blend(voice)
    return bool(parts) and all(n in names for n, _ in parts)


def _mood_key(r):
    e = int(r.get('emotion') or 0)
    return [e, int(r.get('strength', 50)) if e else 0]
FEMALE = 0x1            # NPC_ ACBS flags
USE_TRAITS = 0x1        # NPC_ ACBS template flags: the template's traits, its voice among them


# ---------- what's kept ----------

def _folder(pr):
    return os.path.join(project.PROJECTS_DIR, pr.name + ' voices')


def load(pr):
    try:
        with open(os.path.join(_folder(pr), 'voices.json'), encoding='utf-8') as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    for k in ('npc', 'type', 'lines'):
        d.setdefault(k, {})
    return d


def save(pr, d):
    os.makedirs(_folder(pr), exist_ok=True)
    path = os.path.join(_folder(pr), 'voices.json')
    with open(path + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(d, f, indent=1)
    os.replace(path + '.tmp', path)


# ---------- a line's speaker, voice type and file names ----------

def _record(gd, pr, key):
    if pr and key in pr.records:
        return pr.records[key]
    if key.startswith('+'):
        return None
    try:
        return recordio.load(gd, gd.from_key(key))
    except Exception:
        return None


def _acbs(rec, name):
    s = next((s for s in rec['subs'] if s['tag'] == 'ACBS'), None)
    f = next((f for f in (s or {}).get('fields', []) if f.get('name') == name), None)
    return int(f['value']) if f else 0


def voice_type_of(gd, pr, who, depth=0):
    """(voice type key, female) for an NPC or creature key, following a template that gives its traits."""
    rec = _record(gd, pr, who)
    if not rec or depth > 4:
        return None, False
    female = bool(_acbs(rec, 'Flags') & FEMALE)
    tplt = recordio.field(rec, 'TPLT')
    if tplt and _acbs(rec, 'Template flags') & USE_TRAITS:
        vt, fem = voice_type_of(gd, pr, tplt, depth + 1)
        if vt:
            return vt, fem
    return recordio.field(rec, 'VTCK') or None, female


def speaker_of(gd, pr, plain):
    """The character a line is said by: its speaker, else a 'GetIsID <who> == 1' condition."""
    if plain.get('speaker'):
        return plain['speaker']
    for c in plain['conditions']:
        if c.get('op') == '=' and c.get('value') == 1 and isinstance(c.get('p1'), str) and c['fn'] == 72:
            return c['p1']
    return None


def own_id(pr, key):
    """The INFO's form ID as the mod's plugin writes it, without the load-order byte; None for a line of another file."""
    if key.startswith('+'):
        return int(key[1:], 16)
    plugin, _, hexid = key.rpartition(':')
    if plugin.lower() == pr.plugin.lower():
        return int(hexid, 16)
    return None


def edid(gd, pr, key):
    rec = _record(gd, pr, key)
    return recordio.field(rec, 'EDID') if rec else ''


def line_info(gd, pr, key, voices=None):
    """Everything about voicing one line: who says it, the voice to use, each response's file and whether it's done.
    'problem' says why it can't be voiced."""
    rec = _record(gd, pr, key)
    if not rec or rec.get('type') != 'INFO':
        return {'key': key, 'problem': 'not a line'}
    plain = qr.info_plain(json.loads(json.dumps(rec)))
    voices = voices if voices is not None else load(pr)
    out = {'key': key, 'responses': [], 'problem': None}
    local = own_id(pr, key)
    topic = plain.get('topic') or qr.line_topic(gd, pr, key, rec)
    who = speaker_of(gd, pr, plain)
    vt, female = voice_type_of(gd, pr, who) if who else (None, False)
    out.update({'who': who, 'voice_type': vt, 'voice_type_edid': edid(gd, pr, vt) if vt else ''})
    if local is None:
        out['problem'] = 'Only your own lines can be voiced: this one belongs to %s.' % key.rpartition(':')[0]
    elif not plain.get('quest') or not topic:
        out['problem'] = 'The line needs a quest and a topic first.'
    elif not who:
        out['problem'] = 'Nobody in particular says it: give it a speaker (Who says it) first.'
    elif not vt:
        out['problem'] = 'Its speaker has no voice type: give them one on the Characters page.'
    out['choice'] = choice_for(voices, who, vt, female)
    out['engine'] = engine_of(voices)
    if out['problem']:
        return out
    q, t = edid(gd, pr, plain['quest']), edid(gd, pr, topic)
    import voicegen
    done = voices['lines'].get(key, {})
    for r in plain['responses']:
        rel = voicegen.voice_path(pr.plugin, out['voice_type_edid'], q, t, local, r['number'])
        had = done.get(str(r['number']))
        there = os.path.isfile(os.path.join(library.assets_dir(pr), rel + '.ogg'))
        mood = _mood_key(r)
        c = out['choice']
        changed = had and (had.get('text') != r['text'] or had.get('path') != rel or had.get('mood', [0, 0]) != mood
                           or any(had.get(f) != c[f] for f in ('voice', 'speed', 'pitch', 'lively'))
                           or had.get('engine', 'kokoro') != out['engine'])
        state = 'none' if not there or not had else ('old' if changed else 'done')
        out['responses'].append({'number': r['number'], 'text': r['text'], 'path': rel, 'state': state,
                                 'emotion': mood[0], 'strength': int(r.get('strength', 50))})
    return out


def choice_for(voices, who, vt, female):
    c = dict(voices['npc'].get(who or '') or voices['type'].get(vt or '') or {})
    if 'voice' not in c:
        c.update(own_default(who, female) if who else {'voice': DEFAULT['female' if female else 'male']})
    c.setdefault('speed', PACE)
    c.setdefault('pitch', 0.0)
    c.setdefault('lively', LIVELY)
    c['own'] = 'npc' if who in voices['npc'] else 'type' if vt in voices['type'] else None
    return c


# ---------- doing it ----------

def status():
    """Whether this FOLab can speak: the packages, and the user's downloaded model; and whether Chatterbox is there."""
    try:
        import voicegen
        import onnxruntime  # noqa: F401
        import numpy  # noqa: F401
        import soundfile  # noqa: F401
    except Exception as e:      # noqa: BLE001 - reported to the page
        return {'engine': False, 'model': False, 'why': 'This FOLab has no voice maker (%s).' % e}
    have = voicegen.find_model(copy=False)
    return {'engine': True, 'model': bool(have), 'files': [voicegen.MODEL, voicegen.VOICES],
            'why': None if have else voicegen.MISSING, 'chatterbox': voicegen.chatterbox_folder()}


# Chatterbox's feeling dial (exaggeration) by the game's emotion at full strength; CALM's at Neutral. It acts the
# emotion out, so its lines take only this from the mood (not speed, pitch or tune, which would change the clip it copies).
FEELING = {1: 0.8, 2: 0.6, 3: 0.75, 4: 0.6, 5: 0.7, 6: 0.75, 7: 0.65}


def feeling_of(emotion, strength):
    import voicegen
    calm = voicegen.CALM['exaggeration']
    m = FEELING.get(int(emotion or 0))
    if not m:
        return calm
    f = max(0, min(100, int(strength if strength is not None else 50))) / 100.0
    return calm + (m - calm) * f


def engine_of(voices):
    """The voice maker a mod's lines use: its own choice ('engine' in voices.json), else Chatterbox when it's there."""
    import voicegen
    want = voices.get('engine')
    if want == 'kokoro':
        return 'kokoro'
    return 'chatterbox' if voicegen.chatterbox_folder() else 'kokoro'


def voice_line(gd, pr, key, voices=None):
    """Voices every response of a line; returns the line's info afterwards."""
    import voicegen
    voices = voices if voices is not None else load(pr)
    info = line_info(gd, pr, key, voices)
    if info['problem']:
        raise ValueError(info['problem'])
    c = info['choice']
    root = library.assets_dir(pr)
    kept = voices['lines'].setdefault(key, {})
    engine = engine_of(voices)
    for r in info['responses']:
        if not r['text'].strip():
            continue
        base = os.path.join(root, r['path'])
        if engine == 'chatterbox':
            voicegen.write_line(base, r['text'], c['voice'], float(c['speed']), float(c['pitch']), float(c['lively']),
                                engine='chatterbox', feeling=feeling_of(r['emotion'], r['strength']))
        else:
            times, up, tune = mood_of(r['emotion'], r['strength'])
            voicegen.write_line(base, r['text'], c['voice'], float(c['speed']) * times,
                                float(c['pitch']) + up, float(c['lively']) * tune)
        kept[str(r['number'])] = {'text': r['text'], 'voice': c['voice'], 'speed': c['speed'], 'pitch': c['pitch'],
                                  'lively': c['lively'], 'path': r['path'], 'mood': _mood_key(r), 'engine': engine}
    save(pr, voices)
    library.publish(pr)
    return line_info(gd, pr, key, voices)


def own_lines_of(gd, pr, who):
    """The mod's own lines a character says (the ones that can be voiced)."""
    out = []
    for k, rec in pr.records.items():
        if rec.get('type') != 'INFO' or own_id(pr, k) is None:
            continue
        if speaker_of(gd, pr, qr.info_plain(json.loads(json.dumps(rec)))) == who:
            out.append(k)
    return sorted(out)


def voice_character(gd, pr, who, only_missing=False):
    voices = load(pr)
    done, problems = 0, []
    for k in own_lines_of(gd, pr, who):
        info = line_info(gd, pr, k, voices)
        if info['problem']:
            problems.append(info['problem'])
            continue
        if only_missing and all(r['state'] == 'done' for r in info['responses']):
            continue
        voice_line(gd, pr, k, voices)
        done += 1
    return {'voiced': done, 'problems': sorted(set(problems)), 'lines': len(own_lines_of(gd, pr, who))}


def set_choice(gd, pr, body):
    """A character's (or voice type's) voice, speed and pitch; voice None takes the character's own choice away."""
    voices = load(pr)
    where = 'type' if body.get('for') == 'type' else 'npc'
    k = body['key']
    if body.get('voice') is None:
        voices[where].pop(k, None)
    else:
        if not valid_voice(body['voice']):
            raise ValueError('no voice called %s' % body['voice'])
        voices[where][k] = {'voice': body['voice'], 'speed': max(0.5, min(2.0, float(body.get('speed', PACE)))),
                            'pitch': max(-6.0, min(6.0, float(body.get('pitch', 0.0)))),
                            'lively': max(0.5, min(2.0, float(body.get('lively', LIVELY))))}
    save(pr, voices)
    return {'ok': True}


def sample(body):
    """A few words in a voice, to hear before choosing (an .ogg, not kept)."""
    import io
    import soundfile
    import voicefx
    import voicegen
    voice = body.get('voice', 'am_michael')
    if not valid_voice(voice):
        raise ValueError('no voice called %s' % voice)
    say = voicegen.speak_chatterbox if body.get('engine') == 'chatterbox' else voicegen.speak
    audio, _timed = say(body.get('text') or 'Aloha. This is how I sound. Do I sound right to you?', voice,
                        float(body.get('speed', PACE)), float(body.get('pitch', 0.0)), float(body.get('lively', LIVELY)))
    audio = voicefx.master(audio, voicegen.is_female(voice))
    buf = io.BytesIO()
    soundfile.write(buf, audio, voicegen.RATE, format='OGG', subtype='VORBIS')
    return buf.getvalue(), 'audio/ogg'


# ---------- routes ----------

def get(path, q, gd, pr):
    if path == '/api/voice/status':
        return dict(status(), voices=VOICES)
    if not pr:
        raise ValueError('Start a mod first (My mod).')
    if path == '/api/voice/line':
        return line_info(gd, pr, q['key'])
    if path == '/api/voice/file':
        info = line_info(gd, pr, q['key'])
        r = next(r for r in info['responses'] if str(r['number']) == str(q.get('n', 1)))
        with open(os.path.join(library.assets_dir(pr), r['path'] + '.ogg'), 'rb') as f:
            return f.read(), 'audio/ogg'
    if path == '/api/voice/character':
        lines = [line_info(gd, pr, k) for k in own_lines_of(gd, pr, q['who'])]
        vt, female = voice_type_of(gd, pr, q['who'])
        return {'lines': lines, 'choice': choice_for(load(pr), q['who'], vt, female), 'voice_type': vt}
    return None


def post(path, body, gd, pr):
    if path == '/api/voice/sample':
        return sample(body)
    if not pr:
        raise ValueError('Start a mod first (My mod).')
    if path == '/api/voice/line':
        return voice_line(gd, pr, body['key'])
    if path == '/api/voice/engine':          # which voice maker this mod's lines use
        if body.get('engine') not in ('kokoro', 'chatterbox'):
            raise ValueError('no voice maker called %s' % body.get('engine'))
        voices = load(pr)
        voices['engine'] = body['engine']
        save(pr, voices)
        return {'ok': True, 'engine': engine_of(voices)}
    if path == '/api/voice/character':
        return voice_character(gd, pr, body['who'], bool(body.get('only_missing')))
    if path == '/api/voice/choice':
        return set_choice(gd, pr, body)
    return None
