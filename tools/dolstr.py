"""Find translatable DOL strings and their references."""
import os
import re, struct, json, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(chr(92), '/') + '/tools')
from ppc import B, SEG, a2o, o2a, R2, R13

CODE = [(o, ad, s) for o, ad, s in SEG[:2]]


def scan_refs():
    """return dict target_addr -> list of (kind, insn_addr)"""
    refs = {}
    def add(t, k, a): refs.setdefault(t, []).append((k, a))
    for o, ad, s in CODE:
        words = struct.unpack('>%dI' % (s // 4), B[o:o + s])
        for i, w in enumerate(words):
            op = w >> 26
            a = ad + 4 * i
            if op == 15 and (w >> 16) & 31 == 0:  # lis rd, hi
                rd = (w >> 21) & 31; hi = w & 0xffff
                for k in range(1, 40):
                    if i + k >= len(words): break
                    w2 = words[i + k]
                    op2 = w2 >> 26
                    ra2 = (w2 >> 16) & 31; rt2 = (w2 >> 21) & 31
                    if op2 in (14, 24) and ra2 == rd if op2 == 14 else False:
                        lo = w2 & 0xffff; lo = lo - 0x10000 if lo & 0x8000 else lo
                        add(((hi << 16) + lo) & 0xffffffff, 'lisaddi', (a, ad + 4 * (i + k)))
                    if op2 == 14 and ra2 == rd:
                        if rt2 == rd: break
                        continue
                    if op2 in (18,) or w2 == 0x4e800020: break
                    if rt2 == rd and op2 not in (36, 37, 38, 44, 52, 54): break
            elif op == 14:
                ra = (w >> 16) & 31; d = w & 0xffff; d = d - 0x10000 if d & 0x8000 else d
                if ra == 13: add(R13 + d, 'r13', a)
                if ra == 2: add(R2 + d, 'r2', a)
    # absolute pointers in data
    for o, ad, s in SEG[2:]:
        for x in range(o, o + s - 3, 4):
            v = struct.unpack('>I', B[x:x + 4])[0]
            if 0x8010e000 <= v < 0x802d0000:
                add(v, 'ptr', ad + x - o)
    return refs


def strings():
    out = []
    for o, ad, s in SEG[2:]:
        seg = B[o:o + s]
        for m in re.finditer(rb'[\x20-\x7e\n\r]{2,}\x00', seg):
            st = m.start()
            if st > 0 and seg[st - 1] != 0: continue
            txt = m.group()[:-1]
            if not re.search(rb'[A-Za-z]{2}', txt): continue
            e = m.end()
            while e < len(seg) and seg[e] == 0 and (e % 4): e += 1
            out.append({'addr': ad + st, 'en': txt.decode('latin1'), 'slot': e - st})
    return out


if __name__ == '__main__':
    refs = scan_refs()
    res = []
    for s in strings():
        r = refs.get(s['addr'], [])
        s['refs'] = r
        res.append(s)
    json.dump(res, open(os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(chr(92), '/') + r'/text/dolstr_all.json', 'w', encoding='utf8'), ensure_ascii=False, indent=0)
    for s in res:
        print(hex(s['addr']), s['slot'], len(s['refs']), [k for k, _ in s['refs']][:4], repr(s['en'])[:60])
