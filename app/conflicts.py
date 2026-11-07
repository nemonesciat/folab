"""Where a plugin clashes with the rest of the load order: for every record it touches, who else changes it, who wins,
and whether anything the plugin meant actually goes missing. Read-only; the one thing that writes is move(), at the
user's click, through loadorder.save (backup first).

How a clash is decided. The game takes the last copy of a record whole, it doesn't merge. So for a plugin M:
  - M's change is what differs between M and its base: the last copy among the files M was built on (its masters and
    theirs). Struct fields are told apart by schema.py's layouts where a layout fits; repeated subrecords (inventory
    lines, conditions...) count as a bag, so "added this, took that out" is the change; other subrecords are compared
    whole. Links are compared by the file that owns them (recdiff.spelled), never by the plugin's own numbering.
  - If a later plugin has the last copy, M's change survives only if that copy says the same in every field M changed.
    A copy byte for byte like M's, or differing only in fields M left alone, is harmless.
  - If M has the last copy, a plugin loaded earlier and not among M's masters loses whatever it changed that M's copy
    doesn't say. That's "you undo them": real, though usually what the player wanted of a later mod.
  - NAVI is never a clash: the game merges each file's NAVI into one.

Speed. Only the record headers are read at first, once per file: formid, type, offset, flags and parent group kept
sorted in cache/conflicts (name, size and date in the file name), so a later run reads a few hundred small files. Then
only copies of the records the plugin touches are read.

    check(data_dir, path)       the whole thing, synchronously
    start(S, file) / status()   the same on a thread, with progress, for the page
    compare(data_dir, path, key)    one record, side by side, every copy
    move(data_dir, plugin, after)   load one plugin after another: dates, with loadorder's backup"""
import array
import bisect
import collections
import json
import os
import struct
import threading
import time

import formlinks
import loadorder
import project
import recdiff
import schema
import tes4

FORMAT = 1
LIMIT = 300                 # (rows listed in one group; the counts are always the full ones)
DEEP_LIMIT = 250000         # (past this many records of its own, a plugin's links aren't followed: it takes too long)
SEAM = 4.0                  # (ground that differs by more than this, in units, shows as a crack: heights go in steps of 8)
NEAR = 1e-4                 # (floats closer than this are the same number written twice)
SUNK = -20000.0
DISABLED = 0x800
NAVI, NAVM, LAND, CELL, WRLD = 'NAVI', 'NAVM', 'LAND', 'CELL', 'WRLD'
PLACED = formlinks.PLACED_TAGS
PARENT_GROUPS = {tes4.G_WORLD_CHILDREN, tes4.G_CELL_CHILDREN, tes4.G_TOPIC_CHILDREN, tes4.G_CELL_PERSISTENT,
                 tes4.G_CELL_TEMPORARY, tes4.G_CELL_VWD}

# ---- how things are told apart and said ----

GROUPS = [('masters', 'Masters', 'The files your mod is built on.'),
          ('cell', 'Places and placed things', 'The things in the world and the settings of the places they stand in.'),
          ('navmesh', 'Navmeshes', 'The paths characters walk on.'),
          ('land', 'Ground', 'The shape, colours and paint of the land outside.'),
          ('items', 'Items', 'Weapons, armour, aid, ammo, containers and lists of them.'),
          ('npcs', 'Characters and creatures', 'Characters, creatures, their factions, packages and levelled lists.'),
          ('scripts', 'Scripts', 'The code things run.'),
          ('quests', 'Quests and dialogue', 'Quests, topics and spoken lines.'),
          ('other', 'Everything else', 'Settings, weather, sounds, and other records.')]
GROUP_TITLE = {k: t for k, t, _w in GROUPS}
_TAGS = {'cell': ('CELL', 'WRLD', 'REFR', 'ACHR', 'ACRE', 'PGRE', 'PMIS', 'PBEA', 'PFLA', 'PCBE', 'PGRD'),
         'navmesh': ('NAVM',), 'land': ('LAND',),
         'items': ('WEAP', 'ARMO', 'ARMA', 'AMMO', 'MISC', 'ALCH', 'KEYM', 'BOOK', 'NOTE', 'CMNY', 'IMOD', 'LVLI', 'FLST', 'CONT', 'RCPE', 'RCCT',
                   'COBJ', 'CHIP', 'CCRD', 'CDCK', 'INGR'),
         'npcs': ('NPC_', 'CREA', 'LVLN', 'LVLC', 'RACE', 'FACT', 'PACK', 'CLAS', 'CSTY', 'HAIR', 'EYES', 'HDPT', 'BPTD', 'VTYP', 'AVIF', 'REPU', 'SPEL', 'EFSH', 'MGEF', 'PERK'),
         'scripts': ('SCPT',), 'quests': ('QUST', 'DIAL', 'INFO', 'MESG')}
GROUP_OF = {t: k for k, tags in _TAGS.items() for t in tags}

ISSUES = {
    # (the order is the rank: what stops the game first, what's worth a look last)
    'master': ('error', 'Masters missing or out of order', 'A plugin\'s masters are the files it\'s built on. Without them, or with them loading after it, the game won\'t start or will crash on the way in.'),
    'deleted': ('error', 'Records someone deleted', 'A deleted record that anything still uses can crash the game, and a record one mod deletes and another changes means neither gets what it expected.'),
    'overwritten': ('error', 'Your change is overwritten', 'A plugin loading later says something else about what you changed. The game uses theirs whole, so your change never happens.'),
    'navmesh': ('error', 'Navmesh in the same place', 'Only one mesh can win in a place, and meshes join their neighbours by number, so two mods\' meshes in one place leave characters stuck, or crash the game when it looks for a mesh that isn\'t there.'),
    'door': ('error', 'Door links', 'A door and the door at its other end must point at each other. If another mod changes either end, the player arrives in the wrong place, or the door doesn\'t work.'),
    'land_seam': ('warn', 'Ground that doesn\'t meet', 'Two neighbouring squares of ground come from different plugins and their edges don\'t agree, so the player sees a crack or a cliff along the edge.'),
    'land': ('warn', 'Ground changed by both', 'Both mods change the ground in the same square. Only the winner\'s shape and paint are used.'),
    'topic': ('warn', 'Topics more than one mod adds to', "A topic lists the quests with lines in it, and the last copy's list is the one used. The game's own add-ons do this to each other, so it isn't fatal, but some lines of the mod that loses may never be spoken."),
    'cell_header': ('warn', 'Place settings overwritten', 'A place\'s record holds its lighting, water, music and name. Every mod that changes anything in a place carries a copy, so the last one\'s settings win, whether it meant them or not.'),
    'you_overwrite': ('warn', 'You undo someone else\'s change', 'You load after them, so your copy wins, and theirs is lost. Often that\'s what you want; sometimes it just comes from carrying a copy of the record.'),
    'patched': ('info', 'Plugins built on yours', 'These load after your mod and need it, so changing your records is what they\'re for: a patch, most likely.'),
}
RANK = {k: n for n, k in enumerate(ISSUES)}
NOTICE = {
    'cell': 'In game it stands, looks or behaves as their mod has it.',
    'items': 'In game the item has their numbers and looks, not yours.',
    'npcs': 'In game the character or creature has their stats, look or inventory, not yours.',
    'scripts': 'The game runs their script. Whatever relies on yours won\'t work.',
    'quests': 'Your quest stages or lines may not exist in game, which can leave a quest stuck.',
    'other': 'In game their setting is the one used.',
}
LABELS = {'DATA': 'where it stands', 'NAME': 'what it is', 'XTEL': 'door link', 'XSCL': 'size', 'XLOC': 'lock', 'XOWN': 'owner', 'XESP': 'enable parent', 'XEZN': 'encounter zone',
          'XLKR': 'linked thing', 'XRDO': 'radio', 'XCNT': 'count', 'XTRG': 'target', 'XMBR': 'multibound', 'XLCM': 'level', 'XRNK': 'owner\'s rank',
          'XHLP': 'health', 'XCHG': 'charge', 'XPRD': 'patrol', 'XRGD': 'ragdoll', 'XRDS': 'radius', 'XMRK': 'map marker', 'FNAM': 'map marker flags', 'FULL': 'name'}
