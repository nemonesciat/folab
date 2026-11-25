"""Pirates out of Waikiki's lands (the user, 25 Nov 2026, on the census of pirates outside their land: "pirates shouldn't be in
waikiki lands. remove them").

By the concept map (territory.py), every pirate of the mod's own standing outside in land that isn't the pirates' goes:
- **Who:** `census` is territory.pirates_misplaced plus the parley groups' leaders (their records are named for parley,
  not pirates). The Waimanalo beach raiders (huangland's `RAIDER`, decided) stay.
- **Never what something names:** a pirate whose ref has an editor ID, or whose key any record or other ref names (a
  script, a quest, a link), isn't removed. If it's a parley group's, the group is moved instead (below); anything else
  is reported and left.
- **Parley groups standing outside pirate land** (one, 25 Nov: group 5, placed when the map read its spot as the
  pirates') are moved, leader and crew, to a fresh spot on the coast road in the pirates' land by parley's own rules
  (clear of doors, signposts, the trade ground, the Huang's posts, Hanauma, and `parley.SITE_APART` from the other
  groups, else half that). The same refs under the same keys (removed and placed again, outdoors a ref belongs to its
  cell), so every script and link still names them.
- **Their scenes, cleanly** (the user: abandoned camps, but nothing pirate-only left facing nobody): bedrolls, fires,
  tents and crates stay. The gore they hang (`GORE`) and idle markers (`IDLM`) within `PROP_R` of a removed pirate go,
  unless someone still stands within `STILL_R` of them.

    plan(gd, pr)       (rows, skipped)
    ops(gd, pr, P)     (ops, report): one Undo
    census(gd, pr)     every pirate (and parley leader) of the mod's own outside pirate land, raiders marked
"""
import json
import math
import re

import recordio

LABEL = "Pirates out of Waikiki's lands"
RAIDER = 'FOLabPirateRaider'
LEADER = re.compile(r'^FOLabParleyLeader\d+$')
GORE = re.compile(r'RaiderCorpseDressing|Gore|BloodPool|MeatHook|SkullPike', re.I)
PROP_R, STILL_R = 600.0, 800.0
ACTORS = ('NPC_', 'LVLN', 'CREA', 'LVLC')
KEY = re.compile(r'\+[0-9A-F]{6}')


def _info(gd, pr, b):
    if not b:
        return None, ''
    if b in pr.records:
        return pr.records[b].get('type'), recordio.field(pr.records[b], 'EDID') or ''
    try:
        f = gd.from_key(b)
        return gd.forms[f][1].tag, gd.edid(f) or ''
    except (KeyError, ValueError, IndexError):
        return None, ''


def census(gd, pr):
    """territory.pirates_misplaced, and the parley leaders outside pirate land (their editor IDs don't say Pirate)."""
    import territory
    out = territory.pirates_misplaced(gd, pr)
    leaders = {k for k, r in pr.records.items() if r.get('type') == 'NPC_' and LEADER.match(recordio.field(r, 'EDID') or '')}
    maps = {}
    for ck, c in pr.cells.items():
        if ck.startswith('+'):
            continue
        for rk, r in (c.get('refs') or {}).items():
            if r.get('base') in leaders and not r.get('removed') and r.get('p'):
                w = gd.ext_cells.get(gd.from_key(ck))
                if w is None:
                    continue
                m = maps.setdefault(w, territory.Map(gd, w))
                h = m.holder(r['p'][0], r['p'][1])
                if h in territory.NOT_PIRATES:
                    out.append({'holder': h, 'edid': recordio.field(pr.records[r['base']], 'EDID'), 'cell': ck, 'ref': rk,
                                'p': [round(v) for v in r['p'][:3]]})
    for r in out:
        r['raider'] = r['edid'] == RAIDER
    return out


def _named_keys(pr):
    """Every ref key something names: in records (scripts' SCRO, conditions, quests) or in other refs (links, parents)."""
    got = set(KEY.findall(json.dumps(pr.records)))
    for c in pr.cells.values():
        for rk, r in (c.get('refs') or {}).items():
            for k in KEY.findall(json.dumps({x: v for x, v in r.items() if x != 'base'})):
                if k != rk:
                    got.add(k)
    return got


