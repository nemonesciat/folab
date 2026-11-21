"""Synthesized voices for dialogue lines: Kokoro speaks the words, lipwrite makes the .lip from the very sound timings
Kokoro spoke them with, and the line's .ogg and .lip go where the game looks for them (`voice_path`).

Needs onnxruntime, numpy and soundfile (FOLab.exe's Python carries them: packaging/build.py's voice packages); words
become sounds in g2p.py, FOLab's own. The plan: docs/voiced-dialogue-plan.md.

FOLab downloads nothing: the user downloads Kokoro's model (kokoro-v1.0.onnx from kokoro-onnx's model-files-v1.1
release: that export reports each sound's duration; the model-files-v1.0 one of the same name does not) and voices-v1.0.bin, by hand. `find_model` looks in
models/kokoro under FOLab's home, then Downloads, and copies them home.

How the game names a line's voice (fnv_decomp's TESResponse::BuildResponseFileName, BuildQuestTopicName,
VFDialogue::BuildVoiceFilePath):
    sound\\voice\\<the INFO's plugin>\\<voice type EDID>\\<quest>_<topic>_<INFO form id & 0xFFFFFF, %08X>_<response>.ogg
quest and topic are editor IDs; together over 25 letters, the quest is cut to 10 and the topic to 15 plus what the quest
left. The game's voices are Ogg Vorbis, mono, 24,000 a second, as Kokoro speaks."""
import os
import shutil

import lipwrite

MODEL = 'kokoro-v1.0.onnx'
VOICES = 'voices-v1.0.bin'
RATE = 24000
# Marks Kokoro speaks as tokens of their own: length gives its time to the sound before, stress to the sound after.
LENGTH, STRESS = 'ːˑ', 'ˈˌ'
# Kokoro's one-letter gliding vowels, as the two sounds the mouth makes
GLIDES = {'A': ('e', 'ɪ'), 'I': ('a', 'ɪ'), 'O': ('o', 'ʊ'), 'W': ('a', 'ʊ'), 'Y': ('ɔ', 'ɪ'), 'Q': ('ə', 'ʊ')}


def home():
    return os.environ.get('FOLAB_HOME') or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


MISSING = ("Download kokoro-v1.0.onnx (from the model-files-v1.1 release on kokoro-onnx's GitHub page"
           ': that one reports '
           'how long each sound lasts) and voices-v1.0.bin, and leave them in your Downloads folder. FOLab copies them '
           'from there the first time it voices a line.')


def find_model(downloads=None, copy=True):
    """(model path, voices path) in FOLab's home, copied there from Downloads if need be; None if either is missing.
    copy=False only looks (and doesn't open the model to check it)."""
    keep = os.path.join(home(), 'models', 'kokoro')
    downloads = downloads or os.path.join(os.path.expanduser('~'), 'Downloads')
    found = []
    for name in (MODEL, VOICES):
        here = os.path.join(keep, name)
        if not os.path.isfile(here):
            there = os.path.join(downloads, name)
            if not os.path.isfile(there):
                return None
            if not copy:
                found.append(there)
                continue
            if name == MODEL and not _has_durations(there):
                return None
            os.makedirs(keep, exist_ok=True)
            shutil.copyfile(there, here)
        found.append(here)
    return tuple(found)


def _has_durations(path):
    import onnxruntime
    s = onnxruntime.InferenceSession(path, providers=['CPUExecutionProvider'])
    return 'duration' in {o.name for o in s.get_outputs()}


