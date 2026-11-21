"""Rooms that aren't the same room twice. A city made from a map borrows the game's interiors for its buildings (townbuild),
and the game has only so many of each kind: a hundred and sixteen to lend, five of them shops, so the same shop opened behind
nine doors. This finds the mod's places that are copies of one game place (`twins`: what they're built of, walls and floors,
is the same) and makes every copy after the first its own:

- things swapped for others of the same kind and size (`Swaps`): a desk for another desk, a chair for another chair, a shelf,
  a lamp; the same kind is the same nouns in its editor ID (`NOUNS`), the same size its bounds within `FIT` on every side,
  so it stands where the first stood, against the same wall, and the place's navmesh still fits; only things from the same
  game file, with no script of their own (a script may be a quest's);
- some of the small things on the floor and tables taken out (`THIN` of what `LOOSE` names);
- the light of another mood (`MOODS`: warm, cool, dim, dusty...), written to the cell's own lighting and taken off what the
  lighting template gave it.

Doors, the way out, anything named, locked, linked or owned, and the building itself stay as they are. The places' navmeshes
are copies of the game's: they stay, and are told they are still current (what changed is the size it was). A copy that
no longer matches the first (made its own already, or changed by hand) is left alone, so a second run does nothing."""
import collections
import json
import random
import re
import struct

import gamedata
import navbuild
import recordio

KINDS = ('STAT', 'FURN', 'MSTT', 'CONT', 'MISC', 'LIGH')
NOUNS = ('chair', 'armchair', 'stool', 'bench', 'couch', 'sofa', 'loveseat', 'desk', 'table', 'counter', 'bed', 'bunk', 'cot',
         'mattress', 'dresser', 'nightstand', 'wardrobe', 'shelf', 'shelves', 'bookcase', 'bookshelf', 'cabinet', 'locker',
         'footlocker', 'chest', 'crate', 'box', 'barrel', 'trash', 'trashcan', 'bin', 'lamp', 'light', 'rug', 'carpet', 'poster',
         'painting', 'picture', 'plant', 'planter', 'sign', 'booth', 'fridge', 'stove', 'oven', 'sink', 'toilet', 'tub',
         'mirror', 'clock', 'radio', 'television', 'tv', 'paper', 'papers', 'debris', 'rubble', 'junk', 'clutter', 'bottle',
         'can', 'cup', 'mug', 'plate', 'tray', 'book', 'books', 'magazine', 'file', 'filing', 'typewriter', 'phone', 'telephone',
         'register', 'cart', 'vending', 'jukebox', 'fan', 'curtain', 'drape', 'tire', 'pallet', 'sandbag', 'toolbox', 'workbench')
LOOSE = ('paper', 'papers', 'debris', 'rubble', 'junk', 'clutter', 'bottle', 'can', 'cup', 'mug', 'plate', 'tray', 'book', 'books',
         'magazine', 'trash', 'box', 'file')
WORD_RE = re.compile('[A-Z]+(?![a-z])|[A-Z]?[a-z]+')
# (not swapped in: a quest's own things, its editor ID led by the quest's code, MS17..., PS05...; a vault's, V...; things of
# one faction or one famous place, which say where they're from in any room)
_NOT_LED = re.compile(r'^([A-Z]{1,4}\d{1,3}|V[A-Z][a-z]|(?!NV|TV)[A-Z]{2,4}[a-z])')
_NOT_WORD = re.compile(r'restricted|vault|enclave|safehouse|brotherhood|lucky38|sierra|tenpenny|ultraluxe|gomorrah|thetops|legion|caesar'
                       r'|khan|followers|kingsschool|^test|dummy|debug|unused|quest|unique'
                       r'|imposter|crater|ncr|mojave|nevada|vegas', re.I)   # (an imposter is a far wall, not a poster)


class _NotIn:
    def search(self, edid):
        return _NOT_LED.search(edid or '') or _NOT_WORD.search(edid or '')


