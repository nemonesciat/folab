import os, sys, threading, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
"""A place opening asks for hundreds of files at once, on the server's threads. In a Mod Organizer loadout the first asker made
the list of archives while the others read it part made, and a file in an archive not reached yet came back as missing: the
place's corridors, first in line, went invisible until FOLab was closed."""
import gamedata


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' ' + str(detail) if detail and not ok else ''))


G = gamedata.GameData()
paths = [a.path for a in G.archives()]
path = 'meshes\\dungeons\\vault\\hallsmall\\vhallsm1way01.nif'
check('the corridor piece is in the game\'s archives', bool(G.read_file(path)))


class SlowView:
    """A loadout's virtual folder that takes its time, so the threads below all arrive while the list is being made."""
    def archives_like(self, pattern):
        time.sleep(0.05)
        return paths if pattern.startswith('fallout') else []

    def path(self, rel):
        return None


G.view = SlowView()
G._archives = None
wrong, seen = [], []
start = threading.Barrier(16)


def ask():
    start.wait()
    try:
        G.read_file(path)
        seen.append(len(G.archives()))
    except Exception as e:
        wrong.append(repr(e))


threads = [threading.Thread(target=ask) for _ in range(16)]
for t in threads:
    t.start()
for t in threads:
    t.join()
check('every thread asking at once finds the file, in a loadout', not wrong, wrong[:2])
check('and they all see the whole list of archives', set(seen) == {len(set(paths))}, set(seen))
