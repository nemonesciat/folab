"""Mod Organizer 2's setups, read, so a loadout can be what the lab works in.

MO2 leaves the game's Data folder alone. Each mod sits in its own folder under mods\\ with what would go in Data; a profile
says which are on and in what priority (modlist.txt, highest first) and which plugins are on (plugins.txt, loadorder.txt).
When it starts the game it lays them over Data in a virtual folder: Data lowest, then the mods by priority, overwrite on top.
A Loadout works out the same picture from the files, so FOLab needn't be started through MO2.

An instance is a folder with ModOrganizer.ini: beside the program when portable, else %LOCALAPPDATA%\\ModOrganizer\\<name>.

Everything here only reads (mo2write.py is what changes MO2). While a loadout is what's loaded (current()), refuse_writes() stops
anything writing to the game: what it wrote would be in the real Data folder and the game's own plugins.txt, which that loadout
doesn't go by."""
import fnmatch
import os
import re

import bsa
import tes4

GAME_NAMES = ('new vegas', 'falloutnv', 'fallout nv', 'fallout: new vegas', 'ttw', 'tale of two wastelands')
PRIMARY = 'falloutnv.esm'
HIDDEN = '.mohidden'
MAX_PLUGINS = 254           # (a form ID's top byte names the file; one is kept for the mod being made)
COMMON = [r'C:\Modding\MO2', r'C:\MO2', r'C:\Mod Organizer 2', r'C:\ModOrganizer', r'C:\Games\MO2', r'C:\Games\Mod Organizer 2',
          r'C:\Program Files\Mod Organizer 2', r'C:\Program Files (x86)\Mod Organizer 2', r'D:\Modding\MO2', r'D:\MO2', r'D:\Mod Organizer 2']

_current = None
_from_mo2 = False


def under_mo2():
    """Did MO2 start this program? Then its virtual folder is hooked into this process, and whatever this starts gets it too."""
    try:
        import ctypes
        get = ctypes.windll.kernel32.GetModuleHandleW
        get.restype = ctypes.c_void_p
        return bool(get('usvfs_x64.dll') or get('usvfs_x86.dll'))
    except (AttributeError, OSError):
        return False


def started_from_mo2():
    return _from_mo2


def _registry_instance():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Mod Organizer Team\Mod Organizer') as k:
            return winreg.QueryValueEx(k, 'CurrentInstance')[0] or ''
    except (ImportError, OSError):
        return ''


def game_list_path():
    return os.path.join(os.environ.get('LOCALAPPDATA', ''), 'FalloutNV', 'plugins.txt')


def _program_folder():
    """The folder of the MO2 that's running. A portable instance is kept beside it."""
    import subprocess
    try:
        out = subprocess.run(['powershell', '-NoProfile', '-Command', '(Get-Process ModOrganizer -ErrorAction SilentlyContinue | Select-Object -First 1).Path'], capture_output=True, text=True,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), timeout=20).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ''
    return os.path.dirname(out) if out else ''


def _profiles_showing(inst, seen):
    """The instance's profiles whose plugin list is what this program sees as the game's."""
    same = []
    for p in inst.profiles():
        try:
            with open(os.path.join(inst.profiles_dir, p, 'plugins.txt'), 'rb') as f:
                if f.read() == seen:
                    same.append(p)
        except OSError:
            continue
    return same


