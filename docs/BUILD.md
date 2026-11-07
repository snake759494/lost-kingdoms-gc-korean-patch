# 재빌드

## 준비물

- Python 3.11 이상
- `numpy`, `Pillow` (`pip install numpy pillow`)
- Dolphin에 들어 있는 `DolphinTool.exe`
- 원본 북미판 GRNE52 디스크(RVZ 또는 ISO)
  - ISO로 바꿨을 때 MD5가 `181d5c18f4325d22148098759ca21b28`이어야 합니다.
- 글꼴(`docs/FONT_CREDITS.md`). 저장소 최상위에 둡니다.
  - `SeoulHangangEB.ttf`
  - `Galmuri11.ttf`
- (배포 파일을 만들 때) xdelta3

## 순서

```powershell
python tools/prepare.py 'C:\Dolphin\DolphinTool.exe' '.\Lost Kingdoms (USA).rvz'
```

이 명령이 하는 일은 다음과 같습니다.
1. 원본을 `orig.iso`로 변환하고 MD5를 확인합니다.
2. 디스크 파일을 `ext/`에 풉니다.
3. `tools/extract.py`로 원문 표(`text/dialogue.json`, `res.json`, `crd.json`, `mel.json`)를 만듭니다.

```powershell
python tools/build.py '.\Lost Kingdoms (Korean).iso'
python tools/check.py
python tools/audit.py
```

- `build.py`: 한글 글꼴·문자열·그림 글자를 넣은 ISO를 만듭니다.
  - 출력 끝에 `glyphs 878`, `built ... 52 files`가 나오면 성공입니다.
  - `!`로 시작하는 줄은 칸 넘침 경고입니다.
- `check.py`: 대사의 줄 길이와 쪽 넘침을 검사합니다.
- `audit.py`: 결과 파일에 영어나 일본어 문자열이 남아 있는지 훑어봅니다.
  - 데이터가 우연히 문자처럼 읽힌 결과도 함께 나오니, 실제로 쓰이는 문자열인지 직접 판단해야 합니다.

## 배포 파일 만들기

```powershell
xdelta3 -e -0 -S none -A -s orig.iso '.\Lost Kingdoms (Korean).iso' Lost_Kingdoms_GC_KO_v1.0.xdelta
```

결과 ISO의 SHA-256이 README 표의 값과 같으면 배포판과 같은 결과입니다.

## 생성·무시되는 파일

다음 파일은 `.gitignore`에 들어 있어 커밋되지 않습니다.
- `orig.iso`, `ext/`
- 원문 표(`text/dialogue.json` 등)
- 결과 ISO와 xdelta
- 글꼴

`tools/dolstr.py`는 실행파일 문자열 표를 처음부터 다시 만드는 도구입니다. 저장소의 `text/dolstr_all.json`에는 손으로 추가한 항목이 있습니다. 그러니 다시 만들지 말고 그대로 쓰세요.
