"""줍쥐 정적 페이지 생성기.

site/data/*.json 을 읽어서 만든다 (쿠팡 API 호출 없음 → 언제 돌려도 안전):
  site/p/<상품ID>.html   상품 상세 페이지 (한 번이라도 TOP 100에 오른 상품)
  site/pick/<날짜>.html  오늘 이건 줍쥐! 단독 게시물
  site/sitemap.xml, site/robots.txt
"""
import html
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"
DATA = SITE / "data"
BASE = os.environ.get("SITE_URL", "https://joopjwi.github.io").rstrip("/")
INSTA = "https://www.instagram.com/joopjwi/"
DISCLOSURE = "이 사이트는 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
e = html.escape


def load(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def won(n):
    return f"{int(n):,}원"


def ship(p):
    parts = []
    if p.get("rocket"):
        parts.append("로켓배송")
    if p.get("freeShip"):
        parts.append("무료배송")
    return " · ".join(parts)


def head(title, desc, url, image, depth=1):
    up = "../" * depth
    return f"""<!DOCTYPE html>
<html lang="ko"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title><meta name="description" content="{e(desc)}"><meta name="theme-color" content="#6625E8">
<meta property="og:type" content="article"><meta property="og:site_name" content="줍쥐">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:image" content="{e(image or BASE + '/assets/og.png')}"><meta property="og:url" content="{e(url)}">
<meta name="twitter:card" content="summary_large_image"><link rel="canonical" href="{e(url)}">
<link rel="icon" href="{up}assets/favicon.png">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/pretendard@1.3.9/dist/web/static/pretendard-dynamic-subset.css">
<link rel="stylesheet" href="{up}assets/style.css"><script src="{up}config.js"></script>
<script>function loadScript(a){{var b=document.getElementsByTagName("head")[0],c=document.createElement("script");c.type="text/javascript",c.src="https://tracker.metricool.com/app/resources/be.js",c.onreadystatechange=a,c.onload=a,b.appendChild(c)}}loadScript(function(){{beTracker.t({{hash:"8846943123fa01df9118bec76e6f7219"}})}});</script>
</head><body>
<div class="notice">{DISCLOSURE}</div>
<div class="top"><div class="wrap"><div class="hdr">
<a class="logo" href="{up}"><img src="{up}assets/character.png" alt="" onerror="this.remove()"><b>줍쥐</b><small>JOOPJWI</small></a>
<span class="sp"></span>
<a class="icon-btn" href="{up}#top" aria-label="검색"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg></a>
</div></div></div>"""


def foot(depth=1):
    up = "../" * depth
    return f"""<div class="detail"><footer>
<p><b>쿠팡 파트너스 고지</b><br>{DISCLOSURE} 구매 가격에는 영향이 없어요.</p>
<p><b>가격 안내</b><br>가격은 표시된 확인 시각 기준이며 쿠팡에서 수시로 바뀔 수 있어요. 품절 여부와 최종 가격·배송비는 쿠팡 상품 페이지에서 확인해 주세요.</p>
<p>© 줍쥐 JOOPJWI · <a href="{INSTA}" target="_blank" rel="noopener">@joopjwi</a></p>
</footer></div>
<nav class="bnav" aria-label="하단 메뉴">
<a href="{up}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M3 11 12 4l9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/></svg>홈</a>
<a href="{up}#top100"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 20V10M12 20V4M18 20v-7"/></svg>TOP 100</a>
<a href="{up}#top"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="4" width="7" height="7" rx="2"/><rect x="13" y="4" width="7" height="7" rx="2"/><rect x="4" y="13" width="7" height="7" rx="2"/><rect x="13" y="13" width="7" height="7" rx="2"/></svg>카테고리</a>
<a href="{up}#drops"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6l6 6 4-4 6 6"/><path d="M20 9v5h-5"/></svg>가격하락</a>
<a href="{INSTA}" target="_blank" rel="noopener"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3.5" y="3.5" width="17" height="17" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.3" cy="6.7" r="1" fill="currentColor"/></svg>인스타</a>
</nav>
<script src="{up}assets/common.js"></script>
</body></html>"""


def chart(hist):
    """가격 이력 SVG (기록 2일 이상일 때만)."""
    pts = sorted(hist.items())
    if len(pts) < 2:
        return ""
    vals = [v for _, v in pts]
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    w, h, pad = 600, 120, 14
    xy = [(pad + i * (w - 2 * pad) / (len(pts) - 1), h - pad - (v - lo) / span * (h - 2 * pad)) for i, (_, v) in enumerate(pts)]
    path = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(xy))
    lx, ly = xy[-1]
    return f"""<div class="chart"><div class="sec-h" style="margin:18px 0 4px"><div><h2 style="font-size:18px">가격 변동</h2>
<p>{e(pts[0][0])} ~ {e(pts[-1][0])} · 최저 {won(lo)} · 최고 {won(hi)}</p></div></div>
<svg viewBox="0 0 {w} {h}" role="img" aria-label="가격 변동 그래프"><path d="{path}" fill="none" stroke="#6625E8" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>
<circle cx="{lx:.1f}" cy="{ly:.1f}" r="6" fill="#DFFF00" stroke="#6625E8" stroke-width="3"/></svg></div>"""


