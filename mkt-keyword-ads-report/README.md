# mkt-keyword-ads-report

Google Ads + GA4 실데이터로 **키워드 광고 성과 리포트(차트 포함 PDF)**를 자동 생성하는 스킬.

키워드별 노출·클릭·CTR·비용·CPC·품질점수 + GA4 신청퍼널을 결합해 **신청클릭당 비용·효율 등급**을
산출하고, 일별 추이·WoW 비교·노출점유율 병목을 차트로 시각화한다.

## 빠른 시작

```bash
pip install "google-ads>=24,<25" matplotlib PyYAML   # 최초 1회

python scripts/generate_report.py \
  --campaign "AX 인재전쟁" --cid 8834896313 --ga4 542898562 \
  --yaml /path/to/google-ads.yaml \
  --preset this_week \
  --outdir "/path/to/out" \
  --title "AX 인재전쟁 — 주간 키워드 리포트" --author "조코딩AX 마케팅"
```

→ `<캠페인>-keyword-report-<날짜>.md`, `.pdf`, `charts/*.png` 생성.

## 필요한 것
- `google-ads.yaml` (adwords + analytics.readonly 스코프 refresh token)
- `make-pdf` 바이너리 (없으면 MD만 생성)
- 한글 폰트 (macOS AppleGothic 자동 / Linux NanumGothic 설치)

자세한 사용법·옵션·효율 등급 규칙은 `SKILL.md` 참고.

## 프리셋
`this_week`(월~오늘) · `last_7_days` · `last_14_days` · 또는 `--start/--end`.
WoW는 직전 동일길이 기간을 자동 비교.
