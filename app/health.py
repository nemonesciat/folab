"""The health check: what's wrong with a plugin, in plain words, each with where it is and, where it's safe, a fix.

It reads the plugin itself, so it works on any plugin: the open mod (written to a scratch file first, so what's checked
is what would be saved, and the keys it gives are the project's so a click can go there) or someone else's, read only.

    Scan(gd, path, ...)         reads one plugin against the game
    check_mod(server)           the open mod, with the checks only a project can have (navmesh out of date...)
    check_file(gd, path)        any plugin, read only: no fixes
    fix_ops(server, fixes)      the fixes asked for, as one undoable step

A fix never changes the game's files; it's a change to the mod like any other."""
import hashlib
import os
import re
import struct
import tempfile

import formlinks
import gamedata
import navbuild
import project as projectmod
import recordio
import schema
import scriptc
import tes4

ERROR, WARN, INFO = 'error', 'warn', 'info'
KINDS = {
    'cant_write': (ERROR, 'Can\'t be saved', 'FOLab can\'t write the plugin as it stands.'),
    'broken': (ERROR, 'Damaged records', 'Records FOLab can\'t read. The game may not be able to either.'),
    'master': (ERROR, 'Missing masters', 'Files this plugin needs that aren\'t in the game\'s Data folder. The game won\'t start with it switched on.'),
    'link': (ERROR, 'Links to things that don\'t exist', 'Something points at a record that isn\'t there. Usually harmless until the game reaches for it, then a crash or something missing.'),
    'deleted_ref': (ERROR, 'Deleted things', 'Things of the game\'s that were deleted outright. A save that knew them, or another mod using them, can crash the game. The safe way is to disable them and sink them out of sight.'),
    'deleted_record': (WARN, 'Deleted records', 'Records of the game\'s that were deleted. Anything else using them will break.'),
    'no_compile': (ERROR, 'Scripts with no compiled code', 'Scripts with text but nothing the game can run. They do nothing in game.'),
    'door_gone': (ERROR, 'Doors to removed doors', 'A door leads to a door that has been removed, deep under the floor.'),
    'mesh': (ERROR, 'Missing meshes', 'Models no file can be found for, loose or in an archive. The game shows a bright "!" or nothing, or can crash.'),
    'texture': (WARN, 'Missing textures', 'Pictures no file can be found for. The game shows purple or nothing.'),
    'navmesh_missing': (WARN, 'Characters with no navmesh', 'Places with characters and no navmesh. Characters can\'t find their way: they stand still or walk into walls.'),
    'navmesh_old': (WARN, 'Navmesh out of date', 'What\'s in the place has changed since its navmesh was made.'),
    'no_way_back': (WARN, 'Doors with no way back', 'A door leads somewhere, but the door at the other end doesn\'t lead back.'),
    'same': (WARN, 'Changes identical to the game', 'Records that say just what the game already says. They do nothing except get in the way of other mods.'),
    'same_edid': (WARN, 'Two things with one editor ID', 'Scripts and the console find things by editor ID: only one of these can be found.'),
    'no_lights': (INFO, 'Places with no lights', 'Places with no lights in them, so only the place\'s own ambient light shows them.'),
    'unreachable': (INFO, 'Places nothing leads to', 'Places of the mod\'s own that no door in it leads to. Fine if you only reach them another way.'),
    'unused_master': (INFO, 'Masters nothing uses', 'Files the plugin says it needs, though nothing in it uses them. It makes players install more than they need.'),
    'navmesh_game': (INFO, 'Places changed, the game\'s navmesh kept', 'You added or removed things in a place that still has the game\'s navmesh. Characters may walk through or round them.'),
}
ORDER = list(KINDS)
LIMIT = 400                 # (of one kind, listed; the count is always the full one)

TYPE_WORDS = {t: lab for t, (lab, _l) in schema.TYPES.items()}
TYPE_WORDS.update({'REFR': 'Placed thing', 'ACHR': 'Placed character', 'ACRE': 'Placed creature', 'PGRE': 'Placed grenade', 'PMIS': 'Placed mine',
                   'SCPT': 'Scripts', 'NAVM': 'Navmesh', 'LAND': 'Ground', 'NAVI': 'Navmesh index', 'WTHR': 'Weather', 'SOUN': 'Sounds'})
