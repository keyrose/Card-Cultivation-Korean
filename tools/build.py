"""번역과 한글 폰트를 적용한 게임 파일을 build/ 에 생성한다."""
import json
import sys

import UnityPy

from build_font import merge
from common import (BUILD_DIR, KOREAN_LABEL, LANG_COLUMNS, SOURCE_DIR, TARGET_LANG,
                    TRANS_DIR, original, read_dat, xor)
from extract import parse_textmapper, script_bytes
from luban import Reader, w_str, w_uint

COL = {"ChineseSimplified": "zh", "ChineseTraditional": "zht", "English": "en", "Russian": "ru"}[TARGET_LANG]
FONT_NAME = "FangZhengLiBian_GBK_0"


def load_translations() -> dict[str, str]:
    p = TRANS_DIR / "ko.json"
    if not p.exists():
        return {}
    return {k: v for k, v in json.loads(p.read_text(encoding="utf-8")).items() if v}


def build_textmapper(raw: bytes, ko: dict) -> tuple[bytes, int]:
    rows = parse_textmapper(raw)
    out = [w_uint(len(rows))]
    hit = 0
    for r in rows:
        if r["key"] in ko:
            r[COL] = ko[r["key"]]
            hit += 1
        out += [w_str(r[c]) for c in ("key", "zh", "zht", "en", "ru")]
    return b"".join(out), hit


def build_languages(raw: bytes) -> bytes:
    r = Reader(raw)
    n = r.uint()
    out = [w_uint(n)]
    for _ in range(n):
        name, label = r.str(), r.str()
        if name == TARGET_LANG:
            label = KOREAN_LABEL
        out += [w_str(name), w_str(label)]
    assert r.eof()
    return b"".join(out)


def set_script(obj, data: bytes):
    ta = obj.read()
    ta.m_Script = data.decode("utf-8", "surrogateescape")
    ta.save()


def write_dat(rel, env, key):
    out = BUILD_DIR / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(xor(env.file.save(), key))
    print("  →", out)


def patch_luban(ko):
    rel = "StreamingAssets/LubanTables.dat"
    data, key = read_dat(original(rel))
    env = UnityPy.load(data)
    for o in env.objects:
        if o.type.name != "TextAsset":
            continue
        name = o.peek_name()
        if name == "lang_tbtextmapper":
            new, hit = build_textmapper(script_bytes(o.read()), ko)
            set_script(o, new)
            print(f"  텍스트 {hit}개 적용")
        elif name == "lang_tblanguages":
            set_script(o, build_languages(script_bytes(o.read())))
    write_dat(rel, env, key)


def patch_fonts(env, font_cache):
    n = 0
    for o in env.objects:
        if o.type.name == "Font" and o.peek_name() == FONT_NAME:
            t = o.read_typetree()
            if "merged" not in font_cache:
                print("  한글 글리프 병합 중...")
                font_cache["merged"] = merge(bytes(t["m_FontData"]))
            t["m_FontData"] = list(font_cache["merged"])
            o.save_typetree(t)
            n += 1
    assert n, "폰트를 찾지 못함"


def main():
    BUILD_DIR.mkdir(exist_ok=True)
    ko = load_translations()
    print(f"번역 {len(ko)}개 로드")
    print("LubanTables.dat")
    patch_luban(ko)
    if "--text-only" in sys.argv:
        return
    font_cache = {}
    print("Entities/Timer.dat")
    rel = "StreamingAssets/Entities/Timer.dat"
    data, key = read_dat(original(rel))
    env = UnityPy.load(data)
    patch_fonts(env, font_cache)
    write_dat(rel, env, key)
    print("resources.assets")
    env = UnityPy.load(str(original("resources.assets")))
    patch_fonts(env, font_cache)
    out = BUILD_DIR / "resources.assets"
    out.write_bytes(env.file.save())
    print("  →", out)


if __name__ == "__main__":
    main()
