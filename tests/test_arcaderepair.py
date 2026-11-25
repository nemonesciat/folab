"""Repair at the Kilauea's arcade (arcaderepair.py): the script played through on stormsched's interpreter, given its
blocks and `return` here: a machine found broken; without the skill, without the part, fixed with the part (taken) and
with Tinkerer (not taken); rigging offered at 85 and not below; a rigged machine pays half again on a session that came out
ahead, capped; the court notices in time (score down, infamy, the machine fair again); a fair machine pays no bonus.
The messages' buttons match what the script reads; every message the script names is made."""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import arcaderepair as R  # noqa: E402
import stormsched as S  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


S._ARGS.update({'isactionref': 1, 'getactorvalue': 1, 'hasperk': 1, 'getitemcount': 1, 'removeitem': 2, 'additem': 2,
                'showslotmachinemenuparams': 4, 'getdistance': 1, 'addreputation': 3})


class Game(S.Game):
    def __init__(self, repair=0, parts=0, perk=False, money=100, seed=1):
        S.Game.__init__(self, seed)
        self.av = {'repair': repair}
        self.items = {R.PART.lower(): parts, 'caps001': money}
        self.perk = perk
        self.qvars = {'court': 0}
        self.infamy = 0
        self.menus = 0
        self.near = 100
        self.pct = None                         # (GetRandomPercent's answer, when fixed by the test)

    def call(self, name, args, ref):
        n = name.lower()
        if ref == R.RS.QUEST:
            return self.qvars[n]
        if n == 'getrandompercent' and self.pct is not None:
            return self.pct
        if n == 'isactionref':
            return 1
        if n == 'getactorvalue':
            return self.av[args[0].lower()]
        if n == 'hasperk':
            return 1 if self.perk else 0
        if n == 'getitemcount':
            return self.items.get(args[0].lower(), 0)
        if n in ('removeitem', 'additem'):
            k = args[0].lower()
            self.items[k] = self.items.get(k, 0) + (1 if n == 'additem' else -1) * int(float(args[1]))
            return 0
        if n == 'showslotmachinemenuparams':
            self.menus += 1
            return 0
        if n == 'getdistance':
            return self.near
        if n == 'addreputation':
            self.infamy += int(float(args[2]))
            return 0
        return S.Game.call(self, name, args, ref)


class Machine(S.Script):
    """The script with its blocks apart and `return`; `run(game, 'OnActivate' | 'GameMode')`."""

    def __init__(self, text):
        self.vars, self.refs, self.blocks, self.ints = {}, set(), {}, set()
        block = None
        for raw in text.splitlines():
            line = raw.split(';')[0].strip()
            if not line:
                continue
            low = line.lower()
            if low.startswith(('short ', 'long ', 'float ')):
                kind, n = line.split()
                self.vars[n.lower()] = 0
                if kind != 'float':
                    self.ints.add(n.lower())
            elif low.startswith('begin'):
                block = line.split()[1].lower()
                self.blocks[block] = []
            elif low == 'end':
                block = None
            elif block:
                self.blocks[block].append(line)

    def run(self, game, block):
        stack = []
        for line in self.blocks[block.lower()]:
            low = line.lower()
            word = low.split()[0]
            live = all(s[0] for s in stack)
            if word == 'if':
                ok = live and bool(self._value(self._tokens(line[2:]), game))
                stack.append([ok, ok])
            elif word == 'elseif':
                top, outer = stack[-1], all(s[0] for s in stack[:-1])
                ok = outer and not top[1] and bool(self._value(self._tokens(line[6:]), game))
                top[0], top[1] = ok, top[1] or ok
            elif word == 'else':
                top = stack[-1]
                top[0], top[1] = all(s[0] for s in stack[:-1]) and not top[1], True
            elif word == 'endif':
                stack.pop()
            elif not live:
                continue
            elif word == 'return':
                return
            elif word == 'set':
                m = re.match(r'set\s+([\w.]+)\s+to\s+(.*)$', line, re.I)
                v = self._value(self._tokens(m.group(2)), game)
                name = m.group(1).lower()
                if '.' in name:
                    game.qvars[name.split('.')[1]] = v
                else:
                    self.vars[name] = int(v) if name in self.ints else v
            else:
                self._value(self._tokens(line), game)


def use(g, m, button=None):
    """The player uses the machine; if a menu comes up, presses `button`; frames run until it's settled."""
    g.menu = None
    m.run(g, 'OnActivate')
    if g.menu and button is not None:
        g.button = button
        m.run(g, 'GameMode')
    m.run(g, 'GameMode')


