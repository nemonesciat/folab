"""Keeping the user's game as it was while the game test runs: the start and restore layer.

Everything takes its folders as arguments (a Paths), so all of this is tested on fake folders. It knows nothing of
checkers or reports. A run goes:

    before = fingerprint(paths)          every save, the INIs, plugins.txt, the dates of the plugins in Data
    s = Session.begin(paths, ...)        a journal on disk first, then each change noted in it BEFORE it's made
    s.put_file / s.set_plugins / s.set_ini
    supervise(...)                       the time cap, the silent-file stop, the live checks
    s.restore()                          in a finally; and recover() on the next start if FOLab died in between

The journal is what makes a crash safe: whatever had been done when FOLab died is listed, with the copy of what it
replaced, and restore() puts back exactly that, however far it got, as many times as it's asked. What it never does:
touch a save, delete a file it didn't put there, or stop a process it didn't start."""
import hashlib
import json
import os
import shutil
import stat
import subprocess
import time

JOURNAL = 'journal.json'
INI_FILES = ('Fallout.ini', 'FalloutPrefs.ini')
TEST_SAVES = 'FOLabGameTest'                # (a folder beside the user's Saves, as sLocalSavePath names it)
GAME_EXE = 'FalloutNV.exe'


class Refused(Exception):
    """Why a run won't start, in words for the page."""


class Paths:
    """Where everything is. work: FOLab's own folder for this (journal and copies), never in the game's."""

    def __init__(self, data_dir, ini_dir, plugins_txt, work):
        self.data_dir, self.ini_dir, self.plugins_txt, self.work = data_dir, ini_dir, plugins_txt, work

    @property
    def game_dir(self):
        return os.path.dirname(os.path.normpath(self.data_dir))

    def saves(self):
        """The user's own saves folder, as the INIs have it now (read before anything is changed)."""
        name = 'Saves\\'
        for fn in INI_FILES:
            v = ini_value(os.path.join(self.ini_dir, fn), 'General', 'sLocalSavePath')
            if v:
                name = v
        return os.path.join(self.ini_dir, name.strip().strip('\\/'))


# ---------- INI files, line by line ----------

def read_ini_lines(path):
    with open(path, encoding='cp1252', errors='surrogateescape', newline='') as f:
        return f.read().splitlines()


def ini_value(path, section, key):
    try:
        lines = read_ini_lines(path)
    except OSError:
        return None
    sec, found = '', None
    for line in lines:
        s = line.strip()
        if s.startswith('[') and s.endswith(']'):
            sec = s[1:-1]
        elif '=' in s and not s.startswith((';', '#')):
            k, v = s.split('=', 1)
            if sec.lower() == section.lower() and k.strip().lower() == key.lower():
                found = v.strip()
    return found


def edit_ini_lines(lines, changes, add=False):
    """changes: {(section, key): value}. Returns (new lines, the changes this file had a line for). With add, the ones
    it hadn't go in too, under their section, made if it must be."""
    want = {(s.lower(), k.lower()): (s, k, str(v)) for (s, k), v in changes.items()}
    out, sec, placed = list(lines), '', set()
    for n, line in enumerate(out):
        s = line.strip()
        if s.startswith('[') and s.endswith(']'):
            sec = s[1:-1]
        elif '=' in s and not s.startswith((';', '#')):
            k = s.split('=', 1)[0].strip()
            hit = want.get((sec.lower(), k.lower()))
            if hit:
                out[n] = '%s=%s' % (k, hit[2])
                placed.add((sec.lower(), k.lower()))
    if add:
        for low, (s, k, v) in want.items():
            if low in placed:
                continue
            at = next((n for n, l in enumerate(out) if l.strip().lower() == '[%s]' % s.lower()), None)
            if at is None:
                out += ['[%s]' % s, '%s=%s' % (k, v)]
            else:
                out.insert(at + 1, '%s=%s' % (k, v))
    return out, placed


# ---------- fingerprints ----------

def _sha1(path):
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def _mark(path, full=True):
    st = os.stat(path)
    return [st.st_size, st.st_mtime_ns, _sha1(path) if full else None]


