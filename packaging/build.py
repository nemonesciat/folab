"""Build FOLab for people without Python: a folder (and a zip of it) with FOLab.exe, its own Python and the app.

Run with the Python FOLab is developed with:  py -3 packaging\\build.py
Output: packaging\\out\\FOLab\\ and packaging\\out\\FOLab-<version>-portable.zip. Nothing is downloaded: Python comes
from this computer's own installation (only the standard library FOLab uses), and FOLab.exe is compiled with the C#
compiler that ships with Windows. (After Morrowind Workshop's packaging/build.py.)

    FOLab.exe          starts FOLab: no console, its own window, an icon by the clock (open, log, quit)
    python\\            Python, the standard library and the DLLs it needs, nothing else
    app\\               FOLab
    README.txt, THIRD_PARTY_NOTICES.txt
Your mods, settings, backups and logs are kept beside FOLab.exe, so the folder can live anywhere you can save files."""
import os
import re
import shutil
import struct
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
APP = os.path.join(ROOT, 'app')
OUT = os.path.join(HERE, 'out')
STAGE = os.path.join(OUT, 'FOLab')
KEEP = os.path.join(HERE, 'kept during build')
BUILT = {'app', 'python', 'FOLab.exe', 'README.txt', 'THIRD_PARTY_NOTICES.txt', 'folab_running.json'}   # (the rest is the user's)
CSC = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), r'Microsoft.NET\Framework64\v4.0.30319\csc.exe')

PY = sys.base_prefix
PYVER = 'python%d%d' % sys.version_info[:2]
# parts of the standard library FOLab never uses
LIB_SKIP = {'site-packages', 'test', 'tests', 'idlelib', 'tkinter', 'turtledemo', 'ensurepip', 'lib2to3',
            '__pycache__', 'venv', 'pydoc_data', 'distutils', 'turtle.py', 'unittest', 'pydoc.py'}
DLL_SKIP = re.compile(r'^(_test|xxlimited|_tkinter|_ctypes_test|tcl|tk)', re.I)
APP_SKIP = {'__pycache__'}


def log(*a):
    print(*a, flush=True)


def version():
    v = {}
    exec(open(os.path.join(APP, 'version.py'), encoding='utf-8').read(), v)
    return v['VERSION']


def copy_tree(src, dst, skip=()):
    for name in os.listdir(src):
        if name in skip or name.endswith(('.pyc', '.pyo')):
            continue
        s, d = os.path.join(src, name), os.path.join(dst, name)
        if os.path.isdir(s):
            os.makedirs(d, exist_ok=True)
            copy_tree(s, d, skip)
        else:
            shutil.copy2(s, d)


def pe_imports(path):
    """DLL names a Windows program or DLL loads (its import table)."""
    with open(path, 'rb') as f:
        data = f.read()
    try:
        pe = struct.unpack_from('<I', data, 0x3C)[0]
        if data[pe:pe + 4] != b'PE\0\0':
            return []
        nsec = struct.unpack_from('<H', data, pe + 6)[0]
        optsize = struct.unpack_from('<H', data, pe + 20)[0]
        opt = pe + 24
        magic = struct.unpack_from('<H', data, opt)[0]
        dd = opt + (112 if magic == 0x20B else 96)
        imp_rva = struct.unpack_from('<I', data, dd + 8)[0]
        secs = []
        for i in range(nsec):
            s = opt + optsize + i * 40
            vsize, va, rsize, rptr = struct.unpack_from('<IIII', data, s + 8)
            secs.append((va, max(vsize, rsize), rptr))

        def off(rva):
            for va, size, rptr in secs:
                if va <= rva < va + size:
                    return rva - va + rptr
            return None
        out, p = [], off(imp_rva)
        while p is not None:
            name_rva = struct.unpack_from('<I', data, p + 12)[0]
            if not name_rva:
                break
            q = off(name_rva)
            out.append(data[q:data.index(b'\0', q)].decode('ascii', 'replace'))
            p += 20
        return out
    except (struct.error, ValueError):
        return []


