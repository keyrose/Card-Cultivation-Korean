"""튜토리얼 안내 이미지(Localization/*.dat) 한글화.

TUTORIAL = {텍스처 이름: 함수(img -> img)}. image_specs.LOCALIZATION 에 합쳐진다.

안내 문단 이미지(play_guide_text1x, game_introduction)는 투명 배경 위 글자 + 작은 카드 아이콘이라
빈 캔버스에 원본 아이콘(카드 제목만 한국어로 바꿔서)을 옮겨 붙이고 한국어 줄을 새로 조판한다.
"""
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT_DIR = Path(__file__).parent / "fonts"
FONT_FILES = {
    "brush": str(FONT_DIR / "EastSeaDokdo-Regular.ttf"),
    "callig": str(FONT_DIR / "SongMyung-Regular.ttf"),
    "serif": str(Path(__file__).parent / "fonts" / "NotoSerifKR-VF.ttf"),
    "sans": str(Path(__file__).parent / "fonts" / "NotoSansKR-VF.ttf"),
}

TAN = (109, 95, 65, 255)      # 안내문 본문 색
DARK = (35, 33, 27, 255)      # 괄호 설명 줄 색
WHITE = (255, 255, 255, 255)
BLACK = (0, 0, 0, 255)


@lru_cache(None)
def font(name, size, weight=None):
    f = ImageFont.truetype(FONT_FILES[name], size)
    if name in ("serif", "sans"):
        f.set_variation_by_axes([weight or (900 if name == "serif" else 500)])
    return f


@lru_cache(None)
def _cmap(name):
    from fontTools.ttLib import TTFont
    return set(TTFont(FONT_FILES[name], fontNumber=0).getBestCmap())


def _font_for(ch, name, size, weight):
    """글리프가 없는 글자(《》 등)는 serif 로 대신 그린다."""
    if ch == " " or ord(ch) in _cmap(name):
        return font(name, size, weight)
    return font("serif", size, 600)


