"""The New Vegas Script Extender (xNVSE): finding it, putting it in the game, taking it out again.

xNVSE's own instructions: its .dll and .exe files go beside FalloutNV.exe (never in Data), and the game is started with
nvse_loader.exe. Its default config goes in Data\\NVSE. FOLab keeps a copy of anything it replaces in its backups
folder and remembers what it put in, so Take out removes exactly that. FOLab fetches nothing: the user downloads it from
xNVSE's page in their browser and FOLab installs it from their Downloads folder, unpacked into its own downloads first."""
import json
import os
import shutil
import subprocess
import time

import project

DOWNLOADS = os.path.join(project.HOME, 'downloads', 'xnvse')
RECORD = os.path.join(project.HOME, 'downloads', 'xnvse', 'installed.json')


def game_dir(data_dir):
    return os.path.dirname(os.path.normpath(data_dir))


def status(data_dir):
    g = game_dir(data_dir)
    dll = os.path.join(g, 'nvse_1_4.dll')
    out = {'installed': os.path.isfile(dll), 'loader': os.path.isfile(os.path.join(g, 'nvse_loader.exe')),
           'by_folab': os.path.isfile(RECORD), 'version': None, 'page': PAGE}
    if os.path.isfile(RECORD):
        with open(RECORD, encoding='utf-8') as f:
            out['version'] = json.load(f).get('version')
    return out


def _files(unpacked):
    """(source, destination relative to the game folder) for what goes in: .dll and .exe beside the game, Data\\... in
    Data (debug symbols, .pdb, are left out)."""
    out = []
    for root, _dirs, files in os.walk(unpacked):
        for fn in files:
            src = os.path.join(root, fn)
            rel = os.path.relpath(src, unpacked)
            if rel.lower().startswith('data' + os.sep):
                out.append((src, rel))
            elif os.path.dirname(rel) == '' and fn.lower().endswith(('.dll', '.exe')):
                out.append((src, rel))
    return out


PAGE = 'https://github.com/xNVSE/NVSE/releases/latest'
LOADER_DLL = 'nvse_1_4.dll'