PLACED = formlinks.PLACED_TAGS
MODEL_ENDS = ('.nif', '.kf', '.egm', '.egt', '.tri', '.spt')
MESH_FIELDS = {'MODL', 'MOD2', 'MOD3', 'MOD4', 'DMDL', 'NAM1'} | {'MWD%d' % i for i in range(1, 8)}
TEX_FIELDS = {'ICON', 'MICO', 'ICO2', 'MIC2', 'FNAM', 'GNAM', 'DNAM', 'CNAM', 'ANAM', 'BNAM', 'XNAM', 'NNAM'} | {'TX0%d' % i for i in range(8)}
NO_ASSETS = {'REFR', 'ACHR', 'ACRE', 'PGRE', 'PMIS', 'LAND', 'NAVM', 'NAVI', 'INFO', 'DIAL', 'QUST', 'CELL', 'SCPT', 'GMST'}
# (fields the game keeps for nothing: dozens of its own records name files that never existed)
NOT_USED = {('ARMA', 'ICON'), ('ARMA', 'ICO2'), ('TREE', 'ICON')}
PARENTS = {'CELL', 'WRLD', 'DIAL'}          # (a plugin has to carry these to change what's in them)
ACTOR_REFS = {'ACHR', 'ACRE'}
SUNK = -20000.0                             # (anything below this has been sunk out of sight)
DISABLED = 0x800


def asset_path(tag, st, data):
    """(kind, path under Data) of a file a subrecord names, or None."""
    if tag in NO_ASSETS or (tag, st) in NOT_USED or not data.endswith(b'\0') or len(data) < 6:
        return None
    if st not in MESH_FIELDS and st not in TEX_FIELDS:
        return None
    v = tes4.zstr(data).strip().replace('/', '\\').lower().lstrip('\\')
    if not v or not all(32 <= ord(c) < 127 for c in v):
        return None
    if v.startswith('data\\'):
        v = v[5:]
    if v.endswith(MODEL_ENDS):
        pre = 'trees\\' if tag == 'TREE' else 'meshes\\'
        return ('mesh', v if v.startswith(pre) else pre + v)
    if v.endswith('.dds'):
        return ('texture', v if v.startswith('textures\\') else 'textures\\' + v)
    return None


def has_code(text):
    """Script text with something in it besides comments."""
    return any(l.strip() and not l.strip().startswith(b';') for l in text.rstrip(b'\0').splitlines())


class SideFiles:
    """Masters FOLab hasn't loaded (another mod's), read just enough to know what's in them."""

    def __init__(self, data_dir):
        self.data_dir, self.seen = data_dir, {}

    def forms(self, name):
        low = name.lower()
        if low not in self.seen:
            p = os.path.join(self.data_dir or '', name)
            if not os.path.isfile(p):
                self.seen[low] = None
            else:
                pf = tes4.PluginFile(p)
                own = len(pf.header['masters'])
                self.seen[low] = {r.formid & 0xFFFFFF for r, _g in pf.walk() if r.formid >> 24 == own}
                pf.close()
        return self.seen[low]


