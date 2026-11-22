"""A FOLab project: the changes a mod makes, kept as JSON beside FOLab and written out as an .esp on save.

    cells: {cell key: {'refs': {ref key: change}}}
      cell key / game ref key: 'FalloutNV.esm:10FDEB' (file and object ID, whatever the load order)
      new ref key: '+000800' (its object ID in this plugin)
      cell key '+ID': a place of the mod's own (its CELL record in records under the same key)
      change: {'base': key, 'p': [x, y, z, rx, ry, rz], 's': scale} for a new ref;
              'tel': {'door': ref key, 'p': [x, y, z, rx, ry, rz]} on a door: where it leads (made persistent);
              {'p': [...], 's': scale, 'base': key} for a changed game ref (each part optional: moved, rescaled,
              swapped for another thing); {'removed': True} for a removed one

Kept as <name>.json, the mod as it was when last written whole, and <name>.changes beside it: a line of JSON a save, the
entries that save changed ('set', 'del', 'head'), the first line naming the .json they go on (its size and date: a .json
written since by anything else makes the lines stale, and they're put aside as .changes.stale). A save writes only what
changed, found by comparing each entry with what was last written: cells, records, cellinfo and water by their contents
(so a change made by hand is found too), land and navmesh by identity (an entry there is only ever replaced whole).
save() writes the .json whole and starts the lines afresh, as does a .changes grown past JOURNAL_MOST. A copy of a mod is
both files, or compact() first and the .json alone.

Undo keeps, a step, what the step changed as it was before (cells and records as pickled bytes).

While FOLab's server has a mod open it holds <name>.inuse beside it (hold/release): any other process that tries to write
that mod (a script's save, apply, sync) gets InUse instead, so a script can't overwrite the user's edits, nor FOLab a
script's. Reading is always allowed. A lock left by a FOLab that died counts for nothing."""
import hashlib
import io
import json
import os
import pickle
import re
import time

HOME = os.environ.get('FOLAB_HOME') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS_DIR = os.path.join(HOME, 'projects')
BUILD_DIR = os.path.join(HOME, 'build')
FIRST_ID = 0x800                        # object IDs below this are the game's own


def safe_name(name):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', name).strip().strip('.')
    return name[:60] or 'New Mod'


def list_projects():
    if not os.path.isdir(PROJECTS_DIR):
        return []
    out = []
    for fn in os.listdir(PROJECTS_DIR):
        if fn.endswith('.json'):
            p = os.path.join(PROJECTS_DIR, fn)
            out.append({'name': fn[:-5], 'modified': modified(p)})
    return sorted(out, key=lambda x: -x['modified'])


DIFFED = ('cells', 'records', 'cellinfo', 'water')     # told changed by their contents
WHOLE = ('land', 'navmesh')                            # by identity: an entry there is only ever replaced whole
HEAD = ('name', 'plugin', 'author', 'description', 'drop', 'source', 'esm', 'trim_masters', 'newgame', 'next_id')
UNDONE = ('next_id', 'drop', 'newgame')                # what of the head Undo puts back
JOURNAL_MOST = 64 << 20                                # lines longer than this (or half the .json) are folded into the .json


def journal_path(path):
    return os.path.splitext(path)[0] + '.changes'


def modified(path):
    """When a mod was last changed: its .json or its lines, whichever is later."""
    t = os.path.getmtime(path)
    try:
        return max(t, os.path.getmtime(journal_path(path)))
    except OSError:
        return t


def _mark(path):
    try:
        st = os.stat(path)
        return [st.st_size, st.st_mtime_ns]
    except OSError:
        return None


class InUse(ValueError):
    """The mod is open in a running FOLab, and this is another program trying to change it."""


def lock_path(path):
    return os.path.splitext(path)[0] + '.inuse'


def _alive(pid):
    """Is that process still running, and a Python (FOLab's server)? (A dead FOLab's lock is no lock.)"""
    if pid == os.getpid():
        return True
    try:
        import ctypes
        from ctypes import wintypes
        k = ctypes.windll.kernel32
    except (ImportError, AttributeError):
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    h = k.OpenProcess(0x1000, False, int(pid))         # (PROCESS_QUERY_LIMITED_INFORMATION)
    if not h:
        return False
    try:
        code = wintypes.DWORD()
        if not k.GetExitCodeProcess(h, ctypes.byref(code)) or code.value != 259:      # (STILL_ACTIVE)
            return False
        buf, n = ctypes.create_unicode_buffer(1024), wintypes.DWORD(1024)
        if k.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)):
            return 'python' in os.path.basename(buf.value).lower()     # (a pid used again by another program)
        return True
    finally:
        k.CloseHandle(h)


