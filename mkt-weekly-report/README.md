# mkt-weekly-report

조코딩AX 주간 마케팅 주요지표 보고서(GA4 + Google Ads → 차트 6종 포함 PDF) 생성 스킬.

## 빠른 시작

```bash
cd ~/Desktop/dev/marketing
PY=./ads/.venv/bin/python
SK=~/.claude/skills/mkt-weekly-report/scripts

$PY $SK/collect_ga4.py                                   # → _workspace/ga4_data.json
$PY $SK/collect_ads.py                                   # → _workspace/ads_data.json
$PY $SK/build_report.py --yt-views 37000 --ig-views 41000  # → ads/reports/주간마케팅/<주차>/*.pdf
```

- SNS 조회수(유튜브 쇼츠·인스타 릴스)는 매주 수동 입력값 → `--yt-views/--ig-views`.
- 주차·기간·주차 라벨은 실행일 기준 자동. `--week/--title/--date/--outdir/--workspace`로 오버라이드.
- 상세: `SKILL.md` 참고. 조코딩AX 속성·계정·퍼널이 내장된 전용 스킬(타 브랜드 사용 금지).

## 요건
`--ads-dir`(기본 `~/Desktop/dev/marketing/ads`)에 `ga4_auth.py`(+GA4 토큰), `google-ads.yaml`,
`.venv`(google-ads·google-analytics-data·matplotlib). PDF는 gstack `make-pdf` 바이너리.