text = R.script_source('Caps001')
shown = set(re.findall(r'ShowMessage (\w+)', text))
check('every message the script shows is made', shown <= set(R.MSGS), shown - set(R.MSGS))
check('the rig menu has Play, Rig, Leave', len(R.MSGS['FOLabArcadeRigMsg'][1]) == 3)
check('the fix menus have Fix, Leave', all(len(R.MSGS[e][1]) == 2 for e in ('FOLabArcadeFixMsg', 'FOLabArcadeFixFreeMsg')))

# a machine found broken, nobody able
g, m = Game(repair=20, parts=1), Machine(text)
g.pct = 0                                       # (broken when first used)
use(g, m)
check('a machine can start broken', m.vars['state'] == 1)
check('without Repair 55 it says so and nothing opens', g.menu == 'FOLabArcadeNoSkillMsg' and g.menus == 0, g.menu)
g.av['repair'] = 60
g.items[R.PART.lower()] = 0
use(g, m)
check('with the skill but no part it says what it takes', g.menu == 'FOLabArcadeNoPartMsg' and m.vars['state'] == 1, g.menu)
g.items[R.PART.lower()] = 2
use(g, m, button=1)
check('"Leave it" leaves it broken, the part kept', m.vars['state'] == 1 and g.items[R.PART.lower()] == 2)
use(g, m, button=0)
check('fixed with the part, one taken', m.vars['state'] == 2 and g.items[R.PART.lower()] == 1 and g.menu == 'FOLabArcadeFixedMsg')
use(g, m)
check('a fixed machine opens the slot menu', g.menus == 1)

g, m = Game(repair=55, parts=0, perk=True), Machine(text)
g.pct = 0
use(g, m)
check('with Tinkerer the fix needs no part', g.menu == 'FOLabArcadeFixFreeMsg')
use(g, m, button=0)
check('...and none is taken', m.vars['state'] == 2 and g.items[R.PART.lower()] == 0)

# a working machine, a fair session
g, m = Game(repair=84, money=100), Machine(text)
g.pct = 99
use(g, m)
check('a working machine plays at once below Repair 85', g.menus == 1 and g.menu is None and m.vars['playing'] == 1)
g.items['caps001'] = 140
m.run(g, 'GameMode')
check('a fair machine pays only what the menu paid', g.items['caps001'] == 140 and m.vars['playing'] == 0)

# rigging
g, m = Game(repair=90, money=100), Machine(text)
g.pct = 99
use(g, m, button=1)
check('at Repair 85 a working machine offers rigging', m.vars['state'] == 3 and g.menu == 'FOLabArcadeRiggedMsg')
use(g, m)
check('a rigged machine plays without asking', g.menus == 1 and m.vars['playing'] == 1)
g.items['caps001'] = 140
m.run(g, 'GameMode')
check('a session ahead pays half again', g.items['caps001'] == 160, g.items['caps001'])
check('the court missed it this time', m.vars['state'] == 3 and g.qvars['court'] == 0 and g.infamy == 0)
use(g, m)
g.items['caps001'] = 1000
m.run(g, 'GameMode')
check('the bonus is capped', g.items['caps001'] == 1000 + R.BONUS_MOST, g.items['caps001'] - 1000)
use(g, m)
g.items['caps001'] -= 30
m.run(g, 'GameMode')
check('a session behind pays nothing more', g.items['caps001'] == 1070 and m.vars['playing'] == 0)
use(g, m)
g.items['caps001'] += 20
g.pct = 0                                       # (the steward is watching)
m.run(g, 'GameMode')
check('noticed: court score down, infamy, the machine fair', g.qvars['court'] == -R.CAUGHT and g.infamy == 1 and
      m.vars['state'] == 2 and g.menu == 'FOLabArcadeCaughtMsg', (g.qvars, g.infamy, m.vars['state']))

g, m = Game(repair=90), Machine(text)
g.pct = 99
use(g, m, button=0)
check('"Play" from the rig menu opens the slot menu, not offered again', g.menus == 1 and m.vars['offered'] == 1)
use(g, m)
check('...and plays straight next time', g.menus == 2)
g, m = Game(repair=90), Machine(text)
g.pct = 99
use(g, m)
use(g, m, button=2)
check('"Leave it" opens nothing', g.menus == 0 and m.vars['state'] == 2)
g, m = Game(), Machine(text)
g.pct = 99
use(g, m)
g.near = 5000
g.items['caps001'] += 999
m.run(g, 'GameMode')
check('walking away ends the session unread', m.vars['playing'] == 0 and g.items['caps001'] == 1099)
