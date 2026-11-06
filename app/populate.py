"""Populate: people and creatures for a place, learnt from who the game puts in places like it.

survey() reads every place the game has once: its main kit of building pieces (the mesh folder most of its statics come
from), the words of its name, its owner, and who stands in it. plan() finds the game's places most like the one asked
for, takes one of them as the model (so the group is one the game itself would have, not a mix), and proposes who, how
many (the game's own crowding for that floor space) and how hard. Nothing changes until apply(), which makes everything
as one undo step.

Only people and creatures the game means to be many: levelled ones, ones it places more than once, or one of several
with the same name; never its one-of-a-kind characters, its dead, or those with a script of their own (those belong to quests). The game never places
a levelled list itself: it places a character whose template is the list. Levelled here does the same."""
import json
import math
import random
import re
import statistics
import struct

import actors
import land as landmod
import navbuild
import recordio
import tes4

BUSY = {'few': 0.5, 'usual': 1.0, 'many': 1.7}
MAX_PEOPLE = 30
SIMILAR = 14                    # (how many of the game's places a plan learns from)
SPACING = 90.0                  # (units apart they stand, to start with)
CREATURE, PERSON = 'creature', 'person'
# words that say what a place is: they count for more than the rest of its name
KIND_WORDS = {'cave', 'mine', 'vault', 'sewer', 'metro', 'tunnel', 'casino', 'hotel', 'motel', 'house', 'home', 'shack', 'office', 'factory', 'plant',
              'bunker', 'base', 'camp', 'fort', 'store', 'shop', 'saloon', 'bar', 'clinic', 'hospital', 'station', 'warehouse', 'garage', 'school', 'church'}
NEVER = ('dead', 'corpse', 'test', 'dummy', 'companion', 'follower', 'audiotemplate', 'template')
BED = ('bed', 'mattress', 'cot', 'sleepingbag', 'bedroll')


def _words(text):
    """'GSProspectorSaloonInterior01' as {'prospector', 'saloon', 'interior'}."""
    return {w.lower() for w in re.findall(r'[A-Z]?[a-z]{2,}', text)} - {'interior', 'int', 'ext', 'exterior', 'the', 'nv'}


def _folder(model):
    parts = model.lower().replace('/', '\\').split('\\')
    return '\\'.join(parts[:2]) if len(parts) > 2 else parts[0]