class Scan:
    def __init__(self, gd, path, pr=None, data_dir=None):
        self.gd, self.path, self.pr = gd, path, pr
        self.pf = tes4.PluginFile(path)
        self.name = os.path.basename(path)
        self.lower = self.name.lower()
        self.masters = list(self.pf.header['masters'])
        self.own = len(self.masters)
        self.new_mod = bool(pr and not pr.source)
        self.side = SideFiles(data_dir or gd.data_dir)
        self.issues = {}
        self.counts = {}
        self.here = {}          # form ID as this plugin numbers it -> (record, groups)
        self.parents = set()    # form IDs that have groups under them here
        self.subs_of = {}
        self.ref_cell = {}      # a ref's form ID -> its cell's form ID
        self.lower_names = [m.lower() for m in self.masters]
        self.changed = {}       # project: a ref's key -> its cell's key, from the project's changes
        self.nav_cells = set()  # cells with a navmesh in this plugin
        self.unused = []        # masters nothing uses
        if pr:
            for ck, c in pr.cells.items():
                for rk in c['refs']:
                    self.changed[rk] = ck

    def close(self):
        self.pf.close()

    # ---- forms ----

    def owner(self, v):
        i = v >> 24
        return self.masters[i] if i < self.own else self.name

    def key(self, v):
        if v >> 24 >= self.own:
            return '+%06X' % (v & 0xFFFFFF) if self.new_mod else '%s:%06X' % (self.name, v & 0xFFFFFF)
        return '%s:%06X' % (self.masters[v >> 24], v & 0xFFFFFF)

    def global_id(self, v):
        """Where a form is in the loaded game (the game's index), or None when its file isn't loaded."""
        name = self.owner(v).lower()
        if name in self.gd.names:
            return (self.gd.names.index(name) << 24) | (v & 0xFFFFFF)
        return None

    def exists(self, v):
        low = v & 0xFFFFFF
        if low < gamedata.BUILTIN_LIMIT or v in self.here:
            return True
        if v >> 24 > self.own:
            return False
        if v >> 24 == self.own:
            return False
        g = self.global_id(v)
        if g is not None:
            return g in self.gd.forms
        known = self.side.forms(self.owner(v))
        return True if known is None else low in known     # (its file is missing: told about once, as a master)

    def tag_of(self, v):
        if v in self.here:
            return self.here[v][0].tag
        g = self.global_id(v)
        e = self.gd.forms.get(g) if g is not None else None
        return e[1].tag if e else None

    def subs(self, rec):
        return list(tes4.iter_subrecords(self.pf.data(rec)))

    def edid(self, v):
        """An editor ID (or name) for a form, from this plugin or the game."""
        if v in self.here:
            f = dict(reversed(self.subs(self.here[v][0])))
        else:
            g = self.global_id(v)
            if g is None or g not in self.gd.forms:
                return ''
            f = self.gd.fields(g)
        return tes4.zstr(f.get('EDID', b'')) or tes4.zstr(f.get('FULL', b''))

    def label(self, v):
        e = self.edid(v)
        return e or self.key(v)

    # ---- where ----

    def where(self, rec, path):
        """Where a click goes for this record."""
        v = rec.formid
        if rec.tag in PLACED or rec.tag == 'NAVM' or rec.tag == 'LAND':
            cell = self.cell_of(path)
            out = {'cell': self.key(cell) if cell is not None else None}
            if rec.tag in PLACED:
                out['ref'] = self.key(v)
            world = next((lab for gt, lab, _o in path if gt == tes4.G_WORLD_CHILDREN), None)
            if world is not None:
                out['world'] = self.key(world)
                d = dict(reversed(self.subs(rec))).get('DATA') if rec.tag in PLACED else None
                if d and len(d) >= 12:
                    out['p'] = list(struct.unpack_from('<3f', d))
            return out
        if rec.tag == 'CELL':
            world = next((lab for gt, lab, _o in path if gt == tes4.G_WORLD_CHILDREN), None)
            if world is None:
                return {'cell': self.key(v)}
            out = {'world': self.key(world)}
            xclc = dict(reversed(self.subs(rec))).get('XCLC')
            if xclc and len(xclc) >= 8:
                x, y = struct.unpack_from('<2i', xclc)
                out['p'] = [x * 4096 + 2048, y * 4096 + 2048, 0]
            return out
        return {'record': self.key(v)}

    @staticmethod
    def cell_of(path):
        for gt, lab, _o in reversed(path):
            if gt in (tes4.G_CELL_PERSISTENT, tes4.G_CELL_TEMPORARY, tes4.G_CELL_VWD, tes4.G_CELL_CHILDREN):
                return lab
        return None

    def add(self, kind, text, where=None, fix=None, sub=None):
        self.counts[kind] = self.counts.get(kind, 0) + 1
        rows = self.issues.setdefault(kind, [])
        if len(rows) < LIMIT:
            row = {'text': text}
            if where:
                row['go'] = where
            if fix:
                row['fix'] = fix
            if sub:
                row['sub'] = sub
            rows.append(row)

    # ---- the checks ----

    def run(self):
        for rec, path in self.pf.walk():
            self.here[rec.formid] = (rec, path)
            for gt, lab, _o in path:
                if gt in formlinks.LABEL_IS_FORM:
                    self.parents.add(lab)
            if rec.tag in PLACED or rec.tag == 'NAVM':
                c = self.cell_of(path)
                if c is not None:
                    self.ref_cell[rec.formid] = c
                    if rec.tag == 'NAVM':
                        self.nav_cells.add(c)
        self.check_masters()
        self.assets = {}
        used, edids, overrides, doors, scripts = set(), {}, [], [], []
        place_refs = {}
        for v, (rec, path) in self.here.items():
            try:
                subs = self.subs(rec)
            except Exception as e:
                self.add('broken', '%s %s can\'t be read (%s).' % (self.word(rec.tag), self.key(v), e), self.where(rec, []))
                continue
            f = {}
            for t, d in subs:
                f.setdefault(t, d)
            self.check_links(rec, path, subs, used)
            if rec.flags & tes4.DELETED:
                self.check_deleted(rec, path)
            if v >> 24 < self.own:
                used.add(v >> 24)
                overrides.append(v)
            if v >> 24 == self.own and 'EDID' in f and rec.tag not in ('NAVM', 'LAND'):
                edids.setdefault(tes4.zstr(f['EDID']).lower(), []).append(v)
            for t, d in subs:
                a = asset_path(rec.tag, t, d)
                if a:
                    self.assets.setdefault(a, (rec, path))
            if rec.tag in PLACED:
                if len(f.get('XTEL', b'')) >= 4:
                    doors.append((rec, path, f))
                c = self.ref_cell.get(v)
                if c is not None and not rec.flags & tes4.DELETED:
                    place_refs.setdefault(c, []).append((rec, f))
            elif 'SCTX' in f or 'SCDA' in f or rec.tag == 'SCPT':
                scripts.append((rec, path, subs))
        for gt_label in self.parents:
            if gt_label >> 24 < self.own:
                used.add(gt_label >> 24)
        self.check_assets()
        self.check_same(overrides)
        self.check_doors(doors)
        self.check_scripts(scripts)
        self.check_places(place_refs, doors)
        for e, vs in edids.items():
            if len(vs) > 1 and e:
                self.add('same_edid', '%s is the editor ID of %d records.' % (e, len(vs)), self.where(*self.here[vs[0]]),
                         sub=[self.key(x) for x in vs[:6]])
        for i, m in enumerate(self.masters):
            if i not in used and i > 0:     # (the first is the game itself: every plugin needs it)
                self.unused.append(m)
                self.add('unused_master', '%s names %s as a master, but nothing in it uses that file.' % (self.name, m))
        return self

    def word(self, tag):
        return TYPE_WORDS.get(tag, tag)

    def what(self, rec):
        e = self.edid(rec.formid)
        if not e and rec.tag in PLACED:                 # (placed things rarely have a name: say what they are)
            name = dict(reversed(self.subs(rec))).get('NAME')
            base = self.label(struct.unpack_from('<I', name)[0]) if name and len(name) == 4 else ''
            if base:
                return '%s (a placed thing, %s)' % (base, self.key(rec.formid))
        return '%s%s' % (e or self.key(rec.formid), ' (%s)' % self.word(rec.tag))

    def check_masters(self):
        data_dir = self.side.data_dir
        for m in self.masters:
            if m.lower() in self.gd.names:
                continue
            if not data_dir or not os.path.isfile(os.path.join(data_dir, m)):
                self.add('master', '%s needs %s, which isn\'t in the game\'s Data folder.' % (self.name, m))

    def _field_word(self, tag, st, data):
        try:
            return schema.decode_sub(tag, st, data)['label']
        except Exception:
            return st

    def check_links(self, rec, path, subs, used):
        known = None
        for n, o, v in formlinks.values(rec.tag, subs, self.own):
            if v >> 24 < self.own:
                used.add(v >> 24)
            if self.exists(v):
                continue
            st, d = subs[n]
            field = self._field_word(rec.tag, st, d)
            bad = v >> 24 > self.own
            text = '%s: its %s %s.' % (self.what(rec), field,
                                       'points past the end of the plugin\'s masters (%08X)' % v if bad else 'links to %s, which doesn\'t exist' % self.key(v))
            fix = None
            if self.pr:
                if known is None:
                    known = set(schema.record_form_offsets(rec.tag, subs)) if rec.tag in schema.TYPES else set()
                k = self.key(rec.formid)
                if rec.tag in PLACED:
                    cell = self.changed.get(k) or (self.key(self.cell_of(path)) if self.cell_of(path) is not None else None)
                    if st == 'NAME' and rec.formid >> 24 == self.own and cell:
                        fix = {'action': 'remove_ref', 'cell': cell, 'ref': k, 'label': 'Remove the thing'}
                    elif st == 'XTEL' and cell:
                        fix = {'action': 'unlink', 'cell': cell, 'ref': k, 'label': 'Clear the door\'s link'}
                elif (n, o) in known and not bad and rec.tag != 'CELL':
                    fix = {'action': 'clear_link', 'key': k, 'target': self.key(v), 'label': 'Clear the link'}
            self.add('link', text, self.where(rec, path), fix)

    def check_deleted(self, rec, path):
        v = rec.formid
        k = self.key(v)
        if rec.tag in PLACED:
            cell = self.cell_of(path)
            can = self.pr and cell is not None
            if v >> 24 >= self.own:
                fix = {'action': 'remove_ref', 'cell': self.key(cell), 'ref': k, 'label': 'Take it out'} if can else None
                self.add('deleted_ref', '%s is the plugin\'s own and marked deleted: it can simply go.' % self.what(rec), self.where(rec, path), fix)
                return
            fix = {'action': 'sink', 'cell': self.key(cell), 'ref': k, 'label': 'Disable and sink it'} if can else None
            self.add('deleted_ref', '%s (%s) is deleted outright.' % (self.what(rec), k), self.where(rec, path), fix)
        elif v >> 24 < self.own:
            fix = {'action': 'drop', 'key': k, 'label': 'Keep the game\'s'} if self.pr else None
            self.add('deleted_record', '%s is deleted.%s' % (self.what(rec), ' A deleted navmesh crashes the game when anything looks for it.' if rec.tag == 'NAVM' else ''),
                     {'record': k} if rec.tag not in ('NAVM', 'CELL', 'LAND') else None, fix)

    def check_assets(self):
        for (kind, rel), (rec, path) in sorted(self.assets.items()):
            if self.gd.find_file(rel) or (self.pr and os.path.isfile(os.path.join(projectmod.PROJECTS_DIR, self.pr.name + ' files', rel))):
                continue
            self.add(kind, '%s needs %s, and there\'s no such file.' % (self.what(rec), rel), self.where(rec, path))

    # ---- the same as the game ----

    def _normal(self, pf, tag, data, own_name):
        """A record's bytes with every link spelled by its file, so copies numbered differently compare equal."""
        subs = list(tes4.iter_subrecords(data))
        masters = pf.header['masters']
        own = len(masters)

        def spell(v):
            return self._reg(masters[v >> 24] if v >> 24 < own else own_name, v & 0xFFFFFF)
        out, _ = formlinks.repoint(tag, subs, own, spell)
        return out

    def _reg(self, name, low):
        names = self.__dict__.setdefault('_names', {})
        return (names.setdefault(name.lower(), len(names) + 1) << 24) | low

    def _earlier(self, wanted):
        """The record each form ID has in the files before this plugin: {form ID: (plugin file, Record)}."""
        out, walk = {}, {}
        for v in wanted:
            g = self.global_id(v)
            e = self.gd.forms.get(g) if g is not None else None
            if e and self.gd.names[e[0]] != self.lower:
                out[v] = (self.gd.plugins[e[0]], e[1])
            else:
                walk[v] = g
        if walk:
            # (an opened mod is loaded on top, so the game's copy is under it: look in its masters, last first)
            left = set(walk)
            for m in reversed(self.masters):
                if not left:
                    break
                low = m.lower()
                if low in self.gd.names:
                    pf = self.gd.plugins[self.gd.names.index(low)]
                else:
                    p = os.path.join(self.side.data_dir or '', m)
                    if not os.path.isfile(p):
                        continue
                    pf = tes4.PluginFile(p)
                own = {}
                for mi, mn in enumerate(pf.header['masters']):
                    own[mi] = mn.lower()
                own[len(pf.header['masters'])] = low
                want = {(self.lower_owner(v), v & 0xFFFFFF): v for v in left}
                for r, _g in pf.walk():
                    k = (own.get(r.formid >> 24), r.formid & 0xFFFFFF)
                    if k in want and want[k] in left:
                        out[want[k]] = (pf, r)
                        left.discard(want[k])
        return out

    def lower_owner(self, v):
        return self.owner(v).lower()

    def check_same(self, overrides):
        rows = [v for v in overrides if not (self.here[v][0].tag in PARENTS and v in self.parents)
                and not self.here[v][0].flags & tes4.DELETED and self.here[v][0].tag != 'NAVI']
        if not rows:
            return
        earlier = self._earlier(rows)
        for v in rows:
            rec, path = self.here[v]
            e = earlier.get(v)
            if not e:
                continue
            pf, orig = e
            try:
                a = self._normal(self.pf, rec.tag, self.pf.data(rec), self.name)
                b = self._normal(pf, orig.tag, pf.data(orig), os.path.basename(pf.path))
            except Exception:
                continue
            if a != b or (rec.flags & ~tes4.COMPRESSED) != (orig.flags & ~tes4.COMPRESSED):
                continue
            self.add('same', '%s says just what the game says.' % self.what(rec), self.where(rec, path), self._same_fix(v, path))

    def _same_fix(self, v, path):
        if not self.pr:
            return None
        k = self.key(v)
        rec = self.here[v][0]
        if k in self.pr.records:
            return {'action': 'revert_record', 'key': k, 'label': 'Take it out'}
        if k in self.changed:
            return {'action': 'revert_ref', 'cell': self.changed[k], 'ref': k, 'label': 'Take it out'}
        if self.pr.source:
            return {'action': 'drop', 'key': k, 'label': 'Take it out'}
        return None

    # ---- doors ----

    def _door_fields(self, v):
        """(fields, flags) of a door as the plugin leaves it; None when it can't be found."""
        if v in self.here:
            rec = self.here[v][0]
            return dict(reversed(self.subs(rec))), rec.flags, None
        g = self.global_id(v)
        cell = self.gd.ref_cell.get(g) if g is not None else None
        e = self.gd.cell_refs.get(cell, {}).get(g) if cell is not None else None
        if not e:
            return None
        i, rec = e
        return self.gd.plugins[i].fields(rec), rec.flags, i

    def check_doors(self, doors):
        for rec, path, f in doors:
            if rec.flags & (tes4.DELETED | DISABLED):
                continue
            target = struct.unpack_from('<I', f['XTEL'])[0]
            if not target:
                continue
            got = self._door_fields(target)
            if got is None:
                continue                    # (a dead link: told about as one)
            tf, flags, i = got
            d = tf.get('DATA')
            if flags & tes4.DELETED or (flags & DISABLED and d and len(d) >= 12 and struct.unpack_from('<3f', d)[2] < SUNK):
                self.add('door_gone', '%s leads to %s, which has been removed.' % (self.what(rec), self.label(target)), self.where(rec, path))
                continue
            back = tf.get('XTEL')
            if not back:
                self.add('no_way_back', '%s leads to %s, which leads nowhere.' % (self.what(rec), self.label(target)), self.where(rec, path))
                continue
            bv = struct.unpack_from('<I', back)[0]
            if i is not None:               # (the other door is the game's: its own numbering)
                same = self.gd.to_global(i, bv) == self.global_id(rec.formid)
            else:
                same = bv == rec.formid
            if not same:
                self.add('no_way_back', '%s leads to %s, but that door leads somewhere else.' % (self.what(rec), self.label(target)), self.where(rec, path))

    # ---- scripts ----

    def check_scripts(self, scripts):
        for rec, path, subs in scripts:
            pairs = []
            for t, d in subs:                       # (a record can hold several: a quest's stages, a terminal's lines)
                if t == 'SCHR':
                    pairs.append([d, None, None])
                elif t == 'SCDA' and pairs:
                    pairs[-1][1] = d
                elif t == 'SCTX':
                    if not pairs or pairs[-1][2] is not None:
                        pairs.append([None, None, None])
                    pairs[-1][2] = d
                elif t == 'SCDA':
                    pairs.append([None, d, None])
            for schr, data, text in pairs:
                if text and not data and has_code(text):
                    self.add('no_compile', '%s has script text but no compiled code.' % self.what(rec), self.where(rec, path), self._compile_fix(rec))
                    break

    def _compile_fix(self, rec):
        if not self.pr or rec.tag != 'SCPT':
            return None
        return {'action': 'compile', 'key': self.key(rec.formid), 'label': 'Compile it'}

    # ---- places ----

    def check_places(self, place_refs, doors):
        reachable = set()
        for rec, path, f in doors:
            t = struct.unpack_from('<I', f['XTEL'])[0]
            if t in self.ref_cell:
                reachable.add(self.ref_cell[t])
        for v, (rec, path) in self.here.items():
            if rec.tag != 'CELL' or rec.flags & tes4.DELETED:
                continue
            if next((1 for gt, _l, _o in path if gt == tes4.G_WORLD_CHILDREN), None):
                continue
            mine = place_refs.get(v, [])
            if not mine and v >> 24 < self.own:
                continue
            self._check_place(v, rec, path, mine, v in reachable)
        # (characters put in the world's cells: only their navmesh is asked after, and FOLab can't make those yet)

    def _check_place(self, v, rec, path, mine, reached):
        own_place = v >> 24 == self.own
        gcell = self.global_id(v)
        # what's in it as the plugin leaves it
        changed = {r.formid: (r, f) for r, f in mine}
        game = {}
        if not own_place and gcell is not None:
            for t in self.gd.refs(gcell):
                game[t['ref']] = t
        actors = any(r.tag in ACTOR_REFS and not r.flags & DISABLED for r, _f in mine)
        lights = 0
        had_lights = 0
        bases = lambda f: struct.unpack_from('<I', f['NAME'])[0] if len(f.get('NAME', b'')) == 4 else None
        for r, f in mine:
            d = f.get('DATA')
            sunk = r.flags & DISABLED and d and len(d) >= 12 and struct.unpack_from('<3f', d)[2] < SUNK
            b = bases(f)
            if not sunk and b is not None and self.tag_of(b) == 'LIGH':
                lights += 1
        names = self.gd.names
        for g, t in game.items():
            low = g & 0xFFFFFF
            local = None
            owner = names[g >> 24]
            if owner in self.lower_names:
                local = (self.lower_names.index(owner) << 24) | low
            elif owner == self.lower:
                local = (self.own << 24) | low
            if t['base'] in self.gd.forms and self.gd.forms[t['base']][1].tag == 'LIGH':
                had_lights += 1
                if local not in changed:
                    lights += 1
        place = '%s' % (self.edid(v) or self.key(v))
        key = self.key(v)
        if not lights and (own_place or had_lights):
            ambient = None
            xcll = dict(reversed(self.subs(rec))).get('XCLL')
            if xcll and len(xcll) >= 4:
                ambient = sum(xcll[:3])
            dim = ' and its ambient light is close to black' if ambient is not None and ambient < 45 else ''
            self.add('no_lights', '%s has no lights%s.' % (place, dim), {'cell': key})
        if actors:
            has = v in self.nav_cells
            if not has and gcell is not None:
                has = bool(self.gd.navmeshes(gcell))
            if not has and self.pr:
                has = key in self.pr.navmesh
            if not has:
                fix = {'action': 'navmesh', 'cell': key, 'label': 'Make a navmesh'} if self.pr else None
                self.add('navmesh_missing', '%s has characters and no navmesh.' % place, {'cell': key}, fix)
        if own_place and not reached:
            self.add('unreachable', 'No door in the plugin leads to %s.' % place, {'cell': key})

    def report(self):
        groups = []
        for kind in ORDER:
            if kind in self.issues:
                sev, title, why = KINDS[kind]
                rows = self.issues[kind]
                groups.append({'kind': kind, 'sev': sev, 'title': title, 'why': why, 'count': self.counts[kind], 'rows': rows,
                               'fixable': sum(1 for r in rows if r.get('fix') and not r['fix'].get('one'))})
        return groups


