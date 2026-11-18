"""What a recording made by 'Measure the game.cmd' says about the game: its threads and how busy each kept a core,
its frames, and where its time went (functions named from fnv_decomp's list through gamenames.py).

    py -3 -I tools/measure/analyze.py <recording.etl> [report.txt]
"""
import collections
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import etlread  # noqa: E402
import gamenames  # noqa: E402

GAME = 'falloutnv.exe'
D3D9 = '783aca0a-790e-4d7f-8451-aa850511c6b9'
IMAGE, THREAD, PERF, STACK, HEADER = 20, 5, 15, 24, 0


MODULE_PARTS = [('d3d9', 'drawing: Direct3D and the graphics driver'), ('nvd3d', 'drawing: Direct3D and the graphics driver'),
                ('aticfx', 'drawing: Direct3D and the graphics driver'), ('amdxx', 'drawing: Direct3D and the graphics driver'),
                ('d3dx9', 'drawing: Direct3D and the graphics driver'), ('dsoal', 'sound'), ('dsound', 'sound'),
                ('vorbis', 'sound'), ('nvse', 'xNVSE and its plugins'), ('jip', 'xNVSE and its plugins'),
                ('nvtf', 'xNVSE and its plugins'), ('stewie', 'xNVSE and its plugins'), ('johnny', 'xNVSE and its plugins'),
                ('overlay', 'Steam overlay'), ('steam', 'Steam overlay')]
# by the function's name and source file (fnv_decomp's), first match wins
PARTS = [
    (('cull', 'classifypoint', 'classifysphere', 'occlu', 'portal', 'roomnode', 'bsmultibound'), 'culling: working out what is in view'),
    (('shadow',), 'shadows'),
    (('water',), 'water'),
    (('decal',), 'decals'),
    (('renderer', 'nid3d', 'shader', 'bsbatch', 'render', 'passstate', 'texture', 'd3d', 'geometry', 'skinpartition',
      'niconsole', 'blk_00e8', 'blk_00e9', 'blk_00b7', 'blk_00b8', 'blk_00b9', 'imagespace'), 'drawing: preparing what to draw'),
    (('ninode', 'niavobject', 'nitransform', 'nimatrix', 'downwardpass', 'updateworld', 'nipoint', 'nibound', 'nicontroller',
      'interpolator', 'timeline', 'animat', 'bsanim', 'nicontrollermanager', 'nikeyframe'), 'scene update: moving models and animation'),
    (('hkp', 'hk', 'bhk', 'havok', 'collision', 'ragdoll', 'charactercontroller'), 'physics (Havok)'),
    (('process', 'actor', 'pathing', 'navmesh', 'ai', 'package', 'combat', 'detection', 'character', 'creature', 'npc',
      'movement'), 'AI and actors'),
    (('script', 'tesscript', 'effectitem', 'activeeffect', 'magic', 'quest'), 'scripts and effects'),
    (('audio', 'sound', 'music'), 'sound'),
    (('modelloader', 'queuedfile', 'bsfile', 'archive', 'loader', 'bsa', 'threadsafe', 'taskmanager', 'iomanager',
      'queued'), 'loading models and files'),
    (('memorypool', 'heap', 'memory', 'alloc'), 'memory'),
    (('menu', 'hud', 'tile', 'interface', 'ui'), 'menus and HUD'),
    (('cell', 'grid', 'land', 'tesworld', 'tesobjectrefr', 'tesform', 'extradata', 'bgsprimitive', 'xgamesetting'),
     'world: cells, references, forms'),
]


def wstr(b, off):
    end = off
    while end + 1 < len(b) and (b[end] or b[end + 1]):
        end += 2
    return bytes(b[off:end]).decode('utf-16-le', 'replace')


class Modules:
    def __init__(self):
        self.rows = []

    def add(self, base, size, name):
        self.rows.append((base, base + size, name))

    def done(self):
        self.rows.sort()
        self.starts = [r[0] for r in self.rows]

    def find(self, a):
        import bisect
        i = bisect.bisect_right(self.starts, a) - 1
        if i >= 0 and a < self.rows[i][1]:
            return self.rows[i]
        return None


def first_pass(path):
    freq = None
    mods = collections.defaultdict(Modules)
    threads = {}    # tid -> (pid, start address)
    game = set()
    presents = collections.defaultdict(list)
    names = {}
    for ev in etlread.events(path):
        if ev.kind == 'k':
            if ev.group == HEADER and ev.type == 0 and freq is None and len(ev.payload) >= 264:
                freq, = struct.unpack_from('<q', ev.payload, 256)
            elif ev.group == IMAGE and ev.type in (3, 10) and len(ev.payload) > 56:
                base, size, pid = struct.unpack_from('<QQI', ev.payload, 0)
                name = wstr(ev.payload, 56)
                mods[pid].add(base, size, name)
                if os.path.basename(name).lower() == GAME:
                    game.add(pid)
                    names[pid] = name
            elif ev.group == THREAD and ev.type in (1, 3) and len(ev.payload) >= 56:
                pid, tid = struct.unpack_from('<II', ev.payload, 0)
                start, = struct.unpack_from('<Q', ev.payload, 48)
                threads.setdefault(tid, (pid, start))
        elif ev.kind == 'e' and ev.provider == D3D9 and ev.id == 1:
            presents[ev.pid].append(ev.time)
    for m in mods.values():
        m.done()
    return freq, mods, threads, game, presents, names


