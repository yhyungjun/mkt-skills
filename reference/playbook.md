# 강의 랜딩페이지 풀스택 빌드 플레이북

> **목적**: 강의(온라인/오프라인) 사전예약·결제 랜딩을 **시간낭비 없이 순차로** 다시 만들기 위한 마스터 가이드.
> granter-landing(조코딩AX 셀러OS) 실제 구현을 역설계해 정리. 기획 → 셋업 → 디자인 → 섹션 → DB →
> 폼 → 결제 → 메일 → 트래킹 → 인증 → 어드민 → 마감 → 배포 → QA까지 전 영역.
>
> **사용법**: Phase 0부터 순서대로. 각 Phase는 앞 Phase 산출물에 의존하므로 순서를 지키면 막힘이 없다.
> Claude에게 "이 플레이북대로 Phase N 구현해줘"라고 단계별로 시키면 된다.
>
> 🔢 **번호 = 빌드 순서**는 **Track B(랜딩 우선)** 기준이다(맨 아래 "순서 변형 트랙" 참조).
> 풀스택 결제+소셜로그인(Track A)은 DB·인증을 섹션 앞으로 당긴다.

---

## 📐 검증된 기술 스택 (그대로 채택 권장)

| 영역 | 선택 | 비고 |
|---|---|---|
| 프레임워크 | **Next.js 16 App Router** + React 19 | 풀스택(서버액션·API라우트) |
| 스타일 | **Tailwind CSS 4** + CSS 토큰(globals.css `:root`) | 디자인 시스템 |
| DB | **Supabase (PostgreSQL)** | 서버에서 service_role로만 접근 |
| 인증 | **Auth.js v5 (NextAuth)** JWT 세션 | Google·Kakao·Naver |
| 결제 | **Toss Payments v2 위젯** | 국내 PG |
| 메일 | **Resend**(결제완료) + **Google Apps Script**(대량 발송) | 이원화 |
| SMS 인증 | **OCTOMO**(역방향 문자 인증) | 선택 |
| 배포 | **Cloudflare Workers** (@opennextjs/cloudflare) | Vercel도 가능 |
| 분석 | **GTM → GA4** | 코드는 dataLayer push만 |

폰트: Pretendard(CDN link) + IBM Plex Mono(next/font). 차트(어드민): Recharts.

---

## 🗺️ 전체 라우팅 맵 (목표 산출물)

```
/                     랜딩 본문 (섹션 16개)
/signin /signup       소셜 로그인 / 가입(약관동의)
/onboarding           전화번호 수집 + SMS 인증
/preorder  /preorder/done    사전예약 설문 (PAYMENT_ENABLED=false)
/pay  /pay/success  /pay/fail 결제 (PAYMENT_ENABLED=true)
/apply  /apply/done   신청 폼
/terms /privacy /refund      약관/정책
/admin  /admin/signin /admin/users /admin/applications  어드민 + CSV export
/api/auth/[...nextauth]      NextAuth 핸들러
/api/applications            신청 INSERT
/api/counter                 결제완료 수(얼리버드 카운터)
/api/otp/send /api/otp/verify  SMS OTP
/api/track/open /api/track/click  메일 추적
```

### 🔑 핵심 스위치 — `NEXT_PUBLIC_PAYMENT_ENABLED`
하나의 불리언이 전체 동선을 전환한다. **이 패턴을 그대로 채택**하면 PG 심사 대기 중엔 사전예약,
승인 후엔 결제로 코드 수정 없이 전환된다.
```ts
// lib/config.ts 류
PRIMARY_CTA_HREF     = PAYMENT_ENABLED ? "/pay" : "/signup"
POST_ONBOARDING_PATH = PAYMENT_ENABLED ? "/pay" : "/preorder"
```

---

# STEP 0 — 결제 방식 선택 (구성 1순위 분기)

> **가장 먼저 고른다.** "결제를 어떻게 받는가"가 페이지·lib·env·인증·트랙(A/B)을 통째로 결정한다.
> 아래 3모델 중 **택1**(또는 하이브리드) → 표가 가리키는 모듈만 빌드하고 나머지는 **만들지 않는다**.
> 이건 빌드타임 구성 선택이다(스킬이 P0에서 묻고 그에 맞춰 조립). 모델 1 안의 사전예약↔결제 전환은
> 런타임 토글 `PAYMENT_ENABLED`가 따로 담당한다.

### 3모델 비교

| | **모델1 · 토스 PG 결제** | **모델2 · 계좌이체** | **모델3 · 외부 폼/링크** |
|---|---|---|---|
| 한 줄 | 사이트에서 즉시 카드결제 | 신청 받고 계좌입금 확인 | 신청·결제를 외부(구글폼·결제링크)로 |
| 트랙 | **Track A**(DB·인증 선행) | **Track B**(랜딩 우선) | Track B(최소) |
| CTA 목적지 | `/signup`→`/pay` (또는 `/preorder`) | `/apply` | 외부 URL |
| 수강생 로그인(P9) | **필요**(결제 세션·Nav) | 불필요(어드민 role만) | 불필요 |
| 결제 페이지 | `/pay`·`/pay/success`·`/pay/fail`·웹훅 | ❌ | ❌ |
| 좌석 카운터 | `payments` approved 수 | `applications` confirmed 수 | 수동/없음 |
| 자동 메일(P7) | 결제완료 메일 | 입금안내 메일 | (선택) 없음 |
| 핵심 env | `TOSS_CLIENT/SECRET_KEY`·`PAYMENT_ENABLED` | `BANK`·`RESEND`·`SLACK_*` | 외부 폼 URL |
| 빌드 비용 | 큼(PG 심사·웹훅·인증) | 중(폼·메일·어드민) | 작음 |
| 적합 | 즉시 카드결제·자동영수증·규모 | PG 전/소규모/B2B 청구 | MVP·초고속 검증 |
| 레퍼런스 | `guides/pg-review-guide.md`·`code-templates/payment.md` | 🆕`guides/no-pg-account-transfer.md` | (랜딩만 — P4~P10 대부분 생략) |

### 모델별 포함/제외 (이것만 빌드)

- **모델1 (PG)** — P4 DB·P9 인증·P5 폼·**P6 결제**·**P7 결제메일**·P8·P10 전부. 순서는 **Track A**(DB·인증을 P3 앞으로).
  사전예약 먼저면 `PAYMENT_ENABLED=false`(CTA→`/signup`→`/preorder`), 승인 후 `=true`(→`/pay`).
- **모델2 (계좌이체)** — P3 섹션 우선(**Track B**). P4 DB·P5 `/apply`·P7 입금안내메일·P10 어드민(입금확인). **P6 결제·P9 수강생인증·온보딩/SMS 제외.**
  좌석=confirmed 수. 🆕 Slack 알림(`slack-notify.md`) 권장. 상세 동선 = `no-pg-account-transfer.md`.
- **모델3 (외부)** — P2·P3 랜딩 + CTA가 외부 URL. P4~P10 대부분 생략(원하면 P8 GA만). 가장 빠른 검증용.

### 모델별 활성 단계 화이트리스트 (이 단계만 = 완료. 나머지는 "빠진 게 아니라 비활성")

> 번호는 풀스택(모델1) 기준이라, 모델2/3은 단계가 빠진 것처럼 보인다 — **아래가 각 모델의 "전부"다.**