class Kokoro:
    """Kokoro run by FOLab itself: the model through onnxruntime, sounds from g2p (FOLab's own words to sounds; the
    kokoro-onnx package isn't used, since it loads espeak-ng and phonemizer, which are GPL). Each sound is a token of
    Kokoro's table (kokorovocab.json, from Kokoro's own config); the model gives the audio and how many frames each
    token lasted (its 'duration' output), which places every sound in time."""

    MOST = 500                      # tokens Kokoro takes at once (510 less the pads): longer lines go a sentence at a time

    def __init__(self, model, voices):
        import json
        import numpy as np
        import onnxruntime
        self.np = np
        self.sess = onnxruntime.InferenceSession(model, providers=['CPUExecutionProvider'])
        names = {o.name for o in self.sess.get_outputs()}
        if 'duration' not in names:
            raise RuntimeError(MISSING)
        self.inputs = {i.name: i.type for i in self.sess.get_inputs()}
        self.voices = np.load(voices)
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kokorovocab.json'), encoding='utf-8') as f:
            self.vocab = json.load(f)

    def voice_names(self):
        return sorted(self.voices.files)

    def style(self, voice, n):
        """A voice's style for n tokens: one of Kokoro's, or a blend of them (`blend`)."""
        np = self.np
        return sum(w * np.asarray(self.voices[name][n], dtype=np.float32) for name, w in blend(voice))

    def _one(self, sounds, voice, speed):
        np = self.np
        tokens = [self.vocab[c] for c in sounds]
        style = self.style(voice, len(tokens))
        ids = 'input_ids' if 'input_ids' in self.inputs else 'tokens'
        feed = {ids: np.array([[0] + tokens + [0]], dtype=np.int64), 'style': np.asarray(style, dtype=np.float32),
                'speed': np.array([speed], dtype=np.int32 if 'int' in self.inputs['speed'] else np.float32)}
        out = dict(zip([o.name for o in self.sess.get_outputs()], self.sess.run(None, feed)))
        audio = np.asarray(out.get('waveform', out.get('audio'))).ravel().astype(np.float32)
        dur = np.asarray(out['duration']).ravel().astype(np.float64)
        edges = np.round(np.concatenate([[0], np.cumsum(dur)]) * (len(audio) / dur.sum())).astype(np.int64)
        # token k of sounds is the model's k + 1 (a pad leads)
        timed = [(c, edges[k + 1] / RATE, edges[k + 2] / RATE) for k, c in enumerate(sounds)]
        return audio, timed

    def create(self, sounds, voice, speed=1.0, pause=0.15):
        """(audio, [(sound, start, end)]) for a string of Kokoro's sound letters."""
        np = self.np
        sounds = ''.join(c for c in sounds if c in self.vocab)
        parts, at = [], 0
        while sounds:
            if len(sounds) <= self.MOST:
                cut = len(sounds)
            else:                       # at the last sentence end (or comma, or space) that fits
                window = sounds[:self.MOST]
                cut = max(window.rfind(m) for m in '.!?') + 1 or max(window.rfind(m) for m in ',;:') + 1 or window.rfind(' ') + 1 or self.MOST
            parts.append(sounds[:cut].strip())
            sounds = sounds[cut:].strip()
        audio, timed = [], []
        for n, part in enumerate(parts):
            if n:
                gap = np.zeros(int(pause * RATE), dtype=np.float32)
                audio.append(gap)
                at += len(gap)
            a, t = self._one(part, voice, speed)
            timed += [(c, s + at / RATE, e + at / RATE) for c, s, e in t]
            audio.append(a)
            at += len(a)
        return np.concatenate(audio), timed


_KOKORO = {}


def kokoro():
    if 'k' not in _KOKORO:
        paths = find_model()
        if not paths:
            raise FileNotFoundError(MISSING)
        _KOKORO['k'] = Kokoro(*paths)
    return _KOKORO['k']


# ---------- Chatterbox: the more human voice, when the user has it ----------
# Chatterbox (Resemble AI, MIT) acts a line out, with a dial for how much feeling (exaggeration). It needs torch and a
# graphics card: gigabytes FOLab.exe doesn't carry, so it lives in a folder of its own (its own Python in venv\, the
# model's files in hf\), which FOLab runs chatterbox_run.py in. It copies the voice of a clip: each character's clip is
# their Kokoro voice (`reference`), so a character keeps the voice chosen for them. Its sound reports no timings:
# voicealign carries Kokoro's across for the lip file. The user liked it best at the calmer settings (21 Nov 2026).
CALM = {'exaggeration': 0.45, 'cfg': 0.25}
REF_TEXT = ("I've walked this beach every morning for twenty years, and the sea still finds something new to leave me. "
            "Most days it's driftwood and bottles. Some days, it's people. You were one of the lucky ones.")


def chatterbox_folder():
    """The Chatterbox folder FOLab uses: FOLAB_CHATTERBOX, else folab_settings.json's 'chatterbox', else
    chatterbox\\ under FOLab's home; one with venv\\Scripts\\python.exe and chatterbox in it, else None."""
    import json
    tries = [os.environ.get('FOLAB_CHATTERBOX')]
    try:
        with open(os.path.join(home(), 'folab_settings.json'), encoding='utf-8') as f:
            tries.append(json.load(f).get('chatterbox'))
    except (OSError, ValueError):
        pass
    tries.append(os.path.join(home(), 'chatterbox'))
    for t in tries:
        if t and os.path.isfile(os.path.join(t, 'venv', 'Scripts', 'python.exe')) and \
                os.path.isdir(os.path.join(t, 'venv', 'Lib', 'site-packages', 'chatterbox')):
            return t
    return None


