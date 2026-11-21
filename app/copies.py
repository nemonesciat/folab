"""Every other copy of the mod's plugin the game could load instead of the one just put in.

Put in MO2 put the new Waikiki.esp in MO2's mod folder and said it was in, but the game's own Data still held the
day before's Waikiki.esp, switched on in the game's plugins.txt: started from Steam, the game loaded that, and the
ship stood where she had been (18 Nov 2026). So nothing says "in" while another copy differs:

- in a loadout: the real game's Data (what plays when the game starts outside MO2), MO2's overwrite folder, and any
  other mod folder switched on in the profile holding a plugin of that name;
- in the plain game: nothing else loads, so only nv-rs's mods folder, when the game chosen to play in is nv-rs.

`others` lists them, `stale` keeps those whose bytes differ from the build. `move_out` puts stale copies in FOLab's
backups (only on the user's click, never into the game: a move out of it, and only of a file with the mod's name).
"""
import json
import os
import shutil
import time

import install
import project


def _same(a, b):
    try:
        if os.path.getsize(a) != os.path.getsize(b):
            return False
    except OSError:
        return False
    return install._hash_kept(a) == install._hash_kept(b)


def others(built, lo=None, mod_folder=None, nvrs_mods=None):
    """[{where, path, same, movable}] for each copy of built's plugin other than the one installed (mod_folder in a
    loadout, the game's Data in the plain game). movable: FOLab may move it out; another MO2 mod's or overwrite's
    file is MO2's to change (mo2write never touches a folder it didn't make)."""
    plugin = os.path.basename(built)
    found = []

    def look(where, folder, movable=False):
        if not folder:
            return
        p = os.path.join(folder, plugin)
        if os.path.isfile(p):
            found.append({'where': where, 'path': p, 'same': _same(p, built), 'movable': movable})

    if lo:
        look("the game's own Data folder (it loads when the game is started without MO2)", lo.data_dir, True)
        left = loose_left(built, lo.data_dir)
        if left:
            found.append({'where': "the game's own Data folder: %d loose files of an older Put in game (far view, models, "
                                   "textures), which the game draws beside the mod's own" % len(left),
                          'path': lo.data_dir, 'same': False, 'movable': True, 'loose': len(left)})
        look("MO2's overwrite folder", lo.instance.overwrite_dir)
        mine = os.path.normcase(os.path.abspath(mod_folder)) if mod_folder else None
        for m in lo.modlist:
            if not m.get('on') or m.get('unmanaged'):
                continue
            folder = os.path.join(lo.instance.mods_dir, m['name'])
            if mine and os.path.normcase(os.path.abspath(folder)) == mine:
                continue
            look('the MO2 mod "%s"' % m['name'], folder)
    for nm in ([nvrs_mods] if isinstance(nvrs_mods, str) else nvrs_mods or []):
        # (every nv-rs on the PC: each one started plays its own mods folder)
        look("nv-rs's mods folder (%s)" % os.path.basename(os.path.dirname(nm)), nm, True)
    return found


def stale(*a, **k):
    return [c for c in others(*a, **k) if not c['same']]


def far_view(roots):
    """Far views under these folders (laid out as Data) that the game would draw none of (lodgen.check_folder), as stale
    entries: not a copy to move, but the mod isn't ready while one is there."""
    import lodgen
    out, seen = [], set()
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        for w, why in lodgen.check_folder(root):
            if w.lower() in seen:
                continue
            seen.add(w.lower())
            out.append({'where': 'the far view of %s: %s' % (w, why), 'path': root, 'same': False, 'movable': False, 'far': True})
    return out


def loose_left(built, data_dir):
    """The files an older Put in game left loose in data_dir (install.py's list beside the build): far views, models,
    textures. In a loadout the game draws them beside the mod's own, and far-view blocks named otherwise all at once:
    the old ship stood in the distance after she had moved (18 Nov 2026)."""
    try:
        with open(built + '.files.json', encoding='utf-8') as f:
            names = json.load(f)
    except (OSError, ValueError):
        return []
    return [r for r in names if os.path.isfile(os.path.join(data_dir, r))]


