"""translation/raw/*.json (대표 키 → 번역)을 검증하고 같은 원문의 모든 키로 펼쳐
translation/ko.json (키 → 번역) 을 만든다."""
import json
import re
from collections import Counter, defaultdict

from common import SOURCE_DIR, TRANS_DIR

TAG = re.compile(r"<[^>]+>|\{[^}]*\}")
LINE_INDENT = re.compile(r"</?line-indent(=[^>]*)?>")


def localize_indent(ko):
    """원문의 '첫 줄 두 글자 들여쓰기'(<line-indent=20%> 등)는 한국어 대사에서 띄어쓰기가 어긋난 것처럼
    보이므로 들여쓰기 태그를 모두 없앤다."""
    return LINE_INDENT.sub("", ko)


def check(zh, ko):
    """문제 목록을 돌려준다 (빈 목록이면 통과)."""
    errs = []
    if Counter(TAG.findall(zh)) != Counter(TAG.findall(ko)):
        errs.append(f"태그 불일치 {sorted(TAG.findall(zh))} ≠ {sorted(TAG.findall(ko))}")
    if "\n" in ko and "\n" not in zh:
        errs.append("줄바꿈 문자 추가됨")
    if re.search(r"[一-鿿]{3,}", TAG.sub("", ko)):
        errs.append("중국어 잔존")
    return errs


def main():
    rows = json.loads((SOURCE_DIR / "textmapper.json").read_text(encoding="utf-8"))
    zh_of = {r["key"]: r["zh"] for r in rows}
    keys_of = defaultdict(list)
    for r in rows:
        keys_of[r["zh"]].append(r["key"])

    fixes = json.loads((TRANS_DIR / "fixes.json").read_text(encoding="utf-8"))
    by_zh, problems = {}, []
    for p in sorted((TRANS_DIR / "raw").glob("*.json")):
        for k, v in json.loads(p.read_text(encoding="utf-8")).items():
            if k not in zh_of:
                problems.append(f"{p.name} {k}: 알 수 없는 키")
                continue
            for f in fixes:  # 청크 간 표기 통일
                if f["zh"] in zh_of[k]:
                    v = v.replace(f["from"], f["to"])
            errs = check(zh_of[k], v)
            if errs:
                problems.append(f"{p.name} {k}: {'; '.join(errs)}")
                if any("태그" in e for e in errs):
                    continue  # 태그가 깨진 번역은 적용하지 않음 (게임 표시 오류 방지)
            by_zh[zh_of[k]] = localize_indent(v)

    ko = {}
    for zh, v in by_zh.items():
        for k in keys_of[zh]:
            ko[k] = v
    (TRANS_DIR / "ko.json").write_text(
        json.dumps(dict(sorted(ko.items())), ensure_ascii=False, indent=1), encoding="utf-8")
    (TRANS_DIR / "problems.txt").write_text("\n".join(problems), encoding="utf-8")
    todo = sum(1 for r in rows if r["zh"] and r["key"] not in ko)
    print(f"번역 {len(ko)}/{len(rows)} 키 (미번역 {todo}), 문제 {len(problems)}건 → translation/problems.txt")


if __name__ == "__main__":
    main()
