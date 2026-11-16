# 줍쥐 데일리 특가 TOP 5 릴스 — 매일 작업 지침

담당: 김신혜(총괄). 대표는 결과만 확인한다. 사용자에게 하는 모든 말과 알림은 **한국어**로.

## 0. 준비
- 저장소: `joopjwi/joopjwi.github.io` (add_repo, access push) → 클론 (`/home/claude/jj`)
- 상품 데이터와 이미지: 같은 저장소의 `media` 브랜치를 별도 폴더에 클론 (`git clone --depth 1 -b media ... /home/claude/media`)
  - `media/products.json`의 `checkedAt` 날짜가 **오늘(한국시간)** 이 아니면 아무것도 만들지 말고 "오늘 데이터 갱신이 안 됐어요"라고 보고하고 끝낸다.
  - 오늘 릴스가 이미 있으면(`site/data/reels/<오늘>.json` 존재) 중복 제작하지 말고 끝낸다.

## 1. 상품 5개 고르기 (가장 중요)
- `python3 tools/reels/candidates.py /home/claude/media site/data/reels/index.json <오늘>` 로 후보를 본다. 최근 6일 릴스 상품은 자동 제외됨.
- **상위 순위 5개가 아니라 바이럴될 만한 5개**를 고른다.
  - 사람들이 "이게 뭐지?" 궁금해할 물건 2~3개 + 매일 쓰는 생필품(물티슈·생수·휴지 등) 1~2개
  - 같은 탭(카테고리)에서 2개 넘게 고르지 않는다. 계절·날씨·시기(예: 수능, 김장, 장마)에 맞는 물건 우선.
  - 상품 사진이 무엇인지 한눈에 보이는 것 (`media/img/<id>.jpg`를 직접 열어 확인).
- 각 상품의 **요약 이름**(화면 표시용, 2~8자 정도): 예) "탐사 클래식 물티슈 캡형" → "물티슈", "자동 오픈 계란 한판 보관함 3단 30구" → "계란 보관함".

## 2. 대본 (상품당 7~10초, 전체 55초 이하, 쉼 커트 후 40~50초)
- 구조: 인트로 1문장 → 1번~5번 (번호 + 상황 공감 1문장 + 상품 소개 + 가격) → 아웃트로 1문장
- 인트로 예: "만원도 안 하는 오늘의 생활 꿀템, 다섯 개 바로 갑니다!" (매일 조금씩 바꿔도 됨)
- 아웃트로 예: "가격은 바뀔 수 있으니까, 프로필 링크에서 번호로 바로 줍쥐!"
- 말투: 친구한테 꿀템 알려주듯 짧고 경쾌하게.
- **사실 규칙(할루시네이션 금지)**: 상품명·가격·카테고리·태그로 확인되는 것만 말한다. 개수·용량·효능·후기·배송 도착 시간은 상품명에 없으면 말하지 않는다. "최저가/역대급/무조건" 금지. 배송비 언급 금지. 가격 하락은 dropPct>0일 때만.
- 숫자는 **말하는 텍스트(spoken)** 에서 한글로 풀어 쓴다: "1번"→"일번", "6,550원"→"육천오백오십원", "30구"→"삼십 구". 화면 자막(display)은 숫자 그대로.
- **"만원", "○○원"은 띄우지 않고 붙여 쓴다** (spoken·display 모두). "만 원"처럼 띄우면 TTS가 "만-원"으로 끊어 읽는다 (대표 지적).
- spec 파일 `/home/claude/reel_<오늘>.json` 형식 (완성 예시: `tools/reels/example_spec.json`):
```json
{"date":"YYYY-MM-DD","dateLabel":"11월 16일 (월)","dataCheckedAt":"<checkedAt>",
 "items":[{"id":"...","short":"계란 보관함","script":"..."}, ... 5개],
 "chunks":[{"scene":"intro","display":"만 원도 안 하는","spoken":"만 원도 안 하는"},
           {"scene":1,"display":"1번!","spoken":"일번!"}, ... ,
           {"scene":"outro","display":"번호로 바로 줍쥐!","spoken":"번호로 바로 줍쥐!"}]}
```
  - chunk 하나 = 화면 자막 한 줄 (16자 안팎). scene은 "intro", 1~5, "outro".
  - TTS 텍스트 = 모든 chunk의 spoken을 공백으로 이어 붙인 것.

## 3. 제작 요청 보내기 (음성·영상은 GitHub가 만든다)
- 위 spec에 아래 `tts` 블록을 그대로 넣어 `site/data/reels/requests/<오늘>.json` 으로 저장한다.
```json
"tts": {"voiceId": "vn80HZNY7EsdYzoFRYZm", "model": "eleven_multilingual_v2",
        "voiceSettings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.25, "use_speaker_boost": true, "speed": 1.08}}
```
  - 목소리: 대표 본인 ElevenLabs 계정의 **SK (Friendly & Mid-High Pitch)**. 다른 목소리로 바꾸지 않는다.
- 이 파일을 main에 push하면 GitHub Actions "줍쥐 릴스 렌더링"이 자동으로:
  ElevenLabs TTS 생성 → **문장 사이 쉼·호흡 0.2초로 커트** → 단어 타이밍으로 자막 싱크 → 영상·표지 렌더링 → 배경음악 믹스 → `reels-out` 브랜치 저장 → 사이트 재배포.
