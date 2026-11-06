import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import shutil, struct, threading, copy
import adopt, espwrite, formlinks, gamedata, health, navbuild, plugintree, project, recordio, tes4


def check(what, ok, extra=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' ' + str(extra) if extra and not ok else ''))


gd = gamedata.GameData()
HOME = os.environ['FOLAB_HOME']


class Server:                   # (what the tools need of server.py)
    _lock = threading.RLock()
    GD, PR = gd, None

    @classmethod
    def edit(cls, label, ops):
        return {'made': cls.PR.apply(label, ops)}

    @staticmethod
    def state():
        return {}


def kinds(rep):
    return {g['kind']: g for g in rep['groups']}


def rows(rep, kind):
    return (kinds(rep).get(kind) or {'rows': []})['rows']


# ---------- the things to plant problems with ----------
by_tag = lambda tag, test=lambda f: True: next(f for f, (i, r) in gd.forms.items() if r.tag == tag and f >> 24 == 0 and test(f))
misc = by_tag('MISC')
weap = by_tag('WEAP')
chair = by_tag('FURN')
stat = by_tag('STAT')
npc = by_tag('NPC_')
door_base = by_tag('DOOR')
cells = [c for c in gd.interiors if c >> 24 == 0]


def doors_in(cell):
    return [r for r in gd.refs(cell) if r['leads'] and r['pos']]


# a game door whose other end leads back
pair = None
for c in cells:
    for r in doors_in(c):
        f = gd.ref_fields(gd.cell_refs[c][r['ref']])[1]
        t = struct.unpack_from('<I', f['XTEL'])[0]
        g = gd.to_global(0, t)
        tc = gd.ref_cell.get(g)
        if tc is not None and tc in gd.interiors:
            pair = (c, r, tc, g)
            break
    if pair:
        break
cell_a, door_a, cell_b, door_b = pair
ka, kb = gd.key(door_a['ref']), gd.key(door_b)
other_door = next(r for c in cells if c not in (cell_a, cell_b) for r in doors_in(c))
other_cell = gd.ref_cell[other_door['ref']]
plain_cell = next(c for c in cells if c not in (cell_a, cell_b, other_cell) and len(gd.refs(c)) > 5 and gd.navmeshes(c)
                  and len(gd.navmeshes(c)) == 1 and len([t for t in gd.refs(c) if t['type'] == 'REFR' and t['pos']]) > 3 and len(gd.refs(c)) < 120)
plain_refs = [t for t in gd.refs(plain_cell) if t['type'] == 'REFR' and t['pos'] and not t['persistent']]

pr = project.Project.create('Healthy')
Server.PR = pr

# ---------- a plugin with one of everything wrong ----------
own = copy.deepcopy(recordio.load(gd, weap))
recordio.set_field(own, 'EDID', 'FolabDeadLink')
recordio.set_field(own, 'NAM0', '+00FFF0', kind='F', label='Ammo')
assets = copy.deepcopy(recordio.load(gd, misc))
recordio.set_field(assets, 'EDID', 'FolabNoFiles')
recordio.set_field(assets, 'MODL', 'folabtest\\nothing.nif', label='Model')
recordio.set_field(assets, 'ICON', 'folabtest\\none.dds', label='Icon')
twin = copy.deepcopy(recordio.load(gd, misc))
recordio.set_field(twin, 'EDID', 'FolabTwin')
twin2 = copy.deepcopy(twin)
script = {'type': 'SCPT', 'flags': 0, 'src': '', 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': 'FolabNoCompile'},
                                                         {'tag': 'SCTX', 'label': 'SCTX', 'kind': 'raw', 'value': b'scn FolabNoCompile\r\nbegin GameMode\r\nend\r\n'.hex()}]}
place = copy.deepcopy(recordio.load(gd, plain_cell))
recordio.set_field(place, 'EDID', 'FolabEmptyPlace')
place2 = copy.deepcopy(place)
recordio.set_field(place2, 'EDID', 'FolabPeopled')

made = pr.apply('plant', [{'op': 'record_new', 'record': own}, {'op': 'record_new', 'record': assets}, {'op': 'record_new', 'record': twin},
                          {'op': 'record_new', 'record': twin2}, {'op': 'record_new', 'record': script},
                          {'op': 'record_new', 'record': place}, {'op': 'record_new', 'record': place2}])
