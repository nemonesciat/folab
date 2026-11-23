"""A mod as a program's file (23 Nov 2026, the user: "you Open it ... and can save, save as, open"): FOLab's copy
(project.working) keeps edits out of the mod until Save, in <mod>.recovery; store() moves them in; a FOLab that died with
unsaved edits leaves them to be got back; the lock is held only while something is unsaved, and an edit made after another
program changed the mod opens it again first. Save As (server.save_as) writes a copy that shares the mod's own files."""
import json
import os
import subprocess
import sys
import types

APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app')
sys.path.insert(0, APP)
import project  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


def rec(key, edid):
    return {'op': 'record', 'key': key, 'record': {'type': 'MISC', 'EDID': edid}}


def files(pr):
    out = []
    for p in (pr.path, pr.journal_path):
        try:
            st = os.stat(p)
            out.append((st.st_size, st.st_mtime_ns))
        except OSError:
            out.append(None)
    return out


def child(code):
    return subprocess.run([sys.executable, '-c', 'import sys; sys.path.insert(0, %r); import project\n' % APP + code],
                          capture_output=True, text=True, env=dict(os.environ))


base = project.Project.create('Work')
base.apply('first', [rec('+000900', 'Saved1')])         # (a plain copy: written straight in, as scripts do)

# ---- unsaved until Save
pr = project.Project.open('Work')
pr.working = True
before = files(pr)
pr.apply('a box', [rec('+000901', 'Unsaved1')])
pr.apply('another', [rec('+000902', 'Unsaved2')])
check("edits don't touch the mod's files", files(pr) == before, (before, files(pr)))
check('they are in the recovery file', os.path.exists(pr.recovery_path) and pr.unsaved() and pr.unsaved_edits == 2)
check('the mod is held while unsaved', json.load(open(project.lock_path(pr.path)))['pid'] == os.getpid())
r = child('pr = project.Project.open("Work")\nprint(sorted(pr.records))\npr.records["+000999"] = {"type": "MISC"}\n'
          'try:\n    pr.sync(); print("WROTE")\nexcept project.InUse: print("REFUSED")')
check('another program reads the saved mod only', "'+000901'" not in r.stdout and "'+000900'" in r.stdout, r.stdout + r.stderr)
check('and may not write it while something is unsaved', 'REFUSED' in r.stdout, r.stdout + r.stderr)
pr.undo()
check('Undo works on unsaved edits', '+000902' not in pr.records and pr.unsaved())
pr.redo()
n = pr.store()
check('Save moves them into the mod (two edits, an undo, a redo)', n == 4 and not os.path.exists(pr.recovery_path) and not pr.unsaved(), n)
check('the lock is let go', not os.path.exists(project.lock_path(pr.path)))
again = project.Project.open('Work')
check('opened again, the saved mod has them', {'+000900', '+000901', '+000902'} <= set(again.records))
pr.undo()
check('Undo after Save makes it unsaved again', pr.unsaved() and '+000902' not in pr.records)
pr.store()

# ---- nothing unsaved: another program may change the mod; the next edit opens it again first
r = child('pr = project.Project.open("Work")\npr.apply("script", [{"op": "record", "key": "+000910", "record": {"type": "MISC", "EDID": "Script"}}])\nprint("OK")')
check('with nothing unsaved, a script may write the mod', 'OK' in r.stdout, r.stdout + r.stderr)
pr.apply('mine', [rec('+000911', 'Mine')])
check("FOLab's next edit goes on what the script made", pr.reloaded and '+000910' in pr.records and '+000911' in pr.records)
pr.store()
both = project.Project.open('Work')
check('both saved, neither lost', {'+000910', '+000911'} <= set(both.records))

# ---- FOLab dies with unsaved edits: they are offered back
code = ('pr = project.Project.open("Work")\npr.working = True\n'
        'pr.apply("lost?", [{"op": "record", "key": "+000920", "record": {"type": "MISC", "EDID": "Crash1"}}])\n'
        'pr.apply("lost?", [{"op": "record", "key": "+000921", "record": {"type": "MISC", "EDID": "Crash2"}}])\n'
        'import os; os._exit(1)')
