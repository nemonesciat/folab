"""Play reports: nv-rs's F12 reports turned into a fix list (a Markdown page per play session, and JSON).

nv-rs (its Play.exe sets NV_REPORT_DIR to userdata\\reports) writes a numbered folder at each F12 press, read in its
window procedure (WM_KEYDOWN 0x7B), so it works with a pad connected too:

    NNN\\picture.bmp     the frame
    NNN\\log.txt         the log so far ("F12: place: <place.txt's lines joined by '; '>", "F12: report in <folder>")
    NNN\\log-start.txt   the log's first bytes (the same for every report of one run of the game)
    NNN\\note.txt        the player's words, under nv-rs's prompt line
    NNN\\place.txt       where it was (nv-rs crates/host/src/report_place.rs), for example:
        worldspace: WastelandNV (0x000da726)        (or "interior cell: GSDocMitchellHouse (0x00104c1c)")
        cell: 0x000de4c2 at grid (-10, 4)
        position: -39000 18200 5800
        view: pitch 3.0 heading 270.0 (degrees)
        game hour: 17.50
        weather: ...
        lighting: key=value ...
        console: cow WastelandNV -10 4; player.setpos x -39000; player.setpos y 18200; player.setpos z 5800; ...
      or "no place: nothing in this program writes it" / "place not given within N presents".
    NNN\\hitches.txt     the run's hitch lines

Form IDs in a place are the running game's (load-order index first), so worlds and cells are matched to the plugin by
editor ID first, then by the low 24 bits.

For each report: where (world, cell, position, else the cell's middle), the mod's things near it read from the built
plugin as the game loads it (tes4.PluginFile, read only), which step placed each where its editor ID or its base's says
(the `FOLab...` names FOLab's own modules write, `steps_by_name`), and the note. With `live=` the mod's .json (and its
.changes, read here without touching them: project.read_journal moves and cuts files, so it isn't used) says what the
mod has changed near the spot since that build. Never project.apply: it writes the journal.

Output goes to the reports folder's parent (nv-rs's userdata) or a folder given; never into the game's folder or nv-rs's
mods or app folders (`refuse_out`).

    py -3 app/playreports.py C:\\Games\\nv-rs-newest\\userdata\\reports [--out DIR] [--live PROJECT.json] [--from N]
"""
import argparse
import glob
import hashlib
import json
import math
import os
import re
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tes4                                                     # noqa: E402

APP = os.path.dirname(os.path.abspath(__file__))
CELL = 4096.0
RADIUS = 1024.0             # outside: things this near the spot are listed
RADIUS_IN = 768.0           # inside a place
MOST = 30                   # listed per report (the rest counted)
GONE_Z = -29000.0           # a game ref the mod took out is disabled and sunk to -30000 (espwrite)
REF_TAGS = ('REFR', 'ACHR', 'ACRE', 'PGRE', 'PMIS')
PROMPT = 'Write here what went wrong and what you did just before it:'
LOG_HINT = re.compile(r'error|warning|crash|missing|not found|could not|failed', re.I)


# --- place.txt -------------------------------------------------------------------------------------------------------

_NAMED = re.compile(r'^\s*(?:(?P<edid>\S+)\s+\()?(?P<fid>0x[0-9a-fA-F]+)\)?\s*$')


def named(text):
    """'WastelandNV (0x000da726)' or '0x01000d7e' -> {'edid', 'formid'}; anything else is kept as the name."""
    text = (text or '').strip()
    m = _NAMED.match(text)
    if not m:
        return {'edid': text or None, 'formid': None} if text and text != 'none' else None
    return {'edid': m.group('edid'), 'formid': int(m.group('fid'), 16)}


