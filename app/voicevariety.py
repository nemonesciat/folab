"""A voice for everyone (the user, 25 Nov 2026: "there should be a good variety of generic voices in english and in
chinese, and then all unique/important npcs should get their own unique voices"; "Yes, vary them").

**The rule** (kept in voices.json as `rules`, so later steps follow it):
- Every named or quest person has a voice no one else has: a Kokoro voice or blend, with a pitch and pace of their own.
- Generic people (Shouwei, Nongmin, guards, pirates, locals) draw from pools of distinct voices: at least 8 English men,
  8 English women, 6 Mandarin men and 4 Mandarin women. They're spread so people standing together don't sound alike.
- A changed voice means every line of that person is spoken again.

**What this step does:**
- **Every Huang speaker** gets a voice of their own: a blend of Kokoro's Chinese voices (`ZH_MEN`, `ZH_WOMEN`: four
  each), a constant pitch shift (which keeps the tones: voicegen.write_line's pitch for Mandarin) and a pace (`zh_palette`).
  Their Mandarin lines (`lang` zh: the pinyin in `say`) and their English lines are spoken again.
- **Any two people of voices.json's `npc` choices with the same voice** (the six on one English blend) get distinct
  blends, and their lines are spoken again (Chatterbox when it's the engine).
- **Entries are written exactly as api_voices writes them** (`_mood_key`, the line's own text), so FOLab doesn't call
  them "old". `fix_entries` mends the ones voicelines wrote before (the Speech checks' 27).

    plan(gd, pr)          {'zh': {speaker: choice}, 'en': {speaker: choice}, 'lines': {speaker: [line keys]}, ...}
    run(gd, pr, P, progress)   speaks everything planned; {'spoken', 'missing', 'voices', ...}
"""
import itertools
import os

import recordio

ZH_MEN = ('zm_yunjian', 'zm_yunxi', 'zm_yunxia', 'zm_yunyang')
ZH_WOMEN = ('zf_xiaobei', 'zf_xiaoni', 'zf_xiaoxiao', 'zf_xiaoyi')
ZH_PITCH = (0.0, -1.5, 1.5, -3.0, 3.0, -0.75, 0.75, -2.25, 2.25)
ZH_PACE = (0.9, 0.84, 0.96, 0.87, 0.93)
EN_MEN = ('am_adam', 'am_echo', 'am_eric', 'am_fenrir', 'am_liam', 'am_michael', 'am_onyx', 'am_puck', 'bm_daniel', 'bm_fable',
          'bm_george', 'bm_lewis')
EN_WOMEN = ('af_alloy', 'af_aoede', 'af_bella', 'af_heart', 'af_jessica', 'af_kore', 'af_nicole', 'af_nova', 'af_river', 'af_sarah',
            'af_sky', 'bf_alice', 'bf_emma', 'bf_isabella', 'bf_lily')
RULES = ("Every named or quest person has a voice no one else has. Generic people draw from pools of distinct voices: at least 8 "
         "English men, 8 English women, 6 Mandarin men and 4 Mandarin women, spread so people standing together don't sound "
         "alike. A changed voice means every line of that person is spoken again. (The user, 25 Nov 2026.)")
POOL_LEAST = {'en men': 8, 'en women': 8, 'zh men': 6, 'zh women': 4}


def _timbres(names):
    """Every voice and every two-voice blend (65/35 both ways) of the names."""
    out = list(names)
    for a, b in itertools.combinations(names, 2):
        out += ['%s*0.65+%s*0.35' % (a, b), '%s*0.65+%s*0.35' % (b, a)]
    return out


