#!/usr/bin/env bash
# GitHub Actions에서 실행: 요청 JSON 하나로 음성 → 커트 → 영상 → 표지까지 만든다.
# 사용: build_reel.sh <request.json> <media 폴더> <출력 폴더>
set -euo pipefail
REQ="$1"; MEDIA="$2"; OUT="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"
DATE=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['date'])" "$REQ")
BGM_URL=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('bgmUrl','https://cdn.creativeclaw.co/u/8e4a1e1b/audio/ac8109bd-e1e8-46eb-8c15-5c80989d68a4.mp3'))" "$REQ")
mkdir -p "$OUT" /tmp/reelwork
curl -sSfL -o /tmp/reelwork/bgm.mp3 "$BGM_URL"
python3 "$HERE/tts_eleven.py" "$REQ" /tmp/reelwork
python3 "$HERE/make_reel_v2.py" "$REQ" "$MEDIA" /tmp/reelwork/tts.mp3 /tmp/reelwork/words.json /tmp/reelwork/bgm.mp3 "$OUT/$DATE.mp4"
python3 "$HERE/make_cover.py" "$REQ" "$MEDIA" "$OUT/$DATE.jpg"
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT/$DATE.mp4")
python3 - "$OUT/$DATE.json" "$DATE" "$DUR" /tmp/reelwork/tts_meta.json <<'PY'
import json, sys
out, date, dur, meta = sys.argv[1:5]
m = json.load(open(meta))
json.dump({"date": date, "status": "ok", "duration": round(float(dur), 2), "tts": m,
           "video": f"https://joopjwi.github.io/reels/{date}.mp4",
           "cover": f"https://joopjwi.github.io/reels/{date}.jpg"}, open(out, "w"), ensure_ascii=False, indent=1)
PY
echo "완료: $OUT/$DATE.mp4 (${DUR}초)"
