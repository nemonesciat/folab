"""The Scripts page's data: the game's scripts and the mod's, compiling on save, what runs a script, putting one on a thing.

A script of the mod's is an ordinary SCPT record in project.records, kept in the same form as any other (recordio.py):
EDID, SCHR, SCDA and SCTX (raw: they hold no form IDs), SLSD + SCVR for each variable, SCRV / SCRO for each reference (form
links as keys, so espwrite re-points them to the plugin's own numbering when it writes). Nothing with an error in it
is ever stored: the record always holds bytes the compiler gave for the source beside them.

Routes are in get() and post(), hooked into server.py by one line each; setup() says where the server keeps things."""
import bisect
import copy
import json
import os
import re
import struct

import recordio
import schema
import scriptc
import scriptdocs
import scripttemplates
import tes4

KINDS = {'object': scriptc.SCRIPT_OBJECT, 'quest': scriptc.SCRIPT_QUEST, 'effect': scriptc.SCRIPT_EFFECT}
KIND_OF = {v: k for k, v in KINDS.items()}

# What can carry a script (SCRI), and what comes before SCRI in each, as the game's records have them: every record of
# the game keeps to this (tests/test_scripts_page.py takes each SCRI out and puts it back through set_script).
_ITEM = ('EDID', 'OBND', 'FULL', 'MODL', 'MODT', 'MODS', 'ICON', 'MICO')
SCRI_AFTER = {
    'ACTI': _ITEM, 'TACT': _ITEM, 'TERM': _ITEM, 'ARMO': ('EDID', 'OBND', 'FULL'), 'CONT': _ITEM, 'DOOR': _ITEM, 'LIGH': _ITEM,
    'MISC': _ITEM, 'FURN': _ITEM, 'WEAP': _ITEM, 'AMMO': _ITEM, 'KEYM': _ITEM, 'ALCH': _ITEM, 'BOOK': _ITEM, 'CCRD': _ITEM,
    'NPC_': _ITEM + ('ACBS', 'SNAM', 'INAM', 'VTCK', 'TPLT', 'RNAM', 'EAMT', 'SPLO'),
    'CREA': _ITEM + ('ACBS', 'SNAM', 'INAM', 'VTCK', 'TPLT', 'EAMT', 'SPLO', 'DEST', 'DSTD', 'DSTF', 'EITM', 'NIFT', 'NIFZ'),
    'QUST': ('EDID',), 'CHAL': ('EDID', 'FULL'),
}
CARRIERS = tuple(SCRI_AFTER)


class ScriptProblem(ValueError):
    """Something the user can fix, in plain words."""


def set_script(rec, script_key):
    """The record's SCRI set to a script's key, or taken off (None), in its place among the record's parts."""
    rec['subs'] = [s for s in rec['subs'] if s['tag'] != 'SCRI']
    if script_key:
        after = SCRI_AFTER.get(rec['type'])
        if after is None:
            raise ScriptProblem('A %s can\'t carry a script.' % rec['type'])
        at = 0
        for n, s in enumerate(rec['subs']):
            if s['tag'] in after:
                at = n + 1
        rec['subs'].insert(at, {'tag': 'SCRI', 'label': 'Script', 'kind': 'F', 'value': script_key})
    return rec


def source_of(rec):
    """A script record's source as text with plain line ends."""
    s = next((s for s in rec['subs'] if s['tag'] == 'SCTX'), None)
    if not s:
        return ''
    return bytes.fromhex(s['value']).decode(scriptc.ENC, 'replace').replace('\r\n', '\n').replace('\r', '\n')


def header_of(rec):
    """(type, variable count) from a script record's SCHR."""
    s = next((s for s in rec['subs'] if s['tag'] == 'SCHR'), None)
    if not s or s['kind'] != 'struct':
        return scriptc.SCRIPT_OBJECT, 0
    f = {x.get('name'): x.get('value') for x in s['fields']}
    return f['Type'], f['Variable count']


def vars_of(rec):
    """[(number, name, is integer)] from a script record."""
    out, last = [], None
    for s in rec['subs']:
        if s['tag'] == 'SLSD' and s['kind'] == 'struct':
            f = {x.get('name'): x.get('value') for x in s['fields']}
            last = (f['Index'], bool(f['Flags']))
        elif s['tag'] == 'SCVR' and last:
            out.append((last[0], s['value'], last[1]))
            last = None
    return out


