"""The Huang's numbers, and the freighter hold's watch (docs/waikiki-speech-science.md section J, system 11; the user,
25 Nov 2026: option (a), "if you think you can make something cool").

- **The watchman** (`WATCH`): a Shouwei of the mod's own, with a face no one else has and a Mandarin voice of his own, in
  the freighter's hold by the house door. Twice a day he goes to eat at the freighter house's stove (`MEALS`, his
  packages' hours: noon to one, six to seven), then back.
- **Caught in the hold:** while he's there and sees you in the hold without the elder's key, he says so ("Zei! Chuqu!"),
  and it costs 1 infamy with the Huang (AddReputation, as their crimes do) and `CAUGHT_FACE` of their face
  (repstanding.py). Once a visit.
- **The way in without the elder:** the deck hatch's lock is now `HATCH_LOCK` (Hard: a lockpick at 75, or the key); its
  side in the hold opens without one, so nobody is shut in. The house door stays the elder's key only.
- **The numbers** on Haixin Dongtai (the Huang's station): a short reed tune (`signal`), then a woman reads cipher groups
  in Mandarin, twice, as numbers stations do. Their station's other talk is unchanged; this is one more talk line.
- **Decoding:** the Radar Dome's terminal gets "Analyse the Haixin Dongtai numbers". At Science `DECODE` it adds a note
  (`NOTE`) of what the groups say, in plain English: the hold watch's meal hours (true: his packages), and two other true
  Huang things (the road patrol from the Makapuu gate to the Border Post; their silk going to Waikiki through Linda
  Moreno). Under it, a message that the key escapes you.
- **[proposal]** The meal hours, the hatch's lock, the watchman, the cipher's words and the Radar Dome as where it's
  broken are this step's own; what the note says is true in the game.

    plan(gd, pr)       (rows, skipped)
    apply(pr, gd, P)   one Undo (records and refs, then the lines compiled against them)
    voice(gd, pr)      the bulletin's voice file: the tune, the groups read twice, on air; its .lip
"""
import json
import math

import recordio

LABEL = "The Huang's numbers, and the hold's watch"
QUEST, SCRIPT = 'FOLabHoldWatch', 'FOLabHoldWatchScript'
VOICE = [QUEST]
WATCH, WATCH_NAME = 'FOLabShouweiHoldWatch', 'Shouwei'
HOLD, HOUSE, STOVE = 'FOLabFreighterHold', 'FOLabFreighterHouse', 'CookStove'
HATCH_CELL_DOOR = 'HatchDoor'
MEALS = [(12, 1), (18, 1)]                       # (hour, hours): the gap in the watch
MEAL_FROM = 'DefaultSandboxEditorLocation256'
STAY = 'DefaultStayAtEditorLocation'
HATCH_LOCK = 75
CAUGHT_FACE = 10
DECODE = 70
NEAR_DOOR = (180.0, 450.0)
STATION = 'Haixin Dongtai'
READER, PACE = 'zf_xiaobei', 0.82
SAY = {   # key: (English, pinyin with tones)
    'caught': ("Thief! Out of the hold!", "Zéi! Chūqù!"),
    'ask': ("The hold. Nobody goes in without the elders' word.", "Huòcāng. Méiyǒu zhǎnglǎo de huà, shéi yě bù néng jìn."),
}
ASK_TOPIC = "What do you guard?"
BULLETIN = ("Hǎixīn sān hào. Hǎixīn sān hào. Zhùyì. Yāo èr líng líng, yāo sān líng líng. Yāo bā líng líng, yāo jiǔ líng líng. "
            "Wǔ qī sān, èr liù yāo. Sì sì bā, líng jiǔ èr. Chóngfù. Yāo èr líng líng, yāo sān líng líng. Yāo bā líng líng, "
            "yāo jiǔ líng líng. Wǔ qī sān, èr liù yāo. Sì sì bā, líng jiǔ èr. Wánbì.")
BULLETIN_GLOSS = "Haixin number three. Attention. (cipher groups, read twice) End."
NOTE = ('FOLabHaixinNumbersNote', 'Haixin Dongtai numbers, decoded')
NOTE_TEXT = """HAIXIN DONGTAI, NUMBERS, "HAIXIN NUMBER THREE" (worked out at the Waialae Nui radar station)

1200 1300 / 1800 1900: the freighter's hold. The watch goes to eat, noon to one and six to seven. The deck hatch has a lock and no guard while he eats.
573 261: the road watch walks from the Makapuu gate to the Border Post and back.
448 092: the silk goes to Waikiki through Linda Moreno, the trader."""
DECODED = "The groups are hours and a short codebook. You write out what they say. (Added to your notes.)"
NO_KEY = "The groups repeat, but you can't find their key. (Science %d)" % DECODE
TERMINAL, ITEM = 'FOLabRadarDomeTerminal', 'Analyse the Haixin Dongtai numbers'
MSG_DECODED, MSG_NOKEY = 'FOLabHaixinDecodedMsg', 'FOLabHaixinNoKeyMsg'
GETISID = 72
ZH = {}


