"""Waikiki's trait emblems: white ink on clear, 256 square as the game's (the Pip-Boy tints them).
Drawn at 1024 on an alpha mask (255 ink, 0 cut), shrunk with a soft filter."""
import math, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

S = 1024
OUT = os.path.dirname(os.path.abspath(__file__))
INK, CUT = 255, 0


def canvas():
    m = Image.new('L', (S, S), 0)
    return m, ImageDraw.Draw(m)


def poly_line(d, pts, w, c=INK):
    d.line(pts, fill=c, width=w, joint='curve')
    for x, y in (pts[0], pts[-1]):
        d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=c)


def bezier(p0, p1, p2, p3, n=40):
    out = []
    for i in range(n + 1):
        t = i / n
        a = (1 - t) ** 3; b = 3 * (1 - t) ** 2 * t; c = 3 * (1 - t) * t * t; e = t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + e * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + e * p3[1]))
    return out


def circle(d, x, y, r, c=INK):
    d.ellipse([x - r, y - r, x + r, y + r], fill=c)


def ring(d, x, y, r, w, c=INK):
    d.ellipse([x - r, y - r, x + r, y + r], outline=c, width=w)


def leaf(cx, cy, ang, length, width, bend=0.25):
    """A frond: a pointed leaf from (cx, cy) along ang, as a polygon."""
    ca, sa = math.cos(ang), math.sin(ang)
    pts_l, pts_r = [], []
    for i in range(21):
        t = i / 20
        along = t * length
        droop = bend * length * t * t
        half = width * math.sin(math.pi * t) * (1 - 0.3 * t)
        x = cx + ca * along - sa * 0
        y = cy + sa * along + droop
        nx, ny = -sa, ca
        pts_l.append((x + nx * half, y + ny * half))
        pts_r.append((x - nx * half, y - ny * half))
    return pts_l + pts_r[::-1]


def waves(d, y, x0, x1, amp, n, w, c=INK):
    pts = [(x, y + amp * math.sin((x - x0) / (x1 - x0) * n * 2 * math.pi)) for x in range(x0, x1 + 1, 8)]
    poly_line(d, pts, w, c)


def font(size, cjk=False):
    for f in (['msyhbd.ttc', 'msyh.ttc', 'simhei.ttf'] if cjk else ['impact.ttf', 'arialbd.ttf']):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


# ---------------------------------------------------------------- the eighteen

def island_raised():
    m, d = canvas()
    circle(d, 640, 420, 190); circle(d, 640, 420, 150, CUT)      # sun ring behind
    for a in range(0, 360, 30):
        r = math.radians(a)
        poly_line(d, [(640 + 215 * math.cos(r), 420 + 215 * math.sin(r)), (640 + 265 * math.cos(r), 420 + 265 * math.sin(r))], 22)
    d.pieslice([170, 700, 870, 1000], 180, 360, fill=INK)          # the island
    trunk = bezier((470, 790), (450, 600), (480, 450), (560, 330))
    poly_line(d, trunk, 56)
    for i in range(1, 9):
        x, y = trunk[i * 4]
        d.line([(x - 30, y + 6), (x + 30, y - 6)], fill=CUT, width=8)
    top = trunk[-1]
    for ang, ln, bd in ((-2.9, 300, 0.35), (-2.3, 260, 0.2), (-0.4, 300, 0.35), (-0.95, 250, 0.15), (-1.6, 200, 0.05), (2.7, 240, 0.4), (0.3, 250, 0.45)):
        d.polygon(leaf(top[0], top[1], ang, ln, 46, bd), fill=INK)
    circle(d, top[0] - 30, top[1] + 30, 26); circle(d, top[0] + 10, top[1] + 44, 26)
    waves(d, 920, 120, 900, 18, 4, 26)
    d.rectangle([0, 960, S, S], fill=0)
    return m


