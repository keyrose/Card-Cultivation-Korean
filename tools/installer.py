"""Card Cultivation 한글 패치 설치 프로그램.

사용자 PC의 게임 파일을 직접 고친다 (게임 원본 파일은 배포하지 않음).
  - 텍스트: lang_tbtextmapper 의 영어 열 → 한국어, 언어 표시명 → 한국어
  - 폰트: 게임 폴백 폰트에 한글 글리프 병합 (Noto Serif KR, SIL OFL)
  - 이미지: 한글화한 텍스처로 교체
  - (선택) 치트 메뉴: BepInEx 6 + 치트 플러그인 (F1)
원본은 게임 폴더의 KoreanPatch_backup/ 에 보관하고, 메뉴에서 복구할 수 있다.
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile
import traceback
import urllib.request
import zipfile
from pathlib import Path

import UnityPy
from PIL import Image

from build_font import merge
from luban import Reader, w_str, w_uint

APP = "Card Cultivation 한글 패치"
GAME_EXE = "CardCultivation.exe"
STEAM_SUBDIR = Path("steamapps/common/Card Cultivation")
BACKUP = "KoreanPatch_backup"
FONT_NAME = "FangZhengLiBian_GBK_0"
LANG_COL = 3  # key, zh, zht, en, ru → en 자리에 한국어
MAGIC = b"UnityFS\0"

# 치트 메뉴용 BepInEx (치트 플러그인을 빌드한 버전에 고정). 온라인판은 설치 때 받고,
# 오프라인판은 릴리스 zip 에 exe 와 나란히 들어 있다.
# 게임의 IL2CPP 메타데이터가 v31 이라 6.0.0-pre.2(GitHub 릴리스, v29 까지)는 못 쓰고 bleeding edge 빌드가 필요하다.
BEPINEX_ZIP = "BepInEx-Unity.IL2CPP-win-x64-6.0.0-be.788+5b766a3.zip"
BEPINEX_URL = ("https://builds.bepinex.dev/projects/bepinex_be/788/"
               "BepInEx-Unity.IL2CPP-win-x64-6.0.0-be.788%2B5b766a3.zip")
BEPINEX_SHA256 = "f4cc496bd098a0df4164b81e3737297707f13a47c2478dba2f60eefab784817a"
BEPINEX_SKIP = {"changelog.txt"}  # BepInEx 변경 기록은 게임 폴더에 필요 없다
BEPINEX_OWNED = ["BepInEx", "dotnet", "winhttp.dll", "doorstop_config.ini", ".doorstop_version"]
CHEAT_DLL = "CardCultivationCheat.dll"
SAVE_DIR = r"%USERPROFILE%\AppData\LocalLow\DarkIndex\CardCultivation\SaveRecord"


def payload_dir() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent / "dist"))
    return base / "payload"


def exe_dir() -> Path:
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path.cwd()


# ---------------------------------------------------------------- 게임 폴더 찾기
def steam_libraries():
    roots = []
    try:
        import winreg
        for hive, key in [(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
                          (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")]:
            try:
                with winreg.OpenKey(hive, key) as k:
                    for v in ("SteamPath", "InstallPath"):
                        try:
                            roots.append(Path(winreg.QueryValueEx(k, v)[0]))
                        except OSError:
                            pass
            except OSError:
                pass
    except ImportError:
        pass
    roots.append(Path(r"C:\Program Files (x86)\Steam"))
    libs = []
    for r in roots:
        libs.append(r)
        vdf = r / "steamapps" / "libraryfolders.vdf"
        if vdf.exists():
            for line in vdf.read_text(encoding="utf-8", errors="ignore").splitlines():
                parts = line.strip().split('"')
                if len(parts) >= 4 and parts[1] == "path":
                    libs.append(Path(parts[3].replace("\\\\", "\\")))
    seen, out = set(), []
    for l in libs:
        k = str(l).lower()
        if k not in seen:
            seen.add(k)
            out.append(l)
    return out


def find_game():
    cands = []
    if len(sys.argv) > 1:
        cands.append(Path(sys.argv[1]))
    cands += [exe_dir(), Path.cwd()]
    cands += [lib / STEAM_SUBDIR for lib in steam_libraries()]
    for c in cands:
        if (c / GAME_EXE).exists():
            return c
    return None


# ---------------------------------------------------------------- 유틸
def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def xor(data: bytes, key: bytes) -> bytes:
    n = len(data)
    rep = (key * (n // 4 + 1))[:n]
    return (int.from_bytes(data, "little") ^ int.from_bytes(rep, "little")).to_bytes(n, "little")


def read_dat(path: Path):
    d = path.read_bytes()
    key = bytes(a ^ b for a, b in zip(d[:4], MAGIC[:4]))
    return xor(d, key), key


def script_bytes(ta) -> bytes:
    s = ta.m_Script
    return s.encode("utf-8", "surrogateescape") if isinstance(s, str) else bytes(s)


def set_script(obj, data: bytes):
    ta = obj.read()
    ta.m_Script = data.decode("utf-8", "surrogateescape")
    ta.save()


def set_texture(tex, img):
    mips = max(1, tex.m_MipCount or 1)
    try:
        tex.set_image(img, target_format=tex.m_TextureFormat, mipmap_count=mips)
    except Exception:
        tex.set_image(img, target_format=4, mipmap_count=mips)
    tex.save()


# ---------------------------------------------------------------- 패치 내용
class Patch:
    def __init__(self):
        p = payload_dir()
        self.dir = p
        self.manifest = json.loads((p / "manifest.json").read_text(encoding="utf-8"))
        self.ko = json.loads((p / "ko.json").read_text(encoding="utf-8"))
        self.font = str(p / "NotoSerifKR-VF.ttf")
        cheat = p / "cheat" / CHEAT_DLL
        self.cheat = cheat if cheat.exists() else None  # 치트 플러그인을 넣지 않은 릴리스면 None
        self._merged = None

    def image(self, h):
        return Image.open(self.dir / "images" / f"{h}.png").convert("RGBA")

    def textmapper(self, raw: bytes) -> bytes:
        r = Reader(raw)
        n = r.uint()
        out = [w_uint(n)]
        for _ in range(n):
            row = [r.str() for _ in range(5)]
            if row[0] in self.ko:
                row[LANG_COL] = self.ko[row[0]]
            out += [w_str(c) for c in row]
        return b"".join(out)

    def languages(self, raw: bytes) -> bytes:
        r = Reader(raw)
        n = r.uint()
        out = [w_uint(n)]
        for _ in range(n):
            name, label = r.str(), r.str()
            if name == "English":
                label = "한국어"
            out += [w_str(name), w_str(label)]
        return b"".join(out)

    def fonts(self, env):
        for o in env.objects:
            if o.type.name == "Font" and o.peek_name() == FONT_NAME:
                t = o.read_typetree()
                if self._merged is None:
                    print("    한글 글꼴 병합 중...")
                    self._merged = merge(bytes(t["m_FontData"]), self.font)
                t["m_FontData"] = list(self._merged)
                o.save_typetree(t)

    def apply(self, rel: str, src: Path) -> bytes:
        """원본 파일(src)에 패치를 적용한 바이트를 돌려준다"""
        is_bundle = rel.startswith("StreamingAssets/")
        if is_bundle:
            data, key = read_dat(src)
            env = UnityPy.load(data)
        else:
            env = UnityPy.load(str(src))
        imgs = self.manifest["images"].get(rel, {})
        for o in env.objects:
            t = o.type.name
            if t == "TextAsset" and rel.endswith("LubanTables.dat"):
                n = o.peek_name()
                if n == "lang_tbtextmapper":
                    set_script(o, self.textmapper(script_bytes(o.read())))
                elif n == "lang_tblanguages":
                    set_script(o, self.languages(script_bytes(o.read())))
            elif t == "Texture2D" and imgs:
                n = o.peek_name()
                if n in imgs:
                    set_texture(o.read(), self.image(imgs[n]))
        if rel in self.manifest["fonts"]:
            self.fonts(env)
        if is_bundle:
            return xor(env.file.save(packer="lz4"), key)
        return env.file.save()


# ---------------------------------------------------------------- 설치 / 복구
def install(game: Path, patch: Patch):
    data_dir = game / "CardCultivation_Data"
    bdir = game / BACKUP
    state_p = bdir / "state.json"
    state = json.loads(state_p.read_text(encoding="utf-8")) if state_p.exists() else {}
    files = patch.manifest["files"]
    mismatch = []
    for i, (rel, info) in enumerate(files.items(), 1):
        cur = data_dir / rel
        bak = bdir / rel
        print(f"[{i}/{len(files)}] {rel}")
        if not cur.exists():
            print("    (게임에 없는 파일 - 건너뜀)")
            continue
        cur_sha = sha256(cur)
        if bak.exists() and (state.get(rel) == cur_sha or sha256(bak) == info["sha256"]):
            src = bak  # 이미 패치됨, 또는 백업이 제작 기준 원본과 같음 → 백업에서 다시 적용
        else:
            bak.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(cur, bak)  # 첫 설치 또는 게임 업데이트 후: 현재 파일이 원본
            src = bak
        if rel == "resources.assets":  # 리소스 스트림 파일도 원본 옆에 있어야 읽힘
            ress = data_dir / "resources.assets.resS"
            if ress.exists() and not (bdir / "resources.assets.resS").exists():
                shutil.copy2(ress, bdir / "resources.assets.resS")
        if sha256(src) != info["sha256"]:
            mismatch.append(rel)
        out = patch.apply(rel, src)
        tmp = cur.with_suffix(cur.suffix + ".kptmp")
        tmp.write_bytes(out)
        os.replace(tmp, cur)
        state[rel] = sha256(cur)
        state_p.parent.mkdir(parents=True, exist_ok=True)
        state_p.write_text(json.dumps(state, indent=1), encoding="utf-8")
    print()
    if mismatch:
        print("※ 다음 파일은 패치 제작 때와 게임 버전이 다릅니다. 대부분 정상 동작하지만,")
        print("  일부 텍스트/이미지가 적용되지 않았을 수 있습니다:")
        for m in mismatch:
            print("   -", m)
        print()
    print("설치 완료! 게임 설정 → Language 에서 '한국어' 를 선택하세요.")


# ---------------------------------------------------------------- 치트 메뉴 (선택)
def bepinex_installed(game: Path) -> bool:
    return (game / "BepInEx" / "core" / "BepInEx.Unity.IL2CPP.dll").exists()


def download(url: str, dst: Path):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})  # 기본 UA 는 403
    with urllib.request.urlopen(req, timeout=60) as r, open(dst, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done, shown = 0, -1
        while chunk := r.read(1 << 16):
            f.write(chunk)
            done += len(chunk)
            pct = done * 100 // total if total else -1
            if pct // 10 != shown // 10:
                shown = pct
                print(f"    {done / 1e6:.1f} / {total / 1e6:.1f} MB" if total else f"    {done / 1e6:.1f} MB")


def find_bepinex_zip(tmp: Path):
    """오프라인판(exe 옆 zip) → 없으면 내려받기. 둘 다 안 되면 None"""
    for d in dict.fromkeys([exe_dir(), Path.cwd()]):
        local = sorted(d.glob("BepInEx-Unity.IL2CPP-win-x64*.zip"))
        if local:
            z = d / BEPINEX_ZIP if (d / BEPINEX_ZIP).exists() else local[-1]
            print("    BepInEx:", z.name)
            if z.name != BEPINEX_ZIP:
                print(f"    ※ 치트 메뉴는 {BEPINEX_ZIP} 기준으로 만들어졌습니다. 다른 버전은 동작하지 않을 수 있습니다.")
            elif sha256(z) != BEPINEX_SHA256:
                print("    ※ 파일이 손상되었습니다. 다시 받아 주세요.")
                return None
            return z
    print("    BepInEx 내려받는 중... (약 34MB)")
    z = tmp / BEPINEX_ZIP
    try:
        download(BEPINEX_URL, z)
    except Exception as e:
        print("    내려받기 실패:", e)
        return None
    if sha256(z) != BEPINEX_SHA256:
        print("    내려받은 파일이 예상과 다릅니다.")
        return None
    return z


def bepinex_guide():
    print()
    print("※ BepInEx 를 준비하지 못해 치트 메뉴를 설치하지 않았습니다. (한글 패치는 설치됨)")
    print("  인터넷이 안 되는 PC라면 다른 PC에서 아래 파일을 받아")
    print("  이 설치 프로그램(exe)과 같은 폴더에 넣고 다시 3번을 선택하세요. (zip 은 풀지 마세요)")
    print("   ", BEPINEX_URL)
    print("  또는 릴리스 페이지의 '_offline' zip 을 받으면 BepInEx 가 함께 들어 있습니다.")


def install_cheat(game: Path, patch: Patch) -> bool:
    bdir = game / BACKUP
    cheat_p = bdir / "cheat.json"
    cheat = json.loads(cheat_p.read_text(encoding="utf-8")) if cheat_p.exists() else {"bepinex": False}
    print("치트 메뉴")
    if not bepinex_installed(game):
        with tempfile.TemporaryDirectory() as tmp:
            z = find_bepinex_zip(Path(tmp))
            if z is None:
                bepinex_guide()
                return False
            with zipfile.ZipFile(z) as zf:
                zf.extractall(game, [m for m in zf.namelist() if m not in BEPINEX_SKIP])
        cheat["bepinex"] = True  # 패치가 깐 BepInEx → 복구할 때 함께 지운다
        print("    BepInEx 설치")
    else:
        print("    BepInEx 이미 설치됨 - 그대로 사용")
    plugins = game / "BepInEx" / "plugins"
    plugins.mkdir(parents=True, exist_ok=True)
    shutil.copy2(patch.cheat, plugins / CHEAT_DLL)
    print("    플러그인 설치:", CHEAT_DLL)
    bdir.mkdir(parents=True, exist_ok=True)
    cheat_p.write_text(json.dumps(cheat, indent=1), encoding="utf-8")
    print()
    print("치트 메뉴 설치 완료! 게임 안에서 F1 키로 엽니다.")
    print("  - 설치 후 첫 실행은 BepInEx 준비 때문에 몇 분 걸립니다 (검은 콘솔 창이 함께 뜹니다).")
    print("  - 치트를 쓰기 전에 세이브 폴더를 백업해 두세요:")
    print("   ", SAVE_DIR)
    return True


def restore_cheat(game: Path):
    cheat_p = game / BACKUP / "cheat.json"
    if not cheat_p.exists():
        return
    cheat = json.loads(cheat_p.read_text(encoding="utf-8"))
    dll = game / "BepInEx" / "plugins" / CHEAT_DLL
    if dll.exists():
        dll.unlink()
        print("제거:", dll.relative_to(game))
    if cheat.get("bepinex"):
        for name in BEPINEX_OWNED:
            p = game / name
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            elif p.exists():
                p.unlink()
            else:
                continue
            print("제거:", name)


def restore(game: Path):
    bdir = game / BACKUP
    state_p = bdir / "state.json"
    if not state_p.exists():
        print("백업이 없습니다. (패치가 설치되지 않았습니다)")
        return
    restore_cheat(game)
    state = json.loads(state_p.read_text(encoding="utf-8"))
    data_dir = game / "CardCultivation_Data"
    for rel in state:
        if (bdir / rel).exists():
            shutil.copy2(bdir / rel, data_dir / rel)
            print("복구:", rel)
    shutil.rmtree(bdir, ignore_errors=True)
    print("\n원본으로 복구했습니다.")


def main():
    patch = Patch()
    print("=" * 56)
    print(f"  {APP}  v{patch.manifest['version']}")
    print("=" * 56)
    game = find_game()
    while game is None:
        print("게임 폴더를 찾지 못했습니다.")
        p = input(f"{GAME_EXE} 가 있는 폴더 경로를 입력하세요: ").strip().strip('"')
        if p and (Path(p) / GAME_EXE).exists():
            game = Path(p)
    print("게임 폴더:", game)
    print()
    menu = ["1) 한글 패치 설치 / 업데이트", "2) 원본으로 복구 (패치" + (" + 치트 메뉴" if patch.cheat else "") + " 제거)"]
    if patch.cheat:
        menu.append("3) 한글 패치 + 치트 메뉴(F1) 설치")
    menu.append(f"{len(menu) + 1}) 종료")
    for m in menu:
        print("  " + m)
    choice = input(f"\n선택 (1~{len(menu)}): ").strip()
    print()
    if choice == "1" or (choice == "3" and patch.cheat):
        print("※ 게임을 종료한 상태에서 진행하세요. 몇 분 걸릴 수 있습니다.\n")
        install(game, patch)
        if choice == "3":
            print()
            install_cheat(game, patch)
    elif choice == "2":
        restore(game)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        print("\n오류가 발생했습니다. 위 내용을 캡처해서 알려주세요.")
    input("\n엔터를 누르면 종료합니다...")