def _group_of(pr, leader_row, mis):
    """The leader's crew: refs of parley crew (FOLabPirateRoadsideParley) within parley.PAIR of it."""
    import parley
    crew_base = next((k for k, r in pr.records.items() if recordio.field(r, 'EDID') == parley.ROADSIDE + 'Parley'), None)
    out = []
    for ck, c in pr.cells.items():
        for rk, r in (c.get('refs') or {}).items():
            if r.get('base') == crew_base and not r.get('removed') and r.get('p') and \
                    math.dist(r['p'][:2], leader_row['p'][:2]) < parley.PAIR:
                out.append((ck, rk))
    return out


def _new_site(gd, pr, world, others, want):
    """A coast-road spot in the pirates' land for one parley group: parley.plan's rules."""
    import factionfolk as ff
    import parley as PL
    import robots
    import secretcaches
    import territory
    import waikikilife as WL
    T = territory.Map(gd, world)
    mk = ff._markers(pr)
    road = [r['p'] for _c, _k, r in secretcaches._outside_refs(gd, pr, lambda r: 'road' in PL._ed(pr, r.get('base', '')).lower()
                                                               and PL._ed(pr, r.get('base', '')).startswith('FOLab'))]
    clear = []
    for e, d in PL.CLEAR_OF:
        k = PL._mod_key(pr, e)
        if k:
            clear += [(r['p'], d) for _c, _k, r in secretcaches._outside_refs(gd, pr, lambda r, k=k: r.get('base') == k)]
    start = mk.get('Hanauma Bay', (None, None))[1]
    posts = [r['p'] for _c, _k, r in secretcaches._outside_refs(gd, pr, lambda r: PL._ed(pr, r.get('base', '')) == secretcaches.TRAIL_POST)]
    away = [(mk[n][1], d) for n, d in PL.MARKERS_CLEAR if n in mk]
    sp = WL.Spots(gd, pr, world)
    sp.taken = ff._standing(gd, pr)
    sp.gd, sp.pr, sp.grid = gd, pr, gd.grid(world)
    cands = [p for p in road if T.holder(p[0], p[1]) == 'pirates'
             and not (start and math.hypot(p[0] - start[0], p[1] - start[1]) < PL.START_CLEAR)
             and not any(math.hypot(p[0] - q[0], p[1] - q[1]) < d for q, d in clear + away)]
    for apart in (PL.SITE_APART, PL.SITE_APART / 2):
        for p in sorted(cands, key=lambda p: -min((math.hypot(p[0] - a, p[1] - b) for a, b in others), default=0)):
            if any(math.hypot(p[0] - a, p[1] - b) < apart for a, b in others):
                continue
            doors = robots._outside_doors(gd, pr, sp.grid, {'a': (p[0], p[1])})
            spots = [s for s in ff._near(sp, p[0], p[1], 4, radii=(350, 500, 650), turns=10)
                     if secretcaches._clear(gd, pr, sp, s[0], s[1], doors, posts) and T.holder(s[0], s[1]) == 'pirates']
            if len(spots) >= want:
                return [(round(s[0], 1), round(s[1], 1), round(s[2] + 4, 1), round(math.atan2(p[0] - s[0], p[1] - s[1]), 4))
                        for s in spots[:want]], {'road': [round(v) for v in p[:2]], 'apart': apart,
                                                 'door': round(min((math.hypot(p[0] - d[0], p[1] - d[1]) for d in doors), default=1e9))}
    return None, None


