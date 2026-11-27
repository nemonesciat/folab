"""placehints: the words fit the game's font and terminals; an entry is spliced before a terminal's cache item."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import placehints as H     # noqa: E402


def test_words():
    assert H.words_ok() == []
    for part, ents in H.ENTRIES.items():
        assert part in H.MARKERS
        for site, title, words, mi in ents:
            assert 0 <= mi < len(H.MARKERS[part]) and title and words.strip()
    assert '{dist}' in H.NOTE_WORDS and '{dir}' in H.NOTE_WORDS


def test_items_split():
    z = lambda t, v: {'tag': t, 'value': v}
    rec = {'type': 'TERM', 'subs': [z('EDID', 'X'), z('DESC', 'hi'), z('ITXT', 'A'), z('RNAM', 'a'),
                                    z('ITXT', 'Open the safe'), z('SCTX', 'FOLabSafeREF.Unlock'), z('ITXT', 'B')]}
    head, items = H._items_of(rec['subs'])
    assert [s['tag'] for s in head] == ['EDID', 'DESC'] and [H._text(i) for i in items] == ['A', 'Open the safe', 'B']
    assert [H._unlocks(i) for i in items] == [False, True, False]
    assert H.has_entry(rec, 'B') and not H.has_entry(rec, 'C')


def test_dir():
    assert H._dir((0, 0), (0, 100)) == 'north' and H._dir((0, 0), (-100, 100)) == 'north-west'


if __name__ == '__main__':
    for f in (test_words, test_items_split, test_dir):
        f()
    print('ok')
