"""One picture sheet a plant (plantsheet.py): a shrub's leaves, flowers and stems side by side in one texture, so the
whole plant is one shape, one thing for the game to draw.

Each look over a picture of its own is a shape of its own, and each shape is a draw: a FOLab shrub was three (its stems
and two kinds of leaf spray), a ti plant or heliconia two. Round the Castaway's start the low shrubs alone were 3,909
draws of 12,693 (Freeside's gate in the game draws 2,196 in all: the user had 12 fps, 20 Nov 2026). Put on one sheet,
`modelmake.make` makes every look one shape, since they share the picture.

  - SHEETED: the pieces done so (every look either drawn once across its part, or a stem: a stick look with a 'band',
    whose picture repeats down it). Trees and palms aren't: their bark repeats both ways;
  - the sheet (`compose`): each picture scaled to the sheet's height, side by side in strips, the width made a power of
    two with clear space; `strips` tells the encoder (dds.encode) which strip is a stem (halved plainly: it stays solid
    far off) and which are leaves (each keeps its own share over the cut, its own border clear);
  - each look's 'sheet' (u0, u1): modelmake moves its texture coordinates across onto its strip; down stays as it was,
    so a stem's picture still repeats down it (its strip is the sheet's whole height)."""
import modelsets as ms
import plantsplit  # noqa: F401  (its pieces, the clumps' shrubs among them, are in modelsets.PIECES first)
import texpaint as tp

SHEETED = ('shrub_low_a', 'shrub_low_b', 'shrub_tall_a', 'shrub_tall_b', 'shrub_tall_c', 'ti_red', 'ti_green', 'heliconia',
           'hibiscus', 'banana')
H = 256
_plan = {}


def _name(piece):
    return 'jungle/sheet_' + piece


def _by_path():
    return {ms.tex_path(n).lower(): n for n in ms.TEXTURES}


def _canvas(name):
    c = ms.TEXTURES[name]()
    return c


def plan(piece, original):
    """[(texture name, x0, x1, is a stem)] across the sheet, and its width; None where the piece can't be sheeted."""
    if piece in _plan:
        return _plan[piece]
    desc = original()
    paths = _by_path()
    names = []
    for lk in desc['looks'].values():
        if (lk.get('tile') and not lk.get('band')) or not lk.get('alpha'):
            _plan[piece] = None
            return None
        n = paths.get(lk['tex'].lower())
        if n is None:
            _plan[piece] = None
            return None
        if n not in names:
            names.append(n)
    out, x = [], 0
    for n in names:
        c = _canvas(n)
        w = max(4, int(round(c.w * H / float(c.h) / 4.0)) * 4)
        out.append((n, x, x + w, bool(getattr(c, 'plain_halving', False))))
        x += w
    width = 1
    while width < x:
        width *= 2
    _plan[piece] = (out, width)
    return _plan[piece]


def compose(piece):
    """The sheet as a texpaint canvas, with its strips."""
    strips, width = _plan[piece]
    first = _canvas(strips[0][0])
    c = tp.Canvas(width, H, clear=(96, 110, 70))
    for n, x0, x1, _stem in strips:
        src = _canvas(n)
        sw, sh = src.w, src.h
        w = x1 - x0
        for y in range(H):
            sy = min(sh - 1, int(y * sh / float(H)))
            for x in range(w):
                sx = min(sw - 1, int(x * sw / float(w)))
                i, j = y * width + x0 + x, sy * sw + sx
                c.rgb[i] = src.rgb[j]
                c.ht[i] = src.ht[j]
                c.a[i] = src.a[j] if src.a is not None else 1.0
    c.strips = [(x0, x1, stem, not stem) for _n, x0, x1, stem in strips]
    return c


def _wrap(piece, original):
    def describe():
        desc = original()
        p = plan(piece, original)
        if not p:
            return desc
        strips, width = p
        at = {n: (x0 / float(width), x1 / float(width)) for n, x0, x1, _s in strips}
        paths = _by_path()
        looks = {}
        for k, lk in desc['looks'].items():
            n = paths[lk['tex'].lower()]
            looks[k] = dict(lk, tex=ms.tex_path(_name(piece)), normal=ms.tex_path(_name(piece), True), sheet=at[n], alpha=True)
        return dict(desc, looks=looks)
    return describe


for _p in SHEETED:
    if _p in ms.PIECES and not ms.PIECES[_p].get('sheeted'):
        _orig = ms.PIECES[_p]['describe']
        ms.PIECES[_p]['describe'] = _wrap(_p, _orig)
        ms.PIECES[_p]['sheeted'] = True
        ms.TEXTURES[_name(_p)] = (lambda p=_p: compose(p))
