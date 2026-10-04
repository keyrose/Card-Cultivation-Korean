"""이미지 한글화 사양. 키 = Texture2D 이름, 값 = imgedit.relabel spec (또는 spec 리스트).

LOCALIZATION 은 Localization/*.dat (언어별 이미지) — 간체 중국어 이미지를 기준으로 만든 한국어
이미지를 모든 언어 번들에 넣는다.
"""
W = (255, 255, 255)
CREAM = (233, 222, 186)
BLACK = (0, 0, 0)

# 먹 번짐 위 밝은 글자: 글자 픽셀(light)을 지우고 같은 색으로 다시 쓴다
def ink(text, **kw):
    return {"text": text, "font": "brush", "mask": "light", "thresh": 120, "dilate": 3,
            "stroke": BLACK, "stroke_w": 0.06, "bold": 0.03, **kw}


# 투명 배경 위 글자: 통째로 지우고 다시 쓴다
def plain(text, **kw):
    return {"text": text, "font": "brush", "mask": "alpha", "dilate": 1, "bold": 0.035, **kw}


BY_BUNDLE = {}

LOCALIZATION = {
    # 스토리 아이콘 (먹/색 번짐 + 큰 글자)
    "icon_story": ink("주", fill=CREAM, stroke=None, scale=1.1),
    "icon_story_branch": ink("서브", fill=CREAM, stroke=None, scale=1.25),
    "icon_story_clue": ink("단서", fill=CREAM, stroke=None, thresh=105, dilate=5, scale=0.85,
                           text_box=(20, 15, 185, 110)),
    "icon_summon": ink("소환", font="callig", fill=(248, 244, 225), stroke=None, thresh=215, bold=0.04,
                       text_box=(25, 30, 120, 120)),
    "learned_point": {"text": "수련 완료", "font": "brush", "mask": "sat", "thresh": 0.4,
                      "fill": (255, 205, 0), "stroke": BLACK, "stroke_w": 0.08, "scale": 1.05,
                      "dilate": 2, "grow": (10, 0)},
    # 상생/주/상극 표시
    "text_balance_grow": plain("생", fill=(60, 60, 50, 230), font="callig"),
    "text_balance_main": plain("주", fill=W, stroke=BLACK, stroke_w=0.08, font="callig"),
    "text_balance_restrain": plain("극", fill=(200, 50, 50), font="callig"),
    # 검은 상자 위 흰 글자
    "text_collect": ink("도감", stroke=None),
    "text_play": ink("안내", stroke=None),
    "text_task": ink("임무", stroke=None),
    "text_the_way": ink("선도", stroke=None),
    # 투명 배경 글자
    "text_core_golden": plain("금단", fill=(20, 20, 20)),
    "text_exp_leveup": plain("대성", fill=(245, 240, 210), stroke=(40, 30, 20), stroke_w=0.05),
    "text_gameover": plain("수명이 다하다", fill=(20, 20, 20), scale=1.0),
    "text_pause": plain("일시정지", fill=W, stroke=BLACK, stroke_w=0.08, grow=(0, 6)),
    # 먹 번짐 버튼
    "text_notice": ink("공지"),
    "text_options": ink("설정"),
    "text_patch": ink("패치"),
    # 수리
    "text_repair": {"text": "수리", "font": "brush", "mask": "light", "thresh": 140,
                    "box": (150, 230, 320, 426), "fill": (150, 150, 150), "dilate": 3},
    "text_repair_tips": {"text": "수리", "font": "brush", "mask": "light", "thresh": 110,
                         "box": (25, 30, 82, 84), "fill": (150, 150, 150), "dilate": 2},
    # 엔딩 부제
    "text_story_end01": plain("우화등선", fill=W),
    "text_story_end02": plain("스스로 짊어진 겁난", fill=W),
    "text_story_end03": plain("다시 범인으로", fill=W),
    "text_story_end04": plain("잊혀진 마음의 상처", fill=W),
    "text_story_end05": plain("반쯤 막힌 대도", fill=W),
    "text_story_end06": plain("생의 끝", fill=W),
    # 지도 (위쪽 핀 아이콘은 유지)
    "txt_minimap": {"text": "지도", "font": "brush", "mask": "light", "thresh": 150,
                    "box": (0, 60, 52, 223), "layout": "v", "fill": W, "dilate": 2},
    # 도(道) 이름: 흐릿한 큰 글자 두 자
    **{f"txt_the_way0{i}": plain(t, layout="v", fill=(90, 85, 70, 110), scale=0.95)
       for i, t in enumerate(["기초", "무도", "술도", "단도", "기도", "수도", "마도"])},
    # 타이머 버튼
    **{f"txt_timer0{i + 1}": ink(t) for i, t in enumerate(["수련", "연제", "배양", "조사", "회복"])},
    # 메뉴 제목
    "txt_title_free": plain("자유 모드", fill=(100, 95, 80, 140)),
    "txt_title_load": plain("불러오기", fill=(100, 95, 80, 140)),
    "txt_title_options": plain("설정", fill=(100, 95, 80, 140)),
    "txt_title_save": plain("게임 저장", fill=(100, 95, 80, 140)),
    "txt_title_story": plain("스토리 모드", fill=(100, 95, 80, 140)),
    "txt_title_the_way": plain("성선의 길", fill=(100, 95, 80, 140)),
    "txt_the_way": plain("성선의 길", fill=(100, 95, 80, 140)),
    # 영어 번들에만 있는 것
    "text_adverse": plain("역경", layout="v", fill=(180, 30, 30), stroke=BLACK, stroke_w=0.05),
}


