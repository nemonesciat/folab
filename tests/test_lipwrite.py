"""Lip files (lipwrite.py): a sample of the game's own .lip files read and written back byte for byte (the full proof
over every one is `py -3 app/lipwrite.py`), the header's size and flags as the game's, and a lip made from timed speech
sounds opening the mouth in the right shapes at the right frames."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import bsa  # noqa: E402
import gamedata  # noqa: E402
import lipwrite as L  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


def main():
    a = bsa.Archive(os.path.join(gamedata.find_data_dir(), 'Fallout - Voices1.bsa'))
    lips = sorted(p for p in a.files if p.endswith('.lip'))[::200]
    same, starts = 0, set()
    for p in lips:
        data = a.read(p)
        lip = L.read(data)
        starts.add(lip.start)
        same += L.write(lip) == data
    a.close()
    check('game lip files written back byte for byte', same == len(lips), '%d of %d' % (same, len(lips)))
    check('starting frames never after the start', max(starts) <= 0 and L.START in starts, sorted(starts)[:3])

    tl = [('HH', 0.0, 0.08), ('AH', 0.08, 0.2), ('L', 0.2, 0.28), ('OW', 0.28, 0.5), ('sil', 0.5, 0.7)]
    lip = L.from_timeline(tl)
    check('one frame a thirtieth of a second', len(lip.frames) == 21, len(lip.frames))
    oh = L.PHONEMES.index('Oh')
    at = [f[0][oh] for f in lip.frames]
    check('Oh strongest in its own time', max(range(len(at)), key=at.__getitem__) in range(9, 15), at)
    check('mouth shut in the silence', max(lip.frames[-1][0]) == 0.0)
    check('eases in from before the first sound', lip.start == -L.LEAD_IN, lip.start)
    again = L.read(L.write(lip))
    check('a made lip reads back', len(again.frames) == 21 and abs(again.frames[11][0][oh] - at[11]) < 1e-6)
    check('IPA split into sounds', L.ipa_sounds('həlˈoʊ') == ['h', 'ə', 'l', 'o', 'ʊ'],
          ascii(L.ipa_sounds('həlˈoʊ')))


main()