k_dead, k_assets, k_t1, k_t2, k_script, k_place, k_peopled = made
pr.apply('more', [
    {'op': 'add', 'cell': k_place, 'base': gd.key(stat), 'p': [0, 0, 0, 0, 0, 0]},            # (no lights, nothing leads here)
    {'op': 'add', 'cell': k_peopled, 'base': gd.key(npc), 'p': [0, 0, 0, 0, 0, 0]},           # (characters, no navmesh)
    {'op': 'record', 'key': gd.key(misc), 'record': recordio.load(gd, misc)},                 # (identical)
    {'op': 'move', 'cell': gd.key(plain_cell), 'ref': gd.key(plain_refs[0]['ref']), 'p': list(plain_refs[0]['pos']) + list(plain_refs[0]['rot'])},
])
door1, door2, gone_ref = pr.apply('doors', [
    {'op': 'add', 'cell': k_place, 'base': gd.key(door_base), 'p': [10, 0, 0, 0, 0, 0]},
    {'op': 'add', 'cell': k_place, 'base': gd.key(door_base), 'p': [20, 0, 0, 0, 0, 0]},
    {'op': 'add', 'cell': k_place, 'base': gd.key(door_base), 'p': [30, 0, 0, 0, 0, 0]},
])
gone_key = gd.key(other_door['ref'])
pr.apply('links', [
    {'op': 'tel', 'cell': k_place, 'ref': door1, 'tel': {'door': kb, 'p': [0, 0, 0, 0, 0, 0]}},        # (that door leads elsewhere)
    {'op': 'tel', 'cell': k_place, 'ref': door2, 'tel': {'door': gone_key, 'p': [0, 0, 0, 0, 0, 0]}},  # (that door is removed)
    {'op': 'remove', 'cell': gd.key(other_cell), 'ref': gone_key},
])
# a navmesh that goes out of date
data, _r = navbuild.generate(gd, pr, gd.key(plain_cell))
pr.apply('mesh', [{'op': 'navmesh', 'cell': gd.key(plain_cell), 'mesh': data}])
check('a fresh navmesh is current', navbuild.status(gd, pr, gd.key(plain_cell))['current'])
pr.apply('after', [{'op': 'add', 'cell': gd.key(plain_cell), 'base': gd.key(stat), 'p': [5, 5, 5, 0, 0, 0]}])

rep = health.check_mod(Server)
print('  found:', {g['kind']: g['count'] for g in rep['groups']})
has = lambda kind, word: any(word.lower() in r['text'].lower() for r in rows(rep, kind))
check('a link to something that doesn\'t exist', has('link', 'FolabDeadLink'))
check('a missing mesh', has('mesh', 'folabtest\\nothing.nif'))
check('a missing texture', has('texture', 'folabtest\\none.dds'))
check('an identical record', has('same', gd.edid(misc)))
check('an identical placed thing', any(r['go'].get('ref') == gd.key(plain_refs[0]['ref']) for r in rows(rep, 'same')))
check('a door with no way back', has('no_way_back', gd.edid(door_base)))
check('a door to a removed door', len(rows(rep, 'door_gone')) == 1)
check('a script with no compile', has('no_compile', 'FolabNoCompile'))
check('a place with no lights', has('no_lights', 'FolabEmptyPlace'))
check('a place with characters and no navmesh', has('navmesh_missing', 'FolabPeopled'))
check('a navmesh out of date', any(r['go']['cell'] == gd.key(plain_cell) for r in rows(rep, 'navmesh_old')))
check('a place nothing leads to', has('unreachable', 'FolabPeopled'))
check('two things with one editor ID', has('same_edid', 'FolabTwin'))
check('a fresh mod\'s keys are the project\'s', any(r['go'].get('record') == k_dead for r in rows(rep, 'link')))
check('the removed game door was sunk, not deleted: nothing deleted', 'deleted_ref' not in kinds(rep))

# ---------- the safe fixes ----------
fixes = [r['fix'] for kind in ('link', 'same', 'no_compile', 'navmesh_old') for r in rows(rep, kind) if r.get('fix')]
out = health.apply_fixes(Server, fixes)
check('fixes: all made', not out['failed'], out['failed'])
rep2 = health.check_mod(Server)
check('fixes: dead link cleared', not rows(rep2, 'link'), rows(rep2, 'link')[:2])
check('fixes: identical changes taken out', not rows(rep2, 'same'), rows(rep2, 'same')[:2])
check('fixes: the script compiled', not rows(rep2, 'no_compile') and any(s['tag'] == 'SCDA' for s in pr.records[k_script]['subs']))
check('fixes: the navmesh made again', navbuild.status(gd, pr, gd.key(plain_cell))['current'])
pr.undo()
check('fixes are one undo step', rows(health.check_mod(Server), 'link'))
pr.redo()

