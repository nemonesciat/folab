"""Storms for Waikiki on a schedule (docs/waikiki-weather-plan.md, "The schedule the user chose", 21 Nov 2026).

One quest script runs the island's weather on the game's clock (GameDaysPassed, so waiting, sleeping and fast travel
move it too):
- fair weather most of the time: the region's own weathers, which `fair_ops` keeps to sunny and lightly cloudy ones;
- a squall every `SQUALL_GAP` days or so (sky building, a squall of 1 to 2 hours, clearing), never within
  `QUIET_AFTER` of a big storm's end or `QUIET_BEFORE` its first band;
- a big storm `BIG_GAP` days after the last one ended: squall bands, building, storm, the hurricane peak, storm, bands,
  clearing (`BIG_STEPS`).
Its steps are walked one a frame from where the last one ended, so a wait or sleep through a storm lands where the storm
would be by then (or past it: the next ones are counted from when it would have ended).

What the tests taught (tests 5 to 9 in nv-rs, 21 Nov 2026), kept here:
- each step's own work first, the sky change last; a storm sky not current `CHECK` days in is forced;
- at the start, any weather override a save carries is let go (ReleaseWeatherOverride);
- rain is particle models kept on the player and turned with the player's heading every frame, so it always crosses the
  screen (rain flying at the camera read as white streaks at you); the pictures are FOLab's own (`stormpictures/`).

Where: the sky and the rain on you only in the island's world (`WORLD`). In a hotel's small world (`hotelinside.VIEWS`)
the sky is the storm's and the rain is persistent emitters stood outside the glass (`view_spots`), switched with one
parent marker; indoors no rain. Anywhere else outdoors (the Mojave, the DLC worlds) the override is let go, and given
back on return.

`script_source(L)` is the script for a set of lengths; `run(L, ...)` runs that very text in a small interpreter of the
lines it uses (tests/test_stormsched.py) with frames, waits and sleeps, and `check` says whether the rules held. `ops`
is everything for a mod, one Undo; the models and pictures go in the mod's own files (`files`)."""
import math
import os
import random
import re
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
PICTURES = os.path.join(HERE, 'stormpictures')
STREAKS = 'textures\\folab\\weather\\folabstormstreaks.dds'
HAZE = 'textures\\folab\\weather\\folabstormhaze.dds'

WORLD = 'FOLabWaikiki'
VIEW_WORLDS = ('FOLabRoyalHawaiianWorld', 'FOLabMoanaWorld', 'FOLabKilaueaWorld')
OVERCAST = 'NVDLC02TheNarrowsWeather'           # (Honest Hearts' overcast: the building and clearing sky, seen in tests 6 to 9)

# sky codes: 0 fair (the override let go), 1 overcast, 2 squall, 3 storm, 4 the peak
# rain codes: 0 none, 1 the squall's sheets, 2 the storm's sheets and scud, 3 those and the fury
SKY = {1: OVERCAST, 2: 'FOLabSquallWeather', 3: 'FOLabStormWeather', 4: 'FOLabHurricaneWeather'}

# the big storm, step by step: (sky, rain, hours)
BIG_STEPS = [
    (2, 1, 1.0), (1, 0, 2.0), (2, 1, 1.0), (1, 0, 2.0),          # squall bands before (6 h)
    (2, 1, 2.0),                                                # building
    (3, 2, 6.0), (4, 3, 3.0), (3, 2, 6.0),                      # storm, the hurricane peak, storm
    (2, 1, 1.0), (1, 0, 2.0), (2, 1, 1.0), (1, 0, 2.0),          # squall bands after (6 h)
    (1, 0, 2.0),                                                # clearing
]
# a squall: (sky, rain, hours); the middle one's hours are SQUALL_MIN + SQUALL_SPAN * chance
SQUALL_STEPS = [(1, 0, 0.5), (2, 1, None), (1, 0, 0.5)]

REAL = {
    'squall_min': 1.0, 'squall_span': 1.0,          # (hours: a squall's rain 1 to 2 h)
    'squall_gap_min': 0.9, 'squall_gap_span': 0.9,  # (days from a squall's end to the next one's start)
    'big_gap_min': 3.0, 'big_gap_span': 3.0,        # (days from a big storm's end to the next one's first band)
    'quiet_after': 1.0,                             # (days after a big storm with no squall)
    'quiet_before': 0.5,                            # (days before a big storm's first band with no squall)
    'first_big_min': 1.5, 'first_big_span': 1.5,    # (days from the first start to the first big storm)
    'first_squall_min': 0.5, 'first_squall_span': 0.5,
    'check': 0.007,                                 # (days: ten game minutes, then a sky not yet current is forced)
}
# the look in the game: the big storm half an hour in, the first squall after it as usual
TEST = dict(REAL, first_big_min=0.02, first_big_span=0.0)

SQUALL_LONGEST = (0.5 + 0.5) / 24 + (REAL['squall_min'] + REAL['squall_span']) / 24


def _f(v):
    return ('%.5f' % v).rstrip('0').rstrip('.') or '0'


# what a big storm leaves and who hides from it (stormafter.py): the shelter flag is up from the building step to the last
# storm step; the wrack is laid when the storm's second half starts (the peak's rain hides it coming) and taken up
# WRACK_STAY days later, when you are not out on the island (or WRACK_LATE days after that whatever)
SHELTER_STEPS = (4, 5, 6, 7)
WRACK_STEP = 7
WRACK_STAY = (14 / 24.0 + 1.0, 1.0)     # (days from that step's start: the storm's rest, then 1 to 2 days)
WRACK_LATE = 1.0


