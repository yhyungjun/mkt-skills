---
name: mkt-link
description: |
  jocodingax.ai UTM 링크 + Cloudflare "표시 링크"(jocodingax.ai/go/{code})를 한 번에 생성·등록한다.
  UTM 컨벤션(utm-youtube-convention)을 강제 검증하고, 슬러그 기반 mnemonic 숏코드를 자동 생성해
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

### 1) 사용자에게 받을 4가지
| 입력 | 값 | 비고 |
|---|---|---|
| 제목/슬러그 | 콘텐츠 제목(영문 권장) | `--campaign` 미지정 시 여기서 슬러그 자동 생성 |
| 종류 | 영상/쇼츠/커뮤니티/댓글 | → `--medium` |
| 위치 | 설명란/고정댓글/커뮤니티/카드 | → `--content` |
| 목적지 | `https://jocodingax.ai/...` 또는 `https://blog.jocodingax.ai/...` | 순수 경로(쿼리 X) |

### 2) 값 매핑 (utm-youtube-convention — 스크립트가 강제 검증)
| 종류 | `--medium` | 종류 | `--medium` |
|---|---|---|---|
| 롱폼 영상 | `video` | 커뮤니티 게시물 | `social` |
| 쇼츠 ⭐ | `shorts` | 댓글 | `comment` |

| 위치 | `--content` |
|---|---|
| 설명란 | `description` |
| 고정댓글 | `pinned` |
| 커뮤니티 본문 | `community` |
| 카드 | `card` |
| 채널 프로필·About·링크 | `profile` |

> ⚠️ **쇼츠는 반드시 `shorts`** (롱폼 `video`와 안 섞음). 무태깅 금지.
> **프로필/채널 링크**(특정 영상 아님)는 `--medium social --content profile`,
> campaign은 지속형 식별자(예: `channel-profile`). 예: `jocodingax.ai/go/yp`.

### 3) 명령 실행
```bash
cd ~/Desktop/dev/marketing
python3 ads/shortlink.py add \
  --title "콘텐츠 제목" \
  --dest  "https://jocodingax.ai/경로" \
  --source youtube --medium <형식> --content <위치>
# 옵션: --campaign <슬러그 직접지정>  --code <숏코드 직접지정>  --status 302  --dry-run
```
→ `표시 링크 : https://jocodingax.ai/go/{code}` + 목적지 + 검증 커맨드 출력.

### 4) 검증 (반드시)
```bash
curl -sI "https://jocodingax.ai/go/{code}" | grep -iE "^(HTTP|location)"
# 기대: HTTP/2 301  +  location 에 UTM 4개
```
> Bulk Redirect 전파에 몇 초 걸릴 수 있으니 301 나올 때까지 몇 번 재시도.

### 현황
```bash
python3 ads/shortlink.py list
```

## 예시
```bash
# 유튜브 커뮤니티 게시물 → 문의폼
python3 ads/shortlink.py add --title "vibe-coding-nondev-case" \
  --dest "https://jocodingax.ai/contact" --source youtube --medium social --content community

# 쇼츠 고정댓글 → 홈
python3 ads/shortlink.py add --title "claude as employee" \
  --dest "https://jocodingax.ai/" --source youtube --medium shorts --content pinned
```

## 주의
- **숏코드 충돌**: 같은 콘텐츠라도 목적지가 다르면 별도 코드 필요(예: `vcn`→blog, `vcnc`→/contact).
  같은 콘텐츠는 `--campaign` 슬러그를 재사용(콘텐츠 단위 합산). GA4는 랜딩페이지로 목적지 구분.
- **무료플랜 상한**: Cloudflare Bulk Redirect 20개 근접 시 스크립트가 경고. 초과 시 CF 상향 요청.
- **토큰 노출**: 토큰을 채팅/스크린샷에 노출하면 즉시 Roll(재발급) 후 `ads/.cloudflare.env` 교체.
- **내부 링크 금지**: UTM/표시링크는 외부→사이트 진입에만. 사이트 내부 이동에 달면 세션 끊김.