def text_img(text, name, size, fill, weight=None, track=0, ss=1, stroke=0, stroke_fill=None):
    """글자 한 줄을 투명 이미지로 ('ss' 배로 그려 축소)."""
    f = font(name, size * ss, weight)
    asc, desc = f.getmetrics()
    sw = stroke * ss
    w = 0
    for ch in text:
        w += _font_for(ch, name, size * ss, weight).getlength(ch) + track * ss
    w = int(w - track * ss + 2 * sw + 4 * ss)
    im = Image.new("RGBA", (max(1, w), asc + desc + 2 * sw + 2 * ss + size * ss // 5), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = sw + ss
    for ch in text:
        fc = _font_for(ch, name, size * ss, weight)
        d.text((x, sw + ss), ch, font=fc, fill=fill, stroke_width=sw, stroke_fill=stroke_fill)
        x += fc.getlength(ch) + track * ss
    if ss > 1:
        im = im.resize((max(1, im.width // ss), max(1, im.height // ss)), Image.LANCZOS)
    return im


def ink_offset(name, size, weight=None):
    """한글 글자 잉크의 세로 중심 (그림 위쪽 기준 px)"""
    f = font(name, size, weight)
    b = f.getbbox("한글")
    return 1 + (b[1] + b[3]) / 2


def draw_text(canvas, x, yc, text, name="callig", size=32, fill=TAN, weight=None, track=0,
              stroke=0, stroke_fill=None, align="l"):
    """(x, yc) = 왼쪽(또는 align) 끝, 글자 잉크 세로 중심. 반환: 글자 폭"""
    im = text_img(text, name, size, fill, weight, track, 1, stroke, stroke_fill)
    oy = ink_offset(name, size, weight) + stroke
    w = im.width - 2
    if align == "c":
        x -= w / 2
    elif align == "r":
        x -= w
    canvas.alpha_composite(im, (int(round(x)) - 1 - stroke, int(round(yc - oy))))
    return w - 2 * stroke


def text_width(text, name="callig", size=32, weight=None, track=0):
    return sum(_font_for(c, name, size, weight).getlength(c) for c in text) + track * (len(text) - 1)


# ---------------------------------------------------------------- 카드 아이콘 제목
def _lum(a):
    return a[..., :3].astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)


def retitle(card, title, band=None, size=11, skip_left=0, color=None, weight=700, name="sans"):
    """작은 카드 이미지의 위쪽 제목 띠 글자를 지우고 한국어 제목을 쓴다.
    band = 제목 띠 높이(px), skip_left = 왼쪽 속성 표시(◆) 폭."""
    a = np.array(card).copy()
    h, w = a.shape[:2]
    bh = band or 14
    sub = a[:bh]
    lum = _lum(a)
    vis = a[..., 3] > 100
    # 띠 바탕색 = 띠 영역 밝기 중앙값, 글자 = 바탕과 밝기 차이 큰 픽셀
    rows = slice(2, bh - 1)
    xs = slice(skip_left + 1 if skip_left else 3, w - 3)
    bgl = np.median(lum[rows, xs][vis[rows, xs]])
    diff = np.abs(lum - bgl)
    m = np.zeros((h, w), bool)
    m[rows, xs] = (diff[rows, xs] > 45) & vis[rows, xs]
    if not m.any():
        return card
    tx = np.nonzero(m.any(0))[0]
    tcol = a[m][:, :3]
    if color is None:
        # 글자 색: 바탕과 가장 다른 픽셀들의 중앙값
        dd = diff[m]
        color = tuple(int(v) for v in np.median(tcol[dd >= np.percentile(dd, 60)], 0)) + (255,)
    bgpx = a[:bh][((diff < 25) & vis)[:bh]][:, :3]
    bgc = np.median(bgpx, 0) if len(bgpx) else np.array([30, 30, 30])
    mk = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    mk[bh:] = False
    mk[:, :skip_left + 1] = False
    a[mk, :3] = bgc.astype(np.uint8)
    out = Image.fromarray(a)
    # 제목: 가능한 크기로 (가로 = 원래 글자 영역 근처, 세로 = 띠)
    x0 = max(skip_left + 1, min(tx.min(), skip_left + 3))
    x1 = w - 2
    cx = (x0 + x1) / 2 if skip_left else w / 2
    avail = (x1 - x0) if skip_left else w - 4
    s = size
    while s > 7 and text_width(title, name, s, weight) > avail:
        s -= 0.5
    t = text_img(title, name, int(s * 4), color, weight, 0, 1)
    t = t.resize((max(1, round(t.width / 4)), max(1, round(t.height / 4))), Image.LANCZOS)
    bb = t.getbbox()
    if bb:
        t = t.crop(bb)
        ys = np.nonzero(m.any(1))[0]
        yc = (ys.min() + ys.max() + 1) / 2
        out.alpha_composite(t, (int(round(cx - t.width / 2)), int(round(yc - t.height / 2))))
    return out


# ---------------------------------------------------------------- 문단 조판
def keep_main_blob(im):
    """잘라낸 아이콘에서 가장 큰 덩어리(카드)와 붙은 것만 남긴다 (옆 글자 조각 제거)."""
    a = np.array(im).copy()
    m = (a[..., 3] > 0).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    if n > 2:
        big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        a[(lab != big) & (lab != 0)] = 0
    return Image.fromarray(a)


class Icon:
    def __init__(self, rect, title=None, dy=0, **kw):
        self.rect, self.title, self.dy, self.kw = rect, title, dy, kw

    def image(self, src):
        im = keep_main_blob(src.crop(self.rect))
        if self.title:
            im = retitle(im, self.title, **{k: v for k, v in self.kw.items() if k != "center"})
        return im


class HL:  # 검은 상자 + 흰 글자 강조
    def __init__(self, text):
        self.text = text


def card(rect, title=None, **kw):
    return Icon(rect, title, **kw)


def hl_box(template, width):
    """원본 강조 상자를 글자 없는 검은 상자로 만들고 가로로 늘린다(가장자리 유지)."""
    a = np.array(template).copy()
    a[..., :3] = 0
    t = Image.fromarray(a)
    h = t.height
    e = min(12, t.width // 3)
    width = max(width, 2 * e + 1)
    out = Image.new("RGBA", (width, h), (0, 0, 0, 0))
    out.alpha_composite(t.crop((0, 0, e, h)), (0, 0))
    out.alpha_composite(t.crop((t.width - e, 0, t.width, h)), (width - e, 0))
    mid = t.crop((e, 0, t.width - e, h)).resize((width - 2 * e, h), Image.BICUBIC)
    out.alpha_composite(mid, (e, 0))
    return out


def compose(src, lines, size=32, name="callig", fill=TAN, track=3, hl_rect=None, gap=3,
            base=None, x0=572):
    """lines: [(yc, [항목...], 옵션 dict)] — 항목 = 문자열 | Icon | HL.
    아이콘은 원래 y 위치 그대로, x 는 앞 항목 뒤에 이어 붙인다."""
    out = base if base is not None else Image.new("RGBA", src.size, (0, 0, 0, 0))
    tmpl = src.crop(hl_rect) if hl_rect else None
    for ln in lines:
        yc, items = ln[0], ln[1]
        o = ln[2] if len(ln) > 2 else {}
        x = o.get("x", x0)
        sz, fl, tr = o.get("size", size), o.get("fill", fill), o.get("track", track)
        for it in items:
            if isinstance(it, str):
                x += draw_text(out, x, yc, it, name, sz, fl, track=tr)
            elif isinstance(it, Icon):
                im = it.image(src)
                x += gap
                iy = int(round(yc - im.height / 2)) + it.dy if it.kw.get("center") else it.rect[1] + it.dy
                out.alpha_composite(im, (int(x), iy))
                x += im.width + gap
            elif isinstance(it, HL):
                tw = text_width(it.text, name, sz, track=tr)
                box = hl_box(tmpl, int(tw + 14))
                by = int(round(yc - box.height / 2))
                out.alpha_composite(box, (int(x), by))
                draw_text(out, x + 7, yc, it.text, name, sz, WHITE, track=tr)
                x += box.width
    return out


# ---------------------------------------------------------------- play_guide_text10 (수련)
def guide10(img):
    C = card
    L = [
        (260, ["이 작업대에서는 ", HL("수련"), "과 관련된 일을 할 수 있다."]),
        (346, ["1. 주인공", C((675, 301, 727, 369), "주인공"), "+ 영기",
               C((825, 301, 881, 369), "금 영기", skip_left=12), "= 수위", C((993, 301, 1045, 369), "수위")]),
        (389, ["(수련은 수위를 얻는 중요한 방법이다)"], {"fill": DARK}),
        (474, ["2. 주인공", C((682, 432, 734, 500), "주인공"), "+ 심법", C((835, 432, 887, 500), "분염경"),
               "= 능력(구결", C((1089, 432, 1141, 500)), "/ 기술", C((1240, 429, 1293, 500), "초진 일식"),
               "/ 천부", C((1395, 432, 1447, 500)), ")"]),
        (519, ["(심법마다 얻는 능력 카드가 다르다)"], {"fill": DARK}),
        (605, ["3. 오도", C((684, 563, 736, 631), "오도"), "+ 깨달음", C((835, 563, 887, 631), "약리"),
               "= 여러 가지 심법", C((1114, 563, 1166, 631), "백약보")]),
        (648, ["(스스로 오도하는 것이 심법을 얻는 중요한 방법이다)"], {"fill": DARK}),
    ]
    return compose(img, L, hl_rect=(975, 240, 1052, 279))


# 카드 그림 속 큰 글자 바꾸기 (심마 카드의 '贪', 손상 표시 '修' 등)
def swap_glyph(card, box, text, fill, test, name="brush", size=None, stroke=0, stroke_fill=None):
    """card 안 box 영역에서 test(arr)->bool 마스크 픽셀을 인페인트로 지우고 text 를 가운데에 쓴다."""
    a = np.array(card).copy()
    x0, y0, x1, y1 = box
    m = np.zeros(a.shape[:2], bool)
    m[y0:y1, x0:x1] = test(a[y0:y1, x0:x1].astype(np.int32))
    if not m.any():
        return card
    mk = cv2.dilate(m.astype(np.uint8) * 255, np.ones((3, 3), np.uint8))
    a[..., :3] = cv2.inpaint(np.ascontiguousarray(a[..., :3]), mk, 3, cv2.INPAINT_TELEA)
    out = Image.fromarray(a)
    ys, xs = np.nonzero(m)
    cx, cy = (xs.min() + xs.max() + 1) / 2, (ys.min() + ys.max() + 1) / 2
    hgt = size or (ys.max() - ys.min() + 1)
    s = 4
    t = text_img(text, name, int(hgt * 1.15 * s), fill, None, 0, 1, stroke * s, stroke_fill)
    t = t.crop(t.getbbox())
    r = hgt / t.height
    t = t.resize((max(1, round(t.width * r)), max(1, round(t.height * r))), Image.LANCZOS)
    out.alpha_composite(t, (int(round(cx - t.width / 2)), int(round(cy - t.height / 2))))
    return out


class Swap(Icon):  # 그림 속 글자까지 바꾸는 아이콘
    def __init__(self, rect, title=None, swap=None, **kw):
        super().__init__(rect, title, **kw)
        self.swap = swap

    def image(self, src):
        im = super().image(src)
        return swap_glyph(im, **self.swap) if self.swap else im


def _pink(a):
    return (a[..., 0] > 110) & (a[..., 0] - a[..., 1] > 40) & (a[..., 3] > 100)


def _white(a):
    l = a[..., :3].min(-1)
    return (l > 185) & (a[..., 3] > 100)


INNER_GREED = dict(box=(6, 10, 46, 60), text="탐", fill=(200, 110, 105, 255), test=_pink)
BROKEN = dict(box=(20, 30, 52, 62), text="수", fill=(240, 240, 240, 255), test=_white,
              stroke=1, stroke_fill=(60, 60, 60, 255))

SPIRIT = dict(skip_left=12)  # 왼쪽에 속성 표시가 있는 카드


# ---------------------------------------------------------------- play_guide_text11 (연제)
def guide11(img):
    C = card
    L = [
        (260, ["이곳에서 카드를 연제해 ", HL("새로운"), " 다른 카드로 만들 수 있다."]),
        (345, ["1. 아무 재료", C((749, 301, 805, 369), "발톱", **SPIRIT), "+ 아무 재료",
               C((975, 301, 1031, 369), "짐승 뼈", **SPIRIT), "x4 = 새 법보", C((1266, 301, 1321, 372), "적염도")]),
        (390, ["(재료를 1~5개 넣으면 모두 새 법보를 연제할 수 있다)"], {"fill": DARK}),
        (475, ["2. 아무 약초", C((760, 430, 812, 498), "지혈초"), "+ 아무 약초",
               C((949, 430, 1001, 498), "백령삼"), "x4 = 단약", C((1164, 430, 1216, 498), "화어단")]),
        (519, ["(약초를 1~5개 넣으면 모두 단약을 연제할 수 있다)"], {"fill": DARK}),
        (605, ["3. 영기", C((680, 561, 736, 629), "금 영기", **SPIRIT), "+ 영기",
               C((829, 561, 885, 629), "금 영기", **SPIRIT), "(같은 속성) = 아무 재료",
               C((1278, 561, 1334, 629), "성휘정", **SPIRIT)]),
        (691, ["4. 내단", C((685, 647, 737, 715), "내단"), "+ 짐승 피", C((834, 647, 886, 715), "짐승 피"),
               "= 재료", C((997, 647, 1053, 715), "발톱", **SPIRIT), "/ 영기",
               C((1150, 647, 1206, 715), "금 영기", **SPIRIT), "/ 다른 카드(확률)"]),
        (735, ["(요수를 처치하고 얻은 내단은 이곳에서 다른 카드로 연제할 수 있다)"], {"fill": DARK}),
    ]
    return compose(img, L, hl_rect=(976, 240, 1053, 279))


# ---------------------------------------------------------------- play_guide_text12 (회복)
def guide12(img):
    C = card
    L = [
        (261, ["이곳에서 다친 카드의 ", HL("생명을 회복"), "하거나, 부정적인 카드를 없앨 수 있다."]),
        (346, ["1. 다친 카드", C((752, 301, 808, 372), "주인공"), "= 생명 회복", C((1031, 301, 1087, 372), "주인공")]),
        (433, ["2. 손상된 법보", Swap((795, 388, 850, 459), "비홍검", swap=BROKEN), "+ 수리 재료",
               C((1017, 388, 1073, 456), "성휘정", **SPIRIT), "= 온전한 법보", C((1259, 388, 1315, 459), "비홍검")]),
        (519, ["3. 심마", Swap((684, 476, 736, 544), swap=INNER_GREED), "+ 심경",
               C((833, 476, 885, 544), "심경"), "(생략 가능) = 심마 제거"]),
        (605, ["4. 짐승 피", C((684, 562, 736, 630), "짐승 피"), "= 영기",
               C((847, 562, 903, 630), "금 영기", **SPIRIT), "(무작위)"]),
        (691, ["5. 재료", C((680, 649, 736, 717), "성휘정", **SPIRIT), "= 전체 회복 진법 발동"]),
    ]
    return compose(img, L, hl_rect=(976, 240, 1165, 279))


# ---------------------------------------------------------------- play_guide_text13 (배양)
def guide13(img):
    C = card
    L = [
        (261, ["이곳에서 영약을 심거나 카드의 품질을 높일 수 있다."]),
        (346, ["1. 약초", C((667, 301, 719, 369), "지혈초"), "+ 아무 영기",
               C((887, 301, 943, 369), "금 영기", **SPIRIT), "(생략 가능) = 같은 영약",
               C((1335, 301, 1387, 369), "지혈초"), "(수량 무작위)"]),
        (432, ["2. 재료", C((671, 388, 727, 456), "성휘정", **SPIRIT), "+ 재료",
               C((820, 388, 876, 456), "짐승 뼈", **SPIRIT), "(조건 충족) = 재료 품질 상승",
               C((1376, 388, 1432, 456), "성휘정", **SPIRIT)]),
        (519, ["3. 법보", C((673, 476, 729, 547), "비홍검"), "+ 재료",
               C((819, 476, 875, 544), "성휘정", **SPIRIT), "(조건 충족) = 법보 품질 상승",
               C((1378, 476, 1433, 547), "비홍검")]),
        (605, ["4. 요수", C((673, 562, 725, 630), "비휴"), "+ 내단", C((824, 562, 876, 630), "내단"),
               "= 품질 상승", C((1064, 562, 1116, 630), "비휴")]),
    ]
    return compose(img, L)


# ---------------------------------------------------------------- play_guide_text14 (탐색)
def guide14(img):
    C = card
    L = [
        (260, ["이곳에서 장소를 탐색하고, 단서를 조사하고, 회상 이야기를 해금할 수 있다."]),
        (345, ["1. 주인공", C((674, 301, 726, 369), "주인공"), "/ 신식", C((823, 301, 875, 369), "신식"),
               "= 탁상 위의 장소 탐색"]),
        (432, ["2. XX의 땅 단서", C((807, 388, 859, 456), "위험한 땅"), "/ XXX 소문",
               C((1027, 388, 1079, 456), "소문"), "= 보상 또는 비경"]),
        (519, ["3. 회상", C((684, 476, 736, 544), "회상"), "+ 단서", C((832, 476, 884, 544), "단서"),
               "= 완전한 회상"]),
        (605, ["4. NPC 신념", C((759, 563, 811, 631), "NPC 신념"), "= NPC 소환", C((1003, 563, 1055, 631))]),
    ]
    return compose(img, L)


def measure(it, name, size, track, gap=3):
    if isinstance(it, str):
        return text_width(it, name, size, track=track)
    if isinstance(it, HL):
        return text_width(it.text, name, size, track=track) + 14
    return it.rect[2] - it.rect[0] + 2 * gap


def flow(items, x0, x1, y0, pitch, indent=0, name="callig", size=32, track=3):
    """항목(문자열/아이콘)을 [x0, x1] 폭으로 줄바꿈해 compose 용 줄 목록으로. 문자열은 공백에서 끊는다."""
    toks = []  # (항목, 앞에서 끊을 수 있나)
    for it in items:
        if isinstance(it, str):
            words = it.split(" ")
            for k, w in enumerate(words):
                if k:
                    toks.append((" ", True))
                if w:
                    toks.append((w, k > 0))
        else:
            toks.append((it, False))
    lines, cur, x, y = [], [], x0 + indent, y0
    start = x
    for t, brk in toks:
        w = measure(t, name, size, track)
        if brk and x + w > x1 and cur:
            while cur and cur[-1] == " ":
                cur.pop()
            lines.append((y, cur, {"x": start}))
            cur, x, y = [], x0, y + pitch
            start = x0
        if t == " " and not cur:
            continue
        if isinstance(t, str) and cur and isinstance(cur[-1], str):
            cur[-1] += t
        else:
            cur.append(t)
        x += w + (track if isinstance(t, str) else 0)
    if cur:
        lines.append((y, cur, {"x": start}))
    return lines, y + pitch


# ---------------------------------------------------------------- game_introduction (게임 소개)
def game_intro(img):
    CARD = card((944, 454, 976, 497), center=True)
    TABLE = card((1575, 488, 1635, 547), center=True)
    X0, X1, P = 572, 1755, 43
    L = [(260, ["《카드 수선전》은 ", HL("수묵 동양풍"), " 스타일, ", HL("수선"), " 소재의 ",
                HL("카드 관리"), " 탁상 게임이다."]),
         (346, ["게임 특징:"])]
    y = 390
    for para in (
        ["게임은 탁상 위의 세계를 무대로 한다. 세계에 흔히 있는 실체(법보, 단약, 인물, 괴물 등)든 "
         "추상적인 개념(플레이어의 수위, 구결, 수행 중의 기연, 수련의 깨달음 등)이든 모두 한 장의 카드",
         CARD, " 형태로 존재한다."],
        ["게임의 '행동'(수련, 연제, 탐색 등)은 작업대", TABLE, " 형태로 존재한다."],
        ["따라서 게임의 플레이 방식은 이렇다: 서로 다른 개념의 카드", CARD,
         "를 해당 '행동'의 작업대", TABLE, "에 넣고, 시간을 들여 새로운 카드를 얻는 것이다."],
    ):
        ls, y = flow(para, X0, X1, y, P, indent=80)
        L += ls
    return compose(img, L, hl_rect=(1197, 240, 1274, 279))


# ---------------------------------------------------------------- play_shortcut_keys (단축키 안내)
def clear_rects(img, rects):
    a = np.array(img).copy()
    for x0, y0, x1, y1 in rects:
        a[y0:y1, x0:x1] = 0
    return Image.fromarray(a)


SHORTCUT_LABELS = [  # (지울 영역, 한국어, 정렬 기준 x, 정렬, 색)
    ((128, 22, 330, 50), "설정/작업대 닫기", None, "c"),
    ((436, 4, 626, 31), "임무 표시줄 열기/닫기", None, "c"),
    ((268, 74, 336, 99), "확대", None, "c"),
    ((376, 74, 443, 99), "축소", None, "c"),
    ((340, 124, 372, 151), "위", None, "c"),
    ((538, 109, 644, 137), "빠른 저장", None, "c"),
    ((1023, 58, 1139, 86), "카드 더블클릭 시", None, "c"),
    ((985, 87, 1173, 114), "해당 작업대에 넣기", None, "c"),
    ((1104, 130, 1296, 157), "카드를 슬롯에 넣기", None, "c"),
    ((1130, 159, 1270, 186), "또는 창 닫기", None, "c"),
    ((4, 280, 159, 308), "시간 흐름 속도 전환", 156, "r"),
    ((54, 334, 159, 362), "카메라 이동", 156, "r"),
    ((300, 493, 343, 519), "왼쪽", None, "c"),
    ((356, 516, 399, 541), "아래", None, "c"),
    ((409, 494, 450, 519), "오른쪽", None, "c"),
    ((520, 514, 699, 542), "일시정지/게임 시작", None, "c"),
    ((446, 552, 499, 580), "수확", None, "c"),
    ((446, 596, 577, 622), "작업대 가동", None, "c"),
    ((1086, 516, 1207, 544), "확대/축소", None, "c"),
]


def shortcut_keys(img):
    a = np.array(img)
    out = clear_rects(img, [r for r, *_ in SHORTCUT_LABELS])
    for (x0, y0, x1, y1), t, ax, al in SHORTCUT_LABELS:
        sub = a[y0:y1, x0:x1]
        px = sub[sub[..., 3] > 200]
        col = tuple(int(v) for v in np.median(px, 0)[:3]) + (255,) if len(px) else BLACK
        ys = np.nonzero((sub[..., 3] > 60).any(1))[0]
        yc = y0 + (ys.min() + ys.max() + 1) / 2 if len(ys) else (y0 + y1) / 2
        sz = 22
        lim = (ax - 2) if al == "r" else None
        while lim and text_width(t, "callig", sz, track=1) > lim and sz > 14:
            sz -= 1
        x = ax if al == "r" else (x0 + x1) / 2
        draw_text(out, x, yc, t, "callig", sz, col, track=1, align=al)
    return out


# ---------------------------------------------------------------- 스크린샷/포스터 속 글자 바꾸기
def ui_label(img, rect, text, name="sans", weight=500, size=None, fill=None, align="l", thresh=60,
             dx=0, dy=0, track=0, keep=None, scale=1.0, stroke=0, stroke_fill=None, bg=None, x=None,
             flat=False):
    """rect 안에서 바탕과 다른 글자 픽셀을 찾아 인페인트로 지우고, 같은 자리에 text 를 쓴다.
    size 가 없으면 원래 글자 높이에 맞춘다. align: l(원래 글자 왼쪽 기준) / c / r. keep = 건드리지 않을 영역(rect 기준 좌표 아님, 전체 좌표)."""
    a = np.array(img).copy()
    x0, y0, x1, y1 = rect
    sub = a[y0:y1, x0:x1, :3].astype(np.int32)
    edge = np.concatenate([sub[0], sub[-1], sub[:, 0], sub[:, -1]])
    bgc = np.median(edge, 0) if bg is None else np.array(bg[:3])
    diff = np.abs(sub - bgc).sum(-1)
    m = diff > thresh
    if keep:
        for kx0, ky0, kx1, ky1 in keep:
            m[max(0, ky0 - y0):max(0, ky1 - y0), max(0, kx0 - x0):max(0, kx1 - x0)] = False
    if not m.any():
        return img
    ys, xs = np.nonzero(m)
    tb = (x0 + xs.min(), y0 + ys.min(), x0 + xs.max() + 1, y0 + ys.max() + 1)
    if fill is None:
        dd = diff[m]
        fill = tuple(int(v) for v in np.median(sub[m][dd >= np.percentile(dd, 70)], 0)) + (255,)
    full = np.zeros(a.shape[:2], np.uint8)
    full[y0:y1, x0:x1] = m
    mk = cv2.dilate(full * 255, np.ones((5, 5), np.uint8))
    mk[:y0] = 0; mk[y1:] = 0; mk[:, :x0] = 0; mk[:, x1:] = 0
    if flat:  # 단색 바탕: 영역 전체를 바탕색으로
        a[y0:y1, x0:x1, :3] = bgc.astype(np.uint8)
    else:
        a[..., :3] = cv2.inpaint(np.ascontiguousarray(a[..., :3]), mk, 4, cv2.INPAINT_TELEA)
    out = Image.fromarray(a)
    hgt = tb[3] - tb[1]
    if size is None:
        f = font(name, 100, weight)
        b = f.getbbox("한")
        size = max(6, round(hgt / ((b[3] - b[1]) / 100) * scale))
    yc = (tb[1] + tb[3]) / 2 + dy
    if x is None:
        x = {"l": tb[0], "c": (tb[0] + tb[2]) / 2, "r": tb[2]}[align]
    ss = 4 if size < 40 else 1
    t = text_img(text, name, size * ss, fill, weight, track * ss, 1, stroke * ss, stroke_fill)
    if ss > 1:
        t = t.resize((max(1, round(t.width / ss)), max(1, round(t.height / ss))), Image.LANCZOS)
    oy = ink_offset(name, size, weight) + stroke
    w = t.width - 2
    px = x + dx - (w / 2 if align == "c" else w if align == "r" else 0)
    out.alpha_composite(t, (int(round(px)) - 1, int(round(yc - oy))))
    return out


def relabel_all(img, labels, **common):
    for lb in labels:
        rect, text = lb[0], lb[1]
        kw = dict(common, **(lb[2] if len(lb) > 2 else {}))
        img = ui_label(img, rect, text, **kw)
    return img


# ---------------------------------------------------------------- steam_teach (Steam 베타 버전 받는 법)
STEAM = [
    # 제목, 단계 설명 (흰 바탕)
    ((330, 30, 1125, 92), "Steam에서 게임 테스트 버전으로 업데이트하는 방법", {"align": "c", "weight": 600, "x": 728, "flat": True}),
    ((36, 124, 1420, 177), "1. Steam을 열고 '라이브러리' 클릭 → '카드 수선전'을 마우스 오른쪽 버튼으로 클릭 → 목록에서 '속성...' 클릭",
     {"size": 29, "flat": True}),
    ((36, 680, 1330, 732), "2. 열린 창의 왼쪽에서 '게임 버전 및 베타' 선택 → 오른쪽 목록에서 'public_beta' 선택",
     {"size": 29, "flat": True}),
    # 스크린샷 1: Steam 라이브러리
    ((122, 184, 155, 205), "보기"), ((160, 184, 193, 205), "친구"), ((197, 184, 230, 205), "게임"),
    ((235, 184, 268, 205), "도움말"),
    ((116, 211, 250, 235), "상점   라이브러리   커뮤니티", {"size": 13}),
    ((52, 262, 88, 284), "홈"), ((55, 307, 90, 329), "게임"),
    ((63, 383, 113, 404), "미분류", {"dx": 3}),
    ((96, 432, 166, 454), "카드 수선전", {"size": 14}),
    ((295, 453, 360, 472), "플레이", {"thresh": 150, "size": 14}),
    ((370, 549, 391, 572), "플", {"thresh": 150, "size": 14}),
    ((272, 482, 360, 505), "즐겨찾기에 추가", {"size": 12}),
    ((272, 517, 322, 539), "다음에 추가", {"size": 13}),
    ((272, 549, 308, 572), "관리"),
    ((272, 582, 318, 605), "속성..."),
    # 스크린샷 2: 속성 창
    ((62, 772, 160, 798), "카드 수선전"),
    ((62, 822, 102, 846), "일반"), ((62, 859, 102, 883), "업데이트"), ((62, 895, 142, 919), "설치된 파일"),
    ((62, 929, 186, 953), "게임 버전 및 베타"),
    ((62, 967, 115, 989), "컨트롤러"), ((62, 1003, 130, 1025), "게임 녹화"), ((62, 1039, 130, 1061), "개인 정보"),
    ((62, 1075, 115, 1097), "사용자 지정"),
    ((258, 766, 446, 799), "게임 버전 및 베타"),
    ((258, 812, 380, 833), "선택된 게임 버전"),
    ((258, 838, 742, 860), "이 버전은 게임 개발자가 제공하며, 불안정한 테스트 버전이나 이전 버전일 수 있습니다. 신중히 진행하세요.", {"size": 12}),
    ((298, 888, 374, 910), "이름 및 설명"),
    ((768, 888, 856, 910), "최근 업데이트", {"align": "r"}),
    ((301, 933, 386, 955), "기본 공개 버전"),
    ((303, 955, 401, 973), "가장 일반적인 게임 버전", {"size": 13, "thresh": 80}),
    ((258, 1163, 324, 1185), "비공개 버전"),
    ((258, 1183, 540, 1205), "액세스 코드를 입력해 비공개 게임 버전이나 테스트 버전 잠금 해제:"),
    ((781, 1219, 844, 1243), "코드 확인", {"align": "c"}),
]


def steam_teach(img):
    out = relabel_all(img, STEAM)
    return out


# ---------------------------------------------------------------- plan_next (향후 업데이트 계획 포스터)
INK = (35, 27, 23, 255)
BAR_TEXT = (243, 245, 243, 255)


def _hsv_masks(a):
    rgb = a[..., :3].astype(np.float32)
    lum = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
    mx, mn = rgb.max(-1), rgb.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1)
    return lum, sat


def erase(img, mask, radius=4, dil=2):
    a = np.array(img).copy()
    mk = mask.astype(np.uint8) * 255
    if dil:
        mk = cv2.dilate(mk, np.ones((2 * dil + 1, 2 * dil + 1), np.uint8))
    a[..., :3] = cv2.inpaint(np.ascontiguousarray(a[..., :3]), mk, radius, cv2.INPAINT_TELEA)
    return Image.fromarray(a)


def wrap_runs(runs, x0, x1, name, size, first_x=None, track=0):
    """runs = [(문자열, weight)] → 줄 목록 [[(x, 문자열, weight)...]]. 공백에서 줄바꿈."""
    toks = []
    for text, wt in runs:
        parts = text.split(" ")
        for k, p in enumerate(parts):
            if k:
                toks.append((" ", wt, True))
            if p:
                toks.append((p, wt, k > 0 or not toks))
    lines, cur = [], []
    x = first_x if first_x is not None else x0
    for t, wt, brk in toks:
        w = text_width(t, name, size, wt, track)
        if t != " " and brk and x + w > x1 and cur:
            while cur and cur[-1][1] == " ":
                cur.pop()
            lines.append(cur)
            cur, x = [], x0
        if t == " " and not cur:
            continue
        cur.append((x, t, wt))
        x += w + track
    if cur:
        lines.append(cur)
    return lines


def plan_body(out, blocks, size=17, pitch=29, x0=45, x1=512, name="serif"):
    """blocks = [(시작 y(첫 줄 글자 중심), [문단...])], 문단 = [(글자, weight)] (+ 들여쓰기 없음)."""
    for y, paras in blocks:
        for para in paras:
            gap = 0
            if para and para[0] == "GAP":
                gap, para = para[1], para[2:]
            y += gap
            for ln in wrap_runs(para, x0, x1, name, size):
                for x, t, wt in ln:
                    draw_text(out, x, y, t, name, size, INK, weight=wt)
                y += pitch
    return out


def stamp_text(out, rect, text, angle, size, fill=WHITE, name="callig"):
    """도장(빨간 상자) 안 흰 글자를 지우고 기울여 다시 쓴다."""
    a = np.array(out)
    x0, y0, x1, y1 = rect
    lum, sat = _hsv_masks(a[y0:y1, x0:x1])
    m = np.zeros(a.shape[:2], bool)
    m[y0:y1, x0:x1] = (lum > 170) & (sat < 0.35)
    out = erase(out, m, 3, 1)
    t = text_img(text, name, size * 4, fill, None, 0, 1)
    t = t.crop(t.getbbox()).rotate(angle, resample=Image.BICUBIC, expand=True)
    t = t.resize((max(1, t.width // 4), max(1, t.height // 4)), Image.LANCZOS)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    out.alpha_composite(t, (int(cx - t.width / 2), int(cy - t.height / 2)))
    return out


def bar_text(out, rect, text, size=17, x=None):
    """어두운 띠 위 흰 글자(연월 제목)를 지우고 다시 쓴다. 띠 폭에 맞춰 줄인다."""
    a = np.array(out)
    x0, y0, x1, y1 = rect
    lum, sat = _hsv_masks(a[y0:y1, x0:x1])
    m = np.zeros(a.shape[:2], bool)
    m[y0:y1, x0:x1] = lum > 120
    out = erase(out, m, 3, 1)
    s = size
    while text_width(text, "serif", s, 700) > (x1 - x0) - 16 and s > 10:
        s -= 0.5
    draw_text(out, x if x is not None else x0 + 8, (y0 + y1) / 2, text, "serif", int(round(s)), BAR_TEXT, weight=700)
    return out


B, R = 800, 500  # 굵게 / 보통

PLAN_BLOCKS = [
    (396, [
        [("1. 어검비행 개선: ", B), ("카드를 한 번만 놓으면 되도록 조작 단계 축소", R)],
        [("2. 편의성 설정 추가: ", B), ("글자 크기, 대화 속도, 자동 일시정지, 전송문 시간 등 조절 지원", R)],
        [("3. 용기 법보 기능 개선: ", B), ("용기마다 해당 종류의 법보/영수를 수납할 수 있고, 전투 중 자동으로 펼쳐지며 영기를 소모하지 않음", R)],
        [("4. 지도 기능 개선: ", B), ("지도에 주인공 위치와 발견한 장소 표시", R)],
        [("5. 게임 수치·안내·기능 체험 개선: ", B), ("요수 횡행 임무 안내, 아이템 설명, 무작위 드롭 확률 등 개선", R)],
    ]),
    (721, [
        [("1. 난이도 선택이 있는 자유 모드와 스토리 모드 추가:", B)],
        [("자유 모드에서는 주인공의 초기 속성, 기본 천부, 출신 등 시작 조건을 자유롭게 설정할 수 있다. 또한 여러 단계의 난이도 선택이 추가된다:", R)],
        [("체험 난이도: ", B), ("괴물이 약하고, 전투로 얻는 재료의 경지가 더 높으며, 카드가 사라지는 시간이 더 길다.", R)],
        [("보통 난이도: ", B), ("괴물 수치가 평균적이며, 게임 시스템을 어느 정도 아는 플레이어에게 알맞다.", R)],
        [("도전 난이도: ", B), ("괴물 수치가 더 높고, 영석 얻기가 더 어려우며, 카드가 사라지는 시간이 더 짧다 등.", R)],
        [("진선 난이도: ", B), ("수치와 생존 압박이 한층 더 높아지며, 집중 모드에서만 선택 가능.", R)],
        ["GAP", 14, ("2. 원영기 콘텐츠 일부 개방:", B)],
        [("경지가 원영기까지 열려 원영 심법을 수련하고, 원영 법보·영수·괴뢰 카드의 품질을 높일 수 있다.", R)],
        [("3. 피드백에 따라 게임 수치와 안내 지속 개선:", B)],
        [("여러분의 플레이 피드백을 계속 반영해 게임의 수치 표현, 성장 속도, 초보자 안내를 꾸준히 개선하겠습니다.", R)],
    ]),
    (1378, [
        [("1. 어검비행 중 기우 장소와 사건이 일어나는 시스템 재제작. 귀시, 문도대 등 다양한 비경 콘텐츠와 더 많은 NPC·서브 스토리 추가.", 700)],
        [("2. 원영기 콘텐츠: 장소·비경을 카드로 바꿔 법보, 기술, 구결 연제에 사용 가능.", 700)],
        [("3. 결단·원영 경지 콘텐츠 보완: 비경, NPC 서브 스토리, 심법, 기술, 천부 등 추가.", 700)],
        [("4. 자유 모드와 난이도 모드 조정 및 보완.", 700)],
    ]),
    (1678, [
        [("1. 메인 스토리 추가 — ", B), ("소련연 캐릭터 플레이와 전용 스토리", R)],
        [("2. 메인 스토리 추가 — ", B), ("육일진 캐릭터 플레이와 전용 스토리", R)],
        [("3. 메인 스토리 추가 — ", B), ("냉봉 캐릭터 플레이와 전용 스토리", R)],
        [("4. NPC 서브 임무 지속 추가", B)],
    ]),
    (1850, [[(t, R)] for t in ["1. 교역회 콘텐츠", "2. 지하 비무 콘텐츠", "3. 더 깊어진 종문 콘텐츠",
                               "4. 플레이 방식이 다른 다양한 비경", "5. NPC 서브 임무 지속 추가",
                               "6. 그 밖의 새로운 콘텐츠 추가"]]),
]

# 본문 글자가 있는 줄 (y0, y1) — 이 범위의 어두운 글자 픽셀만 지운다
PLAN_TEXT_ROWS = [(380, 662), (705, 1080), (1110, 1298), (1362, 1615), (1662, 1788), (1834, 2022)]
PLAN_BARS = [  # (띠 안쪽 영역, 한국어)
    ((38, 349, 147, 373), "2026년 3월"),
    ((38, 671, 318, 697), "2026년 4월 테스트 브랜치 공개"),
    ((38, 1331, 463, 1357), "2026년 5월 원영 콘텐츠 순차 업데이트"),
    ((38, 1628, 463, 1654), "2026년 6월  5월 말 상세 업데이트 내용 공개"),
    ((38, 1800, 463, 1826), "2026년 중  6월 말 상세 업데이트 내용 공개"),
]


def plan_title(out):
    """큰 제목 '未来更新计划'(흰 붓글씨 + 검은 테두리)과 부제 띠."""
    a = np.array(out)
    lum, sat = _hsv_masks(a)
    x0, y0, x1, y1 = 90, 186, 450, 250
    white = np.zeros(lum.shape, bool)
    white[y0:y1, x0:x1] = (lum[y0:y1, x0:x1] > 200) & (sat[y0:y1, x0:x1] < 0.15)
    near = cv2.dilate(white.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    m = white | (near & (lum < 90))
    out = erase(out, m, 7, 2)
    t = text_img("향후 업데이트 계획", "brush", 62 * 4, WHITE, None, 2 * 4, 1, 4 * 4, (25, 25, 30, 255))
    t = t.crop(t.getbbox())
    t = t.resize((t.width // 4, t.height // 4), Image.LANCZOS)
    r = min(1.0, 370 / t.width)
    if r < 1:
        t = t.resize((int(t.width * r), int(t.height * r)), Image.LANCZOS)
    out.alpha_composite(t, (int(270 - t.width / 2), int(219 - t.height / 2)))
    # 부제 띠
    bx0, by0, bx1, by1 = 172, 258, 383, 280
    a = np.array(out)
    lum, sat = _hsv_masks(a)
    m = np.zeros(lum.shape, bool)
    m[by0:by1, bx0:bx1] = lum[by0:by1, bx0:bx1] > 110
    out = erase(out, m, 3, 1)
    draw_text(out, (bx0 + bx1) / 2, (by0 + by1) / 2, "5월 상세 업데이트 계획 발표", "callig", 14,
              (240, 240, 240, 255), track=1, align="c")
    return out


def plan_next(img):
    a = np.array(img)
    lum, sat = _hsv_masks(a)
    m = np.zeros(lum.shape, bool)
    for y0, y1 in PLAN_TEXT_ROWS:
        sl = (slice(y0, y1), slice(36, 514))
        m[sl] = (lum[sl] < 92) | ((lum[sl] < 112) & (sat[sl] < 0.3))
    # 띠 영역은 따로 처리
    for (x0, y0, x1, y1), _ in PLAN_BARS:
        m[y0 - 3:y1 + 3, x0 - 3:x1 + 3] = False
    out = erase(img, m, 4, 2)
    out = plan_body(out, PLAN_BLOCKS[:1], size=17, pitch=30)
    out = plan_body(out, PLAN_BLOCKS[1:2], size=16, pitch=29)
    out = plan_body(out, PLAN_BLOCKS[2:], size=16, pitch=29)
    out = plan_title(out)
    for r, t in PLAN_BARS:
        out = bar_text(out, r, t)
    out = stamp_text(out, (162, 328, 240, 366), "완료", 10, 20)
    out = stamp_text(out, (333, 658, 410, 696), "완료", 10, 20)
    return out


TUTORIAL = {
    "play_guide_text10": guide10,
    "play_guide_text11": guide11,
    "play_guide_text12": guide12,
    "play_guide_text13": guide13,
    "play_guide_text14": guide14,
    "game_introduction": game_intro,
    "play_shortcut_keys": shortcut_keys,
    "steam_teach": steam_teach,
    "plan_next": plan_next,
}