NOT_IN = _NotIn()
LIGHT_ROLES = frozenset(('key', 'fill', 'amb', 'rim', 'spot'))   # (a light swapped for one doing the same job in the room)
STYLE_WEIGHT = 4       # (a swap that shares a word of style with the thing, Dirty, Office, Hotel..., this many times likelier)
FIT = 0.2               # (a swap's bounds within this share of the thing's size on every side...)
FIT_LEAST = 8           # (...or within this many units, for small things)
SWAP = 0.75             # (of the things that have others of their kind, how many are swapped in a copy)
THIN = 0.3              # (of the loose things, how many a copy leaves out)
SEED = 4271
# (a mood: what ambient, directional and fog light are multiplied by, red, green, blue)
MOODS = (('warm', (1.18, 1.02, 0.80), (1.20, 1.00, 0.78), (1.10, 1.00, 0.85)),
         ('cool', (0.84, 0.96, 1.18), (0.85, 0.98, 1.20), (0.85, 0.95, 1.15)),
         ('dim', (0.70, 0.70, 0.72), (0.65, 0.65, 0.68), (0.75, 0.75, 0.78)),
         ('dusty', (1.10, 1.00, 0.82), (1.00, 0.92, 0.75), (1.25, 1.10, 0.85)),
         ('bright', (1.22, 1.20, 1.14), (1.25, 1.22, 1.15), (1.05, 1.05, 1.05)),
         ('green', (0.88, 1.12, 0.90), (0.90, 1.10, 0.90), (0.90, 1.08, 0.92)),
         ('rose', (1.12, 0.92, 0.96), (1.15, 0.92, 0.95), (1.08, 0.95, 0.98)))
INHERIT_COLOURS = 0b111   # (LNAM: ambient, directional, fog colour taken from the lighting template)


def words(edid):
    return [w.lower() for w in WORD_RE.findall(edid or '')]


def nouns(edid):
    """The kind of thing an editor ID names: its words that are things a room has (frozenset; empty: not one of them)."""
    plain = (edid or '').lower()
    return frozenset(w for w in NOUNS if w in words(edid) or (len(w) >= 5 and w in plain))


# A building's own pieces are never swapped: a whole room's shell, a hangar's, a bank of rubble. The game names how worn a
# kit's piece 'Light' or 'Heavy' (UshomIntLight01, Barracks01IntLight, NVCraftsmanRmLight), which read as a lamp: a
# house's inside was swapped for another house's of another shape and the copies stood with a wall open onto nothing
# (the user's look in nv-rs, 20 Nov 2026). The name can't tell (OffRmLight01 is a real ceiling lamp), the size can: every
# such shell is over 1,000 across, a lamp 255 at most. Anything wider than MOST either way is a building's part.
MOST = 600


def building_piece(edid, b):
    """Part of the building, not a thing in the room: never swapped, never swapped in (edid kept for a rule by name)."""
    return b is not None and max(b[3] - b[0], b[4] - b[1]) > MOST


def _bounds(gd, fid):
    ob = gd.fields(fid).get('OBND')
    return struct.unpack('<6h', ob[:12]) if ob and len(ob) >= 12 else None


def _fits(a, b):
    """Bounds b stand where bounds a did: every side within FIT of the size that way, or FIT_LEAST."""
    for k in range(3):
        size = max(a[k + 3] - a[k], 1)
        tol = max(FIT_LEAST, FIT * size)
        if abs(a[k] - b[k]) > tol or abs(a[k + 3] - b[k + 3]) > tol:
            return False
    return True


def _radius(gd, fid):
    d = gd.fields(fid).get('DATA')
    return struct.unpack_from('<I', d, 4)[0] if d and len(d) >= 8 else 0


