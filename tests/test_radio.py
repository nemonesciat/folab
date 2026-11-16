"""Radio stations: what radio.py makes is, record for record, what the game's own music stations are made of; a station
made in a fresh mod reads back from the written plugin linked as the game's are, with its files in place."""
import base64
import io
import math
import os
import struct
import sys
import wave
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import api_quests
import espwrite
import gamedata
import library
import project
import questrec as qr
import radio
import recordio
import schema
import tes4

gd = gamedata.GameData()
pr = project.Project.create('Radio Test')
P = radio.patterns(gd)


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)


def edit(label, ops):
    return {'made': pr.apply(label, ops), 'state': {}}


def game_link(k):
    """a key's form ID as FalloutNV.esm itself numbers it"""
    return gd.from_key(k) & 0xFFFFFF


def game_subs(key):
    i, rec = gd.source(gd.from_key(key))
    return list(tes4.iter_subrecords(gd.plugins[i].data(rec))), rec.flags & ~tes4.COMPRESSED


# ---- byte checks: our records, given the game's names, are the game's records ----
subs, flags = game_subs(P['station'])
ours = radio.station_record(gd, 'vCountryRadio', 'Mojave Music Radio')
check('the station: a talking activator the same as Mojave Music Radio\'s, bytes and flags (%08X)' % flags,
      recordio.to_bytes(ours, game_link) == subs and ours['flags'] == flags == 0x40020000)

subs, _f = game_subs(P['script'])
game_src = dict(subs)['SCTX'].decode('cp1252')
ours = radio.script_record(gd, 'vCountryRadioQuestSCRIPT', game_src)
mine = recordio.to_bytes(ours, game_link)
check('the quest\'s script compiles to the game\'s bytes (%d subrecords)' % len(subs), mine == subs)
own = recordio.to_bytes(radio.script_record(gd, 'vCountryRadioQuestSCRIPT'), game_link)
check('the source FOLab writes for it compiles to the same header, code and variables',
      [x for x in own if x[0] != 'SCTX'] == [x for x in subs if x[0] != 'SCTX'])

subs, flags = game_subs(P['quest'])
ours = radio.quest_record(gd, 'vCountryRadioQuest', P['station'], P['script'])
check('the quest: start game enabled, repeated topics, only the station\'s (bytes as the game\'s)', recordio.to_bytes(ours, game_link) == subs)

subs, flags = game_subs(P['song'])
ours = radio.song_record(gd, 'MUSNVGoinUnder', 'songs\\radionv\\mus_goin_under.mp3')
check('a song\'s sound record, bytes as the game\'s', recordio.to_bytes(ours, game_link) == subs)

li = qr.line_index(gd)
lines = li.by_quest[gd.from_key(P['quest'])]
same, n_lines = 0, 0
forms = api_quests.ModForms(gd, None)
for f in lines:
    subs, flags = game_subs(gd.key(f))
    l = qr.info_plain(recordio.load(gd, f))
    m = radio.re.search(r'iLastSong1 to (\d+)', l['begin']['source'])
    t = radio.re.match(r'\s*\{Song \d+ (.*)\}', l['responses'][0]['text'])
    n = int(m.group(1))
    plain = radio.line_plain(gd, P['quest'], n, t.group(1), l['responses'][0]['sound'])
    rec = radio._compiled(gd, None, plain, 'vCountryRadioQuest', n)
    mine = recordio.to_bytes(rec, game_link)
    # (the game's TRDT holds leftover bytes in its padding, and two of its lines a stray choice: neither is the pattern)
    mask = lambda xs: [(t, d[:13] + b'\0\0\0' + d[16:21] + b'\0\0\0' if t == 'TRDT' else d) for t, d in xs if t != 'TCLT']
    n_lines += 1
    same += mask(mine) == mask(subs) and flags == rec['flags'] == 0x2000 and gd.key(li.topic_of[f]) == plain['topic']
check('all %d of Mojave Music Radio\'s song lines come out of line_plain byte for byte (conditions, compiled result script)' % n_lines,
      n_lines >= 10 and same == n_lines)


def game_xrdo(edid):
    for i, p in enumerate(gd.plugins):
        for rec, _path in p.walk():
            if rec.tag == 'REFR':
                f = p.fields(rec)
                if 'XRDO' in f and gd.edid(gd.to_global(i, int.from_bytes(f['NAME'], 'little'))) == edid:
                    return f['XRDO'], rec.flags
    return None, 0


