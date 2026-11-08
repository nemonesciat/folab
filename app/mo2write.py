"""Putting a mod into MO2: the one place FOLab changes MO2's files, and only at the user's asking.

The plugin (and the mod's own files) go in a mod folder of its own, built beside it and swapped in whole, marked as FOLab's in its
meta.ini so that FOLab only ever replaces or removes what it made. The profile's lists get a line each: modlist.txt at the top, which
is highest priority; plugins.txt and, when the profile has one, loadorder.txt at the end, which loads last. A copy of each list goes
to FOLab's backups first.

MO2 rewrites these lists itself when it closes, so they're never changed while it's running. Started from MO2 it's always running:
then Put in MO2 writes only the mod folder, and the user switches it on in MO2 after FOLab closes. Play here may also replace what's
in a mod's folder with MO2 open, as long as the lists already say what's needed: only a file's contents change. Started from MO2,
Play here goes in for one run only (place_inside, below)."""
import hashlib
import os
import shutil
import time

import gametestguard
import install
import loadout

MARK = 'madeByFOLab=true'
LISTS = ('modlist.txt', 'plugins.txt', 'loadorder.txt')
TEST_FOLDER = 'FOLab Test'      # (the mod folder of Play here's own plugin)
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


def _listed(lo, folder_name, plugin, last=False):
    """Do the profile's files, as they are now, have this mod on and this plugin on (and loading last, if that's wanted)?"""
    try:
        mods, _how = _read_lines(os.path.join(lo.folder, 'modlist.txt'))
        plugins, _how = _read_lines(os.path.join(lo.folder, 'plugins.txt'))
    except OSError:
        return False
    names = [l.lstrip('*').strip() for l in plugins if l.strip() and not l.lstrip().startswith('#')]
    return any(l[:1] == '+' and _same_name(l[1:], folder_name) for l in mods) and \
        any(_same_name(n, plugin) for n in (names[-1:] if last else names))


def _set_lists(lo, folder_name, plugin, last=False):
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
            there = [l for l in lines if _same_name(l.lstrip('*'), plugin)]
            if last and there:          # (it builds on what's before it: it can't stay behind something added since)
                lines = [l for l in lines if l not in there]
                _write_lines(path, lines + there[:1], how)
            elif not there:
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


def install_mod(lo, built, mod_name, last=False, may_be_open=False):
    """The saved plugin at built, and the files in '<plugin> assets' beside it, as a mod in this profile: on, and loading last.
    last: and moved to the end if it's on already. may_be_open: MO2 being open is fine if its lists need no change."""
    plugin = os.path.basename(built)
    name = _folder_name(mod_name)
    running = mo2_running()
    from_inside = loadout.started_from_mo2() and running
    needs_none = may_be_open and running and _listed(lo, name, plugin, last)
    lists = not (from_inside or needs_none)
    if lists:
        _refuse_while_running()
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
        _set_lists(lo, name, plugin, last)
    return {'path': os.path.join(folder, plugin), 'mod': name, 'profile': lo.title, 'backups': backups, 'switch_on': from_inside}


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


def clear_test(lo, plugin):
    """Open in game: Play here's plugin mustn't move you. Taken out of the profile, or with MO2 open, emptied till it can be."""
    folder = os.path.join(lo.instance.mods_dir, TEST_FOLDER)
    if not os.path.isdir(folder) or not _is_mine(folder):
        return None
    if mo2_running():
        for fn in os.listdir(folder):
            p = os.path.join(folder, fn)
            if fn.lower() != 'meta.ini':
                shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
        return {'emptied': True}
    return uninstall_mod(lo, plugin, TEST_FOLDER)


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


# ---------- started from MO2: Play here for one run, MO2's lists left as they are ----------
# Started from MO2, FOLab runs inside its virtual folder: what it writes into the game's Data folder lands in MO2's overwrite folder,
# and the game it starts sees it at once. MO2's own lists can't change while it's locked, but the game reads the profile's
# plugins.txt only as it starts. So the files go in for the run (new ones in overwrite, the mod's own folder updated in place), the
# lines plugins.txt lacks are added, and it all comes out again: the lines once the game has read them, the files when FOLab closes,
# Open in game is used, or FOLab next starts. What's put in is kept in a note in FOLab's home, so it comes out even after a cut-off.
# A file the real Data folder or another mod has is never written through: that would change their copy.

INSIDE_NOTE = 'mo2_inside.json'
home = None                 # (FOLab's home, where the note is kept: the server sets it)
RELEASE_AFTER = 90          # (seconds after the game starts: it has read plugins.txt long before)


