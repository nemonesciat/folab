"""Quests and dialogue made through the project read back from the written plugin the way the game's own files have them."""
import json
import os
import struct
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import api_quests as aq
import browse
import espwrite
import gamedata
import project
import questrec as qr
import recordio
import schema
import scriptc
import tes4

gd = gamedata.GameData()
pr = project.Project.create('Quest Test')
br = browse.Browse(gd, lambda: pr)


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)


def edit(label, ops):
    return {'made': pr.apply(label, ops)}


def find(tag, edid):
    for fid, (i, rec) in gd.forms.items():
        if rec.tag == tag and tes4.zstr(gd.plugins[i].fields(rec).get('EDID', b'')) == edid:
            return fid


_writes = [0]


def written():
    # (a file of its own each time: what's been read stays open)
    _writes[0] += 1
    path = pr.plugin_path()[:-4] + ' %d.esp' % _writes[0]
    espwrite.write(gd, pr, path)
    return path, tes4.PluginFile(path)


# ---- every record of the game: conditions read by function, plain fields and back ----
def link_for(i):
    masters = [m.lower() for m in gd.plugins[i].header['masters']]

    def link(k):
        fid = gd.from_key(k)
        n = gd.names[fid >> 24]
        return ((masters.index(n) if n in masters else len(masters)) << 24) | (fid & 0xFFFFFF)
    return link


TO_PLAIN = {'QUST': (qr.quest_plain, qr.quest_record), 'DIAL': (qr.topic_plain, qr.topic_record), 'INFO': (qr.info_plain, qr.info_record)}
counts = {t: 0 for t in TO_PLAIN}
wrong = {t: 0 for t in TO_PLAIN}
raw_links = 0
forms_in_conditions = 0
for i, p in enumerate(gd.plugins):
    link = link_for(i)
    for rec, _path in p.walk():
        if rec.tag in TO_PLAIN:
            subs = list(tes4.iter_subrecords(p.data(rec)))
            r = {'type': rec.tag, 'flags': 0, 'src': gd.names[i], 'subs': [recordio._keys(gd, i, rec.tag, s) for s in schema.decode_record(rec.tag, subs)]}
            counts[rec.tag] += 1
            for s in r['subs']:
                if s['tag'] == 'CTDA':
                    forms_in_conditions += sum(1 for f in s['fields'] if f.get('code') == 'F' and f['value'])
            to, back = TO_PLAIN[rec.tag]
            if recordio.to_bytes(r, link) != subs or recordio.to_bytes(back(json.loads(json.dumps(to(r)))), link) != subs:
                wrong[rec.tag] += 1
for t in TO_PLAIN:
    check('%s: all %d of the game\'s, as form keys and as plain fields, encode back byte for byte' % (t, counts[t]), counts[t] > 100 and wrong[t] == 0)
check('conditions name forms by key (%d links read by function)' % forms_in_conditions, forms_in_conditions > 50000)

# a condition with a form: GetIsID's parameter is a link, its value a float
c = schema.decode_sub('INFO', 'CTDA', struct.pack('<B3sfH2sIIII', 0, b'\0\0\0', 1.0, 72, b'\0\0', 0x1234, 0, 0, 0))
check('GetIsID: parameter 1 is a form link, parameter 2 a number', c['fields'][5]['code'] == 'F' and c['fields'][6]['code'] == 'I' and c['fields'][2]['code'] == 'f')
c = schema.decode_sub('INFO', 'CTDA', struct.pack('<B3sIH2sIIII', 4, b'\0\0\0', 0x77, 14, b'\0\0', 5, 0, 0, 0))
check('compared with a global: the value is a form link; an actor value parameter stays a number', c['fields'][2]['code'] == 'F' and c['fields'][5]['code'] == 'I')

