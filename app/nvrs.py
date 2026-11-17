"""nv-rs (github.com/slaterain/nv-rs): New Vegas run on the game's own code translated to Rust, as the other way to
play a mod.

nv-rs is a folder of its own (Play.exe, app\\FalloutNV.exe, mods, userdata) that runs the player's installed game and
never writes to it. "Play with mods" (Play.exe --mods) builds a game folder of its own each start, in
userdata\\modgame: the game's files linked, with the mods folder's files on top. The plugins on are the DLC a mod
needs, then the mods' .esm, then their .esp, ordered by file date (or by a plugins.txt in the mods folder).

So playing a mod there means putting its plugin and its own files in that mods folder and starting Play.exe --mods.
What FOLab put there is listed in mods\\folab.json, so it takes out exactly those and never another file of yours;
a file of yours it would replace is copied to FOLab's backups first. The mod's own files go in as links when nv-rs is
on the same drive as FOLab (nv-rs only reads them), else as copies; plugins always as copies, dated so FOLab Test.esp
loads after the mod.

What nv-rs can't do yet: anything needing xNVSE or JIP (FOLab's loading of your newest save at the menu among them),
so you load a save yourself. Saves made with mods stay in nv-rs's userdata\\mods; import_saves copies yours there with
nv-rs's own Import (it asks first, never changes the originals)."""
import json
import os
import shutil
import time

import install
import playtest

MANIFEST = 'folab.json'
DEFAULT_PLACES = [r'C:\Games\nv-rs', os.path.join(os.path.expanduser('~'), 'Games', 'nv-rs')]


def is_nvrs(folder):
    return bool(folder) and os.path.isfile(os.path.join(folder, 'Play.exe')) and \
        os.path.isfile(os.path.join(folder, 'app', 'FalloutNV.exe'))


def find(chosen=None):
    """The nv-rs folder: the one chosen in FOLab's settings, else one in the usual places. None if there's none."""
    for d in ([chosen] if chosen else []) + DEFAULT_PLACES:
        if is_nvrs(d):
            return os.path.normpath(d)
    return None


def version(folder):
    """The first line of its BUILD.txt ('nv-rs Windows preview 2026-11-07.2'), or None."""
    try:
        with open(os.path.join(folder, 'BUILD.txt'), encoding='utf-8', errors='replace') as f:
            return f.readline().strip() or None
    except OSError:
        return None


def mods_dir(folder):
    return os.path.join(folder, 'mods')


def saves_dir(folder):
    """Where nv-rs keeps the saves of its Play with mods."""
    return os.path.join(folder, 'userdata', 'mods', 'Documents', 'My Games', 'FalloutNV', 'Saves')


def status(chosen, data_dir):
    folder = find(chosen)
    if not folder:
        return {'found': False, 'places': DEFAULT_PLACES}
    game_drive = os.path.splitdrive(os.path.abspath(data_dir or ''))[0].lower()
    try:
        saves = sum(1 for f in os.listdir(saves_dir(folder)) if f.lower().endswith('.fos'))
    except OSError:
        saves = 0
    return {'found': True, 'folder': folder, 'version': version(folder), 'saves': saves,
            'same_drive': os.path.splitdrive(folder)[0].lower() == game_drive,
            'mine': sorted(_read(folder).get('plugins', []))}


