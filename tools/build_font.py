"""게임 폴백 폰트(FZLiBian, glyf/UPM 256)에 한글 글리프를 이식한다.

TMP 동적 폴백 폰트 에셋(FangZhengLiBian_GBK_0_SDF_Fallback)은 이 TTF에서
런타임에 글리프를 생성하므로, 한글을 TTF에 넣기만 하면 화면에 표시된다.
"""
import io

from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

from common import KR_FONT, KR_FONT_WEIGHT

# 한글 음절, 호환 자모, 자모, 그리고 한국어 문장에서 자주 쓰는 기호
KR_RANGES = [(0xAC00, 0xD7A3), (0x3131, 0x318E), (0x1100, 0x11FF)]
EXTRA = [0x00B7, 0x2027, 0x203B, 0x2192, 0x2190, 0x2191, 0x2193, 0x25CB, 0x25CF, 0x2605, 0x2606, 0x300C, 0x300D, 0x300E, 0x300F]


def _ref_box(font, ch):
    gs = font.getGlyphSet()
    name = font.getBestCmap()[ord(ch)]
    from fontTools.pens.boundsPen import BoundsPen
    bp = BoundsPen(gs)
    gs[name].draw(bp)
    return bp.bounds


def merge(base_bytes: bytes) -> bytes:
    base = TTFont(io.BytesIO(base_bytes))
    kr = TTFont(KR_FONT)
    if "fvar" in kr:
        kr = instantiateVariableFont(kr, {"wght": KR_FONT_WEIGHT})

    # 한자 '中'의 크기/위치로 비율과 세로 오프셋을 맞춘다
    bx0, by0, bx1, by1 = _ref_box(base, "中")
    kx0, ky0, kx1, ky1 = _ref_box(kr, "中")
    scale = (by1 - by0) / (ky1 - ky0)
    dy = (by0 + by1) / 2 - (ky0 + ky1) / 2 * scale

    base_cmap = base.getBestCmap()
    kr_cmap = kr.getBestCmap()
    wanted = [c for a, b in KR_RANGES for c in range(a, b + 1)] + EXTRA
    wanted = [c for c in wanted if c in kr_cmap and c not in base_cmap]

    kr_gs = kr.getGlyphSet()
    glyf = base["glyf"]
    hmtx = base["hmtx"].metrics
    vmtx = base["vmtx"].metrics if "vmtx" in base else None
    order = list(base.getGlyphOrder())
    adv_v = base["vhea"].advanceHeightMax if "vhea" in base else base["head"].unitsPerEm

    new_map = {}
    for cp in wanted:
        src = kr_cmap[cp]
        rec = DecomposingRecordingPen(kr_gs)
        kr_gs[src].draw(rec)
        pen = TTGlyphPen(None)
        rec.replay(TransformPen(pen, (scale, 0, 0, scale, 0, dy)))
        g = pen.glyph()
        name = f"kr{cp:04X}"
        glyf.glyphs[name] = g
        order.append(name)
        g.recalcBounds(glyf)
        adv = round(kr["hmtx"].metrics[src][0] * scale)
        lsb = getattr(g, "xMin", 0)
        hmtx[name] = (adv, lsb)
        if vmtx is not None:
            vmtx[name] = (adv_v, 0)
        new_map[cp] = name

    base.setGlyphOrder(order)
    glyf.glyphOrder = order
    for t in base["cmap"].tables:
        if t.isUnicode():
            if t.format == 4:
                t.cmap.update({c: n for c, n in new_map.items() if c <= 0xFFFF})
            elif t.format == 12:
                t.cmap.update(new_map)
    base["maxp"].numGlyphs = len(order)
    out = io.BytesIO()
    base.save(out)
    return out.getvalue()
