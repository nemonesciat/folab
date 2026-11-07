"""Getting a mod ready to share: check it, clean it, see what it needs, gather its files, write a readme, make a zip in
FOLab's own releases folder. Nothing is uploaded anywhere: the zip is yours to do what you like with.

The zip is laid out as mod managers expect: Data\\<plugin>, Data\\meshes\\..., and the readme at the top. The mod's own
files are what its records (and those files' meshes) name that the game's own archives don't have. Files it needs that
nothing names, like music, go in projects\\<name> files\\ in the same layout as Data, and come along."""
import json
import os
import re
import time
import zipfile

import bsa
import espwrite
import gamedata
import health
import project
import tes4

OFFICIAL_STEMS = tuple(os.path.splitext(n)[0].lower() for n in gamedata.OFFICIAL)
FRIENDLY = {'falloutnv.esm': 'the game', 'deadmoney.esm': 'the Dead Money add-on', 'honesthearts.esm': 'the Honest Hearts add-on',
            'oldworldblues.esm': 'the Old World Blues add-on', 'lonesomeroad.esm': 'the Lonesome Road add-on',
            'gunrunnersarsenal.esm': 'the Gun Runners\' Arsenal add-on', 'classicpack.esm': 'the Classic Pack', 'mercenarypack.esm': 'the Mercenary Pack',
            'tribalpack.esm': 'the Tribal Pack', 'caravanpack.esm': 'the Caravan Pack'}
PERMISSIONS = ['Ask me before uploading this mod elsewhere or using its parts in your own mods.',
               'You can use parts of this mod in your own mods, as long as you credit me.',
               'Do whatever you like with this mod, no need to ask or credit me.']
TEXTURES_IN_MESH = re.compile(rb'[A-Za-z0-9_ \-\\/.()]+\.dds', re.I)


def releases_dir():
    return os.path.join(project.HOME, 'releases')


def extra_dir(pr):
    return os.path.join(project.PROJECTS_DIR, pr.name + ' files')


def _info_path(pr):
    return os.path.join(project.PROJECTS_DIR, pr.name + ' release.json')


def load_info(pr):
    try:
        with open(_info_path(pr), encoding='utf-8') as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    d.setdefault('version', '1.0')
    d.setdefault('notes', '')
    d.setdefault('start', '')
    d.setdefault('credits', '')
    d.setdefault('permissions', PERMISSIONS[0])
    d.setdefault('changelog', [])
    return d


def save_info(S, body):
    pr = S.PR
    d = load_info(pr)
    for k in ('version', 'notes', 'start', 'credits', 'permissions'):
        if k in body:
            d[k] = str(body[k])[:4000]
    with open(_info_path(pr), 'w', encoding='utf-8') as f:
        json.dump(d, f, indent=1)
    if 'author' in body or 'description' in body:
        pr.author = str(body.get('author', pr.author))[:511]
        pr.description = str(body.get('description', pr.description))[:511]
        pr.save()
    return info(S)


# ---------- what it's made of ----------

def _scan(S):
    """The mod's plugin written to a scratch file and read, with the file's path."""
    path = health.scratch_path(S.PR.plugin)
    with S._lock:
        data = espwrite.Writer(S.GD, S.PR).build()
    with open(path, 'wb') as f:
        f.write(data)
    return health.Scan(S.GD, path, S.PR).run(), path


def _official_archive(name):
    n = name.lower()
    return n.startswith('fallout - ') or n == 'update.bsa' or any(n.startswith(s + ' - ') for s in OFFICIAL_STEMS)


def _is_loose_game_file(gd, rel):
    """Is a loose file also in one of the game's own archives (so the mod replaces the game's)?"""
    return any(rel in a.files for a in gd.archives() if _official_archive(os.path.basename(a.path)))