# a DLC's condition, re-pointed: a Dead Money line whose condition names a Dead Money form, moved into a mod listing only some masters
dm = gd.names.index('deadmoney.esm') if 'deadmoney.esm' in gd.names else None
if dm:
    hit = None
    for rec, _path in gd.plugins[dm].walk():
        if rec.tag == 'INFO':
            for t, d in tes4.iter_subrecords(gd.plugins[dm].data(rec)):
                if t == 'CTDA' and d[8] == 72 and d[9] == 0 and struct.unpack_from('<I', d, 12)[0] >> 24 == len(gd.plugins[dm].header['masters']):
                    hit = (gd.key(gd.to_global(dm, rec.formid)), struct.unpack_from('<I', d, 12)[0])
            if hit:
                break
    r = recordio.load(gd, gd.from_key(hit[0]))
    fake = {}
    out = dict(recordio.to_bytes(r, lambda k: fake.setdefault(k, (0x05 << 24) | (gd.from_key(k) & 0xFFFFFF))))
    d = out['CTDA']
    check('a DLC line\'s condition is re-pointed to the plugin\'s numbering', struct.unpack_from('<I', d, 12)[0] == (0x05 << 24) | (hit[1] & 0xFFFFFF))

# ---- 1. a quest: stages, objectives, targets, conditions ----
made = aq.new_quest(gd, pr, br, edit, {'name': 'Find the Lost Key', 'edid': 'FOLabLostKey'})['made']
qk = made[0]
view = aq.quest_view(gd, pr, qk)
q = view['quest']
check('a new quest reads back with its name and starts with the game', q['name'] == 'Find the Lost Key' and q['flags']['start_enabled'] and q['delay'] == 5.0)
ringo = gd.key(find('NPC_', 'GSRingo')) if find('NPC_', 'GSRingo') else gd.key(next(f for f, (i, r) in gd.forms.items() if r.tag == 'NPC_' and i == 0))
ref_target = gd.key(next(f for f, c2 in gd.ref_cell.items() if gd.forms[f][1].flags & tes4.PERSISTENT and gd.forms[f][1].tag == 'ACHR'))
q['stages'] = [
    {'index': 10, 'entries': [{'flags': {}, 'conditions': [], 'log': 'I should look for the key.', 'next': '',
                               'script': {'source': 'SetObjectiveDisplayed FOLabLostKey 10 1\n', 'parts': []}}]},
    {'index': 20, 'entries': [{'flags': {'complete': True}, 'conditions': [], 'log': 'I found it.', 'next': '',
                               'script': {'source': 'SetObjectiveCompleted FOLabLostKey 10 1\nplayer.AddItem Caps001 10\n', 'parts': []}}]}]
q['objectives'] = [{'index': 10, 'text': 'Find the key', 'targets': [{'target': ref_target, 'flags': 1, 'conditions': [
    {'or': False, 'op': '<', 'fn': 58, 'p1': qk, 'p2': 0, 'run': 0, 'ref': '', 'value': 20.0, 'words': 'not kept'}]}]}]
q['conditions'] = [{'or': False, 'op': '=', 'fn': 70, 'p1': 1, 'p2': 0, 'run': 1, 'ref': '', 'value': 1.0}]
res = aq.save_quest(gd, pr, edit, qk, json.loads(json.dumps(q)))
check('the quest saves', 'errors' not in res)
bad = json.loads(json.dumps(q))
bad['stages'][0]['entries'][0]['script'] = {'source': 'SetStage NoSuchQuestAtAll 10\n', 'parts': []}
res = aq.save_quest(gd, pr, edit, qk, bad)
check('a script that doesn\'t compile stops the save, and says which stage', res.get('errors') and 'Stage 10' in res['errors'][0]['where'])
check('... and the quest is as it was', 'SetObjectiveDisplayed' in aq.quest_view(gd, pr, qk)['quest']['stages'][0]['entries'][0]['script']['source'])

path, p = written()
topm = {}
for rec, grp in p.walk():
    topm.setdefault(rec.tag, []).append((rec, grp))
subs = list(tes4.iter_subrecords(p.data(topm['QUST'][0][0])))
tags = [t for t, _d in subs]
check('the record has the game\'s order: EDID, FULL, DATA, condition, stage, flags, log, script...',
      tags[:5] == ['EDID', 'FULL', 'DATA', 'CTDA', 'INDX'] and tags[5:9] == ['QSDT', 'CNAM', 'SCHR', 'SCDA'])
