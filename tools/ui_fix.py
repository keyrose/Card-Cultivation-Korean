"""원본 UI 의 설정 누락 보정 (build.py 와 installer.py 가 함께 쓴다)."""

# 스프라이트 에셋이 비어 있어 <sprite=N> 이 글자 그대로 나오는 TMP 텍스트 → TextIcon 연결
# {번들: [(창 이름, 오브젝트 이름)]}
SPRITE_ASSET_FIXES = {
    "UI/UIForms.dat": [
        ("RoleShowGameEasyForm", "showDesc"),  # 캐릭터 정보 → 난이도 설명 (#2)
    ],
}
SPRITE_ASSET = "TextIcon"


def fix_sprite_assets(env, targets) -> int:
    """targets 의 TMP 텍스트 중 스프라이트 에셋이 비어 있는 것에 TextIcon 을 연결한다"""
    objs = {o.path_id: o for o in env.objects}
    icon = next((o.path_id for o in env.objects
                 if o.type.name == "MonoBehaviour" and o.peek_name() == SPRITE_ASSET), None)
    assert icon, f"{SPRITE_ASSET} 스프라이트 에셋을 찾지 못함"

    def root_name(go):
        t = objs[next(c["component"]["m_PathID"] for c in go["m_Component"]
                      if objs[c["component"]["m_PathID"]].type.name in ("Transform", "RectTransform"))]
        tt = t.read_typetree()
        while tt["m_Father"]["m_PathID"]:
            tt = objs[tt["m_Father"]["m_PathID"]].read_typetree()
        return objs[tt["m_GameObject"]["m_PathID"]].peek_name()

    names = {name for _, name in targets}
    n = 0
    for o in env.objects:
        if o.type.name != "GameObject" or o.peek_name() not in names:
            continue
        go = o.read_typetree()
        if (root_name(go), o.peek_name()) not in targets:
            continue
        for c in go["m_Component"]:
            co = objs[c["component"]["m_PathID"]]
            if co.type.name != "MonoBehaviour":
                continue
            t = co.read_typetree()
            if "m_spriteAsset" in t and not t["m_spriteAsset"]["m_PathID"]:
                t["m_spriteAsset"] = {"m_FileID": 0, "m_PathID": icon}
                co.save_typetree(t)
                n += 1
    return n