class Swaps:
    """Every base the game has that a thing could be swapped for: by (type, the plugin it's in, its nouns)."""

    def __init__(self, gd):
        self.gd = gd
        self.by = collections.defaultdict(list)
        self.info = {}
        for fid, (i, rec) in gd.forms.items():
            if rec.tag not in KINDS:
                continue
            f = gd.plugins[i].fields(rec)
            if 'SCRI' in f or (rec.tag != 'LIGH' and 'MODL' not in f):
                continue
            edid = gd.edid(fid)
            if NOT_IN.search(edid):
                continue
            n = nouns(edid)
            if not n and rec.tag != 'LIGH':
                continue
            b = _bounds(gd, fid)
            if b is None or building_piece(edid, b):
                continue
            key = (rec.tag, i, n, 'MODL' in f)
            style = frozenset(w for w in words(edid) if w not in NOUNS and len(w) > 2)
            self.info[fid] = (key, b, _radius(gd, fid) if rec.tag == 'LIGH' else 0, n, style)
            self.by[key].append(fid)

    def options(self, fid):
        """What this base could be swapped for (not itself)."""
        got = self.info.get(fid)
        if not got:
            return []
        key, b, rad, _, _ = got
        out = []
        for o in self.by[key]:
            if o == fid:
                continue
            _, ob, orad, _, _ = self.info[o]
            if not _fits(b, ob):
                continue
            if key[0] == 'LIGH' and (not (0.7 * rad <= orad <= 1.3 * rad) or
                                     self.info[fid][4] & LIGHT_ROLES != self.info[o][4] & LIGHT_ROLES):
                continue
            out.append(o)
        return out

    def choose(self, fid, opts, rng):
        """One of the options, those sharing a word of style with the thing likelier."""
        style = self.info[fid][4]
        opts = sorted(opts)
        weights = [STYLE_WEIGHT if style & self.info[o][4] else 1 for o in opts]
        return rng.choices(opts, weights)[0]

    def loose(self, fid):
        got = self.info.get(fid)
        return bool(got and (got[0][0] == 'MISC' or (got[3] and got[3] <= set(LOOSE))))


def _kept(ch):
    """A ref nothing may change: a door's way, a name, a lock, an owner, an enable parent, a marker..."""
    return any(k in ch for k in ('tel', 'props', 'marker', 'zone', 'link', 'persistent', 'xlcm'))


def interiors(pr):
    """The mod's own interior places: their keys."""
    out = []
    for k, rec in pr.records.items():
        if not k.startswith('+') or rec.get('type') != 'CELL' or k not in pr.cells:
            continue
        flags = _flags(rec)
        if flags is not None and int(flags) & 1:
            out.append(k)
    return out


def _flags(rec):
    for s in rec['subs']:
        if s['tag'] == 'DATA' and s.get('kind') == 'struct':
            return s['fields'][0].get('value')
    return None


def _frame(gd, pr, sw, key):
    """What a place is built of (its walls, floors, doors: what this never changes), to know copies of one place."""
    rows = []
    for rk, ch in pr.cells[key].get('refs', {}).items():
        if not rk.startswith('+') or ch.get('removed') or 'base' not in ch:
            continue
        try:
            fid = gd.from_key(ch['base'])
        except Exception:
            fid = None
        if fid is not None and fid in sw.info:
            continue
        p = ch['p']
        rows.append((ch['base'], round(p[0] / 4), round(p[1] / 4), round(p[2] / 4)))
    return tuple(sorted(rows))


def twins(gd, pr, sw):
    """[[place key, ...]]: places that are copies of one game place, first made first."""
    by = collections.defaultdict(list)
    for k in interiors(pr):
        f = _frame(gd, pr, sw, k)
        if len(f) >= 4:
            by[f].append(k)
    return [sorted(v, key=lambda k: int(k[1:], 16)) for v in by.values() if len(v) > 1]


def _rgb(fields, prefix):
    return [next(f for f in fields if f.get('name') == '%s %s' % (prefix, c)) for c in ('red', 'green', 'blue')]


def mood_record(gd, rec, mood):
    """The place's record lit in a mood: XCLL's colours from what it shows now (its own or its template's), times the mood;
    LNAM no longer takes those colours from the template. None when the place has no lighting of its own to change."""
    rec = json.loads(json.dumps(rec))
    xcll = next((s for s in rec['subs'] if s['tag'] == 'XCLL'), None)
    if not xcll:
        return None
    lnam = next((s for s in rec['subs'] if s['tag'] == 'LNAM'), None)
    inherit = int(lnam['fields'][0]['value']) if lnam else 0
    tmpl = None
    ltmp = next((s for s in rec['subs'] if s['tag'] == 'LTMP'), None)
    if ltmp and ltmp.get('value') and inherit & INHERIT_COLOURS:
        try:
            t = recordio.load(gd, gd.from_key(ltmp['value']))
            tmpl = next(s for s in t['subs'] if s['tag'] == 'DATA')['fields']
        except Exception:
            tmpl = None
    _, amb, dirl, fog = mood
    parts = (('Ambient', 'Ambient', 0, amb), ('Directional', 'Light', 1, dirl), ('Fog', 'Fog', 2, fog))
    for mine, theirs, bit, mul in parts:
        dst = _rgb(xcll['fields'], mine)
        src = _rgb(tmpl, theirs) if (tmpl and inherit & (1 << bit)) else dst
        for d, s, m in zip(dst, src, mul):
            d['value'] = max(0, min(255, int(round(int(s['value']) * m))))
    if lnam:
        lnam['fields'][0]['value'] = inherit & ~INHERIT_COLOURS
    return rec


