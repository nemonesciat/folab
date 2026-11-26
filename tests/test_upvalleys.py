"""upvalleys: every line's topics and words are there, the scripts read, every quest has its ways through, the leads climb."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
import upvalleys as U   # noqa: E402


def test_lines():
    L = U.lines_spec()
    assert len(L) >= 50
    for who, quest, topic, w, conds, end, skill, choices, bye in L:
        assert who in U.PEOPLE or who in U.THEIRS, who
        assert quest in U.QUESTS
        assert topic == 'G' or topic in U.TOPICS, topic
        assert w in U.W or w in U.M, w
        for c in choices:
            assert c in U.TOPICS, c
        U.words(w).encode('cp1252', 'strict') if w in U.W else None
        for c in conds:
            if c[0] == 'q':
                assert c[2] in U.VARS[c[1]], c
            if c[0] == 'skill':
                assert c[1] in U.AVI, c


def test_every_topic_has_a_line():
    used = {l[2] for l in U.lines_spec()}
    assert set(U.TOPICS) <= used, set(U.TOPICS) - used


def test_ways_through():
    ends = {l[5] for l in U.lines_spec()}
    # the beacon: lit three ways, reported, left dark, caught lying
    for v in ('lit 1', 'lit 2', 'lit 3', 'reported', 'broken', 'caught'):
        assert any(('FOLabUVDarkBeacon.' + v.split()[0] + ' to ' + (v.split()[1] if ' ' in v else '1')) in e for e in ends), v
    # the count: paid, talked, threatened; truth, lie, tally
    for how in (1, 2, 3):
        assert any('FOLabUVTheCount.how to %d' % how in e for e in ends), how
    for a in (1, 2, 3):
        assert any('FOLabUVTheCount.answered to %d' % a in e for e in ends), a
    # the glass: both, glass only, sold
    for v in ('gavebook to 1', 'gavebook to 2', 'sold to 1'):
        assert any('FOLabUVNavigatorsGlass.' + v in e for e in ends), v


def test_scripts_shape():
    for src in (U.beacon_script(), U.count_script(), U.glass_script('A', 'B'),
                U.leads_script({n: 'c%d' % n for n in range(1, 5)}, {n: 'k%d' % n for n in range(1, 5)},
                               {n: 'm%d' % n for n in range(1, 5)}, {n: ('x', 'y') for n in range(1, 5)})):
        lines = src.split('\n')
        assert lines[0].startswith('scn ') and 'End' in lines
        assert sum(l.strip().startswith('if ') for l in lines) == sum(l.strip() == 'endif' for l in lines)


def test_leads():
    assert len(U.LEADS) == 4 and sorted(L['n'] for L in U.LEADS.values()) == [1, 2, 3, 4]
    for L in U.LEADS.values():
        L['clue']['words'].encode('cp1252')
        for line in L['entry'][1].strip('\n').split('\n'):
            assert len(line.strip()) <= 92, line


def test_mandarin():
    import re
    for k, (en, py) in U.M.items():
        assert en and py and not re.search(r'[一-鿿]', py), k

def test_mandarin_pieces():
    # every Mandarin piece is a sentence pair (shown and said), each within a subtitle unless one sentence is longer;
    # nobody of ours has a name taken by another speaker of the mod (the story session's gate)
    U._zh()
    for k in U.M:
        parts = U.zh_parts(k)
        assert len(parts) >= 1 and all(t in U.ZH and U.ZH[t] == z for t, z in parts), k
        assert ' '.join(t for t, _z in parts) != U.shown(k) or len(parts) == 1, k
        assert all(len(t) <= 150 for t, _z in parts) or len(parts) == 1, k
    names = [v[1] for v in U.PEOPLE.values()]
    assert 'Fang Jun' not in names and not any(n.split()[0] == 'Leilani' for n in names)


if __name__ == '__main__':
    for f in (test_lines, test_every_topic_has_a_line, test_ways_through, test_scripts_shape, test_leads, test_mandarin, test_mandarin_pieces):
        f()
    print('ok')
