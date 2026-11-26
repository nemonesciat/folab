"""wreckhints: each wreck told once, words fit a terminal, no game model's name shown."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
import wreckhints as H   # noqa: E402

W = [{'name': n, 'model': m, 'p': [x, y, -d], 'depth': d} for n, m, x, y, d in (
    ('bomber', 'SunkenB29', 94720, 97792, 1304), ('barge', 'dlc04bargeozymandias', -42496, 225792, 1072),
    ('fishing boat', 'Boat01a', -114176, -27136, 912), ('fishing boat', 'Boat01b', -94720, -43520, 1008),
    ('fishing boat', 'Boat01d', -12800, -43520, 896))]
MARKS = [('Blue Lagoon', 91232, 73728), ("Kane'ohe", -64359, 195583), ('Battery Randolph', -102976, -25344),
         ('Waikiki Natatorium', -84672, -45888), ('Makai Tower', -9696, -31520)]


def test_each_told_once():
    told = H.assign(W, MARKS)
    assert sorted(i for _s, i in told) == list(range(len(W)))
    assert len({s for s, _i in told}) == len(W)            # (one a source while there are sources enough)


def test_words():
    for s, i in H.assign(W, MARKS):
        title, said = H.words(s, W[i], MARKS)
        text = title + said
        assert 'B29' not in text and 'ozymandias' not in text.lower() and 'Boat0' not in text
        text.encode('cp1252')
        if s != 'notebook':
            assert all(len(l) <= 92 for l in said.split('\n')), said


def test_plain():
    assert [n for pat, n in H.PLAIN if __import__('re').search(pat, 'SunkenB29')][0] == 'bomber'


if __name__ == '__main__':
    for f in (test_each_told_once, test_words, test_plain):
        f()
    print('ok')