def second_pass(path, game, threads, window=None):
    samples = {}                       # (tid, time) -> ip, for the game's threads
    per_thread = collections.Counter()
    all_samples = collections.Counter()
    stacks = {}
    run = collections.Counter()        # tid -> ticks on a core (from switches)
    last = {}                          # cpu -> (time, tid)
    span = [None, None]
    game_tids = {t for t, (p, _s) in threads.items() if p in game}
    for ev in etlread.events(path, want=lambda k, g, t: k == 'k' and g in (PERF, STACK, THREAD)):
        if ev.group == PERF and ev.type == 46:
            ip, tid = struct.unpack_from('<QI', ev.payload, 0)
            all_samples[ev.cpu] += 1
            if tid in game_tids:
                samples[(tid, ev.time)] = ip
                per_thread[tid] += 1
            span[0] = ev.time if span[0] is None else min(span[0], ev.time)
            span[1] = ev.time if span[1] is None else max(span[1], ev.time)
        elif ev.group == STACK and ev.type == 32:
            ts, pid, tid = struct.unpack_from('<QII', ev.payload, 0)
            if pid in game and (tid, ts) in samples:
                n = (len(ev.payload) - 16) // 8
                stacks[(tid, ts)] = struct.unpack_from('<%dQ' % n, ev.payload, 16)
        elif ev.group == THREAD and ev.type == 36:
            new, old = struct.unpack_from('<II', ev.payload, 0)
            prev = last.get(ev.cpu)
            if prev and prev[1] in game_tids and (window is None or window[0] <= prev[0] <= window[1]):
                run[prev[1]] += ev.time - prev[0]
            last[ev.cpu] = (ev.time, new)
    return samples, per_thread, all_samples, stacks, run, span


