"""Second pass: the weaker emblems drawn again with more to them, and a finer print style:
hatching only on forms wide enough to carry it, a highlight cut along each form's lit edge, fast morphology."""
import math, os, sys
from PIL import Image, ImageDraw, ImageChops, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import draw
from draw import S, INK, CUT, canvas, poly_line, bezier, circle, ring, leaf, waves, font, coin, skull

OUT = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------- redrawn

def frond(d, x, y, ang, length, width, droop):
    """A palm frond: a curved rib with leaflets cut into its edge."""
    pts = leaf(x, y, ang, length, width, droop)
    d.polygon(pts, fill=INK)
    ca, sa = math.cos(ang), math.sin(ang)
    for i in range(3, 19, 2):                      # notches between leaflets
        t = i / 20
        along = t * length
        px = x + ca * along
        py = y + sa * along + droop * length * t * t
        nx, ny = -sa, ca
        half = width * math.sin(math.pi * t) * (1 - 0.3 * t)
        for side in (1, -1):
            ex, ey = px + nx * half * side, py + ny * half * side
            d.line([(ex, ey), (px + nx * half * 0.35 * side + ca * 18, py + ny * half * 0.35 * side + sa * 18)], fill=CUT, width=7)
    rib = [(x + ca * t * length, y + sa * t * length + droop * length * (t * t)) for t in [i / 20 for i in range(21)]]
    d.line(rib[1:-2], fill=CUT, width=6)


def island_raised():
    m, d = canvas()
    # sun low on the left, behind the island
    circle(d, 280, 640, 150)
    for k in range(5):
        d.line([(110, 600 + k * 26), (450, 600 + k * 26)], fill=CUT, width=9)
    d.pieslice([150, 650, 900, 1010], 180, 360, fill=INK)          # the island
    for x in (300, 420, 560, 700):                                    # sand ripples
        d.arc([x - 50, 760, x + 50, 820], 200, 340, fill=CUT, width=9)
    trunk = bezier((600, 790), (560, 600), (560, 420), (650, 250))
    for i in range(len(trunk) - 1):                                   # trunk tapers, ringed
        w = 70 - 34 * i / len(trunk)
        poly_line(d, [trunk[i], trunk[i + 1]], int(w))
    for i in range(2, 38, 4):
        x, y = trunk[i]
        w = 70 - 34 * i / len(trunk)
        d.arc([x - w / 2, y - 14, x + w / 2, y + 14], 0, 180, fill=CUT, width=7)
    tx, ty = trunk[-1]
    for ang, ln, bd in ((-3.0, 320, 0.45), (-2.5, 280, 0.25), (-0.15, 330, 0.45), (-0.7, 280, 0.25),
                        (-1.6, 200, 0.02), (2.6, 230, 0.6), (0.5, 240, 0.65)):
        frond(d, tx, ty, ang, ln, 52, bd)
    for dx, dy in ((-34, 34), (10, 50), (42, 26)):                     # coconuts
        circle(d, tx + dx, ty + dy, 30); circle(d, tx + dx - 9, ty + dy - 9, 8, CUT)
    waves(d, 940, 60, 960, 20, 5, 28)
    return m


def two_tongues():
    m, d = canvas()
    # two bubbles, each a tongue of its own: Mandarin on the left, English on the right
    d.ellipse([70, 150, 600, 580], fill=INK)
    d.polygon([(180, 520), (110, 700), (330, 560)], fill=INK)
    d.ellipse([110, 190, 560, 540], fill=CUT)
    d.text((335, 365), '说', font=font(250, True), fill=INK, anchor='mm')
    d.ellipse([424, 430, 954, 860], fill=INK)
    d.polygon([(840, 800), (920, 980), (700, 840)], fill=INK)
    d.ellipse([464, 470, 914, 820], fill=CUT)
    d.text((689, 645), 'Hi!', font=font(200), fill=INK, anchor='mm')
    for a in (200, 225, 250):                                        # chatter marks
        t = math.radians(a)
        poly_line(d, [(335 + 300 * math.cos(t), 365 + 280 * math.sin(t)), (335 + 360 * math.cos(t), 365 + 340 * math.sin(t))], 20)
    return m


