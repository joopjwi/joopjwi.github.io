"""줍쥐 특가 단톡용 - 가격 하락 / 최근 5일 최저가 상품 찾기.

update.py(TOP 100)와 별도로 돌고, 같은 시간대에 API를 몰아 쓰지 않도록
GitHub Actions에서 update 작업이 끝나고 65분 뒤에 실행된다.

기준
  - 식품·생활용품 위주 + 겨울 계절템 + 전자기기(아이폰·갤럭시 등)
  - 문구·도서·완구·패션 제외
  - 가격 상한: 일반 10만원, 전자기기 200만원
  - 호출 수: 베스트 8회 + 검색 10회 = 18회

만드는 파일
  site/data/deals/history.json  상품별 일자별 가격 (vendorItemId 포함, 90일)
  site/data/deals/<날짜>.json    오늘 특가 목록
  site/data/deals/latest.json
  site/deals/index.html          단톡에 붙여 넣을 메시지 + 복사 버튼 (검색 노출 안 함)
"""
import html
import json
import os
import re
import time
import urllib.parse
from datetime import datetime, timedelta

import update as U

MAX_NORMAL = 100_000
MAX_DIGITAL = 2_000_000
HIST_DAYS = 90
DROP_MIN, DROP_MAX = 10, 70   # 10% 미만은 특가로 안 봄, 70% 초과는 옵션 바뀜 등 오류 가능성이 커서 제외

# 쿠팡 카테고리 베스트 (각 100개)
CATS = {
    1012: ("식품", False), 1024: ("식품", False),
    1014: ("생활용품", False), 1011: ("생활용품", False),
    1013: ("주방·살림", False), 1015: ("생활용품", False),
    1016: ("전자기기", True), 1029: ("반려동물", False),
}
# 검색 (각 10개): 고정 4 + 순환 6
FIXED_KW = [("핫팩", "겨울템", False), ("온풍기", "겨울템", True),
            ("아이폰", "전자기기", True), ("갤럭시", "전자기기", True)]
POOL_KW = [
    ("전기요", "겨울템", True), ("가습기", "겨울템", True), ("전기장판", "겨울템", True),
    ("난방텐트", "겨울템", False), ("귤", "식품", False), ("에어팟", "전자기기", True),
    ("갤럭시 버즈", "전자기기", True), ("아이패드", "전자기기", True), ("갤럭시탭", "전자기기", True),
    ("애플워치", "전자기기", True), ("생수", "식품", False), ("화장지", "생활용품", False),
    ("세탁세제", "생활용품", False), ("기저귀", "생활용품", False), ("쌀", "식품", False),
    ("계란", "식품", False), ("커피믹스", "식품", False), ("라면", "식품", False),
    ("닭가슴살", "식품", False), ("물티슈", "생활용품", False), ("수면양말", "겨울템", False),
    ("제습제", "생활용품", False), ("로봇청소기", "전자기기", True), ("무선청소기", "전자기기", True),
]
POOL_PER_DAY = 6
EXCLUDE_RE = re.compile(r"볼펜|연필|노트|다이어리|스티커|테이프|포스트잇|형광펜|문구|필통|색연필|크레파스|"
                        r"스케치북|완구|장난감|레고|퍼즐|도서|책|교재|케이스|필름|보호필름|거치대|스트랩")
SEASON_RE = re.compile(r"핫팩|온풍|히터|전기요|전기장판|난방|가습기|수면양말|담요|내복|발열|손난로|문풍지|뽁뽁이")
ORDER = ["식품", "생활용품", "겨울템", "주방·살림", "전자기기", "반려동물"]

DATA = U.DATA / "deals"
PAGE = U.ROOT / "site" / "deals" / "index.html"


def item_key(url):
    m = re.search(r"vendorItemId=(\d+)", url or "")
    return m.group(1) if m else ""


def won(n):
    return f"{n:,}원"