def strong_swimmer():
    m, d = canvas()
    # a curling wave
    outer = bezier((120, 820), (160, 380), (520, 160), (820, 300)) + bezier((820, 300), (900, 340), (880, 470), (780, 470))
    inner = bezier((780, 470), (660, 470), (600, 390), (650, 330))[::-1]
    inner2 = bezier((650, 330), (480, 380), (420, 600), (470, 820))
    d.polygon(outer + inner[::-1] + inner2 + [(470, 900), (120, 900)], fill=INK)
    for k in range(4):
        y = 420 + k * 110
        d.arc([300 + k * 30, y, 560 + k * 30, y + 160], 200, 300, fill=CUT, width=18)
    for x, y, r in ((780, 600, 46), (860, 700, 30), (720, 720, 26), (820, 800, 20), (900, 560, 18)):
        ring(d, x, y, r, 14)
    waves(d, 930, 60, 960, 20, 5, 30)
    return m


def wrench(d, x0, y0, x1, y1, w):
    poly_line(d, [(x0, y0), (x1, y1)], w)
    ang = math.atan2(y1 - y0, x1 - x0)
    for (x, y, back) in ((x1, y1, 1), (x0, y0, -1)):
        circle(d, x, y, w * 1.25)
        cx, cy = x + back * math.cos(ang) * w * 0.7, y + back * math.sin(ang) * w * 0.7
        circle(d, cx, cy, w * 0.62, CUT)
        nx, ny = math.cos(ang) * back, math.sin(ang) * back
        d.polygon([(cx, cy), (cx + nx * w * 2 - ny * w * 0.5, cy + ny * w * 2 + nx * w * 0.5),
                   (cx + nx * w * 2 + ny * w * 0.5, cy + ny * w * 2 - nx * w * 0.5)], fill=CUT)


def fixers_hands():
    m, d = canvas()
    wrench(d, 230, 790, 790, 230, 70)
    # a lockpick and tension bar across it
    poly_line(d, [(250, 250), (700, 700)], 34)
    poly_line(d, [(700, 700), (760, 700), (790, 660)], 24)
    d.rounded_rectangle([170, 170, 330, 330], 30, fill=INK)
    circle(d, 250, 250, 34, CUT)
    poly_line(d, [(330, 560), (330, 800), (420, 800)], 26)
    for a in range(0, 360, 45):
        r = math.radians(a)
        poly_line(d, [(512 + 330 * math.cos(r), 512 + 330 * math.sin(r)), (512 + 380 * math.cos(r), 512 + 380 * math.sin(r))], 16) if a % 90 == 45 else None
    return m


def night_fisher():
    m, d = canvas()
    circle(d, 300, 260, 150); circle(d, 365, 220, 135, CUT)        # the moon
    for x, y in ((560, 160), (720, 260), (480, 360), (840, 140)):
        d.polygon([(x, y - 30), (x + 9, y - 9), (x + 30, y), (x + 9, y + 9), (x, y + 30), (x - 9, y + 9), (x - 30, y), (x - 9, y - 9)], fill=INK)
    rod = bezier((150, 900), (350, 700), (650, 420), (880, 380))
    poly_line(d, rod, 22)
    poly_line(d, [(880, 380), (880, 520)], 8)
    # the lantern
    d.polygon([(830, 520), (930, 520), (910, 540), (850, 540)], fill=INK)
    d.rounded_rectangle([845, 540, 915, 660], 14, fill=INK)
    d.rounded_rectangle([862, 560, 898, 640], 8, fill=CUT)
    circle(d, 880, 612, 14)
    d.rectangle([835, 660, 925, 680], fill=INK)
    for a in (200, 240, 280, 320, 340, 20):
        r = math.radians(a)
        poly_line(d, [(880 + 120 * math.cos(r), 600 + 120 * math.sin(r)), (880 + 160 * math.cos(r), 600 + 160 * math.sin(r))], 14)
    waves(d, 820, 300, 960, 16, 3, 22); waves(d, 900, 200, 980, 16, 3, 22)
    return m


def bubble(d, box, tail, c=INK):
    d.rounded_rectangle(box, 70, fill=c)
    d.polygon(tail, fill=c)


