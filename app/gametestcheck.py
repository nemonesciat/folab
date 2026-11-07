"""What the game runs in a game test: the checker, as text, and the small plugin it needs.

Nothing here has been run in the game yet: docs/game-test-first-run.md lists what a first run must prove. What has been
read from the user's own files, by `py -3 app/gametestcheck.py` (the commands' tables in the DLLs):

- JIP LN's script runner reads Data\\NVSE\\plugins\\scripts\\*.txt. A name's first two letters and a '_' pick when it runs:
  gr at the main menu (at once), others kept for events (gl, gn, ln, gs, gx, xm).
- GetRayCastPos takes three GLOBALS for its answer, and needs a calling ref: hence a plugin with globals in it.
- WriteStringToFile (path, mode, format, up to 20 numbers) goes by the game's folder. Mode not 0 adds to a file that's there,
  a line break first; a new file gets its folders made. ReadStringFromFile (path, first line from 1, how many) reads only
  the first 16 KB of a file: hence the plan in chunks.
- xNVSE's CompileScript looks in Data\\NVSE\\user_defined_functions.
- Neither has a clock in milliseconds, so waits count ticks of the main-loop callback: frames, which is what physics goes by.

How it goes: gr_ writes the first line and starts the tick (a function called every few frames by the game's main loop).
The tick reads one plan line at a time and moves through it by phases; everything it must keep between ticks is in the
plugin's globals. It measures and writes raw numbers, and decides nothing: gametest.py judges them. A plan line is
numbers split by '|' (see LINE_KINDS); result lines are in RESULTS.

Should the first CELL move reset the globals or the callback (not known yet), gl_ and gn_ start the tick again, and
went.txt keeps the first move from happening twice."""
import os
import re
import struct

CHECKER_PLUGIN = 'FOLab Game Test.esp'
FOLDER = 'FOLabGameTest'                        # (inside Data; everything the run reads and writes)
RESULT_FILE = 'lines.txt'
CONSOLE_FILE = 'console.txt'
TICK_FILE = 'folabgt_tick.txt'
CHUNK = 100                                     # (plan lines in a file: well under the 16 KB ReadStringFromFile sees)
MAX_TICK_BYTES = 30000
TICK_EVERY = 2                                  # (frames between ticks)
SETTLE = 12                                     # (ticks to let the player land)

GO, CAL, STAND, THING, ACTOR, DOOR, NPC, DONE = range(8)
LINE_KINDS = {GO: 'go|id|cell number', CAL: 'cal|id|x|y|z', STAND: 'stand|id|x|y|z', THING: 'thing|id|mod|hex|x|y|z',
              ACTOR: 'actor|id|mod|hex|x|y|z', DOOR: 'door|id|mod|hex|x|y|z', NPC: 'npc|id|ax|ay|az|bx|by|bz|ticks', DONE: 'done|id'}

# Result lines: the kind, then these fields. text fields stay strings; others are numbers.
RESULTS = {
    'boot': ('where', 'run'),
    'go': ('id',),
    'at': ('id', 'form', 'name', 'x', 'y', 'z'),
    'cal': ('id', 'x', 'y', 'z', 'dx', 'dy', 'dz', 'uz', 'nx', 'ny'),
    'stand': ('id', 'x1', 'y1', 'z1', 'x2', 'y2', 'z2', 'air', 'water', 'd0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7'),
    'thing': ('id', 'found', 'x', 'y', 'z', 'disabled', 'hit', 'hitform'),
    'actor': ('id', 'found', 'x', 'y', 'z', 'air', 'dead', 'water'),
    'door': ('id', 'found', 'load', 'locked', 'form', 'name'),
    'land': ('id', 'form', 'name', 'x', 'y', 'z1', 'z2', 'air'),
    'npc': ('id', 'dist', 'ticks'),
    'beat': ('n',),
    'died': ('id',),
    'abort': ('why', 'id'),
    'done': ('n',),
}
TEXT_FIELDS = {'where', 'run', 'form', 'name', 'hitform', 'why'}

