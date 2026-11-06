"""Putting a saved plugin into the game, at the user's request, and taking it out again.

The game loads the plugins listed in %LOCALAPPDATA%\\FalloutNV\\plugins.txt, in the order of the files' modified
times. Install copies the plugin into Data (stamped newest, so it loads last and wins), adds its line, and keeps a
copy of plugins.txt and of any file it replaces in FOLab's backups folder first. The mod's own files (meshes and
textures, library.py), kept beside the plugin in "<plugin> assets", go into Data with it; what was put in is listed in
"<plugin>.files.json" beside the plugin, so taking it out removes exactly those."""
import hashlib
import json
import os
import shutil
import time

import project

BACKUPS = os.path.join(project.HOME, 'backups')


def plugins_txt():
    return os.path.join(os.environ.get('LOCALAPPDATA', ''), 'FalloutNV', 'plugins.txt')


def _lines():
    try:
        with open(plugins_txt(), encoding='cp1252', errors='replace') as f:
            return f.read().splitlines()
    except OSError:
        return []


def _hash(path):
    try:
        with open(path, 'rb') as f:
            return hashlib.sha1(f.read()).hexdigest()
    except OSError:
        return None


_kept = {}


def _hash_kept(path):
    """A file's hash, read again only when it has changed (the page asks after every edit)."""
    try:
        st = os.stat(path)
    except OSError:
        return None
    k = (path, st.st_size, st.st_mtime_ns)
    if k not in _kept:
        if len(_kept) > 5000:
            _kept.clear()
        _kept[k] = _hash(path)
    return _kept[k]


def _backup(path):
    if os.path.exists(path):
        os.makedirs(BACKUPS, exist_ok=True)
        stamp, n = time.strftime('%Y-%m-%d %H%M%S'), 1
        dest = os.path.join(BACKUPS, '%s %s' % (stamp, os.path.basename(path)))
        while os.path.exists(dest):                 # (several in the same second, of the same name)
            n += 1
            dest = os.path.join(BACKUPS, '%s %d %s' % (stamp, n, os.path.basename(path)))
        shutil.copy2(path, dest)
        return dest


def _assets_folder(built):
    return os.path.splitext(built)[0] + ' assets'


def _files_list(built):
    return built + '.files.json'


def _read_files_list(built):
    try:
        with open(_files_list(built), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _put_assets(data_dir, built):
    """The mod's files into Data, beside whatever's there (a copy of anything replaced goes to backups). Those the last
    Put in game left that the mod no longer has are taken out."""
    folder, backed = _assets_folder(built), []
    had = _read_files_list(built)
    now = {}
    for d, _dirs, files in os.walk(folder):
        for fn in files:
            src = os.path.join(d, fn)
            rel = os.path.relpath(src, folder)
            dest = os.path.join(data_dir, rel)
            h = _hash(src)
            if os.path.exists(dest) and _hash(dest) != h and _hash(dest) != had.get(rel.lower()):
                backed.append(_backup(dest))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(src, dest)
            now[rel.lower()] = h
    for rel, h in had.items():
        dest = os.path.join(data_dir, rel)
        if rel not in now and _hash(dest) == h:
            os.remove(dest)
    if now or had:
        with open(_files_list(built), 'w', encoding='utf-8') as f:
            json.dump(now, f, indent=1)
    return backed


def _take_assets(data_dir, built):
    """What Put in game put in, out again (a file changed since is left alone)."""
    backed = []
    for rel, h in _read_files_list(built).items():
        dest = os.path.join(data_dir, rel)
        if _hash(dest) == h:
            backed.append(_backup(dest))
            os.remove(dest)
    if os.path.exists(_files_list(built)):
        os.remove(_files_list(built))
    return backed


def status(data_dir, plugin):
    """{'installed': in Data, 'active': listed in plugins.txt, 'current': Data's copy matches the last save}"""
    dest = os.path.join(data_dir, plugin)
    built = os.path.join(project.BUILD_DIR, plugin)
    there = os.path.isfile(dest)
    files = [os.path.relpath(os.path.join(d, fn), _assets_folder(built)) for d, _s, fs in os.walk(_assets_folder(built)) for fn in fs]
    listed = _read_files_list(built)
    return {'installed': there, 'active': any(l.strip().lower() == plugin.lower() for l in _lines()),
            'current': there and _hash(dest) == _hash(built) and all(listed.get(r.lower()) and listed[r.lower()] == _hash_kept(os.path.join(_assets_folder(built), r)) for r in files),
            'plugins_txt': plugins_txt()}


def install(data_dir, built):
    plugin = os.path.basename(built)
    dest = os.path.join(data_dir, plugin)
    backed = []
    if os.path.exists(dest) and _hash(dest) != _hash(built):
        backed.append(_backup(dest))
    shutil.copyfile(built, dest)
    now = time.time()
    os.utime(dest, (now, now))
    lines = _lines()
    if not any(l.strip().lower() == plugin.lower() for l in lines):
        os.makedirs(os.path.dirname(plugins_txt()), exist_ok=True)
        b = _backup(plugins_txt())
        if b:
            backed.append(b)
        with open(plugins_txt(), 'w', encoding='cp1252', newline='\r\n') as f:
            f.write('\n'.join([l for l in lines if l.strip()] + [plugin]) + '\n')
    backed += _put_assets(data_dir, built)
    return {'path': dest, 'backups': [b for b in backed if b]}


def uninstall(data_dir, plugin):
    """Take the plugin out of plugins.txt and Data (a copy goes to backups first)."""
    lines = _lines()
    keep = [l for l in lines if l.strip().lower() != plugin.lower()]
    backed = []
    if len(keep) != len(lines):
        backed.append(_backup(plugins_txt()))
        with open(plugins_txt(), 'w', encoding='cp1252', newline='\r\n') as f:
            f.write('\n'.join(keep) + '\n')
    dest = os.path.join(data_dir, plugin)
    if os.path.exists(dest):
        backed.append(_backup(dest))
        os.remove(dest)
    backed += _take_assets(data_dir, os.path.join(project.BUILD_DIR, plugin))
    return {'backups': [b for b in backed if b]}
