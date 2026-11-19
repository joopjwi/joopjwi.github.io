"""해외 원본 쇼츠(원본 작업실)용 오디오 생성 — 회원님 ElevenLabs 계정 사용.

python make_audio.py <request.json> <출력 폴더>
환경변수: ELEVENLABS_API_KEY
- 나레이션: tools/reels/tts_eleven.py 재사용 (쉼 0.2초 커트 + 단어 타이밍)
- 효과음: request["sfx"] = [{"name", "prompt", "seconds"}]
- BGM: request["music"] = {"prompt", "seconds"} (실패해도 계속 진행, status.json에 기록)
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "reels"))
import tts_eleven  # noqa: E402

KEY = os.environ.get("ELEVENLABS_API_KEY", "")


def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"xi-api-key": KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def main(req_path, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    spec = json.load(open(req_path, encoding="utf-8"))
    status = {"id": spec["id"], "tts": "pending", "sfx": {}, "music": "skipped"}

    tts_eleven.main(req_path, str(out))
    status["tts"] = "ok"

    for s in spec.get("sfx", []):
        try:
            audio = post("https://api.elevenlabs.io/v1/sound-generation?output_format=mp3_44100_128",
                         {"text": s["prompt"], "duration_seconds": s.get("seconds", 1.0),
                          "prompt_influence": s.get("influence", 0.5)})
            (out / f"sfx_{s['name']}.mp3").write_bytes(audio)
            status["sfx"][s["name"]] = "ok"
        except Exception as e:  # noqa: BLE001
            status["sfx"][s["name"]] = f"error: {getattr(e, 'code', '')} {str(e)[:200]}"

    m = spec.get("music")
    if m:
        try:
            audio = post("https://api.elevenlabs.io/v1/music?output_format=mp3_44100_128",
                         {"prompt": m["prompt"], "music_length_ms": int(m.get("seconds", 40) * 1000),
                          "force_instrumental": True})
            (out / "bgm.mp3").write_bytes(audio)
            status["music"] = "ok"
        except urllib.error.HTTPError as e:
            status["music"] = f"error {e.code}: {e.read().decode(errors='ignore')[:300]}"
        except Exception as e:  # noqa: BLE001
            status["music"] = f"error: {str(e)[:300]}"

    json.dump(status, open(out / "status.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(status, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:3])
