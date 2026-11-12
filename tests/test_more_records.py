"""The kinds of record the GECK edits from its World, Gameplay and Character menus (schema._MORE): game settings,
weather, image spaces, lighting templates, sounds, music, water, combat styles and the rest. Each is changed as the
Browse page changes it, saved, and read back from the plugin: the change is there, a new one of its own stands beside
the game's, and everything not changed is the game's own bytes."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import project  # noqa: E402
import recordio  # noqa: E402
import schema  # noqa: E402
import tes4  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


gd = gamedata.GameData()
pr = project.Project.create('More Records')


def find(tag, edid):
    return next(f for f, (i, r) in gd.forms.items() if r.tag == tag and gd.edid(f) == edid)


def setf(rec, tag, name, v):
    s = next(s for s in rec['subs'] if s['tag'] == tag)
    next(f for f in s['fields'] if f.get('name') == name)['value'] = v


def subs_of(g, fid):
    i, rec = g.source(fid)
    return i, list(tes4.iter_subrecords(g.plugins[i].data(rec)))


check('every kind the GECK edits is listed for Browse', all(t in schema.TYPES for t in schema._MORE) and len(schema._MORE) >= 27, len(schema._MORE))

jump = next(f for f, (i, r) in gd.forms.items() if r.tag == 'GMST' and gd.edid(f).startswith('f'))
greet = find('GMST', 'sPoisonNoWeaponMessage')
whole = next(f for f, (i, r) in gd.forms.items() if r.tag == 'GMST' and gd.edid(f).startswith('i') and len(gd.fields(f)['DATA']) == 4)
weather, light = find('WTHR', 'NVWastelandClearEast'), find('LGTM', 'HiddenValleyInterior')
sound, style, space = find('SOUN', 'EMTCampfireInactive02'), find('CSTY', 'DefaultCombatstyle'), find('IMGS', 'NVSewerImageSpace01')
music, stage = find('MUSC', 'musSCRVegasStinger'), find('RADS', 'Rad1')

r = recordio.load(gd, jump)
kinds = {s['tag']: s['kind'] for s in r['subs']}
check('a setting named f... is a number with a fraction', kinds['DATA'] == 'struct' and next(s for s in r['subs'] if s['tag'] == 'DATA')['fields'][0]['code'] == 'f')
setf(r, 'DATA', 'Value', 123.5)
r2 = recordio.load(gd, greet)
check('a setting named s... is words', next(s for s in r2['subs'] if s['tag'] == 'DATA')['kind'] == 'z')
recordio.set_field(r2, 'DATA', 'Mind the blade.')
r3 = recordio.load(gd, whole)
was_whole = next(s for s in r3['subs'] if s['tag'] == 'DATA')['fields'][0]
check('a setting named i... is a whole number', was_whole['code'] == 'i')
setf(r3, 'DATA', 'Value', 77)
rw = recordio.load(gd, weather)
setf(rw, 'FNAM', 'Day far', 54321.0)
setf(rw, 'DATA', 'Wind speed', 200)
rl = recordio.load(gd, light)
setf(rl, 'DATA', 'Fog red', 250)
setf(rl, 'DATA', 'Fog far', 999.0)
rs = recordio.load(gd, sound)
recordio.set_field(rs, 'FNAM', 'fx\\folab\\test.wav')
setf(rs, 'SNDD', 'Priority', 7)
rc = recordio.load(gd, style)
setf(rc, 'CSTD', 'Block %', 90)
ri = recordio.load(gd, space)
setf(ri, 'DNAM', 'Saturation', 0.25)
rm = recordio.load(gd, music)
setf(rm, 'ANAM', 'dB', -3.0)
rr = recordio.load(gd, stage)
setf(rr, 'DATA', 'Starts at', 150)
new_weather = recordio.load(gd, weather)
recordio.set_field(new_weather, 'EDID', 'MoreRecordsStorm')
setf(new_weather, 'DATA', 'Thunder frequency', 3)
new_setting = recordio.load(gd, jump)
recordio.set_field(new_setting, 'EDID', 'fMoreRecordsOwnSetting')
setf(new_setting, 'DATA', 'Value', 2.25)
ops = [{'op': 'record', 'key': gd.key(f), 'record': x} for f, x in ((jump, r), (greet, r2), (whole, r3), (weather, rw), (light, rl), (sound, rs),
                                                                   (style, rc), (space, ri), (music, rm), (stage, rr))]
made = pr.apply('more records', ops + [{'op': 'record_new', 'record': new_weather}, {'op': 'record_new', 'record': new_setting}])
path = pr.plugin_path()
espwrite.write(gd, pr, path)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [path])
me = len(g.plugins) - 1


def now(fid):
    i, subs = subs_of(g, fid)
    return i == me, dict(subs), subs


def untouched(fid, changed):
    """Every subrecord but the changed ones is the game's own, byte for byte (links aside, which are numbered for this plugin)."""
    i0, a = subs_of(gd, fid)
    _mine, _d, b = now(fid)
    if [t for t, _ in a] != [t for t, _ in b]:
        return False
    for (t, x), (_t, y) in zip(a, b):
        if t in changed:
            continue
        xm, ym = bytearray(x), bytearray(y)
        for o in schema.form_offsets(gd.forms[fid][1].tag, t, x):
            if gd.to_global(i0, struct.unpack_from('<I', x, o)[0]) != g.to_global(me, struct.unpack_from('<I', y, o)[0]):
                return False
            xm[o:o + 4] = ym[o:o + 4] = bytes(4)
        if xm != ym:
            return False
    return True