| 모델 | 활성 Phase | 비활성(만들지 않음) |
|---|---|---|
| **1 · PG** | P0·P1·P2·P3·**P3.5 프리뷰배포**·P4·P5·**P5.0 법무게시**·P6·P7·P8·P9·P10·P11·P12·P13 | — |
| **2 · 계좌이체** | P0·P1·P2·P3·**P3.5 프리뷰배포**·P4·P5·**P5.0 법무게시**·P7(입금메일)·P8·P10·P11·P12·P13 | P6 결제·P9 수강생인증·온보딩/SMS |
| **3 · 외부** | P0·P1·P2·P3·**P3.5 프리뷰배포**·P8(선택 GA)·P11(SEO)·P12·P13 | P4~P7·P9·P10 (단, 폼이 외부라도 **개인정보 안내는 필요**) |

- **P3.5 프리뷰 배포**·**P5.0 법무 페이지 게시**는 이번 검토로 추가된 명시 체크포인트(아래 각 Phase 참조).
- 모델3도 외부 폼이 PII를 받으면 **개인정보 처리방침·동의 안내는 랜딩에 필요**(법무는 모델 무관).

> 🔀 **하이브리드(권장 성장 경로)**: 모델2(계좌이체)로 빨리 오픈 → 수요 확인·PG 심사 통과 후 **모델1로 승격**
> (P4·P9·P6·P7 추가, CTA를 `/pay`로). 모델2가 모델1의 부분집합이라 버릴 코드가 적다.

> 🆕 **가격 변형은 결제 모델과 직교**: 어느 모델이든 같은 랜딩을 가격만 다르게(공개/제휴) 뿌리려면
> `code-templates/price-variant.md`를 얹는다(경로 분기·서버 가격매핑). 모델2에서 실전 검증됨(axacademy).

---

# Phase 0 — 기획 (반나절)

코드 들어가기 전에 **아래를 먼저 확정**해야 뒤가 안 꼬인다. (**STEP 0 결제 방식**을 가장 먼저.)

- [ ] **상품 정의**: 강의명, 기수 코드(`cohort`), 정가, 얼리버드 티어/할인율/인원.
      (예: 오프라인 정가 50만 → tier1 20% / 온라인 정가 50만 → tier1 40%. tier1·tier2 각 20명, 이후 regular)
      ⚠️ **`cohort`는 하드코딩하지 말고 설정값(`lib/config.ts` 상수/ env)으로** — 기수마다 코드 수정 방지(원본은 `beta-2026` 하드코딩).
- [ ] **동선 결정**: 사전예약 먼저인가(PG 심사 대기) 결제 먼저인가 → `PAYMENT_ENABLED` 초기값.
- [ ] **설문 항목**: 수집할 필드(형태/요일/시간대/지역/직군/채널/매출/관심강의/자유의견) 확정 → DB 컬럼 = 설문.
- [ ] **수집 정보 & 동의**: 이름·이메일·전화 + 마케팅 동의(개인정보보호법/PIPA — 수집·이용 목적 명시 동의).
- [ ] **법무 콘텐츠 사전 확보(⚠️ 리드타임 김)**: 이용약관·개인정보처리방침·**환불정책**. 환불은 전자상거래법·
      (학원 등록 여부에 따른) 평생교육법 적용이 달라 **법적 검토 필요**. 표 수정 시 본문 조항과 상호 점검.
- [ ] **섹션 카피·순서**: Phase 3 섹션 17개를 자기 상품에 맞게. (Track B는 섹션을 일찍 빌드하므로 P0에서 확정 권장.)
- [ ] **도메인 & 발신 이메일**: 배포 도메인, `noreply@도메인` 발신 주소(Resend 도메인 인증 필요).

산출물: 한 장짜리 기획 메모(가격표·동선·설문·카피) + 법무 초안 의뢰. → `acceptance-criteria` 스킬로 합격기준 박아두면 굿.

---

# Phase 1 — 프로젝트 셋업 (1~2시간)

> 의존성: 없음. 가장 먼저.

- [ ] Next.js 16 앱 생성(`apps/web`), Tailwind 4, TypeScript, ESLint.
- [ ] **AGENTS.md/CLAUDE.md**: "이 Next.js는 최신이라 학습데이터와 다름 → 코드 전 docs 확인" 같은 가드 1줄.
- [ ] `package.json` 의존성: `next react react-dom @supabase/supabase-js next-auth@beta tailwindcss
      recharts bcryptjs resend`. 배포는 `@opennextjs/cloudflare wrangler`.
- [ ] `.env.example` 작성 → **reference/env-vars.md 복붙**. `.env.local` 로컬값 채우기.
- [ ] 배포 타깃 설정:
  - Cloudflare: `wrangler.jsonc`(name, account_id, compatibility_date, `nodejs_compat`, R2 assets,
    `vars`에 public env), `open-next.config.ts`, `next.config.ts`(initOpenNextCloudflareForDev).
    스크립트: `preview`/`deploy` = `opennextjs-cloudflare build && ... deploy`.
  - Vercel이면 이 단계 생략하고 그냥 연결.
- [ ] 패키지 매니저는 **npm** (이 환경 컨벤션). `npm run dev`로 기동 확인.

⏱️ **시간 절약**: `korean-landing-bootstrap` 스킬이 있으면 이 Phase를 자동화. 없으면 위 체크리스트.

⚠️ **함정**: Turbopack이 `globals.css` 변경을 자동반영 못 하는 경우 있음 → `.next` 캐시 비우고 재시작.

---

# Phase 2 — 디자인 시스템 (2~3시간)

> 의존성: Phase 0(브랜드 방향)·Phase 1. 섹션·로그인페이지 등 **모든 UI의 토대**.

> ❓ **"디자인이 처음부터 들어가야 하나?"** — 토대(토큰·폰트·공통클래스·reveal)는 **일찍**.
> 단 이건 *한 번 세팅하는 도구상자*이지 백엔드를 막는 게이트가 아니다:
> - **백엔드(P4 DB·P9 인증 로직·API)는 디자인에 의존하지 않음** → 디자인과 병렬 진행 가능.
> - 디자인이 실제로 필요한 시점 = **첫 UI 페이지(P3 섹션, P9 로그인 화면)**.
> - 그래서 "P2에 위치 = 일찍 깔되 병렬 가능"이 정답. 비주얼 디테일 다듬기는 P3 섹션에서 본격화.
> - 2-0 레퍼런스 수집은 **기획(P0) 때 같이** 해두면 더 빠르다.
> 결론: *최소 토대는 앞에, 풀 비주얼은 섹션과 함께* — "처음부터 전부 완성"일 필요는 없다.

> 🧱 **구조 vs 비주얼 분리(핵심 원칙)**: 디자인을 두 층으로 나눠 작업한다.
> - **구조(토큰구조·폰트로딩·공통클래스·reveal·반응형·접근성)** = `reference/design-system-skeleton.css`
>   **그대로 복제**(브랜드 무관·검증됨). 변수명/클래스/규칙은 손대지 않는다.
> - **비주얼 정체성(색·무드·타이포 값)** = `reference/design-phase-prompt.md`의 프롬프트로 **매번 새로 결정**.
> ⚠️ 라이브 granter 레포를 참조하지 말 것 — 스켈레톤 스냅샷이 단일 출처(움직이는 표적 금지).

