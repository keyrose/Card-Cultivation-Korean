"""Card Cultivation 한글 패치 설치 프로그램.

사용자 PC의 게임 파일을 직접 고친다 (게임 원본 파일은 배포하지 않음).
  - 텍스트: lang_tbtextmapper 의 영어 열 → 한국어, 언어 표시명 → 한국어
  - 폰트: 게임 폴백 폰트에 한글 글리프 병합 (Noto Serif KR, SIL OFL)
  - 이미지: 한글화한 텍스처로 교체
  - UI: 원본에서 빠진 스프라이트 에셋 연결 (아이콘 태그가 글자로 나오는 문제)
  - (선택) 치트 메뉴: BepInEx 6 + 치트 플러그인 (F1)
원본은 게임 폴더의 KoreanPatch_backup/ 에 보관하고, 메뉴에서 복구할 수 있다.

Steam 실행 옵션 `"...\\CardCultivation_KoreanPatch.exe" --auto %command%` 로 실행하면
게임 실행 전에 패치가 풀렸는지(스팀 업데이트) 확인해 다시 적용하고 게임을 실행한다.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.request
import zipfile
from pathlib import Path

import UnityPy
from PIL import Image

from build_font import merge
from luban import Reader, w_str, w_uint
from ui_fix import SPRITE_ASSET_FIXES, fix_sprite_assets

APP = "Card Cultivation 한글 패치"
APPID = "2963600"
GAME_EXE = "CardCultivation.exe"
EXE_NAME = "CardCultivation_KoreanPatch.exe"
STEAM_SUBDIR = Path("steamapps/common/Card Cultivation")
BACKUP = "KoreanPatch_backup"
FONT_NAME = "FangZhengLiBian_GBK_0"
LANG_COL = 3  # key, zh, zht, en, ru → en 자리에 한국어
MAGIC = b"UnityFS\0"
STATE_VER = 2

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
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        cands.append(Path(sys.argv[1]))
    cands += [exe_dir(), Path.cwd()]
    cands += [lib / STEAM_SUBDIR for lib in steam_libraries()]
    for c in cands:
        if (c / GAME_EXE).exists():
            return c
    return None


def steam_buildid(game: Path):
    """steamapps/appmanifest_<appid>.acf 의 buildid (스팀 업데이트마다 바뀜). 없으면 None"""
    acf = game.parent.parent / f"appmanifest_{APPID}.acf"
    try:
        for line in acf.read_text(encoding="utf-8", errors="ignore").splitlines():
            parts = line.strip().split('"')
            if len(parts) >= 4 and parts[1] == "buildid":
                return parts[3]
    except OSError:
        pass
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
        fixes = SPRITE_ASSET_FIXES.get(rel.removeprefix("StreamingAssets/"))
        if fixes:
            fix_sprite_assets(env, fixes)
        if is_bundle:
            return xor(env.file.save(packer="lz4"), key)
        return env.file.save()


# ---------------------------------------------------------------- 설치 상태 (KoreanPatch_backup/state.json)
# {"ver": 2, "buildid": 설치 때 스팀 빌드, "time": 마지막 기록 시각,
#  "files": {rel: {"patched": 패치된 파일 sha, "orig": 백업 sha, "size", "mtime"}}}
# v1.0.x 는 {rel: 패치된 파일 sha} 만 있었다 (legacy).
def load_state(bdir: Path) -> dict:
    p = bdir / "state.json"
    if not p.exists():
        return {"ver": STATE_VER, "buildid": None, "time": None, "files": {}}
    s = json.loads(p.read_text(encoding="utf-8"))
    if s.get("ver") != STATE_VER:
        s = {"ver": STATE_VER, "buildid": None, "time": p.stat().st_mtime, "legacy": True,
             "files": {rel: {"patched": sha} for rel, sha in s.items()}}
    return s


def save_state(bdir: Path, state: dict):
    state["time"] = time.time()
    s = {k: v for k, v in state.items() if k != "legacy"}
    p = bdir / "state.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, indent=1), encoding="utf-8")
    os.replace(tmp, p)


def stale_backup(game: Path, state: dict) -> bool:
    """v1.0.1 이 스팀 업데이트 뒤 옛 백업으로 LubanTables.dat 를 되돌려 놓은 상태인지.

    백업(=원본) 이 게임 코드(GameAssembly.dll) 보다 한참 오래됐는데 현재 파일이 우리가 쓴 것이면,
    새 버전 원본은 이미 사라졌으므로 스팀 무결성 검사로 다시 받아야 한다.
    """
    if not state.get("legacy"):
        return False
    rel = "StreamingAssets/LubanTables.dat"
    cur, bak, ga = game / "CardCultivation_Data" / rel, game / BACKUP / rel, game / "GameAssembly.dll"
    if not (cur.exists() and bak.exists() and ga.exists()):
        return False
    return (ga.stat().st_mtime > bak.stat().st_mtime + 3600
            and sha256(cur) == state["files"].get(rel, {}).get("patched"))


def explain_stale():
    print("※ 이전 버전(v1.0.1) 설치 프로그램이 게임 업데이트 뒤 옛 데이터를 덮어쓴 상태입니다.")
    print("  스팀에서 '게임 파일 무결성 확인' 을 한 뒤 이 프로그램을 다시 실행하세요.")
    print("  (스팀 라이브러리 → Card Cultivation 우클릭 → 속성 → 설치된 파일 → 게임 파일 무결성 확인)")
    try:
        if input("\n지금 스팀 무결성 확인을 열까요? (y/n): ").strip().lower() == "y":
            os.startfile(f"steam://validate/{APPID}")
    except (OSError, EOFError):
        pass


# ---------------------------------------------------------------- 설치 / 복구
def install(game: Path, patch: Patch) -> bool:
    data_dir = game / "CardCultivation_Data"
    bdir = game / BACKUP
    state = load_state(bdir)
    if stale_backup(game, state):
        explain_stale()
        return False
    buildid = steam_buildid(game)
    prev_build, prev_time = state.get("buildid"), state.get("time")

    def updated(cur: Path) -> bool:
        """현재 파일이 마지막 설치 뒤 스팀 업데이트로 새로 받은 것인지"""
        if prev_build and buildid:
            return prev_build != buildid
        return prev_time is not None and cur.stat().st_mtime > prev_time + 1

    state["buildid"] = buildid
    files = patch.manifest["files"]
    mismatch, renewed = [], []
    for i, (rel, info) in enumerate(files.items(), 1):
        cur = data_dir / rel
        bak = bdir / rel
        ent = state["files"].get(rel, {})
        print(f"[{i}/{len(files)}] {rel}")
        if not cur.exists():
            print("    (게임에 없는 파일 - 건너뜀)")
            continue
        cur_sha = sha256(cur)
        bak_sha = (ent.get("orig") or sha256(bak)) if bak.exists() else None
        if bak_sha and cur_sha in (ent.get("patched"), bak_sha):
            pass  # 패치된 그대로이거나 원본 그대로 → 백업에서 다시 적용
        elif bak_sha == info["sha256"] and not updated(cur):
            pass  # 다른 방법으로 이미 패치된 파일 → 제작 기준 원본인 백업에서 다시 적용
        else:
            # 첫 설치 또는 스팀 업데이트 후: 현재 파일이 (새) 원본
            if bak_sha:
                renewed.append(rel)
            bak.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(cur, bak)
            bak_sha = cur_sha
            if rel == "resources.assets":  # 리소스 스트림 파일도 원본 옆에 있어야 읽힘
                ress = data_dir / "resources.assets.resS"
                if ress.exists():
                    shutil.copy2(ress, bdir / "resources.assets.resS")
        if rel == "resources.assets":
            ress = data_dir / "resources.assets.resS"
            if ress.exists() and not (bdir / "resources.assets.resS").exists():
                shutil.copy2(ress, bdir / "resources.assets.resS")
        if bak_sha != info["sha256"]:
            mismatch.append(rel)
        out = patch.apply(rel, bak)
        tmp = cur.with_suffix(cur.suffix + ".kptmp")
        tmp.write_bytes(out)
        os.replace(tmp, cur)
        st = cur.stat()
        state["files"][rel] = {"patched": sha256(cur), "orig": bak_sha,
                               "size": st.st_size, "mtime": st.st_mtime_ns}
        save_state(bdir, state)
    print()
    if renewed:
        print("게임 업데이트로 바뀐 파일을 새 원본으로 백업했습니다:")
        for m in renewed:
            print("   -", m)
        print()
    if mismatch:
        print("※ 다음 파일은 패치 제작 때와 게임 버전이 다릅니다. 대부분 정상 동작하지만,")
        print("  새로 추가된 문장은 영어로 나오거나 일부 이미지가 적용되지 않았을 수 있습니다:")
        for m in mismatch:
            print("   -", m)
        print()
    print("설치 완료! 게임 설정 → Language 에서 '한국어' 를 선택하세요.")
    return True


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
    print("  이 설치 프로그램(exe)과 같은 폴더에 넣고 다시 4번을 선택하세요. (zip 은 풀지 마세요)")
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
    if not (bdir / "state.json").exists():
        print("백업이 없습니다. (패치가 설치되지 않았습니다)")
        return
    state = load_state(bdir)
    if stale_backup(game, state):
        explain_stale()
        return
    restore_cheat(game)
    data_dir = game / "CardCultivation_Data"
    for rel, ent in state["files"].items():
        cur, bak = data_dir / rel, bdir / rel
        if not bak.exists() or not cur.exists():
            continue
        if sha256(cur) == ent.get("patched"):
            shutil.copy2(bak, cur)
            print("복구:", rel)
        else:  # 스팀 업데이트로 이미 새 원본이 받아져 있음 → 옛 백업으로 덮지 않는다
            print("건너뜀 (이미 원본):", rel)
    shutil.rmtree(bdir, ignore_errors=True)
    print("\n원본으로 복구했습니다.")
    print("자동 패치(스팀 실행 옵션)를 설정했다면 실행 옵션도 지워 주세요.")


# ---------------------------------------------------------------- 자동 패치 (스팀 실행 옵션)
def patch_intact(game: Path, patch: Patch) -> bool:
    """설치한 패치가 그대로인지 (크기·수정 시각이 같으면 해시 생략)"""
    data_dir = game / "CardCultivation_Data"
    bdir = game / BACKUP
    state = load_state(bdir)
    dirty = False
    for rel in patch.manifest["files"]:
        cur = data_dir / rel
        if not cur.exists():
            continue
        ent = state["files"].get(rel)
        if not ent:
            return False
        st = cur.stat()
        if (st.st_size, st.st_mtime_ns) == (ent.get("size"), ent.get("mtime")):
            continue
        if sha256(cur) != ent.get("patched"):
            return False
        ent["size"], ent["mtime"] = st.st_size, st.st_mtime_ns  # v1.0.x 기록 보충
        dirty = True
    if dirty:
        save_state(bdir, state)
    return True


def hide_console():
    try:
        import ctypes
        h = ctypes.windll.kernel32.GetConsoleWindow()
        if h:
            ctypes.windll.user32.ShowWindow(h, 0)
    except Exception:
        pass


def auto(cmd: list):
    """--auto %command%: 패치가 풀렸으면 다시 적용하고 게임(cmd)을 실행한다"""
    game = Path(cmd[0]).parent if cmd else find_game()
    if not cmd and game:
        cmd = [str(game / GAME_EXE)]
    try:
        # 패치를 설치한 적이 있을 때만 (복구 후에는 다시 깔지 않음)
        if game and (game / BACKUP / "state.json").exists():
            patch = Patch()
            if not patch_intact(game, patch):
                print("=" * 56)
                print(f"  {APP}  v{patch.manifest['version']} - 자동 패치")
                print("=" * 56)
                print("게임 업데이트로 한글 패치가 풀려 다시 적용합니다. 몇 분 걸릴 수 있습니다.\n")
                if not install(game, patch):
                    input("\n엔터를 누르면 게임을 그대로 실행합니다...")
    except Exception:
        traceback.print_exc()
        input("\n자동 패치 중 오류가 발생했습니다. 엔터를 누르면 게임을 그대로 실행합니다...")
    if not cmd:
        return
    hide_console()
    subprocess.call(cmd, cwd=str(Path(cmd[0]).parent))  # 끝날 때까지 기다려야 스팀이 실행 중으로 인식


def setup_auto(game: Path):
    """설치 프로그램을 게임 폴더에 복사하고 스팀 실행 옵션 문자열을 알려준다"""
    if not (game / BACKUP / "state.json").exists():
        print("먼저 1번으로 패치를 설치합니다.\n")
        if not install(game, Patch()):
            return
        print()
    exe = Path(sys.executable)
    if getattr(sys, "frozen", False):
        dst = game / EXE_NAME
        if exe.resolve() != dst.resolve():
            shutil.copy2(exe, dst)  # 다운로드 폴더의 exe 를 지워도 동작하도록
        launch = f'"{dst}" --auto %command%'
    else:
        launch = f'"{exe}" "{Path(__file__).resolve()}" --auto %command%'
    try:
        subprocess.run("clip", input=launch.encode("utf-16"), check=True)
        copied = " (클립보드에 복사됨)"
    except Exception:
        copied = ""
    print("스팀 실행 옵션에 아래 한 줄을 넣으면, 게임을 켤 때마다 패치가 풀렸는지 확인해")
    print(f"자동으로 다시 적용합니다{copied}:\n")
    print("   ", launch, "\n")
    print("설정 방법: 스팀 라이브러리 → Card Cultivation 우클릭 → 속성 → 일반 → 실행 옵션")
    print("해제하려면 실행 옵션을 지우면 됩니다.")


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
    menu = ["1) 한글 패치 설치 / 업데이트",
            "2) 원본으로 복구 (패치" + (" + 치트 메뉴" if patch.cheat else "") + " 제거)",
            "3) 스팀 업데이트 후 자동 재적용 설정"]
    if patch.cheat:
        menu.append("4) 한글 패치 + 치트 메뉴(F1) 설치")
    menu.append(f"{len(menu) + 1}) 종료")
    for m in menu:
        print("  " + m)
    choice = input(f"\n선택 (1~{len(menu)}): ").strip()
    print()
    if choice == "1" or (choice == "4" and patch.cheat):
        print("※ 게임을 종료한 상태에서 진행하세요. 몇 분 걸릴 수 있습니다.\n")
        if install(game, patch) and choice == "4":
            print()
            install_cheat(game, patch)
    elif choice == "2":
        restore(game)
    elif choice == "3":
        setup_auto(game)


if __name__ == "__main__":
    if "--auto" in sys.argv:
        auto(sys.argv[sys.argv.index("--auto") + 1:])
        sys.exit(0)
    try:
        main()
    except Exception:
        traceback.print_exc()
        print("\n오류가 발생했습니다. 위 내용을 캡처해서 알려주세요.")
    input("\n엔터를 누르면 종료합니다...")