- 7단계(기록·TOP 5 맞추기) 파일도 같은 커밋에 넣어도 된다.

## 4. 결과 기다리기·검수
- 30초 간격으로 최대 15분: `git ls-remote https://github.com/joopjwi/joopjwi.github.io reels-out` 후
  `git clone --depth 1 -b reels-out https://github.com/joopjwi/joopjwi.github.io /home/claude/ro` 해서 `<오늘>.json` 의 `status` 확인.
  - `"error"`면: `gh api repos/joopjwi/joopjwi.github.io/actions/workflows/reel.yml/runs?per_page=1` 로 실행 ID를 찾고 로그를 확인해 원인을 보고하고 끝낸다 (ElevenLabs 크레딧 부족 등).
  - `tts.words` 와 `tts.expectedWords` 가 다르면 자막이 조금 어긋날 수 있음을 보고에 적는다.
  - `duration` 이 55초를 넘으면 대본을 줄여 요청을 다시 보낸다.
- `/home/claude/ro/<오늘>.mp4` 에서 프레임 3~4장(0초, 상품 1개, 아웃트로)을 ffmpeg로 뽑아 직접 보고 글자 겹침·잘림이 없는지 확인한다.
- 사이트 재배포 완료 확인: `gh api "repos/joopjwi/joopjwi.github.io/actions/workflows/update.yml/runs?per_page=1"` 가 요청 이후 시각에 `completed/success` 인지 본다 (최대 10분 대기).
  - 영상 주소: `https://joopjwi.github.io/reels/<오늘>.mp4`, 표지: `https://joopjwi.github.io/reels/<오늘>.jpg`

## 5. (예비) GitHub 렌더링이 안 될 때만
- Creative Claw 방식(예전 방식)은 쓰지 않는다. 실패하면 억지로 올리지 말고 원인을 보고한다.

## 6. 업로드 (Metricool, 브랜드 joopjwi, blogId `7441991`)
- 게시 시각: **오늘 08:30 (Asia/Seoul)**. 이미 지났으면 지금부터 15분 뒤.
- media: `https://joopjwi.github.io/reels/<오늘>.mp4`
- 인스타그램 (별도 게시물): providers instagram, instagramData `{"type":"REEL","showReelOnFeed":true}`, `videoThumbnailUrl` = `https://joopjwi.github.io/reels/<오늘>.jpg`
- 유튜브 (별도 게시물, 표지 넣지 않음): youtubeData `{"title":"만 원도 안 하는 오늘의 득템 TOP 5 🐭 <M월 D일> #shorts","type":"short","privacy":"public","madeForKids":false,"category":"HOWTO_STYLE","tags":["줍쥐","만원이하","득템","생활꿀템","쿠팡추천"]}`
- autoPublish true.
- 유튜브 제목은 `만 원도 안 하는 오늘의 득템 TOP 5 🐭 <M월 D일> #shorts` 형식.
- 캡션은 **아주 짧고 가볍게**. 광고 문구·#광고·[광고]는 넣지 않는다 (대표 지시: 홈페이지에 쿠팡 파트너스 고지가 있음).
  - 인스타: `팔로우 해놓고 매일 특가 확인하쥐 🐭` + 줄바꿈 + `#줍쥐 #만원이하 #득템 #생활꿀템`
  - 유튜브 설명: `팔로우 해놓고 매일 특가 확인하쥐 🐭` + 줄바꿈 + `👉 번호로 찾기: https://joopjwi.github.io/` + 줄바꿈 + `#줍쥐 #만원이하 #득템`
  - 문구 톤은 매일 조금씩 바꿔도 되지만 "팔로우 해놓고 매일 특가 확인하쥐" 느낌을 유지한다.

## 7. 홈페이지 번호 맞추기 + 기록
- `site/data/reels/<오늘>.json` 저장: `{"date","dateLabel","checkedAt","items":[{"no","id","short","script"}]}`
- `site/data/reels/index.json` 맨 앞에 `{"date":"<오늘>","ids":[5개 id]}` 추가 (최근 30일만 유지)
- 홈페이지 TOP 5·top5.json을 릴스 순서로 맞춘다:
```
cd /home/claude/jj && python3 - <<'PY'
import json, update
from datetime import datetime
reel=json.load(open('site/data/reels/<오늘>.json'))
d=json.load(open('site/data/products.json')); by={p['id']:p for p in d['products']}
top5=[by[x['id']] for x in reel['items'] if x['id'] in by]
d['top5']=[p['id'] for p in top5]; d['top5Selection']='curated'
json.dump(d,open('site/data/products.json','w'),ensure_ascii=False,indent=1)
st=json.load(open('site/api/status.json'))
update.write_api(d['products'],top5,'curated',datetime.fromisoformat(st['lastSuccessAt']),d['checkedAt'],st.get('apiCalls',23))
PY
```
- 커밋 메시지 "줍쥐 릴스 <오늘>" 로 main에 push (push하면 사이트가 자동 재배포됨).

## 8. 보고 (한국어, 5줄 이내)
- 오늘 고른 5개(요약 이름·가격), 영상 길이, 게시 예정 시각.
- 문제가 있었으면(자막 단어 수 불일치, 렌더링 실패 등) 한 줄로 알린다.
