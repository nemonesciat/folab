"""Merging another plugin into the open mod.

The mod is saved as it stands, the other plugin's records are grafted onto it group by group, and the result becomes
the mod's own plugin (opened, as adopt.py does), so the Undo history starts afresh: a copy of how things were goes to
backups first, and can be put back.

Every link keeps pointing at the same thing: both plugins are renumbered to one list of masters (both their lists
together, without each other), and the other plugin's own records keep their object IDs unless the mod already uses that
one. Where both change the same record differently, the mod's copy is kept unless asked otherwise (prefer)."""
import json
import os
import shutil
import struct
import time

import adopt
import espwrite
import masterlist
import navmesh
import plugintree
import project
import schema
import tes4

CHILD_GROUPS = {tes4.G_WORLD_CHILDREN, tes4.G_CELL_CHILDREN, tes4.G_TOPIC_CHILDREN}
PARENTS = {'CELL', 'WRLD', 'DIAL'}


def candidates(S):
    """Plugins that can be merged in: the Data folder's mods, and other FOLab mods' saved plugins."""
    out = []
    mine = S.PR.plugin.lower() if S.PR else ''
    for c in adopt.candidates(S.GD.data_dir):
        if c['file'].lower() != mine and not c.get('error'):
            out.append({'file': c['file'], 'where': 'data', 'records': c['records'], 'author': c['author'], 'masters': c['masters']})
    if os.path.isdir(project.BUILD_DIR):
        for fn in sorted(os.listdir(project.BUILD_DIR)):
            if fn.lower().endswith(('.esp', '.esm')) and fn.lower() != mine and not fn.lower().startswith('folab test'):
                pf = tes4.PluginFile(os.path.join(project.BUILD_DIR, fn))
                h = pf.header
                out.append({'file': fn, 'where': 'build', 'records': h['records'], 'author': h['author'], 'masters': h['masters']})
                pf.close()
    return out


def path_of(S, item):
    base = os.path.basename(item['file'])
    d = project.BUILD_DIR if item.get('where') == 'build' else S.GD.data_dir
    return os.path.join(d, base)


def _edid(rec):
    for t, d in tes4.iter_subrecords(rec.data()):
        if t == 'EDID':
            return tes4.zstr(d)
    return ''


def _build_mod(gd, pr):
    return espwrite.Writer(gd, pr).build()


def _read_bytes(data, name):
    os.makedirs(os.path.join(project.HOME, 'cache', 'merge'), exist_ok=True)
    p = os.path.join(project.HOME, 'cache', 'merge', name)
    with open(p, 'wb') as f:
        f.write(data)
    tree = plugintree.Plugin.read(p)
    os.remove(p)
    return tree


def _rank(gd, names):
    """The merged list of masters: load order for what's loaded, then the rest as they came."""
    rows = []
    seen = set()
    for n in names:
        if n.lower() not in seen:
            seen.add(n.lower())
            rows.append(n)
    loaded = {x: i for i, x in enumerate(gd.names)}
    return sorted(rows, key=lambda n: (loaded.get(n.lower(), 1 << 20), rows.index(n)))


def _plan(gd, pr, mod_tree, other_tree, other_name):
    mod_name = pr.plugin
    mm, xm = masterlist.masters_of(mod_tree), masterlist.masters_of(other_tree)
    skip = {mod_name.lower(), other_name.lower()}
    merged = _rank(gd, [m for m in mm + xm if m.lower() not in skip])
    mown, xown = len(mm), len(xm)
    mine = {r.formid & 0xFFFFFF for r, _p, _x in mod_tree.records() if r.formid >> 24 == mown}
    theirs = sorted(r.formid & 0xFFFFFF for r, _p, _x in other_tree.records() if r.formid >> 24 == xown)
    nxt = max([project.FIRST_ID, pr.next_id] + [x + 1 for x in mine] + [x + 1 for x in theirs])
    renum = {}
    for low in theirs:
        if low in mine or low < project.FIRST_ID:
            renum[low] = nxt
            nxt += 1
    return {'merged': merged, 'renum': renum, 'next_id': nxt, 'mod_masters': mm, 'other_masters': xm}


