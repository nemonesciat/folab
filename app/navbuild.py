"""A navmesh for a place in the mod: what's in it as the mod has it (navgen builds the mesh, navmesh.py holds the rules),
kept in the project as plain lists and written with the plugin by espwrite.

    project.navmesh[cell key] = {'form': the NAVM's key, 'verts': [[x, y, z]], 'tris': [[8 numbers]],
                                 'doors': [[door ref's key, triangle]], 'ext': [[kind, the other NAVM's key, triangle]],
                                 'cover': [numbers], 'sig': what the place held when it was made,
                                 'copy': True if it's a game mesh kept only to change its links (a neighbour's),
                                 'no_door': [doors that stood by the old mesh and now stand by none],
                                 'outline': what NAVI needs for all but one mesh of a place,
                                 'others': [the place's other meshes, each of this same form]}

A door's link back to its triangle (XNDP) is on the door's own record, so the writer adds it there. Several meshes in a
place: the first is made anew, the rest become stubs (navmesh.stub_mesh).

Outside, a mesh joins its neighbours: Area does the joining, across any set of cells at once. Links are triangle numbers,
so whichever game mesh gets a link from a new mesh, or had one to the old mesh, is copied into the project whole, with
the same triangles and only its links changed."""
import hashlib
import json
import struct

import navgen
import navmesh as N
import tes4

ACTORS = {'NPC_': 'ACHR', 'CREA': 'ACRE'}
DISABLED = 0x800


class NavError(ValueError):
    """Why a place can't have a navmesh made, in words for the person asking."""


def _base_type(gd, project, bkey):
    if bkey.startswith('+'):
        return (project.records.get(bkey) or {}).get('type')
    return gd.forms[gd.from_key(bkey)][1].tag


def place_refs(gd, project, ckey):
    """Everything in a place as the mod leaves it, in the form navgen reads, with refs named by key. Things made from
    the mod's own records have no shape FOLab can read yet, so only their being there as actors or doors counts."""
    cell = None if ckey.startswith('+') else gd.from_key(ckey)
    mine = (project.cells.get(ckey) or {}).get('refs', {})
    out = []

    def add(key, bkey, p, s, leads):
        out.append({'ref': key, 'type': ACTORS.get(_base_type(gd, project, bkey), 'REFR'),
                    'base': None if bkey.startswith('+') else gd.from_key(bkey),
                    'pos': tuple(p[:3]), 'rot': tuple(p[3:6]), 'scale': s, 'leads': leads, 'bkey': bkey})
    if cell is not None:
        for r in gd.refs(cell):
            if r['base'] not in gd.forms or not r['pos']:
                continue
            if gd.forms[r['ref']][1].flags & DISABLED:    # (not there when the game starts: never in the way)
                continue
            key = gd.key(r['ref'])
            ch = mine.get(key) or {}
            if ch.get('removed'):
                continue
            add(key, ch.get('base') or gd.key(r['base']), ch.get('p') or list(r['pos']) + list(r['rot']),
                ch.get('s', r['scale']), bool(ch['tel']) if 'tel' in ch else r['leads'])
    for key, ch in mine.items():
        if key.startswith('+') and not ch.get('removed'):
            add(key, ch['base'], ch['p'], ch.get('s', 1.0), bool(ch.get('tel')))
    return out


def signature(refs):
    """Changes when something that matters to the mesh moves, so a mesh can say it's out of date."""
    rows = sorted([r['ref'], r['bkey'], [round(v, 1) for v in r['pos'] + r['rot']], round(r['scale'], 3), r['leads']] for r in refs)
    return hashlib.md5(json.dumps(rows).encode()).hexdigest()[:16]


def outside_signature(project, ckey, refs):
    """The same, outside: the ground and the water count too."""
    return hashlib.md5(json.dumps([signature(refs), (project.land.get(ckey) or {}).get('h'), project.water.get(ckey, 'game')]).encode()).hexdigest()[:16]


def is_outside(gd, ckey):
    return not ckey.startswith('+') and gd.from_key(ckey) in gd.ext_cells


