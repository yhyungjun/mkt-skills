# 강의 랜딩 전체 기능 체크리스트 (순차)

> 기획(PRD)부터 QA까지 전 기능을 빌드 순서대로. 빌드하며 하나씩 `[x]` 체크.
> 상세 구현·함정·코드 경로는 `playbook.md`의 동일 Phase 참조.
> 빌드 **순서**는 Track B(랜딩 우선·기본/캐논, 아래 번호 그대로) / Track A(풀스택 결제·변형, DB·인증을 섹션 앞으로) 중 택1 — `playbook.md` "순서 변형 트랙" 참조. 체크 항목 자체는 동일.

## STEP 0 — 결제 방식 선택 (★ 가장 먼저 · 구성 분기)
- [ ] **결제 모델 택1** → `playbook.md` "STEP 0" 표:
  - [ ] 모델1 · 토스 PG(Track A: P4·P9·P6·P7 포함, `/pay`)
  - [ ] 모델2 · 계좌이체(Track B: `/apply`·입금메일·Slack·confirmed, **P6·P9수강생·SMS 제외**)
  - [ ] 모델3 · 외부 폼/링크(랜딩만, P4~P10 대부분 생략)
- [ ] (직교) 가격 변형 필요 여부 → 있으면 `code-templates/price-variant.md`
- [ ] ⇒ 고른 모델이 가리키는 P단계만 빌드. 아래 체크리스트에서 해당 없는 항목은 스킵.

## P0 — 기획 / PRD
- [ ] 상품 정의(강의명·`cohort`·정가·얼리버드 티어/할인/인원) — **cohort는 설정값화**
- [ ] 동선 결정 → `PAYMENT_ENABLED` 초기값(사전예약 vs 결제)
- [ ] 설문 항목 확정(형태·요일·시간대·지역·직군·채널·매출·관심강의·의견)
- [ ] 수집정보·동의(PIPA 목적 명시), 마케팅 동의
- [ ] 법무 콘텐츠 사전 확보(약관·개인정보·**환불정책 법적검토**) — 리드타임 김
- [ ] 섹션 카피·순서, 도메인·발신 이메일

## P1 — 셋업
- [ ] Next16+React19+TS+ESLint, Tailwind4
- [ ] 의존성(supabase·next-auth@beta·recharts·bcryptjs·resend)
- [ ] `.env.example`(env-vars.md), 배포구성(wrangler/open-next/next.config)
- [ ] `lib/config.ts`(PAYMENT_ENABLED 분기·CTA href·cohort)

## P2 — 디자인 시스템
- [ ] (2-0) 레퍼런스 수집 → `design-phase-prompt.md` 프롬프트로 팔레트·폰트·무드 확정
- [ ] (2-0) 디자인 스킬 연계(ui-ux-pro-max·design-shotgun·design-review)
- [ ] (2-1) `design-system-skeleton.css` 복제 → 토큰 값만 주입(구조 불변)
- [ ] 폰트 로딩(웹폰트 link + next/font), RevealOnScroll, 대비/접근성 검증

## P3 — 랜딩 섹션 (17)
- [ ] Hero·Benefits·(Creator)Intro·TrustLogos·WhyNow·WhoIsThisFor·ProblemAware·Solution
- [ ] Partners·Curriculum(→mac-open-motion)·TakeHome·Instructor(→instructor-spotlight)·NonDev·Pricing·HowToJoin·FinalCTA·Faq
- [ ] (선택) **USP/가치 총정리**(→usp-value-stack): "이만큼 배우고 남긴다·남들엔 없는 N가지" — 해결 직후 or 가격 직전, TakeHome과 초점 분리
- [ ] 공통 UI: Nav·Footer·FloatingBar·StickyCTA, examples iframe + 맥북 프레임
- [ ] (Track A면) Nav 로그인표시 위해 P9 인증 선행
- [ ] 🔁 **콘텐츠 반복 루프**: 콘텐츠/데이터 분리(`content.ts`·`*.data.ts`) → 초안→리뷰(`design-review`/`browse`)→수정 수렴
- [ ] **설득 아크 점검**(`section-narrative.md`·`copywriting-guide.md`), 완성 섹션 아카이브 폴더에 저장

## P3.5 — 프리뷰 배포 체크포인트 (Track B "조기 배포" 실행)
- [ ] 프리뷰 배포(CF/Vercel preview, 백엔드 stub OK) → 실기기·이해관계자 공유 피드백 → 3-X 루프 환류
- [ ] **8A 랜딩 이벤트 조기 활성**(view_item·섹션퍼널 — 폼/결제 없이 가능)
- [ ] ⚠️ 프리뷰는 `noindex`(미완성본 색인·유출 방지)

## P4 — DB (Supabase)
- [ ] 프로젝트·키 발급, `db-schema.sql` 적용(users·applications·payments·otp_codes·admins·email_sends·email_events)
- [ ] `lib/supabase/server.ts`(service_role, stub 모드), 전 테이블 RLS on
- [ ] 설문 컬럼 명시, email_events 포함, onboarded_at 판정 기준

