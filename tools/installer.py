"""Card Cultivation 한글 패치 설치 프로그램.

사용자 PC의 게임 파일을 직접 고친다 (게임 원본 파일은 배포하지 않음).
  - 텍스트: lang_tbtextmapper 의 영어 열 → 한국어, 언어 표시명 → 한국어
  - 폰트: 게임 폴백 폰트에 한글 글리프 병합 (Noto Serif KR, SIL OFL)
  - 이미지: 한글화한 텍스처로 교체
  - UI: 원본에서 빠진 스프라이트 에셋 연결 (아이콘 태그가 글자로 나오는 문제)
원본은 게임 폴더의 KoreanPatch_backup/ 에 보관하고, 메뉴에서 복구할 수 있다.
"""
import hashlib
import json
import os
import shutil
import sys
import traceback
from pathlib import Path

import UnityPy
from PIL import Image

from build_font import merge
from luban import Reader, w_str, w_uint
from ui_fix import SPRITE_ASSET_FIXES, fix_sprite_assets

APP = "Card Cultivation 한글 패치"
GAME_EXE = "CardCultivation.exe"
STEAM_SUBDIR = Path("steamapps/common/Card Cultivation")
BACKUP = "KoreanPatch_backup"
FONT_NAME = "FangZhengLiBian_GBK_0"
LANG_COL = 3  # key, zh, zht, en, ru → en 자리에 한국어
MAGIC = b"UnityFS\0"


def payload_dir() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent / "dist"))
    return base / "payload"


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
    exe_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path.cwd()
    cands += [exe_dir, Path.cwd()]
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


def restore(game: Path):
    bdir = game / BACKUP
    state_p = bdir / "state.json"
    if not state_p.exists():
        print("백업이 없습니다. (패치가 설치되지 않았습니다)")
        return
    state = json.loads(state_p.read_text(encoding="utf-8"))
    data_dir = game / "CardCultivation_Data"
    for rel in state:
        if (bdir / rel).exists():
            shutil.copy2(bdir / rel, data_dir / rel)
            print("복구:", rel)
    shutil.rmtree(bdir, ignore_errors=True)
    print("\n원본으로 복구했습니다.")


def main():
    print("=" * 56)
    print(f"  {APP}  v{Patch().manifest['version']}")
    print("=" * 56)
    game = find_game()
    while game is None:
        print("게임 폴더를 찾지 못했습니다.")
        p = input(f"{GAME_EXE} 가 있는 폴더 경로를 입력하세요: ").strip().strip('"')
        if p and (Path(p) / GAME_EXE).exists():
            game = Path(p)
    print("게임 폴더:", game)
    print()
    print("  1) 한글 패치 설치 / 업데이트")
    print("  2) 원본으로 복구 (패치 제거)")
    print("  3) 종료")
    choice = input("\n선택 (1/2/3): ").strip()
    print()
    if choice == "1":
        print("※ 게임을 종료한 상태에서 진행하세요. 몇 분 걸릴 수 있습니다.\n")
        install(game, Patch())
    elif choice == "2":
        restore(game)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        print("\n오류가 발생했습니다. 위 내용을 캡처해서 알려주세요.")
    input("\n엔터를 누르면 종료합니다...")
