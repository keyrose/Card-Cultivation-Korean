"""배포용 패치 설치 파일 만들기.

python release.py 1.0.2

1. build.py 를 돌리면서 바꾼 이미지를 모두 모은다
2. dist/payload/ 에 번역(ko.json), 이미지(PNG, 중복 제거), 한글 글꼴, manifest.json 작성
3. PyInstaller 로 installer.py 를 exe 하나로 묶고 zip 으로 압축
"""
import hashlib
import io
import json
import shutil
import subprocess
import sys
import zipfile

import build
from common import BUILD_DIR, DATA_DIR, KR_FONT, ROOT, TRANS_DIR, original
from ui_fix import SPRITE_ASSET_FIXES

DIST = ROOT / "dist"
PAYLOAD = DIST / "payload"
EXE_NAME = "CardCultivation_KoreanPatch"


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def make_payload(version):
    if PAYLOAD.exists():
        shutil.rmtree(PAYLOAD)
    (PAYLOAD / "images").mkdir(parents=True)

    build.RECORD = {}
    sys.argv = ["build.py"]
    build.main()

    images = {}
    seen = set()
    for bundle, texs in build.RECORD.items():
        rel = bundle if bundle == "resources.assets" else "StreamingAssets/" + bundle
        images[rel] = {}
        for name, img in texs.items():
            buf = io.BytesIO()
            img.save(buf, "PNG", optimize=True)
            data = buf.getvalue()
            h = hashlib.sha1(data).hexdigest()[:16]
            if h not in seen:
                (PAYLOAD / "images" / f"{h}.png").write_bytes(data)
                seen.add(h)
            images[rel][name] = h

    files = sorted({"StreamingAssets/LubanTables.dat", "resources.assets",
                    *("StreamingAssets/" + b for b in build.FONT_BUNDLES),
                    *("StreamingAssets/" + b for b in SPRITE_ASSET_FIXES), *images})
    manifest = {
        "version": version,
        "files": {rel: {"sha256": sha256_file(original(rel))} for rel in files},
        "images": images,
        "fonts": ["resources.assets", *("StreamingAssets/" + b for b in build.FONT_BUNDLES)],
    }
    (PAYLOAD / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    shutil.copy2(TRANS_DIR / "ko.json", PAYLOAD / "ko.json")
    shutil.copy2(KR_FONT, PAYLOAD / "NotoSerifKR-VF.ttf")
    shutil.copy2(ROOT / "tools" / "fonts" / "OFL.txt", PAYLOAD / "OFL.txt")
    n = sum(len(v) for v in images.values())
    print(f"payload: 이미지 {n}개 (고유 {len(seen)}개), 파일 {len(files)}개")


README = """Card Cultivation 한글 패치 v{version}
=====================================

[설치]
1. 게임을 종료합니다.
2. {exe}.exe 를 실행하고 1번(설치)을 선택합니다.
   - 스팀 게임 폴더를 자동으로 찾습니다. 못 찾으면 경로를 물어봅니다.
   - exe 를 게임 폴더(CardCultivation.exe 가 있는 곳)에 넣고 실행해도 됩니다.
3. 게임 실행 → 설정(Options) → Language → '한국어' 선택.

[제거]
같은 exe 를 실행하고 2번(원본으로 복구)을 선택합니다.
원본 파일은 게임 폴더의 KoreanPatch_backup 폴더에 보관됩니다.

[게임 업데이트 후]
스팀 업데이트로 한글이 풀리면 exe 를 다시 실행해 1번을 선택하세요.
게임을 지우고 다시 받을 필요 없이, 업데이트된 파일을 새 원본으로 백업하고 다시 패치합니다.

[자동 재적용 (추천)]
exe 를 실행해 3번을 선택하면 스팀 실행 옵션에 넣을 한 줄이 클립보드에 복사됩니다.
스팀 라이브러리 → Card Cultivation 우클릭 → 속성 → 일반 → 실행 옵션에 붙여넣으면,
게임을 켤 때마다 패치가 풀렸는지 확인해 자동으로 다시 적용합니다.
(업데이트 직후 첫 실행만 몇 분 걸립니다. 해제는 실행 옵션을 지우면 됩니다.)

[참고]
- 영어 언어 자리를 한국어로 바꾸는 방식이라 패치 후에는 영어 대신 한국어가 나옵니다.
- 비공식 팬 번역입니다. 문제/오역 제보: https://github.com/keyrose/Card-Cultivation-Korean
- 포함 글꼴: Noto Serif KR, East Sea Dokdo, Song Myung (SIL Open Font License 1.1)
"""


def make_exe(version):
    tools = ROOT / "tools"
    work = DIST / "pyi"
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile", "--console",
           "--name", EXE_NAME, "--distpath", str(DIST), "--workpath", str(work), "--specpath", str(work),
           "--paths", str(tools), "--add-data", f"{PAYLOAD};payload",
           "--collect-all", "UnityPy", "--collect-all", "fmod_toolkit", "--collect-all", "archspec",
           "--exclude-module", "cv2", "--exclude-module", "matplotlib",
           str(tools / "installer.py")]
    subprocess.run(cmd, check=True)
    exe = DIST / f"{EXE_NAME}.exe"
    zp = DIST / f"{EXE_NAME}_v{version}.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(exe, exe.name)
        z.writestr("읽어주세요.txt", README.format(version=version, exe=EXE_NAME).encode("utf-8-sig"))
    print("→", zp, f"{zp.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    ver = sys.argv[1] if len(sys.argv) > 1 else "1.0.2"
    if "--exe-only" not in sys.argv:
        make_payload(ver)
    make_exe(ver)
