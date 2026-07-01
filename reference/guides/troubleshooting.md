# 트러블슈팅 — 알려진 함정 모음

> granter-landing 빌드에서 실제로 밟았거나 밟기 쉬운 함정들. **증상 → 원인 → 해결** 형식.
> 빌드 중 막히면 Ctrl+F로 증상을 찾는다. Phase는 `playbook.md` 기준.

---

## 1. Turbopack이 globals.css 변경을 반영 안 함 (Phase 1)
- **증상**: `globals.css`의 토큰·색을 바꿨는데 브라우저에 안 먹는다. 새로고침·하드리로드해도 옛 스타일.
- **원인**: Turbopack의 CSS 캐시가 변경을 못 잡는 경우.
- **해결**: dev 서버 끄고 `.next` 캐시 비우고 재시작.
  ```bash
  rm -rf apps/web/.next && cd apps/web && npm run dev
  ```

---

## 2. 카카오 로그인에 이메일이 안 옴 (Phase 9)
- **증상**: 카카오 OAuth는 되는데 프로필에 이메일이 없어 `users` upsert가 깨지거나 null.
- **원인**: **카카오 비즈앱 전환 + 동의항목 검수 전**에는 이메일·전화 같은 민감정보를 제공하지 않는다.
- **해결**:
  - placeholder 이메일로 채워 가입은 통과시킨다: `kakao_{kakaoId}@placeholder.local`.
  - 전화·이메일 필수 동의는 **비즈앱 검수 통과 후** `OAUTH_REQUEST_CONTACT=true`로 켠다.
  - 온보딩(`/onboarding`)에서 전화번호를 따로 수집해 보완.

---

## 3. email_events 테이블 누락 → 트래킹 API 500 (Phase 4/8)
- **증상**: `/api/track/open`·`/api/track/click` 호출 시 에러. 메일 오픈/클릭이 안 쌓인다.
- **원인**: 마이그레이션에서 `email_events` 테이블이 빠졌던 전례. 트래킹 API가 이 테이블을 INSERT한다.
- **해결**: `reference/db-schema.sql` 적용 시 `email_events` 포함 확인. `list_tables`로 7개 테이블
  (users·applications·payments·otp_codes·admins·email_sends·**email_events**) 전부 존재 확인.

---

## 4. Tailwind v4 폰트 @import 순서로 폰트 미적용 (Phase 2)
- **증상**: 웹폰트(Pretendard 등) `@import`했는데 적용 안 되거나 콘솔 경고.
- **원인**: CSS `@import`는 **다른 규칙보다 먼저** 와야 한다. Tailwind v4의 `@import "tailwindcss"`와
  폰트 `@import` 순서가 어긋나면 무시된다.
- **해결**:
  - 본문 웹폰트는 `globals.css` `@import`에 의존하지 말고 **`layout.tsx` `<head>`의 `<link>`**로 로드.
  - 모노 폰트는 `next/font`로. (스켈레톤 `design-system-skeleton.css` 주석 참조.)
  - 굳이 CSS에서 import하면 **파일 최상단**, Tailwind import보다 앞에.

---

## 5. 설문 컬럼 동적 생성 → 스키마 드리프트 (Phase 4/5)
- **증상**: 폼 필드를 추가했는데 INSERT 실패, 또는 환경마다 `applications` 컬럼이 다름.
- **원인**: 설문 컬럼을 마이그레이션에 명시하지 않고 **코드 INSERT로 동적 생성**해서 스키마가 환경별로 어긋남.
- **해결**: 설문 필드는 **Phase 0에서 확정한 목록 그대로 마이그레이션(schema.sql)에 명시**.
  `text`/`text[]` 매핑만 코드에서. 필드 추가 시 마이그레이션 먼저.

---

## 6. Apps Script에 Supabase secret 하드코딩 노출 (Phase 7)
- **증상**: 대량 발송용 Google Apps Script에 service_role 키가 평문으로 박혀 유출 위험.
- **원인**: 스크립트 본문에 secret 하드코딩.
- **해결**: **스크립트 속성(Script Properties)/환경**으로 키를 옮긴다. 코드엔 키 문자열 금지.
  이미 커밋·공유됐다면 **키 로테이션**.

---

## 7. 결제 success 리다이렉트 누락 = 승인됐는데 DB 미기록 (Phase 6)
- **증상**: 토스 콘솔엔 결제 승인인데 우리 `payments`/`applications`엔 기록이 없음. 사용자는 돈 냈는데 미반영.
- **원인**: 승인 로직이 **`/pay/success` 리다이렉트에만** 있어서, 사용자가 결제 후 리다이렉트 전에
  창을 닫으면 confirm 호출이 안 됨.
- **해결**: **Toss 웹훅(`/api/toss/webhook`)을 진실 원천**으로 추가.
  - 웹훅에서 결제상태를 서버 재동기화. `toss_order_id` **unique**로 멱등 처리(중복 INSERT 방지).
  - success 리다이렉트는 UX용, 웹훅은 데이터 정합성용. 둘 다 둔다.
  - 배포 시 토스 콘솔에 **웹훅 URL 등록** 필수.

---

## 8. onboarded_at 판정 누락 → 보호 페이지 우회/오류 (Phase 4/9/5)
- **증상**: 온보딩 안 한 사용자가 결제/사전예약에 들어가거나, 반대로 끝난 사람이 다시 온보딩으로 튕김.
- **원인**: `users.onboarded_at` null 여부가 온보딩 완료 판정 기준인데, 일부 보호 페이지에서 체크 누락.
- **해결**: **모든 보호 페이지**에서 `onboarded_at` 체크.
  - null이면 `/onboarding`으로, 값 있으면 통과. 판정 기준을 한 군데(유틸)로 통일.

---

## 9. TOSS_CLIENT_KEY vs TOSS_SECRET_KEY 혼동 (Phase 6)
- **증상**: 위젯이 초기화 안 되거나, 결제 승인이 401. 또는 시크릿이 클라이언트 번들에 노출.
- **원인**: 두 키의 역할을 바꿔 씀.
- **해결**:
  - `TOSS_CLIENT_KEY` = **브라우저 노출(공개)**. 위젯 초기화 `TossPayments(clientKey)`에만.
  - `TOSS_SECRET_KEY` = **서버 전용**. 승인 `POST /v1/payments/confirm`의
    `Authorization: Basic base64(SECRET:)`에만. **절대 `NEXT_PUBLIC_`로 노출 금지.**
  - 테스트키/실키 전환 시 둘 다 같은 환경(test↔live)으로 교체했는지 확인.

---

## 빠른 진단표

| 증상 키워드 | 항목 |
|---|---|
| CSS 안 먹음 / 스타일 캐시 | §1 Turbopack `.next` |
| 카카오 이메일 null | §2 비즈앱 placeholder |
| track API 500 / 메일통계 안쌓임 | §3 email_events |
| 폰트 미적용 | §4 @import 순서 |
| INSERT 실패 / 컬럼 다름 | §5 스키마 드리프트 |
| 키 유출 / Apps Script | §6 Script Properties |
| 결제했는데 미기록 | §7 웹훅 |
| 보호 페이지 우회/튕김 | §8 onboarded_at |
| 위젯 초기화 안됨 / 승인 401 | §9 CLIENT vs SECRET |
