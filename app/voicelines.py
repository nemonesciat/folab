"""Voicing the lines a step adds (the story session, 25 Nov 2026: "make voicing part of each pick's own step, with its
check failing when any new line lacks .ogg/.lip"; "a crowd doesn't all share one").

Every line of the given quests is spoken by peopletalk.voice, the way Waikiki's people's lines were:
- api_voices with Chatterbox when it's there, else Kokoro;
- each speaker's own voice from voices.json; a speaker with none gets one of their own (api_voices.own_default of their
  record), so new people never share one;
- every voice-type folder a speaker may use (a template's lists included);
- a check's "[SUCCEEDED]" or "[FAILED]" stays on screen and isn't said (`spoken`).
`missing` lists every response still without its .ogg or .lip; a step's check fails on any.

    plan_for(gd, pr, quests)           [{'line', 'number', 'unit', 'keys'}] for every response of the quests' lines
    voice(gd, pr, quests, progress, zh, only)    {'voiced', 'copied', 'problems', 'missing', 'voices': {speaker: voice}}
"""
import re

import recordio

GETISID = 72
TAG = re.compile(r'^\s*\[[A-Z ]+\]\s*')        # ("[SUCCEEDED]", "[FAILED]": shown, as the game's checks show them, never said)


def spoken(text):
    """What is said of a line's words: its check tag left out."""
    return TAG.sub('', text or '')


def _quest_keys(pr, quests):
    return {k for k, r in pr.records.items() if r.get('type') == 'QUST' and recordio.field(r, 'EDID') in quests}


def plan_for(gd, pr, quests):
    import questrec as qr
    qkeys = _quest_keys(pr, quests)
    plan = []
    for k, rec in sorted(pr.records.items()):
        if rec.get('type') != 'INFO':
            continue
        l = qr.info_plain(rec)
        if l['quest'] not in qkeys:
            continue
        who = [c['p1'] for c in l['conditions'] if c['fn'] == GETISID and c['op'] == '=' and c['p1']]
        name = recordio.field(pr.records.get(who[0]) or {'subs': []}, 'FULL') if who else ''
        for r in l['responses']:
            plan.append({'line': k, 'number': r['number'], 'unit': name or (who[0] if who else k), 'keys': who})
    return plan


def _voice_zh(gd, pr, plan, zh):
    """Speaks the plan's Mandarin responses (their words in zh); returns the rest of the plan and what it spoke."""
    import os
    import api_voices as av
    import huangland
    import library
    import voicegen
    V = av.load(pr)
    root = library.assets_dir(pr)
    rest, done = [], []
    for p in plan:
        info = av.line_info(gd, pr, p['line'], V)
        r = next((x for x in info.get('responses', ()) if x['number'] == p['number']), None)
        if not r or r['text'] not in zh:
            rest.append(p)
            continue
        c = dict(info.get('choice') or {})
        if not str(c.get('voice', '')).startswith('z'):          # (no Mandarin voice chosen: one of his own, huangland's way)
            _vt, female = av.voice_type_of(gd, pr, info['who'])
            c = {'voice': huangland.zh_voice(info['who'], female, 'elder'), 'speed': huangland.ZH_PACE, 'pitch': 0.0}
        voicegen.write_line(os.path.join(root, r['path']), zh[r['text']], c['voice'], float(c.get('speed', huangland.ZH_PACE)),
                            float(c.get('pitch', 0.0)), lang='zh')
        V['lines'].setdefault(p['line'], {})[str(r['number'])] = {
            'text': r['text'], 'voice': c['voice'], 'speed': c.get('speed', huangland.ZH_PACE), 'pitch': c.get('pitch', 0.0),
            'lively': 1.0, 'path': r['path'], 'mood': av._mood_key(r), 'engine': 'kokoro', 'lang': 'zh', 'say': zh[r['text']]}
        done.append(p)
    av.save(pr, V)
    return rest, done


def voice(gd, pr, quests, progress=None, zh=None, only=None):
    """zh: {a response's shown words: the pinyin said} for lines spoken in Mandarin (huangland's way: Kokoro's Chinese
    voices, kept in voices.json with lang 'zh' and 'say'); every other line as peopletalk speaks it. only: these line keys
    of the quests and no others (a step that rewords a few lines of a quest already voiced)."""
    import api_voices as av
    import peopletalk
    whole = plan = [p for p in plan_for(gd, pr, quests) if only is None or p['line'] in only]
    in_zh = []
    if zh:
        plan, in_zh = _voice_zh(gd, pr, plan, zh)
    shown = av.line_info

    def said(*a, **k):                     # (the tag stays on screen; the voice says the rest)
        out = shown(*a, **k)
        for r in out.get('responses', ()):
            r['text'] = spoken(r['text'])
        return out
    av.line_info = said
    try:
        got = peopletalk.voice(gd, pr, plan, progress)
    finally:
        av.line_info = shown
    voices = av.load(pr)
    who = {}
    for p in whole:
        v = (voices.get('lines', {}).get(p['line']) or {}).get(str(p['number']))
        if v:
            who.setdefault(p['unit'], v['voice'])
    import voicevariety
    got['entries_fixed'] = voicevariety.fix_entries(gd, pr, quests)     # (kept as api_voices keeps them: not "old")
    got['missing'] = peopletalk.unvoiced(gd, pr, whole)      # (the Mandarin lines checked too)
    got['voiced'] = got.get('voiced', 0) + len(in_zh)
    got['in_mandarin'] = len(in_zh)
    got['lines'] = len({p['line'] for p in whole})
    got['responses'] = len(whole)
    got['voices'] = who
    got['engine'] = av.engine_of(voices)
    return got
