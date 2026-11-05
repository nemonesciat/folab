"""FOLab's local web server: the editor page and a small JSON API over the game's data and the open project.

    py -3 server.py [port] [--no-browser]        opens http://127.0.0.1:8771/ when ready

Game files are only read. Projects live in FOLab's projects folder; Save writes the plugin to FOLab's build folder,
and Install (the user's choice) copies it into the game."""
import json
import os
import struct
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import espwrite
import gamedata
import install
import nif
import nvse
import playtest
import project
import actors
import adopt
import browse
import recordio
import refinfo
import tes4

PORT = 8771
WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web')
SETTINGS = os.path.join(project.HOME, 'folab_settings.json')
TYPES = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css',
         '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.txt': 'text/plain',
         '.woff2': 'font/woff2'}
# What the Place panel offers, with the names it shows
PLACEABLE = {'STAT': 'Statics', 'MSTT': 'Movable statics', 'FURN': 'Furniture', 'CONT': 'Containers',
             'DOOR': 'Doors', 'LIGH': 'Lights', 'MISC': 'Items', 'ACTI': 'Activators', 'TACT': 'Talking activators',
             'TERM': 'Terminals', 'BOOK': 'Books', 'NOTE': 'Notes', 'WEAP': 'Weapons', 'ARMO': 'Apparel',
             'ALCH': 'Aid', 'AMMO': 'Ammo', 'KEYM': 'Keys', 'IDLM': 'Idle markers', 'PWAT': 'Placeable water',
             'ADDN': 'Addon nodes', 'IMOD': 'Weapon mods', 'CHIP': 'Chips', 'CMNY': 'Caravan money',
             'CCRD': 'Caravan cards', 'NPC_': 'Characters', 'CREA': 'Creatures'}
ACTORS = {'NPC_', 'CREA'}

GD = None
PR = None
BR = None
CATALOGUE = []                          # [key, type, edid, name, model] of every placeable game object
_meshes = {}
_actors = {}                            # base key -> parts (actors.py)
_lock = threading.RLock()


