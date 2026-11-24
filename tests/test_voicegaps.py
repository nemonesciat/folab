"""voicegaps: who can say a line (GetIsID, GetInFaction through SNAM, GetIsVoiceType keeps folders, run on target not the
speaker); fill speaks each missing folder with the right voice (the line's own folder its choice, a crowd's other folders a
voice of their own, the other sex never the line's voice), copies a take already made, notes only the line's own folder."""
import os
import sys
import tempfile
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app'))
import voicegaps as VG  # noqa: E402

FAILS = []


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)
    if not ok:
        FAILS.append(what)


def cond(fn, p1, op='=', value=1, run=0):
    return {'fn': fn, 'p1': p1, 'op': op, 'value': value, 'run': run}


pr = types.SimpleNamespace(records={
    '+A': {'type': 'NPC_', 'subs': [{'tag': 'SNAM', 'fields': [{'name': 'Faction', 'value': '+F'}, {'name': 'Rank', 'value': 0}]}]},
    '+B': {'type': 'NPC_', 'subs': [{'tag': 'SNAM', 'fields': [{'name': 'Faction', 'value': '+F'}]}]},
    '+C': {'type': 'NPC_', 'subs': []},
    'FalloutNV.esm:000001': {'type': 'NPC_', 'subs': [{'tag': 'SNAM', 'fields': [{'name': 'Faction', 'value': '+F'}]}]},
})
mem = VG._members(pr)
check('faction members: the mod\'s own with that SNAM', sorted(mem.get('+F', [])) == ['+A', '+B'])
keys, only = VG.speakers({'speaker': '', 'conditions': [cond(72, '+C', **{}), cond(71, '+F')]}, mem)
check('GetIsID and GetInFaction both name speakers', keys == ['+C', '+A', '+B'] and only is None)
keys, only = VG.speakers({'speaker': '', 'conditions': [cond(72, '+C', run=1), cond(72, '+A', value=0)]}, mem)
check('a condition on the target, or == 0, names nobody', keys == [])
keys, only = VG.speakers({'speaker': '+C', 'conditions': [cond(427, '+V')]}, mem)
check('a speaker field counts; GetIsVoiceType keeps the folders', keys == ['+C'] and only == ['+V'])

# fill, with the voice maker and the mod's voices faked
import api_voices as av  # noqa: E402
import library  # noqa: E402
import voicegen  # noqa: E402
root = tempfile.mkdtemp()
spoken = []


def fake_write(base, text, voice, speed, pitch, lively, **kw):
    os.makedirs(os.path.dirname(base), exist_ok=True)
    for ext in ('.ogg', '.lip'):
        open(base + ext, 'w').write(voice)
    spoken.append((os.path.basename(os.path.dirname(base)), voice))


voices = {'lines': {}, 'npc': {}, 'type': {}}
voicegen.write_line = fake_write
voicegen.is_female = lambda v: v.startswith('af_')
av.load = lambda pr: voices
av.save = lambda pr, d: None
av.engine_of = lambda v: 'kokoro'
av.line_info = lambda gd, pr, k, v=None: {'choice': {'voice': 'am_onyx', 'speed': 0.9, 'pitch': 0.0, 'lively': 1.3}}
library.assets_dir = lambda pr: root
library.publish = lambda pr: None
VG._VT.update({'x': None})          # (no voice types to look up)


def m(folder, female, primary, keys, text='Aloha.'):
    return {'line': '+L1', 'number': 1, 'text': text, 'path': os.path.join('sound', 'voice', 'w.esp', folder, 'q_t_1_1'),
            'folder': folder, 'female': female, 'primary': primary, 'keys': keys, 'mood': [0, 50]}


crowd = ['+A', '+B']
got = VG.fill(None, pr, [m('maleadult01default', False, True, crowd), m('maleadult03', False, False, crowd),
                         m('femaleadult02', True, False, crowd)])
by = dict(spoken)
check('the line\'s own folder keeps its choice', by.get('maleadult01default') == 'am_onyx')
check('a crowd\'s other folder gets a voice of its own', by.get('maleadult03') not in (None, 'am_onyx'))
check('a woman\'s folder never gets the man\'s voice', by.get('femaleadult02', 'am_').startswith('af_'))
check('every file there', all(os.path.isfile(os.path.join(root, x['path']) + e) for x in [m('maleadult03', 0, 0, crowd)] for e in ('.ogg', '.lip')))
check('only the line\'s own folder noted in voices.json', voices['lines']['+L1']['1']['path'].endswith(os.path.join('maleadult01default', 'q_t_1_1')))
spoken.clear()
got = VG.fill(None, pr, [m('maleadult01default', False, True, ['+C']), m('maleadult03', False, False, ['+C'])])
check('one person in two folders of the same sex: one take, copied', len(spoken) == 1 and got['copied'] == 1)
if FAILS:
    sys.exit(1)
