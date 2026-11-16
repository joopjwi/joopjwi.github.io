"""오늘 후보 목록: TOP 100 중 최근 6일 릴스에 나온 상품은 빼고 보여준다.
python candidates.py <media 폴더> <site/data/reels/index.json> <오늘 YYYY-MM-DD>"""
import json, sys
from datetime import date, timedelta
media, idx_path, today = sys.argv[1:4]
d = json.load(open(f"{media}/products.json", encoding="utf-8"))
try:
    idx = json.load(open(idx_path, encoding="utf-8"))
except FileNotFoundError:
    idx = []
cut = (date.fromisoformat(today) - timedelta(days=6)).isoformat()
used = {i for x in idx if cut <= x["date"] < today for i in x["ids"]}
print("데이터 확인 시각:", d.get("checkedAt"), "/ 최근 6일 사용:", len(used), "개 제외")
for p in d["products"]:
    if p["id"] in used:
        continue
    tag = "매일" if p.get("everyday") else ("궁금" if p.get("curious") else "-")
    print(p["rank"], p["id"], p["group"], f'{p["price"]:,}원', tag, p.get("kw") or p.get("sub"), "|", p["name"])