def parse_place(text):
    """place.txt's lines (or log.txt's 'F12: place:' line, the same joined by '; ') as a dict; None for no place."""
    if not text or not text.strip():
        return None
    t = text.replace('\r', '')
    if t.lstrip().startswith(('no place', 'place not given')):
        return {'missing': t.strip()}
    if '\n' not in t.strip() and '; ' in t:            # the log's one line
        t = re.sub(r'; (?=(worldspace|cell|interior cell|position|view|game hour|weather|lighting|console): )', '\n', t)
    out = {'interior': False, 'world': None, 'cell': None, 'grid': None, 'position': None}
    for line in t.split('\n'):
        key, _, val = line.partition(': ')
        key, val = key.strip(), val.strip()
        if key == 'worldspace':
            out['world'] = named(val)
        elif key == 'interior cell':
            out['interior'] = True
            out['cell'] = named(val)
        elif key == 'cell':
            m = re.match(r'(.*?)\s+at grid \((-?\d+), (-?\d+)\)', val)
            if m:
                out['cell'] = named(m.group(1))
                out['grid'] = [int(m.group(2)), int(m.group(3))]
            else:
                out['cell'] = named(val)
        elif key == 'position':
            nums = re.findall(r'-?\d+(?:\.\d+)?', val)
            if len(nums) >= 3:
                out['position'] = [float(n) for n in nums[:3]]
        elif key == 'view':
            m = re.search(r'pitch (-?[\d.]+).*heading (-?[\d.]+)', val)
            if m:
                out['view'] = {'pitch': float(m.group(1)), 'heading': float(m.group(2))}
        elif key == 'game hour':
            try:
                out['hour'] = float(val)
            except ValueError:
                pass
        elif key == 'weather':
            out['weather'] = named(val)
        elif key == 'lighting':
            out['lighting'] = val
        elif key == 'console':
            out['console'] = val
            m = re.search(r'\bcow (\S+) (-?\d+) (-?\d+)', val)
            if m:
                out['world'] = out['world'] or {'edid': m.group(1), 'formid': None}
                if out['world'].get('edid') is None:
                    out['world']['edid'] = m.group(1)
                out['grid'] = out['grid'] or [int(m.group(2)), int(m.group(3))]
            m = re.search(r'\bcoc (\S+?);', val + ';')
            if m and out['cell'] and not out['cell'].get('edid'):
                out['cell']['edid'] = m.group(1)
            if not out['position']:
                xyz = [re.search(r'setpos %s (-?[\d.]+)' % a, val) for a in 'xyz']
                if all(xyz):
                    out['position'] = [float(x.group(1)) for x in xyz]
    if out['position'] and not out['interior'] and not out['grid']:
        out['grid'] = [math.floor(out['position'][0] / CELL), math.floor(out['position'][1] / CELL)]
    return out


def spot_of(place):
    """(x, y, z, guessed): the position, else the middle of the cell (z 0)."""
    if not place or place.get('missing'):
        return None
    if place.get('position'):
        x, y, z = place['position']
        return x, y, z, False
    if place.get('grid'):
        gx, gy = place['grid']
        return (gx + 0.5) * CELL, (gy + 0.5) * CELL, 0.0, True
    return None


# --- the report folders ----------------------------------------------------------------------------------------------

def _read(path, limit=None):
    try:
        with open(path, 'rb') as f:
            b = f.read() if limit is None else f.read(limit)
    except OSError:
        return None
    return b.decode('utf-8', 'replace')


def note_of(text):
    """The player's words: nv-rs's prompt line taken off."""
    if text is None:
        return ''
    t = text.replace('\r', '')
    if t.lstrip().startswith(PROMPT):
        t = t.lstrip()[len(PROMPT):]
    return t.strip()


def read_report(folder):
    """One numbered report folder as a dict."""
    name = os.path.basename(os.path.normpath(folder))
    log = _read(os.path.join(folder, 'log.txt')) or ''
    place_text = _read(os.path.join(folder, 'place.txt'))
    log_place = None
    for line in log.replace('\r', '').split('\n'):
        if line.startswith('F12: place: '):
            log_place = line[len('F12: place: '):]
    place = parse_place(place_text) if place_text and place_text.strip() else parse_place(log_place)
    start = _read(os.path.join(folder, 'log-start.txt')) or ''
    pic = os.path.join(folder, 'picture.bmp')
    if not os.path.isfile(pic):
        pics = sorted(glob.glob(os.path.join(folder, '*.bmp')) + glob.glob(os.path.join(folder, '*.png')))
        pic = pics[0] if pics else None
    when = os.path.getmtime(pic or folder)
    lines = [l for l in log.replace('\r', '').split('\n') if l.strip() and not l.startswith('F12: ')]
    hints = [l[:300] for l in lines[-400:] if LOG_HINT.search(l)][-8:]
    return {
        'number': int(name) if name.isdigit() else None, 'name': name, 'folder': os.path.abspath(folder),
        'picture': os.path.abspath(pic) if pic else None, 'note': note_of(_read(os.path.join(folder, 'note.txt'))),
        'place': place, 'place_text': (place_text or log_place or '').replace('\r', '').strip(),
        'when': time.strftime('%Y-%m-%d %H:%M', time.localtime(when)), 'time': when,
        'run': hashlib.sha1(start.encode('utf-8', 'replace')).hexdigest()[:12] if start else None,
        'log_hints': hints,
    }


