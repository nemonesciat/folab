"""Read only: every modelsets piece (the live app's sets, this branch's doorset/huangset over them) for parts drawn by
mistake: a box whose six faces are all left out (collision alone) but that carries a look, which the live modelmake
draws as a slab. Also notes which of those pieces Waikiki has a record of (they're in its own files, to write again)."""
import collections
import importlib.util
import json
import os
import sys

APP = r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\app'
MINE = r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\.claude\worktrees\overnight-richer-interiors-664965\app'
os.environ['FOLAB_HOME'] = r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\packaging\out\FOLab'
os.environ['FOLAB_NO_GAME_WRITES'] = '1'
sys.path.insert(0, APP)
sys.stdout.reconfigure(encoding='utf-8')
import modelsets, project, recordio  # noqa: E402
modelsets._all_sets()
BOX = ('front', 'back', 'left', 'right', 'top', 'bottom')
mine = set(sys.argv[1:]) if len(sys.argv) > 1 else set()
if 'mine' in mine:
    for k in [k for k, v in modelsets.PIECES.items() if v.get('set') in ('doors', 'huang')] + ['kilauea', 'kilauea_open', 'kilauea_steps']:
        modelsets.PIECES.pop(k, None)
    for m in ('doorset', 'huangset', 'towerset'):
        sp = importlib.util.spec_from_file_location(m, os.path.join(MINE, m + '.py'))
        sys.modules[m] = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(sys.modules[m])


def drawn_hits(desc):
    out = []
    for p in desc.get('parts', []):
        if p.get('shape', 'box') not in ('box', 'slab'):
            continue
        f = p.get('faces') or {}
        if all(n in f and f[n] is None for n in BOX) and p.get('look') is not None:
            out.append((p.get('look'), p.get('size'), p.get('solid', True)))
    return out


pr = project.Project.open('Waikiki')
have = {recordio.field(r, 'EDID') for k, r in pr.records.items() if k.startswith('+')}
found, by_set, errors = {}, collections.Counter(), []
for piece, what in sorted(modelsets.PIECES.items()):
    try:
        desc = what['describe']()
    except Exception as e:
        errors.append((piece, repr(e)[:80]))
        continue
    hits = drawn_hits(desc)
    far = modelsets.far_of(desc) if hasattr(modelsets, 'far_of') else None
    if hits:
        inw = what['edid'] in have or (what['edid'] + 'Static') in have
        found[piece] = {'set': what['set'], 'edid': what['edid'], 'hits': len(hits), 'in_waikiki': inw, 'what': hits[:3]}
        by_set[what['set']] += 1
print('pieces', len(modelsets.PIECES), 'with a drawn collision box', len(found), dict(by_set))
print('of those in Waikiki', sum(1 for v in found.values() if v['in_waikiki']))
for k, v in found.items():
    print(' ', k, v['set'], v['edid'], 'in Waikiki' if v['in_waikiki'] else '-', v['hits'], v['what'][:1])
print('errors', errors[:5])
json.dump(found, open(r'D:\FOLabScratch\huang\sweep.json', 'w'), indent=1, default=str)
