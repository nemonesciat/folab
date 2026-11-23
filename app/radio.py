"""Radio stations of the mod's own: a name and a list of the user's audio files, made into the records the game's own
music stations are made of.

How the game does it, read from its own records (Mojave Music Radio, the plainest; Radio New Vegas where it differs):

- The station is a talking activator (TACT `vCountryRadio`, "Mojave Music Radio"). Its record flags say what it is:
  0x20000 a radio station, 0x40000000 it broadcasts without stopping (27 of the game's have both), 0x10000000 it is kept
  off the Pip-Boy's list (the casino and shop music). FULL is the name the Pip-Boy lists. VNAM is its voice type (the
  folder its spoken lines' voice files are in; a music station has no spoken lines and the game gives it
  MaleAdult01Default), INAM a sound (`AMLRadio`) whose distances are how far a radio standing in the world carries it.
- Where it is heard is a placed, persistent reference of the activator with radio data, XRDO: range (float), kind
  (0 within the range of this spot, 1 everywhere, 3 two of the game's indoor ones), static (float: the outer so many
  in a hundred of the range are where the signal fades into static), and a reference to measure from instead of
  itself (0 in all but two). Mojave Music Radio and Radio New Vegas are kind 1 with nothing else set, in an interior
  cell nobody visits; Black Mountain Radio is kind 0, range 50000, static 5, outdoors. Every one of the game's 29 is
  in a persistent group. The Pip-Boy lists a station when a reference of it reaches the player, it is not initially
  disabled, and the activator isn't flagged off the list. (Radio New Vegas's is initially disabled and switched on by
  a script; Mojave Music Radio's is simply there.)
- What it plays is dialogue. The quest `vCountryRadioQuest` is start game enabled, allows repeated topics (DATA flags
  0x15), and has one condition: GetIsID vCountryRadio == 1, so its lines are only ever the station's. The game's topic
  `RadioHello` (DIAL 000126, type 7 Radio) is what a station says whenever it has nothing on; each of 19 station
  quests has its lines there. A line is an INFO of type 7, flags Random and Run immediately, record flag 0x2000.
- A song is a line with a sound: its one response (TRDT) names a SOUN record, and the words (NAM1) are a note in
  braces, `  {Song 1 Goin Under}`. A spoken line has no sound in TRDT: the game finds its voice file by name,
  `sound\\voice\\<plugin>\\<voice type>\\<quest>_<topic>_<line's form ID>_<n>.ogg` with a .lip beside it. So songs
  need no voice files, and nothing in a file's name ties it to the line.
- The SOUN (`MUSNVGoinUnder`): FNAM `songs\\radionv\\mus_goin_under.mp3` (under Data\\sound), and one SNDD the game
  gives 85 of its radio songs byte for byte (flags 0x140: 2D, dialogue; no distances). Of the sounds the game's radio
  lines name, 107 are .mp3 and 3 .wav; all 48 of its loose song files are MPEG-1 Layer III, 44.1 kHz, stereo, 256 kbit
  constant rate. Beside every `x.mp3` its archive holds `x_mono.ogg`: the Pip-Boy plays the sound's own file, a radio
  standing in the world asks for the same name with `_mono` before the extension (and that one is played in 3D).
- Picking the next and not repeating: the quest's script is three variables and nothing else (`int iLastSong1`,
  `iLastSong2`, `iLastSong3`). Song n's line has three conditions, GetQuestVariable quest, variable 1 / 2 / 3 != n, and
  a result script that runs as the line starts: `set Q.iLastSong3 to Q.iLastSong2`, `set Q.iLastSong2 to
  Q.iLastSong1`, `set Q.iLastSong1 to n`. Random among the lines whose conditions hold is the whole of the picking.
  Radio New Vegas does the same with nLastTrack1-3 in a topic of its own (`RNVMusic`) that its spoken lines lead to
  through choices (TCLT), counting tracks to know when to talk again; a music-only station needs none of that.

What this makes for a station (`make_station`), all as ops in one Undo:
    TACT   a copy of vCountryRadio with its own editor ID and name
    SCPT   the three variables, compiled by scriptc
    QUST   a copy of vCountryRadioQuest pointing at the TACT and the script
    SOUN + INFO per track (the INFO in the game's RadioHello: questrec.write_lines copies the topic with our quest listed)
    a persistent reference with 'radio' in its change (espwrite writes XRDO): heard everywhere from a small room of the
    mod's own (CELL `FOLabRadioRoom`, made once), or at a spot with a range.
With fewer than four tracks the conditions check only as many of the last-played as leave something to play (three
tracks each barred by the last three would be silence).

Nothing else is kept: a station's tracks, files and place are read back from those records (`stations`), so adding or
taking a track changes only that track's two records and the other lines' conditions.

Files: .mp3 and .wav are what the game's own stations use, and all this takes; anything else is refused with the
reason. FOLab converts nothing, except that a 16-bit WAV's mono copy is made here (averaging two channels is not a
converter). They are copied into the mod's own files as `sound\\songs\\folab\\<mod>\\<station>\\<name>.mp3` with the
mono copy beside them when there is one: a file picked along with the track and named `<name>_mono.ogg` (or .wav,
.mp3), the WAV's own, or the track itself when it's a mono MP3. A stereo MP3 with no mono copy plays on the Pip-Boy
and is expected to be silent from radios standing in the world."""
import base64
import io
import os
import re
import struct
import wave

