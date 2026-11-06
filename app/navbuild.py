"""A navmesh for a place in the mod: what's in it as the mod has it (navgen builds the mesh, navmesh.py holds the rules),
kept in the project as plain lists and written with the plugin by espwrite. Places inside only so far: a place outside
has to join its neighbours' meshes, which means overriding them too.

    project.navmesh[cell key] = {'form': the NAVM's key, 'verts': [[x, y, z]], 'tris': [[8 numbers]],
                                 'doors': [[door ref's key, triangle]], 'sig': what the place held when it was made}

A door's link back to its triangle (XNDP) is on the door's own record, so the writer adds it there. A game place with
several meshes can't be replaced (navmesh.py: the game has no way to remove the others)."""
import hashlib
import json

import navgen
import navmesh as N

ACTORS = {'NPC_': 'ACHR', 'CREA': 'ACRE'}


class NavError(ValueError):
    """Why a place can't have a navmesh made, in words for the person asking."""


def _base_type(gd, project, bkey):
    if bkey.startswith('+'):
        return (project.records.get(bkey) or {}).get('type')
    return gd.forms[gd.from_key(bkey)][1].tag


def place_refs(gd, project, ckey):
    """Everything in a place as the mod leaves it, in the form navgen reads, with refs named by key. Things made from
    the mod's own records have no shape FOLab can read yet, so only their being there as actors or doors counts."""
    cell = None if ckey.startswith('+') else gd.from_key(ckey)
    mine = (project.cells.get(ckey) or {}).get('refs', {})
    out = []

    def add(key, bkey, p, s, leads):
        out.append({'ref': key, 'type': ACTORS.get(_base_type(gd, project, bkey), 'REFR'),
                    'base': None if bkey.startswith('+') else gd.from_key(bkey),
                    'pos': tuple(p[:3]), 'rot': tuple(p[3:6]), 'scale': s, 'leads': leads, 'bkey': bkey})
    if cell is not None:
        for r in gd.refs(cell):
            if r['base'] not in gd.forms or not r['pos']:
                continue
            key = gd.key(r['ref'])
            ch = mine.get(key) or {}
            if ch.get('removed'):
                continue
            add(key, ch.get('base') or gd.key(r['base']), ch.get('p') or list(r['pos']) + list(r['rot']),
                ch.get('s', r['scale']), bool(ch['tel']) if 'tel' in ch else r['leads'])
    for key, ch in mine.items():
        if key.startswith('+') and not ch.get('removed'):
            add(key, ch['base'], ch['p'], ch.get('s', 1.0), bool(ch.get('tel')))
    return out


def signature(refs):
    """Changes when something that matters to the mesh moves, so a mesh can say it's out of date."""
    rows = sorted([r['ref'], r['bkey'], [round(v, 1) for v in r['pos'] + r['rot']], round(r['scale'], 3), r['leads']] for r in refs)
    return hashlib.md5(json.dumps(rows).encode()).hexdigest()[:16]


def game_meshes(gd, ckey):
    """The form keys of the navmeshes the game (or an opened plugin) has for a place."""
    if ckey.startswith('+'):
        return []
    return [gd.key(gd.to_global(e[0], e[1].formid)) for e in gd.navmeshes(gd.from_key(ckey))]


def generate(gd, project, ckey):
    """A navmesh for a place: (the project's form of it, a report in words)."""
    cell = ckey
    if not ckey.startswith('+'):
        cell = gd.from_key(ckey)
        if cell in gd.ext_cells:
            raise NavError('Navmeshes for places outside aren\'t ready yet: only places inside.')
    have = game_meshes(gd, ckey)
    if len(have) > 1:
        raise NavError('This place has %d navmeshes in the game, and there\'s no way to take any away: FOLab can\'t replace them yet.' % len(have))
    refs = place_refs(gd, project, ckey)
    usable = [dict(r) for r in refs if r['base'] is not None or r['type'] != 'REFR']
    m, report = navgen.generate(gd, cell, refs=usable, floors=True)
    if m is None:
        raise NavError('There\'s nothing here to walk on: no floor with room above it.')
    linked, missed = N.link_doors(m, report.get('doors') or [])
    bad = N.validate(m)
    if bad:
        raise NavError('The mesh came out unsound (%s): this is a bug in FOLab, please report it.' % bad[0])
    old = (project.navmesh.get(ckey) or {}).get('form')
    data = {'form': have[0] if have else old, 'verts': [[round(c, 3) for c in v] for v in m['verts']], 'tris': [list(t) for t in m['tris']],
            'doors': [[d[0], d[1]] for d in m['doors']], 'sig': signature(refs)}
    return data, {'triangles': len(m['tris']), 'seconds': report.get('seconds'), 'doors': len(linked), 'doors_missed': len(missed),
                  'pieces': report.get('kept_pieces'), 'cut_off': report.get('dropped_pieces'), 'unread': report.get('unread', 0)}


def status(gd, project, ckey):
    """What a place's navmesh is like now: the Kit tab's words come from this."""
    mine = project.navmesh.get(ckey)
    game = game_meshes(gd, ckey)
    outside = not ckey.startswith('+') and gd.from_key(ckey) in gd.ext_cells
    out = {'mine': bool(mine), 'game': len(game), 'outside': outside, 'can': not outside and len(game) <= 1}
    if mine:
        out['triangles'] = len(mine['tris'])
        out['current'] = mine.get('sig') == signature(place_refs(gd, project, ckey))
    return out


def shape(gd, project, ckey):
    """The mesh to draw: {'verts': flat list, 'tris': flat list of corners}. The mod's, or else the game's."""
    mine = project.navmesh.get(ckey)
    if mine:
        return {'source': 'mod', 'verts': [c for v in mine['verts'] for c in v], 'tris': [c for t in mine['tris'] for c in t[:3]]}
    verts, tris = [], []
    if not ckey.startswith('+'):
        for i, rec in gd.navmeshes(gd.from_key(ckey)):
            m = N.read_navm(gd.plugins[i].data(rec))
            base = len(verts) // 3
            verts += [c for v in m['verts'] for c in v]
            tris += [c + base for t in m['tris'] for c in t[:3]]
    return {'source': 'game' if tris else None, 'verts': verts, 'tris': tris}


def to_record(data, cell_id, link):
    """The NAVM structure for writing: form IDs through link (a key to a form ID as the plugin numbers it)."""
    verts, tris = [tuple(v) for v in data['verts']], [tuple(t) for t in data['tris']]
    return {'version': N.VERSION, 'cell': cell_id, 'verts': verts, 'tris': tris, 'cover': [],
            'doors': [(link(k), t, 0) for k, t in data['doors']], 'ext': [], 'grid': N.build_grid(verts, tris)}


def door_tag_at(subs):
    """Where a door's XNDP goes among its subrecords: after XTEL and its kin, before the scale and the position."""
    for n, (t, _d) in enumerate(subs):
        if t in ('XSCL', 'DATA'):
            return n
    return len(subs)
