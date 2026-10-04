"""이미지 속 글자를 지우고 한국어를 다시 그리는 함수들.

relabel(img, spec) 의 spec 키
  text     그릴 한국어. "\n" 으로 줄바꿈, layout="v" 면 글자마다 세로로 쌓음
  font     "brush"(East Sea Dokdo) | "callig"(Song Myung) | "serif"(Noto Serif KR)
  mask     지울 글자 픽셀 선택: light / dark / sat / alpha(전부 투명 처리) / none
  thresh   mask 임계값
  box      (x0, y0, x1, y1) 작업 영역 (기본: 이미지 전체)
  dilate   mask 팽창 픽셀
  fill     글자색 (기본: 원래 글자 픽셀 중앙값)
  stroke   외곽선 색, stroke_w 외곽선 두께(글자 크기 대비 비율)
  scale    글자 영역 대비 크기 배율
  layout   h | v
  shadow   (dx, dy, (r,g,b,a)) 그림자
  inset    box 안쪽 여백
  bg       지운 자리를 인페인트 대신 이 색으로 채움
  glow     (반경, (r,g,b,a)) 글자 주위 번지는 빛
  stretch_y 글자를 세로로 늘이는 배율
  bold     외곽선이 없을 때 같은 색 외곽선으로 굵게 (글자 크기 대비 비율)
"""
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT_DIR = Path(__file__).parent / "fonts"
FONTS = {
    "brush": str(FONT_DIR / "EastSeaDokdo-Regular.ttf"),
    "callig": str(FONT_DIR / "SongMyung-Regular.ttf"),
    "serif": str(FONT_DIR / "NotoSerifKR-VF.ttf"),
}


def _mask(arr, mode, thresh):
    rgb = arr[..., :3].astype(np.float32)
    a = arr[..., 3]
    lum = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
    mx, mn = rgb.max(-1), rgb.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1)
    vis = a > 40
    if mode == "light":
        return vis & (lum > (thresh or 150))
    if mode == "dark":
        return vis & (lum < (thresh or 80))
    if mode == "sat":
        return vis & (sat > (thresh or 0.35)) & (mx > 60)
    if mode == "alpha":
        return a > (thresh or 8)
    if mode == "disc":  # 영역에 내접하는 원 전체
        h, w = a.shape
        yy, xx = np.mgrid[0:h, 0:w]
        return ((xx - (w - 1) / 2) / (w / 2)) ** 2 + ((yy - (h - 1) / 2) / (h / 2)) ** 2 <= 1
    if mode in ("lighter", "darker"):  # 주변(중앙값 블러)보다 밝은/어두운 가는 획 — 무늬 있는 배경 위 글자
        k = 15
        bgl = cv2.medianBlur(np.clip(lum, 0, 255).astype(np.uint8), k).astype(np.float32)
        diff = (lum - bgl) if mode == "lighter" else (bgl - lum)
        return vis & (diff > (thresh or 30))
    if mode == "none":
        return np.zeros(a.shape, bool)
    raise ValueError(mode)


def _bbox(m):
    ys, xs = np.nonzero(m)
    if len(xs) == 0:
        return None
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def _font(name, size):
    f = ImageFont.truetype(FONTS[name], size)
    if name == "serif":
        f.set_variation_by_axes([900])
    return f


SOLID_FONTS = {"brush"}  # 마른 붓 틈을 메워 그릴 폰트


