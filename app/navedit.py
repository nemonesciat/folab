"""Changing a navmesh by hand: corners moved, triangles added and deleted, edges joined and cut, triangles marked preferred
or water or as cover. Every change is checked by navmesh.validate before it's kept, and anything that names a triangle by number
is put right when the numbers change: the mesh's own edges, doors, cover list, and the links of the meshes next door (which then
go in the mod as well).

A game mesh edited here becomes the mod's own. Later generating over it replaces the hand work (the panel says so)."""
import navbuild
import navmesh as N


class EditError(ValueError):
    """Why that can't be done, in words for the person asking."""


WELD = 96.0     # joining two edges this close welds their corners; further apart it's a ledge link
AREA_MIN = 1.0  # twice the area, from above, a triangle must keep


def _area2(V, t):
    a, b, c = V[t[0]], V[t[1]], V[t[2]]
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _links_out(t, i):
    return bool(t[6] >> i & 1)


def _compact_ext(m):
    """Drop outside links no edge uses any more."""
    used, new = [], {}
    for ti, t in enumerate(m['tris']):
        edges = list(t[3:6])
        for i in range(3):
            if _links_out(t, i):
                e = t[3 + i]
                if e not in new:
                    new[e] = len(used)
                    used.append(m['ext'][e])
                edges[i] = new[e]
        m['tris'][ti] = t[:3] + tuple(edges) + t[6:]
    m['ext'] = used


def _clear_edge(m, ti, i):
    t = m['tris'][ti]
    edges = list(t[3:6])
    edges[i] = N.NONE
    m['tris'][ti] = t[:3] + tuple(edges) + (t[6] & ~(1 << i), t[7])


def _set_edge(m, ti, i, other):
    t = m['tris'][ti]
    edges = list(t[3:6])
    edges[i] = other
    m['tris'][ti] = t[:3] + tuple(edges) + t[6:]


def _add_ext(m, ti, i, kind, target, tri):
    t = m['tris'][ti]
    edges = list(t[3:6])
    edges[i] = len(m['ext'])
    m['ext'].append((kind, target, tri))
    m['tris'][ti] = t[:3] + tuple(edges) + (t[6] | 1 << i, t[7])


def retarget(m, form, mapping):
    """Mesh m's links to mesh form, its triangles renumbered by mapping (old: new, or missing: gone)."""
    changed = False
    for ti, t in enumerate(m['tris']):
        for i in range(3):
            if not _links_out(t, i) or t[3 + i] >= len(m['ext']):
                continue
            k, target, tri = m['ext'][t[3 + i]]
            if target != form:
                continue
            changed = True
            if tri in mapping:
                m['ext'].append((k, target, mapping[tri]))
                _set_edge(m, ti, i, len(m['ext']) - 1)
            else:
                _clear_edge(m, ti, i)
    if changed:
        _compact_ext(m)
    return changed