# ---- TMP 스프라이트 에셋 TextIcon (본문 <sprite=N> 아이콘) : 글리프 번호 → spec
QUALITY = {"인": (255, 255, 255), "지": (150, 225, 90), "천": (110, 185, 245),
           "선": (205, 120, 235), "신": (245, 215, 115), "절": (235, 25, 25)}


def round_icon(t):  # 먹 번짐 위 한 글자
    return {"text": t, "font": "callig", "mask": "light", "thresh": 60, "inset": 22,
            "fill": QUALITY[t], "dilate": 3, "bold": 0.06, "text_inset": 34}


def wide_icon(t):  # 'X품' 품질 표시
    return {"text": t + "품", "font": "callig", "mask": "alpha", "fill": QUALITY[t],
            "stroke": BLACK, "stroke_w": 0.13, "dilate": 0, "scale": 0.97}


def coin(t, fill):  # 동전 모양 원 안 한 글자
    return {"text": t, "font": "callig", "mask": "sat", "thresh": 0.25, "inset": 22,
            "fill": fill, "dilate": 3, "bold": 0.05, "scale": 0.9}


TEXTICON = {
    8: round_icon("인"), 9: round_icon("지"), 10: round_icon("천"), 11: round_icon("선"),
    12: round_icon("신"), 23: round_icon("절"),
    13: wide_icon("인"), 14: wide_icon("지"), 15: wide_icon("천"), 16: wide_icon("선"),
    17: wide_icon("신"), 25: wide_icon("절"),
    26: coin("음", (215, 190, 140)), 27: coin("양", (205, 180, 130)),
    42: coin("공", (225, 190, 120)), 43: coin("시", (215, 165, 100)),
}


# ---- 카드 배지 / 아이콘 (UI/UISprites/Card.dat, ArtData/Card.dat 공통)
def badge(t, fill=W, **kw):  # 먹 번짐 위 흰 글자 (경지 배지 등)
    sp = {"text": t, "font": "brush", "mask": "light", "thresh": 110, "inset": 0.12,
          "fill": fill, "dilate": 2, "bold": 0.03, "layout": "diag" if len(t) == 2 else "h",
          "text_inset": 0.14}
    sp.update(kw)
    return sp