def running_setup(instance_name=None, program_folder=None):
    """(the Loadout MO2 started this in or None, why not). MO2 records the instance it's on by name, and none means the portable one
    beside the program. It shows this program the profile's plugins.txt as the game's own list, so that says which profile (its
    settings file may not have caught up). Never a guess: with no way to tell, None and the reason."""
    name = _registry_instance() if instance_name is None else instance_name
    folder = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'ModOrganizer', name) if name else ''
    if not (folder and os.path.isfile(os.path.join(folder, 'ModOrganizer.ini'))):
        folder = _program_folder() if program_folder is None else program_folder
    try:
        with open(game_list_path(), 'rb') as f:
            seen = f.read()
    except OSError:
        seen = None
    if folder and os.path.isfile(os.path.join(folder, 'ModOrganizer.ini')):
        inst = Instance(folder)
    else:
        found = [i for i in find_instances()[0] if i.is_nv]
        fits = [i for i in found if _profiles_showing(i, seen)] if len(found) > 1 else found
        if len(fits) != 1:
            return None, 'FOLab couldn\'t tell which MO2 instance started it (%d could be). Choose it below.' % len(fits) if fits else 'No MO2 instance for New Vegas was found.'
        inst = fits[0]
    if not inst.is_nv:
        return None, 'MO2 started FOLab in its %s instance, which isn\'t New Vegas.' % (inst.game_name or 'other')
    same = _profiles_showing(inst, seen)
    profile = inst.selected if inst.selected in same or not same else same[0]
    if profile not in inst.profiles():
        return None, 'FOLab couldn\'t tell which profile of "%s" MO2 has on.' % inst.name
    return Loadout(inst, profile), ''


def activate_from_mo2(lo):
    global _from_mo2
    _from_mo2 = True
    activate(lo)


def current():
    return _current


def activate(lo):
    global _current
    _current = lo


def plugin_path(data_dir, name):
    """Where a plugin's file is, as the game would find it. Without a loadout, simply in Data."""
    if _current:
        return _current.plugin_path(name) or os.path.join(_current.data_dir, name)
    return os.path.join(data_dir, name)


def plugin_names(data_dir):
    """Every plugin the game could see."""
    if _current:
        return sorted(_current.plugin_files().values())
    return sorted(fn for fn in os.listdir(data_dir) if fn.lower().endswith(('.esp', '.esm')))


def refuse_writes(what='That'):
    if _current:
        raise ValueError('%s would write to the real game, but you\'re working in the MO2 loadout "%s", which doesn\'t go by those files. '
                         'Put in MO2 adds your mod to this loadout, or you can go back to the plain game on Tools > MO2 loadout.'
                         % (what, _current.title))


# ---------- MO2's files ----------

def _read_text(path):
    try:
        with open(path, 'rb') as f:
            raw = f.read()
    except OSError:
        return []
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = raw.decode('cp1252', 'replace')
    return text.splitlines()


def _value(v):
    """A value as Qt's settings file keeps it."""
    v = v.strip()
    m = re.fullmatch(r'@ByteArray\((.*)\)', v)
    if m:
        v = m.group(1)
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        v = v[1:-1]
    return v.replace('\\\\', '\\').replace('\\"', '"')


def read_ini(path):
    """{section: {key: value}}. Keys keep their case. (Not configparser: % and the 1\\title keys are ordinary here.)"""
    out, sec = {}, 'General'
    for line in _read_text(path):
        s = line.strip()
        if not s or s[0] in ';#':
            continue
        if s[0] == '[' and s[-1] == ']':
            sec = s[1:-1]
        elif '=' in s:
            k, v = s.split('=', 1)
            out.setdefault(sec, {})[k.strip()] = _value(v)
    return out


def is_new_vegas(game_name):
    return (game_name or '').strip().lower() in GAME_NAMES


