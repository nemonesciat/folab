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
nv-rs's own Import (it asks first, never changes the originals).

Other mods go in from a list of folders (a setup, below), as OpenMW's launcher has them."""
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


def all_found(chosen=None):
    """Every nv-rs on this PC: the chosen one first, then the usual places, then any other nv-rs folder beside them
    (C:\\Games\\nv-rs-pad, say). FOLab puts the mod in all of them, so whichever is started plays the same build: on 19
    Nov 2026 nv-rs-pad, started by its own Play.exe, played last night's Waikiki without the wall."""
    out, seen = [], set()

    def add(d):
        if d and is_nvrs(d):
            n = os.path.normcase(os.path.normpath(d))
            if n not in seen:
                seen.add(n)
                out.append(os.path.normpath(d))
    first = find(chosen)
    add(first)
    for d in DEFAULT_PLACES:
        add(d)
    for parent in {os.path.dirname(os.path.normpath(d)) for d in ([first] if first else []) + DEFAULT_PLACES}:
        try:
            for name in sorted(os.listdir(parent)):
                add(os.path.join(parent, name))
        except OSError:
            pass
    return out


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


def _ours(path, row):
    """Still the file FOLab put there? row: its manifest row [name, size, date, (source)]. A link whose source was
    changed in place is still the same file; anything else changed since is yours."""
    if not row:
        return False
    try:
        if _mark(path) == list(row[1:3]):
            return True
        return len(row) > 3 and os.path.samefile(path, row[3])
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


DLC_ORDER = ['DeadMoney.esm', 'HonestHearts.esm', 'OldWorldBlues.esm', 'LonesomeRoad.esm', 'GunRunnersArsenal.esm',
             'ClassicPack.esm', 'MercenaryPack.esm', 'TribalPack.esm', 'CaravanPack.esm']   # (as nv-rs writes them itself)


# ---------- folders of mods, as OpenMW's launcher has them ----------
# A setup (FOLab's setting nvrs_setup) is {'folders': [{'path', 'on'}], lowest first: a later folder's file wins,
# 'plugins': [{'name', 'on'}] in load order, 'from': what it was filled from (an MO2 profile's title) or None}.
# Each folder holds what would go in Data. Play lays the ones that are on in nv-rs's mods folder (links, not copies,
# when on nv-rs's drive), FOLab's own mod on top, and writes a plugins.txt there with the plugins that are on.

TOP_KEEP = ('.esp', '.esm', '.bsa')     # (other files at a folder's top are its readme, MO2's meta.ini and the like)
SKIP_DIRS = {'fomod'}
HIDDEN = '.mohidden'


def clean_setup(setup):
    setup = setup or {}
    folders, seen = [], set()
    for f in setup.get('folders') or []:
        path = os.path.normpath(str(f.get('path') or '').strip().strip('"')) if f.get('path') else ''
        if path and os.path.normcase(path) not in seen:
            seen.add(os.path.normcase(path))
            folders.append({'path': path, 'on': f.get('on', True) is not False})
    plugins, seen = [], set()
    for r in setup.get('plugins') or []:
        name = str(r.get('name') or '').strip()
        if name and name.lower() not in seen:
            seen.add(name.lower())
            plugins.append({'name': name, 'on': r.get('on', True) is not False})
    return {'folders': folders, 'plugins': plugins, 'from': setup.get('from')}


def _on(setup):
    return [f['path'] for f in setup['folders'] if f['on'] and os.path.isdir(f['path'])]


def found_plugins(folders):
    """{lower name: (name, path, folder)}: the plugins at the top of these folders, a later folder's winning."""
    out = {}
    for top in folders:
        try:
            names = os.listdir(top)
        except OSError:
            continue
        for fn in names:
            if fn.lower().endswith(('.esp', '.esm')) and os.path.isfile(os.path.join(top, fn)):
                out[fn.lower()] = (fn, os.path.join(top, fn), top)
    return out