mine, d, _ = now(jump)
check('game setting: the number is changed in the plugin', mine and struct.unpack('<f', d['DATA'])[0] == 123.5)
mine, d, _ = now(greet)
check('game setting: the words are changed', mine and tes4.zstr(d['DATA']) == 'Mind the blade.')
mine, d, _ = now(whole)
check('game setting: the whole number is changed, stored as a whole number', mine and struct.unpack('<i', d['DATA'])[0] == 77)
mine, d, _ = now(weather)
check('weather: fog distance and wind changed', mine and struct.unpack('<6f', d['FNAM'])[1] == 54321.0 and d['DATA'][0] == 200)
check('weather: its colours, clouds and the rest are the game\'s own', untouched(weather, {'FNAM', 'DATA'}))
mine, d, _ = now(light)
check('lighting template: fog colour and distance changed', mine and d['DATA'][8] == 250 and struct.unpack_from('<f', d['DATA'], 16)[0] == 999.0
      and d['DATA'][:8] == gd.fields(light)['DATA'][:8])
mine, d, _ = now(sound)
check('sound: its file and priority changed', mine and tes4.zstr(d['FNAM']) == 'fx\\folab\\test.wav' and struct.unpack_from('<i', d['SNDD'], 24)[0] == 7)
check('sound: the rest is the game\'s own', untouched(sound, {'FNAM', 'SNDD'}))
mine, d, _ = now(style)
check('combat style: block chance changed, the other two parts untouched', mine and d['CSTD'][36] == 90 and untouched(style, {'CSTD'}))
mine, d, _ = now(space)
check('image space: saturation changed', mine and struct.unpack_from('<f', d['DNAM'], 25 * 4)[0] == 0.25 and d['DNAM'][:100] == gd.fields(space)['DNAM'][:100])
mine, d, _ = now(music)
check('music: volume changed', mine and struct.unpack('<f', d['ANAM'])[0] == -3.0)
mine, d, _ = now(stage)
check('radiation stage: where it starts changed, its effect still the game\'s', mine and struct.unpack_from('<I', d['DATA'])[0] == 150
      and g.to_global(me, struct.unpack_from('<I', d['DATA'], 4)[0]) == gd.to_global(gd.source(stage)[0], struct.unpack_from('<I', gd.fields(stage)['DATA'], 4)[0]))
own = [(me << 24) | int(k[1:], 16) for k in made]
tags = sorted(g.forms[f][1].tag for f in own)
check('a weather and a setting of the mod\'s own stand beside the game\'s', tags == ['GMST', 'WTHR'] and {g.edid(f) for f in own} == {'MoreRecordsStorm', 'fMoreRecordsOwnSetting'})
wf = next(f for f in own if g.forms[f][1].tag == 'WTHR')
wd = g.fields(wf)
check('the new weather keeps the game\'s links (its image space changes, its sounds)', all(
    g.to_global(me, struct.unpack('<I', wd[t])[0]) == gd.to_global(gd.source(weather)[0], struct.unpack('<I', gd.fields(weather)[t])[0])
    for t in wd if t.endswith('IAD')) and wd['DATA'][10] == 3)
import health  # noqa: E402
check('the plugin passes the health check', health.check_file(gd, path)['summary']['error'] == 0, health.check_file(gd, path)['summary'])
