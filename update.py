"""줍쥐(JOOPJWI) - 쿠팡파트너스 1만원 이하 인기템 TOP 100 자동 갱신.

GitHub Actions에서 매일 실행된다. 필요한 환경변수(Secrets):
  COUPANG_ACCESS_KEY, COUPANG_SECRET_KEY
선택:
  COUPANG_SUB_ID (채널 구분용 subId, 기본값 joopjwi)
  MAX_PRICE (기본 10000)

만드는 파일 (site/data/):
  products.json  - 오늘의 TOP 100 (사이트가 읽음)
  top5.json      - 오늘의 TOP 5 (홈페이지와 릴스가 같이 쓰는 단일 데이터)
  history.json   - 상품별 일자별 가격 기록 (최대 180일)
  catalog.json   - 한 번이라도 TOP 100에 올랐던 상품 정보 (개별 페이지용)
  ranks.json     - 일자별 TOP 100 순위 기록
  picks/         - 오늘 이건 줍쥐! (데일리 픽) 데이터

순위 기준(사이트에도 안내):
  쿠팡 카테고리 베스트 순위(쿠팡 API 제공)를 점수로 바꾸고,
  어제보다 가격이 내린 상품에 하락률만큼 가산점(최대 0.3),
  식품·간식/생필품에 소폭 가산점(0.08)을 더한 '줍쥐 인기순'.
  판매량·리뷰 수는 API가 주지 않으므로 쓰지 않는다.
"""
import concurrent.futures as cf
import hashlib
import hmac
import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

DOMAIN = "https://api-gateway.coupang.com"
BEST_PATH = "/v2/providers/affiliate_open_api/apis/openapi/v1/products/bestcategories/{cid}"

# 쿠팡파트너스 카테고리 ID -> (줍쥐 탭, 세부 분류)  [베스트 API 1회씩]
CATEGORIES = {
    1012: ("식품·간식", "식품"),
    1024: ("식품·간식", "건강식품"),
    1014: ("생필품", "생활용품"),
    1011: ("생필품", "출산·유아"),
    1013: ("주방·살림", "주방용품"),
    1015: ("청소·수납", "홈인테리어"),
    1016: ("디지털·차량", "가전디지털"),
    1018: ("디지털·차량", "자동차용품"),
    1010: ("뷰티·패션", "뷰티"),
    1001: ("뷰티·패션", "패션"),
    1019: ("도서", "도서"),
    1020: ("문구·취미", "완구·취미"),
    1021: ("문구·취미", "문구·오피스"),
    1017: ("문구·취미", "스포츠·레저"),
    1029: ("반려동물", "반려동물"),
}

# 키워드 검색 API (1회 최대 10개). 매일 쓰는 템은 고정+순환, 궁금한 템은 순환.
EVERYDAY_FIXED = [("물티슈", "생필품"), ("생수", "식품·간식")]
EVERYDAY_POOL = [
    ("삼다수", "식품·간식"), ("화장지", "생필품"), ("키친타월", "주방·살림"), ("세탁세제", "청소·수납"),
    ("칫솔", "생필품"), ("치약", "생필품"), ("쓰레기봉투", "생필품"), ("주방세제", "주방·살림"),
    ("즉석밥", "식품·간식"), ("라면", "식품·간식"), ("샴푸", "뷰티·패션"), ("핸드크림", "뷰티·패션"),
    ("건전지", "디지털·차량"), ("섬유유연제", "청소·수납"),
]
CURIOUS_POOL = [
    "아이디어 상품", "자취 꿀템", "신기한 생활용품", "정리 꿀템", "주방 꿀템", "욕실 꿀템",
    "차량 꿀템", "캠핑 꿀템", "사무실 꿀템", "겨울 꿀템", "다용도 정리함", "틈새 수납",
]
EVERYDAY_PER_DAY, CURIOUS_PER_DAY = 2, 4   # 고정 2 + 순환 2 + 궁금 4 = 검색 8회
SEARCH_PATH = "/v2/providers/affiliate_open_api/apis/openapi/v1/products/search"

