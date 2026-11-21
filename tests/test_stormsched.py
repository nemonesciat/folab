"""stormsched: the storm script's own text run over game days, with waits, sleeps and other worlds; the rules held."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app'))
import stormsched as S


def test_schedule_keeps_its_rules():
    g, s, sm = S.run(S.REAL, days=12, fps=1, seed=5)
    sp = S.spells(sm)
    assert [m for _a, _b, m in sp].count(2) >= 1, sp
    assert [m for _a, _b, m in sp].count(1) >= 3, sp
    assert S.check(sm) == [], S.check(sm)
    assert 0.6 < S.fair_share(sm) < 0.9, S.fair_share(sm)
    big = [b for b in sp if b[2] == 2 and b is not sp[-1]]
    assert all(abs((b - a) * 24 - 31) < 0.2 for a, b, _m in big), big


def test_other_worlds_waits_and_sleeps():
    ev = [(0.40, ('go', 'mojave')), (0.45, ('go', 'island')), (0.50, ('go', 'view')), (0.55, ('go', 'inside')),
          (0.60, ('go', 'island')), (0.65, ('sleep', 12))]
    g, s, sm = S.run(S.TEST, days=1.5, fps=1, events=ev, seed=3)
    log = [(round(t - 10, 3), w, x) for t, w, x in g.log]
    at = lambda t0, t1: [(w, x) for t, w, x in log if t0 <= t < t1]
    assert ('releaseweatheroverride', None) in at(0.40, 0.41)          # (the Mojave: the storm let go)
    assert ('disable', 'sheets') in at(0.40, 0.41)
    assert ('forceweather', 'FOLabStormWeather') in at(0.45, 0.46)     # (back: given at once)
    assert ('disable', 'sheets') in at(0.50, 0.51)                     # (a hotel's small world: none on you)
    assert ('enable', 'fury') in at(0.60, 0.61)                        # (the peak)
    woke = at(1.15, 1.16)                                              # (asleep through the peak: only where it ended up)
    assert ('setweather', 'NVDLC02TheNarrowsWeather') in woke and ('enable', 'fury') not in woke, woke
    assert not [x for w, x in woke if w == 'setweather' and x != 'NVDLC02TheNarrowsWeather'], woke


def test_script_reads_as_the_game_does():
    text = S.script_source(S.REAL)
    lines = [l.strip().lower() for l in text.splitlines()]
    assert 'GetInWorldspace FOLabWaikiki' in text
    assert sum(l.startswith('if ') for l in lines) == sum(l == 'endif' for l in lines)
    s = S.Script(text)
    assert {'sheets', 'scud', 'fury', 'squall'} <= s.refs


if __name__ == '__main__':
    for n, f in list(globals().items()):
        if n.startswith('test_'):
            f()
            print('ok', n)