def collect_dlls(py_dir):
    """Copy the DLLs (not Windows' own) that python.exe, its DLL and the .pyd modules load."""
    search = [PY, os.path.join(PY, 'DLLs'), os.path.join(PY, 'Library', 'bin')]
    sys32 = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'System32')
    have = {n.lower() for n in os.listdir(py_dir)} | {n.lower() for n in os.listdir(os.path.join(py_dir, 'DLLs'))}
    todo = [os.path.join(dp, f) for dp, _d, fs in os.walk(py_dir) for f in fs if f.lower().endswith(('.dll', '.pyd', '.exe'))]
    added = []
    while todo:
        for dep in pe_imports(todo.pop()):
            low = dep.lower()
            if low in have or low.startswith(('api-ms-', 'ext-ms-')) or os.path.exists(os.path.join(sys32, dep)):
                continue
            src = next((os.path.join(d, dep) for d in search if os.path.exists(os.path.join(d, dep))), None)
            have.add(low)
            if not src:
                log('  ! not found:', dep)
                continue
            dst = os.path.join(py_dir, dep)
            shutil.copy2(src, dst)
            added.append(dep)
            todo.append(dst)
    return added


def build_python(py_dir):
    log('Python from', PY)
    os.makedirs(py_dir)
    for f in os.listdir(PY):
        if re.match(r'^(python(w)?\.exe|python3\d*\.dll|vcruntime140.*\.dll|msvcp140.*\.dll|LICENSE.*)$', f, re.I):
            shutil.copy2(os.path.join(PY, f), os.path.join(py_dir, f))
    os.makedirs(os.path.join(py_dir, 'DLLs'))
    for f in os.listdir(os.path.join(PY, 'DLLs')):
        if f.lower().endswith(('.pyd', '.dll')) and not DLL_SKIP.match(f):
            shutil.copy2(os.path.join(PY, 'DLLs', f), os.path.join(py_dir, 'DLLs', f))
    lib = os.path.join(py_dir, 'Lib')
    os.makedirs(lib)
    copy_tree(os.path.join(PY, 'Lib'), lib, LIB_SKIP)
    added = collect_dlls(py_dir)
    log('  DLLs the modules need:', ', '.join(added) or 'none')
    # a "._pth" file makes this Python ignore any other Python on the computer
    with open(os.path.join(py_dir, PYVER + '._pth'), 'w', encoding='ascii') as f:
        f.write('Lib\nDLLs\n..\\app\n')


def check_python(py_dir):
    """Import everything FOLab uses with the bundled Python, with nothing else on PATH."""
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(('PYTHON', 'CONDA'))}
    env['PATH'] = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'System32')
    mods = sorted(os.path.splitext(f)[0] for f in os.listdir(os.path.join(STAGE, 'app')) if f.endswith('.py'))
    code = ('import sys, ctypes, zlib, json, http.server, webbrowser, mmap, hashlib, base64\n'
            'for m in %r: __import__(m)\n'
            'print("ok", sys.version.split()[0], sys.prefix)\n') % mods
    r = subprocess.run([os.path.join(py_dir, 'python.exe'), '-c', code], env=env, capture_output=True, text=True,
                       cwd=os.path.join(STAGE, 'app'))
    if r.returncode != 0 or not r.stdout.startswith('ok'):
        raise SystemExit('The bundled Python does not work:\n' + r.stdout + r.stderr)
    log('  check:', r.stdout.strip())


def strip_pycache(top):
    for dp, dirs, _files in os.walk(top):
        for d in list(dirs):
            if d == '__pycache__':
                shutil.rmtree(os.path.join(dp, d))
                dirs.remove(d)


def compile_launcher(exe, icon, ver):
    nums = (re.findall(r'\d+', ver) + ['0'] * 4)[:4]
    info = os.path.join(OUT, 'buildinfo.cs')
    with open(info, 'w', encoding='utf-8') as f:
        for k, v in (('AssemblyTitle', 'FOLab'), ('AssemblyDescription', 'FOLab, a New Vegas editor'), ('AssemblyProduct', 'FOLab'),
                     ('AssemblyVersion', '.'.join(nums)), ('AssemblyFileVersion', '.'.join(nums)), ('AssemblyInformationalVersion', ver)):
            f.write('[assembly: System.Reflection.%s("%s")]\n' % (k, v))
        # (the version FOLab.exe writes in its log; after the assembly's details, which must come first)
        f.write('static class BuildInfo { public const string Version = "%s"; }\n' % ver)
    args = [CSC, '/nologo', '/optimize+', '/target:winexe', '/platform:anycpu', '/out:' + exe, '/win32icon:' + icon,
            '/win32manifest:' + os.path.join(HERE, 'app.manifest'), '/r:System.Windows.Forms.dll', '/r:System.Drawing.dll',
            info] + [os.path.join(HERE, f) for f in ('launcher.cs', 'common.cs', 'appwindow.cs')]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit('Compiling FOLab.exe failed:\n' + r.stdout + r.stderr)