# ---------- anybody's plugin, read only: a deleted ref planted in a written plugin ----------
peek = project.Project.create('Peek')
Server.PR = peek
victim = plain_refs[1]['ref']
peek.apply('m', [{'op': 'move', 'cell': gd.key(plain_cell), 'ref': gd.key(victim), 'p': list(plain_refs[1]['pos']) + list(plain_refs[1]['rot'])},
                 {'op': 'record', 'key': gd.key(misc), 'record': recordio.load(gd, misc)}])
out_path = os.path.join(HOME, 'Theirs.esp')
espwrite.write(gd, peek, out_path)
tree = plugintree.Plugin.read(out_path)
local = None
for r, parent, path in tree.records():
    if r.tag == 'REFR':
        r.flags |= tes4.DELETED
        r.set_data(b'', r.flags)
        local = r.formid
open(out_path, 'wb').write(tree.bytes())
before = open(out_path, 'rb').read()
look = health.check_file(gd, out_path)
print('  their plugin:', {g['kind']: g['count'] for g in look['groups']})
check('a look finds the deleted ref', len(rows(look, 'deleted_ref')) == 1)
check('a look offers no fixes', not any(r.get('fix') for g in look['groups'] for r in g['rows']))
check('a look changes nothing', before == open(out_path, 'rb').read())

# opened as a mod, the fix brings it back disabled and sunk, as the game needs
name = adopt.adopt(gd, out_path)
op = project.Project.open(name)
gd2 = gamedata.GameData(plugins=[p.path for p in gd.plugins] + [op.source_path()])
Server.GD, Server.PR = gd2, op
rep3 = health.check_mod(Server)
sink = [r['fix'] for r in rows(rep3, 'deleted_ref')]
check('opened, the deleted ref has a fix', len(sink) == 1 and sink[0]['action'] == 'sink', sink)
same = [r['fix'] for r in rows(rep3, 'same')]
check('opened, the identical record comes out of the plugin', any(f['action'] == 'drop' for f in same), same)
health.apply_fixes(Server, sink + same)
built = os.path.join(HOME, 'Fixed.esp')
espwrite.write(gd2, op, built)
t2 = plugintree.Plugin.read(built)
fixed = next((r for r, _p, _x in t2.records() if r.formid == local), None)
sub = dict(tes4.iter_subrecords(fixed.data()))
check('the fix: not deleted, disabled', not fixed.flags & tes4.DELETED and fixed.flags & espwrite.INITIALLY_DISABLED)
check('the fix: its base back from its master, sunk', 'NAME' in sub and struct.unpack_from('<3f', sub['DATA'])[2] == espwrite.SUNK_Z)
check('the fix: the identical record left out', not any(r.tag == 'MISC' for r, _p, _x in t2.records()))
Server.GD = gd

# ---------- no false alarms: a whole file of the game's, read as if it were someone's mod ----------
theirs = os.path.join(HOME, 'HHAsAMod.esm')
shutil.copyfile(os.path.join(gd.data_dir, 'HonestHearts.esm'), theirs)
big = health.check_file(gd, theirs)
print('  Honest Hearts as a mod:', {g['kind']: g['count'] for g in big['groups']})
n = {g['kind']: g['count'] for g in big['groups']}
check('real content: no missing masters', 'master' not in n)
check('real content: hardly a dead link', n.get('link', 0) < 30, n.get('link'))
check('real content: hardly a missing mesh', n.get('mesh', 0) < 20, n.get('mesh'))
check('real content: scripts all compiled', n.get('no_compile', 0) < 5, n.get('no_compile'))
os.remove(theirs)

# ---------- getting it ready to share: a zip in FOLab's own folder ----------
import release, zipfile


class Server2(Server):
    @classmethod
    def save(cls):
        path = cls.PR.plugin_path()
        return {'path': path, 'bytes': espwrite.write(cls.GD, cls.PR, path)}


