"""New Vegas lip-sync files (.lip): read, write, and make from timed phonemes.

Learnt from the game's own files (every .lip in its voice archives) and fnv_decomp's names for how the game reads them
(LipSyncAnimation, BS_FACEGEN_PHONEME). Our own code.

File: a 12-byte header, three int32: version 1, the payload's size plus 16, flags (1: the payload is packed). Packed,
each non-zero byte stands for itself and a zero byte is followed by a uint16 count of zero bytes it stands for (a lone
zero is 00 01 00). An old form without the header (version not 1) is packed after one skipped byte; the game's own
files never use it, so this module only reads it.

Payload: int32 frame count (the game refuses over 1,000,000), int32 starting frame (`iStartingFrame`, 0 to -27 in
the game's files: the face eases into the first frame over the longer of 0.2 s and -start/30 s; the game's files put
it about 4 frames before the first sound, `LEAD_IN`), then per frame 16 float32 phoneme weights (PHONEMES order) followed by 17 float32 modifiers (MODIFIERS
order; the game scales the last three, the head's turns, by settings as it reads). The game plays one frame every
1/30 s (ApplyToAnimationData: 0.033333335 per keyframe). Field names as nv-rs's port has them from the Xbox PDB.

Run `py -3 app/lipwrite.py` to decode and re-encode every .lip in the game's archives and compare bytes."""
import struct

FPS = 30
PHONEMES = ('Aah', 'BigAah', 'BMP', 'ChJSh', 'DST', 'Eee', 'Eh', 'FV', 'I', 'K', 'N', 'Oh', 'OohQ', 'R', 'Th', 'W')
# FaceGen's modifier order; the game's head .tri names the same morphs. Lip sync only needs PHONEMES.
MODIFIERS = ('BlinkLeft', 'BlinkRight', 'BrowDownLeft', 'BrowDownRight', 'BrowInLeft', 'BrowInRight', 'BrowUpLeft',
             'BrowUpRight', 'LookDown', 'LookLeft', 'LookRight', 'LookUp', 'SquintLeft', 'SquintRight', 'HeadPitch',
             'HeadRoll', 'HeadYaw')
NP, NM = len(PHONEMES), len(MODIFIERS)
FRAME = struct.Struct('<%df' % (NP + NM))
SIZE_EXTRA = 16      # the header's size is always the payload's plus 16 in the game's files
START = -4           # iStartingFrame of most game files
LEAD_IN = 4


class Lip:
    """frames: list of (phonemes tuple of 16, modifiers tuple of 17) floats; start: iStartingFrame."""

    def __init__(self, frames=None, start=START):
        self.frames = frames or []
        self.start = start

    @property
    def seconds(self):
        return len(self.frames) / FPS


def unpack_zeros(data):
    out = bytearray()
    i, n = 0, len(data)
    while i < n:
        b = data[i]
        if b:
            out.append(b)
            i += 1
        else:
            out += bytes(struct.unpack_from('<H', data, i + 1)[0])
            i += 3
    return bytes(out)


def pack_zeros(data):
    out = bytearray()
    i, n = 0, len(data)
    while i < n:
        if data[i]:
            j = i
            while j < n and data[j]:
                j += 1
            out += data[i:j]
            i = j
        else:
            j = i
            while j < n and not data[j] and j - i < 0xFFFF:
                j += 1
            out += b'\0' + struct.pack('<H', j - i)
            i = j
    return bytes(out)


def payload_of(data):
    version, size, flags = struct.unpack_from('<iii', data, 0)
    if version != 1:
        return unpack_zeros(data[1:])
    body = data[12:]
    return unpack_zeros(body) if flags & 1 else body[:size - SIZE_EXTRA]


def read(data):
    p = payload_of(data)
    count, start = struct.unpack_from('<ii', p, 0)
    frames = []
    for k in range(count):
        f = FRAME.unpack_from(p, 8 + k * FRAME.size)
        frames.append((f[:NP], f[NP:]))
    return Lip(frames, start)


def payload(lip):
    out = bytearray(struct.pack('<ii', len(lip.frames), lip.start))
    for ph, mod in lip.frames:
        out += FRAME.pack(*ph, *mod)
    return bytes(out)