x, fl = game_xrdo('vCountryRadio')
check('heard everywhere: radio data as Mojave Music Radio\'s reference has it', x == radio.xrdo({'kind': radio.EVERYWHERE}) and fl & tes4.PERSISTENT)
x, fl = game_xrdo('RadioBlackMountainTA')
check('heard in a range: radio data as Black Mountain Radio\'s', x == radio.xrdo({'kind': radio.IN_RANGE, 'range': 50000, 'static': 5}))


# ---- three generated tones ----
def tone(hz, seconds=0.4, channels=2, bits=16, rate=44100):
    out = io.BytesIO()
    with wave.open(out, 'wb') as w:
        w.setnchannels(channels)
        w.setsampwidth(bits // 8)
        w.setframerate(rate)
        n = int(rate * seconds)
        if bits == 16:
            w.writeframes(b''.join(struct.pack('<h', int(12000 * math.sin(2 * math.pi * hz * k / rate))) * channels for k in range(n)))
        else:
            w.writeframes(bytes(128 + int(60 * math.sin(2 * math.pi * hz * k / rate)) for k in range(n)) * channels)
    return out.getvalue()


def silent_mp3(frames=40, mono=False):
    """MPEG-1 Layer III, 128 kbit, 44.1 kHz frames with nothing in them: silence the game's decoder can read."""
    return (b'\xff\xfb\x90' + (b'\xc0' if mono else b'\x00') + b'\0' * 413) * frames


tones = [('Aloha Oe.wav', tone(440)), ('Blue Hawaii.wav', tone(554, channels=1)), ('Sweet Leilani.wav', tone(659))]
out = radio.make_station(gd, pr, edit, 'Radio Waikiki', tones)
st = radio.station(gd, pr, out['station'])
check('a station of three tones: three songs, numbered 1 to 3, nothing left out',
      [t['n'] for t in st['tracks']] == [1, 2, 3] and not out['left_out'] and st['name'] == 'Radio Waikiki')
check('titles from the file names', [t['title'] for t in st['tracks']] == ['Aloha Oe', 'Blue Hawaii', 'Sweet Leilani'])
assets = library.assets_dir(pr)
check('each song\'s file is among the mod\'s own under sound\\songs, with a one-channel copy beside it',
      all(os.path.isfile(os.path.join(assets, t['file'])) and t['file'].startswith('sound\\songs\\folab\\') and t['info']['mono']
          and wave.open(os.path.join(assets, t['info']['mono'])).getnchannels() == 1 for t in st['tracks']))
check('the copy is the file as picked, byte for byte', open(os.path.join(assets, st['tracks'][0]['file']), 'rb').read() == tones[0][1])
check('heard everywhere, from a room of the mod\'s own', st['where'] and st['where']['everywhere'] and st['where']['cell'].startswith('+'))

_writes = [0]


def written():
    _writes[0] += 1
    path = pr.plugin_path()[:-4] + ' %d.esp' % _writes[0]
    espwrite.write(gd, pr, path)
    return tes4.PluginFile(path)


def read(p):
    """{form ID: (Record, [(tag, bytes)], group path)} of a written plugin"""
    return {rec.formid: (rec, list(tes4.iter_subrecords(p.data(rec))), path) for rec, path in p.walk()}


def of(recs, tag):
    return [(fid, r, subs, path) for fid, (r, subs, path) in recs.items() if r.tag == tag]


p = written()
masters = [m.lower() for m in p.header['masters']]
own = len(masters) << 24
recs = read(p)
check('the plugin needs only FalloutNV.esm', masters == ['falloutnv.esm'])
tacts = of(recs, 'TACT')
check('one talking activator, flagged a radio station that never stops, on the Pip-Boy\'s list, named',
      len(tacts) == 1 and tacts[0][1].flags == 0x40020000 and dict(tacts[0][2])['FULL'] == b'Radio Waikiki\0')
tact = tacts[0][0]
t = dict(tacts[0][2])
check('it has the game\'s voice type and radio sound', t['VNAM'] == struct.pack('<I', game_link('FalloutNV.esm:00002D')) and t['INAM'] == struct.pack('<I', game_link('FalloutNV.esm:04EC8A')))
refs = [(fid, r, subs, path) for fid, r, subs, path in of(recs, 'REFR') if dict(subs)['NAME'] == struct.pack('<I', tact)]
check('one reference of it, persistent, in a persistent group, with radio data: everywhere',
      len(refs) == 1 and refs[0][1].flags & tes4.PERSISTENT and refs[0][3][-1][0] == tes4.G_CELL_PERSISTENT
      and dict(refs[0][2])['XRDO'] == struct.pack('<fIfI', 0, 1, 0, 0))
cells = of(recs, 'CELL')
check('in an interior cell of the mod\'s own', len(cells) == 1 and cells[0][0] == refs[0][3][-1][1] and dict(cells[0][2])['DATA'] == b'\x01'
      and dict(cells[0][2])['EDID'] == b'FOLabRadioRoom\0')
quests = of(recs, 'QUST')
q = dict(quests[0][2])
ctda = q['CTDA']
check('one quest: start game enabled, repeated topics; its condition GetIsID the station == 1',
      len(quests) == 1 and q['DATA'][0] == 0x15 and struct.unpack_from('<H', ctda, 8)[0] == 72 and struct.unpack_from('<I', ctda, 12)[0] == tact
      and struct.unpack_from('<f', ctda, 4)[0] == 1.0)
quest = quests[0][0]
scripts = of(recs, 'SCPT')
s = scripts[0][2]
check('its script is the mod\'s, compiled: a quest script of three variables',
      len(scripts) == 1 and q['SCRI'] == struct.pack('<I', scripts[0][0]) and [d for t, d in s if t == 'SCVR'] == [b'iLastSong1\0', b'iLastSong2\0', b'iLastSong3\0']
      and struct.unpack('<IIIIHH', dict(s)['SCHR'])[2:5] == (len(dict(s)['SCDA']), 3, 1))
dials = of(recs, 'DIAL')
hello = gd.from_key(P['topic'])
fi, frec = li.first_topic[hello]           # (the file that first has the topic: what a plugin adding lines copies)
game_quests = [d for t, d in tes4.iter_subrecords(gd.plugins[fi].data(frec)) if t == 'QSTI']
mine = [d for t, d in dials[0][2] if t == 'QSTI'] if dials else []
check('the game\'s RadioHello topic comes along as a copy, every quest the game lists on it kept, the station\'s added',
      len(dials) == 1 and dials[0][0] == hello & 0xFFFFFF and mine[:len(game_quests)] == game_quests and mine[len(game_quests):] == [struct.pack('<I', quest)]
      and dict(dials[0][2])['DATA'][0] == 7)
infos = sorted(of(recs, 'INFO'))
souns = {fid: dict(subs) for fid, r, subs, path in of(recs, 'SOUN')}
ok = len(infos) == 3 and len(souns) == 3
song_src = game_subs(P['song'])[0]
for n, (fid, r, subs, path) in enumerate(infos, 1):
    d = dict(subs)
    conds = [x for t, x in subs if t == 'CTDA']
    snd = struct.unpack_from('<I', d['TRDT'], 16)[0]
    scro = [x for t, x in subs if t == 'SCRO']
    ok = ok and (path[-1][0] == tes4.G_TOPIC_CHILDREN and path[-1][1] == hello & 0xFFFFFF and r.flags == 0x2000 and d['DATA'] == bytes([7, 0, 10, 0])
                 and d['QSTI'] == struct.pack('<I', quest) and snd in souns and len(conds) == 2
                 and all(struct.unpack_from('<H', c, 8)[0] == 79 and struct.unpack_from('<I', c, 12)[0] == quest and struct.unpack_from('<I', c, 16)[0] == v
                         and struct.unpack_from('<f', c, 4)[0] == float(n) and c[0] >> 5 == 1 for v, c in enumerate(conds, 1))
                 and scro == [struct.pack('<I', quest)] and len(d['SCDA']) > 20 and d['NAM1'].startswith(b'  {Song %d ' % n))
    ok = ok and souns[snd]['SNDD'] == dict(song_src)['SNDD'] and souns[snd]['FNAM'].startswith(b'songs\\folab\\radio_test\\') \
        and os.path.isfile(os.path.join(assets, 'sound', souns[snd]['FNAM'][:-1].decode()))
check('three lines in RadioHello\'s group: radio type, random, each naming its own sound (the game\'s song settings, a file that is there), '
      'its quest, a compiled result script, and (with three songs) barred by the last two played', ok)
check('saving puts the song files beside the plugin', library.publish(pr) == 6 and all(
    os.path.isfile(os.path.join(library.built_dir(pr), t['file'])) for t in st['tracks']))

# ---- adding, refusing, taking off ----
more = [('Mono Song.mp3', silent_mp3(mono=True)), ('Stereo Song.mp3', silent_mp3()), ('Stereo Song_mono.ogg', b'OggS' + b'\0' * 60),
        ('Lossless.flac', b'fLaC' + b'\0' * 100), ('Not really.mp3', b'hello there, this is text' * 40), ('Eight bit.wav', tone(440, bits=8)),
        ('Orphan_mono.ogg', b'OggS')]
before = dict(pr.records)
out = radio.add_tracks(gd, pr, edit, st['key'], more)
st = radio.station(gd, pr, st['key'])
check('two MP3s added: five songs, numbers going on from 3', [t['n'] for t in st['tracks']] == [1, 2, 3, 4, 5])
check('the station itself, its quest and its script are untouched by adding songs',
      all(pr.records[k] is before[k] for k in (st['key'], st['quest'], recordio.field(pr.records[st['quest']], 'SCRI'))))
check('what the game wouldn\'t play is left out, each with its reason (%d)' % len(out['left_out']),
      len(out['left_out']) == 4 and any('FLAC' in x for x in out['left_out']) and any('isn\'t an MP3 inside' in x for x in out['left_out'])
      and any('8-bit' in x for x in out['left_out']) and any('Orphan' in x for x in out['left_out']))
by = {t['title']: t for t in st['tracks']}
check('a one-channel MP3 is its own copy for radios in the world; a stereo one takes the _mono.ogg picked with it',
      by['Mono Song']['info']['mono'].endswith('mono_song_mono.mp3') and by['Stereo Song']['info']['mono'].endswith('stereo_song_mono.ogg')
      and by['Stereo Song']['info']['channels'] == 2 and by['Mono Song']['info']['channels'] == 1)
check('an MP3\'s length and rate are read (%.1f s, %s Hz)' % (by['Stereo Song']['info']['seconds'], by['Stereo Song']['info']['rate']),
      abs(by['Stereo Song']['info']['seconds'] - 40 * 1152 / 44100) < 0.15 and by['Stereo Song']['info']['rate'] == 44100)
depth = lambda: sorted({len(qr.info_plain(pr.records[t['key']])['conditions']) for t in radio.station(gd, pr, st['key'])['tracks']})
check('with five songs every line is barred by the last three played, as the game\'s', depth() == [3])
recs = read(written())
check('written again: five lines, five sounds, still one quest and one topic', len(of(recs, 'INFO')) == 5 and len(of(recs, 'SOUN')) == 5
      and len(of(recs, 'QUST')) == 1 and len(of(recs, 'DIAL')) == 1 and all(len([1 for t, _d in subs if t == 'CTDA']) == 3 for _f, _r, subs, _p in of(recs, 'INFO')))

radio.remove_track(gd, pr, edit, st['key'], by['Blue Hawaii']['key'])
radio.remove_track(gd, pr, edit, st['key'], by['Mono Song']['key'])
st = radio.station(gd, pr, st['key'])
check('two taken off: three left, their numbers kept, their records gone', [t['n'] for t in st['tracks']] == [1, 3, 5]
      and by['Blue Hawaii']['key'] not in pr.records and by['Blue Hawaii']['sound'] not in pr.records and depth() == [2])
left = radio.unused_files(gd, pr)
check('their files stay until cleared (so Undo can bring a song back): %d' % len(left), len(left) == 4)
pr.undo()
check('Undo brings the song back, with its file', len(radio.station(gd, pr, st['key'])['tracks']) == 4 and len(radio.unused_files(gd, pr)) == 2 and depth() == [3])
pr.redo()
check('clearing removes only what no station plays', len(radio.clear_unused(gd, pr)) == 4 and not radio.unused_files(gd, pr)
      and all(not t['info'].get('missing') for t in radio.station(gd, pr, st['key'])['tracks']))
one = radio.make_station(gd, pr, edit, 'One Song', [('Only.wav', tone(300))])
check('a station of one song has no conditions (it would bar itself)', len(qr.info_plain(pr.records[radio.station(gd, pr, one['station'])['tracks'][0]['key']])['conditions']) == 0)
check('a second station heard everywhere shares the room', radio.station(gd, pr, one['station'])['where']['cell'] == st['where']['cell'])

# ---- a spot with a range ----
place = gd.key(sorted(gd.interiors)[0]) if not isinstance(gd.interiors, dict) else gd.key(sorted(gd.interiors)[0])
radio.set_where(gd, pr, edit, st['key'], {'everywhere': False, 'cell': place, 'p': [100, 200, 300], 'range': 3000, 'static': 30})
w = radio.station(gd, pr, st['key'])['where']
check('moved to a spot in a game place with a range', not w['everywhere'] and w['cell'] == place and w['range'] == 3000 and w['static'] == 30)
p = written()
recs = read(p)
tact = next(fid for fid, r, subs, path in of(recs, 'TACT') if dict(subs)['FULL'] == b'Radio Waikiki\0')
refs = [(fid, r, subs, path) for fid, r, subs, path in of(recs, 'REFR') if dict(subs)['NAME'] == struct.pack('<I', tact)]
check('written: one reference, persistent, in that place\'s persistent group, radio data as the game writes a range (as its Camp Guardian beacon)',
      len(refs) == 1 and refs[0][1].flags & tes4.PERSISTENT and refs[0][3][-1] [0] == tes4.G_CELL_PERSISTENT and refs[0][3][-1][1] == gd.from_key(place) & 0xFFFFFF
      and dict(refs[0][2])['XRDO'] == struct.pack('<fIfI', 3000, 0, 30, 0) and struct.unpack_from('<3f', dict(refs[0][2])['DATA']) == (100, 200, 300))
try:
    radio.set_where(gd, pr, edit, st['key'], {'everywhere': False, 'cell': place, 'p': [0, 0, 0], 'range': 0})
    check('a spot needs a range', False)
except radio.RadioProblem:
    check('a spot needs a range', True)

# ---- the routes ----
b64 = lambda d: base64.b64encode(d).decode()
got = radio.post('/api/radio/new', {'name': 'Route Radio', 'files': [{'name': 'x.wav', 'data': b64(tone(500))}]}, gd, pr, None, edit)
check('the route makes a station and answers with the list', got.get('station') and len(got['stations']) == 3 and 'problem' not in got)
got2 = radio.post('/api/radio/new', {'name': 'Bad', 'files': [{'name': 'x.flac', 'data': b64(b'fLaC')}]}, gd, pr, None, edit)
check('a station of files the game can\'t play is a problem in plain words, and nothing is made', 'FLAC' in got2.get('problem', '') and len(radio.stations(gd, pr)) == 3)
check('no name is a problem', 'name' in radio.post('/api/radio/new', {'name': ' ', 'files': []}, gd, pr, None, edit).get('problem', ''))
radio.post('/api/radio/rename', {'station': got['station'], 'name': 'KHON Honolulu'}, gd, pr, None, edit)
check('renaming changes the name, not the editor ID', radio.station(gd, pr, got['station'])['name'] == 'KHON Honolulu' and radio.station(gd, pr, got['station'])['edid'] == 'FOLabRadioRouteRadio')
data, ctype = radio.get('/api/radio/file', {'path': radio.station(gd, pr, got['station'])['tracks'][0]['file']}, gd, pr, None)
check('a song can be listened to from the page', ctype == 'audio/wav' and data[:4] == b'RIFF')
check('nothing outside the mod\'s radio folder is served', radio.get('/api/radio/file', {'path': '..\\..\\Radio Test.json'}, gd, pr, None) is None)
for s in radio.stations(gd, pr):
    radio.remove_station(gd, pr, edit, s['key'])
check('removing the stations leaves no station, quest, script, sound or line behind',
      not radio.stations(gd, pr) and not [r for r in pr.records.values() if r['type'] in ('TACT', 'QUST', 'SCPT', 'SOUN', 'INFO')]
      and not any(r.get('radio') for c in pr.cells.values() for r in c['refs'].values()))