class Instance:
    def __init__(self, folder):
        self.folder = os.path.abspath(folder)
        self.ini_path = os.path.join(self.folder, 'ModOrganizer.ini')
        if not os.path.isfile(self.ini_path):
            raise FileNotFoundError('There\'s no ModOrganizer.ini in %s.' % self.folder)
        self.ini = read_ini(self.ini_path)
        g, s = self.ini.get('General', {}), self.ini.get('Settings', {})
        self.game_name = g.get('gameName', '')
        self.game_path = os.path.normpath(g['gamePath']) if g.get('gamePath') else ''
        self.selected = g.get('selected_profile', '')
        self.base = self._folder(s.get('base_directory'), self.folder, self.folder)
        self.mods_dir = self._folder(s.get('mod_directory'), os.path.join(self.base, 'mods'), self.base)
        self.profiles_dir = self._folder(s.get('profiles_directory'), os.path.join(self.base, 'profiles'), self.base)
        self.overwrite_dir = self._folder(s.get('overwrite_directory'), os.path.join(self.base, 'overwrite'), self.base)
        self.downloads_dir = self._folder(s.get('download_directory'), os.path.join(self.base, 'downloads'), self.base)
        self.name = os.path.basename(self.folder)
        self.is_nv = is_new_vegas(self.game_name)

    @staticmethod
    def _folder(value, default, base):
        if not value:
            return os.path.normpath(default)
        return os.path.normpath(value.replace('%BASE_DIR%', base))

    @property
    def data_dir(self):
        return os.path.join(self.game_path, 'Data') if self.game_path else ''

    def profiles(self):
        if not os.path.isdir(self.profiles_dir):
            return []
        return sorted(d for d in os.listdir(self.profiles_dir) if os.path.isfile(os.path.join(self.profiles_dir, d, 'modlist.txt')))

    def executables(self):
        """What the instance has set up to run: [{title, binary, arguments}]."""
        sec, out = self.ini.get('customExecutables', {}), []
        for n in range(1, int(sec.get('size', 0) or 0) + 1):
            if sec.get('%d\\binary' % n):
                out.append({'title': sec.get('%d\\title' % n, ''), 'binary': sec['%d\\binary' % n], 'arguments': sec.get('%d\\arguments' % n, '')})
        return out

    def summary(self):
        return {'folder': self.folder, 'name': self.name, 'game': self.game_name, 'game_path': self.game_path, 'new_vegas': self.is_nv,
                'profiles': self.profiles(), 'selected': self.selected, 'mods_dir': self.mods_dir}


def find_instances(extra=()):
    """([Instance], [MO2 programs found]) in the usual places, what MO2's own link handler knows, and the folders given."""
    folders, programs, seen = [], [], set()
    root = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'ModOrganizer')
    if os.path.isdir(root):
        folders += [os.path.join(root, d) for d in sorted(os.listdir(root))]
    known = list(extra) + COMMON
    handler = read_ini(os.path.join(root, 'nxmhandler.ini')).get('handlers', {}) if os.path.isdir(root) else {}
    known += [os.path.dirname(v) for k, v in handler.items() if k.endswith('executable')]
    for d in known:
        folders.append(d)
        if os.path.isfile(os.path.join(d, 'ModOrganizer.exe')):
            programs.append(os.path.normpath(d))
    out = []
    for d in folders:
        key = os.path.normcase(os.path.abspath(d))
        if key in seen or not os.path.isfile(os.path.join(d, 'ModOrganizer.ini')):
            continue
        seen.add(key)
        try:
            out.append(Instance(d))
        except (OSError, ValueError):
            continue
    return out, list(dict.fromkeys(programs))


# ---------- a profile ----------

def read_modlist(path):
    """[{'name', 'on', 'unmanaged'}] as the file has them: highest priority first."""
    out = []
    for line in _read_text(path):
        s = line.strip()
        if not s or s[0] == '#':
            continue
        if s[0] in '+-*':
            out.append({'name': s[1:], 'on': s[0] != '-', 'unmanaged': s[0] == '*'})
    return out


def read_plugin_list(path):
    """Plugin names in the file's order. A line starting * is on in some games' lists; here every line listed counts."""
    return [l.strip().lstrip('*') for l in _read_text(path) if l.strip() and not l.lstrip().startswith('#')]


