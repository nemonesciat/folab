"""gear50: the intact gear door's picture (textures\\dungeons\\vault\\VGearDoor03.dds, 1024 square) with "50" where it shows
"101" (the plate in the middle) and "112" (the hatch strip below): the old figures taken off with the plate's own dark,
the new ones drawn as tall as the old in their colour, with the old figures' grain. picture(gd) -> DDS bytes; it needs
PIL (a build step from the developer's Python, as garmentprint)."""
import struct
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\app')
import dds  # noqa: E402

SRC = chr(92).join(['textures', 'dungeons', 'vault', 'VGearDoor03.dds'])
PLATES = [(440, 455, 590, 565), (255, 925, 410, 1015)]     # (the "101" and the "112", on the 1024 picture)
RIM = 4                                                     # (taken off round each old figure)
FONTS = [r'C:\Windows\Fonts\impact.ttf', r'C:\Windows\Fonts\arialbd.ttf']


def _yellow(p):
    r, g, b = p[:3]
    return r > 60 and g > 55 and r - b > 22 and g - b > 15


def picture(gd, text='50'):
    data = gd.read_file(SRC)
    w, h, px = dds.decode(data, want=4096)[:3]
    im = Image.frombytes('RGBA', (w, h), bytes(px))
    pix = im.load()
    for (x0, y0, x1, y1) in PLATES:
        mask = [(x, y) for y in range(y0, y1) for x in range(x0, x1) if _yellow(pix[x, y])]
        if not mask:
            continue
        mx0, mx1 = min(m[0] for m in mask), max(m[0] for m in mask)
        my0, my1 = min(m[1] for m in mask), max(m[1] for m in mask)
        col = tuple(sum(pix[m][i] for m in mask) // len(mask) for i in range(3))
        grain = [sum(pix[m][:3]) / 3.0 for m in mask]
        g_mean = sum(grain) / len(grain)
        # the old figures off: a plaque of the plate's own darkest tone over them (RIM round), keeping the old grain's
        # light and dark: copying from beside them left marks of the plate's lighter ring
        bx0, by0, bx1, by1 = mx0 - RIM, my0 - RIM, mx1 + RIM, my1 + RIM
        dark = sorted((sum(pix[x, y][:3]) / 3.0, pix[x, y]) for y in range(by0 - 8, by1 + 9) for x in range(bx0 - 8, bx1 + 9)
                      if 0 <= x < w and 0 <= y < h and not _yellow(pix[x, y]))
        tone = dark[len(dark) // 5][1] if dark else (20, 20, 20, 255)
        lums = [sum(pix[x, y][:3]) / 3.0 for y in range(by0, by1 + 1) for x in range(bx0, bx1 + 1)]
        lm = sum(lums) / len(lums)
        for y in range(by0, by1 + 1):
            for x in range(bx0, bx1 + 1):
                o = pix[x, y]
                k_ = 0.8 + 0.4 * min(1.5, (sum(o[:3]) / 3.0) / max(1.0, lm))
                pix[x, y] = tuple(max(0, min(255, int(tone[i] * k_))) for i in range(3)) + (o[3],)
        # the new figures, as tall as the old and over the same middle
        hgt = my1 - my0 + 1
        font = None
        for f in FONTS:
            try:
                font = ImageFont.truetype(f, int(hgt * 1.25))
                break
            except OSError:
                continue
        layer = Image.new('L', (w, h), 0)
        dr = ImageDraw.Draw(layer)
        bx = dr.textbbox((0, 0), text, font=font)
        tw, th = bx[2] - bx[0], bx[3] - bx[1]
        sx = min(1.0, (mx1 - mx0 + 1) * 0.9 / tw)
        tmp = Image.new('L', (tw + 4, th + 4), 0)
        ImageDraw.Draw(tmp).text((2 - bx[0], 2 - bx[1]), text, fill=255, font=font)
        tmp = tmp.resize((max(1, int((tw + 4) * sx)), hgt))
        cx, cy = (mx0 + mx1) // 2, (my0 + my1) // 2
        layer.paste(tmp, (cx - tmp.width // 2, cy - tmp.height // 2))
        lp = layer.load()
        k = 0
        for y in range(my0 - 2, my1 + 3):
            for x in range(max(0, cx - tmp.width), min(w, cx + tmp.width)):
                a = lp[x, y] / 255.0
                if a <= 0:
                    continue
                gv = grain[k % len(grain)] / max(1.0, g_mean)
                k += 7
                o = pix[x, y]
                nc = tuple(int(col[i] * (0.8 + 0.2 * gv)) for i in range(3))
                pix[x, y] = tuple(int(o[i] * (1 - a) + nc[i] * a) for i in range(3)) + (o[3],)
    return dds.encode(w, h, im.tobytes()), im


if __name__ == '__main__':
    import gamedata
    gd = gamedata.GameData()
    data, im = picture(gd)
    im.convert('RGB').crop((380, 400, 650, 620)).save('D:/FOLab-tmp/gear/plate50.png')
    im.convert('RGB').crop((220, 880, 450, 1024)).save('D:/FOLab-tmp/gear/strip50.png')
    open('D:/FOLab-tmp/gear/VGearDoor03_50.dds', 'wb').write(data)
    print(len(data))
