"""Starting the game from FOLab, and "Play here".

Open in game puts the mod in the game and starts it (through xNVSE's loader when it's there, else Steam). The game
can't be told on its command line where to start, so you still press Continue or load a save.

Play here adds FOLab Test.esp, kept apart from your mod: an invisible marker where you asked, and a quest whose script
moves you there once a save is loaded. It is the one script FOLab writes, compiled by hand to the same bytes the game's
own compiler gives (checked against the game's scripts: GameMode block, if/set on a local, ShowWarning, MoveTo):

    scn FOLabTestScript
    short done
    begin GameMode
        if done == 0
            set done to 1
            ShowWarning "FOLab: Play here (...)"
            player.MoveTo FOLabTestMarker
        endif
    end

Each Play here makes a new quest (a new form ID), so it moves you once in any save, even one that used an earlier one.
Open in game on its own takes FOLab Test.esp out again.

In a Mod Organizer loadout (FOLab opened on its own) all of this goes in the profile as mods, not the game's folder, and the game
starts through MO2, the only way it sees them: ModOrganizer.exe [-i instance] -p profile run -e <what's on its Run list>.
Started from MO2, it goes in MO2's virtual folder for that one run instead, as FOLab Play Here.esp (mo2write.place_inside)."""
import os
import shutil
import struct
import subprocess

import espwrite
import install
import plugintree
import project
import loadout
import tes4

TEST_PLUGIN = 'FOLab Test.esp'
INSIDE_PLUGIN = 'FOLab Play Here.esp'       # (the same, when MO2 started FOLab: never a name the real Data folder may have)
PLAYER_REF = 0x14
QUEST_START_ENABLED = 0x01
SCRIPT_QUEST = 1


def game_exe(data_dir):
    return os.path.join(os.path.dirname(os.path.normpath(data_dir)), 'FalloutNV.exe')


def game_running():
    """Is New Vegas running? (it holds its plugins open, and a save while it runs could leave it half-written)"""
    try:
        out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq FalloutNV.exe', '/NH'], capture_output=True, text=True,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return 'falloutnv.exe' in out.lower()


def launch(data_dir, via='nvse'):
    """Start the game: through xNVSE's nvse_loader.exe when it's there (no launcher window; how xNVSE says to start
    it), else the way Steam's Play button does (the game's launcher opens first). Never FalloutNV.exe directly: the
    Steam copy then fails with Steam's "Application load error 5:0000065434"."""
    inside = loadout.started_from_mo2()         # (what FOLab starts inside MO2's virtual folder sees the loadout's mods)
    if not inside:
        loadout.refuse_writes('Starting the game from here')
    exe = game_exe(data_dir)
    if not os.path.isfile(exe):
        raise FileNotFoundError('FalloutNV.exe not found beside the Data folder (%s)' % exe)
    loader = os.path.join(os.path.dirname(exe), 'nvse_loader.exe')
    if inside and not os.path.isfile(loader):
        raise ValueError('xNVSE isn\'t beside the game: started through Steam, the game wouldn\'t see your MO2 mods. Use MO2\'s Run button.')
    if (via == 'nvse' or inside) and os.path.isfile(loader):
        _start([loader])
        return 'nvse'
    os.startfile('steam://rungameid/22380')
    return 'steam'


def _start(args):
    """Starts a program and leaves it. (Tests put their own in its place: nothing there may start the real game.)"""
    flags = getattr(subprocess, 'DETACHED_PROCESS', 0) | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
    subprocess.Popen(args, cwd=os.path.dirname(args[0]), creationflags=flags, close_fds=True)


def mo2_program(extra=()):
    """Where ModOrganizer.exe is: the one running, or one found where MO2's programs are looked for. None if not found."""
    running = loadout._program_folder()
    found = [running] if running else []
    found += loadout.find_instances(extra)[1]
    for d in found:
        p = os.path.join(d, 'ModOrganizer.exe')
        if os.path.isfile(p):
            return p
    return None


def run_entry(instance):
    """Which of the instance's programs starts the game: xNVSE's if it's on the list, else the game. Its title, or None."""
    rows = instance.executables()
    for want in ('nvse_loader.exe', 'falloutnv.exe'):
        for e in rows:
            if os.path.basename(e['binary'].replace('\\', '/')).lower() == want:
                return e['title']
    return None