child(code)
pr = project.Project.open('Work')
pr.working = True
f = pr.recovery_found
check('a FOLab that died left them, found on open', f and f['edits'] == 2 and f['fits'], f)
check('not laid on by themselves', '+000920' not in pr.records)
check("its lock counts for nothing", project.holder(pr.path) is None)
got = pr.recover()
check('got back, still unsaved', got == 2 and '+000921' in pr.records and pr.unsaved() and pr.recovery_found is None, got)
pr.apply('one more', [rec('+000922', 'After')])
pr.store()
check('then saved, all three', {'+000920', '+000921', '+000922'} <= set(project.Project.open('Work').records))

# ---- thrown away
pr.apply('throw me', [rec('+000930', 'Throw')])
pr.throw_away_recovery()
check('thrown away: the file gone, the lock let go', not os.path.exists(pr.recovery_path) and not os.path.exists(project.lock_path(pr.path)))
check('the saved mod never had them', '+000930' not in project.Project.open('Work').records)

# ---- unsaved edits left and not yet decided are never written over
child(code.replace('+000920', '+000940').replace('+000921', '+000941'))
pr = project.Project.open('Work')
pr.working = True
pr.apply('new work', [rec('+000942', 'New')])
kept = [e for e in os.listdir(project.PROJECTS_DIR) if e.startswith('Work.recovery ') and e.endswith('.old')]
check('an undecided recovery is kept aside, not written over', len(kept) == 1, kept)

# ---- Save refused when the mod changed under unsaved edits (an app that doesn't know the lock)
with open(pr.journal_path, 'ab') as fh:
    fh.write(b'{"t":1,"set":{"records":{"+000950":{"type":"MISC"}}}}\n')
try:
    pr.store()
    check('Save refused when the mod changed under unsaved edits', False)
except ValueError as e:
    check('Save refused when the mod changed under unsaved edits, in words', 'Save As' in str(e), e)
check('and nothing lost: the unsaved edits still kept', os.path.exists(pr.recovery_path))
pr.throw_away_recovery()

# ---- Save As: a copy that shares the mod's own files
import library  # noqa: E402
import server  # noqa: E402
pr = project.Project.open('Work')
pr.working = True
os.makedirs(library.assets_dir(pr), exist_ok=True)
os.makedirs(os.path.join(project.PROJECTS_DIR, 'Work maps'), exist_ok=True)
with open(os.path.join(project.PROJECTS_DIR, 'Work maps', 'made.json'), 'w') as fh:
    fh.write('{}')
pr.apply('for the copy', [rec('+000960', 'CopyOnly')])
server.PR = pr
server.load_game = lambda p: None
server.save_settings = lambda **kw: None
server.state = lambda: {'project': {'name': server.PR.name}}
import loadout  # noqa: E402
loadout.current = lambda: None
mods_before = {e for e in os.listdir(project.PROJECTS_DIR) if e.endswith('.json')}
out = server.save_as('Work Two')
cp = server.PR
check('Save As opens the copy', out['project']['name'] == 'Work Two' and cp.name == 'Work Two' and cp.plugin == 'Work Two.esp')
check('the copy has the unsaved edit', '+000960' in cp.records)
check("the original doesn't", '+000960' not in project.Project.open('Work').records and not os.path.exists(pr.recovery_path))
check("its models and pictures are the original's folder", library.assets_dir(cp) == library.assets_dir(pr) and cp.files_of == 'Work')
check('small side files copied', os.path.isfile(os.path.join(project.PROJECTS_DIR, 'Work Two maps', 'made.json')))
check('only the copy is a new mod (its own file was once copied as "Work Two Two")', {e for e in os.listdir(project.PROJECTS_DIR) if e.endswith('.json')} - mods_before == {'Work Two.json'})
check('no second assets folder made', not os.path.exists(os.path.join(project.PROJECTS_DIR, 'Work Two assets')))
try:
    server.save_as('Work')
    check('a name in use is refused', False)
except ValueError:
    check('a name in use is refused', True)
