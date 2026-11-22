import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
"""The mod's file kept as its .json and a .changes of what each save changed (project.py): every edit reads back the same
after opening the mod again, Undo and Redo put back exactly what a step changed, a change made by hand is found, a .json
written by anything else makes old lines stale, a save broken off is cut off, long lines are folded in."""
import copy
import json
import project


def check(what, ok, more=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % more if more and not ok else ''))


def state(pr):
    return json.loads(json.dumps({k: getattr(pr, k) for k in project.DIFFED + project.WHOLE + project.HEAD}))


def same_on_disk(pr, what):
    again = project.Project.open(pr.name)
    check(what, state(again) == state(pr))
    return again


A, B = 'FalloutNV.esm:000A00', 'FalloutNV.esm:000B00'
pr = project.Project.create('Store Test')
size = os.path.getsize(pr.path)
made = pr.apply('Put things', [{'op': 'add', 'cell': A, 'base': 'FalloutNV.esm:00000F', 'p': [1, 2, 3, 0, 0, 0]},
                               {'op': 'add', 'cell': B, 'base': 'FalloutNV.esm:00000F', 'p': [4, 5, 6, 0, 0, 0]},
                               {'op': 'water', 'cell': B, 'h': None},
                               {'op': 'record_new', 'record': {'type': 'MISC', 'flags': 0, 'src': '', 'subs': []}}])
check('an edit writes a .changes, not the .json', os.path.isfile(pr.journal_path) and os.path.getsize(pr.path) == size)
same_on_disk(pr, 'the mod reads back the same')
first = state(pr)
pr.apply('Move', [{'op': 'move', 'cell': A, 'ref': made[0], 'p': [9, 9, 9, 0, 0, 0]}])
pr.apply('Ground', [{'op': 'land', 'cell': A, 'land': {'h': [1.0] * 4, 'q': []}},
                    {'op': 'navmesh', 'cell': B, 'mesh': {'verts': [], 'tris': [], 'doors': []}}])
moved = state(pr)
check('Undo puts back what the step changed', pr.undo() == 'Ground' and pr.undo() == 'Move' and state(pr) == dict(first, next_id=pr.next_id))
check('an undone ID isn\'t given again', pr.next_id == moved['next_id'])
same_on_disk(pr, 'undone, read back the same')
check('Redo makes them again', pr.redo() == 'Move' and pr.redo() == 'Ground' and state(pr) == moved)
same_on_disk(pr, 'redone, read back the same')
pr.apply('Water', [{'op': 'water', 'cell': B, 'h': 50.5}])
pr.apply('More water', [{'op': 'water_revert', 'cell': B}], merge=True)
check('a merged step undoes as one', pr.undo() == 'Water' and pr.water == {B: None} and pr.redo_stack and not pr.undo_stack[-1][0] == 'Water')
pr.apply('Again', [{'op': 'move', 'cell': B, 'ref': made[1], 'p': [7, 7, 7, 0, 0, 0]}])
check('a new edit clears Redo', not pr.redo_stack)

# a change made by hand, then written
pr.records[made[2]]['subs'].append({'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': 'ByHand'})
pr.esm = True
pr.sync()
again = same_on_disk(pr, 'a change made by hand is written by sync()')
check('… head too', again.esm is True)
pr.records[made[2]]['subs'][-1]['value'] = 'ByHand2'
pr.apply('Something else', [{'op': 'move', 'cell': A, 'ref': made[0], 'p': [8, 8, 8, 0, 0, 0]}])
same_on_disk(pr, 'and by the next edit')

# a save broken off: its line is cut off
lines = open(pr.journal_path, 'rb').read()
want = state(pr)
pr.apply('Lost', [{'op': 'move', 'cell': A, 'ref': made[0], 'p': [0, 0, 0, 0, 0, 0]}])
whole = open(pr.journal_path, 'rb').read()
with open(pr.journal_path, 'wb') as f:
    f.write(whole[:len(lines) + 20])
again = project.Project.open(pr.name)
check('a last line cut short is left out', state(again) == want)
check('… and cut off the file', open(pr.journal_path, 'rb').read() == lines)

# the .json written by something else: the old lines are stale
pr = project.Project.open('Store Test')
d = json.load(open(pr.path, encoding='utf-8'))
d['description'] = 'written by another'
json.dump(d, open(pr.path, 'w', encoding='utf-8'))
again = project.Project.open('Store Test')
check('lines on a .json written since are put aside', again.description == 'written by another' and again.cells == d.get('cells')
      and os.path.isfile(again.journal_path + '.stale') and not os.path.isfile(again.journal_path))
pr.apply('After', [{'op': 'move', 'cell': A, 'ref': made[0], 'p': [5, 5, 5, 0, 0, 0]}])
again = same_on_disk(pr, 'an edit on a mod whose .json was written since writes it whole')
check('… so the other\'s writing is gone, as before', again.description == '')

# folding the lines in
pr = project.Project.open('Store Test')
pr.compact()
check('compact(): the .json alone', not os.path.isfile(pr.journal_path))
same_on_disk(pr, 'compacted, read back the same')
project.JOURNAL_MOST = 1
grew = []
for n in range(100):
    pr.apply('Big', [{'op': 'move', 'cell': A, 'ref': made[0], 'p': [n, 6, 6, 0, 0, 0]}])
    grew.append(os.path.getsize(pr.journal_path) if os.path.isfile(pr.journal_path) else 0)
    if not grew[-1]:
        break
check('lines longer than half the .json (and JOURNAL_MOST) are folded in', not grew[-1] and len(grew) > 1
      and grew[-2] > os.path.getsize(pr.path) // 2 * 0.8, str(grew[-3:]))
same_on_disk(pr, 'folded, read back the same')
project.JOURNAL_MOST = 64 << 20

# digests follow the contents
pr = project.Project.open('Store Test')
d1 = pr.digest('cells', A)
pr.cells[A]['refs'][made[0]]['p'][0] = 123.0
pr.sync()
d2 = pr.digest('cells', A)
other = project.Project.open('Store Test')
check('a digest changes with what\'s in the entry, and is the same read back', d1 != d2 and other.digest('cells', A) == d2
      and pr.digest('cells', 'nowhere') is None)
copied = copy.deepcopy(pr.cells)
pr.cells = copied
pr.sync()
check('the same contents in other objects: the same digest', pr.digest('cells', A) == d2)
