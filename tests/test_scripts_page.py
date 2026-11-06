"""The Scripts page's backend against the game: listing and reading the game's scripts; a script made and saved through the
project reads back from the written plugin with the compiler's own bytes and its references re-pointed; a compile error
says the right line and changes nothing; variables keep their numbers; a script goes on a thing in the record's right place;
the starter templates all compile."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import api_scripts  # noqa: E402
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import project  # noqa: E402
import recordio  # noqa: E402
import scriptc  # noqa: E402
import tes4  # noqa: E402


def check(ok, what):
    print(('PASS ' if ok else 'FAIL ') + what)


gd = gamedata.GameData()
pr = project.Project.create('Scripts Test')
s = api_scripts.Scripts(gd, lambda: pr)


def written():
    """The mod written out and loaded on top of the game (a new file each time: Windows keeps a loaded plugin open)."""
    global writes
    writes += 1
    out = os.path.join(project.BUILD_DIR, 'Scripts Test %d.esp' % writes)
    os.makedirs(project.BUILD_DIR, exist_ok=True)
    espwrite.write(gd, pr, out)
    g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
    return g, len(g.plugins) - 1, out


writes = 0


def fid_of(tag, edid=None, plugin=None, need=None):
    for fid, (i, r) in gd.forms.items():
        if r.tag == tag and (plugin is None or gd.names[i] == plugin) and fid >> 24 == i:
            f = gd.plugins[i].fields(r)
            if (edid is None or tes4.zstr(f.get('EDID', b'')).lower() == edid.lower()) and (need is None or need(f)):
                return fid


# ---- listing and reading (stage 1) ----
rows = s.rows()
check(len(rows['rows']) + rows['more'] > 3000, 'the list has the game\'s scripts (%d)' % (len(rows['rows']) + rows['more']))
found = s.rows('GraveContScript')['rows']
check(len(found) == 1 and found[0]['edid'] == 'GraveContScript' and found[0]['kind'] == 'object', 'searching by name finds one, with its kind')
inside = s.rows('NoShovelMsg', inside=True)['rows']
check(any(r['edid'] == 'GraveContScript' for r in inside), 'searching inside scripts finds the words in the source')
check(not s.rows('NoShovelMsg')['rows'], '...and by name alone it doesn\'t')
one = s.one(found[0]['key'])
check('showMessage NoShovelMsg' in one['text'] and '\r' not in one['text'] and one['check']['ok'], 'one script: its source, plain line ends, compiles')
check(one['vars'] == [['Opened', 'short']], 'its variables')

# ---- every game script's bytes, through the mod's layer of forms: same as the plain compiler's ----
same = total = 0
for _e, fid in s.game[::40]:
    i, rec = gd.source(fid)
    d = dict(tes4.iter_subrecords(gd.plugins[i].data(rec)))
    key = gd.key(fid)
    total += 1
    try:
        if s.compile(s.one(key)['text'], key).data == d['SCDA']:
            same += 1
    except scriptc.CompileError:
        pass
check(total > 80 and same >= total - 1, 'recompiled through the page: %d of %d sampled game scripts the same bytes' % (same, total))

# ---- made and saved through the project; read back from the plugin (stage 2) ----
item = pr.apply('item', [{'op': 'record_new', 'record': recordio.load(gd, fid_of('MISC', 'Caps001') or fid_of('MISC'))}])[0]
rec = pr.records[item]
recordio.set_field(rec, 'EDID', 'FOLabTestThing')
dlc = fid_of('MISC', plugin='deadmoney.esm', need=lambda f: f.get('EDID'))
dlc_edid = tes4.zstr(gd.plugins[gd.forms[dlc][0]].fields(gd.forms[dlc][1])['EDID'])
new_id = pr.next_id
TEXT = """scn FOLabTestScript

short counter
float seconds
ref thing

