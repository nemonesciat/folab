"""Shacks with insides of their own (the user, 23 Nov 2026: "shacks all have the same exact inside").

townbuild lends a building the game's own place behind it, else one from its family's pool. Lonesome Road's shack barracks
(dlc04shackbarrack01), Waikiki's commonest shack, stands in the game at Cottonwood Cove in front of its two restrooms, so 286
of Waikiki's 506 shacks with a way in, and 17 other buildings, opened into one of two small restrooms. roomvary made each copy
differ (things swapped for others like them, a light of its own), but a restroom is a restroom: the same room every time.

`POOL` is the game's own shack and cabin insides (those behind its WoodShack and fuselage shacks, found from townbuild's
catalogue: Goodsprings', Novac's, Searchlight's and the camps', the fisherman's, the bootlegger's, the farmer's...). Every
place of the mod's that is a copy of a restroom (roomvary.sources) is taken out and another of the pool copied in its place
(townbuild.inside_ops: no people, keys, notes, quests' things; doors elsewhere locked), the pool dealt out evenly in a
shuffled order so neighbours differ; the same editor ID and name, the same door outside linked to the new way out both ways,
arriving where you did before outside and where the game arrives inside; anyone linked to a marker in the old place (storm
shelters) linked to a marker at the new arrival. Then each place's navmesh (the game's own when it can be taken as it is:
townbuild.copied_navmesh; else made), and roomvary makes every copy after the first of each pool place its own.

    plan(gd, pr)                [(place key, pool place editor ID)]
    ops(gd, pr, cat, chosen)    (ops, follow, report): one Undo with `after`
    after(gd, pr, follow)       the second half once ops are applied: links, navmeshes (ops, report)"""
import random

import recordio
import roomvary
import townbuild

RESTROOMS = ('CottonwoodCoveRestroomF', 'CottonwoodCoveRestroomM')
POOL = ('GSAbandonedShack', 'NovacAbandonedShack', 'NovacNoBarksShack', 'CottonwoodCoveShack', 'FarmerShackInt01',
        'SLAbandonedShack01INT', 'SLAbandonedShack02INT', 'SLAbandonedShack03INT', 'SLBeerBootleggerINT', 'SLCapCounterfeiterINT',
        'SLFishermansShackINT', 'SLLuckyJimMineHouseINT', 'SLNuclearTestShackINT', 'SLSilverPeakMineShackINT', 'SLTumbleweedRanchINT',
        'WinsResidence', 'CampForlornHope03', 'CampForlornHope04', 'QJBarracks')
SEED = 2311


def pool_insides(gd, cat):
    """{pool editor ID: the catalogue's inside (cell, exit, arrive_in)}."""
    out = {}
    for b in cat:
        for i in b.get('insides', ()):
            e = gd.edid(gd.from_key(i['cell']))
            if e in POOL and e not in out:
                out[e] = {k: v for k, v in i.items() if k != 'arrive_out'}
    return out


def plan(gd, pr, pool):
    src = roomvary.sources(gd, pr)
    targets = sorted((k for k, c in src.items() if gd.edid(c) in RESTROOMS), key=lambda k: int(k[1:], 16))
    names = sorted(pool)
    rng = random.Random(SEED)
    out = []
    deck = []
    for k in targets:
        if not deck:
            deck = names[:]
            rng.shuffle(deck)
        out.append((k, deck.pop()))
    return out


def _doors_into(pr, key):
    inside = (pr.cells.get(key) or {}).get('refs', {})
    return [(ck, rk, r) for ck, c in pr.cells.items() if ck != key for rk, r in (c.get('refs') or {}).items()
            if (r.get('tel') or {}).get('door') in inside]