def fixers_hands():
    m, d = canvas()
    # a spanner, open jaw up-right, ring end down-left
    poly_line(d, [(250, 780), (720, 310)], 84)
    for k in range(5):
        x, y = 330 + k * 70, 700 - k * 70
        d.line([(x - 20, y - 20), (x + 20, y + 20)], fill=CUT, width=8)
    circle(d, 760, 270, 130)
    d.polygon([(760, 270), (950, 160), (950, 60), (860, 60)], fill=CUT)
    circle(d, 760, 270, 52, CUT)
    circle(d, 220, 810, 115)
    d.regular_polygon((220, 810, 56), 6, rotation=15, fill=CUT)
    # a lockpick and a tension wrench crossing it
    d.rounded_rectangle([140, 140, 330, 250], 40, fill=INK)            # pick handle
    for x in range(170, 320, 30):
        d.line([(x, 152), (x, 238)], fill=CUT, width=8)
    poly_line(d, [(330, 195), (760, 600)], 30)
    poly_line(d, [(760, 600), (800, 600), (830, 560), (860, 610)], 22)  # the pick's hook
    poly_line(d, [(560, 880), (900, 880), (900, 760)], 30)             # tension wrench
    return m


def reef_fighter():
    m, d = canvas()
    # the leiomano: a teardrop head of koa ringed with shark teeth, grain on it, cord-wrapped grip, lanyard
    head = []
    for i in range(80):
        t = 2 * math.pi * i / 80
        r = 1 - 0.35 * max(0, math.cos(t))           # narrower toward the grip
        head.append((512 + 190 * math.sin(t) * r, 380 - 290 * math.cos(t)))
    d.polygon(head, fill=INK)
    for k in range(3):                                # grain
        d.arc([380 + k * 40, 150 + k * 30, 640 - k * 40, 620 - k * 30], 120, 240, fill=CUT, width=7)
    n = 22
    for k in range(n):
        t = 2 * math.pi * (k + 0.5) / n
        if math.cos(t) > 0.8:
            continue
        r = 1 - 0.35 * max(0, math.cos(t))
        bx, by = 512 + 190 * math.sin(t) * r, 380 - 290 * math.cos(t)
        nx, ny = math.sin(t), -math.cos(t) * 0.75
        L = math.hypot(nx, ny); nx, ny = nx / L, ny / L
        px, py = -ny, nx
        tip = (bx + nx * 78 + px * 18, by + ny * 78 + py * 18)        # teeth hook a little
        d.polygon([(bx - px * 26, by - py * 26), (bx + px * 26, by + py * 26), tip], fill=INK)
        d.line([(bx, by), ((bx + tip[0]) / 2, (by + tip[1]) / 2)], fill=CUT, width=5)
    d.rounded_rectangle([474, 640, 550, 920], 26, fill=INK)
    for y in range(650, 910, 26):
        d.line([(474, y), (550, y + 13)], fill=CUT, width=7)
    circle(d, 512, 950, 40); circle(d, 512, 950, 16, CUT)
    d.arc([360, 880, 664, 1020], 15, 165, fill=INK, width=16)
    return m


def iron_gut():
    m, d = canvas()
    # a raw reef fish, bones showing, over a bowl of sea water that steams nothing: eaten and fine
    body = bezier((180, 420), (330, 220), (720, 220), (860, 400)) + bezier((860, 400), (720, 560), (330, 560), (180, 420))[1:]
    d.polygon(body, fill=INK)
    d.polygon([(200, 420), (60, 300), (100, 420), (60, 540)], fill=INK)      # tail
    circle(d, 740, 370, 40, CUT); circle(d, 748, 362, 16)
    d.arc([620, 300, 760, 500], 300, 60, fill=CUT, width=10)                  # gill
    poly_line(d, [(250, 410), (610, 405)], 14, CUT)                           # spine
    for x in range(290, 610, 50):
        d.line([(x, 410), (x + 40, 300)], fill=CUT, width=9)
        d.line([(x, 410), (x + 40, 515)], fill=CUT, width=9)
    d.polygon([(400, 260), (520, 170), (560, 270)], fill=INK)                  # dorsal fin
    # the bowl
    d.chord([200, 560, 824, 960], 0, 180, fill=INK)
    d.rectangle([200, 740, 824, 770], fill=INK)
    waves(d, 760, 240, 790, 10, 3, 12, CUT)
    d.rounded_rectangle([400, 930, 624, 970], 16, fill=INK)
    return m


REDRAWN = {'island_raised': island_raised, 'two_tongues': two_tongues, 'fixers_hands': fixers_hands,
           'reef_fighter': reef_fighter, 'iron_gut': iron_gut}