class ModForms(scriptc.GameForms):
    """The game's forms with the open mod's laid over them, for the compiler. A form of the mod's own has its key ('+000800')
    where a game form has its number."""

    def __init__(self, gd):
        super().__init__(gd)
        self.pr = None
        self.mine = {}
        self.extra = {}

    def refresh(self, pr, extra=None):
        self.pr = pr
        self.extra = extra or {}
        self.mine = {}
        for k, r in list((pr.records if pr else {}).items()) + list(self.extra.items()):
            e = recordio.field(r, 'EDID')
            if e:
                self.mine[e.lower()] = k
        return self

    def _rec(self, key):
        return self.extra.get(key) or (self.pr.records.get(key) if self.pr else None)

    def find_edid(self, name):
        key = self.mine.get(name.lower())
        if key is None:
            return super().find_edid(name)
        if key.startswith('+'):
            r = self._rec(key)
            return scriptc.Form(self, key, r['type'], bool(r.get('flags', 0) & tes4.PERSISTENT), None, r)
        return self._form(*self.gd.source(self.gd.from_key(key)))

    def script_vars(self, form):
        if isinstance(form.fid, str):
            sk = recordio.field(form.rec, 'SCRI') if form.tag == 'QUST' else ''
            return self._vars_by_key(sk) if sk else None
        if form.plugin is None:
            return None
        if form.tag == 'QUST':
            mine = self._rec(self.gd.key(form.fid))
            if mine:
                sk = recordio.field(mine, 'SCRI')
                return self._vars_by_key(sk) if sk else None
        elif form.tag in scriptc.REF_TAGS:
            base = self._fields(form).get('NAME')
            if base:
                mine = self._rec(self.gd.key(self.gd.to_global(form.plugin, struct.unpack('<I', base)[0])))
                if mine:
                    sk = recordio.field(mine, 'SCRI')
                    return self._vars_by_key(sk) if sk else None
        return super().script_vars(form)

    def _vars_by_key(self, key):
        r = self._rec(key)
        if r:
            return {n.lower(): (i, is_int) for i, n, is_int in vars_of(r)}
        return {} if key.startswith('+') else self.vars_of(self.gd.from_key(key))

    def vars_of(self, sid):
        r = self._rec(self.gd.key(sid))
        if r:
            return {n.lower(): (i, is_int) for i, n, is_int in vars_of(r)}
        return super().vars_of(sid)

    def message_text(self, form):
        r = form.rec if isinstance(form.fid, str) else self._rec(self.gd.key(form.fid))
        if r:
            return recordio.field(r, 'DESC').encode(scriptc.ENC, 'replace')
        return super().message_text(form)

    def is_interior(self, form):
        if isinstance(form.fid, str):
            d = next((s for s in form.rec['subs'] if s['tag'] == 'DATA'), None)
            return bool(form.tag == 'CELL' and d and d['kind'] == 'struct' and d['fields'][0]['value'] & 1)
        return super().is_interior(form)

    def is_map_marker(self, form):
        return False if isinstance(form.fid, str) else super().is_map_marker(form)