def two_tongues():
    m, d = canvas()
    bubble(d, [90, 160, 640, 560], [(220, 540), (180, 700), (360, 550)])
    d.rounded_rectangle([120, 190, 610, 530], 50, fill=CUT)
    d.text((365, 360), '你好', font=font(190, True), fill=INK, anchor='mm')
    bubble(d, [400, 460, 950, 860], [(820, 840), (880, 980), (700, 850)])
    d.rounded_rectangle([430, 490, 920, 830], 50, fill=CUT)
    d.text((675, 660), 'HELLO', font=font(130), fill=INK, anchor='mm')
    return m


def coin(d, x, y, r, mark='K'):
    circle(d, x, y, r)
    ring(d, x, y, r * 0.82, max(8, int(r * 0.06)), CUT)
    for a in range(0, 360, 20):
        t = math.radians(a)
        circle(d, x + r * 0.92 * math.cos(t), y + r * 0.92 * math.sin(t), r * 0.035, CUT)
    d.text((x, y + r * 0.04), mark, font=font(int(r * 1.05)), fill=CUT, anchor='mm')


def kala_sense():
    m, d = canvas()
    coin(d, 470, 540, 300)
    for a in (-60, -30, 0, -90):
        t = math.radians(a)
        poly_line(d, [(470 + 360 * math.cos(t), 540 + 360 * math.sin(t)), (470 + 440 * math.cos(t), 540 + 440 * math.sin(t))], 26)
    # a magnifying glass over it: the eye for worth
    ring(d, 760, 330, 120, 40)
    poly_line(d, [(840, 410), (960, 530)], 56)
    return m


def captains_kin():
    m, d = canvas()
    d.chord([170, 220, 860, 640], 180, 360, fill=INK)             # crown of the cap
    d.rounded_rectangle([200, 420, 830, 560], 30, fill=INK)        # band
    d.rectangle([220, 450, 810, 470], fill=CUT)
    d.chord([170, 440, 760, 720], 0, 180, fill=INK)                # peak, joined to the band
    d.line([(200, 562), (800, 562)], fill=CUT, width=14)
    # anchor badge
    circle(d, 512, 340, 92, CUT)
    poly_line(d, [(512, 280), (512, 410)], 20)
    poly_line(d, [(470, 300), (554, 300)], 16)
    d.arc([440, 330, 584, 420], 20, 160, fill=INK, width=18)
    ring(d, 512, 268, 18, 10)
    for k in range(5):                                                 # braid on the peak
        circle(d, 320 + k * 95, 610, 20, CUT)
    waves(d, 860, 160, 860, 18, 4, 26)
    return m


def raised_on_the_boats():
    m, d = canvas()
    d.polygon([(130, 640), (900, 640), (790, 790), (240, 790)], fill=INK)     # hull
    for x in range(300, 760, 110):
        circle(d, x, 700, 20, CUT)
    poly_line(d, [(500, 640), (500, 150)], 30)
    d.polygon([(520, 170), (520, 600), (820, 600)], fill=INK)                 # sail
    d.polygon([(480, 220), (480, 600), (230, 600)], fill=INK)
    d.line([(520, 400), (700, 600)], fill=CUT, width=10)
    # the flag: skull and crossbones
    d.rectangle([500, 80, 690, 200], fill=INK)
    circle(d, 595, 130, 34, CUT)
    d.rectangle([580, 150, 610, 175], fill=CUT)
    circle(d, 583, 126, 9); circle(d, 607, 126, 9)
    poly_line(d, [(545, 105), (645, 185)], 10, CUT); poly_line(d, [(645, 105), (545, 185)], 10, CUT)
    circle(d, 595, 130, 34, CUT); circle(d, 583, 126, 9); circle(d, 607, 126, 9)
    waves(d, 840, 60, 960, 22, 5, 30); waves(d, 930, 120, 900, 18, 4, 24)
    return m


def skull(d, x, y, s, c=INK, cut=CUT):
    d.ellipse([x - 160 * s, y - 180 * s, x + 160 * s, y + 120 * s], fill=c)
    d.rounded_rectangle([x - 95 * s, y + 60 * s, x + 95 * s, y + 200 * s], 30 * s, fill=c)
    for ex in (-62, 62):
        d.ellipse([x + (ex - 48) * s, y - 60 * s, x + (ex + 48) * s, y + 40 * s], fill=cut)
    d.polygon([(x, y + 40 * s), (x - 24 * s, y + 90 * s), (x + 24 * s, y + 90 * s)], fill=cut)
    for tx in range(-75, 80, 37):
        d.polygon([(x + (tx - 16) * s, y + 130 * s), (x + (tx + 16) * s, y + 130 * s), (x + tx * s, y + 190 * s)], fill=cut)