def main():
    access, secret = os.environ["COUPANG_ACCESS_KEY"], os.environ["COUPANG_SECRET_KEY"]
    now = datetime.now(U.KST)
    today = now.strftime("%Y-%m-%d")
    hist = U.load_json(DATA / "history.json", {})
    main_hist = U.load_json(U.DATA / "history.json", {})   # TOP 100 쪽 1만원 이하 기록도 참고
    seen = {}

    def add(it, group, digital, src):
        try:
            price = int(it.get("productPrice") or 0)
        except (TypeError, ValueError):
            return
        name = (it.get("productName") or "").strip()
        url = it.get("productUrl") or ""
        cap = MAX_DIGITAL if digital else MAX_NORMAL
        if not (0 < price <= cap and name and url.startswith("https://link.coupang.com/")):
            return
        if EXCLUDE_RE.search(name) and not SEASON_RE.search(name):
            return
        if group == "전자기기" and price < 10_000:   # 전자기기 칸에서 소모품·액세서리는 제외
            return
        g = "겨울템" if SEASON_RE.search(name) else group
        pid = str(it["productId"])
        if pid in seen:
            return
        seen[pid] = {"id": pid, "name": name, "price": price, "url": url, "vid": item_key(url),
                     "image": it.get("productImage", ""), "group": g, "src": src,
                     "rocket": bool(it.get("isRocket")), "freeShip": bool(it.get("isFreeShipping")),
                     "rank": int(it.get("rank") or 100)}

    calls = 0
    day_index = (now.date() - datetime(2026, 1, 1).date()).days
    kws = FIXED_KW + [POOL_KW[(day_index * POOL_PER_DAY + i) % len(POOL_KW)] for i in range(POOL_PER_DAY)]
    for kw, group, digital in kws:
        try:
            calls += 1
            for i, it in enumerate(U.fetch_search(kw, access, secret), 1):
                it.setdefault("rank", i)
                add(it, group, digital, kw)
        except Exception as e:
            print("검색 실패:", kw, e)
        time.sleep(1.5)
    for cid, (group, digital) in CATS.items():
        try:
            calls += 1
            for it in U.fetch_best(cid, access, secret):
                add(it, group, digital, f"best{cid}")
        except Exception as e:
            print("베스트 실패:", cid, e)
        time.sleep(1)
    print(f"API 호출 {calls}회 / 수집 {len(seen)}개")
    if len(seen) < 50:
        raise SystemExit(f"수집 상품이 {len(seen)}개뿐이라 중단")

    state = U.load_json(U.DATA / "api_state.json", {})
    state["lastDealsRun"] = now.isoformat()
    state["dealsCalls"] = calls
    U.save_json(U.DATA / "api_state.json", state)

    drops, lows = [], []
    for pid, p in seen.items():
        h = hist.setdefault(pid, {})
        past = {d: v for d, v in h.items() if d < today}
        # 같은 판매 옵션(vendorItemId)의 기록만 비교. 옵션 정보가 없는 TOP 100 기록은 보조로만 씀
        same = {d: v["p"] for d, v in past.items() if v.get("v") in ("", p["vid"])}
        for d, price in main_hist.get(pid, {}).items():
            if d < today and d not in same:
                same[d] = price
        h[today] = {"p": p["price"], "v": p["vid"]}
        if not same:
            continue
        last_day = max(same)
        gap = (datetime.fromisoformat(today) - datetime.fromisoformat(last_day)).days
        prev = same[last_day]
        if gap <= 3 and prev > p["price"]:
            pct = round((prev - p["price"]) / prev * 100)
            if DROP_MIN <= pct <= DROP_MAX:
                drops.append({**p, "prev": prev, "prevDate": last_day, "dropPct": pct})
        start = (now.date() - timedelta(days=4)).isoformat()   # 오늘 포함 최근 5일
        window = {d: v for d, v in same.items() if d >= start}
        if len(window) >= 2 and p["price"] < min(window.values()):
            lows.append({**p, "days": {**window, today: p["price"]},
                         "lowGap": min(window.values()) - p["price"]})

    cutoff = (now.date() - timedelta(days=HIST_DAYS)).isoformat()
    for pid in list(hist):
        hist[pid] = {d: v for d, v in hist[pid].items() if d >= cutoff}
        if not hist[pid]:
            del hist[pid]
    U.save_json(DATA / "history.json", hist, indent=None)

    gorder = {g: i for i, g in enumerate(ORDER)}
    drops.sort(key=lambda x: (-x["dropPct"], gorder.get(x["group"], 9)))
    drop_ids = {d["id"] for d in drops[:8]}
    lows = [l for l in lows if l["id"] not in drop_ids]
    lows.sort(key=lambda x: (gorder.get(x["group"], 9), -x["lowGap"]))
    pick_drops = balance(drops, 8)
    pick_lows = balance(lows, 5)

    out = {"date": today, "checkedAt": now.strftime("%Y-%m-%d %H:%M"), "calls": calls,
           "collected": len(seen), "drops": pick_drops, "lows": pick_lows,
           "allDrops": len(drops), "allLows": len(lows), "keywords": [k for k, _, _ in kws]}
    U.save_json(DATA / f"{today}.json", out)
    U.save_json(DATA / "latest.json", out)
    msg = message(out, now)
    (DATA / f"{today}.txt").write_text(msg, encoding="utf-8")
    write_page(msg, out)
    print(msg)