## P5.0 — ⚖️ 법무 페이지 선행 게이트 (폼 가동 전 · HIGH · 모델 무관)
- [ ] `/privacy` 게시 + 폼 **수집·이용 동의 체크**(필수, 마케팅 동의와 분리) — PII 폼 라이브 전 필수
- [ ] PII 경로(폼·완료·메일)에 목적·보관기간·위탁 명시. `/terms`·`/refund`은 결제/입금 시점까지
- [ ] (모델3 외부폼도 개인정보 안내 필요) 본문=`legal-boilerplate.md`(법적검토 필수)

## P5 — 폼 (온보딩·사전예약·신청)
- [ ] `/onboarding` + SMS OTP(`/api/otp/send`·`/verify`, OCTOMO, 쿨다운/TTL)
- [ ] `/preorder`+SurveyForm → `submitPreorder()` applications INSERT → `/preorder/done`
- [ ] `/apply`+done, `POST /api/applications`(검증·stub)
- [ ] **봇/허니팟/레이트리밋**(공개 엔드포인트 보호)

## P6 — 결제 (Toss) — 선택(계좌이체·외부폼이면 생략)
- [ ] `/pay`(로그인가드·신청조회/생성·티어산정), `PayWidget`(v2 위젯)
- [ ] `/pay/success`(승인 confirm→payments/applications), `/pay/fail`, `/api/counter`
- [ ] PG 심사 모드(@review.*), **Toss 웹훅 재동기화(멱등)**

## P7 — 자동 메일 + 운영자 알림
- [ ] **7-A 고객 메일**: Resend 결제완료/입금안내(`lib/email.ts`), AppsScript 대량발송(email_sends)
- [ ] 오픈/클릭 추적(`/api/track/open`·`/click` + email_events)
- [ ] **발송 한도/도메인 워밍업**(Gmail 쿼터·SPF/DKIM/DMARC)
- [ ] 🔔 **7-B 운영자 Slack 알림**(모델 무관 권장): `lib/notify.ts` Block Kit → `/api/applications` INSERT 직후 발화
- [ ] 시크릿 `SLACK_APPLICATIONS_WEBHOOK_URL`(vars 아님)·미설정 스텁·try/catch 격리·mrkdwn 링크 — `slack-notify.md`

## P8 — 분석 / GA·GTM (8A 랜딩=P3 의존 / 8B 전환=P5·P6 의존)
- [ ] 공통: `lib/gtm.ts`+GTMScript, sessionStorage 가드
- [ ] **8A 랜딩**(P3.5에 조기 활성): view_item·begin_checkout(CTA 래퍼)·🆕 섹션퍼널 sec_NN(`sections.ts`)
- [ ] **8B 전환**(폼·결제 후): generate_lead, (모델1) login·purchase
- [ ] GTM: GA4 Config + Event 태그(섹션퍼널 `^sec_\d+_` 정규식 1개) + 전환 별표

## P9 — 인증 / OAuth
- [ ] `lib/auth.ts`(Auth.js v5 JWT), Google·Kakao·Naver(커스텀)·toss-review(Credentials)
- [ ] callbacks(signIn 동의쿠키+users upsert / jwt admin role / session)
- [ ] `/api/auth/[...nextauth]`, `/signup`(동의쿠키)·`/signin`(AccessDenied 안내)
- [ ] Nav 로그인표시(MyPageDropdown), 전화 정규화, isAdminEmail
- [ ] (어드민만 필요한 Track B면 Google role만 가볍게)

## P10 — 어드민 (선택)
- [ ] `/admin`(통계 Recharts)·users·applications + CSV export, 권한가드
- [ ] **환불/취소 액션**(토스 취소 API + 상태 동기화)

## P11 — 프로덕션 마감 / 하드닝
- [ ] **SEO**: sitemap.ts·robots.ts·JSON-LD(Course/FAQ/Org)·canonical·메타·아이콘
- [ ] **에러/404/loading 바운더리**(not-found·error·global-error·loading)
- [ ] **이미지 최적화/성능예산**(next/image·WebP·priority, LCP<2.5s)
- [ ] **모니터링/에러 트래킹**(Sentry/CF 로그), 분석·개인정보 동의(PIPA), (선택)PWA manifest

## P12 — 배포 / 인프라
- [ ] 프로덕션 env(public/secret), OAuth redirect 등록, Toss 실키+웹훅 URL
- [ ] Resend 도메인 인증, 정책/사업자정보 실제값, GTM 게시, deploy
- [ ] **통신판매업 신고**(⚠️ PG 승인 *후* 순서): 구매안전서비스 확인증 → 관할 구청 신고 → **신고번호를 Footer + 약관 3p 회사정보에 입력·재배포**

## P13 — QA / 런치 (품질 게이트)
- [ ] 자동화 테스트(결제·OTP·폼·티어 단위 + Playwright E2E)
- [ ] 배포 전: E2E 동선·폼/봇·반응형/접근성·에러페이지·Core Web Vitals
- [ ] 배포 후: OAuth 실로그인·**결제 실거래1건+웹훅**·GA4 퍼널·메일추적·심사계정·SEO·모니터링
- [ ] ✅ 런치 게이트 통과 후 정식 오픈/광고