# ---------- the open mod ----------

def scratch_dir():
    return os.path.join(projectmod.HOME, 'cache', 'health')


def scratch_path(plugin):
    """A file of the plugin's name, in a folder of its own: two scans at once can't get in each other's way."""
    os.makedirs(scratch_dir(), exist_ok=True)
    return os.path.join(tempfile.mkdtemp(dir=scratch_dir()), plugin)


def project_links(gd, pr):
    """Links in the project that name a file no longer loaded, which the writer can't even number: [(what, where, fix)]."""
    out = []
    known = lambda k: k.startswith('+') or k.rsplit(':', 1)[0].lower() in gd.names
    for key, rec in pr.records.items():
        if not known(key):
            out.append(('%s changes something in %s, which isn\'t loaded.' % (key, key.rsplit(':', 1)[0]), None, {'action': 'revert_record', 'key': key, 'label': 'Take the change out'}))
            continue
        for k in recordio.links(rec):
            if not known(k):
                out.append(('%s links to %s, in a file that isn\'t loaded.' % (recordio.field(rec, 'EDID') or key, k), {'record': key},
                            {'action': 'clear_link', 'key': key, 'target': k, 'label': 'Clear the link'}))
    for ck, c in pr.cells.items():
        for rk, r in c['refs'].items():
            for k, f in ((r.get('base'), 'base'), ((r.get('tel') or {}).get('door'), 'tel')):
                if k and not known(k):
                    fix = {'action': 'remove_ref', 'cell': ck, 'ref': rk, 'label': 'Remove the thing'} if rk.startswith('+') and f == 'base' else \
                        {'action': 'unlink', 'cell': ck, 'ref': rk, 'label': 'Clear the door\'s link'} if f == 'tel' else None
                    out.append(('A thing in your mod uses %s, in a file that isn\'t loaded.' % k, {'cell': ck, 'ref': rk}, fix))
    return out