LAND_LABELS = {'VHGT': 'ground shape', 'VNML': 'ground shading', 'VCLR': 'ground colours', 'BTXT': 'ground textures', 'ATXT': 'ground textures', 'VTXT': 'ground textures', 'VTEX': 'ground textures'}
FLAGS = {0x200: 'hidden from the local map', 0x400: 'persistent', 0x800: 'starts disabled', 0x8000: 'visible when distant'}
IGNORE = {WRLD: {'OFST'}, NAVM: set()}      # (WRLD's OFST: a table of offsets into its own file, meaningless to compare)
BLOBS = {'MODT', 'MO2T', 'MO3T', 'MO4T', 'NIFT', 'DMDT', 'FGGS', 'FGGA', 'FGTS'}


def cache_dir():
    return os.path.join(project.HOME, 'cache', 'conflicts', 'v%d' % FORMAT)


# ---------- each file's headers, kept ----------

class Index:
    """One file's records, sorted by form ID as the file numbers them. Rows are positions in these arrays."""
    __slots__ = ('path', 'name', 'low', 'masters', 'own', 'fid', 'tag', 'off', 'flg', 'par', 'ext', 'esm', 'owners', 'squares')

    def __init__(self, path, name, masters, esm, fid, tag, off, flg, par, ext):
        self.path, self.name, self.low, self.masters = path, name, name.lower(), masters
        self.own, self.esm = len(masters), esm
        self.fid, self.tag, self.off, self.flg, self.par, self.ext = fid, tag, off, flg, par, ext
        self.owners = masters + [self.low]
        self.squares = None

    def row(self, v):
        at = bisect.bisect_left(self.fid, v)
        return at if at < len(self.fid) and self.fid[at] == v else None

    def form(self, v):
        """(owner, object ID) of a form ID in this file's numbering."""
        return (self.owners[min(v >> 24, self.own)], v & 0xFFFFFF)

    def local(self, owner, low):
        """This file's number for a form; None when it can't name it (the owner isn't among its masters)."""
        try:
            return (self.owners.index(owner) << 24) | low
        except ValueError:
            return None

    def tag_at(self, at):
        return _untag(self.tag[at])

    def of_tag(self, tag):
        code = _tag(tag)
        return [i for i, t in enumerate(self.tag) if t == code]

    def __len__(self):
        return len(self.fid)


def _tag(s):
    return struct.unpack('<I', s.encode('ascii'))[0]


def _untag(n):
    return struct.pack('<I', n).decode('ascii', 'replace')


def _scan(path):
    """Read one plugin's record headers straight through; only an outside cell's own record is opened, for its square."""
    pf = tes4.PluginFile(path)
    try:
        masters = [m.lower() for m in pf.header['masters']]
        own = len(masters)
        mm, unpack = pf.mm, struct.unpack_from
        fid, tag, off, flg, par, ext = [], [], [], [], [], []
        pos, end = pf.first, len(mm)
        stack = [(end, 0, False)]       # (where it stops, the parent form its records have, is it in a world's children)
        cell_code = _tag(CELL)
        while stack:
            stop, parent, world = stack[-1]
            if pos + 24 > stop:
                stack.pop()
                pos = max(pos, stop)
                continue
            head = unpack('<4I', mm, pos)
            if head[0] == 0x50555247:       # 'GRUP'
                gsize, label = head[1], head[2]
                gtype = unpack('<i', mm, pos + 12)[0]
                if gsize < 24:
                    raise ValueError('bad group size at %d' % pos)
                if gtype in PARENT_GROUPS:
                    stack.append((pos + gsize, label, world or gtype == tes4.G_WORLD_CHILDREN))
                elif gtype == tes4.G_TOP or gtype == tes4.G_INT_BLOCK or gtype == tes4.G_INT_SUBBLOCK:
                    stack.append((pos + gsize, 0, False))
                else:
                    stack.append((pos + gsize, parent, world))
                pos += 24
                continue
            size, flags, v = head[1], head[2], head[3]
            if v >> 24 > own:               # (past its masters: it's the file's own, as the game takes it)
                v = (own << 24) | (v & 0xFFFFFF)
            fid.append(v)
            tag.append(head[0])
            off.append(pos)
            flg.append(flags)
            par.append(parent)
            if head[0] == cell_code and world:
                xy = _cell_square(pf, pos, size, flags)
                if xy:
                    ext += [v, xy[0], xy[1]]
            pos += 24 + size
        order = sorted(range(len(fid)), key=fid.__getitem__)
        col = lambda c: array.array('I', [c[i] for i in order])
        esm = bool(pf.header['flags'] & 1) or path.lower().endswith('.esm')
        return Index(path, os.path.basename(path), masters, esm, col(fid), col(tag), col(off), col(flg), col(par), array.array('I', [x & 0xFFFFFFFF for x in ext]))
    finally:
        pf.close()


def _cell_square(pf, pos, size, flags):
    try:
        d = pf.data(tes4.Record(CELL, pos, flags, 0, size))
    except Exception:
        return None
    for t, s in tes4.iter_subrecords(d):
        if t == 'XCLC' and len(s) >= 8:
            return struct.unpack_from('<2i', s)
    return None


_mem = {}


def _stamp(path):
    st = os.stat(path)
    return st.st_size, st.st_mtime_ns


def load_index(path, keep=True):
    """A file's Index: from memory, from the cache, or read. keep=False for scratch files: nothing goes on disk."""
    size, when = _stamp(path)
    name = os.path.basename(path)
    k = path.lower()
    got = _mem.get(k)
    if got and got[0] == (size, when):
        return got[1]
    file = os.path.join(cache_dir(), '%s.%d.%d.idx' % (name, size, when))
    ix = _read_cache(file, path, name) if keep else None
    if ix is None:
        ix = _scan(path)
        if keep:
            _write_cache(file, ix)
    if keep:
        _mem[k] = ((size, when), ix)
    return ix


def _read_cache(file, path, name):
    try:
        with open(file, 'rb') as f:
            head = json.loads(f.readline())
            cols = []
            for n in (head['n'],) * 5 + (head['ext'],):
                a = array.array('I')
                a.frombytes(f.read(n * 4))
                if len(a) != n:
                    return None
                cols.append(a)
    except (OSError, ValueError, KeyError):
        return None
    return Index(path, name, head['masters'], head['esm'], *cols)


def _write_cache(file, ix):
    d = os.path.dirname(file)
    tmp = '%s.%d.tmp' % (file, threading.get_ident())
    try:
        os.makedirs(d, exist_ok=True)
        low = ix.name.lower() + '.'
        for old in os.listdir(d):       # (the same file at another size or date)
            rest = old[len(low):] if old.lower().startswith(low) else ''
            if rest.endswith('.idx') and rest[:-4].replace('.', '').isdigit():
                os.remove(os.path.join(d, old))
        with open(tmp, 'wb') as f:
            f.write(json.dumps({'masters': ix.masters, 'esm': ix.esm, 'n': len(ix.fid), 'ext': len(ix.ext)}).encode('utf-8') + b'\n')
            for a in (ix.fid, ix.tag, ix.off, ix.flg, ix.par, ix.ext):
                f.write(a.tobytes())
        os.replace(tmp, file)
    except OSError:
        pass                            # (no cache: slower next time, nothing worse)


# ---------- the load order, with the plugin being checked in its place ----------

def order_rows(data_dir, path):
    """The load order's rows (loadorder.py) with the plugin at path among them: in its place if Data has one of its name,
    last among its kind if not, as installing it would put it. Switched on, whatever the list says."""
    name = os.path.basename(path)
    got = loadorder.read(data_dir, name)
    rows = got['rows']
    me = next((r for r in rows if r['name'].lower() == name.lower()), None)
    installed = bool(me and me['found'])
    was_on = bool(me and me['active'])
    pf = tes4.PluginFile(path)
    try:
        head = dict(pf.header)
    finally:
        pf.close()
    if me is None:
        me = {'name': name, 'official': False, 'found': True, 'author': '', 'description': '', 'records': head['records'], 'mine': True, 'helper': False, 'size': os.path.getsize(path)}
        rows.append(me)
    if not installed:
        me['mtime'] = float('inf')
    me.update(found=True, active=True, esm=bool(head['flags'] & 1) or name.lower().endswith('.esm'), masters=head['masters'])
    me.pop('error', None)
    rows = loadorder.problems(loadorder.in_game_order(rows))
    return rows, me, installed, was_on


