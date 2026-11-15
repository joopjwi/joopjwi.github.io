# 줍쥐 JOOPJWI — 이게 만원도 안 한다고?

매일 아침 6시쯤 쿠팡파트너스 API로 1만원 이하 인기템 TOP 100을 갱신하는 쇼핑 큐레이션 사이트.

- 사이트: https://joopjwi.github.io/
- 인스타그램: @joopjwi

## 구성
- `update.py` — 쿠팡 API 호출, 검증(가격·링크·이미지), 가격/순위 기록, TOP 5, 데일리 픽 후보
- `build.py` — 상품 상세(`p/`), 데일리 픽(`pick/`), sitemap, robots 생성 (API 호출 없음)
- `site/` — 홈페이지, 공통 스타일·스크립트, 데이터(`site/data/`)
- `.github/workflows/update.yml` — 매일 갱신 + 코드 변경 시 재배포

## 데이터
- `site/data/products.json` 오늘의 TOP 100
- `site/data/top5.json` 홈페이지 TOP 5 = 릴스 TOP 5 (같은 파일)
- `site/data/picks/<날짜>.json` 오늘 이건 줍쥐! (copySource: template → ai)

## 브랜드 캐릭터
`site/assets/character.png`(배경 투명 PNG)를 넣으면 헤더 로고와 메인 배너에 자동으로 표시됩니다.

## 분석
`site/config.js`의 `ga4`에 GA4 측정 ID를 넣으면 쿠팡 이동·상품 보기·공유·검색 이벤트가 기록됩니다.

## 폰트
- Pretendard (CDN)
- 여기어때 잘난체: 사이트 문구에 쓰인 글자만 잘라 `site/assets/fonts/jalnan-subset.woff2`로 포함.
  배너·섹션 제목 문구를 바꾸면 서브셋을 다시 만들어야 합니다.
