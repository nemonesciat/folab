"""Putting a saved plugin into the game, at the user's request, and taking it out again.

The game loads the plugins listed in %LOCALAPPDATA%\\FalloutNV\\plugins.txt, in the order of the files' modified
times. Install copies the plugin into Data (stamped newest, so it loads last and wins), adds its line, and keeps a
copy of plugins.txt and of any file it replaces in FOLab's backups folder first."""
import hashlib
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


def _backup(path):
    if os.path.exists(path):
        os.makedirs(BACKUPS, exist_ok=True)
        dest = os.path.join(BACKUPS, '%s %s' % (time.strftime('%Y-%m-%d %H%M%S'), os.path.basename(path)))
        shutil.copy2(path, dest)
        return dest


def status(data_dir, plugin):
    """{'installed': in Data, 'active': listed in plugins.txt, 'current': Data's copy matches the last save}"""
    dest = os.path.join(data_dir, plugin)
    built = os.path.join(project.BUILD_DIR, plugin)
    there = os.path.isfile(dest)
    return {'installed': there, 'active': any(l.strip().lower() == plugin.lower() for l in _lines()),
            'current': there and _hash(dest) == _hash(built), 'plugins_txt': plugins_txt()}


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
    return {'backups': [b for b in backed if b]}