class Order:
    """The files that count, in load order, as Indexes; the first files read may take a while."""

    def __init__(self, data_dir, path, progress=None):
        self.data_dir, self.path = data_dir, path
        self.rows, self.row, self.installed, self.was_on = order_rows(data_dir, path)
        self.files, self.notes = [], []
        self.real = {}
        scratch = os.path.normcase(os.path.dirname(os.path.abspath(path))) != os.path.normcase(os.path.abspath(data_dir))
        todo = [r for r in self.rows if r['active'] and r['found'] and not (r.get('helper') and r is not self.row) and not (r.get('error') and r is not self.row)]
        self.me = None
        for n, r in enumerate(todo):
            mine = r is self.row
            p = path if mine else os.path.join(data_dir, r['name'])
            if progress:
                progress('reading', n, len(todo), r['name'])
            try:
                ix = load_index(p, keep=not (mine and scratch))
            except (OSError, ValueError, struct.error) as e:
                self.notes.append('%s couldn\'t be read, so it isn\'t counted: %s' % (r['name'], e))
                continue
            if mine:
                self.me = len(self.files)
            self.files.append(ix)
            self.real[ix.low] = ix.name
            for m, low in zip(r.get('masters') or [], ix.masters):
                self.real.setdefault(low, m)
        lost = [r['name'] for r in self.rows if r['active'] and not r['found']]
        if lost:
            one = len(lost) == 1
            self.notes.append("%d plugin%s on the game's list %s no file in Data, so %s checked. A mod manager may keep them elsewhere: start FOLab through it to see them. (%s%s)" % (
                len(lost), '' if one else 's', 'has' if one else 'have', "it wasn't" if one else "they weren't", ', '.join(lost[:6]), '…' if len(lost) > 6 else ''))
        self.at = {ix.low: i for i, ix in enumerate(self.files)}
        self.closures = {}
        self.pfs = {}

    def real_name(self, low):
        return self.real.get(low, low)

    def closure(self, low):
        """Every file a file is built on: its masters, theirs..."""
        got = self.closures.get(low)
        if got is None:
            got = set()
            self.closures[low] = got
            i = self.at.get(low)
            if i is not None:
                for m in self.files[i].masters:
                    got.add(m)
                    got |= self.closure(m)
        return got

    def pf(self, i):
        p = self.pfs.get(i)
        if p is None:
            p = self.pfs[i] = tes4.PluginFile(self.files[i].path)
        return p

    def close(self):
        for p in self.pfs.values():
            p.close()
        self.pfs = {}

    def find(self, want):
        """{(owner, object ID): [(file's place in the load order, row)]} for want: {owner: set of object IDs}."""
        out = collections.defaultdict(list)
        for i, ix in enumerate(self.files):
            where = [(n, want[o], o) for n, o in enumerate(ix.owners) if o in want]
            total = sum(len(w[1]) for w in where)
            if not total:
                continue
            fid = ix.fid
            if total * 12 < len(fid):
                for n, lows, o in where:
                    hi = n << 24
                    for low in lows:
                        v = hi | low
                        at = bisect.bisect_left(fid, v)
                        if at < len(fid) and fid[at] == v:
                            out[(o, low)].append((i, at))
            else:
                index = {n: (lows, o) for n, lows, o in where}
                for at, v in enumerate(fid):
                    w = index.get(v >> 24)
                    if w is not None and v & 0xFFFFFF in w[0]:
                        out[(w[1], v & 0xFFFFFF)].append((i, at))
        return out

    def key(self, form):
        return '%s:%06X' % (self.real_name(form[0]), form[1])


class Copy:
    """One copy of a record, read, its links spelled the same whichever plugin wrote it."""
    __slots__ = ('i', 'at', 'tag', 'flags', 'deleted', 'subs', 'by', 'name')

    def __init__(self, order, i, at):
        ix = order.files[i]
        pf = order.pf(i)
        self.i, self.at, self.name = i, at, ix.name
        rec = pf.record_at(ix.off[at])
        self.tag = rec.tag
        self.flags = rec.flags & ~tes4.COMPRESSED
        self.deleted = bool(rec.flags & tes4.DELETED)
        try:
            raw = list(tes4.iter_subrecords(pf.data(rec)))
        except Exception:               # (a deleted record often has nothing in it at all)
            raw = []
        try:
            subs = recdiff.spelled(pf, rec.tag, raw)
        except Exception:
            subs = raw
        drop = IGNORE.get(rec.tag)
        self.subs = [x for x in subs if x[0] not in drop] if drop else subs
        by = {}
        for t, d in self.subs:
            by.setdefault(t, []).append(d)
        if rec.tag in PLACED or rec.tag == NAVM:
            p = ix.par[at]
            if p:
                o, low = ix.form(p)
                by['@cell'] = [('%s:%d' % (o, low)).encode('ascii', 'replace')]
        self.by = by

    def same(self, other):
        return self.flags == other.flags and self.subs == other.subs and self.by.get('@cell') == other.by.get('@cell')

    def field(self, st):
        v = self.by.get(st)
        return v[0] if v else None


# ---------- what a change is, and whether it survives ----------

def label_of(tag, st):
    if st == '@cell':
        return 'which place it\'s in'
    if tag == LAND and st in LAND_LABELS:
        return LAND_LABELS[st]
    if tag in PLACED and st in LABELS:
        return LABELS[st]
    try:
        d = schema.layout(tag, st)
    except Exception:
        d = None
    return d[0] if d else LABELS.get(st, st)


def _same_float(a, b):
    """Equal, as far as anyone could tell: tools round floats differently, which is no clash."""
    if a == b or (a != a and b != b):
        return True
    return isinstance(a, float) and isinstance(b, float) and abs(a - b) < NEAR


def _near_floats(a, b):
    return a == b or all(_same_float(x, y) for x, y in zip(struct.unpack('<3f', a), struct.unpack('<3f', b)))


def _struct_lost(tag, st, b, m, f):
    """The named fields of one subrecord that changed from b to m and aren't m in f. None if no layout tells them apart."""
    if tag in PLACED and st == 'DATA' and m is not None and f is not None and len(m) == 24 and len(f) == 24:
        out = []
        if (b is None or not _near_floats(m[:12], b[:12])) and not _near_floats(m[:12], f[:12]):
            out.append('where it stands')
        if (b is None or not _near_floats(m[12:], b[12:])) and not _near_floats(m[12:], f[12:]):
            out.append('how it\'s turned')
        return out
    if m is None or f is None:
        return None
    try:
        sm, sf = schema.decode_sub(tag, st, m), schema.decode_sub(tag, st, f)
        sb = schema.decode_sub(tag, st, b) if b is not None else None
    except Exception:
        return None
    if sm['kind'] != 'struct' or sf['kind'] != 'struct' or len(sm['fields']) != len(sf['fields']):
        return None
    if sb is not None and (sb['kind'] != 'struct' or len(sb['fields']) != len(sm['fields'])):
        return None
    out = []
    for n, x in enumerate(sm['fields']):
        if 'name' not in x:
            continue
        if sb is not None and _same_float(sb['fields'][n]['value'], x['value']):
            continue
        if not _same_float(x['value'], sf['fields'][n]['value']):
            out.append('%s: %s' % (sm['label'], x['name']))
    return out