def mini_card(p, depth=1):
    up = "../" * depth
    return f"""<div class="card"><a class="ph" href="{up}p/{e(p['id'])}.html"><img src="{e(p['image'])}" alt="{e(p['name'])}" loading="lazy"><span class="rank">{p['rank']}</span></a>
<a class="nm" href="{up}p/{e(p['id'])}.html">{e(p['name'])}</a><div class="price">{won(p['price'])}</div>{f'<div class="ship">{e(ship(p))}</div>' if ship(p) else ''}</div>"""


def related(pid, group, live, n=4, depth=1):
    rel = [p for p in live if p["group"] == group and p["id"] != pid][:n]
    if not rel:
        return ""
    return f"""<section class="sec"><div class="sec-h"><div><h2 style="font-size:19px">같이 보면 좋쥐</h2><p>오늘 {e(group)} TOP 100에서</p></div></div>
<div class="grid">{''.join(mini_card(p, depth) for p in rel)}</div></section>"""


def product_page(pid, meta, live_map, hist, live, checked_at):
    p = live_map.get(pid)
    url = f"{BASE}/p/{pid}.html"
    name = meta["name"]
    if p:
        price_block = f"""<div class="price">{won(p['price'])}{f"<s>{won(p['prevPrice'])}</s>" if p.get('dropPct') else ''}</div>
<div class="info">{f'<div><span>배송</span><b>{e(ship(p))}</b></div>' if ship(p) else ''}
<div><span>가격 확인</span><b>{e(p['checkedAt'])}</b></div>
<div><span>오늘 줍쥐 순위</span><b>{p['rank']}위 · {e(p['group'])}</b></div>
<div><span>쿠팡 카테고리 베스트</span><b>{e(p['sub'])} {p['catRank']}위</b></div>
{f"<div><span>어제 기록 대비</span><b style='color:#E5383B'>▼ {p['dropPct']}% ({won(p['prevPrice'])} → {won(p['price'])})</b></div>" if p.get('dropPct') else ''}</div>"""
        go = p["url"]
        stale = ""
    else:
        last_day = max(hist) if hist else meta.get("lastSeen", "")
        last_price = hist.get(last_day) if hist else None
        price_block = f"""<div class="info"><div><span>마지막 기록 가격</span><b>{won(last_price) if last_price else '기록 없음'}</b></div>
<div><span>마지막 확인일</span><b>{e(last_day)}</b></div></div>"""
        stale = (f'<div class="stale">이 상품은 오늘 줍쥐 TOP 100에 없어서 최신 가격을 확인하지 못했어요. '
                 f'위 가격은 {e(last_day)} 기록이에요. 현재 가격은 쿠팡에서 확인해 주세요.</div>')
        go = meta["url"]
    desc = (f"{meta['group']} · 쿠팡 {meta['sub']} 카테고리 인기 상품이에요. "
            f"줍쥐가 매일 아침 가격을 확인해서 기록하고 있어요.")
    body = f"""<main class="detail">
<div class="crumb"><a href="../">줍쥐</a> › {e(meta['group'])}</div>
<div class="hero-img"><img src="{e(meta['image'])}" alt="{e(name)}"></div>
<h1 class="clamp2" data-clamp>{e(name)}</h1><button class="more-btn" hidden>더 보기</button>
{price_block}{stale}
<div class="ctas" style="display:flex;gap:8px;margin:14px 0">
<a class="btn" href="{e(go)}" target="_blank" rel="sponsored nofollow noopener" data-go="{e(pid)}" data-place="detail">자세히 보기</a>
<button class="btn ghost" style="flex:0 0 auto" onclick="shareItem('{e(url)}', document.title)">공유</button></div>
<p style="font-size:14.5px;color:#3b3550">{e(desc)}</p>
{chart(hist)}
{related(pid, meta['group'], live)}
</main>"""
    title = f"{name} | 줍쥐"
    return head(title, f"{name} - {won(p['price']) if p else ''} 줍쥐에서 발견한 1만원 이하 가성비템", url, meta["image"]) + body + foot()