def game_entries(gd, ckey):
    if ckey.startswith('+'):
        return []
    return sorted(gd.navmeshes(gd.from_key(ckey)), key=lambda e: e[1].formid)


def game_meshes(gd, ckey):
    """The form keys of the navmeshes the game (or an opened plugin) has for a place."""
    return [gd.key(gd.to_global(e[0], e[1].formid)) for e in game_entries(gd, ckey)]


def game_info(gd):
    """What NAVI says of each mesh, later files over earlier: {mesh's form: NVMI entry, form IDs left as they were}."""
    have = getattr(gd, '_navi_info', None)
    if have is None:
        have = {}
        for i, p in enumerate(gd.plugins):
            for r, _path in p.walk():
                if r.tag == 'NAVI':
                    for e in N.read_navi(p.data(r))['info']:
                        have[gd.to_global(i, e['navm'])] = e
        gd._navi_info = have
    return have


def _outline_data(o):
    return {'min': list(o['min']), 'max': list(o['max']), 'verts': [list(v) for v in o['verts']], 'tris': [list(t) for t in o['tris']]}


def outline_record(o):
    return {'min': tuple(o['min']), 'max': tuple(o['max']), 'verts': [tuple(v) for v in o['verts']], 'tris': [tuple(t) for t in o['tris']]}


def game_copy(gd, entry):
    """A game mesh in the project's form, its form IDs as keys."""
    i, rec = entry
    m = N.read_navm(gd.plugins[i].data(rec))
    k = lambda fid: gd.key(gd.to_global(i, fid))
    fid = gd.to_global(i, rec.formid)
    out = {'form': gd.key(fid), 'copy': True, 'verts': [list(v) for v in m['verts']], 'tris': [list(t) for t in m['tris']],
           'cover': list(m['cover']), 'doors': [[k(d[0]), d[1]] for d in m['doors']], 'ext': [[e[0], k(e[1]), e[2]] for e in m['ext']]}
    info = game_info(gd).get(fid)
    if info and info['outline'] is not None:
        out['outline'] = _outline_data(info['outline'])
    return out


def as_mesh(data):
    """The project's form as navmesh.py's working form, with keys for form IDs (they're only names to it)."""
    return {'version': N.VERSION, 'cell': None, 'verts': [tuple(v) for v in data['verts']], 'tris': [tuple(t) for t in data['tris']],
            'cover': list(data.get('cover', [])), 'doors': [(d[0], d[1], 0) for d in data['doors']],
            'ext': [tuple(e) for e in data.get('ext', [])], 'grid': None}


def as_data(m, form, **more):
    out = {'form': form, 'verts': [list(v) if more.get('copy') else [round(c, 3) for c in v] for v in m['verts']], 'tris': [list(t) for t in m['tris']],
           'doors': [[d[0], d[1]] for d in m['doors']], 'ext': [list(e) for e in m['ext']], 'cover': list(m['cover'])}
    out.update(more)
    return out


def keys_used(nav):
    """Every form key a mesh names, its others' too (for the plugin's masters)."""
    out = [nav['form']] + [d[0] for d in nav['doors']] + [e[1] for e in nav.get('ext', [])] + list(nav.get('no_door', []))
    for o in nav.get('others', []):
        out += keys_used(o)
    return out


def new_form(project):
    key = '+%06X' % project.next_id
    project.next_id += 1
    return key


def stub_data(form, near):
    """A mesh that had to go, as the project keeps it."""
    m = N.stub_mesh(*near)
    return as_data(m, form, outline=_outline_data(N.outline_of(m)), stub=True)


def _ref_position(gd, key):
    if key.startswith('+'):
        return None
    e = gd.forms.get(gd.from_key(key))
    if not e:
        return None
    d = gd.plugins[e[0]].fields(e[1]).get('DATA')
    return struct.unpack_from('<3f', d) if d and len(d) >= 12 else None