class Survey:
    """Every place in the game and who stands in it."""

    def __init__(self, gd):
        self.gd = gd
        self.placed = {}            # base -> how many times the game places it
        self.seen_xlcm = {}         # base -> the difficulties its levelled refs have
        self.places = []
        self.actors = {}
        self.bases = {}             # base -> (type, mesh folder), asked once
        self.named = {}             # lower name -> how many characters and creatures have it
        for f, (i, r) in gd.forms.items():
            if r.tag in ('NPC_', 'CREA'):
                n = tes4.zstr(gd.plugins[i].fields(r).get('FULL', b'')).lower()
                if n:
                    self.named[n] = self.named.get(n, 0) + 1
        for cell, refs in gd.cell_refs.items():
            for rf, (i, r) in refs.items():
                if r.tag in ('ACHR', 'ACRE') and not r.flags & tes4.DELETED:
                    f = gd.plugins[i].fields(r)
                    if 'NAME' in f:
                        b = gd.to_global(i, struct.unpack('<I', f['NAME'])[0])
                        self.placed[b] = self.placed.get(b, 0) + 1
                        if 'XLCM' in f:
                            self.seen_xlcm.setdefault(b, []).append(struct.unpack('<i', f['XLCM'])[0])
        for cell in gd.interiors:
            self.places.append(self.read_place(cell))

    def features(self, cell):
        """Its main kit, the words of its name, its owner."""
        gd = self.gd
        folders = {}
        for r in gd.refs(cell):
            if r['base'] in gd.forms and gd.forms[r['base']][1].tag == 'STAT':
                b = self.bases.get(r['base'])
                if b is None:
                    b = self.bases[r['base']] = _folder(gd.describe(r['base'])[3])
                folders[b] = folders.get(b, 0) + 1
        f = gd.fields(cell)
        i = gd.forms[cell][0]
        words = _words(tes4.zstr(f.get('EDID', b'')) + ' ' + tes4.zstr(f.get('FULL', b'')))
        owner = gd.to_global(i, struct.unpack('<I', f['XOWN'])[0]) if len(f.get('XOWN', b'')) == 4 else None
        return {'folder': max(folders, key=folders.get) if folders else '', 'words': words, 'owner': owner}

    def read_place(self, cell):
        gd = self.gd
        roster = []
        for rf, (i, r) in gd.cell_refs.get(cell, {}).items():
            if r.tag in ('ACHR', 'ACRE') and not r.flags & tes4.DELETED:
                f = gd.plugins[i].fields(r)
                if 'NAME' in f:
                    roster.append(gd.to_global(i, struct.unpack('<I', f['NAME'])[0]))
        return dict(self.features(cell), cell=cell, roster=roster, area=None)

    def actor(self, b):
        """What a plan needs to know of a base form, or None if it's not one to place freely."""
        if b in self.actors:
            return self.actors[b]
        out = self._read_actor(b)
        self.actors[b] = out
        return out

    def _read_actor(self, b):
        gd = self.gd
        if b not in gd.forms or gd.forms[b][1].tag not in ('NPC_', 'CREA'):
            return None
        i, rec = gd.forms[b]
        f = gd.plugins[i].fields(rec)
        edid = tes4.zstr(f.get('EDID', b''))
        low = edid.lower()
        if any(w in low for w in NEVER) or len(f.get('ACBS', b'')) < 24:
            return None
        flags, level, tflags = struct.unpack_from('<I', f['ACBS'])[0], struct.unpack_from('<h', f['ACBS'], 8)[0], struct.unpack_from('<H', f['ACBS'], 22)[0]
        if flags & 0x2 or flags & 0x4:                   # (essential, or a character-creation face)
            return None
        tp = gd.to_global(i, struct.unpack('<I', f['TPLT'])[0]) if len(f.get('TPLT', b'')) == 4 else None
        levelled = self._levelled(tp) if tp else False
        script = 'SCRI' in f and not tflags & 0x200
        placed = self.placed.get(b, 0)
        name = tes4.zstr(f.get('FULL', b''))
        if not name and tp:
            first = actors._first_in_list(gd, tp, (rec.tag,))
            name = tes4.zstr(gd.fields(first).get('FULL', b'')) if first else ''
        # (one the game means to be many: levelled, placed again and again, or one of several with the same name, like
        # "Goodsprings Settler")
        if script or not (levelled or placed >= 2 or self.named.get(name.lower(), 0) >= 3):
            return None
        if not name:
            name = edid
        mult = bool(flags & 0x80)
        ai = f.get('AIDT', b'')
        return {'base': b, 'key': gd.key(b), 'tag': rec.tag, 'kind': CREATURE if rec.tag == 'CREA' else PERSON, 'edid': edid, 'name': name, 'levelled': levelled,
                'level': None if levelled else (round(level / 1000, 2) if mult else level), 'mult': mult, 'aggression': ai[0] if ai else 0, 'tflags': tflags}

    def _levelled(self, fid, depth=0):
        gd = self.gd
        if fid not in gd.forms or depth > 6:
            return False
        i, r = gd.forms[fid]
        if r.tag.startswith('LVL'):
            return True
        f = gd.plugins[i].fields(r)
        if len(f.get('TPLT', b'')) == 4 and len(f.get('ACBS', b'')) >= 24:
            return self._levelled(gd.to_global(i, struct.unpack('<I', f['TPLT'])[0]), depth + 1)
        return False


_survey = {'gd': None, 'it': None}


def survey(gd):
    if _survey['gd'] is not gd:
        _survey.update(gd=gd, it=Survey(gd))
    return _survey['it']


# ---------- the place ----------

