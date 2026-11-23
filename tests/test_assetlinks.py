import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
"""nv-rs's mods folder holds hard links to the build's files (nvrs.put_in). Nothing FOLab writes may reach the game
through them before the mod is put in again: a Save (library.publish) and every writer of a mod's files put a new file
in place of the old instead of writing into it (install.write_new / copy_new), so the game keeps its copy until put_in
links the new one. 22 Nov 2026: new distant blocks and models went live in the user's game at a Save, beside an
older Waikiki.esp."""
import struct
import install
import library
import nvrs
import plugintree
import project


def check(what, ok, more=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % more if more and not ok else ''))


class Mod:
    name, plugin = 'Link Test', 'Link Test.esp'


pr = Mod()
os.environ.pop('FOLAB_NO_GAME_WRITES', None)
game = os.path.join(project.HOME, 'nv-rs')                  # (a pretend nv-rs, on the same drive: its files are links)
os.makedirs(os.path.join(game, 'mods'))
built = os.path.join(project.BUILD_DIR, pr.plugin)
os.makedirs(project.BUILD_DIR, exist_ok=True)
with open(built, 'wb') as f:
    f.write(plugintree.Plugin.empty(b'HEDR' + struct.pack('<HfiI', 12, 1.34, 0, 0x800)).bytes())
rel = os.path.join('meshes', 'linktest', 'thing.nif')
mine = os.path.join(library.assets_dir(pr), rel)
there = os.path.join(game, 'mods', rel)
read = lambda p: open(p, 'rb').read()

library._put(library.assets_dir(pr), rel, b'first')
library.publish(pr)
nvrs.put_in(game, [built])
check('put in: the game\'s file is a link to the build\'s', os.path.samefile(there, os.path.join(library.built_dir(pr), rel)))

library._put(library.assets_dir(pr), rel, b'second, longer')
check('rewritten among the mod\'s own files: the game\'s copy as it was', read(there) == b'first')
library.publish(pr)
check('a Save (publish): the build has it new', read(os.path.join(library.built_dir(pr), rel)) == b'second, longer')
check('… and the game\'s copy is still the old one, until it is put in', read(there) == b'first')

install.write_new(os.path.join(library.built_dir(pr), rel), b'third')
check('written in the build\'s folder itself (write_new): the game\'s copy unchanged', read(there) == b'first')
library.publish(pr)                                         # (the mod's own file is newer: the build goes back to it)

nvrs.put_in(game, [built])
check('put in again: the game has the new file', read(there) == read(mine) == b'second, longer')
check('… linked to the build\'s again', os.path.samefile(there, os.path.join(library.built_dir(pr), rel)))
check('no temporary files left behind', not any(n.endswith('.folab-tmp') for _d, _s, fs in os.walk(project.HOME) for n in fs))