def read_reports(folder, first=None):
    """Every numbered report under folder (or folder itself if it is one), oldest first."""
    folder = os.path.abspath(folder)
    if any(os.path.isfile(os.path.join(folder, f)) for f in ('place.txt', 'note.txt', 'log.txt')):
        subs = [folder]
    else:
        subs = [os.path.join(folder, d) for d in os.listdir(folder)
                if d.isdigit() and os.path.isdir(os.path.join(folder, d))]
    out = [read_report(s) for s in subs]
    if first is not None:
        out = [r for r in out if r['number'] is None or r['number'] >= first]
    return sorted(out, key=lambda r: (r['number'] if r['number'] is not None else 1 << 30, r['time']))


def sessions(reports):
    """Reports grouped by run of the game (the same log start), in order."""
    groups, order = {}, []
    for r in reports:
        k = r['run'] or r['when'][:10]
        if k not in groups:
            groups[k] = []
            order.append(k)
        groups[k].append(r)
    return [groups[k] for k in order]


# --- which step made a thing -----------------------------------------------------------------------------------------

_LITERAL = re.compile(r'''['"](FOLab[A-Za-z0-9_]{2,})''')


def steps_by_name(app_dir=APP):
    """{editor ID prefix: [module, ...]} from the FOLab... names in FOLab's own modules, the module naming it most first."""
    count = {}
    for path in glob.glob(os.path.join(app_dir, '*.py')):
        mod = os.path.splitext(os.path.basename(path))[0]
        if mod == 'playreports':
            continue
        try:
            with open(path, encoding='utf-8', errors='replace') as f:
                text = f.read()
        except OSError:
            continue
        for lit in _LITERAL.findall(text):
            c = count.setdefault(lit, {})
            c[mod] = c.get(mod, 0) + 1
    return {lit: [m for m, _ in sorted(c.items(), key=lambda kv: -kv[1])] for lit, c in count.items()}


_SET_PATH = re.compile(r"folab[\\/]+([a-z0-9_]+)[\\/]", re.I)
_SET_NAME = re.compile(r"""\bSET\s*=\s*['"]([a-z0-9_]+)['"]""")


def steps_by_set(app_dir=APP):
    """{model folder under meshes\\folab: [module, ...]}: the module whose SET it is first, then those naming the folder."""
    count = {}
    for path in glob.glob(os.path.join(app_dir, '*.py')):
        mod = os.path.splitext(os.path.basename(path))[0]
        if mod == 'playreports':
            continue
        try:
            with open(path, encoding='utf-8', errors='replace') as f:
                text = f.read()
        except OSError:
            continue
        for s, weight in [(m, 1) for m in _SET_PATH.findall(text)] + [(m, 5) for m in _SET_NAME.findall(text)]:
            c = count.setdefault(s.lower(), {})
            c[mod] = c.get(mod, 0) + weight
    return {s: [m for m, _ in sorted(c.items(), key=lambda kv: -kv[1])] for s, c in count.items()}


def set_of(model):
    """The folder of FOLab's own model under meshes\\folab ('rubble' for folab\\rubble\\heap_a.nif), or None."""
    if not model:
        return None
    parts = [p for p in re.split(r'[\\/]+', model.lower()) if p]
    if parts and parts[0] == 'meshes':
        parts = parts[1:]
    return parts[1] if len(parts) > 2 and parts[0] == 'folab' else None


class Steps:
    """Which of FOLab's modules made a thing: by its editor ID (the FOLab... names they write), else by its model's
    folder (FOLab's own pieces are meshes\\folab\\<set>\\...)."""

    def __init__(self, table=None, sets=None):
        self.table = steps_by_name() if table is None else table
        self.sets = steps_by_set() if sets is None else sets
        self._by_len = sorted(self.table, key=len, reverse=True)
        self._cache = {}

    def of(self, *edids, model=None):
        """The modules, best first (at most three), or []."""
        for e in edids:
            if not e or not e.startswith('FOLab'):
                continue
            if e not in self._cache:
                hit = next((lit for lit in self._by_len if e.startswith(lit)), None)
                self._cache[e] = self.table[hit][:3] if hit else []
            if self._cache[e]:
                return self._cache[e]
        s = set_of(model)
        if s:
            return self.sets.get(s, [])[:3] or ['set %s' % s]
        return []


# --- the built plugin ------------------------------------------------------------------------------------------------

def _edid(fields):
    e = fields.get('EDID')
    return tes4.zstr(e) if e else None