import library
import questrec as qr
import recordio
import schema
import scriptc

RADIO_STATION, NOT_ON_PIPBOY, CONTINUOUS = 0x20000, 0x10000000, 0x40000000
EVERYWHERE, IN_RANGE = 1, 0
GET_IS_ID, GET_QUEST_VARIABLE = 72, 79
HISTORY = 3                             # the last songs a station won't play again, as the game's
ROOM = 'FOLabRadioRoom'
FORMATS = ('New Vegas plays radio songs from .mp3 or .wav files; its own are MP3, 44.1 kHz, stereo. FOLab copies your files as they '
           'are and converts nothing.')
MONO_NOTE = ('Radios standing in the world play a second, one-channel copy of each song. FOLab makes it itself from a WAV, and uses a '
             'one-channel MP3 as its own. For a stereo MP3, pick a copy named like the song with _mono on the end (Blue Hawaii.mp3 and '
             'Blue Hawaii_mono.ogg) along with it; without one the song plays on the Pip-Boy only.')
OTHER_KINDS = {'.ogg': 'an Ogg Vorbis file', '.flac': 'a FLAC file', '.m4a': 'an AAC file', '.aac': 'an AAC file', '.wma': 'a Windows Media file',
               '.opus': 'an Opus file', '.aiff': 'an AIFF file', '.aif': 'an AIFF file', '.mp4': 'a video file', '.mid': 'a MIDI file'}


class RadioProblem(ValueError):
    """Something the user can put right, in plain words."""


# ---------- what an audio file is ----------
_RATES = {3: (44100, 48000, 32000), 2: (22050, 24000, 16000), 0: (11025, 12000, 8000)}
_KBIT = {True: (0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320),
         False: (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160)}


def _frame(d, at):
    """An MPEG Layer III frame header at d[at:]: (rate, channels, kbit, frame length, samples a frame, is MPEG-1), or None."""
    if at + 4 > len(d) or d[at] != 0xFF or d[at + 1] & 0xE0 != 0xE0:
        return None
    h = struct.unpack_from('>I', d, at)[0]
    ver, layer, br, sr, pad, mode = (h >> 19) & 3, (h >> 17) & 3, (h >> 12) & 15, (h >> 10) & 3, (h >> 9) & 1, (h >> 6) & 3
    if ver == 1 or layer != 1 or br in (0, 15) or sr == 3:
        return None
    rate, kbit = _RATES[ver][sr], _KBIT[ver == 3][br]
    samples = 1152 if ver == 3 else 576
    return rate, 1 if mode == 3 else 2, kbit, samples // 8 * kbit * 1000 // rate + pad, samples, ver == 3


def mp3_info(d, size=None):
    """What an MP3 is, from its start (size: the whole file's, when d is only its head). None if it isn't one."""
    size = size or len(d)
    at = 0
    if d[:3] == b'ID3' and len(d) > 10:
        at = 10 + ((d[6] & 0x7F) << 21 | (d[7] & 0x7F) << 14 | (d[8] & 0x7F) << 7 | (d[9] & 0x7F))
        if at >= len(d):                    # (a tag longer than the head we were given: its cover picture, mostly)
            return {'kind': 'mp3', 'unread': True}
    end = min(len(d) - 4, at + 65536)
    while at < end:
        f = _frame(d, at)
        if f:
            nxt = _frame(d, at + f[3])
            if nxt and nxt[0] == f[0] or at + f[3] + 4 > len(d):
                break
        at += 1
    else:
        return None
    rate, channels, kbit, _length, samples, mpeg1 = f
    out = {'kind': 'mp3', 'rate': rate, 'channels': channels, 'kbit': kbit, 'mpeg1': mpeg1}
    head = d[at:at + 200]
    x = max(head.find(b'Xing'), head.find(b'Info'))
    if x >= 0 and struct.unpack_from('>I', head, x + 4)[0] & 1:
        out['seconds'] = round(struct.unpack_from('>I', head, x + 8)[0] * samples / rate, 1)
        out['varies'] = head[x:x + 4] == b'Xing'
    else:
        out['seconds'] = round((size - at) * 8 / (kbit * 1000), 1)
    return out