def _read(folder):
    try:
        with open(os.path.join(mods_dir(folder), MANIFEST), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _write(folder, m):
    with open(os.path.join(mods_dir(folder), MANIFEST), 'w', encoding='utf-8') as f:
        json.dump(m, f, indent=1)


def _mark(path):
    st = os.stat(path)
    return [st.st_size, st.st_mtime_ns]


def _ours(path, mark):
    """Still the file FOLab put there? (size and date as left; a file you changed since is yours)"""
    try:
        return _mark(path) == mark
    except OSError:
        return False


def _place(src, dest, link, had):
    """src at dest: kept as it is when it's already that file, else a link or a copy; a file of yours there goes to backups."""
    backed = None
    if os.path.exists(dest):
        try:
            if os.path.samefile(src, dest):
                return None
        except OSError:
            pass
        if not _ours(dest, had):
            backed = install._backup(dest)
        os.remove(dest)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if link:
        try:
            os.link(src, dest)
            return backed
        except OSError:
            pass
    shutil.copy2(src, dest)
    return backed


OFFICIAL = {'falloutnv.esm', 'deadmoney.esm', 'honesthearts.esm', 'oldworldblues.esm', 'lonesomeroad.esm',
            'gunrunnersarsenal.esm', 'classicpack.esm', 'mercenarypack.esm', 'tribalpack.esm', 'caravanpack.esm'}


def masters_of(path):
    import tes4
    p = tes4.PluginFile(path)
    try:
        return [tes4.zstr(d) for t, d in tes4.iter_subrecords(p.data(p.record_at(0))) if t == 'MAST']
    finally:
        p.close()


def missing_masters(folder, built_plugins):
    """Masters nv-rs wouldn't have: not the game's own files, not going in with these, not in its mods folder."""
    have = {os.path.basename(b).lower() for b in built_plugins}
    try:
        have |= {f.lower() for f in os.listdir(mods_dir(folder))}
    except OSError:
        pass
    out = []
    for b in built_plugins:
        out += [m for m in masters_of(b) if m.lower() not in OFFICIAL and m.lower() not in have and m not in out]
    return out


def put_in(folder, built_plugins):
    """These saved plugins (in load order: the mod, then FOLab Test.esp) with their own files into nv-rs's mods folder,
    and what FOLab put there before and doesn't now taken out. {'folder', 'plugins', 'files', 'backups'}"""
    missing = missing_masters(folder, built_plugins)
    if missing:
        raise ValueError('nv-rs plays the game\'s own files and what is in its mods folder, and your mod needs %s too. '
                         'Put %s in %s first (nv-rs can\'t see Mod Organizer\'s mods).' % (
                             ', '.join(missing), 'it' if len(missing) == 1 else 'them', mods_dir(folder)))
    mods = mods_dir(folder)
    os.makedirs(mods, exist_ok=True)
    old = _read(folder)
    had = old.get('files', {})
    now, backed = {}, []
    link = os.path.splitdrive(os.path.abspath(folder))[0].lower() == \
        os.path.splitdrive(os.path.abspath(built_plugins[0]))[0].lower() if built_plugins else False
    stamp = time.time()
    for n, built in enumerate(built_plugins):
        plugin = os.path.basename(built)
        dest = os.path.join(mods, plugin)
        backed.append(_place(built, dest, False, (had.get(plugin.lower()) or [None])[1:]))
        os.utime(dest, (stamp + 2 * n, stamp + 2 * n))     # (nv-rs orders plugins by date: each after the one before)
        now[plugin.lower()] = [plugin] + _mark(dest)
        assets = install._assets_folder(built)
        for d, _dirs, files in os.walk(assets):
            for fn in files:
                src = os.path.join(d, fn)
                rel = os.path.relpath(src, assets)
                if rel.lower() == MANIFEST:
                    continue
                dest = os.path.join(mods, rel)
                backed.append(_place(src, dest, link, (had.get(rel.lower()) or [None])[1:]))
                now[rel.lower()] = [rel] + _mark(dest)
    for key, row in had.items():
        if key not in now:
            dest = os.path.join(mods, row[0])
            if _ours(dest, row[1:]):
                os.remove(dest)
                _prune(os.path.dirname(dest), mods)
    _write(folder, {'plugins': [os.path.basename(b) for b in built_plugins], 'files': now})
    return {'folder': mods, 'plugins': [os.path.basename(b) for b in built_plugins], 'files': len(now),
            'backups': [b for b in backed if b]}


def take_out(folder):
    """Everything FOLab put in nv-rs's mods folder, out again (a file changed since is left alone)."""
    mods = mods_dir(folder)
    left = []
    for row in _read(folder).get('files', {}).values():
        dest = os.path.join(mods, row[0])
        if _ours(dest, row[1:]):
            os.remove(dest)
            _prune(os.path.dirname(dest), mods)
        elif os.path.exists(dest):
            left.append(row[0])
    if os.path.exists(os.path.join(mods, MANIFEST)):
        os.remove(os.path.join(mods, MANIFEST))
    return {'left': left}


def _prune(d, top):
    """Empty folders FOLab's files leave behind, up to the mods folder."""
    top = os.path.normcase(os.path.abspath(top))
    while os.path.normcase(os.path.abspath(d)).startswith(top + os.sep):
        try:
            os.rmdir(d)
        except OSError:
            return
        d = os.path.dirname(d)


def launch(folder):
    """Start nv-rs's Play with mods. (Through playtest._start, which tests replace: nothing there may start a game.)"""
    playtest._start([os.path.join(folder, 'Play.exe'), '--mods'])
    return 'nv-rs'


def import_saves(folder):
    """nv-rs's own Import my saves, into its Play with mods: it asks first, copies, and leaves your saves as they are."""
    playtest._start([os.path.join(folder, 'Play.exe'), '--mods', '--import-saves'])