def _make_one(gd, project, ckey, meshes_now):
    """A new mesh from what a place holds: (project form of it without the form filled in unless it has one, report).
    meshes_now: the place's meshes as they are now, project form (their doors must be told)."""
    outside = is_outside(gd, ckey)
    cell = ckey
    refs = place_refs(gd, project, ckey)
    usable = [dict(r) for r in refs if r['base'] is not None or r['type'] != 'REFR']
    if outside:
        cell = gd.from_key(ckey)

        def land_of(x, y):
            c = gd.grid(gd.ext_cells[cell]).get((x, y))
            mine = project.land.get(gd.key(c)) if c is not None else None
            return mine['h'] if mine else None

        def refs_of(c):
            return [r for r in place_refs(gd, project, gd.key(c)) if r['base'] is not None or r['type'] != 'REFR']
        water = False
        if ckey in project.water:
            h = project.water[ckey]
            w = gd.fields(gd.ext_cells[cell]).get('DNAM')
            water = h if h is not None else (struct.unpack_from('<f', w, 4)[0] if w and len(w) >= 8 else None)
        m, report = navgen.generate(gd, cell, refs_of=refs_of, land_of=land_of, water=water)
    else:
        if not ckey.startswith('+'):
            cell = gd.from_key(ckey)
        m, report = navgen.generate(gd, cell, refs=usable, floors=True)
    if m is None:
        return None, report, refs
    doors = list(report.get('doors') or [])
    seen = {d[0] for d in doors}
    # doors that stood by the old mesh and aren't in this cell's list (a door just over the edge) still need a triangle
    for old in meshes_now:
        for d, _t in old['doors']:
            if d not in seen:
                p = _ref_position(gd, d)
                if p:
                    doors.append((d, p))
                    seen.add(d)
    linked, missed = N.link_doors(m, doors)
    report['linked'] = linked
    report['missed'] = missed
    return m, report, refs


def generate(gd, project, ckey):
    """A navmesh for a place inside: (the project's form of it, a report in words). Outside use Area."""
    if is_outside(gd, ckey):
        raise NavError('This place is outside: it joins its neighbours, so it\'s made with Area.')
    now = project.navmesh.get(ckey)
    old_meshes = ([now] + now.get('others', [])) if now else [game_copy(gd, e) for e in game_entries(gd, ckey)]
    m, report, refs = _make_one(gd, project, ckey, old_meshes)
    if m is None:
        raise NavError('There\'s nothing here to walk on: no floor with room above it.')
    bad = N.validate(N.refresh(m))
    if bad:
        raise NavError('The mesh came out unsound (%s): this is a bug in FOLab, please report it.' % bad[0])
    data = as_data(m, old_meshes[0]['form'] if old_meshes else None, sig=signature(refs))
    if report['missed']:
        data['no_door'] = list(report['missed'])
    if len(old_meshes) > 1:
        v = m['verts'][0]
        data['others'] = [stub_data(o['form'], (v[0], v[1])) for o in old_meshes[1:]]
    return data, {'triangles': len(m['tris']), 'seconds': report.get('seconds'), 'doors': len(report['linked']), 'doors_missed': len(report['missed']),
                  'pieces': report.get('kept_pieces'), 'cut_off': report.get('dropped_pieces'), 'unread': report.get('unread', 0),
                  'stubs': len(old_meshes) - 1 if len(old_meshes) > 1 else 0}


# --- outside: a set of cells, joined to each other and to what's round them ---

