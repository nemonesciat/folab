"""Opening an existing plugin (.esp or .esm) as your mod.

The plugin is copied into FOLab's projects folder and loaded on top of the game, so everything in it shows and can be
edited like the game's own things. Saving starts from that copy, every group and record of it kept as it was, with
your changes laid over it, and keeps its masters in their order; anything else your changes use is added after them,
every link in the file re-pointed (masterlist.py). A mod it needs is loaded under it. Saved untouched, it comes out the
same file. Put in game writes it back where it came from, a copy of the old one going to backups first."""
import json
import os
import shutil

import gamedata
import project
import loadout
import tes4


def candidates(data_dir):
    """Plugins in the game's Data folder that aren't the game's own."""
    out = []
    official = {n.lower() for n in gamedata.OFFICIAL}
    for fn in loadout.plugin_names(data_dir):
        if fn.lower() not in official:
            p = loadout.plugin_path(data_dir, fn)
            try:
                h = tes4.PluginFile(p).header
            except (ValueError, OSError) as e:
                out.append({'file': fn, 'error': str(e)})
                continue
            out.append({'file': fn, 'masters': h['masters'], 'author': h['author'], 'records': h['records'],
                        'size': os.path.getsize(p)})
    return out


def check(gd, path):
    """Why a plugin can't be opened here, or None."""
    name = os.path.basename(path)
    if name.lower() in gd.names:
        return '%s is one of the files already loaded: FOLab can only open mods.' % name
    try:
        h = tes4.PluginFile(path).header
    except (ValueError, OSError) as e:
        return 'Not a plugin FOLab can read: %s' % e
    folder = os.path.dirname(path)
    missing = [m for m in h['masters'] if m.lower() not in gd.names and not os.path.isfile(loadout.plugin_path(gd.data_dir, m))
               and not os.path.isfile(os.path.join(folder, m))]
    if missing:
        return '%s needs %s, which isn\'t in the game\'s Data folder.' % (name, ', '.join(missing))
    return None


def extra_masters(data_dir, path):
    """The mods a plugin needs loaded under it: its masters that aren't the game's, and theirs, those first."""
    official = {n.lower() for n in gamedata.OFFICIAL}
    out, seen = [], set()

    def visit(p):
        pf = tes4.PluginFile(p)
        masters = list(pf.header['masters'])
        pf.close()
        for m in masters:
            q = loadout.plugin_path(data_dir, m)
            if m.lower() in official or m.lower() in seen or not os.path.isfile(q):
                continue
            seen.add(m.lower())
            visit(q)
            out.append(q)
    visit(path)
    return out


def adopt(gd, path):
    """Make a project from a plugin; returns the project's name."""
    why = check(gd, path)
    if why:
        raise ValueError(why)
    fn = os.path.basename(path)
    pname = project.safe_name(os.path.splitext(fn)[0])
    folder = pname + ' source'
    os.makedirs(os.path.join(project.PROJECTS_DIR, folder), exist_ok=True)
    shutil.copy2(path, os.path.join(project.PROJECTS_DIR, folder, fn))
    pf = tes4.PluginFile(os.path.join(project.PROJECTS_DIR, folder, fn))
    h = pf.header
    own = len(h['masters'])
    # new things get IDs after every one the plugin already has (its header's "next ID" can't be trusted: Dead Money's
    # says 0xFF0148C4)
    highest = max([r.formid & 0xFFFFFF for r, _g in pf.walk() if r.formid >> 24 == own] or [0])
    pf.close()
    next_id = max(project.FIRST_ID, highest + 1)
    with open(os.path.join(project.PROJECTS_DIR, pname + '.json'), 'w', encoding='utf-8') as f:
        json.dump({'name': pname, 'plugin': fn, 'author': h['author'], 'description': h['description'],
                   'cells': {}, 'records': {}, 'next_id': next_id, 'source': folder + '/' + fn,
                   'esm': bool(h['flags'] & 1), 'opened_from': path}, f, indent=1)
    return pname
