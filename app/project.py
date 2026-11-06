"""A FOLab project: the changes a mod makes, kept as JSON beside FOLab and written out as an .esp on save.

    cells: {cell key: {'refs': {ref key: change}}}
      cell key / game ref key: 'FalloutNV.esm:10FDEB' (file and object ID, whatever the load order)
      new ref key: '+000800' (its object ID in this plugin)
      cell key '+ID': a place of the mod's own (its CELL record in records under the same key)
      change: {'base': key, 'p': [x, y, z, rx, ry, rz], 's': scale} for a new ref;
              'tel': {'door': ref key, 'p': [x, y, z, rx, ry, rz]} on a door: where it leads (made persistent);
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
        self.records = d.get('records', {})     # form key or '+ID' -> record (recordio.py): game records changed, new ones
        self.land = d.get('land', {})           # outside CELL key -> its ground as the mod has it (land.py's form)
        self.navmesh = d.get('navmesh', {})     # place's CELL key -> its navmesh as the mod has it (navbuild.py)
        self.water = d.get('water', {})         # outside CELL key -> its water's height (None: the world's own level)
        self.source = d.get('source')           # an opened plugin: its copy, under projects/ (adopt.py); None for a new mod
        self.esm = d.get('esm', False)          # saved as a master (.esm)
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
                'cells': self.cells, 'records': self.records, 'land': self.land, 'water': self.water, 'navmesh': self.navmesh, 'next_id': self.next_id,
                'source': self.source, 'esm': self.esm}

    def save(self):
        tmp = self.path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=1)
        os.replace(tmp, self.path)

    def source_path(self):
        return os.path.join(PROJECTS_DIR, self.source) if self.source else None

    def plugin_path(self):
        os.makedirs(BUILD_DIR, exist_ok=True)
        return os.path.join(BUILD_DIR, self.plugin)

    def count(self):
        return sum(len(c['refs']) for c in self.cells.values()) + len(self.records) + len(self.land) + len(self.water) + len(self.navmesh)

    # --- edits: each one a single undo step ---

    def _step(self, label):
        self.undo_stack.append((label, copy.deepcopy(self.cells), copy.deepcopy(self.records), self.next_id, dict(self.land), dict(self.water), dict(self.navmesh)))
        del self.undo_stack[:-200]
        self.redo_stack.clear()

    def _refs(self, cell):
        return self.cells.setdefault(cell, {'refs': {}})['refs']

    def apply(self, label, ops):
        """Make several changes as one undo step. ops: [{'op': 'add'|'move'|'remove', ...}]. Returns the keys
        given to new refs, in order."""
        self._step(label)
        made, new_record = [], None
        for o in ops:
            if o['op'] == 'record':                  # a record as the mod has it (a game one changed, or its own)
                self.records[o['key']] = o['record']
                continue
            if o['op'] == 'record_new':              # a record of the mod's own: its key is made here
                key = '+%06X' % self.next_id
                self.next_id += 1
                self.records[key] = o['record']
                made.append(key)
                new_record = key
                continue
            if o['op'] == 'record_revert':           # a game record back as the game has it; one of the mod's own, gone
                self.records.pop(o['key'], None)
                continue
            if o['op'] == 'navmesh':                 # a place's navmesh, whole; its record's ID made here the first time
                mesh = dict(o['mesh'])
                if not mesh.get('form'):
                    mesh['form'] = '+%06X' % self.next_id
                    self.next_id += 1
                self.navmesh[o['cell']] = mesh
                continue
            if o['op'] == 'navmesh_revert':
                self.navmesh.pop(o['cell'], None)
                continue
            if o['op'] == 'land':                    # an outside cell's ground, whole (heights, colours, textures)
                self.land[o['cell']] = o['land']
                continue
            if o['op'] == 'land_revert':
                self.land.pop(o['cell'], None)
                continue
            if o['op'] == 'water':                   # an outside cell's water level (None: back to the world's)
                self.water[o['cell']] = None if o.get('h') is None else float(o['h'])
                continue
            if o['op'] == 'water_revert':
                self.water.pop(o['cell'], None)
                continue
            if o.get('cell') == '$new':                # (the place a record_new earlier in these ops just made)
                o = dict(o, cell=new_record)
            if o.get('base') == '$made':               # (a thing swapped for the record a record_new just made)
                o = dict(o, base=new_record)
            refs = self._refs(o['cell'])
            if o['op'] == 'tel':                     # a door's link: where it leads, or (None) nowhere new
                r = refs.setdefault(o['ref'], {})
                if o.get('tel'):
                    r['tel'] = o['tel']
                    r['persistent'] = True
                else:
                    r.pop('tel', None)
                    if not o['ref'].startswith('+'):
                        r.pop('persistent', None)
                if not r:
                    refs.pop(o['ref'], None)
            elif o['op'] == 'add':
                key = '+%06X' % self.next_id
                self.next_id += 1
                refs[key] = {'base': o['base'], 'p': [float(v) for v in o['p']], 's': float(o.get('s', 1.0))}
                if o.get('gen'):
                    refs[key]['gen'] = True          # (generated in the Kit tab)
                if o.get('sc'):
                    refs[key]['sc'] = True           # (scattered by the brush)
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
            elif o['op'] == 'props':                 # its owner, lock, what enables it (refprops.py)
                r = refs.setdefault(o['ref'], {})
                r.setdefault('props', {}).update(o['props'])
            elif o['op'] == 'persist':               # kept loaded: something else names it
                refs.setdefault(o['ref'], {})['persistent'] = True
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
        label, cells, records, nid, land, water, nav = self.undo_stack.pop()
        self.redo_stack.append((label, copy.deepcopy(self.cells), copy.deepcopy(self.records), self.next_id, dict(self.land), dict(self.water), dict(self.navmesh)))
        self.cells, self.records, self.next_id = cells, records, max(nid, self.next_id)   # (an undone ID is never reused)
        self.land, self.water, self.navmesh = land, water, nav
        self.save()
        return label

    def redo(self):
        if not self.redo_stack:
            return None
        label, cells, records, nid, land, water, nav = self.redo_stack.pop()
        self.undo_stack.append((label, copy.deepcopy(self.cells), copy.deepcopy(self.records), self.next_id, dict(self.land), dict(self.water), dict(self.navmesh)))
        self.cells, self.records, self.next_id = cells, records, max(nid, self.next_id)
        self.land, self.water, self.navmesh = land, water, nav
        self.save()
        return label

    def state(self):
        return {'name': self.name, 'plugin': self.plugin, 'changes': self.count(), 'opened': bool(self.source), 'esm': self.esm,
                'undo': self.undo_stack[-1][0] if self.undo_stack else None,
                'redo': self.redo_stack[-1][0] if self.redo_stack else None, 'saved': time.time()}