def preview(S, item):
    """What a merge would do, nothing changed: new records, changes, those both make differently, masters added."""
    gd, pr = S.GD, S.PR
    path = path_of(S, item)
    name = os.path.basename(path)
    if name.lower() == pr.plugin.lower():
        raise ValueError('That is the mod that is open.')
    missing = _missing_masters(S, path)
    mod_tree = _read_bytes(_build_mod(gd, pr), pr.plugin)
    other = plugintree.Plugin.read(path)
    plan = _plan(gd, pr, mod_tree, other, name)
    a, b = _renumbered(pr, mod_tree, other, name, plan)
    found = {r.formid: r for r, _p, _x in a.records()}
    rows, new, same, changes = [], 0, 0, 0
    own = len(plan['merged'])
    for r, _p, _x in b.records():
        have = found.get(r.formid)
        if have is None:
            new += r.formid >> 24 == own
            changes += r.formid >> 24 != own
            continue
        if r.tag == 'NAVI':
            continue
        if _same(have, r):
            same += 1
        elif not (r.tag in PARENTS):
            rows.append({'id': '%08X' % r.formid, 'type': r.tag, 'word': schema.TYPES[r.tag][0] if r.tag in schema.TYPES else r.tag,
                         'edid': _edid(have) or _edid(r)})
    added = [m for m in plan['merged'] if m.lower() not in {x.lower() for x in plan['mod_masters']}]
    return {'file': name, 'new': new, 'changes': changes, 'same': same, 'conflicts': rows[:500], 'conflict_count': len(rows), 'masters_added': added, 'renumbered': len(plan['renum']),
            'missing': missing, 'unknown': masterlist.unknown_types(other), 'plugin': pr.plugin, 'opened': bool(pr.source), 'undo_lost': len(pr.undo_stack)}


def _missing_masters(S, path):
    pf = tes4.PluginFile(path)
    try:
        return [m for m in pf.header['masters'] if m.lower() not in S.GD.names and not os.path.isfile(os.path.join(S.GD.data_dir, m)) and m.lower() != S.PR.plugin.lower()]
    finally:
        pf.close()


def _same(a, b):
    if a.flags & ~tes4.COMPRESSED != b.flags & ~tes4.COMPRESSED:
        return False
    return a.data() == b.data()


def _renumbered(pr, mod_tree, other, other_name, plan):
    """Both trees in the merged numbering."""
    merged, renum = plan['merged'], plan['renum']
    masterlist.remap(mod_tree, len(plan['mod_masters']),
                     masterlist.mapper(plan['mod_masters'], pr.plugin, merged, renamed={other_name.lower(): renum}))
    masterlist.remap(other, len(plan['other_masters']),
                     masterlist.mapper(plan['other_masters'], other_name, merged, own_low=renum, renamed={pr.plugin.lower(): None}))
    return mod_tree, other