class _Virtual:
    """The game's Data folder as a program MO2 started sees it. (Tests put a stand-in in its place.)"""

    def exists(self, lo, rel):
        return os.path.exists(os.path.join(lo.data_dir, rel))

    def create(self, lo, rel, src):
        """A new file, through MO2: it must land in overwrite. Its real place."""
        if not loadout.under_mo2():
            raise ValueError('FOLab isn\'t inside MO2\'s virtual folder, so nothing was written.')
        target = os.path.join(lo.data_dir, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copyfile(src, target)
        real = os.path.join(lo.instance.overwrite_dir, rel)
        if not os.path.isfile(real):        # (it went to the real Data folder: take it straight back out)
            os.remove(target)
            raise ValueError('MO2\'s virtual folder didn\'t take FOLab\'s file, so Play here stopped. Close FOLab, open it on its own and use Play here there.')
        return real

    def remove(self, lo, rel, real):
        try:
            if loadout.under_mo2():
                os.remove(os.path.join(lo.data_dir, rel))
        except OSError:
            pass
        if os.path.exists(real):
            os.remove(real)


VIRTUAL = _Virtual()


def _note_path():
    return os.path.join(home or '.', INSIDE_NOTE)


def _read_note():
    import json
    try:
        with open(_note_path(), encoding='utf-8') as f:
            n = json.load(f)
        return {'lines': n.get('lines', []), 'files': n.get('files', [])}
    except (OSError, ValueError, AttributeError):
        return {'lines': [], 'files': []}


def _write_note(n):
    import json
    path = _note_path()
    if not n['lines'] and not n['files']:
        if os.path.exists(path):
            os.remove(path)
        return
    with open(path + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(n, f, indent=1)
    os.replace(path + '.tmp', path)


def place_inside(lo, mod_name, files, plugins):
    """Started from MO2: files [(path under Data, file to copy)] where the game will see them this run, and plugins (names, in the
    order they must load) on in the profile's plugins.txt. {'placed': [paths under Data], 'left_out': [(path, why)], 'lines': [...]}.
    Raises ValueError if a plugin can't go in."""
    clean_inside(lo)
    note = _read_note()
    try:
        name = _folder_name(mod_name) if mod_name else None
    except ValueError:
        name = None
    ours = bool(name) and _is_mine(os.path.join(lo.instance.mods_dir, name))
    placed, left, reals = [], [], {}
    for rel, src in files:
        who = lo.who(rel)
        if who == name and ours:            # (the mod's own folder in MO2: only the file's contents change)
            real = lo.path(rel)
            shutil.copyfile(src, real)
        elif who is None and not VIRTUAL.exists(lo, rel):
            real = VIRTUAL.create(lo, rel, src)
            note['files'].append({'data': lo.data_dir, 'rel': rel, 'real': real, 'sha': _hash(real)})
            _write_note(note)
        else:
            why = 'the game\'s own Data folder has it' if who == 'Data folder' else 'the mod "%s" has it' % who if who else 'MO2 has it already'
            if rel.lower().endswith(('.esp', '.esm')):
                raise ValueError('%s can\'t go in for this run: %s, and FOLab won\'t change another copy. %s' % (
                    rel, why, 'Take it out of the game (My mod), then try again.' if who == 'Data folder' else 'Give your mod another name.'))
            left.append((rel, why))
            continue
        placed.append(rel)
        reals[rel.lower()] = real
    when = time.time()
    for k, p in enumerate(plugins):         # (the game goes by the files' dates: each newer than the one it builds on)
        if p.lower() in reals:
            os.utime(reals[p.lower()], (when + k, when + k))
    path = os.path.join(lo.folder, 'plugins.txt')
    lines, how = _read_lines(path) if os.path.isfile(path) else ([], ('utf-8', '\r\n'))
    there = {l.lstrip('*').strip().lower() for l in lines}
    added = [p for p in plugins if p.lower() not in there]
    if added:
        note['lines'] += [{'file': path, 'line': p} for p in added]
        _write_note(note)
        _write_lines(path, lines + added, how)
    return {'placed': placed, 'left_out': left, 'lines': added}


def release_lines():
    """The lines place_inside added to plugins.txt taken out again (the game has read them), so MO2 never takes them for its own."""
    note = _read_note()
    for row in note['lines']:
        try:
            lines, how = _read_lines(row['file'])
        except OSError:
            continue
        at = [k for k, l in enumerate(lines) if _same_name(l.lstrip('*'), row['line'])]
        if at:
            del lines[at[-1]]
            _write_lines(row['file'], lines, how)
    note['lines'] = []
    _write_note(note)


def clean_inside(lo=None, game_running=False):
    """Everything place_inside put in, out: its lines, and its files unless the game is running (it reads them as it plays). A file
    that's changed since isn't FOLab's to remove. What can't come out yet stays in the note for next time."""
    release_lines()
    if game_running:
        return _read_note()['files']
    note = _read_note()
    kept = []
    for row in note['files']:
        if not os.path.exists(row['real']):
            continue
        if _hash(row['real']) != row['sha']:
            continue
        try:
            VIRTUAL.remove(lo or type('L', (), {'data_dir': row['data']})(), row['rel'], row['real'])
            top = os.path.normcase(os.path.normpath(row['real'][:len(row['real']) - len(row['rel'])]))     # (overwrite itself)
            d = os.path.dirname(row['real'])       # (the folders it needed, if nothing else is in them)
            while os.path.normcase(os.path.normpath(d)) != top and os.path.isdir(d) and not os.listdir(d):
                os.rmdir(d)
                d = os.path.dirname(d)
        except OSError:
            kept.append(row)
    note['files'] = kept
    _write_note(note)
    return kept


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

