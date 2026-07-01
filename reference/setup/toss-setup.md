# Toss Payments 설정 절차

> 결제. env 키: `TOSS_CLIENT_KEY`(브라우저 위젯·공개), `TOSS_SECRET_KEY`(서버 승인 API·Basic 인증).
> 결제 활성화 토글: `NEXT_PUBLIC_PAYMENT_ENABLED`. 웹훅 경로: `/api/toss/webhook`.
> PG 심사용 임시계정 키: `TOSS_REVIEW_ID`, `TOSS_REVIEW_PASSWORD_HASH_B64`.
> 콘솔 UI 라벨은 자주 바뀌므로 "~ 찾기"로 기술.

## 1. 가맹점 가입
1. https://www.tosspayments.com → 회원가입/가맹점 신청.
2. 개발자센터(https://developers.tosspayments.com) 로그인 → 상점/테스트 환경 확인.
3. 사업자 정보(상호·대표·사업자번호·정산 계좌 등)는 사업자등록증과 **일관되게** 입력
   (PG 심사에서 불일치 시 반려).

## 2. 테스트 키 → 실키 발급
1. 개발자센터에서 **API 키** 메뉴 찾기.
2. 처음엔 **테스트 키**(client/secret)로 개발:
   - 테스트 Client Key → `TOSS_CLIENT_KEY`
   - 테스트 Secret Key → `TOSS_SECRET_KEY`
3. PG 심사 통과 후 **실(라이브) 키**로 교체.
   - secret 키는 서버 결제승인 API에서 **Basic 인증**(`{secret}:` base64)으로 사용.
   - ⚠️ `TOSS_SECRET_KEY`는 서버 라우트/서버액션에서만. 클라이언트 노출 금지.

## 3. PG 심사 절차
1. 콘솔에서 **계약/심사** 관련 메뉴 찾기 → 서류 제출(사업자등록증, 대표자 정보, 정산계좌 등).
2. 심사 중에는 결제수단 활성화·라이브 키 사용이 제한될 수 있다.
3. **심사용 임시계정**(Credentials provider)으로 심사자가 결제 직전까지 검증하도록 함:
   - `TOSS_REVIEW_ID` = 심사용 로그인 ID.
   - `TOSS_REVIEW_PASSWORD_HASH_B64` = 비밀번호의 **bcrypt 해시를 base64 인코딩**한 값.
4. 심사 결과에 맞춰 `NEXT_PUBLIC_PAYMENT_ENABLED` 토글(아래 5번).

## 4. 웹훅 URL 등록 (`/api/toss/webhook`)
1. 콘솔에서 **웹훅(Webhook)** 설정 메뉴 찾기.
2. 결제 상태 변경 이벤트 수신 URL 등록:
   - `https://<프로덕션도메인>/api/toss/webhook`
3. **왜 필요한가(중요)**: 사용자가 결제 인증 후 success로 **리다이렉트되기 전 창을 닫으면
   토스엔 승인됐는데 우리 DB(payments)엔 미기록**되는 누락이 생긴다. 웹훅으로 이를 보정
   (서버가 승인 이벤트를 받아 payments를 동기화)한다.
4. 웹훅 핸들러는 멱등(같은 paymentKey 재수신 시 중복 INSERT 안 함)하게 구현.

## 5. PAYMENT_ENABLED 토글 시점
- `NEXT_PUBLIC_PAYMENT_ENABLED=false` → 결제 비활성. CTA가 사전예약(`/preorder` 등) 동선.
- `NEXT_PUBLIC_PAYMENT_ENABLED=true` → `/pay` 결제 동선 활성.
- **권장 순서**: 사전예약(false)으로 먼저 오픈 → PG 심사 통과 + 실키 교체 + 웹훅 등록 완료
  후 `true`로 전환. 심사 미통과 상태에서 true로 켜면 실결제가 깨진다.

## 흔한 함정 요약
- 테스트 키로 운영 오픈 → 실결제 안 됨. 실키 교체 + PAYMENT_ENABLED 동시 점검.
- 웹훅 미등록 → 창 닫힘/네트워크 끊김 시 결제 누락(승인됐는데 DB 없음).
- secret 키 클라이언트 노출 → 즉시 재발급.
- 사업자 정보 불일치로 심사 반려 → 등록증 기준으로 통일.
