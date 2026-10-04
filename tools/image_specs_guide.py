"""UI/UISprites/Guide.dat (튜토리얼 안내 이미지) 한글화 사양.

GUIDE = {텍스처 이름: spec | spec 리스트 | 함수(img -> img)}
카드 이름은 게임 내 한국어 이름(translation/ko.json)과 맞춘다.
"""
from PIL import Image, ImageDraw, ImageFont

from imgedit import FONTS, relabel

W = (245, 245, 240)
BLACK = (0, 0, 0)


# ---------------------------------------------------------------- 카드 제목 띠
def band(text, box, fill=W, mask="light", thresh=140, dilate=2, text_box=None, scale=0.85, bold=0.005, **kw):
    """카드 위쪽 제목 띠: box 안 글자 픽셀을 지우고 같은 자리에 한국어 제목."""
    sp = {"text": text, "font": "callig", "mask": mask, "thresh": thresh, "box": box, "fill": fill,
          "dilate": dilate, "bold": bold, "text_box": text_box or box, "scale": scale}
    sp.update(kw)
    return sp


# 크기별 제목 띠 영역 (x0, y0, x1, y1)
B128 = (11, 5, 117, 33)    # 128x170 어두운 띠
B139 = (12, 5, 127, 36)    # 139x177 어두운 띠
B140 = (30, 6, 126, 37)    # 140x173 재료 (왼쪽 속성 아이콘 제외)
BBOOK = (10, 5, 118, 35)   # 128x170 베이지 띠 (책 / 약초)


def dark128(t, box=B128, **kw):
    return band(t, box, **kw)


def dark139(t, box=B139, **kw):
    return band(t, box, **kw)


def mat(t, fill, **kw):
    return band(t, B140, fill=fill, mask="lighter", thresh=40, dilate=2, scale=0.9, **kw)


def book(t, **kw):
    return band(t, BBOOK, fill=(240, 236, 222), mask="lighter", thresh=22, dilate=2, scale=0.92, bold=0.02,
                stroke=(120, 105, 80), stroke_w=0.03, **kw)


CARDS = {
    # 공법서 (제목 띠만; 책 표지 그림 속 작은 글씨는 그림의 일부로 둠)
    "book710100": book("토납법"),
    "book710601": book("어검술"),
    "book710701": book("백약보"),
    "book710801": book("유심술"),
    "book710901": book("쉬골공"),
    "book711001": book("금강권"),
    "herb511601": book("지혈초"),
    # 깨달음 / 수위
    "exp5001": dark128("수위"),
    "insight30001": dark128("시금"),
    "insight30101": dark128("채목"),
    "insight30201": dark128("인수"),
    "insight30301": dark128("공화"),
    "insight30401": dark128("어토"),
    "insight30501": dark128("검의"),
    "insight30601": dark128("초식"),
    "insight30701": dark128("약리"),
    "insight5008": dark128("오도"),
    # 재료
    "materials": dark128("지심의 불", box=(4, 5, 125, 35), text_box=(9, 6, 119, 34)),
    "materials550201": mat("성휘정", (250, 247, 224)),
    "materials560101": mat("유잔목", (90, 245, 80)),
    "materials570201": mat("해파정", (125, 210, 255)),
    "materials580501": mat("날카로운 발톱", (250, 245, 235), text_box=(28, 6, 132, 37)),
    "materials590301": mat("자오암", (242, 241, 241)),
    # 단약
    "potion800501": dark128("독심환"),
    "potion800701": dark128("대력환"),
    # 인물 / 영수 / 괴뢰 / 법보
    "pet990401": dark139("영사"),
    "puppet620011": dark139("목제 괴뢰"),
    "role": dark139("무명씨"),
    "role_none": dark128("무명씨", box=(11, 5, 117, 35)),
    "role1100103": dark139("연로한 노인"),
    "role1100105": dark139("신비인"),
    "role1100107": dark139("상인"),
    "role800120": dark139("조자의"),
    "role_child01": dark139("아이"),
    "role_child02": dark139("아이"),
    "role_oldman": dark139("사부"),
    "role_unknown": dark128("신비인", box=(11, 5, 117, 35)),
    "spirit_beast_none": dark128("염사자", box=(11, 5, 117, 35)),
    "weapon100101": dark139("비홍검"),
    "weapon100701": dark139("열화검"),
    # 요괴 (붉은 띠)
    "enemy980101": band("산표범", B139, fill=(230, 30, 30), mask="lighter", thresh=25),
    "enemy981400": band("나무 요괴", B139, mask="lighter", thresh=40),
    "enemy_red981400": band("나무 요괴", B139, fill=(230, 30, 30), mask="lighter", thresh=25),
    "red_core": band("분고고의 내단", B139, fill=(235, 20, 20), mask="lighter", thresh=25),
    # 신식 (남색 띠)
    "soul": band("신식", (12, 5, 121, 36), fill=(131, 159, 220), mask="lighter", thresh=25),
    # 스토리 카드 (종이 띠 위 어두운 글자)
    "story01": band("나의 신분?", (10, 4, 118, 32), fill=(63, 46, 13), mask="darker", thresh=25),
    "story02": band("내 이름은?", (10, 4, 118, 32), fill=(63, 46, 13), mask="darker", thresh=25),
    "story03": band("진법 타파", (10, 4, 118, 32), fill=(63, 46, 13), mask="darker", thresh=25),
}