check('... its target with its condition', tags[-3:] == ['NNAM', 'QSTA', 'CTDA'])
check('quests sit straight in the top group', [g[0] for g in topm['QUST'][0][1]] == [tes4.G_TOP])

# result script bytes equal the compiler's, in the record, and its references re-pointed
forms = aq.ModForms(gd, pr)
c1 = scriptc.compile_result('SetObjectiveDisplayed FOLabLostKey 10 1\n', forms)
c2 = scriptc.compile_result('SetObjectiveCompleted FOLabLostKey 10 1\nplayer.AddItem Caps001 10\n', forms)
mine = len(p.header['masters']) << 24
qid = topm['QUST'][0][0].formid
at = {n: i for n, i in zip([20], [k for k, (t, _d) in enumerate(subs) if t == 'INDX'][1:])}[20]
blocks = [k for k, (t, _d) in enumerate(subs) if t == 'SCHR']
sc1 = dict(subs[blocks[0]:blocks[1]])
sc2 = subs[blocks[1]:]
check('stage 10\'s compiled bytes are the compiler\'s', sc1['SCDA'] == c1.data and sc1['SCHR'] == c1.schr() and sc1['SCTX'] == c1.source)
check('stage 20\'s too', dict(sc2)['SCDA'] == c2.data and dict(sc2)['SCHR'] == c2.schr())
sco = [struct.unpack('<I', d)[0] for t, d in subs[blocks[0]:blocks[1]] if t == 'SCRO']
check('a stage script\'s reference to the mod\'s own quest is the plugin\'s own ID', sco == [qid] and qid >> 24 == mine >> 24)
sco2 = [struct.unpack('<I', d)[0] for t, d in sc2 if t == 'SCRO']
check('and to the game\'s forms by the master list', len(sco2) == 3 and qid in sco2 and 0x14 in sco2 and all(x >> 24 == 0 for x in sco2 if x != qid))
cta = [d for t, d in subs if t == 'CTDA'][1]
check('a target\'s GetStage condition names the mod\'s own quest, re-pointed', struct.unpack_from('<I', cta, 12)[0] == qid and struct.unpack_from('<f', cta, 4)[0] == 20.0 and cta[0] >> 5 == 4)
qsta = next(d for t, d in subs if t == 'QSTA')
check('a target is the game\'s ref by the master list', struct.unpack_from('<I', qsta, 0)[0] & 0xFFFFFF == gd.from_key(ref_target) & 0xFFFFFF and qsta[4] == 1)

# copy of a game quest
game_q = next(f for f, (i, r) in gd.forms.items() if r.tag == 'QUST' and i == 0 and b'SCDA' in gd.plugins[i].data(r) and b'CNAM' in gd.plugins[i].data(r))
ck = aq.copy_quest(gd, pr, br, edit, gd.key(game_q))['made'][0]
cq = aq.quest_view(gd, pr, ck)['quest']
orig = aq.quest_view(gd, pr, gd.key(game_q))['quest']
check('a copy of a game quest has its stages and objectives, and an editor ID of its own',
      len(cq['stages']) == len(orig['stages']) and cq['edid'] != orig['edid'] and len(cq['objectives']) == len(orig['objectives']))
res = aq.save_quest(gd, pr, edit, ck, json.loads(json.dumps(cq)))
check('saving it without changes keeps its compiled scripts as they were',
      'errors' not in res and [s for s in pr.records[ck]['subs'] if s['tag'] == 'SCDA'] == [s for s in recordio.load(gd, game_q)['subs'] if s['tag'] == 'SCDA'])
check('every stage has its script header', all(e.get('script') for st in aq.quest_view(gd, pr, ck)['quest']['stages'] for e in st['entries']))

