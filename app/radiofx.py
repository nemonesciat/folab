"""A voice as it comes out of an old valve radio: what makes a station's talk sound broadcast, not read out in a quiet room.

The user, 22 Nov 2026, of the first voiced drafts: Radio Atoll "sounds like a generic female assistant at a kiosk", Haixin
Dongtai "way too artificial and clean". The voice makers give studio-clean speech, full range, no room, no noise; a
broadcast of the 1950s that Waikiki's stations stand in for is none of those:
- the band of an AM set: little under ~250 Hz or over ~4.5 kHz (`LOW`, `HIGH`), with the hump a small speaker has in
  the middle (`HUMP`);
- a valve stage driven a little hard: soft clipping that thickens the sound (`DRIVE`);
- a broadcast limiter's evenness: quiet syllables brought up (`SQUEEZE`);
- the carrier under it: a low hiss and now and then a crackle (`HISS`, `CRACKLE`), steady through the pauses, so the
  line never drops to dead silence the way a file does;
- a slight wander of the pitch, as a turntable or tape the station plays from (`WOW`).

`air(x)` does all of it to a mono float clip at voicefx.RATE and brings it to the game's speech level (voicefx.LOUD),
with the same length, so the .lip made from the dry take still fits. `strength` 0..1 scales the whole effect.
numpy only, like voicefx."""
import numpy as np

RATE = 24000
LOW, HIGH = 250.0, 4500.0        # Hz: the band an AM set gives
HUMP = (1800.0, 4.0)             # Hz, dB: a small speaker's middle
DRIVE = 2.2                      # how hard the valve stage is pushed
SQUEEZE = 0.55                   # 0 nothing, 1 every syllable as loud as the loudest
HISS = -46.0                     # dB under full scale
CRACKLE = 1.5                    # clicks a second, on average
WOW = (0.6, 0.0025)              # Hz, depth (share of the pitch)
LOUD = -22.0                     # the game's speech, dB RMS (voicefx.LOUD)
PEAK = -3.0


def _band(x, rate, low, high, hump):
    n = len(x)
    f = np.fft.rfftfreq(n, 1.0 / rate)
    X = np.fft.rfft(x)
    lo = 1.0 / (1.0 + (low / np.maximum(f, 1.0)) ** 4)          # 4th-order-like shoulders
    hi = 1.0 / (1.0 + (f / high) ** 6)
    centre, gain = hump
    bump = 1.0 + (10 ** (gain / 20.0) - 1.0) * np.exp(-0.5 * (np.log2(np.maximum(f, 1.0) / centre) / 0.7) ** 2)
    return np.fft.irfft(X * lo * hi * bump, n)


def _wow(x, rate, hz, depth):
    t = np.arange(len(x)) / rate
    warp = t + depth / (2 * np.pi * hz) * np.sin(2 * np.pi * hz * t)
    return np.interp(warp * rate, np.arange(len(x)), x)


def _squeeze(x, rate, amount):
    win = int(0.03 * rate)
    env = np.sqrt(np.convolve(x * x, np.ones(win) / win, mode='same')) + 1e-5
    ref = np.percentile(env, 95)
    gain = (ref / env) ** amount
    gain = np.minimum(gain, 10 ** (12 / 20.0))                    # never lift the silence more than 12 dB
    gain = np.convolve(gain, np.ones(win) / win, mode='same')
    return x * gain


def air(x, rate=RATE, strength=1.0, seed=0):
    """The clip as heard on the radio: same length, at the game's speech level."""
    x = np.asarray(x, dtype=np.float64)
    if strength <= 0 or not len(x):
        return x.astype(np.float32)
    rng = np.random.default_rng(seed)
    s = float(strength)
    dry = x / (np.sqrt(np.mean(x * x)) + 1e-9) * 10 ** (LOUD / 20.0)
    y = _wow(dry, rate, WOW[0], WOW[1] * s)
    y = _band(y, rate, LOW * s + 60 * (1 - s), HIGH / s if s > 0.3 else 10000.0, (HUMP[0], HUMP[1] * s))
    y = _squeeze(y, rate, SQUEEZE * s)
    d = 1.0 + (DRIVE - 1.0) * s
    lvl = np.percentile(np.abs(y), 99.5) + 1e-9
    y = np.tanh(d * y / lvl) / np.tanh(d) * lvl
    noise = rng.standard_normal(len(y))
    noise = _band(noise, rate, 400.0, 6000.0, (3000.0, 3.0))
    noise *= 10 ** ((HISS + 20 * np.log10(max(s, 1e-3))) / 20.0) / (np.sqrt(np.mean(noise * noise)) + 1e-9)
    clicks = np.zeros(len(y))
    k = rng.poisson(CRACKLE * s * len(y) / rate)
    at = rng.integers(0, len(y), size=k)
    clicks[at] = rng.uniform(-1, 1, size=k) * 10 ** (-30 / 20.0)
    clicks = np.convolve(clicks, np.exp(-np.arange(48) / 6.0), mode='same')
    y = y + noise + clicks
    y = y / (np.sqrt(np.mean(y * y)) + 1e-9) * 10 ** (LOUD / 20.0)
    top = np.max(np.abs(y))
    if top > 10 ** (PEAK / 20.0):
        y = y * 10 ** (PEAK / 20.0) / top
    return y.astype(np.float32)
