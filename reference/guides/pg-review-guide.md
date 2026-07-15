# PG 심사 대응 가이드 — 토스페이먼츠

> 국내 PG(토스페이먼츠 등) **가맹점 심사**를 한 번에 통과하기 위한 체크리스트와, 심사 기간 동안
> 사이트를 어떻게 운영하는지(사전예약 모드 + 심사용 계정)에 대한 실전 가이드.
> granter-landing 실제 구현(`Credentials("toss-review")` 계정 + `PAYMENT_ENABLED` 토글)을 정리.

---

## 0. 큰 그림 — 심사 전/중/후 운영 전략

PG 심사는 보통 며칠~2주 걸린다. 그동안 사이트를 멈추지 말고 **사전예약으로 리드를 모은다.**

```
[심사 신청 전]  PAYMENT_ENABLED=false → 모든 CTA가 /signup → /preorder (결제 없이 리드 수집)
[심사 중]       동일. 단, 심사관이 결제 플로우를 테스트할 수 있도록 "심사용 계정"으로 /pay 접근 가능
[심사 통과 후]  실 키로 교체 + PAYMENT_ENABLED=true → CTA가 /pay (실결제)
```

핵심 스위치(플레이북 §핵심 스위치):
```ts
PRIMARY_CTA_HREF     = PAYMENT_ENABLED ? "/pay" : "/signup"
POST_ONBOARDING_PATH = PAYMENT_ENABLED ? "/pay" : "/preorder"
```
→ 불리언 하나로 전체 동선 전환. **코드 수정 없이** 심사 결과에 맞춰 토글.

---

## 1. 심사 시 확인하는 항목 (= 미리 갖춰야 할 것)

PG/카드사 심사관이 실제로 보는 것들. 하나라도 비면 반려.

### (1) 사업자 정보 일관성 ★가장 흔한 반려 원인
- 사이트 **Footer의 사업자 정보**가 사업자등록증·통신판매업 신고와 **글자 단위로 일치**:
  - 상호 / 대표자명 / 사업자등록번호 / **통신판매업 신고번호** / 사업장 주소 / 대표 연락처 / 고객센터.
- 결제창에 표시될 **상점명(상호)**과 사이트 표기 일치.
- ⚠️ 띄어쓰기·법인격(주식회사/(주)) 표기까지 통일. 심사관은 등록증과 1:1 대조한다.
- ⏱️ **통신판매업 신고번호는 순서상 PG 승인 *후* 에 생긴다**(chicken-and-egg 주의): PG 심사 통과 → PG사가 **구매안전서비스 이용확인증(에스크로)** 발급 → 그 확인증으로 관할 구청 신고 → 신고번호 발급. 따라서 **초기 PG 심사 제출 시엔 Footer에 신고번호가 없어도 정상**(일부 카드사만 요구). 발급 후 **Footer + 약관 3p에 채우고 재배포**한다. 상세 순서 = `playbook.md` Phase 12 "통신판매업 신고 → 신고번호 게시".

### (2) 약관·정책 페이지 실재 + 링크
- `/terms`(이용약관) · `/privacy`(개인정보처리방침) · `/refund`(환불정책)가 **실제 접근 가능**하고 Footer에서 링크.
- 환불정책에 **단계별 환불 기준이 구체적으로** 적혀 있어야 함(추상적 "환불 가능" ✕). → `legal-boilerplate.md`.

### (3) 판매 상품의 실재성·명확성
- 무엇을 파는지(강의명·기간·형식·**가격**)가 사이트에 **명확히 표시**.
- 가격이 결제 금액과 일치. 할인이면 정가·할인가 함께.
- "추상적 서비스/선결제만 있고 상품 불명확"이면 반려 위험.

### (4) 실제 결제 플로우 동작
- 심사관이 **결제 화면까지 진입**해 결제수단·약관동의 위젯이 정상 렌더되는지 확인.
- 결제 성공/실패 후 안내 페이지(`/pay/success`, `/pay/fail`)가 정상.
- → 그래서 **심사용 계정**이 필요(아래 §3).

### (5) 연락 가능성
- 고객센터 전화/이메일이 실재하고 응답 가능.

---

## 2. 흔한 반려 사유 (사전 점검)

| 반려 사유 | 예방 |
|---|---|
| 사업자 정보 불일치 | Footer ↔ 등록증 글자 대조. 통신판매업 신고번호 누락 주의. |
| 환불정책 불충분/부재 | 단계별 환불표 + 본문 조항 게시. 약관·FAQ와 숫자 일치. |
| 약관/개인정보 페이지 없음·링크 깨짐 | 3개 페이지 실재 + Footer 링크 + 배포본에서 실제 접속 확인. |
| 판매 상품 불명확 | 상품명·가격·제공 내용 명시. |
| 결제 테스트 불가 (로그인 막힘) | 심사용 계정 제공(§3). |
| 미허용 업종/콘텐츠 | 업종코드·판매물이 PG 정책에 부합하는지 사전 확인. |
| 도메인 미연결/임시 페이지 | 실도메인 배포 후 신청. localhost·프리뷰 URL로 신청 금지. |