GLOBALS = ['FOLabGTStep', 'FOLabGTPhase', 'FOLabGTWait', 'FOLabGTBeat', 'FOLabGTDone', 'FOLabGTChunk', 'FOLabGTLine', 'FOLabGTTries',
           'FOLabGTX', 'FOLabGTY', 'FOLabGTZ', 'FOLabGTAX', 'FOLabGTAY', 'FOLabGTAZ', 'FOLabGTBX', 'FOLabGTBY', 'FOLabGTBZ',
           'FOLabGTTick', 'FOLabGTRef'] + ['FOLabGTRay%d' % i for i in range(8)]

# The commands the checker calls that aren't the game's own, and what their tables in the DLLs say:
#   (file, parameters, needs a calling ref) as read from the user's copies; test_gametest compares when the files are there.
COMMANDS = {
    'WriteStringToFile': ('jip', 23, False), 'ReadStringFromFile': ('jip', 3, False), 'FileExists': ('jip', 2, False),
    'GetRayCastPos': ('jip', 7, True), 'GetRayCastRef': ('jip', 2, True), 'SetPosEx': ('jip', 4, True),
    'GetFormFromMod': ('jip', 2, False), 'SetGameMainLoopCallback': ('jip', 4, False), 'IsInAir': ('jip', 0, True), 'IsInWater': ('jip', 0, True),
    'SetGlobalRef': ('jip', 2, False), 'GetGlobalRef': ('jip', 1, False),
    'CompileScript': ('nvse', 2, False), 'GetTeleportCell': ('nvse', 0, True), 'IsLoadDoor': ('nvse', 0, True), 'GetParentCell': ('nvse', 0, True),
    'sv_Split': ('nvse', 3, False), 'ToNumber': ('nvse', 3, False), 'sv_Construct': ('nvse', 21, False),
}
# The game's own commands it calls, by the name in scriptfuncs.json's tables. The console ones go through xNVSE's con_ prefix.
GAME_COMMANDS = ['MenuMode', 'GetPos', 'SetAngle', 'GetDead', 'GetDisabled', 'GetLocked', 'Activate', 'PlaceAtMe', 'AddScriptPackage',
                 'GetDistance', 'Disable', 'MarkForDelete']
CONSOLE_COMMANDS = ['SCOF', 'CenterOnCell', 'CenterOnWorld', 'ToggleGodMode', 'QuitGame']


def data_rel(name):
    """A path as the game's commands want it: from the game's folder."""
    return 'Data\\%s\\%s' % (FOLDER, name)


def _write(fmt, *args):
    return 'WriteStringToFile "%s" 1 "%s"%s' % (data_rel(RESULT_FILE), fmt, ''.join(' ' + a for a in args))


def _start_lines(where, run):
    """Start the tick, once: the runner's three scripts share this. (A callback that survived a load is taken off first:
    two ticks would run the plan twice as fast and out of step.)"""
    return ['ref rT',
            _write('boot|%s|%s' % (where, run)),
            'let rT := GetGlobalRef FOLabGTTick',
            'if rT',
            '    SetGameMainLoopCallback rT 0',
            'else',
            '    let rT := CompileScript "%s"' % TICK_FILE,
            '    SetGlobalRef FOLabGTTick rT',
            'endif',
            'if rT',
            '    SetGameMainLoopCallback rT 1 %d 3' % TICK_EVERY,
            'else',
            '    ' + _write('abort|tick did not compile|0'),
            'endif']


def boot_text(run):
    return '\r\n'.join(['; FOLab game test. FOLab takes this file away when the run ends.',
                        'con_SCOF "%s"' % data_rel(CONSOLE_FILE)] + _start_lines('gr', run)) + '\r\n'


def again_text(where, run):
    return '\r\n'.join(['; FOLab game test: if a load stopped the tick, start it again.'] + _start_lines(where, run)) + '\r\n'


