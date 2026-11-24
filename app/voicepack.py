"""The voice pack: the voice maker's packages (numpy, onnxruntime, soundfile and what they need, ~94 MB of FOLab's
139), a download of its own so FOLab itself stays small. Most people never voice a line.

It is a zip holding one folder, `voice pack\\`, with the packages and `voicepack.json` ({"python": "3.13", "made_for":
FOLab's version}): the packages are built for one Python, so a pack fits the FOLabs on that Python. Two ways in, as with
the Kokoro model: unzip it into FOLab's folder yourself, or leave it in Downloads and press Install on the Voice part of
the dialogue editor (`install`: checked, unpacked beside, then renamed into place). FOLab fetches nothing from the
internet (Nexus's rule on tools that download): the user gets the zip from FOLab's Nexus or GitHub page.

`load()` puts the pack's folder on sys.path (server.py at start, and after an install: no restart). Run from source with
a Python that has the packages already, none of this is needed and `state()` says so."""
import glob
import importlib
import json
import os
import shutil
import sys
import zipfile

FOLDER = 'voice pack'
MARK = 'voicepack.json'
ZIP = 'FOLab-voice-pack-*.zip'
PAGE = 'https://github.com/nemonesciat/folab/releases'
PACKAGES = ('numpy', 'onnxruntime', 'soundfile')


def home():
    return os.environ.get('FOLAB_HOME') or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


def folder():
    return os.path.join(home(), FOLDER)


def python_tag():
    return '%d.%d' % sys.version_info[:2]


def _mark(path):
    try:
        with open(os.path.join(path, MARK), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def load():
    """Puts an installed pack that fits this Python on sys.path; True if there is one."""
    m = _mark(folder())
    if not m or m.get('python') != python_tag():
        return False
    p = os.path.abspath(folder())
    if p not in sys.path:
        sys.path.append(p)
        importlib.invalidate_caches()
    return True


def importable():
    try:
        for name in PACKAGES:
            importlib.import_module(name)
        return True
    except Exception:       # noqa: BLE001 - any failure means no voice maker
        return False


def found_zip(downloads=None):
    """The newest voice pack zip in Downloads, or None."""
    downloads = downloads or os.path.join(os.path.expanduser('~'), 'Downloads')
    zips = sorted(glob.glob(os.path.join(downloads, ZIP)), key=os.path.getmtime, reverse=True)
    return zips[0] if zips else None


def state(downloads=None):
    """{'ready', 'installed', 'zip', 'why'}: what the Voice part says when there's no voice maker."""
    load()
    if importable():
        return {'ready': True, 'installed': bool(_mark(folder())), 'zip': None, 'why': None}
    m = _mark(folder())
    z = found_zip(downloads)
    if m and m.get('python') != python_tag():
        why = ('The voice pack in FOLab\'s folder is for another FOLab (Python %s, this one is %s): download the voice '
               'pack made for this version.' % (m.get('python'), python_tag()))
    elif z:
        why = 'The voice pack is in your Downloads folder (%s): press Install to put it in.' % os.path.basename(z)
    else:
        why = ('Voicing lines needs FOLab\'s voice pack, a download of its own (about 30 MB): get '
               'FOLab-voice-pack-<version>.zip from FOLab\'s Nexus Files tab or GitHub page and leave it in your '
               'Downloads folder, or unzip it into FOLab\'s folder.')
    return {'ready': False, 'installed': bool(m), 'zip': z, 'why': why, 'page': PAGE}


def install(path=None, downloads=None):
    """Unpacks the voice pack zip (the newest in Downloads unless given) into FOLab's folder and loads it."""
    path = path or found_zip(downloads)
    if not path:
        raise ValueError('No FOLab-voice-pack zip in your Downloads folder.')
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        bad = [n for n in names if n.startswith(('/', '\\')) or '..' in n.replace('\\', '/').split('/')
               or not n.replace('\\', '/').startswith(FOLDER + '/')]
        if bad or (FOLDER + '/' + MARK) not in names:
            raise ValueError('%s isn\'t a FOLab voice pack.' % os.path.basename(path))
        m = json.loads(z.read(FOLDER + '/' + MARK).decode('utf-8'))
        if m.get('python') != python_tag():
            raise ValueError('That voice pack is for another FOLab (Python %s; this one is %s): download the one made '
                             'for this version.' % (m.get('python'), python_tag()))
        new = os.path.join(home(), FOLDER + ' (unpacking)')
        shutil.rmtree(new, ignore_errors=True)
        os.makedirs(new)
        z.extractall(new)
    old = folder()
    if os.path.isdir(old):
        gone = old + ' (old)'
        shutil.rmtree(gone, ignore_errors=True)
        os.rename(old, gone)        # (a loaded pack's DLLs can't be deleted while FOLab runs: they go next start)
    os.rename(os.path.join(new, FOLDER), old)
    shutil.rmtree(new, ignore_errors=True)
    load()
    return dict(state(downloads), made_for=m.get('made_for'))


def tidy():
    """At start: a pack set aside by an install while it was loaded."""
    shutil.rmtree(folder() + ' (old)', ignore_errors=True)


def make(packages_dir, out_zip, made_for):
    """The build's side (packaging/build.py): a voice pack zip from the staged packages."""
    with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr(FOLDER + '/' + MARK, json.dumps({'python': python_tag(), 'made_for': made_for}))
        for dp, dirs, files in os.walk(packages_dir):
            dirs[:] = [d for d in dirs if d not in ('bin', '__pycache__')]
            for fn in files:
                p = os.path.join(dp, fn)
                z.write(p, FOLDER + '/' + os.path.relpath(p, packages_dir).replace('\\', '/'))
    return out_zip
