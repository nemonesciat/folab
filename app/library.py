"""The Library: every mesh, texture and sound the game can load, and the mod's own.

Game files: an index over the archives and loose folders (searched and walked by folder), with pictures made on demand
and kept under cache/thumbs (a texture's small copy; a mesh drawn by meshthumb.py).

A mod's own: files from anywhere on the computer, kept in projects/<mod> assets/ under the same folders the game uses
(meshes\\folab\\<mod>\\..., textures\\folab\\<mod>\\...), seen through GameData's overlay as if they were game files.
Saving copies them to build/<plugin> assets/, beside the plugin; Put in game copies that into Data with the plugin
(install.py). A mesh's textures brought in with it are re-pointed by nifwrite.py to where they now live, so nothing of
the mod's can land on a game file's name. Records are made from them in a click.

Pages use one hook in server.py: get(path, q) and post(path, body) answer /api/library/<path>."""
import base64
import bisect
import hashlib
import json
import os
import re
import shutil
import struct
import threading

import bsa
import dds
import meshthumb
import nif
import nifwrite
import project
import recordio
import refprops
import schema
import stylesurvey

KINDS = {'mesh': ('meshes\\', ('.nif',)), 'texture': ('textures\\', ('.dds', '.tga', '.bmp')),
         'sound': (('sound\\', 'music\\'), ('.wav', '.ogg', '.mp3'))}
LOOSE = ('meshes', 'textures', 'sound', 'music')
AUDIO = {'.wav': 'audio/wav', '.ogg': 'audio/ogg', '.mp3': 'audio/mpeg'}
PICTURES = ('.png', '.tga', '.bmp')
SOUNDS = ('.wav', '.ogg', '.mp3')
# what a mesh can become in a click, with what's kept of the record it's modelled on (the rest of a game record is that
# thing's own: its sounds of breaking, its script)
THING_KINDS = {'STAT': 'A static: scenery you can\'t pick up', 'MISC': 'An item you can pick up',
               'CONT': 'A container', 'ACTI': 'An activator: something scripts can use'}
KEEP = {'MISC': ('EDID', 'OBND', 'FULL', 'MODL', 'DATA', 'YNAM', 'ZNAM'), 'CONT': ('EDID', 'OBND', 'FULL', 'MODL', 'DATA', 'SNAM', 'QNAM'),
        'ACTI': ('EDID', 'OBND', 'FULL', 'MODL', 'SNAM', 'VNAM')}
EMPTY_PNG = meshthumb.png_rgba(1, 1, b'\0\0\0\0')

_ctx = {}
_index = {}             # GameData -> Index (one at a time)
_busy = threading.Semaphore(3)      # (pictures being made at once: the editor answers first)


def setup(**kw):
    """The server's own parts: gd, pr, br (each a function), edit, catalogue, state."""
    _ctx.update(kw)


def slug(name):
    s = re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')
    return s[:40] or 'mod'


# ---------- the index of what the game has ----------

