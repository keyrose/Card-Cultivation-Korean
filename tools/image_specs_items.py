"""ArtData/Items.dat, UI/UISprites/Items.dat (아이템 그림) 한글화 사양.

ITEMS = {텍스처 이름: spec | spec 리스트 | 함수(img -> img)}
두 번들에 같은 이름·같은 그림으로 들어 있다(일부는 UI 쪽만 종이 액자 안에 그려져 있어 함수로 구분).
이름은 게임 내 한국어 이름(translation/ko.json)과 맞춘다. 공법서 표지(5xxxx)는 CardBook_xxxx.
"""
import math

import cv2
import numpy as np
from PIL import Image

from imgedit import fit_text, relabel

BLACK = (0, 0, 0)
W = (255, 255, 255)


# ---------------------------------------------------------------- 기울어진 표지 제목 띠
def _lum(a):
    return a[..., :3].astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)


def _rect_mask(shape, c, ang, L, Wd):
    """중심 c, 세로축이 ang(도, 시계 방향으로 기울어짐) 인 L x Wd 직사각형 마스크"""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    t = math.radians(ang)
    ax, ay = math.sin(t), math.cos(t)          # 글자 진행 방향(아래쪽)
    px, py = math.cos(t), -math.sin(t)         # 가로 방향
    dx, dy = xx - c[0], yy - c[1]
    u = dx * ax + dy * ay
    v = dx * px + dy * py
    return (np.abs(u) <= L / 2) & (np.abs(v) <= Wd / 2)