# ---------------------------------------------------------------- 글자 라벨
def outlined(t):  # 투명 배경 위 검은 글자 + 흰 테두리
    return {"text": t, "font": "callig", "mask": "alpha", "dilate": 1, "fill": (15, 15, 15),
            "stroke": (245, 240, 225), "stroke_w": 0.14, "scale": 1.0}


LABELS = {
    "new_text01": outlined("여기에 카드 넣기"),
    "new_text02": outlined("아이"),
    "new_text03": outlined("토납법"),
    "new_text04": outlined("탐색"),
    "new_text05": outlined("나의 물품"),
    "new_text06": outlined("나의 법보"),
    "new_text07": outlined("나의 수위"),
    "memory": {"text": "기억 일깨우기", "font": "callig", "mask": "lighter", "thresh": 25, "box": (30, 12, 170, 58),
               "fill": (150, 150, 150), "dilate": 2, "bold": 0.02, "text_box": (30, 14, 172, 56)},
    "memory_activation": {"text": "기억 일깨우기", "font": "callig", "mask": "light", "thresh": 170,
                          "box": (30, 12, 170, 58), "fill": (255, 250, 245), "dilate": 2, "bold": 0.03,
                          "text_box": (30, 14, 172, 56)},
    "start": {"text": "시작[F]", "font": "callig", "mask": "lighter", "thresh": 20, "box": (90, 40, 290, 95),
              "fill": (120, 120, 120), "dilate": 2, "bold": 0.02},
    "start_activation": {"text": "시작[F]", "font": "callig", "mask": "light", "thresh": 150,
                         "box": (90, 40, 290, 95), "fill": (255, 255, 255), "dilate": 2, "bold": 0.03},
    "story_text": {"text": "떠올릴 수 없음", "font": "callig", "mask": "light", "thresh": 120, "box": (20, 20, 402, 72),
                   "fill": (190, 170, 120), "dilate": 1, "bold": 0.02},
    "spell720102": {"text": "환화결", "font": "brush", "mask": "alpha", "layout": "v", "fill": (55, 52, 45, 170),
                    "bold": 0.03},
    "level": [
        {"mask": "light", "thresh": 140, "box": (33, 30, 95, 92), "dilate": 4},
        {"mask": "light", "thresh": 140, "box": (40, 85, 110, 128), "dilate": 4},
        {"mask": "dark", "thresh": 60, "box": (22, 62, 34, 88), "dilate": 2},
        {"text": "초기", "font": "callig", "mask": "dark", "thresh": 70, "box": (25, 125, 105, 160),
         "text_box": (32, 131, 98, 159), "fill": (25, 15, 5), "dilate": 2, "bold": 0.035},
        {"text": "연기", "font": "brush", "mask": "none", "layout": "diag", "text_box": (24, 30, 108, 124),
         "fill": (255, 255, 255), "stroke": BLACK, "stroke_w": 0.06},
    ],
}



# ---------------------------------------------------------------- 작은 글씨 화면(폼) 캡처
def _f(size, font="callig"):
    return ImageFont.truetype(FONTS[font], size)


def erase(img, box, mask="darker", thresh=30, dilate=3):
    return relabel(img, {"mask": mask, "thresh": thresh, "box": box, "dilate": dilate})


def wrap(text, font, width, indent=0):
    """단어 단위 줄바꿈 (단어가 너무 길면 글자 단위)."""
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))

    def tw(t):
        return d.textlength(t, font=font)

    lines, cur, first = [], "", True
    for word in text.split(" "):
        cand = (cur + " " + word) if cur else word
        if tw(cand) <= width - (indent if first else 0):
            cur = cand
            continue
        if cur:
            lines.append(cur)
            first, cur = False, ""
        lim = width - (indent if first else 0)
        while tw(word) > lim:  # 긴 단어 쪼개기
            k = len(word)
            while k > 1 and tw(word[:k]) > lim:
                k -= 1
            lines.append(word[:k])
            first, word, lim = False, word[k:], width
        cur = word
    if cur:
        lines.append(cur)
    return lines


