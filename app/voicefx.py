"""What FOLab does to a synthesized voice after the model speaks: a pitch change that keeps the voice's own character, a
livelier (or flatter) tune, and the sound of the game's own recordings. numpy only.

Pitch (`retune`): pitch-synchronous overlap-add. The voice's pitch is followed (`track`, a YIN-style search 5 ms at a
time), a mark is set at each beat of the voice (`marks`), and each beat's grain (two periods, windowed) is laid down again
at the new spacing. Length, and so every sound's timing (the lip file's), stays as it was; the mouth and throat (the
formants) stay too, which a plain speed-up doesn't do: that one moves them with the pitch, so a voice up a few semitones
sounded thin and one down sounded like a slow cassette.

Tune (`lively`): each moment's pitch is taken as so many semitones off the line's middle; times `lively` it is that much
further off. Kokoro speaks evenly: a bit over 1 reads as a person meaning what they say, under 1 as tired or sad.
`ends` bends the tune where a sentence ends: a question rises, a statement settles.

Sound (`master`): the game's voices measured (300 men's and 300 women's lines from Fallout - Voices1.bsa, 21 Nov 2026:
speech about -22 dB RMS, peaks about -4.5 dB, the spectrum in third octaves, `GAME_MEN`/`GAME_WOMEN`). Kokoro's had 10
to 16 dB more boom under 130 Hz and 4 to 9 dB less presence from 1 to 10 kHz: each line is brought to the game's
spectrum (smoothed, at most `MOST_EQ` dB either way) and to its loudness, peaks held under `PEAK`."""
import numpy as np

RATE = 24000
HOP = 120                       # pitch followed every 5 ms
F_LOW, F_HIGH = 60.0, 420.0     # voices' pitch range
BANDS = [50 * 2 ** (i / 3) for i in range(24)]      # 50 Hz .. 10 kHz, third octaves
# the game's spectrum on speech, dB per band about its mean (see the module's words)
GAME_MEN = [-13.2, -8.6, 1.7, 9.3, 11.4, 12.1, 14.3, 14.4, 13.0, 11.2, 8.2, 5.5, 3.2, 3.2, 1.7, -1.6, -3.8, -8.0, -8.6,
            -10.6, -10.8, -12.9, -14.1, -16.9]
GAME_WOMEN = [-17.1, -16.0, -12.2, -2.8, 9.0, 16.4, 16.2, 15.7, 15.5, 13.8, 10.2, 6.8, 6.4, 4.9, 2.6, -0.1, -3.0, -4.5,
              -8.3, -9.0, -9.9, -10.7, -11.1, -12.8]
LOUD = -22.0                    # the game's speech RMS, dB
PEAK = -3.0                     # no peak over this, dB
MOST_EQ = 9.0


# ---------- pitch ----------