def graft(gd, mod_tree, other, prefer_theirs, order):
    """other's records and groups into mod_tree (both numbered alike). prefer_theirs(form ID): take their copy."""
    found = {}

    def index(kids, parent):
        for n, k in enumerate(kids):
            if isinstance(k, plugintree.Group):
                index(k.kids, k)
            else:
                found[k.formid] = (k, parent)
    for t in mod_tree.tops:
        index(t.kids, t)
    counts = {'added': 0, 'theirs': 0, 'mine': 0, 'same': 0}

    def group_in(kids, label, gtype):
        for g in kids:
            if isinstance(g, plugintree.Group) and g.gtype == gtype and g.label == label:
                return g
        g = plugintree.Group(label, gtype)
        kids.append(g)
        return g

    def children_of(have, parent, sample):
        at = parent.kids.index(have)
        nxt = parent.kids[at + 1] if at + 1 < len(parent.kids) else None
        if isinstance(nxt, plugintree.Group) and nxt.gtype == sample.gtype:
            return nxt
        g = plugintree.Group(sample.label, sample.gtype)
        parent.kids.insert(at + 1, g)
        return g

    def place_of_cell(r, parent):
        """An inside place goes in the block its object ID says; one renumbered may belong in another."""
        if parent.gtype == tes4.G_INT_SUBBLOCK:
            low = r.formid & 0xFFFFFF
            top = mod_tree.top('CELL', order)
            block = group_in(top.kids, low % 10, tes4.G_INT_BLOCK)
            return group_in(block.kids, (low // 10) % 10, tes4.G_INT_SUBBLOCK)
        return parent

    def walk(src_kids, dst):
        i = 0
        while i < len(src_kids):
            k = src_kids[i]
            nxt = src_kids[i + 1] if i + 1 < len(src_kids) else None
            kids = nxt if isinstance(nxt, plugintree.Group) and nxt.gtype in CHILD_GROUPS else None
            i += 1
            if isinstance(k, plugintree.Group):
                walk(k.kids, group_in(dst.kids, k.label, k.gtype))
                continue
            i += bool(kids)
            have = found.get(k.formid)
            if have is None:
                target = place_of_cell(k, dst) if k.tag == 'CELL' else dst
                target.kids.append(k)
                found[k.formid] = (k, target)
                counts['added'] += 1
                if kids:
                    fresh = plugintree.Group(kids.label, kids.gtype, kids.tail)
                    target.kids.append(fresh)
                    walk(kids.kids, fresh)
                continue
            old, parent = have
            if k.tag == 'NAVI':
                _merge_navi(old, k)
            elif _same(old, k):
                counts['same'] += 1
            elif prefer_theirs(k.formid):
                old.flags, old.head, old.raw = k.flags, k.head, k.raw
                counts['theirs'] += 1
            else:
                counts['mine'] += 1
            if kids:
                walk(kids.kids, children_of(old, parent, kids))
    for g in other.tops:
        if g.gtype == tes4.G_TOP:
            tag = struct.pack('<I', g.label).decode('ascii', 'replace')
            walk(g.kids, mod_tree.top(tag, order))
    return counts


def _prune(kids):
    """Without the groups a merge left empty."""
    keep = []
    for k in kids:
        if isinstance(k, plugintree.Group):
            k.kids = _prune(k.kids)
            if not k.kids:
                continue
        keep.append(k)
    return keep


def _merge_navi(mine, theirs):
    """The master index of two plugins' navmeshes: entries for all of them."""
    a, b = navmesh.read_navi(mine.data()), navmesh.read_navi(theirs.data())
    have = {e['navm'] for e in a['info']}
    info = a['info'] + [e for e in b['info'] if e['navm'] not in have]
    have = {e['navm'] for e in a['links']}
    links = a['links'] + [e for e in b['links'] if e['navm'] not in have]
    mine.set_data(navmesh.write_navi(navmesh.new_navi(info, links)), 0)


def _header_after(tree, other, masters, next_id, own_name):
    """The merged header: their list of what's overridden added to ours, the masters, its counts."""
    masterlist.set_masters(tree, masters)
    subs = list(tes4.iter_subrecords(tree.header.raw))
    theirs = next((d for t, d in tes4.iter_subrecords(other.header.raw) if t == 'ONAM'), b'')
    if theirs:
        at = next((n for n, (t, _d) in enumerate(subs) if t == 'ONAM'), None)
        if at is None:
            subs.append(('ONAM', theirs))
        else:
            have = subs[at][1]
            old = {have[i:i + 4] for i in range(0, len(have), 4)}
            subs[at] = ('ONAM', have + b''.join(theirs[i:i + 4] for i in range(0, len(theirs), 4) if theirs[i:i + 4] not in old))
    old = next(d for t, d in subs if t == 'HEDR')
    v = struct.unpack_from('<f', old)[0]
    own = len(masters)
    nid = max([next_id] + [(r.formid & 0xFFFFFF) + 1 for r, _p, _x in tree.records() if r.formid >> 24 == own])
    hedr = struct.pack('<fiI', v, tree.count(), (own << 24) | nid) + old[12:]
    subs = [(t, hedr if t == 'HEDR' else d) for t, d in subs]
    tree.header.set_data(masterlist.join(subs), tree.header.flags)
    return nid


def write_merged(gd, pr, path, prefer=None):
    """The merged plugin's bytes, and a report. prefer: {'all': 'theirs'} or {'theirs': [ids from preview]}."""
    prefer = prefer or {}
    name = os.path.basename(path)
    if name.lower() == pr.plugin.lower():
        raise ValueError('A plugin can\'t be merged into itself.')
    mod_tree = _read_bytes(_build_mod(gd, pr), pr.plugin)
    other = plugintree.Plugin.read(path)
    plan = _plan(gd, pr, mod_tree, other, name)
    a, b = _renumbered(pr, mod_tree, other, name, plan)
    picked = {int(x, 16) for x in prefer.get('theirs', ())}
    every = prefer.get('all') == 'theirs'
    counts = graft(gd, a, b, lambda fid: every or fid in picked, gd.plugins[0].top_groups())
    a.tops = _prune(a.tops)
    nid = _header_after(a, b, plan['merged'], plan['next_id'], pr.plugin)
    return a.bytes(), dict(counts, masters=plan['merged'], renumbered=len(plan['renum']), renum=plan['renum'], next_id=nid)


# ---------- the mod becomes its merged plugin ----------

def backup_project(pr, why):
    """A copy of the project and its source plugin. Returns the folder's name."""
    root = os.path.join(project.HOME, 'backups', 'mods')
    name = '%s %s %s' % (pr.name, time.strftime('%Y-%m-%d %H%M%S'), why)
    d = os.path.join(root, name)
    os.makedirs(d, exist_ok=True)
    shutil.copy2(pr.path, d)
    if pr.source and os.path.isfile(pr.source_path()):
        shutil.copy2(pr.source_path(), d)
    return name


def backups(pr):
    root = os.path.join(project.HOME, 'backups', 'mods')
    if not os.path.isdir(root):
        return []
    return sorted((x for x in os.listdir(root) if x.startswith(pr.name + ' ')), reverse=True)[:20]


def _become(S, data, next_id):
    """The mod is now this plugin, opened."""
    pr = S.PR
    folder = pr.name + ' source'
    os.makedirs(os.path.join(project.PROJECTS_DIR, folder), exist_ok=True)
    target = os.path.join(project.PROJECTS_DIR, folder, pr.plugin)
    # (FOLab has the old copy open while it's the game on show: load without it first)
    d = pr.to_dict()
    d.update(cells={}, records={}, land={}, water={}, navmesh={}, drop=[], next_id=next_id, source=folder + '/' + pr.plugin)
    name = pr.name
    S.PR = None
    S.load_game(None)
    with open(target + '.tmp', 'wb') as f:
        f.write(data)
    os.replace(target + '.tmp', target)
    with open(pr.path, 'w', encoding='utf-8') as f:
        json.dump(d, f, indent=1)
    return S.open_project(name)


def merge(S, item, prefer=None):
    pr = S.PR
    path = path_of(S, item)
    why = _missing_masters(S, path)
    if why:
        raise ValueError('%s needs %s, which isn\'t in the game\'s Data folder.' % (os.path.basename(path), ', '.join(why)))
    backup = backup_project(pr, 'before merging')
    data, report = write_merged(S.GD, pr, path, prefer)
    state = _become(S, data, report['next_id'])
    report.update(backup=backup, state=state, file=os.path.basename(path))
    report.pop('renum', None)
    return report


def restore(S, name):
    """A mod back as a backup has it (first keeping a copy of how it is now)."""
    pr = S.PR
    d = os.path.join(project.HOME, 'backups', 'mods', os.path.basename(name))
    if not os.path.isdir(d) or not name.startswith(pr.name + ' '):
        raise ValueError('There\'s no such copy of this mod.')
    backup_project(pr, 'before putting back')
    jsn = os.path.join(d, os.path.basename(pr.path))
    with open(jsn, encoding='utf-8') as f:
        kept = json.load(f)
    pname = pr.name
    path = pr.path
    S.PR = None
    S.load_game(None)
    if kept.get('source'):
        src = os.path.join(project.PROJECTS_DIR, kept['source'])
        os.makedirs(os.path.dirname(src), exist_ok=True)
        shutil.copy2(os.path.join(d, os.path.basename(src)), src)
    shutil.copy2(jsn, path)
    return S.open_project(pname)


def trim_masters(S):
    """An opened plugin without the masters nothing in it uses."""
    pr = S.PR
    if not pr.source:
        raise ValueError('A new mod names only the masters it uses already.')
    tree = _read_bytes(_build_mod(S.GD, pr), pr.plugin)
    used = masterlist.used_masters(tree)
    if used is None:
        raise ValueError('It has kinds of record FOLab doesn\'t know (%s), so it can\'t be sure nothing in them uses a master.' % ', '.join(masterlist.unknown_types(tree)))
    old = masterlist.masters_of(tree)
    keep = [m for i, m in enumerate(old) if used[i] or i == 0]
    if len(keep) == len(old):
        return {'removed': [], 'state': S.state()}
    backup = backup_project(pr, 'before trimming masters')
    masterlist.grow(tree, pr.plugin, keep)
    own = len(keep)
    nid = max([pr.next_id] + [(r.formid & 0xFFFFFF) + 1 for r, _p, _x in tree.records() if r.formid >> 24 == own])
    subs = list(tes4.iter_subrecords(tree.header.raw))
    subs = [(t, struct.pack('<fiI', struct.unpack_from('<f', d)[0], tree.count(), (own << 24) | nid) + d[12:] if t == 'HEDR' else d) for t, d in subs]
    tree.header.set_data(masterlist.join(subs), tree.header.flags)
    state = _become(S, tree.bytes(), nid)
    return {'removed': [m for m in old if m not in keep], 'backup': backup, 'state': state}


def info(S):
    return {'candidates': candidates(S), 'backups': backups(S.PR), 'plugin': S.PR.plugin, 'opened': bool(S.PR.source)}
