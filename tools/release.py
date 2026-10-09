"""배포용 패치 설치 파일 만들기.

python release.py 1.0.4 [--cheat 치트.dll]

1. build.py 를 돌리면서 바꾼 이미지를 모두 모은다
2. dist/payload/ 에 번역(ko.json), 이미지(PNG, 중복 제거), 한글 글꼴, manifest.json 작성
   치트 플러그인(기본: cheat/bin/Release/net6.0/)이 있으면 payload/cheat/ 에 넣는다
3. PyInstaller 로 installer.py 를 exe 하나로 묶고 zip 으로 압축
   - 온라인판 _vX.Y.Z.zip: exe 만. 치트 메뉴를 고르면 설치 때 BepInEx 를 내려받는다
   - 오프라인판 _vX.Y.Z_offline.zip: exe + BepInEx zip (치트 플러그인이 있을 때만)
"""
import hashlib
import io
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import build
from common import BUILD_DIR, DATA_DIR, KR_FONT, ROOT, TRANS_DIR, original
from installer import BEPINEX_SHA256, BEPINEX_URL, BEPINEX_ZIP, CHEAT_DLL, download
from ui_fix import SPRITE_ASSET_FIXES

DIST = ROOT / "dist"
PAYLOAD = DIST / "payload"
EXE_NAME = "CardCultivation_KoreanPatch"
CHEAT_BUILD = ROOT / "cheat" / "bin" / "Release" / "net6.0" / CHEAT_DLL


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


def add_cheat(src):
    """치트 플러그인을 payload 에 넣는다. 없으면 치트 메뉴 없는 릴리스"""
    dst = PAYLOAD / "cheat"
    shutil.rmtree(dst, ignore_errors=True)
    if src is None or not src.exists():
        print("치트 플러그인 없음 → 한글 패치만 (빌드: cd cheat && dotnet build -c Release)")
        return False
    dst.mkdir(parents=True)
    shutil.copy2(src, dst / CHEAT_DLL)
    print("치트 플러그인:", src)
    return True


def bepinex_zip():
    """오프라인판에 넣을 BepInEx zip (dist/ 에 받아 둔다)"""
    z = DIST / BEPINEX_ZIP
    if not z.exists() or sha256_file(z) != BEPINEX_SHA256:
        print("BepInEx 내려받는 중...")
        download(BEPINEX_URL, z)
        assert sha256_file(z) == BEPINEX_SHA256, "BepInEx zip 해시 불일치"
    return z


README = """Card Cultivation 한글 패치 v{version}
=====================================

[설치]
1. 게임을 종료합니다.
2. {exe}.exe 를 실행하고 1번(설치)을 선택합니다.
   - 스팀 게임 폴더를 자동으로 찾습니다. 못 찾으면 경로를 물어봅니다.
   - exe 를 게임 폴더(CardCultivation.exe 가 있는 곳)에 넣고 실행해도 됩니다.
3. 게임 실행 → 설정(Options) → Language → '한국어' 선택.

{cheat}[제거]
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

README_CHEAT = """[치트 메뉴 (선택)]
4번을 선택하면 한글 패치와 함께 인게임 치트 메뉴(F1)를 설치합니다.
- 치트 메뉴는 BepInEx 6 모드 로더가 필요합니다. 이미 설치되어 있으면 그대로 씁니다.
{bepinex}- 설치 후 첫 실행은 BepInEx 준비 때문에 몇 분 걸립니다.
- 치트를 쓰기 전에 세이브 폴더를 백업해 두세요:
  %USERPROFILE%\\AppData\\LocalLow\\DarkIndex\\CardCultivation\\SaveRecord
- 2번(원본으로 복구)을 선택하면 치트 메뉴와 패치가 설치한 BepInEx 도 함께 제거됩니다.

"""
README_ONLINE = """- 이 판은 설치할 때 BepInEx(약 34MB)를 인터넷에서 내려받습니다.
  인터넷이 안 되면 아래 파일을 다른 PC에서 받아 exe 와 같은 폴더에 넣고 (zip 은 풀지 않음) 다시 4번을 선택하거나,
  릴리스 페이지의 _offline zip 을 받으세요.
  {url}
"""
README_OFFLINE = """- 이 판(_offline)에는 BepInEx 가 함께 들어 있어 인터넷 없이 설치됩니다.
  {zip} 파일을 exe 와 같은 폴더에 둔 채로 실행하세요. (zip 은 풀지 않음)
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
    cheat = (PAYLOAD / "cheat" / CHEAT_DLL).exists()

    def readme(bepinex):
        c = README_CHEAT.format(bepinex=bepinex) if cheat else ""
        return README.format(version=version, exe=EXE_NAME, cheat=c).encode("utf-8-sig")

    zp = DIST / f"{EXE_NAME}_v{version}.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(exe, exe.name)
        z.writestr("읽어주세요.txt", readme(README_ONLINE.format(url=BEPINEX_URL)))
    print("→", zp, f"{zp.stat().st_size / 1e6:.1f} MB")
    if not cheat:
        return
    bep = bepinex_zip()
    zp = DIST / f"{EXE_NAME}_v{version}_offline.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(exe, exe.name)
        z.write(bep, bep.name, compress_type=zipfile.ZIP_STORED)  # 이미 압축된 zip
        z.writestr("읽어주세요.txt", readme(README_OFFLINE.format(zip=BEPINEX_ZIP)))
    print("→", zp, f"{zp.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    args = sys.argv[1:]
    cheat_src = CHEAT_BUILD
    if "--cheat" in args:
        i = args.index("--cheat")
        cheat_src = Path(args[i + 1])
        del args[i:i + 2]
    ver = args[0] if args and not args[0].startswith("--") else "1.0.4"
    if "--exe-only" not in args:
        make_payload(ver)
    add_cheat(cheat_src)
    make_exe(ver)