def gather(S, scan):
    """Everything of the mod's own: {'files': [{rel, from, kind, replaces}], 'archives': [paths], 'missing': [rel]}."""
    gd, pr = S.GD, S.PR
    extra = extra_dir(pr)
    files, missing, archives = {}, [], set()
    want = [(kind, rel) for kind, rel in scan.assets]

    def note(kind, rel):
        rel = bsa.norm(rel)
        if rel in files:
            return True
        x = os.path.join(extra, rel)
        if os.path.isfile(x):
            files[rel] = {'rel': rel, 'from': x, 'kind': kind, 'replaces': _is_loose_game_file(gd, rel)}
            return True
        where = gd.find_file(rel)
        if where == 'loose':
            files[rel] = {'rel': rel, 'from': gd.loose_path(rel), 'kind': kind, 'replaces': _is_loose_game_file(gd, rel)}
            return True
        if where and not _official_archive(where):
            archives.add(where)
        return bool(where)
    for kind, rel in sorted(want):
        if not note(kind, rel):
            missing.append(rel)
    # (textures named by the mod's own meshes)
    for row in [r for r in files.values() if r['kind'] == 'mesh' and r['rel'].endswith('.nif')]:
        try:
            with open(row['from'], 'rb') as f:
                blob = f.read()
        except OSError:
            continue
        for m in set(TEXTURES_IN_MESH.findall(blob)):
            t = m.decode('ascii').replace('/', '\\').lower().lstrip('\\')
            i = t.find('textures\\')
            if i < 0:
                continue
            t = t[i:]
            if not note('texture', t) and t not in missing:
                missing.append(t)
    # voices and faces by the plugin's name, and an archive named for the plugin
    stem = os.path.splitext(pr.plugin)[0]
    for sub in (('sound', 'voice', pr.plugin), ('meshes', 'characters', 'facegendata', 'facegeom', pr.plugin), ('textures', 'characters', 'facegendata', 'facetint', pr.plugin)):
        d = os.path.join(gd.data_dir, *sub)
        for root, _dirs, fns in os.walk(d):
            for fn in fns:
                p = os.path.join(root, fn)
                rel = bsa.norm(os.path.relpath(p, gd.data_dir))
                files.setdefault(rel, {'rel': rel, 'from': p, 'kind': 'voice' if sub[0] == 'sound' else 'face', 'replaces': False})
    if os.path.isdir(gd.data_dir):
        for fn in os.listdir(gd.data_dir):
            if fn.lower().startswith(stem.lower() + ' - ') and fn.lower().endswith('.bsa'):
                archives.add(fn)
    # anything in the mod's files folder comes along
    if os.path.isdir(extra):
        for root, _dirs, fns in os.walk(extra):
            for fn in fns:
                p = os.path.join(root, fn)
                rel = bsa.norm(os.path.relpath(p, extra))
                files.setdefault(rel, {'rel': rel, 'from': p, 'kind': 'extra', 'replaces': _is_loose_game_file(gd, rel)})
    return {'files': sorted(files.values(), key=lambda r: r['rel']), 'archives': sorted(archives), 'missing': sorted(set(missing))}


def masters_needed(scan):
    """Each master: whether anything uses it, and in plain words."""
    out = []
    for m in scan.masters:
        out.append({'name': m, 'friendly': FRIENDLY.get(m.lower(), 'another mod'), 'official': m.lower() in FRIENDLY, 'unused': m in scan.unused})
    return out


def what_it_adds(S, scan):
    """Lines for the readme, from what the plugin holds."""
    counts = {}
    pr = S.PR
    own = scan.own
    interiors = []
    for v, (rec, path) in scan.here.items():
        k = 'new' if v >> 24 >= own else 'changed'
        counts.setdefault(rec.tag, {'new': 0, 'changed': 0})[k] += 1
        if rec.tag == 'CELL' and k == 'new' and not any(gt == tes4.G_WORLD_CHILDREN for gt, _l, _o in path):
            interiors.append(scan.edid(v))
    lines = []
    words = (('CELL', 'new place', 'place changed'), ('WEAP', 'new weapon', 'weapon changed'), ('ARMO', 'new piece of apparel', 'piece of apparel changed'),
             ('ALCH', 'new aid item', 'aid item changed'), ('AMMO', 'new ammo type', 'ammo type changed'), ('MISC', 'new misc item', 'misc item changed'),
             ('NPC_', 'new character', 'character changed'), ('CREA', 'new creature', 'creature changed'), ('QUST', 'new quest', 'quest changed'),
             ('NOTE', 'new note', 'note changed'), ('BOOK', 'new book', 'book changed'), ('TERM', 'new terminal', 'terminal changed'))
    for tag, new, ch in words:
        c = counts.get(tag)
        if not c:
            continue
        if c['new']:
            lines.append('%d %s%s' % (c['new'], new, '' if c['new'] == 1 else 's'))
        if c['changed']:
            lines.append('%d %s' % (c['changed'], ch.replace(' changed', 's changed') if c['changed'] != 1 else ch))
    placed = sum(c['new'] + c['changed'] for t, c in counts.items() if t in health.PLACED)
    if placed:
        lines.append('%d thing%s placed or changed in the world' % (placed, '' if placed == 1 else 's'))
    return lines, [p for p in interiors if p]


def readme(S, scan=None, bbcode=False):
    pr = S.PR
    rel = load_info(pr)
    close = scan is None
    path = None
    if close:
        scan, path = _scan(S)
    try:
        adds, places = what_it_adds(S, scan)
        ms = masters_needed(scan)
        H = (lambda t: '[size=4][b]%s[/b][/size]' % t) if bbcode else (lambda t: '== %s ==' % t)
        L = (lambda items: '[list]\n' + '\n'.join('[*]' + i for i in items) + '\n[/list]') if bbcode else (lambda items: '\n'.join('- ' + i for i in items))
        out = ['%s  (version %s)' % (pr.name, rel['version'])]
        if pr.author:
            out.append('by ' + pr.author)
        out.append('')
        if pr.description:
            out += [pr.description, '']
        out += [H('What it adds'), L(adds or ['(nothing yet)']), '']
        if rel['start'].strip():
            out += [H('Where to start'), rel['start'].strip(), '']
        elif places:
            out += [H('Where to go'), 'In the console (~): ' + L(['coc %s' % p for p in places[:6]]), '']
        out += [H('Requirements'), L(['Fallout: New Vegas'] + ['%s (%s)' % (m['name'], m['friendly']) for m in ms if m['name'].lower() != 'falloutnv.esm' and not m['unused']]), '']
        out += [H('Installation'),
                L(['With a mod manager: install this zip like any other mod, then switch on %s.' % pr.plugin,
                   'By hand: copy what\'s in the Data folder of this zip into the game\'s Data folder, then tick %s in the game\'s launcher under Data Files.' % pr.plugin]), '']
        out += [H('Load order'), 'Load %s after %s.' % (pr.plugin, ', '.join(m['name'] for m in ms) or 'the game'), '']
        log = rel.get('changelog') or []
        if log:
            out += [H('Changes'), L(['%s (%s): %s' % (c['version'], c.get('date', ''), c['notes']) for c in reversed(log)]), '']
        if rel['credits'].strip():
            out += [H('Credits'), rel['credits'].strip(), '']
        out += [H('Permissions'), rel['permissions'], '', 'Made with FOLab.']
        return '\n'.join(out).replace('\n\n\n', '\n\n') + '\n'
    finally:
        if close:
            scan.close()
            health._remove(path)


