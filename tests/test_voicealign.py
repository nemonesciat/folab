"""voicealign: timings carried from one take of some sounds to another take said at a different pace. Made sounds stand in
for voices: a run of vowels (a buzz through two resonances each) and hisses, the second take with every piece stretched
or squeezed differently and pauses let in; every piece's start should land within 30 ms (a lip file's frame is 33)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import numpy as np  # noqa: E402
import voicealign as VA  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


R = VA.RATE
rng = np.random.default_rng(3)
VOWELS = {'a': (750, 1200), 'i': (280, 2300), 'u': (320, 800), 'e': (500, 1900), 'o': (500, 900)}


def piece(kind, seconds, f0=120.0):
    n = int(seconds * R)
    if kind == 's':
        return rng.normal(0, 0.15, n) * np.hanning(n)
    if kind == ' ':
        return np.zeros(n)
    t = np.arange(n) / R
    buzz = sum(np.sin(2 * np.pi * f0 * k * t) / k for k in range(1, 30))
    spec = np.fft.rfft(buzz)
    f = np.fft.rfftfreq(n, 1 / R)
    shape = sum(1 / (1 + ((f - fc) / 90) ** 2) for fc in VOWELS[kind])
    return np.fft.irfft(spec * shape, n) * np.hanning(n) ** 0.3


def take(kinds, lengths):
    audio, timed, at = [], [], 0.0
    for k, s in zip(kinds, lengths):
        audio.append(piece(k, s))
        timed.append((k, at, at + s))
        at += s
    a = np.concatenate(audio)
    return a / np.abs(a).max() * 0.5, timed


kinds = list('asiusoe aiso eusa')
first = rng.uniform(0.08, 0.2, len(kinds))
second = first * rng.uniform(0.6, 1.6, len(kinds))
second[[k == ' ' for k in kinds]] += 0.3
a, ta = take(kinds, first)
b, tb = take(kinds, second)
got = VA.carry(ta, a, b)
err = np.array([abs(g[1] - w[1]) for g, w in zip(got, tb) if w[0] != ' '])   # a pause's start is where a sound fades: no mouth moves
check('every sound lands where the second take says it (within 30 ms)', err.max() < 0.03,
      '%.0f ms worst, %.0f ms median' % (err.max() * 1000, np.median(err) * 1000))
check('in order, and inside the second take', all(g1[1] <= g2[1] for g1, g2 in zip(got, got[1:])) and got[-1][2] <= len(b) / R + 1e-9)
check('a take laid on itself stays where it was', max(abs(g[1] - w[1]) for g, w in zip(VA.carry(ta, a, a), ta)) < 0.011)

