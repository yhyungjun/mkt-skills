# Toss Payments 설정 절차

> 결제. env 키: `TOSS_CLIENT_KEY`(브라우저 위젯·공개), `TOSS_SECRET_KEY`(서버 승인 API·Basic 인증).
> 결제 활성화: `PAYMENT_OPEN_AT`(날짜 게이팅) + `isPaymentEnabled()`(요청시점 평가), `NEXT_PUBLIC_PAYMENT_ENABLED`=수동 오버라이드. 웹훅 경로: `/api/toss/webhook`.
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
   - ⚠️ **심사 종료 후 이 백도어는 반드시 제거**한다(아래 6-C). 방치하면 무단 로그인·중복 신청행 누적.
4. 심사 결과에 맞춰 정식 전환(아래 6번) 진행.

## 4. 웹훅 URL 등록 (`/api/toss/webhook`)
1. 콘솔에서 **웹훅(Webhook)** 설정 메뉴 찾기.
2. 결제 상태 변경 이벤트 수신 URL 등록:
   - `https://<프로덕션도메인>/api/toss/webhook`
3. **왜 필요한가(중요)**: 사용자가 결제 인증 후 success로 **리다이렉트되기 전 창을 닫으면
   토스엔 승인됐는데 우리 DB(payments)엔 미기록**되는 누락이 생긴다. 웹훅으로 이를 보정
   (서버가 승인 이벤트를 받아 payments를 동기화)한다.
4. 웹훅 핸들러는 멱등(같은 paymentKey 재수신 시 중복 INSERT 안 함)하게 구현.

## 5. 결제 활성화 토글 시점
- 결제 비활성 → CTA가 사전예약(`/preorder` 등) 동선. 활성 → `/pay` 결제 동선.
- **권장 순서**: 사전예약으로 먼저 오픈 → PG 심사 통과 + 실키 교체 + 웹훅 등록 완료 후 결제로 전환.
  심사 미통과 상태에서 켜면 실결제가 깨진다.
- 단순 불리언(`NEXT_PUBLIC_PAYMENT_ENABLED`)보다 **날짜 게이팅 함수**가 낫다 → 6-B 참조
  (예약 오픈 시각을 코드에 박아 재배포 없이 자동 전환).

## 6. PG 심사 통과 후 → 정식 전환 (실전 체크리스트)

> granter-landing 실제 전환 과정을 정리. **심사 통과 시점에 A~E를 한 번에** 처리한다.

### A. 키 전환 (테스트 → 라이브)
- 개발자센터에서 **라이브 Client/Secret Key** 발급 → env 교체:
  - `NEXT_PUBLIC_TOSS_CLIENT_KEY` = 라이브 client (public/`vars`)
  - `TOSS_SECRET_KEY` = 라이브 secret (`wrangler secret put` / Vercel env, **서버 전용**)
- 웹훅 URL을 **프로덕션 도메인**으로 등록·확인(4번).

### B. 결제 활성화 = 빌드 상수 ❌ → 요청시점 평가 ✅ (핵심 함정)
> `PAYMENT_ENABLED = process.env… === "true"`(모듈 **상수**)는 **정적 렌더에서 빌드 시점 값으로 굳어**,
> 날짜 자동 오픈·env 변경이 재배포 없이는 반영 안 된다. **함수로 바꿔 요청 시점에 평가**한다.

```ts
// lib/config.ts
export const PAYMENT_OPEN_AT = "2026-06-29T00:00:00+09:00"; // 정식 오픈 시각(KST)

/** 요청 시점 평가 — 모듈 상수로 캐시 금지. 정적 렌더에서 호출하면 빌드값으로 굳으니 금지. */
export function isPaymentEnabled(now: number = Date.now()): boolean {
  if (process.env.NEXT_PUBLIC_PAYMENT_ENABLED === "true") return true; // 수동 오버라이드(긴급)
  return now >= new Date(PAYMENT_OPEN_AT).getTime();                    // 날짜 도달 시 자동 오픈
}
export function postOnboardingPath(): string {
  return isPaymentEnabled() ? "/pay" : "/preorder";
}
```
- `/pay`(동적·auth 페이지): 맨 앞에 `if (!isPaymentEnabled()) redirect("/preorder");` — 오픈 전 진입 차단.
- 랜딩 CTA는 **클라이언트 날짜 게이팅 컴포넌트**(마운트 후 재평가)로 → **정적 페이지 재배포 없이** 사전예약↔결제 자동 전환.
- `env=true`는 날짜 무관 즉시 오픈(수동 오버라이드)으로 남겨 둔다.

### C. 심사용 백도어 제거 (심사 종료 후 필수 · 보안)
심사 때 쓴 임시 로그인·자동 신청행은 **끝나면 반드시 제거**(방치 시 무단 로그인·중복행 누적):
- `auth.ts`: `Credentials("toss-review")` provider·`isReview` 분기·bcrypt 의존 제거.
- `/pay`: `@review.*` 심사계정 **자동 신청행 INSERT 블록 제거**(중복 신청행 누적의 근본 원인).
- `/signin`: 심사용 로그인 UI(ReviewSignInForm) 삭제.
- env: `TOSS_REVIEW_ID`·`TOSS_REVIEW_PASSWORD_HASH_B64` 제거.

### D. 위젯 렌더 함정 — `variantKey` 필수
토스 v2 위젯은 `variantKey` 없이 호출하면 "알 수 없는 에러가 발생했습니다"로 렌더 실패:
```ts
widgets.renderPaymentMethods({ selector: "#payment-method", variantKey: "DEFAULT" });
widgets.renderAgreement({ selector: "#agreement", variantKey: "AGREEMENT" });
```

### E. 스모크 (전환 직후)
실키로 **실거래 1건** 승인 → `payments`/`applications` 갱신 → 결제완료 메일 → 토스 콘솔 대조
→ **웹훅 동기화 확인** → (가능하면) 취소/환불 1건까지.

## 흔한 함정 요약
- 테스트 키로 운영 오픈 → 실결제 안 됨. 실키 교체 + 결제 활성화 동시 점검.
- **결제 활성화를 모듈 상수로 두면 정적 렌더에서 굳음** → 날짜/ env 전환이 재배포 없인 반영 안 됨. 요청시점 함수(`isPaymentEnabled()`)로(6-B).
- **심사 백도어 방치** → 무단 로그인·중복 신청행 누적. 심사 종료 시 즉시 제거(6-C).
- 위젯 `variantKey` 누락 → "알 수 없는 에러"로 렌더 실패(6-D).
- 웹훅 미등록 → 창 닫힘/네트워크 끊김 시 결제 누락(승인됐는데 DB 없음).
- secret 키 클라이언트 노출 → 즉시 재발급.
- 사업자 정보 불일치로 심사 반려 → 등록증 기준으로 통일.
