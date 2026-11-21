"""Voicing lines from the dialogue editor (api_voices.py), with Kokoro stood in for (voicegen.write_line writes small
files): a greeting for Chet gets his voice type's folder and the game's name for its file; a character's chosen voice is
kept beside the mod (not in it) and used; a voiced line is done, out of date once its words change; a game line and a
line nobody in particular says are refused with a reason; the files reach the build beside the plugin."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import api_quests  # noqa: E402
import api_voices as AV  # noqa: E402
import browse  # noqa: E402
import gamedata  # noqa: E402
import library  # noqa: E402
import project  # noqa: E402
import server  # noqa: E402
import voicegen  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


spoken = []


engines = []


def fake_write(base, text, voice, speed, pitch, lively=1.0, engine='kokoro', feeling=None):
    spoken.append((text, voice, speed, pitch))
    engines.append((engine, feeling))
    os.makedirs(os.path.dirname(base), exist_ok=True)
    for ext in ('.ogg', '.lip'):
        with open(base + ext, 'wb') as f:
            f.write(b'x')
    return 1.0


voicegen.write_line = fake_write
os.environ.pop('FOLAB_CHATTERBOX', None)       # Kokoro unless this test puts a Chatterbox there
G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Voices')
chet = G.key(next(f for f, (i, r) in G.forms.items() if r.tag == 'NPC_' and G.edid(f) == 'GSChet'))
made = api_quests.start_conversation(G, pr, server.BR, server.edit, {'who': chet, 'text': 'Aloha. Mind the crabs.'})
line = [k for k, r in pr.records.items() if r.get('type') == 'INFO'][0]

info = AV.line_info(G, pr, line)
check('a line of the mod\'s own, said by Chet, can be voiced', info['problem'] is None, info['problem'])
check('his voice type, from his record', info['voice_type_edid'] == 'MaleAdult04', info['voice_type_edid'])
want = os.path.join('sound', 'voice', 'voices.esp', 'maleadult04', 'chettalk_greeting_%08x_1' % int(line[1:], 16))
check('the file named as the game looks for it', info['responses'][0]['path'] == want, info['responses'][0]['path'])
own = info['choice']['voice']
check('not voiced yet, a man\'s voice of his own by default', info['responses'][0]['state'] == 'none' and '+' in own
      and all(p.split('*')[0] in AV.BLEND_FROM['male'] for p in own.split('+')), own)
check('the same mix each time, another for someone else',
      AV.own_default(chet, False) == AV.own_default(chet, False) and AV.own_default(chet, False) != AV.own_default(chet + 'x', False))

AV.set_choice(G, pr, {'key': chet, 'voice': 'am_fenrir', 'speed': 0.9, 'pitch': -1})
check('his voice kept beside the mod, not in it', os.path.isfile(os.path.join(project.PROJECTS_DIR, 'Voices voices', 'voices.json'))
      and not any(k.endswith('.json') and 'voices' in k.lower() and k != 'Voices.json' for k in os.listdir(project.PROJECTS_DIR)))
after = AV.voice_line(G, pr, line)
check('voiced in his voice', spoken == [('Aloha. Mind the crabs.', 'am_fenrir', 0.9, -1.0)], spoken)
check('the line is done', after['responses'][0]['state'] == 'done')
built = os.path.join(library.built_dir(pr), want)
check('its files beside the built plugin', os.path.isfile(built + '.ogg') and os.path.isfile(built + '.lip'))

rec = pr.records[line]
for s in rec['subs']:
    if s['tag'] == 'NAM1':
        s['value'] = 'Aloha. Mind the eels.'
check('new words: out of date', AV.line_info(G, pr, line)['responses'][0]['state'] == 'old')

r = AV.voice_character(G, pr, chet, only_missing=True)
check('voice every line for him: the changed one again', r['voiced'] == 1 and spoken[-1][0] == 'Aloha. Mind the eels.', r)

game_line = next(G.key(f) for f, (i, r) in G.forms.items() if r.tag == 'INFO' and i == 0)
check('a game line is refused', 'Only your own lines' in (AV.line_info(G, pr, game_line)['problem'] or ''))
for s in rec['subs'][:]:
    if s['tag'] == 'CTDA':
        rec['subs'].remove(s)
rec.pop('conditions', None)
p = AV.line_info(G, pr, line)['problem'] or ''
check('a line nobody in particular says asks for a speaker', 'speaker' in p, p)

# ---- moods: a response's emotion nudges its voice, and a change of emotion makes it out of date ----
check('neutral changes nothing', AV.mood_of(0, 50) == (1.0, 0.0, 1.0))
sp, up, tune = AV.mood_of(4, 100)
check('sad, very strongly: slower, lower and flatter', sp < 1 and up < 0 and tune < 1, (sp, up, tune))
check('half the strength, half the nudge', abs(AV.mood_of(4, 50)[1] - up / 2) < 1e-9)
check('afraid: quicker and higher', AV.mood_of(3, 75)[0] > 1 and AV.mood_of(3, 75)[1] > 0)
check('a blend of two of Kokoro\'s is a voice; a made-up one is not',
      AV.valid_voice('am_onyx*0.6+bm_george*0.4') and not AV.valid_voice('am_onyx*0.6+nobody*0.4'))
rec['subs'].insert(0, {'tag': 'ANAM', 'label': 'Speaker', 'kind': 'F', 'value': chet}) if not any(s['tag'] == 'ANAM' for s in rec['subs']) else None
AV.voice_line(G, pr, line)
AV.set_choice(G, pr, {'key': chet, 'voice': 'am_onyx*0.6+bm_george*0.4', 'speed': 0.9, 'pitch': -1, 'lively': 1.5})
check('a new voice makes his lines out of date', AV.line_info(G, pr, line)['responses'][0]['state'] == 'old')
AV.voice_line(G, pr, line)
check('voiced in the blend', spoken[-1][1] == 'am_onyx*0.6+bm_george*0.4' and AV.line_info(G, pr, line)['responses'][0]['state'] == 'done', spoken[-1])
for s in rec['subs']:
    if s['tag'] == 'TRDT':
        for f in s['fields']:
            if f.get('name') == 'Emotion':
                f['value'] = 4
            elif f.get('name') == 'Emotion strength':
                f['value'] = 100
spoken.clear()
info = AV.line_info(G, pr, line)
if info['problem'] is None:
    check('a new emotion makes the voice out of date', info['responses'][0]['state'] == 'old', info['responses'][0])
    AV.voice_line(G, pr, line)
    base = AV.load(pr)['npc'][chet]
    check('spoken slower and lower for sad', abs(spoken[-1][2] - base['speed'] * sp) < 1e-9 and abs(spoken[-1][3] - (base['pitch'] + up)) < 1e-9, spoken[-1])
    check('then done again', AV.line_info(G, pr, line)['responses'][0]['state'] == 'done')
else:
    check('the line can be voiced again with a speaker', False, info['problem'])

# ---- Chatterbox: used once its folder is there, its feeling from the emotion; a mod can choose Kokoro again ----
check('no Chatterbox: Kokoro', AV.engine_of(AV.load(pr)) == 'kokoro' and engines[-1][0] == 'kokoro')
fake_cb = os.path.join(os.environ['FOLAB_HOME'], 'fake chatterbox')
os.makedirs(os.path.join(fake_cb, 'venv', 'Scripts'), exist_ok=True)
os.makedirs(os.path.join(fake_cb, 'venv', 'Lib', 'site-packages', 'chatterbox'), exist_ok=True)
open(os.path.join(fake_cb, 'venv', 'Scripts', 'python.exe'), 'wb').close()
os.environ['FOLAB_CHATTERBOX'] = fake_cb
info = AV.line_info(G, pr, line)
check('with Chatterbox there it is used, and lines Kokoro spoke are out of date', info['engine'] == 'chatterbox' and info['responses'][0]['state'] == 'old', info['engine'])
AV.voice_line(G, pr, line)
check('Chatterbox acts the sad line with the feeling the emotion asks', engines[-1] == ('chatterbox', AV.feeling_of(4, 100)) and AV.feeling_of(4, 100) > voicegen.CALM['exaggeration'], engines[-1])
check('a neutral line at the calm setting', AV.feeling_of(0, 50) == voicegen.CALM['exaggeration'])
AV.post('/api/voice/engine', {'engine': 'kokoro'}, G, pr)
check('the mod can choose Kokoro again', AV.line_info(G, pr, line)['engine'] == 'kokoro' and AV.line_info(G, pr, line)['responses'][0]['state'] == 'old')
os.environ.pop('FOLAB_CHATTERBOX', None)
