"""원본 준비: RVZ/ISO -> orig.iso, 파일 추출, 원문 표 생성.

python tools/prepare.py <DolphinTool.exe 경로> <원본 .rvz 또는 .iso>
"""
import os, sys, subprocess, hashlib, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ISO = os.path.join(ROOT, 'orig.iso')
EXT = os.path.join(ROOT, 'ext')
MD5 = '181d5c18f4325d22148098759ca21b28'


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 24), b''):
            h.update(c)
    return h.hexdigest()


def main(tool, src):
    if src.lower().endswith('.iso'):
        shutil.copyfile(src, ISO)
    else:
        subprocess.check_call([tool, 'convert', '-i', src, '-o', ISO, '-f', 'iso'])
    got = md5(ISO)
    if got != MD5:
        sys.exit(f'orig.iso MD5 불일치: {got} (기대값 {MD5})')
    if os.path.isdir(EXT):
        shutil.rmtree(EXT)
    subprocess.check_call([tool, 'extract', '-i', ISO, '-o', EXT, '-q'])
    subprocess.check_call([sys.executable, os.path.join(ROOT, 'tools', 'extract.py')])
    print('준비 완료')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