NOTICES = """FOLab bundles these, each under its own licence:

Python {py} (Python Software Foundation License) - python\\LICENSE.txt. https://www.python.org/
three.js, its DDSLoader and TransformControls (MIT License, Copyright 2010-2021 three.js authors). https://threejs.org/
Cinzel (Natanael Gama), Inter (Rasmus Andersson), Oswald (Vernon Adams and contributors) and Share Tech Mono (Carrois
Type Design): SIL Open Font License 1.1 - app\\web\\vendor\\OFL-*.txt and app\\web\\vendor\\licenses.

FOLab downloads nothing itself. xNVSE, JIP LN NVSE and NVTF are their makers' own: you get them from their pages.
Fallout: New Vegas is Bethesda Softworks' and Obsidian Entertainment's. FOLab contains none of the game's files and
isn't made or endorsed by them.
"""


def main():
    if not os.path.exists(CSC):
        raise SystemExit('The C# compiler that comes with Windows was not found at ' + CSC)
    ver = version()
    log('FOLab', ver)
    # FOLab keeps your mods and settings beside FOLab.exe: a copy you've been running keeps them through a rebuild, set
    # aside here (the zip is made without them) and put back afterwards.
    if os.path.exists(KEEP):
        raise SystemExit('A build that stopped left your things in ' + KEEP + ': move what you want back and delete it.')
    if os.path.exists(STAGE):
        try:
            os.rename(STAGE, KEEP)
        except OSError:
            raise SystemExit('packaging\\out\\FOLab is in use (is FOLab.exe from it still running?): close it and build again.')
    try:
        shutil.rmtree(OUT, ignore_errors=True)
        make(ver)
    finally:
        restore_kept()


def restore_kept():
    if not os.path.exists(KEEP):
        return
    os.makedirs(STAGE, exist_ok=True)
    for name in os.listdir(KEEP):
        if name not in BUILT:
            shutil.move(os.path.join(KEEP, name), os.path.join(STAGE, name))
    shutil.rmtree(KEEP)


def make(ver):
    os.makedirs(STAGE)
    icon = os.path.join(APP, 'web', 'vendor', 'folab.ico')
    if not os.path.exists(icon):
        sys.path.insert(0, HERE)
        import brand
        brand.main()
    log('App')
    os.makedirs(os.path.join(STAGE, 'app'))
    copy_tree(APP, os.path.join(STAGE, 'app'), APP_SKIP)
    build_python(os.path.join(STAGE, 'python'))
    check_python(os.path.join(STAGE, 'python'))
    strip_pycache(STAGE)
    log('FOLab.exe')
    compile_launcher(os.path.join(STAGE, 'FOLab.exe'), icon, ver)
    readme = open(os.path.join(ROOT, 'README.md'), encoding='utf-8').read()
    readme = readme.replace('Double-click **Start FOLab.bat**.', 'Double-click **FOLab.exe**.')
    with open(os.path.join(STAGE, 'README.txt'), 'w', encoding='utf-8') as f:
        f.write(readme)
    with open(os.path.join(STAGE, 'THIRD_PARTY_NOTICES.txt'), 'w', encoding='utf-8') as f:
        f.write(NOTICES.format(py=sys.version.split()[0]))
    z = os.path.join(OUT, 'FOLab-%s-portable.zip' % ver)
    log('Zip')
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for dp, _d, files in os.walk(STAGE):
            for fn in files:
                p = os.path.join(dp, fn)
                zf.write(p, os.path.join('FOLab', os.path.relpath(p, STAGE)))
    size = sum(os.path.getsize(os.path.join(dp, f)) for dp, _d, fs in os.walk(STAGE) for f in fs)
    log('Done: %s (%.0f MB unpacked, %.0f MB zipped)' % (z, size / 1e6, os.path.getsize(z) / 1e6))


if __name__ == '__main__':
    main()
