"""스킬(Skill.dat) / 무기(Weapon.dat) 그림 속 한자 한글화 사양.

SKILLS  : UI/UISprites/Skill.dat, ArtData/Skill.dat 공통 (같은 이름 = 같은 그림, 단 주문 두루마리 17개는
          ArtData 쪽이 글자만 있는 300x406 투명 그림이라 크기로 나눠 처리)
WEAPONS : UI/UISprites/Weapon.dat, ArtData/Weapon.dat 공통

값은 imgedit.relabel spec / spec 리스트 / 함수(img -> img).
나무패(천부 패)와 술어 종이(71001~)는 글자 없는 바탕(image_assets/*.png, 같은 그림 수백 장에서
글자 부분을 빼고 중앙값으로 복원)으로 글자 자리를 덮은 뒤 한국어를 다시 쓴다.
"""
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from imgedit import _render, fit_text, relabel

ASSETS = Path(__file__).parent / "image_assets"
_cache = {}


def _asset(name):
    if name not in _cache:
        _cache[name] = np.array(Image.open(ASSETS / name).convert("RGBA"))
    return _cache[name]


def _restore(img, blank, box, thresh=25, dilate=2):
    """box 안에서 바탕과 다른 픽셀(=글자)을 글자 없는 바탕 픽셀로 바꾼다."""
    a = np.array(img.convert("RGBA"))
    x0, y0, x1, y1 = box
    d = np.abs(a[y0:y1, x0:x1, :3].astype(int) - blank[y0:y1, x0:x1, :3].astype(int)).max(-1) > thresh
    m = np.zeros(a.shape[:2], np.uint8)
    m[y0:y1, x0:x1] = d
    if dilate:
        m = cv2.dilate(m, np.ones((2 * dilate + 1, 2 * dilate + 1), np.uint8))
    a[m > 0] = blank[m > 0]
    return a, m > 0


def _paste_text(img, t, cx, cy):
    out = img if isinstance(img, Image.Image) else Image.fromarray(img)
    out.alpha_composite(t, (int(cx - t.width / 2), int(cy - t.height / 2)))
    return out


def chain(*steps):
    """spec / spec 리스트 / 함수를 차례로 적용하는 함수 (image_specs.apply 의 리스트는 함수를 못 담음)"""
    def f(img):
        for st in steps:
            for s in (st if isinstance(st, list) else [st]):
                img = s(img) if callable(s) else relabel(img, s)
        return img
    return f


def _white(text, font, layout, gap, size=200):
    """흰 글자 (굵기·외곽선 없이). 세로쓰기는 글자 사이를 gap(글자 크기 대비)만큼 띄운다."""
    if layout != "v":
        return _render(text, font, size, layout, (255, 255, 255, 255), None, 0)
    gl = [_render(c, font, size, "h", (255, 255, 255, 255), None, 0) for c in text]
    W = max(g.width for g in gl)
    H = sum(g.height for g in gl) + int(size * gap) * (len(gl) - 1)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    y = 0
    for g in gl:
        im.alpha_composite(g, ((W - g.width) // 2, y))
        y += g.height + int(size * gap)
    return im


def draw_text(text, font, bw, bh, layout="h", fill=(255, 255, 255, 255), edge=None, edge_w=0.0, bold=0.0,
              gap=0.12):
    """(bw, bh) 에 맞춘 글자 이미지. 굵기/외곽선은 PIL stroke 대신 알파 팽창으로 만든다.
    (Song Myung 의 '택'·'팀' 처럼 윤곽이 겹친 글리프는 PIL stroke 를 쓰면 획이 깨진다)"""
    size = 200
    t = _white(text, font, layout, gap, size)
    rb, re = int(round(size * bold)), (int(round(size * edge_w)) if edge else 0)
    pad = rb + re + 2
    a = np.pad(np.array(t.getchannel("A")), pad)

    def grow(x, r):
        return cv2.dilate(x, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))) if r > 0 else x
    core = grow(a, rb)
    out = np.zeros(a.shape + (4,), np.float32)
    if edge:
        out[..., :3] = edge[:3]
        out[..., 3] = grow(core, re).astype(np.float32) / 255 * (edge[3] if len(edge) > 3 else 255)
    c = core.astype(np.float32) / 255
    fa = c * (fill[3] if len(fill) > 3 else 255)
    oa = out[..., 3] * (1 - c)
    na = fa + oa
    rgb = (np.array(fill[:3], np.float32) * fa[..., None] + out[..., :3] * oa[..., None]) / np.maximum(na, 1e-6)[..., None]
    im = Image.fromarray(np.dstack([rgb, na]).clip(0, 255).astype(np.uint8))
    im = im.crop(im.getbbox())
    r = min(bw / im.width, bh / im.height)
    return im.resize((max(1, round(im.width * r)), max(1, round(im.height * r))), Image.LANCZOS)


