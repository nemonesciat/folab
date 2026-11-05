import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import json, struct, sys
import gamedata, project, espwrite, recordio, tes4
gd = gamedata.GameData()
pr = project.Project.create('Places Test'); pr.cells, pr.records, pr.next_id = {}, {}, project.FIRST_ID
def check(what, ok): print(('PASS ' if ok else 'FAIL ') + what)
shop = next(c for c in gd.interiors if gd.edid(c) == '2EOVault21GiftShop')
rec = recordio.load(gd, shop); recordio.set_field(rec, 'EDID', 'FOLabEmptyRoom'); recordio.set_field(rec, 'FULL', 'My Empty Room')
coc = next(gd.key(f) for f, (i, r) in gd.forms.items() if r.tag == 'STAT' and gd.edid(f) == 'COCMarkerHeading')
doorbase = next(gd.key(f) for f, (i, r) in gd.forms.items() if r.tag == 'DOOR' and gd.edid(f) == 'VDoorSliding02')
made = pr.apply('new place', [{'op': 'record_new', 'record': rec}, {'op': 'add', 'cell': '$new', 'base': coc, 'p': [0,0,0,0,0,0]},
                              {'op': 'add', 'cell': '$new', 'base': doorbase, 'p': [256,0,0,0,0,1.5708]}])
room, mydoor = made[0], made[2]
rec2 = recordio.load(gd, shop); recordio.set_field(rec2, 'EDID', 'FOLabShopCopy'); recordio.set_field(rec2, 'FULL', 'Shop Copy')
things = [r for r in gd.refs(shop) if r['pos'] and r['base'] in gd.forms]
ops = [{'op': 'record_new', 'record': rec2}] + [{'op': 'add', 'cell': '$new', 'base': gd.key(r['base']), 'p': list(r['pos']) + list(r['rot']), 's': r['scale']} for r in things]
copy = pr.apply('copy', ops)[0]
shopdoor = next(r for r in gd.refs(shop) if r['leads'])
pr.apply('link', [{'op': 'tel', 'cell': room, 'ref': mydoor, 'tel': {'door': gd.key(shopdoor['ref']), 'p': [10, 20, 30, 0, 0, 3.14]}},
                  {'op': 'tel', 'cell': gd.key(shop), 'ref': gd.key(shopdoor['ref']), 'tel': {'door': mydoor, 'p': [256, 80, 0, 0, 0, 0]}}])
path = pr.plugin_path(); espwrite.write(gd, pr, path)
gd2 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [path]); me = len(gd2.plugins) - 1
own = lambda k: (me << 24) | int(k[1:], 16)
check('both new places are interiors', own(room) in gd2.interiors and own(copy) in gd2.interiors)
check('their names', gd2.edid(own(room)) == 'FOLabEmptyRoom' and tes4.zstr(gd2.fields(own(copy))['FULL']) == 'Shop Copy')
check('the copy has every thing the shop has', len(gd2.refs(own(copy))) == len(things))
check('lighting copied (XCLL the same)', gd2.fields(own(copy)).get('XCLL') == gd.fields(shop).get('XCLL'))
i, r = gd2.cell_refs[own(room)][own(mydoor)]
x = gd2.plugins[i].fields(r)['XTEL']
check('new door: persistent, XTEL 32 bytes to the shop door', r.flags & tes4.PERSISTENT and len(x) == 32 and gd2.to_global(me, struct.unpack_from('<I', x)[0]) == shopdoor['ref'])
i, r = gd2.cell_refs[shop][shopdoor['ref']]
x = gd2.plugins[i].fields(r)['XTEL']
check('shop door now leads to the new door, arrival as asked', i == me and gd2.to_global(me, struct.unpack_from('<I', x)[0]) == own(mydoor) and [round(v) for v in struct.unpack_from('<3f', x, 4)] == [256, 80, 0])
check('shop door stays persistent', r.flags & tes4.PERSISTENT)
pr.undo(); pr.undo(); pr.undo(); check('undo takes it all back', pr.records == {} and pr.cells == {})