Begin OnActivate
\tset counter to counter + 1
\tset thing to player
\tif player.GetItemCount FOLabTestThing >= 1
\t\tplayer.AddItem Caps001 5
\t\tplayer.AddItem %s 1
\telse
\t\tthing.AddItem FOLabTestThing 1
\tendif
\tActivate
End
""" % dlc_edid
made = s.new('FOLabTestScript')
key = made['key']
check(key == '+%06X' % new_id, 'a new script gets a key of the mod\'s own')
check(s.record(key)['type'] == 'SCPT' and 'Begin OnActivate' in s.one(key)['text'], 'a blank new script is a compiled script with a skeleton')
got = s.save(key, TEXT)
check(got['ok'], 'saving compiles and keeps it')
compiled = s.compile(TEXT, key)
gd2, me, path = written()
masters = tes4.PluginFile(path).header['masters']
check('DeadMoney.esm' in masters, 'the DLC it names became a master (%s)' % ', '.join(masters))
fid2 = (me << 24) | int(key[1:], 16)
i2, rec2 = gd2.source(fid2)
back = list(tes4.iter_subrecords(gd2.plugins[i2].data(rec2)))
want = [('EDID', b'FOLabTestScript\0')] + compiled.subrecords(lambda f: 0)
check(rec2.tag == 'SCPT', 'the plugin holds it as an SCPT')
check([t for t, _d in back] == [t for t, _d in want], 'its parts are in the game\'s order: ' + ' '.join(t for t, _d in back))
check(all(a == b for (t, a), (_t, b) in zip(back, want) if t != 'SCRO'), 'EDID SCHR SCDA SCTX SLSD SCVR SCRV: the very bytes the compiler gave')
d2 = dict(back)
check(d2['SCDA'] == compiled.data and d2['SCTX'] == TEXT.replace('\n', '\r\n').encode('cp1252'), 'SCDA is the compiled bytes, SCTX the source')
check(struct.unpack('<IIIIHH', d2['SCHR'])[1:4] == (len(compiled.refs), len(compiled.data), compiled.var_count), 'SCHR counts agree')
scro = [gd2.to_global(me, struct.unpack('<I', d)[0]) for t, d in back if t == 'SCRO']
expect = [(me << 24) | int(f.fid[1:], 16) if isinstance(f.fid, str) else f.fid for _n, f, v in compiled.refs if not v]
check(scro == expect, 'every SCRO points at the same forms through the plugin\'s own numbering')
check((me << 24) | int(item[1:], 16) in scro, '...the mod\'s own thing among them')
check(gd.forms[dlc][1].formid & 0xFFFFFF in [x & 0xFFFFFF for x in scro] and dlc in scro, '...and the DLC\'s')
check(any(t == 'SCRV' for t, _d in back), 'the ref variable is an SCRV')

# ---- errors ----
before = pr.count(), s.one(key)['text'], len(pr.undo_stack)
BAD = """scn FOLabTestScript