def _vtext(text):  # 세로쓰기: 띄어쓰기는 뺀다
    return text.replace(" ", "")


# ---------------------------------------------------------------- 천부 나무패 (80001~87066, 300x406)
TAG_BOX = (100, 85, 205, 360)        # 글자가 있는 세로 띠
TAG_TEXT = (151, 220)                # 글자 중심
TAG_CHAR = 64                        # 원문 글자 한 칸 높이
TAG_MAXH = 252


def _tag_colors(a, m):
    px = a[m][:, :3].astype(int)
    if not len(px):
        return (240, 220, 195), (70, 50, 32)
    mx = px.max(1)
    hi, lo = px[mx >= np.percentile(mx, 85)], px[mx <= np.percentile(mx, 30)]
    return tuple(int(v) for v in np.median(hi, 0)), tuple(int(v) for v in np.median(lo, 0))


def tag(text):
    def f(img):
        if img.size != (300, 406):
            return img
        orig = np.array(img.convert("RGBA"))
        a, m = _restore(img, _asset("skill_tag_blank.png"), TAG_BOX, thresh=25, dilate=2)
        fill, edge = _tag_colors(orig, m)
        s = _vtext(text)
        h = min(TAG_MAXH, TAG_CHAR * len(s))
        t = draw_text(s, "callig", 68, h, "v", fill + (255,), edge + (255,), 0.11, 0.01)
        return _paste_text(a, t, *TAG_TEXT)
    return f


TAGS = {  # 텍스처 이름 = 앞 4자리 + 등급(1~6, 글자색만 다름)
    "8000": {1: "어검비행", 2: "어검비행", 3: "천벌", 4: "심룡분금", 5: "어검비행", 6: "어검비행"},
    "8100": "검술 정통", "8101": "어검무봉", "8102": "검기 난사", "8103": "단사참", "8104": "기심통명",
    "8105": "금봉파", "8106": "소리장봉",
    "8200": "단원최화", "8201": "독술 정통", "8202": "천환독수", "8203": "독술 종사", "8204": "장생지법",
    "8205": "원운독술", "8206": "영식의 마음", "8207": "청명인", "8208": "만곡단원", "8209": "환진독수",
    "8210": "단원통현", "8211": "꽃의 혼", "8212": "낙엽귀근",
    "8300": "영력 친화", "8301": "영맥의 몸", "8302": "만법귀류", "8303": "법술 정통", "8304": "취령의 몸",
    "8305": "낙주회춘", "8306": "생생불식", "8307": "무형빙",
    "8400": "백련강구", "8401": "혈수강구", "8402": "진염도", "8403": "신혼단체", "8404": "태소연형",
    "8405": "천궁", "8406": "욕화의 몸",
    "8500": "생사계약", "8501": "어수지도", "8502": "태고의 혈맥", "8503": "부동여산", "8504": "수혼각성",
    "8505": "영유혈계", "8506": "재천순", "8507": "반석의 몸", "8508": "짐승과 함께 춤을",
    "8600": "서혼", "8601": "살육", "8602": "구혼", "8603": "탈령",
    "8700": "허경요관", "8701": "규천기", "8702": "염봉온기", "8703": "병갑통현", "8704": "통허영모",
    "8705": "회춘성체", "8706": "영서교수",
}