def _key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and recordio.field(r, 'EDID') == edid), None)


def _base_edid(gd, pr, b):
    if b in pr.records:
        return recordio.field(pr.records[b], 'EDID') or ''
    try:
        return gd.edid(gd.from_key(b)) or ''
    except (KeyError, ValueError, IndexError):
        return ''


def shown(k):
    import huangland
    english, pinyin = SAY[k]
    return huangland.shown(english, pinyin)


def _zh():
    for k in SAY:
        ZH[shown(k)] = SAY[k][1]


def plan(gd, pr):
    import radio
    rows, skipped = [], []
    if _key(pr, QUEST, 'QUST'):
        return rows, [(QUEST, 'already in the mod (Undo first)')]
    hold, house = _key(pr, HOLD, 'CELL'), _key(pr, HOUSE, 'CELL')
    if not hold or not house:
        return rows, [('freighter', 'no %s or %s' % (HOLD, HOUSE))]
    refs = (pr.cells.get(hold) or {}).get('refs') or {}
    doors = {rk: r for rk, r in refs.items() if r.get('tel') and not r.get('removed')}
    house_refs = (pr.cells.get(house) or {}).get('refs') or {}
    to_house = next((rk for rk, r in doors.items() if r['tel'].get('door') in house_refs), None)
    to_deck = next((rk for rk, r in doors.items() if rk != to_house), None)
    hatch = None
    if to_deck:
        hatch_key = doors[to_deck]['tel'].get('door')
        hatch = next(((ck, hatch_key) for ck, c in pr.cells.items() if hatch_key in (c.get('refs') or {})), None)
    stove = next((rk for rk, r in house_refs.items() if _base_edid(gd, pr, r.get('base')) == STOVE and not r.get('removed')), None)
    missing = [w for w, v in (('house door', to_house), ('deck door', to_deck), ('hatch', hatch), ('stove', stove)) if not v]
    if missing:
        return rows, [('freighter', 'missing: %s' % ', '.join(missing))]
    spot = _spot(gd, pr, hold, refs[to_house]['p'], [doors[to_deck]['p']])
    if not spot:
        return rows, [('watch', 'no spot by the house door on the hold\'s navmesh')]
    st = next((s for s in radio.stations(gd, pr) if s.get('name') == STATION), None)
    if not st:
        skipped.append(('numbers', 'no %s station' % STATION))
    if not _key(pr, TERMINAL, 'TERM'):
        skipped.append(('decoding', '%s not in the mod' % TERMINAL))
    rows.append({'hold': hold, 'house': house, 'to_house': to_house, 'to_deck': to_deck, 'hatch': hatch, 'stove': stove,
                 'spot': spot, 'station': st['key'] if st else None, 'terminal': _key(pr, TERMINAL, 'TERM')})
    return rows, skipped


def _spot(gd, pr, ck, door, avoid):
    import robots as R
    tris = R._tris(gd, pr, ck)
    _doors, actors, seats = R._things(gd, pr, ck)
    best = None
    for p in tris:
        d = math.dist(p[:2], door[:2])
        if not NEAR_DOOR[0] <= d <= NEAR_DOOR[1]:
            continue
        if min((math.dist(p[:2], q[:2]) for q in actors + seats), default=1e9) < 120:
            continue
        score = abs(d - 260)
        if best is None or score < best[0]:
            best = (score, p)
    if not best:
        return None
    p = best[1]
    far = avoid[0] if avoid else door
    return (round(p[0], 1), round(p[1], 1), round(p[2] + 4, 1), round(math.atan2(far[0] - p[0], far[1] - p[1]), 4))


SPARE = ('Man', 'Woman', 'Boomer', 'Local', 'Squatter', 'Traveling Merchant')


