"""pickrun.py [--home H] [--app A] [--out FILE]: doorpick over every door in the mod that something leads to (read only)."""
import collections, json, math, os, struct, sys, time

ARGS = sys.argv[1:]


def opt(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


HOME = opt('--home', r'D:\FOLabScratch\pick')
APP = opt('--app', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\app')
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = opt('--out', os.path.join(HERE, 'pick_report.json'))
os.environ['FOLAB_HOME'] = HOME
os.environ['FOLAB_NO_GAME_WRITES'] = '1'
sys.path.insert(0, APP)
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8')
t0 = time.time()
say = lambda *a: print('%5.0fs' % (time.time() - t0), *a, flush=True)
import gamedata, project, server, doorswap, recordio  # noqa: E402
import doorpick  # noqa: E402
server.not_while_playing = lambda: None
server.GD = gamedata.GameData(); server.BR = None
pr = project.Project.open('Waikiki'); server.load_game(pr); server.PR = pr
gd = server.GD
name = doorswap.Names(gd, pr)
refs = {rk: (ck, r) for ck, c in pr.cells.items() for rk, r in (c.get('refs') or {}).items() if not r.get('removed')}


def model_of(base):
    try:
        if base.startswith('+'):
            rec = pr.records.get(base)
            m = recordio.field(rec, 'MODL') if rec else None
            return ('meshes' + chr(92) + m) if m else None
        t, e, f, m = gd.describe(gd.from_key(base))
        return gd.model_path(t, m) if m else None
    except Exception:
        return None


def obnd(base):
    try:
        if base.startswith('+'):
            s = next(x for x in pr.records[base]['subs'] if x['tag'] == 'OBND')
            return [int(f['value']) for f in s['fields'] if 'name' in f]
        return list(struct.unpack('<6h', gd.fields(gd.from_key(base))['OBND'][:12]))
    except Exception:
        return None


_g = {}


def group_of(ck):
    if ck not in _g:
        try:
            w = gd.ext_cells.get(gd.from_key(ck))
        except Exception:
            w = None
        _g[ck] = ('world', w) if w is not None else ('place', ck)
    return _g[ck]


leads = {}
for rk, (ck, r) in refs.items():
    t = r.get('tel') or {}
    if t.get('door') and t.get('p'):
        leads.setdefault(t['door'], []).append(t['p'])
P = doorpick.Picker(gd, pr, refs, model_of, group_of)
doors = [rk for rk in leads if rk in refs and name(refs[rk][1].get('base') or '')[1] == 'DOOR']
say('doors something leads to', len(doors))
rep = {}
for k, rk in enumerate(doors):
    ck, r = refs[rk]
    a = leads[rk][0]
    vx, vy = a[0] - r['p'][0], a[1] - r['p'][1]
    ln = math.hypot(vx, vy)
    box = obnd(r['base'])
    if ln < 1 or not box or not any(box):
        rep[rk] = {'skipped': 'no arrival in front' if ln < 1 else 'no bounds'}
        continue
    res = P.door(rk, (vx / ln, vy / ln), box)
    g = group_of(ck)
    rep[rk] = dict(res, edid=name(r['base'])[0], where='outside' if g[0] == 'world' else 'place', cell=ck,
                   by={name(b)[0] if b.startswith(('+', 'F', 'W', 'D', 'H', 'N', 'O', 'T', 'G', 'C', 'M', 'L', 'U')) and ':' in b or b.startswith('+') else b: v for b, v in res['by'].items()})
    if k % 250 == 0:
        say(k, 'of', len(doors))
done = [v for v in rep.values() if 'spots' in v]
full = sum(1 for v in done if v['picked'] == v['spots'])
say('checked', len(done), '| every spot picks the door', full, '| some', sum(1 for v in done if 0 < v['picked'] < v['spots']),
    '| none', sum(1 for v in done if v['picked'] == 0), '| spots picked %d of %d' % (sum(v['picked'] for v in done), sum(v['spots'] for v in done)))
for where in ('outside', 'place'):
    d = [v for v in done if v['where'] == where]
    say('  %s: %d doors, all spots %d, spots %d of %d' % (where, len(d), sum(1 for v in d if v['picked'] == v['spots']), sum(v['picked'] for v in d), sum(v['spots'] for v in d)))
bad = collections.Counter()
for v in done:
    if v['picked'] < v['spots']:
        bad[v['edid']] += 1
say('doors not picked everywhere, by door', bad.most_common(25))
blk = collections.Counter()
for v in done:
    for b, n in v['by'].items():
        blk[b] += n
say('what takes the pick', blk.most_common(20))
json.dump(rep, open(OUT, 'w'), indent=1)
