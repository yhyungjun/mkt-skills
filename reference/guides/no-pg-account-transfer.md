# 계좌이체 트랙 — PG 없는 신청·입금 동선 (Track B 결제 생략 구체화)

> **출처**: 강의 랜딩 사례 — 토스 PG·소셜로그인·SMS·`PAYMENT_ENABLED`를 **의도적으로 제외**하고
> 네이티브 신청폼 + **계좌이체** + 자동 안내메일 + 운영자 Slack 알림으로 끝낸 실제 구성.
> **언제**: PG 심사 전/소규모/B2B 청구서 결제처럼 "신청 받고 입금은 계좌이체"가 맞는 강의.
> playbook의 Track B에서 **P6 결제·P9 인증(수강생)·온보딩/SMS를 통째로 생략**한 형태.

---

## 동선 (한 줄)
```
랜딩 → /apply 폼 제출 → applications INSERT(status='pending')
     → 고객에게 입금안내 메일(Resend) + 운영자 Slack 알림
     → 운영자가 입금 확인 → 어드민에서 status='confirmed' 로 변경
     → 남은 자리 = 정원 − confirmed 수
```
- **로그인 없음**: 공개 엔드포인트 → 허니팟 + (권장)레이트리밋으로 보호(playbook P5).
- **인증은 어드민만**: Google role 하나. 토스/카카오/네이버/OCTOMO 패턴은 빼고 되살리지 않는다.

## config — 계좌·정원·마감 단일 출처 (`lib/config.ts`)
```ts
export const SEATS = { capacity: 30 } as const; // 남은 자리 = capacity − confirmed
export const APPLY_DEADLINE = "2026-06-26T23:59:59+09:00"; // KST, 카운트다운 종료
export const BANK = {
  bank: "신한은행", account: "000-000-000000", holder: "주식회사 …",
} as const; // Pricing·신청완료 화면·메일에 노출
export const PRIMARY_CTA_HREF = "/apply";
```

## 남은 자리 카운터 (PG 카운터 대체)
얼리버드 결제 수 대신 **`status='confirmed'` 신청 수**로 좌석을 센다.
```ts
// GET /api/applications  (또는 /api/counter)
const { count } = await supabase.from(APPLICATIONS_TABLE)
  .select("id", { count: "exact", head: true })
  .eq("cohort", SITE.cohort).eq("status", "confirmed");
const remaining = Math.max(0, SEATS.capacity - (count ?? 0));
// env 미설정(stub)·에러 시 capacity 전체 반환 → FloatingBar/StickyCTA 폴링
```

## 입금안내 메일 (결제완료 메일 대체)
`lib/email.ts` `sendApplicationEmail(to, name, variant)` — Resend REST 직접 호출(패키지 의존 없이 Workers 동작).
본문에 **과정 안내 + 입금계좌(BANK) + 세금계산서 안내 + (선택)진단설문 링크**. 금액은 `priceForVariant(variant)`로 재계산
([[price-variant]] 참조 — 변형별 금액을 클라가 아니라 서버 메일에서 확정). `RESEND_API_KEY` 미설정 시 스텁(스킵).

## 신청폼 필드 (B2B 입금/세금계산서 대응)
- 필수: 이름·전화·이메일 + **사업자명·사업자번호·직무/직책 + 세금계산서 필요여부**(필요 시 발행 이메일).
- 서버 검증: 이메일/전화 정규식, 필수 누락, 중복(같은 이메일+cohort=409), 허니팟(`company` 채워지면 조용히 성공).
- 제출 성공 → 메일 + Slack([[slack-notify]]) → `/apply/done`(입금계좌·다음 안내 노출).

## 어드민 — 상태 관리 = 입금 확인 워크플로
- 신청 표에서 `pending → confirmed`(입금확인) / `cancelled` 상태 변경 액션 버튼.
- confirmed 수가 곧 좌석 카운터 → 어드민 액션이 랜딩 "남은 자리"에 즉시 반영.
- 결제 PG가 없으므로 환불=계좌 반환(수동) + status 동기화. 환불정책(P0)과 문구 일치.

## 빼는 것 (되살리지 말 것 — AGENTS.md에 명시 권장)
- ❌ Toss 위젯/`/pay`·`/pay/success`·`/api/counter(결제수)`·웹훅
- ❌ 소셜로그인(Google/Kakao/Naver) 수강생 계정 · `/signin`·`/signup`·`/onboarding`·SMS(OCTOMO)
- ❌ `NEXT_PUBLIC_PAYMENT_ENABLED` 분기 (동선이 한 갈래뿐)

## 풀스택 결제가 필요해지면
PG 심사 통과·수강생 계정·자동 영수증이 필요하면 playbook **Track A**로 승격: P4 DB·P9 인증을 섹션 앞으로,
P6 결제(Toss)·P7 결제완료 메일·`PAYMENT_ENABLED` 도입. 계좌이체 트랙은 그 전 단계의 가벼운 출발점.
