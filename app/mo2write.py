"""Putting a mod into MO2: the one place FOLab changes MO2's files, and only at the user's asking.

The plugin (and the mod's own files) go in a mod folder of its own, built beside it and swapped in whole, marked as FOLab's in its
meta.ini so that FOLab only ever replaces or removes what it made. The profile's lists get a line each: modlist.txt at the top, which
is highest priority; plugins.txt and, when the profile has one, loadorder.txt at the end, which loads last. A copy of each list goes
to FOLab's backups first.

MO2 rewrites these lists itself when it closes, so they're never changed while it's running. Started from MO2 it's always running:
then only the mod folder is written, and the user switches it on in MO2 after FOLab closes."""
import hashlib
import os
import shutil
import time

import gametestguard
import install
import loadout

MARK = 'madeByFOLab=true'
LISTS = ('modlist.txt', 'plugins.txt', 'loadorder.txt')
PROGRAM = 'ModOrganizer.exe'


def mo2_running():
    return bool(gametestguard.game_pids(PROGRAM))


def _refuse_while_running():
    if mo2_running():
        raise ValueError('Mod Organizer 2 is open, and it would overwrite this change when it closes. Close MO2, then do this again.')


def _hash(path):
    try:
        with open(path, 'rb') as f:
            return hashlib.sha1(f.read()).hexdigest()
    except OSError:
        return None


def _read_lines(path):
    """(lines, how to write them back): the file's own encoding and line ends are kept."""
    with open(path, 'rb') as f:
        raw = f.read()
    try:
        text, enc = raw.decode('utf-8-sig'), 'utf-8-sig' if raw.startswith(b'\xef\xbb\xbf') else 'utf-8'
    except UnicodeDecodeError:
        text, enc = raw.decode('cp1252', 'replace'), 'cp1252'
    return text.splitlines(), (enc, '\r\n' if b'\r\n' in raw or not raw else '\n')


def _write_lines(path, lines, how):
    enc, end = how
    tmp = path + '.folab-tmp'
    with open(tmp, 'wb') as f:
        f.write((end.join(lines) + end).encode(enc, 'replace'))
    os.replace(tmp, path)


def _is_mine(folder):
    try:
        with open(os.path.join(folder, 'meta.ini'), encoding='utf-8', errors='replace') as f:
            return any(l.strip() == MARK for l in f)
    except OSError:
        return False


def mod_folder(lo, mod_name):
    return os.path.join(lo.instance.mods_dir, _folder_name(mod_name))


def _folder_name(mod_name):
    name = mod_name.strip().rstrip('.')
    if not name or name.endswith('_separator') or any(c in name for c in '<>:"/\\|?*'):
        raise ValueError('"%s" can\'t be the name of a mod folder.' % mod_name)
    return name


def _backup_lists(lo):
    return [b for b in (install._backup(os.path.join(lo.folder, fn)) for fn in LISTS) if b]


def _same_name(a, b):
    return a.strip().lower() == b.lower()


def _set_lists(lo, folder_name, plugin):
    path = os.path.join(lo.folder, 'modlist.txt')
    lines, how = _read_lines(path)
    lines = [l for l in lines if not (l[:1] in ('+', '-') and _same_name(l[1:], folder_name))]
    at = 0
    while at < len(lines) and lines[at].lstrip().startswith('#'):       # (after its heading; the top is highest priority)
        at += 1
    lines.insert(at, '+' + folder_name)
    _write_lines(path, lines, how)
    for fn in ('plugins.txt', 'loadorder.txt'):
        path = os.path.join(lo.folder, fn)
        if os.path.isfile(path):
            lines, how = _read_lines(path)
            if not any(_same_name(l.lstrip('*'), plugin) for l in lines):
                _write_lines(path, lines + [plugin], how)
        elif fn == 'plugins.txt':
            _write_lines(path, [plugin], ('utf-8', '\r\n'))


def _unset_lists(lo, folder_name, plugin):
    path = os.path.join(lo.folder, 'modlist.txt')
    lines, how = _read_lines(path)
    _write_lines(path, [l for l in lines if not (l[:1] in ('+', '-') and _same_name(l[1:], folder_name))], how)
    for fn in ('plugins.txt', 'loadorder.txt'):
        path = os.path.join(lo.folder, fn)
        if os.path.isfile(path):
            lines, how = _read_lines(path)
            _write_lines(path, [l for l in lines if not _same_name(l.lstrip('*'), plugin)], how)


