"""The game's data as one thing: its Data folder, plugins in load order, archives, and an index of every form.
Read-only."""
import glob
import os
import re
import struct
import threading

import bsa
import tes4

_ARCHIVES_LOCK = threading.Lock()
STEAM_APP = 22380
# The game's own files, in the order the launcher loads them
OFFICIAL = ['FalloutNV.esm', 'DeadMoney.esm', 'HonestHearts.esm', 'OldWorldBlues.esm', 'LonesomeRoad.esm',
            'GunRunnersArsenal.esm', 'ClassicPack.esm', 'MercenaryPack.esm', 'TribalPack.esm', 'CaravanPack.esm']

# Base record types that are drawn from a mesh (MODL)
MODEL_TYPES = {'STAT', 'MSTT', 'FURN', 'CONT', 'DOOR', 'LIGH', 'MISC', 'ACTI', 'TACT', 'IDLM', 'BOOK', 'WEAP',
               'ARMO', 'ALCH', 'AMMO', 'KEYM', 'NOTE', 'TERM', 'ADDN', 'PWAT', 'SCOL', 'CHIP', 'CMNY', 'IMOD',
               'CCRD', 'TREE', 'GRAS', 'BPTD', 'HAIR', 'EYES'}
REF_TYPES = {'REFR', 'ACHR', 'ACRE', 'PGRE', 'PMIS', 'PBEA', 'PFLA', 'PCBE', 'NAVM'}
# Form IDs below this are made by the game itself, not by any plugin (markers such as 0x20)
BUILTIN_LIMIT = 0x800


GAME_FOLDER = 'Fallout New Vegas'
# Where Windows is told a program lives: (hive, key, value). Steam itself, then the game as its launcher, Steam's
# uninstaller and GOG's each write it down.
_STEAM_KEYS = [('HKCU', r'Software\Valve\Steam', 'SteamPath'), ('HKLM', r'SOFTWARE\WOW6432Node\Valve\Steam', 'InstallPath'),
               ('HKLM', r'SOFTWARE\Valve\Steam', 'InstallPath')]
