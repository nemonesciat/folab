"""The game's own settings: Fallout.ini and FalloutPrefs.ini in Documents\\My Games\\FalloutNV.

The game reads Fallout.ini, then FalloutPrefs.ini over it, so a setting both have is changed in both. Values are
changed in place: every other line, comment and the order are kept, and a file marked read-only stays read-only. A
copy of each file goes to FOLab's backups before it's written. FOLab won't write while the game runs (it writes
FalloutPrefs.ini itself when it quits)."""
import ctypes
import os
import threading
import shutil
import time

import project

FILES = ('Fallout.ini', 'FalloutPrefs.ini')


def folder():
    """FOLAB_NV_INI overrides it (the tests point it at copies)."""
    return os.environ.get('FOLAB_NV_INI') or os.path.join(os.path.expanduser('~'), 'Documents', 'My Games', 'FalloutNV')


def _read(path):
    with open(path, encoding='cp1252', errors='replace') as f:
        return f.read().splitlines()


def read_all():
    """{file: [(section, key, value)]} for every key=value line"""
    out = {}
    for fn in FILES:
        p = os.path.join(folder(), fn)
        if not os.path.isfile(p):
            continue
        rows, sec = [], ''
        for line in _read(p):
            s = line.strip()
            if s.startswith('[') and s.endswith(']'):
                sec = s[1:-1]
            elif '=' in s and not s.startswith((';', '#')):
                k, v = s.split('=', 1)
                rows.append((sec, k.strip(), v.strip()))
        out[fn] = rows
    return out


def value(section, key):
    """The value the game ends up with: FalloutPrefs.ini's, else Fallout.ini's (None if neither has it)."""
    found = None
    for fn, rows in read_all().items():
        for sec, k, v in rows:
            if sec.lower() == section.lower() and k.lower() == key.lower():
                found = v
    return found


def write(changes, files=FILES):
    """changes: [(section, key, value)]. Each is set in every one of `files` that has it; a key neither has goes into
    the last of them (FalloutPrefs.ini by default), in its section. Returns the backup folder."""
    stamp = time.strftime('%Y-%m-%d %H%M%S')
    bk = os.path.join(project.HOME, 'backups', 'game settings ' + stamp)
    have = {}
    for fn in files:
        p = os.path.join(folder(), fn)
        if os.path.isfile(p):
            have[fn] = _read(p)
    pending = {(s.lower(), k.lower()): (s, k, str(v)) for s, k, v in changes}
    placed = set()
    for fn, lines in have.items():
        sec = ''
        for n, line in enumerate(lines):
            s = line.strip()
            if s.startswith('[') and s.endswith(']'):
                sec = s[1:-1]
            elif '=' in s and not s.startswith((';', '#')):
                k = s.split('=', 1)[0].strip()
                hit = pending.get((sec.lower(), k.lower()))
                if hit:
                    lines[n] = '%s=%s' % (k, hit[2])
                    placed.add((sec.lower(), k.lower()))
    for key, (s, k, v) in pending.items():
        if key in placed:
            continue
        fn = [f for f in files if f in have][-1]           # (a setting no file has yet: in the last, its section)
        lines = have[fn]
        at = next((n for n, l in enumerate(lines) if l.strip().lower() == '[%s]' % s.lower()), None)
        if at is None:
            lines += ['', '[%s]' % s, '%s=%s' % (k, v)]
        else:
            lines.insert(at + 1, '%s=%s' % (k, v))
    os.makedirs(bk, exist_ok=True)
    for fn, lines in have.items():
        p = os.path.join(folder(), fn)
        shutil.copy2(p, os.path.join(bk, fn))
        ro = not os.access(p, os.W_OK)
        if ro:
            os.chmod(p, 0o666)
        with open(p, 'w', encoding='cp1252', errors='replace', newline='\r\n') as f:
            f.write('\n'.join(lines) + '\n')
        if ro:
            os.chmod(p, 0o444)
    return bk