def script_source(L=REAL, name='FOLabStormScript', world=WORLD, views=VIEW_WORLDS, view_parent='FOLabStormViewRain',
                  wrack=None, shelter=None):
    """The quest script, as text (CRLF lines). Only plain commands: nv-rs runs no extender. wrack: the editor ID of the
    persistent parent of the beach's wrack (switched on after a big storm); shelter: a global's editor ID, 1 while
    people should be indoors. Their variables are declared last, so a save made before them keeps its values."""
    h = lambda hours: _f(hours / 24.0)
    T = []
    a = T.append
    a('scn %s' % name)
    a('')
    a('; FOLab storms on the game clock (stormsched.py). Sky: 0 fair, 1 overcast, 2 squall, 3 storm, 4 the peak.')
    a('; Rain: 0 none, 1 squall, 2 storm, 3 the peak. Mode: 0 fair, 1 a squall, 2 a big storm.')
    for v in ('sheets', 'scud', 'fury', 'squall'):
        a('ref %s' % v)
    for v in ('started', 'mode', 'step', 'go', 'sky', 'rain', 'given', 'here', 'snap', 'lit', 'live'):
        a('short %s' % v)
    for v in ('now', 'next', 'check', 'bigdue', 'squalldue', 'len', 'ang'):
        a('float %s' % v)
    if wrack:
        a('short wrack')
        a('float wrackgone')
    a('')
    a('begin GameMode')
    a('')
    a('\tset now to GameDaysPassed')
    a('\tif started == 0')
    a('\t\tset started to 1')
    a('\t\tset sheets to player.PlaceAtMe FOLabStormSheets 1')
    a('\t\tset scud to player.PlaceAtMe FOLabStormScud 1')
    a('\t\tset fury to player.PlaceAtMe FOLabStormFury 1')
    a('\t\tset squall to player.PlaceAtMe FOLabSquallSheets 1')
    a('\t\tsheets.Disable')
    a('\t\tscud.Disable')
    a('\t\tfury.Disable')
    a('\t\tsquall.Disable')
    a('\t\tReleaseWeatherOverride')
    a('\t\tset bigdue to now + %s + %s * GetRandomPercent / 100' % (_f(L['first_big_min']), _f(L['first_big_span'])))
    a('\t\tset squalldue to now + %s + %s * GetRandomPercent / 100' % (_f(L['first_squall_min']), _f(L['first_squall_span'])))
    a('\tendif')
    a('')
    a('\t; fair: the next storm or squall due?')
    a('\tif mode == 0')
    a('\t\tif now >= bigdue')
    a('\t\t\tset mode to 2')
    a('\t\t\tset step to 0')
    a('\t\t\tset next to bigdue')
    a('\t\t\tset go to 1')
    a('\t\telseif now >= squalldue')
    a('\t\t\tif squalldue + %s > bigdue - %s' % (_f(SQUALL_LONGEST), _f(L['quiet_before'])))
    a('\t\t\t\tset squalldue to bigdue + 99')
    a('\t\t\telse')
    a('\t\t\t\tset mode to 1')
    a('\t\t\t\tset step to 0')
    a('\t\t\t\tset next to squalldue')
    a('\t\t\t\tset go to 1')
    a('\t\t\tendif')
    a('\t\tendif')
    a('\telseif now >= next')
    a('\t\tset step to step + 1')
    a('\t\tset go to 1')
    a('\tendif')
    a('')
    a('\t; a step begins where the last one ended (one a frame, so a long wait or sleep walks through them)')
    a('\tif go')
    a('\t\tset go to 0')
    a('\t\tset len to -1')
    a('\t\tif mode == 1')
    for k, (sky, rain, hours) in enumerate(SQUALL_STEPS):
        a('\t\t\t%s step == %d' % ('if' if k == 0 else 'elseif', k))
        a('\t\t\t\tset sky to %d' % sky)
        a('\t\t\t\tset rain to %d' % rain)
        if hours is None:
            a('\t\t\t\tset len to %s + %s * GetRandomPercent / 100' % (h(L['squall_min']), h(L['squall_span'])))
        else:
            a('\t\t\t\tset len to %s' % h(hours))
    a('\t\t\tendif')
    a('\t\telse')
    for k, (sky, rain, hours) in enumerate(BIG_STEPS):
        a('\t\t\t%s step == %d' % ('if' if k == 0 else 'elseif', k))
        a('\t\t\t\tset sky to %d' % sky)
        a('\t\t\t\tset rain to %d' % rain)
        a('\t\t\t\tset len to %s' % h(hours))
        if wrack and k == WRACK_STEP:
            a('\t\t\t\tset wrack to 1')
            a('\t\t\t\tset wrackgone to next + %s + %s * GetRandomPercent / 100' % (_f(WRACK_STAY[0]), _f(WRACK_STAY[1])))
            a('\t\t\t\t%s.Enable' % wrack)
    a('\t\t\tendif')
    a('\t\tendif')
    a('\t\tif len >= 0')
    a('\t\t\tset next to next + len')
    a('\t\telse')
    a('\t\t\tset sky to 0')
    a('\t\t\tset rain to 0')
    a('\t\t\tif mode == 2')
    a('\t\t\t\tset bigdue to next + %s + %s * GetRandomPercent / 100' % (_f(L['big_gap_min']), _f(L['big_gap_span'])))
    a('\t\t\t\tset squalldue to next + %s + %s * GetRandomPercent / 100' % (_f(L['quiet_after']), _f(L['squall_gap_span'])))
    a('\t\t\telse')
    a('\t\t\t\tset squalldue to next + %s + %s * GetRandomPercent / 100' % (_f(L['squall_gap_min']), _f(L['squall_gap_span'])))
    a('\t\t\tendif')
    a('\t\t\tset mode to 0')
    a('\t\tendif')
    a('\tendif')
    a('')
    a('\t; a step already over (walking through after a wait or sleep) shows nothing: only where the walk ends does')
    a('\tset live to 1')
    a('\tif mode > 0 && now >= next')
    a('\t\tset live to 0')
    a('\tendif')
    if shelter:
        a('\t; people indoors from the building step to the storm\'s end')
        a('\tif live')
        a('\t\tif mode == 2 && step >= %d && step <= %d' % (SHELTER_STEPS[0], SHELTER_STEPS[-1]))
        a('\t\t\tset %s to 1' % shelter)
        a('\t\telse')
        a('\t\t\tset %s to 0' % shelter)
        a('\t\tendif')
        a('\tendif')
    a('')
    a('\t; where you are: 1 the island, 2 a hotel\'s small world, 3 indoors, 0 another world')
    a('\tset here to 0')
    a('\tif player.GetInWorldspace %s' % world)
    a('\t\tset here to 1')
    for k, v in enumerate(views):
        a('\telseif player.GetInWorldspace %s' % v)
        a('\t\tset here to 2')
    a('\telseif player.IsInInterior')
    a('\t\tset here to 3')
    a('\tendif')
    a('')
    a('\t; the sky: given once a step in the island or a hotel; let go in another world, given at once on return')
    a('\tif live == 0')
    a('\telseif here == 0')
    a('\t\tif given > 0')
    a('\t\t\tReleaseWeatherOverride')
    a('\t\t\tset given to 0')
    a('\t\t\tset snap to 1')
    a('\t\tendif')
    a('\telseif here < 3')
    a('\t\tif given != sky || snap')
    a('\t\t\tset given to sky')
    a('\t\t\tset check to 0')
    a('\t\t\tif sky == 0')
    a('\t\t\t\tReleaseWeatherOverride')
    a('\t\t\telse')
    a('\t\t\t\tset check to now + %s' % _f(L['check']))
    for k in (1, 2, 3, 4):
        a('\t\t\t\t%s sky == %d' % ('if' if k == 1 else 'elseif', k))
        a('\t\t\t\t\tif snap')
        a('\t\t\t\t\t\tForceWeather %s 1' % SKY[k])
        a('\t\t\t\t\telse')
        a('\t\t\t\t\t\tSetWeather %s 1' % SKY[k])
        a('\t\t\t\t\tendif')
    a('\t\t\t\tendif')
    a('\t\t\tendif')
    a('\t\t\tset snap to 0')
    a('\t\tendif')
    a('\tendif')
    a('\tif check > 0')
    a('\t\tif now >= check')
    a('\t\t\tset check to 0')
    for k in (1, 2, 3, 4):
        a('\t\t\t%s sky == %d' % ('if' if k == 1 else 'elseif', k))
        a('\t\t\t\tif GetIsCurrentWeather %s == 0' % SKY[k])
        a('\t\t\t\t\tForceWeather %s 1' % SKY[k])
        a('\t\t\t\tendif')
    a('\t\t\tendif')
    a('\t\tendif')
    a('\tendif')
    a('')
    a('\t; the rain on you, out in the island only, turned with you so it crosses the view')
    a('\tset ang to player.GetAngle z')
    for ref, test in (('squall', 'rain == 1'), ('sheets', 'rain >= 2'), ('scud', 'rain >= 2'), ('fury', 'rain == 3')):
        a('\tif live == 0')
        a('\telseif here == 1 && %s' % test)
        a('\t\tif %s.GetDisabled' % ref)
        a('\t\t\t%s.Enable' % ref)
        a('\t\tendif')
        a('\t\t%s.MoveTo player' % ref)
        a('\t\t%s.SetAngle z ang' % ref)
        a('\telseif %s.GetDisabled == 0' % ref)
        a('\t\t%s.Disable' % ref)
        a('\tendif')
    if view_parent:
        a('')
        a('\t; the rain outside the hotels\' glass: one parent for every emitter stood there')
        a('\tif live == 0')
        a('\telseif rain > 0 && lit == 0')
        a('\t\t%s.Enable' % view_parent)
        a('\t\tset lit to 1')
        a('\telseif rain == 0 && lit')
        a('\t\t%s.Disable' % view_parent)
        a('\t\tset lit to 0')
        a('\tendif')
    if wrack:
        a('')
        a('\t; the wrack taken up a day or two after the storm, when you are not out on the island to see it go')
        a('\tif wrack == 1 && now >= wrackgone')
        a('\t\tif here != 1 || now >= wrackgone + %s' % _f(WRACK_LATE))
        a('\t\t\t%s.Disable' % wrack)
        a('\t\t\tset wrack to 0')
        a('\t\tendif')
        a('\tendif')
    a('')
    a('end')
    a('')
    return '\r\n'.join(T)


