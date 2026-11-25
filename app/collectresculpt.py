"""The collectibles' sculpted models into a mod that has the first ones (the user, 25 Nov 2026: "make em look nice";
collectibles.sculpted, collectsculpt.py). Each hula doll's and jade charm's model is written again at its own path among
the mod's files, with its new picture and relief map; each MISC's bounds follow the new model. Where they stand, their
scripts and the quest are untouched.

    plan(gd, pr)       {'rows': [{'edid', 'key', 'triangles', 'box'}], 'skipped'}
    ops(gd, pr, P)     (ops, report): one Undo
"""
import json

import recordio

LABEL = 'The collectibles sculpted: hula dolls and jade charms'


def plan(gd, pr):
    import collectibles as C
    rep = {'rows': [], 'skipped': []}
    keys = {recordio.field(r, 'EDID'): k for k, r in pr.records.items() if r.get('type') == 'MISC' and r.get('subs')}
    for kind, names in (('hula', C.SPECIAL), ('jade', C.SKILLS)):
        for s in names:
            e = C._edid(kind, s)
            if e in keys:
                rep['rows'].append({'edid': e, 'key': keys[e], 'kind': kind, 'stat': s})
            else:
                rep['skipped'].append((e, 'not in the mod'))
    return rep


def ops(gd, pr, P=None):
    import collectibles as C
    import library
    P = P or plan(gd, pr)
    if not P['rows']:
        raise ValueError('the mod has no collectibles: %s' % P['skipped'][:3])
    root = library.assets_dir(pr)
    out, rep = [], {'made': [], 'skipped': list(P['skipped']), 'files': 0, 'triangles': {}}
    for r in P['rows']:
        made = C.sculpted(r['kind'], r['stat'])
        for path, data in made['files'].items():
            library._put(root, path, data)
            rep['files'] += 1
        rec = json.loads(json.dumps(pr.records[r['key']]))
        for s in rec['subs']:
            if s['tag'] == 'OBND':
                s['fields'] = [dict(q, value=int(round(v))) for q, v in zip(s['fields'], made['box'])]
            elif s['tag'] == 'MODL' and s['value'].lower() != made['mesh'][7:].lower():
                s['value'] = made['mesh'][7:]
        out.append({'op': 'record', 'key': r['key'], 'record': rec})
        rep['made'].append(r['edid'])
        rep['triangles'][r['edid']] = made['triangles']
    return out, rep