def _nav_area(verts, tris):
    """(floor area, [(area, triangle)] of the walkable triangles)"""
    out, total = [], 0.0
    for k in range(0, len(tris), 3):
        a, b, c = tris[k:k + 3]
        A, B, C = verts[a * 3:a * 3 + 3], verts[b * 3:b * 3 + 3], verts[c * 3:c * 3 + 3]
        u = [B[n] - A[n] for n in range(3)]
        v = [C[n] - A[n] for n in range(3)]
        cross = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        size = math.sqrt(sum(x * x for x in cross)) / 2
        if size > 1 and abs(cross[2]) / (2 * size) > 0.75:      # (nearly flat)
            out.append((size, (A, B, C)))
            total += size
    return total, out


def floors(gd, pr, ckey):
    """Where someone can stand in a place inside: the mod's navmesh, the game's, or one worked out from its pieces now
    (not kept). (source, area, triangles)."""
    s = navbuild.shape(gd, pr, ckey)
    if s.get('source'):
        area, tris = _nav_area(s['verts'], s['tris'])
        return s['source'], area, tris
    try:
        data, _report = navbuild.generate(gd, pr, ckey)
    except navbuild.NavError:
        return None, 0.0, []
    area, tris = _nav_area([c for v in data['verts'] for c in v], [c for t in data['tris'] for c in t[:3]])
    return 'worked out', area, tris


def _height_fn(gd, pr, cell):
    world = gd.ext_cells[cell]
    x, y = gd.cell_grid(cell)
    mine = pr.land.get(gd.key(cell)) if pr else None
    if mine:
        h = mine['h']
    else:
        e = gd.land_at(world, x, y)
        h = landmod.heights_of(dict(tes4.iter_subrecords(gd.plugins[e[0]].data(e[1])))['VHGT']) if e else None
    if not h:
        return None

    def at(px, py):
        fx, fy = (px - x * 4096) / 128, (py - y * 4096) / 128
        c0, r0 = min(31, int(fx)), min(31, int(fy))
        tx, ty = fx - c0, fy - r0
        p = lambda r, c: h[r * 33 + c]
        return (p(r0, c0) * (1 - tx) + p(r0, c0 + 1) * tx) * (1 - ty) + (p(r0 + 1, c0) * (1 - tx) + p(r0 + 1, c0 + 1) * tx) * ty
    return at


def _water_level(gd, cell):
    f = gd.fields(cell)
    if len(f.get('XCLW', b'')) == 4:
        v = struct.unpack('<f', f['XCLW'])[0]
        if v < 1e30:
            return v
    w = gd.fields(gd.ext_cells[cell])
    return struct.unpack_from('<f', w['DNAM'])[0] if len(w.get('DNAM', b'')) >= 4 else -1e9


def _others(gd, pr, ckey):
    """Where things already stand in a place, as the mod leaves it: actors keep clear of these."""
    out = []
    mine = (pr.cells.get(ckey) or {}).get('refs', {}) if pr else {}
    if not ckey.startswith('+'):
        for r in gd.refs(gd.from_key(ckey)):
            if r['pos'] and r['base'] in gd.forms and gd.forms[r['base']][1].tag in ('ACHR', 'NPC_', 'CREA', 'FURN') and not (mine.get(gd.key(r['ref'])) or {}).get('removed'):
                out.append(r['pos'][:2])
    out += [c['p'][:2] for k, c in mine.items() if k.startswith('+') and c.get('p')]
    return out