def ops(gd, pr, clear_ops, pool, chosen, buildings=None):
    """clear_ops: fn(place key) -> the ops that empty a place (server._place_clear_ops); buildings: the catalogue's buildings'
    base keys (for a way out where there was none)."""
    out, follow, rep = [], [], {'places': 0, 'skipped': [], 'by_pool': {}}
    for n, (key, pick) in enumerate(chosen):
        doors = _doors_into(pr, key)
        if not doors:
            rep['skipped'].append((key, '0 doors lead in'))
            continue
        # (two buildings may share one place: every door outside leads to the new way out, which leads back to the first)
        dck, drk, dr = sorted(doors, key=lambda d: d[1])[0]
        old_exit = dr['tel']['door']
        arrive_out = (pr.cells[key]['refs'].get(old_exit) or {}).get('tel', {}).get('p')
        if not arrive_out:
            # (a place you could get into but not out of: out a step clear of the door, away from the building it is on)
            arrive_out = _out_of(pr, dck, dr, buildings or set())
            rep['given a way out'] = rep.get('given a way out', 0) + 1
        if not arrive_out:
            rep['skipped'].append((key, 'its way out leads nowhere'))
            continue
        inside_refs = pr.cells[key].get('refs', {})
        linked = [(ck, rk, r['link']) for ck, c in pr.cells.items() if ck != key for rk, r in (c.get('refs') or {}).items()
                  if r.get('link') in inside_refs]
        markers = {lk: inside_refs[lk]['base'] for _c, _r, lk in linked}
        rec = pr.records[key]
        edid, full = recordio.field(rec, 'EDID'), recordio.field(rec, 'FULL') or 'House'
        tag = 'sh%d' % n
        out += clear_ops(key)
        out.append({'op': 'record_revert', 'key': key})
        made, _kept, game_doors = townbuild.inside_ops(gd, pool[pick], tag, edid, full)
        out += made
        for ock, ork, _o in doors:
            out.append({'op': 'tel', 'cell': ock, 'ref': ork, 'tel': {'door': '$' + tag + 'x', 'p': pool[pick]['arrive_in']}})
        out.append({'op': 'tel', 'cell': '$' + tag, 'ref': '$' + tag + 'x', 'tel': {'door': drk, 'p': arrive_out}})
        for m, (lk, base) in enumerate(sorted(markers.items())):
            a = pool[pick]['arrive_in']
            out.append({'op': 'add', 'cell': '$' + tag, 'base': base, 'p': [a[0], a[1], a[2] + 8, 0.0, 0.0, a[5] if len(a) > 5 else 0.0],
                        's': 1.0, 'name': '%sm%d' % (tag, m), 'extra': {'persistent': True}})
        follow.append({'tag': tag, 'src': pool[pick]['cell'], 'doors': game_doors,
                       'links': [(ck, rk, '%sm%d' % (tag, sorted(markers).index(lk))) for ck, rk, lk in linked]})
        rep['places'] += 1
        rep['by_pool'][pick] = rep['by_pool'].get(pick, 0) + 1
    return out, follow, rep


OUT = 120.0          # (a way out given where there was none: this far from the door, away from its building)


def _out_of(pr, ck, door, buildings):
    """[x y z rx ry rz]: a step outside a door, away from the middle of the nearest catalogue building in its cell."""
    import math
    p = door['p']
    best = None
    for r in (pr.cells.get(ck) or {}).get('refs', {}).values():
        if r.get('base') in buildings and r.get('p') and not r.get('removed'):
            d = math.hypot(r['p'][0] - p[0], r['p'][1] - p[1])
            if d < 2000 and (best is None or d < best[0]):
                best = (d, r['p'])
    if best is None or best[0] < 1:
        return None
    ux, uy = (p[0] - best[1][0]) / best[0], (p[1] - best[1][1]) / best[0]
    return [round(p[0] + ux * OUT, 2), round(p[1] + uy * OUT, 2), round(p[2], 2), 0.0, 0.0, round(math.atan2(ux, uy) % math.tau, 4)]


def after(gd, pr, names, follow):
    """Once ops are applied (names: project.names as they left them): the people's links to their new markers, and each
    place's navmesh. (ops, report)."""
    import navbuild
    out, rep = [], {'links': 0, 'navmesh copied': 0, 'navmesh made': 0, 'navmesh failed': []}
    for f in follow:
        ck = names.get(f['tag'])
        for lck, lrk, mname in f['links']:
            out.append({'op': 'ref_set', 'cell': lck, 'ref': lrk, 'set': {'link': names[mname]}})
            rep['links'] += 1
        door_keys = {g: names[n] for g, n in f['doors'].items() if n in names}
        data = townbuild.copied_navmesh(gd, pr, f['src'], ck, door_keys)
        if data is not None:
            out.append({'op': 'navmesh', 'cell': ck, 'mesh': data})
            rep['navmesh copied'] += 1
            continue
        try:
            data, _r = navbuild.generate(gd, pr, ck)
            out.append({'op': 'navmesh', 'cell': ck, 'mesh': data})
            rep['navmesh made'] += 1
        except navbuild.NavError as e:
            rep['navmesh failed'].append((f['tag'], str(e)))
    return out, rep