def lost_fields(tag, base, mine, final):
    """What mine changed from base that final doesn't say: a list of field names, empty when mine's change survives
    whole. base None: mine is where the record starts, so everything in it counts."""
    out = []
    bf = base.flags if base else 0
    for bit, word in FLAGS.items():
        if (bf ^ mine.flags) & bit and (mine.flags ^ final.flags) & bit:
            out.append(word)
    bby = base.by if base else {}
    for st in set(bby) | set(mine.by):
        b, m, f = bby.get(st, []), mine.by.get(st, []), final.by.get(st, [])
        if b == m or m == f:
            continue
        if len(b) <= 1 and len(m) <= 1 and len(f) <= 1:
            got = _struct_lost(tag, st, b[0] if b else None, m[0] if m else None, f[0] if f else None)
            if got is None:
                out.append(label_of(tag, st))
            else:
                out += got
            continue
        cb, cm, cf = collections.Counter(b), collections.Counter(m), collections.Counter(f)
        added = cm - cb
        gone = cb - cm
        if any(cf[v] < cm[v] for v in added) or any(cf[v] > cm[v] for v in gone):
            out.append(label_of(tag, st))
    seen, uniq = set(), []
    for w in out:
        if w not in seen:
            seen.add(w)
            uniq.append(w)
    return uniq


def changes_nothing(base, mine):
    return base is not None and base.same(mine)


def _nice(fields):
    """Field names for a sentence: the hash blobs only if there's nothing else."""
    show = [f for f in fields if f not in BLOBS]
    return show or fields


# ---------- the check ----------

