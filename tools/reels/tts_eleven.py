"""회원님 ElevenLabs 계정으로 TTS 생성 + 문장 사이 쉼을 0.2초로 커트 + 단어 타이밍 생성.

python tts_eleven.py <request.json> <출력 폴더>
환경변수: ELEVENLABS_API_KEY
출력: tts.mp3 (커트 완료), words.json (단어별 시작·끝, 커트 반영), tts_meta.json
"""
import base64
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

MAX_GAP = 0.2      # 글자 사이 쉼(정적)이 이보다 길면 이 길이로 줄임
LEAD, TAIL = 0.05, 0.35


def call_eleven(text, voice_id, settings, model):
    key = os.environ["ELEVENLABS_API_KEY"]
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps?output_format=mp3_44100_128"
    body = json.dumps({"text": text, "model_id": model, "voice_settings": settings}).encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"xi-api-key": key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"ElevenLabs 오류 {e.code}: {e.read().decode()[:400]}")


def main(req_path, out_dir):
    spec = json.load(open(req_path, encoding="utf-8"))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    text = " ".join(c["spoken"] for c in spec["chunks"])
    tts = spec.get("tts", {})
    voice = tts.get("voiceId", "vn80HZNY7EsdYzoFRYZm")
    model = tts.get("model", "eleven_multilingual_v2")
    settings = tts.get("voiceSettings", {"stability": 0.45, "similarity_boost": 0.8, "style": 0.25,
                                         "use_speaker_boost": True, "speed": 1.08})
    res = call_eleven(text, voice, settings, model)
    raw = out / "tts_raw.mp3"
    raw.write_bytes(base64.b64decode(res["audio_base64"]))
    al = res.get("normalized_alignment") or res["alignment"]
    chars, st, en = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                         "-of", "csv=p=0", str(raw)]).strip())

    # 1) 잘라낼 정적 구간 찾기 (두 가지를 합침)
    #  - 글자 타이밍: 문장부호(?!.,…)는 말소리가 아니므로 제외하고, 글자 사이 간격
    #  - 실제 파형: -38dB 이하 무음 구간
    PUNCT = set(" \t\n.,!?…·~\"'()[]")
    idx = [i for i, ch in enumerate(chars) if ch not in PUNCT]
    gaps = [(en[a], st[b]) for a, b in zip(idx, idx[1:]) if st[b] - en[a] > MAX_GAP]
    sd = subprocess.run(["ffmpeg", "-i", str(raw), "-af", f"silencedetect=n=-38dB:d={MAX_GAP}", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    s0 = None
    for line in sd.splitlines():
        if "silence_start:" in line:
            s0 = float(line.split("silence_start:")[1].split()[0])
        elif "silence_end:" in line and s0 is not None:
            gaps.append((s0, float(line.split("silence_end:")[1].split()[0])))
            s0 = None
    first, last = st[idx[0]], en[idx[-1]]
    gaps = sorted((max(a, first), min(b, last)) for a, b in gaps if b > first and a < last)
    merged = []
    for a, b in gaps:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    keep, cur = [], max(0.0, first - LEAD)
    for a, b in merged:
        if b - a > MAX_GAP:
            keep.append((cur, a + MAX_GAP / 2))
            cur = b - MAX_GAP / 2
    keep.append((cur, min(dur, last + TAIL)))

    def remap(t):
        """원본 시각 -> 커트 후 시각"""
        acc = 0.0
        for s, e in keep:
            if t < s:
                return acc
            if t <= e:
                return acc + (t - s)
            acc += e - s
        return acc

    # 2) ffmpeg로 남길 구간만 이어 붙임 (이음새에 5ms 페이드로 '틱' 소리 방지)
    parts = "".join(
        f"[0:a]atrim={s:.3f}:{e:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.005,afade=t=out:st={max(0, e - s - 0.005):.3f}:d=0.005[a{i}];"
        for i, (s, e) in enumerate(keep))
    concat = "".join(f"[a{i}]" for i in range(len(keep))) + f"concat=n={len(keep)}:v=0:a=1[out]"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-filter_complex", parts + concat,
                    "-map", "[out]", "-c:a", "libmp3lame", "-b:a", "192k", str(out / "tts.mp3")], check=True)

    # 3) 단어 타이밍 (공백 기준 단어 = 대본 spoken 단어)
    words, cur = [], None
    for i, ch in enumerate(chars):
        if ch.strip():
            if cur is None:
                cur = {"text": "", "s": st[i], "e": en[i]}
            cur["text"] += ch
            cur["e"] = en[i]
        elif cur is not None:
            words.append(cur)
            cur = None
    if cur is not None:
        words.append(cur)
    wj = [{"text": w["text"], "startSeconds": round(remap(w["s"]), 3), "endSeconds": round(remap(w["e"]), 3)} for w in words]
    json.dump(wj, open(out / "words.json", "w", encoding="utf-8"), ensure_ascii=False)
    new_dur = sum(e - s for s, e in keep)
    expected = len(text.split())
    meta = {"rawDuration": round(dur, 2), "duration": round(new_dur, 2), "cuts": len(keep) - 1,
            "words": len(wj), "expectedWords": expected, "voiceId": voice, "model": model}
    json.dump(meta, open(out / "tts_meta.json", "w"), ensure_ascii=False, indent=1)
    print("TTS:", meta)
    if len(wj) != expected:
        print("주의: 단어 수가 대본과 달라 자막 타이밍이 조금 어긋날 수 있음")


if __name__ == "__main__":
    main(*sys.argv[1:3])
