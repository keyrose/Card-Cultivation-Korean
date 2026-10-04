"""이미지 한글화 미리보기: python preview_images.py <번들 상대경로> <출력.png> [이름 필터...]"""
import sys

import UnityPy
from PIL import Image, ImageDraw

import image_specs
from common import SA_DIR, original, read_dat


def specs_for(bundle):
    return image_specs.LOCALIZATION if "Localization" in bundle else image_specs.BY_BUNDLE.get(bundle, {})


def main(bundle, out, *flt):
    data, _ = read_dat(original("StreamingAssets/" + bundle))
    env = UnityPy.load(data)
    specs = specs_for(bundle)
    pairs = []
    for o in env.objects:
        if o.type.name != "Texture2D":
            continue
        n = o.peek_name()
        if n not in specs or (flt and not any(f in n for f in flt)):
            continue
        img = o.read().image.convert("RGBA")
        new = image_specs.apply(img, specs[n])
        pairs.append((n, img, new))
    T = 150
    sheet = Image.new("RGB", (T * 4, (T + 16) * len(pairs)), (120, 120, 120))
    d = ImageDraw.Draw(sheet)
    for i, (n, a, b) in enumerate(pairs):
        for j, (im, bg) in enumerate([(a, (120, 120, 120)), (b, (120, 120, 120)), (b, (30, 30, 30)), (b, (235, 225, 200))]):
            r = min(T / im.width, T / im.height); t = im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)
            cell = Image.new("RGBA", (T, T), bg + (255,)); cell.alpha_composite(t, ((T - t.width) // 2, (T - t.height) // 2))
            sheet.paste(cell.convert("RGB"), (j * T, i * (T + 16)))
        d.text((2, i * (T + 16) + T), n, fill=(255, 255, 0))
    sheet.save(out)
    print(len(pairs), "→", out)


if __name__ == "__main__":
    main(*sys.argv[1:])