class ModIndex:
    """What the built plugin has at each report's spot: one walk for the worlds and cells, one for the refs there."""

    def __init__(self, esp, masters_names=None):
        self.path = esp
        self.pf = tes4.PluginFile(esp)
        self.masters = self.pf.header['masters']
        self.own = len(self.masters)
        self.file = os.path.basename(esp)
        self.names = {}             # formid (plugin's numbering) -> (tag, edid) for every non-ref record
        self.models = {}            # formid -> MODL, for the records that have one
        self.worlds = {}            # formid -> edid
        self.cells = {}             # formid -> {'edid', 'grid', 'world', 'interior', 'name'}
        self.master_names = masters_names
        self._first_walk()

    def close(self):
        self.pf.close()

    def file_of(self, formid):
        i = formid >> 24
        return self.masters[i] if i < self.own else self.file

    def key_of(self, formid):
        """FOLab's key for a form: '+XXXXXX' for the plugin's own, 'File.esm:XXXXXX' for a master's."""
        if formid >> 24 >= self.own:
            return '+%06X' % (formid & 0xFFFFFF)
        return '%s:%06X' % (self.file_of(formid), formid & 0xFFFFFF)

    def _first_walk(self):
        pf = self.pf
        for rec, groups in pf.walk():
            if rec.tag in REF_TAGS or rec.tag in ('NAVM', 'LAND', 'INFO', 'NAVI'):
                continue
            f = pf.fields(rec)
            e = _edid(f)
            self.names[rec.formid] = (rec.tag, e)
            if 'MODL' in f:
                self.models[rec.formid] = tes4.zstr(f['MODL'])
            if rec.tag == 'WRLD':
                self.worlds[rec.formid] = e
            elif rec.tag == 'CELL':
                world = next((lab for gt, lab, _ in reversed(groups) if gt == tes4.G_WORLD_CHILDREN), None)
                flags = f.get('DATA', b'\0')[0] if f.get('DATA') else 0
                grid = list(struct.unpack_from('<ii', f['XCLC'], 0)) if len(f.get('XCLC', b'')) >= 8 else None
                full = f.get('FULL')
                # a world's persistent cell sits straight in its children group (not in a block), and carries
                # an XCLC of (0, 0) when written as the game files it: by its group, not by a missing grid
                in_block = any(gt in (4, 5) for gt, _, _ in groups)
                persistent = world is not None and (grid is None or not in_block)
                self.cells[rec.formid] = {'edid': e, 'grid': None if persistent else grid, 'world': world,
                                          'interior': bool(flags & 1),
                                          'name': tes4.zstr(full) if full else None,
                                          'persistent': persistent}

    # matching the running game's forms to the plugin's

    def _match(self, want, pool):
        """The formids in pool {formid: edid} that `want` ({'edid', 'formid'}) names: by editor ID, then low 24 bits."""
        if not want:
            return []
        if want.get('edid'):
            hits = [fid for fid, e in pool.items() if e and e.lower() == want['edid'].lower()]
            if hits:
                return hits
        if want.get('formid') is not None:
            low = want['formid'] & 0xFFFFFF
            hits = [fid for fid in pool if fid & 0xFFFFFF == low]
            own = [h for h in hits if h >> 24 >= self.own]
            return own or hits
        return []

    def where(self, place):
        """{'world': formid or None, 'cells': [formid, ...], 'interior': bool} in the plugin's numbering."""
        if not place or place.get('missing'):
            return None
        if place.get('interior'):
            pool = {fid: c['edid'] for fid, c in self.cells.items() if c['interior']}
            return {'world': None, 'cells': self._match(place.get('cell'), pool), 'interior': True}
        worlds = self._match(place.get('world'), self.worlds)
        world = worlds[0] if worlds else None
        cells = []
        if world is not None and place.get('grid'):
            gx, gy = place['grid']
            cells = [fid for fid, c in self.cells.items() if c['world'] == world and c['grid']
                     and abs(c['grid'][0] - gx) <= 1 and abs(c['grid'][1] - gy) <= 1]
            cells += [fid for fid, c in self.cells.items() if c['world'] == world and c['persistent']]
        return {'world': world, 'cells': cells, 'interior': False}

    def refs_in(self, cell_ids):
        """{cell formid: [ref, ...]} for the refs the plugin has in those cells (their data read only there)."""
        want = set(cell_ids)
        out = {c: [] for c in want}
        if not want:
            return out
        pf = self.pf
        for rec, groups in pf.walk():
            if rec.tag not in REF_TAGS or not groups:
                continue
            gt, cell, _ = groups[-1]
            if gt not in (tes4.G_CELL_PERSISTENT, tes4.G_CELL_TEMPORARY, tes4.G_CELL_VWD) or cell not in want:
                continue
            f = pf.fields(rec)
            if 'DATA' not in f or len(f['DATA']) < 24:
                continue
            pos = struct.unpack_from('<6f', f['DATA'], 0)
            base = struct.unpack_from('<I', f['NAME'], 0)[0] if len(f.get('NAME', b'')) >= 4 else None
            full = f.get('FULL')
            out[cell].append({
                'formid': rec.formid, 'tag': rec.tag, 'edid': _edid(f), 'base': base, 'pos': list(pos[:3]),
                'rot': list(pos[3:]), 'scale': struct.unpack_from('<f', f['XSCL'], 0)[0] if 'XSCL' in f else 1.0,
                'off': bool(rec.flags & 0x800), 'deleted': bool(rec.flags & tes4.DELETED),
                'marker': 'XMRK' in f, 'marker_name': tes4.zstr(full) if full and 'XMRK' in f else None,
                'parent': struct.unpack_from('<I', f['XESP'], 0)[0] if len(f.get('XESP', b'')) >= 4 else None,
                'door_to': 'XTEL' in f, 'own': rec.formid >> 24 >= self.own, 'cell': cell,
            })
        return out

    def base_name(self, formid):
        """(tag, edid, file) of a base form, the masters' through master_names when given."""
        if formid is None:
            return None, None, None
        tag, e = self.names.get(formid, (None, None))
        if e is None and self.master_names is not None and formid >> 24 < self.own:
            tag, e = self.master_names.get(self.file_of(formid), formid & 0xFFFFFF)
        return tag, e, self.file_of(formid)