def spots(gd, pr, ckey, count, rng):
    """Up to count (x, y, z, turn) spots spread over a place's floor, or over the ground of a square outside."""
    cell = None if ckey.startswith('+') else gd.from_key(ckey)
    others = _others(gd, pr, ckey)
    out = []

    def free(x, y, gap):
        return all((x - a) ** 2 + (y - b) ** 2 > gap * gap for a, b in others + [(s[0], s[1]) for s in out])
    if cell in gd.ext_cells:
        at = _height_fn(gd, pr, cell)
        if not at:
            return []
        gx, gy = gd.cell_grid(cell)
        water = _water_level(gd, cell)
        for tries in range(count * 60):
            x, y = gx * 4096 + 200 + rng.random() * 3696, gy * 4096 + 200 + rng.random() * 3696
            z = at(x, y)
            # (not where it's steep, or under water)
            if z > water + 16 and max(abs(at(x + 64, y) - z), abs(at(x, y + 64) - z)) < 48 and free(x, y, SPACING * 2):
                out.append((round(x, 1), round(y, 1), round(z, 1), round(rng.random() * 6.283, 3)))
                if len(out) >= count:
                    break
        return out
    _source, area, tris = floors(gd, pr, ckey)
    if not tris:
        return []
    weights = [t[0] for t in tris]
    for gap in (SPACING, SPACING * 0.6, SPACING * 0.3, 8.0):
        for tries in range(count * 40):
            if len(out) >= count:
                return out
            _a, (A, B, C) = rng.choices(tris, weights)[0]
            u, v = rng.random(), rng.random()
            if u + v > 1:
                u, v = 1 - u, 1 - v
            p = [A[n] + (B[n] - A[n]) * u + (C[n] - A[n]) * v for n in range(3)]
            if free(p[0], p[1], gap):
                out.append((round(p[0], 1), round(p[1], 1), round(p[2], 1), round(rng.random() * 6.283, 3)))
    return out


def zone(gd, pr, ckey):
    """The encounter zone a place has: its name and the lowest level things in it scale to."""
    if ckey.startswith('+'):
        rec = pr.records.get(ckey)
        k = recordio.field(rec, 'XEZN') if rec else ''
        z = gd.from_key(k) if k and not k.startswith('+') else None
    else:
        cell = gd.from_key(ckey)
        f = gd.fields(cell)
        if 'XEZN' not in f and cell in gd.ext_cells:
            f = gd.fields(gd.ext_cells[cell])
            cell = gd.ext_cells[cell]
        z = gd.to_global(gd.forms[cell][0], struct.unpack('<I', f['XEZN'])[0]) if len(f.get('XEZN', b'')) == 4 else None
    if z is None or z not in gd.forms:
        return None
    d = gd.fields(z).get('DATA', b'')
    return {'name': gd.edid(z), 'min': d[5] if len(d) >= 6 else 0}


def has_bed(gd, pr, ckey):
    keys = []
    if not ckey.startswith('+'):
        keys += [r['base'] for r in gd.refs(gd.from_key(ckey)) if r['base'] in gd.forms and gd.forms[r['base']][1].tag == 'FURN']
    for k, c in (pr.cells.get(ckey) or {}).get('refs', {}).items():
        b = c.get('base')
        if b and not b.startswith('+') and gd.from_key(b) in gd.forms and gd.forms[gd.from_key(b)][1].tag == 'FURN':
            keys.append(gd.from_key(b))
    return any(any(w in gd.edid(f).lower() for w in BED) for f in keys)


def place_info(gd, pr, ckey):
    """What the page shows of a place before anything is asked."""
    name = _place_name(gd, pr, ckey)
    out = {'cell': ckey, 'name': name, 'zone': zone(gd, pr, ckey)}
    cell = None if ckey.startswith('+') else gd.from_key(ckey)
    if cell is None or cell not in gd.ext_cells:
        s = navbuild.shape(gd, pr, ckey)
        out['navmesh'] = s.get('source')
    return out


def _place_name(gd, pr, ckey):
    if ckey.startswith('+'):
        rec = pr.records.get(ckey)
        return (recordio.field(rec, 'FULL') or recordio.field(rec, 'EDID')) if rec else ckey
    cell = gd.from_key(ckey)
    f = gd.fields(cell)
    name = tes4.zstr(f.get('FULL', b'')) or tes4.zstr(f.get('EDID', b''))
    if cell in gd.ext_cells:
        x, y = gd.cell_grid(cell)
        return '%s (%d, %d)' % (name or gd.edid(gd.ext_cells[cell]), x, y)
    return name or ckey


# ---------- what to propose ----------

def _score(me, other):
    s = 0.0
    if me['folder'] and me['folder'] == other['folder']:
        s += 3
    elif me['folder'] and me['folder'].split('\\')[-1] == other['folder'].split('\\')[-1]:
        s += 1.5
    share = me['words'] & other['words']
    s += sum(4.0 if w in KIND_WORDS else 0.5 for w in share)
    if me['owner'] and me['owner'] == other['owner']:
        s += 1
    return s


