"""Whether the game's exe may use 4 GB or only 2 (playtest.memory_room): one flag in its header, read from made-up
exes in a temporary folder. Nothing here goes near the real game."""
import os
import struct
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import playtest  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


top = tempfile.mkdtemp(prefix='folab-mem-')
data = os.path.join(top, 'Data')
os.makedirs(data)
exe = os.path.join(top, 'FalloutNV.exe')


def make(flags, pe=0x108):
    head = bytearray(1024)
    head[:2] = b'MZ'
    struct.pack_into('<I', head, 0x3C, pe)
    head[pe:pe + 4] = b'PE\0\0'
    struct.pack_into('<H', head, pe + 22, flags)
    with open(exe, 'wb') as f:
        f.write(head)


check('no exe: it can\'t tell', playtest.memory_room(data)['big'] is None)
make(0x0102)
check('the game as it ships stops at 2 GB', playtest.memory_room(data)['big'] is False)
make(0x0122)
check('with the patch\'s flag it may use 4', playtest.memory_room(data)['big'] is True)
make(0x0122, pe=0x80)
check('wherever the header is', playtest.memory_room(data)['big'] is True)
with open(exe, 'wb') as f:
    f.write(b'not a program at all')
check('a file that isn\'t a program: it can\'t tell', playtest.memory_room(data)['big'] is None)
check('it names the patch\'s page and fetches nothing', playtest.memory_room(data)['page'].startswith('https://www.nexusmods.com/'))
before = open(exe, 'rb').read()
playtest.memory_room(data)
check('the exe is only read', open(exe, 'rb').read() == before)