class MasterNames:
    """Editor IDs of master records, read from the game's Data folder (read only) for just the forms asked."""

    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.wanted = {}            # file -> set of object ids
        self.found = {}             # (file, object id) -> (tag, edid)

    def want(self, file, objid):
        if (file, objid) not in self.found:
            self.wanted.setdefault(file, set()).add(objid)

    def resolve(self):
        for file, ids in self.wanted.items():
            path = os.path.join(self.data_dir, file)
            if not ids or not os.path.isfile(path):
                continue
            pf = tes4.PluginFile(path)
            own = len(pf.header['masters'])
            try:
                for rec, _ in pf.walk():
                    if rec.tag in REF_TAGS or rec.formid >> 24 != own:
                        continue
                    o = rec.formid & 0xFFFFFF
                    if o in ids:
                        self.found[(file, o)] = (rec.tag, _edid(pf.fields(rec)))
            finally:
                pf.close()
        self.wanted = {}

    def get(self, file, objid):
        return self.found.get((file, objid), (None, None))


# --- the live mod, read only -----------------------------------------------------------------------------------------

def read_live(path):
    """The mod's .json with its .changes laid on in memory: the files are only read (never project.read_journal)."""
    with open(path, encoding='utf-8') as f:
        d = json.load(f)
    jp = os.path.splitext(path)[0] + '.changes'
    try:
        with open(jp, 'rb') as f:
            lines = f.read().split(b'\n')
    except OSError:
        return d
    for line in lines[1:]:
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except ValueError:
            break
        for part, ents in (e.get('set') or {}).items():
            d.setdefault(part, {}).update(ents)
        for part, keys in (e.get('del') or {}).items():
            for k in keys:
                (d.get(part) or {}).pop(k, None)
    return d


def live_refs(live, idx, cell_ids):
    """{ref key: change} the live mod has in those cells (keyed as FOLab keys them)."""
    out = {}
    cells = live.get('cells') or {}
    for cid in cell_ids:
        key = idx.key_of(cid)
        alt = '%s:%06X' % (idx.file, cid & 0xFFFFFF) if key.startswith('+') else None
        for k in (key, alt):
            for rk, ch in ((cells.get(k) or {}).get('refs') or {}).items():
                out[rk] = dict(ch, cell=cid)
    return out


# --- one report against the plugin -----------------------------------------------------------------------------------

def _dist(a, b):
    return math.sqrt(sum((p - q) ** 2 for p, q in zip(a, b)))