class Index:
    def __init__(self, gd):
        self.paths = {k: [] for k in KINDS}
        self.where = {}             # path -> (where from, size)
        kinds = {}
        for a in gd.archives():
            src = os.path.basename(a.path)
            for f, (_o, size, _c) in a.files.items():
                k = self._kind(f)
                if k:
                    kinds.setdefault(k, set()).add(f)
                    self.where[f] = (src, size)
        for top in LOOSE:
            root = os.path.join(gd.data_dir, top)
            for d, _dirs, files in os.walk(root):
                for fn in files:
                    full = os.path.join(d, fn)
                    rel = bsa.norm(os.path.relpath(full, gd.data_dir))
                    k = self._kind(rel)
                    if k:
                        kinds.setdefault(k, set()).add(rel)
                        self.where[rel] = ('Data folder', os.path.getsize(full))
        self.folders = {}           # kind -> {folder: {subfolder name: files under it}}
        for k, s in kinds.items():
            self.paths[k] = sorted(s)
            tree = self.folders[k] = {}
            for p in self.paths[k]:
                parts = p.split('\\')[:-1]
                at = ''
                for part in parts:
                    kids = tree.setdefault(at, {})
                    kids[part] = kids.get(part, 0) + 1
                    at = at + part + '\\'
        for k in KINDS:
            self.folders.setdefault(k, {})

    @staticmethod
    def _kind(f):
        for k, (top, exts) in KINDS.items():
            if f.startswith(top) and f.endswith(exts):
                return k
        return None

    def folder(self, kind, folder):
        """(subfolders [{name, path, n}], paths directly in the folder)"""
        folder = folder.lower().strip('\\')
        folder = folder + '\\' if folder else ''
        kids = self.folders[kind].get(folder, {})
        subs = [{'name': n, 'path': folder + n, 'n': c} for n, c in sorted(kids.items())]
        paths = self.paths[kind]
        i = bisect.bisect_left(paths, folder)
        out = []
        while i < len(paths) and paths[i].startswith(folder):
            if '\\' not in paths[i][len(folder):]:
                out.append(paths[i])
            i += 1
        return subs, out

    def search(self, kind, q, folder=''):
        """Paths holding every word, those whose file name does first."""
        words = q.lower().replace('/', '\\').split()
        folder = folder.lower().strip('\\')
        folder = folder + '\\' if folder else ''
        first, rest = [], []
        for p in self.paths[kind]:
            if folder and not p.startswith(folder):
                continue
            if all(w in p for w in words):
                name = p[p.rfind('\\') + 1:]
                (first if all(w in name for w in words) else rest).append(p)
        return first + rest


def index(gd):
    if gd not in _index:
        _index.clear()
        _index[gd] = Index(gd)
    return _index[gd]


# ---------- the mod's own files ----------

def assets_dir(pr):
    return os.path.join(project.PROJECTS_DIR, pr.name + ' assets')


def built_dir(pr):
    """Where a save puts the mod's files, beside its plugin."""
    return install_dir(pr.plugin)


def install_dir(plugin):
    return os.path.join(project.BUILD_DIR, os.path.splitext(plugin)[0] + ' assets')


class Overlay:
    """The open mod's own files, as GameData sees them: looked for before the game's."""

    def __init__(self, pr_fn):
        self.pr = pr_fn

    def path(self, rel):
        pr = self.pr()
        if not pr:
            return None
        p = os.path.join(assets_dir(pr), rel)
        return p if os.path.isfile(p) else None

    def meshes(self):
        pr = self.pr()
        return [r[7:] for r in own_files(pr) if r.endswith('.nif')] if pr else []


def own_files(pr):
    """Every file of the mod's own, by its path under Data."""
    root = assets_dir(pr)
    out = []
    for d, _dirs, files in os.walk(root):
        for fn in files:
            out.append(bsa.norm(os.path.relpath(os.path.join(d, fn), root)))
    return sorted(out)


def _free(root, rel):
    """rel, or rel with a number, so nothing already there is written over."""
    stem, ext = os.path.splitext(rel)
    n, cand = 1, rel
    while os.path.exists(os.path.join(root, cand)):
        n += 1
        cand = '%s_%d%s' % (stem, n, ext)
    return cand


def _put(root, rel, data):
    full = os.path.join(root, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full + '.tmp', 'wb') as f:
        f.write(data)
    os.replace(full + '.tmp', full)


def _picture_to_dds(name, data):
    """A picture from elsewhere as the game wants it, with a warning if there's something to say."""
    ext = os.path.splitext(name)[1].lower()
    w, h, px = {'.png': meshthumb.read_png, '.tga': meshthumb.read_tga, '.bmp': meshthumb.read_bmp}[ext](data)
    return dds.encode(w, h, px), w, h