def load_settings():
    try:
        with open(SETTINGS, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_settings(**kw):
    s = load_settings()
    s.update(kw)
    with open(SETTINGS, 'w', encoding='utf-8') as f:
        json.dump(s, f, indent=1)


def is_marker(btype, edid, model):
    """Editor-only things the game never draws."""
    m = model.lower()
    return btype == 'STAT' and ('marker' in edid.lower() or m.startswith(('marker', 'editor')))


def build_catalogue():
    out = []
    for fid, (i, rec) in GD.forms.items():
        if rec.tag not in PLACEABLE:
            continue
        btype, edid, name, model = GD.describe(fid)
        if btype in ACTORS:
            out.append([GD.key(fid), btype, edid, name, ''])
            continue
        if not model or is_marker(btype, edid, model):
            continue
        out.append([GD.key(fid), btype, edid, name, GD.model_path(btype, model)])
    out.sort(key=lambda x: x[2].lower())
    return out


# --- places and things ---

def interiors():
    out = []
    changed = set(PR.cells) if PR else set()
    for c in GD.interiors:
        f = GD.fields(c)
        k = GD.key(c)
        out.append({'id': k, 'edid': tes4.zstr(f.get('EDID', b'')), 'name': tes4.zstr(f.get('FULL', b'')),
                    'refs': len(GD.cell_refs.get(c, ())), 'plugin': GD.names[c >> 24], 'mine': k in changed})
    out.sort(key=lambda x: x['edid'].lower())
    return out


def base_info(bkey):
    """(type, editor ID, name, model) of a base form as the mod leaves it: its own records and changes first."""
    rec = PR.records.get(bkey) if PR else None
    if rec:
        model = (recordio.field(rec, 'MOD2') if rec['type'] == 'ARMO' else '') or recordio.field(rec, 'MODL')
        return rec['type'], recordio.field(rec, 'EDID'), recordio.field(rec, 'FULL'), model
    return GD.describe(GD.from_key(bkey))


def light_of(bkey):
    """A light's radius, colour and flags, as the mod leaves it (None when it isn't a light)."""
    rec = PR.records.get(bkey) if PR else None
    if rec:
        d = next((s for s in rec['subs'] if s['tag'] == 'DATA' and s['kind'] == 'struct'), None)
        if not d:
            return None
        v = {f['name']: f['value'] for f in d['fields'] if 'name' in f}
    else:
        fid = GD.from_key(bkey)
        data = GD.fields(fid).get('DATA', b'')
        if len(data) < 32:
            return None
        t, radius, r, g, b, _x, flags, falloff, fov = struct.unpack_from('<iIBBBBIff', data)
        v = {'Radius': radius, 'Red': r, 'Green': g, 'Blue': b, 'Flags': flags, 'Falloff exponent': falloff}
    flags = v.get('Flags', 0)
    return {'radius': v.get('Radius', 0), 'color': [v.get('Red', 255), v.get('Green', 255), v.get('Blue', 255)],
            'off': bool(flags & 0x20), 'negative': bool(flags & 0x4), 'falloff': v.get('Falloff exponent', 1)}


def actor_parts(bkey):
    """The meshes a character or creature is drawn from (the game's form, or a record of the mod's own copied from
    one: drawn as the one it was copied from, by its editor ID's original)."""
    if bkey not in _actors:
        try:
            if bkey.startswith('+'):
                bkey_draw = (PR.records.get(bkey) or {}).get('copied_from', '') if PR else ''
                fid = GD.from_key(bkey_draw) if bkey_draw else None
            else:
                fid = GD.from_key(bkey)
            _actors[bkey] = actors.parts(GD, fid) if fid in GD.forms else {'parts': [], 'scale': 1.0}
        except Exception as e:
            _actors[bkey] = {'parts': [], 'scale': 1.0, 'error': str(e)}
    return _actors[bkey]


def thing(key, bkey, p, s, state):
    btype, edid, name, model = base_info(bkey)
    t = {'key': key, 'bkey': bkey, 'base': edid, 'type': btype, 'name': name,
         'model': GD.model_path(btype, model) if model else '', 'p': list(p), 's': s,
         'marker': is_marker(btype, edid, model), 'state': state}
    if btype in ACTORS:
        t['actor'] = True
    if btype == 'LIGH':
        t['light'] = light_of(bkey)
    return t


def cell_things(ckey):
    """Every drawable thing in a cell as the mod leaves it: the game's refs with the project's changes laid over,
    and the project's own new ones."""
    c = GD.from_key(ckey)
    mine = (PR.cells.get(ckey) or {}).get('refs', {}) if PR else {}
    out = []
    for r in GD.refs(c):
        if r['base'] not in GD.forms or not r['pos']:
            continue
        btype, _e, _n, model = GD.describe(r['base'])
        if (not model and btype not in ACTORS and btype != 'LIGH') or btype == 'TREE':
            continue
        k = GD.key(r['ref'])
        ch = mine.get(k)
        p, s, state, base = list(r['pos']) + list(r['rot']), r['scale'], '', GD.key(r['base'])
        if ch:
            if ch.get('removed'):
                state = 'removed'
            else:
                p, s, state = ch.get('p', p), ch.get('s', s), 'moved'
                if ch.get('base'):
                    base = ch['base']
        t = thing(k, base, p, s, state)
        if r['leads']:
            t['door'] = True
        out.append(t)
    for k, ch in mine.items():
        if k.startswith('+'):
            out.append(thing(k, ch['base'], ch['p'], ch.get('s', 1.0), 'new'))
    return out


def cell(ckey):
    return {'id': ckey, 'edid': GD.edid(GD.from_key(ckey)), 'things': cell_things(ckey)}


def ref(ckey, rkey):
    """One placed thing for the object window: its base record and its own fields."""
    t = next((t for t in cell_things(ckey) if t['key'] == rkey), None)
    if not t:
        raise FileNotFoundError(rkey)
    frm = 'your mod' if t['bkey'].startswith('+') else GD.names[GD.source(GD.from_key(t['bkey']))[0]]
    out = {'thing': t, 'base': {'key': t['bkey'], 'type': t['type'], 'edid': t['base'], 'name': t['name'],
                                'model': t['model'], 'from': frm}}
    if not rkey.startswith('+'):
        out['ref'] = refinfo.ref_info(GD, GD.from_key(rkey))
    return out


def door(rkey):
    if rkey.startswith('+'):
        return None
    return refinfo.door_target(GD, GD.from_key(rkey))


def mesh(path):
    key = path.lower()
    with _lock:
        if key in _meshes:
            return _meshes[key]
    try:
        shapes = nif.mesh_from_nif(GD.read_file(path))
        for s in shapes:
            t = s['tex'].lower()
            if t and not t.startswith('textures\\'):
                s['tex'] = 'textures\\' + s['tex']
        out = json.dumps({'shapes': shapes}, separators=(',', ':')).encode()
    except Exception as e:
        out = json.dumps({'shapes': [], 'error': str(e)}).encode()
    with _lock:
        _meshes[key] = out
    return out


def search(q, kind='', limit=300):
    words = q.lower().split()
    out = []
    for k, r in (PR.records.items() if PR else ()):         # the mod's own new things first
        if k.startswith('+') and r['type'] in PLACEABLE and (not kind or r['type'] == kind) and recordio.field(r, 'MODL'):
            e, n = recordio.field(r, 'EDID'), recordio.field(r, 'FULL')
            if all(w in (e + ' ' + n).lower() for w in words):
                out.append({'key': k, 'type': r['type'], 'edid': e, 'name': n, 'model': GD.model_path(r['type'], recordio.field(r, 'MODL'))})
    for row in CATALOGUE:
        if kind and row[1] != kind:
            continue
        hay = (row[2] + ' ' + row[3] + ' ' + row[4]).lower()
        if all(w in hay for w in words):
            out.append({'key': row[0], 'type': row[1], 'edid': row[2], 'name': row[3], 'model': row[4]})
            if len(out) >= limit:
                break
    return out


# --- the project ---

def state():
    s = {'game': GD.data_dir, 'interiors': len(GD.interiors), 'project': PR.state() if PR else None,
         'projects': project.list_projects(), 'kinds': PLACEABLE}
    s['nvse'] = nvse.status(GD.data_dir)
    s['launch_via'] = load_settings().get('launch_via', 'nvse')
    if PR:
        s['installed'] = install.status(GD.data_dir, PR.plugin)
        built = os.path.join(project.BUILD_DIR, PR.plugin)
        s['project']['built'] = os.path.isfile(built) and os.path.getmtime(built) >= os.path.getmtime(PR.path)
        s['project']['masters'] = masters()
    return s


def load_game(pr):
    """The game as FOLab shows it: the official files, and an opened mod's own plugin on top of them."""
    global GD, CATALOGUE, BR
    data_dir = GD.data_dir if GD else gamedata.find_data_dir()
    want = [os.path.join(data_dir, n) for n in gamedata.OFFICIAL if os.path.isfile(os.path.join(data_dir, n))]
    if pr and pr.source:
        want.append(pr.source_path())
    if GD and [p.path for p in GD.plugins] == want:
        return
    t = time.time()
    if BR:
        BR.close()
    GD = gamedata.GameData(data_dir, want)
    CATALOGUE = build_catalogue()
    BR = browse.Browse(GD, lambda: PR)
    _meshes.clear()
    _actors.clear()
    print('loaded %d plugins (%.1fs)' % (len(GD.plugins), time.time() - t), flush=True)


def open_project(name, create=False):
    global PR
    pr = project.Project.create(name) if create else project.Project.open(name)
    load_game(pr)
    PR = pr
    save_settings(project=PR.name)
    return state()


def masters():
    """The open mod's masters, as it would be saved now."""
    try:
        w = espwrite.Writer(GD, PR)
        w.plan()
        return w.masters
    except Exception as e:
        return ['(%s)' % e]


def edit(label, ops):
    if not PR:
        raise ValueError('no mod open')
    made = PR.apply(label, ops)
    out = {'state': state(), 'made': made}
    cells = {o['cell'] for o in ops if 'cell' in o}
    if len(cells) == 1:
        out['things'] = [t for t in cell_things(cells.pop()) if t['key'] in made or t['key'] in {o.get('ref') for o in ops}]
    return out


def record_copy(key):
    """A new record of the mod's own, a copy of this one, with an editor ID of its own."""
    rec = BR.record(key)['record']
    rec = json.loads(json.dumps(rec))
    base = recordio.field(rec, 'EDID') or 'Record'
    taken = set(BR.edids or {}) | {recordio.field(r, 'EDID').lower() for r in PR.records.values()}
    n, edid = 1, base + 'Copy'
    while edid.lower() in taken:
        n += 1
        edid = '%sCopy%d' % (base, n)
    recordio.set_field(rec, 'EDID', edid, label='Editor ID')
    rec['src'] = rec.get('src') or ''
    rec['copied_from'] = (PR.records.get(key) or {}).get('copied_from') or key   # (drawn like the one it came from)
    return edit('Copy ' + base, [{'op': 'record_new', 'record': rec}])


def not_while_playing():
    if playtest.game_running():
        raise ValueError('New Vegas is running: close it first (it holds its plugins open while it runs).')


def play(body):
    """Save, put the mod in the game, and start it; with a place and a spot, Play here."""
    not_while_playing()
    saved = save()
    out = {'install': install.install(GD.data_dir, saved['path'])}
    if body.get('cell'):
        cell = GD.from_key(body['cell'])
        path = os.path.join(project.BUILD_DIR, playtest.TEST_PLUGIN)
        f = GD.fields(cell)
        place = tes4.zstr(f.get('FULL', b'')) or tes4.zstr(f.get('EDID', b''))
        out['test'] = playtest.write_test_plugin(GD, cell, body['p'], path, place)
        out['test_install'] = install.install(GD.data_dir, path)      # (after the mod: newest, so it loads last)
        out['autoload'] = playtest.set_autoload(GD.data_dir, True)
    else:
        playtest.take_out_test(GD.data_dir)
        playtest.set_autoload(GD.data_dir, False)
    out['via'] = playtest.launch(GD.data_dir, load_settings().get('launch_via', 'nvse'))
    out['state'] = state()
    return out


def save():
    path = PR.plugin_path()
    n = espwrite.write(GD, PR, path)
    return {'path': path, 'bytes': n, 'state': state()}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, body, ctype='application/json', code=200, cache=False):
        if not isinstance(body, (bytes, bytearray)):
            body = json.dumps(body).encode()
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'max-age=86400' if cache else 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = dict(urllib.parse.parse_qsl(u.query))
        try:
            if u.path in ('/', '/index.html'):
                return self.file(os.path.join(WEB, 'index.html'))
            if u.path.startswith('/web/'):
                p = os.path.normpath(os.path.join(WEB, u.path[5:]))
                if not p.startswith(WEB):
                    return self.send(b'no', 'text/plain', 403)
                return self.file(p)
            if u.path == '/api/state':
                return self.send(state())
            if u.path == '/api/interiors':
                return self.send(interiors())
            if u.path == '/api/cell':
                with _lock:
                    return self.send(cell(q['id']))
            if u.path == '/api/ref':
                with _lock:
                    return self.send(ref(q['cell'], q['key']))
            if u.path == '/api/door':
                return self.send(door(q['key']))
            if u.path == '/api/nvse/latest':
                return self.send(nvse.latest())
            if u.path == '/api/plugins':
                return self.send(adopt.candidates(GD.data_dir))
            if u.path == '/api/types':
                return self.send(BR.types())
            if u.path == '/api/records':
                with _lock:
                    return self.send(BR.records(q['type'], q.get('q', '')))
            if u.path == '/api/record':
                with _lock:
                    return self.send(BR.record(q['key']))
            if u.path == '/api/resolve':
                return self.send(BR.resolve(q.get('q', '')))
            if u.path == '/api/used':
                return self.send(BR.where_used(q['key']))
            if u.path == '/api/search':
                return self.send(search(q.get('q', ''), q.get('kind', '')))
            if u.path == '/api/actor':
                with _lock:
                    return self.send(actor_parts(q['key']))
            if u.path == '/api/mesh':
                return self.send(mesh(q['path']), cache=True)
            if u.path == '/api/file':
                return self.send(GD.read_file(q['path']), 'application/octet-stream', cache=True)
            self.send(b'not found', 'text/plain', 404)
        except FileNotFoundError:
            self.send(b'not found', 'text/plain', 404)
        except Exception as e:
            self.send({'error': str(e)}, code=500)

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        try:
            n = int(self.headers.get('Content-Length') or 0)
            body = json.loads(self.rfile.read(n) or b'{}')
            with _lock:
                if u.path == '/api/nvse/download':
                    rel = nvse.latest()
                    return self.send({'version': nvse.download(rel), 'state': state()})
                if u.path == '/api/nvse/install':
                    not_while_playing()
                    return self.send({'install': nvse.install(GD.data_dir, body['version']), 'state': state()})
                if u.path == '/api/nvse/uninstall':
                    not_while_playing()
                    return self.send({'removed': nvse.uninstall(GD.data_dir), 'state': state()})
                if u.path == '/api/launch_via':
                    save_settings(launch_via='nvse' if body.get('via') == 'nvse' else 'steam')
                    return self.send(state())
                if u.path == '/api/project/new':
                    return self.send(open_project(body['name'], create=True))
                if u.path == '/api/project/open':
                    return self.send(open_project(body['name']))
                if u.path == '/api/project/adopt':
                    name = adopt.adopt(GD, os.path.join(GD.data_dir, os.path.basename(body['file'])))
                    return self.send(open_project(name))
                if not PR:
                    return self.send({'error': 'Open or start a mod first.'}, code=400)
                if u.path == '/api/edit':
                    return self.send(edit(body.get('label', 'Edit'), body['ops']))
                if u.path in ('/api/undo', '/api/redo'):
                    label = PR.undo() if u.path == '/api/undo' else PR.redo()
                    return self.send({'label': label, 'state': state()})
                if u.path == '/api/record/save':
                    rec = body['record']
                    return self.send(edit('Edit ' + (recordio.field(rec, 'EDID') or body['key']), [{'op': 'record', 'key': body['key'], 'record': rec}]))
                if u.path == '/api/record/copy':
                    return self.send(record_copy(body['key']))
                if u.path == '/api/record/revert':
                    return self.send(edit('Put back ' + body['key'], [{'op': 'record_revert', 'key': body['key']}]))
                if u.path == '/api/project/esm':
                    PR.esm = bool(body.get('on'))
                    PR.save()
                    return self.send(state())
                if u.path == '/api/save':
                    return self.send(save())
                if u.path == '/api/play':
                    return self.send(play(body))
                if u.path == '/api/install':
                    not_while_playing()
                    saved = save()
                    return self.send({'install': install.install(GD.data_dir, saved['path']), 'state': state()})
                if u.path == '/api/uninstall':
                    not_while_playing()
                    playtest.take_out_test(GD.data_dir)
                    playtest.set_autoload(GD.data_dir, False)
                    return self.send({'install': install.uninstall(GD.data_dir, PR.plugin), 'state': state()})
            self.send(b'not found', 'text/plain', 404)
        except Exception as e:
            self.send({'error': str(e)}, code=500)

    def file(self, p):
        if not os.path.isfile(p):
            return self.send(b'not found', 'text/plain', 404)
        with open(p, 'rb') as f:
            self.send(f.read(), TYPES.get(os.path.splitext(p)[1], 'application/octet-stream'))


def main():
    global GD, CATALOGUE, PR, BR
    args = sys.argv[1:]
    port = next((int(a) for a in args if a.isdigit()), PORT)
    t = time.time()
    last = load_settings().get('project')
    if last:
        try:
            PR = project.Project.open(last)
        except (OSError, ValueError):
            PR = None
    load_game(PR)
    print('%s: %d interiors, %d placeable objects (%.1fs)' % (GD.data_dir, len(GD.interiors), len(CATALOGUE),
                                                               time.time() - t), flush=True)
    # (on Windows, address reuse lets a second FOLab bind the same port, and the browser then talks to whichever
    # answers, an old one included: refuse to start twice instead)
    ThreadingHTTPServer.allow_reuse_address = False
    try:
        srv = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    except OSError:
        print('FOLab is already running on port %d: close that one first (or open http://127.0.0.1:%d/).' % (port, port))
        sys.exit(1)
    print('FOLab on http://127.0.0.1:%d/' % port, flush=True)
    if '--no-browser' not in args:
        import webbrowser
        webbrowser.open('http://127.0.0.1:%d/' % port)
    srv.serve_forever()


if __name__ == '__main__':
    main()