def _ray(i):
    """One ray, in the way the player faces, to the flat distance; -1 for no answer."""
    return ['set FOLabGTX to -99999',
            'set FOLabGTY to -99999',
            'player.GetRayCastPos FOLabGTX FOLabGTY FOLabGTZ',
            'if FOLabGTX == -99999',
            '    set FOLabGTRay%d to -1' % i,
            'else',
            '    let FOLabGTRay%d := (((FOLabGTX - fPX) ^ 2) + ((FOLabGTY - fPY) ^ 2)) ^ 0.5' % i,
            'endif']


def _advance():
    """On to the next plan line."""
    return ['set FOLabGTStep to FOLabGTStep + 1', 'set FOLabGTPhase to 0', 'set FOLabGTWait to 0', 'set FOLabGTLine to FOLabGTLine + 1',
            'if FOLabGTLine >= %d' % CHUNK, '    set FOLabGTLine to 0', '    set FOLabGTChunk to FOLabGTChunk + 1', 'endif']


def tick_text(cells, base, package):
    """The tick. cells: {number: ('coc', edid) or ('cow', world edid, grid x, grid y)}; base, package: (file, 6 hex digits) of
    the NPC for the walk test and its follow package. A UDF: every local is gone by the next tick, so what lasts is in globals."""
    go = []
    for n, c in sorted(cells.items()):
        go += ['if fA == %d' % n, ('    con_CenterOnCell "%s"' % c[1]) if c[0] == 'coc' else '    con_CenterOnWorld %s %d %d' % (c[1], c[2], c[3]), 'endif']
    lines = [
        'scn FOLabGTTick', '',
        'array_var aP', 'string_var sL', 'string_var sPath', 'string_var sMod', 'string_var sHex',
        'ref rT', 'ref rC', 'ref rB', 'ref rK',
        'float fA', 'float fB', 'float fC', 'float fD', 'float fE', 'float fF', 'float fId', 'float fKind', 'float fPh',
        'float fPX', 'float fPY', 'float fPZ', 'short iAir', 'short iWater', 'short iA', 'short iB', 'short iC', '',
        'begin Function { }', '',
        'if FOLabGTDone', '    return', 'endif',
        'set FOLabGTBeat to FOLabGTBeat + 1',
        # (a menu but the main one: wait. No line is written, so a message box that never closes ends as "went silent".)
        'if MenuMode', '    if MenuMode 1013 == 0', '        return', '    endif', '    if FOLabGTBeat < 40', '        return', '    endif', 'endif',
        'if player.GetDead', '    ' + _write('died|%.0f', 'FOLabGTStep'), '    set FOLabGTDone to 1', '    con_QuitGame', '    return', 'endif',
        'let sPath := sv_Construct "%s" FOLabGTChunk' % data_rel('plan\\%.0f.txt'),
        'let fA := FOLabGTLine + 1',
        'let sL := ReadStringFromFile $sPath fA 1',
        'let aP := sv_Split $sL "|"',
        'let fKind := ToNumber aP[0]',
        'let fId := ToNumber aP[1]',
        'set fPh to FOLabGTPhase',
        '',
        '; ----- go to a place -----',
        'if fKind == %d' % GO,
        '    let fA := ToNumber aP[2]',
        '    if fPh == 0',
        '        ' + _write('go|%.0f', 'fId'),
        # (the first move, from the main menu, happens once whatever a reset does to the globals)
        '        if FOLabGTStep > 0 || FileExists "%s\\went.txt" == 0' % FOLDER,
        '            WriteStringToFile "%s" 0 "went"' % data_rel('went.txt'),
    ] + ['            ' + g for g in go] + [
        '        endif',
        '        set FOLabGTPhase to 1', '        set FOLabGTWait to 0', '        return',
        '    endif',
        '    if MenuMode',                  # (still at the main menu: try once more after a while, then give up)
        '        set FOLabGTWait to FOLabGTWait + 1',
        '        if FOLabGTWait >= 400',
        '            set FOLabGTTries to FOLabGTTries + 1',
        '            if FOLabGTTries >= 2',
        '                ' + _write('abort|the first move never happened|%.0f', 'fId'),
        '                set FOLabGTDone to 1', '                con_QuitGame', '                return',
        '            endif',
    ] + ['            ' + g for g in go] + [
        '            set FOLabGTWait to 0',
        '        endif',
        '        return',
        '    endif',
        '    set FOLabGTWait to FOLabGTWait + 1',
        '    if FOLabGTWait < 40', '        return', '    endif',
        '    if FOLabGTStep == 0', '        con_ToggleGodMode', '    endif',
        '    let rC := player.GetParentCell',
        '    set fPX to player.GetPos X', '    set fPY to player.GetPos Y', '    set fPZ to player.GetPos Z',
        '    ' + _write('at|%.0f|%i|%n|%.1f|%.1f|%.1f', 'fId', 'rC', 'rC', 'fPX', 'fPY', 'fPZ'),
    ] + ['    ' + a for a in _advance()] + ['    return', 'endif', '',
        '; ----- nothing can be measured from a menu -----',
        'if MenuMode', '    return', 'endif', '',
        '; ----- stand on a point: land, measure twice, eight rays round; cal adds straight down, up -----',
        'if fKind == %d || fKind == %d' % (CAL, STAND),
        '    let fA := ToNumber aP[2]', '    let fB := ToNumber aP[3]', '    let fC := ToNumber aP[4]',
        '    if fPh == 0',
        '        player.SetAngle X 0',
        '        player.SetPosEx fA fB fC',
        '        set FOLabGTPhase to 1', '        set FOLabGTWait to %d' % SETTLE, '        return',
        '    endif',
        '    if FOLabGTWait > 0', '        set FOLabGTWait to FOLabGTWait - 1', '        return', '    endif',
        '    set fPX to player.GetPos X', '    set fPY to player.GetPos Y', '    set fPZ to player.GetPos Z',
        '    if fPh == 1',
        '        set FOLabGTAX to fPX', '        set FOLabGTAY to fPY', '        set FOLabGTAZ to fPZ',
        '        set FOLabGTPhase to 2', '        set FOLabGTWait to %d' % SETTLE, '        return',
        '    endif',
        '    if fPh == 2',
        '        set FOLabGTBX to fPX', '        set FOLabGTBY to fPY', '        set FOLabGTBZ to fPZ',
        '        player.SetAngle Z 0',
        '        set FOLabGTPhase to 10', '        return',
        '    endif',
    ]
    for i in range(8):
        lines += ['    if fPh == %d' % (10 + i)] + ['        ' + r for r in _ray(i)] + \
                 ['        player.SetAngle Z %d' % ((i + 1) * 45 % 360), '        set FOLabGTPhase to %d' % (11 + i), '        return', '    endif']
    lines += [
        '    if fKind == %d' % STAND,
        '        let iAir := player.IsInAir', '        let iWater := player.IsInWater',
        '        ' + _write('stand|%.0f|%.1f|%.1f|%.1f|%.1f|%.1f|%.1f|%.0f|%.0f|%.0f|%.0f|%.0f|%.0f|%.0f|%.0f|%.0f|%.0f', 'fId', 'FOLabGTAX', 'FOLabGTAY', 'FOLabGTAZ',
                          'FOLabGTBX', 'FOLabGTBY', 'FOLabGTBZ', 'iAir', 'iWater', *['FOLabGTRay%d' % i for i in range(8)]),
    ] + ['        ' + a for a in _advance()] + ['        return', '    endif',
        # (calibration: what a ray's answer means, read back by the report before it trusts any ray)
        '    if fPh == 18',
        '        player.SetAngle X 89', '        set FOLabGTPhase to 19', '        return',
        '    endif',
        '    if fPh == 19',
        '        set FOLabGTX to -99999', '        set FOLabGTY to -99999', '        set FOLabGTZ to -99999',
        '        player.GetRayCastPos FOLabGTX FOLabGTY FOLabGTZ',
        '        set FOLabGTAX to FOLabGTX', '        set FOLabGTAY to FOLabGTY', '        set FOLabGTAZ to FOLabGTZ',
        '        player.SetAngle X -89', '        set FOLabGTPhase to 20', '        return',
        '    endif',
        '    if fPh == 20',
        '        set FOLabGTZ to -99999',
        '        player.GetRayCastPos FOLabGTX FOLabGTY FOLabGTZ',
        '        set FOLabGTBZ to FOLabGTZ',
        '        player.SetAngle X 0', '        player.SetAngle Z 0', '        set FOLabGTPhase to 21', '        return',
        '    endif',
        '    set FOLabGTX to -99999', '    set FOLabGTY to -99999',
        '    player.GetRayCastPos FOLabGTX FOLabGTY FOLabGTZ',
        '    ' + _write('cal|%.0f|%.1f|%.1f|%.1f|%.1f|%.1f|%.1f|%.1f|%.1f|%.1f', 'fId', 'fPX', 'fPY', 'fPZ', 'FOLabGTAX', 'FOLabGTAY', 'FOLabGTAZ', 'FOLabGTBZ', 'FOLabGTX', 'FOLabGTY'),
    ] + ['    ' + a for a in _advance()] + ['    return', 'endif', '',
        '; ----- a thing that should rest on something: above it, look down, where is it, what is under it -----',
        'if fKind == %d' % THING,
        '    let fA := ToNumber aP[4]', '    let fB := ToNumber aP[5]', '    let fC := ToNumber aP[6]',
        '    if fPh == 0',
        '        player.SetAngle X 89',
        '        let fC := fC + 96',
        '        player.SetPosEx fA fB fC',
        '        set FOLabGTPhase to 1', '        set FOLabGTWait to 10', '        return',
        '    endif',
        '    if FOLabGTWait > 0', '        set FOLabGTWait to FOLabGTWait - 1', '        return', '    endif',
        '    let sMod := aP[2]', '    let sHex := aP[3]',
        '    let rT := GetFormFromMod $sMod $sHex',
        '    set FOLabGTZ to -99999',
        '    player.GetRayCastPos FOLabGTX FOLabGTY FOLabGTZ',
        '    let rC := player.GetRayCastRef',
        '    if rT',
        '        set fD to rT.GetPos X', '        set fE to rT.GetPos Y', '        set fF to rT.GetPos Z',
        '        let iA := rT.GetDisabled',
        '        ' + _write('thing|%.0f|1|%.1f|%.1f|%.1f|%.0f|%.1f|%i', 'fId', 'fD', 'fE', 'fF', 'iA', 'FOLabGTZ', 'rC'),
        '    else',
        '        ' + _write('thing|%.0f|0|0|0|0|0|%.1f|%i', 'fId', 'FOLabGTZ', 'rC'),
        '    endif',
        '    player.SetAngle X 0',
    ] + ['    ' + a for a in _advance()] + ['    return', 'endif', '',
        '; ----- someone the mod placed: have they stayed where they were put? -----',
        'if fKind == %d' % ACTOR,
        '    let fA := ToNumber aP[4]', '    let fB := ToNumber aP[5]', '    let fC := ToNumber aP[6]',
        '    if fPh == 0',
        '        let fA := fA + 96',
        '        let fC := fC + 32',
        '        player.SetPosEx fA fB fC',
        '        set FOLabGTPhase to 1', '        set FOLabGTWait to 30', '        return',
        '    endif',
        '    if FOLabGTWait > 0', '        set FOLabGTWait to FOLabGTWait - 1', '        return', '    endif',
        '    let sMod := aP[2]', '    let sHex := aP[3]',
        '    let rT := GetFormFromMod $sMod $sHex',
        '    if rT',
        '        set fD to rT.GetPos X', '        set fE to rT.GetPos Y', '        set fF to rT.GetPos Z',
        '        let iA := rT.IsInAir', '        let iB := rT.GetDead', '        let iC := rT.IsInWater',
        '        ' + _write('actor|%.0f|1|%.1f|%.1f|%.1f|%.0f|%.0f|%.0f', 'fId', 'fD', 'fE', 'fF', 'iA', 'iB', 'iC'),
        '    else',
        '        ' + _write('actor|%.0f|0|0|0|0|0|0|0', 'fId'),
        '    endif',
    ] + ['    ' + a for a in _advance()] + ['    return', 'endif', '',
        '; ----- a door: what the game says of it, then through it; where did we land? -----',
        'if fKind == %d' % DOOR,
        '    let fA := ToNumber aP[4]', '    let fB := ToNumber aP[5]', '    let fC := ToNumber aP[6]',
        '    if fPh == 0',
        '        player.SetPosEx fA fB fC',
        '        set FOLabGTPhase to 1', '        set FOLabGTWait to 8', '        return',
        '    endif',
        '    if FOLabGTWait > 0', '        set FOLabGTWait to FOLabGTWait - 1', '        return', '    endif',
        '    if fPh == 1',
        '        let sMod := aP[2]', '        let sHex := aP[3]',
        '        let rT := GetFormFromMod $sMod $sHex',
        '        if rT == 0',
        '            ' + _write('door|%.0f|0|0|0|0|-', 'fId'),
    ] + ['            ' + a for a in _advance()] + ['            return', '        endif',
        '        let rC := rT.GetTeleportCell', '        let iA := rT.IsLoadDoor', '        let iB := rT.GetLocked',
        '        ' + _write('door|%.0f|1|%.0f|%.0f|%i|%n', 'fId', 'iA', 'iB', 'rC', 'rC'),
        '        if iA == 0 || iB',
    ] + ['            ' + a for a in _advance()] + ['            return', '        endif',
        '        rT.Activate player 1',
        '        set FOLabGTPhase to 2', '        set FOLabGTWait to 40', '        return',
        '    endif',
        '    if fPh == 2',
        '        set FOLabGTAZ to player.GetPos Z',
        '        set FOLabGTPhase to 3', '        set FOLabGTWait to %d' % SETTLE, '        return',
        '    endif',
        '    let rC := player.GetParentCell',
        '    set fPX to player.GetPos X', '    set fPY to player.GetPos Y', '    set fPZ to player.GetPos Z',
        '    let iAir := player.IsInAir',
        '    ' + _write('land|%.0f|%i|%n|%.1f|%.1f|%.1f|%.1f|%.0f', 'fId', 'rC', 'rC', 'fPX', 'fPY', 'FOLabGTAZ', 'fPZ', 'iAir'),
    ] + ['    ' + a for a in _advance()] + ['    return', 'endif', '',
        '; ----- an NPC told to follow: does the navmesh bring them across? -----',
        'if fKind == %d' % NPC,
        '    if fPh == 0',
        '        let fA := ToNumber aP[2]', '        let fB := ToNumber aP[3]', '        let fC := ToNumber aP[4]',
        '        player.SetPosEx fA fB fC',
        '        set FOLabGTPhase to 1', '        set FOLabGTWait to %d' % SETTLE, '        return',
        '    endif',
        '    if FOLabGTWait > 0 && fPh == 1', '        set FOLabGTWait to FOLabGTWait - 1', '        return', '    endif',
        '    if fPh == 1',
        '        let fD := ToNumber aP[5]', '        let fE := ToNumber aP[6]', '        let fF := ToNumber aP[7]',
        '        let rB := GetFormFromMod "%s" "%s"' % tuple(base),
        '        let rK := GetFormFromMod "%s" "%s"' % tuple(package),
        '        let rT := player.PlaceAtMe rB 1',
        '        SetGlobalRef FOLabGTRef rT',
        '        rT.AddScriptPackage rK',
        '        player.SetPosEx fD fE fF',
        '        let FOLabGTWait := ToNumber aP[8]',
        '        set FOLabGTPhase to 2', '        return',
        '    endif',
        '    let rT := GetGlobalRef FOLabGTRef',
        '    set FOLabGTWait to FOLabGTWait - 1',
        '    set fD to rT.GetDistance player',
        '    if fD < 300 || FOLabGTWait <= 0',
        '        ' + _write('npc|%.0f|%.1f|%.0f', 'fId', 'fD', 'FOLabGTWait'),
        '        rT.Disable', '        rT.MarkForDelete',
    ] + ['        ' + a for a in _advance()] + ['    endif', '    return', 'endif', '',
        '; ----- the end -----',
        'if fKind == %d' % DONE,
        '    ' + _write('done|%.0f', 'FOLabGTStep'),
        '    set FOLabGTDone to 1',
        '    con_QuitGame',
        '    return',
        'endif',
        # (a line it can't read: the end of the plan's file, or ReadStringFromFile isn't what's thought)
        _write('abort|plan line not understood|%.0f', 'FOLabGTStep'),
        'set FOLabGTDone to 1',
        'con_QuitGame',
        '', 'end']
    return '\r\n'.join(lines) + '\r\n'


