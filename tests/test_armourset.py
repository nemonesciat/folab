"""Waikiki's armour and dress (armourset): in a small mod with a pirates' body list, every armour and the mahiole get
the keys they were planned with, the written plugin has each as an ARMO worn where its base is (slots, numbers) with
no script or enchantment, every model among the mod's own files and drawn with its own pictures only where the game's
were (the skin and the base's normal maps kept), cut-outs kept see-through, the mahiole clear of the game's head, the
boarding armour in the pirates' list and the rest reported unworn; a second time refused."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))

import armourset as A  # noqa: E402
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import hats  # noqa: E402
import library  # noqa: E402
import nifwrite  # noqa: E402
import peopledress as P  # noqa: E402
import project  # noqa: E402
import tes4  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


gd = gamedata.GameData()
find = lambda tag, e: next(f for f, (i, r) in gd.forms.items() if r.tag == tag and gd.edid(f) == e)

check('the mahiole clears the game\'s head', A.mahiole_clearance(hats.head_points(gd)) > 0.1, round(A.mahiole_clearance(hats.head_points(gd)), 3))

pr = project.Project.create('Armour Test')
shirt = gd.key(find('ARMO', 'ArmorLeather'))
pr.apply('list', [{'op': 'record_new', 'record': P._lvli(gd, 'FOLabPirateBodyList', 0, [(shirt, 3)])}])
lk = next(k for k, r in pr.records.items() if r['type'] == 'LVLI')
first = pr.next_id
ops, rep = A.ops(gd, pr)
made = pr.apply('armour', ops)
news = sum(1 for o in ops if o['op'] == 'record_new')
check('nine records, the keys as planned', news == len(A.ARMOURS) + 1 and made[:news] == ['+%06X' % (first + n) for n in range(news)], news)
rows = [s for s in pr.records[lk]['subs'] if s['tag'] == 'LVLO']
got = [next(f['value'] for f in s['fields'] if f.get('code') == 'F') for s in rows]
check('the boarding armour twice in the pirates\' list, the old entries kept', got.count(rep['armour']['boarding']['key']) == 2 and got.count(shirt) == 3, got)
check('the rest reported unworn', len(rep['unworn']) == len(A.ARMOURS), rep['unworn'])
try:
    A.ops(gd, pr)
    check('a second time refused', False)
except ValueError:
    check('a second time refused', True)

path = pr.plugin_path()
espwrite.write(gd, pr, path)
gd2 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [path])
me = len(gd2.plugins) - 1
raw = lambda fid: dict(tes4.iter_subrecords(gd2.plugins[gd2.forms[fid][0]].data(gd2.forms[fid][1])))
root = library.assets_dir(pr)
for k, info in rep['armour'].items():
    d = raw((me << 24) | int(info['key'][1:], 16))
    base = A.ARMOURS[k][0] if k in A.ARMOURS else hats.GAME_HAT
    g = dict(tes4.iter_subrecords(gd.plugins[gd.forms[find('ARMO', base)][0]].data(gd.forms[find('ARMO', base)][1])))
    check('%s: worn where %s is (slots, numbers), no script or enchantment' % (info['name'], base),
          d['BMDT'] == g['BMDT'] and d['DATA'] == g['DATA'] and d['DNAM'] == g['DNAM'] and 'SCRI' not in d and 'EITM' not in d)
    ok, own, kept = True, set(), set()
    for tag in A.MODEL_TAGS:
        if tag not in g:
            continue
        m = tes4.zstr(d.get(tag, b''))
        f = os.path.join(root, 'meshes', m)
        if not m or not os.path.isfile(f):
            ok = False
            continue
        for t in nifwrite.textures_in(open(f, 'rb').read()):
            (own if '\\folab\\' in t['path'].lower() else kept).add(t['path'].lower())
    check('%s: every model among the mod\'s files, drawn with pictures of its own' % info['name'],
          ok and own and all(os.path.isfile(os.path.join(root, p)) for p in own), sorted(own)[:3])
    if k in A.ARMOURS:
        painted = {p.split('\\')[-1][len(k) + 1:] for p in own}
        left = [p for p in kept if p.split('\\')[-1] in painted]
        check('%s: none of the pictures it paints left the game\'s; the skin not painted' % info['name'],
              not left and not any('characters' in p for p in own), left[:3])
legion = [p for p in os.listdir(os.path.join(root, 'textures', 'folab', library.slug(pr.name), 'armour')) if 'lecloak' in p or 'legionbase' in p]
four = {p: open(os.path.join(root, 'textures', 'folab', library.slug(pr.name), 'armour', p), 'rb').read()[84:88] for p in legion}
check('the Legion pieces\' cut-outs kept (DXT5, with alpha)', four and all(v == b'DXT5' for v in four.values()), four)