---

## 3. 심사용 계정 패턴 (`@review.*` Credentials)

소셜 로그인만 있으면 심사관이 실제 카카오/구글 계정으로 가입해야 해서 번거롭고, 신청 데이터도
없어 결제 화면 진입이 막힌다. 해결책: **이메일/비밀번호 Credentials provider를 심사 전용으로** 추가.

### 동작
1. **Credentials provider `"toss-review"`** 등록 (Auth.js v5). 이메일+비밀번호로 로그인.
   - 비밀번호는 bcrypt 해시 비교(평문 저장 금지).
   - 허용 계정은 `@review.*` 도메인 이메일 등으로 한정(일반 사용자 가입 경로와 분리).
2. **신청 자동 생성**: 심사 계정으로 `/pay` 진입 시 `applications`에 신청 레코드가 없으면
   **즉석에서 pending 신청을 생성** → 결제 화면으로 바로 진행 가능.
   - granter 패턴: `@review.*` 계정은 신청 없으면 즉석 pending 생성.
3. 심사관에게 **이메일/비밀번호 + 접속 URL + "이 계정으로 로그인 후 결제하기"** 안내를 전달.

### 구현 스케치 (Auth.js v5)
```ts
// lib/auth.ts — providers 배열에 추가
Credentials({
  id: "toss-review",
  name: "Review",
  credentials: { email: {}, password: {} },
  async authorize(creds) {
    const email = String(creds?.email ?? "");
    // 심사 전용 계정으로 한정 (일반 가입과 분리)
    if (!email.endsWith("@review.local")) return null;
    const ok = await bcrypt.compare(String(creds?.password ?? ""), REVIEW_HASH);
    if (!ok) return null;
    return { id: `review-${email}`, email, name: "PG Review" };
  },
}),
```
```ts
// /pay page.tsx — 신청 없으면 즉석 생성 (심사관 결제 테스트용)
let app = await findApplication(userId);
if (!app && session.user.email?.endsWith("@review.local")) {
  app = await createPendingApplication(userId); // status: 'pending'
}
```
⚠️ 심사 **진행 중**에는 계정·도메인을 엄격히 제한(누구나 결제 우회 금지), 비밀번호 해시는 env/secret으로(평문/하드코딩 금지).
심사가 **완전히 종료되면 이 백도어는 제거**한다(방치 시 무단 로그인·중복 신청행 누적) — 제거 항목은 `setup/toss-setup.md` 6-C.

---

## 4. 심사 중 사전예약 운영 (`PAYMENT_ENABLED=false`)

- 일반 방문자: CTA → `/signup` → 온보딩 → `/preorder`(설문) → `/preorder/done`. **결제 없음.**
- 사전예약자는 마케팅 동의 시 `email_sends`로 일괄 안내(오픈 시 결제 링크).
- 심사관만 §3 계정으로 `/pay` 도달 가능(일반 CTA로는 노출 안 됨).
- 통과되면 **정식 전환**(전체 절차 = `setup/toss-setup.md` 6번):
  1. 토스 **실 키로 교체**(`TOSS_CLIENT_KEY` 공개키 / `TOSS_SECRET_KEY` 서버 시크릿) + **웹훅 실도메인 등록**.
  2. 결제 활성화를 **요청시점 함수**(`isPaymentEnabled()`+`PAYMENT_OPEN_AT` 날짜 게이팅)로 → 정적 렌더에 굳는 함정 회피.
  3. **심사용 백도어 제거**(§3 provider·`@review.*` 자동신청·심사 로그인 UI·관련 env).
  4. 위젯 `variantKey` 확인 + 실거래 1건 스모크.

⚠️ **키 혼동 금지**: `TOSS_CLIENT_KEY`는 브라우저 노출(공개, 위젯 초기화용), `TOSS_SECRET_KEY`는
서버 승인(`/v1/payments/confirm`, `Authorization: Basic base64(SECRET:)`)에서만. 시크릿이
클라이언트 번들에 들어가면 즉시 노출 사고.

---

## 5. 심사 제출 직전 체크리스트

- [ ] 실도메인에 배포 완료 (프리뷰/localhost 아님).
- [ ] Footer 사업자 정보 = 등록증 글자 단위 일치(통신판매업 신고번호 포함).
- [ ] `/terms` `/privacy` `/refund` 실접속 + Footer 링크 정상.
- [ ] 환불정책에 단계별 기준 명시, 약관·FAQ와 숫자 일치.
- [ ] 상품명·가격·제공 내용이 사이트에 명확.
- [ ] 심사용 계정(이메일/비번/URL/안내문) 준비 + 로그인→결제까지 직접 1회 테스트.
- [ ] `PAYMENT_ENABLED=false`로 일반 동선은 사전예약, 심사 계정만 결제 도달 확인.
- [ ] 고객센터 연락처 응답 가능.