def describe(rep, idx, steps, refs_by_cell, live=None, radius=None):
    """The report with 'at' (where, in the plugin's terms) and 'near' (the mod's things round the spot)."""
    place = rep['place']
    at = idx.where(place)
    spot = spot_of(place)
    rep = dict(rep, at=None, near=[], more=0, landmark=None, live_changes=[])
    if not at:
        return rep
    world = idx.worlds.get(at['world']) if at['world'] is not None else None
    cell_names = [idx.cells[c]['edid'] or idx.cells[c]['name'] or idx.key_of(c) for c in at['cells']
                  if not idx.cells[c]['persistent']]
    rep['at'] = {'world': world, 'world_found': at['world'] is not None or at['interior'],
                 'cells': cell_names[:9], 'interior': at['interior'], 'found': bool(at['cells']),
                 'spot': list(spot[:3]) if spot else None, 'spot_guessed': bool(spot and spot[3])}
    if not spot:
        return rep
    r = radius or (RADIUS_IN if at['interior'] else RADIUS)
    xyz = spot[:3]
    flat = spot[3]                  # no height given: measure across the ground only
    near, landmark = [], None
    for cid in at['cells']:
        for ref in refs_by_cell.get(cid, []):
            sunk = ref['pos'][2] < GONE_Z      # (a game thing taken out lies far under: measured across the ground)
            d = _dist(ref['pos'][:2], xyz[:2]) if flat or sunk else _dist(ref['pos'], xyz)
            if ref['marker'] and ref['marker_name']:
                dd = _dist(ref['pos'][:2], xyz[:2])
                if landmark is None or dd < landmark[1]:
                    landmark = (ref['marker_name'], dd)
            if d > r:
                continue
            near.append((d, ref))
    near.sort(key=lambda t: t[0])
    rep['more'] = max(0, len(near) - MOST)
    rep['landmark'] = {'name': landmark[0], 'distance': round(landmark[1])} if landmark else None
    for d, ref in near[:MOST]:
        btag, bedid, bfile = idx.base_name(ref['base'])
        kind = 'added by the mod' if ref['own'] else 'a game thing the mod changed'
        if not ref['own'] and (ref['pos'][2] < GONE_Z or ref['deleted']):
            kind = 'a game thing the mod took out'
        rep['near'].append({
            'distance': round(d), 'ref': idx.key_of(ref['formid']), 'edid': ref['edid'], 'base': bedid or (
                idx.key_of(ref['base']) if ref['base'] is not None else None), 'base_type': btag,
            'base_file': bfile, 'kind': kind, 'starts_off': ref['off'],
            'pos': [round(v) for v in ref['pos']], 'scale': round(ref['scale'], 3),
            'model': idx.models.get(ref['base']),
            'step': steps.of(ref['edid'], bedid, model=idx.models.get(ref['base'])), 'door': ref['door_to'],
        })
    if live is not None:
        rep['live_changes'] = _live_diff(live, idx, at['cells'], refs_by_cell, xyz, r, flat)
    return rep


def _live_diff(live, idx, cells, refs_by_cell, xyz, r, flat):
    """What the live mod has near the spot that the built plugin doesn't: moved, swapped, removed, new."""
    built = {}
    for cid in cells:
        for ref in refs_by_cell.get(cid, []):
            built[idx.key_of(ref['formid'])] = ref
    out = []
    for rk, ch in live_refs(live, idx, cells).items():
        p = ch.get('p')
        b = built.get(rk)
        where = p[:3] if p else (b['pos'] if b else None)
        if where is None:
            continue
        d = _dist(where[:2], xyz[:2]) if flat else _dist(where, xyz)
        if d > r:
            continue
        what = None
        if ch.get('removed'):
            if b is not None and b['pos'][2] > GONE_Z and not b['own']:
                what = 'taken out since the build'
            elif b is not None and b['own']:
                what = 'taken out since the build'
        elif b is None:
            what = 'added since the build'
        else:
            if p and _dist(p[:3], b['pos']) > 1.0:
                what = 'moved since the build'
            bk = idx.key_of(b['base']) if b['base'] is not None else None
            if ch.get('base') and bk and ch['base'] != bk and not ch['base'].startswith('$'):
                what = (what + ', ' if what else '') + 'swapped since the build'
        if what:
            out.append({'ref': rk, 'what': what, 'distance': round(d), 'base': ch.get('base')})
    out.sort(key=lambda t: t['distance'])
    return out[:MOST]


# --- the pages -------------------------------------------------------------------------------------------------------