def check_mod(S):
    """The open mod as it would be saved now, with the checks only a project has. S: the server module."""
    gd, pr = S.GD, S.PR
    import espwrite
    path = scratch_path(pr.plugin)
    pre = project_links(gd, pr)
    built = None
    with S._lock:
        if not pre:
            try:
                data = espwrite.Writer(gd, pr).build()
                with open(path, 'wb') as f:
                    f.write(data)
                built = path
            except Exception as e:
                pre.append(('The plugin can\'t be written: %s' % e, None, None))
    groups, counts = [], {}
    if built:
        scan = Scan(gd, built, pr).run()
        try:
            check_project_nav(scan, gd, pr)
            groups = scan.report()
        finally:
            scan.close()
            _remove(path)
    else:
        rows = [dict(text=t, **({'go': w} if w else {}), **({'fix': f} if f else {})) for t, w, f in pre]
        sev, title, why = KINDS['link' if pre and pre[0][2] else 'cant_write']
        groups = [{'kind': 'link' if pre and pre[0][2] else 'cant_write', 'sev': sev, 'title': title, 'why': why, 'count': len(rows), 'rows': rows,
                   'fixable': sum(1 for r in rows if r.get('fix'))}]
    return {'plugin': pr.plugin, 'mine': True, 'groups': groups, 'summary': _summary(groups)}