# 생활용품 중 청소·수납 성격이 뚜렷한 상품은 청소·수납 탭으로 옮김 (상품명 기준)
CLEAN_RE = re.compile(r"수납|정리함|정리대|청소|걸레|밀대|먼지|클리너|선반|바구니|후크|행거|옷걸이|제습|탈취|빗자루|물티슈 케이스|틈새")

# 탭 순서 + 그룹별 기본 자리 수 (합계 100). '오늘의 득템'은 사이트에서 조건으로 묶는 탭이라 여기엔 없음.
GROUP_QUOTA = {
    "식품·간식": 15,
    "생필품": 15,
    "신기한템": 14,
    "주방·살림": 10,
    "청소·수납": 9,
    "디지털·차량": 8,
    "뷰티·패션": 9,
    "도서": 8,
    "문구·취미": 7,
    "반려동물": 5,
}
GROUP_ORDER = list(GROUP_QUOTA)
GROUP_BONUS = {"식품·간식": 0.08, "생필품": 0.08}
EVERYDAY_BONUS, CURIOUS_BONUS = 0.12, 0.10
API_COOLDOWN_MIN = 65   # 직전 API 실행 후 이 시간 안에는 다시 호출하지 않음 (시간당 30회 제한 보호)
PICK_GROUPS = {"식품·간식", "생필품", "주방·살림", "청소·수납", "신기한템"}

MAX_PRICE = int(os.environ.get("MAX_PRICE", "10000"))
SUB_ID = os.environ.get("COUPANG_SUB_ID", "joopjwi")
TOP_N = 100
HISTORY_DAYS = 180
PICK_COOLDOWN_DAYS = 7

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "site" / "data"
KST = timezone(timedelta(hours=9))

RANKING_RULE = (
    "줍쥐 인기순은 쿠팡이 제공하는 카테고리별 베스트 순위와 키워드 검색 순위를 기본으로, "
    "매일 쓰는 템(물티슈·생수 등)과 궁금한 꿀템, 어제보다 가격이 내린 상품, 식품·생필품에 가산점을 더해 "
    "매일 아침 자동으로 정해요. 판매량이나 리뷰 수는 반영하지 않아요."
)


# ---------- 쿠팡 API ----------
def auth_header(method, path, query, access, secret):
    signed_date = time.strftime("%y%m%dT%H%M%SZ", time.gmtime())
    message = signed_date + method + path + query
    signature = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return (f"CEA algorithm=HmacSHA256, access-key={access}, "
            f"signed-date={signed_date}, signature={signature}")


def call_api(path, query, access, secret):
    req = urllib.request.Request(
        f"{DOMAIN}{path}?{query}",
        headers={"Authorization": auth_header("GET", path, query, access, secret),
                 "Content-Type": "application/json;charset=UTF-8"},
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        body = json.loads(res.read().decode("utf-8"))
    if str(body.get("rCode")) != "0":
        raise RuntimeError(f"{path}: {body.get('rMessage')}")
    return body.get("data")


def fetch_best(cid, access, secret):
    return call_api(BEST_PATH.format(cid=cid), f"limit=100&subId={SUB_ID}", access, secret) or []


def fetch_search(keyword, access, secret):
    q = "keyword=" + urllib.parse.quote(keyword) + f"&limit=10&subId={SUB_ID}"
    data = call_api(SEARCH_PATH, q, access, secret) or {}
    items = data.get("productData") if isinstance(data, dict) else data
    return items or []


def todays_keywords(day_index):
    """요일·날짜에 따라 순환. 매일 쓰는 템 고정 2 + 순환 2, 궁금한 템 4."""
    ev = [EVERYDAY_POOL[(day_index * EVERYDAY_PER_DAY + i) % len(EVERYDAY_POOL)] for i in range(EVERYDAY_PER_DAY)]
    cu = [CURIOUS_POOL[(day_index * CURIOUS_PER_DAY + i) % len(CURIOUS_POOL)] for i in range(CURIOUS_PER_DAY)]
    return EVERYDAY_FIXED + ev, cu


# ---------- 검증 ----------
def image_ok(url):
    if not url or not url.startswith("http"):
        return False
    try:
        req = urllib.request.Request(url, headers={"Range": "bytes=0-0", "User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as res:
            return res.status in (200, 206) and res.headers.get("Content-Type", "").startswith("image")
    except Exception:
        return False


def valid_item(it):
    try:
        price = int(it.get("productPrice") or 0)
    except (TypeError, ValueError):
        return False
    url = it.get("productUrl") or ""
    return (0 < price <= MAX_PRICE and (it.get("productName") or "").strip()
            and url.startswith("https://link.coupang.com/"))


# ---------- 유틸 ----------
def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, obj, indent=1):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=indent), encoding="utf-8")