# ---------- the script, run: a small interpreter of the lines script_source writes ----------

class Game:
    """What the script sees of the game: the clock, where the player is, the sky, refs that can be on or off. `log` gets
    (time, what) for every sky command and every rain switched."""

    def __init__(self, seed=1, here='island'):
        self.rnd = random.Random(seed)
        self.days = 10.0
        self.where = here               # 'island', 'view', 'inside', 'mojave'
        self.override = None            # (the weather the script holds, or None)
        self.current = 'fair'
        self.on = {}
        self.log = []
        self.flags = []                 # (day, the shelter flag, the wrack on) once a game minute

    def call(self, name, args, ref):
        n = name.lower()
        if n == 'gamedayspassed':
            return self.days
        if n == 'getrandompercent':
            return self.rnd.randrange(100)
        if n == 'placeatme':
            k = args[0].lower()
            self.on[k] = True
            return k
        if n == 'getinworldspace':
            w = args[0]
            return 1 if (w == WORLD and self.where == 'island') or (w in VIEW_WORLDS and self.where == 'view') else 0
        if n == 'isininterior':
            return 1 if self.where == 'inside' else 0
        if n == 'getangle':
            return 0.0
        if n in ('releaseweatheroverride', 'setweather', 'forceweather'):
            w = args[0] if args else None
            self.override = w if n != 'releaseweatheroverride' else None
            self.current = w or 'fair'          # (taken as changed at once: the check forces it in the game if not)
            self.log.append((self.days, n, w))
            return 0
        if n == 'getiscurrentweather':
            return 1 if self.current == args[0] else 0
        if n in ('enable', 'disable'):
            was = self.on.get(ref, False)
            self.on[ref] = n == 'enable'
            if was != self.on[ref]:
                self.log.append((self.days, n, ref))
            return 0
        if n == 'getdisabled':
            return 0 if self.on.get(ref, False) else 1
        if n in ('moveto', 'setangle'):
            return 0
        raise KeyError('the runner knows no %s' % name)