def launch_through_mo2(lo, extra=()):
    """Start the game inside this profile, as MO2's Run button does. 'mo2', or 'by hand' if FOLab can't find how: everything's in
    the profile by now, so MO2's own Run button still does it."""
    exe, title = mo2_program(extra), run_entry(lo.instance)
    if not exe or not title:
        return 'by hand'
    home = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'ModOrganizer', lo.instance.name)
    which = ['-i', lo.instance.name] if os.path.normcase(os.path.abspath(home)) == os.path.normcase(os.path.abspath(lo.instance.folder)) else []
    _start([exe] + which + ['-p', lo.profile, 'run', '-e', title])
    return 'mo2'


def floor_near(gd, refs, p):
    """The spot to arrive at for a place made of these things ([{'base': key, 'p': pose, 's': scale}]), given where the view is: the
    nearest floor of the main walkable part, straight below if there's floor there. The view is often up in the air, or above
    the roof: as it stood you'd fall into the void. p: [x, y, z, facing]. p itself if no floor can be worked out."""
    import kitplan
    rows = []
    for n, r in enumerate(refs):
        b = gd.from_key(r['base']) if not r['base'].startswith('+') else None
        if b and b in gd.forms and gd.forms[b][1].tag != 'DOOR':
            rows.append({'ref': n, 'type': 'REFR', 'base': b, 'pos': tuple(r['p'][:3]), 'rot': tuple(r['p'][3:6]), 'scale': r.get('s', 1.0), 'leads': False, 'bkey': r['base']})
    w = kitplan.Walk(gd, rows, tuple(p[:3]), cache={}, erode=True)
    if not w.pieces:
        return p
    main = max(w.pieces, key=len)
    v = w.voxel
    best, far = None, None
    for i in main:
        q = w.graph.p[i]
        x, y, z = (q[1] + 0.5) * v, (q[0] + 0.5) * v, q[2]
        # (height counts for little: the floor under the view, not the one level with it round a corner)
        d = (x - p[0]) ** 2 + (y - p[1]) ** 2 + ((z - p[2]) * 0.25) ** 2
        if far is None or d < far:
            best, far = (x, y, z), d
    return [best[0], best[1], best[2] + 8, p[3]]


def compiled_script(message=b'', move=True, give=()):
    """The bytecode of the script in this module's docstring (ref 1 = the player, ref 2 = the marker); with a message,
    ShowWarning shows it on screen as you're moved. give: [(script ref number, count)], each a player.AddItem: the
    form as that ref, the count a literal (the same bytes as the game's own Hull20GaAddScript and others)."""
    cond = b' s\x01\x00 0 =='                                        # done == 0
    set_ = struct.pack('<HH', 0x15, 7) + b's\x01\x00' + struct.pack('<H', 2) + b' 1'   # set done to 1
    # ShowWarning "text": 1 parameter, the text, then how many values fill into it (none)
    warn = struct.pack('<HHHH', 0x11B9, 6 + len(message), 1, len(message)) + message + b'\0\0' if message else b''
    moveto = struct.pack('<HHHHH', 0x1C, 1, 0x109E, 5, 1) + b'r\x02\x00' if move else b''   # player.MoveTo marker
    adds = b''.join(struct.pack('<HHHHH', 0x1C, 1, 0x1002, 10, 2) + b'r' + struct.pack('<H', r) + b'n' +
                    struct.pack('<i', c) for r, c in give)                # player.AddItem <form> <count>
    inside = 1 + bool(message) + bool(move) + len(give)
    if_ = struct.pack('<HHHH', 0x16, 4 + len(cond), inside, len(cond)) + cond  # if (skip what's inside when false)
    endif, end = struct.pack('<HH', 0x19, 0), struct.pack('<HH', 0x11, 0)
    body = if_ + set_ + warn + moveto + adds + endif + end
    begin = struct.pack('<HHHI', 0x10, 6, 0, len(body))                 # begin GameMode
    return struct.pack('<HH', 0x1D, 0) + begin + body                     # (scn)


def source(message, move=True, give=()):
    """give: [(editor ID, count)]"""
    return ('scn FOLabTestScript\r\n\r\nshort done\r\n\r\nbegin GameMode\r\n\tif done == 0\r\n\t\tset done to 1\r\n'
            '\t\tShowWarning "%s"\r\n' % message + ('\t\tplayer.MoveTo FOLabTestMarker\r\n' if move else '') +
            ''.join('\t\tplayer.AddItem %s %d\r\n' % g for g in give) + '\tendif\r\nend\r\n')