def _target_features(gd, pr, sv, ckey):
    """A place's features as the mod leaves it: its own record's name, its pieces' main folder."""
    if ckey.startswith('+'):
        rec = pr.records.get(ckey)
        if not rec:
            raise ValueError('That place is no longer in your mod.')
        words = _words(recordio.field(rec, 'EDID') + ' ' + recordio.field(rec, 'FULL'))
        owner = None
    else:
        f = sv.features(gd.from_key(ckey))
        words, owner = f['words'], f['owner']
    folders = {}
    if not ckey.startswith('+'):
        for r in gd.refs(gd.from_key(ckey)):
            if r['base'] in gd.forms and gd.forms[r['base']][1].tag == 'STAT':
                b = sv.bases.get(r['base']) or _folder(gd.describe(r['base'])[3])
                folders[b] = folders.get(b, 0) + 1
    for _k, c in (pr.cells.get(ckey) or {}).get('refs', {}).items():
        b = c.get('base') or ''
        if b and not b.startswith('+') and gd.from_key(b) in gd.forms and gd.forms[gd.from_key(b)][1].tag == 'STAT':
            m = gd.describe(gd.from_key(b))[3]
            folders[_folder(m)] = folders.get(_folder(m), 0) + 1
    return {'folder': max(folders, key=folders.get) if folders else '', 'words': words, 'owner': owner}


def _wanted(a, who):
    if who == 'people':
        return a['kind'] == PERSON
    if who == 'creatures':
        return a['kind'] == CREATURE
    return True


def _neighbours(gd, sv, cell):
    """Outside: the squares round it as 'places like it', nearest first, those with someone in them."""
    world = gd.ext_cells[cell]
    x, y = gd.cell_grid(cell)
    grid = gd.grid(world)
    out = []
    for reach in range(0, 13):
        for dx in range(-reach, reach + 1):
            for dy in range(-reach, reach + 1):
                if max(abs(dx), abs(dy)) != reach:
                    continue
                c = grid.get((x + dx, y + dy))
                if c is None:
                    continue
                roster = [r['base'] for r in gd.refs(c) if r['type'] in ('ACHR', 'ACRE') and r['base']]
                if roster:
                    out.append({'cell': c, 'roster': roster, 'score': 13.0 - reach})
        if len(out) >= SIMILAR:
            break
    return out[:SIMILAR]


