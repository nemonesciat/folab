"""leafsweep.py: for each of FOLab's door pieces, how many of its placements doorpick finds picked at every spot with the
leaf further forward (hole pieces: doorset.LEAF_Y; flush pieces: doorset.FLUSH_OUT). Read only: the models are made in
memory and read in place of the installed ones."""
import importlib.util, json, math, os, struct, sys

HOME = r'D:\FOLabScratch\arrive'
APP = r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\.claude\worktrees\zealous-rosalind-5e1645\app'
BRANCH = r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\.claude\worktrees\zealous-rosalind-5e1645\app'
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ['FOLAB_HOME'] = HOME
os.environ['FOLAB_NO_GAME_WRITES'] = '1'
sys.path.insert(0, APP)
sys.path.insert(0, HERE)
for mod in ('doorset',):
    spec = importlib.util.spec_from_file_location(mod, os.path.join(BRANCH, mod + '.py'))
    m = importlib.util.module_from_spec(spec)
    sys.modules[mod] = m
    spec.loader.exec_module(m)
import doorset  # noqa: E402
import gamedata, project, server, doorswap, recordio, modelsets  # noqa: E402
import doorpick  # noqa: E402
server.not_while_playing = lambda: None
server.GD = gamedata.GameData(); server.BR = None
pr = project.Project.open('Waikiki'); server.load_game(pr)
gd = server.GD
modelsets._all_sets()
name = doorswap.Names(gd, pr)
refs = {rk: (ck, r) for ck, c in pr.cells.items() for rk, r in (c.get('refs') or {}).items() if not r.get('removed')}


def model_of(b):
    try:
        if b.startswith('+'):
            rr = pr.records.get(b)
            mm = recordio.field(rr, 'MODL') if rr else None
            return ('meshes' + chr(92) + mm) if mm else None
        t, e, f, mm = gd.describe(gd.from_key(b))
        return gd.model_path(t, mm) if mm else None
    except Exception:
        return None


_g = {}


def group_of(c):
    if c not in _g:
        try:
            w = gd.ext_cells.get(gd.from_key(c))
        except Exception:
            w = None
        _g[c] = ('world', w) if w is not None else ('place', c)
    return _g[c]


leads = {}
for rk, (ck, r) in refs.items():
    t = r.get('tel') or {}
    if t.get('door') and t.get('p'):
        leads.setdefault(t['door'], []).append(t['p'])
real_read = gd.read_file
out = {}
PIECES = {'door_bungalow': 'flush', 'huang_door': 'flush', 'door_royal_hawaiian': 'hole', 'door_kilauea': 'hole', 'door_goodsprings': 'hole',
          'door_usonian': 'hole', 'door_novac_a': 'hole', 'door_novac_b': 'hole', 'door_moana': 'hole'}
for piece, kind in PIECES.items():
    edid = modelsets.PIECES[piece]['edid'] if piece in modelsets.PIECES else None
    key = next((k for k, rec in pr.records.items() if rec.get('type') == 'DOOR' and recordio.field(rec, 'EDID') == edid), None) if edid else None
    if not key:
        print(piece, 'no record'); continue
    mpath = model_of(key)
    doors = [rk for rk, (ck, r) in refs.items() if r.get('base') == key and rk in leads]
    row = {}
    for v in ((0.0, 3.0, 6.0, 9.0, 12.0) if kind == 'flush' else (-3.5, -6.0, -8.5, -11.0, -13.5)):
        if kind == 'flush':
            doorset.FLUSH_OUT, doorset.LEAF_Y = v, -3.5
        else:
            doorset.FLUSH_OUT, doorset.LEAF_Y = 0.0, v
        made = modelsets.build(piece)
        nif = next(d for k, d in made['files'].items() if k.lower().endswith('.nif'))
        box = [int(x) for x in made['box']]
        gd.read_file = lambda path, nif=nif: nif if path.lower() == mpath.lower() else real_read(path)
        P = doorpick.Picker(gd, pr, refs, model_of, group_of)
        full = spots = picked = 0
        for rk in doors:
            ck, r = refs[rk]
            a = leads[rk][0]
            vx, vy = a[0] - r['p'][0], a[1] - r['p'][1]
            ln = math.hypot(vx, vy) or 1.0
            res = P.door(rk, (vx / ln, vy / ln), box)
            full += res['picked'] == res['spots']
            spots += res['spots']
            picked += res['picked']
        gd.read_file = real_read
        row[str(v)] = '%d of %d doors, %d/%d spots' % (full, len(doors), picked, spots)
        print(piece, kind, v, row[str(v)], flush=True)
    out[piece] = row
doorset.FLUSH_OUT, doorset.LEAF_Y = 0.0, -3.5
json.dump(out, open(os.path.join(HERE, 'leafsweep.json'), 'w'), indent=1)
