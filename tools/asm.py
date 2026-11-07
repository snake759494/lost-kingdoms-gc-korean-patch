"""Minimal PowerPC encoder for the patches."""
import struct

def _s16(v):
    assert -0x8000 <= v < 0x8000, hex(v)
    return v & 0xffff

def D(op, rt, ra, imm): return (op << 26) | (rt << 21) | (ra << 16) | _s16(imm)
def DU(op, rt, ra, imm): return (op << 26) | (rt << 21) | (ra << 16) | (imm & 0xffff)
def X(op, rt, ra, rb, xo, rc=0): return (op << 26) | (rt << 21) | (ra << 16) | (rb << 11) | (xo << 1) | rc

def addi(rt, ra, v): return D(14, rt, ra, v)
def li(rt, v): return addi(rt, 0, v)
def addis(rt, ra, v): return D(15, rt, ra, v)
def lis(rt, v): return DU(15, rt, 0, v)
def ori(ra, rs, v): return DU(24, rs, ra, v)
def lwz(rt, d, ra): return D(32, rt, ra, d)
def lbz(rt, d, ra): return D(34, rt, ra, d)
def stw(rs, d, ra): return D(36, rs, ra, d)
def stwu(rs, d, ra): return D(37, rs, ra, d)
def lhz(rt, d, ra): return D(40, rt, ra, d)
def lfs(ft, d, ra): return D(48, ft, ra, d)
def mulli(rt, ra, v): return D(7, rt, ra, v)
def cmpwi(ra, v, cr=0): return D(11, cr << 2, ra, v)
def cmplwi(ra, v, cr=0): return DU(10, cr << 2, ra, v)
def rlwinm(ra, rs, sh, mb, me): return (21 << 26) | (rs << 21) | (ra << 16) | (sh << 11) | (mb << 6) | (me << 1)
def clrlwi(ra, rs, n): return rlwinm(ra, rs, 0, n, 31)
def slwi(ra, rs, n): return rlwinm(ra, rs, n, 0, 31 - n)
def srwi(ra, rs, n): return rlwinm(ra, rs, 32 - n, n, 31)
def add(rt, ra, rb): return X(31, rt, ra, rb, 266)
def subf(rt, ra, rb): return X(31, rt, ra, rb, 40)
def mullw(rt, ra, rb): return X(31, rt, ra, rb, 235)
def divwu(rt, ra, rb): return X(31, rt, ra, rb, 459)
def mr(ra, rs): return X(31, rs, ra, rs, 444)
def fmr(ft, fb): return X(63, ft, 0, fb, 72)
def mflr(r): return (31 << 26) | (r << 21) | (8 << 16) | (339 << 1)
def mtlr(r): return (31 << 26) | (r << 21) | (8 << 16) | (467 << 1)
def blr(): return 0x4e800020
def nop(): return 0x60000000

def b(src, dst, link=0):
    off = dst - src
    assert -0x2000000 <= off < 0x2000000 and off % 4 == 0
    return (18 << 26) | (off & 0x3fffffc) | link
def bl(src, dst): return b(src, dst, 1)

def bc(src, dst, bo, bi):
    off = dst - src
    assert -0x8000 <= off < 0x8000
    return (16 << 26) | (bo << 21) | (bi << 16) | (off & 0xfffc)
def blt(src, dst, cr=0): return bc(src, dst, 12, cr * 4 + 0)
def bge(src, dst, cr=0): return bc(src, dst, 4, cr * 4 + 0)
def bgt(src, dst, cr=0): return bc(src, dst, 12, cr * 4 + 1)
def beq(src, dst, cr=0): return bc(src, dst, 12, cr * 4 + 2)
def bne(src, dst, cr=0): return bc(src, dst, 4, cr * 4 + 2)

def ha(v): return ((v >> 16) + (1 if v & 0x8000 else 0)) & 0xffff
def lo(v): v &= 0xffff; return v - 0x10000 if v & 0x8000 else v


class Code:
    """Sequential code builder. items are ints or callables(addr)->int."""
    def __init__(self, base):
        self.base = base
        self.items = []
        self.labels = {}
    @property
    def pc(self): return self.base + 4 * len(self.items)
    def label(self, name): self.labels[name] = self.pc
    def __call__(self, *ins):
        for i in ins: self.items.append(i)
    def L(self, name): return self.labels[name]
    def bytes(self):
        out = b''
        for k, it in enumerate(self.items):
            a = self.base + 4 * k
            v = it(a) if callable(it) else it
            out += struct.pack('>I', v & 0xffffffff)
        return out