def _settings_counter():
    path = os.path.join(project.HOME, 'folab_settings.json')
    import json
    try:
        with open(path, encoding='utf-8') as f:
            s = json.load(f)
    except (OSError, ValueError):
        s = {}
    n = s.get('play_counter', 0) + 1
    s['play_counter'] = n
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(s, f, indent=1)
    return n


def write_test_plugin(gd, cell, p, path, place='', give=(), mod=None, own_place=None):
    """FOLab Test.esp: an XMarkerHeading at p = [x, y, z, rz] in cell, and the quest and script that move the player
    there once. Its masters are every file the game loads before it (so every form ID reads the same in it).
    With no cell nothing moves you. give: [(form key, count, editor ID)], put in your inventory once; a key of the
    mod's own ('+ID') needs mod, its plugin's file name (in the game before this one). own_place: (key, CELL record) when
    the place is the mod's own, not the game's (with mod too, and cell left out): its record is copied the same way."""
    n = _settings_counter()
    masters = [os.path.basename(pl.path) for pl in gd.plugins if os.path.basename(pl.path).lower() not in (TEST_PLUGIN.lower(), INSIDE_PLUGIN.lower())]
    if mod and mod.lower() not in [m.lower() for m in masters]:
        masters.append(mod)
    own = len(masters) << 24
    base = 0x800 + n * 4                       # (new IDs every time: a save that ran an earlier one runs this one too)
    marker_id, script_id, quest_id = own | base, own | (base + 1), own | (base + 2)

    class _P:                                   # (what espwrite's CELL copying asks of a project)
        plugin, records, cells, esm = TEST_PLUGIN, {}, {}, False

        @staticmethod
        def source_path():
            return None
    w = espwrite.Writer(gd, _P)
    w.masters = masters
    w.mindex = {m.lower(): k for k, m in enumerate(masters)}
    moving = bool(cell or own_place)

    marker_base = next(fid for fid, (i, r) in gd.forms.items()
                       if r.tag == 'STAT' and tes4.zstr(gd.fields(fid).get('EDID', b'')) == 'XMarkerHeading')
    tree = plugintree.Plugin.empty(b'')
    order = gd.plugins[0].top_groups()
    # the script and its quest
    if moving:
        msg = 'FOLab: Play here%s' % (' (' + place + ')' if place else '')
    else:
        msg = 'FOLab: added %s' % ', '.join('%d %s' % (c, e) if c > 1 else e for _k, c, e in give)
    msg = msg.encode('cp1252', 'replace')[:120]
    mod_i = next((k for k, m in enumerate(masters) if mod and m.lower() == mod.lower()), None)

    def item_id(key):
        if key.startswith('+'):
            return (mod_i << 24) | int(key[1:], 16)
        return w.local(gd.from_key(key))
    w.link = item_id                            # (the place's own record may name the mod's forms)
    scda = compiled_script(msg, move=moving, give=[(2 + moving + k, g[1]) for k, g in enumerate(give)])
    refs = [PLAYER_REF] + ([marker_id] if moving else []) + [item_id(k) for k, _c, _e in give]
    schr = struct.pack('<IIIIHH', 0, len(refs), len(scda), 1, SCRIPT_QUEST, 1)
    slsd = struct.pack('<I12sB7s', 1, b'\0' * 12, 1, b'\0' * 7)          # local 1: done (a short)
    text = source(msg.decode('cp1252'), moving, [(e, c) for _k, c, e in give])
    script = espwrite.join([('EDID', b'FOLabTestScript%d\0' % n), ('SCHR', schr), ('SCDA', scda),
                            ('SCTX', text.encode('cp1252', 'replace')), ('SLSD', slsd), ('SCVR', b'done\0')] +
                           [('SCRO', struct.pack('<I', r)) for r in refs])
    tree.top('SCPT', order).kids.append(plugintree.Rec.new('SCPT', 0, script_id, script))
    quest = espwrite.join([('EDID', b'FOLabTestQuest%d\0' % n), ('SCRI', struct.pack('<I', script_id)),
                           ('FULL', b'FOLab test\0'), ('DATA', struct.pack('<BBHf', QUEST_START_ENABLED, 0, 0, 0.5))])
    tree.top('QUST', order).kids.append(plugintree.Rec.new('QUST', 0, quest_id, quest))
    if not moving:
        return _finish(tree, masters, own, base, path, 'FOLabTestQuest%d' % n)
    # the marker, in the place (a copy of its CELL record carries it, as every plugin that adds to a cell must)
    # (outside, a persistent thing lives in its world's persistent cell, as the game's own do)
    found = {}
    if own_place:
        lid = item_id(own_place[0])
        _node, kids = w._cell_node(tree, found, None, lid, order, own_place[1])
    else:
        cell = gd.world_persistent.get(gd.ext_cells[cell], cell) if cell in gd.ext_cells else cell
        lid = w.local(cell)
        _node, kids = w._cell_node(tree, found, cell, lid, order)
    ref = espwrite.join([('EDID', b'FOLabTestMarker\0'), ('NAME', struct.pack('<I', marker_base)),
                         ('DATA', struct.pack('<6f', p[0], p[1], p[2], 0.0, 0.0, p[3]))])
    w._ref_group(kids, lid, True).kids.append(plugintree.Rec.new('REFR', tes4.PERSISTENT, marker_id, ref))
    return _finish(tree, masters, own, base, path, 'FOLabTestQuest%d' % n)


