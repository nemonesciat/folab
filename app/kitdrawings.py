"""The Kit tab's drawn floor plans: checked while drawing, and kept by name (after Morrowind Workshop's plans.py).

    check(ts, rooms, links)          what's wrong with a drawing before it's built: {'ok', 'problems', 'notes', 'rooms', 'reached'}
    save(name, drawing) / load(name) / remove(name) / names()     plans kept as JSON in FOLab's home, `plans/`, like prefabs

A drawing is the canvas's own form: {'rooms': [{'x', 'y', 'w', 'h', 'level', 'purpose', 'name'}], 'links': [[a, b]], 'kit'}.
check plans it as Build would (kitplan.plan_from_drawing: doors where linked rooms touch, corridors and stairs where they
don't, a room nobody linked joined to its nearest) but lays no pieces, so it answers in a moment; what Build then can't fill
or walk is said by Build. Problems stop a build; notes are what Build would do differently from the drawing."""
import json
import os

import kitplan as P
import project

PLANS_DIR = os.path.join(project.HOME, 'plans')
KEEP = ('rooms', 'links', 'kit')


def check(ts, rooms, links, seed=1):
    """A drawing checked as Build would plan it, without its pieces."""
    if not rooms:
        return {'ok': False, 'problems': ['Draw at least one room.'], 'notes': [], 'rooms': 0, 'reached': 0}
    if not ts.can['rooms']:
        return {'ok': False, 'problems': ['This kit has no pieces that close a room, so it can\'t build a drawn plan.'], 'notes': [], 'rooms': len(rooms), 'reached': 0}
    plan, said = P.plan_from_drawing(ts, rooms, links, seed)
    if plan is None:
        return {'ok': False, 'problems': said, 'notes': [], 'rooms': len(rooms), 'reached': 0}
    reached = P._reached(plan, 0)
    return {'ok': True, 'problems': [], 'notes': said, 'rooms': len(rooms), 'reached': sum(1 for o in plan.rooms() if o['n'] in reached),
            'flights': len(plan.flights)}


def _path(name):
    if not (name or '').strip():
        raise ValueError('Give the plan a name.')
    return os.path.join(PLANS_DIR, project.safe_name(name) + '.json')


def save(name, drawing):
    """Keeps a drawing under this name (replacing one of the same name). Returns the names kept."""
    if not drawing.get('rooms'):
        raise ValueError('There\'s nothing drawn to keep.')
    os.makedirs(PLANS_DIR, exist_ok=True)
    out = {k: drawing[k] for k in KEEP if k in drawing}
    out['name'] = name.strip()
    with open(_path(name), 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1)
    return names()


def load(name):
    with open(_path(name), encoding='utf-8') as f:
        return json.load(f)


def remove(name):
    p = _path(name)
    if os.path.isfile(p):
        os.remove(p)
    return names()


def names():
    """[{'name', 'rooms', 'kit'}] of the plans kept, by name."""
    out = []
    if os.path.isdir(PLANS_DIR):
        for fn in sorted(os.listdir(PLANS_DIR)):
            if fn.endswith('.json'):
                try:
                    with open(os.path.join(PLANS_DIR, fn), encoding='utf-8') as f:
                        d = json.load(f)
                except (OSError, ValueError):
                    continue
                out.append({'name': d.get('name') or fn[:-5], 'rooms': len(d.get('rooms', [])), 'kit': d.get('kit', '')})
    return out
