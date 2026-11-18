"""줍쥐 데일리 특가 TOP 5 릴스 v2 (1080x1920, 30fps).

python make_reel_v2.py <spec.json> <media 폴더> <tts.mp3> <tts_timings.json> <bgm.mp3> <out.mp4>

레이아웃 (고정):
  상단 검정 밴드  : 날짜 / "10,000원 이하 꿀템" / "오늘의 특가 TOP 5"
  가운데 흰 영역  : 상품 이미지 박스(효과는 박스 안에서만) / TTS 자막 줄 / 요약 상품명 + 가격
  하단 검정 밴드  : ★프로필 링크 확인★ / 매일 업데이트
  (모바일 상단 UI에 날짜가 가리지 않도록 전체를 DY만큼 아래로 내림, 대표 지시 11/18)
"""
import json
import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
F = HERE / "fonts"
W, H, FPS = 1080, 1920, 30
BLACK, WHITE, LIME, YELLOW, INK, GRAY = (10, 10, 10), (255, 255, 255), (223, 255, 0), (255, 230, 0), (24, 24, 24), (238, 238, 238)
PURPLE = (102, 37, 232)

DOH = lambda s: ImageFont.truetype(str(F / "BMDoHyeon.ttf"), s)
PB = lambda s: ImageFont.truetype(str(F / "Pretendard-Bold.otf"), s)
PX = lambda s: ImageFont.truetype(str(F / "Pretendard-ExtraBold.otf"), s)

DY = 140                              # 전체 디자인을 아래로 내린 양
TOP_H, BOT_Y = 400 + DY, 1520 + DY
BOX = (60, 440 + DY, 1020, 1150 + DY)  # 상품 이미지 박스 (효과는 이 안에서만)
SUB_Y = 1218 + DY                     # 자막 줄 중심
NAME_Y = 1372 + DY                        # 요약 상품명 + 가격 중심


def fit_font(d, text, fn, size, maxw):
    while size > 24 and d.textlength(text, font=fn(size)) > maxw:
        size -= 2
    return fn(size)


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def base_layer(date_label):
    im = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(im)
    # 상단
    d.rectangle((0, 0, W, TOP_H), fill=BLACK)
    d.text((W / 2, 92 + DY), date_label, font=PB(46), fill=WHITE, anchor="mm")
    d.text((W / 2, 196 + DY), "10,000원 이하 꿀템", font=DOH(104), fill=LIME, anchor="mm")
    a, b = "오늘의 특가 ", "TOP 5"
    f = DOH(104)
    wa, wb = d.textlength(a, font=f), d.textlength(b, font=f)
    x0 = W / 2 - (wa + wb) / 2
    d.text((x0, 312 + DY), a, font=f, fill=WHITE, anchor="lm")
    d.text((x0 + wa, 312 + DY), b, font=f, fill=YELLOW, anchor="lm")
    # 하단
    d.rectangle((0, BOT_Y, W, H), fill=BLACK)
    d.text((W / 2, BOT_Y + 78), "★프로필 링크 확인★", font=PX(60), fill=WHITE, anchor="mm")
    d.text((W / 2, BOT_Y + 178), "매일 업데이트", font=DOH(84), fill=LIME, anchor="mm")
    return im


def load_src(path):
    im = Image.open(path).convert("RGB")
    im.thumbnail((1600, 1600))
    return im


def contain(src, bw, bh, scale=1.0):
    """박스 안에 상품 전체가 보이도록(contain) 맞춘 뒤 scale 배율."""
    s = min(bw / src.width, bh / src.height) * scale
    return src.resize((max(1, int(src.width * s)), max(1, int(src.height * s))), Image.BILINEAR)


def box_canvas():
    bw, bh = BOX[2] - BOX[0], BOX[3] - BOX[1]
    return Image.new("RGB", (bw, bh), WHITE), bw, bh


def paste_box(frame, canvas):
    bw, bh = canvas.size
    mask = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, bw - 1, bh - 1), 36, fill=255)
    frame.paste(canvas, (BOX[0], BOX[1]), mask)


EFFECTS = ["zoom_in", "pan", "zoom_out", "rise", "swing"]


