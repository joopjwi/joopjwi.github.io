"""줍쥐 데일리 TOP 5 쇼츠 생성기 (1080x1920, 30fps).

사용: python make_reel.py <spec.json> <media 폴더> <출력.mp4>
  spec.json  : dateLabel, items[{id, hook, name}] (5개)
  media 폴더 : products.json + img/<id>.jpg (GitHub media 브랜치)
가격·링크는 spec이 아니라 products.json(그날 아침 확인값)에서 읽는다.
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
F = HERE / "fonts"
W, H, FPS = 1080, 1920, 30
PER_ITEM, OUTRO = 3.2, 2.4
LIME, PUR, DEEP, WHITE, LAV, INK = (223, 255, 0), (102, 37, 232), (43, 21, 80), (255, 255, 255), (244, 241, 250), (32, 32, 32)

def font(name, size):
    return ImageFont.truetype(str(F / name), size)

JAL = lambda s: font("yg-jalnan-normal.woff", s)
PB = lambda s: font("Pretendard-Bold.otf", s)
PX = lambda s: font("Pretendard-ExtraBold.otf", s)
PK = lambda s: font("Pretendard-Black.otf", s)
PS = lambda s: font("Pretendard-SemiBold.otf", s)


def jal_text(d, xy, text, size, fill, anchor_center=False):
    """잘난체엔 공백 글리프가 없어서 단어 단위로 그림."""
    f = JAL(size)
    gap = int(size * 0.28)
    words = text.split(" ")
    widths = [d.textlength(w, font=f) for w in words]
    total = sum(widths) + gap * (len(words) - 1)
    x, y = xy
    if anchor_center:
        x = x - total / 2
    for w, wd in zip(words, widths):
        d.text((x, y), w, font=f, fill=fill)
        x += wd + gap
    return total


def jal_width(d, text, size):
    f = JAL(size)
    ws = text.split(" ")
    return sum(d.textlength(w, font=f) for w in ws) + int(size * 0.28) * (len(ws) - 1)


def fit(d, text, fn, size, maxw):
    while size > 20 and d.textlength(text, font=fn(size)) > maxw:
        size -= 2
    return fn(size)


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def base_layer(date_label):
    """모든 프레임 공통 배경 (상단 자막, 제목, 하단 CTA)."""
    im = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(im)
    # 1) 최상단 자막
    d.rectangle((0, 0, W, 150), fill=DEEP)
    t = "1만원 이하 득템 매일 업데이트"
    d.text((W / 2, 88), t, font=PX(54), fill=LIME, anchor="mm")
    # 2) 두 번째 제목
    d.rectangle((0, 150, W, 430), fill=LIME)
    d.text((W / 2, 214), date_label, font=PK(52), fill=DEEP, anchor="mm")
    size = 116
    while size > 60 and jal_width(d, "놓치면 안 됨 TOP 5", size) > W - 110:
        size -= 2
    jal_text(d, (W / 2, 250 + (116 - size) // 2), "놓치면 안 됨 TOP 5", size, PUR, anchor_center=True)
    # 하단 CTA
    d.rectangle((0, 1500, W, H), fill=DEEP)
    d.rounded_rectangle((90, 1528, W - 90, 1648), 60, fill=LIME)
    d.text((W / 2, 1590), "프로필 링크에서 득템하세요", font=PK(56), fill=DEEP, anchor="mm")
    d.text((W / 2, 1700), "영상 속 번호로 찾아쥐!", font=PB(40), fill=WHITE, anchor="mm")
    d.text((W / 2, 1770), "쿠팡 파트너스 활동으로 일정액의 수수료를 제공받습니다", font=PS(26), fill=(190, 178, 220), anchor="mm")
    return im


def product_canvas(img_path):
    src = Image.open(img_path).convert("RGB")
    src.thumbnail((1400, 1400))
    return src


def draw_item(frame, it, idx, t, src):
    """t: 이 상품 구간 내 경과 시간(초)."""
    d = ImageDraw.Draw(frame)
    box = (110, 455, 970, 1145)  # 이미지 영역 860x690
    bw, bh = box[2] - box[0], box[3] - box[1]
    # 사진: 살짝 줌인 + 등장 슬라이드
    z = 1.0 + 0.07 * (t / PER_ITEM)
    cover = max(bw / src.width, bh / src.height) * z
    rs = src.resize((int(src.width * cover), int(src.height * cover)), Image.BILINEAR)
    cx, cy = (rs.width - bw) // 2, (rs.height - bh) // 2
    crop = rs.crop((cx, cy, cx + bw, cy + bh))
    slide = int((1 - ease(t / 0.35)) * 260)
    mask = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, bw, bh), 40, fill=255)
    shadow = Image.new("RGBA", (bw + 60, bh + 60), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((30, 40, bw + 30, bh + 40), 40, fill=(43, 21, 80, 70))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    frame.paste(shadow, (box[0] - 30 + slide, box[1] - 30), shadow)
    frame.paste(crop, (box[0] + slide, box[1]), mask)
    # 번호 배지
    pop = ease((t - 0.2) / 0.25)
    if pop > 0:
        r = int(78 * (0.6 + 0.4 * pop))
        bx, by = box[0] + 70 + slide, box[1] + 70
        d.ellipse((bx - r, by - r, bx + r, by + r), fill=LIME, outline=DEEP, width=6)
        d.text((bx, by + 2), str(idx), font=PK(int(r * 1.15)), fill=DEEP, anchor="mm")
    # 자막
    a = ease((t - 0.25) / 0.3)
    if a > 0:
        dy = int((1 - a) * 30)
        hook = it["hook"]
        f = fit(d, hook, PK, 66, W - 120)
        d.text((W / 2, 1210 + dy), hook, font=f, fill=INK, anchor="mm")
        nf = fit(d, it["name"], PS, 38, W - 160)
        d.text((W / 2, 1290 + dy), it["name"], font=nf, fill=(95, 88, 115), anchor="mm")
        price = f"{it['price']:,}원"
        pw = d.textlength(price, font=PK(96))
        px = W / 2 - pw / 2
        d.rounded_rectangle((px - 30, 1340 + dy, px + pw + 30, 1462 + dy), 30, fill=PUR)
        d.text((W / 2, 1402 + dy), price, font=PK(96), fill=WHITE, anchor="mm")


def draw_outro(frame, items, srcs, t):
    d = ImageDraw.Draw(frame)
    d.rectangle((0, 430, W, 1500), fill=LAV)
    jal_text(d, (W / 2, 470), "번호로 찾아쥐!", 84, DEEP, anchor_center=True)
    cell = 270
    pos = [(90, 600), (405, 600), (720, 600), (247, 990), (562, 990)]
    for i, ((x, y), it, s) in enumerate(zip(pos, items, srcs), 1):
        a = ease((t - 0.08 * i) / 0.3)
        if a <= 0:
            continue
        th = s.copy()
        sc = max(cell / th.width, cell / th.height)
        th = th.resize((int(th.width * sc), int(th.height * sc)))
        th = th.crop(((th.width - cell) // 2, (th.height - cell) // 2, (th.width - cell) // 2 + cell, (th.height - cell) // 2 + cell))
        m = Image.new("L", (cell, cell), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, cell, cell), 28, fill=255)
        yy = y + int((1 - a) * 40)
        frame.paste(th, (x, yy), m)
        d.ellipse((x - 14, yy - 14, x + 66, yy + 66), fill=LIME, outline=DEEP, width=5)
        d.text((x + 26, yy + 27), str(i), font=PK(48), fill=DEEP, anchor="mm")
        d.text((x + cell / 2, yy + cell + 40), f"{it['price']:,}원", font=PK(42), fill=PUR, anchor="mm")


def main(spec_path, media_dir, out):
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    media = Path(media_dir)
    prods = {p["id"]: p for p in json.loads((media / "products.json").read_text(encoding="utf-8"))["products"]}
    items = []
    for it in spec["items"]:
        p = prods[it["id"]]
        items.append({**it, "price": p["price"], "url": p["url"], "fullName": p["name"]})
    srcs = [product_canvas(media / "img" / f"{it['id']}.jpg") for it in items]
    base = base_layer(spec["dateLabel"])
    total = PER_ITEM * len(items) + OUTRO
    n = int(total * FPS)
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-shortest", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)
    for f in range(n):
        t = f / FPS
        frame = base.copy()
        k = int(t // PER_ITEM)
        if k < len(items):
            lt = t - k * PER_ITEM
            if k == 0:
                lt = max(lt, 0.7) if lt < 0.7 else lt  # 첫 장면은 애니메이션 없이 바로 완성
            draw_item(frame, items[k], k + 1, lt, srcs[k])
        else:
            draw_outro(frame, items, srcs, t - PER_ITEM * len(items))
        ff.stdin.write(frame.tobytes())
    ff.stdin.close()
    ff.wait()
    # 캡션(인스타 본문) 초안 + 상품 링크 목록
    lines = ["[광고] 쿠팡 파트너스 활동으로 일정액의 수수료를 제공받습니다.", "",
             f"{spec['dateLabel']} 놓치면 안 됨 TOP 5 🐭", "1만원 이하 득템, 매일 업데이트해요!", ""]
    lines += [f"{i}. {it['name']} {it['price']:,}원" for i, it in enumerate(items, 1)]
    lines += ["", "👉 프로필 링크에서 번호로 찾아쥐!", f"(가격은 {spec.get('checkedAt', '')} 기준, 쿠팡에서 바뀔 수 있어요)", "",
              "#줍쥐 #만원이하 #득템 #쿠팡추천템 #생활꿀템 #살림템 #가성비템"]
    Path(out).with_suffix(".txt").write_text("\n".join(lines), encoding="utf-8")
    print("완료:", out, f"{total:.1f}초")


if __name__ == "__main__":
    main(*sys.argv[1:4])