def plugin_rows(setup):
    """Every plugin the folders that are on have, in the setup's order (new ones after, masters first, then by date),
    with what each needs that nothing earlier gives: [{'name', 'on', 'folder', 'needs'}]."""
    setup = clean_setup(setup)
    found = found_plugins(_on(setup))
    rows, seen = [], set()
    for r in setup['plugins']:
        hit = found.get(r['name'].lower())
        if hit and r['name'].lower() not in seen:
            seen.add(r['name'].lower())
            rows.append({'name': hit[0], 'on': r['on'], 'folder': hit[2]})
    rest = [v for k, v in found.items() if k not in seen]
    rest.sort(key=lambda v: (not v[0].lower().endswith('.esm'), os.path.getmtime(v[1]), v[0].lower()))
    rows += [{'name': v[0], 'on': True, 'folder': v[2]} for v in rest]
    have = set(OFFICIAL)
    for r in rows:
        try:
            masters = masters_of(found[r['name'].lower()][1])
        except Exception:
            masters = []
        r['needs'] = [m for m in masters if m.lower() not in have]
        if r['on']:
            have.add(r['name'].lower())
    return rows


def layer_files(folders, off=()):
    """{lower path under Data: (path as spelt, real file)} from these folders, a later folder's winning; plugins in
    off and MO2's hidden files left out."""
    out = {}
    for top in folders:
        for d, dirs, files in os.walk(top):
            at_top = os.path.normcase(d) == os.path.normcase(top)
            dirs[:] = [x for x in dirs if not x.endswith(HIDDEN) and not (at_top and x.lower() in SKIP_DIRS)]
            for fn in files:
                low = fn.lower()
                if low.endswith(HIDDEN) or (at_top and (not low.endswith(TOP_KEEP) or low in off)):
                    continue
                src = os.path.join(d, fn)
                rel = os.path.relpath(src, top)
                out[rel.lower()] = (rel, src)
    return out


def from_mo2(lo):
    """A setup from an MO2 profile (a loadout.Loadout): its mods that are on, lowest priority first, overwrite last,
    and its plugins in its order. Plugins MO2 finds only in the game's own Data folder are listed apart: nv-rs
    plays the game's own plugins, not others put there. ({setup}, [names only in Data])"""
    folders = [{'path': path, 'on': True} for name, path in lo.layers() if name != 'Data folder' and os.path.isdir(path)]
    plugins, data_only = [], []
    for n in lo.active():
        if n.lower() in OFFICIAL:
            continue
        if lo.who(n) == 'Data folder':
            data_only.append(n)
        else:
            plugins.append({'name': n, 'on': True})
    return clean_setup({'folders': folders, 'plugins': plugins, 'from': lo.title}), data_only


def missing_masters(folder, built_plugins, also=()):
    """Masters nv-rs wouldn't have: not the game's own files, not going in with these or the folders' plugins (also),
    not in its mods folder."""
    have = {os.path.basename(b).lower() for b in built_plugins} | {a.lower() for a in also}
    try:
        have |= {f.lower() for f in os.listdir(mods_dir(folder))}
    except OSError:
        pass
    out = []
    for b in built_plugins:
        out += [m for m in masters_of(b) if m.lower() not in OFFICIAL and m.lower() not in have and m not in out]
    return out


def _drive(p):
    return os.path.splitdrive(os.path.abspath(p))[0].lower()