def holder(path):
    """Who holds the mod at path open, if it's another running process: {'pid', 'by', 'since'}; else None."""
    try:
        with open(lock_path(path), encoding='utf-8') as f:
            d = json.load(f)
        pid = int(d['pid'])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if pid == os.getpid() or not _alive(pid):
        return None
    return d


def hold(path, by='FOLab'):
    """This process has the mod open for editing: no other may write it until release (FOLab's server does this for
    the mod it has open). Raises InUse if another running process holds it already."""
    h = holder(path)
    if h:
        raise InUse(_in_use_words(path, h))
    with open(lock_path(path), 'w', encoding='utf-8') as f:
        json.dump({'pid': os.getpid(), 'by': by, 'since': time.time()}, f)


def release(path):
    """Let go of the mod if this process holds it."""
    p = lock_path(path)
    try:
        with open(p, encoding='utf-8') as f:
            mine = int(json.load(f).get('pid', -1)) == os.getpid()
    except (OSError, ValueError, TypeError):
        return
    if mine:
        try:
            os.remove(p)
        except OSError:
            pass


def _in_use_words(path, h):
    name = os.path.splitext(os.path.basename(path))[0]
    return ('%s is open in %s (since %s). Close FOLab first: while it has the mod open, nothing else may change it, '
            'so nobody\'s edits are lost.' % (name, h.get('by') or 'FOLab', time.strftime('%H:%M', time.localtime(h.get('since') or 0))))


def check_free(path):
    """Raise InUse if a running FOLab other than this process has the mod open. Every write of a mod's files asks."""
    h = holder(path)
    if h:
        raise InUse(_in_use_words(path, h))


def pickled(v):
    """An entry's contents as bytes: the same for the same contents, however its parts are shared."""
    f = io.BytesIO()
    p = pickle.Pickler(f, pickle.HIGHEST_PROTOCOL)
    p.fast = True                       # (no memo: a string used twice is written twice, so sharing doesn't show)
    p.dump(v)
    return f.getvalue()


def read_journal(path, d):
    """A mod's .changes laid over its .json's contents d. False if there were none (none, or stale: put aside). A last
    line cut short (a save broken off) is cut off the file."""
    jp = journal_path(path)
    try:
        f = open(jp, 'rb')
    except OSError:
        return False
    with f:
        first = f.readline()
        try:
            head = json.loads(first)
        except ValueError:
            head = None
        stale = not isinstance(head, dict) or head.get('base') != _mark(path)
        good, cut = len(first), False
        for line in ([] if stale else f):
            try:
                if not line.endswith(b'\n'):
                    raise ValueError('cut short')
                e = json.loads(line)
            except ValueError:
                cut = True
                break
            for part, ents in (e.get('set') or {}).items():
                d.setdefault(part, {}).update(ents)
            for part, keys in (e.get('del') or {}).items():
                for k in keys:
                    (d.get(part) or {}).pop(k, None)
            d.update(e.get('head') or {})
            good += len(line)
    if stale:
        os.replace(jp, jp + '.stale')
        return False
    if cut:
        with open(jp, 'r+b') as f:
            f.truncate(good)
    return True


