"""navgen's opt-in keep across cells (`_joined_beyond`, generate(beyond=True)): a deck that crosses a cell's edge, its only
way down a ramp in the next cell, is dropped from the cell's own field (no ground there) and kept once the wider field
shows it joined to the ground; a deck that joins nothing is never kept; land cut off at the field's edge is never added
(that is the neighbour's to mesh). Built from triangles by hand: no game files."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import navgen  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


CELL = 4096.0
crop = (0.0, 0.0, CELL, CELL)


def box_top(f, x0, y0, x1, y1, z, ground=False):
    f.add(x0, y0, z, x1, y0, z, x1, y1, z, ground)
    f.add(x0, y0, z, x1, y1, z, x0, y1, z, ground)


def slab(f, x0, y0, x1, y1, z, t=20.0):
    """A slab's top and sides (its underside left out: nothing stands under it here)."""
    box_top(f, x0, y0, x1, y1, z)
    for (ax, ay), (bx, by) in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        f.add(ax, ay, z - t, bx, by, z - t, bx, by, z)
        f.add(ax, ay, z - t, bx, by, z, ax, ay, z)


def lay(reach):
    f = navgen.Field(navgen.VOXEL_OUT, 0.66913, (crop[0] - reach, crop[1] - reach, crop[2] + reach, crop[3] + reach))
    box_top(f, -3000, -3000, CELL + 3000, CELL + 3000, 0.0, ground=True)        # (land everywhere)
    slab(f, 3200, 1000, 4600, 1400, 400.0)          # (a deck over the cell's east edge, 400 up)
    # its ramp, all in the next cell: from the deck's east end down to the land
    f.add(4600, 1000, 400, 5400, 1000, 0, 5400, 1400, 0)
    f.add(4600, 1000, 400, 5400, 1400, 0, 4600, 1400, 400)
    slab(f, 1000, 2600, 4400, 3000, 400.0)          # (a deck over the same edge that joins nothing)
    return f


def run():
    narrow = lay(navgen.MARGIN)
    g = navgen.Graph(navgen._places(narrow, navgen.HEADROOM), narrow.v, navgen.STEP, navgen.HEADROOM)
    keep = g.erode([True] * len(g.p), navgen.RADIUS)
    pieces, _label = g.pieces(keep)
    wanted = {k for k, piece in enumerate(pieces) if sum(1 for i in piece if g.p[i][5]) >= navgen.MIN_REGION}
    extra = navgen._joined_beyond(g, pieces, wanted, crop, lambda: lay(navgen.WIDE), navgen.STEP, navgen.HEADROOM, navgen.RADIUS)

    def at(k):
        P = [g.p[i] for i in pieces[k]]
        return sum(q[1] for q in P) / len(P) * g.v, sum(q[0] for q in P) / len(P) * g.v, sum(q[2] for q in P) / len(P)
    decks = [k for k in range(len(pieces)) if at(k)[2] > 300]
    joined = [k for k in decks if 1000 <= at(k)[1] <= 1400]
    alone = [k for k in decks if 2600 <= at(k)[1] <= 3000]
    check('both decks are dropped by the cell\'s own field (no ground of their own)', joined and alone and not (set(decks) & wanted),
          [at(k) for k in decks])
    check('the deck whose ramp is in the next cell is kept once the wider field is looked at', set(joined) <= extra, (joined, extra))
    check('the deck that joins nothing is not kept', not (set(alone) & extra), (alone, extra))
    check('nothing on the ground is added (land cut off at the field\'s edge is the neighbour\'s)',
          all(not any(g.p[i][5] for i in pieces[k]) for k in extra), extra)


run()