def balance(items, n, per_group=3):
    """한 분류가 몰리지 않게 분류당 최대 3개."""
    out, cnt = [], {}
    for it in items:
        if cnt.get(it["group"], 0) >= per_group:
            continue
        cnt[it["group"]] = cnt.get(it["group"], 0) + 1
        out.append(it)
        if len(out) >= n:
            break
    return out


def short(name, n=28):
    name = re.sub(r"\s+", " ", name)
    return name if len(name) <= n else name[:n].rstrip() + "…"


def message(o, now):
    md = f"{now.month}월 {now.day}일"
    lines = [f"🐭 {md} 줍쥐 특가", ""]
    if o["drops"]:
        lines.append("📉 어제보다 가격 내린 템")
        for i, d in enumerate(o["drops"], 1):
            tag = " ❄️" if d["group"] == "겨울템" else ""
            lines += [f"{i}. {short(d['name'])}{tag}",
                      f"   {won(d['prev'])} → {won(d['price'])} (↓{d['dropPct']}%)",
                      f"   {d['url']}", ""]
    if o["lows"]:
        lines.append("🔻 최근 5일 중 가장 싼 날")
        for i, d in enumerate(o["lows"], 1):
            lines += [f"{i}. {short(d['name'])}",
                      f"   오늘 {won(d['price'])} (기록 {len(d['days'])}일 중 최저)",
                      f"   {d['url']}", ""]
    if not o["drops"] and not o["lows"]:
        lines += ["오늘은 크게 내린 상품이 없어요. 내일 다시 알려드릴게요!", ""]
    lines += [f"※ {o['checkedAt']} 기준 가격이라 바뀔 수 있어요.",
              "※ 쿠팡 파트너스 활동으로 수수료를 받을 수 있어요."]
    return "\n".join(lines)


def write_page(msg, o):
    PAGE.parent.mkdir(parents=True, exist_ok=True)
    PAGE.write_text(f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow">
<title>줍쥐 특가 단톡 {o['date']}</title>
<style>body{{font-family:-apple-system,sans-serif;background:#2B1550;color:#fff;margin:0;padding:16px}}
h1{{font-size:18px;color:#DFFF00}}p{{font-size:13px;opacity:.8}}
textarea{{width:100%;height:65vh;box-sizing:border-box;border-radius:12px;padding:12px;font-size:14px}}
button{{width:100%;margin-top:12px;padding:16px;border:0;border-radius:12px;background:#DFFF00;color:#2B1550;font-size:17px;font-weight:800}}</style>
</head><body><h1>🐭 {o['date']} 단톡 메시지</h1>
<p>하락 {o['allDrops']}개 · 5일 최저 {o['allLows']}개 중 골랐어요 (수집 {o['collected']}개)</p>
<textarea id="t">{html.escape(msg)}</textarea>
<button onclick="navigator.clipboard.writeText(document.getElementById('t').value).then(()=>this.textContent='복사됐어요 ✅')">전체 복사</button>
</body></html>""", encoding="utf-8")


if __name__ == "__main__":
    main()
