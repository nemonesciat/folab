"""What the last build of a mod made of each of its parts, kept so the next build can take what didn't change.

A part is found again only by a digest of everything that went into it (the mod's entries by Project.digest, the masters,
the game's files, the opened plugin), never by trusting that nothing changed: a build that takes parts from here writes
the same bytes as one that makes them all (tests/test_espreuse.py builds both ways). Kept beside the build as
<plugin>.reuse, an SQLite file with a row a part (a build writes only the rows it made afresh), and in memory between
builds in one FOLab."""
import hashlib
import os
import pickle
import sqlite3

VERSION = 1
_MEM = {}                               # path -> (context, items): the last build's, in memory


def digest(*parts):
    """A short digest of anything pickle can write (bytes, numbers, strings, tuples, None)."""
    return hashlib.blake2b(pickle.dumps(parts, 4), digest_size=16).digest()


def mark(path):
    try:
        st = os.stat(path)
        return (st.st_size, st.st_mtime_ns)
    except OSError:
        return None


def _open(path):
    db = sqlite3.connect(path)
    db.execute('CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v BLOB)')
    db.execute('CREATE TABLE IF NOT EXISTS part (kind TEXT, key BLOB, dig BLOB, value BLOB, PRIMARY KEY (kind, key))')
    return db


class Reuse:
    """get(kind, key, digest) -> what was made, or None; put(kind, key, digest, value) -> value. Only what this build got
    or put is kept for the next."""

    def __init__(self, path, context):
        self.path, self.context = path, context
        self.old, self.new = {}, {}
        self.hits = self.misses = 0
        had = _MEM.get(path)
        if had and had[0] == context:
            self.old = had[1]
        elif path and os.path.isfile(path):
            try:
                db = _open(path)
                try:
                    row = db.execute("SELECT v FROM meta WHERE k = 'context'").fetchone()
                    if row and row[0] == context + bytes([VERSION]):
                        self.old = {(kind, pickle.loads(key)): (dig, pickle.loads(value))
                                    for kind, key, dig, value in db.execute('SELECT kind, key, dig, value FROM part')}
                finally:
                    db.close()
            except (sqlite3.Error, pickle.UnpicklingError, EOFError, ValueError):
                self.old = {}

    def get(self, kind, key, dig):
        had = self.old.get((kind, key))
        if had is not None and had[0] == dig:
            self.new[(kind, key)] = had
            self.hits += 1
            return had[1]
        self.misses += 1
        return None

    def put(self, kind, key, dig, value):
        self.new[(kind, key)] = (dig, value)
        return value

    def save(self):
        """Kept for the next build: the parts made afresh written, those no longer made taken out."""
        if not self.path:
            return
        made = [(k, v) for k, v in self.new.items() if self.old.get(k) is not v]
        gone = [k for k in self.old if k not in self.new]
        fresh = not os.path.isfile(self.path)
        try:
            db = _open(self.path)
            try:
                row = db.execute("SELECT v FROM meta WHERE k = 'context'").fetchone()
                if fresh or not row or row[0] != self.context + bytes([VERSION]) or not self.old:
                    db.execute('DELETE FROM part')
                    made, gone = list(self.new.items()), []
                    db.execute("INSERT OR REPLACE INTO meta VALUES ('context', ?)", (self.context + bytes([VERSION]),))
                db.executemany('DELETE FROM part WHERE kind = ? AND key = ?', [(kind, pickle.dumps(key, 4)) for kind, key in gone])
                db.executemany('INSERT OR REPLACE INTO part VALUES (?, ?, ?, ?)',
                               [(kind, pickle.dumps(key, 4), dig, pickle.dumps(value, pickle.HIGHEST_PROTOCOL))
                                for (kind, key), (dig, value) in made])
                db.commit()
            finally:
                db.close()
        except sqlite3.Error as e:
            print('espreuse: %s not kept (%s): the next build makes everything afresh' % (self.path, e), flush=True)
            try:
                os.remove(self.path)        # (a damaged file: the next build makes everything afresh)
            except OSError:
                pass
        _MEM.clear()                        # (one mod's at a time: a big world's parts are as big as its plugin)
        _MEM[self.path] = (self.context, self.new)


    def remember(self):
        """What this one took or made kept in memory only, beside what's kept already (a plan for the page, not a build)."""
        items = dict(self.old)              # (what it found kept, in memory or read from the file)
        items.update(self.new)
        _MEM.clear()
        _MEM[self.path] = (self.context, items)


def forget(path=None):
    """Nothing kept in memory (for tests and a mod closed)."""
    if path is None:
        _MEM.clear()
    else:
        _MEM.pop(path, None)