# ---------- the page ----------

def info(S):
    pr = S.PR
    scan, path = _scan(S)
    try:
        return {'name': pr.name, 'plugin': pr.plugin, 'author': pr.author, 'description': pr.description, 'opened': bool(pr.source),
                'release': load_info(pr), 'permissions': PERMISSIONS, 'summary': _tally(scan), 'cleanable': _cleanable(scan), 'masters': masters_needed(scan),
                'assets': gather(S, scan), 'readme': readme(S, scan), 'nexus': readme(S, scan, bbcode=True), 'extra_dir': extra_dir(pr),
                'releases': releases(), 'releases_dir': releases_dir()}
    finally:
        scan.close()
        health._remove(path)


def _tally(scan):
    out = {'error': 0, 'warn': 0, 'info': 0}
    for g in scan.report():
        out[g['sev']] += g['count']
    return out


def _clean_fixes(scan):
    rows = list(scan.issues.get('same', [])) + list(scan.issues.get('deleted_ref', [])) + list(scan.issues.get('deleted_record', []))
    return [r['fix'] for r in rows if r.get('fix')]


def _cleanable(scan):
    return {'same': scan.counts.get('same', 0), 'deleted': scan.counts.get('deleted_ref', 0) + scan.counts.get('deleted_record', 0), 'fixes': len(_clean_fixes(scan))}


def clean(S):
    """Take out what does nothing, and make deleted things safe: one undo step."""
    scan, path = _scan(S)
    try:
        fixes = _clean_fixes(scan)
    finally:
        scan.close()
        health._remove(path)
    out = health.apply_fixes(S, fixes)
    out['info'] = info(S)
    return out


def releases():
    d = releases_dir()
    if not os.path.isdir(d):
        return []
    rows = [{'file': f, 'size': os.path.getsize(os.path.join(d, f)), 'when': os.path.getmtime(os.path.join(d, f))} for f in os.listdir(d) if f.endswith('.zip')]
    return sorted(rows, key=lambda r: -r['when'])


def package(S, include_replacing=True):
    """Save the plugin and make the zip in FOLab's releases folder. Returns what went in."""
    pr = S.PR
    rel = load_info(pr)
    saved = S.save()
    scan, path = _scan(S)
    try:
        assets = gather(S, scan)
        if rel['notes'].strip() and not any(c['version'] == rel['version'] for c in rel['changelog']):
            rel['changelog'].append({'version': rel['version'], 'date': time.strftime('%Y-%m-%d'), 'notes': rel['notes'].strip()})
            with open(_info_path(pr), 'w', encoding='utf-8') as f:
                json.dump(rel, f, indent=1)
        text = readme(S, scan)
    finally:
        scan.close()
        health._remove(path)
    os.makedirs(releases_dir(), exist_ok=True)
    stem = re.sub(r'[^\w\-.]+', '_', pr.name) + '-' + re.sub(r'[^\w\-.]+', '_', rel['version'])
    target = os.path.join(releases_dir(), stem + '.zip')
    n = 1
    while os.path.exists(target):
        n += 1
        target = os.path.join(releases_dir(), '%s-%d.zip' % (stem, n))
    names = []
    tmp = target + '.tmp'
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('%s readme.txt' % pr.name, text.replace('\n', '\r\n').encode('cp1252', 'replace'))
        names.append('%s readme.txt' % pr.name)
        z.write(saved['path'], 'Data/' + pr.plugin)
        names.append('Data/' + pr.plugin)
        for fn in assets['archives']:
            z.write(os.path.join(S.GD.data_dir, fn), 'Data/' + fn)
            names.append('Data/' + fn)
        for r in assets['files']:
            if r['replaces'] and not include_replacing:
                continue
            arc = 'Data/' + r['rel'].replace('\\', '/')
            z.write(r['from'], arc)
            names.append(arc)
    os.replace(tmp, target)
    return {'zip': target, 'file': os.path.basename(target), 'size': os.path.getsize(target), 'names': names, 'missing': assets['missing'], 'state': S.state()}