class Area:
    """Meshes being changed, cell by cell: each a working mesh with keys for IDs, and whether it was made here."""

    def __init__(self, gd, project):
        self.gd, self.project = gd, project
        self.cells = {}         # cell key -> [{'form', 'm', 'copy', 'keep': other things kept in the project form}]
        self.before = {}        # form -> (links, triangle count), to see what changed

    def meshes(self, ckey, fresh=False):
        if ckey not in self.cells:
            now = None if fresh else self.project.navmesh.get(ckey)
            datas = ([now] + now.get('others', [])) if now else [game_copy(self.gd, e) for e in game_entries(self.gd, ckey)]
            row = []
            for d in datas:
                row.append({'form': d['form'], 'm': as_mesh(d), 'copy': bool(d.get('copy')), 'data': d})
                self.before[d['form']] = (list(row[-1]['m']['ext']), len(d['tris']))
            self.cells[ckey] = row
        return self.cells[ckey]

    def neighbours(self, ckey, reach=1):
        gd = self.gd
        cell = gd.from_key(ckey)
        grid = gd.grid(gd.ext_cells[cell])
        x, y = gd.cell_grid(cell)
        out = []
        for dx in range(-reach, reach + 1):
            for dy in range(-reach, reach + 1):
                c = grid.get((x + dx, y + dy))
                if (dx or dy) and c is not None:
                    out.append((gd.key(c), abs(dx) + abs(dy) == 1, (x + dx, y + dy)))
        return out

    def join(self, targets):
        """Join each target cell's meshes to whatever is round it, both ways, doing each pair of cells once."""
        gd = self.gd
        made = 0
        done = set()
        for ck in targets:                                  # (first, nothing round here may still name the old triangles)
            forms = [e['form'] for e in self.meshes(ck)]
            for nk, _side, _nxy in self.neighbours(ck):
                for b in self.meshes(nk):
                    for f in forms:
                        N._forget_links(b['m'], f)
        for ck in targets:
            xy = gd.cell_grid(gd.from_key(ck))
            for nk, side, nxy in self.neighbours(ck):
                if not side or (nk, ck) in done:
                    continue
                done.add((ck, nk))
                for a in self.meshes(ck):
                    for b in self.meshes(nk):
                        if not a['data'].get('stub') and not b['data'].get('stub'):
                            made += N.link_edges(a['m'], a['form'], xy, b['m'], b['form'], nxy, split_b=not b['copy'])
        return made

    def forget_far(self, ckey, old_ext_targets):
        """Meshes beyond the eight neighbours that linked to a mesh being replaced (the game has a few)."""
        gd = self.gd
        forms = [e['form'] for e in self.meshes(ckey)]
        for target in old_ext_targets:
            home = gd.ref_cell.get(gd.from_key(target)) if not target.startswith('+') else None
            if home is None:
                continue
            for b in self.meshes(gd.key(home)):
                for f in forms:
                    N._forget_links(b['m'], f)

    def check(self):
        """Every mesh here against each other: what's wrong, as words."""
        rows = [e for row in self.cells.values() for e in row]
        others = {e['form']: e['m'] for e in rows}
        made = {e['form']: e['m'] for e in rows if not e['copy']}
        bad = []
        for m in others.values():
            N.refresh(m)
        for e in rows:      # (the game's own links between the game's own meshes aren't all mutual: not ours to mend)
            bad += ['%s: %s' % (e['form'], s) for s in N.validate(e['m'], made if e['copy'] else others, e['form'])]
        return bad

    def changed(self):
        """[(cell key, form of the cell's first mesh as the project will keep it)] for what has to be in the project."""
        ops = []
        for ck, row in self.cells.items():
            changed = False
            for e in row:
                was = self.before.get(e['form'])
                if e.get('new') or was is None or was[0] != e['m']['ext'] or was[1] != len(e['m']['tris']):
                    changed = True
            if changed:
                datas = []
                for e in row:
                    keep = {k: e['data'][k] for k in ('outline', 'stub', 'no_door', 'sig', 'hand') if k in e['data']}
                    if e['copy']:
                        keep['copy'] = True
                    datas.append(as_data(e['m'], e['form'], **keep))
                first = datas[0]
                if len(datas) > 1:
                    first['others'] = datas[1:]
                ops.append({'op': 'navmesh', 'cell': ck, 'mesh': first})
        return ops