class Check:
    def __init__(self, order, progress=None):
        self.o = order
        self.progress = progress or (lambda *a: None)
        self.me = order.files[order.me]
        self.mine = self.me.low
        self.built_on = order.closure(self.mine)
        self.rows = []
        self.counts = collections.Counter()
        self.group_counts = collections.Counter()
        self.harmless = collections.Counter()
        self.harmless_rows = []
        self.by_mod = collections.defaultdict(collections.Counter)
        self.touched = 0
        self.contested = 0
        self.edids = {}

    # ---- rows ----

    def add(self, issue, group, text, notice='', advice='', **more):
        self.counts[issue] += 1
        self.group_counts[group] += 1
        row = dict(issue=issue, group=group, sev=ISSUES[issue][0], rank=RANK[issue], text=text, notice=notice, advice=advice)
        row.update(more)
        self.rows.append(row)
        return row

    def built_on_me(self, low):
        return self.mine in self.o.closure(low)

    def can_move_after(self, low):
        """Can the plugin being checked be loaded after this one? (plan, or why not)"""
        o = self.o
        if not o.installed:
            return None, 'Your mod isn\'t in Data yet: wherever it goes when it\'s installed decides this.'
        i = o.at[low]
        them = o.files[i]
        if self.me.esm and not them.esm:
            return None, '%s is a master, so it always loads before plugins like %s. Only a patch can settle this one.' % (self.me.name, them.name)
        for j in range(o.me + 1, i + 1):
            f = o.files[j]
            if self.mine in f.masters:
                if f.low == low:
                    return None, '%s is built on %s, so it has to load after it.' % (them.name, self.me.name)
                return None, '%s needs %s and loads before %s, so moving past it would break it.' % (f.name, self.me.name, them.name)
        return {'plugin': self.me.name, 'after': them.name}, ''

    def advice_for(self, low):
        """(what to do, a move to offer) when a later plugin beats the one being checked."""
        move, why = self.can_move_after(low)
        name = self.o.files[self.o.at[low]].name
        if move:
            return 'Load %s after %s if yours matters more here (that gives their change up), or make a patch that has both.' % (self.me.name, name), move
        return (why + ' A small patch plugin loaded last can carry both changes.') if why else 'A small patch plugin loaded last can carry both changes.', None

    # ---- names ----

    def edid_of(self, form):
        """An editor ID or name for a form, from the last file that has it."""
        if form in self.edids:
            return self.edids[form]
        o = self.o
        word = ''
        for i in range(len(o.files) - 1, -1, -1):
            ix = o.files[i]
            v = ix.local(*form)
            at = ix.row(v) if v is not None else None
            if at is None:
                continue
            word = self._edid_at(i, at)
            if word:
                break
        self.edids[form] = word
        return word

    def _edid_at(self, i, at):
        o = self.o
        pf = o.pf(i)
        try:
            f = tes4.subrecord_dict(pf.data(pf.record_at(o.files[i].off[at])))
        except Exception:
            return ''
        return tes4.zstr(f.get('EDID', b'')) or tes4.zstr(f.get('FULL', b''))

    def place_of(self, cell):
        word = self.edid_of(cell)
        if word:
            return word
        return self._grid_word(cell) or self.o.key(cell)

    def _grid_word(self, cell):
        for ix in self.o.files:
            xy = self._square(ix, cell)
            if xy:
                return 'outside, square %d, %d' % xy
        return ''

    def _square(self, ix, cell):
        v = ix.local(*cell)
        return _ext_map(ix).get(v) if v is not None else None

    def what(self, form, copy):
        """What a record is, in words."""
        word = tes4.zstr(copy.by['EDID'][0]) if copy.by.get('EDID') else ''
        word = word or (tes4.zstr(copy.by['FULL'][0]) if copy.by.get('FULL') else '')
        tag = copy.tag
        if tag in PLACED:
            ix = self.o.files[copy.i]
            base = ''
            raw = self.o.pf(copy.i)
            try:
                f = tes4.subrecord_dict(raw.data(raw.record_at(ix.off[copy.at])))
                if len(f.get('NAME', b'')) == 4:
                    base = self.edid_of(ix.form(struct.unpack('<I', f['NAME'])[0]))
            except Exception:
                pass
            p = ix.par[copy.at]
            where = (' in %s' % self.place_of(ix.form(p))) if p else ''
            return '%s%s' % (word or base or 'A placed thing (%s)' % self.o.key(form), where)
        return '%s (%s)' % (word or self.o.key(form), type_word(tag))

    def go_of(self, form, copy):
        tag = copy.tag
        key = self.o.key(form)
        ix = self.o.files[copy.i]
        if tag in PLACED:
            p = ix.par[copy.at]
            if not p:
                return None
            cell = ix.form(p)
            out = {'cell': self.o.key(cell), 'ref': key}
            at = ix.row(p)
            if at is not None and ix.par[at]:      # (outside: it's a square of a world)
                out = {'world': self.o.key(ix.form(ix.par[at])), 'ref': key}
                d = copy.by.get('DATA')
                if d and len(d[0]) >= 12:
                    out['p'] = list(struct.unpack_from('<3f', d[0]))
            return out
        if tag == CELL:
            if ix.par[copy.at]:
                xy = self._square(ix, form)
                out = {'world': self.o.key(ix.form(ix.par[copy.at]))}
                if xy:
                    out['p'] = [xy[0] * 4096 + 2048, xy[1] * 4096 + 2048, 0]
                return out
            return {'cell': key}
        if tag in (NAVM, LAND, WRLD, NAVI):
            return None
        return {'record': key}

    # ---- the main pass ----

    def run(self):
        o, me = self.o, self.me
        self.check_masters()
        want = collections.defaultdict(set)
        tags = me.tag
        navi, navm, land = _tag(NAVI), _tag(NAVM), _tag(LAND)
        special = {NAVM: [], LAND: []}
        total = 0
        for at, v in enumerate(me.fid):
            t = tags[at]
            if t == navi:
                continue
            total += 1
            if t == navm:
                special[NAVM].append(at)
            elif t == land:
                special[LAND].append(at)
            else:
                f = me.form(v)
                want[f[0]].add(f[1])
        self.touched = total
        self.progress('finding', 0, 1, '')
        hits = o.find(want)
        forms = [k for k, c in hits.items() if len(c) > 1]
        self.progress('comparing', 0, len(forms), '')
        for n, form in enumerate(forms):
            if n % 200 == 0:
                self.progress('comparing', n, len(forms), '')
            try:
                self.judge(form, hits[form])
            except (struct.error, ValueError, KeyError, IndexError) as e:
                o.notes.append('%s couldn\'t be compared: %s' % (o.key(form), e))
        self.progress('comparing', len(forms), len(forms), 'navmeshes')
        self.check_navmeshes(special[NAVM])
        self.progress('comparing', len(forms), len(forms), 'ground')
        self.check_land(special[LAND])
        if len(me) <= DEEP_LIMIT:
            self.progress('comparing', len(forms), len(forms), 'links and doors')
            self.check_links(hits)
        else:
            o.notes.append('%s has %d records of its own, so its links weren\'t followed to see if anything deleted what they point at.' % (me.name, len(me)))
        return self

    def check_masters(self):
        o = self.o
        for m in o.row['problems']:
            self.add('master', 'masters', m, 'The game won\'t start, or will crash loading.',
                     'Install what it needs and press Fix masters on the Load order page.', tool='loadorder')
        name = o.row['name']
        for r in o.rows:
            if r is o.row or not r['active'] or not r['found']:
                continue
            for m in r.get('problems') or []:
                if name.lower() in m.lower():
                    self.add('master', 'masters', '%s: %s' % (r['name'], m), 'The game can crash loading.', 'Press Fix masters on the Load order page.', tool='loadorder')

    def judge(self, form, copies):
        """One record the plugin has that someone else does too."""
        o = self.o
        my_at = next(k for k, c in enumerate(copies) if c[0] == o.me)
        others = [c for k, c in enumerate(copies) if k != my_at]
        out = [c for c in others if o.files[c[0]].low not in self.built_on]
        last = copies[-1]
        if not out and last[0] == o.me:
            return                                  # (only files it's built on, under it: nobody else in this)
        self.contested += 1
        read = {}

        def get(c):
            got = read.get(c[0])
            if got is None:
                got = read[c[0]] = Copy(o, c[0], c[1])
            return got
        mine = get(copies[my_at])
        tag = mine.tag

        def base_of(low, before):
            """The copy a file was built on: the last among its masters, loaded before it."""
            built = o.closure(low)
            for c in reversed(copies[:before]):
                if o.files[c[0]].low in built:
                    return get(c)
            return None
        base = base_of(self.mine, my_at)
        group = GROUP_OF.get(tag, 'other')
        chain = [o.files[c[0]].name for c in copies]
        final = get(last)
        common = dict(key=o.key(form), type=tag, chain=chain, wins=final.name)
        # ---- someone deleted it ----
        if final.deleted and not mine.deleted:
            who = final.name
            self.by_mod[who]['beats'] += 1
            adv, mv = self.advice_for(o.files[last[0]].low)
            self.add('deleted', group, '%s deletes %s, which your mod changes.' % (who, self.what(form, mine)),
                     'It\'s gone in game, along with your change. Anything using it may crash the game.', adv, move=mv, go=self.go_of(form, mine), **common)
            return
        if mine.deleted and any(not get(c).deleted for c in others if o.files[c[0]].low not in self.built_on):
            names = ', '.join(o.files[c[0]].name for c in out if not get(c).deleted)
            self.add('deleted', group, 'Your mod deletes %s, which %s also changes.' % (self.what(form, mine), names),
                     'If yours wins, their change is gone and anything using it may crash the game. If theirs wins, the deletion does nothing.',
                     'Disable it and sink it out of sight instead of deleting it: the Health check does this.', go=self.go_of(form, mine), **common)
            return
        if not mine.deleted and last[0] == o.me:
            dead = [get(c).name for c in others if get(c).deleted]
            if dead:
                self.add('deleted', group, 'Your mod brings back %s, which %s deleted.' % (self.what(form, mine), ', '.join(dead)),
                         'It\'s in the game again, as you have it. Whatever %s changed around it may not expect that.' % dead[-1],
                         'Check what that mod meant by taking it out, and whether you need this record at all.', go=self.go_of(form, mine), **common)
                return
        # ---- a later plugin has the last word ----
        if last[0] != o.me:
            who = final.name
            low = o.files[last[0]].low
            lost = [] if changes_nothing(base, mine) else lost_fields(tag, base, mine, final)
            if not lost:
                why = 'same' if mine.same(final) else 'no_change' if changes_nothing(base, mine) else 'other_fields'
                self.harmless[why] += 1
                self.by_mod[who]['harmless'] += 1
                if len(self.harmless_rows) < 40:
                    self.harmless_rows.append({'why': why, 'what': self.what(form, mine), 'who': who, **common})
                return
            names = ', '.join(_nice(lost))
            what = self.what(form, mine)
            if self.built_on_me(low):
                self.by_mod[who]['patched'] += 1
                self.add('patched', group, '%s changes what you set on %s (%s).' % (who, what, names), 'They load after yours and need it, so theirs is what\'s used.',
                         'Nothing, unless the patch is out of date for this version of your mod.', fields=lost, go=self.go_of(form, mine), **common)
                return
            self.by_mod[who]['beats'] += 1
            adv, mv = self.advice_for(low)
            if tag in PLACED and 'door link' in lost:
                self.add('door', group, '%s changes where %s leads: your door link is lost.' % (who, what), 'The player arrives where their mod says, or the door doesn\'t work.',
                         adv, move=mv, fields=lost, go=self.go_of(form, mine), **common)
            elif tag == 'DIAL':
                self.add('topic', group, '%s has its own list for %s, without what you added: %s.' % (who, what, names), 'Some of your lines in this topic may never be spoken.',
                         adv, move=mv, fields=lost, go=self.go_of(form, mine), **common)
            elif tag == CELL or tag == WRLD:
                self.add('cell_header', group, '%s overwrites your settings for %s: %s.' % (who, what, names),
                         'The place has their lighting, water, music or name, not yours.', adv, move=mv, fields=lost, go=self.go_of(form, mine), **common)
            else:
                self.add('overwritten', group, 'Your change to %s doesn\'t reach the game: %s loads later and says otherwise about %s.' % (what, who, names),
                         NOTICE.get(group, NOTICE['other']), adv, move=mv, fields=lost, go=self.go_of(form, mine), **common)
            return
        # ---- this plugin has the last word: who loses by it? ----
        undone = []
        clean = 0
        for k, c in enumerate(copies[:-1]):
            low = o.files[c[0]].low
            if low in self.built_on:
                continue
            them = get(c)
            b = base_of(low, k)
            lost = [] if changes_nothing(b, them) else lost_fields(tag, b, them, mine)
            if lost:
                undone.append((them.name, lost))
                self.by_mod[them.name]['beaten'] += 1
            else:
                clean += 1
                self.by_mod[them.name]['harmless'] += 1
        if not undone:
            self.harmless['keeps_theirs'] += 1
            if len(self.harmless_rows) < 40:
                self.harmless_rows.append({'why': 'keeps_theirs', 'what': self.what(form, mine), 'who': ', '.join(chain[:-1]), **common})
            return
        says = '; '.join('%s\'s %s' % (n, ', '.join(_nice(f))) for n, f in undone)
        names = [n for n, _f in undone]
        fields = sorted({x for _n, f in undone for x in f})
        nothing = changes_nothing(base, mine)
        what = self.what(form, mine)
        pre = 'Your mod carries a copy of %s that changes nothing, and it undoes %s.' % (what, says) if nothing else 'Your copy of %s wins, and undoes %s.' % (what, says)
        if nothing and tag not in (CELL, WRLD, 'DIAL'):
            adv = 'Take the copy out: your mod doesn\'t need it.'
        elif tag == CELL or tag == WRLD:
            adv = 'Your mod has to carry the place to change what\'s in it. To keep their settings, load it before %s, or copy their settings into your place.' % names[-1]
        else:
            adv = 'Load %s before yours if theirs should win, or copy what they changed into yours.' % names[-1]
        issue = 'cell_header' if tag in (CELL, WRLD) else 'topic' if tag == 'DIAL' else 'you_overwrite'
        notice = {'cell_header': "The place keeps your copy's lighting, water and music, not theirs.", 'topic': 'Some of their lines in this topic may never be spoken.'}.get(issue, "Their change doesn't happen in game.")
        self.add(issue, group, pre, notice, adv, fields=fields, losers=names, itm=nothing and tag not in (CELL, WRLD, 'DIAL'), go=self.go_of(form, mine), **common)

    # ---- navmeshes ----

    def check_navmeshes(self, rows):
        o, me = self.o, self.me
        if not rows:
            return
        here = collections.defaultdict(list)
        for at in rows:
            here[me.form(me.par[at])].append(at)
        for i, ix in enumerate(o.files):
            if i == o.me or ix.low in self.built_on:
                continue
            for at in ix.of_tag(NAVM):
                cell = ix.form(ix.par[at])
                if cell not in here:
                    continue
                self.nav_clash(cell, here[cell], i, at)

    def nav_clash(self, cell, mine_rows, i, at):
        o, me = self.o, self.me
        ix = o.files[i]
        them = Copy(o, i, at)
        form = ix.form(ix.fid[at])
        same_form = next((a for a in mine_rows if me.form(me.fid[a]) == form), None)
        mine = Copy(o, o.me, same_form if same_form is not None else mine_rows[0])
        self.contested += 1
        if same_form is not None and mine.same(them):
            self.harmless['same'] += 1
            self.by_mod[ix.name]['harmless'] += 1
            return
        place = self.place_of(cell)
        later = i > o.me
        key = o.key(form)
        common = dict(key=key, type=NAVM, chain=[me.name, ix.name] if later else [ix.name, me.name], wins=ix.name if later else me.name, go={'cell': o.key(cell)})
        if self.built_on_me(ix.low):
            self.by_mod[ix.name]['patched'] += 1
            self.add('patched', 'navmesh', '%s has its own navmesh in %s, and needs your mod.' % (ix.name, place), 'Theirs is used.', 'Nothing, unless it\'s out of date for your mod.', **common)
            return
        self.by_mod[ix.name]['beats' if later else 'beaten'] += 1
        if same_form is not None:
            text = '%s and your mod both change the same navmesh in %s; %s\'s is used.' % (ix.name, place, ix.name if later else me.name)
        else:
            text = '%s and your mod each put a navmesh of their own in %s.' % (ix.name, place)
        adv, mv = self.advice_for(ix.low) if later else ('The two can\'t be combined by load order. Make a patch whose navmesh fits what both mods put there.', None)
        self.add('navmesh', 'navmesh', text, 'Characters may stand still, walk through what the other mod placed, or the game can crash when it follows a link to a mesh that isn\'t there.',
                 adv, move=mv, **common)

    # ---- ground ----

    def check_land(self, rows):
        o, me = self.o, self.me
        if not rows:
            return
        at_square = {}
        for at in rows:
            sq = self.land_square(me, at)
            if sq:
                at_square[sq] = at
        if not at_square:
            return
        near = set(at_square)
        for w, x, y in at_square:
            near.update([(w, x + 1, y), (w, x - 1, y), (w, x, y + 1), (w, x, y - 1)])
        worlds = {sq[0] for sq in near}
        land = collections.defaultdict(list)    # square -> [(file, row)] in load order
        for i, ix in enumerate(o.files):
            if i == o.me:
                for sq, at in at_square.items():
                    land[sq].append((i, at))
                continue
            if not ix.ext:
                continue
            ext = _ext_map(ix)
            for at in ix.of_tag(LAND):
                xy = ext.get(ix.par[at])
                if not xy:
                    continue
                c = ix.row(ix.par[at])
                if c is None:
                    continue
                w = ix.form(ix.par[c])
                sq = (w, xy[0], xy[1])
                if w in worlds and sq in near:
                    land[sq].append((i, at))
        for sq, my_at in at_square.items():
            self.land_same_square(sq, my_at, land[sq])
        self.land_seams(at_square, land)

    def land_square(self, ix, at):
        cell = ix.par[at]
        xy = _ext_map(ix).get(cell)
        c = ix.row(cell)
        if not xy or c is None:
            return None
        return (ix.form(ix.par[c]), xy[0], xy[1])

    def land_same_square(self, sq, my_at, copies):
        o, me = self.o, self.me
        others = [c for c in copies if c[0] != o.me and o.files[c[0]].low not in self.built_on]
        last = copies[-1]
        if not others and last[0] == o.me:
            return
        self.contested += 1
        mine = Copy(o, o.me, my_at)
        built = [c for c in copies if o.files[c[0]].low in self.built_on]
        base = Copy(o, built[-1][0], built[-1][1]) if built else None
        final = Copy(o, last[0], last[1])
        where = 'outside, square %d, %d of %s' % (sq[1], sq[2], self.edid_of(sq[0]) or o.key(sq[0]))
        common = dict(key=o.key(me.form(me.fid[my_at])), type=LAND, wins=final.name, chain=[o.files[c[0]].name for c in copies],
                      go={'world': o.key(sq[0]), 'p': [sq[1] * 4096 + 2048, sq[2] * 4096 + 2048, 0]})
        if last[0] != o.me:
            lost = [] if changes_nothing(base, mine) else lost_fields(LAND, base, mine, final)
            if not lost:
                self.harmless['same' if mine.same(final) else 'other_fields'] += 1
                self.by_mod[final.name]['harmless'] += 1
                return
            low = o.files[last[0]].low
            if self.built_on_me(low):
                self.by_mod[final.name]['patched'] += 1
                self.add('patched', 'land', '%s changes your ground %s.' % (final.name, where), 'Theirs is used.', 'Nothing, unless it\'s out of date.', fields=lost, **common)
                return
            self.by_mod[final.name]['beats'] += 1
            adv, mv = self.advice_for(low)
            self.add('land', 'land', 'Your ground %s is overwritten by %s: %s.' % (where, final.name, ', '.join(lost)),
                     'The ground has their shape or paint, not yours; what you placed on it may float or sink.', adv, move=mv, fields=lost, **common)
            return
        undone = []
        for c in others:
            them = Copy(o, c[0], c[1])
            lost = lost_fields(LAND, base, them, mine)
            if lost and not changes_nothing(base, them):
                undone.append(them.name)
                self.by_mod[them.name]['beaten'] += 1
            else:
                self.by_mod[them.name]['harmless'] += 1
        if undone:
            self.add('land', 'land', 'Your ground %s replaces what %s did there.' % (where, ', '.join(undone)),
                     'What their mod placed on the ground may float or sink.', 'Load yours before theirs to let theirs win, or shape the square to suit both.', losers=undone, **common)
        else:
            self.harmless['keeps_theirs'] += 1

    def land_seams(self, at_square, land):
        """Where the square a plugin's copy ends up winning meets one someone else's copy wins, and the edges disagree."""
        o = self.o
        heights = {}

        def h(c):
            got = heights.get(c)
            if got is None:
                got = heights[c] = _heights(o, c[0], c[1])
            return got
        for sq in at_square:
            copies = land[sq]
            if copies[-1][0] != o.me:
                continue
            for step, side in (((1, 0), 'east'), ((-1, 0), 'west'), ((0, 1), 'north'), ((0, -1), 'south')):
                nb = (sq[0], sq[1] + step[0], sq[2] + step[1])
                them = land.get(nb)
                if not them or them[-1][0] == o.me:
                    continue
                a, b = h(copies[-1]), h(them[-1])
                if a is None or b is None:
                    continue
                gap = _edge_gap(a, b, side)
                if gap <= SEAM:
                    continue
                # (it was already so before this plugin? then it's not of its making)
                under = copies[-2] if len(copies) > 1 else None
                if under is not None:
                    u = h(under)
                    if u is not None and _edge_gap(u, b, side) >= gap - SEAM:
                        continue
                other = o.files[them[-1][0]].name
                self.contested += 1
                self.by_mod[other]['beats'] += 1
                self.add('land_seam', 'land', 'Along the %s edge of square %d, %d of %s, your ground and %s\'s are up to %d units apart.' % (side, sq[1], sq[2], self.edid_of(sq[0]) or o.key(sq[0]), other, round(gap)),
                         'A crack or a cliff in the ground along that line; the player can see through it or fall in.',
                         'Bring the edges together in your mod with the ground brush, or edit that edge against %s.' % other,
                         key=o.key(self.me.form(self.me.fid[copies[-1][1]])), type=LAND, wins=self.me.name, chain=[self.me.name, other],
                         go={'world': o.key(sq[0]), 'p': [sq[1] * 4096 + 2048, sq[2] * 4096 + 2048, 0]})

    # ---- links and doors ----

    def check_links(self, hits):
        """Deleted things the plugin's links point at, and the far ends of its doors."""
        o, me = self.o, self.me
        dead = {}
        for i, ix in enumerate(o.files):
            if i == o.me:
                continue
            for at, f in enumerate(ix.flg):
                if f & tes4.DELETED:
                    dead.setdefault(ix.form(ix.fid[at]), []).append(i)
        doors = []
        pf = o.pf(o.me)
        wanted = collections.defaultdict(list)
        for at, v in enumerate(me.fid):
            tag = me.tag_at(at)
            if tag in (NAVI, NAVM, LAND):
                continue
            rec = pf.record_at(me.off[at])
            if rec.flags & tes4.DELETED:
                continue
            try:
                subs = list(tes4.iter_subrecords(pf.data(rec)))
                links = formlinks.values(tag, subs, me.own)
            except Exception:
                continue
            if tag in PLACED:
                for st, d in subs:
                    if st == 'XTEL' and len(d) >= 4:
                        doors.append((at, tag, me.form(struct.unpack_from('<I', d)[0])))
            if dead:
                for n, _o, lv in links:
                    t = me.form(lv)
                    if t in dead and subs[n][0] != 'XTEL':
                        wanted[t].append((at, tag, subs[n][0]))
        if wanted:
            found = o.find(_group(wanted))
            for t, users in wanted.items():
                cs = found.get(t)
                if not cs or cs[-1][0] == o.me or o.files[cs[-1][0]].low in self.built_on or not Copy(o, cs[-1][0], cs[-1][1]).deleted:
                    continue    # (what a file it's built on deleted is the Health check's dead link)
                who = o.files[cs[-1][0]].name
                self.by_mod[who]['beats'] += 1
                self.contested += 1
                at, tag, st = users[0]
                c = Copy(o, o.me, at)
                self.add('deleted', GROUP_OF.get(tag, 'other'), '%s\'s %s links to %s, which %s deletes%s.' % (
                         self.what(me.form(me.fid[at]), c), label_of(tag, st), self.edid_of(t) or o.key(t), who, ' (%d of your records do)' % len(users) if len(users) > 1 else ''),
                         'The game can crash when it reaches for it, or the thing is simply missing.', 'Load %s before the plugin that deletes it, or point at something else.' % me.name,
                         key=o.key(t), type=tag, wins=who, chain=[me.name, who], go=self.go_of(me.form(me.fid[at]), c))
        if not doors:
            return
        found = o.find(_group({d[2]: 1 for d in doors}))
        for at, tag, target in doors:
            self.check_door(at, tag, target, found.get(target))

    def check_door(self, at, tag, target, copies):
        """The door at the far end, as the game ends up with it, doesn't lead back or is gone: only if someone else did that."""
        o, me = self.o, self.me
        if not copies:
            return
        i, row = copies[-1]
        low = o.files[i].low
        if i == o.me or low in self.built_on:
            return
        far = Copy(o, i, row)
        d = far.field('DATA')
        sunk = far.flags & DISABLED and d is not None and len(d) >= 12 and struct.unpack_from('<3f', d)[2] < SUNK
        ix = o.files[i]
        raw = tes4.subrecord_dict(o.pf(i).data(o.pf(i).record_at(ix.off[row]))).get('XTEL') if not far.deleted else None
        leads = ix.form(struct.unpack_from('<I', raw)[0]) if raw and len(raw) >= 4 else None
        form = me.form(me.fid[at])
        if far.deleted or sunk:
            says, notice = 'has removed that door', "The door doesn't work, or the player ends up under the world."
        elif leads is None:
            says, notice = "takes away that door's link", "The player can go in and can't come back that way."
        elif leads != form:
            says, notice = 'has that door lead somewhere else', 'The player goes one way and comes back somewhere else.'
        else:
            return
        c = Copy(o, o.me, at)
        adv, mv = self.advice_for(low)
        self.contested += 1
        self.by_mod[far.name]['beats'] += 1
        self.add('door', 'cell', '%s leads to %s, but %s %s.' % (self.what(form, c), self.edid_of(target) or o.key(target), far.name, says), notice, adv, move=mv,
                 key=o.key(target), type=tag, wins=far.name, chain=[o.files[x[0]].name for x in copies], go=self.go_of(form, c))

    # ---- the report ----

    def report(self):
        o = self.o
        self.rows.sort(key=lambda r: (r['rank'], r['text'].lower()))
        groups = []
        for k, title, why in GROUPS:
            rows = [r for r in self.rows if r['group'] == k]
            if rows:
                worst = min(r['rank'] for r in rows)
                groups.append({'kind': k, 'title': title, 'why': why, 'count': len(rows), 'rows': rows[:LIMIT], 'sev': list(ISSUES.values())[worst][0]})
        issues = [{'issue': k, 'sev': v[0], 'title': v[1], 'why': v[2], 'count': self.counts[k]} for k, v in ISSUES.items() if self.counts[k]]
        mods = []
        for name, c in self.by_mod.items():
            low = name.lower()
            row = {'name': name, 'beats': c['beats'], 'beaten': c['beaten'], 'harmless': c['harmless'], 'patched': c['patched']}
            if c['beats'] and low in o.at:
                mv, why = self.can_move_after(low)
                row['move'] = mv
                row['why'] = why
            mods.append(row)
        mods.sort(key=lambda m: (-m['beats'], -m['beaten'], -m['harmless'], m['name'].lower()))
        sev = collections.Counter()
        for k, n in self.counts.items():
            sev[ISSUES[k][0]] += n
        return {'plugin': self.me.name, 'installed': o.installed, 'was_on': o.was_on,
                'place': o.me + 1, 'of': len(o.files), 'masters': o.row.get('masters') or [],
                'touched': self.touched, 'contested': self.contested, 'summary': {'error': sev['error'], 'warn': sev['warn'], 'info': sev['info'], 'harmless': sum(self.harmless.values())},
                'issues': issues, 'groups': groups, 'mods': mods, 'harmless': dict(self.harmless), 'harmless_rows': self.harmless_rows, 'notes': o.notes, 'when': time.time()}


