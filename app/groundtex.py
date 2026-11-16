"""Ground textures of FOLab's own: what a wet green island is floored with, which the Mojave's files don't hold.

The game has one truly green ground texture (the lawn's) and a few mossy ones; these are drawn here (texpaint) and
made kinds of ground the mod owns. A kind of ground is two records: a texture set (TXST: the picture and its normal
map) and a landscape texture (LTEX: the set, what it is to walk on, and optionally a grass).

GRASS IS THE DANGER. An LTEX with a grass (GNAM) grows 3D grass in the game wherever it lies in a quarter of a cell,
under other textures too. Exactly one ground here carries grass ('grass', the game's own lawn grass); the same picture
without grass is 'grass_plain'. Nothing else here grows anything, whatever game texture it is modelled on: `put`
strips the GNAM. greenground lays the grass-bearing one only in quarters that are wild at every point.

The pictures go among the mod's files (textures\\folab\\ground\\). `put` writes them and gives the ops that make the
records, with the keys the records will have: a 'land' op's textures are not among what project.apply re-points, so the
keys are worked out here as apply will give them (one per record_new, counting up from the mod's next ID): these ops
must be the first record_new ops of their apply."""
import os

import library
import recordio
import texpaint as tp

FOLDER = 'folab\\ground'
# name: (editor ID, file, how it is drawn, the game ground it is like to walk on, does it grow grass)
GROUNDS = {
    # (its grass is the game's sparse green kinds, Zion's if those files are loaded: the lawn's, at four times the
    # density, is for lawns: it was what stood "like hair on a dog")
    'grass': ('FOLabGroundJungleGrass', 'jungle_grass', lambda: tp.ground_grass(seed=80), ('ScrubBarrenWastes02GrassMix', 'ScrubBarrenWastes02GrassGreen'), True),
    'grass_plain': ('FOLabGroundJungleGrassPlain', 'jungle_grass', lambda: tp.ground_grass(seed=80), 'LGrassGreenSuburbsNoGrass', False),
    'litter': ('FOLabGroundForestFloor', 'forest_floor', lambda: tp.ground_litter(seed=81), 'LGrassGreenSuburbsNoGrass', False),
    'moss': ('FOLabGroundMoss', 'moss', lambda: tp.ground_moss(seed=82), 'LGrassGreenSuburbsNoGrass', False),
    'mossy_rock': ('FOLabGroundMossyRock', 'mossy_rock', lambda: tp.ground_mossy_rock(seed=83), 'LRockWastelandNV', False),
}
_drawn = {}


def files(name):
    """(colour DDS, normal map DDS) of a ground, drawn once a run (two grounds may share one picture)."""
    f = GROUNDS[name][1]
    if f not in _drawn:
        _drawn[f] = GROUNDS[name][2]().files(bump=2.0, shine=20)
    return _drawn[f]


def path(name, normal=False):
    return 'textures\\%s\\%s%s.dds' % (FOLDER, GROUNDS[name][1], '_n' if normal else '')


def _have(pr, edid):
    for key, rec in pr.records.items():
        if key.startswith('+') and rec.get('type') == 'LTEX' and recordio.field(rec, 'EDID') == edid:
            return key
    return None


def grows(pr, key):
    """Does this landscape texture of the mod's grow grass?"""
    rec = pr.records.get(key)
    return bool(rec) and any(s['tag'] == 'GNAM' for s in rec['subs'])


def put(gd, pr):
    """(ops, {name: LTEX key}): the pictures written among the mod's files, and the records the mod hasn't yet. A record
    the mod has from an earlier version that grows grass where it now must not has its grass taken off (in place)."""
    root = library.assets_dir(pr)
    like = {gd.edid(f): f for f, (_i, r) in gd.forms.items() if r.tag == 'LTEX'}
    first_of = lambda m: m if isinstance(m, str) else next((x for x in m if x in like), m[-1])
    ops, keys = [], {}
    nxt = pr.next_id
    for name, (edid, _file, _draw, model, grass) in GROUNDS.items():
        model = first_of(model)
        for normal in (False, True):
            data = files(name)[1 if normal else 0]
            full = os.path.join(root, path(name, normal))
            if not os.path.isfile(full) or os.path.getsize(full) != len(data):
                library._put(root, path(name, normal), data)
        have = _have(pr, edid)
        if have:
            subs = [s for s in pr.records[have]['subs'] if s['tag'] != 'GNAM']
            if grass and model in like:             # (and one made by an earlier version takes the grass it should have now)
                subs += [dict(s) for s in recordio.load(gd, like[model])['subs'] if s['tag'] == 'GNAM']
            pr.records[have]['subs'] = subs
            keys[name] = have
            continue
        inner = path(name)[len('textures\\'):]
        txst = {'type': 'TXST', 'flags': 0, 'src': '', 'subs': [
            {'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': edid + 'Set'},
            {'tag': 'TX00', 'label': 'Colour map', 'kind': 'z', 'value': inner},
            {'tag': 'TX01', 'label': 'Normal map', 'kind': 'z', 'value': inner[:-4] + '_n.dds'}]}
        # the landscape texture: a game one's own form (physics, shine) with our name and our pictures
        ltex = recordio.load(gd, like[model]) if model in like else {'type': 'LTEX', 'flags': 0, 'src': '', 'subs': [
            {'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': ''}, {'tag': 'TNAM', 'label': 'Texture set', 'kind': 'F', 'value': ''}]}
        wanted = ('EDID', 'TNAM', 'HNAM', 'SNAM') + (('GNAM',) if grass else ())
        ltex = {'type': 'LTEX', 'flags': 0, 'src': '', 'subs': [dict(s) for s in ltex['subs'] if s['tag'] in wanted]}
        for s in ltex['subs']:
            if s['tag'] == 'EDID':
                s['value'] = edid
            elif s['tag'] == 'TNAM':
                s['value'] = '+%06X' % nxt            # (the texture set made just before it)
        ops += [{'op': 'record_new', 'record': txst}, {'op': 'record_new', 'record': ltex}]
        keys[name] = '+%06X' % (nxt + 1)
        nxt += 2
    return ops, keys