def generate_area(gd, project, ckeys, progress=None):
    """New meshes for outside cells, joined to each other and their neighbours. Returns (ops for project.apply, report):
    one op for each cell made and each neighbour whose mesh had to change. A cell with no ground to walk on keeps
    nothing: its game meshes, if it has any, become stubs."""
    A = Area(gd, project)
    report = {'cells': 0, 'triangles': 0, 'doors': 0, 'doors_missed': 0, 'joined': 0, 'neighbours': 0, 'empty': [], 'stubs': 0, 'seconds': 0.0}
    far = {}
    for n, ck in enumerate(ckeys):
        if progress:
            progress(n, len(ckeys), ck)
        if not is_outside(gd, ck):
            raise NavError('%s isn\'t a cell outside.' % ck)
        row = A.meshes(ck)
        far[ck] = {x[1] for e in row for x in e['m']['ext']}
        m, rep, refs = _make_one(gd, project, ck, [e['data'] for e in row])
        report['seconds'] += rep.get('seconds') or 0
        cell = gd.from_key(ck)
        x, y = gd.cell_grid(cell)
        near = (x * N.CELL_SIZE + 2048.0, y * N.CELL_SIZE + 2048.0)
        if m is None:
            report['empty'].append(ck)
            if not row:             # (nothing here and nothing to make)
                A.cells[ck] = []
                continue
            first, rest = row[0], row[1:]
        else:
            report['cells'] += 1
            report['doors'] += len(rep['linked'])
            report['doors_missed'] += len(rep['missed'])
            first = row[0] if row else {'form': new_form(project)}
            rest = row[1:]
        stubs = []
        for e in ([first] if m is None else []) + rest:
            d = stub_data(e['form'], near)
            stubs.append({'form': e['form'], 'm': as_mesh(d), 'copy': False, 'data': d, 'new': True})
        report['stubs'] += len(stubs)
        if m is None:
            A.cells[ck] = stubs
            continue
        m['cell'] = None
        data = {'sig': outside_signature(project, ck, refs)}
        if rep['missed']:
            data['no_door'] = list(rep['missed'])
        A.cells[ck] = [{'form': first['form'], 'm': m, 'copy': False, 'data': data, 'new': True}] + stubs
    targets = [ck for ck in ckeys if A.cells.get(ck)]
    for ck in targets:
        A.forget_far(ck, far.get(ck, ()))
    report['joined'] = A.join(targets)
    report['triangles'] = sum(len(A.cells[ck][0]['m']['tris']) for ck in targets)
    bad = A.check()
    if bad:
        raise NavError('The mesh came out unsound (%s): this is a bug in FOLab, please report it.' % bad[0])
    ops = A.changed()
    report['neighbours'] = sum(1 for o in ops if o['cell'] not in ckeys)
    return ops, report


def remove_area(gd, project, ckeys):
    """Take the mod's meshes off outside cells: back to the game's, every neighbour rejoined. Returns the ops."""
    A = Area(gd, project)
    gone = set(ckeys)
    gone_forms = set()
    for ck in gone:
        now = project.navmesh.get(ck)
        if now:
            gone_forms.update(o['form'] for o in [now] + now.get('others', []))
    # copies round these start again from the game's, and whatever the mod made next to any of that is joined afresh
    fresh = set(gone)
    for ck in gone:
        for nk, _s, _xy in A.neighbours(ck):
            now = project.navmesh.get(nk)
            if now and now.get('copy'):
                fresh.add(nk)
    made = set()
    for ck in fresh:
        for nk, _s, _xy in A.neighbours(ck):
            now = project.navmesh.get(nk)
            if now and not now.get('copy') and nk not in fresh:
                made.add(nk)
    for ck in fresh:
        A.meshes(ck, fresh=True)
    for ck in made:
        for e in A.meshes(ck):
            for f in gone_forms:
                N._forget_links(e['m'], f)
    A.join(sorted(made))
    bad = A.check()
    if bad:
        raise NavError('The meshes came out unsound (%s): this is a bug in FOLab, please report it.' % bad[0])
    ops = A.changed()
    have = {o['cell'] for o in ops}
    ops += [{'op': 'navmesh_revert', 'cell': ck} for ck in fresh if ck in project.navmesh and ck not in have]
    return ops


