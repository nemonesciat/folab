"""The proposed north expansion, with the coast the grow makes (mapscale heights, then coast.shape_sea by OSM's coastline): land and
sea as they'll be, the reef flats and sandbar the raw heights called land shown as shallows. Reads only."""
import sys, json, math
sys.path.insert(0, r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\app')
sys.stdout.reconfigure(encoding='utf-8')
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import elevation, osm, osmplace, mapgrow, coast, mapscale as MS

OUT = sys.argv[1]
side = json.load(open(r"C:\Users\AMD RYZEN\Claude Code Projects\FOLab\packaging\out\FOLab\projects\Waikiki maps\made.json", encoding='utf-8'))['FOLabWaikiki']
S0, W, N1, E = 21.2408, -157.8684, 21.5051, -157.6312
new, added = mapgrow.grown_side(side, [S0, W, N1, E])
data = osm.read('D:/FOLabScratch/north/waikiki-north.osm')
r = elevation.read_file(r"C:\Users\AMD RYZEN\Claude Code Projects\FOLab\packaging\out\FOLab\maps\N21W158.hgt.gz")
plan = mapgrow.plan_of(r, new)
grid = MS.heights(plan)
geo = osmplace.Georef(new, data)
raw = np.array(grid.pts, dtype=np.float32).reshape(grid.down, grid.across)[::-1].copy()
coast.shape_sea(grid, [[geo.xy(p) for p in line] for line in data.coast], plan.floor)
z = np.array(grid.pts, dtype=np.float32).reshape(grid.down, grid.across)[::-1]     # (rows from the north)
STEP = 3                                                     # (land points a pixel)
z, raw = z[::STEP, ::STEP], raw[::STEP, ::STEP]
land = z > 0
flats = (raw > 0) & ~land                                    # (the raw heights' land the coastline makes sea: reef flats, sandbar)
gy, gx = np.gradient(z, 128.0 * STEP)
shade = np.clip((gx * 0.6 - gy * 0.6 + 1.0) / np.sqrt(gx * gx + gy * gy + 1.0) * 0.8 + 0.15, 0, 1.2)
t = np.clip(z / (700 * 28.0), 0, 1)
ramp = np.array([[96, 120, 76], [128, 140, 90], [160, 150, 110], [180, 170, 150], [230, 228, 222]], np.float32)
idx = t * (len(ramp) - 1)
lo = np.floor(idx).astype(int).clip(0, len(ramp) - 2)
f = (idx - lo)[..., None]
col = (ramp[lo] * (1 - f) + ramp[lo + 1] * f) * shade[..., None]
col[~land] = (22, 40, 62)
col[flats] = (52, 128, 140)
img = Image.fromarray(col.clip(0, 255).astype(np.uint8))
img = img.resize((int(img.width * 1.3), int(img.height * 1.3)), Image.LANCZOS)
K = 1.3 / (128.0 * STEP)                                     # (pixels a game unit)
x0w, ytop = new['x0'] * 4096, (new['y0'] + new['H']) * 4096
px = lambda x, y: ((x - x0w) * K, (ytop - y) * K)
g = ImageDraw.Draw(img, 'RGBA')
font = lambda n, b=False: ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf' if b else 'C:/Windows/Fonts/segoeui.ttf', n)
# main roads, over land only
for w in data.roads:
    if w['class'] != 'major':
        continue
    pts = [px(*geo.xy(p)) for p in w['pts']]
    if len(pts) > 1:
        g.line(pts, fill=(250, 214, 130, 230), width=2)
# the north edge now, the grown edge
yo = px(0, (side['y0'] + side['H']) * 4096)[1]
for i in range(0, img.width, 14):
    g.line([(i, yo), (i + 8, yo)], fill=(255, 255, 255, 230), width=2)
# the border: reef over sea, pali where it crosses land (from the made land along the edge)
H_, W_ = land.shape
def edge_cells(points):
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        n = int(max(abs(bx - ax), abs(by - ay))) or 1
        for i in range(n):
            x, y = ax + (bx - ax) * i / n, ay + (by - ay) * i / n
            c, rr = min(W_ - 1, max(0, int(x / 1.3))), min(H_ - 1, max(0, int(y / 1.3)))
            yield (x, y), (ax + (bx - ax) * (i + 1) / n, ay + (by - ay) * (i + 1) / n), land[rr, c]
corners = [(1, 1), (img.width - 2, 1), (img.width - 2, img.height - 2), (1, img.height - 2), (1, 1)]
pali = reef = 0
for a_, b_, on_land in edge_cells(corners):
    if on_land:
        g.line([a_, b_], fill=(200, 60, 40, 255), width=7); pali += 1
    else:
        g.line([a_, b_], fill=(120, 235, 245, 255), width=5); reef += 1


def label(text, lat, lon, size=18, bold=True):
    x, y = px(*geo.xy((lat, lon)))
    fnt = font(size, bold)
    g.text((x + 1, y + 1), text, font=fnt, fill=(0, 0, 0, 200), anchor='mm')
    g.text((x, y), text, font=fnt, fill=(255, 255, 255, 255), anchor='mm')


for p in data.places:
    if p['name'] in ('Kailua', 'Kāneʻohe'):
        label(p['name'], p['pt'][0], p['pt'][1], 20)
label('Koʻolau', 21.40, -157.835, 20)
label('Kāneʻohe Bay', 21.47, -157.80, 15, False)
label('Lanikai', 21.391, -157.716, 13, False)
label('Mōkapu', 21.452, -157.745, 13, False)
label('the world now (Waikīkī, Honolulu)', 21.30, -157.80, 15)
fx, fy = 14, img.height - 140
g.rectangle([fx - 6, fy - 8, fx + 400, img.height - 8], fill=(0, 0, 0, 160))
for k, (c, w_, t) in enumerate((((255, 255, 255), 2, 'the north edge now (21.36°N)'), ((120, 235, 245), 5, 'reef and surf, the border in the shallows'),
                                 ((200, 60, 40), 7, 'pali cliff where the border crosses land'), ((250, 214, 130), 2, 'main roads (OpenStreetMap)'))):
    g.line([(fx, fy + 6 + k * 20), (fx + 30, fy + 6 + k * 20)], fill=c, width=w_)
    g.text((fx + 38, fy - 4 + k * 20), t, font=font(13), fill='white')
g.rectangle([fx, fy + 82, fx + 30, fy + 94], fill=(52, 128, 140))
g.text((fx + 38, fy + 76), 'reef flats and sandbar: shallow sea (OSM: not land)', font=font(13), fill='white')
g.text((fx, fy + 98), 'coast: OSM\'s coastline, islets kept', font=font(13), fill='white')
cell_px = 4096 * K
sx, sy = img.width - 30 - 17 * cell_px, img.height - 30
g.rectangle([sx - 10, sy - 30, img.width - 14, img.height - 8], fill=(0, 0, 0, 160))
g.line([(sx, sy), (sx + 17 * cell_px, sy)], fill='white', width=3)
g.text((sx, sy - 26), '17 cells = 5 km real at 1:5', font=font(13), fill='white')
g.text((14, 10), 'FOLabWaikiki grown north: +55 cells, 84 x 100 (8,400 cells), the coast as it will be made', font=font(19, True), fill='white')
img.save(OUT)
print('saved', OUT, img.size, 'border: reef %d, pali %d' % (reef, pali), 'shallow points', int(flats.sum()))