def track(x, rate=RATE):
    """(f0 per HOP samples, 0 where unvoiced). A YIN-style search: the lag where the signal best matches itself."""
    w = int(rate / F_LOW * 2.2)
    lo, hi = int(rate / F_HIGH), int(rate / F_LOW)
    n = max(0, (len(x) - w) // HOP + 1)
    f0 = np.zeros(n)
    if n == 0:
        return f0
    energy = np.array([np.sqrt(np.mean(x[i * HOP:i * HOP + w] ** 2)) for i in range(n)])
    quiet = energy < energy.max() * 0.03
    size = 1 << int(np.ceil(np.log2(2 * w)))
    for i in range(n):
        if quiet[i]:
            continue
        seg = x[i * HOP:i * HOP + w]
        seg = seg - seg.mean()
        # difference function d(t) = sum (x_j - x_j+t)^2 over the first half, by FFT correlation
        half = w // 2
        a = seg[:half]
        corr = np.fft.irfft(np.fft.rfft(seg, size) * np.conj(np.fft.rfft(a, size)), size)[:hi + 2]
        cs = np.concatenate([[0], np.cumsum(seg ** 2)])
        e0 = cs[half]
        et = cs[np.arange(hi + 2) + half] - cs[np.arange(hi + 2)]
        d = e0 + et - 2 * corr
        d[0] = 0
        cm = d[1:] * np.arange(1, len(d)) / np.maximum(np.cumsum(d[1:]), 1e-12)   # cumulative mean normalised
        cm = np.concatenate([[1], cm])
        t = None
        for k in range(lo, hi):
            if cm[k] < 0.3 and cm[k] <= cm[k + 1]:
                t = k
                break
        if t is None:
            continue
        # parabola through the dip for a fraction of a sample
        a_, b_, c_ = cm[t - 1], cm[t], cm[t + 1]
        den = a_ - 2 * b_ + c_
        tt = t + (0.5 * (a_ - c_) / den if den else 0)
        f0[i] = rate / tt
    return _tidy(f0)


def _tidy(f0):
    """Median of five, octave slips folded back, voiced runs shorter than 25 ms dropped, gaps under 25 ms filled."""
    v = f0 > 0
    out = f0.copy()
    for i in np.nonzero(v)[0]:
        win = f0[max(0, i - 2):i + 3]
        win = win[win > 0]
        m = np.median(win)
        if out[i] > m * 1.7:
            out[i] /= 2
        elif out[i] < m / 1.7:
            out[i] *= 2
    runs = _runs(out > 0)
    for s, e, on in runs:
        if on and e - s < 5:
            out[s:e] = 0
    for s, e, on in _runs(out > 0):
        if not on and e - s < 5 and s > 0 and e < len(out):
            out[s:e] = np.linspace(out[s - 1], out[e], e - s + 2)[1:-1]
    return out


def _runs(mask):
    out, s = [], 0
    for i in range(1, len(mask) + 1):
        if i == len(mask) or mask[i] != mask[s]:
            out.append((s, i, bool(mask[s])))
            s = i
    return out


def marks(x, f0):
    """[(sample, period)]: one at each beat of the voice where it's voiced (on the beat's peak), every 5 ms where not."""
    out = []
    t = 0
    n = len(x)
    while t < n:
        i = min(len(f0) - 1, t // HOP) if len(f0) else 0
        f = f0[i] if len(f0) else 0
        if f > 0:
            p = int(RATE / f)
            # the beat's peak, near where the last one's period says it falls
            lo, hi = max(0, t - p // 4), min(n, t + p // 4 + 1)
            if out and out[-1][1] and hi > lo:
                t = lo + int(np.argmax(np.abs(x[lo:hi])))
            out.append((t, p))
            t += max(p, 1)
        else:
            out.append((t, 0))
            t += HOP
    return out


def retune(x, shift):
    """x with its pitch moved by `shift` semitones, a number or an array per HOP (as track gives), length kept."""
    x = np.asarray(x, dtype=np.float64)
    f0 = track(x)
    if not len(f0) or not (f0 > 0).any():
        return x.astype(np.float32)
    shift = np.broadcast_to(np.asarray(shift, dtype=np.float64), f0.shape) if np.ndim(shift) == 0 else np.asarray(shift)
    if np.allclose(shift, 0):
        return x.astype(np.float32)
    ms = marks(x, f0)
    at = np.array([m[0] for m in ms])
    out = np.zeros(len(x) + 4 * RATE // int(F_LOW))
    wsum = np.zeros_like(out)
    t = float(at[0])
    n = len(x)
    while t < n:
        k = int(np.argmin(np.abs(at - t)))
        c, p = ms[k]
        i = min(len(f0) - 1, int(t) // HOP)
        if p:
            ratio = 2 ** (shift[i] / 12.0)
            grain_p = p
            step = p / ratio
        else:
            grain_p = HOP
            step = HOP
        lo, hi = c - grain_p, c + grain_p
        win = np.hanning(2 * grain_p + 1)
        a, b = max(0, lo), min(n, hi + 1)
        g = x[a:b] * win[a - lo:a - lo + (b - a)]
        dst = int(round(t)) - (c - a)
        if dst >= 0 and dst + len(g) <= len(out):
            out[dst:dst + len(g)] += g
            wsum[dst:dst + len(g)] += win[a - lo:a - lo + (b - a)]
        t += max(step, 1.0)
    out = out[:n]
    wsum = wsum[:n]
    good = wsum > 0.25
    out[good] /= wsum[good]
    out[~good] *= 4 * np.maximum(wsum[~good], 0)       # fades where few grains reach (line ends)
    return out.astype(np.float32)


def contour(x, semitones=0.0, lively=1.0, ends=()):
    """Semitones per HOP: the voice's own tune times `lively` about its middle, plus `semitones`, plus each sentence end's
    bend (ends: [(second, kind)] with kind '?' rising, '.' settling, '!' a lift then a fall)."""
    f0 = track(np.asarray(x, dtype=np.float64))
    shift = np.full(len(f0), float(semitones))
    v = f0 > 0
    if v.sum() > 4 and lively != 1.0:
        st = 12 * np.log2(np.where(v, f0, 1) / np.median(f0[v]))
        shift[v] += (lively - 1.0) * np.clip(st[v], -8, 8)
    t = np.arange(len(f0)) * HOP / RATE
    for when, kind in ends:
        span = 0.35
        u = np.clip((t - (when - span)) / span, 0, 1)
        inside = (t <= when + 0.05)
        if kind == '?':
            shift += np.where(inside, 3.0 * u ** 1.5, 0)
        elif kind == '!':
            shift += np.where(inside, 1.5 * np.sin(np.pi * u), 0)
        elif kind == '.':
            shift += np.where(inside, -1.0 * u, 0)
    return shift


# ---------- sound ----------

def _spectrum(x):
    fr = 2048
    n = len(x) // fr
    if n < 2:
        return None
    frames = x[:n * fr].reshape(n, fr)
    rms = np.sqrt((frames ** 2).mean(axis=1)) + 1e-9
    db = 20 * np.log10(rms)
    sp = frames[db > db.max() - 30]
    s = (np.abs(np.fft.rfft(sp * np.hanning(fr), axis=1)) ** 2).mean(axis=0)
    f = np.fft.rfftfreq(fr, 1 / RATE)
    out = []
    for lo in BANDS:
        m = (f >= lo) & (f < lo * 2 ** (1 / 3))
        out.append(10 * np.log10(s[m].mean() + 1e-12))
    out = np.array(out)
    return out - out.mean()


def master(x, female=False):
    """x brought to the game's voices' spectrum and loudness."""
    x = np.asarray(x, dtype=np.float64)
    if not len(x):
        return x.astype(np.float32)
    have = _spectrum(x)
    if have is not None:
        want = np.array(GAME_WOMEN if female else GAME_MEN)
        gain = np.clip(want - have, -MOST_EQ, MOST_EQ)
        gain = np.convolve(np.pad(gain, 1, mode='edge'), [0.25, 0.5, 0.25], mode='valid')       # smoothed
        centres = np.array([b * 2 ** (1 / 6) for b in BANDS])
        size = 1 << int(np.ceil(np.log2(len(x) + 1024)))
        f = np.fft.rfftfreq(size, 1 / RATE)
        g_db = np.interp(np.log(np.maximum(f, 1)), np.log(centres), gain, left=gain[0] - 12, right=gain[-1])
        g_db[f < 70] -= 12 * (1 - f[f < 70] / 70)      # and the rumble under any voice out
        y = np.fft.irfft(np.fft.rfft(x, size) * 10 ** (g_db / 20), size)[:len(x)]
    else:
        y = x
    fr = 480
    n = max(1, len(y) // fr)
    frames = y[:n * fr].reshape(n, fr) if len(y) >= fr else y.reshape(1, -1)
    db = 20 * np.log10(np.sqrt((frames ** 2).mean(axis=1)) + 1e-9)
    speech = frames[db > db.max() - 30]
    loud = 20 * np.log10(np.sqrt((speech ** 2).mean()) + 1e-12)
    y = y * 10 ** ((LOUD - loud) / 20)
    # peaks over PEAK: a soft limiter (a gain that falls fast and recovers over 50 ms)
    ceiling = 10 ** (PEAK / 20)
    over = np.abs(y) / ceiling
    if over.max() > 1:
        need = np.maximum(over, 1.0)
        k = int(0.05 * RATE)
        env = np.array([need[i:i + k].max() for i in range(0, len(need), k // 4)]).repeat(k // 4)[:len(y)]
        env = np.convolve(np.pad(env, (k // 4, k // 4), mode='edge'), np.ones(k // 2) / (k // 2), mode='same')[k // 4:k // 4 + len(y)]
        y = y / np.maximum(env, 1.0)
        y = np.clip(y, -ceiling, ceiling)
    return y.astype(np.float32)