Begin GameMode
\tset counter to 1
\tplayer.NotARealCommand 3
End
"""
c = s.check(BAD, key)
check(not c['ok'] and c['problem']['line'] == 5 and 'NotARealCommand' in c['problem']['message'], 'an unknown command: the error is on line 5: ' + c['problem']['message'])
r = s.save(key, BAD)
check(not r['ok'] and r['problem']['line'] == 5, 'saving it says the same')
check((pr.count(), s.one(key)['text'], len(pr.undo_stack)) == before, '...and nothing changed: no broken script is ever kept')
for text, line in [('scn FOLabX\nshort folabnum\nBegin GameMode\n\tset folabother to 1\nEnd\n', 4),
                   ('scn FOLabX\n\n\n; a comment\nBegin GameMode\n\tif 1\nEnd\n', 6),
                   ('scn FOLabX\nBegin GameMode\nEnd\n\n\nset a to 1\n', 6)]:
    c = s.check(text)
    check(not c['ok'] and c['problem']['line'] == line, 'an error on line %d says line %d: %s' % (line, c['problem'].get('line', 0), c['problem'].get('message')))
c = s.check('scn GraveContScript\nBegin GameMode\nEnd\n', key)
check(not c['ok'] and 'taken' in c['problem']['message'] and c['problem']['line'] == 1, 'a name another form has is refused')

# ---- variables keep their numbers ----
d = {n: i for i, n, _f in api_scripts.vars_of(s.record(key))}
r = s.save(key, TEXT.replace('float seconds\n', '').replace('short counter\n', 'short counter\nshort extra\n'))
d3 = {n: i for i, n, _f in api_scripts.vars_of(s.record(key))}
check(r['ok'] and d3['counter'] == d['counter'] and d3['thing'] == d['thing'] and d3['extra'] > max(d.values()), 'compiled again, variables keep their numbers; a new one takes a new number')
check(api_scripts.header_of(s.record(key))[1] >= max(d3.values()), 'the count covers the highest number given out')
pr.undo()
check('float seconds' in s.one(key)['text'], 'Undo puts the last version back')

# ---- a game script changed; a copy of it ----
gk = gd.key(fid_of('SCPT', 'GraveContScript'))
gt = s.one(gk)['text']
r = s.save(gk, gt.replace('>= 1', '>= 2'))
check(r['ok'] and r['script']['state'] == 'changed' and gk in pr.records, 'a game script changed is an override in the mod')
check(s.rows('GraveContScript')['rows'][0]['state'] == 'changed', 'the list says so')
cp = s.copy(gk, 'FOLabGraveCopy')
ct = s.one(cp['key'])
check(cp['key'].startswith('+') and ct['text'].lower().startswith('scn folabgravecopy') and ct['check']['ok'], 'a copy is a script of the mod\'s own under its new name')
s.remove(gk)
check(gk not in pr.records, 'a changed game script can go back as the game has it')
print('(a quest script reads the variables of the mod\'s other scripts)')
q = s.new('FOLabQuestScript', 'quest')['key']
s.save(q, 'scn FOLabQuestScript\n\nshort stageflag\n\nBegin GameMode\nEnd\n')
qrec = recordio.load(gd, fid_of('QUST'))
recordio.set_field(qrec, 'EDID', 'FOLabTestQuest')
api_scripts.set_script(qrec, q)
pr.apply('quest', [{'op': 'record_new', 'record': qrec}])
c = s.check('scn FOLabReader\n\nBegin GameMode\n\tset FOLabTestQuest.stageflag to 1\nEnd\n')
check(c['ok'], 'FOLabTestQuest.stageflag compiles: the mod\'s quest, its script\'s variable (%s)' % c.get('problem'))
c = s.check('scn FOLabReader\n\nBegin GameMode\n\tset FOLabTestQuest.nosuch to 1\nEnd\n')
check(not c['ok'] and c['problem']['line'] == 4, '...a variable it hasn\'t, an error on its line')

# ---- what the editor's comforts ask for ----
hit = s.complete('FOLabTest')
check(any(h['edid'] == 'FOLabTestThing' for h in hit) and hit[0]['key'].startswith('+'), 'completing editor IDs: the mod\'s first')
check(any(h['edid'].lower() == 'caps001' for h in s.complete('caps00')), '...and the game\'s, in their own spelling')
check(all(h['tag'] == 'KEYM' for h in s.complete('key', ['KEYM'])) and s.complete('key', ['KEYM']), '...by kind')
u = s.used_in('NoShovelMsg')
check(any(r['edid'] == 'GraveContScript' and r['line'] > 1 and 'noshovelmsg' in r['text'] for r in u['rows']), 'where a word is used: script, line, the line itself')
check(s.used_in('showmessage')['total'] > 100, 'a function is found in the game\'s own scripts (%d)' % s.used_in('showmessage')['total'])
check(any(r['edid'] == 'FOLabTestScript' for r in s.used_in('FOLabTestThing')['rows']), '...the mod\'s scripts too')
check(s.info()['functions'] and all(not f['name'].lower().startswith('unused') for f in s.info()['functions']), 'the function table for help')
gi = next(f for f in s.info()['functions'] if f['name'] == 'GetItemCount')
check(gi['doc'] and gi['ref'] and gi['params'], 'GetItemCount has plain words and its parameters')
check(next(f for f in s.info()['functions'] if f['name'] == 'GetActorValue')['doc'], 'a note kept by the short name reaches the long one')

# ---- SCRI: in the game's own place, for every record of the game ----
wrong, seen = 0, 0
for fid, (i, r) in gd.forms.items():
    if r.tag in api_scripts.SCRI_AFTER:
        subs = list(tes4.iter_subrecords(gd.plugins[i].data(r)))
        tags = [t for t, _d in subs]
        if 'SCRI' in tags:
            seen += 1
            fake = {'type': r.tag, 'subs': [{'tag': t} for t in tags if t != 'SCRI']}
            api_scripts.set_script(fake, 'x')
            if [x['tag'] for x in fake['subs']] != tags:
                wrong += 1
check(seen > 4000 and not wrong, 'SCRI put back in the same place in all %d game records that carry one (%d not)' % (seen, wrong))

# ---- putting a script on a thing ----
door = next(fid for fid, (i, r) in gd.forms.items() if r.tag == 'DOOR' and fid >> 24 == 0 and b'SCRI' not in gd.plugins[0].data(r))
dk = gd.key(door)
sc = s.new('FOLabDoorScript')['key']
n = len(pr.undo_stack)
got = s.attach(dk, sc)
check(got['on']['script']['key'] == sc and len(pr.undo_stack) == n + 1, 'a script goes on a game door, one Undo step')
check(any(x['key'] == dk for x in s.who(sc)['rows']), '...and the script says what runs it')
s.attach(dk, '')
check(dk not in pr.records, 'taken off again, the door is just as the game has it')
s.attach(dk, sc)
try:
    s.attach(dk, q)
    check(False, 'a quest script is refused on a door')
except api_scripts.ScriptProblem as e:
    check('quest' in str(e), 'a quest script is refused on a door: ' + str(e))
qk = gd.key(fid_of('QUST'))
try:
    s.attach(qk, sc)
    check(False, 'an object script is refused on a quest')
except api_scripts.ScriptProblem as e:
    check(True, 'an object script is refused on a quest: ' + str(e))
stat = next(fid for fid, (i, r) in gd.forms.items() if r.tag == 'STAT')
check(not s.on(gd.key(stat))['can'], 'a static can\'t carry a script')
try:
    s.attach(gd.key(stat), sc)
    check(False, 'refused on a static')
except api_scripts.ScriptProblem as e:
    check(True, 'refused on a static')
gd2, me, path = written()
i2, rec2 = gd2.source(door)
d = dict(tes4.iter_subrecords(gd2.plugins[i2].data(rec2)))
check(i2 == me and gd2.to_global(me, struct.unpack('<I', d['SCRI'])[0]) == (me << 24) | int(sc[1:], 16), 'in the plugin: the door\'s SCRI is the mod\'s script')
s.remove(sc)
check(sc not in pr.records and not recordio.field(pr.records.get(dk, {'subs': []}), 'SCRI'), 'deleting a script takes it off what it was on')

# ---- the starters ----
key_edid = tes4.zstr(gd.plugins[0].fields(gd.forms[fid_of('KEYM', plugin='falloutnv.esm')][1])['EDID'])
quest_edid = tes4.zstr(gd.plugins[0].fields(gd.forms[fid_of('QUST', plugin='falloutnv.esm')][1])['EDID'])
answers = {'door_key': {'key': key_edid, 'text': 'It\'s locked.'}, 'item_equip': {}, 'trigger_message': {},
           'pickup_stage': {'quest': quest_edid, 'stage': '20'}}
import scripttemplates  # noqa: E402
check(set(answers) == set(scripttemplates.TEMPLATES), 'the four starters asked for are all there')
for tid, fields in answers.items():
    t = scripttemplates.TEMPLATES[tid]
    name = 'FOLabT' + tid.replace('_', '')
    n = len(pr.undo_stack)
    made = s.new(name, template=tid, fields=fields)
    one = s.one(made['key'])
    check(one['check']['ok'] and one['kind'] == t['kind'] and len(pr.undo_stack) == n + 1, '%s: compiles from plain answers, one Undo step' % t['title'])
    if t.get('message'):
        m = next(k for k, r in pr.records.items() if recordio.field(r, 'EDID') == name + 'Msg')
        check(recordio.field(pr.records[m], 'DESC') and any(r['name'].lower() == (name + 'msg').lower() and r.get('key') == m for r in one['check']['refs']), '  ...with its message, a record of its own')
    for target in t['on'][:1]:
        tf = next(fid for fid, (i, r) in gd.forms.items() if r.tag == target and fid >> 24 == 0)
        s.attach(gd.key(tf), made['key'])
try:
    s.new('FOLabTbad', template='door_key', fields={'key': 'NoSuchKeyAnywhere', 'text': 'x'})
    check(False, 'a starter refuses a key that isn\'t there')
except api_scripts.ScriptProblem as e:
    check('NoSuchKeyAnywhere' in str(e), 'a starter refuses a key that isn\'t there: ' + str(e))
try:
    s.new('FOLabTbad', template='door_key', fields={'key': quest_edid, 'text': 'x'})
    check(False, 'a starter refuses the wrong kind of thing')
except api_scripts.ScriptProblem as e:
    check(True, 'a starter refuses the wrong kind of thing: ' + str(e))
gd2, me, path = written()
mesg = [r for fid, (i, r) in gd2.forms.items() if i == me and r.tag == 'MESG' and fid >> 24 == me]
ok = bool(mesg)
for r in mesg:
    tags = [t for t, _d in tes4.iter_subrecords(gd2.plugins[me].data(r))]
    ok = ok and tags == ['EDID', 'DESC', 'INAM', 'DNAM', 'TNAM']
check(ok, 'the messages come out in the plugin with the parts a game message has (%d)' % len(mesg))
check(gd2.plugins[me].top_groups().index('MESG') > gd2.plugins[me].top_groups().index('SCPT'), 'groups in the game\'s order')

# ---- a plugin opened as the mod: its scripts are its own, edited in place, under the masters it has ----
import adopt  # noqa: E402
pr_name = adopt.adopt(gd, path)
pr3 = project.Project.open(pr_name)
gd3 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [pr3.source_path()])
s3 = api_scripts.Scripts(gd3, lambda: pr3)
own = next(r for r in s3.rows('FOLabTestScript')['rows'] if r['edid'] == 'FOLabTestScript')
check(own['key'].lower().startswith('scripts test') and not own['state'], 'opened: the plugin\'s script is listed under its own file')
text3 = s3.one(own['key'])['text']
check(s3.one(own['key'])['check']['ok'], 'opened: it compiles, naming the plugin\'s own forms by editor ID')
got3 = s3.save(own['key'], text3 + '\n; changed\n')
check(got3['ok'] and got3['script']['state'] == 'changed', 'opened: saving keeps the change over the plugin\'s record')
out3 = os.path.join(project.BUILD_DIR, 'Opened.esp')
espwrite.write(gd3, pr3, out3)
p3 = tes4.PluginFile(out3)
want3 = s3.compile(text3 + '\n; changed\n', own['key'])
recs3 = [r for r, _path in p3.walk() if r.tag == 'SCPT' and tes4.zstr(p3.fields(r).get('EDID', b'')) == 'FOLabTestScript']
check(len(recs3) == 1 and p3.fields(recs3[0])['SCDA'] == want3.data and b'; changed' in p3.fields(recs3[0])['SCTX'], 'opened: the plugin holds one such script, the new bytes')
check(p3.header['masters'] == tes4.PluginFile(pr3.source_path()).header['masters'], 'opened: its masters are as they were')
ours = [struct.unpack('<I', d)[0] for t, d in tes4.iter_subrecords(p3.data(recs3[0])) if t == 'SCRO']
check(any(x >> 24 == len(p3.header['masters']) for x in ours), 'opened: a reference to the plugin\'s own thing numbers as the plugin\'s own')
