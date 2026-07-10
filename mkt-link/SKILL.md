---
name: mkt-link
description: |
  jocodingax.ai UTM 링크 + Cloudflare "표시 링크"(jocodingax.ai/go/{code})를 한 번에 생성·등록한다.
  회사 정본 `utm/taxonomy.md`(닫힌집합 5축)를 강제 검증하고, mnemonic 숏코드를 자동 생성해
  Cloudflare Bulk Redirect로 301 리다이렉트를 등록한 뒤 깔끔한 표시 링크를 반환한다.
  Use when asked to "utm 표시링크 만들어", "숏링크 만들어줘", "유튜브 링크 표시링크로",
  "/go 링크 만들어", "cloudflare 리다이렉트 utm 링크", "mkt-link". 대상은 유튜브(영상/쇼츠/
  커뮤니티/댓글)·블로그·링크드인 등에서 jocodingax.ai 또는 blog.jocodingax.ai로 보내는 링크.
  단순 UTM URL만 필요하고 리다이렉트(표시링크)가 필요 없으면 utm-tagging-jocodingax 를 사용.
  조코딩AX 계정·토큰이 하드코딩되어 있으니 타 브랜드/도메인엔 사용 금지.
---

# mkt-link — UTM + Cloudflare 표시 링크 원스텝 생성

유튜브/블로그 등 외부 게시물에 붙일 **깔끔한 표시 링크**(`https://jocodingax.ai/go/{code}`)를
만들고, 그게 UTM이 붙은 실제 목적지로 301 리다이렉트되도록 Cloudflare Bulk Redirect에 자동 등록한다.
"링크마다 UTM 손으로 붙이고 규칙 어긋나는" 문제를 스크립트가 검증·자동화한다.

## 언제 발동
- "이 유튜브(영상/쇼츠/커뮤니티) 링크 표시링크로 만들어줘", "숏링크 만들어", "/go 링크".
- 외부 채널 → jocodingax.ai/제품 페이지로 유입시키고 GA4에서 채널·콘텐츠별로 보고 싶을 때.
- 단순 UTM URL만 필요(리다이렉트 불필요)하면 → `utm-tagging-jocodingax`.

## 동작 원리
```
표시 링크 jocodingax.ai/go/{code}
   │  Cloudflare Bulk Redirect (301)
   ▼
목적지 ...?utm_source=..&utm_medium=..&utm_campaign=..&utm_content=..
```
- 표시 링크는 짧고 깔끔 → 유튜브/게시물엔 이것만 노출.
- UTM은 리다이렉트가 자동 부착 → GA4가 `sessionSource/Medium/CampaignName/ManualAdContent` 기본 차원으로 수집(맞춤측정기준 등록 불필요).
- 나중에 목적지·UTM을 바꿔도 게시물의 표시 링크는 그대로 유지.

## 사전 요건 (marketing 레포에 이미 구성됨)
- 스크립트: `~/Desktop/dev/marketing/ads/shortlink.py` (stdlib only, Python 3.9+).
- 레지스트리(진실의 원천, 커밋됨): `~/Desktop/dev/marketing/ads/shortlinks.json`.
- Cloudflare API 토큰: `~/Desktop/dev/marketing/ads/.cloudflare.env` (gitignore).
  권한 = Account Filter Lists:Edit + Bulk URL Redirects:Edit. 최초 1회 `setup` 필요(이미 완료).
- CF 계정 `6fb2581c6dd22084d4df956047e72a0e`, 리스트 `jocodingax_shortlinks`.

## 실행 절차 (Claude가 수행)

### 1) 사용자에게 받을 정보 (정본 5축 — `utm/taxonomy.md`)
| 입력 | → 인자 | 값 |
|---|---|---|
| 노출 채널 | `--source` | youtube·instagram·blog·contestkorea·linkedin … (taxonomy §2) |
| 목표 | `--campaign` | `{goal}-{yymm}` — `b2b-lead-2607`·`brand-2607`·`content-2607` (**소재명 아님**) |
| 계정·표면·위치 | `--content` | `{account}-{surface}-{placement}` 예 `ax-longform-desc` |
| 소재(선택) | `--term` | 영상/게시물 슬러그(`musinsa` 등). cpc면 키워드 |
| 목적지 | `--dest` | `utm/destinations.md`의 URL (순수 경로, 쿼리 X) |

> `--medium`은 **source에서 자동 도출**(youtube→social, blog→referral, google→cpc). 지정 불필요(모호한 `crm`만 예외).

### 2) content 3세그먼트 (taxonomy §4 — 스크립트가 강제)
`{account}-{surface}-{placement}`, 세그먼트 내부 하이픈 금지.
| 축 | 허용값 |
|---|---|
| account | `ax`(조코딩AX) · `jc`(조코딩) · `co`(회사) · `fo`(파운더) |
| surface | `longform`·`shorts`·`reels`·`post`·`story`·`profile`·`community`·`article` |
| placement | `desc`·`comment`·`caption`·`body`·`bio`·`link` |

예: 영상 설명란 `ax-longform-desc` · 쇼츠 댓글 `ax-shorts-comment` · 커뮤니티 본문 `ax-community-body` · 프로필 링크 `ax-profile-link`.

### 3) 명령 실행
```bash
cd ~/Desktop/dev/marketing
python3 ads/shortlink.py add \
  --source youtube --dest "https://jocodingax.ai/경로" \
  --campaign b2b-lead-2607 --content ax-longform-desc --term nia-ai-training
# 옵션: --code <숏코드>  --status 302  --dry-run
```
→ `표시 링크 : https://jocodingax.ai/go/{code}` + 목적지(medium 자동) + 검증 커맨드 출력.
> 표에 없는 값이면 스크립트가 **거부** → `utm/requests.md`에 제안 후 승격하고 다시 실행.

### 4) 검증 (반드시)
```bash
curl -sI "https://jocodingax.ai/go/{code}" | grep -iE "^(HTTP|location)"
# 기대: HTTP/2 301 + location 에 UTM
```
> Bulk Redirect 전파에 십수 초 걸릴 수 있으니 301 나올 때까지 재시도.

### 현황 / 재태깅
```bash
python3 ads/shortlink.py list                    # 등록 현황
python3 ads/shortlink.py retag --code <c> ...     # 기존 링크 정본 재태깅(레지스트리)
python3 ads/shortlink.py sync                     # 레지스트리로 CF 리스트 전체 반영
```

## 예시
```bash
# 유튜브 영상 설명란 → 문의폼
python3 ads/shortlink.py add --source youtube --dest "https://jocodingax.ai/contact" \
  --campaign b2b-lead-2607 --content ax-longform-desc --term nia-ai-training

# 쇼츠 고정댓글 → 홈
python3 ads/shortlink.py add --source youtube --dest "https://jocodingax.ai/" \
  --campaign brand-2607 --content ax-shorts-comment --term claude-as-employee
```

## 주의
- **campaign은 목표**(소재명 아님). 소재 식별은 `--term`. 여러 소재를 한 목표로 묶어 ROI를 본다.
- **숏코드 충돌**: 같은 콘텐츠라도 목적지가 다르면 별도 코드 필요(예: `vcn`→blog, `vcnc`→/contact).
- **무료플랜 상한**: Cloudflare Bulk Redirect 20개 근접 시 스크립트가 경고. 초과 시 CF 상향 요청.
- **토큰 노출**: 토큰을 채팅/스크린샷에 노출하면 즉시 Roll(재발급) 후 `ads/.cloudflare.env` 교체.
- **내부 링크 금지**: UTM/표시링크는 외부→사이트 진입에만. 사이트 내부 이동에 달면 세션 끊김.