def plan(gd, pr, br, body):
    """Who to put in a place. body: cell, who ('all'|'people'|'creatures'), busy, difficulty (0..3 or 'auto'),
    levelled, live, seed, and max level (fixed-level ones above it are left out). Changes nothing."""
    ckey = body['cell']
    sv = survey(gd)
    rng = random.Random(body.get('seed', 1))
    who = body.get('who', 'all')
    cell = None if ckey.startswith('+') else gd.from_key(ckey)
    outside = cell in gd.ext_cells
    notes = []
    max_level = body.get('max_level')
    # (the base game's, and those of the place's own file: no Sierra Madre ghost people in a Mojave saloon)
    files = {0} if cell is None else {0, cell >> 24}
    allowed = lambda a: a and a['base'] >> 24 in files and _wanted(a, who) and (max_level in (None, '') or a['levelled'] or a['mult'] or a['level'] is None or a['level'] <= int(max_level))
    if outside:
        similar = _neighbours(gd, sv, cell)
    else:
        me = _target_features(gd, pr, sv, ckey)
        similar = []
        for p in sv.places:
            if p['cell'] == cell:
                continue
            s = _score(me, p)
            if s > 0 and any(allowed(sv.actor(b)) for b in p['roster']):
                similar.append(dict(p, score=s))
        similar.sort(key=lambda p: -p['score'])
        if not similar:                                 # (nothing like it: anywhere inside with someone suitable)
            similar = [dict(p, score=0.1) for p in sv.places if any(allowed(sv.actor(b)) for b in p['roster'])]
            rng.shuffle(similar)
            notes.append('The game has no place much like this one, so this is learnt from places chosen at random.')
        similar = similar[:SIMILAR]
    similar = [p for p in similar if any(allowed(sv.actor(b)) for b in p['roster'])]
    if not similar:
        return {'rows': [], 'notes': ['The game has no one suitable for places like this.'], 'learnt': [], 'place': _place_name(gd, pr, ckey), 'count': 0}

    # how many: the game's own crowding (people per floor space, inside; per square, outside), for this one's size
    counts = [sum(1 for b in p['roster'] if allowed(sv.actor(b))) for p in similar]
    busy = BUSY.get(body.get('busy', 'usual'), 1.0)
    source, area = None, 0.0
    if outside:
        target = statistics.median(counts) * busy
    else:
        source, area, _t = floors(gd, pr, ckey)
        dens = []
        for p in similar[:8]:
            if p['area'] is None:
                p_area = 0.0
                for i, rec in gd.navmeshes(p['cell']):
                    import navmesh as N
                    m = N.read_navm(gd.plugins[i].data(rec))
                    p_area += _nav_area([c for v in m['verts'] for c in v], [c for t in m['tris'] for c in t[:3]])[0]
                p['area'] = p_area
                for q in sv.places:
                    if q['cell'] == p['cell']:
                        q['area'] = p_area
            n = sum(1 for b in p['roster'] if allowed(sv.actor(b)))
            if p['area'] > 0 and n:
                dens.append(n / p['area'])
        if not area:
            notes.append('This place has no floor FOLab can find, so nobody can be placed yet: add some floor pieces, or a navmesh in the Kit tab.')
            target = statistics.median(counts) * busy
        elif dens:
            target = statistics.median(dens) * area * busy
        else:
            target = statistics.median(counts) * busy
    target = max(1, min(MAX_PEOPLE, int(round(target))))

    # the model: one of the most alike, whose group is taken whole; the others fill any gap
    weights = [p['score'] ** 2 for p in similar]
    model = rng.choices(similar, weights)[0]
    roster = [b for b in model['roster'] if allowed(sv.actor(b))]
    rng.shuffle(roster)
    pool = {}
    for p, w in zip(similar, weights):
        for b in p['roster']:
            if allowed(sv.actor(b)):
                pool[b] = pool.get(b, 0) + w
    chosen = {}
    for k in range(target):
        if k < len(roster):
            b = roster[k]
        elif rng.random() < 0.8:
            b = rng.choice(roster)
        else:
            b = rng.choices(list(pool), list(pool.values()))[0]
        chosen[b] = chosen.get(b, 0) + 1

    # how hard
    diff = body.get('difficulty', 'auto')
    rows = []
    for b, n in sorted(chosen.items(), key=lambda kv: -kv[1]):
        a = sv.actor(b)
        seen = sv.seen_xlcm.get(b) or []
        x = None
        if a['levelled']:
            x = int(diff) if diff not in ('auto', None, '') else (max(set(seen), key=seen.count) if seen else None)
        rows.append({'base': a['key'], 'name': a['name'], 'edid': a['edid'], 'kind': a['kind'], 'levelled': a['levelled'], 'level': a['level'], 'mult': a['mult'],
                     'aggression': a['aggression'], 'count': n, 'xlcm': x})
    learnt = [_place_name(gd, pr, gd.key(p['cell'])) for p in similar[:6]]
    out = {'place': _place_name(gd, pr, ckey), 'cell': ckey, 'rows': rows, 'count': target, 'model': _place_name(gd, pr, gd.key(model['cell'])), 'learnt': learnt,
           'learnt_n': len(similar), 'zone': zone(gd, pr, ckey), 'floor': 'ground' if outside else source, 'area': round(area / (128 * 128), 1), 'notes': notes,
           'bed': has_bed(gd, pr, ckey), 'seed': body.get('seed', 1), 'outside': outside}
    if not outside and source != 'mod' and source != 'game' and area:
        out['notes'].append('This place has no navmesh yet: they\'ll be placed on its floor but won\'t walk about until it has one (Kit tab).')
    return out


# ---------- making it so ----------

def _stem(text):
    return ''.join(w.capitalize() for w in re.sub(r'[^A-Za-z0-9]+', ' ', text).split())[:32]


