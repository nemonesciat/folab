"""What goes with what, learnt from how the game's own places are dressed.

Every place inside, and every 4 x 4 cells of the big worlds outside, is a bag of what's in it. From those:
- 'Suggested for this place': the places most like the one open now (by what they hold, rare things counting for more),
  and what they hold that this one doesn't yet;
- style palettes: a place's style is the building kit most of its walls come from; a thing belongs to a style when that
  style's places hold it much more often than places do in general, its staples first;
- sets: a table with what the game stands round it and on it, taken whole from the place where that arrangement is most
  typical, to put down as one;
- 'goes with': what the game most often stands within a few steps of a thing.

The survey is read once per set of game files, in the background, and kept under cache/style."""
import collections
import hashlib
import json
import math
import os
import re
import threading
import traceback

import project

TYPES = {'STAT', 'MSTT', 'FURN', 'CONT', 'DOOR', 'LIGH', 'MISC', 'ACTI', 'TACT', 'TERM', 'BOOK', 'NOTE', 'WEAP', 'ARMO',
         'ALCH', 'AMMO', 'KEYM', 'PWAT', 'ADDN', 'IMOD', 'CHIP', 'CMNY', 'CCRD'}
ITEM_TYPES = {'MISC', 'BOOK', 'NOTE', 'WEAP', 'ARMO', 'ALCH', 'AMMO', 'KEYM', 'IMOD', 'CHIP', 'CMNY', 'CCRD'}
SECTIONS = [('shell', 'Walls and floors', 'What the place is built of'), ('furniture', 'Furniture', 'Beds, tables, seats, storage, machines'),
            ('decor', 'Dressing', 'Lights, clutter, signs, plants and rubble'), ('items', 'Things to pick up', 'Food, bottles, books, weapons, ammo')]
# a style: its name, from the folders its walls come from (first match wins)
STYLES = [('Vault', r'dungeons\\vault|nvdlc0\d\\.*vault'), ('Casino', r'nv_casino|nvgamorrah|nvlucky38|nvtops|nvultraluxe|casino'),
          ('Hotel', r'hotel'), ('Office', r'dungeons\\office|dungeons\\metro'), ('Workshop and utility', r'dungeons\\utility|dungeons\\industrial|dungeons\\facility'),
          ('Caves and mines', r'dungeons\\caves|dungeons\\mine|\\caves?\\'), ('Shacks and scrap', r'architecture\\megaton|dungeons\\wastelandhomes|architecture\\wasteland|dungeons\\shack'),
          ('Houses', r'nv_ushome|nv_craftsman|dungeons\\basement|nv_goodsprings|dungeons\\homes'), ('Military and bunkers', r'dungeons\\enclave|bunker|dungeons\\military|dungeons\\rivetcity'),
          ('Hoover Dam', r'hooverdam'), ('Sunset Sarsaparilla', r'sunsetsarsaparilla'), ('Old World Blues', r'^nvdlc03\\|^dlc03\\'),
          ('Dead Money', r'^nvdlc01\\'), ('Honest Hearts', r'^nvdlc02\\'), ('Lonesome Road', r'^nvdlc04\\'), ('Neoclassical', r'neoclassical'),
          ('City ruins', r'architecture\\urban|architecture\\strip|architecture\\freeside')]
WORLD_STYLES = {'wastelandnv': 'The Mojave', 'thestripworldnew': 'The Strip', 'freesideworld': 'Freeside', 'freesidefortworld': 'Freeside',
                'nvdlc02zioncanyon': 'Zion', 'nvdlc03bigmt': 'The Big MT', 'nvdlc04dividevistaworld': 'The Divide'}
SHELL_WALK = re.compile(r'^(?:nvdlc0\d\\|dlc0\d\\|dlcanch\\|dlcpitt\\)?(?:dungeons|architecture)\\')
ANCHOR = re.compile(r'table|desk|bed(?!rock)|counter|shelf|shelves|bar(?!rel|rier|bed)|workbench|cabinet|stove|sink|booth|locker|dresser|bookcase|fridge|refrigerator')
FURNITURE = re.compile(r'chair|table|desk|bed(?!rock)|couch|sofa|stool|bench|shelf|shelves|locker|cabinet|counter|wardrobe|dresser|bookcase')
DRESSING = re.compile(r'rubble|debris|light|lamp|sconce|grass|horseweed|fern|plant|poster|sign|seam|crack|stain')
FLAT = re.compile(r'(^|\\)(decals|effects|fx)\\|\\fx[a-z]')     # (marks on walls, light beams: never part of a set)
NEAR = 110.0                            # how close 'stands with it' means, across
NEAR_Z = 130.0

_lock = threading.Lock()
_state = {'for': None, 'survey': None, 'error': None}


