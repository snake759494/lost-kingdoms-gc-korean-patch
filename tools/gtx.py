import struct, numpy as np
from PIL import Image
BLK={0:(8,8,4),1:(8,4,8),2:(8,4,8),3:(4,4,16),4:(4,4,16),5:(4,4,16),6:(4,4,32),8:(8,8,4),9:(8,4,8),14:(8,8,4)}
def c565(v): return ((v>>11&31)*255//31,(v>>5&63)*255//63,(v&31)*255//31,255)
def c5a3(v):
    if v&0x8000: return ((v>>10&31)*255//31,(v>>5&31)*255//31,(v&31)*255//31,255)
    return ((v>>8&15)*17,(v>>4&15)*17,(v&15)*17,(v>>12&7)*255//7)
def read_tex(b):
    n=struct.unpack('>I',b[4:8])[0]
    offs=struct.unpack('>%dI'%n,b[8:8+4*n]); return offs
def hdr(b,o):
    fmt=b[o+10]; w,h=struct.unpack('>HH',b[o+12:o+16]); return fmt,w,h
def decode(b,o):
    fmt,w,h=hdr(b,o); d=b[o+0x20:]
    bw,bh,bpp=BLK[fmt]
    W=(w+bw-1)//bw*bw; H=(h+bh-1)//bh*bh
    img=np.zeros((H,W,4),np.uint8); p=0
    if fmt==14:
        for by in range(0,H,8):
          for bx in range(0,W,8):
            for sy in (0,4):
              for sx in (0,4):
                c0,c1,bits=struct.unpack('>HHI',d[p:p+8]);p+=8
                a=c565(c0);bb=c565(c1)
                if c0>c1: pal=[a,bb,tuple((2*a[i]+bb[i])//3 for i in range(4)),tuple((a[i]+2*bb[i])//3 for i in range(4))]
                else: pal=[a,bb,tuple((a[i]+bb[i])//2 for i in range(4)),(0,0,0,0)]
                for y in range(4):
                  for x in range(4):
                    img[by+sy+y,bx+sx+x]=pal[(bits>>(30-2*(y*4+x)))&3]
        return Image.fromarray(img[:h,:w])
    for by in range(0,H,bh):
      for bx in range(0,W,bw):
        for y in range(bh):
          for x in range(bw):
            if fmt==0:
              v=d[p>>1]; v=(v>>4 if p&1==0 else v&15)*17; p+=1; px=(v,v,v,v)
            elif fmt==2:
              v=d[p];p+=1; i=(v&15)*17;a=(v>>4)*17; px=(i,i,i,a)
            elif fmt==3:
              a,i=d[p],d[p+1];p+=2; px=(i,i,i,a)
            elif fmt==1:
              v=d[p];p+=1;px=(v,v,v,v)
            elif fmt==5:
              v=struct.unpack('>H',d[p:p+2])[0];p+=2;px=c5a3(v)
            elif fmt==4:
              v=struct.unpack('>H',d[p:p+2])[0];p+=2;px=c565(v)
            else: return None
            img[by+y,bx+x]=px
    return Image.fromarray(img[:h,:w])