_ARGS = {'placeatme': 2, 'getinworldspace': 1, 'setweather': 2, 'forceweather': 2, 'getiscurrentweather': 1, 'getangle': 1,
         'moveto': 1, 'setangle': 2}
_TOKEN = re.compile(r'\s*(?:(\d+\.\d*|\.\d+|\d+)|([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?)|(&&|\|\||==|!=|>=|<=|[-+*/<>()]))')


class Script:
    """The script's text, parsed once into lines; `frame(game)` runs its GameMode block once."""

    def __init__(self, text):
        self.vars = {}
        self.refs = set()
        self.lines = []
        body = False
        for raw in text.splitlines():
            line = raw.split(';')[0].strip()
            if not line:
                continue
            low = line.lower()
            if low.startswith(('ref ', 'short ', 'float ')):
                kind, n = line.split()
                self.vars[n.lower()] = 0
                if kind == 'ref':
                    self.refs.add(n.lower())
            elif low.startswith('begin'):
                body = True
            elif low == 'end':
                body = False
            elif body:
                self.lines.append(line)

    def _tokens(self, s):
        out, i = [], 0
        while i < len(s):
            m = _TOKEN.match(s, i)
            if not m or m.end() == i:
                if s[i:].strip():
                    raise ValueError('cannot read %r' % s[i:])
                break
            i = m.end()
            out.append(m.group(0).strip())
        return out

    def _value(self, toks, game):
        """Reads one expression off toks (a list, used up as it goes)."""
        def atom():
            t = toks.pop(0)
            if t == '(':
                v = orr()
                toks.pop(0)
                return v
            if t == '-':
                return -atom()
            if re.match(r'[\d.]', t):
                return float(t)
            ref, _, fn = t.rpartition('.')
            if not ref and t.lower() in self.vars:
                return self.vars[t.lower()]
            n = _ARGS.get(fn.lower(), 0)
            args = []
            while n and toks and re.match(r'[A-Za-z_\d]', toks[0]):
                a = toks.pop(0)
                args.append(self.vars.get(a.lower(), a) if a.lower() in self.vars and a.lower() not in self.refs else a)
                n -= 1
            return game.call(fn, args, ref.lower() if ref.lower() in self.refs else ref)

        def mul():
            v = atom()
            while toks and toks[0] in ('*', '/'):
                op = toks.pop(0)
                w = atom()
                v = v * w if op == '*' else v / w
            return v

        def add():
            v = mul()
            while toks and toks[0] in ('+', '-'):
                op = toks.pop(0)
                w = mul()
                v = v + w if op == '+' else v - w
            return v

        def cmp():
            v = add()
            while toks and toks[0] in ('==', '!=', '>=', '<=', '>', '<'):
                op = toks.pop(0)
                w = add()
                v = 1 if {'==': v == w, '!=': v != w, '>=': v >= w, '<=': v <= w, '>': v > w, '<': v < w}[op] else 0
            return v

        def andd():
            v = cmp()
            while toks and toks[0] == '&&':
                toks.pop(0)
                w = cmp()
                v = 1 if (v and w) else 0
            return v

        def orr():
            v = andd()
            while toks and toks[0] == '||':
                toks.pop(0)
                w = andd()
                v = 1 if (v or w) else 0
            return v
        return orr()

    def frame(self, game):
        stack = []          # (taking this branch now, a branch already taken)
        for line in self.lines:
            low = line.lower()
            word = low.split()[0]
            live = all(s[0] for s in stack)
            if word == 'if':
                ok = live and bool(self._value(self._tokens(line[2:]), game))
                stack.append([ok, ok])
            elif word == 'elseif':
                top = stack[-1]
                outer = all(s[0] for s in stack[:-1])
                ok = outer and not top[1] and bool(self._value(self._tokens(line[6:]), game))
                top[0] = ok
                top[1] = top[1] or ok
            elif word == 'else':
                top = stack[-1]
                outer = all(s[0] for s in stack[:-1])
                top[0] = outer and not top[1]
                top[1] = True
            elif word == 'endif':
                stack.pop()
            elif not live:
                continue
            elif word == 'set':
                m = re.match(r'set\s+(\w+)\s+to\s+(.*)$', line, re.I)
                self.vars[m.group(1).lower()] = self._value(self._tokens(m.group(2)), game)
            else:
                self._value(self._tokens(line), game)
        if stack:
            raise ValueError('an if without its endif')