def write(lip):
    p = payload(lip)
    return struct.pack('<iii', 1, len(p) + SIZE_EXTRA, 1) + pack_zeros(p)


# --- making one from timed phonemes ---------------------------------------------------------------------------------

# Speech sounds (ARPAbet, as most aligners and synthesizers' lexicons give them, stress digits dropped) to the game's
# mouth shapes, with a weight. Silence and pauses map to nothing.
ARPABET = {
    'AA': ('BigAah', 1.0), 'AE': ('Aah', 1.0), 'AH': ('Aah', 0.8), 'AO': ('Oh', 1.0), 'AW': ('BigAah', 1.0),
    'AY': ('BigAah', 0.9), 'EH': ('Eh', 1.0), 'ER': ('R', 0.9), 'EY': ('Eh', 0.9), 'IH': ('I', 1.0), 'IY': ('Eee', 1.0),
    'OW': ('Oh', 1.0), 'OY': ('Oh', 1.0), 'UH': ('OohQ', 0.8), 'UW': ('OohQ', 1.0),
    'B': ('BMP', 1.0), 'P': ('BMP', 1.0), 'M': ('BMP', 1.0), 'F': ('FV', 1.0), 'V': ('FV', 1.0),
    'CH': ('ChJSh', 1.0), 'JH': ('ChJSh', 1.0), 'SH': ('ChJSh', 1.0), 'ZH': ('ChJSh', 1.0),
    'D': ('DST', 0.9), 'S': ('DST', 1.0), 'T': ('DST', 0.9), 'Z': ('DST', 1.0),
    'TH': ('Th', 1.0), 'DH': ('Th', 0.9), 'K': ('K', 0.9), 'G': ('K', 0.9), 'NG': ('K', 0.8), 'HH': ('K', 0.4),
    'N': ('N', 0.9), 'L': ('N', 0.8), 'Y': ('Eee', 0.6), 'R': ('R', 1.0), 'W': ('W', 1.0),
}

# IPA (what espeak-ng based synthesizers such as Kokoro and Piper speak in) to the same shapes; longest match first.
IPA = {
    'ɑ': ('BigAah', 1.0), 'a': ('BigAah', 0.9), 'æ': ('Aah', 1.0), 'ʌ': ('Aah', 0.8), 'ə': ('Aah', 0.5),
    'ɐ': ('Aah', 0.6), 'ɔ': ('Oh', 1.0), 'o': ('Oh', 1.0), 'ɒ': ('Oh', 0.9), 'ɛ': ('Eh', 1.0), 'e': ('Eh', 0.9),
    'ɜ': ('R', 0.8), 'ɚ': ('R', 0.8), 'ɝ': ('R', 0.9), 'ɪ': ('I', 1.0), 'i': ('Eee', 1.0), 'ʊ': ('OohQ', 0.8),
    'u': ('OohQ', 1.0), 'ᵻ': ('I', 0.8), 'ɨ': ('I', 0.8), 'ᵊ': ('Aah', 0.4),
    # Kokoro's one-letter gliding vowels (voicegen splits them into their two halves first; these are for a lone one)
    'A': ('Eh', 0.9), 'I': ('BigAah', 0.9), 'O': ('Oh', 1.0), 'W': ('BigAah', 0.9), 'Y': ('Oh', 1.0), 'Q': ('Oh', 0.9),
    'b': ('BMP', 1.0), 'p': ('BMP', 1.0), 'm': ('BMP', 1.0), 'f': ('FV', 1.0), 'v': ('FV', 1.0),
    'tʃ': ('ChJSh', 1.0), 'dʒ': ('ChJSh', 1.0), 'ʃ': ('ChJSh', 1.0), 'ʒ': ('ChJSh', 1.0), 'ʧ': ('ChJSh', 1.0),
    'ʤ': ('ChJSh', 1.0), 'd': ('DST', 0.9), 's': ('DST', 1.0), 't': ('DST', 0.9), 'z': ('DST', 1.0),
    'ɾ': ('DST', 0.6), 'ʔ': ('K', 0.3), 'θ': ('Th', 1.0), 'ð': ('Th', 0.9), 'k': ('K', 0.9), 'ɡ': ('K', 0.9),
    'g': ('K', 0.9), 'ŋ': ('K', 0.8), 'h': ('K', 0.4), 'x': ('K', 0.6), 'n': ('N', 0.9), 'l': ('N', 0.8),
    'ɫ': ('N', 0.8), 'j': ('Eee', 0.6), 'ɹ': ('R', 1.0), 'r': ('R', 1.0), 'w': ('W', 1.0),
}
IPA_SKIP = set('ˈˌːˑ.‿ ,;:!?—–-"\'()[]{}' + '̩̯̃')