def bring(gd, pr, files):
    """Files from anywhere ([(name, bytes)]) into the mod. Pictures brought with a mesh become its textures: the mesh
    is pointed at them by file name. Returns {'made': [{path, kind}], 'warnings': [text]}."""
    root = assets_dir(pr)
    me = slug(pr.name)
    made, warnings, textures = [], [], {}
    # first the pictures, so the meshes can be pointed at where they went
    for name, data in files:
        name = os.path.basename(name.replace('\\', '/'))
        stem, ext = os.path.splitext(name)
        ext = ext.lower()
        if ext == '.dds' or ext in PICTURES:
            try:
                if ext != '.dds':
                    data, w, h = _picture_to_dds(name, data)
                else:
                    i = dds.info(data)
                    if not i:
                        raise ValueError('it isn\'t a DDS picture')
                    w, h = i['w'], i['h']
            except (ValueError, struct.error, IndexError, KeyError) as e:
                warnings.append('%s was left out: %s' % (name, e))
                continue
            if w & (w - 1) or h & (h - 1):
                warnings.append('%s is %d x %d: the game is happiest with sides that are powers of two (256, 512, 1024...).' % (name, w, h))
            rel = _free(root, 'textures\\folab\\%s\\%s.dds' % (me, slug(stem)))
            _put(root, rel, data)
            textures[stem.lower()] = rel
            made.append({'path': rel, 'kind': 'texture'})
    for name, data in files:
        name = os.path.basename(name.replace('\\', '/'))
        stem, ext = os.path.splitext(name)
        ext = ext.lower()
        if ext == '.nif':
            try:
                got = nifwrite.textures_in(data)
            except (nif.NifError, struct.error, IndexError, ValueError) as e:
                warnings.append('%s was left out: it isn\'t a New Vegas mesh (%s).' % (name, e))
                continue
            changes, missing = {}, set()
            for t in got:
                base = os.path.splitext(t['path'].replace('/', '\\').rsplit('\\', 1)[-1])[0].lower()
                if base in textures:
                    changes[t['path']] = textures[base]
                elif not gd.find_file(_tex_rel(t['path'])):
                    missing.add(t['path'])
            data = nifwrite.retexture(data, changes)
            if missing:
                warnings.append('%s names textures neither brought in with it nor in the game: %s. Bring them in with the mesh, or the game will draw it purple.' % (name, ', '.join(sorted(missing))))
            rel = _free(root, 'meshes\\folab\\%s\\%s.nif' % (me, slug(stem)))
            _put(root, rel, data)
            made.append({'path': rel, 'kind': 'mesh'})
        elif ext in SOUNDS:
            rel = _free(root, 'sound\\folab\\%s\\%s%s' % (me, slug(stem), ext))
            _put(root, rel, data)
            made.append({'path': rel, 'kind': 'sound'})
        elif ext != '.dds' and ext not in PICTURES:
            warnings.append('%s was left out: FOLab takes .nif meshes, .dds .png .tga .bmp pictures and .wav .ogg .mp3 sounds.' % name)
    return {'made': made, 'warnings': warnings}


def publish(pr):
    """What a save does: the mod's files, as they are now, beside the plugin."""
    dest = built_dir(pr)
    want = own_files(pr)
    if not want:
        if os.path.isdir(dest):
            shutil.rmtree(dest)
        return 0
    root = assets_dir(pr)
    for rel in want:
        src, out = os.path.join(root, rel), os.path.join(dest, rel)
        if not os.path.isfile(out) or os.path.getsize(out) != os.path.getsize(src) or os.path.getmtime(out) < os.path.getmtime(src):
            os.makedirs(os.path.dirname(out), exist_ok=True)
            shutil.copy2(src, out)
    keep = set(want)
    for d, _dirs, files in os.walk(dest):
        for fn in files:
            full = os.path.join(d, fn)
            if bsa.norm(os.path.relpath(full, dest)) not in keep:
                os.remove(full)
    return len(want)