### 2-0. 비주얼 방향 설정 (토큰 "값" 정하기 — 기획 P0와 병행 권장)
- [ ] **레퍼런스 수집**: 유사·경쟁 강의 랜딩(패스트캠퍼스·인프런·클래스101), Dribbble/Behance/awwwards 3~5개.
      받을 게 없으면 사용자에게 3가지만 질문: 무드 / 강조색 방향(웜·쿨·뉴트럴) / 다크 비중.
- [ ] **`design-phase-prompt.md`의 마스터 프롬프트 실행** → 팔레트·폰트·무드 확정.
- [ ] **디자인 스킬 연계(선택)**: `ui-ux-pro-max`(팔레트·폰트페어링), `design-shotgun`/`design-html`(시안 다중),
      `design-review`(비평). 결과 색·폰트를 토큰 값으로 환원.
- [ ] **재사용 자산 검토**: `ld_archive/`(instructor-spotlight·mac-open-motion) "새로 만들 것 vs 가져올 것" 구분.

### 2-1. 스켈레톤 복제 + 토큰 값 주입 (구조는 코드, 값만 교체)
- [ ] **`reference/design-system-skeleton.css`를 `app/globals.css`로 복제.**
- [ ] 2-0에서 확정한 값을 스켈레톤 `:root`에 주입(`--ink/--paper/--signal/--signal-text/--rule/--mute` + 폰트).
      **변수명·공통클래스·reveal·반응형·접근성 규칙은 변경 금지.**
- [ ] **폰트 로딩**: 본문 웹폰트는 `layout.tsx` `<head>` `<link>`, 모노는 `next/font`. (Tailwind v4 @import 순서 함정 회피 — 스켈레톤 주석 참조.)
- [ ] `RevealOnScroll.tsx`(IntersectionObserver, threshold 0.12 → `.in` 토글) 추가 — 스켈레톤의 `.reveal`/`.reveal-stagger`와 짝.
- [ ] 대비/접근성 검증: 강조색 WCAG AA(4.5:1), 다크섹션 가독성, 버튼 hover/disabled.

⏱️ **재사용 자산(이미 보유)**: `ld_archive/instructor-spotlight`(글로우 인물), `ld_archive/mac-open-motion`(핀 스크럽+맥북).
두 폴더 다 "🤖 적용 지침" 포함 → 그대로 투입.

---

# Phase 3 — 랜딩 본문 섹션 (1~2일)

> 의존성: Phase 2(디자인 시스템)만. 랜딩 섹션은 백엔드와 무관 → **먼저 빌드해 조기 배포·공유 가능**(Track B 핵심).
> `app/page.tsx`에 순서대로 배치. 각 섹션 = `components/sections/*.tsx`.
> ⚠️ 소셜로그인이 있는 **Track A**라면 Nav 로그인 표시를 위해 **Phase 9(인증)을 이 단계 앞으로 당긴다.**
> 📐 **순서의 의도·예비구매자 의미는 `guides/section-narrative.md`**(설득 아크), **시각·모션 장치는 `guides/design-devices.md`** 를 먼저 읽고 배치할 것 — 순서는 임의가 아니라 구매 심리 흐름이다.

검증된 섹션 순서(라이브 17개, 자기 상품에 맞게 카피만 교체):

| # | 섹션 | 역할 | 배경 |
|---|---|---|---|
| 1 | Hero | 핵심 가치 한 줄 + 메인 CTA + 배경이미지 | dark |
| 2 | Benefits | 사전예약 혜택 3개 | 크림(offer-pre) |
| 3 | (Creator)Intro | 크리에이터/브랜드 신뢰도 | dark |
| 4 | TrustLogos | 교육 기업 로고 마퀴 | white |
| 5 | WhyNow | 문제 인식 3카드 | white |
| 6 | WhoIsThisFor | 타겟 페르소나 3 | white |
| 7 | ProblemAware | 문제 시각화(흩어진 화면) | dark+glow |
| 8 | Solution | 해결책 = 라이브 데모 iframe(맥북) | 크림 |
| 9 | Partners | 파트너 2카드 + 연결 | #FAF5EF |
| 10 | Curriculum | 주차 커리큘럼 + 맥북 데모 (→ mac-open-motion) | white |
| 11 | TakeHome | 졸업 후 얻는 것 3 | dark |
| 12 | Instructor | 강사 소개 (→ instructor-spotlight) | dark |
| 13 | NonDev | 비개발자 가능(Before/After) | white |
| 14 | Pricing | 가격·얼리버드·혜택 | white |
| 15 | HowToJoin | 신청 절차 타임라인 | dark |
| 16 | FinalCTA | 클로징 CTA | dark |
| 17 | Faq | FAQ 아코디언 | white |

- [ ] 공통 UI: `Nav.tsx`(sticky 헤더+로그인표시), `Footer.tsx`(사업자정보·정책링크),
      `FloatingBar.tsx`(스크롤 후 등장: 실시간 관람수/마감카운트다운/얼리버드 잔여석),
      `StickyCTA.tsx`(모바일 하단 고정).
- [ ] iframe 데모는 `public/examples/*.html` 정적 파일 + 맥북 프레임(mac-open-motion).

⚠️ **함정**: CTA는 전부 **Phase 8의 `CheckoutCTA`/`Cta` 래퍼**로 만들어 `begin_checkout` 자동 발화. FloatingBar의
잔여석 카운터는 **결제 모델에 따라 의존처가 다르다**:
- 모델1(PG): `/api/counter`(결제 approved 수, **Phase 6**)
- 모델2(계좌이체): `/api/applications` GET(confirmed 수, **Phase 4·5**) ← axacademy 실제
- 모델3(외부): 카운터 없음(수동/생략)
→ 섹션은 먼저 만들고, 카운터·전환 트래킹은 해당 모델의 Phase에서 배선. **단, 랜딩측 트래킹(`view_item`·섹션 퍼널)은 폼/결제와 무관 → Phase 3 직후 바로 켤 수 있다**(아래 P3.5·Phase 8 "랜딩 이벤트" 참조).

### 🔁 3-X. 콘텐츠 반복 루프 (랜딩 작업의 실제 본체 — 단발 아님)
> **실측(axacademy git): 전체 18커밋 중 절반 이상이 섹션·카피·디자인 반복**이었고 전 기간에 퍼져 있었다.
> P3는 "한 번 짓고 끝"이 아니라 **초안 → 리뷰 → 수정**을 도는 루프다. 이 루프를 1급 단계로 다룬다.

- [ ] **콘텐츠/데이터 분리**: 카피·후기·커리큘럼·FAQ 등 긴 콘텐츠는 `lib/content.ts`·`*.data.ts`로 분리
      (컴포넌트=레이아웃, 데이터=대본). 카피 수정이 레이아웃 변경 없이 데이터만 고치게 → 반복 비용↓.
- [ ] **루프 1회 = 초안 배치 → `design-review`/`browse`로 실화면 확인 → 카피·간격·위계 수정**. 한 섹션씩 수렴시킨다.
- [ ] **설득 아크 점검**: `guides/section-narrative.md`(순서=구매심리)·`guides/copywriting-guide.md`(섹션별 설득구조)로
      "이 섹션이 예비구매자에게 무슨 일을 하는가"를 매 루프 확인. 막연한 미화 카피 금지(검증 가능한 사실 우선).