def type_word(tag):
    import health
    return health.TYPE_WORDS.get(tag, tag)


def _ext_map(ix):
    """{a cell's form ID in this file's numbering: (x, y)} for the cells outside."""
    if ix.squares is None:
        e = ix.ext
        m = {}
        for n in range(0, len(e), 3):
            x, y = e[n + 1], e[n + 2]
            m[e[n]] = (x - 0x100000000 if x >= 0x80000000 else x, y - 0x100000000 if y >= 0x80000000 else y)
        ix.squares = m
    return ix.squares


def _group(forms):
    out = collections.defaultdict(set)
    for owner, low in forms:
        out[owner].add(low)
    return out


def _heights(order, i, at):
    pf = order.pf(i)
    try:
        d = tes4.subrecord_dict(pf.data(pf.record_at(order.files[i].off[at]))).get('VHGT')
    except Exception:
        return None
    side = 33
    if not d or len(d) < 4 + side * side:
        return None
    start = struct.unpack_from('<f', d)[0]
    steps = struct.unpack_from('<%db' % (side * side), d, 4)
    h, row = [], start
    for r in range(side):
        row += steps[r * side]
        v = row
        h.append(v * 8)
        for c in range(1, side):
            v += steps[r * side + c]
            h.append(v * 8)
    return h