# The settings the page shows as controls: (id, group, label, section, key, kind, options, note)
SETTINGS = [
    ('fullscreen', 'Display', 'Fullscreen', 'Display', 'bFull Screen', 'bool', None, 'Off: a window with a frame (the game has no borderless mode of its own)'),
    ('width', 'Display', 'Width', 'Display', 'iSize W', 'res', None, ''),
    ('height', 'Display', 'Height', 'Display', 'iSize H', 'res', None, ''),
    ('vsync', 'Display', 'V-sync', 'Display', 'iPresentInterval', 'bool', None, 'Locks the frame rate to the monitor'),
    ('adapter', 'Display', 'Monitor', 'Display', 'iAdapter', 'adapter', None, 'Which screen fullscreen uses'),
    ('posx', 'Display', 'Window left', 'Display', 'iLocation X', 'int', None, 'Where the window opens (windowed)'),
    ('posy', 'Display', 'Window top', 'Display', 'iLocation Y', 'int', None, ''),
    ('fov', 'Display', 'Field of view', 'Display', 'fDefaultFOV', 'float', (55, 120), 'The world (75 is the game\'s)'),
    ('fov1st', 'Display', 'Weapon field of view', 'Display', 'fDefault1stPersonFOV', 'float', (40, 90), 'Your hands and weapon (55 is the game\'s)'),
    ('aniso', 'Display', 'Texture filtering', 'Display', 'iMaxAnisotropy', 'choice', [0, 2, 4, 8, 15], 'Anisotropic filtering'),
    ('msaa', 'Display', 'Anti-aliasing', 'Display', 'iMultiSample', 'choice', [0, 2, 4, 8], 'Samples'),
    ('active', 'Behaviour', 'Keep running when you Alt+Tab', 'General', 'bAlwaysActive', 'bool', None, 'The game doesn\'t pause in the background'),
    ('intro', 'Behaviour', 'Intro video', 'General', 'SIntroSequence', 'intro', None, 'Off skips the opening video'),
    ('shots', 'Behaviour', 'Screenshots (Print Screen)', 'Display', 'bAllowScreenShot', 'bool', None, ''),
    ('mouse', 'Behaviour', 'Mouse when the game isn\'t in front', 'Controls', 'bBackground Mouse', 'bool', None, ''),
    ('threads', 'Performance', 'CPU threads the game uses', 'General', 'iNumHWThreads', 'choice', [1, 2, 3, 4], '2 fixes stutter on many-core CPUs'),
    ('threadai', 'Performance', 'AI on its own thread', 'General', 'bUseThreadedAI', 'bool', None, ''),
    ('volume', 'Performance', 'Master volume', 'Audio', 'fDefaultMasterVolume', 'float', (0, 1), ''),
]
INTRO = 'Fallout INTRO Vsk.bik'


# --- Screens -------------------------------------------------------------------------------------------------------

class _DevMode(ctypes.Structure):
    _fields_ = [('name', ctypes.c_wchar * 32), ('spec', ctypes.c_ushort), ('drv', ctypes.c_ushort),
                ('size', ctypes.c_ushort), ('extra', ctypes.c_ushort), ('fields', ctypes.c_ulong),
                ('x', ctypes.c_long), ('y', ctypes.c_long), ('orient', ctypes.c_ulong), ('fixed', ctypes.c_ulong),
                ('color', ctypes.c_short), ('duplex', ctypes.c_short), ('yres', ctypes.c_short),
                ('tt', ctypes.c_short), ('collate', ctypes.c_short), ('form', ctypes.c_wchar * 32),
                ('logpix', ctypes.c_ushort), ('bpp', ctypes.c_ulong), ('w', ctypes.c_ulong), ('h', ctypes.c_ulong),
                ('dflags', ctypes.c_ulong), ('hz', ctypes.c_ulong), ('rest', ctypes.c_ulong * 8)]


