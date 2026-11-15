"""오천픽 - 쿠팡파트너스 5천원 이하 인기템 TOP 100 자동 갱신 스크립트.

GitHub Actions에서 매일 실행된다. 필요한 환경변수(Secrets):
  COUPANG_ACCESS_KEY, COUPANG_SECRET_KEY
선택:
  COUPANG_SUB_ID (채널 구분용 subId, 기본값 ochunpick)
  MAX_PRICE (기본 5000)

결과물:
  site/data/products.json  - 사이트가 읽는 오늘의 TOP 100
  site/data/history.json   - 상품별 일자별 가격 기록 (최대 180일)
"""
import hashlib
import hmac
import json
import os
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

DOMAIN = "https://api-gateway.coupang.com"
BEST_PATH = "/v2/providers/affiliate_open_api/apis/openapi/v1/products/bestcategories/{cid}"

# 쿠팡파트너스 카테고리 ID -> (사이트 그룹, 세부 분류)
CATEGORIES = {
    1012: ("식품", "식품"),
    1024: ("식품", "건강식품"),
    1014: ("생필품", "생활용품"),
    1011: ("생필품", "출산·유아"),
    1010: ("생필품", "뷰티·위생"),
    1013: ("주방·수납", "주방"),
    1015: ("주방·수납", "인테리어·수납"),
    1021: ("문구·취미", "문구·오피스"),
    1020: ("문구·취미", "완구·취미"),
    1018: ("기타", "차량용품"),
    1029: ("기타", "반려동물"),
}

# 화면에 보이는 순서 + 그룹별 기본 자리 수 (합계 100)
GROUP_QUOTA = {
    "식품": 25,
    "생필품": 25,
    "주방·수납": 20,
    "문구·취미": 15,
    "기타": 15,
}
GROUP_ORDER = list(GROUP_QUOTA)

MAX_PRICE = int(os.environ.get("MAX_PRICE", "5000"))
SUB_ID = os.environ.get("COUPANG_SUB_ID", "ochunpick")
TOP_N = 100
HISTORY_DAYS = 180

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "site" / "data"
KST = timezone(timedelta(hours=9))


def auth_header(method: str, path: str, query: str, access: str, secret: str) -> str:
    signed_date = time.strftime("%y%m%dT%H%M%SZ", time.gmtime())
    message = signed_date + method + path + query
    signature = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return (
        f"CEA algorithm=HmacSHA256, access-key={access}, "
        f"signed-date={signed_date}, signature={signature}"
    )


def fetch_best(cid: int, access: str, secret: str) -> list:
    path = BEST_PATH.format(cid=cid)
    query = f"limit=100&subId={SUB_ID}"
    req = urllib.request.Request(
        f"{DOMAIN}{path}?{query}",
        headers={
            "Authorization": auth_header("GET", path, query, access, secret),
            "Content-Type": "application/json;charset=UTF-8",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        body = json.loads(res.read().decode("utf-8"))
    if str(body.get("rCode")) != "0":
        raise RuntimeError(f"{cid}: {body.get('rMessage')}")
    return body.get("data") or []


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def score(item: dict) -> float:
    """카테고리 내 순위를 0~1 점수로 바꾸고, 가격 하락 상품에 가산점."""
    s = 1 - (item["rank"] - 1) / 100
    if item.get("drop_pct", 0) > 0:
        s += min(item["drop_pct"], 30) / 100
    return s


def main():
    access = os.environ["COUPANG_ACCESS_KEY"]
    secret = os.environ["COUPANG_SECRET_KEY"]
    today = datetime.now(KST).strftime("%Y-%m-%d")

    history = load_json(DATA / "history.json", {})
    seen = {}

    for cid, (group, label) in CATEGORIES.items():
        try:
            items = fetch_best(cid, access, secret)
        except Exception as e:  # 한 카테고리 실패해도 나머지는 진행
            print("실패:", e)
            continue
        for it in items:
            price = int(it.get("productPrice") or 0)
            if price <= 0 or price > MAX_PRICE:
                continue
            pid = str(it["productId"])
            if pid in seen:
                continue
            seen[pid] = {
                "id": pid,
                "name": it.get("productName", ""),
                "price": price,
                "image": it.get("productImage", ""),
                "url": it.get("productUrl", ""),
                "rocket": bool(it.get("isRocket")),
                "freeShip": bool(it.get("isFreeShipping")),
                "category": group,
                "sub": label,
                "rank": int(it.get("rank") or 100),
            }
        time.sleep(1)  # API 호출 간격

    # 가격 기록 갱신 + 뱃지 계산
    cutoff = (datetime.now(KST) - timedelta(days=HISTORY_DAYS)).strftime("%Y-%m-%d")
    for pid, p in seen.items():
        h = history.setdefault(pid, {})
        h[today] = p["price"]
        past = {d: v for d, v in h.items() if d < today}
        if past:
            prev = past[max(past)]
            low = min(past.values())
            p["prevPrice"] = prev
            p["drop_pct"] = round((prev - p["price"]) / prev * 100) if prev > p["price"] else 0
            p["allTimeLow"] = p["price"] <= low
        else:
            p["drop_pct"] = 0
            p["allTimeLow"] = False
        p["days"] = len(h)
    for pid in list(history):
        history[pid] = {d: v for d, v in history[pid].items() if d >= cutoff}
        if not history[pid]:
            del history[pid]

    # 그룹별로 인기순 정렬 후 정해진 자리 수만큼 뽑고, 모자라면 남은 인기 상품으로 채움
    by_group = {g: sorted([p for p in seen.values() if p["category"] == g], key=score, reverse=True)
                for g in GROUP_ORDER}
    picked = []
    for g in GROUP_ORDER:
        picked += by_group[g][:GROUP_QUOTA[g]]
    if len(picked) < TOP_N:
        ids = {p["id"] for p in picked}
        rest = sorted([p for p in seen.values() if p["id"] not in ids], key=score, reverse=True)
        picked += rest[:TOP_N - len(picked)]

    # 최종 순서: 그룹 순서(식품 → 생필품 → ...) 안에서 인기순
    ranked = []
    for g in GROUP_ORDER:
        items = sorted([p for p in picked if p["category"] == g], key=score, reverse=True)
        for i, p in enumerate(items, 1):
            p["top"] = i
        ranked += items

    DATA.mkdir(parents=True, exist_ok=True)
    out = {
        "updatedAt": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "maxPrice": MAX_PRICE,
        "groups": GROUP_ORDER,
        "products": ranked,
    }
    (DATA / "products.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    (DATA / "history.json").write_text(json.dumps(history, ensure_ascii=False), encoding="utf-8")
    print(f"완료: {len(ranked)}개 상품 ({today})")


if __name__ == "__main__":
    main()