def draw_product(frame, src, t, dur, effect):
    """t: 장면 경과 시간. 효과는 BOX 안에서만."""
    cv, bw, bh = box_canvas()
    p = min(1.0, t / max(dur, 0.1))
    enter = ease(t / 0.35)
    if effect == "zoom_in":
        im = contain(src, bw, bh, 0.92 + 0.22 * p)
        x, y = (bw - im.width) // 2, (bh - im.height) // 2
    elif effect == "zoom_out":
        im = contain(src, bw, bh, 1.25 - 0.3 * p)
        x, y = (bw - im.width) // 2, (bh - im.height) // 2
    elif effect == "pan":
        im = contain(src, bw, bh, 1.25)
        span = im.width - bw
        x = int(-span * p) if span > 0 else (bw - im.width) // 2
        y = (bh - im.height) // 2
    elif effect == "rise":
        im = contain(src, bw, bh, 1.0 + 0.1 * p)
        x = (bw - im.width) // 2
        y = (bh - im.height) // 2 + int((1 - enter) * bh * 0.6)
    else:  # swing: 살짝 흔들리며 확대
        im = contain(src, bw, bh, 0.95 + 0.12 * p)
        im = im.rotate(math.sin(t * 3.2) * 2.2, resample=Image.BICUBIC, expand=True, fillcolor=WHITE)
        x, y = (bw - im.width) // 2, (bh - im.height) // 2
    if effect != "rise":
        x += int((1 - enter) * bw * 0.5)  # 오른쪽에서 밀려 들어옴 (박스 안)
    cv.paste(im, (x, y))
    paste_box(frame, cv)


def draw_badge(frame, n, t):
    d = ImageDraw.Draw(frame)
    pop = ease((t - 0.15) / 0.25)
    if pop <= 0:
        return
    r = int(64 * (0.6 + 0.4 * pop))
    cx, cy = BOX[0] + 78, BOX[1] + 78
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=LIME, outline=BLACK, width=6)
    d.text((cx, cy + 3), str(n), font=DOH(int(r * 1.35)), fill=BLACK, anchor="mm")


