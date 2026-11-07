"""xNVSE goes in from the user's Downloads folder and comes out again, and FOLab has no way left to fetch anything.
A fake home and a fake game folder: nothing goes near the real game."""
import ast
import os
import subprocess
import sys
import tempfile
import zipfile
APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app')
sys.path.insert(0, APP)

top = tempfile.mkdtemp(prefix='folab-nvse-')
os.environ['USERPROFILE'] = os.environ['HOME'] = top
import nvse  # noqa: E402

dl = os.path.join(top, 'Downloads')
game = os.path.join(top, 'game')
data = os.path.join(game, 'Data')
os.makedirs(dl)
os.makedirs(data)


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % detail if detail else ''))


def pack(name, files):
    with zipfile.ZipFile(os.path.join(dl, name), 'w') as z:
        for n, text in files.items():
            z.writestr(n, text)


check('nothing in Downloads, nothing found', nvse.find_xnvse() == [])
REAL = {'nvse_1_4.dll': 'dll', 'nvse_loader.exe': 'exe', 'nvse_editor_1_4.dll': 'dll', 'nvse_1_4.pdb': 'symbols',
        'Data/NVSE/nvse_config.ini': 'ini', 'readme.txt': 'text'}
pack('JIP LN NVSE.zip', {'NVSE/Plugins/jip_nvse.dll': 'plugin'})      # a plugin, with NVSE in its name
pack('holiday photos.zip', {'nvse_1_4.dll': 'not named nvse'})        # not named for it
pack('xnvse_6_4_0.zip', REAL)
found = nvse.find_xnvse()
check('only the extender is found', [a['file'] for a in found] == ['xnvse_6_4_0.zip'], str([a['file'] for a in found]))

try:
    nvse.install(data, 'JIP LN NVSE.zip')
    check('a plugin is refused', False)
except FileNotFoundError:
    check('a plugin is refused', True)

# what was in the game before: kept in backups, and FOLab's copy is what's there now
old = os.path.join(game, 'nvse_loader.exe')
open(old, 'w').write('older')
r = nvse.install(data, 'xnvse_6_4_0.zip')
check('its files are beside the game', all(os.path.isfile(os.path.join(game, f)) for f in ('nvse_1_4.dll', 'nvse_editor_1_4.dll')))
check('the older file was replaced and kept', open(old).read() == 'exe' and len(r['backups']) == 1 and open(r['backups'][0]).read() == 'older')
check('its config is in Data', os.path.isfile(os.path.join(data, 'NVSE', 'nvse_config.ini')))
check('no symbols or readme go in', not os.path.exists(os.path.join(game, 'nvse_1_4.pdb')) and not os.path.exists(os.path.join(game, 'readme.txt')))
s = nvse.status(data)
check('status says so', s['installed'] and s['loader'] and s['by_folab'] and s['version'] == 'xnvse_6_4_0', str(s))
check('status has the page', s['page'].startswith('https://github.com/xNVSE/NVSE/'))
nvse.uninstall(data)
check('take out removes it', not os.path.exists(os.path.join(game, 'nvse_1_4.dll')) and not nvse.status(data)['by_folab'])

# inside a folder of its own, and a real .7z when this Windows's tar can make one
pack('NVSE in a folder.zip', {'xNVSE 6.4/nvse_1_4.dll': 'dll', 'xNVSE 6.4/nvse_loader.exe': 'exe'})
os.utime(os.path.join(dl, 'NVSE in a folder.zip'), (2000000000, 2000000000))
check('newest comes first', nvse.find_xnvse()[0]['file'] == 'NVSE in a folder.zip')
nvse.install(data, 'NVSE in a folder.zip')
check('from a folder inside the archive', os.path.isfile(os.path.join(game, 'nvse_1_4.dll')))
nvse.uninstall(data)
src = os.path.join(top, 'src')
os.makedirs(src)
open(os.path.join(src, 'nvse_1_4.dll'), 'w').write('dll')
tar = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'System32', 'tar.exe')
made = subprocess.run([tar, '--format=7zip', '-cf', os.path.join(dl, 'nvse_7z.7z'), '-C', src, 'nvse_1_4.dll'], capture_output=True).returncode == 0
if made:
    nvse.install(data, 'nvse_7z.7z')
    check('from a .7z', os.path.isfile(os.path.join(game, 'nvse_1_4.dll')))
    nvse.uninstall(data)
else:
    print('(this tar makes no .7z; reading one was seen on the real xNVSE archive before)')

# Nexus's rule on tools that fetch things: nothing in the app can
NET = {'urllib.request', 'http.client', 'ftplib', 'smtplib', 'poplib', 'imaplib', 'telnetlib', 'xmlrpc.client'}
bad = []
for fn in os.listdir(APP):
    if fn.endswith('.py'):
        for node in ast.walk(ast.parse(open(os.path.join(APP, fn), encoding='utf-8').read())):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module] if isinstance(node, ast.ImportFrom) else []
            bad += ['%s: %s' % (fn, n) for n in names if n in NET]
check('no internet client is imported anywhere in the app', not bad, ', '.join(bad))