def pick_page(pk, live_map, live):
    pid = pk["id"]
    p = live_map.get(pid)
    url = f"{BASE}/pick/{pk['date']}.html"
    if p:
        price_html = f"""<div class="price">{won(p['price'])}</div>
<div class="info">{f'<div><span>배송</span><b>{e(ship(p))}</b></div>' if ship(p) else ''}<div><span>가격 확인</span><b>{e(p['checkedAt'])}</b></div></div>"""
        go = p["url"]
    else:
        price_html = f"""<div class="info"><div><span>선정 당시 가격</span><b>{won(pk['price'])}</b></div>
<div><span>선정일</span><b>{e(pk['date'])}</b></div></div>
<div class="stale">지난 줍쥐픽이에요. 위 가격은 선정 당시 기준이고, 지금 가격은 쿠팡에서 확인해 주세요.</div>"""
        go = pk["url"]
    problem = f'<p style="font-size:16px;line-height:1.7;color:#3b3550">{e(pk.get("problem",""))}</p>' if pk.get("problem") else ""
    points = "".join(f"<li>{e(x)}</li>" for x in pk.get("points", []))
    usage = f'<p style="font-size:15px;line-height:1.7">{e(pk.get("usage",""))}</p>' if pk.get("usage") else ""
    body = f"""<main class="detail"><div class="crumb"><a href="../">줍쥐</a> › 오늘 이건 줍쥐! · {e(pk['date'])}</div>
<div style="margin:14px 0 0"><span class="kicker">JOOPJWI'S DAILY PICK</span></div>
<h1 class="hook">{e(pk['title'])}</h1>
<div class="hero-img"><img src="{e(pk['image'])}" alt="{e(pk['name'])}"></div>
{problem}
<p style="font-size:16px;line-height:1.7">{e(pk['story'])}</p>
<div class="pick" style="border:0;margin:6px 0 0"><div class="body" style="padding:0"><ul>{points}</ul></div></div>
{usage}
<div class="clamp2" data-clamp style="font-size:14px;color:#6d6680;margin:12px 0 0">{e(pk['name'])}</div><button class="more-btn" hidden>더 보기</button>
{price_html}
<div style="display:flex;gap:8px;margin:14px 0">
<a class="btn" href="{e(go)}" target="_blank" rel="sponsored nofollow noopener" data-go="{e(pid)}" data-place="pick-page">자세히 보기</a>
<button class="btn ghost" style="flex:0 0 auto" onclick="shareItem('{e(url)}', document.title)">공유</button></div>
{related(pid, pk['group'], live, n=4)}
</main>"""
    return head(f"{pk['title']} | 오늘 이건 줍쥐!", pk["story"][:110], url, pk["image"]) + body + foot()


