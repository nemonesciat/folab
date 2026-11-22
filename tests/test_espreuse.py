import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
"""A build that takes what the last one made of the parts that didn't change (espreuse.py) writes exactly the bytes of a
build that makes everything: after edits of each kind (things placed, moved, made persistent, swapped for a character of
the mod's own; ground beside other ground; records; water; a place's details; a navmesh and its doors), after a change
made by hand, and read back from its file in a fresh start."""
import copy
import espreuse
import espwrite
import gamedata
import land
import navbuild
import project


def check(what, ok, more=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % more if more and not ok else ''))


gd = gamedata.GameData()
pr = project.Project.create('Reuse Test')
out = pr.plugin_path()
fresh = os.path.join(project.HOME, 'fresh.esp')


def builds_alike(what, hits=None):
    """The build reusing, then one making everything; the same bytes. Returns the reusing writer."""
    w = espwrite.Writer(gd, pr)
    w.reuse_path = out + '.reuse'
    data = w.build()
    w.reuse.save()
    with open(out, 'wb') as f:
        f.write(data)
    whole = espwrite.Writer(gd, pr).build()
    ok = data == whole
    check(what + ': the same bytes as a build from scratch', ok, '%d vs %d bytes' % (len(data), len(whole)))
    if hits is not None:
        check(what + ': %s' % hits[0], hits[1](w.reuse), 'took %d, made %d' % (w.reuse.hits, w.reuse.misses))
    return w


world = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
g = gd.grid(world)
here, east = g[(-18, 0)], g[(-17, 0)]
hk, ek = gd.key(here), gd.key(east)
inside = next(c for c in sorted(gd.interiors) if len(gd.navmeshes(c)) == 1 and 20 < len(gd.refs(c)) < 150 and any(r['leads'] for r in gd.refs(c)))
ik = gd.key(inside)
stuff = next(gd.key(f) for f, (i, rec) in gd.forms.items() if rec.tag == 'STAT' and i == 0)
crate = next(f for f, (i, rec) in gd.forms.items() if rec.tag == 'CONT' and i == 0 and gd.edid(f).startswith('Footlocker'))
person = next(gd.key(f) for f, (i, rec) in gd.forms.items() if rec.tag == 'NPC_' and i == 0)
import recordio
crate_rec = recordio.load(gd, crate)

ops = [{'op': 'add', 'cell': ik, 'base': stuff, 'p': [10.0 * n, 0, 0, 0, 0, 0]} for n in range(5)]
ops += [{'op': 'add', 'cell': hk, 'base': stuff, 'p': [-73000 + 100.0 * n, 2000, 8000, 0, 0, 0]} for n in range(5)]
ops += [{'op': 'add', 'cell': hk, 'base': stuff, 'p': [-73000, 2100, 8000, 0, 0, 0], 'extra': {'persistent': True}}]
ops += [{'op': 'record', 'key': gd.key(crate), 'record': crate_rec},
        {'op': 'record_new', 'record': {'type': 'MISC', 'flags': 0, 'src': '', 'subs': [
            {'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': 'ReuseTestThing'}]}},
        {'op': 'water', 'cell': hk, 'h': 9000.0}]
for ck, cell in ((hk, here), (ek, east)):
    L = land.decode(gd, gd.land[cell], {})
    L['h'] = [h + 200 for h in L['h']]
    ops.append({'op': 'land', 'cell': ck, 'land': L})
made = pr.apply('Things', ops)
nav, _rep = navbuild.generate(gd, pr, ik)
pr.apply('Navmesh', [{'op': 'navmesh', 'cell': ik, 'mesh': nav}])
builds_alike('the first build', ('everything made', lambda r: r.hits == 0 and r.misses > 0))
builds_alike('again, nothing changed', ('everything taken', lambda r: r.misses == 0 and r.hits > 0))

# one cell's ground: it and the cell beside it (whose normals look across) are made again, nothing else
L = copy.deepcopy(pr.land[ek])
L['h'][0] += 64
pr.apply('Ground', [{'op': 'land', 'cell': ek, 'land': L}])
w = builds_alike('ground changed beside other ground')
check('… both cells\' land made again, nothing else', w.reuse.misses == 2, str(w.reuse.misses))

pr.apply('Move', [{'op': 'move', 'cell': ik, 'ref': made[0], 'p': [55, 5, 5, 0, 0, 0]}])
builds_alike('a thing moved')
pr.apply('Persist', [{'op': 'persist', 'cell': hk, 'ref': made[5]}])
builds_alike('a thing outside made persistent')
crate_rec = copy.deepcopy(pr.records[gd.key(crate)])
crate_rec['subs'] += [s for s in crate_rec['subs'] if s['tag'] == 'CNTO'][:3]
pr.apply('Crate', [{'op': 'record', 'key': gd.key(crate), 'record': crate_rec}])
builds_alike('things added to a container', ('only the container made', lambda r: r.misses == 1))
pr.apply('Person', [{'op': 'record_new', 'record': recordio.load(gd, gd.from_key(person))}])
mine = pr.undo_stack and [k for k in pr.records if k.startswith('+')][-1]
pr.apply('Swap', [{'op': 'swap', 'cell': ik, 'ref': made[1], 'base': mine}])
builds_alike('a thing swapped for a character of the mod\'s own (an ACHR now)')
pr.apply('Info', [{'op': 'cellinfo', 'cell': hk, 'info': {'XCMO': ''}}])
builds_alike('a place\'s details')
pr.apply('Water', [{'op': 'water', 'cell': hk, 'h': None}])
builds_alike('water back to the world\'s')
pr.apply('Gone', [{'op': 'remove', 'cell': ik, 'ref': made[2]}])
builds_alike('a thing taken out (its navmesh unchanged)')
pr.undo()
builds_alike('… and put back by Undo')

# by hand, not through an edit: sync() at the build finds it
pr.records[mine]['subs'].append({'tag': 'FULL', 'label': 'Name', 'kind': 'z', 'value': 'By Hand'})
builds_alike('a record changed by hand', ('only that record made', lambda r: r.misses == 1))

# a fresh start: read back from the .reuse file
espreuse.forget()
pr = project.Project.open('Reuse Test')
w = espwrite.Writer(gd, pr)                 # (the page's list of masters first, as FOLab shows it after opening)
w.reuse_path = out + '.reuse'
w._start_reuse(sync=False)
w.plan()
w.reuse.remember()
builds_alike('read back from its file, the masters worked out first', ('everything taken', lambda r: r.misses == 0 and r.hits > 0))
check('espwrite.write keeps it beside the build', espwrite.write(gd, pr, out) == os.path.getsize(out) and os.path.isfile(out + '.reuse'))
