"""게임에서 번역 원문(lang_tbtextmapper)을 추출해 source/textmapper.json 으로 저장한다."""
import json

import UnityPy

from common import SOURCE_DIR, original, read_dat
from luban import Reader


def load_luban_env():
    data, _ = read_dat(original("StreamingAssets/LubanTables.dat"))
    return UnityPy.load(data)


def script_bytes(ta) -> bytes:
    s = ta.m_Script
    return s.encode("utf-8", "surrogateescape") if isinstance(s, str) else bytes(s)


def parse_textmapper(raw: bytes) -> list[dict]:
    r = Reader(raw)
    rows = []
    for _ in range(r.uint()):
        key, zh, zht, en, ru = (r.str() for _ in range(5))
        rows.append({"key": key, "zh": zh, "zht": zht, "en": en, "ru": ru})
    assert r.eof()
    return rows


def main():
    env = load_luban_env()
    for o in env.objects:
        if o.type.name == "TextAsset" and o.peek_name() == "lang_tbtextmapper":
            rows = parse_textmapper(script_bytes(o.read()))
            break
    SOURCE_DIR.mkdir(exist_ok=True)
    with open(SOURCE_DIR / "textmapper.json", "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    print(f"{len(rows)}개 항목 추출 → {SOURCE_DIR / 'textmapper.json'}")


if __name__ == "__main__":
    main()
