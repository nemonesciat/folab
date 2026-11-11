"""Finding the game (gamedata.find_data_dir): Steam wherever Windows says it is and every library it lists, the game's
own note of where it was installed, the folder the user chose; and when it's nowhere, the server answers only the page
that asks (server.NO_GAME) until a folder with the game in it is given. Fake folders throughout, but for the last step,
which reads the real game from the folder it's told."""
import json
import os
import sys
import threading
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata  # noqa: E402
import project  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


REAL = gamedata.find_data_dir()             # (before anything is faked: the last step loads from it)
os.environ.pop('FOLAB_NV_DATA', None)
root = os.path.join(project.HOME, 'findgame')


def game_at(*parts):
    """A fake install: a game folder with FalloutNV.exe and Data\\FalloutNV.esm."""
    g = os.path.join(root, *parts)
    os.makedirs(os.path.join(g, 'Data'), exist_ok=True)
    for name in ('FalloutNV.exe', os.path.join('Data', 'FalloutNV.esm')):
        with open(os.path.join(g, name), 'wb') as f:
            f.write(b'x')
    return g


# ---------- what counts as the game's folder ----------
g = game_at('plain', 'Fallout New Vegas')
data = os.path.join(g, 'Data')
check('the game folder gives its Data folder', gamedata.data_dir_from(g) == data)
check('so does Data itself', gamedata.data_dir_from(data) == data)
check('and the game\'s exe, or a path pasted in quotes', gamedata.data_dir_from(os.path.join(g, 'FalloutNV.exe')) == data and gamedata.data_dir_from('"%s"' % g) == data)
check('a folder without the game is not it', gamedata.data_dir_from(root) is None and gamedata.data_dir_from('') is None
      and gamedata.data_dir_from(os.path.join(root, 'nowhere')) is None)
half = game_at('steam', 'steamapps', 'downloading', '22380')
check('never Steam\'s download folder', gamedata.data_dir_from(half) is None)

# ---------- Steam somewhere else, the game in a library on another drive ----------
steam = os.path.join(root, 'elsewhere', 'Steam')
library = os.path.join(root, 'drive S', 'SteamLibrary')
there = game_at('drive S', 'SteamLibrary', 'steamapps', 'common', 'Fallout New Vegas')
os.makedirs(os.path.join(steam, 'steamapps'), exist_ok=True)
with open(os.path.join(steam, 'steamapps', 'libraryfolders.vdf'), 'w', encoding='utf-8') as f:
    f.write('"libraryfolders"\n{\n\t"0"\n\t{\n\t\t"path"\t\t"%s"\n\t}\n\t"1"\n\t{\n\t\t"path"\t\t"%s"\n\t}\n}\n'
            % (steam.replace('\\', '\\\\'), library.replace('\\', '\\\\')))
known = {}
gamedata._registry = lambda hive, key, value: known.get((hive, key, value), '')
gamedata._STEAM_USUAL = []
check('nothing known: not found, and nowhere looked', gamedata.find_data_dir() is None and gamedata.looked_in() == [])
known[gamedata._STEAM_KEYS[0]] = steam.replace('\\', '/')        # (Steam writes its own path with forward slashes)
check('Steam where Windows says it is: the game is found in its other library', gamedata.find_data_dir() == os.path.join(there, 'Data'),
      gamedata.find_data_dir())
check('and FOLab can say where it looked', os.path.join(library, 'steamapps', 'common', 'Fallout New Vegas') in gamedata.looked_in())

# ---------- no Steam: the game's own note of where it is (its launcher, GOG) ----------
known.clear()
gog = game_at('GOG Games', 'Fallout New Vegas')
known[gamedata._GAME_KEYS[0]] = gog + '\\'
check('the folder the game\'s launcher wrote down', gamedata.find_data_dir() == os.path.join(gog, 'Data'))
known.clear()
known[gamedata._GAME_KEYS[3]] = gog
check('the folder GOG wrote down', gamedata.find_data_dir() == os.path.join(gog, 'Data'))
known[gamedata._GAME_KEYS[3]] = os.path.join(root, 'gone')
check('a note of a folder that is gone: not found', gamedata.find_data_dir() is None)

# ---------- the user's own answer ----------
with open(os.path.join(project.HOME, 'folab_settings.json'), 'w', encoding='utf-8') as f:
    json.dump({'launch_via': 'steam'}, f)
check('a wrong folder is not kept', gamedata.remember_data_dir(root) is None and gamedata.find_data_dir() is None)
check('the right one is', gamedata.remember_data_dir(g) == data and gamedata.find_data_dir() == data)
with open(os.path.join(project.HOME, 'folab_settings.json'), encoding='utf-8') as f:
    kept = json.load(f)
check('kept beside the other settings, which stay', kept == {'launch_via': 'steam', 'game_data': data}, kept)
known[gamedata._GAME_KEYS[0]] = gog
check('it comes before what FOLab would find by itself', gamedata.find_data_dir() == data)
os.remove(os.path.join(data, 'FalloutNV.esm'))
check('once the game has gone from it, FOLab looks again', gamedata.find_data_dir() == os.path.join(gog, 'Data'))
known.clear()
os.remove(os.path.join(project.HOME, 'folab_settings.json'))

# ---------- the server with no game: only the asking page ----------
import server  # noqa: E402
from http.server import ThreadingHTTPServer  # noqa: E402

server.NO_GAME = True
srv = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = 'http://127.0.0.1:%d' % srv.server_address[1]


def ask(path, body=None):
    req = urllib.request.Request(base + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


code, page = ask('/')
check('no game: the page asks where it is', code == 200 and b'Where is New Vegas?' in page)
code, d = ask('/api/game/missing')
check('and says it is not found', code == 200 and json.loads(d)['found'] is False)
check('everything else waits', ask('/api/state')[0] == 503 and ask('/api/save', {})[0] == 503)
check('its own files still come', ask('/web/vendor/fonts.css')[0] == 200)
code, d = ask('/api/game/folder', {'path': root})
check('a folder without the game: said plainly, still asking', code == 500 and 'FalloutNV.exe' in json.loads(d)['error'] and server.NO_GAME)
if REAL:
    code, d = ask('/api/game/folder', {'path': os.path.dirname(os.path.normpath(REAL))})
    check('the game\'s folder: FOLab loads it', code == 200 and json.loads(d)['data'] == os.path.normpath(REAL) and not server.NO_GAME, d[:200])
    code, d = ask('/api/state')
    check('and is FOLab from then on', code == 200 and json.loads(d)['interiors'] > 400)
    check('with the page its own', b'Where is New Vegas?' not in ask('/')[1])
    check('the answer is kept for next time', gamedata.find_data_dir() == os.path.normpath(REAL))
srv.shutdown()