def run(L=REAL, days=30.0, timescale=30.0, fps=4.0, seed=1, events=(), text=None):
    """The script run over `days` of game time. events: (at game day, what): ('wait', hours) or ('sleep', hours) jump
    the clock in one go (a single frame, as the game does after the wait menu), ('go', 'mojave'|'island'|'view'|'inside')
    moves the player. Returns (game, samples): samples (day, mode, sky, rain, where) once a game minute."""
    s = Script(text or script_source(L))
    g = Game(seed)
    start = g.days
    step = timescale / 86400.0 / fps
    todo = sorted((start + at, what) for at, what in events)
    samples, last = [], -1
    while g.days < start + days:
        while todo and g.days >= todo[0][0]:
            _at, (kind, v) = todo.pop(0)
            if kind in ('wait', 'sleep'):
                g.days += v / 24.0
                g.log.append((g.days, kind, v))
            else:
                g.where = v
        s.frame(g)
        minute = int(g.days * 1440)
        if minute != last:
            last = minute
            samples.append((g.days, int(s.vars['mode']), int(s.vars['sky']), int(s.vars['rain']), g.where))
            g.flags.append((g.days, int(s.vars.get('folabstormshelter', 0)), 1 if g.on.get('FOLabStormWrack') else 0))
        g.days += step
    return g, s, samples


def spells(samples):
    """[(start, end, mode)]: each squall and big storm, by its first and last minute not fair."""
    out, cur = [], None
    for day, mode, sky, _rain, _w in samples:
        busy = mode if sky or mode else 0
        if cur and (busy != cur[2]):
            out.append(tuple(cur))
            cur = None
        if busy and not cur:
            cur = [day, day, busy]
        if cur:
            cur[1] = day
    if cur:
        out.append(tuple(cur))
    return out


def check(samples, L=REAL, waited=()):
    """What broke the rules, as sentences (none: they held). waited: (from, to) spans of a wait or sleep, where a storm
    may end unseen."""
    bad = []
    sp = spells(samples)
    big = [s for s in sp if s[2] == 2]
    sq = [s for s in sp if s[2] == 1]
    skipped = lambda a, b: any(a - 0.01 <= w0 and w1 <= b + 0.01 or w0 - 0.01 <= a <= w1 + 0.01 or w0 - 0.01 <= b <= w1 + 0.01 for w0, w1 in waited)
    for a, b in zip(big, big[1:]):
        gap = b[0] - a[1]
        if not skipped(a[1], b[0]) and not (L['big_gap_min'] - 0.02 <= gap <= L['big_gap_min'] + L['big_gap_span'] + 0.02):
            bad.append('big storms %.2f days apart (from %.2f)' % (gap, a[1]))
    for s in big:
        long_ = (s[1] - s[0]) * 24
        if not skipped(s[0], s[1]) and abs(long_ - sum(h for _s, _r, h in BIG_STEPS)) > 0.2 and s is not big[-1]:
            bad.append('a big storm of %.1f hours (from %.2f)' % (long_, s[0]))
    for s in sq:
        for b in big:
            if skipped(b[0], s[0]):
                continue
            if b[1] <= s[0] < b[1] + L['quiet_after'] - 0.01:
                bad.append('a squall %.2f days after a big storm' % (s[0] - b[1]))
            if b[0] - L['quiet_before'] + 0.01 < s[1] <= b[0]:
                bad.append('a squall %.2f days before a big storm' % (b[0] - s[1]))
    every = sorted(sp)
    for a, b in zip(every, every[1:]):
        if (a[2] == 1 or b[2] == 1) and b[0] - a[1] < 0.5 - 0.01 and not skipped(a[1], b[0]):
            bad.append('only %.1f sunny hours between %.2f and %.2f' % ((b[0] - a[1]) * 24, a[1], b[0]))
    return bad


def fair_share(samples):
    return sum(1 for s in samples if s[2] == 0) / max(1, len(samples))


# ---------- the models ----------

LOOKS = {
    # the storm's driven sheets: three bands side by side, thrown along +x from upwind
    'sheets': ('nvdlc02/sky/nvdlc02rain2.nif', 'folab\\weather\\folabstormsheets.nif', STREAKS,
               dict(speed=3800, speed_var=700, decl=1.2, size=80, size_var=30, life=1.15, life_var=0.2, rate=420, gravity=700,
                    upwind=2600, across=(-1800, 0, 1800), width=1900, height=1300, z=600)),
    # torn scud low down
    'scud': ('nvdlc02/sky/nvdlc02rain.nif', 'folab\\weather\\folabstormscud.nif', HAZE,
             dict(speed=2900, speed_var=600, decl=1.52, size=230, size_var=80, life=1.7, life_var=0.3, rate=110, gravity=40,
                  upwind=2600, across=(0,), width=5200, height=900, z=300)),
    # the peak's extra: heavier, faster, flatter sheets nearer the ground
    'fury': ('nvdlc02/sky/nvdlc02rain2.nif', 'folab\\weather\\folabstormfury.nif', STREAKS,
             dict(speed=5000, speed_var=900, decl=1.32, size=80 + 15, size_var=30, life=0.9, life_var=0.2, rate=700, gravity=700,
                  upwind=2800, across=(-1800, 0, 1800), width=1900, height=1000, z=350)),
    # a squall: the storm's sheets at half as many, a little slower
    'squall': ('nvdlc02/sky/nvdlc02rain2.nif', 'folab\\weather\\folabsquallsheets.nif', STREAKS,
               dict(speed=3200, speed_var=600, decl=1.15, size=75, size_var=25, life=1.3, life_var=0.2, rate=210, gravity=700,
                    upwind=2600, across=(-1800, 0, 1800), width=1900, height=1300, z=600)),
    # outside a hotel's glass: one band along the wall, tall enough for two floors
    'window': ('nvdlc02/sky/nvdlc02rain2.nif', 'folab\\weather\\folabstormwindow.nif', STREAKS,
               dict(speed=3800, speed_var=700, decl=1.2, size=80, size_var=30, life=1.15, life_var=0.2, rate=380, gravity=700,
                    upwind=2600, across=(0,), width=900, height=1500, z=800)),
}
ACTIVATORS = {'sheets': 'FOLabStormSheets', 'scud': 'FOLabStormScud', 'fury': 'FOLabStormFury', 'squall': 'FOLabSquallSheets',
              'window': 'FOLabStormWindowRain'}