- [ ] **완성 섹션 아카이브**: 재사용 가치 있는 섹션은 `~/Desktop/dev/ld_archive/`에 저장(섹션 완성 시 저장 여부 먼저 질문).

### 🚀 3.5 — 프리뷰 배포 체크포인트 (Track B "조기 배포"의 실행 지점)
> Track B의 명분이 "랜딩 먼저 → 조기 배포·공유"인데 정작 배포는 P12뿐 → **여기서 한 번 띄운다.**
> 콘텐츠 반복(3-X)을 **실배포 위에서** 돌려야 실기기·실링크 공유 피드백이 모인다.

- [ ] **프리뷰 배포**(Cloudflare preview / Vercel preview)로 랜딩을 실URL에 올린다(백엔드 stub 모드 OK).
- [ ] 실기기(모바일/데스크톱)·이해관계자 공유 → 카피·디자인 피드백을 3-X 루프로 환류.
- [ ] **랜딩측 트래킹 조기 활성화**(선택이지만 권장): `view_item`·섹션 퍼널(Phase 8 "랜딩 이벤트")을 지금 켜면
      프리뷰 단계부터 스크롤 이탈·도달률 데이터가 쌓인다(폼/결제 없이도 가능).
- [ ] ⚠️ **프리뷰는 비색인**: preview 도메인은 `noindex`(또는 접근제한) — 미완성본 색인·유출 방지.

---

# Phase 4 — 데이터베이스 (Supabase) (반나절)

> 의존성: Phase 1. 폼·결제·메일·어드민이 모두 이 스키마에 의존 → **폼(P5) 전에 깐다.** (디자인·섹션과 병렬 가능.)

- [ ] Supabase 프로젝트 생성, `NEXT_PUBLIC_SUPABASE_URL`/`ANON_KEY`/`SERVICE_ROLE_KEY` 발급.
- [ ] **reference/db-schema.sql 적용** (users, applications, payments, otp_codes, admins, email_sends, email_events).
- [ ] `lib/supabase/server.ts` — `getSupabaseAdmin()`(service_role, `persistSession:false`).
      **env 미설정 시 null 반환 → stub 모드**로 빌드는 통과시키는 패턴 채택(개발 초기 편함).
- [ ] 전 테이블 RLS on(정책 없음) = 서버 전용. 클라이언트에서 직접 쿼리 금지.

⚠️ **함정 3개(원본 전례)**:
1. **설문 컬럼을 마이그레이션에 명시**할 것(원본은 코드 INSERT로 동적생성 → 스키마 드리프트). schema.sql엔 반영됨.
2. **email_events 테이블 누락 주의** — 트래킹 API가 참조하는데 마이그레이션에서 빠졌던 전례. schema.sql에 포함됨.
3. `onboarded_at` null 여부가 온보딩 완료 판정 기준. 모든 보호 페이지에서 체크.

---

# Phase 5 — 폼 (사전예약·신청·온보딩) (1일)

> 의존성: Phase 4(applications/users/otp_codes 테이블). (Track A에서 결제 전 로그인 세션이 필요하면 Phase 9 인증 선행.)

### ⚖️ 5.0 — 법무 페이지 선행 게이트 (PII 폼 가동 *전* 필수 · 모델 무관)
> **HIGH·컴플라이언스.** 개인정보(이름·연락처·이메일)를 받는 폼이 **라이브가 되는 순간** 개인정보처리방침과
> 수집·이용 동의가 **법적 선행조건**이다(PIPA). P0에서 초안만 확보하고 *페이지 게시*는 P11로 미루면,
> 프리뷰(P3.5)에서 실신청을 받는 순간 무방비가 된다 → **폼 공개 전에 게시**한다.
- [ ] `/privacy`(개인정보처리방침) **게시** + 폼에 **수집·이용 동의 체크**(필수, 마케팅 동의와 분리).
- [ ] PII를 수집·노출하는 모든 경로(폼·완료페이지·메일)에 처리 목적·보관기간·위탁(외주) 명시.
- [ ] `/terms`·`/refund`은 결제/계약 발생 시점까지(P6 또는 입금안내) 게시 — 폼만이면 `/privacy` 우선.
- [ ] 모델3(외부 폼)이라도 **개인정보 안내는 랜딩에 필요**(외부폼에 PII가 가면 위탁·링크 안내).
- ⚠️ 초안·검토 리드타임이 길다(P0 확보) → 본문은 `guides/legal-boilerplate.md`(법적 검토 필수).

- [ ] `/onboarding` — 전화번호 입력 → **SMS OTP**:
  - `POST /api/otp/send`(전화 정규식 `^010\d{8}$`, 30초 쿨다운, `otp_codes` INSERT, ~5분 TTL).
  - `POST /api/otp/verify`(OCTOMO `checkOctomoMessage`로 역방향 문자 확인 → `users.phone/phone_verified/onboarded_at` 갱신).
  - OCTOMO 안 쓰면: 단순 코드발송/검증으로 대체하거나 온보딩에서 전화만 수집.
- [ ] `/preorder` + `SurveyForm.tsx` — 설문(형태/요일/시간대/지역/직군/채널/매출/그랜터사용/관심강의/의견).
      클라 검증(`isComplete`로 제출버튼 토글) → 서버액션 `submitPreorder()`가 `applications` INSERT
      (`is_preorder=true`, `status='pending'`, 중복 체크 후). → `/preorder/done`.
- [ ] `/apply` + `/apply/done`, `POST /api/applications`(name/email/phone 필수, 이메일 정규식, stub 모드 지원).
- [ ] 완료 페이지에서 마케팅 수신 동의/무료자료 안내.
- [ ] **봇/스팸 방지(공개 엔드포인트 보호)**: `/api/applications`·OTP는 인증 없이 호출 가능 → **허니팟 필드 +
      IP/세션 레이트리밋**(예: 동일 IP 분당 N회). OTP는 30초 쿨다운 외 일일 횟수 상한도. (원본은 미흡.)

⏱️ **시간 절약**: 설문 필드는 Phase 0에서 확정한 목록 그대로 → `text` / `text[]` 매핑만.

---

# Phase 6 — 결제 (Toss Payments) (1일)

> 의존성: Phase 4(DB)·9(인증)·5(폼). `PAYMENT_ENABLED=true`일 때 활성. (계좌이체 등 PG 미사용이면 생략.)

- [ ] `/pay` (`page.tsx`): 로그인 필수(미로그인 → `/signin?from=/pay`). `applications`에서 사용자 신청 조회
      (없으면 자동 생성). **얼리버드 티어 산정**: `payments where status='approved'` 카운트로 tier1/tier2/regular 결정.
- [ ] `PayWidget.tsx`: 토스 v2 SDK(`https://js.tosspayments.com/v2/standard`),
      `TossPayments(clientKey).widgets({customerKey:userId})` → `setAmount` → `renderPaymentMethods`/`renderAgreement`
      → `requestPayment({orderId:"ord-{app8}-{ts}", successUrl, failUrl, ...})`.