def small_icon(t, fill=W, **kw):  # 먹 번짐 위 작은 한 글자
    sp = {"text": t, "font": "callig", "mask": "light", "thresh": 90, "inset": 0.15,
          "fill": fill, "dilate": 2, "bold": 0.02, "text_inset": 0.24}
    sp.update(kw)
    return sp


def coin2(t, fill, inset=0.27, text_inset=0.27, light_bg=False):
    # 어두운 동전: 밝은 글자 / 밝은 동전(양): 배경보다 어두운 글자
    m = {"mask": "dark", "thresh": 215} if light_bg else {"mask": "light", "thresh": 100}
    return coin(t, fill) | {"inset": inset, "text_inset": text_inset, "bold": 0.02} | m


REALM = {
    "type_realm_BodyIntegration": "합체", "type_realm_CoreFormation": "결단",
    "type_realm_CoreFormationEarly": "결단", "type_realm_FoundationEstablishment": "축기",
    "type_realm_FoundationEstablishmentEarly": "축기", "type_realm_FoundationEstablishmentMiddle": "축기",
    "type_realm_GreatAscension": "대승", "type_realm_Human": "범인", "type_realm_NascentSoul": "원영",
    "type_realm_NascentSoulEarly": "원영", "type_realm_QiRefing": "연기", "type_realm_QiRefingEarly": "연기",
    "type_realm_QiRefingMiddle": "연기", "type_realm_Special": "미지",
    "type_realm_SpiritTransformation": "화신", "type_realm_VoidRefining": "연허",
}
REALM_SPECS = {k: badge(v) for k, v in REALM.items()}

UI_CARD = {
    **REALM_SPECS,
    "quality_Blue": small_icon("천", QUALITY["천"], thresh=60),
    "quality_Gold": small_icon("신", QUALITY["신"], thresh=60),
    "quality_Green": small_icon("지", QUALITY["지"], thresh=60),
    "quality_Purple": small_icon("선", QUALITY["선"], thresh=60),
    "quality_Red": small_icon("절", QUALITY["절"], mask="sat", thresh=0.5),
    "quality_White": small_icon("인"),
    "type_Evidence": small_icon("증"), "type_Guide": small_icon("인"),
    "type_Inner": small_icon("마"),
    "type_InnerMonster": small_icon("마", (220, 30, 30), mask="sat", thresh=0.5),
    "type_Spell": small_icon("결"), "type_SummonCard": small_icon("소"),
    "type_wuxing_All": small_icon("전", W, mask="light", thresh=150, inset=0.2),
    "type_wuxing_Space": coin2("공", (225, 190, 120)),
    "type_wuxing_Time": coin2("시", (215, 165, 100)),
    "type_wuxing_Yang": coin2("양", (205, 180, 130), 0.34, 0.3, light_bg=True),
    "type_wuxing_Yin": coin2("음", (215, 190, 140), 0.34, 0.3),
}

COIN_BOX = (24, 30, 74, 80)  # 먹 방울 위쪽 동전 영역

ART_CARD = {
    **REALM_SPECS,
    "alert": {"text": "헉!", "font": "brush", "mask": "alpha", "fill": (215, 25, 25), "bold": 0.04},
    "attribute_wuxing_Yang": coin2("양", (205, 180, 130), 0, 0.12) | {"box": COIN_BOX, "mask": "disc",
                                                                      "fill": (200, 175, 125), "bg": (238, 232, 220), "dilate": 0},
    "attribute_wuxing_Yin": coin2("음", (215, 190, 140), 0, 0.12) | {"box": COIN_BOX, "mask": "disc", "bg": (22, 20, 17),
                                                                   "dilate": 0},
    "card_role_free_soul": {"text": "원신", "font": "callig", "mask": "light", "thresh": 120,
                         "box": (0, 0, 9999, 0.2), "fill": (150, 170, 200), "dilate": 2},
    "card_role_soul": {"text": "원신", "font": "callig", "mask": "light", "thresh": 120,
                       "box": (0, 0, 9999, 0.2), "fill": (150, 170, 200), "dilate": 2},
    "attribute_wuxing_All": small_icon("전", W, thresh=150, inset=0.1, box=(0, 0, 9999, 0.5),
                                       text_inset=0.28),
    "favorite_point": {"text": "본명", "font": "brush", "mask": "light", "thresh": 70, "layout": "v",
                       "fill": (230, 60, 60), "stroke": BLACK, "stroke_w": 0.06, "dilate": 2},
}