def dread_name():
    m, d = canvas()
    for a, b in (((220, 860), (800, 280)), ((800, 860), (220, 280))):          # crossed clubs behind
        poly_line(d, [a, b], 56)
        circle(d, b[0], b[1], 80)
    skull(d, 512, 470, 1.35)
    for a in (200, 230, 310, 340):                                             # the glare
        t = math.radians(a)
        poly_line(d, [(512 + 290 * math.cos(t), 420 + 290 * math.sin(t)), (512 + 380 * math.cos(t), 420 + 380 * math.sin(t))], 26)
    return m


def soft_touch():
    m, d = canvas()
    poly_line(d, [(280, 950), (280, 110)], 36)
    circle(d, 280, 100, 34)
    flag = bezier((300, 140), (480, 60), (620, 240), (880, 150)) + bezier((880, 150), (840, 330), (860, 420), (900, 520))[1:] \
        + bezier((900, 520), (650, 600), (500, 420), (300, 520))[1:]
    d.polygon(flag, fill=INK)
    d.line(bezier((360, 220), (500, 160), (620, 320), (820, 250)), fill=CUT, width=12)
    d.line(bezier((360, 420), (520, 340), (640, 520), (840, 450)), fill=CUT, width=12)
    for y in (300, 380, 460):
        poly_line(d, [(130, y), (210, y - 20)], 18)
    return m


def storm_touched():
    m, d = canvas()
    for x, y, r in ((330, 360, 170), (520, 270, 210), (720, 370, 170), (420, 450, 150), (640, 470, 150)):
        circle(d, x, y, r)
    d.rectangle([180, 450, 860, 560], fill=INK)
    d.arc([200, 300, 520, 620], 200, 320, fill=CUT, width=14)
    d.polygon([(560, 470), (420, 720), (520, 720), (440, 960), (700, 640), (590, 640), (680, 470)], fill=CUT)
    d.polygon([(575, 500), (470, 700), (560, 700), (490, 900), (660, 660), (570, 660), (650, 500)], fill=INK)
    for x in range(220, 860, 90):
        if 420 < x < 700:
            continue
        poly_line(d, [(x, 640), (x - 60, 820)], 20)
        poly_line(d, [(x - 30, 860), (x - 60, 950)], 20)
    return m


def reef_fighter():
    m, d = canvas()
    # the leiomano: a paddle head ringed with shark teeth, a grip and a lanyard
    head = [(512 + 170 * math.sin(t / 40 * math.pi), 470 - 330 * math.cos(t / 40 * math.pi) * (1 if t <= 20 else 1)) for t in range(41)]
    d.ellipse([340, 140, 684, 640], fill=INK)
    d.ellipse([390, 200, 634, 590], outline=CUT, width=12)
    for k in range(18):
        t = math.pi * 0.08 + k * math.pi * 1.84 / 17
        cx, cy = 512 + 172 * math.sin(t - math.pi / 2 + math.pi / 2) * 1, 390 - 250 * math.cos(t)
        nx, ny = math.sin(t) * 172, -math.cos(t) * 250
        L = math.hypot(nx / 172, ny / 250)
        ux, uy = math.sin(t), -math.cos(t)
        bx, by = 512 + 172 * ux, 390 + 250 * uy
        px, py = -uy, ux
        d.polygon([(bx - px * 22, by - py * 22), (bx + px * 22, by + py * 22), (bx + ux * 60, by + uy * 60)], fill=INK)
    d.rounded_rectangle([470, 600, 554, 900], 30, fill=INK)
    for y in range(640, 880, 40):
        d.line([(470, y), (554, y + 20)], fill=CUT, width=10)
    circle(d, 512, 930, 44); circle(d, 512, 930, 18, CUT)
    d.arc([380, 860, 640, 1010], 20, 160, fill=INK, width=16)
    return m