def _finish(tree, masters, own, base, path, quest):
    hedr = struct.pack('<fiI', espwrite.HEDR_VERSION, tree.count(), own | (base + 3))
    head = [('HEDR', hedr), ('CNAM', b'FOLab\0'), ('SNAM', b'FOLab test: Play here and Give it to me. Safe to remove.\0')]
    for m in masters:
        head += [('MAST', m.encode('cp1252') + b'\0'), ('DATA', b'\0' * 8)]
    tree.header.set_data(espwrite.join(head), 0)
    with open(path + '.tmp', 'wb') as f:
        f.write(tree.bytes())
    os.replace(path + '.tmp', path)
    return {'quest': quest}


AUTOLOAD = os.path.join('NVSE', 'plugins', 'scripts', 'gr_folab_load.txt')


def saves_dir():
    return os.path.join(os.path.expanduser('~'), 'Documents', 'My Games', 'FalloutNV', 'Saves')


def newest_save():
    """The save Continue would load: the newest .fos in the game's Saves folder (its name without .fos), or None."""
    d = saves_dir()
    fos = [os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith('.fos')] if os.path.isdir(d) else []
    return os.path.splitext(os.path.basename(max(fos, key=os.path.getmtime)))[0] if fos else None


def set_autoload(data_dir, on):
    """With JIP LN NVSE in the game, a gr_ text script runs once when the game reaches its main menu: FOLab's loads the
    newest save there, so Play here goes straight in. Off (Open in game, Take out): the file is removed."""
    loadout.refuse_writes('Setting up Play here')
    path = os.path.join(data_dir, AUTOLOAD)
    has_jip = os.path.isfile(os.path.join(data_dir, 'NVSE', 'plugins', 'jip_nvse.dll'))
    save = newest_save()
    if not (on and has_jip and save):
        if os.path.exists(path):
            os.remove(path)
        return None
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='cp1252', newline='\r\n') as f:
        f.write('; FOLab Play here: loads your newest save as the game reaches its menu.\n'
                '; FOLab removes this file when you use Open in game or Take out of game.\n'
                'LoadGame "%s"\n' % save)
    return save


def test_assets(path, gd=None):
    """What goes beside FOLab Test.esp in a loadout's mod folder, kept in '<plugin> assets' as a mod's own files are: the same
    script as set_autoload, if the loadout has JIP LN NVSE. The save it loads, or None. Without gd: just clears them out."""
    folder = os.path.splitext(path)[0] + ' assets'
    if os.path.isdir(folder):
        shutil.rmtree(folder)
    save = newest_save() if gd is not None else None
    if not save or not gd.loose_path(os.path.join('nvse', 'plugins', 'jip_nvse.dll')):
        return None
    to = os.path.join(folder, AUTOLOAD)
    os.makedirs(os.path.dirname(to), exist_ok=True)
    with open(to, 'w', encoding='cp1252', newline='\r\n') as f:
        f.write('; FOLab Play here: loads your newest save as the game reaches its menu.\nLoadGame "%s"\n' % save)
    return save


def take_out_test(data_dir):
    if os.path.exists(os.path.join(data_dir, TEST_PLUGIN)) or install.status(data_dir, TEST_PLUGIN)['active']:
        return install.uninstall(data_dir, TEST_PLUGIN)
    return None