def score(p):
    s = 1 - (p["catRank"] - 1) / 100
    s += min(p.get("dropPct", 0), 30) / 100
    s += GROUP_BONUS.get(p["group"], 0)
    if p.get("everyday"):
        s += EVERYDAY_BONUS
    if p.get("curious"):
        s += CURIOUS_BONUS
    return round(s, 4)


def template_pick(p, today):
    """AI 카피가 아직 없을 때 쓰는 사실 기반 기본 문구. 확인된 정보만 사용."""
    points = [f"쿠팡 {p['sub']} 베스트 {p['catRank']}위"]
    if p.get("dropPct"):
        points.append(f"어제보다 {p['dropPct']}% 내린 가격")
    if p.get("rocket"):
        points.append("로켓배송 상품")
    return {
        "date": today, "id": p["id"], "copySource": "template",
        "title": "이게 만원도 안 한다고?",
        "story": f"오늘 줍쥐 TOP 100에서 고른 {p['group']} 상품이에요. "
                 f"쿠팡 {p['sub']} 카테고리 베스트 {p['catRank']}위에 올라 있어요.",
        "points": points[:3],
        "name": p["name"], "price": p["price"], "image": p["image"], "url": p["url"],
        "group": p["group"], "sub": p["sub"], "rocket": p["rocket"], "freeShip": p["freeShip"],
        "checkedAt": p["checkedAt"],
    }