def main(path, out=None):
    lines = []

    def say(s=''):
        lines.append(s)
        print(s)

    freq, mods, threads, game, presents, names = first_pass(path)
    if not game:
        say('FalloutNV.exe is not in this recording.')
        return
    freq = freq or 10_000_000
    shown = sorted(t for p in game for t in presents.get(p, []))
    window = (shown[0], shown[-1]) if len(shown) > 2 else None
    samples, per_thread, all_samples, stacks, run, span = second_pass(path, game, threads, window)
    secs = (span[1] - span[0]) / freq
    cpus = len(all_samples)
    gp = sorted(presents.get(max(game), []))
    if len(game) == 1 and len(gp) > 2:
        secs = (gp[-1] - gp[0]) / freq    # the time the game was showing frames (the rest is the recorder stopping)
    gn = gamenames.GameNames()
    pid = max(game, key=lambda p: sum(per_thread[t] for t, (pp, _s) in threads.items() if pp == p))
    m = mods[pid]

    def where(a):
        hit = m.find(a)
        if not hit:
            return 'kernel / unknown' if a >= 0x7ff000000000 else '?'
        mod = os.path.basename(hit[2])
        if mod.lower() == GAME:
            return gn.at(a) or 'FalloutNV.exe @%08x' % a
        return mod

    def module(a):
        hit = m.find(a)
        if not hit:
            return 'kernel' if a >= 0xffff000000000000 else '?'
        return os.path.basename(hit[2])

    say('Recording: %s' % path)
    say('%.1f s, %d CPUs sampled; the game is pid %d (%s)' % (secs, cpus, pid, names.get(pid)))
    per_ms = sum(all_samples.values()) / cpus / secs / 1000.0
    say('samples per CPU per ms: %.2f' % per_ms)

    # frames
    pt = sorted(presents.get(pid, []))
    if len(pt) > 2:
        gaps = sorted((b - a) * 1000.0 / freq for a, b in zip(pt, pt[1:]))
        n = len(gaps)
        say()
        say('Frames: %d in %.1f s = %.1f a second' % (len(pt), (pt[-1] - pt[0]) / freq, (len(pt) - 1) * freq / (pt[-1] - pt[0])))
        say('  frame time ms: median %.1f, 90%% %.1f, 99%% %.1f, worst %.1f' % (
            gaps[n // 2], gaps[int(n * .9)], gaps[int(n * .99)], gaps[-1]))
        say('  frames over 33 ms: %d, over 100 ms: %d' % (sum(g > 33.3 for g in gaps), sum(g > 100 for g in gaps)))
    else:
        say('No frames from the game in this recording (Direct3D 9 events: %s)' % {p: len(v) for p, v in presents.items()})

    # threads
    say()
    say('Threads (share of one core over the recording; from CPU samples, and from switches):')
    tids = sorted((t for t, (p, _s) in threads.items() if p == pid), key=lambda t: -per_thread[t])
    busy_total = 0.0
    for t in tids:
        s = per_thread[t]
        r = run[t] / freq / secs
        busy_total += r
        if s < 10 and r < 0.01:
            continue
        say('  %6d  %5.1f%%  %5.1f%%  starts in %s' % (t, 100.0 * s / per_ms / 1000 / secs, 100 * r, where(threads[t][1])))
    say('  the game kept %.2f cores busy on average (of %d)' % (busy_total, cpus))

    # main thread
    main_tid = tids[0]
    say()
    say('Busiest thread %d: where its time goes' % main_tid)
    excl_mod = collections.Counter()
    excl_fn = collections.Counter()
    incl_fn = collections.Counter()
    n_main = 0
    with_stack = 0
    for (tid, ts), ip in samples.items():
        if tid != main_tid:
            continue
        n_main += 1
        excl_mod[module(ip)] += 1
        st = stacks.get((tid, ts))
        game_frames = []
        if st:
            with_stack += 1
            seen = set()
            for a in st:
                if a < 0x100000000 and m.find(a) and os.path.basename(m.find(a)[2]).lower() == GAME:
                    w = where(a)
                    if w not in seen:
                        seen.add(w)
                        incl_fn[w] += 1
                    game_frames.append(w)
        if m.find(ip) and os.path.basename(m.find(ip)[2]).lower() == GAME:
            excl_fn[where(ip)] += 1
        elif game_frames:
            excl_fn['(in %s, called from) %s' % (module(ip), game_frames[0])] += 1
        else:
            excl_fn['(in %s)' % module(ip)] += 1
    say('  %d samples, %d with a stack' % (n_main, with_stack))
    say('  by module:')
    for k, v in excl_mod.most_common(15):
        say('    %5.1f%%  %s' % (100.0 * v / n_main, k))
    say('  where it is when sampled (the game function, or the game function that called out):')
    for k, v in excl_fn.most_common(40):
        say('    %5.1f%%  %s' % (100.0 * v / n_main, k))
    say('  inside (share of samples with this function anywhere on the stack):')
    for k, v in incl_fn.most_common(60):
        say('    %5.1f%%  %s' % (100.0 * v / max(with_stack, 1), k))

    # by part of the game: the game function the sample is in, or the first one that called out
    def part_of(ip, st):
        a = ip
        if not (m.find(ip) and os.path.basename(m.find(ip)[2]).lower() == GAME):
            mod = module(ip).lower()
            for key, part in MODULE_PARTS:
                if key in mod:
                    return part
            a = next((x for x in (st or ()) if x < 0x100000000 and m.find(x) and
                      os.path.basename(m.find(x)[2]).lower() == GAME), None)
            if a is None:
                return 'system (%s)' % module(ip)
        hit = gn.find(a)
        text = ((hit[1] or '') + ' ' + hit[2]).lower() if hit else ''
        for words, part in PARTS:
            if any(w in text for w in words):
                return part
        return 'other game code'

    parts = collections.Counter()
    main_times = []
    for (tid, ts), ip in samples.items():
        if tid == main_tid:
            p = part_of(ip, stacks.get((tid, ts)))
            parts[p] += 1
            main_times.append((ts, p))
    say()
    say('Busiest thread by part of the game:')
    for k, v in parts.most_common():
        say('    %5.1f%%  %s' % (100.0 * v / n_main, k))
    if len(pt) > 2:
        import bisect
        main_times.sort()
        tlist = [t for t, _p in main_times]
        slow = sorted(((b - a, a, b) for a, b in zip(pt, pt[1:])), reverse=True)[:12]
        say()
        say('The slowest frames, and what the busiest thread was doing in each:')
        for d, a, b in slow:
            i, j = bisect.bisect_left(tlist, a), bisect.bisect_left(tlist, b)
            c = collections.Counter(p for _t, p in main_times[i:j])
            tot = max(j - i, 1)
            say('  %.1f ms at %.1f s: %s' % (d * 1000.0 / freq, (a - pt[0]) / freq,
                                             ', '.join('%s %d%%' % (k, 100 * v // tot) for k, v in c.most_common(4))))

    # the other busy threads, briefly
    for t in tids[1:5]:
        tot = per_thread[t]
        if tot < 500:
            break
        c = collections.Counter()
        for (tid, ts), ip in samples.items():
            if tid == t:
                st = stacks.get((tid, ts)) or ()
                g = next((where(a) for a in st if a < 0x100000000 and m.find(a) and
                          os.path.basename(m.find(a)[2]).lower() == GAME), None)
                c[g or '(in %s)' % module(ip)] += 1
        say()
        say('Thread %d (%d samples):' % (t, tot))
        for k, v in c.most_common(10):
            say('    %5.1f%%  %s' % (100.0 * v / tot, k))
    if out:
        with open(out, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