class Chatterbox:
    """chatterbox_run.py running in the Chatterbox folder's Python, kept going between lines (loading takes a while)."""

    def __init__(self, folder):
        import subprocess
        env = dict(os.environ, HF_HOME=os.path.join(folder, 'hf'), PYTHONIOENCODING='utf-8')
        for k in ('PYTHONPATH', 'PYTHONHOME'):
            env.pop(k, None)
        self.log = open(os.path.join(folder, 'folab-run.log'), 'a', encoding='utf-8')
        self.proc = subprocess.Popen(
            [os.path.join(folder, 'venv', 'Scripts', 'python.exe'), '-I',
             os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chatterbox_run.py')],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log, env=env, cwd=folder,
            text=True, encoding='utf-8', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        first = self._answer()
        if not first.get('ready'):
            raise RuntimeError('Chatterbox did not start: see %s' % self.log.name)
        self.device = first.get('device')

    def _answer(self):
        import json
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError('Chatterbox stopped: see %s' % self.log.name)
        return json.loads(line)

    def say(self, text, ref, out, exaggeration=CALM['exaggeration'], cfg=CALM['cfg']):
        import json
        self.proc.stdin.write(json.dumps({'text': text, 'ref': ref, 'out': out, 'exaggeration': exaggeration,
                                          'cfg': cfg}) + '\n')
        self.proc.stdin.flush()
        a = self._answer()
        if 'error' in a:
            raise RuntimeError('Chatterbox: ' + a['error'])
        return a['seconds']

    def alive(self):
        return self.proc.poll() is None


def chatterbox():
    c = _KOKORO.get('cb')
    if c is None or not c.alive():
        folder = chatterbox_folder()
        if not folder:
            raise FileNotFoundError('No Chatterbox folder found.')
        c = _KOKORO['cb'] = Chatterbox(folder)
    return c


def reference(voice, speed=1.0, pitch=0.0, lively=1.0):
    """A clip of a Kokoro voice for Chatterbox to copy, made once per voice and kept in models\\refs under FOLab's home."""
    import hashlib
    import soundfile
    import voicefx
    key = hashlib.sha1(('%s|%.3f|%.3f|%.3f|%s' % (voice, speed, pitch, lively, REF_TEXT)).encode('utf-8')).hexdigest()[:16]
    path = os.path.join(home(), 'models', 'refs', key + '.wav')
    if not os.path.isfile(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        a, _ = speak(REF_TEXT, voice, speed, pitch, lively)
        soundfile.write(path, voicefx.master(a, is_female(voice)), RATE)
    return path


def speak_chatterbox(text, voice='am_michael', speed=1.0, pitch=0.0, lively=1.0, exaggeration=None, cfg=None):
    """(audio, [(sound, start, end)]) as speak, acted by Chatterbox in the voice's likeness; timings carried from Kokoro
    saying the same words (voicealign)."""
    import tempfile
    import g2p
    import soundfile
    import voicealign
    ref = reference(voice, speed, pitch, lively)
    fd, tmp = tempfile.mkstemp(suffix='.wav')
    os.close(fd)
    try:
        chatterbox().say(text, ref, tmp, CALM['exaggeration'] if exaggeration is None else exaggeration,
                         CALM['cfg'] if cfg is None else cfg)
        audio, _r = soundfile.read(tmp, dtype='float32')
    finally:
        os.remove(tmp)
    known, timed = kokoro().create(g2p.phonemes(text), voice, speed=speed)
    return audio, merge_marks(voicealign.carry(timed, known, audio))


def cut_name(quest, topic):
    """The game's quest_topic part of a voice file's name."""
    if len(quest) + len(topic) > 25:
        topic_most = 15
        if len(quest) > 10:
            quest = quest[:10]
        else:
            topic_most += 10 - len(quest)
        topic = topic[:topic_most]
    return '%s_%s' % (quest, topic)


def voice_path(plugin, voice_type, quest, topic, info_id, response):
    """The game's path for one response of an INFO, without extension (add .ogg / .lip), lower case as the game's."""
    name = '%s_%08X_%u' % (cut_name(quest, topic), info_id & 0xFFFFFF, response)
    return os.path.join('sound', 'voice', plugin, voice_type, name).lower()


def merge_marks(timed):
    """[(sound, start, end)] with Kokoro's length and stress marks folded into their sounds, spaces and stops kept as
    silence."""
    out = []
    carry = None
    for ph, start, end in timed:
        if ph in LENGTH and out:
            s, a, _ = out[-1]
            out[-1] = (s, a, end)
        elif ph in STRESS:
            carry = start if carry is None else carry
        else:
            if carry is not None:
                start, carry = carry, None
            if ph in GLIDES:            # a gliding vowel: its first sound, then its second
                mid = (start + end) / 2
                out += [(GLIDES[ph][0], start, mid), (GLIDES[ph][1], mid, end)]
            else:
                out.append((ph, start, end))
    return out


def blend(voice):
    """[(Kokoro voice, weight)] for a voice: 'am_onyx', or a blend 'am_onyx*0.6+am_michael*0.4' (weights made to add to
    1). A blend is a voice of its own: two of Kokoro's mixed sound like neither, so no two characters need share one."""
    parts = []
    for p in str(voice).split('+'):
        name, _, w = p.strip().partition('*')
        parts.append((name.strip(), float(w) if w else 1.0))
    total = sum(w for _, w in parts if w > 0) or 1.0
    return [(n, w / total) for n, w in parts if w > 0]


def is_female(voice):
    """Whether a voice is a woman's: its first (largest) part's name says (af_, bf_)."""
    first = max(blend(voice), key=lambda p: p[1])[0]
    return first[1:2] == 'f'


# Kokoro barely stops at a comma or between sentences, which is most of why it sounds hurried (the user, 21 Nov 2026):
# seconds of silence added at each mark, more when the voice is slower. Not after the last word.
PAUSES = {'.': 0.3, '?': 0.32, '!': 0.3, ',': 0.12, ';': 0.2, ':': 0.2, '—': 0.2, '…': 0.45}


def breathe(audio, timed, speed=1.0):
    """audio and its timings with PAUSES let in at the marks (in the middle of the mark's own short silence)."""
    import numpy as np
    last = max((i for i, (p, _a, _b) in enumerate(timed) if p not in PAUSES and p.strip()), default=-1)
    cuts = [(int((a + b) / 2 * RATE), PAUSES[p] / max(speed, 0.3)) for i, (p, a, b) in enumerate(timed)
            if p in PAUSES and i < last]
    if not cuts:
        return audio, timed
    parts, at, added = [], 0, []
    for cut, sec in cuts:
        cut = min(max(cut, at), len(audio))
        parts += [audio[at:cut], np.zeros(int(sec * RATE), dtype=audio.dtype)]
        added.append((cut / RATE, sec))
        at = cut
    parts.append(audio[at:])

    def moved(t):
        return t + sum(s for c, s in added if c <= t + 1e-9)
    return np.concatenate(parts), [(p, moved(a), moved(b)) for p, a, b in timed]


def speak(text, voice='am_michael', speed=1.0, pitch=0.0, lively=1.0):
    """(audio float32 mono at RATE, [(sound, start, end)]) for the words. pitch in semitones and lively (how far the tune
    goes from its middle: 1 as Kokoro speaks) are voicefx's, which keep the length and so every sound's time; each
    sentence end bends the tune (a question rises)."""
    import g2p
    import voicefx
    audio, timed = kokoro().create(g2p.phonemes(text), voice, speed=speed)
    audio, timed = breathe(audio, timed, speed)
    ends = [(a, p) for p, a, _b in timed if p in '.?!']
    if pitch or lively != 1.0 or ends:
        audio = voicefx.retune(audio, voicefx.contour(audio, pitch, lively, ends))
    return audio, merge_marks(timed)


def write_line(base, text, voice='am_michael', speed=1.0, pitch=0.0, lively=1.0, engine='kokoro', feeling=None):
    """Writes base + '.ogg' and base + '.lip', sounding as the game's own voices do (voicefx.master); returns seconds
    spoken. engine 'chatterbox' acts it out (feeling: Chatterbox's exaggeration, None for CALM's)."""
    import soundfile
    import voicefx
    if engine == 'chatterbox':
        audio, timed = speak_chatterbox(text, voice, speed, pitch, lively, exaggeration=feeling)
    else:
        audio, timed = speak(text, voice, speed, pitch, lively)
    audio = voicefx.master(audio, is_female(voice))
    os.makedirs(os.path.dirname(base), exist_ok=True)
    soundfile.write(base + '.ogg', audio, RATE, format='OGG', subtype='VORBIS')
    seconds = len(audio) / RATE
    with open(base + '.lip', 'wb') as f:
        f.write(lipwrite.write(lipwrite.from_timeline(timed, seconds=seconds)))
    return seconds


if __name__ == '__main__':
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else 'voicetest'
    print('%.2f s' % write_line(os.path.abspath(out), ' '.join(sys.argv[2:]) or 'Aloha, stranger.'))