def _remove(path):
    try:
        os.remove(path)
        os.rmdir(os.path.dirname(path))
    except OSError:
        pass


def check_project_nav(scan, gd, pr):
    """Navmeshes the mod made that the place has moved on from; the game's kept where the mod has built."""
    for ckey, mesh in pr.navmesh.items():
        if ckey.startswith('+') and ckey not in pr.records:
            continue
        st = navbuild.status(gd, pr, ckey)
        if st.get('mine') and not st.get('current'):
            scan.add('navmesh_old', '%s has changed since its navmesh was made.' % _place(gd, pr, ckey), {'cell': ckey},
                     {'action': 'navmesh', 'cell': ckey, 'label': 'Make it again'})
    for ckey, c in pr.cells.items():
        if ckey in pr.navmesh or ckey.startswith('+'):
            continue
        cell = gd.from_key(ckey)
        if cell in gd.ext_cells or not gd.navmeshes(cell):
            continue
        n = 0
        for rk, r in c['refs'].items():
            base = r.get('base')
            if rk.startswith('+') and base and not base.startswith('+') and gd.forms[gd.from_key(base)][1].tag in ('STAT', 'SCOL', 'FURN', 'CONT', 'DOOR', 'MSTT'):
                n += 1
            elif r.get('removed'):
                n += 1
        if n:
            st = navbuild.status(gd, pr, ckey)
            # (one at a time: it replaces the game's mesh, which isn't for a "fix everything")
            fix = {'action': 'navmesh', 'cell': ckey, 'label': 'Make a new navmesh', 'one': True} if st.get('can') else None
            scan.add('navmesh_game', '%s: %d thing%s added or removed.' % (_place(gd, pr, ckey), n, '' if n == 1 else 's'), {'cell': ckey}, fix)


