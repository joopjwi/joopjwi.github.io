"""인스타 릴스 표지: "<M월 D일> 득템하쥐" + 오늘의 5개 상품.
python make_cover.py <spec.json> <media 폴더> <out.jpg>"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

F = Path(__file__).resolve().parent / "fonts"
DOH = lambda s: ImageFont.truetype(str(F / "BMDoHyeon.ttf"), s)
LIME, PUR, BLACK, WHITE = (223, 255, 0), (102, 37, 232), (10, 10, 10), (255, 255, 255)

def main(spec_path, media_dir, out):
    spec = json.load(open(spec_path, encoding="utf-8"))
    md = spec["dateLabel"].split(" (")[0]  # "11월 16일 (월)" -> "11월 16일"
    W, H = 1080, 1920
    im = Image.new("RGB", (W, H), LIME); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 250), fill=BLACK); d.rectangle((0, H - 250, W, H), fill=BLACK)
    d.text((W / 2, 135), "10,000원 이하 꿀템 TOP 5", font=DOH(76), fill=LIME, anchor="mm")
    d.text((W / 2, H - 130), "프로필 링크에서 번호로 줍쥐!", font=DOH(64), fill=WHITE, anchor="mm")
    d.text((W / 2, 470), md, font=DOH(150), fill=BLACK, anchor="mm")
    f = DOH(250)
    for dx, dy in [(-8, 0), (8, 0), (0, -8), (0, 8), (-6, -6), (6, 6), (-6, 6), (6, -6)]:
        d.text((W / 2 + dx, 690 + dy), "득템하쥐", font=f, fill=BLACK, anchor="mm")
    d.text((W / 2, 690), "득템하쥐", font=f, fill=PUR, anchor="mm")
    cell, gap = 300, 30
    pos = [(W / 2 - cell * 1.5 - gap, 920), (W / 2 - cell / 2, 920), (W / 2 + cell / 2 + gap, 920),
           (W / 2 - cell - gap / 2, 920 + cell + gap), (W / 2 + gap / 2, 920 + cell + gap)]
    for i, (it, (x, y)) in enumerate(zip(spec["items"], pos), 1):
        src = Image.open(Path(media_dir) / "img" / f"{it['id']}.jpg").convert("RGB")
        s = max(cell / src.width, cell / src.height)
        src = src.resize((int(src.width * s), int(src.height * s)))
        src = src.crop(((src.width - cell) // 2, (src.height - cell) // 2, (src.width - cell) // 2 + cell, (src.height - cell) // 2 + cell))
        m = Image.new("L", (cell, cell), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, cell - 1, cell - 1), 30, fill=255)
        d.rounded_rectangle((x - 6, y - 6, x + cell + 6, y + cell + 6), 34, fill=BLACK)
        im.paste(src, (int(x), int(y)), m)
        d.ellipse((x - 10, y - 10, x + 70, y + 70), fill=LIME, outline=BLACK, width=5)
        d.text((x + 30, y + 32), str(i), font=DOH(54), fill=BLACK, anchor="mm")
    im.save(out, quality=92)
    print("cover:", out)

if __name__ == "__main__":
    main(*sys.argv[1:4])
