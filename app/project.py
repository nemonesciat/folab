"""A FOLab project: the changes a mod makes, kept as JSON beside FOLab and written out as an .esp on save.

    cells: {cell key: {'refs': {ref key: change}}}
      cell key / game ref key: 'FalloutNV.esm:10FDEB' (file and object ID, whatever the load order)
      new ref key: '+000800' (its object ID in this plugin)
      change: {'base': key, 'p': [x, y, z, rx, ry, rz], 's': scale} for a new ref;
              {'p': [...], 's': scale, 'base': key} for a changed game ref (each part optional: moved, rescaled,
              swapped for another thing); {'removed': True} for a removed one

Undo keeps whole copies of the changes: small for now, and impossible to get subtly wrong."""
import copy
import json
import os
import re
import time

HOME = os.environ.get('FOLAB_HOME') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS_DIR = os.path.join(HOME, 'projects')
BUILD_DIR = os.path.join(HOME, 'build')
FIRST_ID = 0x800                        # object IDs below this are the game's own


def safe_name(name):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', name).strip().strip('.')
    return name[:60] or 'New Mod'


def list_projects():
    if not os.path.isdir(PROJECTS_DIR):
        return []
    out = []
    for fn in os.listdir(PROJECTS_DIR):
        if fn.endswith('.json'):
            p = os.path.join(PROJECTS_DIR, fn)
            out.append({'name': fn[:-5], 'modified': os.path.getmtime(p)})
    return sorted(out, key=lambda x: -x['modified'])


class Project:
    def __init__(self, path):
        self.path = path
        with open(path, encoding='utf-8') as f:
            d = json.load(f)
        self.name = d['name']
        self.plugin = d['plugin']
        self.author = d.get('author', '')
        self.description = d.get('description', '')
        self.cells = d.get('cells', {})
        self.next_id = d.get('next_id', FIRST_ID)
        self.undo_stack, self.redo_stack = [], []

    @classmethod
    def create(cls, name, author='', description=''):
        os.makedirs(PROJECTS_DIR, exist_ok=True)
        name = safe_name(name)
        path = os.path.join(PROJECTS_DIR, name + '.json')
        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({'name': name, 'plugin': name + '.esp', 'author': author[:511],
                           'description': description[:511], 'cells': {}, 'next_id': FIRST_ID}, f)
        return cls(path)

    @classmethod
    def open(cls, name):
        return cls(os.path.join(PROJECTS_DIR, safe_name(name) + '.json'))

    def to_dict(self):
        return {'name': self.name, 'plugin': self.plugin, 'author': self.author, 'description': self.description,
                'cells': self.cells, 'next_id': self.next_id}

    def save(self):
        tmp = self.path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=1)
        os.replace(tmp, self.path)

    def plugin_path(self):
        os.makedirs(BUILD_DIR, exist_ok=True)
        return os.path.join(BUILD_DIR, self.plugin)

    def count(self):
        return sum(len(c['refs']) for c in self.cells.values())

    # --- edits: each one a single undo step ---

    def _step(self, label):
        self.undo_stack.append((label, copy.deepcopy(self.cells), self.next_id))
        del self.undo_stack[:-200]
        self.redo_stack.clear()

    def _refs(self, cell):
        return self.cells.setdefault(cell, {'refs': {}})['refs']

    def apply(self, label, ops):
        """Make several changes as one undo step. ops: [{'op': 'add'|'move'|'remove', ...}]. Returns the keys
        given to new refs, in order."""
        self._step(label)
        made = []
        for o in ops:
            refs = self._refs(o['cell'])
            if o['op'] == 'add':
                key = '+%06X' % self.next_id
                self.next_id += 1
                refs[key] = {'base': o['base'], 'p': [float(v) for v in o['p']], 's': float(o.get('s', 1.0))}
                made.append(key)
            elif o['op'] == 'move':
                r = refs.setdefault(o['ref'], {})
                r.pop('removed', None)
                r['p'] = [float(v) for v in o['p']]
                if 's' in o:
                    r['s'] = float(o['s'])
            elif o['op'] == 'remove':
                if o['ref'].startswith('+'):
                    refs.pop(o['ref'], None)
                else:
                    refs[o['ref']] = {'removed': True}
            elif o['op'] == 'swap':                  # the same spot, another thing
                r = refs.setdefault(o['ref'], {})
                r.pop('removed', None)
                r['base'] = o['base']
            elif o['op'] == 'revert':                # a game ref back to how the game has it
                refs.pop(o['ref'], None)
            if not refs:
                self.cells.pop(o['cell'], None)
        self.save()
        return made

    def undo(self):
        if not self.undo_stack:
            return None
        label, cells, nid = self.undo_stack.pop()
        self.redo_stack.append((label, copy.deepcopy(self.cells), self.next_id))
        self.cells, self.next_id = cells, max(nid, self.next_id)   # (an undone ref's ID is never reused)
        self.save()
        return label

    def redo(self):
        if not self.redo_stack:
            return None
        label, cells, nid = self.redo_stack.pop()
        self.undo_stack.append((label, copy.deepcopy(self.cells), self.next_id))
        self.cells, self.next_id = cells, max(nid, self.next_id)
        self.save()
        return label

    def state(self):
        return {'name': self.name, 'plugin': self.plugin, 'changes': self.count(),
                'undo': self.undo_stack[-1][0] if self.undo_stack else None,
                'redo': self.redo_stack[-1][0] if self.redo_stack else None, 'saved': time.time()}
