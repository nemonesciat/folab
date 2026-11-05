"""FOLab's local web server: the viewer page and a small JSON API over the game's data. Read-only.

    py -3 server.py [port]        then open http://127.0.0.1:8771/"""
import json
import os
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import gamedata
import nif
import tes4

PORT = 8771
WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web')
TYPES = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css',
         '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.txt': 'text/plain'}

GD = None
_meshes = {}
_lock = threading.Lock()


def is_marker(btype, edid, model):
    """Editor-only things the game never draws: markers, and the built-in forms."""
    m = model.lower()
    return btype == 'STAT' and ('marker' in edid.lower() or m.startswith(('marker', 'editor')))


def interiors():
    out = []
    for c in GD.interiors:
        f = GD.fields(c)
        out.append({'id': '%08X' % c, 'edid': tes4.zstr(f.get('EDID', b'')), 'name': tes4.zstr(f.get('FULL', b'')),
                    'refs': len(GD.cell_refs.get(c, ())), 'plugin': GD.names[c >> 24]})
    out.sort(key=lambda x: x['edid'].lower())
    return out


def cell(cid):
    c = int(cid, 16)
    things = []
    for r in GD.refs(c):
        if r['base'] not in GD.forms or not r['pos']:
            continue
        btype, edid, name, model = GD.describe(r['base'])
        if not model or btype == 'TREE':
            continue
        things.append({'ref': '%08X' % r['ref'], 'base': edid, 'type': btype, 'name': name,
                       'model': GD.model_path(btype, model), 'p': list(r['pos']) + list(r['rot']), 's': r['scale'],
                       'marker': is_marker(btype, edid, model)})
    return {'id': cid, 'edid': GD.edid(c), 'things': things}


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


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, body, ctype='application/json', code=200, cache=False):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        if cache:
            self.send_header('Cache-Control', 'max-age=86400')
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
            if u.path == '/api/interiors':
                return self.send(json.dumps(interiors()).encode())
            if u.path == '/api/cell':
                return self.send(json.dumps(cell(q['id'])).encode())
            if u.path == '/api/mesh':
                return self.send(mesh(q['path']), cache=True)
            if u.path == '/api/file':
                return self.send(GD.read_file(q['path']), 'application/octet-stream', cache=True)
            self.send(b'not found', 'text/plain', 404)
        except FileNotFoundError:
            self.send(b'not found', 'text/plain', 404)
        except Exception as e:
            self.send(json.dumps({'error': str(e)}).encode(), code=500)

    def file(self, p):
        if not os.path.isfile(p):
            return self.send(b'not found', 'text/plain', 404)
        with open(p, 'rb') as f:
            self.send(f.read(), TYPES.get(os.path.splitext(p)[1], 'application/octet-stream'))


def main():
    global GD
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    t = time.time()
    GD = gamedata.GameData()
    print('%s: %d interiors (%.1fs)' % (GD.data_dir, len(GD.interiors), time.time() - t), flush=True)
    srv = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print('FOLab on http://127.0.0.1:%d/' % port, flush=True)
    srv.serve_forever()


if __name__ == '__main__':
    main()
