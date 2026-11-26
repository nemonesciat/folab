"""The emblems in a richer print style: hatched shade on each form's far side, a contour line round the whole drawing,
and one badge (a ring with a kapa border of triangles) behind every emblem so the eighteen read as a set."""
import math, os, sys
from PIL import Image, ImageDraw, ImageChops, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import draw
from draw import S, font

OUT = os.path.dirname(os.path.abspath(__file__))


def grow(m, px):
    return m.filter(ImageFilter.MaxFilter(px * 2 + 1)) if px else m


def shrink(m, px):
    return m.filter(ImageFilter.MinFilter(px * 2 + 1)) if px else m


def hatch(spacing=26, width=9, angle=-45):
    h = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(h)
    t = math.radians(angle)
    ux, uy = math.cos(t), math.sin(t)
    px, py = -uy, ux
    for k in range(-60, 61):
        cx, cy = S / 2 + px * k * spacing, S / 2 + py * k * spacing
        d.line([(cx - ux * S, cy - uy * S), (cx + ux * S, cy + uy * S)], fill=255, width=width)
    return h


HATCH = None


def shade(m):
    """Hatching cut into each form's lower-right side: where the form is, but isn't once moved up-left."""
    global HATCH
    if HATCH is None:
        HATCH = hatch()
    inner = shrink(m, 10)
    lit = ImageChops.offset(inner, -34, -34)
    side = ImageChops.subtract(inner, lit)                       # the far side of each form
    side = side.filter(ImageFilter.GaussianBlur(3)).point(lambda v: 255 if v > 128 else 0)
    cuts = ImageChops.multiply(side, HATCH)
    return ImageChops.subtract(m, cuts)


def badge(art):
    """A ring with kapa triangles, broken where the art stands over it."""
    b = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(b)
    c, R = S / 2, 488
    d.ellipse([c - R, c - R, c + R, c + R], outline=255, width=22)
    d.ellipse([c - R + 70, c - R + 70, c + R - 70, c + R - 70], outline=255, width=10)
    n = 44
    for k in range(n):                                            # kapa: triangles between the two rings
        a0 = 2 * math.pi * k / n
        a1 = 2 * math.pi * (k + 1) / n
        am = (a0 + a1) / 2
        r0, r1 = R - 18, R - 62
        pts = [(c + r0 * math.cos(a0), c + r0 * math.sin(a0)), (c + r0 * math.cos(a1), c + r0 * math.sin(a1)),
               (c + r1 * math.cos(am), c + r1 * math.sin(am))]
        d.polygon(pts, fill=255)
    gap = grow(art, 30)
    return ImageChops.subtract(b, gap)


def stylize(m, framed=True):
    # fit the drawing inside the badge: shrink it about the middle
    k = 0.78
    small = m.resize((int(S * k), int(S * k)), Image.LANCZOS)
    fit = Image.new('L', (S, S), 0)
    fit.paste(small, ((S - small.width) // 2, (S - small.height) // 2 + 6))
    fit = fit.point(lambda v: 255 if v > 127 else 0)
    art = shade(fit)
    # a contour round the whole drawing, a gap inside it
    outer = ImageChops.subtract(grow(fit, 24), grow(fit, 13))
    out = ImageChops.lighter(art, outer)
    if framed:
        out = ImageChops.lighter(out, badge(grow(fit, 13)))
    return out


def icon(fn):
    m = stylize(fn())
    m = m.resize((256, 256), Image.LANCZOS)
    im = Image.new('RGBA', (256, 256), (255, 255, 255, 0))
    im.putalpha(m)
    return im


if __name__ == '__main__':
    done = []
    for name, fn in draw.TRAITS:
        im = icon(fn)
        im.save(os.path.join(OUT, 'styled_%s.png' % fn.__name__))
        done.append((name, im))
    draw.sheet(done, os.path.join(OUT, 'sheet_styled.png'))
    print('styled', len(done))