def _place(gd, pr, ckey):
    if ckey.startswith('+'):
        rec = pr.records.get(ckey)
        return (recordio.field(rec, 'FULL') or recordio.field(rec, 'EDID')) if rec else ckey
    return gd.edid(gd.from_key(ckey)) or ckey


def _summary(groups):
    out = {ERROR: 0, WARN: 0, INFO: 0}
    for g in groups:
        out[g['sev']] += g['count']
    return out


def check_file(gd, path, data_dir=None):
    """Any plugin, read only: nothing here can change it."""
    scan = Scan(gd, path, None, data_dir).run()
    try:
        groups = scan.report()
        # (things in files FOLab hasn't loaded can't be gone to)
        for g in groups:
            for r in g['rows']:
                go = r.get('go')
                if go and not all(_can_go(gd, go[k]) for k in ('record', 'cell', 'world') if go.get(k)):
                    r.pop('go', None)
    finally:
        scan.close()
    return {'plugin': os.path.basename(path), 'mine': False, 'groups': groups, 'summary': _summary(groups), 'masters': scan.masters}


def _can_go(gd, key):
    try:
        return gd.from_key(key) in gd.forms
    except ValueError:
        return False


# ---------- fixes ----------

def _clear(rec, target):
    """A record with every schema-known link to target emptied; whether anything changed."""
    t = target.lower()
    changed = False
    for s in rec['subs']:
        if s['kind'] == 'F' and str(s['value']).lower() == t:
            s['value'] = ''
            changed = True
        elif s['kind'] == 'F*':
            keep = [v for v in s['value'] if str(v).lower() != t]
            if len(keep) != len(s['value']):
                s['value'], changed = keep, True
        elif s['kind'] == 'struct':
            for f in s['fields']:
                if f.get('code') == 'F' and str(f['value']).lower() == t:
                    f['value'] = ''
                    changed = True
    return changed