def paragraphs(img, x0, y0, x1, paras, size, pitch, color, indent=0, font="callig", bold=0):
    """paras 를 x0..x1 폭에 맞춰 줄바꿈해 기준선 y0 부터 그린다. 문단 첫 줄은 indent 만큼 들여쓴다."""
    d = ImageDraw.Draw(img)
    f = _f(size, font)
    y = y0
    for p in paras:
        for i, line in enumerate(wrap(p, f, x1 - x0, indent)):
            d.text((x0 + (indent if i == 0 else 0), y), line, font=f, fill=color, anchor="ls",
                   stroke_width=bold, stroke_fill=color)
            y += pitch
    return img


def label(img, text, xy, size, color, anchor="ls", font="callig", bold=0):
    ImageDraw.Draw(img).text(xy, text, font=_f(size, font), fill=color, anchor=anchor,
                             stroke_width=bold, stroke_fill=color)
    return img


BODY = (80, 80, 71)


def paper_form(title, paras, found=None, found_color=(168, 161, 134)):
    """정실/산기슭/연암송 안내창 (1259x672): 제목 + 회색 상자 본문 (+ 탐색 시 발견 가능)"""
    def f(img):
        img = erase(img, (86, 36, 300, 80), "darker", 60)
        img = erase(img, (92, 108, 560, 290), "darker", 18)
        if found:
            img = erase(img, (74, 345, 240, 380), "darker", 15)
        label(img, title, (92, 71), 38, (0, 0, 0), bold=1)
        paragraphs(img, 98, 143, 535, paras, 27, 36, BODY, indent=52)
        if found:
            label(img, found, (78, 373), 26, found_color)
        return img
    return f


def explore_form(img):
    img = erase(img, (160, 122, 470, 172), "darker", 60)
    img = erase(img, (170, 195, 590, 340), "darker", 18)
    label(img, "무명 마을 방문", (168, 163), 40, (0, 0, 0), bold=1)
    paragraphs(img, 178, 231, 585, ["무명 마을을 찾아가 어떤 사람이나 임무를 만날 수 있는지 살펴보자."], 32, 48,
               BODY, indent=62)
    return img


def practice_form(img):
    img = erase(img, (145, 95, 360, 142), "darker", 60)
    img = erase(img, (155, 165, 590, 405), "darker", 18)
    label(img, "수련처", (151, 133), 40, (0, 4, 0), bold=1)
    paragraphs(img, 162, 200, 584, ["사부님이 마련해 준 수련처다. 이곳에서 토납법을 수련해야 한다.",
                                    "(\"아이 카드\"를 오른쪽 카드 슬롯으로 끌어다 놓기)"], 32, 47, (82, 82, 74),
               indent=62)
    return img


STORY_TXT = (143, 129, 93)


def story_form(img):
    img = erase(img, (140, 95, 610, 170), "darker", 18)
    img = erase(img, (215, 205, 585, 300), "darker", 18)
    img = erase(img, (140, 335, 610, 452), "darker", 18)
    img = erase(img, (270, 50, 470, 86), "lighter", 40)
    img = erase(img, (140, 180, 207, 197), "light", 140, 1)
    img = erase(img, (352, 742, 424, 870), "light", 120)
    label(img, "나의 신분?", (367, 68), 26, (255, 255, 255), anchor="mm", bold=1)
    label(img, "무명씨", (174, 189), 15, (235, 235, 235), anchor="mm")
    paragraphs(img, 148, 125, 605, ["주변을 다 살펴본 뒤, 나는 그늘진 곳을 찾아 앉았다."], 23, 38, STORY_TXT, indent=40)
    paragraphs(img, 235, 230, 590, ["(몸에 상처도 없고, 아픈 곳도 없다.) 그런데... 왜 내가 누구인지 떠오르지 않는 걸까?"],
               21, 30, (77, 77, 65), indent=40)
    paragraphs(img, 148, 364, 605, ["나는 머리를 세게 문지르며 내가 누구인지 필사적으로 떠올려 보았다."], 23, 38, STORY_TXT,
               indent=40)
    label(img, "--------회상--------", (377, 436), 23, STORY_TXT, anchor="ms")
    return relabel(img, {"text": "수선의\n증거", "font": "callig", "mask": "none", "text_box": (342, 740, 432, 870),
                         "fill": (205, 175, 115), "scale": 0.75})


def story_text01(img):
    img = relabel(img, {"mask": "alpha", "dilate": 1})
    paragraphs(img, 2, 26, 454, ["목옥 한구석에서 어린 내가 손을 들어 손가락을 위로 세우자, 앞에 놓인 목검이 천천히 "
                                 "허공으로 떠올랐다."], 25, 37, STORY_TXT, indent=40)
    return img