_STEAM_USUAL = [r'C:\Program Files (x86)\Steam', r'C:\Program Files\Steam']
_GAME_KEYS = [('HKLM', r'SOFTWARE\WOW6432Node\Bethesda Softworks\FalloutNV', 'Installed Path'),
              ('HKLM', r'SOFTWARE\Bethesda Softworks\FalloutNV', 'Installed Path'),
              ('HKLM', r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Steam App %d' % STEAM_APP, 'InstallLocation'),
              ('HKLM', r'SOFTWARE\WOW6432Node\GOG.com\Games\1454587428', 'path'),
              ('HKLM', r'SOFTWARE\WOW6432Node\GOG.com\Games\1312824873', 'path')]


def _registry(hive, key, value):
    """A text value Windows keeps, or '' (also anywhere that isn't Windows)."""
    try:
        import winreg
        with winreg.OpenKey(getattr(winreg, {'HKCU': 'HKEY_CURRENT_USER', 'HKLM': 'HKEY_LOCAL_MACHINE'}[hive]), key) as k:
            v = winreg.QueryValueEx(k, value)[0]
        return v if isinstance(v, str) else ''
    except (ImportError, OSError):
        return ''


def _steam_libraries():
    """Every Steam library folder: Steam's own folder, wherever Windows says it is, and the others its list names."""
    # (the usual places first, spelt as they always were; the registry writes Steam's path in lower case)
    roots = list(_STEAM_USUAL) + [_registry(*k) for k in _STEAM_KEYS]
    out = []
    for root in roots:
        if not root:
            continue
        root = os.path.normpath(root)
        vdf = os.path.join(root, 'steamapps', 'libraryfolders.vdf')
        if os.path.isfile(vdf):
            out.append(root)
            with open(vdf, encoding='utf-8', errors='replace') as f:
                out += [os.path.normpath(p.replace('\\\\', '\\')) for p in re.findall(r'"path"\s+"([^"]+)"', f.read())]
    return _once(out)


def _once(paths):
    """Each folder once, however its letters are cased; the first spelling stays."""
    seen = {}
    for p in paths:
        seen.setdefault(os.path.normcase(p), p)
    return list(seen.values())


def data_dir_from(path):
    """The game's Data folder from whatever was pointed at: Data itself, the game's folder, or a file in either
    (FalloutNV.exe, FalloutNV.esm). None if the game isn't there. Never Steam's download folder: files held open
    there stop Steam moving them into place ("disk write error")."""
    p = os.path.normpath(os.path.expandvars((path or '').strip().strip('"')))
    if not p or p == '.':
        return None
    if os.path.isfile(p):
        p = os.path.dirname(p)
    for d in (p, os.path.join(p, 'Data')):
        if os.path.isfile(os.path.join(d, 'FalloutNV.esm')) and 'steamapps\\downloading' not in d.lower().replace('/', '\\'):
            return d
    return None


def _chosen():
    """The folder the user pointed FOLab at (`remember_data_dir`), while the game is still there."""
    import json
    import project
    try:
        with open(os.path.join(project.HOME, 'folab_settings.json'), encoding='utf-8') as f:
            return data_dir_from(json.load(f).get('game_data') or '')
    except (OSError, ValueError, AttributeError):
        return None


def remember_data_dir(path):
    """Keep the user's own answer to where the game is. Returns the Data folder, or None if the game isn't there."""
    import json
    import project
    d = data_dir_from(path)
    if not d:
        return None
    p = os.path.join(project.HOME, 'folab_settings.json')
    try:
        with open(p, encoding='utf-8') as f:
            s = json.load(f)
    except (OSError, ValueError):
        s = {}
    s['game_data'] = d
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(s, f, indent=1)
    return d


def looked_in():
    """Every place FOLab looks for the game by itself, for saying where it looked."""
    out = [os.path.join(lib, 'steamapps', 'common', GAME_FOLDER) for lib in _steam_libraries()]
    out += [os.path.normpath(v) for v in (_registry(*k) for k in _GAME_KEYS) if v]
    return _once(out)


def find_data_dir():
    """FOLAB_NV_DATA, else the folder the user chose, else the game wherever Steam, the game's own launcher or GOG
    put it. None when it's nowhere to be found: the server then asks (`server.NO_GAME`)."""
    env = os.environ.get('FOLAB_NV_DATA')
    if env:
        return env
    d = _chosen()
    if d:
        return d
    for place in looked_in():
        d = data_dir_from(place)
        if d:
            return d
    return None


class GameData:
    """Plugins in load order with every form indexed by its load-order form ID (last plugin wins)."""

    def __init__(self, data_dir=None, plugins=None):
        self.data_dir = data_dir or find_data_dir()
        if not self.data_dir:
            raise FileNotFoundError('New Vegas Data folder not found (set FOLAB_NV_DATA)')
        names = plugins or [p for p in OFFICIAL if os.path.isfile(os.path.join(self.data_dir, p))]
        self.plugins = [tes4.PluginFile(n if os.path.isabs(n) else os.path.join(self.data_dir, n)) for n in names]
        # (by file name: a plugin loaded from elsewhere, like an opened mod's copy, is still known by its name)
        self.names = [os.path.basename(n).lower() for n in names]
        self.forms = {}         # global form ID -> (plugin index, Record)
        self.cell_refs = {}     # global CELL form ID -> {global ref form ID: (plugin index, Record)}
        self.ref_cell = {}      # global ref form ID -> global CELL form ID
        self.interiors = set()
        self.ext_cells = {}         # global exterior CELL form ID -> its WRLD
        self.world_persistent = {}  # WRLD -> its persistent CELL
        self.land = {}              # CELL -> (plugin index, LAND Record)
        self._grids = {}            # WRLD -> {(x, y): CELL}, filled when asked
        self._persist_grid = {}     # WRLD -> {(x, y): [ref form ID]}, its persistent refs by where they stand
        for i, p in enumerate(self.plugins):
            self._index(i, p)
        self._archives = None
        self.overlay = None         # the open mod's own files, looked for first (library.Overlay)
        self.view = None            # an MO2 loadout: loose files and archives come through it (loadout.py)

    def to_global(self, i, formid):
        """A form ID as plugin i wrote it, re-based on the load order (its high byte names the owning file)."""
        p = self.plugins[i]
        owner = p.owner(formid).lower()
        j = self.names.index(owner) if owner in self.names else i
        return (j << 24) | (formid & 0xFFFFFF)

    def key(self, fid):
        """A form's lasting name, 'FalloutNV.esm:10FDEB': stays right whatever the load order becomes."""
        return '%s:%06X' % (self.plugins[fid >> 24].path.replace('\\', '/').rsplit('/', 1)[-1], fid & 0xFFFFFF)

    def from_key(self, key):
        name, low = key.rsplit(':', 1)
        return (self.names.index(name.lower()) << 24) | int(low, 16)

    def source(self, fid):
        """(plugin index, Record) of the winning record for a form, as the game would load it."""
        return self.forms[fid]

    def _index(self, i, p):
        g = lambda fid: self.to_global(i, fid)
        for rec, path in p.walk():
            fid = g(rec.formid)
            self.forms[fid] = (i, rec)
            if rec.tag == 'CELL':
                if path and path[0][1] == 0x4C4C4543 and len(path) >= 2 and path[1][0] == tes4.G_INT_BLOCK:
                    self.interiors.add(fid)                   # top group 'CELL' (label as int) holds interiors
                else:
                    world = next((lab for gt, lab, _o in path if gt == tes4.G_WORLD_CHILDREN), None)
                    if world is not None:
                        # a grid cell sits in an exterior block; the one straight in the world's group is its
                        # persistent cell, holding everything the world keeps loaded
                        if any(gt == tes4.G_EXT_BLOCK for gt, _l, _o in path):
                            self.ext_cells[fid] = g(world)
                        else:
                            self.world_persistent[g(world)] = fid
            elif rec.tag == 'LAND':
                cell = next((lab for gt, lab, _o in reversed(path) if gt in (tes4.G_CELL_TEMPORARY, tes4.G_CELL_CHILDREN)), None)
                if cell is not None:
                    self.land[g(cell)] = (i, rec)
            elif rec.tag in REF_TYPES:
                for gtype, label, _off in reversed(path):
                    if gtype in (tes4.G_CELL_PERSISTENT, tes4.G_CELL_TEMPORARY, tes4.G_CELL_VWD):
                        self.cell_refs.setdefault(g(label), {})[fid] = (i, rec)
                        self.ref_cell[fid] = g(label)
                        break

    def fields(self, fid):
        i, rec = self.forms[fid]
        return self.plugins[i].fields(rec)

    def ref_fields(self, entry):
        i, rec = entry
        return i, self.plugins[i].fields(rec)

    def edid(self, fid):
        e = self.fields(fid).get('EDID')
        return tes4.zstr(e) if e else ''

    def describe(self, fid):
        """(type, editor ID, display name, model path or '') for a base form."""
        i, rec = self.forms[fid]
        f = self.plugins[i].fields(rec)
        # (apparel lying in the world uses its ground model, MOD2; MODL is the one worn)
        m = f.get('MOD2') or f.get('MODL', b'') if rec.tag == 'ARMO' else f.get('MODL', b'')
        return (rec.tag, tes4.zstr(f.get('EDID', b'')), tes4.zstr(f.get('FULL', b'')),
                tes4.zstr(m) if rec.tag in MODEL_TYPES else '')

    def tree(self, fid):
        """A SpeedTree tree (TREE) as FOLab draws it: the flat picture the game shows of it from afar (its
        billboard: the .dds named like its .spt, in textures/trees/billboards) and that picture's size (BNAM; the
        height at least half its bounds' height)."""
        f = self.fields(fid)
        model = tes4.zstr(f.get('MODL', b''))
        stem = model.replace('/', chr(92)).rsplit(chr(92), 1)[-1].rsplit('.', 1)[0].lower()
        tex = chr(92).join(['textures', 'trees', 'billboards', stem + '.dds'])
        w = h = 256.0
        if 'BNAM' in f and len(f['BNAM']) >= 8:
            w, h = struct.unpack_from('<2f', f['BNAM'])
        if 'OBND' in f and len(f['OBND']) >= 12:
            b = struct.unpack_from('<6h', f['OBND'])
            if b[5] > b[2]:
                h = max(h * 0.5, b[5] - b[2])
        return {'tex': tex if self.find_file(tex) else '', 'w': w, 'h': h}

    def navmeshes(self, cell):
        return [e for e in self.cell_refs.get(cell, {}).values() if e[1].tag == 'NAVM']

    @staticmethod
    def model_path(btype, model):
        """A base form's MODL as a path under Data: trees are SpeedTree files under trees\\, the rest meshes."""
        return ('trees\\' if btype == 'TREE' else 'meshes\\') + model.lstrip('\\/')

    # --- outside: worldspaces and their grid of cells ---

    CELL_SIZE = 4096

    def worlds(self):
        return sorted(f for f, (i, r) in self.forms.items() if r.tag == 'WRLD')

    def grid(self, world):
        """{(x, y): CELL} for a worldspace's exterior cells."""
        if world not in self._grids:
            out = {}
            for c, w in self.ext_cells.items():
                if w == world:
                    xclc = self.fields(c).get('XCLC')
                    if xclc and len(xclc) >= 8:
                        out[struct.unpack_from('<ii', xclc)] = c
            self._grids[world] = out
        return self._grids[world]

    def cell_grid(self, cell):
        xclc = self.fields(cell).get('XCLC')
        return struct.unpack_from('<ii', xclc) if xclc and len(xclc) >= 8 else None

    def parent_world(self, world, flag):
        """The world this one takes something from (flag: 1 land, 2 LOD, 4 map, 8 water...), or None."""
        f = self.fields(world)
        if 'WNAM' not in f:
            return None
        use = struct.unpack_from('<H', f['PNAM'])[0] if 'PNAM' in f and len(f['PNAM']) >= 2 else 0
        i = self.forms[world][0]
        return self.to_global(i, struct.unpack_from('<I', f['WNAM'])[0]) if use & flag else None

    def land_at(self, world, x, y):
        """(plugin index, LAND Record) for a grid square, from the world's parent when it borrows its land."""
        c = self.grid(world).get((x, y))
        if c is not None and c in self.land:
            return self.land[c]
        parent = self.parent_world(world, 1)
        return self.land_at(parent, x, y) if parent is not None and parent != world else None

    def persistent_in(self, world, x, y):
        """The refs a world keeps always loaded that stand in grid square (x, y)."""
        if world not in self._persist_grid:
            out = {}
            pc = self.world_persistent.get(world)
            for rfid, entry in self.cell_refs.get(pc, {}).items():
                i, f = self.ref_fields(entry)
                if 'DATA' in f and len(f['DATA']) >= 12:
                    px, py = struct.unpack_from('<2f', f['DATA'])
                    out.setdefault((int(px // self.CELL_SIZE), int(py // self.CELL_SIZE)), []).append(rfid)
            self._persist_grid[world] = out
        return self._persist_grid[world].get((x, y), [])

    def refs(self, cell):
        """Every placed thing in a cell (navmeshes apart): dicts with the ref, its base form, position, rotation (radians) and scale.
        An exterior cell includes the world's always-loaded things standing in it."""
        out = []
        entries = dict(self.cell_refs.get(cell, {}))
        if cell in self.ext_cells:
            xy = self.cell_grid(cell)
            pc = self.world_persistent.get(self.ext_cells[cell])
            for rfid in self.persistent_in(self.ext_cells[cell], *xy) if xy else ():
                entries[rfid] = self.cell_refs[pc][rfid]
        for rfid, entry in sorted(entries.items()):
            i, f = self.ref_fields(entry)
            if entry[1].flags & tes4.DELETED or entry[1].tag == 'NAVM':
                continue
            base = self.to_global(i, struct.unpack_from('<I', f['NAME'])[0]) if 'NAME' in f else None
            pos = rot = None
            if 'DATA' in f and len(f['DATA']) >= 24:
                v = struct.unpack_from('<6f', f['DATA'])
                pos, rot = v[:3], v[3:]
            scale = struct.unpack_from('<f', f['XSCL'])[0] if 'XSCL' in f else 1.0
            out.append({'ref': rfid, 'type': entry[1].tag, 'base': base, 'pos': pos, 'rot': rot, 'scale': scale,
                        'persistent': bool(entry[1].flags & tes4.PERSISTENT), 'leads': 'XTEL' in f})
        return out

    # --- archives and loose files ---

    def archives(self):
        """BSAs in the order the game searches them: later ones win, like plugins."""
        got = self._archives
        if got is not None:
            return got
        # (the server's threads all ask at once as a place opens: none may see a list that's only part made, or a file in
        # an archive not reached yet reads as missing)
        with _ARCHIVES_LOCK:
            if self._archives is not None:
                return self._archives
            if self.view:
                found = self.view.archives_like('fallout - *.bsa')
                for n in self.names:
                    stem = os.path.splitext(n)[0]
                    found += self.view.archives_like(glob.escape(stem) + '.bsa') + self.view.archives_like(glob.escape(stem) + ' - *.bsa')
                found += self.view.archives_like('update.bsa')
                made = []
                for p in dict.fromkeys(found):
                    try:                    # (one mod's broken archive mustn't stop the rest of a loadout loading)
                        made.append(bsa.Archive(p))
                    except (OSError, ValueError, struct.error) as e:
                        print('archive left out: %s: %s' % (p, e), flush=True)
            else:
                found = sorted(glob.glob(os.path.join(self.data_dir, 'Fallout - *.bsa')))
                for n in self.names:
                    stem = os.path.splitext(n)[0]
                    found += sorted(glob.glob(os.path.join(self.data_dir, stem + ' - *.bsa')))
                found += glob.glob(os.path.join(self.data_dir, 'Update.bsa'))
                made = [bsa.Archive(p) for p in dict.fromkeys(found)]
            self._archives = made
        return made

    def loose_path(self, rel):
        """The loose file the game would use for a path under Data, or None."""
        if self.view:
            return self.view.path(rel)
        p = os.path.join(self.data_dir, rel)
        return p if os.path.isfile(p) else None

    def find_file(self, rel):
        """Where a game file comes from: 'loose', an archive's file name, or None."""
        rel = bsa.norm(rel)
        if self.overlay and self.overlay.path(rel):
            return 'your mod'
        if self.loose_path(rel):
            return 'loose'
        for a in reversed(self.archives()):
            if rel in a.files:
                return os.path.basename(a.path)
        return None

    def mesh_list(self):
        """Every .nif in the meshes folder the game can load (archives and loose files), relative to that folder as
        records name them, sorted. Built once."""
        if getattr(self, '_mesh_list', None) is None:
            found = set()
            for a in self.archives():
                found.update(f[7:] for f in a.files if f.startswith('meshes\\') and f.endswith('.nif'))
            if self.view:
                found.update(rel[7:] for rel, _p in self.view.under('meshes') if rel.endswith('.nif'))
            root = os.path.join(self.data_dir, 'meshes')
            for d, _dirs, files in os.walk(root) if not self.view else ():
                for f in files:
                    if f.lower().endswith('.nif'):
                        found.add(bsa.norm(os.path.relpath(os.path.join(d, f), root)))
            self._mesh_list = sorted(found)
        return sorted(self._mesh_list + self.overlay.meshes()) if self.overlay else self._mesh_list

    def read_file(self, rel):
        rel = bsa.norm(rel)
        p = (self.overlay.path(rel) if self.overlay else None) or self.loose_path(rel)
        if p and os.path.isfile(p):
            with open(p, 'rb') as f:
                return f.read()
        for a in reversed(self.archives()):
            if rel in a.files:
                return a.read(rel)
        raise FileNotFoundError(rel)