def _edge_gap(a, b, side):
    """The biggest difference along the edge where square a meets its neighbour b on that side."""
    n = 33
    if side == 'east':
        pts = ((r * n + n - 1, r * n) for r in range(n))
    elif side == 'west':
        pts = ((r * n, r * n + n - 1) for r in range(n))
    elif side == 'north':
        pts = (((n - 1) * n + c, c) for c in range(n))
    else:
        pts = ((c, (n - 1) * n + c) for c in range(n))
    return max(abs(a[p] - b[q]) for p, q in pts)


def check(data_dir, path, progress=None):
    """A plugin against the active load order, read only. path: a plugin in Data, or one elsewhere, as if installed."""
    order = Order(data_dir, path, progress)
    if order.me is None:
        raise ValueError('%s couldn\'t be read.' % os.path.basename(path))
    try:
        return Check(order, progress).run().report()
    finally:
        order.close()


# ---------- one record, side by side ----------

def compare(data_dir, path, key):
    """Every copy of one record, in load order, line up by field: {'columns': [...], 'rows': [{label, values, differs}]}."""
    name, low = key.rsplit(':', 1)
    form = (name.lower(), int(low, 16))
    order = Order(data_dir, path)
    if order.me is None:
        raise ValueError('%s couldn\'t be read.' % os.path.basename(path))
    try:
        ck = Check(order)
        found = order.find(_group([form])).get(form, [])
        cols, per = [], []
        for i, at in found:
            ix = order.files[i]
            pf = order.pf(i)
            rec = pf.record_at(ix.off[at])
            try:
                subs = list(tes4.iter_subrecords(pf.data(rec)))
            except Exception:
                subs = []
            text = _linker(ck, ix)
            per.append(recdiff.lines(rec.tag, subs, text))
            cols.append({'plugin': ix.name, 'mine': i == order.me, 'deleted': bool(rec.flags & tes4.DELETED), 'owner': ix.low == form[0], 'built_on': ix.low in ck.built_on})
        if cols:
            cols[-1]['wins'] = True
        rows = _line_up(per)
        return {'key': key, 'columns': cols, 'rows': rows, 'type': order.files[found[0][0]].tag_at(found[0][1]) if found else ''}
    finally:
        order.close()