def tips_npc_demand(img):
    img = relabel(img, {"text": "교환", "font": "callig", "mask": "darker", "thresh": 60, "box": (150, 28, 255, 68),
                        "fill": (19, 14, 14), "dilate": 2, "bold": 0.03})
    return relabel(img, {"text": "지혈초", "font": "callig", "mask": "lighter", "thresh": 30, "box": (280, 68, 382, 98),
                         "fill": (243, 243, 235), "dilate": 2, "bold": 0.02})


BAG_TABS = ["재료", "영약", "도구", "내단", "심법", "중요"]


def bag_from(img):
    img = relabel(img, {"text": "보관 수량", "font": "callig", "mask": "lighter", "thresh": 30,
                        "box": (275, 100, 393, 134), "fill": (154, 139, 121), "dilate": 2,
                        "text_box": (296, 107, 391, 130)})
    for i, t in enumerate(BAG_TABS):
        y0 = 169 + i * 64  # 글자 윗줄
        active = i == 0
        img = relabel(img, {"text": t, "font": "callig", "mask": "darker" if active else "lighter",
                            "thresh": 30 if active else 12, "box": (132, y0 - 6, 228, y0 + 40), "dilate": 3,
                            "fill": (40, 35, 30) if active else (187, 171, 136), "bold": 0.01,
                            "text_box": (140, y0, 226, y0 + 34), "scale": 0.85})
    return img


def ink_text_erase(img, box, light=150, dark=90, close=25):
    """먹 번짐 속 흰 글자만 지운다: 어두운 먹 영역(구멍 메움) 안쪽의 밝은 픽셀 → 인페인트."""
    import cv2
    import numpy as np
    arr = np.array(img.convert("RGBA"))
    x0, y0, x1, y1 = box
    sub = arr[y0:y1, x0:x1]
    lum = sub[..., :3].astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)
    ink = (lum < dark).astype(np.uint8) * 255
    ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((close, close), np.uint8))
    cs, _ = cv2.findContours(ink, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    region = np.zeros_like(ink)
    cv2.drawContours(region, cs, -1, 255, -1)
    m = ((lum > light) & (region > 0)).astype(np.uint8) * 255
    m = cv2.dilate(m, np.ones((7, 7), np.uint8)) & region
    full = np.zeros(arr.shape[:2], np.uint8)
    full[y0:y1, x0:x1] = m
    arr[..., :3] = cv2.inpaint(np.ascontiguousarray(arr[..., :3]), full, 7, cv2.INPAINT_TELEA)
    return Image.fromarray(arr)


def game_from(img):
    for t, box, lay in [("옵션", (18, 125, 112, 210), "diag"), ("플레이\n방법", (132, 120, 250, 210), "h"),
                        ("도감", (255, 120, 350, 210), "diag")]:
        img = ink_text_erase(img, box)
        img = relabel(img, {"text": t, "font": "brush", "mask": "none", "fill": (250, 248, 240),
                            "stroke": BLACK, "stroke_w": 0.05, "layout": lay, "text_box": box, "scale": 0.9})
    img = relabel(img, {"text": "수명 90", "font": "callig", "mask": "light", "thresh": 150,
                        "box": (1672, 120, 1768, 155), "fill": (245, 245, 245), "dilate": 2,
                        "text_box": (1676, 124, 1762, 150)})
    img = relabel(img, {"text": "34세", "font": "callig", "mask": "dark", "thresh": 90, "box": (1680, 165, 1765, 205),
                        "fill": (33, 34, 31), "dilate": 2, "text_box": (1690, 171, 1758, 198)})
    return relabel(img, {"text": "5년째", "font": "callig", "mask": "dark", "thresh": 90, "box": (1362, 168, 1440, 197),
                         "fill": (40, 35, 25), "dilate": 1, "text_box": (1366, 172, 1436, 193)})


FORMS = {
    "dungeon_com_form": paper_form("정실", ["벼랑 위에 고요히 서 있는 정수실이다. 이곳이 노인의 거처일까?"]),
    "widget_com_form": paper_form("산기슭", [
        "이 산맥은 높지는 않지만 백 리에 걸쳐 이어져 있다. 산기슭에서는 큰 위험이 발견되지 않았고, "
        "이따금 쓸모 있는 물건도 찾을 수 있다.",
        "신식으로 탐색하거나 사람을 보낼 수 있다!"], found="탐색 시 발견 가능:"),
    "widget_fire_tree_form": paper_form("연암송", [
        "벼랑 위에 가로로 뻗은 소나무가 중력 때문에 아래로 자라지 않다니, 분명 뿌리에 품은 막대한 영기 때문일 것이다."],
        found="탐색 시 발견 가능:"),
    "explore_form": explore_form,
    "practice_form": practice_form,
    "story_form": story_form,
    "story_text01": story_text01,
    "tips_npc_demand": tips_npc_demand,
    "bag_from": bag_from,
    "game_from": game_from,
}

GUIDE = {**CARDS, **LABELS, **FORMS}
