"""완성본을 원본 작업실 '완성본' 탭에 올린다.

python publish_done.py <영상.mp4> <meta.json>
meta.json: {"id","category","name","ytTitle","ytDesc","source"(선택)}
studio-done 브랜치(영상·표지·done.json, 최근 30개 유지)에 올리고 사이트 재배포를 요청한다.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = "https://github.com/joopjwi/joopjwi.github.io"
KEEP = 30


def sh(*a, cwd=None, check=True):
    return subprocess.run(a, cwd=cwd, check=check, capture_output=True, text=True)


def main(video, meta_path):
    meta = json.load(open(meta_path, encoding="utf-8"))
    vid = meta["id"]
    work = Path(tempfile.mkdtemp())
    if sh("git", "clone", "-q", "--depth", "1", "-b", "studio-done", REPO, str(work / "d"), check=False).returncode:
        (work / "d").mkdir()
    d = work / "d"
    shutil.copy(video, d / f"{vid}.mp4")
    sh("ffmpeg", "-v", "error", "-y", "-ss", "1.5", "-i", video, "-frames:v", "1", "-vf", "scale=360:-1", "-q:v", "4", str(d / f"{vid}.jpg"))
    dur = float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video).stdout)
    man = d / "done.json"
    items = json.load(open(man, encoding="utf-8"))["items"] if man.exists() else []
    items = [i for i in items if i["id"] != vid]
    now = datetime.now(timezone(timedelta(hours=9)))
    items.append({**meta, "video": f"done/{vid}.mp4", "poster": f"done/{vid}.jpg", "fileName": f"{meta['name']}.mp4",
                  "duration": round(dur), "date": now.strftime("%m/%d"), "createdAt": now.isoformat(timespec="seconds")})
    items.sort(key=lambda i: i["createdAt"], reverse=True)
    for old in items[KEEP:]:
        for ext in ("mp4", "jpg"):
            (d / f"{old['id']}.{ext}").unlink(missing_ok=True)
    items = items[:KEEP]
    json.dump({"items": items}, open(man, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    shutil.rmtree(d / ".git", ignore_errors=True)
    sh("git", "init", "-q", "-b", "studio-done", cwd=d)
    sh("git", "add", "-A", cwd=d)
    sh("git", "-c", "user.name=joopjwi", "-c", "user.email=joopjwi@users.noreply.github.com", "commit", "-qm", f"완성본 {vid}", cwd=d)
    sh("git", "push", "-fq", REPO, "studio-done", cwd=d)
    sh("gh", "api", "-X", "POST", "repos/joopjwi/joopjwi.github.io/actions/workflows/update.yml/dispatches",
       "-f", "ref=main", "-f", "inputs[build_only]=true")
    print(f"올림: {vid} ({len(items)}개 보관) → 재배포 요청")


if __name__ == "__main__":
    main(*sys.argv[1:3])
