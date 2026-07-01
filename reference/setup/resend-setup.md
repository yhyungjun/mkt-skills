# Resend 설정 절차 (메일 발송)

> 결제완료/사전예약 메일 발송. env 키: `RESEND_API_KEY`.
> 콘솔 UI 라벨은 자주 바뀌므로 "~ 찾기"로 기술.

## 1. API 키 발급
1. https://resend.com 로그인 → **API Keys** 메뉴 찾기 → Create.
2. 발급된 키 → `RESEND_API_KEY` (서버 전용. 클라이언트 노출 금지).
> 도메인 인증 전이라도 Resend의 샌드박스 발신주소(예: onboarding@resend.dev)로
> 본인에게 테스트 발송은 가능. 실서비스 발송은 아래 도메인 인증 필요.

## 2. 도메인 추가
1. **Domains** 메뉴 찾기 → Add Domain → 발송에 쓸 도메인 입력(예: `yourco.ai`
   또는 서브도메인 `mail.yourco.ai`).
2. 추가하면 등록해야 할 **DNS 레코드 목록**을 보여준다.

## 3. DNS 레코드 (SPF · DKIM · DMARC)
도메인 DNS 관리(Cloudflare DNS 등)에 Resend가 안내한 값을 그대로 추가:
1. **SPF** — TXT 레코드. 발신 서버를 인증(보통 `include:` 형태).
2. **DKIM** — Resend가 주는 TXT(또는 CNAME) 레코드. 서명 키.
3. **DMARC** — TXT 레코드(`_dmarc` 호스트). 정책(예: `p=none`으로 시작 권장).
4. 등록 후 Resend 콘솔에서 **Verify**(검증) → 상태가 Verified가 될 때까지 대기
   (DNS 전파로 수분~수시간 소요될 수 있음).
> Cloudflare DNS 사용 시: 프록시(주황 구름) 끄고 **DNS only**로 두는 게 안전(메일 레코드는 프록시 대상 아님).

## 4. 발신 주소
- 인증된 도메인의 주소로 발신(예: `no-reply@yourco.ai`).
- From 표시 이름 + 주소 형태(`그랜터 <no-reply@yourco.ai>`)로 가독성 향상.
- 미인증 도메인 주소로는 실발송 거부되거나 스팸 처리됨.

## 5. 신규 도메인 워밍업
- 갓 인증한 도메인/IP는 평판이 없어 초기 발송이 스팸으로 갈 수 있다.
- **워밍업**: 처음엔 소량(본인·내부 수신자)부터 보내고 점진적으로 발송량을 늘린다.
- 오픈/클릭이 잘 나오는 수신자부터 → 평판 축적 후 대량 캠페인.
- DMARC를 `p=none`으로 모니터링하다 안정되면 정책 강화.

## 흔한 함정 요약
- DNS 미검증 상태로 실발송 → 미도착/스팸. Verified 확인 후 발송.
- SPF/DKIM 중 하나만 설정 → 일부 수신처에서 반려. 셋 다(SPF·DKIM·DMARC) 권장.
- Cloudflare DNS에서 메일 TXT 레코드를 프록시 ON으로 둠 → 검증 실패. DNS only로.
- 신규 도메인 첫날 대량 발송 → 평판 하락. 워밍업 필수.
