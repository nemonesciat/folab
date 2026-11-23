"""onedoor.py RK: one door's test sheet for the game-harness session (read only): the fixed model's file, where to stand, the
heading, the 25 aim points, and the form ID as nv-rs-next's Waikiki.esp has it; doorpick's verdict before and after."""
import importlib.util, json, math, os, struct, sys

RK = sys.argv[1]
HOME = r'D:\FOLabScratch\pick'
APP = r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\app'
DOORSET = r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\.claude\worktrees\zealous-rosalind-5e1645\app\doorset.py'
ESP = r'C:\Games\nv-rs-next\mods\Waikiki.esp'
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ['FOLAB_HOME'] = HOME
os.environ['FOLAB_NO_GAME_WRITES'] = '1'
sys.path.insert(0, APP)
sys.path.insert(0, HERE)
spec = importlib.util.spec_from_file_location('doorset', DOORSET)
_ds = importlib.util.module_from_spec(spec)
sys.modules['doorset'] = _ds
spec.loader.exec_module(_ds)
import gamedata, project, server, doorswap, recordio, modelsets, tes4  # noqa: E402
import doorpick  # noqa: E402
server.not_while_playing = lambda: None
server.GD = gamedata.GameData(); server.BR = None
pr = project.Project.open('Waikiki'); server.load_game(pr); server.PR = pr
gd = server.GD
modelsets._all_sets()
name = doorswap.Names(gd, pr)
refs = {rk: (ck, r) for ck, c in pr.cells.items() for rk, r in (c.get('refs') or {}).items() if not r.get('removed')}
ck, r = refs[RK]
base = r['base']
mine = {k: piece for (piece, t), k in doorswap.records_of(pr).items()}
piece = mine.get(base)
made = modelsets.build(piece) if piece else None
rec = pr.records[base]
mpath = 'meshes' + chr(92) + recordio.field(rec, 'MODL')
fixed = None
if made:
    rel = next(k for k in made['files'] if k.lower().endswith('.nif'))
    fixed = made['files'][rel]
    out_nif = os.path.join(HERE, 'fixed_' + os.path.basename(rel))
    open(out_nif, 'wb').write(fixed)


def obnd(b):
    s = next(x for x in pr.records[b]['subs'] if x['tag'] == 'OBND') if b.startswith('+') else None
    if s:
        return [int(f['value']) for f in s['fields'] if 'name' in f]
    return list(struct.unpack('<6h', gd.fields(gd.from_key(b))['OBND'][:12]))


def model_of(b):
    try:
        if b.startswith('+'):
            rr = pr.records.get(b)
            m = recordio.field(rr, 'MODL') if rr else None
            return ('meshes' + chr(92) + m) if m else None
        t, e, f, m = gd.describe(gd.from_key(b))
        return gd.model_path(t, m) if m else None
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


lead = next(x['tel']['p'] for k, (c, x) in refs.items() if (x.get('tel') or {}).get('door') == RK)
vx, vy = lead[0] - r['p'][0], lead[1] - r['p'][1]
ln = math.hypot(vx, vy)
box = obnd(base)
P = doorpick.Picker(gd, pr, refs, model_of, group_of)
before = P.door(RK, (vx / ln, vy / ln), box)
# the same with the fixed model read in place of the installed one
real_read = gd.read_file
gd.read_file = lambda path: fixed if fixed and path.lower() == mpath.lower() else real_read(path)
P2 = doorpick.Picker(gd, pr, refs, model_of, group_of)
fbox = [int(v) for v in made['box']] if made else box
after = P2.door(RK, (vx / ln, vy / ln), fbox)
gd.read_file = real_read
# the sheet: the door's facing from its bounds, the spot 60 out, the aim points as doorpick casts them
s = float(r.get('s') or 1.0)
p = r['p']
rz = p[5]
c, sn = math.cos(rz), math.sin(rz)
b = fbox
thin_x = (b[3] - b[0]) < (b[4] - b[1])
lx, ly = (1.0, 0.0) if thin_x else (0.0, 1.0)
nx, ny = lx * c + ly * sn, -lx * sn + ly * c
if nx * vx + ny * vy < 0:
    nx, ny = -nx, -ny
width = ((b[4] - b[1]) if thin_x else (b[3] - b[0])) * s
height = (b[5] - b[2]) * s
mx, my = (b[0] + b[3]) / 2.0 * s, (b[1] + b[4]) / 2.0 * s
q = (p[0] + mx * c + my * sn, p[1] - mx * sn + my * c)
foot = p[2] + b[2] * s
spot = [round(q[0] + nx * doorpick.STAND, 1), round(q[1] + ny * doorpick.STAND, 1), round(foot, 1)]
heading = round(math.degrees(math.atan2(-nx, -ny)) % 360.0, 1)       # (0 north, clockwise: facing the door)
tx, ty = -ny, nx
aims = []
for iu in range(doorpick.GRID):
    u = (iu / (doorpick.GRID - 1) - 0.5) * width * 0.8
    for iz in range(doorpick.GRID):
        z = foot + height * (0.1 + 0.8 * iz / (doorpick.GRID - 1))
        aims.append([round(q[0] + tx * u, 1), round(q[1] + ty * u, 1), round(z, 1)])
# the form ID as nv-rs-next's Waikiki.esp has it: the REFR standing at this door's spot with its base
fid = None
pl = tes4.PluginFile(ESP)
for rr, _grp in pl.walk():
    if rr.tag != 'REFR':
        continue
    f = pl.fields(rr)
    d = f.get('DATA')
    if d and len(d) >= 24:
        x, y, z = struct.unpack_from('<3f', d)
        if abs(x - p[0]) < 0.6 and abs(y - p[1]) < 0.6 and abs(z - p[2]) < 0.6:
            fid = '%08X' % rr.formid
            break
w = gd.ext_cells.get(gd.from_key(ck))
grid = gd.cell_grid(gd.from_key(ck))
print(json.dumps({'ref': RK, 'form_id': fid, 'door': name(base)[0], 'piece': piece, 'cell': ck, 'world': gd.edid(w) if w else None,
                  'grid': grid, 'door_p': [round(v, 2) for v in p], 'spot_feet': spot, 'eye_heights_over_feet': list(doorpick.EYES),
                  'heading_deg': heading, 'aim_points': aims, 'check_before': '%d/%d' % (before['picked'], before['spots']),
                  'check_before_by': {name(k)[0] or k: v for k, v in before['by'].items()}, 'check_with_fixed_model': '%d/%d' % (after['picked'], after['spots']),
                  'fixed_model_file': out_nif if fixed else None, 'model_path_in_mods': mpath}, indent=1))
