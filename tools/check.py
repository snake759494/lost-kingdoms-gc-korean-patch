import os
import sys, json, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(chr(92), '/') + '/tools')
import build as B
tr = B.load_tr('dialogue')
d = {x['id']: x for x in json.load(open(B.TX + 'dialogue.json', encoding='utf8'))}
bad = 0
for k, v in tr.items():
    if k not in d: print('unknown key', k); bad += 1; continue
    out = B.layout_dialogue(v)
    lines = out.split('\r\n')
    for l in lines:
        if B.width(l) > B.LINE and not v.startswith('='):
            print('long', k, l); bad += 1
    if v.startswith('='):
        for l in lines:
            if B.width(l) > B.LINE: print('rawlong', k, l); bad += 1
    # pages that overflow 4 lines
    pages = re.split(r'\n\s*\n', v.lstrip('=').strip('\n'))
    for p in pages:
        n = len(B.wrap_page(p))
        if n > 4 and not v.startswith('='): print('page>4', k, n, p.replace('\n', '/')[:60]); bad += 1
    B.E.add_text(v)
    if len(B.E.enc(out)) >= 0x400: print('toolong', k); bad += 1
print('entries', len(tr), 'issues', bad, 'glyphs', len(B.E.chars))