RAIN_FROM = {'nvdlc02/sky/nvdlc02rain2.nif': 'NVDLC02Rain2', 'nvdlc02/sky/nvdlc02rain.nif': 'NVDLC02Rain'}


def blow(gd, src, look, tex):
    """A copy of one of Honest Hearts' rain models whose particles are thrown along +x from upwind (its NiPSysBoxEmitter
    speeds, sizes, lives and box, each emitter's node moved, gravity, birth rate), with its pictures swapped for `tex`."""
    import nif
    import nifwrite
    n = nif.Nif(gd.read_file('meshes/' + src))
    data = bytearray(n.data)
    nodes = []
    for i, t in enumerate(n.types):
        if t != 'NiPSysBoxEmitter':
            continue
        o, size = n.offsets[i], n.sizes[i]
        struct.pack_into('<6f', data, o + 13, look['speed'], look['speed_var'], look['decl'], 0.08, 0.0, 0.15)
        struct.pack_into('<4f', data, o + 13 + 40, look['size'], look['size_var'], look['life'], look['life_var'])
        nodes.append(struct.unpack_from('<i', data, o + size - 16)[0])
        struct.pack_into('<3f', data, o + size - 12, 300.0, look['width'], look['height'])
    for k, node in enumerate(nodes):
        b = n.block(node)
        p = n.offsets[node] + 4 + 4 + 4 * len(b['extra']) + 4 + 4
        y = look['across'][k % len(look['across'])]
        struct.pack_into('<3f9f', data, p, -look['upwind'], y, look['z'], 1, 0, 0, 0, 1, 0, 0, 0, 1)
    for i, t in enumerate(n.types):
        o = n.offsets[i]
        if t == 'NiPSysGravityModifier':
            struct.pack_into('<f', data, o + 33, look['gravity'])
        if t == 'NiPSysEmitterCtlr':
            interp = struct.unpack_from('<i', data, o + n.sizes[i] - 12)[0]
            if n.types[interp] == 'NiFloatInterpolator':
                struct.pack_into('<f', data, n.offsets[interp], look['rate'])
    out = bytes(data)
    nif.Nif(out)
    old = {t['path']: tex for t in nifwrite.textures_in(out)}
    out = nifwrite.retexture(out, old)
    if nifwrite.prove(out, old):
        raise ValueError('the rain model %s did not take its new pictures' % src)
    return out


def files(gd):
    """{path under Data: bytes}: the rain models and their two pictures."""
    out = {}
    for _k, (src, dst, tex, look) in LOOKS.items():
        out['meshes\\' + dst] = blow(gd, src, look, tex)
    for rel in (STREAKS, HAZE):
        with open(os.path.join(PICTURES, os.path.basename(rel)), 'rb') as fh:
            out[rel] = fh.read()
    return out


# ---------- the weathers ----------

GREY_GREEN = (104, 122, 106)
WEATHERS = {
    # edid: (fog day near, far, night near, far), darkness, wind, cloud speed, thunder (lower: more often), extra sounds
    'FOLabSquallWeather': ((200.0, 12000.0, 100.0, 9000.0), 0.9, 190, 110, 200, ('NVDLC04EmtVistaWindLP3', 'AMBNVDLC02RainAmb')),
    'FOLabStormWeather': ((60.0, 6500.0, 40.0, 4500.0), 0.8, 255, 160, 60,
                          ('NVDLC04EmtVistaWindLP4', 'NVDLC04EmtVistaWindLP3', 'AMBNVDLC02RainAmb')),
    'FOLabHurricaneWeather': ((20.0, 3200.0, 10.0, 2400.0), 0.55, 255, 160, 18,
                              ('NVDLC04EmtVistaWindLP4', 'NVDLC04EmtVistaWindLP3', 'AMBNVDLC02RainAmb', 'AMBHiddenValleySandstormLoop',
                               'NVDLC04EmtVistaWindLP2')),
}
WEATHER_FROM = 'NVDLC02ZVRainWeather'


def _game_form(gd, tag, edid):
    for f, (_i, r) in gd.forms.items():
        if r.tag == tag and gd.edid(f) == edid:
            return f
    raise ValueError('the game has no %s %s' % (tag, edid))


def _fields(sub):
    return [f for f in sub['fields'] if 'name' in f]


def weather_record(gd, edid):
    """A copy of Honest Hearts' Zion rain weather made into one of ours: wind, clouds racing, fog closer, the sky's lower
    parts grey-green and darker, thunder, our wind loops added to its sound."""
    import json
    import recordio
    fog, dark, wind, clouds, thunder, sounds = WEATHERS[edid]
    rec = json.loads(json.dumps(recordio.load(gd, _game_form(gd, 'WTHR', WEATHER_FROM))))
    rec['src'] = ''
    tl = sum(GREY_GREEN) / 3
    for s in rec['subs']:
        t = s['tag']
        if t == 'EDID':
            s['value'] = edid
        elif t == 'DATA':
            f = _fields(s)
            f[0]['value'] = wind
            f[1]['value'] = f[2]['value'] = clouds
            f[10]['value'] = thunder
        elif t == 'ONAM':
            for f, v in zip(_fields(s), (127, 0, 0, 127)):
                f['value'] = v
        elif t == 'FNAM':
            for f, v in zip(_fields(s), fog):
                f['value'] = v
        elif t == 'NAM0':
            f = _fields(s)
            if len(f) == 180:                    # (10 parts x 6 times x red, green, blue)
                for part in (1, 7, 8):           # (fog, lower sky, horizon)
                    for time in range(6):
                        o = (part * 6 + time) * 3
                        lum = sum(f[o + c]['value'] for c in range(3)) / 3 or 1
                        for c in range(3):
                            f[o + c]['value'] = min(255, int(GREY_GREEN[c] * lum / tl * dark))
                for part in (0, 3, 4, 9):        # (upper sky, ambient, sunlight, upper clouds: darker at the peak)
                    for time in range(6):
                        o = (part * 6 + time) * 3
                        for c in range(3):
                            f[o + c]['value'] = int(f[o + c]['value'] * min(1.0, dark / 0.8))
    snd = [s for s in rec['subs'] if s['tag'] == 'SNAM']
    at = rec['subs'].index(snd[-1]) + 1 if snd else len(rec['subs'])
    have = {gd.edid(f): f for f, (_i, r) in gd.forms.items() if r.tag == 'SOUN' and gd.edid(f) in sounds}
    for name in sounds:
        if name in have:
            add = json.loads(json.dumps(snd[0]))
            fl = _fields(add)
            fl[0]['value'] = gd.key(have[name])
            fl[1]['value'] = 0
            rec['subs'].insert(at, add)
            at += 1
    return rec