def _spare_face(gd, used):
    """(face, sex) of a game NPC_ of an Asian race, no template, named only by what it is (`SPARE`), that nobody in the mod
    has; men first."""
    import factionfolk as ff
    races = {f: gd.edid(f) for f, (_i, r) in gd.forms.items() if r.tag == 'RACE'}
    got = {'M': [], 'F': []}
    for f, (_i, r) in sorted(gd.forms.items()):
        if r.tag != 'NPC_' or (f >> 24) != 0 or gd.key(f) in used:
            continue
        rec = recordio.load(gd, f)
        if recordio.field(rec, 'TPLT') or recordio.field(rec, 'FULL') not in SPARE:
            continue
        rn = recordio.field(rec, 'RNAM')
        if races.get(gd.from_key(rn)) not in ('Asian', 'AsianOld') if rn else True:
            continue
        got['F' if ff._num(rec, 'ACBS', 'Flags') & 0x1 else 'M'].append(f)
    for sex in ('M', 'F'):
        if got[sex]:
            return got[sex][0], sex
    return None, 'M'


def _cond(fn, op, value, p1=0, p2=0, run=0):
    return {'or': False, 'use_target': False, 'op': op, 'fn': fn, 'p1': p1, 'p2': p2, 'run': run, 'ref': '', 'value': float(value)}


def watch_source(topic_edid, hold_edid=HOLD):
    import repstanding
    return '\n'.join([
        'scn %s' % SCRIPT, '', 'short warned', '', 'Begin GameMode',
        '\tif GetDead', '\t\treturn', '\tendif',
        '\tif player.GetInCell %s' % hold_edid,
        '\t\tif warned == 0 && GetDistance player < 1500 && GetLOS player && player.GetItemCount FOLabFreighterHoldKey == 0',
        '\t\t\tset warned to 1', '\t\t\tAddReputation FOLabRepHuang 0 1', '\t\t\t' + repstanding.bump('huang', -CAUGHT_FACE),
        '\t\t\tStartConversation player %s' % topic_edid, '\t\tendif',
        '\telse', '\t\tset warned to 0', '\tendif', 'End', ''])