def write_api_pages():
    """AI 도구가 읽기 쉬운 HTML 버전: /api/top5.html, /api/top100.html (JSON 원문 포함)."""
    api = SITE / "api"
    for name, title in (("top5", "줍쥐 오늘의 TOP 5 데이터"), ("top100", "줍쥐 오늘의 TOP 100 데이터")):
        d = load(api / f"{name}.json", None)
        if not d:
            continue
        rows = "".join(
            f"<li><b>{it['rank']}. {e(it['productName'])}</b> — {won(it['price'])} · {e(it['category'])}"
            f"<br>이미지: {e(it['imageUrl'])}<br>제휴링크: {e(it['affiliateUrl'])}</li>" for it in d.get("items", []))
        raw = e(json.dumps(d, ensure_ascii=False, indent=1))
        (api / f"{name}.html").write_text(f"""<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title><meta name="robots" content="noindex"></head>
<body style="font-family:sans-serif;line-height:1.5;padding:16px;max-width:900px;margin:auto">
<h1>{title}</h1>
<p>status: <b>{e(d.get('status',''))}</b> · dataDate: <b>{e(d.get('dataDate',''))}</b> · updatedAt: {e(d.get('updatedAt',''))} · selection: {e(d.get('selection','-'))}</p>
<p>{e(d.get('disclosure',''))}</p>
<ol style="list-style:none;padding:0">{rows}</ol>
<h2>JSON 원문</h2><pre style="white-space:pre-wrap;word-break:break-all;background:#f4f1fa;padding:12px">{raw}</pre>
</body></html>""", encoding="utf-8")


def main():
    prod = load(DATA / "products.json", {})
    live = prod.get("products", [])
    live_map = {p["id"]: p for p in live}
    catalog = load(DATA / "catalog.json", {})
    history = load(DATA / "history.json", {})
    picks_index = load(DATA / "picks" / "index.json", [])
    checked = prod.get("checkedAt", "")

    (SITE / "p").mkdir(exist_ok=True)
    (SITE / "pick").mkdir(exist_ok=True)
    urls = [f"{BASE}/"]
    for pid, meta in catalog.items():
        (SITE / "p" / f"{pid}.html").write_text(
            product_page(pid, meta, live_map, history.get(pid, {}), live, checked), encoding="utf-8")
        if pid in live_map:
            urls.append(f"{BASE}/p/{pid}.html")
    for x in picks_index:
        pk = load(DATA / "picks" / f"{x['date']}.json", None)
        if not pk:
            continue
        (SITE / "pick" / f"{x['date']}.html").write_text(pick_page(pk, live_map, live), encoding="utf-8")
        urls.append(f"{BASE}/pick/{x['date']}.html")

    today = prod.get("date", "")
    (SITE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{e(u)}</loc>{f'<lastmod>{today}</lastmod>' if today else ''}</url>\n" for u in urls)
        + "</urlset>\n", encoding="utf-8")
    (SITE / "robots.txt").write_text(
        "# ChatGPT 등 AI 도구가 /api/ 데이터를 읽을 수 있게 허용\n"
        "User-agent: ChatGPT-User\nAllow: /\n\n"
        "User-agent: OAI-SearchBot\nAllow: /\n\n"
        "User-agent: Claude-User\nAllow: /\n\n"
        "User-agent: Perplexity-User\nAllow: /\n\n"
        f"User-agent: *\nAllow: /\nDisallow: /data/\nSitemap: {BASE}/sitemap.xml\n", encoding="utf-8")
    write_api_pages()
    print(f"페이지 생성: 상품 {len(catalog)}개, 픽 {len(picks_index)}개, 사이트맵 {len(urls)}개 URL")


if __name__ == "__main__":
    main()
