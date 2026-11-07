"""Redraw image text. Returns {fst path: bytes}."""
import os
import struct, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(chr(92), '/')
G = W + '/ext/files/game/'
MAIN = W + '/SeoulHangangEB.ttf'
SMALL = W + '/Galmuri11.ttf'      # only for very small (<=16px) text

# (file, entry, text, align)   align: c=center, l=left
JOBS = [
    ('Title.TEX', 1, '새 게임', 'c'), ('Title.TEX', 2, '불러오기', 'c'), ('Title.TEX', 3, '옵션', 'c'),
    ('Title.TEX', 4, '2인 대전', 'c'), ('Title.TEX', 6, 'START 버튼을 누르세요', 'c'),
    ('menu.TEX', 39, '포획 투척', 'l'), ('menu.TEX', 40, '메뉴 표시', 'l'), ('menu.TEX', 41, '이동', 'l'),
    ('menu.TEX', 42, '카메라 조작', 'l'), ('menu.TEX', 43, '카드', 'l'), ('menu.TEX', 44, '버림', 'l'),
    ('menu.TEX', 45, '사용', 'l'), ('menu.TEX', 46, '회전', 'l'),
    ('menu.TEX', 64, '쓰러뜨린 몬스터', 'l'), ('menu.TEX', 65, '획득 경험치', 'l'),
    ('menu.TEX', 66, '입수한 카드', 'l'), ('menu.TEX', 67, '스테이지 클리어', 'l'),
    ('menu.TEX', 68, '스테이지 보너스', 'l'),
    ('menu.TEX', 91, '경험', 'l'), ('menu.TEX', 93, '카드', 'l'), ('menu.TEX', 94, '덱의 카드', 'l'),
    ('menu.TEX', 97, '수집', 'l'),
    ('WorldMap.TEX', 13, '알란제 성', 'c'), ('WorldMap.TEX', 14, '로왈 평원', 'c'),
    ('WorldMap.TEX', 15, '블레순', 'c'), ('WorldMap.TEX', 16, '약재상', 'c'),
    ('WorldMap.TEX', 17, '달녹 계곡', 'c'), ('WorldMap.TEX', 18, '그레일 성', 'c'),
    ('WorldMap.TEX', 19, '이프렉 광산', 'c'), ('WorldMap.TEX', 20, '셰이엘 통로', 'c'),
    ('WorldMap.TEX', 21, '묘지', 'c'), ('WorldMap.TEX', 22, '그롬툴 사막', 'c'),
    ('WorldMap.TEX', 23, '사르반 다리', 'c'), ('WorldMap.TEX', 24, '로바흐', 'c'),
    ('WorldMap.TEX', 25, '켄다리 성', 'c'), ('WorldMap.TEX', 26, '럼스테드', 'c'),
    ('WorldMap.TEX', 27, '베른덴 들판', 'c'), ('WorldMap.TEX', 28, '위트 성', 'c'),
    ('WorldMap.TEX', 29, '그렌포엘 교회', 'c'), ('WorldMap.TEX', 30, '베스트리엘 호수', 'c'),
    ('WorldMap.TEX', 31, '투기장', 'c'), ('WorldMap.TEX', 32, '잔던 산', 'c'),
    ('WorldMap.TEX', 33, '루아록', 'c'), ('WorldMap.TEX', 34, '브로크 신전', 'c'),
    ('WorldMap.TEX', 35, '블랙 얄워그', 'c'), ('WorldMap.TEX', 36, '테르존', 'c'),
    ('WorldMap.TEX', 37, '요정의 신전', 'c'), ('WorldMap.TEX', 38, '후폰젠의 집', 'c'),
    ('WorldMap.TEX', 39, '아멘탕크 신전', 'c'), ('WorldMap.TEX', 41, '클리어 조건', 'c'),
]

def render(text, w, h, align):
    small = h <= 16
    font_path = SMALL if small else MAIN
    stroke = 1 if not small else 0
    best = None
    for size in range(h + 4, 6, -1):
        f = ImageFont.truetype(font_path, size)
        bb = f.getbbox(text, stroke_width=stroke)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        if tw <= w - 2 and th <= h:
            best = (f, bb, tw, th); break
        if small and size <= 12:
            f = ImageFont.truetype(font_path, 12); bb = f.getbbox(text); best = (f, bb, bb[2]-bb[0], bb[3]-bb[1]); break
    f, bb, tw, th = best
    img = Image.new('LA', (w, h), (0, 0))
    d = ImageDraw.Draw(img)
    x = (w - tw) // 2 - bb[0] if align == 'c' else 1 - bb[0]
    y = (h - th) // 2 - bb[1]
    if small:
        d.text((x, y), text, font=f, fill=(255, 255))
        # 1px dark shadow for legibility
        a = np.array(img); sh = np.zeros_like(a)
        sh[1:, 1:] = a[:-1, :-1]; sh[..., 0] = 0
        out = sh.copy(); m = a[..., 1] > 0; out[m] = a[m]
        return out
    d.text((x, y), text, font=f, fill=(255, 255), stroke_width=stroke, stroke_fill=(40, 255))
    return np.array(img)

