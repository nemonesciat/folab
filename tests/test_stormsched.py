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


def _changes(g):
    out, prev = [], None
    for d, sh, w in g.flags:
        if (sh, w) != prev:
            out.append((d - 10, sh, w))
            prev = (sh, w)
    return out


def test_what_a_storm_leaves():
    text = S.script_source(S.REAL, wrack='FOLabStormWrack', shelter='FOLabStormShelter')
    # (the variables stay where they were: a save from before keeps its values)
    old = [l for l in S.script_source(S.REAL).splitlines() if l.startswith(('ref ', 'short ', 'float '))]
    new = [l for l in text.splitlines() if l.startswith(('ref ', 'short ', 'float '))]
    assert new[:len(old)] == old and new[len(old):] == ['short wrack', 'float wrackgone'], new
    # out on the island the whole time: shelter only through the storm, wrack from its second half to a day or two after
    g, s, sm = S.run(S.REAL, days=14, fps=1, seed=5, text=text)
    sp = [b for b in S.spells(sm) if b[2] == 2]
    ch = _changes(g)
    for a, b, _m in sp[:-1]:
        a, b = a - 10, b - 10
        on = [d for d, sh, _w in ch if sh == 1 and a <= d <= b]
        off = [d for d, sh, _w in ch if sh == 0 and a <= d <= b + 0.01]
        assert on and abs((on[0] - a) * 24 - 6) < 0.1, (a, ch)              # (from the building step, 6 h in)
        assert off and abs((off[0] - a) * 24 - 23) < 0.1, (a, ch)           # (to the storm's end, 23 h in)
        laid = [d for d, _sh, w in ch if w == 1 and a <= d <= b]
        assert laid and abs((laid[0] - a) * 24 - 17) < 0.1, (a, ch)        # (the second half of the storm)
        gone = [d for d, _sh, w in ch if w == 0 and d > laid[0]]
        assert gone and 1.0 + 14 / 24 + 1.0 - 0.01 <= gone[0] - laid[0] <= 2.0 + 14 / 24 + 1.0 + 0.01, (laid, gone)
    # asleep through a whole storm, then off to the Mojave: the wrack is laid all the same, taken up while away
    text = S.script_source(S.TEST, wrack='FOLabStormWrack', shelter='FOLabStormShelter')
    g, s, sm = S.run(S.TEST, days=4, fps=1, seed=3, text=text, events=[(0.01, ('sleep', 40)), (1.8, ('go', 'mojave'))])
    ch = _changes(g)
    assert any(w == 1 for _d, _sh, w in ch), ch
    assert ch[-1][2] == 0 and ch[-1][1] == 0, ch
    assert 1.8 <= [d for d, _sh, w in ch if w == 0][-1] <= 3.8, ch
    assert not [d for d, sh, _w in ch if sh == 1 and d > 1.0], ch            # (no shelter flag left up after the storm)


def test_fair_weather_keeps_a_sunny_sky():
    import gamedata
    gd = gamedata.GameData()

    class P:
        records = {}
    keys = {e: gd.key(S._game_form(gd, 'WTHR', e)) for e in ('NVDLC02ZionValleyWeather', 'NVDLC02ZVRainWeather', 'NVDLC02TheNarrowsWeather')}
    assert S._pleasant(gd, P, keys['NVDLC02ZionValleyWeather'])       # (filed as cloudy, kind 2: still a sunny day)
    assert S._pleasant(gd, P, keys['NVDLC02TheNarrowsWeather'])
    assert not S._pleasant(gd, P, keys['NVDLC02ZVRainWeather'])


if __name__ == '__main__':
    for n, f in list(globals().items()):
        if n.startswith('test_'):
            f()
            print('ok', n)
