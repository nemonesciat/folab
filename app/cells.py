"""List the game's interiors, or print one interior's pieces with their meshes.

    py -3 cells.py                 the 25 interiors with the most pieces
    py -3 cells.py <editor ID>     one interior: every placed thing, its base, mesh and where the mesh comes from"""
import collections
import sys
import time

import gamedata
import tes4


def main(argv):
    t = time.time()
    gd = gamedata.GameData()
    print('%s: %d plugins, %d forms, %d interiors (%.1fs)' % (gd.data_dir, len(gd.plugins), len(gd.forms),
                                                             len(gd.interiors), time.time() - t))
    if len(argv) < 2:
        sized = sorted(gd.interiors, key=lambda c: -len(gd.cell_refs.get(c, ())))
        for c in sized[:25]:
            f = gd.fields(c)
            print('  %08X %-36s %5d  %s' % (c, tes4.zstr(f.get('EDID', b'')), len(gd.cell_refs.get(c, ())),
                                           tes4.zstr(f.get('FULL', b''))))
        return
    want = argv[1].lower()
    cell = next((c for c in gd.interiors if gd.edid(c).lower() == want), None)
    if cell is None:
        print('no interior with editor ID %r' % argv[1])
        return 1
    refs = gd.refs(cell)
    kinds = collections.Counter()
    missing = 0
    print('%s %08X: %d refs, %d navmeshes' % (gd.edid(cell), cell, len(refs), len(gd.navmeshes(cell))))
    for r in refs:
        base = gd.forms.get(r['base'])
        if base is None and (r['base'] or 0) < gamedata.BUILTIN_LIMIT:
            kinds['built-in'] += 1
            continue
        if base is None:
            print('  %08X -> missing base %08X' % (r['ref'], r['base'] or 0))
            continue
        btype, bedid, _name, model = gd.describe(r['base'])
        kinds[btype] += 1
        src = gd.find_file(gd.model_path(btype, model)) if model else ''
        if model and not src:
            missing += 1
        pos = '(%7.0f %7.0f %6.0f)' % r['pos'] if r['pos'] else ''
        print('  %s %-4s %-34s %s %-56s %s' % (r['type'], btype, bedid[:34], pos, model[:56], src or ('-' if not model else 'NOT FOUND')))
    print('kinds:', dict(kinds.most_common()))
    print('meshes not found: %d' % missing)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