def _is_marker(btype, edid, model):
    m = model.lower()
    return 'marker' in edid.lower() or m.startswith(('marker', 'editor')) or 'collision' in edid.lower()[:12]


def _section(btype, model):
    m = model.lower().replace('/', '\\')
    if btype in ITEM_TYPES:
        return 'items'
    name = m.rsplit('\\', 1)[-1]
    if btype in ('FURN', 'CONT', 'TERM') or '\\furniture\\' in '\\' + m or FURNITURE.search(name):
        return 'furniture'
    if FLAT.search(m) or DRESSING.search(name):
        return 'decor'
    if btype == 'DOOR' or (btype == 'STAT' and SHELL_WALK.match(m)):
        return 'shell'
    return 'decor'


def _style_of(pieces):
    """A place's style, from how many wall pieces come from each folder."""
    scores = collections.Counter()
    for folder, n in pieces.items():
        for name, pat in STYLES:
            if re.search(pat, folder):
                scores[name] += n
                break
    return scores.most_common(1)[0][0] if scores else None


def read(gd):
    """The survey as plain data. places: [{'id', 'name', 'out', 'style', 'bag': {base index: count}}]"""
    bases, info, seen = [], [], {}

    def base(fid):
        if fid in seen:
            return seen[fid]
        idx = -1
        if fid in gd.forms:
            btype, edid, name, model = gd.describe(fid)
            if btype in TYPES and model and not _is_marker(btype, edid, model):
                idx = len(bases)
                bases.append(gd.key(fid))
                info.append([btype, edid, name, gd.model_path(btype, model), _section(btype, model)])
        seen[fid] = idx
        return idx

    places, near, set_ofs = [], collections.defaultdict(collections.Counter), {}

    def dress(refs, pl_i):
        """Who stands with whom in one place: pairs for 'goes with', and each anchor's company, for sets."""
        cells = collections.defaultdict(list)
        for b, p, s, rot in refs:
            cells[(int(p[0] // NEAR), int(p[1] // NEAR))].append((b, p, s, rot))
        for (cx, cy), here in cells.items():
            for b, p, s, rot in here:
                anchor = ANCHOR.search(info[b][1].lower()) or ANCHOR.search(info[b][3].lower())
                sec = info[b][4]
                if sec == 'shell':
                    continue
                company = []
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        for o in cells.get((cx + dx, cy + dy), ()):
                            if o[0] == b and o[1] is p or info[o[0]][4] == 'shell' or FLAT.search(info[o[0]][3].lower()):
                                continue
                            d2 = (o[1][0] - p[0]) ** 2 + (o[1][1] - p[1]) ** 2
                            if d2 <= NEAR * NEAR and abs(o[1][2] - p[2]) <= NEAR_Z:
                                company.append(o)
                                if o[0] != b:
                                    near[b][o[0]] += 1
                if anchor and sec == 'furniture' and 2 <= len(company) <= 12:
                    set_ofs.setdefault(b, []).append((pl_i, (b, p, s, rot), company))

    for c in sorted(gd.interiors):
        refs, bag, pieces = [], collections.Counter(), collections.Counter()
        for r in gd.refs(c):
            if not r['pos'] or r['pos'][2] < -20000:
                continue
            b = base(r['base'])
            if b < 0:
                continue
            bag[b] += 1
            refs.append((b, r['pos'], r['scale'], r['rot']))
            m = info[b][3].lower()[7:]
            if info[b][0] == 'STAT' and SHELL_WALK.match(m):
                pieces['\\'.join(m.split('\\')[:-1])] += 1
        if not bag:
            continue
        f = gd.fields(c)
        places.append({'id': gd.key(c), 'name': _zs(f.get('FULL')) or _zs(f.get('EDID')), 'out': False, 'style': _style_of(pieces), 'bag': dict(bag)})
        dress(refs, len(places) - 1)
    # outside: every 4 x 4 cells of the worlds people play in
    for w in gd.worlds():
        wname = gd.edid(w).lower()
        if wname not in WORLD_STYLES:
            continue
        blocks = collections.defaultdict(collections.Counter)
        for xy, c in gd.grid(w).items():
            for r in gd.refs(c):
                if not r['pos'] or r['pos'][2] < -20000:
                    continue
                b = base(r['base'])
                if b >= 0:
                    blocks[(xy[0] // 4, xy[1] // 4)][b] += 1
        for (bx, by), bag in blocks.items():
            if sum(bag.values()) >= 3:
                places.append({'id': '%s@%d,%d' % (gd.key(w), bx * 4, by * 4), 'name': '%s, near cell %d, %d' % (WORLD_STYLES[wname], bx * 4 + 2, by * 4 + 2),
                               'out': True, 'style': WORLD_STYLES[wname], 'bag': dict(bag)})
    # the sets: each anchor's most typical company, taken whole from one place
    sets = []
    for b, uses in set_ofs.items():
        if len(uses) < 2:
            continue
        count = collections.Counter(o[0] for _pl, _a, comp in uses for o in comp)
        best = max(uses, key=lambda u: sum(count[o[0]] for o in u[2]) / (1 + abs(len(u[2]) - 5)))
        pl_i, (ab, ap, ascale, arot), comp = best
        items = [{'b': ab, 'p': [0, 0, ap[2], *arot], 's': ascale}]
        for o in comp:
            if o[1] is not ap:
                items.append({'b': o[0], 'p': [o[1][0] - ap[0], o[1][1] - ap[1], o[1][2], *o[3]], 's': o[2]})
        lo = min(i['p'][2] for i in items)
        for i in items:
            i['p'][2] -= lo
            i['p'] = [round(v, 3) for v in i['p']]
        sets.append({'anchor': b, 'place': pl_i, 'uses': len(uses), 'items': items})
    return {'bases': bases, 'info': info, 'places': places, 'sets': sets,
            'near': {str(b): c.most_common(8) for b, c in near.items()}}


def _zs(v):
    return v[:-1].decode('cp1252', 'replace') if v else ''


class Survey:
    def __init__(self, data):
        self.__dict__.update(data)
        for p in self.places:
            p['bag'] = {int(k): v for k, v in p['bag'].items()}
        self.key_of = {k: i for i, k in enumerate(self.bases)}
        n_in, n_out = 0, 0
        df_in, df_out = collections.Counter(), collections.Counter()
        for p in self.places:
            (df_out if p['out'] else df_in).update(p['bag'].keys())
            if p['out']:
                n_out += 1
            else:
                n_in += 1
        self.df = {False: df_in, True: df_out}
        self.n = {False: max(1, n_in), True: max(1, n_out)}
        for p in self.places:
            df, n = self.df[p['out']], self.n[p['out']]
            p['w'] = {b: (1 + math.log(c)) * math.log(1 + n / df[b]) for b, c in p['bag'].items()}
            p['norm'] = math.sqrt(sum(v * v for v in p['w'].values())) or 1.0

    def row(self, b, **more):
        t, e, n, m, sec = self.info[b]
        return dict({'key': self.bases[b], 'type': t, 'edid': e, 'name': n, 'model': m, 'sec': sec}, **more)

    def suggest(self, keys, out=False, skip_id=None, top=40, similar=12):
        """What the places most like these things hold that they don't. keys: the base keys there now."""
        have = collections.Counter(self.key_of[k] for k in keys if k in self.key_of)
        if not have:
            return {'like': [], 'rows': self._common(out, top), 'empty': True}
        df, n = self.df[out], self.n[out]
        w = {b: (1 + math.log(c)) * math.log(1 + n / max(1, df[b])) for b, c in have.items()}
        norm = math.sqrt(sum(v * v for v in w.values())) or 1.0
        scored = []
        for p in self.places:
            if p['out'] != out or p['id'] == skip_id:
                continue
            dot = sum(v * p['w'][b] for b, v in w.items() if b in p['w'])
            if dot:
                scored.append((dot / (norm * p['norm']), p))
        scored.sort(key=lambda s: -s[0])
        like = scored[:similar]
        marks = collections.Counter()
        where = {}
        for sim, p in like:
            for b, v in p['w'].items():
                if b not in have:
                    marks[b] += sim * v
                    where.setdefault(b, p['name'])
        rows = [self.row(b, score=round(s, 2), seen=where[b]) for b, s in marks.most_common(top * 3)]
        # (not all walls: a mix, the most fitting of each section first)
        by = collections.defaultdict(list)
        for r in rows:
            by[r['sec']].append(r)
        mixed = []
        for sec, _l, _d in SECTIONS:
            mixed += by[sec][:top // 4 + 1]
        mixed.sort(key=lambda r: -r['score'])
        return {'like': [{'name': p['name'], 'id': p['id'], 'sim': round(sim, 2)} for sim, p in like[:5]], 'rows': mixed[:top]}

    def _common(self, out, top):
        by = collections.defaultdict(list)
        for b, c in self.df[out].most_common(600):
            by[self.info[b][4]].append(self.row(b, score=c))
        out_rows = []
        for sec, _l, _d in SECTIONS:
            out_rows += by[sec][:top // 4]
        return out_rows

    def styles(self):
        n = collections.Counter(p['style'] for p in self.places if p['style'])
        out = [{'name': s, 'places': c, 'out': s in WORLD_STYLES.values()} for s, c in n.items()]
        out.sort(key=lambda s: (s['out'], s['name']))
        return out

    def palette(self, style, top=48):
        """{'sections': [{id, label, about, rows}], 'sets': [...]} of a style; '*': what's used everywhere."""
        out = style in WORLD_STYLES.values()
        mine = [p for p in self.places if p['out'] == out and (style == '*' or p['style'] == style)]
        if style == '*':
            mine = [p for p in self.places if not p['out']]
        if not mine:
            raise KeyError(style)
        df, n = self.df[out], self.n[out]
        here = collections.Counter()
        for p in mine:
            here.update(p['bag'].keys())
        rows = collections.defaultdict(list)
        for b, c in here.items():
            share, lift = c / len(mine), (c / len(mine)) / (df[b] / n)
            if style != '*' and (lift < 1.5 and share < 0.5 or (c < 2 and len(mine) > 3)):
                continue
            rows[self.info[b][4]].append((share * min(lift, 6) if style != '*' else share, b, share))
        sections = []
        for sec, label, about in SECTIONS:
            got = sorted(rows[sec], key=lambda r: -r[0])[:top]
            sections.append({'id': sec, 'label': label, 'about': about,
                             'rows': [self.row(b, share=round(share, 2), staple=share >= 0.4) for _s, b, share in got]})
        ids = {id(p) for p in mine}
        sets = [s for s in self.sets if id(self.places[s['place']]) in ids] if style != '*' else self.sets
        sets = sorted(sets, key=lambda s: -s['uses'])[:16]
        return {'style': style, 'places': len(mine), 'examples': [p['name'] for p in mine[:6]], 'sections': sections,
                'sets': [self.set_row(s) for s in sets]}

    def set_row(self, s):
        a = self.info[s['anchor']]
        counts = collections.Counter(i['b'] for i in s['items'])
        items = []
        for i in s['items']:
            t, e, _n, m, _sec = self.info[i['b']]
            items.append({'base': self.bases[i['b']], 'p': i['p'], 's': i['s'], 'type': t, 'edid': e, 'model': m})
        return {'name': (a[2] or a[1]) + ' and what goes with it', 'from': self.places[s['place']]['name'], 'uses': s['uses'],
                'lead': a[3], 'count': len(items), 'names': [self.info[b][1] for b, _c in counts.most_common(5)], 'items': items}

    def goes_with(self, key):
        b = self.key_of.get(key)
        if b is None:
            return []
        return [self.row(o, n=c) for o, c in self.near.get(str(b), [])]


def _cache_file(gd):
    sig = hashlib.md5('|'.join('%s:%d:%d' % (p.path, os.path.getsize(p.path), os.path.getmtime(p.path)) for p in gd.plugins).encode()).hexdigest()[:12]
    return os.path.join(project.HOME, 'cache', 'style', sig + '.json')


def survey(gd, wait=False):
    """The survey when it's ready; otherwise it's started in the background and None comes back (wait: read it now)."""
    with _lock:
        if _state['for'] is not gd:
            _state.update({'for': gd, 'survey': None, 'error': None, 'thread': None})
        if _state['survey'] is not None:
            return _state['survey']
        if not _state.get('thread'):
            _state['thread'] = threading.Thread(target=_run, args=(gd,), daemon=True)
            _state['thread'].start()
        th = _state['thread']
    if wait:
        th.join()
        if _state['error']:
            raise ValueError(_state['error'])
        return _state['survey']
    return None


def _run(gd):
    try:
        path = _cache_file(gd)
        data = None
        if os.path.isfile(path):
            try:
                with open(path, encoding='utf-8') as f:
                    data = json.load(f)
            except ValueError:
                data = None
        if data is None:
            data = read(gd)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path + '.tmp', 'w', encoding='utf-8') as f:
                json.dump(data, f)
            os.replace(path + '.tmp', path)
        got = Survey(data)
        if _state['for'] is gd:
            _state['survey'] = got
    except Exception as e:
        traceback.print_exc()
        _state['error'] = str(e)


def get(ctx, path, q):
    """Answers to the Place panel and the palette; KeyError for a path that isn't one of these."""
    if path not in ('suggest', 'styles', 'palette', 'goes'):
        raise KeyError(path)
    gd = ctx['gd']()
    s = survey(gd)
    if s is None:
        return {'error': _state['error']} if _state['error'] else {'building': True}
    if path == 'styles':
        return {'styles': s.styles()}
    if path == 'palette':
        return s.palette(q.get('style', '*'))
    if path == 'goes':
        return {'rows': s.goes_with(q['key'])}
    # suggest: what stands in the cells named now, as the mod leaves them
    keys = []
    out = False
    ids = [c for c in q.get('cells', '').split(';') if c]
    for c in ids:
        if not c.startswith('+') and gd.from_key(c) in gd.ext_cells:
            out = True
        for t in ctx['things'](c):
            if t['state'] != 'removed' and not t['bkey'].startswith('+'):
                keys.append(t['bkey'])
    got = s.suggest(keys, out, skip_id=ids[0] if len(ids) == 1 else None)
    got['out'] = out
    return got


def post(ctx, path, body):
    raise KeyError(path)