def script_record(gd, pr, key, rec):
    """A script's record with its text compiled. Raises scriptc.CompileError for text that doesn't compile."""
    text = None
    for s in rec['subs']:
        if s['tag'] == 'SCTX':
            text = bytes.fromhex(s['value']) if s['kind'] == 'raw' else (s['value'] or '').encode('cp1252', 'replace')
    if not text:
        raise ValueError('It has no text to compile.')
    made = scriptc.compile_script(text.rstrip(b'\0'), scriptc.GameForms(gd))
    keep = [s for s in rec['subs'] if s['tag'] not in ('SCHR', 'SCDA', 'SCTX', 'SLSD', 'SCVR', 'SCRO', 'SCRV')]
    for tag, data in made.subrecords():
        s = schema.decode_sub('SCPT', tag, data)
        if s['kind'] == 'F':
            s['value'] = gd.key(s['value'])
        keep.append(s)
    out = dict(rec, subs=keep)
    return out


def fix_ops(S, fixes):
    """(ops for one undo step, reasons for the fixes that couldn't be made)."""
    gd, pr = S.GD, S.PR
    ops, why, recs = [], [], {}

    def record(key):
        if key not in recs:
            recs[key] = recordio_copy(pr.records.get(key) or recordio.load(gd, gd.from_key(key)))
        return recs[key]
    for f in fixes:
        a = f.get('action')
        try:
            if a == 'revert_record':
                ops.append({'op': 'record_revert', 'key': f['key']})
            elif a == 'revert_ref':
                ops.append({'op': 'revert', 'cell': f['cell'], 'ref': f['ref']})
            elif a == 'remove_ref' or a == 'sink':
                ops.append({'op': 'remove', 'cell': f['cell'], 'ref': f['ref']})
            elif a == 'unlink':
                ops.append({'op': 'tel', 'cell': f['cell'], 'ref': f['ref'], 'tel': None})
            elif a == 'drop':
                ops.append({'op': 'drop', 'key': f['key']})
            elif a == 'clear_link':
                if not _clear(record(f['key']), f['target']):
                    why.append('%s: that link can\'t be cleared from here.' % f['key'])
            elif a == 'navmesh':
                data, _report = navbuild.generate(gd, pr, f['cell'])
                ops.append({'op': 'navmesh', 'cell': f['cell'], 'mesh': data})
            elif a == 'compile':
                recs[f['key']] = script_record(gd, pr, f['key'], record(f['key']))
            else:
                why.append('Unknown fix: %s' % a)
        except Exception as e:
            why.append('%s: %s' % (f.get('key') or f.get('cell') or f.get('ref') or a, e))
    for key, rec in recs.items():
        ops.append({'op': 'record', 'key': key, 'record': rec})
    return ops, why


def recordio_copy(rec):
    import copy
    return copy.deepcopy(rec)


def apply_fixes(S, fixes):
    ops, why = fix_ops(S, fixes)
    n = len(fixes) - len(why)
    out = S.edit('Health check: %d fix%s' % (n, '' if n == 1 else 'es'), ops) if ops else {'state': S.state()}
    out['failed'] = why
    out['fixed'] = n
    return out


def digest(path):
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()
