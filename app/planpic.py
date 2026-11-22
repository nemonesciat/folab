"""A generated place's plan as a picture: every level side by side, seen from above, as an SVG (text needs no font of our own).

    svg(plan, items=(), title='', step=None)    the picture as text (open it in a browser)

Rooms are filled by what they're for (a room's own name, if it has one, is written in it), corridors pale, stairs dark with
an arrow the way down; doors are short bars across the doorway (red when locked, with the lock's level; gold when it needs a
key), the way out green, the key a gold dot, things to search brown dots. Squares are kitplan's, so this needs nothing but the
plan and its items (kitdress.Item: what, owner, link, extra; p in game units)."""
import collections
import html

from kitindex import DX

CELL = 16               # (pixels a square)
COLUMNS = 3             # (levels a row)
GAP = 40                # (between levels)
PAD = 30
COLOURS = {'entrance': '#7fb0d8', 'atrium': '#d8c27f', 'quarters': '#c9a3d6', 'small room': '#c9a3d6', 'washroom': '#9fd0d0', 'rec room': '#e0b48a',
           'mess': '#e6a07a', 'classroom': '#b8d68f', 'office': '#d98f8f', 'clinic': '#f0f0f0', 'store': '#b9a58a', 'workroom': '#a7b4c4',
           'reactor': '#e8e070', 'hall': '#d8c27f', 'far end': '#a7b4c4', 'long room': '#e6a07a', 'under a balcony': '#cfc6a4',
           'over a balcony': '#cfc6a4', 'over the hall': '#cfc6a4'}
ROOM_ELSE = '#c8c8c8'
HALL = '#ecebe6'
STAIRS = '#6b6b6b'
AIR = '#f7f3e6'


def _colour(o):
    return COLOURS.get(o.get('dress') or o['purpose'], ROOM_ELSE)