def uses_of_own(pr, rel):
    """The mod's records drawn with one of its files."""
    want = rel.lower()[7:] if rel.lower().startswith('meshes\\') else None
    if not want:
        return []
    return [k for k, r in pr.records.items() if any(s['kind'] == 'z' and s['tag'] in ('MODL', 'MOD2', 'MOD3', 'MOD4') and s['value'].lower() == want for s in r['subs'])]


def remove_own(gd, pr, rel):
    rel = bsa.norm(rel)
    if uses_of_own(pr, rel):
        raise ValueError('Your mod\'s records use it: take them out first.')
    root = os.path.abspath(assets_dir(pr))
    full = os.path.abspath(os.path.join(root, rel))
    if not full.startswith(root + os.sep) or not os.path.isfile(full):
        raise FileNotFoundError(rel)
    os.remove(full)


# ---------- records from the mod's files ----------

def _tex_rel(p):
    p = bsa.norm(p)
    return p if p.startswith('textures\\') else 'textures\\' + p


def bounds_of(data):
    """[x1, y1, z1, x2, y2, z2] of a mesh, whole numbers round it (what a record's bounds hold)."""
    lo, hi = [1e30] * 3, [-1e30] * 3
    for s in nif.mesh_from_nif(data):
        p = s['p']
        for a in range(3):
            v = [x for x in p[a::3] if x == x]     # (a few of the game's meshes hold not-a-number corners)
            if v:
                lo[a] = min(lo[a], min(v))
                hi[a] = max(hi[a], max(v))
    if lo[0] > hi[0]:
        return [0, 0, 0, 0, 0, 0]
    import math
    return [max(-32768, math.floor(v)) for v in lo] + [min(32767, math.ceil(v)) for v in hi]


def _sub(rtype, tag, data):
    return schema.decode_sub(rtype, tag, data)


def free_edid(wanted, taken):
    wanted = re.sub(r'[^A-Za-z0-9_]', '', wanted) or 'FOLabThing'
    n, e = 1, wanted
    while e.lower() in taken:
        n += 1
        e = '%s%d' % (wanted, n)
    return e


def record_for_mesh(gd, rel, btype, edid, name=''):
    """A record of the mod's own drawn with a mesh: a static from nothing, anything else on the lines of a plain game
    record of its kind."""
    data = gd.read_file(rel)
    model = bsa.norm(rel)
    model = model[7:] if model.startswith('meshes\\') else model
    bounds = bounds_of(data)
    obnd = _sub(btype, 'OBND', struct.pack('<6h', *bounds))
    mod = _sub(btype, 'MODL', model.encode('cp1252', 'replace') + b'\0')
    ed = _sub(btype, 'EDID', edid.encode('cp1252', 'replace') + b'\0')
    if btype == 'STAT':
        return {'type': 'STAT', 'flags': 0, 'src': '', 'subs': [ed, obnd, mod]}
    if btype not in KEEP:
        raise ValueError('FOLab can\'t make a %s from a mesh yet.' % btype)
    tpl = None
    for fid, (i, r) in gd.forms.items():
        if r.tag == btype and i == 0:
            f = gd.fields(fid)
            if 'SCRI' not in f and 'FULL' in f and 'MODL' in f and 'DEST' not in f and 'CNTO' not in f:
                tpl = fid
                break
    rec = recordio.load(gd, tpl)
    rec['subs'] = [s for s in rec['subs'] if s['tag'] in KEEP[btype]]
    for s in rec['subs']:
        if s['tag'] == 'EDID':
            s['value'] = edid
        elif s['tag'] == 'FULL':
            s['value'] = name or edid
        elif s['tag'] == 'MODL':
            s['value'] = model
        elif s['tag'] == 'OBND':
            for f, v in zip([f for f in s['fields'] if 'name' in f], bounds):
                f['value'] = v
    return rec


