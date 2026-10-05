"""번역과 한글 폰트를 적용한 게임 파일을 build/ 에 생성한다."""
import json
import shutil
import sys

import UnityPy
from PIL import Image

import image_specs
from atlas import glyph_boxes, relabel_atlas
from build_font import merge
from common import (BUILD_DIR, DATA_DIR, KOREAN_LABEL, LANG_COLUMNS, SOURCE_DIR, TARGET_LANG,
                    TRANS_DIR, original, read_dat, xor)
from extract import parse_textmapper, script_bytes
from luban import Reader, w_str, w_uint
from ui_fix import SPRITE_ASSET_FIXES, fix_sprite_assets

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
    out.write_bytes(xor(env.file.save(packer="lz4"), key))
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


LANG_BUNDLES = [f"Localization/{l}.dat" for l in LANG_COLUMNS]
TEXTICON_BUNDLES = ["UI/UIForms.dat", "Entities/Timer.dat", "Entities/Effect.dat", "Entities/Tips.dat"]
FONT_BUNDLES = ["Entities/Timer.dat"]


RECORD = None   # release.py 가 {번들: {텍스처 이름: Image}} 로 설정하면 바꾼 이미지를 모아 둔다
CURRENT = None  # 지금 처리 중인 번들


def set_texture(tex, img):
    if RECORD is not None:
        RECORD.setdefault(CURRENT, {})[tex.m_Name] = img
    fmt = tex.m_TextureFormat
    try:
        tex.set_image(img, target_format=fmt, mipmap_count=max(1, tex.m_MipCount or 1))
    except Exception:  # 압축 인코더가 없으면 무압축으로
        tex.set_image(img, target_format=4, mipmap_count=max(1, tex.m_MipCount or 1))
    tex.save()


def korean_localized_images():
    """간체 중국어 이미지를 기준으로 만든 한국어 이미지 {이름: Image}"""
    data, _ = read_dat(original("StreamingAssets/Localization/ChineseSimplified.dat"))
    env = UnityPy.load(data)
    out = {}
    for o in env.objects:
        if o.type.name == "Texture2D" and o.peek_name() in image_specs.LOCALIZATION:
            n = o.peek_name()
            out[n] = image_specs.apply(o.read().image.convert("RGBA"), image_specs.LOCALIZATION[n])
    return out


def fit_canvas(img, w, h):
    """크기가 다른 같은 이름 텍스처(예: 영어판 엔딩 부제)에 맞춰 가운데 배치"""
    if img.size == (w, h):
        return img
    c = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    im = img.copy()
    im.thumbnail((w, h))
    c.alpha_composite(im, ((w - im.width) // 2, (h - im.height) // 2))
    return c


def texticon_boxes():
    data, _ = read_dat(original("StreamingAssets/UI/UIForms.dat"))
    env = UnityPy.load(data)
    for o in env.objects:
        if o.type.name == "MonoBehaviour" and o.peek_name() == "TextIcon":
            t = o.read_typetree()
            tex = next(x for x in env.objects if x.path_id == t["spriteSheet"]["m_PathID"]).read()
            return glyph_boxes(t, tex.m_Height), (tex.m_Width, tex.m_Height)


def patch_textures(env, specs, ko_loc, boxes):
    n = 0
    for o in env.objects:
        if o.type.name != "Texture2D":
            continue
        name = o.peek_name()
        if name == "TextIcon" and boxes:
            tex = o.read()
            if (tex.m_Width, tex.m_Height) == boxes[1]:
                set_texture(tex, relabel_atlas(tex.image.convert("RGBA"), boxes[0], image_specs.TEXTICON))
                n += 1
        elif ko_loc is not None and name in image_specs.LOCALIZATION:
            tex = o.read()
            img = ko_loc.get(name)
            if img is None:  # 이 언어 번들에만 있는 이미지
                img = image_specs.apply(tex.image.convert("RGBA"), image_specs.LOCALIZATION[name])
            set_texture(tex, fit_canvas(img, tex.m_Width, tex.m_Height))
            n += 1
        elif name in specs:
            tex = o.read()
            set_texture(tex, image_specs.apply(tex.image.convert("RGBA"), specs[name]))
            n += 1
    return n


def main():
    BUILD_DIR.mkdir(exist_ok=True)
    ko = load_translations()
    print(f"번역 {len(ko)}개 로드")
    print("LubanTables.dat")
    patch_luban(ko)
    if "--text-only" in sys.argv:
        return
    font_cache = {}
    skip_images = "--no-images" in sys.argv
    ko_loc = None if skip_images else korean_localized_images()
    boxes = None if skip_images else texticon_boxes()
    bundles = set(FONT_BUNDLES) | set(SPRITE_ASSET_FIXES)
    if not skip_images:
        bundles |= set(LANG_BUNDLES) | set(TEXTICON_BUNDLES) | set(image_specs.BY_BUNDLE)
    global CURRENT
    for b in sorted(bundles):
        rel = "StreamingAssets/" + b
        CURRENT = b
        print(b)
        data, key = read_dat(original(rel))
        env = UnityPy.load(data)
        if b in FONT_BUNDLES:
            patch_fonts(env, font_cache)
        if b in SPRITE_ASSET_FIXES:
            print(f"  스프라이트 에셋 {fix_sprite_assets(env, SPRITE_ASSET_FIXES[b])}개 연결")
        if not skip_images:
            n = patch_textures(env, image_specs.BY_BUNDLE.get(b, {}),
                               ko_loc if b in LANG_BUNDLES else None, boxes)
            print(f"  이미지 {n}개")
        write_dat(rel, env, key)
    print("resources.assets")
    CURRENT = "resources.assets"
    src = original("resources.assets")
    ress = src.with_name("resources.assets.resS")
    if not ress.exists():  # 백업본 옆에도 리소스 스트림 파일이 있어야 읽힌다 (수정하지 않는 파일)
        shutil.copy2(DATA_DIR / "resources.assets.resS", ress)
    env = UnityPy.load(str(src))
    patch_fonts(env, font_cache)
    if not skip_images:
        print(f"  이미지 {patch_textures(env, {}, None, boxes)}개")
    out = BUILD_DIR / "resources.assets"
    out.write_bytes(env.file.save())
    print("  →", out)


if __name__ == "__main__":
    main()