def ops(gd, pr, P=None):
    import api_characters as ac
    import api_quests as aq
    import api_scripts
    import factionfolk as ff
    import huanginside
    import huangland
    import newgame
    import questrec as qr
    import radiotalk
    import terminals
    from activity import _new_key
    _zh()
    rows, skipped = P or plan(gd, pr)
    if not rows:
        raise ValueError('nothing to do: %s' % (skipped,))
    r = rows[0]
    out, extra, rep = [], {}, {'made': [], 'skipped': skipped}

    def record(edid, rec, key=None):
        k = key or _new_key(pr)
        extra[k] = rec
        out.append({'op': 'record', 'key': k, 'record': rec})
        rep['made'].append(edid)
        return k
    # the quest and its topics
    qk, qsk = _new_key(pr), _new_key(pr)
    quest = qr.quest_record({'edid': QUEST, 'script': '', 'name': '', 'flags': {'start_enabled': True}, 'priority': 50,
                             'delay': 5.0, 'stages': [], 'objectives': []})
    caught_t = record('FOLabHoldWatchCaught', qr.topic_record({'edid': 'FOLabHoldWatchCaught', 'name': ' ', 'priority': 50.0, 'kind': 0,
                                                                'flags': {}, 'quests': [{'quest': qk, 'links': []}]}))
    ask_t = record('FOLabHoldWatchAsk', qr.topic_record({'edid': 'FOLabHoldWatchAsk', 'name': ASK_TOPIC, 'priority': 50.0, 'kind': 0,
                                                         'flags': {'top_level': True}, 'quests': [{'quest': qk, 'links': []}]}))
    record(QUEST, quest, qk)
    # his meals: two packages near the house's stove, at their hours
    meals = []
    for hour, hours in MEALS:
        meals.append(record('FOLabHoldWatchMeal%02d' % hour, huanginside._pack(gd, MEAL_FROM, 'FOLabHoldWatchMeal%02d' % hour, hour, hours,
                                                                               r['stove'], 256)))
    out.append({'op': 'persist', 'cell': r['house'], 'ref': r['stove']})
    # the watchman: a face no one has, the Shouwei's dress and arms, his meals first, then staying put
    pool, used = huangland.face_pool(gd, pr)
    face, sex = None, 'M'
    for want in (('Asian', 'M'), ('Asian', 'F'), ('AsianOld', 'M'), ('AsianOld', 'F')):     # (Shouwei are men and women)
        face = next((f for f in pool.get(want, []) if gd.key(f) not in used), None)
        if face is not None:
            sex = want[1]
            break
    if face is None:                  # (the pool spent: the game's other Asian people called only by what they are)
        face, sex = _spare_face(gd, used)
    if face is None:
        raise ValueError('no Asian face left that nobody in the mod has')
    g = ff.GROUPS['huang_guard']
    items = [(ff._item(gd, pr, e), 1) for e in g['wear'][sex]]
    arm = ff._mod_key(pr, g['arms'][0], 'WEAP')
    if arm:
        items.append((arm, 1))
    fac = ff._mod_key(pr, ff.FACTIONS['huang'][0], 'FACT')
    npc = ff.person(gd, pr, face, WATCH, WATCH_NAME, dict(g, package=STAY), items, [], fac)
    first = next(i for i, s in enumerate(npc['subs']) if s['tag'] == 'PKID')
    npc['subs'][first:first] = [{'tag': 'PKID', 'label': 'AI package', 'kind': 'F', 'value': k} for k in meals]
    nk = _new_key(pr)
    npc['subs'] = [s for s in npc['subs'] if s['tag'] != 'SCRI']
    ac.insert(npc, {'tag': 'SCRI', 'label': 'Script', 'kind': 'F', 'value': qsk})
    extra[nk] = npc
    sc = api_scripts.scripts()
    c = sc.compile(watch_source('FOLabHoldWatchCaught', _base_edid(gd, pr, r['hold'])), qsk, 'object', extra)
    if not hasattr(c, 'subrecords'):
        raise ValueError('the watch script: %s' % (c,))
    record(SCRIPT, sc._record_of(c, SCRIPT), qsk)
    record(WATCH, npc, nk)
    rep['face'] = gd.key(face)
    rep['sex'] = sex
    x, y, z, rz = r['spot']
    out.append({'op': 'place', 'cell': r['hold'], 'key': _new_key(pr),
                'ref': {'base': nk, 'p': [x, y, z, 0.0, 0.0, rz], 's': 1.0, 'persistent': True}})
    # the hatch: picked at Hard (or the key); its side in the hold opens freely
    hck, hrk = r['hatch']
    props = json.loads(json.dumps(pr.cells[hck]['refs'][hrk].get('props') or {}))
    props.setdefault('lock', {})['level'] = HATCH_LOCK
    out.append({'op': 'props', 'cell': hck, 'ref': hrk, 'props': props})
    inner = json.loads(json.dumps(pr.cells[r['hold']]['refs'][r['to_deck']].get('props') or {}))
    inner['lock'] = None                    # (props merge: None takes the lock off)
    out.append({'op': 'props', 'cell': r['hold'], 'ref': r['to_deck'], 'props': inner})
    # the numbers on the station
    if r['station']:
        got = []
        radiotalk.add_talk(gd, pr, lambda _label, o: got.extend(o) or {}, r['station'], BULLETIN, lang='zh', gloss=BULLETIN_GLOSS)
        out += got
        rep['bulletin'] = True
    # decoding at the Radar Dome's terminal
    if r['terminal']:
        note = terminals.note_record(NOTE[0], NOTE[1], NOTE_TEXT)
        note_k = record(NOTE[0], note)
        record(MSG_DECODED, newgame._message_record(MSG_DECODED, DECODED))
        record(MSG_NOKEY, newgame._message_record(MSG_NOKEY, NO_KEY))
        forms = terminals.mod_forms(gd, pr, extra)
        src = '\n'.join(['if player.GetActorValue Science >= %d' % DECODE, '\tAddNote %s' % NOTE[0], '\tShowMessage %s' % MSG_DECODED,
                         'else', '\tShowMessage %s' % MSG_NOKEY, 'endif'])
        term = json.loads(json.dumps(pr.records[r['terminal']]))
        term['subs'] += [terminals._z('ITXT', 'Menu item text', ITEM), terminals._z('RNAM', 'Result text', ''),
                         {'tag': 'ANAM', 'label': 'Menu item flags', 'kind': 'struct', 'fields': [{'name': 'Flags', 'code': 'B', 'value': 0}]}]
        term['subs'] += terminals._script_parts(src, forms)
        out.append({'op': 'record', 'key': r['terminal'], 'record': term})
        rep['note'] = note_k
    # his lines (Mandarin, subtitled), compiled after the records are in
    lines = []
    for topic, k in ((caught_t, 'caught'), (ask_t, 'ask')):
        l = aq.new_line_plain(gd, pr, topic, qk, nk, shown(k))
        l['responses'] = [dict(l['responses'][0], text=shown(k), number=1)]
        lines.append(l)
    rep['lines'] = len(lines)
    rep['watch'] = {'spot': r['spot'], 'meals': MEALS}
    rep['keys'] = {'quest': qk, 'watch': nk}
    return out, rep, lines


