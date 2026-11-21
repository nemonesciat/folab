"""Two storm pictures of FOLab's own: driven rain streaks and torn scud haze, grey, faint, fading to nothing at the edges
(each is drawn on a square card that faces the camera, so no edge may show)."""
import sys, os
import numpy as np
sys.path.insert(0, r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\app')
import dds
from PIL import Image

OUT = sys.argv[1]
rng = np.random.default_rng(7)
N = 128
yy, xx = np.mgrid[0:N, 0:N] / (N - 1) * 2 - 1


def soft_edge(sx, sy):
    r = np.sqrt((xx / sx) ** 2 + (yy / sy) ** 2)
    return np.clip(1 - r, 0, 1) ** 1.5


def blur_x(a, n):
    k = np.ones(n) / n
    return np.apply_along_axis(lambda r: np.convolve(r, k, mode='same'), 1, a)


def streaks():
    a = np.zeros((N, N))
    slope = 0.36                                    # falling a little as they blow
    for _ in range(70):
        ln = rng.uniform(0.25, 0.9)
        x0, y0 = rng.uniform(-0.75, 0.75) - ln / 2, rng.uniform(-0.8, 0.8)
        th = rng.uniform(0.6, 1.4)                  # thickness in pixels
        bright = rng.uniform(0.35, 1.0)
        t = np.linspace(0, 1, 160)
        px = (x0 + t * ln + 1) / 2 * (N - 1)
        py = (y0 + t * ln * slope + 1) / 2 * (N - 1)
        fade = np.sin(np.pi * t)                    # tapered ends
        for x, y, f in zip(px, py, fade):
            ix, iy = int(round(x)), int(round(y))
            for dy in (-1, 0, 1):
                if 0 <= ix < N and 0 <= iy + dy < N:
                    w = max(0.0, 1 - abs(y - (iy + dy)) / th)
                    a[iy + dy, ix] = max(a[iy + dy, ix], f * bright * w)
    a = blur_x(a, 3)
    return np.clip(a * soft_edge(1.0, 0.85) * 0.75, 0, 1), (215, 224, 220)


def haze():
    a = np.zeros((N, N))
    for scale, amp in ((4, 1.0), (8, 0.5), (16, 0.25)):
        g = rng.random((scale, scale * 2))
        im = Image.fromarray((g * 255).astype(np.uint8)).resize((N * 3, N), Image.BICUBIC)
        a += amp * np.asarray(im, dtype=float)[:, N:2 * N] / 255
    a = a / a.max()
    a = blur_x(a, 9)                                # torn along the wind
    a = np.clip((a - 0.35) / 0.65, 0, 1)
    return np.clip(a * soft_edge(1.0, 0.6) * 0.6, 0, 1), (150, 160, 156)


os.makedirs(OUT, exist_ok=True)
sheet = Image.new('RGB', (N * 2 * 2, N * 2), (40, 55, 70))
for k, (name, (alpha, col)) in enumerate((('folabstormstreaks', streaks()), ('folabstormhaze', haze()))):
    rgba = np.zeros((N, N, 4), np.uint8)
    rgba[..., :3] = col
    rgba[..., 3] = (alpha * 255).astype(np.uint8)
    with open(os.path.join(OUT, name + '.dds'), 'wb') as fh:
        fh.write(dds.encode(N, N, rgba.tobytes()))
    im = Image.fromarray(rgba, 'RGBA').resize((N * 2, N * 2))
    bg = Image.new('RGBA', im.size, (40, 55, 70, 255))
    bg.alpha_composite(im)
    sheet.paste(bg.convert('RGB'), (k * N * 2, 0))
sheet.save(os.path.join(sys.argv[2], 'storm_pictures.png'))
print('ok')