class Loadout:
    def __init__(self, instance, profile):
        self.instance, self.profile = instance, profile
        self.folder = os.path.join(instance.profiles_dir, profile)
        if not os.path.isfile(os.path.join(self.folder, 'modlist.txt')):
            raise FileNotFoundError('The profile "%s" isn\'t in %s.' % (profile, instance.profiles_dir))
        self.title = '%s: %s' % (instance.name, profile)
        self.data_dir = instance.data_dir
        self.modlist = read_modlist(os.path.join(self.folder, 'modlist.txt'))
        self.active_list = read_plugin_list(os.path.join(self.folder, 'plugins.txt'))
        self.order_list = read_plugin_list(os.path.join(self.folder, 'loadorder.txt'))
        s = read_ini(os.path.join(self.folder, 'settings.ini')).get('General', {})
        self.local_saves = s.get('LocalSaves', 'false').lower() == 'true'
        self.local_settings = s.get('LocalSettings', 'false').lower() == 'true'
        self._index = self._plugins = self._heads = None

    # ----- files, as MO2's virtual folder would show them -----

    def layers(self):
        """(name, folder), lowest priority first: the real Data, the mods that are on, overwrite."""
        out = [('Data folder', self.data_dir)] if self.data_dir else []
        for m in reversed(self.modlist):
            if m['on'] and not m['unmanaged'] and not m['name'].endswith('_separator'):
                out.append((m['name'], os.path.join(self.instance.mods_dir, m['name'])))
        out.append(('Overwrite', self.instance.overwrite_dir))
        return out

    def index(self):
        """{lower path under Data, backslashes: (real file, the layer that wins, [layers it replaces])}. Walked once."""
        if self._index is None:
            found = {}
            for layer, folder in self.layers():
                for d, dirs, files in os.walk(folder):
                    dirs[:] = [x for x in dirs if not x.endswith(HIDDEN)]
                    rel_dir = os.path.relpath(d, folder)
                    for fn in files:
                        if fn.endswith(HIDDEN) or (rel_dir == '.' and fn.lower() == 'meta.ini'):
                            continue
                        rel = bsa.norm(fn if rel_dir == '.' else os.path.join(rel_dir, fn))
                        was = found.get(rel)
                        found[rel] = (os.path.join(d, fn), layer, (was[2] + [was[1]]) if was else [])
            self._index = found
        return self._index

    def path(self, rel):
        hit = self.index().get(bsa.norm(rel))
        return hit[0] if hit else None

    def who(self, rel):
        hit = self.index().get(bsa.norm(rel))
        return hit[1] if hit else None

    def under(self, top):
        """(lower path under Data, real file) for everything in a folder."""
        pre = bsa.norm(top).rstrip('\\') + '\\'
        return [(rel, hit[0]) for rel, hit in self.index().items() if rel.startswith(pre)]

    def archives_like(self, pattern):
        """Real paths of the archives at the top of Data matching a pattern, sorted by name."""
        pat = pattern.lower()
        return [self.index()[r][0] for r in sorted(self.index()) if '\\' not in r and r.endswith('.bsa') and fnmatch.fnmatchcase(r, pat)]

    def plugin_files(self):
        """{lower name: name as spelt}: every plugin in any layer that's on."""
        if self._plugins is None:
            self._plugins = {rel: os.path.basename(hit[0]) for rel, hit in self.index().items()
                             if '\\' not in rel and rel.endswith(('.esp', '.esm'))}
        return self._plugins

    def plugin_path(self, name):
        hit = self.index().get(name.lower())
        return hit[0] if hit else None

    # ----- plugins -----

    def head(self, name):
        """A plugin's header, or {'error': why}."""
        if self._heads is None:
            self._heads = {}
        low = name.lower()
        if low not in self._heads:
            try:
                pf = tes4.PluginFile(self.plugin_path(name))
                try:
                    self._heads[low] = dict(pf.header)
                finally:
                    pf.close()
            except (ValueError, OSError, TypeError) as e:
                self._heads[low] = {'error': str(e)}
        return self._heads[low]

    def order_of(self):
        """{lower name: place}: loadorder.txt, then by the files' dates as the game goes (a new profile has no loadorder.txt, and
        its plugins.txt is only a copy of the game's list, in no order), so every plugin has a place."""
        at = {}
        for n in self.order_list:
            at.setdefault(n.lower(), len(at))

        def dated(name):
            p = self.plugin_path(name)
            return (os.path.getmtime(p) if p else float('inf'), name.lower())
        for n in sorted(set(self.active_list) | set(self.plugin_files().values()), key=dated):
            at.setdefault(n.lower(), len(at))
        return at

    def is_master(self, name):
        return name.lower().endswith('.esm') or bool(self.head(name).get('flags', 0) & 1)

    def active(self):
        """The plugins that are on, in the order the game would load them: its own master first, masters before plugins."""
        on = {n.lower(): n for n in self.active_list}
        if PRIMARY in self.plugin_files():
            on.setdefault(PRIMARY, self.plugin_files()[PRIMARY])
        at = self.order_of()
        return sorted(on.values(), key=lambda n: (n.lower() != PRIMARY, not (self.plugin_path(n) and self.is_master(n)), at[n.lower()]))

    def for_lab(self, skip=None):
        """(paths of what the lab can load, [{'name', 'why'}] left out). A plugin whose masters aren't loaded under it can't be
        read rightly (its links would point at the wrong files), and neither can the ones that need it. skip: the open mod's own
        plugin, already in the profile: the mod's changes stand for it, and what's built on it can't load until it's saved."""
        paths, left, have = [], [], set()
        for n in self.active():
            if skip and n.lower() == skip.lower():
                continue
            p = self.plugin_path(n)
            h = self.head(n) if p else {}
            if not p:
                left.append({'name': n, 'why': 'It\'s on in the profile, but no mod that\'s on has the file.'})
            elif 'error' in h:
                left.append({'name': n, 'why': 'It can\'t be read: %s' % h['error']})
            else:
                missing = [m for m in h['masters'] if m.lower() not in have]
                if missing:
                    left.append({'name': n, 'why': 'It needs %s, which isn\'t loaded before it.' % ', '.join(missing)})
                elif len(paths) >= MAX_PLUGINS:
                    left.append({'name': n, 'why': 'More than %d plugins can\'t be loaded together.' % MAX_PLUGINS})
                else:
                    paths.append(p)
                    have.add(n.lower())
        return paths, left

    # ----- what the page shows -----

    def mods(self):
        """Every mod, highest priority first: on or off, a separator or not, how many files, what it has lost and won."""
        wins, loses = {}, {}
        for hit in self.index().values():
            wins[hit[1]] = wins.get(hit[1], 0) + 1
            for was in hit[2]:
                loses[was] = loses.get(was, 0) + 1
        plugins = {}
        for low, name in self.plugin_files().items():
            plugins.setdefault(self.who(low), []).append(name)
        out = []
        for m in self.modlist:
            folder = os.path.join(self.instance.mods_dir, m['name'])
            sep = m['name'].endswith('_separator')
            row = {'name': m['name'][:-10] if sep else m['name'], 'on': m['on'], 'separator': sep, 'unmanaged': m['unmanaged'], 'missing': not (sep or m['unmanaged'] or os.path.isdir(folder)),
                   'files': wins.get(m['name'], 0), 'overridden': loses.get(m['name'], 0), 'plugins': sorted(plugins.get(m['name'], []))}
            meta = read_ini(os.path.join(folder, 'meta.ini')).get('General', {}) if not (sep or m['unmanaged']) else {}
            row['version'] = meta.get('version', '')
            row['nexus'] = meta.get('modid', '')
            out.append(row)
        return out

    def summary(self):
        paths, left = self.for_lab()
        mods = self.mods()
        real = [m for m in mods if not m['separator'] and not m['unmanaged']]
        notes = []
        if not self.instance.is_nv:
            notes.append('This instance is for %s, not New Vegas.' % (self.instance.game_name or 'another game'))
        if self.data_dir and not os.path.isfile(os.path.join(self.data_dir, 'FalloutNV.esm')):
            notes.append('FalloutNV.esm isn\'t in the game folder this instance names: %s.' % self.data_dir)
        if self.local_saves:
            notes.append('This profile keeps its own saves.')
        if self.local_settings:
            notes.append('This profile keeps its own game settings (its Fallout.ini). FOLab\'s Game page changes the ordinary ones, not these.')
        return {'title': self.title, 'folder': self.instance.folder, 'profile': self.profile, 'data': self.data_dir, 'mods_on': sum(1 for m in real if m['on']), 'mods_all': len(real),
                'plugins_on': len(self.active()), 'plugins_loadable': len(paths), 'left_out': left, 'mods': mods, 'missing_mods': [m['name'] for m in real if m['on'] and m['missing']],
                'files': len(self.index()), 'overrides': sum(1 for h in self.index().values() if h[2]), 'executables': self.instance.executables(), 'notes': notes}