UI_COMMON = {
    "spell": small_icon("결", mask="light", thresh=150, inset=0.1, fill=(250, 240, 230)),
    "unknown_talent": {"text": "미지", "font": "callig", "mask": "dark", "thresh": 42,
                       "box": (0.25, 0.3, 0.75, 0.8), "layout": "v", "fill": (35, 25, 15), "dilate": 1,
                       "bold": 0.02, "scale": 0.55},
}

UI_TIMER = {
    "card_bag": {"text": "행낭", "font": "callig", "mask": "light", "thresh": 150,
                 "box": (0, 0, 9999, 0.2), "fill": (235, 235, 235), "dilate": 2, "bold": 0.03},
    **{f"timer_seal{n}": {"text": t, "font": "callig", "mask": "alpha", "fill": (220, 115, 45),
                          "glow": (8, (255, 140, 40, 170)), "scale": 0.85}
       for n, t in [(10, "봉"), (11, "해"), (12, "금"), (13, "제")]},
}

EFFECT = {
    "230": {"text": "무", "font": "callig", "mask": "alpha", "fill": (255, 250, 235, 230), "bold": 0.04, "scale": 0.75,
            "glow": (10, (255, 235, 180, 200))},
    "310": {"text": "대\n도", "font": "brush", "mask": "alpha", "fill": BLACK, "stroke": W, "stroke_w": 0.07},
    "311": {"text": "칠정\n육욕", "font": "brush", "mask": "alpha", "fill": (220, 25, 25), "bold": 0.03},
    "5000": {"text": "수사", "font": "brush", "mask": "alpha", "layout": "diag",
             "fill": W, "stroke": BLACK, "stroke_w": 0.09, "dilate": 0},
    "64101": {"text": "환화결", "font": "callig", "mask": "alpha", "layout": "v", "fill": (100, 95, 85, 150)},
    "80001": {"text": "어검비행", "font": "callig", "mask": "light", "thresh": 120, "inset": 0.2,
              "layout": "v", "fill": (200, 180, 140), "dilate": 2},
    "available": {"text": "가용", "font": "callig", "mask": "alpha", "layout": "v", "fill": (30, 30, 30),
                  "bold": 0.03},
    "entrance": {"text": "진입", "font": "brush", "mask": "alpha", "layout": "v", "fill": W,
                 "stroke": BLACK, "stroke_w": 0.06},
    "forbiden": {"text": "봉", "font": "brush", "mask": "alpha", "fill": (170, 10, 10),
                 "stroke": BLACK, "stroke_w": 0.04},
    "lack": {"text": "영기부족", "font": "callig", "mask": "alpha", "layout": "v", "fill": (30, 30, 30),
             "bold": 0.03},
    "level_up_tips04": {"text": "클릭해 돌파", "font": "brush", "mask": "alpha", "fill": (30, 25, 20),
                        "stroke": W, "stroke_w": 0.06},
    "level_up_tips05": {"text": "도겁", "font": "brush", "mask": "alpha", "fill": (30, 25, 20),
                        "stroke": W, "stroke_w": 0.06},
    "pat": {"text": "팍!", "font": "brush", "mask": "dark", "thresh": 90, "inset": 0.18,
            "fill": BLACK, "dilate": 3, "bold": 0.05},
    "summon": {"text": "환요결", "font": "callig", "mask": "alpha", "layout": "v", "fill": (100, 95, 85, 150)},
    "text_exp_leveup": {"text": "대성", "font": "brush", "mask": "alpha", "fill": (245, 240, 210),
                        "stroke": (40, 30, 20), "stroke_w": 0.05},
    # 封结界印: 2x2 칸에 한 글자씩
    "text": [{"text": t, "font": "callig", "mask": "alpha", "box": b, "fill": (20, 20, 20), "bold": 0.03,
              "text_inset": 0.1}
             for t, b in [("봉", (0.0, 0.0, 0.5, 0.5)), ("결", (0.5, 0.0, 1.0, 0.5)),
                          ("계", (0.0, 0.5, 0.5, 1.0)), ("인", (0.5, 0.5, 1.0, 1.0))]],
}