- [ ] `/pay/success`(서버): 토스 승인 `POST https://api.tosspayments.com/v1/payments/confirm`
      (`Authorization: Basic base64(TOSS_SECRET_KEY:)`) → `payments` INSERT(`status='approved'`, raw_response)
      → `applications.status='paid'` → **결제완료 메일(Phase 7)**.
- [ ] `/pay/fail`: code/message 표시.
- [ ] `GET /api/counter`: 얼리버드 잔여석 표시용 결제완료 수(공개).
- [ ] **PG 심사 모드**: `@review.*` 계정은 신청 없으면 즉석 pending 생성 → 심사관이 결제 테스트 가능.
- [ ] **결제 신뢰성 — 웹훅 보강(권장, 원본 미구현)**: success 리다이렉트 승인만 있으면 **사용자가 결제 후
      리다이렉트 전에 창을 닫을 때 토스엔 승인·DB엔 미기록** 누락 발생. **Toss 웹훅(`/api/toss/webhook`)으로
      결제상태를 서버에서 재동기화**(멱등 처리: `toss_order_id` unique로 중복 INSERT 방지) → success는 UX, 웹훅은 진실원천.

⚠️ **함정**: `TOSS_CLIENT_KEY`는 브라우저 노출(공개), `TOSS_SECRET_KEY`는 서버 승인에서만. 혼동 금지.

---

# Phase 7 — 자동 메일 + 운영자 알림 (반나절)

> 의존성: Phase 4(email_sends/events 테이블) + Phase 5(신청 제출 트리거) / Phase 6(결제 트리거).
> 고객용 메일(7-A)과 **운영자용 알림(7-B Slack)**은 같은 제출 핸들러에서 나란히 발화한다.

**이원 구조**:
- [ ] **결제완료 메일(자동)** — `lib/email.ts` `sendPaymentConfirmEmail()` via **Resend**.
      `/pay/success`에서 호출. 발신 `브랜드 <noreply@도메인>`. 본문에 다운로드/안내.
- [ ] **대량 발송(반자동)** — 사전예약자 일괄 메일은 **Google Apps Script**(`GmailApp.sendEmail`):
      Supabase REST로 대상 조회(`is_preorder=true & marketing_consent=true`) → `email_sends` 기록 → HTML 본문 발송.
- [ ] **오픈/클릭 추적**:
  - 오픈: 본문에 `<img src="{SITE}/api/track/open?id={sendId}" 1x1>`.
  - 클릭: 링크를 `{SITE}/api/track/click?id={sendId}&url={목적지}`로 래핑 → 302 리다이렉트.
  - `GET /api/track/open`(투명 GIF + `email_events` insert), `/api/track/click`(insert + redirect).

- [ ] **발송 한도/도달률**: Apps Script Gmail은 **일일 쿼터(무료 ~500 / Workspace ~2,000건)** → 대량은 분할/배치.
      Resend는 **발신 도메인 인증(SPF·DKIM·DMARC) + 신규 도메인 워밍업**(초기 소량부터) 선행, 스팸함 직행 방지.

⚠️ **함정(원본 전례)**: Apps Script에 Supabase **secret key 하드코딩 금지** → 스크립트 속성/환경으로.
`email_events` 테이블 존재 확인(Phase 4).

### 🔔 7-B. 운영자 Slack 신청 알림 (모델 무관 · 권장)
> 신규 신청이 들어오면 운영 Slack 채널로 즉시 푸시 → 어드민을 안 봐도 실시간 인지·빠른 입금확인/응대.
> **고객용 메일(7-A)과 별개의 운영자용 채널.** 신청 INSERT 성공 직후, 메일과 나란히 발화.
> 복붙 코드·외부설정·함정 전체 = `code-templates/slack-notify.md`.

- [ ] `lib/notify.ts` `sendSlackApplicationAlert()` — Incoming Webhook + **Block Kit**(헤더·필드·기대/의견·어드민 링크).
- [ ] **배선**: `/api/applications` POST에서 INSERT 성공 직후 `await sendApplicationEmail(...)` 다음 줄에 `await sendSlackApplicationAlert(row)`.
- [ ] **시크릿**: `SLACK_APPLICATIONS_WEBHOOK_URL`을 시크릿으로만 주입(`wrangler secret put`/Vercel env, **vars 아님**). 미설정 시 **스텁**(스킵).
- [ ] **알림 실패 격리**: try/catch로 감싸 알림 실패가 신청 저장을 막지 않게(코드에 포함).
- [ ] E2E: 테스트 신청 1건 → 채널 수신 확인 → 테스트 데이터 정리.
- ⚠️ **함정**: Incoming Webhook에 `actions`(버튼) 쓰면 Slack 대화형 경고 → 링크는 **mrkdwn 링크**로(기능 동일). Webhook URL 유출 시 즉시 재발급.

---

# Phase 8 — 분석 / GA·GTM 트래킹 (반나절)

> 의존성: 둘로 쪼갠다 — **8A 랜딩 이벤트는 Phase 3만**, **8B 전환 이벤트는 Phase 5·6**. **reference/gtm-events.md 전체 참조.**
> 💡 8A는 폼/결제 없이도 돌아가므로 **P3.5 프리뷰 배포 때 바로 켜서** 초기부터 스크롤·도달 데이터를 모은다.

- [ ] **공통 토대**: `lib/gtm.ts` 헬퍼(`pushDataLayer` + track 함수), `GTMScript.tsx`/`layout.tsx` 설치. 전부 **sessionStorage 가드**로 중복 발화 방지.

**8A. 랜딩 이벤트 (Phase 3 의존만 — P3.5에서 조기 활성 권장)**
- [ ] `view_item` ← `ViewItemTracker`(홈 진입).
- [ ] `begin_checkout` ← **모든 CTA를 `Cta`/`CheckoutCTA` 래퍼로**(button_location 파라미터). 모델3(외부 URL)도 클릭 발화 가능.
- [ ] 🆕 **섹션 도달 퍼널** `sec_NN_*` ← `SectionFunnelTracker`(`lib/sections.ts` 단일출처). 섹션별 이탈 지점 분석 — `code-templates/section-funnel.md`.

**8B. 전환 이벤트 (Phase 5·6 의존 — 폼/결제 완성 후)**
- [ ] `generate_lead` ← `GenerateLeadTracker`(신청/사전예약 완료: apply/preorder done).
- [ ] `login` ← `GTMTracker`(모델1 인증 사용 시; 모델2/3은 없음).
- [ ] `purchase` ← `PurchaseTracker`(모델1 pay/success, txid·tier; 모델2/3은 없음).

- [ ] GTM 웹UI: GA4 Config 태그 + Event 태그(섹션 퍼널은 `^sec_\d+_` 정규식 트리거 1개로 묶기) + 전환 별표(begin_checkout/generate_lead/purchase).

⏱️ **시간 절약**: `gtm-funnel-tracking` 스킬 보유 → 이 Phase 자동화 가능.

---

# Phase 9 — 인증 / OAuth 소셜로그인 (1일)

> 의존성: Phase 4(users 테이블) + Phase 2(로그인 페이지에 디자인 시스템 필요).
> ⚠️ **Track A(소셜로그인)면 이 Phase를 Phase 3 섹션 앞으로 당긴다** — Nav 로그인 표시가 섹션에 필요하기 때문.
> 어드민만 필요한 Track B면 Google role만 가볍게.

