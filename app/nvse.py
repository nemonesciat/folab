"""The New Vegas Script Extender (xNVSE): finding it, putting it in the game, taking it out again.

xNVSE's own instructions: its .dll and .exe files go beside FalloutNV.exe (never in Data), and the game is started with
nvse_loader.exe. Its default config goes in Data\\NVSE. FOLab keeps a copy of anything it replaces in its backups
folder and remembers what it put in, so Take out removes exactly that. Downloads come only from xNVSE's own GitHub
releases, unpacked into FOLab's downloads folder first."""
import json
import os
import shutil
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
           'by_folab': os.path.isfile(RECORD), 'version': None, 'downloaded': sorted(
               d for d in os.listdir(DOWNLOADS) if os.path.isdir(os.path.join(DOWNLOADS, d))) if os.path.isdir(DOWNLOADS) else []}
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


RELEASES = 'https://api.github.com/repos/xNVSE/NVSE/releases/latest'


def latest():
    """The newest xNVSE release on its GitHub: {'version', 'asset', 'size', 'url'}."""
    import urllib.request
    req = urllib.request.Request(RELEASES, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'FOLab'})
    with urllib.request.urlopen(req, timeout=20) as r:
        rel = json.load(r)
    a = next(a for a in rel['assets'] if a['name'].lower().endswith('.7z'))
    return {'version': rel['tag_name'], 'asset': a['name'], 'size': a['size'], 'url': a['browser_download_url']}


def download(rel):
    """Fetch a release's archive from xNVSE's GitHub and unpack it into its own folder (Windows' tar reads .7z)."""
    import subprocess
    import urllib.request
    if not rel['url'].startswith('https://github.com/xNVSE/NVSE/releases/download/'):
        raise ValueError('Only xNVSE\'s own GitHub releases are downloaded.')
    os.makedirs(DOWNLOADS, exist_ok=True)
    archive = os.path.join(DOWNLOADS, rel['asset'])
    req = urllib.request.Request(rel['url'], headers={'User-Agent': 'FOLab'})
    with urllib.request.urlopen(req, timeout=120) as r, open(archive + '.part', 'wb') as f:
        shutil.copyfileobj(r, f)
    if os.path.getsize(archive + '.part') != rel['size']:
        raise IOError('The download came out the wrong size; try again.')
    os.replace(archive + '.part', archive)
    out = os.path.join(DOWNLOADS, rel['version'])
    os.makedirs(out, exist_ok=True)
    tar = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'System32', 'tar.exe')
    subprocess.run([tar, '-xf', archive, '-C', out], check=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    return rel['version']


def install(data_dir, version):
    unpacked = os.path.join(DOWNLOADS, version)
    files = _files(unpacked)
    if not any(r.lower() == 'nvse_1_4.dll' for _s, r in files):
        raise FileNotFoundError('nvse_1_4.dll is not in %s' % unpacked)
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
    import subprocess
    name = os.path.splitext(os.path.basename(archive))[0]
    out = os.path.join(project.HOME, 'downloads', 'plugins', name)
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    tar = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'System32', 'tar.exe')
    subprocess.run([tar, '-xf', archive, '-C', out], check=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
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