# ---- 3. a conversation for a new character, greeting to goodbye ----
npc_src = next(f for f, (i, r) in gd.forms.items() if r.tag == 'NPC_' and i == 0 and 'VTCK' in gd.plugins[i].fields(r) and 'FULL' in gd.plugins[i].fields(r))
npc = pr.apply('New character', [{'op': 'record_new', 'record': dict(recordio.load(gd, npc_src), copied_from=gd.key(npc_src))}])[0]
pr.records[npc]['subs'] = [dict(s, value='FOLabKeyKeeper') if s['tag'] == 'EDID' else dict(s, value='Key Keeper') if s['tag'] == 'FULL' else s for s in pr.records[npc]['subs']]
out = aq.start_conversation(gd, pr, br, edit, {'who': npc, 'quest': qk, 'text': 'You look lost. Need something?'})
greet = out['made'][0]
ans = aq.add_choice(gd, pr, br, edit, {'line': greet, 'prompt': 'I lost a key.', 'text': 'This one? Take it. And take care of it this time, stranger. I found it by the water tower on the east road, out past the old pumps, and I have no use for it now.', 'goodbye': False})
t1 = ans['topic']
line1 = [k for k in aq.lines_of_topic(gd, pr, t1)][0]
bye = aq.add_choice(gd, pr, br, edit, {'line': line1, 'prompt': 'Thanks. Goodbye.', 'text': 'Goodbye.', 'goodbye': True})
t2 = bye['topic']
line2 = aq.lines_of_topic(gd, pr, t2)[0]
lv = aq.line_view(gd, pr, line1)
lp = lv['line']
lp['end'] = {'source': 'SetStage FOLabLostKey 20\n', 'parts': lp['end']['parts']}
res = aq.save_line(gd, pr, edit, line1, json.loads(json.dumps(lp)))
check('a line with a result script saves', 'errors' not in res)
c3 = scriptc.compile_result('SetStage FOLabLostKey 20\n', aq.ModForms(gd, pr))
cv = aq.convo(gd, pr, who=npc)
check('the conversation starts at the greeting', cv['greeting'] == qr.GREETING and cv['who']['name'] == 'Key Keeper')
tops = {t['key']: t for t in cv['topics']}
g = tops[qr.GREETING]['lines'][0]
check('the greeting says its words, and who says them', g['text'].startswith('You look lost') and g['who'][0]['key'] == npc and 'Key Keeper' in g['when'][0])
check('choices follow: greeting to answer to goodbye', g['choices'][0]['key'] == t1 and tops[t1]['lines'][0]['choices'][0]['key'] == t2 and tops[t2]['lines'][0]['goodbye'])
check('the line says which stage it sets', tops[t1]['lines'][0]['does'][0]['stage'] == 20 and 'FOLabLostKey' in tops[t1]['lines'][0]['does'][0]['text'])
check('long words are cut into responses a subtitle can hold, at the ends of sentences', len(tops[t1]['lines'][0]['line']['responses']) == 2 and all(len(r['text']) <= 150 for r in tops[t1]['lines'][0]['line']['responses']))

path, p = written()
info_groups = {}
dials = {}
order = []
for rec, grp in p.walk():
    order.append((rec.tag, rec.formid, tuple((g[0], g[1]) for g in grp)))
    if rec.tag == 'DIAL':
        dials[rec.formid] = rec
    if rec.tag == 'INFO':
        info_groups.setdefault(grp[-1][1], []).append(rec)
own = len(p.header['masters']) << 24
gid = 0xC8
tid1, tid2 = own | int(t1[1:], 16), own | int(t2[1:], 16)
check('a new topic is a DIAL straight in the top group', all(o[2] == ((tes4.G_TOP, struct.unpack('<I', b'DIAL')[0]),) for o in order if o[0] == 'DIAL'))
check('every line sits in its topic\'s children group (type 7, labelled with the DIAL)',
      all(o[2][-1][0] == tes4.G_TOPIC_CHILDREN and o[2][-1][1] in dials and len(o[2]) == 2 for o in order if o[0] == 'INFO'))
check('... straight after that DIAL in the file', all(order[n - 1][0] in ('DIAL', 'INFO') and (order[n - 1][1] == o[2][-1][1] or order[n - 1][0] == 'INFO') for n, o in enumerate(order) if o[0] == 'INFO'))
check('the greeting went under the game\'s GREETING, the answers under their own topics', set(info_groups) == {gid, tid1, tid2})