def _linker(ck, ix):
    def word(v):
        f = ix.form(v)
        e = ck.edid_of(f)
        k = ck.o.key(f)
        return '%s (%s)' % (e, k) if e else k
    return word


def _line_up(per):
    """Lines of each copy, matched by label (the 2nd of a repeated label with the 2nd, in the order first seen)."""
    order, table = [], {}
    for n, lines in enumerate(per):
        seen = collections.Counter()
        for label, text in lines:
            k = (label, seen[label])
            seen[label] += 1
            if k not in table:
                table[k] = [None] * len(per)
                order.append(k)
            table[k][n] = text
    return [{'label': k[0], 'values': table[k], 'differs': len({str(v) for v in table[k]}) > 1} for k in order]


# ---------- a move, at the user's click ----------

def plan_move(data_dir, plugin, after):
    """The load order with plugin moved just after another: (names in order, what would go wrong)."""
    rows = loadorder.read(data_dir)['rows']
    have = {r['name'].lower(): r for r in rows if r['found']}
    me, them = have.get(plugin.lower()), have.get(after.lower())
    if not me or not them:
        raise ValueError('%s isn\'t in the Data folder.' % (plugin if not me else after))
    if me['official']:
        raise ValueError('The game\'s own files keep their place.')
    if me['esm'] and not them['esm']:
        raise ValueError('%s is a master: it always loads before plugins.' % me['name'])
    names = [r['name'] for r in rows if r['found'] and r['name'].lower() != plugin.lower()]
    names.insert(names.index(them['name']) + 1, me['name'])
    at = {n.lower(): i for i, n in enumerate(names)}
    bad = []
    for r in rows:
        if not r['found'] or not r['active']:
            continue
        for m in r['masters']:
            if m.lower() in at and at[m.lower()] > at[r['name'].lower()]:
                bad.append('%s needs %s, which would then load after it.' % (r['name'], m))
    return names, bad


def move(data_dir, plugin, after):
    """Load plugin after another: new dates, with loadorder.save's backup first. Nothing moves if a plugin would break."""
    names, bad = plan_move(data_dir, plugin, after)
    if bad:
        raise ValueError(bad[0])
    active = [r['name'] for r in loadorder.read(data_dir)['rows'] if r['active']]
    return loadorder.save(data_dir, names, active)


# ---------- on a thread, for the page ----------

_job = {'running': False, 'stage': '', 'done': 0, 'total': 0, 'file': '', 'result': None, 'error': None, 'scratch': None, 'path': None, 'token': 0, 'seconds': 0}
_lock = threading.Lock()


def _forget_scratch():
    if _job.get('scratch'):
        import health
        health._remove(_job['scratch'])
        _job['scratch'] = None


def start(S, file=None, data_dir=None):
    """Begin a check of the open mod (as it would be saved now), or of a plugin in Data. status() follows it."""
    import health
    data_dir = data_dir or S.GD.data_dir
    with _lock:
        if _job['running']:
            return status()
        _forget_scratch()
        _job.update(running=True, stage='starting', done=0, total=0, file='', result=None, error=None, path=None, seconds=0)
        _job['token'] += 1
    scratch = None
    try:
        if file:
            path = os.path.join(data_dir, os.path.basename(file))
            if not os.path.isfile(path):
                raise ValueError('%s isn\'t in the Data folder.' % os.path.basename(file))
        else:
            if not S.PR:
                raise ValueError('Open or start a mod first, or pick a plugin to look at.')
            import espwrite
            scratch = health.scratch_path(S.PR.plugin)
            with S._lock:
                data = espwrite.Writer(S.GD, S.PR).build()
            with open(scratch, 'wb') as f:
                f.write(data)
            path = scratch
    except Exception as e:
        _job.update(running=False, error=str(e), stage='')
        return status()
    _job.update(path=path, scratch=scratch)

    def progress(stage, done, total, name):
        _job.update(stage=stage, done=done, total=total, file=name)

    def work():
        t0 = time.time()
        try:
            out = check(data_dir, path, progress)
            out['mine_open'] = not file
            out['seconds'] = round(time.time() - t0, 2)
            fit_for_page(out, S, bool(file))
            _job.update(result=out, seconds=out['seconds'])
        except Exception as e:
            _job['error'] = str(e)
        _job.update(running=False, stage='')
    threading.Thread(target=work, daemon=True).start()
    return status()


def status():
    """Where the check has got to; the result when it's done."""
    keys = ('running', 'stage', 'done', 'total', 'file', 'error', 'seconds')
    out = {k: _job[k] for k in keys}
    if not _job['running'] and _job['result'] is not None:
        out['result'] = _job['result']
    return out


def fit_for_page(out, S, look):
    """Make clicks go somewhere FOLab can reach: only forms it has loaded, or the open mod's own."""
    gd = getattr(S, 'GD', None)
    pr = None if look else getattr(S, 'PR', None)
    if gd is None:
        return
    import health
    prefix = (out['plugin'].lower() + ':')

    def known(k):
        if k.lower().startswith(prefix) and pr and not pr.source:
            return '+' + k.rsplit(':', 1)[1]
        return k if health._can_go(gd, k) else None
    for g in out['groups']:
        for r in g['rows']:
            go = r.get('go')
            if go:
                new = {}
                for k, v in go.items():
                    if k in ('record', 'cell', 'world', 'ref'):
                        v = known(v)
                        if v is None:
                            new = None
                            break
                    new[k] = v
                if new is None:
                    r.pop('go')
                else:
                    r['go'] = new
            if r.get('itm') and pr:
                k = known(r['key'])
                if k in pr.records:
                    r['fix'] = {'action': 'revert_record', 'key': k, 'label': 'Take the copy out'}
                elif pr.source and k:
                    r['fix'] = {'action': 'drop', 'key': k, 'label': 'Take the copy out'}


def compare_last(data_dir, key):
    """compare() against the plugin the last check read (its scratch file stays until the next check)."""
    p = _job.get('path')
    if not p or not os.path.isfile(p):
        raise ValueError('Run the check first.')
    return compare(data_dir, p, key)


def short(result=None):
    """A line for the health check and the sharing steps: what the last check of the open mod found."""
    r = result if result is not None else _job.get('result')
    if not r:
        return None
    s = r['summary']
    parts = []
    if s['error']:
        parts.append('%d clash%s that will go wrong' % (s['error'], '' if s['error'] == 1 else 'es'))
    if s['warn']:
        parts.append('%d worth a look' % s['warn'])
    text = ', '.join(parts) if parts else 'No clashes with your load order.'
    return {'plugin': r['plugin'], 'text': text, 'sev': 'error' if s['error'] else 'warn' if s['warn'] else 'ok', 'contested': r['contested'], 'harmless': s['harmless'], 'when': r['when'], 'mine': r.get('mine_open', False)}