TRAITS = [(name, REDRAWN.get(fn.__name__, fn)) for name, fn in draw.TRAITS]


# ---------------------------------------------------------------- the style, finer

def grow(m, px):
    for _ in range(px // 2):
        m = m.filter(ImageFilter.MaxFilter(5))
    return m


def shrink(m, px):
    for _ in range(px // 2):
        m = m.filter(ImageFilter.MinFilter(5))
    return m


def hatch(spacing=20, width=6, angle=-45):
    h = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(h)
    t = math.radians(angle)
    ux, uy = math.cos(t), math.sin(t)
    px, py = -uy, ux
    for k in range(-80, 81):
        cx, cy = S / 2 + px * k * spacing, S / 2 + py * k * spacing
        d.line([(cx - ux * S, cy - uy * S), (cx + ux * S, cy + uy * S)], fill=255, width=width)
    return h


HATCH = hatch()


def finish(m):
    m = m.point(lambda v: 255 if v > 127 else 0)
    wide = grow(shrink(m, 22), 22)                         # only forms wide enough to hold hatching
    inner = shrink(wide, 8)
    far = ImageChops.subtract(inner, ImageChops.offset(inner, -40, -40))
    far = far.filter(ImageFilter.GaussianBlur(4)).point(lambda v: 255 if v > 128 else 0)
    art = ImageChops.subtract(m, ImageChops.multiply(far, HATCH))
    # a highlight cut just inside each wide form's lit edge
    lit_in = shrink(wide, 14)
    hl = ImageChops.subtract(lit_in, ImageChops.offset(lit_in, 10, 10))
    hl = ImageChops.subtract(hl, shrink(hl, 4)) if False else hl
    hl = hl.filter(ImageFilter.GaussianBlur(1.5)).point(lambda v: 255 if v > 140 else 0)
    art = ImageChops.subtract(art, hl)
    return art


def badge(art):
    import style
    return style.badge(art) if False else _badge(art)


def _badge(art):
    b = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(b)
    c, R = S / 2, 488
    d.ellipse([c - R, c - R, c + R, c + R], outline=255, width=20)
    d.ellipse([c - R + 66, c - R + 66, c + R - 66, c + R - 66], outline=255, width=9)
    n = 44
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        am = (a0 + a1) / 2
        r0, r1 = R - 16, R - 56
        d.polygon([(c + r0 * math.cos(a0), c + r0 * math.sin(a0)), (c + r0 * math.cos(a1), c + r0 * math.sin(a1)),
                   (c + r1 * math.cos(am), c + r1 * math.sin(am))], fill=255)
    for k in range(n):                                   # small dots between the teeth: kapa's second row
        a = 2 * math.pi * k / n
        r = R - 36
        if True:
            r = R - 50
            x, y = c + r * math.cos(a), c + r * math.sin(a)
            d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=255)
    return ImageChops.subtract(b, grow(art, 28))


def stylize(m):
    k = 0.76
    small = m.resize((int(S * k), int(S * k)), Image.LANCZOS)
    fit = Image.new('L', (S, S), 0)
    fit.paste(small, ((S - small.width) // 2, (S - small.height) // 2 + 6))
    fit = fit.point(lambda v: 255 if v > 127 else 0)
    art = finish(fit)
    outer = ImageChops.subtract(grow(fit, 22), grow(fit, 12))
    out = ImageChops.lighter(art, outer)
    return ImageChops.lighter(out, _badge(grow(fit, 12)))


def icon(fn):
    m = stylize(fn()).resize((256, 256), Image.LANCZOS)
    im = Image.new('RGBA', (256, 256), (255, 255, 255, 0))
    im.putalpha(m)
    return im


def big(fn):
    m = stylize(fn())
    im = Image.new('RGBA', (S, S), (255, 255, 255, 0))
    im.putalpha(m)
    return im


if __name__ == '__main__':
    only = sys.argv[1:]
    done = []
    for name, fn in TRAITS:
        if only and fn.__name__ not in only:
            continue
        im = icon(fn)
        im.save(os.path.join(OUT, 'p2_%s.png' % fn.__name__))
        done.append((name, im))
        print(name, flush=True)
    draw.sheet(done, os.path.join(OUT, 'sheet_p2.png' if not only else 'sheet_p2_some.png'))