def vary_ops(gd, pr, sw, key, n):
    """Ops that make copy n (1 on) of a place its own."""
    rng = random.Random(SEED + int(key[1:], 16))
    ops = []
    # (where each thing stands: the game sometimes stands two things in one spot, and a swap mustn't make them one thing twice)
    spots = collections.defaultdict(list)
    for rk, ch in pr.cells[key].get('refs', {}).items():
        if 'base' in ch and 'p' in ch and not ch.get('removed'):
            spots[ch['base']].append(ch['p'][:3])

    def taken(base, p):
        return any(sum((a - b) ** 2 for a, b in zip(q, p[:3])) < 4.0 ** 2 for q in spots[base])

    for rk, ch in sorted(pr.cells[key].get('refs', {}).items()):
        if not rk.startswith('+') or ch.get('removed') or 'base' not in ch or _kept(ch):
            continue
        try:
            fid = gd.from_key(ch['base'])
        except Exception:
            continue
        if fid not in sw.info:
            continue
        if sw.loose(fid) and rng.random() < THIN:
            ops.append({'op': 'remove', 'cell': key, 'ref': rk})
            continue
        opts = [o for o in sw.options(fid) if not taken(gd.key(o), ch['p'])]
        if opts and rng.random() < SWAP:
            new = gd.key(sw.choose(fid, opts, rng))
            ops.append({'op': 'swap', 'cell': key, 'ref': rk, 'base': new})
            spots[new].append(ch['p'][:3])
    rec = pr.records.get(key)
    if rec:
        mood = MOODS[(n - 1 + int(key[1:], 16)) % len(MOODS)]
        lit = mood_record(gd, rec, mood)
        if lit:
            ops.append({'op': 'record', 'key': key, 'record': lit})
    return ops


def _contents(pr, key):
    """What a place has and how it's lit: the same in a copy as yet untouched as in the first."""
    rec = pr.records.get(key) or {'subs': []}
    light = [json.dumps(s.get('fields')) for s in rec['subs'] if s['tag'] in ('XCLL', 'LNAM')]
    return light + sorted((ch['base'], round(ch['p'][0] / 4), round(ch['p'][1] / 4), round(ch['p'][2] / 4))
                          for rk, ch in pr.cells[key].get('refs', {}).items() if rk.startswith('+') and 'base' in ch and not ch.get('removed'))


def vary(gd, pr, apply=True, sw=None, merge=False, label='Make repeated rooms their own'):
    """Every copy after the first of each place made its own, as one Undo. A copy that is no longer the same as the first
    (made its own before, or changed by hand) is left alone. Returns a report."""
    sw = sw or Swaps(gd)
    groups = twins(gd, pr, sw)
    ops, made, current = [], {}, {}
    for g in groups:
        first = _contents(pr, g[0])
        for n, key in enumerate(g):
            if n == 0 or _contents(pr, key) != first:
                continue
            mesh = pr.navmesh.get(key)
            if mesh and mesh.get('sig') == navbuild.signature(navbuild.place_refs(gd, pr, key)):
                current[key] = mesh
            o = vary_ops(gd, pr, sw, key, n)
            ops += o
            made[key] = n
    rep = {'groups': len(groups), 'places': len(made), 'swapped': sum(1 for o in ops if o['op'] == 'swap'),
           'removed': sum(1 for o in ops if o['op'] == 'remove'), 'lit': sum(1 for o in ops if o['op'] == 'record'),
           'largest': max((len(g) for g in groups), default=0)}
    if not apply or not ops:
        return rep
    pr.apply(label, ops, merge=merge)
    nav = [{'op': 'navmesh', 'cell': k, 'mesh': dict(m, sig=navbuild.signature(navbuild.place_refs(gd, pr, k)))}
           for k, m in current.items()]
    if nav:
        pr.apply(label, nav, merge=True)
    rep['navmeshes'] = len(nav)
    return rep