def iron_gut():
    m, d = canvas()
    # a fish skeleton on a fork
    d.polygon([(170, 470), (250, 380), (250, 560)], fill=INK)                 # tail
    d.ellipse([560, 330, 860, 610], fill=INK)                                  # head
    circle(d, 760, 440, 34, CUT); circle(d, 760, 440, 12)
    d.polygon([(860, 470), (780, 500), (860, 530)], fill=CUT)
    poly_line(d, [(250, 470), (600, 470)], 30)
    for x in range(300, 600, 55):
        poly_line(d, [(x, 470), (x + 40, 360)], 18)
        poly_line(d, [(x, 470), (x + 40, 580)], 18)
    # the fork under it
    poly_line(d, [(512, 640), (512, 960)], 40)
    d.rounded_rectangle([400, 630, 624, 690], 20, fill=INK)
    for x in (420, 480, 544, 604):
        poly_line(d, [(x, 690), (x, 560)], 22) if False else None
    for x in (420, 487, 537, 604):
        poly_line(d, [(x, 640), (x, 590)], 22)
    return m


def foot(d, x, y, s, flip=1):
    d.ellipse([x - 70 * s, y - 120 * s, x + 70 * s, y + 120 * s], fill=INK)
    d.ellipse([x - 55 * s, y + 90 * s, x + 55 * s, y + 200 * s], fill=INK)
    for i, (dx, dy, r) in enumerate(((-55, -165, 30), (-15, -185, 26), (22, -178, 22), (52, -160, 19), (74, -132, 16))):
        circle(d, x + dx * s * flip, y + dy * s, r * s)


def light_traveller():
    m, d = canvas()
    foot(d, 620, 420, 1.3, 1)
    foot(d, 380, 720, 1.3, -1)
    for y, x0, x1 in ((330, 100, 380), (430, 60, 380), (530, 130, 380), (640, 80, 200), (760, 60, 170)):
        poly_line(d, [(x0, y), (x1, y)], 22)
    return m


def link(d, x, y, ang, s=1, c=INK, w=26):
    ca, sa = math.cos(ang), math.sin(ang)
    pts = []
    for i in range(40):
        t = i / 40 * 2 * math.pi
        lx, ly = 70 * s * math.cos(t), 38 * s * math.sin(t)
        pts.append((x + lx * ca - ly * sa, y + lx * sa + ly * ca))
    d.line(pts + [pts[0]], fill=c, width=w, joint='curve')


def sold_and_escaped():
    m, d = canvas()
    # two cuffs, chain broken in the middle with a spark
    for cx in (250, 774):
        ring(d, cx, 600, 150, 52)
        d.rectangle([cx - 30, 430, cx + 30, 470], fill=INK)
        circle(d, cx, 600, 26)
    for i, x in enumerate((340, 410)):
        link(d, x, 470 - i * 40, -0.55)
    for i, x in enumerate((684, 614)):
        link(d, x, 470 - i * 40, 0.55)
    # the broken link ends
    d.arc([440, 300, 520, 380], 120, 330, fill=INK, width=26)
    d.arc([504, 300, 584, 380], 210, 60, fill=INK, width=26)
    for a in range(0, 360, 40):
        t = math.radians(a)
        poly_line(d, [(512 + 70 * math.cos(t), 230 + 70 * math.sin(t)), (512 + 140 * math.cos(t), 230 + 140 * math.sin(t))], 16)
    return m


def kahunas_debt():
    m, d = canvas()
    # an open ledger with a quill, a stack of kala beside
    d.polygon([(110, 520), (500, 470), (500, 860), (110, 900)], fill=INK)
    d.polygon([(524, 470), (914, 520), (914, 900), (524, 860)], fill=INK)
    for k in range(6):
        y = 560 + k * 50
        d.line([(160, y + 6 - k), (450, y - 30)], fill=CUT, width=10)
        d.line([(574, y - 30), (864, y + 6 - k)], fill=CUT, width=10)
    feather = bezier((560, 760), (640, 500), (760, 260), (930, 120))
    d.polygon(leaf(560, 760, -1.0, 560, 60, 0.0), fill=CUT)
    d.polygon(leaf(575, 745, -1.0, 530, 44, 0.0), fill=INK)
    for k, (x, y) in enumerate(((250, 330), (330, 230), (230, 140))):
        coin(d, x, y, 105)
    return m