def _render(text, font, size, layout, fill, stroke, sw):
    """글자를 투명 캔버스에 그려 잘라낸 이미지를 돌려준다."""
    f = _font(font, size)
    if layout == "diag":  # 두 글자를 대각선으로 (왼쪽 위 → 오른쪽 아래)
        a, b = _render(text[0], font, size, "h", fill, stroke, sw), _render(text[1:], font, size, "h", fill, stroke, sw)
        ox, oy = int(a.width * 0.5), int(a.height * 0.92)
        im = Image.new("RGBA", (max(a.width, ox + b.width), oy + b.height), (0, 0, 0, 0))
        im.alpha_composite(a, (0, 0))
        im.alpha_composite(b, (ox, oy))
        return im
    lines = list(text) if layout == "v" else text.split("\n")
    lines = [l for l in lines if l != "\n"]
    pad = sw + 4
    tmp = Image.new("RGBA", (1, 1))
    d = ImageDraw.Draw(tmp)
    boxes = [d.textbbox((0, 0), l, font=f, stroke_width=sw) for l in lines]
    lh = [b[3] - b[1] for b in boxes]
    lw = [b[2] - b[0] for b in boxes]
    gap = int(size * (0.02 if layout == "v" else 0.08))
    W = max(lw) + pad * 2
    H = sum(lh) + gap * (len(lines) - 1) + pad * 2
    def draw(color, width):
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dd = ImageDraw.Draw(layer)
        y = pad
        for l, b, w, h in zip(lines, boxes, lw, lh):
            dd.text(((W - w) / 2 - b[0], y - b[1]), l, font=f, fill=color,
                    stroke_width=width, stroke_fill=color)
            y += h + gap
        return layer

    if font not in SOLID_FONTS:
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        y = pad
        for l, b, w, h in zip(lines, boxes, lw, lh):
            d.text(((W - w) / 2 - b[0], y - b[1]), l, font=f, fill=fill,
                   stroke_width=sw, stroke_fill=stroke)
            y += h + gap
        return im.crop(im.getbbox())
    # 붓글씨 폰트의 마른 붓 틈(구멍)을 메워 단색 글자로: 외곽선/채움 층을 따로 그려 닫힘 연산
    k = max(3, int(size * 0.06) | 1)
    kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for color, width in ([(stroke, sw)] if stroke is not None and sw else []) + [(fill, 0)]:
        layer = draw(tuple(color[:3]) + (255,), width)
        a = cv2.morphologyEx(np.array(layer.getchannel("A")), cv2.MORPH_CLOSE, kern)
        if width:  # 외곽선 층: 바깥과 이어지지 않은 구멍은 모두 메움
            hole = (a < 128).astype(np.uint8)
            n, cc = cv2.connectedComponents(hole, connectivity=4)
            border = set(np.unique(np.concatenate([cc[0], cc[-1], cc[:, 0], cc[:, -1]])))
            for i in range(1, n):
                if i not in border:
                    a[cc == i] = 255
        layer.putalpha(Image.fromarray(a).point(lambda v, m=color[3] if len(color) > 3 else 255: v * m // 255))
        im.alpha_composite(layer)
    return im.crop(im.getbbox())


def fit_text(text, font, bw, bh, layout="h", fill=(255, 255, 255, 255), stroke=None,
             stroke_w=0.0, scale=1.0):
    """(bw, bh) 영역에 맞는 가장 큰 글자 이미지. 작은 글자도 깔끔하도록 4배로 그려 축소한다."""
    ss = 4 if max(bw, bh) < 200 else 1
    lo, hi, best = 4, 600 * ss, None
    while lo <= hi:
        mid = (lo + hi) // 2
        sw = int(round(mid * stroke_w)) if stroke else 0
        im = _render(text, font, mid, layout, fill, stroke, sw)
        if im.width <= bw * scale * ss and im.height <= bh * scale * ss:
            best, lo = im, mid + 1
        else:
            hi = mid - 1
    if ss > 1 and best is not None:
        best = best.resize((max(1, round(best.width / ss)), max(1, round(best.height / ss))), Image.LANCZOS)
    return best


def relabel(img: Image.Image, spec: dict) -> Image.Image:
    arr = np.array(img.convert("RGBA"))
    H, W = arr.shape[:2]
    x0, y0, x1, y1 = spec.get("box") or (0, 0, W, H)
    if any(isinstance(v, float) for v in (x0, y0, x1, y1)):  # 비율 좌표 (0.0~1.0)
        x0, x1 = (int(v * W) if isinstance(v, float) else v for v in (x0, x1))
        y0, y1 = (int(v * H) if isinstance(v, float) else v for v in (y0, y1))
    x1, y1 = min(x1, W), min(y1, H)
    bx0, by0, bx1, by1 = x0, y0, x1, y1
    ins = spec.get("inset", 0)  # 영역 가장자리(번짐 테두리 등)는 건드리지 않음
    if isinstance(ins, float):
        ix, iy = int((x1 - x0) * ins), int((y1 - y0) * ins)
    else:
        ix = iy = ins
    x0, y0, x1, y1 = x0 + ix, y0 + iy, x1 - ix, y1 - iy
    sub = arr[y0:y1, x0:x1]
    m = _mask(sub, spec.get("mask", "light"), spec.get("thresh"))
    full = np.zeros((H, W), bool)
    full[y0:y1, x0:x1] = m
    tb = spec.get("text_box") or (_bbox(full) or (x0, y0, x1, y1))
    if "text_inset" in spec:  # 글자 영역 = 이미지 전체에서 여백만큼 안쪽
        ti = spec["text_inset"]
        bw_, bh_ = bx1 - bx0, by1 - by0
        tx, ty = (int(bw_ * ti), int(bh_ * ti)) if isinstance(ti, float) else (ti, ti)
        tb = (bx0 + tx, by0 + ty, bx1 - tx, by1 - ty)
    fill = spec.get("fill")
    if fill is None:
        px = arr[full]
        fill = tuple(int(v) for v in np.median(px, axis=0)) if len(px) else (255, 255, 255, 255)
    fill = tuple(fill) + ((255,) if len(fill) == 3 else ())

    d = spec.get("dilate", 2)
    if full.any():
        mk = full.astype(np.uint8) * 255
        if d:
            mk = cv2.dilate(mk, np.ones((2 * d + 1, 2 * d + 1), np.uint8))
        if spec.get("mask") == "alpha":
            arr[mk > 0, 3] = 0
        elif spec.get("bg"):  # 단색으로 덮기
            arr[mk > 0] = tuple(spec["bg"]) + ((255,) if len(spec["bg"]) == 3 else ())
        else:
            rgb = cv2.inpaint(np.ascontiguousarray(arr[..., :3]), mk, 5, cv2.INPAINT_TELEA)
            al = cv2.inpaint(np.ascontiguousarray(arr[..., 3]), mk, 5, cv2.INPAINT_TELEA)
            arr[..., :3], arr[..., 3] = rgb, al
    out = Image.fromarray(arr)

    if spec.get("text"):
        bw, bh = tb[2] - tb[0], tb[3] - tb[1]
        if spec.get("grow"):  # 영역 확장 (한국어가 더 길 때)
            gx, gy = spec["grow"]
            bw, bh = min(W, bw + gx), min(H, bh + gy)
        stroke = spec.get("stroke")
        sw_ratio = spec.get("stroke_w", 0.0)
        if spec.get("bold") and stroke is None:  # 같은 색 외곽선으로 굵게
            stroke, sw_ratio = fill, spec["bold"]
        if stroke is not None:
            stroke = tuple(stroke) + ((255,) if len(stroke) == 3 else ())
        sy = spec.get("stretch_y", 1.0)  # 세로로 늘이기 (가늘고 긴 붓글씨 흉내)
        t = fit_text(spec["text"], spec.get("font", "brush"), bw, bh / sy, spec.get("layout", "h"),
                     fill, stroke, sw_ratio, spec.get("scale", 1.0))
        if sy != 1.0:
            t = t.resize((t.width, int(t.height * sy)), Image.LANCZOS)
        cx, cy = (tb[0] + tb[2]) / 2 + spec.get("dx", 0), (tb[1] + tb[3]) / 2 + spec.get("dy", 0)
        px, py = int(cx - t.width / 2), int(cy - t.height / 2)
        px, py = max(0, min(W - t.width, px)), max(0, min(H - t.height, py))
        if spec.get("glow"):  # 번지는 빛
            from PIL import ImageFilter
            r, gc = spec["glow"]
            g = Image.new("RGBA", (t.width + 4 * r, t.height + 4 * r), (0, 0, 0, 0))
            g.alpha_composite(t, (2 * r, 2 * r))
            a = g.getchannel("A").filter(ImageFilter.GaussianBlur(r))
            gl = Image.new("RGBA", g.size, tuple(gc[:3]) + (255,))
            gl.putalpha(a.point(lambda v: v * gc[3] // 255))
            out.alpha_composite(gl, (max(0, px - 2 * r), max(0, py - 2 * r)))
        if spec.get("shadow"):
            sx, sy, sc = spec["shadow"]
            sh = Image.new("RGBA", t.size, tuple(sc))
            sh.putalpha(t.getchannel("A").point(lambda v: v * sc[3] // 255))
            out.alpha_composite(sh, (px + sx, py + sy))
        out.alpha_composite(t, (px, py))
    return out