def refuse_out(out_dir, nvrs_root=None, game_dir=None):
    """Raise if out_dir is inside the game's folder or nv-rs's own mods/app folders."""
    o = os.path.normcase(os.path.abspath(out_dir))
    bad = []
    if game_dir:
        bad.append(game_dir)
    if nvrs_root:
        bad += [os.path.join(nvrs_root, 'mods'), os.path.join(nvrs_root, 'app'),
                os.path.join(nvrs_root, 'userdata', 'modgame')]
    for b in bad:
        b = os.path.normcase(os.path.abspath(b))
        if o == b or o.startswith(b.rstrip('\\/') + os.sep):
            raise ValueError('not writing into %s: pick another folder' % b)
    if os.path.basename(o).lower() == 'data' or (os.sep + 'data' + os.sep) in o + os.sep and \
            os.path.isfile(os.path.join(o, 'FalloutNV.esm')):
        raise ValueError("not writing into a game's Data folder")


def _rel(path, base):
    try:
        return os.path.relpath(path, base).replace('\\', '/')
    except ValueError:
        return 'file:///' + path.replace('\\', '/')


def _where_words(rep):
    p, at = rep['place'], rep['at']
    if not p:
        return 'no place written'
    if p.get('missing'):
        return p['missing'] if p['missing'].startswith('no place') else 'no place (%s)' % p['missing']
    bits = []
    if p.get('interior'):
        c = p.get('cell') or {}
        bits.append('inside %s' % (c.get('edid') or ('%#010x' % c['formid'] if c.get('formid') is not None else '?')))
    else:
        w = p.get('world') or {}
        bits.append(w.get('edid') or ('%#010x' % w['formid'] if w.get('formid') is not None else 'world ?'))
        if p.get('grid'):
            bits.append('cell %d, %d' % tuple(p['grid']))
    if p.get('position'):
        bits.append('at %d %d %d' % tuple(round(v) for v in p['position']))
    elif at and at.get('spot'):
        bits.append("the cell's middle (no position given)")
    return ', '.join(bits)


def markdown(group, out_dir, esp, live_path=None):
    first = group[0]
    lines = ['# Play session %s' % first['when'], '',
             '%d report%s, F12 in nv-rs. Read against `%s` (as built%s).' % (
                 len(group), '' if len(group) == 1 else 's', esp,
                 '; live mod `%s` for changes since' % live_path if live_path else ''), '']
    lines += ['| # | When | Where | Note |', '|---|---|---|---|']
    for r in group:
        note = (r['note'] or '(no note)').replace('\n', ' ').replace('|', '/')
        lines.append('| [%s](#report-%s) | %s | %s | %s |' % (r['name'], r['name'], r['when'][11:],
                                                              _where_words(r).replace('|', '/'),
                                                              note[:120] + ('...' if len(note) > 120 else '')))
    lines.append('')
    for r in group:
        lines += ['<a id="report-%s"></a>' % r['name'], '## Report %s · %s' % (r['name'], r['when']), '']
        lines += ['**Note:** ' + (r['note'].replace('\n', '  \n') if r['note'] else '(no note)'), '']
        lines.append('**Where:** ' + _where_words(r))
        at = r.get('at')
        if at:
            if at.get('world') and not at['interior']:
                lines.append('  \nWorld in the plugin: `%s`; cells: %s' % (
                    at['world'], ', '.join('`%s`' % c for c in at['cells']) or 'none of the mod\'s'))
            elif at['interior']:
                lines.append('  \nPlace in the plugin: %s' % (', '.join('`%s`' % c for c in at['cells'])
                                                             or "not one of the mod's (the game's own)"))
            if not at['world_found']:
                lines.append("  \nThat world isn't in the plugin: the mod has nothing there.")
        if r.get('landmark'):
            lines.append('  \nNearest map marker: %s (%d units)' % (r['landmark']['name'], r['landmark']['distance']))
        p = r['place'] or {}
        if p.get('console'):
            lines.append('  \nTo go there: `%s`' % p['console'])
        lines.append('')
        if r['picture']:
            lines += ['![report %s](%s)' % (r['name'], _rel(r['picture'], out_dir)), '']
        if r['near']:
            lines += ["**The mod's things near** (within %d%s):" % (
                RADIUS_IN if at and at['interior'] else RADIUS, ', across the ground' if at and at['spot_guessed']
                else ''), '', '| Units | Thing | Base | Step | What |', '|---|---|---|---|---|']
            for n in r['near']:
                what = n['kind'] + (', starts off' if n['starts_off'] else '') + (', door' if n['door'] else '')
                lines.append('| %d | `%s`%s | %s%s | %s | %s |' % (
                    n['distance'], n['ref'], ' ' + n['edid'] if n['edid'] else '', n['base'] or '?',
                    ' (%s)' % n['base_type'] if n['base_type'] else '', ', '.join(n['step']) or '-', what))
            if r['more']:
                lines.append('\n%d more within reach not listed.' % r['more'])
            lines.append('')
        elif at:
            lines += ["Nothing of the mod's within reach.", '']
        if r.get('live_changes'):
            lines += ['**Changed in the live mod since that build:**', '']
            lines += ['- `%s` %s (%d units)' % (c['ref'], c['what'], c['distance']) for c in r['live_changes']]
            lines.append('')
        if r['log_hints']:
            lines += ['<details><summary>Log lines worth a look</summary>', '', '```']
            lines += r['log_hints'] + ['```', '', '</details>', '']
        lines += ['Folder: `%s`' % r['folder'], '']
    return '\n'.join(lines)


