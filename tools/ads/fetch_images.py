"""광고 이미지용 상품 사진 받기: 키워드별 쿠팡 검색 상위 상품 사진을 /tmp/adimg 에 저장 (키워드당 API 1회)."""
import json, os, re, sys, time, urllib.request
sys.path.insert(0, os.getcwd())
import update as U
out = "/tmp/adimg"; os.makedirs(out, exist_ok=True)
meta = []
for kw in sys.argv[1].split(","):
    kw = kw.strip()
    items = U.fetch_search(kw, os.environ["COUPANG_ACCESS_KEY"], os.environ["COUPANG_SECRET_KEY"])
    for i, it in enumerate(items[:6], 1):
        url = re.sub(r"/thumbnails/remote/\d+x\d+ex/", "/thumbnails/remote/1000x1000ex/", it.get("productImage", ""))
        try:
            data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=15).read()
            fn = f"{kw.replace(' ', '_')}_{i}.jpg"
            open(f"{out}/{fn}", "wb").write(data)
            meta.append({"file": fn, "kw": kw, "name": it.get("productName"), "price": it.get("productPrice")})
        except Exception as e:
            print("실패", kw, i, e)
    time.sleep(2)
json.dump(meta, open(f"{out}/meta.json", "w"), ensure_ascii=False, indent=1)
print(len(meta), "장 저장")
