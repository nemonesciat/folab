"""Talk between songs (radiotalk.py): a station made by radio.py gains spoken lines, some waiting on what the player has done;
its songs give way to talk every few songs; read back from the written plugin as the game's own radio news is built."""
import io
import math
import os
import struct
import sys
import wave
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import espwrite
import gamedata
import project
import questrec as qr
import radio
import radiotalk
import recordio
import tes4

gd = gamedata.GameData()
pr = project.Project.create('Talk Test')
li = qr.line_index(gd)


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)


def edit(label, ops):
    return {'made': pr.apply(label, ops), 'state': {}}


def tone(hz):
    out = io.BytesIO()
    with wave.open(out, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(b''.join(struct.pack('<h', int(9000 * math.sin(2 * math.pi * hz * k / 44100))) for k in range(8000)))
    return out.getvalue()


def game_ctdas(fn):
    """[(bytes, file index)] of the game's conditions of one function, in radio lines first, then anywhere"""
    out = []
    for i, p in enumerate(gd.plugins):
        for rec, _path in p.walk():
            if rec.tag in ('INFO', 'QUST', 'PACK'):
                for t, d in tes4.iter_subrecords(p.data(rec)):
                    if t == 'CTDA' and len(d) >= 28 and struct.unpack_from('<H', d, 8)[0] == fn:
                        out.append((d, i))
        if out:
            return out
    return out


def link_for(i):
    masters = [m.lower() for m in gd.plugins[i].header['masters']]

    def link(k):
        fid = gd.from_key(k)
        n = gd.names[fid >> 24]
        return ((masters.index(n) if n in masters else len(masters)) << 24) | (fid & 0xFFFFFF)
    return link


def unlink(d, i):
    """a game CTDA's form fields as keys (the file's numbering to the load order's)"""
    return lambda off: gd.key(gd.to_global(i, struct.unpack_from('<I', d, off)[0]))


# ---- the facts' conditions are written as the game writes its own ----
for kind, fn in (('done', 546), ('found', 492), ('dead', 46)):
    got = game_ctdas(fn)
    d, i = next((d, i) for d, i in got if (d[0] >> 5) == 0 and struct.unpack_from('<f', d, 4)[0] == 1.0
                and (fn == 546 or struct.unpack_from('<I', d, 20)[0] == 2))
    k = unlink(d, i)
    fact = {'done': {'kind': 'done', 'quest': k(12)}, 'found': {'kind': 'found', 'marker': k(24)}, 'dead': {'kind': 'dead', 'ref': k(24)}}[kind]
    mine = recordio.to_bytes({'type': 'INFO', 'subs': [qr.condition_sub(radiotalk.fact_condition(fact))]}, link_for(i))[0][1]
    check('a "%s" fact\'s condition is the game\'s own, byte for byte (%s)' % (kind, d.hex()), mine == d)

# ---- a station that talks ----
out = radio.make_station(gd, pr, edit, 'Radio Talk', [('One.wav', tone(400)), ('Two.wav', tone(500)), ('Three.wav', tone(600)), ('Four.wav', tone(700))])
key = out['station']
st = radio.station(gd, pr, key)
quest = st['quest']
qedid = recordio.field(pr.records[quest], 'EDID')
songs_before = {t['key']: pr.records[t['key']] for t in st['tracks']}
check('a new station has no gate: its songs are as before', radiotalk.gate_of(pr, quest) is None
      and all(len(qr.info_plain(r)['conditions']) == 3 for r in songs_before.values()))

radiotalk.add_talk(gd, pr, edit, key, 'You are listening to Radio Talk. More music after this.', every=2)
gate = radiotalk.gate_of(pr, quest)
check('the first talk line starts the gate: every 2 songs', gate and gate['every'] == 2 and gate['name'] == 'iSince')
vars_ = [(n, name) for n, name, _i in radiotalk.script_vars(pr, quest)]
check('the script keeps its three variables and gains iSince as the fourth', vars_ == [(1, 'iLastSong1'), (2, 'iLastSong2'), (3, 'iLastSong3'), (4, 'iSince')])
ok = True
for t in radio.station(gd, pr, key)['tracks']:
    l = qr.info_plain(pr.records[t['key']])
    c = l['conditions'][-1]
    ok = ok and len(l['conditions']) == 4 and c['fn'] == 79 and c['p2'] == 4 and c['op'] == '<' and c['value'] == 2.0
    ok = ok and l['begin']['source'].endswith('set %s.iSince to %s.iSince + 1' % (qedid, qedid))
    ok = ok and any(p['tag'] == 'SCDA' and len(p['value']) > 60 for p in l['begin']['parts'])
check('every song now waits while talk is due and counts itself, compiled', ok)

# facts: a quest of the game done, and a map marker found
done_q = gd.key(next(f for f, (i, r) in gd.forms.items() if r.tag == 'QUST' and gd.edid(f) == 'VMQ01'))
marker = None
for f, (i, r) in gd.forms.items():
    if r.tag == 'REFR' and r.flags & tes4.PERSISTENT and 'XMRK' in gd.plugins[i].fields(r):
        marker = gd.key(f)
        break
radiotalk.add_talk(gd, pr, edit, key, 'Word from the road: the Courier finished what they started. ' * 5, facts=[{'kind': 'done', 'quest': done_q}], times=2)
radiotalk.add_talk(gd, pr, edit, key, 'Somebody found their way out past the old marker.', facts=[{'kind': 'found', 'marker': marker}])
talk = radiotalk.talk_of(gd, pr, quest)
check('three talk lines, read back with their facts and times', len(talk) == 3 and talk[0]['facts'] == [] and talk[1]['facts'] == [{'kind': 'done', 'quest': done_q}]
      and talk[1]['times'] == 2 and talk[1]['heard'] == 'iHeard1' and talk[2]['facts'] == [{'kind': 'found', 'marker': marker}])
check('a long bulletin is cut into responses short enough for subtitles', talk[1]['responses'] >= 2)
vars_ = [name for _n, name, _i in radiotalk.script_vars(pr, quest)]
check('a line said only so often counts itself in a variable of its own', vars_ == ['iLastSong1', 'iLastSong2', 'iLastSong3', 'iSince', 'iHeard1'])
l = qr.info_plain(pr.records[talk[1]['key']])
check('its result script sets iSince back to 0 and counts it heard, compiled',
      'set %s.iSince to 0' % qedid in l['begin']['source'] and 'iHeard1 to %s.iHeard1 + 1' % qedid in l['begin']['source']
      and [p['value'] for p in l['begin']['parts'] if p['tag'] == 'SCRO'] == [quest])
check('nothing to warn of: there is a line that can always be said', radiotalk.check(gd, pr, key) == [])

# the shape of a talk line against the game's own news
rnv = gd.from_key(gd.key(next(f for f, (i, r) in gd.forms.items() if r.tag == 'QUST' and gd.edid(f) == 'RadioNewVegas')))
story = next(f for f in li.by_quest[rnv] if gd.edid(li.topic_of[f]) == 'RNVNewsStory')
gl = qr.info_plain(recordio.load(gd, story))
check('a talk line is flagged as the game\'s news stories are (random, run immediately), radio type, no sound',
      l['kind'] == gl['kind'] == 7 and l['flags'] == gl['flags'] and all(not r['sound'] for r in l['responses']) and not gl['responses'][0]['sound'])

# ---- written and read back ----
path = pr.plugin_path()
espwrite.write(gd, pr, path)
p = tes4.PluginFile(path)
recs = {rec.formid: (rec, list(tes4.iter_subrecords(p.data(rec))), pth) for rec, pth in p.walk()}
infos = [(f, dict(s), s, pth) for f, (r, s, pth) in recs.items() if r.tag == 'INFO']
hello = gd.from_key(radio.patterns(gd)['topic']) & 0xFFFFFF
talk_ids = {int(t['key'][1:], 16) for t in talk}
qid = len(p.header['masters']) << 24 | int(quest[1:], 16)
ok = len(infos) == 7
for f, d, subs, pth in infos:
    ok = ok and pth[-1][0] == tes4.G_TOPIC_CHILDREN and pth[-1][1] == hello and d['QSTI'] == struct.pack('<I', qid)
    trdt = [x for t, x in subs if t == 'TRDT']
    if (f & 0xFFFFFF) in talk_ids:
        ok = ok and all(struct.unpack_from('<I', x, 16)[0] == 0 for x in trdt)
        gates = [x for t, x in subs if t == 'CTDA' and struct.unpack_from('<H', x, 8)[0] == 79 and struct.unpack_from('<I', x, 16)[0] == 4]
        ok = ok and len(gates) == 1 and gates[0][0] >> 5 == 3 and struct.unpack_from('<f', gates[0], 4)[0] == 2.0
    else:
        ok = ok and all(struct.unpack_from('<I', x, 16)[0] != 0 for x in trdt)
check('written: 4 songs with a sound and 3 talk lines without, all in RadioHello, talk waiting on iSince >= 2', ok)
marker_written = [x for f, d, subs, pth in infos for t, x in subs if t == 'CTDA' and struct.unpack_from('<H', x, 8)[0] == 492]
masters = [m.lower() for m in p.header['masters']]
check('the found-a-place condition runs on the marker, linked through the master list',
      len(marker_written) == 1 and struct.unpack_from('<I', marker_written[0], 20)[0] == 2
      and struct.unpack_from('<I', marker_written[0], 24)[0] == (masters.index(gd.names[gd.from_key(marker) >> 24]) << 24 | gd.from_key(marker) & 0xFFFFFF))
scpt = next(dict(s) for f, (r, s, pth) in recs.items() if r.tag == 'SCPT')
check('the script written has five variables', struct.unpack('<IIIIHH', scpt['SCHR'])[3] == 5)

# ---- voice files' names ----
paths = radiotalk.voice_paths(gd, pr, key, talk[0]['key'])
check('a talk line\'s voice file is where the game looks: the plugin, the station\'s voice type, quest_topic_id_n',
      paths[0][2] == os.path.join('sound', 'voice', 'talk test.esp', 'maleadult01default',
                                  '%s_%s_%08x_1' % (qedid[:10].lower(), 'radiohello', int(talk[0]['key'][1:], 16))).lower())

# ---- songs added later, talk taken off ----
radio.add_tracks(gd, pr, edit, key, [('Five.wav', tone(800))])
new = [t for t in radio.station(gd, pr, key)['tracks'] if t['n'] == 5][0]
check('a song added later waits for talk too', len(qr.info_plain(pr.records[new['key']])['conditions']) == 4)
for t in radiotalk.talk_of(gd, pr, quest)[1:]:
    radiotalk.remove_talk(gd, pr, edit, key, t['key'])
check('without the always line... (two taken off: only the ident left, still gated)', radiotalk.gate_of(pr, quest)['every'] == 2)
radiotalk.remove_talk(gd, pr, edit, key, radiotalk.talk_of(gd, pr, quest)[0]['key'])
ok = radiotalk.gate_of(pr, quest) is None
for t in radio.station(gd, pr, key)['tracks']:
    l = qr.info_plain(pr.records[t['key']])
    ok = ok and len(l['conditions']) == 3 and 'iSince' not in l['begin']['source']
check('the last talk line taken off takes the gate off every song', ok)
radiotalk.add_talk(gd, pr, edit, key, 'Station news, and only news.', facts=[{'kind': 'done', 'quest': done_q}])
check('a station whose every line waits on something is warned of', len(radiotalk.check(gd, pr, key)) == 1)
pr.undo()
pr.undo()
check('Undo puts the talk back', len(radiotalk.talk_of(gd, pr, quest)) == 1 and radiotalk.gate_of(pr, quest))
# ---- Mandarin ----
import g2pzh
import json
vocab = json.load(open(os.path.join(os.path.dirname(radio.__file__), 'kokorovocab.json'), encoding='utf-8'))
cases = {'ni3 hao3': 'ni↓ xau↓', 'shi4': 'ʂɨ↘', 'zi4': 'ʦɨ↘', 'ri4': 'ɻɨ↘', 'chi1': 'ꭧʰɨ→', 'zhong1': 'ꭧʊ→ŋ', 'dian4': 'tjɛ↘n',
         'duo1': 'two→', 'lai2': 'lai↗', 'er2': 'ɚ↗', 'ma5': 'ma', 'yu2': 'y↗', 'xue2': 'ɕɥe↗', 'jiu3': 'ʨjou↓', 'gui4': 'kwei↘',
         'lun2': 'lwə↗n', 'jun1': 'ʨy→n', 'Hǎixīn dòngtài.': 'xai↓ɕi→n tʊ↘ŋtʰai↘.'}
got = {k: g2pzh.sounds(k) for k in cases}
check('pinyin to Kokoro Chinese sounds as its own rules give them (%d cases)' % len(cases), got == cases)
check('every sound is one Kokoro has', not set(''.join(got.values())) - set(vocab) - {' '})
check('what shows is pinyin the game can print, the tones kept as numbers for the voice',
      g2pzh.shown('Hǎixīn dòngtài, lǜ') == 'Haixin dongtai, lü' and g2pzh.numbered('Hǎixīn dòngtài') == 'Hai3xin1 dong4tai4'
      and g2pzh.shown('Haixin dongtai, lü').encode('cp1252'))
radiotalk.add_talk(gd, pr, edit, key, 'Zhè lǐ shì Hǎixīn Dòngtài. Yǒu xiāoxi jiù gàosu dàjiā.', lang='zh', gloss='This is Haixin Dongtai.')
zh = [t for t in radiotalk.talk_of(gd, pr, quest) if t['lang'] == 'zh']
check('a Mandarin line: one response a sentence, shown without tones, said with them, the English kept beside',
      len(zh) == 1 and zh[0]['responses'] == 2 and zh[0]['text'] == 'Zhe li shi Haixin Dongtai. You xiaoxi jiu gaosu dajia.'
      and zh[0]['said'] == 'Zhe4 li3 shi4 Hai3xin1 Dong4tai4. You3 xiao1xi5 jiu4 gao4su5 da4jia1.' and zh[0]['gloss'] == 'This is Haixin Dongtai.')
check('its voice file takes the tone-numbered pinyin', [t for _n, t, _p in radiotalk.voice_paths(gd, pr, key, zh[0]['key'])][0] == 'zh:Zhe4 li3 shi4 Hai3xin1 Dong4tai4.')
try:
    radiotalk.add_talk(gd, pr, edit, key, 'Hello there.', lang='zh')
    check('English given as pinyin is refused', False)
except radio.RadioProblem:
    check('English given as pinyin is refused', True)
radio.remove_station(gd, pr, edit, key)
check('removing the station removes its talk too', not [r for r in pr.records.values() if r['type'] == 'INFO'])
