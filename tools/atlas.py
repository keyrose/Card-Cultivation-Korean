"""TMP 스프라이트 에셋(TextIcon) 아틀라스의 글리프 영역별 한글화."""
from PIL import Image

from imgedit import relabel


def glyph_boxes(sprite_asset_tree, tex_h):
    """글리프 번호 → 이미지 좌표(위쪽 원점) box"""
    out = {}
    for g in sprite_asset_tree["m_SpriteGlyphTable"]:
        r = g["m_GlyphRect"]
        x, y, w, h = r["m_X"], r["m_Y"], r["m_Width"], r["m_Height"]
        out[g["m_Index"]] = (x, tex_h - y - h, x + w, tex_h - y)
    return out


def relabel_atlas(img: Image.Image, boxes: dict, specs: dict) -> Image.Image:
    for gi, spec in specs.items():
        x0, y0, x1, y1 = boxes[gi]
        tile = img.crop((x0, y0, x1, y1))
        tile = relabel(tile, spec)
        img.paste(tile, (x0, y0))
    return img