- [ ] `lib/auth.ts` — Auth.js v5 config: `session:{strategy:"jwt"}`, `pages:{signIn:"/signin"}`.
- [ ] Providers:
  - **Google** — 내장 `Google()`.
  - **Kakao** — 내장 `Kakao()`. ⚠️ 비즈앱 전 이메일 미제공 → placeholder `kakao_{id}@placeholder.local`.
    전화는 동의항목 검수 통과 시만. `OAUTH_REQUEST_CONTACT` 토글.
  - **Naver** — 공식 provider 없음 → **커스텀 OAuth**(authorize/token/`openapi.naver.com/v1/nid/me`).
  - **Credentials("toss-review")** — PG 심사용 계정(bcrypt 해시 비교).
- [ ] callbacks:
  - `signIn`: OAuth 프로필 검증 → **약관동의 쿠키 확인(신규가입 보호)** → Supabase `users` upsert → 동의쿠키 삭제.
  - `jwt`: `isAdminEmail()`(ADMIN_DOMAIN/ADMIN_EMAILS)로 role 부여, onboarded 플래그.
  - `session`: 토큰 → 세션.
- [ ] `app/api/auth/[...nextauth]/route.ts` — `export const { GET, POST } = handlers`.
- [ ] 페이지: `/signup`(약관·광고 동의 체크 → `signupWith()` 서버액션이 동의값 httpOnly 쿠키(5분) 저장 →
      `signIn(provider,{redirectTo:POST_ONBOARDING_PATH})`), `/signin`(기존 사용자; 신규는 AccessDenied → 안내).
- [ ] 헤더 로그인 표시: `Nav.tsx`에서 `await auth()` → `MyPageDropdown`(이름·이메일·연락처).
- [ ] **전화번호 정규화 유틸**(`+82 10-...` → `010-...`).

⚠️ **함정**: 신규 사용자가 `/signin`으로 바로 오면 동의 쿠키가 없어 차단(AccessDenied)됨 → "/signup으로" 안내 UX 필수.

---

# Phase 10 — 어드민 대시보드 (1일, 선택)

> 의존성: Phase 9(role) + Phase 4·5·6(데이터) + P8(트래픽 GA4).
> 📁 **복붙 코드 전부 → `reference/code-templates/admin.md`** (6영역 + CSS 일괄). 아래는 체크리스트.

- [ ] **레이아웃·가드**: `/admin/layout.tsx`(다크 네비 + 4탭 대시보드/신청자/가입자/트래픽), 모든 페이지 `force-dynamic` + `role!=="admin"→redirect("/admin/signin")`. `/admin/signin` = Google OAuth, 비-어드민 denied 안내. `proxy.ts`가 미인증 `/admin` 리다이렉트.
- [ ] **공용 날짜선택**: `lib/adminRange.ts`(`resolveRange` — all/7/28/90/맞춤, KST, ISO+라벨) + `RangePicker.tsx`(`<details>` 드롭다운, `extra`로 기존 필터 보존). 대시보드·신청자·가입자 공유. **트래픽은 GA4 상대날짜(`28daysAgo`) 때문에 자체 인라인 변형**.
- [ ] **대시보드** `/admin`: 통계카드 4종(가입자·신청자·결제완료·전환율, 카운트는 `head:true`), 관리자 제외(`isAdminEmail`), 채널분포 막대, 설문통계 `SurveyDashboard`(Pie/가로Bar/Area, `countSingle`/`countArray` 집계).
- [ ] **트래픽(GA4)** `/admin/traffic`: `lib/ga4.ts`(refresh-token OAuth → `runReport` 9병렬, **`/admin` 페이지뷰 제외** 필터). 차트: KPI·Pie 3종·일별Area·시간대Bar·**커스텀 SVG 퍼널 2종**(플로우·섹션, taper + 호버 슬로프 + 최대이탈 강조 — 상시연결 금지)·**요일×시간 히트맵**. 시크릿 `GA4_REFRESH_TOKEN/CLIENT_ID/CLIENT_SECRET/PROPERTY_ID`.
- [ ] **신청자** `/admin/applications`: 표 + 검색(`q` ilike 이스케이프)·유형·상태·기간 필터, `SurveyDetail` 행 펼침, 최근 500건. **가입자** `/admin/users`: 동형 + 채널/권한 필터(role은 메모리 필터).
- [ ] **CSV** `*/export.csv/route.ts`: 목록과 동일 필터, **BOM+CRLF**(엑셀 한글), 401 가드, limit 10000, `no-store`.
- [ ] 권한 가드 env: `ADMIN_DOMAIN`/`ADMIN_EMAILS`. 차트 색은 브랜드 `--signal`로 통일(설문 차트는 범용 팔레트가 기본).
- [ ] **환불/취소 처리**: `status`에 `refunded`/`cancelled` 값은 있으나 원본엔 어드민 액션 없음(수동/토스콘솔).
      최소 **상태 변경 + 토스 취소 API(`/v1/payments/{key}/cancel`) 연동**, `applications.status` 동기화. 환불정책(P0)과 일치.

---

# Phase 11 — 프로덕션 마감 / 하드닝 (반나절~1일)

> 의존성: P3(섹션)·P4~P10 구현 완료. 배포 전 **누락되기 쉬운 교차 관심사**를 일괄 처리. (원본에 다수 누락된 영역.)

- [ ] **SEO**: `app/sitemap.ts` + `app/robots.ts`(원본 없음). 구조화 데이터(JSON-LD): `Course`·`FAQPage`·`Organization`.
      canonical, `metadata`(title/description/OG/twitter, `metadataBase`=SITE_URL), `app/icon.png`·`apple-icon.png`.
- [ ] **에러/404/로딩 바운더리**(원본 전무): `app/not-found.tsx`, `app/error.tsx`, `app/global-error.tsx`,
      필요 라우트 `loading.tsx`. 결제/OAuth 실패 시 깨진 화면 대신 안내.
- [ ] **이미지 최적화/성능 예산**(원본 7MB대 원본 이미지 서빙): 히어로 등 대형 이미지 → `next/image` + 압축/WebP,
      LCP 이미지 `priority`. Cloudflare Image Optimization 바인딩 활용. 목표: LCP < 2.5s.
- [ ] **모니터링/에러 트래킹**: Sentry(또는 Cloudflare Workers 로그/알림)로 런타임 에러·결제 실패 관측.
- [ ] **분석/개인정보 동의(PIPA)**: GA·마케팅 쿠키 안내(한국 기준). 수집 동의는 가입 시(P9)와 일관.
- [ ] **(선택) PWA manifest**(`app/manifest.ts`) — 모바일 홈화면/아이콘 필요 시.

---

# Phase 12 — 배포 / 인프라 (반나절)

> 의존성: P11 마감 완료. 프로덕션에 올리고 외부 연동을 실값으로 전환.

- [ ] 프로덕션 env: Cloudflare `vars`(public) + `wrangler secret put`(secret) / Vercel env.
- [ ] OAuth redirect URI를 프로덕션 도메인으로 등록(구글·카카오·네이버 콘솔). `AUTH_URL`/`NEXT_PUBLIC_SITE_URL` 일치.
- [ ] Toss: 실키 전환(PG 심사 통과 후). `PAYMENT_ENABLED`는 심사 결과에 맞춰 토글. **웹훅 URL 등록**(P6).
- [ ] Resend 도메인 인증(SPF/DKIM/DMARC), 발신 주소 확인.
- [ ] 정책 페이지(terms/privacy/refund)·사업자정보(Footer) 실제값, OG 이미지·메타데이터.
- [ ] GTM 컨테이너 게시.
- [ ] `opennextjs-cloudflare deploy`(또는 Vercel) → 프로덕션 URL 확보.