def wav_info(d, size=None):
    i = library._wav_info(d)
    if not i:
        return None
    out = {'kind': 'wav', 'rate': i.get('rate'), 'channels': i.get('channels'), 'format': i.get('format')}
    at = d.find(b'fmt ')
    out['bits'] = struct.unpack_from('<H', d, at + 22)[0] if 0 <= at and at + 24 <= len(d) else 0
    if i.get('seconds') is not None:
        out['seconds'] = round(i['seconds'], 1)
    elif out['rate'] and out['channels'] and out['bits'] and size:
        out['seconds'] = round(size / (out['rate'] * out['channels'] * out['bits'] / 8), 1)
    return out


def audio_info(name, d, size=None):
    """What a picked file is, or a RadioProblem saying why the game wouldn't play it as a song."""
    ext = os.path.splitext(name)[1].lower()
    if ext == '.mp3':
        i = mp3_info(d, size)
        if not i:
            raise RadioProblem('%s is named .mp3 but isn\'t an MP3 inside. Export it again as MP3 from an audio program.' % name)
        return i
    if ext == '.wav':
        i = wav_info(d, size)
        if not i:
            raise RadioProblem('%s is named .wav but isn\'t a WAV inside.' % name)
        if i['format'] != 'PCM' or i['bits'] != 16 or i['channels'] not in (1, 2):
            raise RadioProblem('%s is a WAV the game can\'t be trusted with (%s, %s-bit, %s channels). Export it as plain 16-bit PCM, or as MP3.'
                               % (name, i['format'], i['bits'], i['channels']))
        return i
    raise RadioProblem('%s is %s. %s Export it as MP3 or WAV from an audio program (in Audacity: File, Export) and pick that.'
                       % (name, OTHER_KINDS.get(ext, 'a %s file' % (ext or 'nameless')), FORMATS))


def notes_on(i):
    """What to tell the user about a file the game should take but isn't like its own."""
    out = []
    if i.get('rate') and i['rate'] != 44100:
        out.append('%.5g kHz, where the game\'s own songs are 44.1' % (i['rate'] / 1000))
    if i['kind'] == 'mp3' and i.get('mpeg1') is False:
        out.append('an older, low-rate kind of MP3')
    return out