def _resident(gd, pr, br, base_key, edid, packages):
    """A character of the mod's own that lives here: a copy of a game one, its AI packages these (the template's left out)."""
    import api_characters as ac
    rec = json.loads(json.dumps(ac.get_record(gd, pr, base_key)))
    recordio.set_field(rec, 'EDID', edid, label='Editor ID')
    rec['subs'] = [s for s in rec['subs'] if s['tag'] != 'PKID']
    if rec['type'] in ('NPC_', 'CREA'):
        ac.set_num(rec, 'ACBS', 'Template flags', ac.num(rec, 'ACBS', 'Template flags') & ~0x20)
    for k in packages:
        ac.insert(rec, {'tag': 'PKID', 'label': 'AI package', 'kind': 'F', 'value': k})
    rec['src'] = rec.get('src') or ''
    rec['copied_from'] = base_key
    return rec


def _level_of(gd, pr, key):
    import api_characters as ac
    r = ac.get_record(gd, pr, key)
    if ac.num(r, 'ACBS', 'Flags') & 0x80:
        return 1
    return max(1, min(100, ac.num(r, 'ACBS', 'Level', 1)))


def _levelled_list(gd, pr, br, rows, kind, stem):
    """A levelled list of these (each at its own level) and a character whose template it is: (list record, actor record)."""
    import api_characters as ac
    tag, wrap_tag = ('LVLC', 'CREA') if kind == CREATURE else ('LVLN', 'NPC_')
    item = 'Creature' if kind == CREATURE else 'Character'
    entries = sorted(rows, key=lambda r: _level_of(gd, pr, r['base']))
    subs = [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': ac.unique_edid(br, pr, 'FOLab%sList%s' % (stem, item))},
            {'tag': 'OBND', 'label': 'Bounds', 'kind': 'struct', 'fields': [{'name': n, 'code': 'h', 'value': 0} for n in ('X1', 'Y1', 'Z1', 'X2', 'Y2', 'Z2')]},
            {'tag': 'LVLD', 'label': 'Chance none', 'kind': 'struct', 'fields': [{'name': 'Percent', 'code': 'B', 'value': 0}]},
            {'tag': 'LVLF', 'label': 'Flags', 'kind': 'struct', 'fields': [{'name': 'Flags', 'code': 'B', 'value': 1}]}]
    for r in entries:
        subs.append({'tag': 'LVLO', 'label': 'Entry', 'kind': 'struct', 'fields': [
            {'name': 'Level', 'code': 'h', 'value': _level_of(gd, pr, r['base'])}, {'pad': '0000'}, {'name': item, 'code': 'F', 'value': r['base']},
            {'name': 'Count', 'code': 'h', 'value': 1}, {'pad': '0000'}]})
    lst = {'type': tag, 'flags': 0, 'src': '', 'subs': subs}
    wrap = json.loads(json.dumps(ac.get_record(gd, pr, entries[0]['base'])))
    assert wrap['type'] == wrap_tag
    recordio.set_field(wrap, 'EDID', ac.unique_edid(br, pr, 'FOLab%sSpawn%s' % (stem, item)), label='Editor ID')
    wrap['subs'] = [s for s in wrap['subs'] if s['tag'] not in ('SCRI', 'FULL')]
    wrap['src'] = wrap.get('src') or ''
    wrap['copied_from'] = entries[0]['base']
    return lst, wrap