sh = project.Project.create('Shared')
Server2.GD, Server2.PR = gd, sh
own_mesh = copy.deepcopy(recordio.load(gd, misc))
recordio.set_field(own_mesh, 'EDID', 'FolabSharedThing')
recordio.set_field(own_mesh, 'MODL', 'folabshare\\own.nif', label='Model')
sh.apply('thing', [{'op': 'record_new', 'record': own_mesh}, {'op': 'record', 'key': gd.key(misc), 'record': recordio.load(gd, misc)}])
extra = os.path.join(release.extra_dir(sh), 'meshes', 'folabshare')
os.makedirs(extra)
with open(os.path.join(extra, 'own.nif'), 'wb') as f:
    f.write(b'not really a mesh textures\\folabshare\\own.dds and more')
tex = os.path.join(release.extra_dir(sh), 'textures', 'folabshare')
os.makedirs(tex)
open(os.path.join(tex, 'own.dds'), 'wb').write(b'DDS ')
release.save_info(Server2, {'version': '1.2', 'notes': 'First go', 'author': 'Tester', 'description': 'A test.', 'credits': 'Everyone'})
info = release.info(Server2)
rels = [a['rel'] for a in info['assets']['files']]
check('share: the mod\'s own mesh is gathered', 'meshes\\folabshare\\own.nif' in rels, rels)
check('share: and the texture that mesh names', 'textures\\folabshare\\own.dds' in rels, rels)
check('share: nothing of the game\'s own', len(rels) == 2, rels)
check('share: the identical record can be cleaned', info['cleanable']['same'] == 1)
out = release.clean(Server2)
check('share: cleaned', out['fixed'] == 1 and gd.key(misc) not in sh.records)
check('share: the readme says it', 'Tester' in info['readme'] and 'A test.' in info['readme'] and '1.2' in info['readme'] and 'Everyone' in info['readme'])
z = release.package(Server2)
names = zipfile.ZipFile(z['zip']).namelist()
check('share: the zip is in FOLab\'s own folder', os.path.dirname(z['zip']) == release.releases_dir() and release.releases_dir().startswith(HOME))
check('share: the plugin and files laid out for mod managers', 'Data/Shared.esp' in names and 'Data/meshes/folabshare/own.nif' in names and 'Data/textures/folabshare/own.dds' in names, names)
check('share: with the readme', any(n.endswith('readme.txt') for n in names))
check('share: the changelog keeps it', any(c['notes'] == 'First go' for c in release.load_info(sh)['changelog']))
z2 = release.package(Server2)
check('share: a second zip doesn\'t overwrite the first', z2['zip'] != z['zip'] and os.path.isfile(z['zip']))

# ---------- My changes ----------
import changes
ch = project.Project.create('Changing')
Server2.PR = ch
mv = plain_refs[2]
ck = gd.key(plain_cell)
rec3 = copy.deepcopy(recordio.load(gd, misc))
d = next(s for s in rec3['subs'] if s['tag'] == 'DATA')
next(f for f in d['fields'] if f['name'] == 'Value')['value'] = 4242
[nw] = ch.apply('c', [{'op': 'move', 'cell': ck, 'ref': gd.key(mv['ref']), 'p': [mv['pos'][0] + 50] + list(mv['pos'][1:]) + list(mv['rot'])},
                      {'op': 'remove', 'cell': ck, 'ref': gd.key(plain_refs[3]['ref'])},
                      {'op': 'add', 'cell': ck, 'base': gd.key(stat), 'p': [1, 2, 3, 0, 0, 0]},
                      {'op': 'record', 'key': gd.key(misc), 'record': rec3}])
every = changes.everything(Server2)
place_rows = every['places'][0]['rows'] if every['places'] else []
kinds_now = sorted(k for r in place_rows for k in r['kinds'])
check('changes: by place, each kind named', kinds_now == ['moved', 'new', 'removed'], kinds_now)
moved = next(r for r in place_rows if 'moved' in r['kinds'])
check('changes: the difference from the game', moved['diff'][0]['label'] == 'Where' and moved['diff'][0]['old'] != moved['diff'][0]['new'], moved['diff'])
check('changes: go there', moved['go'] == {'cell': ck, 'ref': gd.key(mv['ref'])})
rd = changes.record_diff(Server2, gd.key(misc))['changes']
check('changes: a record\'s difference', len(rd) == 1 and '4242' in rd[0]['new'] and '4242' not in rd[0]['old'], rd)
ch.apply('one back', [moved['undo']])
check('changes: one put back, the others stay', gd.key(mv['ref']) not in ch.cells[ck]['refs'] and nw in ch.cells[ck]['refs'])