# the copied GREETING lists the file's own quests and ours
gsubs = list(tes4.iter_subrecords(p.data(dials[gid])))
base = [d for t, d in tes4.iter_subrecords(gd.plugins[0].data(qr.line_index(gd).first_topic[gid][1])) if t == 'QSTI']
got = [d for t, d in gsubs if t == 'QSTI']
check('GREETING is copied from FalloutNV.esm, its %d quests kept and ours added' % len(base), got[:len(base)] == base and got[len(base):] == [struct.pack('<I', qid)])
check('... its other parts as they were', [t for t, _d in gsubs if t not in ('QSTI', 'INFC', 'INFX')] == ['EDID', 'FULL', 'PNAM', 'DATA'])
check('a new mod with game lines needs only the files it uses', [m.lower() for m in p.header['masters']] == ['falloutnv.esm'])

# a line's record
g_info = info_groups[gid][0]
gs = list(tes4.iter_subrecords(p.data(g_info)))
tags = [t for t, _d in gs]
check('a line has the game\'s order: DATA, QSTI, TRDT, NAM1, NAM2, NAM3, condition, choices, script, NEXT, script',
      tags == ['DATA', 'QSTI', 'TRDT', 'NAM1', 'NAM2', 'NAM3', 'CTDA', 'TCLT', 'SCHR', 'NEXT', 'SCHR'])
d = dict(gs)
check('its quest is ours, its choice our topic, re-pointed', struct.unpack('<I', d['QSTI'])[0] == qid and struct.unpack('<I', d['TCLT'])[0] == tid1)
check('its condition names our character', struct.unpack_from('<I', d['CTDA'], 12)[0] == own | int(npc[1:], 16) and struct.unpack_from('<H', d['CTDA'], 8)[0] == 72)
trdt = d['TRDT']
check('silent: no sound named, the words in NAM1, the other two empty, as the game keeps them',
      len(trdt) == 24 and struct.unpack_from('<I', trdt, 16)[0] == 0 and trdt[12] == 1 and d['NAM2'] == b'\0' and d['NAM3'] == b'\0' and d['NAM1'] == b'You look lost. Need something?\0')
check('an empty script is what the game\'s empty ones are', d['SCHR'] == struct.pack('<IIIIHH', 0, 0, 0, 0, 0, 1))
l1 = next(r for r in info_groups[tid1])
ls = list(tes4.iter_subrecords(p.data(l1)))
at = [k for k, (t, _d) in enumerate(ls) if t == 'NEXT'][0]
after = dict(ls[at + 1:])
check('the line\'s result script bytes are the compiler\'s, after the NEXT', after['SCDA'] == c3.data and after['SCHR'] == c3.schr() and after['SCTX'] == c3.source and struct.unpack('<I', after['SCRO'])[0] == qid)
check('goodbye: the flag is on the line that ends it', struct.unpack_from('<H', dict(tes4.iter_subrecords(p.data(info_groups[tid2][0])))['DATA'], 2)[0] & 1)
td = dict(tes4.iter_subrecords(p.data(dials[tid1])))
check('the player\'s words are the topic\'s name, in a plain topic for our quest',
      td['FULL'] == b'I lost a key.\0' and struct.unpack('<I', td['QSTI'])[0] == qid and td['DATA'] == b'\0\0' and struct.unpack('<f', td['PNAM'])[0] == 50.0)

# the whole plugin, read by the game's reader on top of the game
gd2 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [path])
me = len(gd2.plugins) - 1
idx2 = qr.line_index(gd2)
g2 = (me << 24) | int(t1[1:], 16)
check('read on top of the game, the topics hold their lines', len(idx2.lines[g2]) == 1 and idx2.topic_of[idx2.lines[g2][0]] == g2)
check('the game\'s own greeting lines are still there, and ours is last', len(idx2.lines[gid]) > 100 and idx2.lines[gid][-1] >> 24 == me)
check('the character\'s lines are found by who they name', len(idx2.by_who.get((me << 24) | int(npc[1:], 16), ())) == 3)