def main():
    access = os.environ["COUPANG_ACCESS_KEY"]
    secret = os.environ["COUPANG_SECRET_KEY"]
    now = datetime.now(KST)
    today = now.strftime("%Y-%m-%d")
    checked_at = now.strftime("%Y-%m-%d %H:%M")

    history = load_json(DATA / "history.json", {})
    catalog = load_json(DATA / "catalog.json", {})
    ranks = load_json(DATA / "ranks.json", {})
    # 순위 변동·신규 진입은 '오늘 이전 가장 최근 날짜'의 순위 기록과 비교 (같은 날 재실행해도 안전)
    prev_days = sorted(d for d in ranks if d < today)
    prev_rank = ranks[prev_days[-1]] if prev_days else {}

    # 0) 호출 제한 보호: 직전 API 실행 후 65분 안이면 이번엔 건너뜀
    state = load_json(DATA / "api_state.json", {})
    last = state.get("lastApiRun")
    if last:
        last_dt = datetime.fromisoformat(last)
        if (now - last_dt).total_seconds() < API_COOLDOWN_MIN * 60:
            print(f"직전 API 실행({last}) 후 {API_COOLDOWN_MIN}분이 안 지나서 이번엔 갱신을 건너뜀")
            return
    calls = 0

    # 1) 수집 + 기본 검증 + 중복 제거
    seen = {}

    def add(it, group, sub, extra=None):
        if not valid_item(it):
            return
        pid = str(it["productId"])
        name = it["productName"].strip()
        if pid in seen:
            if extra:  # 같은 상품이 검색에도 나오면 표시만 추가
                seen[pid].update(extra)
            return
        g = group
        if group == "생필품" and CLEAN_RE.search(name):
            g = "청소·수납"
        seen[pid] = {
            "id": pid, "name": name, "price": int(it["productPrice"]),
            "image": it.get("productImage", ""), "url": it["productUrl"],
            "rocket": bool(it.get("isRocket")), "freeShip": bool(it.get("isFreeShipping")),
            "group": g, "sub": sub, "catRank": int(it.get("rank") or 100),
            "checkedAt": checked_at, **(extra or {}),
        }

    day_index = (now.date() - datetime(2026, 1, 1).date()).days
    everyday_kw, curious_kw = todays_keywords(day_index)
    for kw, group in everyday_kw:
        try:
            calls += 1
            for i, it in enumerate(fetch_search(kw, access, secret), 1):
                it.setdefault("rank", i)
                add(it, group, kw, {"everyday": True, "kw": kw})
        except Exception as e:
            print("검색 실패:", kw, e)
        time.sleep(1.5)
    for kw in curious_kw:
        try:
            calls += 1
            for i, it in enumerate(fetch_search(kw, access, secret), 1):
                it.setdefault("rank", i)
                add(it, "신기한템", kw, {"curious": True, "kw": kw})
        except Exception as e:
            print("검색 실패:", kw, e)
        time.sleep(1.5)

    for cid, (group, sub) in CATEGORIES.items():
        try:
            calls += 1
            items = fetch_best(cid, access, secret)
        except Exception as e:
            print("카테고리 실패:", e)
            continue
        for it in items:
            add(it, group, sub)
        time.sleep(1)
    save_json(DATA / "api_state.json", {"lastApiRun": now.isoformat(), "calls": calls,
                                         "keywords": [k for k, _ in everyday_kw] + curious_kw})
    print(f"API 호출 {calls}회 / 수집: {len(seen)}개 (가격 {MAX_PRICE}원 이하)")

    # 2) 이미지 유효성 확인 (확인 자체가 대부분 실패하면 네트워크 문제로 보고 거르지 않음)
    with cf.ThreadPoolExecutor(16) as ex:
        results = dict(zip(seen, ex.map(lambda p: image_ok(p["image"]), seen.values())))
    ok_ratio = sum(results.values()) / max(len(results), 1)
    if ok_ratio >= 0.5:
        bad = [pid for pid, ok in results.items() if not ok]
        for pid in bad:
            del seen[pid]
        print(f"이미지 확인 실패로 제외: {len(bad)}개")
    else:
        print(f"이미지 확인 성공률 {ok_ratio:.0%} - 확인 단계 건너뜀")

    # 3) 가격 기록 + 하락률 (실제 이전 기록이 있을 때만)
    for pid, p in seen.items():
        h = history.setdefault(pid, {})
        past = {d: v for d, v in h.items() if d < today}
        h[today] = p["price"]
        p["firstSeen"] = min(h)
        if past:
            last_day = max(past)
            prev_price = past[last_day]
            p["prevPrice"], p["prevPriceDate"] = prev_price, last_day
            p["dropPct"] = round((prev_price - p["price"]) / prev_price * 100) if prev_price > p["price"] else 0
            # 기록이 7일 이상 쌓였을 때만 '기록상 최저가' 표시
            p["allTimeLow"] = len(past) >= 6 and p["price"] < min(past.values())
        else:
            p["dropPct"], p["allTimeLow"] = 0, False
        p["days"] = len(h)
        p["score"] = score(p)

    # 4) 그룹별 자리 배분 후 전체 순위
    by_group = {g: sorted([p for p in seen.values() if p["group"] == g], key=lambda x: -x["score"])
                for g in GROUP_ORDER}
    picked = [p for g in GROUP_ORDER for p in by_group[g][:GROUP_QUOTA[g]]]
    if len(picked) < TOP_N:
        ids = {p["id"] for p in picked}
        rest = sorted([p for p in seen.values() if p["id"] not in ids], key=lambda x: -x["score"])
        picked += rest[:TOP_N - len(picked)]
    ranked = sorted(picked, key=lambda x: -x["score"])
    has_prev = bool(prev_rank)
    for i, p in enumerate(ranked, 1):
        p["rank"] = i
        p["prevRank"] = prev_rank.get(p["id"]) if has_prev else None
        p["isNew"] = has_prev and p["id"] not in prev_rank

    # 5) TOP 5: 상위 순서대로, 같은 탭은 최대 2개 (릴스와 공유)
    top5, per_group = [], {}
    for p in ranked:
        if per_group.get(p["group"], 0) >= 2:
            continue
        top5.append(p)
        per_group[p["group"]] = per_group.get(p["group"], 0) + 1
        if len(top5) == 5:
            break
    top5_ids = [p["id"] for p in top5]

    # 6) 데일리 픽: 오늘 파일이 없을 때만 후보를 정해 기본 문구로 생성 (AI 카피가 나중에 덮어씀)
    picks_dir = DATA / "picks"
    pick_index = load_json(picks_dir / "index.json", [])
    if not (picks_dir / f"{today}.json").exists():
        cutoff = (now - timedelta(days=PICK_COOLDOWN_DAYS)).strftime("%Y-%m-%d")
        recent = {x["id"] for x in pick_index if x["date"] >= cutoff}
        cands = [p for p in ranked if p["group"] in PICK_GROUPS and p["id"] not in recent] or ranked
        pick = template_pick(cands[0], today)
        save_json(picks_dir / f"{today}.json", pick)
        pick_index = [x for x in pick_index if x["date"] != today]
        pick_index.insert(0, {"date": today, "id": pick["id"], "title": pick["title"]})
        save_json(picks_dir / "index.json", pick_index)

    # 7) 기록 정리 + 저장
    cutoff_hist = (now - timedelta(days=HISTORY_DAYS)).strftime("%Y-%m-%d")
    for pid in list(history):
        history[pid] = {d: v for d, v in history[pid].items() if d >= cutoff_hist}
        if not history[pid]:
            del history[pid]
    for p in ranked:
        catalog[p["id"]] = {k: p[k] for k in ("name", "image", "url", "group", "sub", "rocket", "freeShip")}
        catalog[p["id"]]["lastSeen"] = today
    pick_ids = {x["id"] for x in pick_index}
    for pid in list(catalog):
        if pid not in history and pid not in pick_ids:
            del catalog[pid]
    ranks[today] = {p["id"]: p["rank"] for p in ranked}
    ranks = {d: v for d, v in ranks.items() if d >= cutoff_hist}

    out = {
        "brand": "줍쥐", "checkedAt": checked_at, "date": today, "maxPrice": MAX_PRICE,
        "groups": GROUP_ORDER, "rankingRule": RANKING_RULE,
        "top5": top5_ids, "products": ranked,
    }
    save_json(DATA / "products.json", out)
    save_json(DATA / "top5.json", {
        "date": today, "checkedAt": checked_at,
        "note": "홈페이지 TOP 5와 릴스가 함께 쓰는 데이터. 품절 여부는 API로 확인할 수 없어 게시 전 쿠팡 페이지 확인이 필요함.",
        "items": [{
            "rank": i, "id": p["id"], "name": p["name"], "price": p["price"], "image": p["image"],
            "url": p["url"], "group": p["group"], "sub": p["sub"], "rocket": p["rocket"],
            "freeShip": p["freeShip"], "selectedDate": today,
            "hold": False, "holdReasons": [], "stockChecked": False,
        } for i, p in enumerate(top5, 1)],
    })
    save_json(DATA / "history.json", history, indent=None)
    save_json(DATA / "catalog.json", catalog, indent=None)
    save_json(DATA / "ranks.json", ranks, indent=None)
    print(f"완료: TOP {len(ranked)} / TOP5 {len(top5)} ({checked_at})")


if __name__ == "__main__":
    main()
