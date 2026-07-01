---
name: mkt-keyword-ads-report
description: |
  Google Ads + GA4 실데이터로 키워드 광고 성과 리포트를 **차트 4종이 포함된 PDF**로 생성한다.
  키워드별 노출·클릭·CTR·비용·CPC·품질점수 + GA4 신청퍼널(cta_apply_click)을 결합해
  신청클릭당 비용·효율 등급(S~C)을 산출하고, 일별 추이·WoW 비교·노출점유율 병목까지
  시각화한다. 차트는 matplotlib(한글폰트) → base64 인라인 임베드 → make-pdf 로 자립 PDF.
  Use when asked to "키워드 광고 리포트 만들어", "키워드별 효율/성과 리포트 PDF",
  "이번주/주간 광고 성과 정리", "광고 성과 시각화 리포트", "keyword ads report".
  조코딩AX 계정(8834896313) 기본값 내장. 다른 계정은 --cid/--ga4/--yaml 로 지정.
---

# mkt-keyword-ads-report — 키워드 광고 성과 리포트 (시각화 PDF)

Google Ads API + GA4 Data API 실데이터를 모아 **키워드별 효율·성과 리포트**를
차트 포함 PDF로 자동 생성한다. 반복적인 주간/기간 리포트 작업을 한 번의 실행으로 끝낸다.

## 언제 발동
- "이번주 키워드 광고 성과 정리", "키워드별 효율 리포트 PDF로", "광고 성과 시각화" 등.
- 정기(주간) 리포트, 캠페인 점검 리포트.

## 산출물
- `<캠페인>-keyword-report-<날짜>.md` — 읽기용 마크다운(차트는 `charts/` 상대경로)
- `<캠페인>-keyword-report-<날짜>.pdf` — 표지+목차+차트 임베드 자립 PDF
- `charts/1_daily.png … 4_is_wow.png` — 차트 원본

## 리포트 구성
1. 요약 (핵심 지표 + 최고 효율 키워드)
2. WoW 비교 (직전 동일길이 기간 대비) + 노출점유율 병목 스택차트
3. 일별 추이 표 + 비용·클릭 콤보차트
4. 키워드별 성과·효율 표 (신청클릭당 비용·효율등급) + 비용·CTR / 신청단가 차트
5. 결론 & 액션 (규칙 기반 초안 — 분석자가 확정)

## 사전 요건
- `pip install "google-ads>=24,<25" matplotlib PyYAML` (프로젝트 venv 권장)
- `google-ads.yaml` — Ads 인증(client_id/secret/refresh_token + developer_token).
  refresh token은 **adwords + analytics.readonly** 스코프 필요(GA4 병합용, 같은 OAuth 클라이언트).
- `make-pdf` 바이너리(gstack). 없으면 MD만 생성. 경로: 환경변수 `MAKE_PDF_BIN` 또는
  기본 `~/.claude/skills/gstack/make-pdf/dist/pdf`.
- 한글 폰트(macOS AppleGothic 자동 탐지, Linux는 NanumGothic 설치 권장).

## 실행

```bash
# 조코딩AX AX 인재전쟁 · 이번 주 (기본 프리셋)
<venv>/python scripts/generate_report.py \
  --campaign "AX 인재전쟁" --cid 8834896313 --ga4 542898562 \
  --yaml /path/to/ads/google-ads.yaml \
  --preset this_week \
  --outdir "/path/to/docs/AX 인재전쟁" \
  --title "AX 인재전쟁 — 주간 키워드 효율·성과 리포트" --author "조코딩AX 마케팅"
```

옵션:
- `--preset this_week | last_7_days | last_14_days`  또는  `--start YYYY-MM-DD --end YYYY-MM-DD`
- `--apply-event cta_apply_click` (GA4 신청 이벤트명, 기본값)
- `--no-wow` (WoW 비교 생략)

> 조코딩AX 마케팅 레포에서는 보통 `marketing/ads/.venv/bin/python` + `marketing/ads/google-ads.yaml` +
> outdir `marketing/docs/<캠페인>/` 조합으로 실행한다.

## 효율 등급(S~C) 규칙
신청클릭당 비용(=Ads비용÷GA4신청클릭) 최저값 대비 배수 + CTR 보정 휴리스틱.
- S: 최저 신청단가의 1.5배 이내 **또는** CTR≥35%
- A: 3배 이내 **또는** CTR≥20%
- B: 4.5배 이내
- C: 그 외 / 신청 0
→ 자동 초안이므로 최종 판단은 분석자가 캠페인 맥락으로 조정.

## 주의
- `cta_apply_click`은 **신청 버튼 클릭(마이크로 전환)** — 외부 최종 신청완료와 다름.
- GA4 세션은 재방문 때문에 Ads 클릭보다 많을 수 있음(신청단가는 참고 지표).
- 전환(Ads conversion) 지표는 리포트에서 제외(신청은 GA4 기준). 필요 시 별도 확장.
- GA4/Ads 기간·타임존 차이로 절대값보다 키워드 간 상대 비교로 해석.

## 파일
| 파일 | 설명 |
|------|------|
| `scripts/generate_report.py` | 수집→차트→MD→PDF 엔드투엔드 오케스트레이터 |
| `README.md` | 빠른 시작 |