def fingerprint(paths, full=True, saves_dir=None):
    """{name: [size, date, hash]}: every file in the user's saves folder, the INIs, plugins.txt, and (size and date only:
    the game's files are big and read-only to it) the plugins in Data. full=False leaves out hashes: the quick look a
    run takes every few seconds. saves_dir: the saves folder, during a run (the INIs name the test one by then)."""
    out = {}
    saves = saves_dir or paths.saves()
    if os.path.isdir(saves):
        for fn in sorted(os.listdir(saves)):
            p = os.path.join(saves, fn)
            if os.path.isfile(p):
                out['saves/' + fn] = _mark(p, full)
    for fn in INI_FILES:
        p = os.path.join(paths.ini_dir, fn)
        if os.path.isfile(p):
            out['ini/' + fn] = _mark(p, full)
    if os.path.isfile(paths.plugins_txt):
        out['plugins.txt'] = _mark(paths.plugins_txt, full)
    if os.path.isdir(paths.data_dir):
        for fn in sorted(os.listdir(paths.data_dir)):
            if fn.lower().endswith(('.esp', '.esm')):
                p = os.path.join(paths.data_dir, fn)
                if os.path.isfile(p):
                    out['data/' + fn] = _mark(p, False)
    return out


def differences(before, after, only=None):
    """What's not as it was: [{'file', 'how': changed | added | gone}]. only: name prefixes to look at. A hash is
    only compared where both have one."""
    rows = []
    for name in sorted(set(before) | set(after)):
        if only and not name.startswith(tuple(only)):
            continue
        a, b = before.get(name), after.get(name)
        if a is None:
            rows.append({'file': name, 'how': 'added'})
        elif b is None:
            rows.append({'file': name, 'how': 'gone'})
        elif a[0] != b[0] or a[1] != b[1] or (a[2] and b[2] and a[2] != b[2]):
            rows.append({'file': name, 'how': 'changed'})
    return rows


# ---------- is the game running: only what we started is ever stopped ----------

def game_pids(exe=GAME_EXE):
    """The process IDs of every running game. Only reads."""
    try:
        out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq ' + exe, '/NH', '/FO', 'CSV'], capture_output=True, text=True,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    pids = []
    for line in out.splitlines():
        parts = [x.strip('"') for x in line.split('","')]
        if len(parts) >= 2 and parts[0].lower() == exe.lower() and parts[1].isdigit():
            pids.append(int(parts[1]))
    return pids


def pid_alive(pid):
    """Is that process there? (any program: ask game_pids when it matters that it's the game)"""
    if not pid:
        return False
    try:
        out = subprocess.run(['tasklist', '/FI', 'PID eq %d' % pid, '/NH', '/FO', 'CSV'], capture_output=True, text=True,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return ('"%d"' % pid) in out


def stop_pid(pid, wait=15):
    """Ask that one process to close, then end it. By number only, and never its neighbours (no /T)."""
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    subprocess.run(['taskkill', '/PID', str(pid)], capture_output=True, creationflags=flags, timeout=30)
    end = time.time() + wait
    while time.time() < end and pid_alive(pid):
        time.sleep(0.5)
    if pid_alive(pid):
        subprocess.run(['taskkill', '/F', '/PID', str(pid)], capture_output=True, creationflags=flags, timeout=30)


# ---------- the session: every change journalled first ----------

def _write_json(path, data):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, path)


def journal_path(work):
    return os.path.join(work, JOURNAL)


def _copy_over(src, dst):
    """A file back as it was: bytes, date, and read-only if it was."""
    if os.path.exists(dst):
        os.chmod(dst, stat.S_IWRITE | stat.S_IREAD)
    shutil.copy2(src, dst)