class Session:
    """One edit: the place's meshes and, as needed, those round it."""

    def __init__(self, gd, pr, ckey):
        self.gd, self.pr, self.ckey = gd, pr, ckey
        self.A = navbuild.Area(gd, pr)
        self.outside = navbuild.is_outside(gd, ckey)
        self.touched = set()

    def entry(self, ckey, mesh):
        row = self.A.meshes(ckey)
        if not 0 <= mesh < len(row):
            raise EditError('That mesh isn\'t here any more: look again.')
        return row[mesh]

    def mine(self, ckey, mesh):
        """A mesh to be changed: it's the mod's now, and goes in as changed."""
        e = self.entry(ckey, mesh)
        if e['form'] not in self.touched:
            self.touched.add(e['form'])
            if e['copy'] or not e['data'].get('hand'):
                refs = navbuild.place_refs(self.gd, self.pr, ckey)
                sig = navbuild.outside_signature(self.pr, ckey, refs) if navbuild.is_outside(self.gd, ckey) else navbuild.signature(refs)
                e['data'] = dict(e['data'], hand=True)
                e['data'].setdefault('sig', sig)
                if e['copy']:                       # (a game mesh until now: it counts as up to date as of now)
                    e['data']['sig'] = sig
                    e['data'].pop('copy', None)
            e['copy'] = False
            e['new'] = True
        return e

    def around(self, ckey):
        """Every other mesh that could link to a mesh of this place."""
        out = [e for e in self.A.meshes(ckey)]
        if navbuild.is_outside(self.gd, ckey):
            for nk, _s, _xy in self.A.neighbours(ckey):
                out += self.A.meshes(nk)
        return out

    def finish(self):
        """Checked, whole: the ops, or EditError saying what's wrong."""
        for ck, row in self.A.cells.items():
            for e in row:
                if e['form'] in self.touched:
                    N.refresh(e['m'])
                    if e['data'].get('outline') is not None:
                        e['data'] = dict(e['data'], outline=navbuild._outline_data(N.outline_of(e['m'])))
                    bad = N.validate(e['m'])
                    if bad:
                        raise EditError('That would break the mesh: %s.' % bad[0])
        return self.A.changed()

    # --- the changes ---

    def move(self, ckey, mesh, moves):
        """moves: {corner: [x, y, z]}. A corner on an edge joined across a cell's border moves up and down only."""
        e = self.mine(ckey, mesh)
        m = e['m']
        for v, p in moves.items():
            v = int(v)
            if not 0 <= v < len(m['verts']):
                raise EditError('That corner isn\'t here any more.')
            old = m['verts'][v]
            if abs(old[0] - p[0]) > 0.5 or abs(old[1] - p[1]) > 0.5:
                for t in m['tris']:
                    if v in t[:3] and any(_links_out(t, i) and v in (t[i], t[(i + 1) % 3]) and m['ext'][t[3 + i]][0] == 0 for i in range(3)):
                        raise EditError('That corner is on an edge joined to the next mesh: it can only move up and down. Cut the join first.')
            m['verts'][v] = tuple(float(c) for c in p)
        for ti, t in enumerate(m['tris']):
            if any(c in (int(k) for k in moves) for c in t[:3]) and _area2(m['verts'], t) < AREA_MIN:
                raise EditError('That would turn triangle %d over. Move the corner less far.' % ti)

    def add(self, ckey, mesh, pts):
        """A triangle: pts are three corners of the mesh (numbers) or new spots ([x, y, z])."""
        e = self.mine(ckey, mesh)
        m = e['m']
        ids = []
        for p in pts:
            if isinstance(p, int):
                if not 0 <= p < len(m['verts']):
                    raise EditError('That corner isn\'t here any more.')
                ids.append(p)
            else:
                ids.append(len(m['verts']))
                m['verts'].append(tuple(float(c) for c in p))
        if len(set(ids)) != 3:
            raise EditError('A triangle needs three different corners.')
        a = _area2(m['verts'], ids)
        if abs(a) < AREA_MIN:
            raise EditError('Those three are in a line: that\'s no triangle.')
        if a < 0:
            ids = [ids[0], ids[2], ids[1]]
        ti = len(m['tris'])
        edges = [N.NONE] * 3
        pairs = {}
        for oi, t in enumerate(m['tris']):
            for i in range(3):
                pairs[(t[i], t[(i + 1) % 3])] = (oi, i)
        for i in range(3):
            pa, pb = ids[i], ids[(i + 1) % 3]
            if (pa, pb) in pairs:
                raise EditError('Two triangles can\'t share an edge running the same way: this one overlaps triangle %d.' % pairs[(pa, pb)][0])
            hit = pairs.get((pb, pa))
            if hit:
                t = m['tris'][hit[0]]
                if t[3 + hit[1]] != N.NONE:
                    raise EditError('That edge already has a triangle joined to it.')
                _set_edge(m, hit[0], hit[1], ti)
                edges[i] = hit[0]
        m['tris'].append((ids[0], ids[1], ids[2], edges[0], edges[1], edges[2], N.F_FOUND, 0))
        return ti

    def delete(self, ckey, mesh, tris):
        """Take triangles away. Doors on them go to the nearest triangle left, or stand by none. Links to them from
        other meshes go too; the rest are renumbered."""
        e = self.mine(ckey, mesh)
        m = e['m']
        gone = {int(t) for t in tris}
        if len(gone) >= len(m['tris']):
            raise EditError('That would leave no mesh at all. Remove it with Remove from marked instead.')
        mapping, keep = {}, []
        for ti in range(len(m['tris'])):
            if ti not in gone:
                mapping[ti] = len(keep)
                keep.append(ti)
        out = []
        for ti in keep:
            t = m['tris'][ti]
            edges = list(t[3:6])
            fl = t[6]
            for i in range(3):
                if not fl >> i & 1 and edges[i] != N.NONE:
                    edges[i] = mapping.get(edges[i], N.NONE)
            out.append(t[:3] + tuple(edges) + (fl, t[7]))
        # the verts still in use
        used = sorted({c for t in out for c in t[:3]})
        vmap = {v: k for k, v in enumerate(used)}
        m['verts'] = [m['verts'][v] for v in used]
        m['tris'] = [(vmap[t[0]], vmap[t[1]], vmap[t[2]]) + t[3:] for t in out]
        m['cover'] = [mapping[c] for c in m['cover'] if c in mapping]
        _compact_ext(m)
        doors, moved, missed = [], [], []
        for d in m['doors']:
            if d[1] in mapping:
                doors.append((d[0], mapping[d[1]], d[2]))
            else:
                moved.append(d[0])
        m['doors'] = doors
        if moved:
            spots = [(k, navbuild._ref_position(self.gd, k)) for k in moved]
            found, missed = N.link_doors(m, [(k, p) for k, p in spots if p])
            missed = list(missed) + [k for k, p in spots if not p]
            if missed:
                e['data'] = dict(e['data'], no_door=list(e['data'].get('no_door', [])) + missed)
        for o in self.around(ckey):
            if o is not e and o['form'] != e['form'] and retarget(o['m'], e['form'], mapping):
                N.refresh(o['m'], grid=False)
        retarget(m, e['form'], mapping)     # (ledge links within the mesh)
        return len(gone)

    def mark(self, ckey, mesh, tris, flag, on):
        e = self.mine(ckey, mesh)
        m = e['m']
        bit = {'preferred': N.F_PREFERRED, 'water': N.F_WATER}[flag]
        for ti in tris:
            t = m['tris'][int(ti)]
            m['tris'][int(ti)] = t[:6] + ((t[6] | bit) if on else (t[6] & ~bit), t[7])

    def cover(self, ckey, mesh, ti, value):
        """A triangle's cover flags: the eighth number, its list kept with it (NVCA, as the game's meshes have it)."""
        e = self.mine(ckey, mesh)
        m = e['m']
        ti = int(ti)
        t = m['tris'][ti]
        m['tris'][ti] = t[:7] + (int(value) & 0xFFFF,)
        have = set(m['cover'])
        if int(value) & 0xFFFF:
            have.add(ti)
        else:
            have.discard(ti)
        m['cover'] = sorted(have)

    def cut(self, ckey, mesh, ti, i):
        """Cut an edge: the triangle across it stops being joined, both ways."""
        e = self.mine(ckey, mesh)
        m = e['m']
        ti, i = int(ti), int(i)
        t = m['tris'][ti]
        if t[6] >> i & 1:
            k, target, tri = m['ext'][t[3 + i]]
            _clear_edge(m, ti, i)
            for o in self.around(ckey) if target != e['form'] else [e]:
                if o['form'] == target:
                    om = o['m']
                    self.touched.add(o['form']) if o is e else None
                    if tri < len(om['tris']):
                        ot = om['tris'][tri]
                        for j in range(3):
                            if ot[6] >> j & 1 and ot[3 + j] < len(om['ext']) and om['ext'][ot[3 + j]][1:] == (e['form'], ti):
                                _clear_edge(om, tri, j)
                    _compact_ext(om)
            _compact_ext(m)
        elif t[3 + i] != N.NONE:
            other = t[3 + i]
            ot = m['tris'][other]
            _clear_edge(m, ti, i)
            for j in range(3):
                if ot[3 + j] == ti and not ot[6] >> j & 1:
                    _clear_edge(m, other, j)
        else:
            raise EditError('That edge isn\'t joined to anything.')

    def join(self, a, b):
        """Join two free edges, a and b = [cell, mesh, triangle, edge]. In one mesh, edges close together become one, their
        corners welded; further apart, or in two meshes, a link (a ledge link if there's a drop between them)."""
        ea, eb = self.mine(a[0], a[1]), self.mine(b[0], b[1])
        ma, mb = ea['m'], eb['m']
        ta, ia, tb, ib = int(a[2]), int(a[3]), int(b[2]), int(b[3])
        if ta >= len(ma['tris']) or tb >= len(mb['tris']):
            raise EditError('Those triangles aren\'t here any more.')
        ta_t, tb_t = ma['tris'][ta], mb['tris'][tb]
        if ea is eb and ta == tb:
            raise EditError('Pick edges of two different triangles.')
        if ta_t[6] >> ia & 1 or ta_t[3 + ia] != N.NONE or tb_t[6] >> ib & 1 or tb_t[3 + ib] != N.NONE:
            raise EditError('Both edges must be free: cut what they\'re joined to first.')
        pa, qa = ma['verts'][ta_t[ia]], ma['verts'][ta_t[(ia + 1) % 3]]
        pb, qb = mb['verts'][tb_t[ib]], mb['verts'][tb_t[(ib + 1) % 3]]
        d = lambda u, v: ((u[0] - v[0]) ** 2 + (u[1] - v[1]) ** 2 + (u[2] - v[2]) ** 2) ** 0.5
        near = d(pa, qb) <= WELD and d(qa, pb) <= WELD
        if ea is eb and near:
            self._weld(ma, ta_t[ia], tb_t[(ib + 1) % 3])
            self._weld(ma, ta_t[(ia + 1) % 3], tb_t[ib])
            _set_edge(ma, ta, ia, tb)
            _set_edge(ma, tb, ib, ta)
            for ti, t in enumerate(ma['tris']):
                if ti in (ta, tb) and _area2(ma['verts'], t) < AREA_MIN:
                    raise EditError('Those corners can\'t meet without turning a triangle over.')
            return 'welded'
        same_level = abs((pa[2] + qa[2]) / 2 - (pb[2] + qb[2]) / 2) <= N.LINK_HEIGHT
        if ea is eb or not same_level:
            # (the game keeps these within one cell: one link up, one down)
            ka = 1 if (pb[2] + qb[2]) > (pa[2] + qa[2]) else 2
            kb = 3 - ka
        else:
            ka = kb = 0
        _add_ext(ma, ta, ia, ka, eb['form'], tb)
        _add_ext(mb, tb, ib, kb, ea['form'], ta)
        return 'link'

    @staticmethod
    def _weld(m, keep, drop):
        if keep == drop:
            return
        for ti, t in enumerate(m['tris']):
            if drop in t[:3]:
                c = tuple(keep if x == drop else x for x in t[:3])
                if len(set(c)) < 3:
                    raise EditError('Those corners can\'t be welded: a triangle would collapse.')
                m['tris'][ti] = c + t[3:]