def activator_record(gd, kind):
    import json
    import recordio
    src, dst, _tex, _look = LOOKS[kind]
    rec = json.loads(json.dumps(recordio.load(gd, _game_form(gd, 'ACTI', RAIN_FROM[src]))))
    rec['src'] = ''
    rec['subs'] = [s for s in rec['subs'] if s['tag'] != 'MODT']
    for s in rec['subs']:
        if s['tag'] == 'EDID':
            s['value'] = ACTIVATORS[kind]
        elif s['tag'] == 'MODL':
            s['value'] = dst
    return rec


# ---------- the hotels' glass ----------

MARGIN = 450            # (from a wall to the near edge of its band of rain)
BAND = 4000             # (how much wall one emitter covers: its rain runs from 2,600 upwind to ~1,800 past it)


def view_spots(gd, pr, hotel, parent):
    """[(cell key in the hotel's small world, [x y z rx ry rz])]: emitters of window rain round the hotel's open piece,
    each turned so its rain runs along the wall it stands off, `MARGIN` clear of it; a ring at the ground floor and
    one at the lookout or deck. Read from where the mod stands the open piece in the small world."""
    import hotelinside
    import library
    import modelsets
    v = hotelinside.VIEWS[hotel]
    child = _world(gd, v['world'])
    cells = {gd.key(c): xy for xy, c in gd.grid(child).items()}
    modelsets._all_sets()
    open_ = modelsets.record_of(pr, v['open'])
    spot = [r for ck, c in pr.cells.items() if ck in cells for r in c['refs'].values() if r.get('base') == open_ and not r.get('removed')]
    if len(spot) != 1:
        raise ValueError('%s: its open piece stands %d times in its small world' % (v['name'], len(spot)))
    x, y, z, _rx, _ry, rz = spot[0]['p']
    sz = float(spot[0].get('s') or 1.0)
    rec = pr.records[open_]
    import recordio
    model = recordio.field(rec, 'MODL')
    b = library.bounds_of(gd.read_file('meshes\\' + model))
    x0, y0, z0, x1, y1, z1 = [c * sz for c in b]
    grid = gd.grid(child)
    out = []

    def put(lx, ly, lz, face):
        import landmarks
        wx, wy = landmarks._turn(lx, ly, rz)
        px, py = x + wx, y + wy
        c = grid.get((int(px // 4096), int(py // 4096)))
        if c is None:
            return
        out.append((gd.key(c), [round(px, 1), round(py, 1), round(z + lz, 1), 0.0, 0.0, round((rz + face) % math.tau, 4)]))

    def ring(lx0, ly0, lx1, ly1, lz):
        half = LOOKS['window'][3]['width'] / 2
        # each side: the band runs along the side (+x of the emitter along it, the wind going round the building)
        for (ax, ay), (bx, by), (nx, ny) in (((lx0, ly0), (lx1, ly0), (0, -1)), ((lx1, ly0), (lx1, ly1), (1, 0)),
                                             ((lx1, ly1), (lx0, ly1), (0, 1)), ((lx0, ly1), (lx0, ly0), (-1, 0))):
            long_ = math.hypot(bx - ax, by - ay)
            n = max(1, int(math.ceil(long_ / BAND)))
            dx, dy = (bx - ax) / long_, (by - ay) / long_
            face = math.atan2(-dy, dx)                       # (the emitter's +x along the side: a turn rz takes +x to (cos, -sin))
            for k in range(n):
                t = (k + 0.5) / n * long_ + 1000            # (the band starts 2,600 upwind: stood a little downwind of each share)
                put(ax + dx * min(t, long_) + nx * (MARGIN + half), ay + dy * min(t, long_) + ny * (MARGIN + half), lz, face)
    ring(x0, y0, x1, y1, z0 - 100)
    floor_top = v.get('floor_top', hotelinside.FLOOR_TOP) * sz
    high = [d for d in v['doors'] if d[0] == 'lookout']
    if high:
        _n, _e, lx, ly, lz, _f = high[0]
        lx, ly, lz = lx * sz, ly * sz, floor_top + lz * sz
        r = 900 * sz if hotel != 'kilauea' else 2200 * sz
        ring(lx - r, ly - r, lx + r, ly + r, lz - 400)
    return out


def _world(gd, edid):
    for f, (_i, r) in gd.forms.items():
        if r.tag == 'WRLD' and gd.edid(f) == edid:
            return f
    raise ValueError('no world %s' % edid)


# ---------- the region: fair weather only ----------

def fair_ops(gd, pr, world=WORLD):
    """Ops keeping the mod's own regions over the island to clear and lightly cloudy weathers (grey skies come from the
    schedule now): every weather in a region's list (RDWT) whose kind isn't pleasant (DATA's last flags: 1 pleasant,
    2 cloudy, 4 rainy, 8 snow) is taken out. Returns (ops, [(region, weathers out)])."""
    import json
    import recordio
    ops, rep = [], []
    for k, r in pr.records.items():
        if r.get('type') != 'REGN':
            continue
        rec = json.loads(json.dumps(r))
        out = []
        for s in rec['subs']:
            if s['tag'] != 'RDWT':
                continue
            keep = []
            rows = s.get('rows') or s.get('fields') or []
            for row in _rdwt_rows(s):
                w = row['weather']
                if not _pleasant(gd, pr, w):
                    out.append(w)
                else:
                    keep.append(row)
            if not keep:                    # (every weather rainy: the list is left as it is)
                out = []
                continue
            _set_rdwt(s, keep)
        if out:
            ops.append({'op': 'record', 'key': k, 'record': rec})
            rep.append((recordio.field(r, 'EDID'), out))
    return ops, rep


def _rdwt_rows(sub):
    """[{'weather', 'chance', 'global'}] from a region's RDWT as recordio keeps it (raw bytes or rows)."""
    if sub.get('kind') == 'raw':
        raise ValueError('a raw RDWT: read it with schema first')
    rows, cur = [], {}
    for f in sub.get('fields', []):
        n = (f.get('name') or '').lower()
        if 'weather' in n:
            cur = {'weather': f['value']}
            rows.append(cur)
        elif 'chance' in n:
            cur['chance'] = f['value']
        elif 'global' in n:
            cur['global'] = f['value']
    return rows


def _set_rdwt(sub, rows):
    proto = {}
    for f in sub.get('fields', []):
        n = (f.get('name') or '').lower()
        for word in ('weather', 'chance', 'global'):
            if word in n and word not in proto:
                proto[word] = dict(f)
    fields = []
    for k, row in enumerate(rows):
        for word in ('weather', 'chance', 'global'):
            if word in proto:
                f = dict(proto[word], value=row.get(word, proto[word]['value']))
                fields.append(f)
    sub['fields'] = fields


def _pleasant(gd, pr, key):
    """Not rainy or snowy. (Cloudy stays: Zion Valley's sunny day weather is filed as cloudy, kind 2.)"""
    import recordio
    rec = pr.records.get(key) if key.startswith('+') else recordio.load(gd, gd.from_key(key))
    for s in rec['subs']:
        if s['tag'] == 'DATA':
            kind = next((f['value'] for f in _fields(s) if (f.get('name') or '').lower() == 'kind'), 0)
            return not kind & 12
    return False


# ---------- everything for a mod ----------

def ops(gd, pr, views=True, L=REAL):
    """(ops, report): the weathers, rain activators, script and quest, and (views) the window rain round each hotel in
    its small world under one parent marker; one Undo. Nothing is changed here. The models and pictures are `files(gd)`,
    to go in the mod's own files."""
    import api_quests as aq
    import api_scripts
    import newgame
    import questrec as qr
    import recordio
    if any(r.get('type') == 'QUST' and recordio.field(r, 'EDID') == 'FOLabStormQuest' for r in pr.records.values()):
        raise ValueError('the mod already has its storms (FOLabStormQuest)')
    spots = []
    if views:
        import hotelinside
        world = _world(gd, WORLD)
        for hotel, v in hotelinside.VIEWS.items():
            try:
                _world(gd, v['world'])
            except ValueError:
                continue
            spots += view_spots(gd, pr, hotel, world)
    parent_name = 'FOLabStormViewRain' if spots else None
    # the keys every record_new and add below will get, in this order
    order = list(WEATHERS) + list(ACTIVATORS) + (['parent'] + ['window%d' % k for k in range(len(spots))] if spots else []) + ['script', 'quest']
    keys = dict(zip(order, aq._reserve(pr, len(order))))
    out, extra = [], {}
    for edid in WEATHERS:
        rec = weather_record(gd, edid)
        extra[keys[edid]] = rec
        out.append({'op': 'record_new', 'record': rec})
    for kind in ACTIVATORS:
        rec = activator_record(gd, kind)
        extra[keys[kind]] = rec
        out.append({'op': 'record_new', 'record': rec})
    if parent_name:
        marker = gd.key(_game_form(gd, 'STAT', 'XMarker'))
        extra[keys['parent']] = {'type': 'REFR', 'flags': newgame.PERSISTENT,
                                 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': parent_name}]}
        ck0, p0 = spots[0]
        out.append({'op': 'add', 'cell': ck0, 'base': marker, 'p': [p0[0], p0[1], p0[2] - 200, 0.0, 0.0, 0.0], 's': 1.0,
                    'extra': {'persistent': True, 'edid': parent_name, 'props': {'disabled': True}}})
        for ck, p in spots:
            out.append({'op': 'add', 'cell': ck, 'base': keys['window'], 'p': p, 's': 1.0,
                        'extra': {'persistent': True, 'props': {'parent': {'ref': keys['parent'], 'opposite': False, 'popin': False}}}})
    quest = qr.quest_record({'edid': 'FOLabStormQuest', 'script': keys['script'], 'name': '', 'flags': {'start_enabled': True},
                             'priority': 0, 'delay': 0.1, 'stages': [], 'objectives': []})
    extra[keys['quest']] = quest
    sc = api_scripts.scripts()
    text = script_source(L, view_parent=parent_name)
    c = sc.compile(text, keys['script'], 'quest', extra)
    if not hasattr(c, 'subrecords'):
        raise ValueError('the storm script does not compile: %s' % (c,))
    out.append({'op': 'record_new', 'record': sc._record_of(c, 'FOLabStormScript')})
    out.append({'op': 'record_new', 'record': quest})
    return out, {'keys': keys, 'window_rain': len(spots), 'script_bytes': len(c.data)}