class Session:
    def __init__(self, paths, j):
        self.paths, self.j = paths, j

    @classmethod
    def begin(cls, paths, run_id, before, note=''):
        """A journal, on disk before anything is changed. Refuses when one is still there: that run isn't put back."""
        os.makedirs(paths.work, exist_ok=True)
        jp = journal_path(paths.work)
        if os.path.exists(jp):
            raise Refused('An earlier test run hasn\'t been put back yet.')
        keep = os.path.join(paths.work, 'kept', run_id)
        os.makedirs(keep, exist_ok=True)
        j = {'run': run_id, 'started': time.time(), 'note': note, 'keep': keep, 'files': [], 'dirs': [], 'before': before,
             'paths': {'data_dir': paths.data_dir, 'ini_dir': paths.ini_dir, 'plugins_txt': paths.plugins_txt, 'work': paths.work},
             'pid': None, 'loader_pid': None, 'saved_ok': False}
        _write_json(jp, j)
        return cls(paths, j)

    @classmethod
    def load(cls, work):
        with open(journal_path(work), encoding='utf-8') as f:
            j = json.load(f)
        p = j['paths']
        return cls(Paths(p['data_dir'], p['ini_dir'], p['plugins_txt'], work), j)

    def _save(self):
        _write_json(journal_path(self.paths.work), self.j)

    def set_pid(self, pid):
        self.j['pid'] = pid
        self._save()

    def _note_dirs(self, folder):
        """Note each folder that isn't there yet, top first, so it's taken away again only if we made it."""
        missing = []
        d = os.path.normpath(folder)
        while not os.path.exists(d):
            missing.append(d)
            up = os.path.dirname(d)
            if up == d:
                break
            d = up
        for d in reversed(missing):
            if d not in self.j['dirs']:
                self.j['dirs'].append(d)

    def note_file(self, dst):
        """A file the game or the run will make here: noted first, with a copy of what's there now, and taken away (or
        put back) on restore."""
        dst = os.path.normpath(dst)
        if any(e['dst'] == dst for e in self.j['files']):
            return
        self._note_dirs(os.path.dirname(dst))
        entry = {'dst': dst, 'kept': None, 'ro': False}
        if os.path.exists(dst):
            entry['kept'] = os.path.join(self.j['keep'], '%04d %s' % (len(self.j['files']), os.path.basename(dst)))
            shutil.copy2(dst, entry['kept'])
            entry['ro'] = not os.access(dst, os.W_OK)
            os.chmod(entry['kept'], stat.S_IWRITE | stat.S_IREAD)       # (or the copy couldn't be cleared away later)
        self.j['files'].append(entry)
        self._save()

    def put_file(self, src, dst, when=None):
        """Copy a file in (or set its contents, if src is bytes). when: its date, for a plugin's place in the load order."""
        self.note_file(dst)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if isinstance(src, (bytes, bytearray)):
            if os.path.exists(dst):
                os.chmod(dst, stat.S_IWRITE | stat.S_IREAD)
            with open(dst, 'wb') as f:
                f.write(src)
        else:
            _copy_over(src, dst)
        if when:
            os.utime(dst, (when, when))

    def set_plugins(self, names):
        """plugins.txt lists only these, for this run."""
        self.note_file(self.paths.plugins_txt)
        os.makedirs(os.path.dirname(self.paths.plugins_txt), exist_ok=True)
        with open(self.paths.plugins_txt, 'w', encoding='cp1252', errors='replace', newline='\r\n') as f:
            f.write('# FOLab game test: FOLab puts your own list back when the run ends.\n' + '\n'.join(names) + '\n')

    def set_ini(self, changes):
        """Set each value in every INI that has it; what neither has goes in the last. A read-only file stays read-only."""
        have = [fn for fn in INI_FILES if os.path.isfile(os.path.join(self.paths.ini_dir, fn))]
        if not have:
            raise Refused('The game has no Fallout.ini yet: start it once from Steam first.')
        placed = set()
        for fn in have:
            placed |= edit_ini_lines(read_ini_lines(os.path.join(self.paths.ini_dir, fn)), changes)[1]
        rest = {k: v for k, v in changes.items() if (k[0].lower(), k[1].lower()) not in placed}
        for fn in have:
            p = os.path.join(self.paths.ini_dir, fn)
            self.note_file(p)
            ro = not os.access(p, os.W_OK)
            lines = edit_ini_lines(read_ini_lines(p), changes)[0]
            if fn == have[-1] and rest:
                lines = edit_ini_lines(lines, rest, add=True)[0]
            if ro:
                os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
            with open(p, 'w', encoding='cp1252', errors='surrogateescape', newline='\r\n') as f:
                f.write('\n'.join(lines) + '\n')
            if ro:
                os.chmod(p, stat.S_IREAD)

    def make_folder(self, folder):
        self._note_dirs(folder)
        self._save()
        os.makedirs(folder, exist_ok=True)

    def restore(self):
        """Everything back, from the journal alone. Safe to run twice, or after a crash at any point. Returns
        {'differences': what's still not as it was before the run, 'problems': what couldn't be put back}. The journal
        goes only when nothing failed: if a file was held open, the next start tries again."""
        if not os.path.exists(journal_path(self.paths.work)):
            return {'differences': [], 'problems': [], 'run': self.j['run'], 'already': True}
        problems = []
        for e in reversed(self.j['files']):
            try:
                if e['kept']:
                    _copy_over(e['kept'], e['dst'])
                    if e.get('ro'):
                        os.chmod(e['dst'], stat.S_IREAD)
                elif os.path.exists(e['dst']):
                    os.chmod(e['dst'], stat.S_IWRITE | stat.S_IREAD)
                    os.remove(e['dst'])
            except OSError as err:
                problems.append('%s: %s' % (e['dst'], err))
        for d in sorted(self.j['dirs'], key=len, reverse=True):
            # (a folder we made, and only if the game added nothing we don't know of... except the test saves' folder)
            if os.path.basename(d).lower() == TEST_SAVES.lower() and os.path.isdir(d):
                shutil.rmtree(d, ignore_errors=True)
            elif os.path.isdir(d) and not os.listdir(d):
                os.rmdir(d)
        after = fingerprint(self.paths)
        before = self.j['before']
        diffs = differences(before, after)
        out = {'differences': diffs, 'problems': problems, 'run': self.j['run']}
        if not problems:
            done = os.path.join(self.paths.work, 'restored %s.json' % self.j['run'])
            _write_json(done, dict(out, finished=time.time()))
            os.remove(journal_path(self.paths.work))
            shutil.rmtree(self.j['keep'], ignore_errors=True)
        return out