EFFECT["card_role_soul"] = ART_CARD["card_role_soul"]

BY_BUNDLE.update({
    "UI/UISprites/Card.dat": UI_CARD,
    "ArtData/Card.dat": ART_CARD,
    "UI/UISprites/Common.dat": UI_COMMON,
    "UI/UISprites/Timer.dat": UI_TIMER,
    "Effect.dat": EFFECT,
})


# ---- 튜토리얼 이미지(별도 모듈): 값은 spec / spec 리스트 / 함수(img -> img)
try:
    from image_specs_tutorial import TUTORIAL
    LOCALIZATION.update(TUTORIAL)
except Exception:  # 작업 중인 모듈은 건너뜀
    pass
try:
    from image_specs_guide import GUIDE
    BY_BUNDLE["UI/UISprites/Guide.dat"] = GUIDE
except Exception:  # 작업 중인 모듈은 건너뜀
    pass

# 아이템/스킬/무기 아이콘: UI 와 카드 그림 번들에 같은 이름·같은 그림이 있어 둘 다 적용
for _mod, _var, _bundles in [
    ("image_specs_items", "ITEMS", ["UI/UISprites/Items.dat", "ArtData/Items.dat"]),
    ("image_specs_skills", "SKILLS", ["UI/UISprites/Skill.dat", "ArtData/Skill.dat"]),
    ("image_specs_skills", "WEAPONS", ["UI/UISprites/Weapon.dat", "ArtData/Weapon.dat"]),
]:
    try:
        _specs = getattr(__import__(_mod), _var)
        for _b in _bundles:
            BY_BUNDLE.setdefault(_b, {}).update(_specs)
    except Exception:  # 작업 중인 모듈은 건너뜀
        pass


def apply(img, sp):
    """spec / spec 리스트 / 함수 를 이미지에 적용"""
    from imgedit import relabel
    if callable(sp):
        return sp(img)
    for s in (sp if isinstance(sp, list) else [sp]):
        img = relabel(img, s)
    return img


# ---- 타이틀 로고: 영어판 로고(카드 부채 + 두 줄 붓글씨 + 붉은 낙관) 구성을 따른다
#   Card / Cultivation / Biography → 카드 / 수선 / 전
LOGO_SPECS = [
    {"text": "카드", "font": "brush", "mask": "none", "text_box": (330, 92, 740, 238),
     "fill": (22, 22, 22), "bold": 0.012, "stretch_y": 1.05},
    {"text": "수선", "font": "brush", "mask": "none", "text_box": (250, 218, 820, 372),
     "fill": (22, 22, 22), "bold": 0.012, "stretch_y": 1.05},
    # 붉은 낙관 속 흰 글자 Biography → 전
    {"text": "전", "font": "brush", "mask": "light", "thresh": 150, "box": (805, 55, 985, 120),
     "fill": (248, 244, 236), "dilate": 2, "scale": 0.95},
]
_EN_LOGO = {}


