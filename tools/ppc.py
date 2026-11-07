import os
import struct,sys,capstone
B=open(os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(chr(92), '/') + r'/ext/files/GameUS.dol','rb').read()
off=struct.unpack('>18I',B[0:72]);addr=struct.unpack('>18I',B[72:144]);sz=struct.unpack('>18I',B[144:216])
SEG=[(off[i],addr[i],sz[i]) for i in range(18) if sz[i]]
def a2o(a):
    for o,ad,s in SEG:
        if ad<=a<ad+s: return o+a-ad
def o2a(x):
    for o,ad,s in SEG:
        if o<=x<o+s: return ad+x-o
md=capstone.Cs(capstone.CS_ARCH_PPC,capstone.CS_MODE_32|capstone.CS_MODE_BIG_ENDIAN)
def dis(a,n):
    o=a2o(a)
    for i in md.disasm(B[o:o+4*n],a): print(f'{i.address:08x}: {i.mnemonic} {i.op_str}')
if __name__=='__main__':
    a=int(sys.argv[1],16); n=int(sys.argv[2]) if len(sys.argv)>2 else 40
    dis(a,n)
R2=0x802d22e0; R13=0x802d18e0
def xref(target):
    res=[]
    for o,ad,s in SEG[:2]:
        for x in range(o,o+s,4):
            w=struct.unpack('>I',B[x:x+4])[0]
            ra=(w>>16)&31; d=w&0xffff; d=d-0x10000 if d&0x8000 else d
            op=w>>26
            if op in (14,32,33,34,35,36,37,40,41,42,44,45,48,50,52,54) and ((ra==2 and R2+d==target) or (ra==13 and R13+d==target)):
                res.append(ad+x-o)
    return res
def callers(target):
    res=[]
    for o,ad,s in SEG[:2]:
        for x in range(o,o+s,4):
            w=struct.unpack('>I',B[x:x+4])[0]
            if w>>26==18:
                li=w&0x3fffffc
                if li&0x2000000: li-=0x4000000
                a=ad+x-o
                if (li if w&2 else a+li)==target: res.append(a)
    return res
