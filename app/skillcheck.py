"""Skill checks in dialogue, any skill as easily as Speech (the user, 25 Nov 2026: "adding lots of options for stuff makes the
game interesting. same applies for other questlines"; every quest offers several ways through).

The game's way, as FOLab Skill Proof showed for Speech in nv-rs (terminals.py's docstring): a check is a pass line and a fail
line in one topic, both with KNAM naming the skill's AVIF (the engine draws "[Repair 50]" and the like on the choice and
counts the check), conditioned GetActorValue <skill> >= N / < N on the player (run on 1). New Vegas shows Barter, Energy
Weapons, Explosives, Guns, Lockpick, Medicine, Melee Weapons, Repair, Science, Sneak, Speech, Survival and Unarmed checks
this way.

    check_lines(gd, pr, topic, quest, who, skill, need, passed, failed, on_pass='', on_fail='', conditions=())
        -> [pass plain line, fail plain line] for api_quests._compiled_line; `skill` a name as in `SKILLS`.
    tag(skill, need)    "[Repair 50]", for words that name the check themselves
"""
import api_quests as aq

# skill: (actor value number, its AVIF's editor ID, as shown); the game keeps older names for two: Guns is AVSmallGuns, Survival AVThrowing
SKILLS = {'Barter': (32, 'AVBarter', 'Barter'), 'EnergyWeapons': (34, 'AVEnergyWeapons', 'Energy Weapons'),
          'Explosives': (35, 'AVExplosives', 'Explosives'), 'Lockpick': (36, 'AVLockpick', 'Lockpick'),
          'Medicine': (37, 'AVMedicine', 'Medicine'), 'MeleeWeapons': (38, 'AVMeleeWeapons', 'Melee Weapons'),
          'Repair': (39, 'AVRepair', 'Repair'), 'Science': (40, 'AVScience', 'Science'), 'Guns': (41, 'AVSmallGuns', 'Guns'),
          'Sneak': (42, 'AVSneak', 'Sneak'), 'Speech': (43, 'AVSpeech', 'Speech'), 'Survival': (44, 'AVThrowing', 'Survival'),
          'Unarmed': (45, 'AVUnarmed', 'Unarmed')}
GETAV = 14


def _cond(op, need, av):
    return {'or': False, 'use_target': False, 'op': op, 'fn': GETAV, 'p1': av, 'p2': 0, 'run': 1, 'ref': '', 'value': float(need)}


def skill_key(gd, skill):
    """The skill's AVIF as a key (what a line's KNAM names)."""
    _av, avif, _name = SKILLS[skill]
    return gd.key(next(f for f, (_i, r) in gd.forms.items() if r.tag == 'AVIF' and gd.edid(f) == avif))


def tag(skill, need):
    return '[%s %d]' % (SKILLS[skill][2], need)


def check_lines(gd, pr, topic, quest, who, skill, need, passed, failed, on_pass='', on_fail='', conditions=()):
    """A pass and a fail line for a `skill` check at `need`. passed/failed: the speaker's words ("[SUCCEEDED] " and
    "[FAILED] " put in front unless they're there); on_pass/on_fail: result scripts; conditions: more, on both (who
    is the speaker, GetIsID, added by api_quests)."""
    if skill not in SKILLS:
        raise ValueError('no such skill: %s (one of %s)' % (skill, ', '.join(SKILLS)))
    av = SKILLS[skill][0]
    key = skill_key(gd, skill)
    out = []
    for words, op, end, mark in ((passed, '>=', on_pass, '[SUCCEEDED] '), (failed, '<', on_fail, '[FAILED] ')):
        words = words if words.startswith(mark.strip()) else mark + words
        l = aq.new_line_plain(gd, pr, topic, quest, who, words, conditions=list(conditions) + [_cond(op, need, av)])
        l['skill'] = key
        if end:
            l['end'] = {'source': end, 'parts': None}
        out.append(l)
    return out