class Project:
    def __init__(self, path):
        self.path = path
        with open(path, encoding='utf-8') as f:
            d = json.load(f)
        had = read_journal(path, d)
        self.name = d['name']
        self.plugin = d['plugin']
        self.author = d.get('author', '')
        self.description = d.get('description', '')
        self.cells = d.get('cells', {})
        self.records = d.get('records', {})     # form key or '+ID' -> record (recordio.py): game records changed, new ones
        self.land = d.get('land', {})           # outside CELL key -> its ground as the mod has it (land.py's form)
        self.navmesh = d.get('navmesh', {})     # place's CELL key -> its navmesh as the mod has it (navbuild.py)
        self.drop = d.get('drop', [])           # keys of records an opened plugin has that saving leaves out (cleaning it)
        self.water = d.get('water', {})         # outside CELL key -> its water's height (None: the world's own level)
        self.cellinfo = d.get('cellinfo', {})   # CELL key -> what the mod sets on it (worldrec.py): {tag: key}, XCLR a list
        self.source = d.get('source')           # an opened plugin: its copy, under projects/ (adopt.py); None for a new mod
        self.esm = d.get('esm', False)          # saved as a master (.esm)
        self.trim_masters = d.get('trim_masters', False)   # an opened plugin FOLab made (a new world): masters nothing uses are left out
        self.newgame = d.get('newgame')         # the mod's own new game (newgame.py): its settings and what FOLab made for it
        self.next_id = d.get('next_id', FIRST_ID)
        self.undo_stack, self.redo_stack = [], []
        self._base = _mark(path)               # the .json the lines go on
        self._journal = os.path.getsize(self.journal_path) if had else 0
        self._resync()

    @property
    def journal_path(self):
        return journal_path(self.path)

    def modified(self):
        return modified(self.path)

    @classmethod
    def create(cls, name, author='', description=''):
        os.makedirs(PROJECTS_DIR, exist_ok=True)
        name = safe_name(name)
        path = os.path.join(PROJECTS_DIR, name + '.json')
        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({'name': name, 'plugin': name + '.esp', 'author': author[:511],
                           'description': description[:511], 'cells': {}, 'next_id': FIRST_ID}, f)
        return cls(path)

    @classmethod
    def open(cls, name):
        return cls(os.path.join(PROJECTS_DIR, safe_name(name) + '.json'))

    def to_dict(self):
        return {'name': self.name, 'plugin': self.plugin, 'author': self.author, 'description': self.description,
                'cells': self.cells, 'records': self.records, 'land': self.land, 'water': self.water, 'navmesh': self.navmesh, 'drop': self.drop, 'cellinfo': self.cellinfo, 'next_id': self.next_id,
                'source': self.source, 'esm': self.esm, 'trim_masters': self.trim_masters, 'newgame': self.newgame}

    def save(self, afresh=False):
        """Write the mod's .json whole and start its .changes afresh. An edit writes only what it changed (_commit): this is
        for a mod wanted as one file (a copy of it, the lines grown long) and for code that changed the mod by hand. The
        ground and the navmeshes are kept as the text last written for each cell and written again only when that cell's
        entry is another one: a change there always puts a whole new entry in (nothing edits one in place). afresh: don't
        trust that, and write everything out anew."""
        check_free(self.path)
        d = self.to_dict()
        kept = {} if afresh else getattr(self, '_written', {})
        now = {}
        parts = []
        for part in WHOLE:
            rows = []
            for k, v in d.pop(part).items():
                text = self._text(part, k, v, kept)
                now[(part, k)] = (v, text)           # (the entry itself is held, so no other can turn up at its address)
                rows.append(json.dumps(k) + ':' + text)
            parts.append(json.dumps(part) + ':{' + ','.join(rows) + '}')
        self._written = now
        head = json.dumps(d, separators=(',', ':'))
        tmp = self.path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(head[:-1] + ',' + ','.join(parts) + '}')
        os.replace(tmp, self.path)
        self._base = _mark(self.path)
        self._start_journal()
        self._resync()

    def compact(self):
        """The mod as its .json alone (before copying it as a file), unless that's what it is already."""
        if self._journal or self._diff() or json.dumps(self._head(), sort_keys=True) != self._saved_head:
            self.save()

    @staticmethod
    def _text(part, k, v, kept):
        had = kept.get((part, k))
        return had[1] if had is not None and had[0] is v else json.dumps(v, separators=(',', ':'))

    def _start_journal(self):
        """Lines for the .json as it is now, none in them yet (left out where there'd be none: a new mod has one file)."""
        jp = self.journal_path
        if os.path.exists(jp):
            os.remove(jp)
        self._journal = 0

    def _head(self):
        return {k: getattr(self, k) for k in HEAD}

    def _resync(self):
        """What was written is what the mod is now (after reading it or writing it whole)."""
        self._saved = {p: {k: pickled(v) for k, v in getattr(self, p).items()} for p in DIFFED}
        self._saved.update({p: dict(getattr(self, p)) for p in WHOLE})
        self._saved_head = json.dumps(self._head(), sort_keys=True)
        self._digests = {}

    def _diff(self):
        """What differs from what was last written: {part: {key: (as written or None, as now or None)}}, cells and
        records as pickled bytes, land and navmesh entries themselves."""
        out = {}
        for part in DIFFED:
            live, saved, ch = getattr(self, part), self._saved[part], {}
            for k, v in live.items():
                b = pickled(v)
                old = saved.get(k)
                if old != b:
                    ch[k] = (old, b)
            for k in saved.keys() - live.keys():
                ch[k] = (saved[k], None)
            if ch:
                out[part] = ch
        for part in WHOLE:
            live, saved = getattr(self, part), self._saved[part]
            ch = {k: (saved.get(k), v) for k, v in live.items() if saved.get(k) is not v}
            ch.update({k: (saved[k], None) for k in saved.keys() - live.keys()})
            if ch:
                out[part] = ch
        return out

    def _commit(self):
        """What changed since the last write, written as one line of the .changes. Returns _diff()'s."""
        ch = self._diff()
        head = json.dumps(self._head(), sort_keys=True)
        if not ch and head == self._saved_head:
            return ch
        check_free(self.path)
        if self._base is None or _mark(self.path) != self._base:
            self.save()                         # (the .json was written by something else since: the mod written whole)
            return ch
        written = getattr(self, '_written', {})
        sets, dels = [], {}
        for part, ents in ch.items():
            rows = []
            for k, (_old, new) in ents.items():
                if new is None:
                    dels.setdefault(part, []).append(k)
                    continue
                v = getattr(self, part)[k]
                if part in WHOLE:
                    text = self._text(part, k, v, written)
                    written[(part, k)] = (v, text)
                else:
                    text = json.dumps(v, separators=(',', ':'))
                rows.append(json.dumps(k) + ':' + text)
            if rows:
                sets.append(json.dumps(part) + ':{' + ','.join(rows) + '}')
        bits = ['"t":%.3f' % time.time()]
        if sets:
            bits.append('"set":{' + ','.join(sets) + '}')
        if dels:
            bits.append('"del":' + json.dumps(dels))
        if head != self._saved_head:
            bits.append('"head":' + json.dumps(self._head(), separators=(',', ':')))
        line = ('{' + ','.join(bits) + '}\n').encode('utf-8')
        if not self._journal:
            line = (json.dumps({'base': self._base, 'folab': 1}) + '\n').encode() + line
        with open(self.journal_path, 'ab' if self._journal else 'wb') as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
        self._journal += len(line)
        for part, ents in ch.items():
            saved = self._saved[part]
            for k, (_old, new) in ents.items():
                if new is None:
                    saved.pop(k, None)
                else:
                    saved[k] = new
        self._saved_head = head
        if self._journal > max(JOURNAL_MOST, self._base[0] // 2):
            self.save()                         # (folded in: the lines would take longer to read than the .json)
        return ch

    def sync(self):
        """Anything changed by hand since the last write, written now (not an Undo step)."""
        self._commit()

    def digest(self, part, key):
        """A short digest of an entry as last written (None: there's none), for telling what a build can reuse. sync()
        first, so that's how it is now."""
        v = self._saved.get(part, {}).get(key)
        if v is None:
            return None
        had = self._digests.get((part, key))
        if had is not None and had[0] is v:
            return had[1]
        h = hashlib.blake2b(v if part in DIFFED else pickled(v), digest_size=16).digest()
        self._digests[(part, key)] = (v, h)
        return h

    def source_path(self):
        return os.path.join(PROJECTS_DIR, self.source) if self.source else None

    def plugin_path(self):
        os.makedirs(BUILD_DIR, exist_ok=True)
        return os.path.join(BUILD_DIR, self.plugin)

    def count(self):
        return sum(len(c['refs']) for c in self.cells.values()) + len(self.records) + len(self.land) + len(self.water) + len(self.navmesh) + len(self.drop) + len(self.cellinfo)

    # --- edits: each one a single undo step ---

    def _head_copy(self):
        return pickle.loads(pickle.dumps({k: getattr(self, k) for k in UNDONE}))

    def _record(self, label, head, merge=False):
        """After an edit: its changes written, and kept for Undo as they were before (head: the undone part of the head as
        it was). merge: part of the last step."""
        ch = self._commit()
        before = {(part, k): old for part, ents in ch.items() for k, (old, _new) in ents.items()}
        if merge and self.undo_stack:
            for pk, old in before.items():
                self.undo_stack[-1][1].setdefault(pk, old)   # (what the step's first part found is what goes back)
            return
        self.undo_stack.append((label, before, head))
        del self.undo_stack[:-200]
        self.redo_stack.clear()

    def _swap(self, back, head):
        """Entries put back (back: {(part, key): as written, or None for none}), and the undone part of the head; returns
        both as they were, to go the other way."""
        now = {}
        for (part, k), old in back.items():
            live = getattr(self, part)
            now[(part, k)] = (pickled(live[k]) if part in DIFFED else live[k]) if k in live else None
            if old is None:
                live.pop(k, None)
            else:
                live[k] = pickle.loads(old) if part in DIFFED else old
        was = self._head_copy()
        self.next_id = max(head['next_id'], self.next_id)       # (an undone ID is never reused)
        self.drop, self.newgame = head['drop'], head['newgame']
        return now, was

    def _refs(self, cell):
        return self.cells.setdefault(cell, {'refs': {}})['refs']

    def apply(self, label, ops, merge=False):
        """Make several changes as one undo step. ops: [{'op': 'add'|'move'|'remove', ...}]. Returns the keys
        given to new refs, in order. merge: part of the last step (navmeshes made for what that step put in).
        A record_new or add with a 'name' can be named later in the same ops as '$name' (a cell, a ref, a door's link, what a
        placed thing is):
        self.names says what each became."""
        self.sync()                 # (anything changed by hand before this edit stays when it's undone, as it always did)
        head = self._head_copy()
        made, new_record = [], None
        names = self.names = {}

        def named(v):
            return names.get(v[1:], v) if isinstance(v, str) and v.startswith('$') and v not in ('$new', '$made') else v
        for o in ops:
            if names and any(named(o.get(f)) != o.get(f) for f in ('cell', 'ref')):
                o = dict(o, cell=named(o.get('cell')), ref=named(o.get('ref')))
            if names and named(o.get('base')) != o.get('base'):
                o = dict(o, base=named(o['base']))      # (a thing placed of a record made earlier in the same ops)
            if names and o.get('op') == 'tel' and o.get('tel') and named(o['tel'].get('door')) != o['tel'].get('door'):
                o = dict(o, tel=dict(o['tel'], door=named(o['tel']['door'])))
            if o['op'] == 'record':                  # a record as the mod has it (a game one changed, or its own)
                self.records[o['key']] = o['record']
                continue
            if o['op'] == 'record_new':              # a record of the mod's own: its key is made here
                key = '+%06X' % self.next_id
                self.next_id += 1
                self.records[key] = o['record']
                made.append(key)
                new_record = key
                if o.get('name'):
                    names[o['name']] = key
                continue
            if o['op'] == 'record_revert':           # a game record back as the game has it; one of the mod's own, gone
                self.records.pop(o['key'], None)
                continue
            if o['op'] == 'navmesh':                 # a place's navmesh, whole; its record's ID made here the first time
                mesh = dict(o['mesh'])
                if not mesh.get('form'):
                    mesh['form'] = '+%06X' % self.next_id
                    self.next_id += 1
                self.navmesh[o['cell']] = mesh
                continue
            if o['op'] == 'navmesh_revert':
                self.navmesh.pop(o['cell'], None)
                continue
            if o['op'] == 'newgame':                 # the mod's own new game: its settings, whole (newgame.py)
                self.newgame = o['settings']
                continue
            if o['op'] == 'cellinfo':                # details on a place (music, region, zone...), the entry whole
                self.cellinfo[o['cell']] = o['info']
                continue
            if o['op'] == 'cellinfo_revert':
                self.cellinfo.pop(o['cell'], None)
                continue
            if o['op'] == 'place':                   # a ref whose key is already made, for refs that name each other
                self._refs(o['cell'])[o['key']] = o['ref']
                continue
            if o['op'] == 'ref_set':                 # extras on a ref: a map marker's name, a zone, a link
                r = self._refs(o['cell']).setdefault(o['ref'], {})
                r.update(o['set'])
                continue
            if o['op'] == 'land':                    # an outside cell's ground, whole (heights, colours, textures)
                self.land[o['cell']] = o['land']
                continue
            if o['op'] == 'land_revert':
                self.land.pop(o['cell'], None)
                continue
            if o['op'] == 'water':                   # an outside cell's water level (None: back to the world's)
                self.water[o['cell']] = None if o.get('h') is None else float(o['h'])
                continue
            if o['op'] == 'water_revert':
                self.water.pop(o['cell'], None)
                continue
            if o['op'] == 'drop':                    # an opened plugin's own copy of a record, left out when saved
                if o['key'] not in self.drop:
                    self.drop.append(o['key'])
                continue
            if o['op'] == 'drop_revert':
                self.drop = [k for k in self.drop if k != o['key']]
                continue
            if o.get('cell') == '$new':                # (the place a record_new earlier in these ops just made)
                o = dict(o, cell=new_record)
            if o.get('base') == '$made':               # (a thing swapped for the record a record_new just made)
                o = dict(o, base=new_record)
            lock = ((o.get('extra') or {}).get('props') or {}).get('lock') or {}
            if lock.get('key') == '$made':             # (a lock whose key is that record: a generated vault's office)
                o = dict(o, extra=dict(o['extra'], props=dict(o['extra']['props'], lock=dict(lock, key=new_record))))
            elif names and lock.get('key') and named(lock['key']) != lock['key']:     # (a key made earlier in these ops, by name)
                o = dict(o, extra=dict(o['extra'], props=dict(o['extra']['props'], lock=dict(lock, key=named(lock['key'])))))
            refs = self._refs(o['cell'])
            if o['op'] == 'tel':                     # a door's link: where it leads, or (None) nowhere new
                r = refs.setdefault(o['ref'], {})
                if o.get('tel'):
                    r['tel'] = o['tel']
                    r['persistent'] = True
                else:
                    r.pop('tel', None)
                    if not o['ref'].startswith('+'):
                        r.pop('persistent', None)
                if not r:
                    refs.pop(o['ref'], None)
            elif o['op'] == 'add':
                key = '+%06X' % self.next_id
                self.next_id += 1
                refs[key] = {'base': o['base'], 'p': [float(v) for v in o['p']], 's': float(o.get('s', 1.0))}
                if o.get('gen'):
                    refs[key]['gen'] = True          # (generated in the Kit tab)
                if o.get('sc'):
                    refs[key]['sc'] = True           # (scattered by the brush)
                if o.get('xlcm') is not None:
                    refs[key]['xlcm'] = int(o['xlcm'])   # (a levelled actor's difficulty: 0 easy .. 3 very hard)
                if o.get('extra'):
                    refs[key].update(o['extra'])     # (persistent, a map marker, a zone: see worldrec.py)
                if o.get('name'):
                    names[o['name']] = key
                made.append(key)
            elif o['op'] == 'move':
                r = refs.setdefault(o['ref'], {})
                r.pop('removed', None)
                r['p'] = [float(v) for v in o['p']]
                if 's' in o:
                    r['s'] = float(o['s'])
            elif o['op'] == 'remove':
                if o['ref'].startswith('+'):
                    refs.pop(o['ref'], None)
                else:
                    refs[o['ref']] = {'removed': True}
            elif o['op'] == 'props':                 # its owner, lock, what enables it (refprops.py)
                r = refs.setdefault(o['ref'], {})
                r.setdefault('props', {}).update(o['props'])
            elif o['op'] == 'persist':               # kept loaded: something else names it
                refs.setdefault(o['ref'], {})['persistent'] = True
            elif o['op'] == 'swap':                  # the same spot, another thing
                r = refs.setdefault(o['ref'], {})
                r.pop('removed', None)
                r['base'] = o['base']
            elif o['op'] == 'revert':                # a game ref back to how the game has it
                refs.pop(o['ref'], None)
            if not refs:
                self.cells.pop(o['cell'], None)
        self._record(label, head, merge)
        return made

    def undo(self):
        if not self.undo_stack:
            return None
        self.sync()
        label, back, head = self.undo_stack.pop()
        now, was = self._swap(back, head)
        self.redo_stack.append((label, now, was))
        self._commit()
        return label

    def redo(self):
        if not self.redo_stack:
            return None
        self.sync()
        label, back, head = self.redo_stack.pop()
        now, was = self._swap(back, head)
        self.undo_stack.append((label, now, was))
        self._commit()
        return label

    def state(self):
        return {'name': self.name, 'plugin': self.plugin, 'changes': self.count(), 'opened': bool(self.source), 'esm': self.esm,
                'undo': self.undo_stack[-1][0] if self.undo_stack else None,
                'redo': self.redo_stack[-1][0] if self.redo_stack else None, 'saved': time.time()}
