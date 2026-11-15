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

# 다이소 느낌에 맞는 카테고리 (쿠팡파트너스 카테고리 ID)
CATEGORIES = {
    1013: "주방",
    1014: "생활",
    1015: "인테리어·수납",
    1021: "문구·오피스",
    1010: "뷰티",
    1018: "차량용품",
    1029: "반려동물",
    1020: "완구·취미",
}

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

    for cid, label in CATEGORIES.items():
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
                "category": label,
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

    ranked = sorted(seen.values(), key=score, reverse=True)[:TOP_N]
    for i, p in enumerate(ranked, 1):
        p["top"] = i

    DATA.mkdir(parents=True, exist_ok=True)
    out = {
        "updatedAt": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "maxPrice": MAX_PRICE,
        "products": ranked,
    }
    (DATA / "products.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    (DATA / "history.json").write_text(json.dumps(history, ensure_ascii=False), encoding="utf-8")
    print(f"완료: {len(ranked)}개 상품 ({today})")


if __name__ == "__main__":
    main()
