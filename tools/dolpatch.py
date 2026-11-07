"""Build patched GameUS.dol: Korean glyph support + relocated strings."""
import os
import struct
from asm import *

ORIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(chr(92), '/') + r'/ext/files/GameUS.dol'
NEWBASE = 0x80001800          # free low-memory area (up to 0x80003000)

MTXSCALE = 0x800c7bc8
LOADTEXMTX = 0x800e0b6c
SETTEVORDER = 0x800dfbd4


class Dol:
    def __init__(self, path=ORIG):
        self.b = bytearray(open(path, 'rb').read())
        self.off = list(struct.unpack('>18I', self.b[0:72]))
        self.addr = list(struct.unpack('>18I', self.b[72:144]))
        self.size = list(struct.unpack('>18I', self.b[144:216]))

    def a2o(self, a):
        for i in range(18):
            if self.size[i] and self.addr[i] <= a < self.addr[i] + self.size[i]:
                return self.off[i] + a - self.addr[i]
        raise KeyError(hex(a))

    def r32(self, a): return struct.unpack('>I', self.b[self.a2o(a):self.a2o(a) + 4])[0]
    def w32(self, a, v): o = self.a2o(a); self.b[o:o + 4] = struct.pack('>I', v & 0xffffffff)
    def wbytes(self, a, data): o = self.a2o(a); self.b[o:o + len(data)] = data

    def add_text_section(self, addr, data):
        i = next(k for k in range(7) if self.size[k] == 0)
        data = bytes(data) + b'\0' * (-len(data) % 32)
        o = len(self.b) + (-len(self.b) % 32)
        self.b += b'\0' * (o - len(self.b)) + data
        self.off[i], self.addr[i], self.size[i] = o, addr, len(data)
        self.b[0:216] = struct.pack('>18I', *self.off) + struct.pack('>18I', *self.addr) + struct.pack('>18I', *self.size)

    def save(self, path):
        open(path, 'wb').write(self.b)


def rlwimi(ra, rs, sh, mb, me): return (20 << 26) | (rs << 21) | (ra << 16) | (sh << 11) | (mb << 6) | (me << 1)

R2 = 0x802d22e0
# per drawer: (cmp addr, lead reg, char reg, C0 block start, fallback start, k_s/k_t const offset (r2), r2 offsets used by fallback lfs f1/f2)
DRAWERS = [
    dict(cmp=0x8003e2f4, lead=3, ch=4, blk=0x8003e2fc, fb=0x8003e3f4, k=-0x75c4),
    dict(cmp=0x8003f2a4, lead=6, ch=5, blk=0x8003f2ac, fb=0x8003f3a4, k=-0x75a0),
]


def build(max_glyphs, atlas_h):
    """Korean glyphs: lead 0x82.., trail 0x80..0xff -> idx; atlas 1024 x atlas_h IA4, 32x32 cells, 32 per row.
    Re-purposes the unused Latin-1 (lead>=0xC0) path of both glyph drawers."""
    assert max_glyphs <= 1024 and atlas_h <= 1024
    d = Dol()
    f2i = lambda v: struct.unpack('>I', struct.pack('>f', v))[0]
    for D_ in DRAWERS:
        c, L, C, blk, fb = D_['cmp'], D_['lead'], D_['ch'], D_['blk'], D_['fb']
        assert d.r32(c) == cmpwi(L, 0xc0), hex(d.r32(c))
        d.w32(c, cmpwi(L, 0x82))
        code = [addi(L, L, -0x82), clrlwi(0, C, 25), rlwimi(0, L, 7, 0, 24),
                rlwinm(31, 0, 5, 22, 26), rlwinm(30, 0, 0, 0, 26)]
        for i, w in enumerate(code): d.w32(blk + 4 * i, w)
        d.w32(blk + 4 * len(code), b(blk + 4 * len(code), fb))
        ks, kt = blk + 0x20, blk + 0x24          # dead words of old C0 block hold our scales
        d.w32(ks, f2i(1.0 / 1024)); d.w32(kt, f2i(1.0 / atlas_h))
        assert d.r32(fb + 4) == li(31, 0x1c0) and d.r32(fb + 12) == li(30, 0x20)
        assert (d.r32(fb + 8) >> 26) == 48 and (d.r32(fb + 16) >> 26) == 48
        d.w32(fb + 4, lis(5, ha(ks))); d.w32(fb + 8, lfs(1, lo(ks), 5))
        d.w32(fb + 12, lis(5, ha(kt))); d.w32(fb + 16, lfs(2, lo(kt), 5))
        assert d.r32(fb + 0x3c) == li(5, 0), hex(d.r32(fb + 0x3c))
        d.w32(fb + 0x3c, li(5, 1))
    return d
