"""Starting the game from FOLab, and "Play here".

Open in game puts the mod in the game and asks Steam to start it (the game's launcher opens: Play). The game can't be
told on its command line where to start, so you still press Continue or load a save.

Play here adds FOLab Test.esp, kept apart from your mod: an invisible marker where you asked, and a quest whose script
moves you there once a save is loaded. It is the one script FOLab writes, compiled by hand to the same bytes the game's
own compiler gives (checked against the game's scripts: GameMode block, if/set on a local, MoveTo):

    scn FOLabTestScript
    short done
    begin GameMode
        if done == 0
            set done to 1
            player.MoveTo FOLabTestMarker
        endif
    end

Each Play here makes a new quest (a new form ID), so it moves you once in any save, even one that used an earlier one.
Open in game on its own takes FOLab Test.esp out again."""
import os
import struct
import subprocess

import espwrite
import install
import plugintree
import project
import tes4

TEST_PLUGIN = 'FOLab Test.esp'
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
    exe = game_exe(data_dir)
    if not os.path.isfile(exe):
        raise FileNotFoundError('FalloutNV.exe not found beside the Data folder (%s)' % exe)
    loader = os.path.join(os.path.dirname(exe), 'nvse_loader.exe')
    if via == 'nvse' and os.path.isfile(loader):
        flags = getattr(subprocess, 'DETACHED_PROCESS', 0) | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
        subprocess.Popen([loader], cwd=os.path.dirname(exe), creationflags=flags, close_fds=True)
        return 'nvse'
    os.startfile('steam://rungameid/22380')
    return 'steam'


def compiled_script():
    """The bytecode of the script in this module's docstring (ref 1 = the player, ref 2 = the marker)."""
    cond = b' s\x01\x00 0 =='                                        # done == 0
    if_ = struct.pack('<HHHH', 0x16, 4 + len(cond), 2, len(cond)) + cond  # if (skip 2 statements when false)
    set_ = struct.pack('<HH', 0x15, 7) + b's\x01\x00' + struct.pack('<H', 2) + b' 1'   # set done to 1
    moveto = struct.pack('<HHHHH', 0x1C, 1, 0x109E, 5, 1) + b'r\x02\x00'               # player.MoveTo marker
    endif, end = struct.pack('<HH', 0x19, 0), struct.pack('<HH', 0x11, 0)
    body = if_ + set_ + moveto + endif + end
    begin = struct.pack('<HHHI', 0x10, 6, 0, len(body))                 # begin GameMode
    return struct.pack('<HH', 0x1D, 0) + begin + body                     # (scn)


SOURCE = ('scn FOLabTestScript\r\n\r\nshort done\r\n\r\nbegin GameMode\r\n\tif done == 0\r\n\t\tset done to 1\r\n'
          '\t\tplayer.MoveTo FOLabTestMarker\r\n\tendif\r\nend\r\n')


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


def write_test_plugin(gd, cell, p, path):
    """FOLab Test.esp: an XMarkerHeading at p = [x, y, z, rz] in cell, and the quest and script that move the player
    there once. Its masters are every file the game loads before it (so every form ID reads the same in it)."""
    n = _settings_counter()
    masters = [os.path.basename(pl.path) for pl in gd.plugins]
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

    marker_base = next(fid for fid, (i, r) in gd.forms.items()
                       if r.tag == 'STAT' and tes4.zstr(gd.fields(fid).get('EDID', b'')) == 'XMarkerHeading')
    tree = plugintree.Plugin.empty(b'')
    order = gd.plugins[0].top_groups()
    # the script and its quest
    scda = compiled_script()
    schr = struct.pack('<IIIIHH', 0, 2, len(scda), 1, SCRIPT_QUEST, 1)
    slsd = struct.pack('<I12sB7s', 1, b'\0' * 12, 1, b'\0' * 7)          # local 1: done (a short)
    script = espwrite.join([('EDID', b'FOLabTestScript%d\0' % n), ('SCHR', schr), ('SCDA', scda),
                            ('SCTX', SOURCE.encode('cp1252')), ('SLSD', slsd), ('SCVR', b'done\0'),
                            ('SCRO', struct.pack('<I', PLAYER_REF)), ('SCRO', struct.pack('<I', marker_id))])
    tree.top('SCPT', order).kids.append(plugintree.Rec.new('SCPT', 0, script_id, script))
    quest = espwrite.join([('EDID', b'FOLabTestQuest%d\0' % n), ('SCRI', struct.pack('<I', script_id)),
                           ('FULL', b'FOLab test\0'), ('DATA', struct.pack('<BBHf', QUEST_START_ENABLED, 0, 0, 0.5))])
    tree.top('QUST', order).kids.append(plugintree.Rec.new('QUST', 0, quest_id, quest))
    # the marker, in the place (a copy of its CELL record carries it, as every plugin that adds to a cell must)
    lid = w.local(cell)
    found = {}
    _node, kids = w._cell_node(tree, found, cell, lid, order)
    ref = espwrite.join([('EDID', b'FOLabTestMarker\0'), ('NAME', struct.pack('<I', marker_base)),
                         ('DATA', struct.pack('<6f', p[0], p[1], p[2], 0.0, 0.0, p[3]))])
    w._ref_group(kids, lid, True).kids.append(plugintree.Rec.new('REFR', tes4.PERSISTENT, marker_id, ref))
    hedr = struct.pack('<fiI', espwrite.HEDR_VERSION, tree.count(), own | (base + 3))
    head = [('HEDR', hedr), ('CNAM', b'FOLab\0'), ('SNAM', b'FOLab Play here: moves you to a spot once a save loads. Safe to remove.\0')]
    for m in masters:
        head += [('MAST', m.encode('cp1252') + b'\0'), ('DATA', b'\0' * 8)]
    tree.header.set_data(espwrite.join(head), 0)
    with open(path + '.tmp', 'wb') as f:
        f.write(tree.bytes())
    os.replace(path + '.tmp', path)
    return {'quest': 'FOLabTestQuest%d' % n}


def take_out_test(data_dir):
    if os.path.exists(os.path.join(data_dir, TEST_PLUGIN)) or install.status(data_dir, TEST_PLUGIN)['active']:
        return install.uninstall(data_dir, TEST_PLUGIN)
    return None
