"""The tools for looking after a mod and sharing it, behind one hook in server.py: /api/tools/<name>.

Each tool is a module of its own (health.py, loadorder.py...); this only routes. S is the server module: S.GD, S.PR,
S.edit..."""
import os

import adopt
import changes
import gametest
import conflicts
import health
import loadorder
import merge
import release


def need_mod(S):
    if not S.PR:
        raise ValueError('Open or start a mod first.')


def plugin_list(S):
    """The plugins a look can be taken at: the mods in the Data folder."""
    return {'plugins': adopt.candidates(S.GD.data_dir), 'mod': S.PR.plugin if S.PR else None}


def get(name, q, S):
    if name.startswith('gametest/'):
        return gametest.get(name[9:], q, S)
    if name == 'health':
        if q.get('file'):
            return health.check_file(S.GD, os.path.join(S.GD.data_dir, os.path.basename(q['file'])))
        need_mod(S)
        out = health.check_mod(S)
        out['conflicts'] = conflicts.short()
        return out
    if name == 'plugins':
        return plugin_list(S)
    if name == 'loadorder':
        return loadorder.read(S.GD.data_dir, S.PR.plugin if S.PR else None)
    if name == 'loadorder/conflicts':
        return loadorder.conflicts(S.GD.data_dir)
    if name == 'loadorder/wins':
        return loadorder.who_wins(S.GD.data_dir, q['key'], S.GD)
    if name == 'conflicts/status':
        return conflicts.status()
    if name == 'conflicts/compare':
        return conflicts.compare_last(S.GD.data_dir, q['key'])
    if name == 'changes':
        need_mod(S)
        return changes.everything(S)
    if name == 'changes/diff':
        need_mod(S)
        return changes.record_diff(S, q['key'])
    if name == 'changes/plugin':
        need_mod(S)
        return changes.plugin_contents(S)
    if name == 'changes/plugindiff':
        need_mod(S)
        return changes.plugin_diff(S, q['key'])
    if name == 'release':
        need_mod(S)
        return release.info(S)
    if name == 'merge':
        need_mod(S)
        return merge.info(S)
    raise FileNotFoundError(name)


def post(name, body, S):
    if name.startswith('gametest/'):
        return gametest.post(name[9:], body, S)
    if name == 'health/fix':
        need_mod(S)
        return health.apply_fixes(S, body.get('fixes') or [])
    if name == 'conflicts/start':
        return conflicts.start(S, body.get('file') or None)
    if name == 'conflicts/move':
        S.not_while_playing()
        out = conflicts.move(S.GD.data_dir, body['plugin'], body['after'])
        out['state'] = S.state()
        return out
    if name == 'loadorder/save':
        S.not_while_playing()
        out = loadorder.save(S.GD.data_dir, body['order'], body['active'])
        out['state'] = S.state()
        return out
    if name == 'loadorder/restore':
        S.not_while_playing()
        return loadorder.restore(S.GD.data_dir, body['name'])
    if name == 'loadorder/sorted':
        return loadorder.sorted_for_masters(S.GD.data_dir, body['order'], body['active'])
    need_mod(S)
    if name == 'release/info':
        return release.save_info(S, body)
    if name == 'release/clean':
        return release.clean(S)
    if name == 'release/pack':
        return release.package(S, body.get('replacing', True))
    if name == 'release/folder':
        os.makedirs(release.releases_dir(), exist_ok=True)
        os.startfile(release.releases_dir())
        return {'ok': True}
    if name == 'merge/preview':
        return merge.preview(S, body)
    if name == 'merge/go':
        S.not_while_playing()
        return merge.merge(S, body, body.get('prefer'))
    if name == 'merge/restore':
        return merge.restore(S, body['name'])
    if name == 'merge/trim':
        return merge.trim_masters(S)
    raise FileNotFoundError(name)