# order is order of choosing: moved lines change places in the group
more = aq.new_line(gd, pr, edit, {'topic': t1, 'quest': qk, 'who': npc, 'text': 'Another answer.'})['made'][0]
aq.move_line(gd, pr, edit, more, -1)
check('moving a line up puts it first in the topic', aq.lines_of_topic(gd, pr, t1)[0] == more)
path, p = written()
inf = [rec.formid & 0xFFFFFF for rec, grp in p.walk() if rec.tag == 'INFO' and grp[-1][1] == tid1]
check('... and first in the plugin', inf[0] == int(more[1:], 16))
aq.delete_line(gd, pr, edit, more)
check('a line deleted is gone from the topic', more not in aq.lines_of_topic(gd, pr, t1))

# editing a game line: an override under a copy of its topic, nothing else moved
game_line = next(f for f, t in qr.line_index(gd).topic_of.items() if f >> 24 == 0 and t is not None and t & 0xFFFFFF > 0x800 and b'TRDT' in gd.plugins[0].data(gd.forms[f][1]))
gl = aq.line_view(gd, pr, gd.key(game_line))
was_subs = list(tes4.iter_subrecords(gd.plugins[0].data(gd.forms[game_line][1])))
gl['line']['responses'][0]['text'] = 'Changed words.'
aq.save_line(gd, pr, edit, gd.key(game_line), json.loads(json.dumps(gl['line'])))
path, p = written()
got = next(rec for rec, grp in p.walk() if rec.tag == 'INFO' and rec.formid == game_line & 0xFFFFFF)
same = list(tes4.iter_subrecords(p.data(got)))
diff = [t for (t, a), (_t2, b) in zip(was_subs, same) if a != b]
check('a game line edited: only its words change', diff == ['NAM1'] and len(same) == len(was_subs))
check('... in its own topic\'s group', next(grp for rec, grp in p.walk() if rec.formid == game_line & 0xFFFFFF and rec.tag == 'INFO')[-1][1] == qr.line_index(gd).topic_of[game_line] & 0xFFFFFF)
pr.apply('Put back', [{'op': 'record_revert', 'key': gd.key(game_line)}])

# a line saved from Browse (it knows nothing of topics) still lands in its group
g3 = next(f for f, t in qr.line_index(gd).topic_of.items() if f >> 24 == 0 and t is not None and t != game_line and f != game_line)
pr.apply('From Browse', [{'op': 'record', 'key': gd.key(g3), 'record': recordio.load(gd, g3)}])
path, p = written()
check('a line saved from Browse goes in its topic\'s group, not a top group', all(len(grp) == 2 and grp[-1][0] == 7 for rec, grp in p.walk() if rec.tag == 'INFO'))
pr.apply('Put back', [{'op': 'record_revert', 'key': gd.key(g3)}])

# undo
n = len(pr.records)
aq.add_choice(gd, pr, br, edit, {'line': line2, 'prompt': 'One more thing.', 'text': 'What?'})
check('a new choice makes a topic and a line', len(pr.records) == n + 2)
pr.undo()
check('... one Undo takes both away', len(pr.records) == n and pr.records[line2]['subs'] is not None and not any(s['tag'] == 'TCLT' for s in pr.records[line2]['subs']))

# ---- 4. the board ----
b = aq.board(gd, pr, qk)
check('the board has the stages in order', [s['index'] for s in b['stages']] == [10, 20])
m = [x for x in b['moves'] if x['to'] == 20]
check('... and the line that moves it', m and m[0]['kind'] == 'line' and m[0]['who'] == ['Key Keeper'] and 'Take it' in m[0]['text'])
check('a stage nothing sets is flagged; one that something sets isn\'t', b['stages'][0]['unset'] and not b['stages'][1]['unset'])
check('a stage that completes the quest is marked', b['stages'][1]['complete'] and not b['stages'][1]['dead'])

