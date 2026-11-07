"""Lost Kingdoms Korean patch builder.
python build.py [--iso OUT]
"""
import os
import json, struct, os, re, sys, shutil, glob
sys.path.insert(0, os.path.dirname(__file__))
import font as F
import dolpatch

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(chr(92), '/')
G = W + '/ext/files/game/'
TX = W + '/text/'
OUT = W + '/build'
ORIG_ISO = W + '/orig.iso'

# ---------------------------------------------------------------- text loading
def load(name):
    p = TX + name + '.json'
    return json.load(open(p, encoding='utf8')) if os.path.exists(p) else []

import hashlib
def h16(s):
    return hashlib.sha1(s.encode('utf8')).hexdigest()[:16]

class HDict(dict):
    """keys may be the source text itself or its sha1[:16] (public repo form)."""
    def _k(self, k):
        return k if dict.__contains__(self, k) else h16(k)
    def __contains__(self, k): return dict.__contains__(self, self._k(k))
    def __getitem__(self, k): return dict.__getitem__(self, self._k(k))
    def get(self, k, d=None): return dict.get(self, self._k(k), d)

def load_tr(name):
    """translation table file: {key: ko}"""
    out = HDict()
    for p in sorted(glob.glob(TX + 'tr_' + name + '.json') + glob.glob(TX + 'tr_' + name + '_*.json')):
        out.update(json.load(open(p, encoding='utf8')))
    return out

PUNCT = {'…': '...', '‥': '..', '“': '"', '”': '"', '‘': "'", '’': "'", '～': '~', '—': '-', '–': '-',
         '·': '.', '！': '!', '？': '?', '，': ',', '：': ':', '　': ' ', '「': '"', '」': '"', '『': '"', '』': '"'}

def norm(s):
    return ''.join(PUNCT.get(c, c) for c in s)