SKILLS = {}
for _base, _name in TAGS.items():
    for _tier in range(1, 7):
        SKILLS[f"{_base}{_tier}"] = tag(_name[_tier] if isinstance(_name, dict) else _name)

WEAPONS = {}


# ---------------------------------------------------------------- 술어 종이 (71001~71021, UI 전용 300x326)
PAPER_BOX = (40, 5, 260, 318)


def paper(text, font="callig", bold=0.03):
    def f(img):
        if img.size != (300, 326):
            return img
        a, _ = _restore(img, _asset("skill_paper_blank.png"), PAPER_BOX, thresh=40, dilate=2)
        s = _vtext(text)
        ch = min(88, 252 / len(s))
        t = draw_text(s, font, 96, ch * len(s), "v", (0, 0, 0, 255), bold=bold)
        return _paste_text(a, t, 151, 158)
    return f


SKILLS.update({
    "71001": paper("빛의 방패"), "71002": paper("도발"), "71003": paper("취약"), "71004": paper("피해 증가"),
    "71005": paper("피해 감소"), "71006": paper("고정 피해"), "71007": paper("원거리 공격"),
    "71008": paper("방어도"), "71009": paper("중독"), "71010": paper("소환"), "71011": paper("혼란"),
    "71012": paper("속박"), "71013": paper("봉인"), "71014": paper("복제"), "71015": paper("부활"),
    "71016": paper("흡혈"), "71017": paper("부정적 상태"), "71018": paper("패시브"), "71019": paper("대상 선택"),
    "71020": paper("고정 기술"), "71021": paper("본명기"),
})


# ---------------------------------------------------------------- 주문(구결) 두루마리
# UI: 300x326 두루마리 그림 / ArtData: 300x406 투명 바탕에 글자만
SCROLL_INK = (65, 62, 57)


def scroll(text):
    ui = {"text": text, "font": "callig", "mask": "dark", "thresh": 95, "box": (100, 38, 205, 245),
          "layout": "v", "fill": SCROLL_INK, "dilate": 2, "bold": 0.03}
    art = {"text": text, "font": "callig", "mask": "alpha", "layout": "v", "fill": SCROLL_INK,
           "dilate": 1, "bold": 0.03}

    def f(img):
        return relabel(img, art if img.size == (300, 406) else ui)
    return f


SKILLS.update({
    "157": scroll("성진인"),
    "61101": scroll("금망주"), "61102": scroll("환검결"), "62101": scroll("환목결"), "62202": scroll("장생주"),
    "62203": scroll("환령결"), "63101": scroll("치유결"), "63103": scroll("치유진"), "63104": scroll("한빙주"),
    "63105": scroll("응기주"), "63106": scroll("영원주"), "63202": scroll("환령주"), "64101": scroll("환화결"),
    "64202": scroll("취화결"), "65102": scroll("어수결"), "65201": scroll("현갑주"), "66101": scroll("노심주"),
})


# ---------------------------------------------------------------- 본명 법보 카드 (4711001~, UI 전용 300x326)
# 오른쪽 위 먹 자국 위 무지개색 '本命' → '본명'. 표식은 모든 카드에서 같은 자리·같은 모양.
BM_BOX = (214, 22, 294, 146)


def _rainbow(t):
    """흰 글자 이미지 t 를 위(빨강)→아래(자주) 무지개색으로 칠한다."""
    h = t.height
    hue = (np.linspace(0, 150, h)[:, None] * np.ones((1, t.width))).astype(np.uint8)  # OpenCV hue 0~179
    hsv = np.stack([hue, np.full_like(hue, 200), np.full_like(hue, 255)], -1)
    rgb = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    a = np.array(t)
    a[..., :3] = rgb
    return Image.fromarray(a)


