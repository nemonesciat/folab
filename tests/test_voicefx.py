"""voicefx: a voice's pitch moved without its length changing (so a lip file's timings still hold), a livelier tune that
goes further from its middle, and a line brought to the game's voices' loudness with no peak over the ceiling. A made
voice stands in for Kokoro: a buzz at 120 Hz through two vowel-like resonances, gliding as speech does. Also voicegen's
blends: weights made to add to 1, a woman's voice told by its largest part."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import numpy as np  # noqa: E402
import voicefx as FX  # noqa: E402
import voicegen  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


R = FX.RATE


def made_voice(seconds=2.0, f_from=110.0, f_to=135.0):
    t = np.arange(int(seconds * R)) / R
    f = np.linspace(f_from, f_to, len(t))
    phase = 2 * np.pi * np.cumsum(f) / R
    buzz = sum(np.sin(k * phase) / k for k in range(1, 40))
    # two resonances (a vowel), the same whatever the pitch
    out = np.zeros_like(buzz)
    for fc, bw in ((700, 110), (1200, 140)):
        r = np.exp(-np.pi * bw / R)
        a1, a2 = -2 * r * np.cos(2 * np.pi * fc / R), r * r
        y = np.zeros_like(buzz)
        for i in range(2, len(buzz)):
            y[i] = buzz[i] - a1 * y[i - 1] - a2 * y[i - 2]
        out += y
    out *= np.minimum(1, np.minimum(t, t[-1] - t) / 0.05)
    return (out / np.abs(out).max() * 0.5).astype(np.float32)


def median_f0(x):
    f = FX.track(np.asarray(x, dtype=np.float64))
    return float(np.median(f[f > 0])) if (f > 0).any() else 0.0


v = made_voice()
f0 = median_f0(v)
check('the made voice is followed at its pitch', 115 < f0 < 130, round(f0, 1))
for st in (-3, 3):
    up = FX.retune(v, st)
    want = f0 * 2 ** (st / 12)
    got = median_f0(up)
    check('%+d semitones: pitch moved, length kept' % st, len(up) == len(v) and abs(got - want) < want * 0.03, (round(got, 1), round(want, 1)))


def band_peak(x):
    s = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    f = np.fft.rfftfreq(len(x), 1 / R)
    m = (f > 500) & (f < 1500)
    return float(f[m][np.argmax(s[m])])


up = FX.retune(v, 4)
check('the vowel stays where it was (a speed-up would move it a third)', abs(band_peak(up) - band_peak(v)) < 120,
      (band_peak(v), band_peak(up)))

wide = made_voice(2.0, 100, 150)
c = FX.contour(wide, 0, 1.6)
check('livelier: the tune goes further from its middle', np.ptp(c[c != 0]) > 1.5, round(float(np.ptp(c[c != 0])), 2))
q = FX.contour(v, 0, 1.0, [(1.8, '?')])
t = np.arange(len(q)) * FX.HOP / R
check('a question rises at its end', q[(t > 1.7) & (t < 1.8)].mean() > 1.0 and abs(q[t < 1.2]).max() < 1e-9)

m = FX.master(v * 0.05)
fr = 480
frames = m[:len(m) // fr * fr].reshape(-1, fr)
db = 20 * np.log10(np.sqrt((frames ** 2).mean(axis=1)) + 1e-9)
loud = 20 * np.log10(np.sqrt((frames[db > db.max() - 30] ** 2).mean()))
check('brought to the game\'s loudness, peaks under the ceiling',
      abs(loud - FX.LOUD) < 1.5 and 20 * np.log10(np.abs(m).max()) <= FX.PEAK + 0.01, (round(loud, 1), round(20 * np.log10(np.abs(m).max()), 2)))

check('a blend\'s weights add to 1', voicegen.blend('am_onyx*3+bm_george*1') == [('am_onyx', 0.75), ('bm_george', 0.25)])
check('one voice is a blend of one', voicegen.blend('af_heart') == [('af_heart', 1.0)])
check('a woman\'s voice by its largest part', voicegen.is_female('am_onyx*0.3+af_heart*0.7') and not voicegen.is_female('am_onyx'))

# pauses: silence let in at a mark, timings after it moved by as much, none after the last word
aud = np.ones(R, dtype=np.float32)
timed = [('h', 0.0, 0.2), ('i', 0.2, 0.4), ('.', 0.4, 0.45), ('j', 0.45, 0.8), ('?', 0.8, 0.85)]
out, t2 = voicegen.breathe(aud, timed, 1.0)
gap = voicegen.PAUSES['.']
check('a pause after the sentence, none after the last word', abs(len(out) / R - (1 + gap)) < 1e-3, len(out) / R)
check('what follows moves by the pause, what comes before stays',
      t2[0] == timed[0] and abs(t2[3][1] - (0.45 + gap)) < 1e-6 and abs(t2[2][2] - (0.45 + gap)) < 1e-6, t2)
check('a slower voice pauses longer', len(voicegen.breathe(aud, timed, 0.8)[0]) > len(out))
