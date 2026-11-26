"""loreterminals: every terminal's text reads, fits the game's font, and each area gets three or four."""
import collections
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
import loreterminals as L   # noqa: E402
import terminals            # noqa: E402


def test_texts_read():
    edids = set()
    for key, S in L.SITES.items():
        spec = terminals.plan(L.text_of(key).replace('{cache}', 'XREF'))
        assert spec['edid'].startswith('FOLabLore'), key
        assert spec['edid'] not in edids, key
        edids.add(spec['edid'])
        assert 2 <= len(spec['items']) <= 5, key
        S['text'].encode('cp1252')                    # (the game's terminal font: no okina, no macrons)
        for it in spec['items']:
            for line in (it['says'] or '').split('\n'):
                assert len(line) <= 92, (key, line)
        opens = terminals.unlocks(spec)
        assert bool(opens) == bool(S['cache']), key


def test_areas():
    n = collections.Counter(S['area'] for S in L.SITES.values())
    assert sorted(n) == [1, 2, 3, 4, 5, 6]
    assert all(3 <= v <= 4 for v in n.values()), n


def test_caches_named_once():
    names = [S['cache'][0] for S in L.SITES.values() if S['cache']]
    assert len(names) == len(set(names)) and len(names) >= 6


if __name__ == '__main__':
    for f in (test_texts_read, test_areas, test_caches_named_once):
        f()
    print('ok')