def put_in(folder, built_plugins, setup=None):
    """The setup's folders, then these saved plugins (in load order: the mod, then FOLab Test.esp) with their own files,
    into nv-rs's mods folder, and what FOLab put there before and doesn't now taken out. With plugins on in the
    setup, a plugins.txt there says what loads. {'folder', 'plugins', 'files', 'linked', 'copied', 'backups', 'nvse'}"""
    if os.environ.get('FOLAB_NO_GAME_WRITES'):      # (a scratch FOLab: nv-rs is a real game too)
        raise ValueError('Putting the mod in nv-rs would change a real game, and this FOLab is a scratch copy for looking at '
                         'experiments: it may not. Use your own FOLab for that.')
    setup = clean_setup(setup)
    rows = plugin_rows(setup)
    mine = {os.path.basename(b).lower() for b in built_plugins}     # (the mod's own plugin in a folder too: the saved one wins)
    on = [r['name'] for r in rows if r['on'] and r['name'].lower() not in mine]
    on.sort(key=lambda n: not n.lower().endswith('.esm'))      # (stable: masters load first whatever the list says)
    off = {r['name'].lower() for r in rows if not r['on']}
    missing = missing_masters(folder, built_plugins, on)
    if missing:
        raise ValueError('nv-rs plays the game\'s own files and what is in its mods folder, and your mod needs %s too. '
                         'Add the folder %s is in to nv-rs\'s folders on the Mod page (nv-rs can\'t see Mod '
                         'Organizer\'s mods by itself).' % (', '.join(missing), 'it' if len(missing) == 1 else 'each'))
    mods = mods_dir(folder)
    os.makedirs(mods, exist_ok=True)
    here = _drive(mods)
    old = _read(folder)
    had = old.get('files', {})
    want = layer_files(_on(setup), off)
    for built in built_plugins:
        assets = install._assets_folder(built)
        for d, _dirs, files in os.walk(assets):
            for fn in files:
                src = os.path.join(d, fn)
                rel = os.path.relpath(src, assets)
                if rel.lower() != MANIFEST:
                    want[rel.lower()] = (rel, src)
    for built in built_plugins:
        want.pop(os.path.basename(built).lower(), None)
    now, backed, linked, copied = {}, [], 0, 0
    nvse = sum(1 for k in want if k.startswith('nvse\\'))
    for low, (rel, src) in want.items():
        if low in (MANIFEST, 'plugins.txt'):
            continue
        dest = os.path.join(mods, rel)
        backed.append(_place(src, dest, _drive(src) == here, had.get(low)))
        if os.path.samefile(src, dest):
            linked += 1
        else:
            copied += 1
        now[low] = [rel] + _mark(dest) + [src]
    stamp = time.time()
    for n, built in enumerate(built_plugins):
        plugin = os.path.basename(built)
        dest = os.path.join(mods, plugin)
        backed.append(_place(built, dest, False, had.get(plugin.lower())))
        os.utime(dest, (stamp + 2 * n, stamp + 2 * n))     # (nv-rs orders plugins by date: each after the one before)
        now[plugin.lower()] = [plugin] + _mark(dest)
    names = on + [os.path.basename(b) for b in built_plugins]
    if on:
        needed, found = set(), found_plugins(_on(setup))
        for n in on:
            try:
                needed |= {m.lower() for m in masters_of(found[n.lower()][1])}
            except Exception:
                pass
        for b in built_plugins:
            needed |= {m.lower() for m in masters_of(b)}
        lines = [d for d in DLC_ORDER if d.lower() in needed] + names
        dest = os.path.join(mods, 'plugins.txt')
        if os.path.exists(dest) and not _ours(dest, had.get('plugins.txt')):
            backed.append(install._backup(dest))
        with open(dest, 'w', encoding='utf-8', newline='\r\n') as f:
            f.write('\n'.join(lines) + '\n')
        now['plugins.txt'] = ['plugins.txt'] + _mark(dest)
    for key, row in had.items():
        if key not in now:
            dest = os.path.join(mods, row[0])
            if _ours(dest, row):
                os.remove(dest)
                _prune(os.path.dirname(dest), mods)
    _write(folder, {'plugins': names, 'files': now, 'from': setup.get('from')})
    return {'folder': mods, 'plugins': names, 'files': len(now), 'linked': linked, 'copied': copied,
            'backups': [b for b in backed if b], 'nvse': nvse}


def take_out(folder):
    """Everything FOLab put in nv-rs's mods folder, out again (a file changed since is left alone)."""
    mods = mods_dir(folder)
    left = []
    for row in _read(folder).get('files', {}).values():
        dest = os.path.join(mods, row[0])
        if _ours(dest, row):
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
