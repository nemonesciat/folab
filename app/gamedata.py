"""The game's data as one thing: its Data folder, plugins in load order, archives, and an index of every form.
Read-only."""
import glob
import os
import re
import struct

import bsa
import tes4

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


def _steam_libraries():
    roots = [r'C:\Program Files (x86)\Steam', r'C:\Program Files\Steam']
    out = []
    for root in roots:
        vdf = os.path.join(root, 'steamapps', 'libraryfolders.vdf')
        if os.path.isfile(vdf):
            out.append(root)
            with open(vdf, encoding='utf-8', errors='replace') as f:
                out += [p.replace('\\\\', '\\') for p in re.findall(r'"path"\s+"([^"]+)"', f.read())]
    return list(dict.fromkeys(out))


def find_data_dir():
    """FOLAB_NV_DATA, else the game's Data folder in any Steam library. Never Steam's download folder:
    files held open there stop Steam moving them into place ("disk write error")."""
    env = os.environ.get('FOLAB_NV_DATA')
    if env:
        return env
    for lib in _steam_libraries():
        d = os.path.join(lib, 'steamapps', 'common', 'Fallout New Vegas', 'Data')
        if os.path.isfile(os.path.join(d, 'FalloutNV.esm')):
            return d
    return None


class GameData:
    """Plugins in load order with every form indexed by its load-order form ID (last plugin wins)."""

    def __init__(self, data_dir=None, plugins=None):
        self.data_dir = data_dir or find_data_dir()
        if not self.data_dir:
            raise FileNotFoundError('New Vegas Data folder not found (set FOLAB_NV_DATA)')
        names = plugins or [p for p in OFFICIAL if os.path.isfile(os.path.join(self.data_dir, p))]
        self.plugins = [tes4.PluginFile(os.path.join(self.data_dir, n)) for n in names]
        self.names = [n.lower() for n in names]
        self.forms = {}         # global form ID -> (plugin index, Record)
        self.cell_refs = {}     # global CELL form ID -> {global ref form ID: (plugin index, Record)}
        self.ref_cell = {}      # global ref form ID -> global CELL form ID
        self.interiors = set()
        for i, p in enumerate(self.plugins):
            self._index(i, p)
        self._archives = None

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
            if rec.tag == 'CELL' and path and path[0][1] == 0x4C4C4543 and len(path) >= 2 \
                    and path[1][0] == tes4.G_INT_BLOCK:       # top group 'CELL' (label as int) holds interiors
                self.interiors.add(fid)
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
        return (rec.tag, tes4.zstr(f.get('EDID', b'')), tes4.zstr(f.get('FULL', b'')),
                tes4.zstr(f.get('MODL', b'')) if rec.tag in MODEL_TYPES else '')

    def navmeshes(self, cell):
        return [e for e in self.cell_refs.get(cell, {}).values() if e[1].tag == 'NAVM']

    @staticmethod
    def model_path(btype, model):
        """A base form's MODL as a path under Data: trees are SpeedTree files under trees\\, the rest meshes."""
        return ('trees\\' if btype == 'TREE' else 'meshes\\') + model.lstrip('\\/')

    def refs(self, cell):
        """Every placed thing in a cell (navmeshes apart): dicts with the ref, its base form, position, rotation (radians) and scale."""
        out = []
        for rfid, entry in sorted(self.cell_refs.get(cell, {}).items()):
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
        if self._archives is None:
            found = sorted(glob.glob(os.path.join(self.data_dir, 'Fallout - *.bsa')))
            for n in self.names:
                stem = os.path.splitext(n)[0]
                found += sorted(glob.glob(os.path.join(self.data_dir, stem + ' - *.bsa')))
            found += glob.glob(os.path.join(self.data_dir, 'Update.bsa'))
            self._archives = [bsa.Archive(p) for p in dict.fromkeys(found)]
        return self._archives

    def find_file(self, rel):
        """Where a game file comes from: 'loose', an archive's file name, or None."""
        rel = bsa.norm(rel)
        if os.path.isfile(os.path.join(self.data_dir, rel)):
            return 'loose'
        for a in reversed(self.archives()):
            if rel in a.files:
                return os.path.basename(a.path)
        return None

    def read_file(self, rel):
        rel = bsa.norm(rel)
        p = os.path.join(self.data_dir, rel)
        if os.path.isfile(p):
            with open(p, 'rb') as f:
                return f.read()
        for a in reversed(self.archives()):
            if rel in a.files:
                return a.read(rel)
        raise FileNotFoundError(rel)