def mono_wav(d):
    """A 16-bit PCM WAV as one channel (two averaged)."""
    with wave.open(io.BytesIO(d)) as w:
        ch, rate, n = w.getnchannels(), w.getframerate(), w.getnframes()
        frames = w.readframes(n)
    if ch == 2:
        s = struct.unpack('<%dh' % (len(frames) // 2), frames[:len(frames) // 2 * 2])
        frames = struct.pack('<%dh' % (len(s) // 2), *[(s[k] + s[k + 1]) >> 1 for k in range(0, len(s) - 1, 2)])
    out = io.BytesIO()
    with wave.open(out, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(frames)
    return out.getvalue()


def _mono_stem(name):
    stem = os.path.splitext(name)[0]
    return stem[:-5] if stem.lower().endswith('_mono') else None


def sort_files(files):
    """[(name, bytes)] as picked -> ([(name, bytes, info, mono (ext, bytes) or None)], [what was left out and why])."""
    monos, tracks, left = {}, [], []
    for name, d in files:
        name = os.path.basename(name.replace('\\', '/'))
        of = _mono_stem(name)
        if of is not None and os.path.splitext(name)[1].lower() in ('.ogg', '.wav', '.mp3'):
            monos[of.lower()] = (os.path.splitext(name)[1].lower(), d, name)
        else:
            tracks.append((name, d))
    out = []
    for name, d in tracks:
        try:
            i = audio_info(name, d)
        except RadioProblem as e:
            left.append(str(e))
            continue
        mono = monos.pop(os.path.splitext(name)[0].lower(), None)
        mono = mono and mono[:2]
        if mono is None and i['kind'] == 'wav':
            mono = ('.wav', mono_wav(d))
        elif mono is None and i['channels'] == 1:
            mono = ('.mp3', d)
        out.append((name, d, i, mono))
    left += ['%s_mono%s was left out: no song named %s was picked with it.' % (of, e, of) for of, e in ((_mono_stem(n), e) for e, _d, n in monos.values())]
    return out, left


# ---------- the game's own, to copy ----------
def _find(gd, edid, tag):
    f = scriptc.GameForms(gd).find_edid(edid)
    if not f or f.tag != tag:
        raise RadioProblem('The game\'s own %s (%s) isn\'t in these game files: FOLab copies it to make a station.' % (edid, tag))
    return f.fid


def patterns(gd):
    """The game's records a station is copied from, found once: {'station', 'quest', 'script', 'song', 'line', 'topic'} keys."""
    got = getattr(gd, '_radio_patterns', None)
    if got is None:
        quest = _find(gd, 'vCountryRadioQuest', 'QUST')
        lines = qr.line_index(gd).by_quest.get(quest) or []
        if not lines:
            raise RadioProblem('The game\'s Mojave Music Radio has no songs in these game files.')
        got = gd._radio_patterns = {
            'station': gd.key(_find(gd, 'vCountryRadio', 'TACT')), 'quest': gd.key(quest),
            'script': gd.key(_find(gd, 'vCountryRadioQuestSCRIPT', 'SCPT')), 'song': gd.key(_find(gd, 'MUSNVGoinUnder', 'SOUN')),
            'line': gd.key(lines[0]), 'topic': gd.key(_find(gd, 'RadioHello', 'DIAL'))}
    return got


def _copy(gd, key):
    return recordio.load(gd, gd.from_key(key))


# ---------- the records ----------
def station_record(gd, edid, name, on_pipboy=True):
    rec = _copy(gd, patterns(gd)['station'])
    recordio.set_field(rec, 'EDID', edid)
    recordio.set_field(rec, 'FULL', name)
    rec['flags'] = RADIO_STATION | CONTINUOUS | (0 if on_pipboy else NOT_ON_PIPBOY)
    return rec


def script_source(edid):
    return 'scn %s\r\n\r\n' % edid + ''.join('int iLastSong%d\r\n' % n for n in range(1, HISTORY + 1))


def script_record(gd, edid, source=None):
    c = scriptc.compile_script(source or script_source(edid), scriptc.GameForms(gd), scriptc.SCRIPT_QUEST)
    return {'type': 'SCPT', 'flags': 0, 'src': '', 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': edid}]
            + schema.decode_record('SCPT', c.subrecords(lambda _fid: 0))}


def quest_record(gd, edid, station, script):
    q = qr.quest_plain(_copy(gd, patterns(gd)['quest']))
    q.update(edid=edid, script=script, src='')
    for c in q['conditions']:
        if c['fn'] == GET_IS_ID:
            c['p1'] = station
    return qr.quest_record(q)


def song_record(gd, edid, fnam):
    """fnam: the file under Data\\sound, as SOUN names it."""
    rec = _copy(gd, patterns(gd)['song'])
    recordio.set_field(rec, 'EDID', edid)
    recordio.set_field(rec, 'FNAM', fnam)
    return rec


def line_text(n, title):
    return '  {Song %d %s}' % (n, title)


def line_source(quest_edid, n, gate=None):
    """Song n's result script. gate: a station that talks (radiotalk.py) counts the songs since it last did."""
    q = quest_edid
    out = ('set %s.iLastSong3 to %s.iLastSong2\r\nset %s.iLastSong2 to %s.iLastSong1\r\nset %s.iLastSong1 to %d' % (q, q, q, q, q, n))
    if gate:
        out += '\r\nset %s.%s to %s.%s + 1' % (q, gate['name'], q, gate['name'])
    return out


def line_conditions(quest, n, depth=HISTORY, gate=None):
    out = [{'or': False, 'use_target': False, 'op': '!=', 'fn': GET_QUEST_VARIABLE, 'p1': quest, 'p2': v, 'run': 0, 'ref': '', 'value': float(n)}
           for v in range(1, depth + 1)]
    if gate:                                # (a station that talks: no song while talk is due)
        out.append({'or': False, 'use_target': False, 'op': '<', 'fn': GET_QUEST_VARIABLE, 'p1': quest, 'p2': gate['var'], 'run': 0, 'ref': '',
                    'value': float(gate['every'])})
    return out


def line_plain(gd, quest, n, title, sound, depth=HISTORY, gate=None):
    """Song n's line, on the game's first Mojave Music Radio line (its flags, its response's numbers); its result script
    still to compile."""
    l = qr.info_plain(_copy(gd, patterns(gd)['line']))
    r = dict(l['responses'][0], sound=sound, text=line_text(n, title))
    r.pop('pads', None)                 # (the game's hold leftovers from its editor's memory)
    l.update(quest=quest, topic=patterns(gd)['topic'], responses=[r], conditions=line_conditions(quest, n, depth, gate), choices=[], src='', begin=None, end=None)
    return l


def xrdo(r, link=None):
    """A reference's radio data as the game writes it. r: {'kind': EVERYWHERE or IN_RANGE, 'range', 'static', 'from': ref key}."""
    src = r.get('from')
    return struct.pack('<fIfI', float(r.get('range') or 0), int(r.get('kind', EVERYWHERE)), float(r.get('static') or 0), link(src) if src and link else 0)


def room_record(name='Radio room'):
    """A bare interior nobody visits, to keep stations heard everywhere in (the game keeps its own in one too)."""
    subs = [schema.decode_sub('CELL', 'EDID', ROOM.encode() + b'\0'), schema.decode_sub('CELL', 'FULL', name.encode() + b'\0'),
            schema.decode_sub('CELL', 'DATA', b'\x01'),
            schema.decode_sub('CELL', 'XCLL', bytes([40, 40, 40, 0, 0, 0, 0, 0, 20, 20, 20, 0]) + struct.pack('<ffiifff', 200.0, 2000.0, 0, 0, 1.0, 2000.0, 1.0))]
    return {'type': 'CELL', 'flags': 0, 'src': '', 'subs': subs}


# ---------- reading a mod's stations back from its records ----------
class _With:
    """The mod with records about to be made laid over it (for the compiler to find them)."""

    def __init__(self, pr, extra):
        self.records = dict(pr.records if pr else {}, **extra)


def _forms(gd, pr, extra=None):
    import api_quests
    return api_quests.ModForms(gd, _With(pr, extra or {}))


def _compiled(gd, pr, plain, quest_edid, n, extra=None, gate=None):
    import api_quests
    src = line_source(quest_edid, n, gate)
    plain['begin'] = {'source': src, 'parts': api_quests.compile_parts(src, _forms(gd, pr, extra))}
    plain['end'] = qr.empty_script()
    rec = qr.info_record(plain)
    rec['topic'] = plain['topic']
    return rec


def _taken(gd, pr, more=()):
    names = {recordio.field(r, 'EDID').lower() for r in pr.records.values()} | {m.lower() for m in more}
    game = scriptc.GameForms(gd)

    def free(wanted):
        wanted = re.sub(r'[^A-Za-z0-9]', '', wanted) or 'FOLabRadio'
        n, e = 1, wanted
        while e.lower() in names or game.find_edid(e):
            n += 1
            e = '%s%d' % (wanted, n)
        names.add(e.lower())
        return e
    return free


def _folder(pr, station_edid):
    return 'sound\\songs\\folab\\%s\\%s' % (library.slug(pr.name), station_edid.lower())


def _quest_of(pr, station):
    for k, r in pr.records.items():
        if r['type'] == 'QUST' and k.startswith('+'):
            for s in r['subs']:
                if s['tag'] == 'CTDA':
                    f = {x.get('name'): x.get('value') for x in s['fields']}
                    if f.get('Function') == GET_IS_ID and f.get('Parameter 1') == station:
                        return k
    return None


def _file_row(pr, rel):
    p = os.path.join(library.assets_dir(pr), rel)
    if not os.path.isfile(p):
        return {'path': rel, 'missing': True}
    size = os.path.getsize(p)
    with open(p, 'rb') as f:
        head = f.read(262144)
    try:
        i = audio_info(rel, head, size)
    except RadioProblem:
        i = {}
    stem, ext = os.path.splitext(rel)
    mono = next((stem + '_mono' + e for e in (ext, '.ogg', '.wav', '.mp3') if os.path.isfile(os.path.join(library.assets_dir(pr), stem + '_mono' + e))), None)
    return {'path': rel, 'size': size, 'seconds': i.get('seconds'), 'rate': i.get('rate'), 'channels': i.get('channels'), 'kind': i.get('kind'),
            'mono': mono, 'notes': notes_on(i) if i.get('kind') else []}


def tracks_of(pr, quest):
    """A station's songs from its lines: [{'key', 'n', 'title', 'sound', 'file'}] by number."""
    out = []
    for k, r in pr.records.items():
        if r['type'] != 'INFO' or recordio.field(r, 'QSTI') != quest:
            continue
        l = qr.info_plain(r)
        resp = l['responses'][0] if l['responses'] else {}
        m = re.search(r'iLastSong1\s+to\s+(\d+)', (l.get('begin') or {}).get('source', ''), re.I)
        t = re.match(r'\s*\{Song \d+ (.*)\}\s*$', resp.get('text', ''))
        sound = resp.get('sound') or ''
        srec = pr.records.get(sound) if sound.startswith('+') else None
        if not m or not srec:
            continue                    # (a line someone added by hand on the Quests page: not ours to manage)
        out.append({'key': k, 'n': int(m.group(1)), 'title': t.group(1) if t else recordio.field(srec, 'EDID'), 'sound': sound,
                    'file': 'sound\\' + recordio.field(srec, 'FNAM')})
    return sorted(out, key=lambda t: t['n'])


def _where_of(gd, pr, station):
    for ck, c in pr.cells.items():
        for rk, r in c['refs'].items():
            if r.get('base') == station and not r.get('removed'):
                rd = r.get('radio') or {}
                rec = pr.records.get(ck) if ck.startswith('+') else None
                if rec:
                    name = recordio.field(rec, 'FULL') or recordio.field(rec, 'EDID')
                elif ck.startswith('+'):
                    name = ck
                else:
                    d = gd.describe(gd.from_key(ck))            # (tag, editor ID, name, ...)
                    name = (d[2] or d[1]) if isinstance(d, (tuple, list)) and len(d) > 2 else str(d)
                    grid = gd.cell_grid(gd.from_key(ck))
                    if grid and not d[2]:
                        name = 'outdoors, cell %d, %d' % grid
                return {'cell': ck, 'ref': rk, 'everywhere': rd.get('kind', EVERYWHERE) == EVERYWHERE, 'range': rd.get('range') or 0,
                        'static': rd.get('static') or 0, 'p': r.get('p'), 'place': name or ck}
    return None


def stations(gd, pr):
    out = []
    for k, r in pr.records.items():
        if r['type'] == 'TACT' and k.startswith('+') and r.get('flags', 0) & RADIO_STATION:
            quest = _quest_of(pr, k)
            if not quest:
                continue
            tr = tracks_of(pr, quest)
            for t in tr:
                t['info'] = _file_row(pr, t['file'])
            out.append({'key': k, 'edid': recordio.field(r, 'EDID'), 'name': recordio.field(r, 'FULL'), 'quest': quest,
                        'on_pipboy': not r['flags'] & NOT_ON_PIPBOY, 'tracks': tr, 'where': _where_of(gd, pr, k),
                        'folder': _folder(pr, recordio.field(r, 'EDID'))})
    return sorted(out, key=lambda s: s['name'].lower())


def station(gd, pr, key):
    s = next((s for s in stations(gd, pr) if s['key'] == key), None)
    if not s:
        raise RadioProblem('That station isn\'t in this mod any more.')
    return s


def unused_files(gd, pr):
    """Song files in the mod's radio folders no station plays (a taken-out track's file stays, so Undo can bring it back)."""
    root = library.assets_dir(pr)
    base = os.path.join(root, 'sound', 'songs', 'folab')
    used = set()
    for s in stations(gd, pr):
        for t in s['tracks']:
            used.add(t['file'].lower())
            if t['info'].get('mono'):
                used.add(t['info']['mono'].lower())
    out = []
    for d, _dirs, fs in os.walk(base):
        for fn in fs:
            rel = os.path.relpath(os.path.join(d, fn), root).replace('/', '\\')
            if rel.lower() not in used:
                out.append(rel)
    return sorted(out)


def clear_unused(gd, pr):
    root = library.assets_dir(pr)
    gone = unused_files(gd, pr)
    for rel in gone:
        os.remove(os.path.join(root, rel))
    for d, dirs, fs in os.walk(os.path.join(root, 'sound', 'songs', 'folab'), topdown=False):
        if not dirs and not fs:
            os.rmdir(d)
    return gone


# ---------- making and changing ----------
def _title(name):
    t = re.sub(r'[\x00-\x1f{}]', '', os.path.splitext(name)[0]).replace('_', ' ').strip()
    return t[:80] or 'Song'


def _put_files(pr, folder, sorted_files):
    """The picked files into the mod's own; [(title, file under Data, info, has a mono copy)]."""
    root = library.assets_dir(pr)
    out = []
    for name, d, i, mono in sorted_files:
        ext = os.path.splitext(name)[1].lower()
        stem = library.slug(os.path.splitext(name)[0])
        rel, k = '%s\\%s%s' % (folder, stem, ext), 1
        while os.path.exists(os.path.join(root, rel)) or any(os.path.exists(os.path.join(root, '%s\\%s_mono%s' % (folder, os.path.splitext(os.path.basename(rel))[0], e))) for e in ('.ogg', '.wav', '.mp3')):
            k += 1
            rel = '%s\\%s_%d%s' % (folder, stem, k, ext)
        library._put(root, rel, d)
        if mono:
            library._put(root, os.path.splitext(rel)[0] + '_mono' + mono[0], mono[1])
        out.append((_title(name), rel, i, bool(mono)))
    return out


def _depth(count):
    return max(0, min(HISTORY, count - 1))


def _track_ops(gd, pr, st_edid, quest, quest_edid, put, first_n, keys, free, depth, extra, gate=None):
    """record_new ops for songs first_n.. (a SOUN and its line each), their keys taken from keys in order."""
    ops = []
    for k, (title, rel, _i, _mono) in enumerate(put):
        n = first_n + k
        skey, lkey = next(keys), next(keys)
        srec = song_record(gd, free('%sSong%02d' % (st_edid, n)), rel[len('sound\\'):])
        extra[skey] = srec
        ops.append({'op': 'record_new', 'record': srec})
        ops.append({'op': 'record_new', 'record': _compiled(gd, pr, line_plain(gd, quest, n, title, skey, depth, gate), quest_edid, n, extra, gate)})
    return ops


def _relined(gd, pr, quest, depth, skip=(), gate=None, extra=None):
    """ops giving the station's existing song lines conditions of another depth, or another gate (radiotalk.py); a line
    already as it should be is left."""
    ops = []
    quest_edid = recordio.field((extra or {}).get(quest) or pr.records[quest], 'EDID')
    for k, r in pr.records.items():
        if r['type'] == 'INFO' and recordio.field(r, 'QSTI') == quest and k not in skip:
            l = qr.info_plain(r)
            m = re.search(r'iLastSong1\s+to\s+(\d+)', (l.get('begin') or {}).get('source', ''), re.I)
            if not m:
                continue                    # (a talk line, or one added by hand)
            n = int(m.group(1))
            want = line_conditions(quest, n, depth, gate)
            src = line_source(quest_edid, n, gate)
            same_src = (l.get('begin') or {}).get('source', '').replace('\r\n', '\n') == src.replace('\r\n', '\n')
            if [qr.condition_sub(c) for c in l['conditions']] != [qr.condition_sub(c) for c in want] or not same_src:
                l['conditions'] = want
                if not same_src:
                    import api_quests
                    l['begin'] = {'source': src, 'parts': api_quests.compile_parts(src, _forms(gd, pr, extra))}
                rec = qr.info_record(l)
                for f in ('topic', 'seq'):
                    if f in r:
                        rec[f] = r[f]
                ops.append({'op': 'record', 'key': k, 'record': rec})
    return ops


def _room(pr):
    return next((k for k, r in pr.records.items() if k.startswith('+') and r['type'] == 'CELL' and recordio.field(r, 'EDID') == ROOM), None)


def _where_ops(gd, pr, base, where, keys):
    """The reference a station is heard through. where: {'everywhere': True} or {'cell', 'p': [x, y, z], 'range', 'static'}."""
    ops = []
    if where.get('everywhere', True):
        cell = _room(pr)
        if not cell:
            cell = next(keys)
            ops.append({'op': 'record_new', 'record': room_record()})
        n = sum(1 for r in (pr.cells.get(cell) or {'refs': {}})['refs'].values() if r.get('radio'))
        p, radio = [n * 64.0, 0, 0, 0, 0, 0], {'kind': EVERYWHERE, 'range': 0, 'static': 0}
    else:
        cell = where.get('cell')
        if not cell and where.get('world') and where.get('p'):      # (outdoors, with nothing under the view to say which cell)
            c = gd.grid(gd.from_key(where['world'])).get((int(where['p'][0] // 4096), int(where['p'][1] // 4096)))
            cell = gd.key(c) if c is not None else None
        if not cell or not where.get('p'):
            raise RadioProblem('Open the place where it should be heard, and look at the spot, first.')
        rng = float(where.get('range') or 0)
        if rng <= 0:
            raise RadioProblem('Give it a range: how far from the spot it\'s heard (a cell outdoors is 4096 across).')
        p = [float(v) for v in where['p'][:3]] + [0, 0, 0]
        radio = {'kind': IN_RANGE, 'range': rng, 'static': max(0.0, min(100.0, float(where.get('static') or 0)))}
    next(keys)
    ops.append({'op': 'add', 'cell': cell, 'base': base, 'p': p, 's': 1, 'extra': {'persistent': True, 'radio': radio}})
    return ops


def _keys(pr):
    n = pr.next_id
    while True:
        yield '+%06X' % n
        n += 1


def _need_some(put, left):
    if not put:
        raise RadioProblem(' '.join(left) if left else 'Pick the songs first: ' + FORMATS)


def make_station(gd, pr, edit, name, files, where=None):
    """A new station (one Undo). files: [(name, bytes)]. Returns {'station': key, 'left_out': [...], plus edit's answer}."""
    name = (name or '').strip()
    if not name:
        raise RadioProblem('Give the station a name: it\'s what the Pip-Boy lists.')
    patterns(gd)
    sorted_files, left = sort_files(files)
    _need_some(sorted_files, left)
    free = _taken(gd, pr)
    st_edid = free('FOLabRadio' + ''.join(w.capitalize() for w in re.split(r'[^A-Za-z0-9]+', name) if w)[:40])
    q_edid, s_edid = free(st_edid + 'Quest'), free(st_edid + 'QuestSCRIPT')
    put = _put_files(pr, _folder(pr, st_edid), sorted_files)
    keys = _keys(pr)
    st_key, sc_key, q_key = next(keys), next(keys), next(keys)
    script, quest = script_record(gd, s_edid), quest_record(gd, q_edid, st_key, sc_key)
    extra = {sc_key: script, q_key: quest}
    ops = [{'op': 'record_new', 'record': station_record(gd, st_edid, name)}, {'op': 'record_new', 'record': script}, {'op': 'record_new', 'record': quest}]
    ops += _track_ops(gd, pr, st_edid, q_key, q_edid, put, 1, keys, free, _depth(len(put)), extra)
    ops += _where_ops(gd, pr, st_key, where or {'everywhere': True}, keys)
    out = edit('Radio station ' + name, ops)
    out.update(station=st_key, left_out=left)
    return out


def add_tracks(gd, pr, edit, key, files):
    st = station(gd, pr, key)
    sorted_files, left = sort_files(files)
    _need_some(sorted_files, left)
    put = _put_files(pr, st['folder'], sorted_files)
    quest_edid = recordio.field(pr.records[st['quest']], 'EDID')
    depth = _depth(len(st['tracks']) + len(put))
    first = max([t['n'] for t in st['tracks']] or [0]) + 1
    import radiotalk
    gate = radiotalk.gate_of(pr, st['quest'])
    ops = _relined(gd, pr, st['quest'], depth, gate=gate)
    ops += _track_ops(gd, pr, st['edid'], st['quest'], quest_edid, put, first, _keys(pr), _taken(gd, pr), depth, {}, gate)
    out = edit('%d song%s for %s' % (len(put), '' if len(put) == 1 else 's', st['name']), ops)
    out.update(station=key, left_out=left)
    return out


def remove_track(gd, pr, edit, key, track):
    st = station(gd, pr, key)
    t = next((t for t in st['tracks'] if t['key'] == track), None)
    if not t:
        raise RadioProblem('That song isn\'t on the station any more.')
    ops = [{'op': 'record_revert', 'key': t['key']}, {'op': 'record_revert', 'key': t['sound']}]
    import radiotalk
    ops += _relined(gd, pr, st['quest'], _depth(len(st['tracks']) - 1), skip=(t['key'],), gate=radiotalk.gate_of(pr, st['quest']))
    out = edit('Take %s off %s' % (t['title'], st['name']), ops)
    out['station'] = key
    return out


def remove_station(gd, pr, edit, key):
    st = station(gd, pr, key)
    ops = []
    if st['where']:
        ops.append({'op': 'remove', 'cell': st['where']['cell'], 'ref': st['where']['ref']})
    for t in st['tracks']:
        ops += [{'op': 'record_revert', 'key': t['key']}, {'op': 'record_revert', 'key': t['sound']}]
    import radiotalk
    ops += [{'op': 'record_revert', 'key': t['key']} for t in radiotalk.talk_of(gd, pr, st['quest'])]
    quest = pr.records[st['quest']]
    script = recordio.field(quest, 'SCRI')
    ops += [{'op': 'record_revert', 'key': k} for k in (st['quest'], script, key) if k and k.startswith('+')]
    return edit('Remove radio station ' + st['name'], ops)


def rename(gd, pr, edit, key, name):
    name = (name or '').strip()
    if not name:
        raise RadioProblem('A station needs a name.')
    rec = dict(pr.records[key], subs=[dict(s) for s in pr.records[key]['subs']])
    recordio.set_field(rec, 'FULL', name)
    return edit('Rename radio station to ' + name, [{'op': 'record', 'key': key, 'record': rec}])


def set_where(gd, pr, edit, key, where):
    st = station(gd, pr, key)
    ops = [{'op': 'remove', 'cell': st['where']['cell'], 'ref': st['where']['ref']}] if st['where'] else []
    ops += _where_ops(gd, pr, key, where, _keys(pr))
    return edit('Where %s is heard' % st['name'], ops)


# ---------- routes ----------
def _files(body):
    return [(f['name'], base64.b64decode(f['data'])) for f in body.get('files') or ()]


def listing(gd, pr):
    return {'stations': stations(gd, pr) if pr else [], 'unused': unused_files(gd, pr) if pr else [], 'formats': FORMATS, 'mono': MONO_NOTE}


def get(path, q, gd, pr, br):
    """GET /api/radio/..."""
    if path == '/api/radio/list':
        return listing(gd, pr)
    if path == '/api/radio/file':
        rel = (q.get('path') or '').replace('/', '\\')
        root = os.path.normpath(library.assets_dir(pr))
        p = os.path.normpath(os.path.join(root, rel))
        if not rel.lower().startswith('sound\\songs\\folab\\') or not p.startswith(root) or not os.path.isfile(p):
            return None
        with open(p, 'rb') as f:
            return f.read(), {'.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.ogg': 'audio/ogg'}.get(os.path.splitext(p)[1].lower(), 'application/octet-stream')
    return None


def post(path, body, gd, pr, br, edit):
    """POST /api/radio/...: a problem the user can fix comes back as {'problem': text}."""
    try:
        if path == '/api/radio/new':
            out = make_station(gd, pr, edit, body.get('name'), _files(body), body.get('where'))
        elif path == '/api/radio/add':
            out = add_tracks(gd, pr, edit, body['station'], _files(body))
        elif path == '/api/radio/remove_track':
            out = remove_track(gd, pr, edit, body['station'], body['track'])
        elif path == '/api/radio/remove':
            out = remove_station(gd, pr, edit, body['station'])
        elif path == '/api/radio/rename':
            out = rename(gd, pr, edit, body['station'], body.get('name'))
        elif path == '/api/radio/where':
            out = set_where(gd, pr, edit, body['station'], body.get('where') or {})
        elif path == '/api/radio/tidy':
            out = {'gone': clear_unused(gd, pr)}
        else:
            return None
    except RadioProblem as e:
        return {'problem': str(e)}
    out = {k: v for k, v in out.items() if k in ('state', 'station', 'left_out', 'gone')}
    out.update(listing(gd, pr))
    return out
