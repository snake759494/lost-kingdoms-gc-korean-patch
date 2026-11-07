import os
import struct,re,json,glob,os,sys
G=os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(chr(92), '/') + r'/ext/files/game/'
OUT=os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(chr(92), '/') + r'/text/'
def pr(s): return s.decode('latin1')
# 1 dialogue
dlg=[]
for f in sorted(glob.glob(G+'s*.pds')):
    fn=os.path.basename(f); b=open(f,'rb').read()
    n=struct.unpack('>I',b[4:8])[0]; offs=list(struct.unpack('>%dI'%n,b[12:12+4*n]))
    s=offs[8]
    if not s: continue
    for i in range(b[s]):
        r=s+8+i*0x438
        name=b[r:r+0x20].split(b'\0')[0]; txt=b[r+0x20:r+0x420].split(b'\0')[0]
        dlg.append({'id':f'{fn}:{i}','name':name.decode('cp932') if name and name[0]>=0x80 else pr(name),'en':pr(txt),'ko':''})
json.dump(dlg,open(OUT+'dialogue.json','w',encoding='utf8'),ensure_ascii=False,indent=1)
# 2 res
res=[]
for f in sorted(glob.glob(G+'*.res')):
    fn=os.path.basename(f); b=open(f,'rb').read()
    cnt=struct.unpack('>H',b[10:12])[0]
    ents=[struct.unpack('>II',b[12+8*i:20+8*i]) for i in range(cnt)]
    for k,(i,o) in enumerate(ents):
        res.append({'id':f'{fn}:{i}','en':pr(b[o:].split(b'\0')[0]),'ko':''})
json.dump(res,open(OUT+'res.json','w',encoding='utf8'),ensure_ascii=False,indent=1)
print(len(dlg),len(res))
# 3 CRD
crd=[]
for fn in ['Menu.CRD','Menus.CRD']:
    b=open(G+fn,'rb').read()
    n=struct.unpack('>I',b[4:8])[0]; offs=list(struct.unpack('>%dI'%n,b[8:8+4*n]))
    for i,o in enumerate(offs):
        if not o: continue
        for fo,cap in ((0x90,31),(0xb0,15),(0xb2,13),(0xd0,15),(0xe0,15),(0xf0,15)):
            s=b[o+fo:o+fo+cap+1].split(b'\0')[0]
            if len(s)>=2 and all(0x20<=c<0x7f for c in s) and re.search(rb'[A-Za-z]{2}',s) and (fo==0x90 or b[o+fo-1]==0):
                crd.append({'id':f'{fn}:{o+fo:x}','cap':cap,'en':pr(s),'ko':''})
json.dump(crd,open(OUT+'crd.json','w',encoding='utf8'),ensure_ascii=False,indent=1)
# 4 mel groups
mel=[]
for fn in ['Menu_us.mel','Shop_us.mel','VsMenu.mel','Mc.mel','Labo.mel','Detail.Men','WorldMap_us.mel','Report.MEL']:
    b=open(G+fn,'rb').read()
    for m in re.finditer(rb'(?<=\x00)(?:[\x20-\x7e]{2,}\x00)+',b):
        g=m.group(); ss=g[:-1].split(b'\0')
        if not any(re.search(rb'[a-z]{3}',s) or re.fullmatch(rb'[A-Z ]{3,}',s) for s in ss): continue
        e=m.end()
        while e<len(b) and b[e]==0: e+=1
        mel.append({'id':f'{fn}:{m.start():x}','len':len(g),'pad':e-m.end(),'en':[pr(s) for s in ss],'ko':[]})
json.dump(mel,open(OUT+'mel.json','w',encoding='utf8'),ensure_ascii=False,indent=1)
print(len(crd),len(mel))