---

# Phase 13 — QA / 런치 검증 (반나절~1일)

> 의존성: Phase 12(또는 프리뷰 배포). **품질 게이트** — 통과 전 정식 오픈 금지.
> 로컬/프리뷰에서 가능한 건 배포 *전*에, 실키·실도메인 필요한 건 배포 *후* 스모크로.

### 자동화 테스트 (원본 0 → 최소한이라도 도입)
- [ ] **Critical-path 단위/통합 테스트**: 결제 승인(`/pay/success` confirm), OTP 검증, 폼 검증/INSERT, 티어 산정.
- [ ] **E2E 자동화**(Playwright): 가입→온보딩→사전예약/결제 핵심 플로우. CI에 연결.

### 배포 전 (로컬·프리뷰)
- [ ] `qa`/`browse` 스킬로 핵심 동선 E2E: 가입 → 온보딩(SMS) → 사전예약/결제 → 완료.
- [ ] 폼 검증(필수누락·이메일정규식·중복제출) + **봇/레이트리밋 동작 확인**(P5).
- [ ] 반응형(1023/768/639) + `prefers-reduced-motion` + 접근성(sr-only·aria·focus-visible).
- [ ] 빈 상태/에러 상태(결제 실패, OAuth 취소, OTP 만료) + 404/에러 페이지(P11) 노출 확인.
- [ ] **성능(Core Web Vitals)**: Lighthouse LCP/CLS/INP, 이미지 최적화(P11) 반영 확인.

### 배포 후 (실키·실도메인 스모크)
- [ ] OAuth 3사 실제 로그인(프로덕션 redirect URI) 정상.
- [ ] **결제 실거래 1건** 승인 → `payments`/`applications` 갱신 → 결제완료 메일 수신 → 토스 콘솔 대조 → **웹훅 동기화 확인**. (취소/환불도)
- [ ] GA4 실시간 리포트에서 퍼널 이벤트 발화 확인: view_item → begin_checkout → login → generate_lead → purchase.
- [ ] 메일 오픈/클릭 추적(`email_events`) 적재 확인.
- [ ] PG 심사 계정(`@review.*`) 동선 점검.
- [ ] 카운터(`/api/counter`)·얼리버드 잔여석 표시 정상.
- [ ] SEO: `sitemap.xml`/`robots.txt` 응답, OG 미리보기, 구조화 데이터(Rich Results Test).
- [ ] 모니터링(Sentry 등) 이벤트 수신 확인.

✅ **런치 게이트**: 위 전부 통과 시에만 정식 오픈/광고 송출.

---

## 🔁 의존성 그래프 (한눈에)

**Phase 번호 = 빌드 순서**(= Track B 랜딩 우선이 기본 캐논). 번호대로 따라가면 의존성이 안 꼬인다.

```
P0 기획
 └ P1 셋업
    └ P2 디자인 ──┬─ P3 섹션(랜딩) ─🔁콘텐츠루프─ P3.5 프리뷰배포 ──── 8A 랜딩이벤트(view_item·섹션퍼널)
                  │     (P2 토대만 의존 → 먼저 빌드·조기 배포)        │ (P3만 의존 → 프리뷰부터 수집)
                  │                                                  │
                  └─ P4 DB ─┬─ P5.0 ⚖️법무게시 ─ P5 폼 ─┬─ P6 결제 ─ P7 메일
                            │                            └─ 8B 전환이벤트(generate_lead·purchase)
                            └─ P9 인증 ─ P10 어드민 (P9 role + P4·P5·P6 데이터)
                                          └ P11 마감 ── P12 배포 ── P13 QA/런치
```
권장 순서 = **번호 그대로 P0 → P1 → P2 → P3 →(P3.5)→ P4 → P5 → … → P13.**
- **P2 디자인 ∥ P4 DB는 병렬 가능**(백엔드는 디자인 의존 없음).
- **P3 섹션(랜딩)은 P2 토대에만 의존** → 백엔드보다 먼저 빌드. **🔁 콘텐츠 반복 루프가 P3의 본체**(단발 아님).
- **P3.5 프리뷰 배포** = Track B "조기 배포"의 실행 지점. 8A 랜딩 이벤트를 여기서 켜 초기부터 퍼널 수집.
- ⚖️ **P5.0 법무 게시는 폼(P5)보다 먼저**(HIGH): PII 폼이 라이브면 개인정보처리방침·동의가 법적 선행조건.
- 신청폼(P5)은 `applications` 테이블(P4)에 의존 → 폼 전에 DB(또는 `getSupabaseAdmin` null-stub).
- **트래킹 분할**: 8A(랜딩, P3 의존)는 일찍 / 8B(전환, P5·P6 의존)는 폼·결제 후. FloatingBar 카운터 의존처는 **모델별**(P6 또는 P4·P5).
- **P11 마감**(SEO·에러바운더리·이미지최적화·모니터링)은 배포 전 일괄 처리 — 원본에 다수 누락된 영역이라 별도 게이트로 분리.
- **P13 QA는 독립 품질 게이트** — 자동화 테스트 + 배포 전/후 점검. 통과 전 정식 오픈 금지.

---

## 🔀 순서 변형 트랙 (프로젝트 성격별)

위 번호 순서(= **Track B: 랜딩 우선**)가 기본 캐논이다. 결제가 PG가 아니고(계좌이체·외부폼) 수강생
로그인이 없는(인증=어드민만) 마케팅 랜딩에 맞다 — 랜딩(P3)을 먼저 띄워 확인·공유·조기 배포한다.

### Track B — 랜딩 우선 (기본/캐논, 위 번호 그대로)
```
P0 → P1 → P2 → P3 섹션(🔁콘텐츠루프) → P3.5 프리뷰배포+8A → P4 DB → P5.0 법무 → P5 폼 → 8B 전환 → P9 인증 + P10 어드민 → P11 → P12 → P13
```
- **P6 결제·P7 메일은 선택**: 계좌이체면 P6 생략, 신청확인만 필요하면 P7 일부. 어드민 인증(P9)은 Google role만.
- **왜 P3를 앞으로**: 랜딩 섹션은 P2(디자인 토대)에만 의존하고 DB/인증과 무관 → 먼저 지어 조기 배포 가능.
- **주의(의존성은 유지)**: 신청폼(P5)은 `applications`(P4)에 의존 → 폼 빌드 전에 DB 또는 stub.
- 실전 예: **axacademy-landing(조코딩AX 아카데미 2기)** — 계좌이체+네이티브폼+어드민. Toss·소셜로그인·SMS·`PAYMENT_ENABLED` **의도적 제외**.
  이 빌드에서 캐논에 **추가된 신규 패턴 5종**은 아래 "🆕 신규 패턴" 절 참조(가격변형·Slack알림·섹션퍼널·데모섹션·계좌이체 동선).