def move_loose(built, data_dir):
    """Every file loose_left finds, into backups/<plugin> loose files from Data <time>/, same paths. Returns how many."""
    if os.environ.get('FOLAB_NO_GAME_WRITES'):
        raise ValueError('This FOLab is a scratch copy for looking at experiments: it may not move files out of the game.')
    left = loose_left(built, data_dir)
    back = os.path.join(os.path.dirname(project.PROJECTS_DIR), 'backups', '%s loose files from Data %s' % (os.path.basename(built), time.strftime('%Y-%m-%d %H%M%S')))
    for r in left:
        dest = os.path.join(back, r)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.move(os.path.join(data_dir, r), dest)
    for d in sorted({os.path.dirname(r) for r in left}, key=len, reverse=True):
        p = os.path.join(data_dir, d)
        while d and os.path.normcase(p) != os.path.normcase(data_dir):
            try:
                os.rmdir(p)
            except OSError:
                break
            p = os.path.dirname(p)
    return len(left)


def move_out(paths, plugin):
    """Move each stale copy into backups/<plugin> old copies <time>/<n>/; returns where they went."""
    if os.environ.get('FOLAB_NO_GAME_WRITES'):
        raise ValueError('This FOLab is a scratch copy for looking at experiments: it may not move files out of the game.')
    back = os.path.join(os.path.dirname(project.PROJECTS_DIR), 'backups', '%s old copies %s' % (plugin, time.strftime('%Y-%m-%d %H%M%S')))
    moved = []
    for i, p in enumerate(paths):
        if os.path.basename(p).lower() != plugin.lower() or not os.path.isfile(p):
            raise ValueError('Not a copy of %s: %s' % (plugin, p))
        dest = os.path.join(back, str(i + 1))
        os.makedirs(dest, exist_ok=True)
        with open(os.path.join(dest, 'came from.txt'), 'w', encoding='utf-8') as f:
            f.write(p + '\n')
        shutil.move(p, os.path.join(dest, plugin))
        moved.append({'from': p, 'to': os.path.join(dest, plugin)})
    return moved


def everywhere(built, main, main_where, main_path, lo=None, mod_folder=None, nvrs_folders=(), nvrs_chosen=False):
    """Every place the game could load the mod from, each with how it stands: the place FOLab puts it (main: install.status
    or mo2write.status, said as main_where), every nv-rs on the PC, and any other copy that would load instead (others).
    [{where, path, kind: 'main' | 'nv-rs' | 'other', state: 'current' | 'old' | 'off' | 'missing', target, movable}].
    target: Bring everything up to date puts the build there (the main place; an nv-rs when nv-rs is what plays, or when
    it holds a copy already: none is left playing an older build). Another copy is never a target: it goes to backups."""
    plugin = os.path.basename(built)
    rows = []
    st = 'missing' if not main.get('installed') else 'old' if not main.get('current') else 'off' if not main.get('active') else 'current'
    rows.append({'where': main_where, 'path': main_path, 'kind': 'main', 'state': st, 'target': True, 'movable': False})
    for f in nvrs_folders or ():
        p = os.path.join(f, 'mods', plugin)
        there = os.path.isfile(p)
        rows.append({'where': "nv-rs in %s" % f, 'path': p, 'kind': 'nv-rs', 'folder': f,
                     'state': 'missing' if not there else 'current' if _same(p, built) else 'old',
                     'target': bool(nvrs_chosen or there), 'movable': False})
    for c in others(built, lo, mod_folder):
        if c['same'] and not c.get('loose'):
            continue                        # (the very same bytes elsewhere: harmless)
        rows.append(dict(c, kind='other', state='old', target=False))
    return rows