def game_ext(gd, form):
    """A game mesh's outside links with keys, as read from the file."""
    fid = gd.from_key(form) if not form.startswith('+') else None
    e = gd.forms.get(fid) if fid is not None else None
    if not e or e[1].tag != 'NAVM':
        return []
    return game_copy(gd, e)['ext']


def status(gd, project, ckey):
    """What a place's navmesh is like now: the words in the Kit tab and on the map come from this."""
    mine = project.navmesh.get(ckey)
    game = game_meshes(gd, ckey)
    outside = is_outside(gd, ckey)
    out = {'mine': bool(mine) and not mine.get('copy'), 'game': len(game), 'outside': outside, 'can': True}
    if mine and not mine.get('copy'):
        out['triangles'] = len(mine['tris'])
        refs = place_refs(gd, project, ckey)
        out['current'] = mine.get('sig') == (outside_signature(project, ckey, refs) if outside else signature(refs))
        out['hand'] = bool(mine.get('hand'))
    return out


def world_status(gd, project, world):
    """Outside, for the map: {'x,y': state} for every cell that needs saying anything about, where state is
    'made' (the mod's mesh, up to date), 'old' (the mod's, but the cell has changed since), 'joined' (the game's, its links
    changed to meet the mod's), 'land' (the ground or water changed under the game's mesh, or no mesh at all)."""
    out = {}
    grid = gd.grid(world)
    back = {c: xy for xy, c in grid.items()}
    for ckey in set(project.navmesh) | set(project.land) | set(project.water):
        if ckey.startswith('+'):
            continue
        c = gd.from_key(ckey)
        if c not in back:
            continue
        mine = project.navmesh.get(ckey)
        if mine and not mine.get('copy'):
            refs = place_refs(gd, project, ckey)
            state = 'made' if mine.get('sig') == outside_signature(project, ckey, refs) else 'old'
        elif mine:
            state = 'land' if ckey in project.land or ckey in project.water else 'joined'
        else:
            state = 'land'
        out['%d,%d' % back[c]] = state
    return out


def shape(gd, project, ckey):
    """The mesh to draw: {'verts': flat list, 'tris': flat list of corners, 'flags': each triangle's}. The mod's, else the game's."""
    mine = project.navmesh.get(ckey)
    verts, tris, flags, forms = [], [], [], []

    def add(rows, form):
        base = len(verts) // 3
        verts.extend(c for v in rows['verts'] for c in v)
        for t in rows['tris']:
            tris.extend(c + base for c in t[:3])
            flags.append(t[6])
            forms.append(form)
    if mine:
        add(mine, 0)
        for k, o in enumerate(mine.get('others', [])):
            add(o, k + 1)
        return {'source': 'mod', 'verts': verts, 'tris': tris, 'flags': flags, 'mesh': forms}
    if not ckey.startswith('+'):
        for k, (i, rec) in enumerate(gd.navmeshes(gd.from_key(ckey))):
            add(N.read_navm(gd.plugins[i].data(rec)), k)
    return {'source': 'game' if tris else None, 'verts': verts, 'tris': tris, 'flags': flags, 'mesh': forms}


def to_record(data, cell_id, link):
    """The NAVM structure for writing: form IDs through link (a key to a form ID as the plugin numbers it)."""
    verts, tris = [tuple(v) for v in data['verts']], [tuple(t) for t in data['tris']]
    return {'version': N.VERSION, 'cell': cell_id, 'verts': verts, 'tris': tris, 'cover': list(data.get('cover', [])),
            'doors': [(link(k), t, 0) for k, t in data['doors']], 'ext': [(e[0], link(e[1]), e[2]) for e in data.get('ext', [])],
            'grid': N.build_grid(verts, tris)}


def door_tag_at(subs):
    """Where a door's XNDP goes among its subrecords: after XTEL and its kin, before the scale and the position."""
    for n, (t, _d) in enumerate(subs):
        if t in ('XSCL', 'DATA'):
            return n
    return len(subs)