def _english(name):
    """영어 번들의 같은 이름 이미지 (빌드는 간체 이미지를 넘겨주므로 여기서 직접 읽는다)"""
    if name not in _EN_LOGO:
        import UnityPy
        from common import original, read_dat
        env = UnityPy.load(read_dat(original("StreamingAssets/Localization/English.dat"))[0])
        for o in env.objects:
            if o.type.name == "Texture2D" and o.peek_name() in ("logo", "play01"):
                _EN_LOGO[o.peek_name()] = o.read().image.convert("RGBA")
    return _EN_LOGO[name].copy()


def _clean_logo():
    """영어 로고에서 글자를 지운 배경: 같은 배경 그림을 쓰는 중국어 로고의 픽셀로 메우고,
    두 로고 모두 글자가 있던 곳만 인페인트한다"""
    import cv2
    import numpy as np
    from PIL import Image
    import UnityPy
    from common import original, read_dat
    from imgedit import _mask
    env = UnityPy.load(read_dat(original("StreamingAssets/Localization/ChineseSimplified.dat"))[0])
    zh = next(o.read().image.convert("RGBA") for o in env.objects
              if o.type.name == "Texture2D" and o.peek_name() == "logo")
    en = np.array(_english("logo"))
    zh = np.array(zh)
    k = np.ones((9, 9), np.uint8)
    m_en = cv2.dilate(_mask(en, "ink", 150).astype(np.uint8), k) > 0
    m_zh = cv2.dilate((_mask(zh, "ink", 150) | _mask(zh, "dark", 100)).astype(np.uint8), k) > 0
    m_zh[:, 900:] = False  # 중국어 로고의 傳 낙관 자리는 영어 배경을 그대로 쓴다
    m_en[40:130, 800:990] = False  # 영어 낙관(Biography)은 아래 spec 에서 따로 처리
    out = en.copy()
    take = m_en & ~m_zh
    out[take] = zh[take]
    both = (m_en & m_zh).astype(np.uint8) * 255
    out[..., :3] = cv2.inpaint(np.ascontiguousarray(out[..., :3]), both, 5, cv2.INPAINT_TELEA)
    out[..., 3] = cv2.inpaint(np.ascontiguousarray(out[..., 3]), both, 5, cv2.INPAINT_TELEA)
    # 마지막 정리: 남은 먹 점 (낙관 제외)
    rest = _mask(out, "ink", 140)
    rest[30:140, 790:1000] = False
    rest = cv2.dilate(rest.astype(np.uint8) * 255, np.ones((7, 7), np.uint8))
    if rest.any():
        out[..., :3] = cv2.inpaint(np.ascontiguousarray(out[..., :3]), rest, 5, cv2.INPAINT_TELEA)
    return Image.fromarray(out)


def _korean_logo():
    if "ko" not in _EN_LOGO:
        _EN_LOGO["ko"] = apply(_clean_logo(), LOGO_SPECS)
    return _EN_LOGO["ko"].copy()


def logo(img):
    return _korean_logo()


def logo_small(img):
    """시작 화면 작은 로고(play01): 영어판 그림에서 로고 부분만 한국어 로고로 교체"""
    from PIL import Image
    base = _english("play01")
    big = _english("logo")
    a = base.getchannel("A").point(lambda v: 255 if v > 20 else 0)
    bb = a.getbbox()
    # play01 은 logo 를 축소해 넣은 것: 같은 비율 영역에 한국어 로고를 다시 넣는다
    w = bb[2] - bb[0]
    h = round(w * big.height / big.width)
    y0 = bb[1] + ((bb[3] - bb[1]) - h) // 2
    ko = _korean_logo().resize((w, h), Image.LANCZOS)
    out = base.copy()
    out.paste(Image.new("RGBA", (w, h), (0, 0, 0, 0)), (bb[0], y0))
    out.alpha_composite(ko, (bb[0], y0))
    return out


LOCALIZATION["logo"] = logo
LOCALIZATION["play01"] = logo_small