def apply(gd, pr, br, edit, body):
    """Everything a plan asks for, as one undo step. body: cell, rows (as plan gave them, counts as chosen), live,
    levelled, seed."""
    import api_characters as ac
    ckey = body['cell']
    rows = [r for r in body['rows'] if int(r.get('count', 0)) > 0]
    if not rows:
        return {'note': 'Nobody is ticked.'}
    rng = random.Random(body.get('seed', 1) * 7919 + 13)
    total = sum(int(r['count']) for r in rows)
    points = spots(gd, pr, ckey, total, rng)
    if len(points) < total:
        if not points:
            return {'note': 'There\'s nowhere to stand here: FOLab found no floor. Add floor pieces, or a navmesh in the Kit tab.'}
    place = _place_name(gd, pr, ckey)
    stem = _stem(place) or 'Place'
    ops, nid = [], pr.next_id
    pending = {}

    def new_record(rec):
        # (project.apply numbers new records in the order of its ops, so what's made here can link to what's made here)
        nonlocal nid
        ops.append({'op': 'record_new', 'record': rec})
        key = '+%06X' % nid
        nid += 1
        pending[key] = rec
        return key
    taken = set()

    def unique(edid):
        e = ac.unique_edid(br, pr, edid)
        n = 1
        while e.lower() in taken:
            n += 1
            e = ac.unique_edid(br, pr, '%s%d' % (edid, n))
        taken.add(e.lower())
        return e

    # levelled: a list of the fixed ones of each kind, and one character standing for it
    made_lists = 0
    if body.get('levelled'):
        for kind in (CREATURE, PERSON):
            fixed = [r for r in rows if r['kind'] == kind and not r.get('levelled')]
            if len(fixed) >= 1:
                lst, wrap = _levelled_list(gd, pr, br, fixed, kind, stem)
                lkey = new_record(lst)
                tp = ac.one(wrap, 'TPLT')
                if tp:
                    tp['value'] = lkey
                else:
                    ac.insert(wrap, {'tag': 'TPLT', 'label': 'Template', 'kind': 'F', 'value': lkey})
                ac.set_num(wrap, 'ACBS', 'Template flags', 0x3FF)
                wkey = new_record(wrap)
                count = sum(int(r['count']) for r in fixed)
                diff = body.get('difficulty')
                rows = [r for r in rows if r not in fixed] + [{'base': wkey, 'kind': kind, 'levelled': True, 'count': count, 'name': 'Levelled',
                                                               'xlcm': None if diff in ('auto', None, '') else int(diff)}]
                made_lists += 1

    # residents live here: their own copies, with a place to be and (given a bed) somewhere to sleep
    made_people = 0
    if body.get('live') and any(r['kind'] == PERSON for r in rows):
        radius = int(body.get('radius') or (1024 if not ckey.startswith('+') and gd.from_key(ckey) in gd.ext_cells else 512))
        sandbox = ac.new_package(gd, pr, br, 'sandbox', stem + 'Sandbox', {'radius': radius})
        recordio.set_field(sandbox, 'EDID', unique('FOLab%sSandbox' % stem))
        packs = [new_record(sandbox)]
        if has_bed(gd, pr, ckey):
            sleep = ac.new_package(gd, pr, br, 'sleep', stem + 'Sleep', {'radius': radius})
            recordio.set_field(sleep, 'EDID', unique('FOLab%sSleep' % stem))
            packs.insert(0, new_record(sleep))
        for r in rows:
            if r['kind'] == PERSON and r['base'] in pending:     # (the character standing for a list made above: itself)
                rec = pending[r['base']]
                rec['subs'] = [s for s in rec['subs'] if s['tag'] != 'PKID']
                ac.set_num(rec, 'ACBS', 'Template flags', ac.num(rec, 'ACBS', 'Template flags') & ~0x20)
                for k in packs:
                    ac.insert(rec, {'tag': 'PKID', 'label': 'AI package', 'kind': 'F', 'value': k})
            elif r['kind'] == PERSON:
                edid = unique('FOLab%s%s' % (stem, _stem(r.get('name') or 'Resident')))
                r['base'] = new_record(_resident(gd, pr, br, r['base'], edid, packs))
                made_people += 1

    # who stands where
    rng.shuffle(points)
    k = 0
    placed = 0
    for r in rows:
        for _n in range(int(r['count'])):
            if k >= len(points):
                break
            x, y, z, turn = points[k]
            k += 1
            placed += 1
            op = {'op': 'add', 'cell': ckey, 'base': r['base'], 'p': [x, y, z, 0.0, 0.0, turn]}
            if r.get('levelled') and r.get('xlcm') is not None:
                op['xlcm'] = int(r['xlcm'])
            ops.append(op)
    out = edit('Populate ' + place, ops)
    out.pop('things', None)
    out['placed'], out['lists'], out['people'] = placed, made_lists, made_people
    if placed < total:
        out['note'] = 'Only room for %d of %d here.' % (placed, total)
    return out