def zh_palette(female):
    """Distinct Mandarin voices, the most different first: timbres crossed with pitch and pace."""
    tim = _timbres(ZH_WOMEN if female else ZH_MEN)
    out = []
    for n in range(len(tim) * len(ZH_PITCH)):
        t = tim[n % len(tim)]
        p = ZH_PITCH[(n // len(tim)) % len(ZH_PITCH)]
        out.append({'voice': t, 'speed': ZH_PACE[n % len(ZH_PACE)], 'pitch': p, 'lively': 1.0})
    return out


def en_palette(female):
    tim = _timbres(EN_WOMEN if female else EN_MEN)[len(EN_WOMEN if female else EN_MEN):]     # (blends: no one's plain voice)
    return [{'voice': t, 'speed': (0.86, 0.92, 0.98, 0.89, 0.95)[n % 5], 'pitch': (-1.0, 0.5, -2.0, 1.0, -0.5)[n % 5], 'lively': 1.2}
            for n, t in enumerate(tim)]


def _sig(c):
    return (c.get('voice'), round(float(c.get('speed', 1.0)), 2), round(float(c.get('pitch', 0.0)), 2))


def plan(gd, pr):
    import api_voices as av
    import questrec as qr
    V = av.load(pr)
    lines, zh_people = {}, set()
    for lk, resp in V['lines'].items():
        rec = pr.records.get(lk)
        if not rec or rec.get('type') != 'INFO':
            continue
        who = av.speaker_of(gd, pr, qr.info_plain(rec))
        if not who:
            continue
        lines.setdefault(who, []).append(lk)
        if any(e.get('lang') == 'zh' for e in resp.values()):
            zh_people.add(who)
    female = lambda k: bool(av._acbs(pr.records.get(k) or {'subs': []}, 'Flags') & 1) if k in pr.records else False
    taken = {_sig(c) for k, c in V['npc'].items() if k not in zh_people and c.get('voice')}
    zh = {}
    for sex in (False, True):
        pal = [c for c in zh_palette(sex) if _sig(c) not in taken]
        people = sorted(k for k in zh_people if female(k) == sex)
        if len(people) > len(pal):
            raise ValueError('more Huang %s than distinct Mandarin voices (%d > %d)' % ('women' if sex else 'men', len(people), len(pal)))
        # (spread: people in turn round the palette, so the next voice is always another timbre)
        for n, k in enumerate(people):
            zh[k] = dict(pal[n])
    for c in zh.values():
        taken.add(_sig(c))
    en = {}
    seen = {}
    for k, c in sorted(V['npc'].items()):
        if k in zh or not c.get('voice'):
            continue
        s = _sig(c)
        if c.get('voice') in seen and seen[c['voice']] != k:
            pal = [x for x in en_palette(female(k)) if _sig(x) not in taken and x['voice'] not in seen]
            en[k] = dict(pal[0])
            taken.add(_sig(pal[0]))
            seen[pal[0]['voice']] = k
        else:
            seen.setdefault(c['voice'], k)
    names = {k: recordio.field(pr.records.get(k) or {'subs': []}, 'FULL') for k in list(zh) + list(en)}
    return {'zh': zh, 'en': en, 'lines': {k: v for k, v in lines.items() if k in zh or k in en}, 'names': names,
            'responses': sum(len(V['lines'][lk]) for k in list(zh) + list(en) for lk in lines.get(k, ()))}


def run(gd, pr, P, progress=None):
    import api_voices as av
    import library
    import voicegen
    import voicelines
    import peopletalk
    import shutil
    V = av.load(pr)
    root = library.assets_dir(pr)
    engine = av.engine_of(V)
    spoken = 0
    folders = {}
    missing = []
    for who, c in list(P['zh'].items()) + list(P['en'].items()):
        V['npc'][who] = dict(c)
        for lk in P['lines'].get(who, ()):
            info = av.line_info(gd, pr, lk, V)
            for r in info.get('responses', ()):
                had = V['lines'].get(lk, {}).get(str(r['number'])) or {}
                base = os.path.join(root, had.get('path') or r['path'])
                if had.get('lang') == 'zh' and had.get('say'):
                    voicegen.write_line(base, had['say'], c['voice'], float(c['speed']), float(c['pitch']), lang='zh')
                    V['lines'][lk][str(r['number'])] = dict(had, voice=c['voice'], speed=c['speed'], pitch=c['pitch'], lively=1.0,
                                                           path=had.get('path') or r['path'], engine='kokoro')
                else:
                    text = voicelines.spoken(r['text'])
                    if engine == 'chatterbox':
                        voicegen.write_line(base, text, c['voice'], float(c['speed']), float(c['pitch']), float(c['lively']),
                                            engine='chatterbox', feeling=av.feeling_of(r['emotion'], r['strength']))
                    else:
                        t, up, tune = av.mood_of(r['emotion'], r['strength'])
                        voicegen.write_line(base, text, c['voice'], float(c['speed']) * t, float(c['pitch']) + up, float(c['lively']) * tune)
                    V['lines'].setdefault(lk, {})[str(r['number'])] = entry(r, c, engine)
                spoken += 1
                if not all(os.path.isfile(base + e) for e in ('.ogg', '.lip')):
                    missing.append(base)
                # (the same take into every other folder this speaker's voice types may play it from, as peopletalk did)
                parts = (had.get('path') or r['path']).split(os.sep)
                for vt, fem in sorted(folders.setdefault(who, peopletalk.folders(gd, pr, (who,))).items()):
                    if vt == parts[3] or fem != voicegen.is_female(c['voice']):
                        continue
                    other = os.path.join(root, *(parts[:3] + [vt] + parts[4:]))
                    if os.path.isfile(other + '.ogg') or os.path.isdir(os.path.dirname(other)):
                        os.makedirs(os.path.dirname(other), exist_ok=True)
                        for e in ('.ogg', '.lip'):
                            shutil.copyfile(base + e, other + e)
                if progress and spoken % 100 == 0:
                    progress('%d of %d spoken' % (spoken, P['responses']))
                    av.save(pr, V)
    V['rules'] = RULES
    av.save(pr, V)
    library.publish(pr)
    return {'spoken': spoken, 'missing': missing, 'people': len(P['zh']) + len(P['en'])}


def entry(r, c, engine):
    """A voiced response as api_voices.voice_line keeps it (so line_info calls it done)."""
    import api_voices as av
    return {'text': r['text'], 'voice': c['voice'], 'speed': c['speed'], 'pitch': c['pitch'], 'lively': c['lively'],
            'path': r['path'], 'mood': av._mood_key(r), 'engine': engine}


def fix_entries(gd, pr, quests):
    """Entries voicelines wrote with the spoken text (no check tag) and the mood as given, rewritten as api_voices keeps
    them; the sound files stay. Returns how many changed."""
    import api_voices as av
    V = av.load(pr)
    engine = av.engine_of(V)
    n = 0
    import voicelines
    for p in voicelines.plan_for(gd, pr, quests):
        info = av.line_info(gd, pr, p['line'], V)
        r = next((x for x in info.get('responses', ()) if x['number'] == p['number']), None)
        had = (V['lines'].get(p['line']) or {}).get(str(p['number']))
        if not r or not had or had.get('lang') == 'zh':
            continue
        new = entry(r, info['choice'], had.get('engine', engine))
        if new != {k: had.get(k) for k in new}:
            V['lines'][p['line']][str(p['number'])] = new
            n += 1
    av.save(pr, V)
    return n


def census(gd, pr):
    """{'named': (unique, all), 'pools': {pool: distinct voices}, 'shared': [voices shared by more than one person]}."""
    import api_voices as av
    V = av.load(pr)
    roles = {'Shouwei', 'Nongmin', 'Zhanglao', 'Court Guard', 'Court Retainer', 'Servant', 'Guest', 'Pirate', 'Waikiki Local',
             'Child', 'Catcher', 'Court Fighter'}
    by = {}
    for k, c in V['npc'].items():
        if c.get('voice'):
            by.setdefault(_sig(c), []).append(k)
    shared = [list(v) for v in by.values() if len(v) > 1]
    names = {k: recordio.field(pr.records.get(k) or {'subs': []}, 'FULL') for k in V['npc']}
    named = [k for k in V['npc'] if V['npc'][k].get('voice') and names[k] and names[k] not in roles]   # (no voice: a radio station's settings)
    unique_named = [k for k in named if len(by.get(_sig(V['npc'][k]), [])) == 1]
    import voicegen
    pools = {'zh men': set(), 'zh women': set(), 'en men': set(), 'en women': set()}
    for resp in V['lines'].values():              # (every voice a line is spoken in, generic people's own defaults too)
        for e in resp.values():
            if e.get('voice'):
                lang = 'zh' if e.get('lang') == 'zh' or e['voice'].startswith('z') else 'en'
                pools['%s %s' % (lang, 'women' if voicegen.is_female(e['voice']) else 'men')].add(_sig(e))
    return {'named': (len(unique_named), len(named)), 'pools': {k: len(v) for k, v in pools.items()},
            'shared': shared, 'short': {k: POOL_LEAST[k] - len(v) for k, v in pools.items() if len(v) < POOL_LEAST[k]}}