def _strokes(arr, box, mode, thresh, k, tol, extra, poly=None, lab=None):
    """box 안에서 글자 획 마스크, 획 세기, (글자 없는) 배경 추정 이미지를 구한다."""
    H, Wi = arr.shape[:2]
    x0, y0, x1, y1 = box
    region = np.zeros((H, Wi), bool)
    region[max(0, y0):y1, max(0, x0):x1] = True
    if poly is not None:
        region &= poly
    lum = _lum(arr)
    rgb0 = np.ascontiguousarray(arr[..., :3])
    bgimg = op = None
    if mode in ("darker", "lighter"):
        # 닫힘(어두운 획 제거)/열림(밝은 획 제거) 으로 글자 없는 띠를 추정
        op = cv2.MORPH_CLOSE if mode == "darker" else cv2.MORPH_OPEN
        bgimg = cv2.morphologyEx(rgb0, op, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
        diff = (_lum(bgimg) - lum) if mode == "darker" else (lum - _lum(bgimg))
    elif mode == "dark":
        diff = thresh - lum
    elif mode == "light":
        diff = lum - thresh
    else:
        raise ValueError(mode)
    m = diff > (thresh if mode in ("darker", "lighter") else 0)
    m &= region & (arr[..., 3] > 40)
    if extra is not None:
        m &= extra(arr)
    if tol and bgimg is not None and m.sum() > 5:
        # 띠 색(상자 가운데의 글자 없는 배경색)과 비슷한 곳의 획만: 띠 테두리·표지 무늬 제외
        if lab is None:
            cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
            lab = np.median(bgimg[cy - 3:cy + 4, cx - 3:cx + 4].reshape(-1, 3).astype(np.float32), axis=0)
        m &= np.linalg.norm(bgimg.astype(np.float32) - np.array(lab[:3], np.float32), axis=-1) < tol
    return m, diff, bgimg, op


def _geom(m, layout, ang=None):
    """획 마스크 → (중심, 진행축 각도(도), 길이, 폭). 축에서 먼 점은 버리며 다시 맞춘다."""
    ys, xs = np.nonzero(m)
    P = np.stack([xs, ys], 1).astype(np.float32)
    keep = np.ones(len(P), bool)
    for it in range(3):
        Q = P[keep]
        mu = Q.mean(0)
        if ang is None and len(Q) >= 10:
            ev, evec = np.linalg.eigh(np.cov((Q - mu).T))
            d = evec[:, 1]
            if layout == "v" and d[1] < 0 or layout != "v" and d[0] < 0:
                d = -d
            a = math.degrees(math.atan2(d[0], d[1]))
        else:
            a = ang if ang is not None else (0.0 if layout == "v" else 90.0)
        t = math.radians(a)
        n = np.array([math.cos(t), -math.sin(t)], np.float32)
        v = (P - mu) @ n
        med = np.median(v[keep])
        spread = np.percentile(np.abs(v[keep] - med), 90)
        keep = np.abs(v - med) <= spread * 1.3 + 1
    t = math.radians(a)
    d = np.array([math.sin(t), math.cos(t)], np.float32)
    n = np.array([math.cos(t), -math.sin(t)], np.float32)
    Q = P[keep]
    mu = Q.mean(0)
    u, v = (Q - mu) @ d, (Q - mu) @ n
    u0, u1 = np.percentile(u, [0.5, 99.5])
    v0, v1 = np.percentile(v, [1.5, 98.5])
    c = mu + d * (u0 + u1) / 2 + n * (v0 + v1) / 2
    return (float(c[0]), float(c[1])), a, float(u1 - u0), float(v1 - v0)


def title(text, box, mode="darker", thresh=40, fill=None, font="callig", bold=0.03, stroke=None,
          stroke_w=0.0, dilate=1, k=11, tol=70, scale=1.0, glow=None, layout="v", ang=None,
          extra=None, dx=0, dy=0, grow=1.0, poly=None, lab=None, extend=2):
    """표지 제목(기울어져 있어도 됨)을 지우고 같은 자리·같은 기울기로 한국어를 쓴다.

    box: 제목 글자를 대략 감싸는 영역 (x0, y0, x1, y1). 글자 획을 찾아 주성분 방향으로 기울기·크기를 잰다.
    mode: darker/lighter (주변보다 어둡거나 밝은 획), dark/light (절대 밝기)
    ang: 기울기 직접 지정(도, 세로쓰기 기준 아래쪽이 오른쪽으로 기울면 +)
    """
    def f(img):
        arr = np.array(img.convert("RGBA"))
        pm = poly(arr.shape[:2]) if callable(poly) else None
        m, diff, bgimg, op = _strokes(arr, box, mode, thresh, k, tol, extra, pm, lab)
        _lab = None
        if bgimg is not None and lab is None:
            cx, cy = (box[0] + box[2]) // 2, (box[1] + box[3]) // 2
            _lab = np.median(bgimg[cy - 3:cy + 4, cx - 3:cx + 4].reshape(-1, 3).astype(np.float32), axis=0)
        if m.sum() < 5:
            return img
        c, a_, L, w = _geom(m, layout, ang if (ang is not None or len(text or "xx") > 1) else 0.0)
        for _ in range(extend):  # 축을 따라 넓혀 빠진 글자까지 다시 찾는다
            H_, W_ = arr.shape[:2]
            rm = _rect_mask((H_, W_), c, a_, L + 1.3 * w, w * 1.15)
            if pm is not None:
                rm &= pm
            m2, diff, bgimg, op = _strokes(arr, (0, 0, W_, H_), mode, thresh, k, tol, extra, rm,
                                           lab if lab is not None else _lab)
            if m2.sum() < 5:
                break
            g2 = _geom(m2, layout, ang if (ang is not None or len(text or "xx") > 1) else 0.0)
            if g2[2] > L * 1.6 or g2[3] > w * 1.3:  # 띠 밖으로 번지면 버림
                break
            m = m2
            c, a_, L, w = g2
        if ang is None and len(text or "xx") == 1:
            a_ = 0.0 if layout == "v" else 90.0
        col = fill
        if col is None:
            dv = diff[m]
            col = tuple(int(v) for v in np.median(arr[m][dv >= np.median(dv)][:, :3], axis=0))
        rgb0 = np.ascontiguousarray(arr[..., :3])
        mk = m.astype(np.uint8) * 255
        if dilate:
            mk = cv2.dilate(mk, np.ones((2 * dilate + 1, 2 * dilate + 1), np.uint8))
        if bgimg is not None:
            kk = k + 2 * dilate
            fillimg = cv2.morphologyEx(rgb0, op, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kk, kk)))
            fillimg = cv2.GaussianBlur(fillimg, (3, 3), 0)
            al = cv2.GaussianBlur(mk, (3, 3), 0).astype(np.float32)[..., None] / 255
            arr[..., :3] = (rgb0 * (1 - al) + fillimg * al).astype(np.uint8)
        else:
            arr[..., :3] = cv2.inpaint(rgb0, mk, 4, cv2.INPAINT_TELEA)
        out = Image.fromarray(arr)
        if not text:
            return out
        col4 = tuple(col)[:3] + (255,)
        sw_ratio, st = stroke_w, stroke
        if bold and stroke is None:
            st, sw_ratio = col4, bold
        if st is not None:
            st = tuple(st)[:3] + (255,)
        L, w = L * grow, w * grow
        if layout == "v":
            t = fit_text(text, font, w * scale, L * scale, "v", col4, st, sw_ratio)
            rot = a_
        else:
            t = fit_text(text, font, L * scale, w * scale, "h", col4, st, sw_ratio)
            rot = a_ - 90
        if abs(rot) > 0.5:  # 4배로 키워 회전 후 다시 줄인다
            big = t.resize((t.width * 4, t.height * 4), Image.LANCZOS).rotate(rot, Image.BICUBIC, expand=True)
            t = big.resize((max(1, big.width // 4), max(1, big.height // 4)), Image.LANCZOS)
        px_, py_ = int(round(c[0] + dx - t.width / 2)), int(round(c[1] + dy - t.height / 2))
        if glow:
            from PIL import ImageFilter
            r, gc = glow
            g = Image.new("RGBA", (t.width + 4 * r, t.height + 4 * r), (0, 0, 0, 0))
            g.alpha_composite(t, (2 * r, 2 * r))
            a = g.getchannel("A").filter(ImageFilter.GaussianBlur(r))
            gl = Image.new("RGBA", g.size, tuple(gc[:3]) + (255,))
            gl.putalpha(a.point(lambda v: v * gc[3] // 255))
            out.alpha_composite(gl, (px_ - 2 * r, py_ - 2 * r))
        out.alpha_composite(t, (px_, py_))
        return out
    return f


_DEBUG = [False]


def _smooth(arr, mode, k):
    rgb = np.ascontiguousarray(arr[..., :3])
    if mode == "median":
        return cv2.GaussianBlur(cv2.medianBlur(rgb, k if k % 2 else k + 1), (3, 3), 0)
    op = cv2.MORPH_CLOSE if mode == "darker" else cv2.MORPH_OPEN
    return cv2.GaussianBlur(cv2.morphologyEx(rgb, op, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))), (5, 5), 0)


def _fill(sm, alpha, pt, tol, close, clip=None):
    H, W = sm.shape[:2]
    mask = np.zeros((H + 2, W + 2), np.uint8)
    if clip is not None:  # clip 밖으로는 번지지 않게
        mask[:] = 1
        cx0, cy0, cx1, cy1 = clip
        mask[cy0 + 1:cy1 + 1, cx0 + 1:cx1 + 1] = 0
    cv2.floodFill(sm.copy(), mask, pt, (0, 0, 0), (tol,) * 3, (tol,) * 3, 4 | cv2.FLOODFILL_MASK_ONLY | (255 << 8))
    comp = (mask[1:-1, 1:-1] == 255).astype(np.uint8) & alpha
    if close:
        comp = cv2.morphologyEx(comp, cv2.MORPH_CLOSE, np.ones((close, close), np.uint8))
    cs, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cs:
        return None
    cnt = max(cs, key=cv2.contourArea)
    full = np.zeros_like(comp)
    cv2.drawContours(full, [cnt], -1, 1, -1)
    return full.astype(bool), cv2.minAreaRect(cnt), cv2.contourArea(cnt)


def find_label(arr, seed, tol=None, k=11, close=3, mode=None, clip=None, aspect=(1.6, 9), wlim=(9, 70),
               radius=24):
    """seed 근처의 띠(제목 표지)를 찾는다 → (띠 마스크, minAreaRect)
    seed 주변 여러 점 x 여러 허용 색차 x 여러 평활 방식으로 flood fill 해 보고, 직사각형에 가깝고
    가늘고 긴(aspect) 영역 중 가장 큰 것을 고른다."""
    alpha = (arr[..., 3] > 40).astype(np.uint8)
    tols = [tol] if tol else [3, 5, 8]
    modes = [mode] if mode else ["darker", "median", "lighter"]
    sx, sy = seed
    best = None
    for md in modes:
        sm = _smooth(arr, md, k)
        for t in tols:
            seen = set()
            for yy in range(sy - radius, sy + radius + 1, 4):
                for xx in range(sx - radius, sx + radius + 1, 4):
                    r = _fill(sm, alpha, (xx, yy), t, close, clip)
                    if r is None:
                        continue
                    lm, rect, area = r
                    key = (round(rect[0][0]), round(rect[0][1]), round(area))
                    if key in seen:
                        continue
                    seen.add(key)
                    (cx, cy), (rw, rh), _ = rect
                    L, w = max(rw, rh), min(rw, rh)
                    if w < 1 or not lm[sy, sx] and not lm[yy, xx]:
                        continue
                    ratio = area / max(1.0, rw * rh)
                    if ratio < 0.72 or not (aspect[0] <= L / w <= aspect[1]) or not (wlim[0] <= w <= wlim[1]):
                        continue
                    sc = area * ratio
                    if best is None or sc > best[0]:
                        best = (sc, lm, rect)
    if best is None:
        return None
    return best[1], best[2]


def _text_rect(arr, box, mode, thresh, k, layout, pad, ang=None, edge=0.4, maxc=48):
    """box 안 글자 획 → (cx, cy, L, w, 기울기) ; 기울기는 세로쓰기 기준(아래쪽이 오른쪽으로 가면 +)"""
    rgb0 = np.ascontiguousarray(arr[..., :3])
    op = cv2.MORPH_CLOSE if mode == "darker" else cv2.MORPH_OPEN
    bg = cv2.morphologyEx(rgb0, op, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    lum = _lum(arr)
    diff = (_lum(bg) - lum) if mode == "darker" else (lum - _lum(bg))
    x0, y0, x1, y1 = box
    sub = ((diff > thresh) & (arr[..., 3] > 40))[y0:y1, x0:x1].astype(np.uint8)
    n, cc, st, _ = cv2.connectedComponentsWithStats(sub, connectivity=8)
    keep = np.zeros_like(sub, bool)
    h, w = sub.shape
    for i in range(1, n):
        bx, by, bw, bh, area = st[i]
        touch = bx == 0 or by == 0 or bx + bw >= w or by + bh >= h
        if area < 3 or touch and (bw > edge * w or bh > edge * h or edge == 0) or max(bw, bh) > maxc:
            continue
        keep |= cc == i
    ys, xs = np.nonzero(keep)
    if len(xs) < 5:
        print("text_rect: no strokes", box)
        return None
    pts = np.stack([xs + x0, ys + y0], 1).astype(np.float32)
    full = np.zeros(arr.shape[:2], bool)
    full[y0:y1, x0:x1] = keep
    (cx, cy), a, L, W_ = _geom(full, layout, ang)
    if _DEBUG[0]:
        print("  text_rect", round(cx), round(cy), round(L), round(W_), round(a, 1))
    return cx, cy, L * pad[1] + 2, W_ * pad[0] + 2, a
    (cx, cy), (rw, rh), ra = cv2.minAreaRect(pts)
    # minAreaRect 각도 → 진행축 기울기
    if layout == "v":
        L, W_, a = (rh, rw, -ra) if rh >= rw else (rw, rh, 90 - ra)
    else:
        L, W_, a = (rw, rh, -ra) if rw >= rh else (rh, rw, 90 - ra)
    a = (a + 90) % 180 - 90
    if ang is not None:
        # 기울기를 고정하고 그 축으로 다시 잰다
        t = math.radians(ang if layout == "v" else ang + 90)
        d = np.array([math.sin(t), math.cos(t)], np.float32)
        nn = np.array([math.cos(t), -math.sin(t)], np.float32)
        u, v = pts @ d, pts @ nn
        L, W_ = float(u.max() - u.min()), float(v.max() - v.min())
        c = d * (u.max() + u.min()) / 2 + nn * (v.max() + v.min()) / 2
        cx, cy, a = float(c[0]), float(c[1]), ang
    return cx, cy, L * pad[1] + 2, W_ * pad[0] + 2, a


def label(text, seed=None, mode="darker", thresh=35, tol=None, fill=None, font="callig", bold=0.03, stroke=None,
          stroke_w=0.0, dilate=1, k=11, margin=(0.12, 0.06), scale=1.0, layout="v", glow=None, dx=0, dy=0,
          close=3, shrink=2, clip=None, rect=None, find=None, aspect=(1.6, 9), wlim=(9, 70), box=None,
          pad=(1.3, 1.12), ang=None, edge=0.4, erase=(1.0, 1.0), maxc=48, line=None, debug=False):
    """seed 가 가리키는 띠(단색 직사각형, 기울어져도 됨)를 찾아 그 안의 글자를 지우고 한국어를 쓴다.

    mode: darker(띠보다 어두운 글자) / lighter(밝은 글자)
    margin: (폭 방향, 길이 방향) 띠 가장자리 여백 비율
    """
    def f(img):
        arr = np.array(img.convert("RGBA"))
        rr = rect
        if line is not None:  # (첫 글자 중심 x, y, 끝 글자 중심 x, y, 글자 크기)
            lx0, ly0, lx1, ly1, lw = line
            if layout == "v":
                la = math.degrees(math.atan2(lx1 - lx0, ly1 - ly0))
            else:
                la = math.degrees(math.atan2(-(ly1 - ly0), lx1 - lx0))
            rr = ((lx0 + lx1) / 2, (ly0 + ly1) / 2, math.hypot(lx1 - lx0, ly1 - ly0) + lw * 1.15, lw * 1.25, la)
        if box is not None:  # box 안 글자 획(테두리에 닿는 덩어리 제외)으로 기울어진 글자 영역을 잰다
            rr = _text_rect(arr, box, mode, thresh, k, layout, pad, ang, edge, maxc)
            if rr is None:
                return img
        if rr is not None:  # 띠를 직접 지정: (중심x, 중심y, 길이, 폭, 기울기)
            rcx, rcy, rL, rw_, rang = rr
            lm = _rect_mask(arr.shape[:2], (rcx, rcy), rang if layout == "v" else rang + 90, rL * erase[1], rw_ * erase[0])
            rect_ = ((rcx, rcy), (rw_, rL), -rang) if layout == "v" else ((rcx, rcy), (rL, rw_), -rang)
        else:
            r = find_label(arr, seed, tol, k, close, find, clip, aspect, wlim)
            if r is None:
                print("label not found", seed)
                return img
            lm, rect_ = r
        if shrink and rr is None:
            lm = cv2.erode(lm.astype(np.uint8), np.ones((2 * shrink + 1, 2 * shrink + 1), np.uint8)).astype(bool)
        rgb0 = np.ascontiguousarray(arr[..., :3])
        op = cv2.MORPH_CLOSE if mode == "darker" else cv2.MORPH_OPEN
        bgimg = cv2.morphologyEx(rgb0, op, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
        lum = _lum(arr)
        if mode == "darker":
            diff = _lum(bgimg) - lum
        else:
            diff = lum - _lum(bgimg)
        m = (diff > thresh) & lm
        if _DEBUG[0]:
            print("  strokes", int(m.sum()))
        col = fill
        if col is None and m.any():
            dv = diff[m]
            col = tuple(int(v) for v in np.median(arr[m][dv >= np.percentile(dv, 50)][:, :3], axis=0))
        mk = m.astype(np.uint8) * 255
        if dilate:
            mk = cv2.dilate(mk, np.ones((2 * dilate + 1, 2 * dilate + 1), np.uint8))
        mk &= cv2.dilate(lm.astype(np.uint8) * 255, np.ones((3, 3), np.uint8))
        # 띠 색으로 메움 (닫힘/열림 결과 + 경계 부드럽게)
        kk = k + 2 * dilate
        fillimg = cv2.morphologyEx(rgb0, op, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kk, kk)))
        fillimg = cv2.GaussianBlur(fillimg, (3, 3), 0)
        al = cv2.GaussianBlur(mk, (3, 3), 0).astype(np.float32)[..., None] / 255
        arr[..., :3] = (rgb0 * (1 - al) + fillimg * al).astype(np.uint8)
        out = Image.fromarray(arr)
        (cx, cy), (rw, rh), ra = rect_
        # 긴 변 = 글자 진행 방향
        if layout == "v":
            if rh >= rw:
                L, w, a_ = rh, rw, -ra
            else:
                L, w, a_ = rw, rh, 90 - ra
            a_ = (a_ + 90) % 180 - 90
        else:
            if rw >= rh:
                L, w, a_ = rw, rh, -ra
            else:
                L, w, a_ = rh, rw, 90 - ra
            a_ = (a_ + 90) % 180 - 90
        if debug or _DEBUG[0]:
            print("label", seed, "rect", [round(v, 1) for v in (cx, cy, L, w, a_)])
            a2 = np.array(out)
            cs, _ = cv2.findContours(lm.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            cv2.drawContours(a2, cs, -1, (255, 0, 0, 255), 1)
            out = Image.fromarray(a2)
        if not text:
            return out
        bw, bl = w * (1 - 2 * margin[0]), L * (1 - 2 * margin[1])
        col4 = tuple(col or (0, 0, 0))[:3] + (255,)
        sw_ratio, st = stroke_w, stroke
        if bold and stroke is None:
            st, sw_ratio = col4, bold
        if st is not None:
            st = tuple(st)[:3] + (255,)
        if layout == "v":
            t = fit_text(text, font, bw * scale, bl * scale, "v", col4, st, sw_ratio)
        else:
            t = fit_text(text, font, bl * scale, bw * scale, "h", col4, st, sw_ratio)
        rot = a_
        if t is None:
            return out
        if abs(rot) > 0.5:
            big = t.resize((t.width * 4, t.height * 4), Image.LANCZOS).rotate(rot, Image.BICUBIC, expand=True)
            t = big.resize((max(1, big.width // 4), max(1, big.height // 4)), Image.LANCZOS)
        px_, py_ = int(round(cx + dx - t.width / 2)), int(round(cy + dy - t.height / 2))
        if glow:
            from PIL import ImageFilter
            r, gc = glow
            g = Image.new("RGBA", (t.width + 4 * r, t.height + 4 * r), (0, 0, 0, 0))
            g.alpha_composite(t, (2 * r, 2 * r))
            a = g.getchannel("A").filter(ImageFilter.GaussianBlur(r))
            gl = Image.new("RGBA", g.size, tuple(gc[:3]) + (255,))
            gl.putalpha(a.point(lambda v: v * gc[3] // 255))
            out.alpha_composite(gl, (px_ - 2 * r, py_ - 2 * r))
        out.alpha_composite(t, (px_, py_))
        return out
    f.seed = seed if seed is not None else (rect[:2] if rect else (line[:2] if line else None)) or (rect[:2] if rect else (((box[0] + box[2]) // 2, (box[1] + box[3]) // 2) if box else None))
    return f


def comp_text(text, box=None, pick="all", dilate=1, min_area=20, **draw):
    """투명 배경 위 글자 덩어리(연결 요소)를 지우고(알파 0) 그 영역에 한국어를 쓴다.

    pick: all | outlined(흰 글자+검은 테두리 덩어리만: 태극 무늬 방울 등은 남김) | dark | light
    draw: relabel 의 글자 옵션(font, fill, stroke, stroke_w, layout, scale, bold, glow, ...)
    """
    def f(img):
        arr = np.array(img.convert("RGBA"))
        H, W = arr.shape[:2]
        x0, y0, x1, y1 = box or (0, 0, W, H)
        a = (arr[..., 3] > 20).astype(np.uint8)
        sub = np.zeros_like(a)
        sub[y0:y1, x0:x1] = a[y0:y1, x0:x1]
        n, cc, st, _ = cv2.connectedComponentsWithStats(sub, connectivity=8)
        lum = _lum(arr)
        keep = np.zeros((H, W), bool)
        for i in range(1, n):
            if st[i, 4] < min_area:
                continue
            c = cc == i
            if pick == "outlined":
                lw, dk = (lum[c] > 200).mean(), (lum[c] < 70).mean()
                if lw < 0.1 or dk < 0.1:
                    continue
            elif pick == "dark" and lum[c].mean() > 110:
                continue
            elif pick == "light" and lum[c].mean() < 140:
                continue
            keep |= c
        if not keep.any():
            return img
        ys, xs = np.nonzero(keep)
        tb = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
        mk = keep.astype(np.uint8)
        if dilate:
            mk = cv2.dilate(mk, np.ones((2 * dilate + 1, 2 * dilate + 1), np.uint8))
        arr[mk > 0, 3] = 0
        out = Image.fromarray(arr)
        sp = {"text": text, "font": "brush", "mask": "none", "text_box": tb, "fill": (0, 0, 0)}
        sp.update(draw)
        return relabel(out, sp)
    return f


def framed(img):
    """UI 번들 쪽 종이 액자 그림인지 (액자 윗부분 종이 색)"""
    r, g, b, a = img.convert("RGBA").getpixel((150, 30))
    return a > 200 and 120 < (r + g + b) / 3 < 235


FRAME = (66, 74, 0.57)  # UI 액자 그림 = ArtData 그림을 0.57배 해서 (66, 74) 에 놓은 것


def in_frame(spec):
    """ArtData 좌표로 쓴 spec 을 UI 액자 그림에 적용: 액자 속 그림을 원래 크기로 키워 적용 후 바뀐 곳만 되돌려 넣는다."""
    def f(img):
        from image_specs import apply
        ox, oy, sc = FRAME
        w, h = round(300 * sc), round(326 * sc)
        base = img.convert("RGBA")
        crop = base.crop((ox, oy, ox + w, oy + h))
        up = crop.resize((300, 326), Image.LANCZOS)
        new = apply(up.copy(), spec)
        d = np.abs(np.array(new).astype(int) - np.array(up).astype(int)).max(-1) > 3
        if not d.any():
            return img
        small = new.resize((w, h), Image.LANCZOS)
        m = cv2.resize(cv2.dilate(d.astype(np.uint8) * 255, np.ones((5, 5), np.uint8)), (w, h),
                       interpolation=cv2.INTER_AREA)
        m = Image.fromarray(cv2.GaussianBlur(m, (3, 3), 0))
        out = base.copy()
        out.paste(Image.composite(small, crop, m), (ox, oy))
        return out
    return f


def variant(art, ui=None):
    """ArtData(그림만) / UI(종이 액자 안 축소 그림) 두 종류가 있는 텍스처. ui 생략 시 art spec 을 액자 안에 적용"""
    def f(img):
        from image_specs import apply
        return apply(img, (ui or in_frame(art)) if framed(img) else art)
    return f


def chain(*fs):
    def f(img):
        from image_specs import apply
        for s in fs:
            img = apply(img, s)
        return img
    return f


BOOKS = {
    "144": label("대연주천경", line=(106, 73, 149, 174, 26), thresh=35, k=15, fill=(225, 135, 35), dilate=2),
    "50100": label("토납법", rect=(118, 113, 84, 34, -4), thresh=25),
    "50101": label("혼원공", line=(112, 100, 140, 148, 24), thresh=30),
    "50104": label("구전현원공", (182, 122)),
    "50105": label("신기백련", (137, 120)),
    "51101": {"text": "금", "font": "callig", "mask": "darker", "thresh": 25, "box": (150, 93, 175, 122), "fill": (235, 125, 40), "dilate": 1, "bold": 0.03},
    "51102": label("어검술", (176, 112)),
    "51201": label("천망술", (137, 97), thresh=30),
    "51202": label("초진검보", (177, 122)),
    "51203": label("파살검보", (180, 120)),
    "51204": label("음양양의검", (147, 127), mode="lighter"),
    "51205": label("무상검전", rect=(124, 113, 115, 34, 20), mode="lighter", thresh=30),
    "51206": label("귀류검경", (192, 115)),
    "51207": label("구소검포결", line=(210, 88, 170, 180, 24), mode="lighter", thresh=15, k=15, dilate=2, fill=(185, 35, 40)),
    "51250": label("검백결", (177, 117), mode="lighter"),
    "51306": label("금봉보", (180, 117), mode="lighter"),
    "51307": label("심검결", rect=(160, 128, 80, 32, 33)),
    "51308": label("신검보", rect=(197, 113, 85, 24, -15)),
    "51309": label("장봉결", (150, 127), mode="lighter"),
    "51351": label("분광검법", rect=(183, 128, 140, 28, -17), thresh=50, erase=(1.15, 1.0)),
    "51410": label("열금결", rect=(169, 158, 116, 44, -2), thresh=30, erase=(1.3, 1.1)),
    "51411": label("금봉양의결", rect=(225, 122, 126, 32, 0), thresh=30, erase=(1.5, 1.05)),
    "51450": label("귀허검법", (115, 120), thresh=20),
    "51451": label("혈륙검법", (130, 75), thresh=25),
    "52102": label("백약보", (142, 122), mode="lighter"),
    "52201": label("장생록", rect=(163, 123, 100, 32, 30)),
    "52202": label("백독보", (185, 130)),
    "52203": label("유란록", (170, 115)),
    "52204": label("단장경", (140, 135)),
    "52205": label("춘잠결", rect=(139, 113, 64, 18, 0), thresh=12),
    "52206": label("서오공", rect=(157, 117, 82, 28, 20), thresh=8, dilate=2),
    "52208": label("화연결", (157, 135)),
    "52209": label("낙앵결", rect=(176, 112, 140, 52, 18), thresh=30, erase=(1.4, 1.1)),
    "52306": label("독심경", (167, 112)),
    "52307": label("온령결", (137, 127)),
    "52308": label("청명진해", (150, 120)),
    "52309": label("황정내경", (165, 115), mode="darker"),
    "52311": label("화서목", rect=(149, 122, 100, 34, 27), thresh=40),
    "52312": label("귀근호원법", rect=(163, 140, 142, 32, -19), thresh=40),
    "52411": label("만목귀령술", rect=(192, 125, 136, 30, 30), thresh=40),
    "52412": label("혈령경", rect=(162, 143, 160, 56, 21), thresh=30, k=21, fill=(115, 22, 20), margin=(0.05, 0.05)),
    "53102": label("유심술", (163, 115)),
    "53201": label("지수공", rect=(135, 111, 78, 24, -6), thresh=30),
    "53202": label("회춘전", rect=(152, 126, 80, 28, 38)),
    "53203": label("속맥경", rect=(174, 114, 80, 28, 23)),
    "53204": label("인기경", rect=(175, 113, 82, 26, 27)),
    "53205": label("수원결", rect=(172, 118, 80, 28, 35), thresh=25),
    "53207": label("귀장술", rect=(160, 118, 90, 30, 29), mode="lighter", thresh=25),
    "53209": label("윤원심법", rect=(145, 122, 152, 46, -18), k=21, margin=(0.05, 0.04)),
    "53210": label("한영추혼록", rect=(165, 130, 128, 32, 26)),
    "53307": label("응진결", rect=(203, 120, 96, 32, -15), mode="lighter", thresh=25, erase=(1.6, 1.12)),
    "53308": label("창명결", rect=(154, 117, 96, 32, 32)),
    "53309": label("석잔조", rect=(165, 91, 98, 32, 35), thresh=25, erase=(1.15, 1.12)),
    "53312": label("명흡술", rect=(162, 123, 116, 42, 32)),
    "53313": label("회광심결", rect=(151, 157, 86, 26, -33), thresh=30),
    "53314": label("동심전", rect=(130, 132, 70, 24, 3), thresh=30),
    "53412": label("수일결", rect=(139, 113, 120, 44, -9), k=17),
    "54102": label("쉬골공", rect=(130, 120, 80, 30, 26), mode="lighter"),
    "54201": label("분천결", rect=(137, 115, 78, 28, 0), thresh=25),
    "54202": label("현화단골록", rect=(145, 136, 138, 32, 32), mode="lighter"),
    "54203": label("혈수공", rect=(135, 106, 86, 32, 25), mode="lighter", thresh=30),
    "54204": label("분심검보", rect=(181, 123, 110, 32, 32)),
    "54205": label("분맥법", rect=(162, 118, 96, 32, 28), thresh=20),
    "54206": label("연혈술", rect=(196, 140, 82, 30, 29)),
    "54208": label("연봉결", rect=(157, 71, 154, 48, 1), layout="h", k=21, margin=(0.06, 0.06)),
    "54209": label("폭염결", rect=(146, 128, 110, 44, -6), k=17),
    "54306": label("분소결", rect=(170, 112, 84, 30, 24), mode="lighter", thresh=30),
    "54307": label("연신결", rect=(156, 108, 96, 32, 26), mode="lighter", thresh=30),
    "54308": label("연백결", rect=(194, 126, 92, 30, -30), mode="lighter", thresh=30),
    "54311": label("화룡공", rect=(185, 206, 126, 48, 9), layout="h", k=21, margin=(0.06, 0.06)),
    "54312": label("염식심법", rect=(202, 111, 122, 34, 35)),
    "54410": label("구사공", rect=(158, 122, 110, 44, 35), k=17),
    "54411": label("신신결", rect=(149, 131, 140, 48, -33), mode="lighter", k=17, scale=0.85, fill=(240, 120, 50)),
    "55102": label("금강권", rect=(163, 126, 88, 34, 18), mode="lighter"),
    "55201": label("진악결", rect=(137, 108, 72, 26, -7), thresh=25),
    "55202": label("혼원파장권", rect=(166, 124, 128, 32, 28), mode="lighter"),
    "55203": label("부동경", line=(115, 78, 140, 125, 22), mode="lighter", thresh=25),
    "55204": label("윤회경", line=(145, 103, 172, 147, 22)),
    "55205": label("어수결", line=(159, 93, 192, 147, 22), mode="lighter"),
    "55206": label("어룡변", line=(154, 87, 174, 140, 22), mode="lighter"),
    "55211": label("반석공", line=(176, 52, 191, 97, 22)),
    "55212": label("계수결", line=(105, 89, 168, 83, 24), layout="h", k=17),
    "55307": label("박룡진법", line=(125, 63, 197, 110, 22), layout="h", mode="lighter", thresh=25, fill=(235, 195, 70)),
    "55308": label("동혼경", line=(209, 90, 187, 133, 24), mode="lighter"),
    "55309": label("창벽경", line=(99, 60, 129, 113, 22), mode="lighter", thresh=20),
    "55312": label("분신결", line=(198, 97, 220, 157, 22), thresh=30),
    "55313": label("토영결", line=(125, 93, 179, 167, 44), k=21, margin=(0.05, 0.05)),
    "56201": label("서혼비법", line=(101, 67, 132, 120, 24), mode="lighter", thresh=20, fill=(140, 25, 25)),
    "56202": label("음차현공", line=(153, 83, 191, 163, 26)),
    "56203": label("칠살경", line=(210, 101, 178, 147, 22)),
    "56204": label("쇄혼술", line=(100, 75, 136, 132, 24)),
    "56205": label("역생겁전", line=(131, 80, 188, 162, 30), k=15),
    "56301": label("탈령천권", line=(217, 93, 218, 192, 26), thresh=30),
    "56401": label("무장결", line=(143, 90, 175, 150, 28), k=15),
    "57101": label("칠성보전", line=(91, 62, 168, 115, 22), layout="h"),
    "57201": label("관성술", line=(222, 93, 222, 155, 24), thresh=30),
    "57204": label("고본경", line=(176, 88, 154, 147, 32), k=15),
    "57205": label("조식결", line=(152, 90, 178, 148, 24), k=15),
    "57206": label("연원보감", line=(148, 188, 206, 175, 20), layout="h"),
    "57302": label("연심결", line=(217, 90, 190, 138, 22), thresh=25),
    "57303": label("염신술", line=(208, 88, 190, 138, 22), mode="lighter"),
    "57306": label("귀원보감", line=(178, 90, 218, 165, 26), k=15),
    "58301": label("천공경", line=(97, 68, 152, 102, 20), layout="h", mode="lighter", thresh=30),
    "52101": {"text": "목", "font": "callig", "mask": "darker", "thresh": 25, "box": (132, 86, 162, 128),
              "fill": (50, 150, 40), "dilate": 1, "bold": 0.03},
    "53206": label("인조법", rect=(136, 118, 88, 28, 30), mode="lighter", thresh=25),
}


# ---------------------------------------------------------------- 투명 배경 위 큰 붓글씨 (임무/선택 카드)
def brush(text, fill=(0, 0, 0), **kw):
    sp = {"text": text, "font": "brush", "mask": "alpha", "dilate": 1, "fill": fill, "bold": 0.012}
    sp.update(kw)
    return sp


def glow_char(text, fill, glow):  # 빛나는 한 글자 (무/기/수/단/술/마)
    return {"text": text, "font": "callig", "mask": "alpha", "dilate": 1, "fill": fill, "bold": 0.02,
            "glow": (5, glow), "scale": 0.8}


GLOW = {"white": ((248, 244, 230), (255, 250, 230, 230)),
        "gold": ((255, 190, 40), (255, 160, 20, 230)),
        "red": ((240, 20, 20), (255, 0, 0, 230))}


def _ui_faint(text, box=(92, 64, 182, 252), th=148, everything=False):
    """UI 액자 속 흐릿한 이름: 종이보다 어두운 획(테두리 닿는 덩어리 제외)을 지우고 같은 자리에 쓴다

    everything=True 면 모양 필터 없이 영역 안의 어두운 획을 모두 지운다 (X 표시를 다시 그리는 경우)"""
    def f(img):
        arr = np.array(img.convert("RGBA"))
        x0, y0, x1, y1 = box
        lum = _lum(arr)
        sub = (lum[y0:y1, x0:x1] < th).astype(np.uint8)
        n, cc, st, _ = cv2.connectedComponentsWithStats(sub, connectivity=8)
        keep = np.zeros_like(sub, bool)
        h, w = sub.shape
        for i in range(1, n):
            bx, by, bw, bh, ar = st[i]
            if ar < 12:
                continue
            if not everything and (bx == 0 or by == 0 or bx + bw >= w or by + bh >= h):
                continue
            if not everything and max(bw, bh) > 8 * min(bw, bh):
                continue
            keep |= cc == i
        if not keep.any():
            return img
        full = np.zeros(arr.shape[:2], bool)
        full[y0:y1, x0:x1] = keep
        ys, xs = np.nonzero(full)
        tb = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
        mk = cv2.dilate(full.astype(np.uint8) * 255, np.ones((7, 7), np.uint8))
        arr[..., :3] = cv2.inpaint(np.ascontiguousarray(arr[..., :3]), mk, 5, cv2.INPAINT_TELEA)
        return relabel(Image.fromarray(arr), {"text": text, "font": "callig", "mask": "none", "text_box": tb,
                                              "fill": (118, 110, 92), "layout": "v", "bold": 0.02})
    return f


def faint(text):  # 흐릿한 인물/이름 글씨 (ArtData: 투명 배경 / UI: 같은 그림이 종이 액자 안에)
    return variant(brush(text, fill=None, layout="v", font="callig", bold=0.02), _ui_faint(text))


def realm(big, small=None):  # 경지 표시: 흰 글자+검은 테두리 (대각선) + 아래 검은 '초기/중기/후기'
    out = [comp_text(big, pick="outlined", layout="diag", fill=(255, 255, 255), stroke=(0, 0, 0),
                     stroke_w=0.09, scale=1.0, dilate=4)]
    if small:
        out.insert(0, comp_text(small, box=(0, 225, 300, 326), pick="dark", fill=(10, 10, 10), bold=0.04, font="callig", scale=0.9))
    return chain(*out)


TEXTS = {
    # 먹 번짐 아이콘
    "-20057": {"text": "마", "font": "brush", "mask": "sat", "thresh": 0.4, "fill": (225, 30, 30), "dilate": 2,
               "bold": 0.03, "inset": 0.12},
    "-50062": {"text": "인", "font": "brush", "mask": "light", "thresh": 120, "fill": (255, 255, 255), "dilate": 2,
               "bold": 0.04, "inset": 0.12},
    "-5029": {"text": "결", "font": "brush", "mask": "light", "thresh": 120, "fill": (255, 255, 255), "dilate": 2,
              "bold": 0.04, "inset": 0.12},
    # 큰 붓글씨
    "18001": brush("귀사", layout="v"),
    "2000200": brush("미움\n사기", text_inset=0.12, scale=0.85),
    "2000201": brush("기이한\n보물", text_inset=0.12, scale=0.85),
    "2000202": brush("성수", layout="v"),
    "2000203": brush("비경", layout="v"),
    "2102203": brush("사", fill=(205, 45, 45)),
    "2102204": brush("정"),
    "2102220": brush("응"),
    "2102221": brush("사양", text_inset=0.1, scale=0.9),
    "2104201": brush("영약\n돌보기"),
    "2105201": brush("비무", layout="v"),
    "2105202": brush("날\n따라와", text_inset=0.1, scale=0.9),
    "2150001": brush("문검!", layout="v"),
    "2150004": brush("현검각\n입문"),
    "2302401": brush("최심부", layout="v"),
    "2304402": brush("거절", text_inset=0.2, scale=0.8),
    "2304403": brush("허락", text_inset=0.2, scale=0.8),
    "2304404": brush("지화", layout="v"),
    "2304407": brush("속임", text_inset=0.2, scale=0.8),
    "2309200": brush("이정표", layout="v"),
    "2321000": brush("변장 중", layout="v"),
    "2321001": brush("파", fill=None),
    "2321002": brush("활", fill=None),
    "2345001": brush("승", text_inset=0.25, scale=0.8),
    "2346400": brush("가져\n가기", text_inset=0.15, scale=0.85),
    "2346420": brush("특성", layout="v"),
    "310": brush("대도", fill=(0, 0, 0), stroke=(255, 255, 255), stroke_w=0.07, bold=0.01, layout="diag", font="callig"),
    "311": brush("칠정\n육욕", fill=(220, 25, 25)),
    # 빛나는 한 글자: 무수/기수/수수/단수/술수/마수
    **{n: glow_char(t, *GLOW[c]) for n, t, c in [
        ("230", "무", "white"), ("231", "무", "gold"), ("232", "무", "red"),
        ("240", "기", "white"), ("241", "기", "gold"), ("242", "기", "red"),
        ("250", "수", "white"), ("251", "수", "gold"), ("252", "수", "red"),
        ("260", "단", "white"), ("261", "단", "gold"), ("262", "단", "red"),
        ("270", "술", "white"), ("271", "술", "gold"), ("272", "술", "red"),
        ("280", "마", "white"), ("281", "마", "gold"), ("282", "마", "red")]},
    # 흐릿한 이름 글씨
    "30101": faint("소침묵"),
    "30110": faint("소련연"),
    "30801": faint("부명"),
    "30802": faint("상리"),
    "30803": faint("창효"),
    "30804": faint("구신"),
    # 경지
    "5000": comp_text("수사", pick="outlined", layout="diag", fill=(255, 255, 255), stroke=(0, 0, 0), stroke_w=0.09,
                      dilate=4),
    "5001": realm("연기", "중기"), "5002": realm("연기", "후기"),
    "5003": realm("축기", "초기"), "5004": realm("축기", "중기"), "5005": realm("축기", "후기"),
    "5006": realm("결단", "초기"), "5007": realm("결단", "후기"),
    "5008": realm("원영", "초기"), "5009": realm("원영", "후기"),
    "5010": realm("화신"), "5011": realm("연허"), "5012": realm("합체"), "5013": realm("대승"),
}

def stroke_text(text, box, mode="darker", thresh=30, fill=None, font="callig", layout="h", bold=0.03, dilate=2, **kw):
    sp = {"text": text, "font": font, "mask": mode, "thresh": thresh, "box": box, "dilate": dilate, "bold": bold,
          "layout": layout}
    if fill is not None:
        sp["fill"] = fill
    sp.update(kw)
    return sp


TEXTS.update({
    "-50019": {"text": "령", "font": "callig", "mask": "light", "thresh": 150, "box": (16, 14, 46, 46),
               "fill": (255, 255, 255), "dilate": 1, "bold": 0.05},
    "15014": stroke_text("령", (102, 112, 198, 226), thresh=25, fill=(70, 70, 66), bold=0.02, scale=0.85),
    "100083": stroke_text("금지", (138, 88, 186, 160), thresh=22, fill=(22, 24, 30), layout="v", bold=0.05),
    "2000101": [stroke_text("체", (206, 76, 238, 108), thresh=40, fill=(60, 55, 50), bold=0.02, scale=0.85),
                stroke_text("포", (206, 140, 238, 174), thresh=40, fill=(60, 55, 50), bold=0.02, scale=0.85)],
    "229006": stroke_text("술", (120, 155, 177, 210), mode="dark", thresh=60, fill=(25, 15, 12), bold=0.03),
    "19001": stroke_text("괘", (100, 105, 200, 215), thresh=18, fill=(240, 170, 80), bold=0.02),
    "213011": stroke_text("약", (165, 122, 222, 215), thresh=30, fill=(140, 50, 30), bold=0.04),
    "2314200": stroke_text("우승", (136, 128, 172, 190), thresh=40, fill=(40, 35, 30), layout="v", bold=0.03),
})


# ---------------------------------------------------------------- 비무 대회 패 / 계약서
def plate(text, layout="v", **kw):  # 흰 종이 패 위 검은 붓글씨
    sp = {"text": text, "font": "brush", "mask": "dark", "thresh": 80, "box": (95, 55, 215, 288),
          "fill": (15, 12, 10), "dilate": 2, "bold": 0.015, "layout": layout, "scale": 0.88}
    sp.update(kw)
    return sp


def gold_plate(text, **kw):  # 붉은 테 금빛 패
    sp = {"text": text, "font": "brush", "mask": "dark", "thresh": 70, "box": (105, 62, 198, 280),
          "fill": (25, 15, 10), "dilate": 2, "bold": 0.015, "layout": "v", "scale": 0.85}
    sp.update(kw)
    return sp


def keep_red(spec):  # 붉은 X 표시는 원본 그대로 위에 남긴다
    def f(img):
        from image_specs import apply
        arr = np.array(img.convert("RGBA"))
        rgb = arr[..., :3].astype(int)
        red = (rgb[..., 0] > 110) & (rgb[..., 0] - rgb[..., 1] > 50) & (arr[..., 3] > 40)
        out = np.array(apply(img, spec))
        out[red] = arr[red]
        return Image.fromarray(out)
    return f


def contract(text):  # 낡은 계약서 아래쪽 'N年'
    return {"text": text, "font": "brush", "mask": "dark", "thresh": 60, "box": (70, 178, 250, 250),
            "fill": (15, 12, 10), "dilate": 2, "bold": 0.02, "scale": 0.9}


TEXTS.update({
    "2314201": plate("대회\n규칙", layout="h"),
    "2314202": plate("예선"),
    "2314203": plate("16\n강", layout="h"),
    "2314204": plate("8\n강", layout="h"),
    "2314205": plate("4\n강", layout="h"),
    "2314206": plate("결승전"),
    "2314214": keep_red(plate("반칙", thresh=60)),
    "2314210": gold_plate("참가"),
    "2314211": gold_plate("3위", text_box=(110, 70, 192, 270)),
    "2314212": gold_plate("준우승"),
    "2314213": gold_plate("우승"),
    "2346100": {"text": "담보", "font": "brush", "mask": "sat", "thresh": 0.4, "box": (60, 150, 240, 262),
                "fill": (150, 30, 25), "dilate": 2, "bold": 0.02},
    **{f"234610{i + 1}": contract(f"{y}년") for i, y in enumerate([10, 20, 40, 80, 160, 320])},
})


TEXTS.update({
    "2321010": label("암살술", rect=(124, 105, 92, 30, 33), thresh=20, dilate=2, fill=(120, 20, 25), margin=(0.15, 0.08)),
    "30113": variant({"text": "무상전", "font": "callig", "mask": "light", "thresh": 105, "box": (85, 35, 185, 270),
                      "fill": (205, 190, 140), "layout": "v", "dilate": 2, "bold": 0.03,
                      "text_box": (100, 50, 172, 250), "scale": 0.85}),
    "30112": variant({"text": "선인지로", "font": "brush", "mask": "dark", "thresh": 90, "box": (205, 18, 286, 252),
                      "fill": (20, 20, 20), "layout": "v", "dilate": 2, "bold": 0.02}),
    "30109": variant({"text": "선인지로", "font": "brush", "mask": "dark", "thresh": 90, "box": (250, 50, 290, 285),
                      "fill": (20, 20, 20), "layout": "v", "dilate": 2, "bold": 0.02,
                      "text_box": (250, 55, 290, 280)}),
    "30107": variant({"text": "무", "font": "brush", "mask": "darker", "thresh": 14, "box": (100, 85, 200, 160),
                      "fill": (175, 178, 180), "dilate": 2, "bold": 0.02, "scale": 0.8}),
})


def crossed(text, lines, col=(70, 62, 45, 210), width=4):
    """흐릿한 이름 + X 표시 (30102): 이름을 바꾸고 X 선을 다시 긋는다"""
    def draw(img, tf):
        from PIL import ImageDraw
        big = img.resize((img.width * 4, img.height * 4), Image.LANCZOS)
        ov = Image.new("RGBA", big.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        for x0, y0, x1, y1 in lines:
            (a, b), (c, e) = tf(x0, y0), tf(x1, y1)
            n = 12  # 붓선처럼 가운데가 굵은 선
            for i in range(n):
                t0, t1 = i / n, (i + 1) / n
                wd = max(1, int(4 * width * tf.s * (0.35 + 0.65 * math.sin(math.pi * (t0 + t1) / 2))))
                d.line([(4 * (a + (c - a) * t0), 4 * (b + (e - b) * t0)), (4 * (a + (c - a) * t1), 4 * (b + (e - b) * t1))],
                       fill=col, width=wd)
        ov = ov.resize(img.size, Image.LANCZOS)
        out = img.copy()
        out.alpha_composite(ov)
        return out

    def ident(x, y):
        return x, y
    ident.s = 1.0

    def framed_tf(x, y):
        ox, oy, sc = FRAME
        return ox + x * sc, oy + y * sc
    framed_tf.s = FRAME[2]

    def f(img):
        from image_specs import apply
        if framed(img):
            img = _ui_faint(text, everything=True)(img)
            return draw(img, framed_tf)
        img = apply(img, brush(text, fill=None, layout="v", font="callig", bold=0.02))
        return draw(img, ident)
    return f


TEXTS["30102"] = crossed("냉무봉", [(63, 70, 210, 190), (217, 93, 73, 253)])

ITEMS = {**BOOKS, **TEXTS}