def retexture_mesh(gd, pr, rel, changes, stem=None):
    """A copy of a mesh among the mod's files with some of its texture paths changed. Returns its path."""
    data = gd.read_file(rel)
    new = nifwrite.retexture(data, changes)
    wrong = nifwrite.prove(data, changes)
    if wrong:
        raise ValueError('The changed mesh didn\'t read back right: ' + '; '.join(wrong))
    root = assets_dir(pr)
    base = slug(stem or os.path.splitext(os.path.basename(bsa.norm(rel)))[0])
    out = _free(root, 'meshes\\folab\\%s\\%s.nif' % (slug(pr.name), base))
    _put(root, out, new)
    return out


def retextured_record(gd, br, pr, key, new_rel, edid=None):
    """A copy of a record drawn with a retextured mesh."""
    rec = json.loads(json.dumps(br.record(key)['record']))
    model = bsa.norm(new_rel)[7:]
    was = next((s for s in rec['subs'] if s['tag'] == ('MOD2' if rec['type'] == 'ARMO' and any(x['tag'] == 'MOD2' for x in rec['subs']) else 'MODL')), None)
    if not was:
        raise ValueError('That record has no mesh.')
    i = rec['subs'].index(was)
    was['value'] = model
    # (the texture hashes and alternates that follow the old model's path no longer apply)
    while i + 1 < len(rec['subs']) and rec['subs'][i + 1]['tag'] in ('MODT', 'MODS', 'MODD', 'MO2T', 'MO2S', 'MO3T', 'MO3S', 'MO4T', 'MO4S'):
        rec['subs'].pop(i + 1)
    rec['copied_from'] = (pr.records.get(key) or {}).get('copied_from') or key
    rec['src'] = rec.get('src') or ''
    base = recordio.field(rec, 'EDID') or 'Thing'
    recordio.set_field(rec, 'EDID', free_edid(edid or base + 'Retex', _taken(br, pr)), label='Editor ID')
    return rec


def _taken(br, pr):
    return set(br.edids or {}) | {recordio.field(r, 'EDID').lower() for r in pr.records.values()}


# ---------- what a file is ----------

def _wav_info(d):
    if d[:4] != b'RIFF' or d[8:12] != b'WAVE':
        return {}
    p = 12
    out = {}
    fmt = None
    while p + 8 <= len(d):
        tag, n = struct.unpack_from('<4sI', d, p)
        if tag == b'fmt ':
            fmt = struct.unpack_from('<HHIIHH', d, p + 8)
            out.update(format={1: 'PCM', 2: 'ADPCM', 0x11: 'IMA ADPCM', 0x161: 'WMA', 0x162: 'WMA'}.get(fmt[0], 'code %d' % fmt[0]), channels=fmt[1], rate=fmt[2])
        elif tag == b'data' and fmt and fmt[3]:
            out['seconds'] = round(n / fmt[3], 2)
        p += 8 + n + (n & 1)
    return out


