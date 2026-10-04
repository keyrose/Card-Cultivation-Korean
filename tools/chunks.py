"""번역 작업 단위(청크) 생성.

python chunks.py 1   1단계: 짧은 항목(이름·용어·UI) → work/p1/NN.json
python chunks.py 2   2단계: 긴 항목(설명·대사)     → work/p2/NN.json (용어집 힌트 포함)

같은 중국어 원문은 한 번만 번역하고 merge.py 에서 같은 원문의 모든 키로 펼친다.
"""
import json
import sys

from common import ROOT, SOURCE_DIR, TRANS_DIR

SHORT = 10          # 1단계 기준 (중국어 글자 수)
P1_CHUNKS = 8
P2_CHARS = 7000     # 2단계 청크당 중국어 글자 수
WORK = ROOT / "work"


def unique_rows(pred):
    rows = json.loads((SOURCE_DIR / "textmapper.json").read_text(encoding="utf-8"))
    seen, out = set(), []
    for r in sorted(rows, key=lambda r: r["key"]):
        if r["zh"] and pred(r["zh"]) and r["zh"] not in seen:
            seen.add(r["zh"])
            out.append({"id": r["key"], "zh": r["zh"], "en": r["en"]})
    return out


def write(phase, chunks):
    d = WORK / f"p{phase}"
    d.mkdir(parents=True, exist_ok=True)
    for i, c in enumerate(chunks):
        (d / f"{i:02d}.json").write_text(json.dumps(c, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(chunks)}개 청크 → {d}")


def glossary():
    """1단계 번역 결과에서 zh→ko 용어집을 만든다."""
    src = {r["id"]: r["zh"] for r in unique_rows(lambda z: len(z) <= SHORT)}
    g = {}
    for p in sorted((TRANS_DIR / "raw").glob("p1_*.json")):
        for k, v in json.loads(p.read_text(encoding="utf-8")).items():
            z = src.get(k)
            if z and v and "<" not in z and "{" not in z and len(z) >= 2:
                g.setdefault(z, v)
    return g


def main(phase):
    if phase == 1:
        rows = unique_rows(lambda z: len(z) <= SHORT)
        n = -(-len(rows) // P1_CHUNKS)
        write(1, [rows[i:i + n] for i in range(0, len(rows), n)])
        return
    rows = unique_rows(lambda z: len(z) > SHORT)
    g = glossary()
    terms = sorted(g, key=len, reverse=True)
    chunks, cur, size = [], [], 0
    for r in rows:
        cur.append(r)
        size += len(r["zh"])
        if size >= P2_CHARS:
            chunks.append(cur)
            cur, size = [], 0
    if cur:
        chunks.append(cur)
    out = []
    for c in chunks:
        text = "\n".join(r["zh"] for r in c)
        hits = {}
        for t in terms:
            if t in text:
                hits[t] = g[t]
                text = text.replace(t, "\0")  # 긴 용어 우선, 부분 중복 방지
        out.append({"glossary": hits, "rows": c})
    write(2, out)


if __name__ == "__main__":
    main(int(sys.argv[1]))
