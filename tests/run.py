"""FOLab's tests: each test_*.py run on its own, in a fresh scratch folder (FOLAB_HOME), against the game's own files.
Nothing touches the game, your mods or FOLab's own folders.

    py -3 tests/run.py              every test
    py -3 tests/run.py records      the tests whose file name contains "records"

A test prints PASS/FAIL lines; it fails if any line says FAIL, or it stops with an error."""
import glob
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def main(args):
    tests = sorted(glob.glob(os.path.join(HERE, 'test_*.py')))
    if args:
        tests = [t for t in tests if any(a.lower() in os.path.basename(t).lower() for a in args)]
    failed = 0
    for t in tests:
        home = tempfile.mkdtemp(prefix='folab-test-')
        start = time.time()
        r = subprocess.run([sys.executable, t], cwd=os.path.join(HERE, '..', 'app'), capture_output=True, text=True,
                           env=dict(os.environ, FOLAB_HOME=home))
        out = (r.stdout + r.stderr).splitlines()
        passes = sum(l.startswith('PASS') for l in out)
        fails = [l for l in out if l.startswith('FAIL')]
        bad = fails or r.returncode != 0
        failed += bool(bad)
        print('%s %-28s %3d passed%s  (%.0fs)' % ('FAIL' if bad else ' ok ', os.path.basename(t)[5:-3], passes,
                                                  ', %d failed' % len(fails) if fails else '', time.time() - start))
        if bad:
            for l in fails + ([l for l in out if l.strip()][-8:] if r.returncode else []):
                print('       ' + l)
        shutil.rmtree(home, ignore_errors=True)
    print('\n%d of %d test files passed' % (len(tests) - failed, len(tests)))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