def info(gd, rel):
    """What the detail panel shows of a file."""
    rel = bsa.norm(rel)
    data = gd.read_file(rel)
    ext = os.path.splitext(rel)[1]
    idx = index(gd)
    src = idx.where.get(rel, ('your mod', len(data)))
    if gd.overlay and gd.overlay.path(rel):
        src = ('your mod', len(data))
    out = {'path': rel, 'bytes': len(data), 'from': src[0], 'own': src[0] == 'your mod'}
    if ext == '.nif':
        out['kind'] = 'mesh'
        try:
            shapes = nif.mesh_from_nif(data)
            out.update(shapes=len(shapes), verts=sum(len(s['p']) // 3 for s in shapes), tris=sum(len(s['i']) // 3 for s in shapes))
            if shapes:
                b = bounds_of(data)
                out['size'] = [b[3] - b[0], b[4] - b[1], b[5] - b[2]]
            out['textures'] = [{'path': t['path'], 'label': t['label'], 'found': bool(gd.find_file(_tex_rel(t['path'])))} for t in nifwrite.textures_in(data)]
        except (nif.NifError, struct.error, IndexError) as e:
            out['error'] = str(e)
        out['things'] = uses_of_mesh(rel)
    elif ext in ('.dds', '.tga', '.bmp'):
        out['kind'] = 'texture'
        out.update(dds.info(data) or {})
    else:
        out['kind'] = 'sound'
        if ext == '.wav':
            out.update(_wav_info(data))
    return out


_model_rows = {}


def uses_of_mesh(rel):
    """The game's and the mod's placeable things drawn with a mesh."""
    gd = _ctx['gd']() if _ctx else None
    if not gd:
        return []
    if _model_rows.get('for') is not gd:
        by = {}
        for row in _ctx['catalogue']():
            if row[4]:
                by.setdefault(bsa.norm(row[4]), []).append(row)
        _model_rows.update({'for': gd, 'by': by})
    out = [{'key': r[0], 'type': r[1], 'edid': r[2], 'name': r[3], 'model': r[4]} for r in _model_rows['by'].get(rel, [])[:40]]
    pr = _ctx['pr']()
    if pr:
        for k in uses_of_own(pr, rel):
            r = pr.records[k]
            out.insert(0, {'key': k, 'type': r['type'], 'edid': recordio.field(r, 'EDID'), 'name': recordio.field(r, 'FULL'), 'model': rel, 'own': True})
    return out


# ---------- pictures, kept on disk ----------

def _cache_root(gd):
    sig = getattr(gd, '_thumb_sig', None)
    if not sig:
        sig = hashlib.md5('|'.join('%s:%d:%d' % (a.path, os.path.getsize(a.path), os.path.getmtime(a.path)) for a in gd.archives()).encode()).hexdigest()[:12]
        gd._thumb_sig = sig
    return os.path.join(project.HOME, 'cache', 'thumbs', sig)


def thumb_path(gd, rel, size):
    rel = bsa.norm(rel)
    own = gd.overlay.path(rel) if gd.overlay else None
    tag = '%s|%d' % (rel, size)
    if own:
        tag += '|%d' % os.path.getmtime(own)
    else:
        p = os.path.join(gd.data_dir, rel)
        if os.path.isfile(p):
            tag += '|%d' % os.path.getmtime(p)
    h = hashlib.md5(tag.encode('utf-8', 'replace')).hexdigest()
    return os.path.join(_cache_root(gd), h[:2], h + '.png')


def make_thumb(gd, rel, size):
    """A PNG of a texture or a mesh (the empty one if there's nothing to show)."""
    rel = bsa.norm(rel)
    ext = os.path.splitext(rel)[1]
    if ext == '.dds':
        got = dds.decode(gd.read_file(rel), size)
        return meshthumb.png_rgba(*got) if got else EMPTY_PNG
    if ext == '.tga':
        return meshthumb.png_rgba(*meshthumb.read_tga(gd.read_file(rel)))
    if ext == '.bmp':
        return meshthumb.png_rgba(*meshthumb.read_bmp(gd.read_file(rel)))
    if ext == '.nif':
        shapes = nif.mesh_from_nif(gd.read_file(rel))
        small = {}

        def tex(p):
            if p not in small:
                try:
                    small[p] = dds.decode(gd.read_file(_tex_rel(p)), 32)
                except (FileNotFoundError, struct.error, ValueError):
                    small[p] = None
            return small[p]
        got = meshthumb.draw(shapes, tex, size)
        return meshthumb.png_rgba(*got) if got else EMPTY_PNG
    return EMPTY_PNG


def thumb(gd, rel, size=128):
    size = max(16, min(512, int(size)))
    path = thumb_path(gd, rel, size)
    if os.path.isfile(path):
        with open(path, 'rb') as f:
            return f.read()
    with _busy:
        try:
            png = make_thumb(gd, rel, size)
        except FileNotFoundError:
            raise
        except Exception as e:                     # (a file FOLab can't read: nothing to show, and don't try again)
            print('thumbnail', rel, e, flush=True)
            png = EMPTY_PNG
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = '%s.%d.tmp' % (path, threading.get_ident())
    with open(tmp, 'wb') as f:
        f.write(png)
    os.replace(tmp, path)
    return png


def ref_words(gd, pr, ckey, rkey):
    """What the object window says of a placed thing's settings, where the mod changed them."""
    ch = (pr.cells.get(ckey) or {'refs': {}})['refs'].get(rkey) if pr else None
    props = (ch or {}).get('props')
    if not props:
        return {}
    out = {}
    if 'owner' in props:
        out['owner'] = refprops.describe(gd, pr, props['owner'])
    if 'lock' in props:
        lk = props['lock']
        out['lock'] = dict(refprops.LOCK_LEVELS).get(lk['level'], str(lk['level'])) if lk else ''
        out['lock_key'] = refprops.describe(gd, pr, lk['key']) if lk and lk.get('key') else ''
    if 'parent' in props:
        pa = props['parent']
        out['enable_parent'] = refprops.describe(gd, pr, pa['ref']) if pa else ''
        out['enable_opposite'] = bool(pa and pa.get('opposite'))
    if 'disabled' in props:
        out['disabled'] = props['disabled']
    return out


# ---------- what the page asks ----------

def _rows(gd, paths, offset, limit):
    idx = index(gd)
    out = []
    for p in paths[offset:offset + limit]:
        src = idx.where.get(p, ('your mod', 0))
        out.append({'path': p, 'size': src[1], 'from': src[0]})
    return out


def _mine(pr, kind):
    if not pr:
        return []
    ok = KINDS[kind][1] if kind in KINDS else None
    return [p for p in own_files(pr) if not ok or p.endswith(ok)]


def get(path, q):
    """(body, content type, code, cache) for GET /api/library/<path>"""
    gd, pr = _ctx['gd'](), _ctx['pr']()
    if path == 'list':
        kind, folder, words = q.get('kind', 'mesh'), q.get('folder', ''), q.get('q', '').strip()
        offset, limit = int(q.get('offset', 0)), min(500, int(q.get('limit', 120)))
        if kind == 'mine':
            paths = _mine(pr, '')
            if words:
                paths = [p for p in paths if all(w in p for w in words.lower().split())]
            rows = []
            root = assets_dir(pr) if pr else ''
            for p in paths[offset:offset + limit]:
                rows.append({'path': p, 'size': os.path.getsize(os.path.join(root, p)), 'from': 'your mod', 'own': True})
            return {'total': len(paths), 'rows': rows, 'folders': [], 'folder': ''}, 'application/json', 200, False
        idx = index(gd)
        if words:
            paths, subs = idx.search(kind, words, folder), []
        else:
            subs, paths = idx.folder(kind, folder)
        # (the mod's own first, among the game's)
        own = []
        if pr and not folder:
            own = [p for p in _mine(pr, kind) if all(w in p for w in words.lower().split())] if words else []
        rows = [{'path': p, 'size': 0, 'from': 'your mod', 'own': True} for p in own] if offset == 0 else []
        rows += _rows(gd, paths, offset, limit)
        return {'total': len(paths) + len(own), 'rows': rows, 'folders': subs, 'folder': folder.lower().strip('\\')}, 'application/json', 200, False
    if path == 'counts':
        idx = index(gd)
        return {'mesh': len(idx.paths['mesh']), 'texture': len(idx.paths['texture']), 'sound': len(idx.paths['sound']),
                'mine': len(_mine(pr, '')), 'kinds': THING_KINDS}, 'application/json', 200, False
    if path == 'info':
        return info(gd, q['path']), 'application/json', 200, False
    if path == 'thumb':
        return thumb(gd, q['path'], q.get('w', 128)), 'image/png', 200, True
    if path == 'file':
        rel = bsa.norm(q['path'])
        return gd.read_file(rel), AUDIO.get(os.path.splitext(rel)[1], 'application/octet-stream'), 200, True
    for mod in (stylesurvey, refprops):
        try:
            return mod.get(_ctx, path, q), 'application/json', 200, False
        except KeyError as e:
            if e.args != (path,):
                raise
    return b'not found', 'text/plain', 404, False


def post(path, body):
    """What to answer POST /api/library/<path> with."""
    gd, pr, br = _ctx['gd'](), _ctx['pr'](), _ctx['br']()
    if not pr:
        raise ValueError('Start a mod first: what you bring in is kept with it.')
    if path == 'bring':
        files = [(f['name'], base64.b64decode(f['data'])) for f in body['files']]
        out = bring(gd, pr, files)
        out['state'] = _ctx['state']()
        return out
    if path == 'remove':
        remove_own(gd, pr, body['path'])
        return {'state': _ctx['state']()}
    if path == 'make':
        # a thing made from a mesh, in a click
        rel = bsa.norm(body['path'])
        stem = os.path.splitext(os.path.basename(rel))[0]
        edid = free_edid(body.get('edid') or 'FOLab' + ''.join(w.capitalize() for w in re.split(r'[^a-z0-9]+', stem.lower()) if w), _taken(br, pr))
        rec = record_for_mesh(gd, rel, body.get('type', 'STAT'), edid, body.get('name') or stem.replace('_', ' ').title())
        out = _ctx['edit']('Make %s from %s' % (edid, stem), [{'op': 'record_new', 'record': rec}])
        out['item'] = {'key': out['made'][0], 'type': rec['type'], 'edid': edid, 'name': recordio.field(rec, 'FULL'), 'model': rel}
        return out
    if path == 'texture_set':
        # a picture as a texture set record (what decals and some shaders name)
        rel = bsa.norm(body['path'])
        stem = os.path.splitext(os.path.basename(rel))[0]
        edid = free_edid(body.get('edid') or 'FOLab' + ''.join(w.capitalize() for w in re.split(r'[^a-z0-9]+', stem.lower()) if w) + 'Set', _taken(br, pr))
        inner = rel[9:] if rel.startswith('textures\\') else rel
        rec = {'type': 'TXST', 'flags': 0, 'src': '', 'subs': [
            _sub('TXST', 'EDID', edid.encode() + b'\0'), _sub('TXST', 'OBND', b'\0' * 12),
            _sub('TXST', 'TX00', inner.encode('cp1252', 'replace') + b'\0')]}
        out = _ctx['edit']('Texture set ' + edid, [{'op': 'record_new', 'record': rec}])
        out['edid'] = edid
        return out
    if path == 'retexture':
        # a mesh with other textures, a record of the mod's own drawn with it, and (if a placed one is given) that thing
        # swapped for it: one Undo
        key, changes = body['key'], {k: v for k, v in body['changes'].items() if v and v != k}
        if not changes:
            raise ValueError('Pick a new picture for at least one of its textures.')
        rel = bsa.norm(body['model'])
        new = retexture_mesh(gd, pr, rel, changes, body.get('name'))
        rec = retextured_record(gd, br, pr, key, new, body.get('edid'))
        ops = [{'op': 'record_new', 'record': rec}]
        if body.get('ref'):
            ops.append({'op': 'swap', 'cell': body['cell'], 'ref': body['ref'], 'base': '$made'})
        out = _ctx['edit']('Retexture ' + recordio.field(rec, 'EDID'), ops)
        out['model'] = new
        out['edid'] = recordio.field(rec, 'EDID')
        return out
    if path == 'retexture_file':
        # no record: just a mesh with other textures, among the mod's files
        rel = bsa.norm(body['model'])
        new = retexture_mesh(gd, pr, rel, {k: v for k, v in body['changes'].items() if v and v != k}, body.get('name'))
        return {'model': new, 'state': _ctx['state']()}
    return refprops.post(_ctx, path, body)
