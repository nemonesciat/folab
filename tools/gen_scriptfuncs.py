"""Generate app/scriptfuncs.json: the facts the script compiler needs that only the game itself knows.

Read from the user's own FalloutNV.exe (never changed): each script function's name, short name, opcode, whether it
needs a reference and its parameters; the block types; the operators and their priorities; and the short name lists
some parameters take (animation groups, form types, misc stats...). The exe's layout is the 1.4 Steam build's; each
table is checked on the way (first and last names), so another build stops here instead of writing rubbish.

    py -3 tools/gen_scriptfuncs.py
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'app'))
import gamedata  # noqa: E402

# Where each table sits in the running game's memory
KEYWORDS = 0x118cb50
BLOCKS = 0x118e2f0
CONSOLE = 0x118e8e0
SCRIPT = CONSOLE + 206 * 40
PARAM_KINDS = 0x118cdd0
OPERATORS = 0x118cad0
ANIM_GROUPS = 0x11977d8
FORM_TYPE_NAMES, FORM_TYPE_CODES = 0x118a2d8, 0x118a598
ALIGNMENTS, CRIT_STAGES, EQUIP_TYPES, MISC_STATS = 0x1186cf4, 0x119bbb0, 0x11869bc, 0x1189280
SEXES = 0x1199e8c

# The actor values, by number. The game registers them from code at start-up, so they aren't a table in the exe; the
# names are checked to be among its strings below, and the game's scripts check the numbers (tests/test_scriptc.py).
# (SleepDeprevation is the game's own spelling.)
ACTOR_VALUES = ('Aggression Confidence Energy Responsibility Mood Strength Perception Endurance Charisma Intelligence '
                'Agility Luck ActionPoints CarryWeight CritChance HealRate Health MeleeDamage DamageResist PoisonResist '
                'RadResist SpeedMult Fatigue Karma XP PerceptionCondition EnduranceCondition LeftAttackCondition '
                'RightAttackCondition LeftMobilityCondition RightMobilityCondition BrainCondition Barter BigGuns '
                'EnergyWeapons Explosives Lockpick Medicine MeleeWeapons Repair Science Guns Sneak Speech Survival '
                'Unarmed InventoryWeight Paralysis Invisibility Chameleon NightEye Turbo FireResist WaterBreathing '
                'RadiationRads BloodyMess UnarmedDamage Assistance ElectricResist FrostResist EnergyResist EmpResist '
                'Variable01 Variable02 Variable03 Variable04 Variable05 Variable06 Variable07 Variable08 Variable09 '
                'Variable10 IgnoreCrippledLimbs Dehydration Hunger SleepDeprevation DamageThreshold').split()


class Exe:
    def __init__(self, path):
        with open(path, 'rb') as f:
            self.d = f.read()
        pe = struct.unpack_from('<I', self.d, 0x3c)[0]
        count, opt = struct.unpack_from('<H', self.d, pe + 6)[0], struct.unpack_from('<H', self.d, pe + 20)[0]
        base = struct.unpack_from('<I', self.d, pe + 52)[0]
        self.sections = []
        for i in range(count):
            vs, va, rs, rp = struct.unpack_from('<IIII', self.d, pe + 24 + opt + i * 40 + 8)
            self.sections.append((base + va, vs, rp, rs))

    def off(self, v):
        for va, vs, rp, rs in self.sections:
            if va <= v < va + vs and v - va < rs:
                return v - va + rp
        raise ValueError('address %x is not in the file' % v)

    def text(self, v):
        if not v:
            return ''
        o = self.off(v)
        return self.d[o:self.d.index(b'\0', o)].decode('cp1252')

    def u32s(self, v, n):
        return struct.unpack_from('<%dI' % n, self.d, self.off(v))

    def names(self, v, n):
        return [self.text(p) for p in self.u32s(v, n)]


def commands(exe, where, n):
    out = []
    for i in range(n):
        name, short, code, _help, flags, params, _run, _compile, _cond, _x = exe.u32s(where + i * 40, 10)
        ps = []
        for k in range(flags >> 16):
            pn, pt, opt = exe.u32s(params + k * 12, 3)
            ps.append([pt, opt & 0xff, exe.text(pn)])
        out.append({'name': exe.text(name), 'short': exe.text(short), 'code': code, 'ref': flags & 0xff, 'params': ps})
    return out


def build(exe):
    keywords = [(e['name'], e['short'], e['code']) for e in commands(exe, KEYWORDS, 16)]
    blocks = commands(exe, BLOCKS, 38)
    console = commands(exe, CONSOLE, 205)
    script = commands(exe, SCRIPT, 640)
    assert keywords[0][0] == 'Begin' and blocks[0]['name'] == 'GameMode' and console[0]['name'] == 'Show'
    assert script[1]['name'] == 'GetDistance' and script[0]['code'] == 0x1000 and script[-1]['code'] == 0x127f
    kinds = []
    for i in range(70):
        o = exe.off(PARAM_KINDS + i * 8)
        assert exe.d[o] == i
        kinds.append([exe.d[o + 4], exe.d[o + 5]])
    ops = []
    for i in range(16):
        o = exe.off(OPERATORS + i * 8)
        ops.append([struct.unpack_from('<b', exe.d, o + 4)[0], exe.d[o + 5:o + 8].split(b'\0')[0].decode('ascii')])
    for name in ACTOR_VALUES:
        assert exe.d.find(name.encode('ascii') + bytes(1)) >= 0, name
    assert len(ACTOR_VALUES) == 77
    anims = [exe.text(exe.u32s(ANIM_GROUPS + i * 36, 1)[0]) for i in range(245)]
    codes = exe.d[exe.off(FORM_TYPE_CODES):exe.off(FORM_TYPE_CODES) + 87]
    forms = dict(zip(exe.names(FORM_TYPE_NAMES, 87), codes))
    return {
        'keywords': keywords,
        'blocks': blocks,
        'console': console,
        'script': script,
        'param_kinds': kinds,
        'operators': ops,
        'anim_groups': anims,
        'form_types': forms,
        'alignments': exe.names(ALIGNMENTS, 5),
        'crit_stages': exe.names(CRIT_STAGES, 5),
        'equip_types': exe.names(EQUIP_TYPES, 14),
        'misc_stats': exe.names(MISC_STATS, 43),
        'sexes': exe.names(SEXES, 2),
        'actor_values': ACTOR_VALUES,
    }


def main():
    path = os.path.join(os.path.dirname(os.path.normpath(gamedata.find_data_dir())), 'FalloutNV.exe')
    t = build(Exe(path))
    out = os.path.join(HERE, '..', 'app', 'scriptfuncs.json')
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write('{\n')
        parts = []
        for k, v in t.items():
            if k in ('blocks', 'console', 'script'):
                body = ',\n'.join('  ' + json.dumps(e, separators=(',', ':')) for e in v)
                parts.append('"%s": [\n%s\n]' % (k, body))
            else:
                parts.append('"%s": %s' % (k, json.dumps(v, separators=(',', ':'))))
        f.write(',\n'.join(parts) + '\n}\n')
    print('wrote %s: %d script functions, %d console, %d blocks' % (out, len(t['script']), len(t['console']),
                                                                   len(t['blocks'])))
    print(t['operators'], t['alignments'], t['crit_stages'], t['sexes'], t['misc_stats'][:3], t['anim_groups'][:4])


if __name__ == '__main__':
    main()