class Scripts:
    def __init__(self, gd, get_project, get_browse=lambda: None):
        self.gd, self.pr, self.br = gd, get_project, get_browse
        scriptc.GameForms._shared = {k: v for k, v in scriptc.GameForms._shared.items() if k[0] == id(gd)}
        self.forms = ModForms(gd)
        self.game = sorted(((self._edid(fid), fid) for fid, (i, r) in gd.forms.items() if r.tag == 'SCPT'),
                           key=lambda x: x[0].lower())
        self._kinds = {}
        self._sources = None       # game script's key -> its source, kept once something searches inside them
        self._names = None         # sorted lower editor IDs, for completing

    def _edid(self, fid):
        i, rec = self.gd.source(fid)
        return tes4.zstr(self.gd.plugins[i].fields(rec).get('EDID', b''))

    def _kind(self, fid):
        got = self._kinds.get(fid)
        if got is None:
            i, rec = self.gd.source(fid)
            d = self.gd.plugins[i].fields(rec).get('SCHR', b'')
            got = self._kinds[fid] = KIND_OF.get(struct.unpack_from('<H', d, 16)[0] if len(d) >= 20 else 0, 'object')
        return got

    # ---- lists ----

    def mine(self):
        pr = self.pr()
        return {k: r for k, r in (pr.records if pr else {}).items() if r['type'] == 'SCPT'}

    def rows(self, q='', inside=False, limit=800):
        """The mod's scripts, then the game's: q's words in the editor ID, or (inside) anywhere in the source."""
        words, mine = q.lower().split(), self.mine()
        sources = self.sources() if inside and words else None

        def hit(edid, text=None):
            if all(w in edid.lower() for w in words):
                return True
            return text is not None and all(w in text() for w in words)
        out = []
        for k, r in sorted(mine.items(), key=lambda kv: recordio.field(kv[1], 'EDID').lower()):
            e = recordio.field(r, 'EDID')
            if hit(e, (lambda r=r: source_of(r).lower()) if sources is not None else None):
                out.append({'key': k, 'edid': e, 'kind': KIND_OF.get(header_of(r)[0], 'object'), 'state': 'new' if k.startswith('+') else 'changed'})
        total = 0
        for e, fid in self.game:
            k = self.gd.key(fid)
            if k in mine or not hit(e, (lambda k=k: sources[k]) if sources is not None else None):
                continue
            total += 1
            if total <= limit:
                out.append({'key': k, 'edid': e, 'kind': self._kind(fid), 'state': ''})
        return {'rows': out, 'more': max(0, total - limit)}

    def sources(self):
        """Every game script's source in lower case, read once (about 5 MB)."""
        if self._sources is None:
            got = {}
            for _e, fid in self.game:
                i, rec = self.gd.source(fid)
                got[self.gd.key(fid)] = self.gd.plugins[i].fields(rec).get('SCTX', b'').decode(scriptc.ENC, 'replace').lower()
            self._sources = got
        return self._sources

    def record(self, key):
        """The script as the mod has it, else as the game does."""
        pr = self.pr()
        rec = pr.records.get(key) if pr else None
        if rec:
            return rec
        try:
            fid = self.gd.from_key(key)
        except (ValueError, KeyError):
            raise ScriptProblem('There is no script %s.' % key)
        if fid not in self.gd.forms:
            raise ScriptProblem('There is no script %s.' % key)
        return recordio.load(self.gd, fid)

    def one(self, key):
        rec = self.record(key)
        if rec['type'] != 'SCPT':
            raise ScriptProblem('%s is a %s, not a script.' % (key, rec['type']))
        pr = self.pr()
        state = '' if not (pr and key in pr.records) else 'new' if key.startswith('+') else 'changed'
        text = source_of(rec)
        return {'key': key, 'edid': recordio.field(rec, 'EDID'), 'kind': KIND_OF.get(header_of(rec)[0], 'object'), 'state': state, 'text': text,
                'from': 'your mod' if key.startswith('+') else rec.get('src', ''), 'vars': [[n, 'short' if i else 'float'] for _k, n, i in vars_of(rec)],
                'check': self.check(text, key), 'who': self.who(key)}

    # ---- compiling ----

    def compile(self, text, key=None, kind=None, extra=None):
        """The compiled script, or a ScriptProblem. A script compiled again keeps its variables' numbers."""
        rec = None
        if key:
            pr = self.pr()
            rec = pr.records.get(key) if pr else None
            if rec is None and not key.startswith('+'):
                rec = self.record(key)
        old_vars, old_count, was = (), 0, scriptc.SCRIPT_OBJECT
        if rec:
            was, old_count = header_of(rec)
            old_vars = vars_of(rec)
        script_type = KINDS[kind] if kind in KINDS else was
        forms = self.forms.refresh(self.pr(), extra)
        return scriptc.compile_script(text, forms, script_type, old_vars, old_count)

    def check(self, text, key=None, kind=None):
        """What the compiler says about the text, without keeping anything."""
        try:
            c = self.compile(text, key, kind)
            problem = self._name_problem(c.name, text, key)
            if problem:
                raise problem
        except scriptc.CompileError as e:
            return {'ok': False, 'error': {'line': e.line, 'message': e.message, 'text': e.text}, 'warnings': []}
        return {'ok': True, 'name': c.name, 'size': len(c.data), 'warnings': self._warnings(text, c.script_type),
                'vars': [[n, 'short' if i else 'float'] for _k, n, i in c.vars],
                'refs': [self._ref_row(n, f, v) for n, f, v in c.refs]}

    def _ref_row(self, name, form, var):
        if var or form is None:
            return {'name': name, 'var': True}
        return {'name': name, 'key': self._key(form), 'tag': form.tag}

    def _key(self, form):
        return form.fid if isinstance(form.fid, str) else self.gd.key(form.fid)

    def _name_problem(self, name, text, key):
        """Another form with the script's name would make the name mean two things to every other script."""
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', name or ''):
            return scriptc.CompileError('A script\'s name is letters, numbers and _ only, starting with a letter.', _scn_line(text))
        hit = self.forms.find_edid(name)
        if hit is not None and self._key(hit) != key:
            return scriptc.CompileError('"%s" is taken: a %s already has that editor ID. Give the script another name.' % (name, hit.tag), _scn_line(text))
        return None

    @staticmethod
    def _warnings(text, script_type):
        out = []
        for n, line in enumerate(text.splitlines(), 1):
            m = re.match(r'\s*begin\s+(\w+)', line.split(';')[0], re.I)
            if not m:
                continue
            block = m.group(1).lower()
            if block.startswith('scripteffect') and script_type != scriptc.SCRIPT_EFFECT:
                out.append({'line': n, 'message': 'This block only runs in an effect script: change what kind of script this is.'})
            elif script_type == scriptc.SCRIPT_QUEST and block not in ('gamemode', 'menumode'):
                out.append({'line': n, 'message': 'A quest script only runs GameMode and MenuMode blocks.'})
            elif script_type == scriptc.SCRIPT_EFFECT and block not in ('scripteffectstart', 'scripteffectupdate', 'scripteffectfinish', 'gamemode', 'menumode'):
                out.append({'line': n, 'message': 'An effect script only runs ScriptEffect blocks (and GameMode, MenuMode).'})
        return out

    def _record_of(self, c, edid, flags=0, src=''):
        """The compiled script as the mod keeps it."""
        subs = [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': edid}] + schema.decode_record('SCPT', c.subrecords(lambda _fid: 0))
        refs = iter(self._key(form) for _n, form, var in c.refs if not var)
        for s in subs:
            if s['tag'] == 'SCRO':
                s['value'] = next(refs)
        return {'type': 'SCPT', 'flags': flags, 'src': src, 'subs': subs}

    def _need_mod(self):
        pr = self.pr()
        if not pr:
            raise ScriptProblem('Open or start a mod first: a script is kept in your mod.')
        return pr

    def save(self, key, text, kind=None):
        """Compile and keep it (one Undo step). A script that doesn't compile changes nothing: {'ok': False, 'error': ...}."""
        pr = self._need_mod()
        try:
            c = self.compile(text, key, kind)
            problem = self._name_problem(c.name, text, key)
            if problem:
                raise problem
        except scriptc.CompileError as e:
            return {'ok': False, 'error': {'line': e.line, 'message': e.message, 'text': e.text}}
        old = self.record(key)
        rec = self._record_of(c, c.name, old.get('flags', 0), old.get('src', ''))
        pr.apply('Script ' + c.name, [{'op': 'record', 'key': key, 'record': rec}])
        return {'ok': True, 'script': self.one(key)}

    def new(self, name, kind='object', template=None, fields=None):
        """A new script of the mod's own, blank or from a template, with any message the template needs (one Undo step)."""
        pr = self._need_mod()
        name = (name or '').strip()
        kind = kind if kind in KINDS else 'object'
        extra, ops, note = {}, [], ''
        text = 'scn %s\n\nBegin %s\n\t\nEnd\n' % (name, 'ScriptEffectStart' if kind == 'effect' else 'GameMode' if kind == 'quest' else 'OnActivate')
        if template:
            t = scripttemplates.TEMPLATES.get(template)
            if not t:
                raise ScriptProblem('There is no starter called %s.' % template)
            kind, values = t['kind'], self._template_values(t, fields or {})
            text = t['text'].format(name=name, **values)
            note = t.get('then', '')
            if t.get('message'):
                msg_edid = name + 'Msg'
                msg_key = '+%06X' % pr.next_id
                msg = scripttemplates.message_record(msg_edid, values[t['message']].replace('"', "'"))
                extra[msg_key] = msg
                ops.append({'op': 'record_new', 'record': msg})
                text = text.replace('{message}', msg_edid)
        try:
            c = self.compile(text, None, kind, extra)
            problem = self._name_problem(c.name, text, None)
            if problem:
                raise problem
        except scriptc.CompileError as e:
            raise ScriptProblem(e.message)
        ops.append({'op': 'record_new', 'record': self._record_of(c, c.name)})
        made = pr.apply('New script ' + c.name, ops)
        return {'key': made[-1], 'note': note}

    def _template_values(self, t, fields):
        out = {}
        for f in t['fields']:
            v = str(fields.get(f['id'], f.get('default', ''))).strip()
            if f['kind'] == 'form':
                hit = self.forms.refresh(self.pr()).find_edid(v) if v else None
                if hit is None:
                    raise ScriptProblem('%s: nothing is called "%s". Pick one from the list.' % (f['label'], v))
                if f.get('tags') and hit.tag not in f['tags']:
                    raise ScriptProblem('%s: %s is a %s, not what\'s needed here.' % (f['label'], v, hit.tag))
            elif f['kind'] == 'number':
                if not re.fullmatch(r'\d+', v):
                    raise ScriptProblem('%s has to be a whole number.' % f['label'])
            elif not v:
                raise ScriptProblem('%s can\'t be empty.' % f['label'])
            out[f['id']] = v
        return out

    def copy(self, key, name):
        """A script of the mod's own, a copy of this one under a new name."""
        rec = self.record(key)
        name = (name or '').strip()
        text = re.sub(r'(?im)^(\s*(?:scn|scriptname)\s+)\S+', lambda m: m.group(1) + name, source_of(rec), count=1)
        pr = self._need_mod()
        try:
            c = self.compile(text, None, KIND_OF.get(header_of(rec)[0], 'object'))
            problem = self._name_problem(c.name, text, None)
            if problem:
                raise problem
        except scriptc.CompileError as e:
            raise ScriptProblem('Line %d: %s' % (e.line, e.message))
        made = pr.apply('Copy to script ' + c.name, [{'op': 'record_new', 'record': self._record_of(c, c.name)}])
        return {'key': made[-1]}

    def remove(self, key):
        """A script of the mod's own gone (and off whatever it was on); a game script back as the game has it."""
        pr = self._need_mod()
        ops = [{'op': 'record_revert', 'key': key}]
        if key.startswith('+'):
            for k, r in pr.records.items():
                if recordio.field(r, 'SCRI') == key:
                    ops.append({'op': 'record', 'key': k, 'record': set_script(copy.deepcopy(r), None)})
        pr.apply('Remove script ' + recordio.field(self.record(key), 'EDID'), ops)
        return {}

    # ---- what uses what ----

    def who(self, key):
        """What runs a script: every record with it as its SCRI, the game's and the mod's. busy until Browse's index is done."""
        pr, br = self.pr(), self.br()
        rows, seen = [], set()
        for k, r in (pr.records if pr else {}).items():
            if recordio.field(r, 'SCRI') == key:
                seen.add(k)
                rows.append({'key': k, 'type': r['type'], 'label': self._label(k), 'mine': True})
        busy = False
        if br is not None and not key.startswith('+'):
            if br.used is None:
                busy = True
            else:
                for kind, k in br.used.get(self.gd.from_key(key), ()):
                    if kind != 'record' or k in seen:
                        continue
                    seen.add(k)
                    if pr and k in pr.records:
                        continue          # (the mod's version of it doesn't have this script: it would be listed above)
                    t = self.gd.forms[self.gd.from_key(k)][1].tag
                    if t != 'SCPT' and self._has_script(k, key):
                        rows.append({'key': k, 'type': t, 'label': self._label(k), 'mine': False})
        rows.sort(key=lambda r: (not r['mine'], r['label'].lower()))
        return {'rows': rows[:300], 'total': len(rows), 'busy': busy}

    def _has_script(self, k, key):
        fid = self.gd.from_key(k)
        i, rec = self.gd.source(fid)
        d = self.gd.plugins[i].fields(rec).get('SCRI')
        return bool(d) and self.gd.key(self.gd.to_global(i, struct.unpack('<I', d)[0])) == key

    def _label(self, key):
        br = self.br()
        if br is not None:
            return br.label(key)
        r = self.record(key)
        return '%s (%s)' % (recordio.field(r, 'EDID') or key, r['type'])

    def used_in(self, word, limit=200):
        """The scripts that say a word, each with the first line it's on: a function, a variable, an editor ID."""
        word = word.strip().lower()
        if not re.fullmatch(r"[\w']+", word):
            return {'rows': [], 'total': 0}
        rx, mine = re.compile(r'(?<![\w])' + re.escape(word) + r'(?![\w])'), self.mine()
        rows, total = [], 0

        def look(key, edid, low, state):
            nonlocal total
            if word not in low:
                return
            for n, line in enumerate(low.splitlines(), 1):
                code = line.split(';')[0]
                if rx.search(code):
                    total += 1
                    if len(rows) < limit:
                        rows.append({'key': key, 'edid': edid, 'line': n, 'text': code.strip()[:120], 'state': state})
                    return
        for k, r in mine.items():
            look(k, recordio.field(r, 'EDID'), source_of(r).lower(), 'new' if k.startswith('+') else 'changed')
        src = self.sources()
        for e, fid in self.game:
            k = self.gd.key(fid)
            if k not in mine:
                look(k, e, src[k], '')
        return {'rows': rows, 'total': total}

    def complete(self, q, tags=None, limit=30):
        """Forms whose editor ID starts with q (then, with room left, has it inside): the mod's first."""
        q = q.strip().lower()
        pr = self.pr()
        forms = self.forms.refresh(pr)
        forms.find_edid('player')                # (builds the game's names the first time)
        if self._names is None:
            self._names = sorted(forms._names)
        tags = set(tags) if tags else None
        out, seen = [], set()

        def add(key, tag, edid, full):
            if key not in seen and (not tags or tag in tags):
                seen.add(key)
                out.append({'key': key, 'edid': edid, 'tag': tag, 'name': full})
        for low, k in forms.mine.items():
            if q in low:
                r = pr.records[k]
                add(k, r['type'], recordio.field(r, 'EDID'), recordio.field(r, 'FULL'))

        def game(low):
            i, rec = forms._names[low]
            f = self.gd.plugins[i].fields(rec)
            add(self.gd.key(self.gd.to_global(i, rec.formid)), rec.tag, tes4.zstr(f.get('EDID', b'')), tes4.zstr(f.get('FULL', b'')))
        at = bisect.bisect_left(self._names, q)
        while at < len(self._names) and self._names[at].startswith(q) and len(out) < limit:
            game(self._names[at])
            at += 1
        if len(out) < limit and len(q) >= 2:
            for low in self._names:
                if q in low and not low.startswith(q):
                    game(low)
                    if len(out) >= limit:
                        break
        return out[:limit]

    # ---- a script on a thing ----

    def on(self, key):
        """What script a record has, for the panels that show it."""
        rec = self.record(key)
        if rec['type'] not in SCRI_AFTER:
            return {'can': False}
        k = recordio.field(rec, 'SCRI')
        return {'can': True, 'type': rec['type'], 'script': {'key': k, 'edid': recordio.field(self.record(k), 'EDID') if self._exists(k) else k} if k else None,
                'needs': 'quest' if rec['type'] == 'QUST' else 'object'}

    def _exists(self, key):
        try:
            self.record(key)
            return True
        except ScriptProblem:
            return False

    def attach(self, target, script):
        """Put a script on a record (one Undo step), or take it off (script empty)."""
        pr = self._need_mod()
        rec = copy.deepcopy(self.record(target))
        if rec['type'] not in SCRI_AFTER:
            raise ScriptProblem('A %s can\'t carry a script.' % rec['type'])
        edid = recordio.field(rec, 'EDID') or target
        if script:
            s = self.record(script)
            if s['type'] != 'SCPT':
                raise ScriptProblem('%s isn\'t a script.' % script)
            t, name = header_of(s)[0], recordio.field(s, 'EDID')
            if rec['type'] == 'QUST' and t != scriptc.SCRIPT_QUEST:
                raise ScriptProblem('%s is a script for %s. A quest needs a quest script.' % (name, 'an effect' if t == scriptc.SCRIPT_EFFECT else 'things'))
            if rec['type'] != 'QUST' and t != scriptc.SCRIPT_OBJECT:
                raise ScriptProblem('%s is a script for %s. A %s needs an object script.' % (name, 'an effect' if t == scriptc.SCRIPT_EFFECT else 'a quest', rec['type']))
        set_script(rec, script or None)
        if not target.startswith('+') and rec == recordio.load(self.gd, self.gd.from_key(target)):
            ops = [{'op': 'record_revert', 'key': target}]    # (just as the game has it again: nothing to keep)
        else:
            ops = [{'op': 'record', 'key': target, 'record': rec}]
        pr.apply(('Put a script on ' if script else 'Take the script off ') + edid, ops)
        return {'on': self.on(target)}

    # ---- for the editor ----

    def info(self):
        return _INFO()


def _scn_line(text):
    for n, line in enumerate(text.splitlines(), 1):
        if re.match(r'\s*(scn|scriptname)\b', line.split(';')[0], re.I):
            return n
    return 1


_info = None


def _INFO():
    """The language, for colours, completing and help: from the table made from the game's own program, with our notes."""
    global _info
    if _info is None:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scriptfuncs.json'), encoding='utf-8') as f:
            d = json.load(f)

        def params(p):
            return [{'name': re.sub(r'\s*\((?:o|O)ptional\)', '', n), 'opt': bool(o)} for _k, o, n in p]
        funcs = []
        for s in d['script']:
            if s['name'].lower().startswith('unused'):
                continue
            funcs.append({'name': s['name'], 'short': s['short'], 'ref': bool(s['ref']), 'params': params(s['params']),
                          'doc': scriptdocs.FUNCTIONS.get(s['name'].lower()) or scriptdocs.FUNCTIONS.get(s['short'].lower(), '')})
        _info = {'functions': funcs,
                 'blocks': [{'name': b['name'], 'params': params(b['params']), 'doc': scriptdocs.BLOCKS.get(b['name'].lower(), '')}
                            for b in d['blocks'] if not b['name'].startswith('Unused')],
                 'keywords': ['scn', 'scriptname', 'begin', 'end', 'short', 'int', 'long', 'float', 'ref', 'reference', 'set', 'to', 'if', 'else', 'elseif', 'endif', 'return'],
                 'carriers': list(CARRIERS), 'templates': scripttemplates.for_page()}
    return _info


# ---------- routes ----------
_where = {'gd': lambda: None, 'pr': lambda: None, 'br': lambda: None, 'state': lambda: None}
_scripts = None


def setup(get_gd, get_pr, get_br, get_state):
    _where.update(gd=get_gd, pr=get_pr, br=get_br, state=get_state)


def scripts():
    global _scripts
    gd = _where['gd']()
    if _scripts is None or _scripts.gd is not gd:
        _scripts = Scripts(gd, _where['pr'], _where['br'])
    return _scripts


def get(path, q):
    try:
        return _get(path, q)
    except ScriptProblem as e:
        return {'error': str(e)}


def post(path, b):
    try:
        return _post(path, b)
    except ScriptProblem as e:
        return {'error': str(e)}


def _get(path, q):
    s = scripts()
    if path == '/api/scripts':
        return s.rows(q.get('q', ''), q.get('inside') == '1')
    if path == '/api/scripts/info':
        return s.info()
    if path == '/api/scripts/one':
        return s.one(q['key'])
    if path == '/api/scripts/who':
        return s.who(q['key'])
    if path == '/api/scripts/usedin':
        return s.used_in(q.get('word', ''))
    if path == '/api/scripts/complete':
        return s.complete(q.get('q', ''), [t for t in q.get('tags', '').split(',') if t])
    if path == '/api/scripts/on':
        return s.on(q['key'])
    raise ScriptProblem('No such page: ' + path)


def _post(path, b):
    s = scripts()
    if path == '/api/scripts/check':
        return s.check(b.get('text', ''), b.get('key'), b.get('kind'))
    if path == '/api/scripts/save':
        return dict(s.save(b['key'], b['text'], b.get('kind')), state=_where['state']())
    if path == '/api/scripts/new':
        return dict(s.new(b.get('name'), b.get('kind', 'object'), b.get('template'), b.get('fields')), state=_where['state']())
    if path == '/api/scripts/copy':
        return dict(s.copy(b['key'], b.get('name')), state=_where['state']())
    if path == '/api/scripts/remove':
        return dict(s.remove(b['key']), state=_where['state']())
    if path == '/api/scripts/attach':
        return dict(s.attach(b['target'], b.get('script')), state=_where['state']())
    raise ScriptProblem('No such page: ' + path)