def apply(pr, gd, P=None):
    import api_quests as aq
    o, rep, lines = ops(gd, pr, P)
    pr.apply(LABEL, o)
    pr.apply(LABEL, [{'op': 'record_new', 'record': aq._compiled_line(gd, pr, l)} for l in lines], merge=True)
    rep['voice'] = _own_voice(gd, pr, rep['keys']['watch'], rep['sex'] == 'F')
    rep['bulletin_voice'] = voice(gd, pr) if rep.get('bulletin') else None
    return rep


OWN = ['zm_yunjian*0.6+zm_yunxi*0.4', 'zm_yunxi*0.55+zm_yunjian*0.45', 'zm_yunjian*0.7+zm_yunyang*0.3', 'zm_yunxia*0.5+zm_yunjian*0.5']
OWN_F = ['zf_xiaoyi*0.6+zf_xiaoni*0.4', 'zf_xiaoni*0.55+zf_xiaoxiao*0.45', 'zf_xiaoyi*0.7+zf_xiaoxiao*0.3', 'zf_xiaoni*0.5+zf_xiaoyi*0.5']


def _own_voice(gd, pr, npc, female=False):
    """A Mandarin voice nobody else in voices.json has, kept as his choice (so the voicing pass uses it)."""
    import api_voices as av
    V = av.load(pr)
    taken = {(v.get('voice'), round(float(v.get('pitch', 0) or 0), 1)) for v in V.get('npc', {}).values() if isinstance(v, dict)}
    for pitch in (-1.0, -2.0, 1.0, 0.0):
        for v in (OWN_F if female else OWN):
            if (v, pitch) not in taken:
                V.setdefault('npc', {})[npc] = {'voice': v, 'speed': 0.92, 'pitch': pitch, 'lively': 1.0}
                av.save(pr, V)
                return v, pitch
    raise ValueError('no Mandarin voice left for the watchman')


def signal(seconds=3.2):
    """The bulletin's interval tune: four reed notes on the station's five-note scale, twice, a little slow."""
    import numpy as np
    import radiojingle as J
    R = J.RATE
    out = np.zeros(int(seconds * R), dtype=np.float64)
    notes = [70, 74, 77, 74]                         # (B-flat, D, F, D)
    at = 0.0
    for _round in range(2):
        for n in notes:
            J.add(out, at, J.reed(J.hz(n), 0.32), 0.5)
            at += 0.36
        at += 0.2
    out = J.on_air(out[:int(at * R)], 3)
    return out.astype(np.float32)


def voice(gd, pr):
    """The bulletin line's voice: the tune, then each sentence of the groups (its own response's file; the tune before
    the first), on air. [(path, seconds)]."""
    import os
    import numpy as np
    import soundfile
    import api_voices
    import library
    import lipwrite
    import radio
    import radiofx
    import radiotalk
    import voicefx
    import voicegen
    st = next(s for s in radio.stations(gd, pr) if s.get('name') == STATION)
    line = next(t['key'] for t in radiotalk.talk_of(gd, pr, st['quest']) if t['lang'] == 'zh' and t['gloss'] == BULLETIN_GLOSS)
    root = library.assets_dir(pr)
    V = api_voices.load(pr)
    R = voicegen.RATE
    out = []
    for n, said, rel in radiotalk.voice_paths(gd, pr, st['key'], line):
        a, t = voicegen.speak_zh(said[3:], READER, PACE)
        a = voicefx.master(a, True)
        a = radiofx.air(a, R, seed=n)
        if n == 1:
            tune = signal()
            gap = np.zeros(int(0.4 * R), dtype=np.float32)
            shift = (len(tune) + len(gap)) / R
            a = np.concatenate([tune, gap, a.astype(np.float32)])
            t = [(p, x + shift, y + shift) for p, x, y in t]
        base = os.path.join(root, rel)
        os.makedirs(os.path.dirname(base), exist_ok=True)
        with soundfile.SoundFile(base + '.ogg', 'w', R, 1, format='OGG', subtype='VORBIS') as f:
            for k in range(0, len(a), R):
                f.write(a[k:k + R])
        secs = len(a) / R
        with open(base + '.lip', 'wb') as f:
            f.write(lipwrite.write(lipwrite.from_timeline(t, seconds=secs)))
        V['lines'].setdefault(line, {})[str(n)] = {'text': said, 'voice': READER, 'path': rel, 'mood': [0, 50], 'engine': 'kokoro',
                                                   'lang': 'zh', 'say': said[3:], 'speed': PACE, 'jingle': 'signal' if n == 1 else None,
                                                   'on_air': True}
        out.append((rel, round(secs, 1)))
    api_voices.save(pr, V)
    return out


try:
    _zh()
except Exception:                      # (g2pzh unavailable at import: filled when the step runs)
    pass