def _plugin_of(nvrs_root):
    try:
        with open(os.path.join(nvrs_root, 'mods', 'folab.json'), encoding='utf-8') as f:
            plugins = json.load(f).get('plugins') or []
    except (OSError, ValueError):
        plugins = []
    plugins = [p for p in plugins if not p.lower().startswith('folab ')]
    return os.path.join(nvrs_root, 'mods', plugins[0]) if plugins else None


def _game_dir(nvrs_root):
    t = _read(os.path.join(nvrs_root, 'userdata', 'game-folder.txt'))
    return t.strip() if t and t.strip() else None


def run(reports_dir, out_dir=None, esp=None, live=None, data_dir=None, first=None, radius=None, steps=None):
    """Read the reports, write a page per play session and one JSON. Returns (pages, json path, reports)."""
    reports_dir = os.path.abspath(reports_dir)
    parent = os.path.dirname(reports_dir)
    nvrs_root = os.path.dirname(parent) if os.path.basename(parent).lower() == 'userdata' else None
    out_dir = os.path.abspath(out_dir or parent)
    game_dir = _game_dir(nvrs_root) if nvrs_root else None
    refuse_out(out_dir, nvrs_root, game_dir)
    if esp is None and nvrs_root:
        esp = _plugin_of(nvrs_root)
    if not esp or not os.path.isfile(esp):
        raise ValueError('no built plugin to read: give esp=')
    if data_dir is None and game_dir:
        data_dir = os.path.join(game_dir, 'Data')
    reports = read_reports(reports_dir, first)
    names = MasterNames(data_dir) if data_dir and os.path.isdir(data_dir) else None
    idx = ModIndex(esp, names)
    try:
        cells = set()
        for r in reports:
            at = idx.where(r['place'])
            if at:
                cells.update(at['cells'])
        refs = idx.refs_in(cells)
        if names is not None:
            for lst in refs.values():
                for ref in lst:
                    b = ref['base']
                    if b is not None and b >> 24 < idx.own and b not in idx.names:
                        names.want(idx.file_of(b), b & 0xFFFFFF)
            names.resolve()
        steps = steps or Steps()
        live_d = read_live(live) if live else None
        done = [describe(r, idx, steps, refs, live_d, radius) for r in reports]
    finally:
        idx.close()
    os.makedirs(out_dir, exist_ok=True)
    pages = []
    for group in sessions(done):
        stamp = time.strftime('%Y%m%d-%H%M', time.localtime(group[0]['time']))
        path = os.path.join(out_dir, 'play-session-%s-%s.md' % (stamp, group[0]['name']))
        text = markdown(group, out_dir, esp, live)
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(text)
        os.replace(tmp, path)
        pages.append(path)
    jpath = os.path.join(out_dir, 'play-reports.json')
    tmp = jpath + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump({'esp': esp, 'live': live, 'reports': done}, f, indent=1)
    os.replace(tmp, jpath)
    return pages, jpath, done


def main(argv=None):
    ap = argparse.ArgumentParser(description="nv-rs's F12 reports as a fix list")
    ap.add_argument('reports', nargs='?', default=r'C:\Games\nv-rs-newest\userdata\reports')
    ap.add_argument('--out', help="where the pages go (default: the reports folder's parent)")
    ap.add_argument('--esp', help='the built plugin (default: the one in nv-rs mods)')
    ap.add_argument('--live', help="the mod's .json, to show what changed since the build (read only; large)")
    ap.add_argument('--data', help="the game's Data folder, for the game's names (read only)")
    ap.add_argument('--from', dest='first', type=int, help='only reports numbered this or later')
    ap.add_argument('--radius', type=float)
    a = ap.parse_args(argv)
    pages, jpath, done = run(a.reports, a.out, a.esp, a.live, a.data, a.first, a.radius)
    for p in pages:
        print(p)
    print(jpath)
    print('%d reports' % len(done))


if __name__ == '__main__':
    main()