def plan(gd, pr):
    rows, skipped = [], []
    mis = census(gd, pr)
    if not mis:
        return rows, [('pirates', 'none outside pirate land')]
    named = _named_keys(pr)
    leaders = [r for r in mis if LEADER.match(r['edid'])]
    in_groups = set()
    all_leaders = [r['p'] for ck, c in pr.cells.items() if not ck.startswith('+') for rk, r in (c.get('refs') or {}).items()
                   if not r.get('removed') and r.get('p') and LEADER.match(_info(gd, pr, r.get('base'))[1])]
    for L in leaders:
        crew = _group_of(pr, L, mis)
        in_groups |= {L['ref']} | {rk for _c, rk in crew}
        others = [p[:2] for p in all_leaders if math.dist(p[:2], L['p'][:2]) > 1.0]
        world = gd.ext_cells[gd.from_key(L['cell'])]
        spots, near = _new_site(gd, pr, world, others, 1 + len(crew))
        if not spots:
            skipped.append((L['edid'], 'no spot for its group in the pirates\' land: left'))
            continue
        rows.append({'what': 'move', 'refs': [(L['cell'], L['ref'])] + crew, 'to': spots, 'near': near, 'edid': L['edid'],
                     'from': L['p']})
    for r in mis:
        if r['raider'] or r['ref'] in in_groups:
            continue
        ref = pr.cells[r['cell']]['refs'][r['ref']]
        if ref.get('edid') or r['ref'] in named:
            skipped.append((r['edid'], '%s is named by something: left' % r['ref']))
            continue
        rows.append({'what': 'remove', 'cell': r['cell'], 'ref': r['ref'], 'edid': r['edid'], 'holder': r['holder'], 'p': r['p']})
    gone = [r for r in rows if r['what'] == 'remove']
    gone_keys = {r['ref'] for r in gone}
    actors = []
    for ck, c in pr.cells.items():
        if ck.startswith('+'):
            continue
        for rk, x in (c.get('refs') or {}).items():
            if rk not in gone_keys and not x.get('removed') and x.get('p') and _info(gd, pr, x.get('base'))[0] in ACTORS:
                actors.append(x['p'][:2])
    cells = {r['cell'] for r in gone}
    props = set()
    for ck, c in pr.cells.items():
        if ck.startswith('+') or not any(abs(_cxy(gd, ck)[0] - _cxy(gd, g)[0]) <= 1 and abs(_cxy(gd, ck)[1] - _cxy(gd, g)[1]) <= 1 for g in cells):
            continue
        for rk, x in (c.get('refs') or {}).items():
            if not rk.startswith('+') or x.get('removed') or not x.get('p') or rk in named:
                continue
            t, e = _info(gd, pr, x.get('base'))
            if not (t == 'IDLM' or GORE.search(e)):
                continue
            if not any(math.dist(x['p'][:2], g['p'][:2]) < PROP_R for g in gone):
                continue
            if any(math.dist(x['p'][:2], a) < STILL_R for a in actors):
                continue
            if (ck, rk) not in props:
                props.add((ck, rk))
                rows.append({'what': 'prop', 'cell': ck, 'ref': rk, 'edid': e})
    return rows, skipped


_CXY = {}


def _cxy(gd, ck):
    got = _CXY.get(ck)
    if got is None:
        try:
            got = gd.cell_grid(gd.from_key(ck)) or (10 ** 6, 10 ** 6)
        except Exception:                      # (not an outside cell)
            got = (10 ** 6, 10 ** 6)
        _CXY[ck] = got
    return got


def ops(gd, pr, P=None):
    rows, skipped = P or plan(gd, pr)
    if not rows:
        raise ValueError('nothing to do: %s' % (skipped,))
    out, rep = [], {'removed': 0, 'by_land': {}, 'props': {}, 'moved': [], 'skipped': skipped}
    for r in rows:
        if r['what'] == 'remove':
            out.append({'op': 'remove', 'cell': r['cell'], 'ref': r['ref']})
            rep['removed'] += 1
            rep['by_land'][r['holder']] = rep['by_land'].get(r['holder'], 0) + 1
        elif r['what'] == 'prop':
            out.append({'op': 'remove', 'cell': r['cell'], 'ref': r['ref']})
            rep['props'][r['edid']] = rep['props'].get(r['edid'], 0) + 1
        elif r['what'] == 'move':
            world = gd.ext_cells[gd.from_key(r['refs'][0][0])]
            grid = gd.grid(world)
            for (ck, rk), (x, y, z, rz) in zip(r['refs'], r['to']):
                old = json.loads(json.dumps(pr.cells[ck]['refs'][rk]))
                old['p'] = [x, y, z, 0.0, 0.0, rz]
                new_cell = gd.key(grid[(int(x // 4096), int(y // 4096))])
                out += [{'op': 'remove', 'cell': ck, 'ref': rk}, {'op': 'place', 'cell': new_cell, 'key': rk, 'ref': old}]
            rep['moved'].append({'group': r['edid'], 'from': r['from'][:2], 'to': [round(v) for v in r['to'][0][:2]], 'near': r['near']})
    rep['made'] = [r['ref'] if 'ref' in r else r['edid'] for r in rows]
    return out, rep