def outcast():
    m, d = canvas()
    d.pieslice([352, 470, 672, 700], 180, 360, fill=INK)                      # a small island
    poly_line(d, bezier((512, 585), (500, 520), (520, 470), (560, 430)), 24)
    for ang, ln in ((-2.8, 110), (-2.1, 100), (-0.5, 110), (-1.1, 90), (0.4, 100)):
        d.polygon(leaf(560, 430, ang, ln, 22, 0.35), fill=INK)
    waves(d, 620, 330, 700, 10, 3, 16)
    for a in (0, 90, 180, 270):                                                 # four arrows away
        t = math.radians(a - 45)
        x0, y0 = 512 + 240 * math.cos(t), 530 + 240 * math.sin(t)
        x1, y1 = 512 + 430 * math.cos(t), 530 + 430 * math.sin(t)
        poly_line(d, [(x0, y0), (x1, y1)], 34)
        px, py = -math.sin(t), math.cos(t)
        d.polygon([(x1 + math.cos(t) * 60, y1 + math.sin(t) * 60), (x1 + px * 55, y1 + py * 55), (x1 - px * 55, y1 - py * 55)], fill=INK)
    return m


def half_drowned():
    m, d = canvas()
    waves(d, 190, 40, 980, 24, 4, 36)
    waves(d, 260, 80, 940, 14, 5, 18)
    skull(d, 470, 680, 1.05)
    for x, y, r in ((680, 520, 48), (740, 420, 36), (700, 330, 26), (790, 560, 22), (760, 640, 16)):
        ring(d, x, y, r, 14)
    return m


TRAITS = [
    ('Island Raised', island_raised), ('Strong Swimmer', strong_swimmer), ("Fixer's Hands", fixers_hands),
    ('Night Fisher', night_fisher), ('Two Tongues', two_tongues), ('Kala Sense', kala_sense),
    ("Captain's Kin", captains_kin), ('Raised on the Boats', raised_on_the_boats), ('Dread Name', dread_name),
    ('Soft Touch', soft_touch), ('Storm-Touched', storm_touched), ('Reef Fighter', reef_fighter),
    ('Iron Gut', iron_gut), ('Light Traveller', light_traveller), ('Sold and Escaped', sold_and_escaped),
    ("Kahuna's Debt", kahunas_debt), ('Outcast of Every Shore', outcast), ('Half-Drowned', half_drowned),
]


def icon(fn):
    m = fn()
    m = m.resize((256, 256), Image.LANCZOS)
    im = Image.new('RGBA', (256, 256), (255, 255, 255, 0))
    im.putalpha(m)
    return im


def sheet(icons, path):
    cols, cw, ch = 6, 300, 340
    rows = (len(icons) + cols - 1) // cols
    bg = Image.new('RGBA', (cols * cw + 40, rows * ch + 90), (12, 26, 14, 255))
    d = ImageDraw.Draw(bg)
    d.text((20, 18), "Waikiki's traits: emblems as the Pip-Boy shows them", font=font(40), fill=(26, 255, 128, 255))
    f = ImageFont.truetype('arialbd.ttf', 22)
    for k, (name, im) in enumerate(icons):
        x, y = 20 + (k % cols) * cw + 22, 80 + (k // cols) * ch
        g = Image.new('RGBA', im.size, (26, 255, 128, 255)); g.putalpha(im.split()[3])
        d.rectangle([x - 2, y - 2, x + 258, y + 258], outline=(26, 120, 60, 255), width=2)
        bg.alpha_composite(g, (x, y))
        d.text((x + 128, y + 280), name, font=f, fill=(26, 255, 128, 255), anchor='mm')
    bg.convert('RGB').save(path)


if __name__ == '__main__':
    done = []
    for name, fn in TRAITS:
        im = icon(fn)
        im.save(os.path.join(OUT, 'trait_%s.png' % fn.__name__))
        done.append((name, im))
    sheet(done, os.path.join(OUT, 'sheet.png'))
    print('drew', len(done))
