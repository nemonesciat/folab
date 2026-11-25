"""A rebreather made at a workbench (docs/waikiki-speech-science.md section J, system 7): Science 70 makes a mask you can
breathe under water with, so the island's sea is something to go down into.

- **The mask:** FOLabRebreather, the game's Rebreather (VMS15Rebreather: its model, its picture, its Water Breathing
  enchantment) copied as an item of the mod's own, not the quest's. Its quest flag (0x400 on the record) is left off.
- **How it lets you breathe:** as the game's does. Its script adds the game's spell VMS15WaterBreathingActual when you put
  it on and takes it away once you aren't wearing it (the game's own script names only its own mask, so ours has its own).
- **The recipe:** FOLabRecipeRebreather at a workbench (WorkbenchRecipes, MiscSubRecipes), Science 70:
  2 Surgical Tubing, 2 Duct Tape, a Sensor Module and a Fission Battery.

    plan(gd, pr)       (rows, skipped)
    ops(gd, pr, P)     (ops, report): one Undo
"""
import json

import recordio

LABEL = 'A rebreather made at a workbench'
MASK, SCRIPT, RECIPE = 'FOLabRebreather', 'FOLabRebreatherScript', 'FOLabRecipeRebreather'
FROM = 'VMS15Rebreather'
SPELL = 'VMS15WaterBreathingActual'
SCIENCE, LEVEL = 40, 70                         # (the actor value Science, and the skill it takes)
CATEGORY, SUB = 'WorkbenchRecipes', 'MiscSubRecipes'
NEEDS = [('SurgicalTubing', 2), ('DuctTape', 2), ('SensorModule', 1), ('FissionBattery', 1)]
SOURCE = """scn FOLabRebreatherScript

short worn

Begin OnEquip player
\tplayer.AddSpell %(spell)s
\tset worn to 1
End

Begin GameMode
\tif worn == 1 && player.GetEquipped %(mask)s == 0
\t\tplayer.RemoveSpell %(spell)s
\t\tset worn to 0
\tendif
End
"""


def _game(gd, tag, edid):
    f = next((f for f, (_i, r) in gd.forms.items() if r.tag == tag and gd.edid(f) == edid), None)
    if f is None:
        raise ValueError('the game has no %s %s' % (tag, edid))
    return f


def plan(gd, pr):
    rows, skipped = [], []
    if any(recordio.field(r, 'EDID') == MASK for r in pr.records.values()):
        skipped.append((MASK, 'already in the mod (Undo first)'))
        return rows, skipped
    for tag, e in [('ARMO', FROM), ('SPEL', SPELL), ('RCCT', CATEGORY), ('RCCT', SUB)] + [('MISC', n) for n, _c in NEEDS]:
        try:
            _game(gd, tag, e)
        except ValueError as x:
            skipped.append((e, str(x)))
    if not skipped:
        rows.append({'what': 'rebreather', 'science': LEVEL, 'needs': NEEDS})
    return rows, skipped


def ops(gd, pr, P=None):
    import api_scripts
    from activity import _new_key
    from surffish import _copy
    rows, skipped = P or plan(gd, pr)
    if not rows:
        raise ValueError('nothing to make: %s' % (skipped,))
    mask_key, script_key, recipe_key = _new_key(pr), _new_key(pr), _new_key(pr)
    mask = _copy(gd, 'ARMO', FROM, MASK, 'Rebreather')
    mask['flags'] = mask.get('flags', 0) & ~0x400
    for s in mask['subs']:
        if s['tag'] == 'SCRI':
            s['value'] = script_key
    sc = api_scripts.scripts()
    c = sc.compile(SOURCE % {'spell': SPELL, 'mask': MASK}, script_key, 'object', {mask_key: mask})
    if not hasattr(c, 'subrecords'):
        raise ValueError('the rebreather script: %s' % (c,))
    k = lambda tag, e: gd.key(_game(gd, tag, e))
    recipe = recordio.load(gd, _game(gd, 'RCPE', 'RecipeStimpak'))           # (a workbench recipe at Science: its layout)
    like = {s['tag']: s for s in recipe['subs']}
    count = lambda n: dict(json.loads(json.dumps(like['RCQY'])), fields=[{'name': 'Count', 'code': 'i', 'value': n}])
    _sub = lambda tag, value: dict(json.loads(json.dumps(like[tag])), value=value)
    head = [s for s in recipe['subs'] if s['tag'] in ('EDID', 'FULL', 'DATA')]
    for s in head:
        if s['tag'] == 'EDID':
            s['value'] = RECIPE
        if s['tag'] == 'FULL':
            s['value'] = 'Rebreather'
        if s['tag'] == 'DATA':
            for f in s['fields']:
                f['value'] = {'Skill': SCIENCE, 'Level': LEVEL, 'Category': k('RCCT', CATEGORY),
                              'Sub-category': k('RCCT', SUB)}.get(f.get('name'), f['value'])
    body = []
    for n, c_ in NEEDS:
        body += [_sub('RCIL', k('MISC', n)), count(c_)]
    body += [_sub('RCOD', mask_key), count(1)]
    recipe.update(src='', subs=head + body)
    recipe.pop('copied_from', None)
    out = [{'op': 'record', 'key': mask_key, 'record': mask},
           {'op': 'record', 'key': script_key, 'record': sc._record_of(c, SCRIPT)},
           {'op': 'record', 'key': recipe_key, 'record': recipe}]
    return out, {'made': [MASK, SCRIPT, RECIPE], 'keys': {'mask': mask_key, 'script': script_key, 'recipe': recipe_key},
                 'science': LEVEL, 'needs': NEEDS, 'skipped': skipped}