def _spot(base, p):
    return (base, round(p[0] / 8), round(p[1] / 8), round(p[2] / 8))


def sources(gd, pr, keys=None):
    """{place key: the game's interior it is a copy of}: the game place most of its things stand in, where it is most of
    them (a place built some other way, a vault or a ship, has none)."""
    keys = interiors(pr) if keys is None else keys
    want = collections.defaultdict(list)
    for k in keys:
        for rk, ch in pr.cells[k].get('refs', {}).items():
            if rk.startswith('+') and 'base' in ch and 'p' in ch and not ch.get('removed'):
                want[_spot(ch['base'], ch['p'])].append(k)
    votes = collections.defaultdict(collections.Counter)
    game = {n.lower() for n in gamedata.OFFICIAL}
    for c in gd.interiors:
        if gd.names[c >> 24] not in game:
            continue             # (only the game's own: a mod's plugin may hold copies of its places)
        for r in gd.refs(c):
            if r['base'] and r['pos'] and r['base'] in gd.forms:
                for k in want.get(_spot(gd.key(r['base']), r['pos']), ()):
                    votes[k][c] += 1
    out = {}
    for k in keys:
        if votes[k]:
            c, n = votes[k].most_common(1)[0]
            mine = sum(1 for rk, ch in pr.cells[k].get('refs', {}).items() if rk.startswith('+') and 'base' in ch and not ch.get('removed'))
            if n >= 0.5 * mine:
                out[k] = c
    return out


def mend(gd, pr, apply=True, label='Rooms: the buildings put back', sw=None):
    """What an earlier run swapped that today's rules wouldn't put back as the game has it, every place, one Undo: the copy's
    thing standing exactly where the game's piece does, of another base, gets the piece's base again, where the piece is
    part of the building (`building_piece`), or what stands there now is nothing a swap may bring in (a Strip wall's far
    model taken for a poster). Fixed things only (STAT, MSTT): a container filled since (lootplace) is left. Returns
    {place key: [(the game piece's editor ID, what stood there)]}."""
    sw = sw or Swaps(gd)
    fixed = ('STAT', 'MSTT')
    found = {}
    ops = []
    for k, c in sources(gd, pr).items():
        here = {}
        for rk, ch in pr.cells[k].get('refs', {}).items():
            if rk.startswith('+') and 'base' in ch and 'p' in ch and not ch.get('removed') and not ch['base'].startswith('+'):
                here.setdefault(tuple(round(v, 2) for v in ch['p']), []).append((rk, ch['base']))
        for r in gd.refs(c):
            if not r['base'] or not r['pos'] or not r['rot'] or r['base'] not in gd.forms or gd.forms[r['base']][1].tag not in fixed:
                continue
            want = gd.key(r['base'])
            p = tuple(round(v, 2) for v in [round(v, 4) for v in list(r['pos']) + list(r['rot'])])
            there = here.get(p, [])
            if not there or any(b == want for _rk, b in there):
                continue
            rk, b = there[0]
            try:
                bf = gd.from_key(b)
            except Exception:
                continue
            if bf not in gd.forms or gd.forms[bf][1].tag not in fixed:
                continue
            edid = gd.edid(r['base'])
            if not (building_piece(edid, _bounds(gd, r['base'])) or bf not in sw.info):
                continue
            ops.append({'op': 'swap', 'cell': k, 'ref': rk, 'base': want})
            found.setdefault(k, []).append((edid, gd.edid(bf)))
    if apply and ops:
        current = {k: m for k, m in pr.navmesh.items() if k in found and m.get('sig') == navbuild.signature(navbuild.place_refs(gd, pr, k))}
        pr.apply(label, ops)
        nav = [{'op': 'navmesh', 'cell': k, 'mesh': dict(m, sig=navbuild.signature(navbuild.place_refs(gd, pr, k)))}
               for k, m in current.items()]
        if nav:
            pr.apply(label, nav, merge=True)
    return found
