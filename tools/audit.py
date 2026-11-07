"""Full residual-text audit on patched output."""
import sys, re, io, contextlib, os
sys.path.insert(0, os.path.dirname(__file__))
import build as B
cap = {}
B.build_iso = lambda d, f, dol: cap.update(files=f, dol=dol)
with contextlib.redirect_stdout(io.StringIO()) as o:
    B.main('x')
print(o.getvalue()[-300:])
f = cap['files']; f['GameUS.dol'] = cap['dol']
# include unpatched text files too
for p in ['Detail.Men', 'Labo.mel', 'Mc.mel', 'Report.MEL', 'Shop_us.mel', 'WorldMap_us.mel', 'Menu_us.mel', 'VsMenu.mel']:
    f.setdefault('game/' + p, open(B.G + p, 'rb').read())
BAD = re.compile(r'[_/\\]|\.\w{2,3}\b|%0|rror|file|Inf|NaN')
WORD = re.compile(r'\b[A-Za-z][a-z]{2,}\b')
for k in sorted(f):
    if k.endswith(('.TEX', '.gtx', '.tex')): continue
    b = f[k]
    for m in re.finditer(rb'[\x20-\x7e\r\n]{3,}', b):
        s = m.group().decode()
        if k.endswith('.dol') and not (0x10b000 < m.start() < 0x116300 or m.start() > 0x133000): continue
        if WORD.search(s) and sum(c.isalpha() or c in " .,!?'\r\n" for c in s) / len(s) > 0.85 and not BAD.search(s):
            print('EN', k, hex(m.start()), repr(s[:70]))
JP = re.compile(rb'(?:[\x82\x83\x88-\x9f][\x40-\xfc]){3,}')
for k in sorted(f):
    if not k.endswith(('.pds', '.mel', '.Men', '.MEL', '.res', '.CRD', '.dol')): continue
    b = f[k]; n = 0
    for m in JP.finditer(b):
        try: s = m.group().decode('cp932')
        except Exception: continue
        if re.search('[぀-ヿ一-鿿]{3}', s):
            n += 1
            if n <= 3: print('JP', k, hex(m.start()), s[:30])
    if n > 3: print('JP', k, 'total', n)