def benming(img, text="본명"):
    if img.size != (300, 326):
        return img
    a = np.array(img.convert("RGBA"))
    m = _asset("skill_benming_mask.png")[..., 0] > 127
    mk = cv2.dilate(m.astype(np.uint8) * 255, np.ones((7, 7), np.uint8))
    a[..., :3] = cv2.inpaint(np.ascontiguousarray(a[..., :3]), mk, 4, cv2.INPAINT_TELEA)
    x0, y0, x1, y1 = BM_BOX
    t = fit_text(text, "callig", (x1 - x0) * 0.75, (y1 - y0) * 0.9, "v", (255, 255, 255, 255),
                 (255, 255, 255, 255), 0.04)
    return _paste_text(a, _rainbow(t), (x0 + x1) / 2 - 1, (y0 + y1) / 2)


# ---------------------------------------------------------------- 초식 번호 (그림 옆 금색 한 글자)
def numeral(text, box):
    return {"text": text, "font": "callig", "mask": "sat", "thresh": 0.3, "box": box, "dilate": 3,
            "bold": 0.05, "scale": 0.88}


SKILLS.update({
    "71103": numeral("이", (35, 70, 132, 147)),   # 初尘二式
    "71104": numeral("삼", (158, 186, 252, 262)),  # 初尘三式
    "75104": [{"mask": "sat", "thresh": 0.3, "box": (234, 14, 252, 112), "dilate": 3},  # 反击式贰
              numeral("이", (174, 14, 238, 114)) | {"text_box": (180, 20, 246, 108)}],
})


# ---------------------------------------------------------------- 영패에 새긴 글자
def ling(box, light=False, **kw):
    """은빛 영패의 '令' → '령' (먹 글씨 / 390103 은 흰 빛 글씨)"""
    sp = {"text": "령", "font": "callig", "mask": "light" if light else "dark", "thresh": 175 if light else 60,
          "box": box, "dilate": 2, "fill": (235, 245, 250) if light else (15, 15, 20), "bold": 0.03,
          "text_box": box, "scale": 0.85}
    if light:
        sp["glow"] = (3, (170, 220, 240, 160))
    sp.update(kw)
    return sp


def engraved(text, box, fill=(16, 34, 26), hi=(165, 220, 190, 220)):
    """옥패에 음각된 글자: 밝은 테두리·어두운 홈을 지우고 같은 방식으로 새긴다."""
    return [{"mask": "lighter", "thresh": 18, "box": box, "dilate": 1},
            {"text": text, "font": "callig", "mask": "darker", "thresh": 14, "box": box, "dilate": 1,
             "layout": "v", "fill": fill, "bold": 0.015, "text_box": box, "scale": 0.95,
             "shadow": (1, 1, hi)}]


SKILLS.update({k: benming for k in (
    [f"47110{i:02d}" for i in range(1, 23)] + [f"47120{i:02d}" for i in range(1, 20)]
    + [f"47130{i:02d}" for i in range(1, 22)] + [f"47140{i:02d}" for i in range(1, 18)]
    + [f"47150{i:02d}" for i in range(1, 23)] + [f"47160{i:02d}" for i in range(1, 16)]
    + [f"47170{i:02d}" for i in range(1, 9)] + [f"47180{i:02d}" for i in range(1, 8)])})
SKILLS["4713020"] = chain(benming, engraved("현수", (105, 135, 134, 195)))   # 墨玉牌: 玄水
SKILLS["4714008"] = chain(benming, ling((120, 143, 172, 216), text_box=(122, 150, 170, 210)))                 # 영패: 令

WEAPONS.update({
    "390101": ling((125, 133, 178, 198)),
    "390102": ling((126, 128, 180, 200)),
    "390103": ling((128, 120, 178, 190), light=True),
    "390601": engraved("현수", (115, 118, 148, 186)),
})