# ---- 5. the check ----
ch = aq.check_quest(gd, pr, qk)
text = ' | '.join(x['text'] for x in ch['items'])
check('check: a stage nothing sets', 'Stage 10: nothing sets it' in text)
check('check: an objective nothing completes is found only when nothing does', 'nothing completes it' not in text and 'nothing shows it' not in text)
check('check: no complaint about stage 20, which a line sets', 'Stage 20' not in text)
orphan = pr.apply('Orphan', [{'op': 'record_new', 'record': qr.topic_record({'edid': 'FOLabOrphan', 'name': 'Nobody asks this', 'priority': 50.0, 'kind': 0, 'quests': [{'quest': qk, 'links': []}]})}])[0]
ol = aq._compiled_line(gd, pr, aq.new_line_plain(gd, pr, orphan, qk, None, 'Hello?'))
ok = pr.apply('Orphan line', [{'op': 'record_new', 'record': ol}])[0]
broken = qr.info_plain(pr.records[ok])
# (a script that compiled once and whose form has since gone: its source names what's no longer there)
gone = aq.compile_parts('SetStage FOLabLostKey 20\n', aq.ModForms(gd, pr))
for part in gone:
    if part['tag'] == 'SCTX':
        part['value'] = b'SetStage FOLabGoneQuest 5\r\n'.hex()
broken['end'] = {'source': 'SetStage FOLabGoneQuest 5\n', 'parts': gone}
pr.records[ok] = qr.info_record(broken)
obj = aq.quest_view(gd, pr, qk)['quest']
obj['objectives'].append({'index': 99, 'text': 'Do what nobody can', 'targets': []})
aq.save_quest(gd, pr, edit, qk, json.loads(json.dumps(obj)))
ch = aq.check_quest(gd, pr, qk)
text = ' | '.join(x['text'] for x in ch['items'])
check('check: a topic nobody can reach', 'Topic "Nobody asks this": nobody can reach it' in text)
check('check: objectives nothing shows and nothing completes', 'Objective 99' in text and 'nothing shows it' in text and 'nothing completes it' in text)
check('check: a script that doesn\'t compile', 'doesn\'t compile' in text and 'FOLabGoneQuest' in text)
check('check: a line with no conditions', 'no conditions' in text)
pr.records[npc]['subs'] = [s for s in pr.records[npc]['subs'] if s['tag'] not in ('VTCK', 'TPLT')]
ch = aq.check_quest(gd, pr, qk)
check('check: a character with no voice type', any('no voice type' in x['text'] for x in ch['items']))
q2 = pr.apply('Idle quest', [{'op': 'record_new', 'record': qr.quest_record({'edid': 'FOLabIdle', 'flags': {}, 'priority': 0, 'delay': 5.0})}])[0]
check('check: a quest nothing starts', any(x['kind'] == 'start' for x in aq.check_quest(gd, pr, q2)['items']))
gq = aq.check_quest(gd, pr, gd.key(game_q))
check('a game quest checks without errors, and its stages are found set by the game\'s scripts', gq['problems'] < 40 and isinstance(gq['items'], list))
print('game quest %s: %d problems, %d notes' % (gq['edid'], gq['problems'], gq['notes']))

# ---- plain words ----
w = aq.condition_words(gd, pr, {'fn': 58, 'p1': qk, 'p2': 0, 'op': '>=', 'value': 10.0, 'run': 0})
check('words for a stage check: ' + w, 'Find the Lost Key' in w and 'at least 10' in w)
w = aq.condition_words(gd, pr, {'fn': 59, 'p1': qk, 'p2': 20, 'op': '=', 'value': 0.0, 'run': 0})
check('words for a stage not reached: ' + w, 'stage 20 hasn\'t been reached' in w)
w = aq.condition_words(gd, pr, {'fn': 70, 'p1': 1, 'p2': 0, 'op': '=', 'value': 1.0, 'run': 1})
check('words for who: ' + w, w == 'The player is female')
fl = aq.functions(gd)
check('the functions list starts with the common ones', fl[0]['name'] == 'GetIsID' and fl[0]['params'][0]['kind'] == 'form' and next(f for f in fl if f['name'] == 'GetIsSex')['params'][0]['kind'] == 'list')