def _tar(*args):
    """Windows' own tar, which reads .7z as well as .zip."""
    tar = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'System32', 'tar.exe')
    return subprocess.run([tar] + list(args), check=True, capture_output=True, text=True, errors='replace',
                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout


def find_xnvse():
    """xNVSE archives in the user's Downloads folder, newest first. Many plugins have NVSE in their names too, so what
    counts is what's inside: the extender's own DLL."""
    d = os.path.join(os.path.expanduser('~'), 'Downloads')
    out = []
    for fn in os.listdir(d) if os.path.isdir(d) else []:
        if not fn.lower().endswith(('.7z', '.zip')) or 'nvse' not in fn.lower():
            continue
        p = os.path.join(d, fn)
        try:
            names = _tar('-tf', p).splitlines()
        except (OSError, subprocess.CalledProcessError):
            continue
        if any(n.replace('\\', '/').rsplit('/', 1)[-1].lower() == LOADER_DLL for n in names):
            out.append({'file': fn, 'path': p, 'modified': os.path.getmtime(p)})
    return sorted(out, key=lambda x: -x['modified'])


def _unpack(archive):
    """Unpack into FOLab's downloads folder; the folder inside it that holds the extender's DLL."""
    out = os.path.join(DOWNLOADS, os.path.splitext(os.path.basename(archive))[0])
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    _tar('-xf', archive, '-C', out)
    for root, _dirs, files in os.walk(out):
        if any(f.lower() == LOADER_DLL for f in files):
            return root
    raise FileNotFoundError('%s is not in %s' % (LOADER_DLL, os.path.basename(archive)))


def install(data_dir, file):
    """Put in the archive of this name from the user's Downloads folder."""
    hit = next((a for a in find_xnvse() if a['file'] == file), None)
    if not hit:
        raise FileNotFoundError('%s is not an xNVSE archive in your Downloads folder.' % file)
    version = os.path.splitext(file)[0]
    files = _files(_unpack(hit['path']))
    g = game_dir(data_dir)
    stamp = time.strftime('%Y-%m-%d %H%M%S')
    backups, put = [], []
    for src, rel in files:
        dest = os.path.join(g, rel)
        if os.path.exists(dest):
            keep = os.path.join(project.HOME, 'backups', 'xnvse %s' % stamp, rel)
            os.makedirs(os.path.dirname(keep), exist_ok=True)
            shutil.copy2(dest, keep)
            backups.append(keep)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(src, dest)
        put.append(rel)
    with open(RECORD, 'w', encoding='utf-8') as f:
        json.dump({'version': version, 'files': put, 'when': stamp, 'backups': backups}, f, indent=1)
    return {'version': version, 'files': put, 'backups': backups}


PLUGINS_RECORD = os.path.join(project.HOME, 'downloads', 'nvse plugins.json')


def find_archives(names=('nvtf', 'tick fix', 'jip')):
    """Archives in the user's Downloads folder whose names look like the xNVSE plugins FOLab knows (newest first)."""
    d = os.path.join(os.path.expanduser('~'), 'Downloads')
    out = []
    for fn in os.listdir(d) if os.path.isdir(d) else []:
        low = fn.lower()
        if low.endswith(('.7z', '.zip', '.rar')) and any(n in low for n in names):
            p = os.path.join(d, fn)
            out.append({'file': fn, 'path': p, 'size': os.path.getsize(p), 'modified': os.path.getmtime(p)})
    return sorted(out, key=lambda x: -x['modified'])


def install_plugin_archive(data_dir, archive):
    """Install an xNVSE plugin from its archive: unpacked into FOLab's downloads first, then its NVSE folder (wherever
    it sits in the archive: at the top, or inside Data) copied into the game's Data\\NVSE. Records what went in."""
    name = os.path.splitext(os.path.basename(archive))[0]
    out = os.path.join(project.HOME, 'downloads', 'plugins', name)
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    _tar('-xf', archive, '-C', out)
    nvse_dir = None
    for root, dirs, _files in os.walk(out):
        hit = next((d for d in dirs if d.lower() == 'nvse'), None)
        if hit:
            nvse_dir = os.path.join(root, hit)
            break
    if not nvse_dir:
        raise ValueError('%s has no NVSE folder: not an xNVSE plugin FOLab knows how to install.' % os.path.basename(archive))
    dest_root = os.path.join(data_dir, 'NVSE')
    stamp = time.strftime('%Y-%m-%d %H%M%S')
    put, backups = [], []
    for root, _dirs, files in os.walk(nvse_dir):
        for fn in files:
            if fn.lower().endswith('.pdb'):
                continue
            rel = os.path.relpath(os.path.join(root, fn), nvse_dir)
            dest = os.path.join(dest_root, rel)
            if os.path.exists(dest):
                keep = os.path.join(project.HOME, 'backups', 'nvse plugins %s' % stamp, rel)
                os.makedirs(os.path.dirname(keep), exist_ok=True)
                shutil.copy2(dest, keep)
                backups.append(keep)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(os.path.join(root, fn), dest)
            put.append(os.path.join('Data', 'NVSE', rel))
    # NVTF refuses to run without its NVTF.ini, and some copies of its archive leave it out: FOLab's own, written from
    # the settings its source reads (app/nvtf_default.ini), goes in when it's missing
    plug = os.path.join(dest_root, 'Plugins')
    if any(p.lower().endswith('nvtf.dll') for p in put) and not os.path.exists(os.path.join(plug, 'NVTF.ini')):
        shutil.copyfile(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nvtf_default.ini'), os.path.join(plug, 'NVTF.ini'))
        put.append(os.path.join('Data', 'NVSE', 'Plugins', 'NVTF.ini'))
    rec = {}
    if os.path.isfile(PLUGINS_RECORD):
        with open(PLUGINS_RECORD, encoding='utf-8') as f:
            rec = json.load(f)
    rec[name] = {'files': put, 'when': stamp, 'archive': os.path.basename(archive)}
    with open(PLUGINS_RECORD, 'w', encoding='utf-8') as f:
        json.dump(rec, f, indent=1)
    return {'name': name, 'files': put, 'backups': backups}


def plugins(data_dir):
    """The xNVSE plugins in the game (their .dll files), and which FOLab put in."""
    d = os.path.join(data_dir, 'NVSE', 'Plugins')
    dlls = sorted(fn for fn in os.listdir(d) if fn.lower().endswith('.dll')) if os.path.isdir(d) else []
    rec = {}
    if os.path.isfile(PLUGINS_RECORD):
        with open(PLUGINS_RECORD, encoding='utf-8') as f:
            rec = json.load(f)
    return {'dlls': dlls, 'by_folab': list(rec)}


def uninstall(data_dir):
    """Take out what FOLab put in (a copy of each goes to backups first)."""
    if not os.path.isfile(RECORD):
        raise ValueError('FOLab did not install the script extender here, so it leaves it alone.')
    with open(RECORD, encoding='utf-8') as f:
        rec = json.load(f)
    g = game_dir(data_dir)
    stamp = time.strftime('%Y-%m-%d %H%M%S')
    removed = []
    for rel in rec['files']:
        dest = os.path.join(g, rel)
        if os.path.exists(dest):
            keep = os.path.join(project.HOME, 'backups', 'xnvse removed %s' % stamp, rel)
            os.makedirs(os.path.dirname(keep), exist_ok=True)
            shutil.move(dest, keep)
            removed.append(rel)
    os.remove(RECORD)
    return {'removed': removed}