class _Device(ctypes.Structure):
    _fields_ = [('cb', ctypes.c_ulong), ('name', ctypes.c_wchar * 32), ('desc', ctypes.c_wchar * 128),
                ('flags', ctypes.c_ulong), ('id', ctypes.c_wchar * 128), ('key', ctypes.c_wchar * 128)]


def screens():
    """[{name, monitor, primary, x, y, w, h, hz, modes: [[w, h]]}], the main screen first (it is the game's
    iAdapter 0; the others follow in Windows' order, which is how Direct3D numbers them as a rule)."""
    out = []
    try:
        u = ctypes.windll.user32
    except AttributeError:
        return out
    n = 0
    while True:
        d = _Device()
        d.cb = ctypes.sizeof(d)
        if not u.EnumDisplayDevicesW(None, n, ctypes.byref(d), 0):
            break
        n += 1
        if not d.flags & 1:                                     # (attached to the desktop)
            continue
        mon = _Device()
        mon.cb = ctypes.sizeof(mon)
        u.EnumDisplayDevicesW(d.name, 0, ctypes.byref(mon), 0)
        cur = _DevMode()
        cur.size = ctypes.sizeof(cur)
        u.EnumDisplaySettingsW(d.name, -1, ctypes.byref(cur))     # (the mode it's in now)
        modes, i = set(), 0
        while True:
            m = _DevMode()
            m.size = ctypes.sizeof(m)
            if not u.EnumDisplaySettingsW(d.name, i, ctypes.byref(m)):
                break
            i += 1
            if m.bpp == 32 and m.w >= 800:
                modes.add((m.w, m.h))
        out.append({'name': d.name, 'monitor': mon.desc or d.desc, 'primary': bool(d.flags & 4),
                    'x': cur.x, 'y': cur.y, 'w': cur.w, 'h': cur.h, 'hz': cur.hz,
                    'modes': sorted(modes, reverse=True)})
    out.sort(key=lambda s: not s['primary'])
    return out


# --- Borderless ----------------------------------------------------------------------------------------------------
# The game has no borderless mode. FOLab makes one when it starts the game: the game runs windowed at the screen's
# size, and once its window shows, FOLab takes the frame off and lays it over the whole screen (never bringing it to
# the front or touching the keyboard). Starting the game some other way gives the framed window.

def _game_window(u):
    found = []
    k = ctypes.windll.kernel32

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def each(hwnd, _):
        if not u.IsWindowVisible(hwnd):
            return True
        pid = ctypes.c_ulong()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        h = k.OpenProcess(0x1000, False, pid.value)                 # (query limited information)
        if h:
            buf = ctypes.create_unicode_buffer(520)
            size = ctypes.c_ulong(520)
            if k.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)) and \
                    buf.value.lower().endswith('\falloutnv.exe'):
                found.append(hwnd)
            k.CloseHandle(h)
        return True
    u.EnumWindows(each, 0)
    return found[0] if found else None


def make_borderless(screen, wait=180):
    """Watch for the game's window (up to `wait` seconds) in the background and take its frame off."""
    def run():
        try:
            u = ctypes.windll.user32
        except AttributeError:
            return
        u.GetWindowLongW.restype = ctypes.c_long
        end = time.time() + wait
        while time.time() < end:
            hwnd = _game_window(u)
            if hwnd:
                time.sleep(1.5)                                     # (let the game finish setting its window up)
                style = u.GetWindowLongW(hwnd, -16)
                style &= ~(0x00C00000 | 0x00040000 | 0x00020000 | 0x00010000 | 0x00080000)  # caption, frame, buttons
                u.SetWindowLongW(hwnd, -16, style)
                # no z-order change, don't activate, redraw the frame
                u.SetWindowPos(hwnd, None, screen['x'], screen['y'], screen['w'], screen['h'], 0x0004 | 0x0010 | 0x0020)
                return
            time.sleep(1)
    threading.Thread(target=run, daemon=True).start()