def install_mod(lo, built, mod_name):
    """The saved plugin at built, and the files in '<plugin> assets' beside it, as a mod in this profile: on, and loading last."""
    lists = not (loadout.started_from_mo2() and mo2_running())
    if lists:
        _refuse_while_running()
    plugin = os.path.basename(built)
    name = _folder_name(mod_name)
    folder = os.path.join(lo.instance.mods_dir, name)
    if os.path.exists(folder) and not _is_mine(folder):
        raise ValueError('MO2 already has a mod called "%s" that FOLab didn\'t make, so it\'s left alone. Give your mod another name.' % name)
    who = lo.who(plugin)
    if who and who not in (name, 'Data folder'):        # (a copy in the real Data folder is fine: a mod's beats it, and it's left there)
        raise ValueError('%s already comes from the mod "%s" in this loadout, and FOLab won\'t replace another mod\'s plugin. Give your mod another name.' % (plugin, who))
    backups = _backup_lists(lo) if lists else []
    new = folder + '.folab-new'
    if os.path.exists(new):
        shutil.rmtree(new)
    os.makedirs(new)
    try:
        dest = os.path.join(new, plugin)
        shutil.copyfile(built, dest)
        now = time.time()
        os.utime(dest, (now, now))                  # (newest: where a profile with no loadorder.txt goes by dates, it loads last)
        assets = os.path.splitext(built)[0] + ' assets'
        for d, _dirs, files in os.walk(assets):
            for fn in files:
                src = os.path.join(d, fn)
                to = os.path.join(new, os.path.relpath(src, assets))
                os.makedirs(os.path.dirname(to), exist_ok=True)
                shutil.copyfile(src, to)
        with open(os.path.join(new, 'meta.ini'), 'w', encoding='utf-8', newline='\r\n') as f:
            f.write('[General]\ngameName=New Vegas\nmodid=0\nversion=\ncomments=Made in FOLab\n%s\n' % MARK)
        if os.path.exists(folder):
            shutil.rmtree(folder)
        os.replace(new, folder)
    except OSError:
        shutil.rmtree(new, ignore_errors=True)
        raise
    if lists:
        _set_lists(lo, name, plugin)
    return {'path': os.path.join(folder, plugin), 'mod': name, 'profile': lo.title, 'backups': backups, 'switch_on': not lists}


def uninstall_mod(lo, plugin, mod_name):
    """Take out what install_mod put in. Only a folder FOLab made."""
    _refuse_while_running()
    name = _folder_name(mod_name)
    folder = os.path.join(lo.instance.mods_dir, name)
    if os.path.exists(folder) and not _is_mine(folder):
        raise ValueError('FOLab didn\'t make the mod "%s" in MO2, so it leaves it alone.' % name)
    backups = _backup_lists(lo)
    if os.path.isfile(os.path.join(folder, plugin)):
        backups.append(install._backup(os.path.join(folder, plugin)))
    _unset_lists(lo, name, plugin)
    if os.path.exists(folder):
        shutil.rmtree(folder)
    return {'mod': name, 'profile': lo.title, 'backups': [b for b in backups if b]}


def in_run_list(instance, exe):
    want = os.path.normcase(os.path.normpath(exe))
    return any(os.path.normcase(os.path.normpath(e['binary'])) == want for e in instance.executables())


def add_to_run_list(instance, exe):
    """FOLab in the list of programs beside MO2's Run button, so it starts inside MO2's virtual folder. A copy of the settings first."""
    _refuse_while_running()
    if in_run_list(instance, exe):
        return {'added': False, 'backups': []}
    lines, how = _read_lines(instance.ini_path)
    sec = instance.ini.get('customExecutables', {})
    old = next((k.split('\\')[0] for k, v in sec.items() if k.endswith('\\title') and v == 'FOLab' and sec.get(k.split('\\')[0] + '\\binary', '').lower().endswith('folab.exe')), None)
    if old:                                     # (FOLab was moved: the same entry, the new place)
        folder = os.path.dirname(exe).replace('\\', '/')
        backups = [install._backup(instance.ini_path)]
        for n, l in enumerate(lines):
            if l.startswith(old + '\\binary='):
                lines[n] = '%s\\binary=%s' % (old, exe.replace('\\', '/'))
            elif l.startswith(old + '\\workingDirectory='):
                lines[n] = '%s\\workingDirectory=%s' % (old, folder)
        _write_lines(instance.ini_path, lines, how)
        return {'added': True, 'moved': True, 'backups': backups}
    at = next((i for i, l in enumerate(lines) if l.strip() == '[customExecutables]'), None)
    if at is None:
        lines += ['', '[customExecutables]', 'size=0']
        at = len(lines) - 2
    size_at = next((i for i in range(at + 1, len(lines)) if lines[i].startswith('size=')), None)
    if size_at is None:
        size_at = at + 1
        lines.insert(size_at, 'size=0')
    n = int(lines[size_at][5:] or 0) + 1
    end = at + 1
    while end < len(lines) and not lines[end].startswith('['):
        end += 1
    while end > at + 1 and not lines[end - 1].strip():
        end -= 1
    folder = os.path.dirname(exe).replace('\\', '/')
    new = ['%d\\arguments=' % n, '%d\\binary=%s' % (n, exe.replace('\\', '/')), '%d\\hide=false' % n, '%d\\ownicon=true' % n, '%d\\steamAppID=' % n,
           '%d\\title=FOLab' % n, '%d\\toolbar=false' % n, '%d\\workingDirectory=%s' % (n, folder)]
    backups = [install._backup(instance.ini_path)]
    lines[size_at] = 'size=%d' % n
    lines[end:end] = new
    _write_lines(instance.ini_path, lines, how)
    return {'added': True, 'backups': backups}


def status(lo, built, mod_name):
    """The same answers as install.status, about this profile."""
    plugin = os.path.basename(built)
    try:
        folder = mod_folder(lo, mod_name)
    except ValueError:
        return {'installed': False, 'active': False, 'current': False, 'mo2': True}
    there = os.path.join(folder, plugin)
    on = any(m['on'] and m['name'].lower() == os.path.basename(folder).lower() for m in lo.modlist) and any(n.lower() == plugin.lower() for n in lo.active_list)
    return {'installed': os.path.isfile(there), 'active': on, 'current': os.path.isfile(there) and _hash(there) == _hash(built), 'mo2': True, 'plugins_txt': os.path.join(lo.folder, 'plugins.txt')}