def recover(work, alive=None):
    """The next start, or a look from the page. A journal left behind means a run didn't finish: put it back, unless
    the game it started is still running (its files are still in use): {'state': 'clean' | 'restored' | 'game still
    running', ...}."""
    if not os.path.exists(journal_path(work)):
        return {'state': 'clean'}
    s = Session.load(work)
    alive = alive or (lambda pid: pid in game_pids())
    if s.j.get('pid') and alive(s.j['pid']):
        return {'state': 'game still running', 'pid': s.j['pid'], 'run': s.j['run']}
    out = s.restore()
    out['state'] = 'restored' if not out['problems'] else 'could not restore'
    return out


# ---------- watching a run ----------

class Limits:
    """Seconds. cap: the whole run. first_line: from the start to the result file's first words (a game that starts
    and loads takes a while). silent: the file not growing after that. finish: after the finished marker, how long the
    game gets to quit by itself."""

    def __init__(self, cap=1800, first_line=240, silent=120, finish=30, poll=1.0, live_check=5.0):
        self.cap, self.first_line, self.silent, self.finish, self.poll, self.live_check = cap, first_line, silent, finish, poll, live_check


def _file_size(path):
    try:
        return os.path.getsize(path)
    except OSError:
        return -1


def supervise(proc, result_path, limits, finished, live=None, stop_asked=None, clock=time.time, sleep=time.sleep, seen=None):
    """Watch a game till it's over; returns why it ended (a word; ENDINGS says each in full). proc: alive(), stop().
    finished(path): is the finished marker in the file? live(): None, or the reason to stop at once (a save changed,
    the mouse taken). Whatever ends it, the process is stopped here if it's still there. seen, a dict, is given
    'lines_at', the time of the first words."""
    start, grew, size, next_live = clock(), None, -1, 0.0
    seen = seen if seen is not None else {}

    def end(why):
        if proc.alive():
            proc.stop()
        return why
    while True:
        now = clock()
        new = _file_size(result_path)
        if new != size and new > 0:
            size, grew = new, now
            seen.setdefault('lines_at', now - start)
        if size > 0 and finished(result_path):
            wait = now + limits.finish
            while proc.alive() and clock() < wait:
                sleep(limits.poll)
            return 'finished' if not proc.alive() else end('finished, had to be closed')
        if not proc.alive():
            return 'game closed'
        if stop_asked and stop_asked():
            return end('stopped on request')
        if live and now >= next_live:
            next_live = now + limits.live_check
            why = live()
            if why:
                return end(why)
        if now - start > limits.cap:
            return end('time cap')
        if grew is None and now - start > limits.first_line:
            return end('no first line')
        if grew is not None and now - grew > limits.silent:
            return end('went silent')
        sleep(limits.poll)


ENDINGS = {'finished': 'The checker wrote its finished line and the game quit by itself.',
           'finished, had to be closed': 'The checker finished, but the game didn\'t quit by itself: FOLab closed it.',
           'game closed': 'The game closed before the checker finished: a crash, or someone closed it.',
           'stopped on request': 'You stopped it.',
           'time cap': 'It ran past the time allowed: FOLab closed the game.',
           'no first line': 'The game never wrote a word to the result file: FOLab closed it.',
           'went silent': 'The result file stopped growing (a hang, a message box, or a pause): FOLab closed the game.',
           'your saves changed': 'One of your saves changed during the run: FOLab closed the game at once.',
           'mouse taken': 'The game held on to the mouse: FOLab closed it at once.'}


def cursor_clipped():
    """Is something holding the cursor inside part of the screen (a game with the mouse)? The real watch for it."""
    import ctypes

    class Rect(ctypes.Structure):
        _fields_ = [('l', ctypes.c_long), ('t', ctypes.c_long), ('r', ctypes.c_long), ('b', ctypes.c_long)]
    try:
        u = ctypes.windll.user32
        r = Rect()
        if not u.GetClipCursor(ctypes.byref(r)):
            return False
        w, h = u.GetSystemMetrics(78), u.GetSystemMetrics(79)   # (the whole desktop, all screens)
        return (r.r - r.l) < w or (r.b - r.t) < h
    except (AttributeError, OSError):
        return False