def plan_chunks(steps):
    """{chunk's name: text}: the plan lines, CHUNK in a file. steps: lists of fields."""
    out = {}
    for n in range(0, len(steps), CHUNK):
        out['%d.txt' % (n // CHUNK)] = '\r\n'.join('|'.join(str(x) for x in s) for s in steps[n:n + CHUNK]) + '\r\n'
    return out


def game_files(plan_steps, cells, base, package, run):
    """Every text file a run puts in Data, by its path from Data."""
    out = {'NVSE\\plugins\\scripts\\gr_folabgt.txt': boot_text(run),
           'NVSE\\plugins\\scripts\\gl_folabgt.txt': again_text('gl', run),
           'NVSE\\plugins\\scripts\\gn_folabgt.txt': again_text('gn', run),
           'NVSE\\user_defined_functions\\' + TICK_FILE: tick_text(cells, base, package)}
    for name, text in plan_chunks(plan_steps).items():
        out['%s\\plan\\%s' % (FOLDER, name)] = text
    return out


def checker_plugin():
    """The checker's plugin: only globals, for the commands that answer in globals and for what lasts between ticks."""
    import espwrite
    import plugintree
    head = [('HEDR', struct.pack('<fiI', espwrite.HEDR_VERSION, len(GLOBALS), 0x01000800 + len(GLOBALS))), ('CNAM', b'FOLab\0'),
            ('SNAM', b'FOLab game test: put in for a test run, taken out after.\0'), ('MAST', b'FalloutNV.esm\0'), ('DATA', b'\0' * 8)]
    tree = plugintree.Plugin.empty(espwrite.join(head))
    top = tree.top('GLOB')
    for n, name in enumerate(GLOBALS):
        data = espwrite.join([('EDID', name.encode('ascii') + b'\0'), ('FNAM', b'f'), ('FLTV', struct.pack('<f', 0.0))])
        top.kids.append(plugintree.Rec.new('GLOB', 0, 0x01000800 + n, data))
    return tree.bytes()


# ---------- what can be checked without the game ----------

def check_text(text, is_function=False):
    """What can go wrong in a text that needs no game to see it. Returns a list of troubles."""
    out = []
    if len(text.encode('cp1252', 'replace')) > MAX_TICK_BYTES:
        out.append('over %d bytes' % MAX_TICK_BYTES)
    try:
        text.encode('ascii')
    except UnicodeEncodeError:
        out.append('not plain ASCII')
    depth, begins = 0, 0
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.split(';', 1)[0].strip()
        low = line.lower()
        if len(raw) > 480:
            out.append('line %d is long' % n)
        if low.startswith('if '):
            depth += 1
        elif low == 'endif':
            depth -= 1
            if depth < 0:
                out.append('line %d: endif with no if' % n)
                depth = 0
        elif low.startswith('else') and depth == 0:
            out.append('line %d: else with no if' % n)
        if low.startswith('begin '):
            begins += 1
        for fmt, args in re.findall(r'WriteStringToFile "[^"]*" \d "([^"]*)"((?: [^ ]+)*)', line):
            need = len(re.findall(r'%(?:\.\d+f|i|n|z)', fmt))
            have = len(args.split())
            if need != have:
                out.append('line %d: %d values for %d places' % (n, have, need))
            kind = fmt.split('|')[0]
            if kind not in RESULTS and kind != 'went':
                out.append('line %d: writes "%s", which the report doesn\'t know' % (n, kind))
            elif kind in RESULTS and len(fmt.split('|')) - 1 != len(RESULTS[kind]):
                out.append('line %d: "%s" has %d fields, should be %d' % (n, kind, len(fmt.split('|')) - 1, len(RESULTS[kind])))
            if have > 20:
                out.append('line %d: WriteStringToFile takes 20 values at most' % n)
    if depth:
        out.append('%d if without endif' % depth)
    if is_function and begins != 1:
        out.append('a function needs one begin')
    return out


def declared_in(text):
    """Which variables a text declares: a typo'd name wouldn't compile, and only a game would otherwise say so."""
    return {m.group(1).lower() for m in re.finditer(r'^\s*(?:float|short|int|ref|array_var|string_var)\s+(\w+)', text, re.M | re.I)}


def undeclared_in(text):
    """Names that look like this file's variables (f..., i..., r..., s..., a... in camel case, or a FOLabGT global) and aren't known."""
    known = declared_in(text) | {g.lower() for g in GLOBALS}
    out = set()
    for raw in text.splitlines():
        line = re.sub(r'"[^"]*"', '""', raw.split(';', 1)[0])
        for w in re.findall(r'\b(?:FOLabGT\w+|[fsar][A-Z]\w*|i[A-Z][a-z]\w*)\b', line):
            if w.lower() not in known:
                out.add(w)
    return out


# ---------- the commands' tables in the DLLs (read only) ----------

def read_table(path, names):
    """What a DLL's own command table says of each name: {name: {'params': n, 'needs_ref': bool, 'types': [...]}}. Reads the file."""
    with open(path, 'rb') as f:
        b = f.read()
    pe = struct.unpack_from('<I', b, 0x3c)[0]
    count = struct.unpack_from('<H', b, pe + 6)[0]
    opt = struct.unpack_from('<H', b, pe + 20)[0]
    base = struct.unpack_from('<I', b, pe + 52)[0]
    secs = [struct.unpack_from('<IIII', b, pe + 24 + opt + 40 * k + 8) for k in range(count)]

    def to_va(o):
        for _vs, va, rs, rp in secs:
            if rp <= o < rp + rs:
                return o - rp + va + base

    out = {}
    for name in names:
        at = b.find(b'\0' + name.encode() + b'\0')
        if at < 0:
            continue
        va = to_va(at + 1)
        for m in re.finditer(re.escape(struct.pack('<I', va)), b):
            needs, params = struct.unpack_from('<HH', b, m.start() + 16)
            if params <= 40 and needs <= 1:
                out[name] = {'params': params, 'needs_ref': bool(needs)}
                break
    return out


def recheck(game_dir):
    """Every command the checker uses against the user's own DLLs: [troubles]."""
    trouble = []
    files = {'jip': os.path.join(game_dir, 'Data', 'NVSE', 'plugins', 'jip_nvse.dll'), 'nvse': os.path.join(game_dir, 'nvse_1_4.dll')}
    for tag, path in files.items():
        names = [n for n, c in COMMANDS.items() if c[0] == tag]
        table = read_table(path, names)
        for n in names:
            if n not in table:
                trouble.append('%s: not in %s' % (n, os.path.basename(path)))
            elif (table[n]['params'], table[n]['needs_ref']) != COMMANDS[n][1:]:
                trouble.append('%s: its table says %d parameters, needs ref %s' % (n, table[n]['params'], table[n]['needs_ref']))
    return trouble


if __name__ == '__main__':
    import gamedata
    data = gamedata.find_data_dir()
    bad = recheck(os.path.dirname(os.path.normpath(data)))
    print('\n'.join(bad) or 'Every command the checker uses is in the DLLs, with the parameters it expects.')
