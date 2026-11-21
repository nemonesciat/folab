import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
"""The city's further hotels and landmarks (resortset) in texwear's worn paint: every piece builds and checks, the
tall and far-seen ones have far models, the ones made to be walked are walked, the worn pictures repeat without a seam
and are drawn the same every time, and resortplace reads its marks from a map."""
import tempfile

import dds, gamedata, modelmake, modelsets, nifmake, texpaint as tp, texwear as tw, waikikiset, solidwalk


def check(what, ok, got=None):
    print(('PASS ' if ok else 'FAIL ') + what + ('' if ok or got is None else '  ' + repr(got)))


import resortset  # noqa: E402

built, bad = {}, []
for piece in list(resortset.HOTELS) + list(resortset.PIECES):
    built[piece] = m = modelsets.build(piece)
    wrong = nifmake.check(m['nif'], m['shapes'], m['solids'])
    if wrong or m['triangles'] > modelmake.MOST_BUILDING:
        bad.append((piece, m['triangles'], wrong))
check('every new hotel and landmark builds, every block checked, none over MOST_BUILDING triangles', not bad, bad)
nofar = [p for p in built if not built[p].get('far')]
check('every one of them has a far model', not nofar, nofar)
check('Lani Moku stands over twenty floors; the motor lodge two floors under its roof',
      built['lani_moku']['box'][5] > 20 * modelsets.FLOOR and built['tradewinds_lodge']['box'][5] < 2 * modelsets.FLOOR + 300 + 1500)
cb = built['coral_crescent']['box']
check('the crescent bends towards the sea: its ends further out than its middle', cb[1] < -1000, cb)

walk_bad = []
for piece, deck in (('tradewinds_lodge', modelsets.FLOOR), ('band_shell', 110.0)):
    f = solidwalk.Walk(built[piece]['solids']).floors([deck], band=4)[0]
    if not f[0] or f[1] < 0.6 * f[0]:
        walk_bad.append((piece, f))
check("the lodge's upper walkway (up its stairs) and the band shell's stage are walked from the ground", not walk_bad, walk_bad)

gdw = gamedata.GameData()
lit = {p: len(waikikiset.lights(gdw, None, p, 0.0, 0.0, 0.0, 0.0, cell='+000800')) for p in ('lani_moku', 'tradewinds_lodge', 'sky_wheel')}
check('the star, the lodge\'s sign and the wheel are lit by the game\'s own lights', all(lit.values()), lit)

# the worn pictures
a = tw.concrete(size=64, seed=5)
b = tw.concrete(size=64, seed=5)
check('a worn picture is the same every time from the same seed', a.rgb == b.rgb and a.ht == b.ht)


def seam(c):
    """How much the picture jumps from its right column back to its left, against how much it changes inside."""
    w, h = c.w, c.h
    jump = sum(abs(c.rgb[y * w][k] - c.rgb[y * w + w - 1][k]) for y in range(h) for k in range(3)) / float(h)
    inside = sum(abs(c.rgb[y * w + w // 2][k] - c.rgb[y * w + w // 2 - 1][k]) for y in range(h) for k in range(3)) / float(h)
    return jump, inside


seams = {n: seam(fn()) for n, fn in (('render', lambda: tw.render(size=128, seed=3)), ('steel', lambda: tw.steel(size=64, seed=3)),
                                       ('wood', lambda: tw.wood(tp.CORAL, size=64, seed=3)), ('tar', lambda: tw.tar_roof(size=128, seed=3)))}
check('the repeating ones repeat without a seam', all(j < 3 * i + 6 for j, i in seams.values()), seams)
g = tw.grade((240, 40, 40))
check('the grade drains colour and lifts black: a red comes out duller, black not quite black',
      g[0] - g[1] < 200 and min(tw.grade((0, 0, 0))) > 5, (g, tw.grade((0, 0, 0))))
col, nor = tw.glass_curtain(size=32, seed=1).files()
check('a picture with its own gloss writes both its files as the game reads them', dds.info(col)['w'] == 32 and dds.info(nor)['mips'] > 1)
sheet = tw.facade_sheet(bays=2, floors=2, size=64, seed=9)
check('a small hotel face has four different rooms', sheet.w == 64)
up = tw.UPGRADE()
missing = [n for n in up if n not in modelsets.TEXTURES and not n.startswith('coast/')]
check('every drop-in names a texture the hotels already draw', not missing, missing)

import resortplace  # noqa: E402
_osm = os.path.join(tempfile.mkdtemp(), 'city.osm')
with open(_osm, 'w', encoding='utf-8') as f_:
    f_.write('<osm><node id="1" lat="21.27" lon="-157.82"><tag k="man_made" v="water_tower"/></node>'
             '<node id="2" lat="21.26" lon="-157.82"/><node id="3" lat="21.261" lon="-157.82"/><node id="4" lat="21.261" lon="-157.821"/>'
             '<node id="5" lat="21.26" lon="-157.821"/><node id="6" lat="21.265" lon="-157.83"/><node id="7" lat="21.266" lon="-157.83"/>'
             '<node id="8" lat="21.265" lon="-157.831"/>'
             '<node id="10" lat="21.262" lon="-157.825"><tag k="amenity" v="theatre"/><tag k="name" v="Waikiki Shell"/></node>'
             '<node id="11" lat="21.271" lon="-157.821"><tag k="tourism" v="zoo"/><tag k="name" v="City Zoo"/></node>'
             '<way id="20"><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="5"/><nd ref="2"/><tag k="leisure" v="park"/><tag k="name" v="Big Park"/></way>'
             '<way id="21"><nd ref="6"/><nd ref="7"/><tag k="highway" v="secondary"/></way>'
             '<way id="22"><nd ref="6"/><nd ref="8"/><tag k="highway" v="residential"/></way>'
             '<way id="23"><nd ref="6"/><nd ref="2"/><tag k="highway" v="tertiary"/></way></osm>')
om = resortplace.osm_marks(_osm)
check('the city reads its marks from a map: a water tower, a shell, a zoo, a park as an outline, a corner three streets meet at',
      len(om['water_tower']) == 1 and om['shell'][0][2] == 'Waikiki Shell' and len(om['park']) == 1 and len(om['park'][0][3]) == 5
      and len(om['corner']) == 1 and om['corner'][0][2] == 3 and om['zoo'][0][2] == 'City Zoo', {k: len(v) for k, v in om.items()})