def view(gd, pr, ckey):
    """A place's meshes for the editor, everything it may need to know."""
    now = pr.navmesh.get(ckey) if pr else None
    datas = ([now] + now.get('others', [])) if now else [navbuild.game_copy(gd, e) for e in navbuild.game_entries(gd, ckey)]
    return {'cell': ckey, 'source': 'mod' if now and not now.get('copy') else 'game' if datas else None,
            'meshes': [{'form': d['form'], 'verts': d['verts'], 'tris': d['tris'], 'ext': d.get('ext', []), 'doors': d['doors'],
                        'hand': bool(d.get('hand')), 'stub': bool(d.get('stub'))} for d in datas]}


def act(gd, pr, a):
    """One change asked for from the page: (ops for project.apply, a label, cells the view must draw again)."""
    s = Session(gd, pr, a['cell'])
    what = a['do']
    mesh = int(a.get('mesh', 0))
    if what == 'move':
        s.move(a['cell'], mesh, a['moves'])
        label = 'Move navmesh corner'
    elif what == 'add':
        s.add(a['cell'], mesh, [p if isinstance(p, list) else int(p) for p in a['pts']])
        label = 'Add navmesh triangle'
    elif what == 'delete':
        s.delete(a['cell'], mesh, a['tris'])
        label = 'Delete navmesh triangles'
    elif what == 'mark':
        s.mark(a['cell'], mesh, a['tris'], a['flag'], bool(a['on']))
        label = 'Mark navmesh triangles %s' % a['flag']
    elif what == 'cover':
        s.cover(a['cell'], mesh, a['tri'], a['value'])
        label = 'Navmesh cover'
    elif what == 'cut':
        s.cut(a['cell'], mesh, a['tri'], a['edge'])
        label = 'Cut navmesh edge'
    elif what == 'join':
        s.join(a['a'], a['b'])
        label = 'Join navmesh edges'
    else:
        raise EditError('No such change: %s' % what)
    ops = s.finish()
    return ops, label, [o['cell'] for o in ops]