def draw_intro(frame, srcs, t, dur):
    """인트로: 오늘의 5개 상품이 박스 안에서 가로로 흘러감 (롤링)."""
    cv, bw, bh = box_canvas()
    cell = int(bh * 0.78)
    gap = 40
    strip_w = (cell + gap) * len(srcs)
    offset = 30 - int((t / max(dur, 0.1)) * max(0, strip_w - bw))
    d = ImageDraw.Draw(cv)
    for i, s in enumerate(srcs):
        im = contain(s, cell, cell, 1.0)
        x = offset + i * (cell + gap) + (cell - im.width) // 2
        y = (bh - cell) // 2 + (cell - im.height) // 2
        cv.paste(im, (x, y))
        cx = offset + i * (cell + gap) + 46
        d.ellipse((cx - 38, (bh - cell) // 2 + 8, cx + 38, (bh - cell) // 2 + 84), fill=LIME, outline=BLACK, width=4)
        d.text((cx, (bh - cell) // 2 + 48), str(i + 1), font=DOH(56), fill=BLACK, anchor="mm")
    paste_box(frame, cv)


def draw_outro(frame, srcs, items, t):
    cv, bw, bh = box_canvas()
    d = ImageDraw.Draw(cv)
    cell = 280
    pos = [(30, 40), (340, 40), (650, 40), (185, 380), (495, 380)]
    for i, ((x, y), s, it) in enumerate(zip(pos, srcs, items), 1):
        a = ease((t - 0.07 * i) / 0.3)
        if a <= 0:
            continue
        im = contain(s, cell, cell - 20, 1.0)
        yy = y + int((1 - a) * 40)
        cv.paste(im, (x + (cell - im.width) // 2, yy + (cell - 20 - im.height) // 2))
        d.ellipse((x, yy, x + 70, yy + 70), fill=LIME, outline=BLACK, width=4)
        d.text((x + 35, yy + 38), str(i), font=DOH(50), fill=BLACK, anchor="mm")
        d.text((x + cell / 2, yy + cell + 6), f"{it['price']:,}원", font=DOH(40), fill=INK, anchor="mm")
    paste_box(frame, cv)


def draw_sub(frame, text):
    if not text:
        return
    d = ImageDraw.Draw(frame)
    f = fit_font(d, text, PB, 62, W - 170)
    tw = d.textlength(text, font=f)
    pad_x, h = 28, 92
    d.rounded_rectangle((W / 2 - tw / 2 - pad_x, SUB_Y - h / 2, W / 2 + tw / 2 + pad_x, SUB_Y + h / 2), 14, fill=BLACK)
    d.text((W / 2, SUB_Y + 2), text, font=f, fill=WHITE, anchor="mm")


def draw_name_price(frame, short, price):
    d = ImageDraw.Draw(frame)
    text = f"{short} {price:,}원"
    f = fit_font(d, text, DOH, 96, W - 120)
    d.text((W / 2, NAME_Y), text, font=f, fill=INK, anchor="mm")


def chunk_times(chunks, words):
    """말한 단어 타이밍을 자막 덩어리별 (시작, 끝)으로 묶음."""
    ws = [w for w in words if not w["text"].strip().startswith("[")]
    out, i = [], 0
    for c in chunks:
        n = len(c["spoken"].split())
        seg = ws[i:i + n]
        i += n
        if not seg:
            out.append(None)
            continue
        out.append((seg[0]["startSeconds"], seg[-1]["endSeconds"]))
    return out


def main(spec_path, media_dir, tts, timings_path, bgm, out):
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    media = Path(media_dir)
    prods = {p["id"]: p for p in json.loads((media / "products.json").read_text(encoding="utf-8"))["products"]}
    items = [{**it, "price": prods[it["id"]]["price"]} for it in spec["items"]]
    srcs = [load_src(media / "img" / f"{it['id']}.jpg") for it in items]

    words = json.loads(Path(timings_path).read_text(encoding="utf-8"))
    times = chunk_times(spec["chunks"], words)
    # 비어 있는 타이밍은 앞뒤로 보정
    for k, tm in enumerate(times):
        if tm is None:
            prev_end = times[k - 1][1] if k else 0
            times[k] = (prev_end, prev_end + 0.8)
    if tts.startswith("duration="):   # 음성 파일 없이 길이만 받아서 무음 영상 생성 (음성은 나중에 합성)
        total = float(tts.split("=", 1)[1])
    else:
        tts_len = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", tts]).strip())
        total = tts_len + 0.7

    # 장면 경계: 각 장면 첫 자막의 시작 시각
    scenes = []
    for c, tm in zip(spec["chunks"], times):
        if not scenes or scenes[-1][0] != c["scene"]:
            scenes.append([c["scene"], tm[0]])
    bounds = []
    for k, (sc, st) in enumerate(scenes):
        st = 0.0 if k == 0 else max(0.0, st - 0.12)
        en = scenes[k + 1][1] - 0.12 if k + 1 < len(scenes) else total
        bounds.append((sc, st, en))

    base = base_layer(spec["dateLabel"])
    n = int(total * FPS)
    tmp_video = str(Path(out).with_suffix(".video.mp4"))
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                           "-pix_fmt", "yuv420p", tmp_video], stdin=subprocess.PIPE)
    for fi in range(n):
        t = fi / FPS
        frame = base.copy()
        sc, st, en = next(((a, b, c) for a, b, c in bounds if b <= t < c), bounds[-1])
        lt, dur = t - st, en - st
        if sc == "intro":
            draw_intro(frame, srcs, lt, dur)
        elif sc == "outro":
            draw_outro(frame, srcs, items, lt)
        else:
            k = int(sc) - 1
            draw_product(frame, srcs[k], lt, dur, EFFECTS[k % len(EFFECTS)])
            draw_badge(frame, k + 1, lt)
            draw_name_price(frame, items[k]["short"], items[k]["price"])
        # 현재 자막 (말하는 동안 + 다음 자막 전까지 유지)
        cur = ""
        for idx, (c, tm) in enumerate(zip(spec["chunks"], times)):
            nxt = times[idx + 1][0] if idx + 1 < len(times) else total
            if (idx == 0 and t < nxt - 0.05) or (tm[0] - 0.05 <= t < nxt - 0.05):
                cur = c["display"]
        draw_sub(frame, cur)
        ff.stdin.write(frame.tobytes())
    ff.stdin.close()
    ff.wait()

    if tts.startswith("duration="):
        Path(tmp_video).replace(out)
        print(f"완료(무음): {out} ({total:.1f}초)")
        return
    # 오디오: TTS + 잔잔한 BGM(-20dB 안팎, 끝 페이드아웃) 믹스
    fade_st = max(0.0, total - 1.5)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp_video, "-i", tts, "-stream_loop", "-1", "-i", bgm,
                    "-filter_complex",
                    f"[2:a]volume=0.12,afade=t=in:d=0.6,afade=t=out:st={fade_st:.2f}:d=1.5,atrim=0:{total:.2f}[m];"
                    f"[1:a]apad,atrim=0:{total:.2f},volume=1.0[v];[v][m]amix=inputs=2:duration=first:normalize=0[a]",
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                    "-movflags", "+faststart", out], check=True)
    Path(tmp_video).unlink(missing_ok=True)
    print(f"완료: {out} ({total:.1f}초)")


if __name__ == "__main__":
    main(*sys.argv[1:7])