class Enc:
    def __init__(self):
        self.chars = []
        self.idx = {}
    def add_text(self, s):
        for c in norm(s):
            if '\uac00' <= c <= '\ud7a3' or '\u3131' <= c <= '\u318e':
                if c not in self.idx:
                    self.idx[c] = len(self.chars); self.chars.append(c)
    def enc(self, s):
        out = bytearray()
        for c in norm(s):
            if c in self.idx:
                i = self.idx[c]
                out += bytes([0x82 + i // 128, 0x80 + i % 128])
            elif ord(c) < 0x80:
                out.append(ord(c))
            else:
                raise ValueError('unencodable %r in %r' % (c, s))
        return bytes(out)

E = Enc()

# ---------------------------------------------------------------- dialogue layout
LINE = 25     # display columns per line
PAGE = 4      # lines per page

def width(s):
    s = re.sub(r'#(?:\d+,){16}|##', '', norm(s))
    return len(s) + 5 * s.count('@')

def wrap_page(p):
    """wrap one page (no newlines inside, or explicit \n kept) -> list of lines"""
    lines = []
    for para in p.split('\n'):
        words = para.split(' ')
        cur = ''
        for w in words:
            if not cur:
                cur = w
            elif width(cur) + 1 + width(w) <= LINE:
                cur += ' ' + w
            else:
                lines.append(cur); cur = w
            while width(cur) > LINE:  # very long token
                lines.append(cur[:LINE]); cur = cur[LINE:]
        lines.append(cur)
    return lines

def layout_dialogue(ko):
    """ko: pages separated by blank line ('\n\n'). Single '\n' = forced line break.
    Leading/trailing #color codes are kept verbatim. Returns CRLF text."""
    if ko.startswith('='):  # raw: lines exactly as given (choice menus)
        return ko[1:].replace('\n', '\r\n')
    pre = ''
    m = re.match(r'^(#(?:\d+,){16})', ko)
    if m: pre, ko = m.group(1), ko[len(m.group(1)):]
    post = ''
    if ko.endswith('##'): post, ko = '##', ko[:-2]
    pages = [p.strip(' ') for p in re.split(r'\n\s*\n', ko.strip('\n'))]
    allines = []
    for k, p in enumerate(pages):
        ls = wrap_page(p)
        if k < len(pages) - 1:
            ls += [''] * (-len(ls) % PAGE)
        allines += ls
    return pre + '\r\n'.join(allines) + post

# ---------------------------------------------------------------- pds
def patch_pds(fn, b, tr_dlg, tr_names):
    b = bytearray(b)
    n = struct.unpack('>I', b[4:8])[0]
    offs = list(struct.unpack('>%dI' % n, b[12:12 + 4 * n]))
    s8 = offs[8]
    if not s8: return bytes(b), 0
    cnt = b[s8]
    done = 0
    for sec in (8, 9):
        s = offs[sec]
        for i in range(cnt):
            r = s + 8 + i * 0x438
            key = f'{fn}:{i}'
            en_name = b[offs[8] + 8 + i * 0x438: offs[8] + 8 + i * 0x438 + 0x20].split(b'\0')[0].decode('latin1')
            ko = tr_dlg.get(key)
            if ko:
                t = E.enc(layout_dialogue(ko))
                assert len(t) < 0x400, (key, len(t))
                b[r + 0x20:r + 0x420] = t + b'\0' * (0x400 - len(t))
                done += 1
            if en_name and en_name in tr_names:
                nm = E.enc(tr_names[en_name]); assert len(nm) < 0x20
                b[r:r + 0x20] = nm + b'\0' * (0x20 - len(nm))
    return bytes(b), done

# ---------------------------------------------------------------- res (RRED)
def patch_res(fn, b, tr):
    global LINE
    cnt = struct.unpack('>H', b[10:12])[0]
    ents = [struct.unpack('>II', b[12 + 8 * i:20 + 8 * i]) for i in range(cnt)]
    hdr = bytearray(b[:12 + 8 * cnt])
    body = bytearray()
    base = 12 + 8 * cnt
    for k, (i, o) in enumerate(ents):
        s = b[o:].split(b'\0')[0]
        key = f'{fn}:{i}'
        if key in tr and tr[key]:
            t = tr[key].replace('\r\n', '\n')
            if fn == 'Exp.res':
                old, LINE = LINE, 17
                s = E.enc('\r\n'.join(wrap_page(t))); LINE = old
            elif fn == 'WorldMap.res' and i >= 200:
                old, LINE = LINE, 36
                s = E.enc(layout_dialogue(t)); LINE = old
            else:
                s = E.enc(t.replace('\n', '\r\n'))
        struct.pack_into('>II', hdr, 12 + 8 * k, i, base + len(body))
        body += s + b'\0'
    out = hdr + body
    out += b'\0' * (-len(out) % 4)
    struct.pack_into('>I', out, 4, len(out))
    return bytes(out)

# ---------------------------------------------------------------- CRD
def patch_crd(fn, b, tr):
    b = bytearray(b)
    for e in load('crd'):
        f, o = e['id'].split(':')
        if f != fn: continue
        o = int(o, 16)
        ko = tr.get(e['en'])
        if not ko: continue
        s = E.enc(ko)
        assert len(s) <= e['cap'], (e, ko, len(s))
        b[o:o + e['cap'] + 1] = s + b'\0' * (e['cap'] + 1 - len(s))
    return bytes(b)

# ---------------------------------------------------------------- mel pools
def mel_sections(b, fn):
    if fn.lower().endswith('.men'):
        return [len(b)]
    n = struct.unpack('>I', b[4:8])[0]
    return sorted([x for x in struct.unpack('>%dI' % n, b[8:8 + 4 * n]) if x] + [len(b)])

def mel_pools(b, fn):
    secs = mel_sections(b, fn)
    pools = []
    for m in re.finditer(rb'\xff\xff(?:\x00\x00)?(?=[\x20-\xfe])', b):
        st = p = m.end()
        strs = []
        ok = True
        while p < len(b) and b[p] != 0:
            e = b.find(b'\0', p)
            if e < 0: ok = False; break
            s = b[p:e]
            if any(c < 0x20 or c == 0x7f for c in s): ok = False; break
            strs.append(s); p = e + 1
        if not ok or not strs or not any(re.search(rb'[A-Za-z]{2}', s) for s in strs): continue
        q = p
        while q < len(b) and b[q] == 0: q += 1
        bnd = [x for x in secs if p < x <= q]
        at_sec_end = bool(bnd)
        if bnd: q = bnd[0]
        pools.append((st, p, q, at_sec_end, strs))
    return pools

def mel_repoint(orig, b, starts, lo, hi, old_p, new_p):
    """strings are referenced by section-relative u32 offsets; move refs old_p -> new_p"""
    if old_p == new_p: return 0
    base = max(x for x in starts if x <= old_p); nxt = min([x for x in starts if x > old_p] + [len(orig)])
    pat = struct.pack('>I', old_p - base)
    n = 0
    for m in re.finditer(re.escape(pat), orig):
        o = m.start()
        if o % 4 == 0 and base <= o < nxt and not lo <= o < hi:
            struct.pack_into('>I', b, o, new_p - base); n += 1
    return n

def patch_mel(fn, b, tr, report):
    orig = bytes(b)
    starts = sorted(set([0] + mel_sections(orig, fn)))
    b = bytearray(b)
    covered = set()
    for st, end, q, at_end, strs in mel_pools(bytes(b), fn):
        new = b''
        moves = []
        p = st
        for s in strs:
            k = s.decode('latin1')
            moves.append((p, st + len(new)))
            p += len(s) + 1
            new += (E.enc(tr[k]) if k in tr else s) + b'\0'
        cap = (q - st - 1) if at_end else (end - st)
        if len(new) > cap:
            report.append(f'mel overflow {fn}:{st:x} {len(new)}>{cap} ' + '|'.join(tr.get(s.decode("latin1"), s.decode("latin1")) for s in strs))
            continue
        lim = max(end, st + len(new))
        b[st:lim] = new + b'\0' * (lim - st - len(new))
        covered.update(range(st, end))
        for op, np_ in moves: mel_repoint(orig, b, starts, st, max(end, lim), op, np_)
    # leftovers: fixed in-place slots from extraction
    for e in load('mel'):
        f, o = e['id'].split(':')
        if f != fn: continue
        o = int(o, 16)
        if o in covered: continue
        new = b''; moves = []; p = o
        for s in e['en']:
            moves.append((p, o + len(new))); p += len(s.encode('latin1')) + 1
            new += (E.enc(tr[s]) if s in tr else s.encode('latin1')) + b'\0'
        if len(new) > e['len']:
            report.append(f'mel slot overflow {fn}:{o:x} {len(new)}>{e["len"]}'); continue
        b[o:o + e['len']] = new + b'\0' * (e['len'] - len(new))
        for op, np_ in moves: mel_repoint(orig, b, starts, o, o + e['len'], op, np_)
    return bytes(b)

# ---------------------------------------------------------------- Sp.TEX font atlas
def build_sptex(b, chars):
    A, I, H = F.build_atlas(chars)
    data = F.to_ia4(A, I)
    F.preview(A, I, W + '/font_preview.png')
    n = struct.unpack('>I', b[4:8])[0]
    offs = list(struct.unpack('>%dI' % n, b[8:8 + 4 * n]))
    o36 = offs[36]
    hdr = bytearray(b[o36:o36 + 0x20])
    struct.pack_into('>I', hdr, 0, len(data) + 0x20)
    struct.pack_into('>HH', hdr, 12, 1024, H)
    out = bytearray(b[:o36]) + hdr + data
    out += b'\0' * (-len(out) % 32)
    struct.pack_into('>I', out, 0, len(out))
    return bytes(out), H

# ---------------------------------------------------------------- DOL strings
def patch_dol_strings(d, tr, report):
    """tr: {hexaddr: ko}. in place if fits, else relocate via refs."""
    import dolstr
    allstr = {s['addr']: s for s in json.load(open(TX + 'dolstr_all.json', encoding='utf8'))}
    reloc = []
    for k, ko in tr.items():
        a = int(k, 16)
        s = allstr[a]
        data = E.enc(ko.replace('\r\n', '\n'))
        if len(data) + 1 <= s['slot']:
            d.wbytes(a, data + b'\0' * (s['slot'] - len(data)))
        else:
            kinds = {r[0] for r in s['refs']}
            if not s['refs'] or not kinds <= {'lisaddi', 'r2', 'r13', 'ptr'}:
                report.append(f'DOL overflow (no reloc) {k} {len(data)+1}>{s["slot"]} {ko!r}')
                continue
            reloc.append((a, data + b'\0', s['refs']))
    return reloc

def apply_relocs(d, reloc, str_addr, stubs):
    from asm import lis, addi, ha, lo, b as br
    for a, data, refs in reloc:
        na = str_addr[a]
        for kind, where in refs:
            if kind == 'lisaddi':
                la, aa = where
                wl = d.r32(la); wa = d.r32(aa)
                d.w32(la, (wl & 0xffff0000) | ha(na))
                d.w32(aa, (wa & 0xffff0000) | (lo(na) & 0xffff))
            elif kind == 'ptr':
                d.w32(where, na)
            elif kind in ('r2', 'r13'):
                w = d.r32(where)
                rd = (w >> 21) & 31
                st = stubs[(a, where)]
                d.w32(where, br(where, st))

# ---------------------------------------------------------------- ISO
def build_iso(dst, files, dol_bytes):
    """files: {fst path (e.g. 'game/Sp.TEX'): bytes}"""
    shutil.copyfile(ORIG_ISO, dst)
    f = open(dst, 'r+b')
    f.seek(0x420); dol_off, fst_off, fst_sz = struct.unpack('>III', f.read(12))
    f.seek(fst_off); fst = bytearray(f.read(fst_sz))
    n = struct.unpack('>I', fst[8:12])[0]
    strt = n * 12
    def nm(o): return fst[strt + o:fst.index(b'\0', strt + o)].decode()
    paths = {}
    def walk(i, end, pre):
        while i < end:
            w0, a, s = struct.unpack('>III', fst[i * 12:i * 12 + 12])
            name = nm(w0 & 0xffffff)
            if w0 >> 24:
                walk(i + 1, s, pre + name + '/'); i = s
            else:
                paths[pre + name] = i; i += 1
    walk(1, n, '')
    ents = sorted((struct.unpack('>III', fst[i * 12:i * 12 + 12])[1:], p) for p, i in paths.items())
    end = max(o + s for (o, s), p in ents)
    nxt = {}
    for k in range(len(ents)):
        (o, s), p = ents[k]
        nxt[p] = ents[k + 1][0][0] if k + 1 < len(ents) else o + s
    def alloc(size):
        nonlocal end
        end = (end + 0x7fff) & ~0x7fff
        o = end; end += size
        return o
    for p, data in files.items():
        i = paths[p]
        w0, o, s = struct.unpack('>III', fst[i * 12:i * 12 + 12])
        if len(data) > nxt[p] - o:
            o = alloc(len(data))
        f.seek(o); f.write(data)
        struct.pack_into('>III', fst, i * 12, w0, o, len(data))
    # dol
    no = alloc(len(dol_bytes))
    f.seek(no); f.write(dol_bytes)
    if 'GameUS.dol' in paths:
        i = paths['GameUS.dol']; w0 = struct.unpack('>I', fst[i * 12:i * 12 + 4])[0]
        struct.pack_into('>III', fst, i * 12, w0, no, len(dol_bytes))
    f.seek(0x420); f.write(struct.pack('>I', no))
    f.seek(fst_off); f.write(fst)
    f.close()
    assert end <= 1459978240, hex(end)

# ---------------------------------------------------------------- main
def main(out_iso):
    report = []
    tr_dlg = load_tr('dialogue'); tr_names = load_tr('names'); tr_res = load_tr('res')
    tr_crd = load_tr('crd'); tr_mel = load_tr('mel'); tr_dol = load_tr('dol')
    for t in (tr_dlg, tr_names, tr_res, tr_crd, tr_mel, tr_dol):
        for v in t.values(): E.add_text(v)
    E.add_text('카티아')
    print('glyphs', len(E.chars))
    files = {}
    for f in sorted(glob.glob(G + 's*.pds')):
        fn = os.path.basename(f)
        nb, n = patch_pds(fn, open(f, 'rb').read(), tr_dlg, tr_names)
        if n or tr_names: files['game/' + fn] = nb
    for f in sorted(glob.glob(G + '*.res')):
        fn = os.path.basename(f)
        if any(k.startswith(fn + ':') for k in tr_res):
            files['game/' + fn] = patch_res(fn, open(f, 'rb').read(), tr_res)
    if tr_crd:
        for fn in ('Menu.CRD', 'Menus.CRD'):
            if os.path.exists(G + fn): files['game/' + fn] = patch_crd(fn, open(G + fn, 'rb').read(), tr_crd)
    if tr_mel:
        for f in glob.glob(G + '*.mel') + glob.glob(G + '*.Men'):
            fn = os.path.basename(f)
            files['game/' + fn] = patch_mel(fn, open(f, 'rb').read(), tr_mel, report)
    sp, H = build_sptex(open(G + 'Sp.TEX', 'rb').read(), E.chars)
    files['game/Sp.TEX'] = sp
    import images
    files.update(images.build_all())
    assert len(E.chars) <= 1024, len(E.chars)
    d = dolpatch.build(len(E.chars), H)
    reloc = patch_dol_strings(d, tr_dol, report)
    for a, data, refs in reloc:
        report.append('DOL string too long: %x %r' % (a, data))
    # "No" (4-byte slots) -> repoint r2-relative refs to a debug-label slot holding the Korean text
    allstr = {s['addr']: s for s in json.load(open(TX + 'dolstr_all.json', encoding='utf8'))}
    # "Use" -> existing "사용"; "OK" -> debug-label slot " DISP " holding "확인"
    for src, dst in ((0x802ca710, 0x802cb350), (0x802cc1c8, 0x802cb350),
                     (0x802ca6b4, 0x802ca4bc), (0x802ca668, 0x802cb358)):
        for kind, where in allstr[src]['refs']:
            if kind == 'ptr':
                assert d.r32(where) == src
                d.w32(where, dst); continue
            assert kind == 'r2'
            w = d.r32(where)
            assert (w >> 16) & 31 == 2 and (w & 0xffff) == (src - 0x802d22e0) & 0xffff
            d.w32(where, (w & 0xffff0000) | ((dst - 0x802d22e0) & 0xffff))
    build_iso(out_iso, files, bytes(d.b))
    for r in report: print('!', r)
    print('built', out_iso, len(files), 'files')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else OUT + '/test.iso')