def svg(plan, items=(), title='', step=None):
    """Every level of the plan, top level first, left to right; items in game units over the plan's squares (step a square).
    Things to search are the plan's own `finds` (kitlife)."""
    found = {id(it) for it in getattr(plan, 'finds', ())}
    step = step or plan.step
    cells = {c: n for c, n in plan.cells.items()}
    # (a level that's only the air over a tall room isn't one to show)
    levels = sorted({c[2] for c in cells if c not in plan.air}, reverse=True)
    xs = [c[0] for c in cells]
    ys = [c[1] for c in cells]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    w, h = (x1 - x0 + 1) * CELL, (y1 - y0 + 1) * CELL
    cols = min(COLUMNS, len(levels))
    rows = (len(levels) + cols - 1) // cols
    width = max(PAD * 2 + cols * w + (cols - 1) * GAP, PAD * 2 + 7 * len(title or ""), 640)    # (the title and the key below fit)
    height = PAD * 2 + rows * (h + 24 + GAP) + 30

    def corner(k):
        return PAD + (k % cols) * (w + GAP), PAD + (k // cols) * (h + 24 + GAP)

    def at(c, lv_index):
        # (north up: a larger y is higher on the page)
        ox, oy = corner(lv_index)
        return ox + (c[0] - x0) * CELL, oy + 24 + (y1 - c[1]) * CELL

    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" font-family="Segoe UI, Arial, sans-serif">' % (width, height, width, height),
           '<rect width="100%" height="100%" fill="#fbfaf6"/>']
    if title:
        out.append('<text x="%d" y="%d" font-size="15" fill="#222">%s</text>' % (PAD, 18, html.escape(title)))
    door_at = collections.defaultdict(list)
    for it in items:
        if getattr(it, 'what', None) in ('door', 'exit') and isinstance(getattr(it, 'link', None), (frozenset, tuple, set)):
            door_at[it.link].append(it)
    for k, lv in enumerate(levels):
        ox, oy = corner(k)
        out.append('<text x="%d" y="%d" font-size="13" fill="#444">Level %d</text>' % (ox, oy + 16, lv))
        out.append('<rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="#ddd"/>' % (ox, oy + 24, w, h))
        for c, n in cells.items():
            if c[2] != lv:
                continue
            o = plan.owners[n]
            fill = AIR if c in plan.air else STAIRS if o['kind'] == 'void' else HALL if o['kind'] == 'hall' else _colour(o)
            x, y = at(c, k)
            out.append('<rect x="%d" y="%d" width="%d" height="%d" fill="%s" stroke="%s" stroke-width="0.5"/>' % (x, y, CELL, CELL, fill, '#aaa' if o['kind'] != 'room' else '#999'))
        # walls: a side between two owners with no way through, or onto nothing
        for c, n in cells.items():
            if c[2] != lv or c in plan.air:
                continue
            x, y = at(c, k)
            for d, (dx, dy) in enumerate(((1, 0), (0, 1), (-1, 0), (0, -1))):
                q = (c[0] + dx, c[1] + dy, c[2])
                if cells.get(q) == n or frozenset((c, q)) in plan.links:
                    continue
                if d == 0:
                    seg = (x + CELL, y, x + CELL, y + CELL)
                elif d == 1:
                    seg = (x, y, x + CELL, y)
                elif d == 2:
                    seg = (x, y, x, y + CELL)
                else:
                    seg = (x, y + CELL, x + CELL, y + CELL)
                out.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#333" stroke-width="1.6"/>' % seg)
        # stairs: an arrow from the flight's top square down
        for f in plan.flights:
            if f['level'] != lv:
                continue
            a, b = f['cells'][0], f['cells'][-1]
            (ax, ay), (bx, by) = at(a, k), at(b, k)
            out.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#fff" stroke-width="2" marker-end="url(#dn)"/>' % (bx + CELL / 2, by + CELL / 2, ax + CELL / 2, ay + CELL / 2))
        # doors
        for link, ds in door_at.items():
            a, b = tuple(link)
            if a[2] != lv or b[2] != lv:
                continue
            (ax, ay), (bx, by) = at(a, k), at(b, k)
            mx, my = (ax + bx) / 2 + CELL / 2, (ay + by) / 2 + CELL / 2
            lock = ((ds[0].extra or {}).get('props') or {}).get('lock') if getattr(ds[0], 'extra', None) else None
            colour = '#2e9d48' if ds[0].what == 'exit' else '#c9a227' if lock and lock.get('key') else '#c33' if lock else '#555'
            if a[0] != b[0]:
                out.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="4"/>' % (mx, my - CELL * 0.4, mx, my + CELL * 0.4, colour))
            else:
                out.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="4"/>' % (mx - CELL * 0.4, my, mx + CELL * 0.4, my, colour))
            if lock and not lock.get('key'):
                out.append('<text x="%d" y="%d" font-size="8" fill="#c33">%d</text>' % (mx + 3, my - 3, lock['level']))
        # ways out of the place: the way in, and a back door
        exits = plan.exits() if hasattr(plan, 'exits') else ([plan.exit] if plan.exit else [])
        for e, (c, d) in enumerate(exits):
            if c[2] != lv:
                continue
            x, y = at(c, k)
            dx, dy = DX[d]
            mx, my = x + CELL / 2 + dx * CELL / 2, y + CELL / 2 - dy * CELL / 2
            if dx:
                out.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#2e9d48" stroke-width="5"/>' % (mx, my - CELL * 0.4, mx, my + CELL * 0.4))
            else:
                out.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#2e9d48" stroke-width="5"/>' % (mx - CELL * 0.4, my, mx + CELL * 0.4, my))
            out.append('<text x="%d" y="%d" font-size="9" fill="#2e9d48">%s</text>' % (mx + 4, my + 12, 'way in' if e == 0 else 'back door'))
        # names in rooms, on the level they're mostly on
        for o in plan.rooms():
            mine = [c for c in o['cells'] if c[2] == lv and c not in plan.air]
            if not mine or len(mine) < len([c for c in o['cells'] if c not in plan.air]) / 2:
                continue
            cx = sum(at(c, k)[0] for c in mine) / len(mine) + CELL / 2
            cy = sum(at(c, k)[1] for c in mine) / len(mine) + CELL / 2
            label = o.get('name') or o.get('dress') or o['purpose']
            out.append('<text x="%d" y="%d" font-size="9" text-anchor="middle" fill="#111" stroke="#fbfaf6" stroke-width="2.5" paint-order="stroke">%s</text>' % (cx, cy, html.escape(label)))
    # things, by where they stand
    for it in items:
        what = getattr(it, 'what', '')
        if what != 'key' and id(it) not in found:
            continue
        c = (round(it.p[0] / step), round(it.p[1] / step))
        lvs = [lv for lv in levels if (c[0], c[1], lv) in cells and (c[0], c[1], lv) not in plan.air]
        if not lvs:
            continue
        lv = min(lvs, key=lambda l: abs(l * plan.rise - it.p[2]))
        x, y = at((it.p[0] / step, it.p[1] / step, lv), levels.index(lv))
        out.append('<circle cx="%.1f" cy="%.1f" r="%s" fill="%s" stroke="#333" stroke-width="0.6"/>' % (x + CELL / 2, y + CELL / 2, 4 if what == 'key' else 2.5,
                                                                                                        '#f2c200' if what == 'key' else '#8a5a2b'))
    ly = height - 22
    legend = [('#555', 'door'), ('#c33', 'locked (level)'), ('#c9a227', 'needs the key'), ('#2e9d48', 'the way out'), ('#f2c200', 'the key'),
              ('#8a5a2b', 'something to search'), (STAIRS, 'stairs, arrow down')]
    x = PAD
    for colour, words in legend:
        out.append('<rect x="%d" y="%d" width="12" height="12" fill="%s"/><text x="%d" y="%d" font-size="11" fill="#333">%s</text>' % (x, ly - 10, colour, x + 16, ly, words))
        x += 24 + 7 * len(words)
    out.insert(1, '<defs><marker id="dn" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 z" fill="#fff"/></marker></defs>')
    out.append('</svg>')
    return '\n'.join(out)