### Track A — 풀스택 결제 (변형: DB·인증을 섹션 앞으로)
토스 PG 결제 + 소셜로그인(수강생 계정) + 자동메일이 있으면, **Nav 로그인 표시·결제 세션** 때문에
**DB(P4)·인증(P9)을 섹션(P3)보다 먼저** 깐다. 번호는 같되 순서를 당긴다:
```
P0 → P1 → P2 → P4 DB → P9 인증 → P3 섹션(🔁) → P3.5 프리뷰+8A → P5.0 법무 → P5 폼 → P6 결제 → P7 메일 → 8B 전환 → P10 → P11 → P12 → P13
```
- 이때 P3 섹션의 Nav가 P9 인증(로그인 표시)에 의존하므로 인증을 먼저 끝낸다.
- P6 결제·P7 메일은 **필수**(이 트랙의 핵심). PG 심사 동선은 `guides/pg-review-guide.md`.
- ⚖️ **P5.0 법무 게시는 폼 전**(모델 무관·HIGH), 🔁 콘텐츠 루프·P3.5 프리뷰·8A/8B 분할은 Track A에도 동일 적용.

> 어느 트랙이든 **P0 → P1 → P2**는 동일하게 먼저. 갈리는 건 P2 이후(섹션 우선 vs DB·인증 우선)다.
> 의존성 규칙(폼→DB, 결제→DB·인증)은 트랙과 무관하게 항상 지킨다.

---

## ✅ 구현 자산 전수 체크리스트 (원본 대조 — 빠짐 방지)

> granter-landing 실제 파일과 1:1 대조한 전체 목록. 재구현 시 이 표로 누락 점검.

**페이지(18)**: `/` · `/signin` · `/signup` · `/onboarding` · `/preorder` · `/preorder/done`
· `/pay` · `/pay/success` · `/pay/fail` · `/apply` · `/apply/done` · `/terms` · `/privacy` · `/refund`
· `/admin` · `/admin/signin` · `/admin/users` · `/admin/applications`

**API(9)**: `/api/auth/[...nextauth]` · `/api/applications` · `/api/counter` · `/api/otp/send`
· `/api/otp/verify` · `/api/track/open` · `/api/track/click` · `/admin/users/export.csv` · `/admin/applications/export.csv`

**섹션(라이브 17, page.tsx 순서대로)**: Hero · Benefits · JocodingIntro · TrustLogos · WhyNow
· WhoIsThisFor · ProblemAware · Solution · Partners · Curriculum · TakeHome · Instructor · NonDev
· Pricing · HowToJoin · FinalCTA · Faq
- ※ `CaseStudies.tsx`는 파일만 있고 **page.tsx에 미렌더(휴면)** — CSS 잔재만 존재. 필요 시 부활용.

**UI 컴포넌트(16)**: Nav · NavScrollEffect · Footer · MyPageDropdown · FloatingBar · StickyCTA
· CheckoutCTA · CountdownTimer · RevealOnScroll · SocialIcons · ReviewSignInForm(토스심사 로그인)
· GTMScript · GTMTracker · ViewItemTracker · GenerateLeadTracker · PurchaseTracker

**lib 유틸(9)**: `auth.ts` · `config.ts`(PAYMENT_ENABLED 분기·CTA href) · `email.ts`(Resend)
· `gtm.ts` · `octomo.ts`(SMS) · `signupConsent.ts`(동의 쿠키) · `countdown.ts`(마감 D-day)
· `viewerBands.ts`(관람수 시뮬) · `supabase/server.ts`(service_role)

**DB 테이블(7)**: users · applications · payments · otp_codes · admins · email_sends · email_events

**섹션 데이터 분리 패턴**: `curriculum.data.ts`처럼 긴 콘텐츠는 `*.data.ts`로 분리(컴포넌트와 데이터 분리).

---

## 🆕 신규 패턴 (axacademy 2기 빌드에서 캐논에 추가 · 2026-06)

> granter 캐논을 **고치면서** 이번 빌드(axacademy-landing)에서 새로 정립한 재사용 패턴.
> 각 파일은 복붙 가능한 구체 코드/판단 기준. 해당 Phase에서 같이 연다.

| 패턴 | 파일 | 어느 Phase | 한 줄 |
|---|---|---|---|
| **가격 변형(단일배포·경로분기)** | `reference/code-templates/price-variant.md` | P0(가격설계)·P3·P5·P8 | 페이지 1벌·경로로 가격만 분기, 서버 가격매핑(클라 금액 불신), 비공개 변형 noindex, 좌석 공유풀 |
| **운영자 Slack 신청 알림** | `reference/code-templates/slack-notify.md` | **P7 (7-B)** | 신청 INSERT 직후 Block Kit 웹훅, 시크릿 주입·미설정 스텁, actions 대신 mrkdwn 링크 |
| **섹션 도달 퍼널(sec_NN)** | `reference/code-templates/section-funnel.md` | P8 | 섹션별 진입 이벤트로 이탈 지점 분석, `lib/sections.ts` 단일출처(어드민 공유), DOM 무첨가 |
| **제품 UI 데모 섹션** | `reference/guides/demo-sections.md` | P3 | 정적 목업으로 "쓰는 모습" 보여주기(데이터 분리·PII 금지), mac-open-motion iframe의 형제 |
| **계좌이체 트랙(PG 없음)** | `reference/guides/no-pg-account-transfer.md` | P5·P6 생략 | 신청→입금안내메일→어드민 입금확인(confirmed)→좌석카운트. 토스/로그인/SMS 제외 |

- **가격 변형**은 P0 가격설계에서 변형 키·할인액을 먼저 정하면 P3(CTA)·P5(폼·API)·P8(이벤트 value)까지 깔끔히 관통한다.
- **섹션 퍼널**은 기존 P8 5이벤트(`gtm-events.md`)에 **추가**하는 레이어(중복 아님) — 섹션별 도달률이 추가로 보인다.
- **계좌이체 트랙**은 Track B에서 P6 결제·수강생 인증을 통째로 들어낸 가장 가벼운 출발점. PG가 필요해지면 Track A로 승격.

---

## 📎 부속 레퍼런스 (이 폴더)
- `reference/env-vars.md` — 환경변수 마스터 (.env.example 복붙)
- `reference/db-schema.sql` — Supabase 스키마 복붙 (7테이블, 함정 보정 포함)
- `reference/gtm-events.md` — GA4 이벤트 5종 + 헬퍼 + GTM 설정
- `reference/design-system-skeleton.css` — **(Phase 2 구조)** 브랜드 중립 스캐폴드(토큰구조·공통클래스·reveal·반응형·접근성). 복제 후 토큰 값만 교체
- `reference/design-phase-prompt.md` — **(Phase 2 비주얼)** 레퍼런스→팔레트·폰트 결정 프롬프트 + 디자인 스킬 연계

## 🧩 연계 재사용 컴포넌트 (형제 폴더)
- `../instructor-spotlight/` — 강사소개(글로우 인물) 섹션. 드롭인.
- `../mac-open-motion/` — 커리큘럼 핀 스크럽 + 맥북 데모 섹션. 드롭인.

---

_작성 2026-06-11 · 재번호 2026-06-12(Track B 랜딩 우선 = 캐논) · 출처 granter-landing main 역설계 · 가격/인원/카피는 상품별로 교체._
