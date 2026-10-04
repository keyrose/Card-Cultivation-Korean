# Card Cultivation 한글화

Steam 게임 **Card Cultivation (修仙卡牌, App 2963600)** 비공식 한국어 패치 작업 저장소.

게임 내 **설정 → Language → `한국어`** 를 선택하면 한국어로 표시된다.
(영어 열을 한국어로 교체하는 방식이라, 패치 후에는 영어 대신 한국어가 나온다.)

![게임 화면](docs/screenshot_intro.jpg)

## 진행 현황
- 텍스트 14,517개 항목 전부 번역 (중국어 원문 기준, 영어 참고)
- 이미지 속 글자(타이틀 로고, 버튼 그림 등 `Localization/English.dat` 56개)는 미번역 — 영어로 표시됨

## 구조
```
tools/
  common.py      경로 설정, .dat 복호화(4바이트 XOR, UnityFS 헤더로 키 유도)
  luban.py       Luban 바이너리 테이블 reader/writer
  extract.py     LubanTables.dat → source/textmapper.json (원문 추출)
  chunks.py      번역 작업 청크 생성 (1단계: 용어, 2단계: 본문)
  merge.py       translation/raw/*.json 검증(태그/자리표시자) → translation/ko.json
  build_font.py  게임 폴백 폰트(FZLiBian)에 Noto Serif KR 한글 글리프 병합
  build.py       번역·폰트를 적용한 게임 파일을 build/ 에 생성
  install.py     build/ 를 게임 폴더에 설치 (원본은 backup/), `restore` 로 복구
source/textmapper.json   원문 (key, zh, zht, en, ru)
translation/STYLE.md     번역 지침·핵심 용어집
translation/raw/         번역 결과 (대표 키 → 한국어)
translation/ko.json      최종 번역 (키 → 한국어, merge.py 가 생성)
```

## 작동 원리
- 모든 게임 텍스트는 `StreamingAssets/LubanTables.dat` 안의 `lang_tbtextmapper` 테이블에
  (키, 간체, 번체, 영어, 러시아어) 형태로 들어 있다. 영어 열을 한국어로 바꾸고,
  `lang_tblanguages` 의 표시명을 `한국어` 로 바꾼다.
- 기본 TMP 폰트 아틀라스에는 한글이 없지만, 누락 글자는 동적 폴백 폰트
  `FangZhengLiBian_GBK_0_SDF_Fallback` 이 원본 TTF에서 런타임 생성한다.
  그래서 그 TTF(`resources.assets`, `Entities/Timer.dat` 안의 Font)에 한글 글리프를 병합한다.

## 빌드 & 설치
필요: Python 3, `pip install UnityPy fonttools`, Windows 기본 글꼴 `NotoSerifKR-VF.ttf`.
게임은 종료한 상태에서:
```bash
cd tools
python merge.py      # 번역 검증·병합
python build.py      # build/ 에 패치 파일 생성
python install.py    # 게임 폴더에 설치 (최초 1회 원본 백업)
python install.py restore   # 원본 복구
```
게임 업데이트 후에는 `backup/` 을 지우고 `extract.py` → `merge.py` → `build.py` → `install.py` 를 다시 실행한다.
