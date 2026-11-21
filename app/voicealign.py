"""Sound timings for a voice that doesn't report them (Chatterbox): the same words spoken by Kokoro, whose timings are
known, laid against it by dynamic time warping, each sound's start and end carried across. numpy only.

Both are read as mel cepstra (10 ms a frame, the first coefficient left out so loudness doesn't count, each line's mean
taken off so the two voices' colour doesn't either); the warp is the cheapest path through their frame-to-frame
distances (steps right, down or diagonal). Chatterbox copies a clip of the same Kokoro voice, so the two are alike enough
for this. The lip file only needs each sound to within a frame or two of 1/30 s."""
import numpy as np

RATE = 24000
HOP = 240                       # 10 ms
WIN = 600                       # 25 ms
MELS = 26
CEPS = 13


def _mel_bank(n_fft):
    def mel(f):
        return 2595 * np.log10(1 + f / 700.0)

    def hz(m):
        return 700 * (10 ** (m / 2595.0) - 1)
    edges = hz(np.linspace(mel(60), mel(7600), MELS + 2))
    bins = np.fft.rfftfreq(n_fft, 1 / RATE)
    bank = np.zeros((MELS, len(bins)))
    for i in range(MELS):
        lo, mid, hi = edges[i:i + 3]
        bank[i] = np.clip(np.minimum((bins - lo) / (mid - lo), (hi - bins) / (hi - mid)), 0, None)
    return bank


def features(x):
    """Mel cepstra, one row per 10 ms, mean taken off."""
    x = np.asarray(x, dtype=np.float64)
    if len(x) < WIN:
        x = np.pad(x, (0, WIN - len(x)))
    x = np.append(x[0], x[1:] - 0.97 * x[:-1])
    n = 1 + (len(x) - WIN) // HOP
    idx = np.arange(WIN)[None, :] + HOP * np.arange(n)[:, None]
    frames = x[idx] * np.hamming(WIN)
    n_fft = 1024
    power = np.abs(np.fft.rfft(frames, n_fft)) ** 2
    logmel = np.log(power @ _mel_bank(n_fft).T + 1e-10)
    k = np.arange(MELS)
    dct = np.cos(np.pi / MELS * (k[None, :] + 0.5) * np.arange(CEPS)[:, None])
    c = logmel @ dct.T
    c = c[:, 1:]
    return c - c.mean(axis=0)


def warp(a, b):
    """[(i, j)]: the cheapest path matching frames of a to frames of b, start to end."""
    sq = (a ** 2).sum(axis=1)[:, None] + (b ** 2).sum(axis=1)[None, :] - 2 * a @ b.T
    cost = np.sqrt(np.maximum(sq, 0))
    n, m = cost.shape
    d = np.full((n, m), np.inf)
    step = np.zeros((n, m), dtype=np.int8)        # 0 diagonal, 1 from above, 2 from the left
    for i in range(n):
        c = cost[i]
        if i == 0:
            d[0] = np.cumsum(c)
            step[0, 1:] = 2
            continue
        diag = np.concatenate([[np.inf], d[i - 1, :-1]])
        up = d[i - 1]
        t = np.minimum(diag, up) + c
        came = np.where(diag <= up, 0, 1).astype(np.int8)
        # then the steps from the left within the row: d[j] = min(t[j], d[j-1] + c[j])
        cs = np.cumsum(c)
        best = np.minimum.accumulate(t - cs)
        row = best + cs
        left = row < t - 1e-12
        d[i] = np.where(left, row, t)
        step[i] = np.where(left, 2, came)
    path = []
    i, j = n - 1, m - 1
    while i > 0 or j > 0:
        path.append((i, j))
        s = step[i, j]
        if s == 0:
            i, j = i - 1, j - 1
        elif s == 1:
            i -= 1
        else:
            j -= 1
        i, j = max(i, 0), max(j, 0)
    path.append((0, 0))
    return path[::-1]


def carry(timed, known, other):
    """[(sound, start, end)] timed against `known` audio, moved onto `other` audio of the same words."""
    a, b = features(known), features(other)
    path = warp(a, b)
    to = {}
    for i, j in path:
        to.setdefault(i, []).append(j)
    frames = np.array([np.mean(to[i]) if i in to else np.nan for i in range(len(a))])
    seconds_a = np.arange(len(a)) * HOP / RATE
    seconds_b = frames * HOP / RATE

    def move(t):
        return float(np.interp(t, seconds_a, seconds_b))
    end = len(other) / RATE
    out = []
    for s, t0, t1 in timed:
        u0, u1 = min(move(t0), end), min(move(t1), end)
        out.append((s, u0, max(u0, u1)))
    return out