def shape_of(sound):
    """(phoneme index, weight) for an ARPAbet or IPA sound, or None for silence and anything unknown."""
    s = sound.strip()
    a = ARPABET.get(s.upper().rstrip('012'))
    if a is None:
        a = IPA.get(s)
    if a is None:
        return None
    return PHONEMES.index(a[0]), a[1]


def ipa_sounds(text):
    """Splits an IPA string into sounds the IPA table knows (longest match first); stress and length marks dropped."""
    out, i = [], 0
    while i < len(text):
        if text[i] in IPA_SKIP:
            i += 1
            continue
        two = text[i:i + 2]
        if two in IPA:
            out.append(two)
            i += 2
        else:
            out.append(text[i])
            i += 1
    return out


def from_timeline(timeline, seconds=None, ease=0.06, keep_modifiers=None):
    """A Lip from [(sound, start, end), ...] in seconds (ARPAbet or IPA sounds; silence as '' or 'sil').

    Each sound's shape rises over `ease` seconds before its middle and falls after, so neighbours blend as speech does;
    at each frame every shape takes the strongest weight it has from any sound then. `seconds` pads to the audio's
    length (the game ends the face movement with the file). keep_modifiers: optional list of 17-tuples, one a frame."""
    end = max([e for _, _, e in timeline] + [seconds or 0])
    count = max(1, int(round(end * FPS)))
    keys = []
    for sound, start, stop in timeline:
        sh = shape_of(sound) if sound and sound.lower() not in ('sil', 'sp', 'pau') else None
        if sh:
            keys.append((sh[0], sh[1], start, stop))
    frames = []
    zero_mod = (0.0,) * NM
    for k in range(count):
        t = k / FPS
        w = [0.0] * NP
        for idx, weight, start, stop in keys:
            a, b = start - ease, stop + ease
            if t <= a or t >= b:
                continue
            mid0, mid1 = min(start + ease, (start + stop) / 2), max(stop - ease, (start + stop) / 2)
            if t < mid0:
                f = (t - a) / (mid0 - a)
            elif t > mid1:
                f = (b - t) / (b - mid1)
            else:
                f = 1.0
            f = f * f * (3 - 2 * f)            # smooth step
            w[idx] = max(w[idx], weight * f)
        mod = keep_modifiers[k] if keep_modifiers and k < len(keep_modifiers) else zero_mod
        frames.append((tuple(w), tuple(mod)))
    first = next((k for k, f in enumerate(frames) if max(f[0]) > 0.01), 0)
    return Lip(frames, -(first + LEAD_IN))


def recheck(data_dir=None, report=print):
    """Decodes and re-encodes every .lip in the game's archives; returns (count, mismatches)."""
    import os
    import bsa
    import gamedata
    d = data_dir or gamedata.find_data_dir()
    count, bad = 0, []
    for name in sorted(os.listdir(d)):
        if not name.lower().endswith('.bsa'):
            continue
        a = bsa.Archive(os.path.join(d, name))
        try:
            lips = [p for p in a.files if p.endswith('.lip')]
            for p in lips:
                data = a.read(p)
                count += 1
                try:
                    again = write(read(data))
                except Exception as e:      # noqa: BLE001 - reported, not hidden
                    bad.append((name, p, repr(e)))
                    continue
                if again != data:
                    bad.append((name, p, 'differs'))
            if lips:
                report('%s: %d lip files' % (name, len(lips)))
        finally:
            a.close()
    return count, bad


if __name__ == '__main__':
    import sys
    sys.path.insert(0, __import__('os').path.dirname(__file__))
    n, bad = recheck()
    print('%d lip files, %d differ' % (n, len(bad)))
    for b in bad[:30]:
        print('  ', *b)
    sys.exit(1 if bad else 0)