def tiles(a, bw, bh):
    h, w = a.shape[:2]
    H = (h + bh - 1) // bh * bh; Wd = (w + bw - 1) // bw * bw
    p = np.zeros((H, Wd) + a.shape[2:], a.dtype); p[:h, :w] = a
    for by in range(0, H, bh):
        for bx in range(0, Wd, bw):
            yield p[by:by + bh, bx:bx + bw]

def enc(a, fmt):
    out = bytearray()
    if fmt == 2:   # IA4
        for t in tiles(a, 8, 4):
            for i, al in t.reshape(-1, 2):
                out.append(((al >> 4) << 4) | (i >> 4))
    elif fmt == 3:  # IA8
        for t in tiles(a, 4, 4):
            for i, al in t.reshape(-1, 2):
                out += bytes([al, i])
    else:
        raise ValueError(fmt)
    return bytes(out)

def patch_tex(b, jobs):
    b = bytearray(b)
    n = struct.unpack('>I', b[4:8])[0]
    offs = struct.unpack('>%dI' % n, b[8:8 + 4 * n])
    for idx, text, al in jobs:
        o = offs[idx]
        fmt = b[o + 10]; w, h = struct.unpack('>HH', b[o + 12:o + 16])
        data = enc(render(text, w, h, al), fmt)
        b[o + 0x20:o + 0x20 + len(data)] = data
    return bytes(b)

def load_gtx():
    p = G + 'load/000.gtx'
    b = bytearray(open(p, 'rb').read())
    w, h = 256, 64
    f = ImageFont.truetype(MAIN, 30)
    img = Image.new('L', (w * 2, h), 0)
    d = ImageDraw.Draw(img)
    t = '로딩 중'
    bb = f.getbbox(t)
    d.text((45 + (158 - (bb[2] - bb[0])) // 2 - bb[0], 18 + (30 - (bb[3] - bb[1])) // 2 - bb[1]), t, font=f, fill=255)
    img = img.transform(img.size, Image.AFFINE, (1, 0.2, -6, 0, 1, 0), Image.BILINEAR).crop((0, 0, w, h))
    a = np.array(img) >= 128
    out = bytearray()
    for t in tiles(a, 4, 4):
        for v in t.reshape(-1):
            out += b'\xff\xff' if v else b'\0\0'
    b[0x20:0x20 + len(out)] = out
    return bytes(b)

def build_all(preview=None):
    files = {}
    by = {}
    for fn, i, t, al in JOBS: by.setdefault(fn, []).append((i, t, al))
    for fn, jobs in by.items():
        files['game/' + fn] = patch_tex(open(G + fn, 'rb').read(), jobs)
    files['game/load/000.gtx'] = load_gtx()
    return files

if __name__ == '__main__':
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    import gtx
    fs = build_all()
    ims = []
    for fn, jobs in [(f, [j for j in JOBS if j[0] == f]) for f in ('Title.TEX', 'menu.TEX', 'WorldMap.TEX')]:
        b = fs['game/' + fn]
        offs = gtx.read_tex(b)
        for _, i, _, _ in jobs: ims.append(gtx.decode(b, offs[i]).convert('RGBA'))
    e = bytearray(0x20) + fs['game/load/000.gtx'][0x20:]; e[10] = 3; e[12:16] = bytes([1, 0, 0, 64])
    ims.append(gtx.decode(bytes(e), 0).convert('RGBA'))
    Wd = 1024; x = y = rh = 0; pos = []
    for im in ims:
        if x + im.width > Wd: x = 0; y += rh + 4; rh = 0
        pos.append((x, y)); x += im.width + 4; rh = max(rh, im.height)
    S = Image.new('RGBA', (Wd, y + rh), (60, 0, 60, 255))
    for im, p in zip(ims, pos): S.alpha_composite(im, p)
    S.save(sys.argv[1])
