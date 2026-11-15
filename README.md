# 오천픽 — 5천원 이하 인기템 TOP 100

매일 아침 6시쯤 쿠팡파트너스 API에서 카테고리별 베스트 상품을 가져와
5천원 이하만 골라 TOP 100을 만들고, 가격 기록으로 "역대 최저가", "▼ 할인%" 뱃지를 붙입니다.

## 파일 구성
- `site/index.html` — 사이트 화면 (데이터가 없으면 샘플로 표시)
- `update.py` — 쿠팡 API 호출 + 가격 기록 + TOP 100 생성
- `.github/workflows/update.yml` — 매일 자동 실행 + GitHub Pages 배포

## 처음 한 번 세팅 (약 10분)
1. GitHub에서 새 저장소를 만들고 이 파일들을 그대로 올립니다.
2. 저장소 **Settings → Secrets and variables → Actions → New repository secret**에서 추가:
   - `COUPANG_ACCESS_KEY` — 쿠팡파트너스 Access Key
   - `COUPANG_SECRET_KEY` — 쿠팡파트너스 Secret Key
   - `COUPANG_SUB_ID` — (선택) 채널 구분용 이름, 예: `ochunpick`
3. **Settings → Pages → Source**를 `GitHub Actions`로 바꿉니다.
4. **Actions 탭 → "오늘의 TOP 100 갱신" → Run workflow**를 눌러 첫 실행.
5. 끝나면 `https://<아이디>.github.io/<저장소이름>/`에서 사이트가 열립니다.
6. 쿠팡파트너스 **활동 페이지**에 이 주소를 등록하세요.

## 바꾸고 싶을 때
- 가격 상한: `update.py`의 `MAX_PRICE` (기본 5000)
- 카테고리: `update.py`의 `CATEGORIES`
- 갱신 시간: `update.yml`의 `cron` (UTC 기준, 현재 한국시간 06:07)

## 참고
- 페이지 맨 위 대가성 문구는 지우지 마세요(공정위 지침).
- 플로팅 배너·강제 클릭 유도는 쿠팡 정책 위반이라 넣지 않았습니다.
