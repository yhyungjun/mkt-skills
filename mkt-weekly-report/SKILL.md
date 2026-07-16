---
name: mkt-weekly-report
description: |
  조코딩AX 주간 마케팅 주요지표 보고서를 GA4 + Google Ads 실데이터로 **차트 6종 + 표 다수가
  포함된 자립형 PDF**로 생성한다. 홈(jocodingax.ai)·해커톤 랜딩(hackathon.jocodingax.ai)의
  일별 트래픽·CTA, 소스(플랫폼)별 세션·이탈률·전환, 해커톤 신청 퍼널(랜딩→프라이머 이동→신청폼),
  해커톤 연동 UTM 전체 분석, 공모전 UTM 성과, 구글 키워드 광고·일별 지출, google/cpc 랜딩
  페이지별 이탈률, 블로그 유입까지 한 번에 정리한다. 주차·기간·주차라벨은 실행일 기준 자동 계산.
  Use when asked to "이번주/○월 ○주차 마케팅 보고서 만들어", "주간 마케팅 지표 PDF", "주간 마케팅
  주요지표 정리", "마케팅 주간보고", "weekly marketing report". 조코딩AX 전용(속성·계정·퍼널 내장).
---

# mkt-weekly-report — 조코딩AX 주간 마케팅 주요지표 보고서 (시각화 PDF)

GA4 Data API + Google Ads API 실데이터를 모아 **홈·해커톤·블로그·광고**를 아우르는 주간
보고서를 차트 포함 PDF로 자동 생성한다. 3개 스크립트(수집2 + 빌드1)로 반복 작업을 끝낸다.

## 언제 발동
- "이번주/지난주 마케팅 보고서", "○월 ○주차 마케팅 주요지표 PDF로", "주간 마케팅 지표 정리".
- 매주 정기 보고. 조코딩AX(jocodingax.ai·hackathon.jocodingax.ai) 대상일 때만.

## 산출물 (`<outdir>` = `ads/reports/주간마케팅/<주차>/`)
- `조코딩AX-마케팅-주간보고-<날짜>-<주차>.pdf` — 표지+목차+차트 임베드 자립 PDF
- `주간마케팅-보고-<날짜>.md` — 읽기용 마크다운
- `charts/1_home … 6_homesrc.png` — 차트 원본

## 리포트 구성
- **한눈에 보기**: 해커톤 세션·프라이머 이동/신청폼·홈 세션·SNS 조회수·광고 지출·블로그
- **Part 1**: 홈/해커톤 일별 세션·CTA 그래프, 소스(플랫폼)별 세션·CTA·비율·이탈률 표
- **Part 2**: 해커톤 신청 퍼널 & SNS, 해커톤 연동 UTM 전체표, 공모전 UTM, 구글 키워드 광고,
  최근 7일 일별 지출표(합계·CPC), google/cpc 페이지별 이탈률, 블로그 유입
- **전사 공유용 하이라이트** 5줄

## 사전 요건 (마케팅 레포 환경 재사용)
- `--ads-dir`(기본 `~/Desktop/dev/marketing/ads`)에 다음이 있어야 함:
  - `ga4_auth.py` + GA4 refresh token (`cloud_bot/mint_out.txt` 또는 `GA4_REFRESH_TOKEN`) — analytics.readonly
  - `google-ads.yaml` — Ads 인증 (CID 8834896313)
  - `.venv` — `google-ads`, `google-analytics-data`, `matplotlib`, `PyYAML`
- `make-pdf` 바이너리(gstack). 없으면 MD만 생성. 경로: `MAKE_PDF_BIN` 또는 기본 `~/.claude/skills/gstack/make-pdf/dist/pdf`.
- 한글 폰트(macOS AppleGothic 자동, Linux는 NanumGothic 권장).

## 실행 (마케팅 레포 venv로 3단계)

```bash
cd ~/Desktop/dev/marketing
PY=./ads/.venv/bin/python
SK=~/.claude/skills/mkt-weekly-report/scripts

# 1) GA4 수집  2) 광고 수집  → _workspace/*.json
$PY $SK/collect_ga4.py
$PY $SK/collect_ads.py

# 3) 리포트 빌드 (SNS 조회수는 주간 수동 입력)
$PY $SK/build_report.py --yt-views 37000 --ig-views 41000
```

- **SNS 조회수(`--yt-views`/`--ig-views`)는 API로 못 얻는 수동 입력값** — 유튜브 쇼츠·인스타
  릴스 총 조회수를 사용자에게 받아 넣는다. 생략하면 "미입력"으로 표기(리포트는 정상 생성).
- 날짜창은 항상 **실행일 기준 상대창**(14일: `14daysAgo~yesterday`, 지출표 7일: `LAST_7_DAYS`).
  주차 라벨은 실행일에서 자동(`M월 N주차`). `--week`/`--title`/`--date`로 오버라이드 가능.
- 기본 워크스페이스 `<ads-dir>/../_workspace`, 출력 `<ads-dir>/reports/주간마케팅/<주차>`.
  변경: `--workspace`, `--outdir`.

## 사이트 → GA4 속성 → 이벤트 매핑 (내장 상수, 2026-07 실측)
| 대상 | GA4 속성 | 핵심 이벤트 |
|---|---|---|
| jocodingax.ai (홈) | 538854394 | CTA = `cta_click` |
| hackathon.jocodingax.ai (해커톤 랜딩) | 542898562 | 프라이머 이동 = `cta_apply_click` (→ hack.primer.kr) |
| hack.primer.kr (프라이머 신청폼) | 542884357 | 신청 = `form_submit` (퍼널 종단) |
| blog.jocodingax.ai | 529719326 | 세션·페이지뷰 |

- 퍼널: 해커톤 랜딩 세션 → `cta_apply_click`(프라이머 이동, ~46%) → primer `form_submit`.
- **`contestkorea`는 `linkareer`(링커리어)에 합산**(사용자 확정 규칙, build_report에 내장).
- 소스→플랫폼 정규화·공모전 매핑은 `build_report.py`의 `platform()`/`CONTEST` 상수.

## 주의
- `cta_apply_click` = 프라이머 신청 페이지 이동(마이크로 전환), 최종 신청완료(`form_submit`, primer 전체)와 다름.
- primer `form_submit`은 hack.primer.kr **전체 기준**(우리 랜딩 외 직접유입 포함) — 랜딩 귀속 아님.
- 소스표 google은 `sessionSource`만 쓰면 광고+자연이 섞임 → 스크립트가 `sessionMedium`로 cpc/organic 분리.
- GA4/Ads 기간·타임존 차이로 절대값보다 채널 간 상대 비교로 해석. 하이라이트 문구는 규칙 기반 초안 → 분석자 확정.

## 파일
| 파일 | 설명 |
|------|------|
| `scripts/collect_ga4.py` | GA4 수집 → `ga4_data.json` (ga4_auth 재사용, `--ads-dir`) |
| `scripts/collect_ads.py` | 구글애즈 수집 → `ads_data.json` (`--yaml`/`--cid`) |
| `scripts/build_report.py` | 집계→차트→MD→PDF, 주차/기간 자동·SNS 인자·데이터기반 코멘트 |
