"""음성 길이(초)와 자막 덩어리로 단어별 타이밍을 추정한다 (음절 수 비례 + 문장 끝 쉼).
python est_timings.py <spec.json> <음성 길이 초> <out.json>"""
import json, re, sys

def syl(s):
    return len(re.findall(r"[가-힣0-9A-Za-z]", s))

def pause(s):
    s = s.strip()
    return 0.34 if s[-1] in "!?." else (0.16 if s[-1] == "," else 0.06)

def main(spec_path, total, out):
    total = float(total)
    ch = json.load(open(spec_path, encoding="utf-8"))["chunks"]
    lead, tail = 0.12, 0.35
    S = sum(syl(c["spoken"]) for c in ch)
    P = sum(pause(c["spoken"]) for c in ch[:-1])
    r = (total - lead - tail - P) / S
    t, words = lead, []
    for c in ch:
        for tk in c["spoken"].split():
            d = syl(tk) * r
            words.append({"text": tk, "startSeconds": t, "endSeconds": t + d})
            t += d + 0.02
        t += pause(c["spoken"]) - 0.02
    k = (total - tail) / words[-1]["endSeconds"]
    for w in words:
        w["startSeconds"] = round(w["startSeconds"] * k, 3)
        w["endSeconds"] = round(w["endSeconds"] * k, 3)
    json.dump(words, open(out, "w", encoding="utf-8"), ensure_ascii=False)
    print("timings:", len(words), "words, last end", words[-1]["endSeconds"])

if __name__ == "__main__":
    main(*sys.argv[1:4])
