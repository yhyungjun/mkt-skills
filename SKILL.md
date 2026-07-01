---
name: vibe-landing
description: |
  강의(온라인/오프라인) 사전예약·결제 랜딩페이지를 기획(PRD)부터 QA·배포까지 14단계로
  순차 빌드하는 풀스택 플레이북. 소셜로그인(Google·Kakao·Naver)·토스결제·SMS인증·자동메일·
  GA4/GTM 트래킹·어드민·SEO/성능까지 포함. granter-landing 역설계 + 프로덕션 보강.
  **사용자(조코딩AX) 한국어 강의 랜딩 전용.** 드롭인 섹션(mac-open-motion·instructor-spotlight)과
  브랜드 중립 디자인 스켈레톤 번들.
  Use when asked to "강의 랜딩 처음부터 만들어", "사전예약/결제 페이지 풀스택", "랜딩 빌드 순서대로",
  "결제·로그인·메일·GA까지 다 있는 강의 페이지", "lecture landing playbook".
  단순 정적 골격만 필요하면 korean-landing-bootstrap을, 결제/인증/트래킹까지 풀스택이면 이 스킬.
---

# Vibe Landing — 강의 랜딩 풀스택 플레이북

강의 사전예약·결제 랜딩을 **기획 → 배포 → QA**까지 14단계(P0~P13)로 순차 빌드한다.
백엔드(DB·인증·결제·메일)·트래킹·어드민·SEO/성능까지 검증된 순서로 안내한다.

## 언제 발동
- 강의/교육 상품의 **풀스택** 랜딩(결제·소셜로그인·자동메일·GA 포함)을 새로 만들 때.
- 단순 정적 상세페이지 골격만이면 → `korean-landing-bootstrap`.

## 첫 행동 (중요)
1. **`reference/playbook.md`를 읽어라** — STEP 0(결제 방식 분기) + 14 Phase 상세(구현·함정·코드경로·의존성)가 전부 거기 있다.
2. **결제 방식부터 고른다(STEP 0, 구성 1순위)**: 모델1 토스PG / 모델2 계좌이체 / 모델3 외부폼 중 택1
   → `playbook.md` "STEP 0" 표가 가리키는 모듈만 빌드(나머지 미구현). 가격 변형 필요 여부도 같이(직교).
3. **`reference/features-checklist.md`로 진행 상황을 추적**한다(체크박스).
4. 사용자에게 시작점을 확인: 새 프로젝트인가 / 어느 Phase부터인가 / (모델1이면) `PAYMENT_ENABLED` 동선.

## 빌드 순서 (번호 = 빌드 순서, **Track B 랜딩 우선 = 캐논**)
```
STEP0 결제방식 → P0 기획 → P1 셋업 → P2 디자인 → P3 섹션(🔁콘텐츠루프) → P3.5 프리뷰배포+8A 랜딩이벤트
→ P4 DB → P5.0 ⚖️법무게시 → P5 폼 → 8B 전환이벤트 → P6 결제 → P7 메일+🔔Slack알림 → P9 인증 → P10 어드민
→ P11 마감(SEO/에러/성능) → P12 배포 → P13 QA
```
- **STEP0 결제 방식**이 1순위 분기(모델1/2/3) — 모델별 활성 단계만 빌드(playbook STEP 0 표).
- **P3 섹션(랜딩)은 P2 토대에만 의존** → 백엔드보다 먼저. **🔁 콘텐츠 반복 루프가 P3의 본체**(단발 아님 — 실측 git 절반이 카피·디자인 반복).
- 🆕 **P3.5 프리뷰 배포** = Track B "조기 배포"의 실행 지점. **8A 랜딩 이벤트**(view_item·섹션퍼널, P3만 의존)를 여기서 켠다.
- ⚖️ 🆕 **P5.0 법무 게시는 폼(P5) 전**(HIGH·모델 무관): PII 폼 라이브면 개인정보처리방침·동의가 법적 선행조건.
- **트래킹 분할**: 8A(랜딩, 일찍) / **8B 전환 이벤트**(generate_lead·purchase, P5·P6 의존).
- **P2 디자인 ∥ P4 DB 병렬 가능**. 신청폼(P5)은 DB(P4)에 의존 → 폼 전 DB 또는 stub.
- **P6 결제·P7 메일은 선택**(계좌이체·외부폼이면 생략). 인증(P9)은 어드민만이면 Google role만.
- **P13 QA는 독립 품질 게이트** — 통과 전 정식 오픈/광고 금지.

### 순서 변형 — Track A: 풀스택 결제 (DB·인증을 섹션 앞으로)
토스 PG 결제 + 소셜로그인(수강생 계정)이면, **Nav 로그인 표시·결제 세션** 때문에 **DB·인증을 섹션보다 먼저** 깐다:
```
P0 → P1 → P2 → P4 DB → P9 인증 → P3 섹션 → P5 폼 → P6 결제 → P7 메일 → P8 트래킹 → P10 → P11 → P12 → P13
```
- 번호는 같고 순서만 당김(인증·DB를 P3 섹션 앞으로). P6 결제·P7 메일은 이 트랙의 필수.
- 프로젝트 성격에 맞게 택1. 상세는 `playbook.md`의 "순서 변형 트랙".

## 번들 자산 (이 스킬 폴더)

**기획·진행**
- `reference/playbook.md` — 마스터 14단계 상세(단일 출처).
- `reference/features-checklist.md` — 순차 체크리스트.
- `reference/env-vars.md` — 환경변수 마스터(.env.example 복붙).
- `reference/db-schema.sql` — Supabase 7테이블 복붙.

**코드 템플릿** (`reference/code-templates/` — 디버깅 끝난 복붙 코드)
- `auth.md` / `auth-pages.md` — Auth.js v5(Naver 커스텀·Kakao placeholder·동의쿠키·전화정규화·심사계정) + signup/signin.
- `payment.md` — Toss v2 위젯·success confirm·/api/counter + **/api/toss/webhook(멱등, 신규)**.
- `tracking.md` — lib/gtm.ts·GTMScript·Tracker 4종·CheckoutCTA(이벤트 5종 배선).
- `lib-core.md` — config.ts(PAYMENT_ENABLED 분기)·supabase/server.ts(stub)·RevealOnScroll.
- `email-sms.md` — email.ts(Resend)·octomo.ts·OTP 라우트.
- `forms.md` — applications API·preorder submitPreorder 서버액션.
- `bulk-mail-appsscript.md` — Apps Script 대량발송(**secret 분리 안전판**)+추적픽셀.
- `admin.md` — **어드민 전 영역(P10)**: 레이아웃·인증가드, 공용 날짜선택(adminRange·RangePicker), 대시보드 통계·설문차트(Recharts), 트래픽(GA4 페처·커스텀 SVG 퍼널·히트맵), 신청자·가입자 표·필터·CSV + CSS 일괄.
- 🆕 `price-variant.md` — **가격 변형(단일배포·경로분기)**: variant 모듈·PRICE_BY_VARIANT·VariantProvider·CTA `?v=` 전달·서버 재검증·noindex·좌석 공유풀(P0·P3·P5·P8).
- 🆕 `slack-notify.md` — **운영자 Slack 신청 알림**: Block Kit 웹훅·시크릿 주입·미설정 스텁·mrkdwn 링크(대화형 경고 회피)(**P7 7-B**, 신청 INSERT 직후).
- 🆕 `section-funnel.md` — **섹션 도달 퍼널(sec_NN)**: `lib/sections.ts` 단일출처 + IntersectionObserver 트래커(어드민 공유, DOM 무첨가)(P8).

**외부 설정 절차** (`reference/setup/`)
- `supabase-setup.md` · `oauth-console-setup.md`(Google·Kakao·Naver) · `toss-setup.md`(PG심사·웹훅) · `resend-setup.md`(DNS) · `octomo-setup.md` · `deploy-setup.md`(Cloudflare/Vercel) · `gtm-ga4-setup.md`.

**판단·작문·정책 가이드** (`reference/guides/`)
- `section-narrative.md`(**섹션 순서 = 설득 아크 + 예비구매자 의미**) · `design-devices.md`(**시각·모션·인터랙션 장치 + 설득 목적**)
- `copywriting-guide.md`(섹션별 설득구조) · `legal-boilerplate.md`(약관/개인정보/환불 ⚠️법적검토) · `pg-review-guide.md` · `p0-questions.md`(기획 질문 템플릿) · `troubleshooting.md`(함정 모음).
- 🆕 `demo-sections.md`(**제품 UI 데모 섹션** — 정적 목업·데이터분리·PII 금지, P3) · 🆕 `no-pg-account-transfer.md`(**계좌이체 트랙** — PG·로그인·SMS 제외 동선, P5·P6 생략).

**디자인 (P2)**
- `reference/design-system-skeleton.css` — **(구조)** 브랜드 중립 스캐폴드. 복제 후 토큰 값만 교체.
- `reference/design-phase-prompt.md` — **(비주얼)** 색·폰트 결정 프롬프트.
- `reference/gtm-events.md` — GA4 이벤트 + GTM 콘솔 설정.

**드롭인 섹션** (`assets/`)
- `mac-open-motion/` — 커리큘럼 핀 스크럽 + 맥북 데모(🤖 적용지침). `instructor-spotlight/` — 글로우 인물 강사소개(🤖 적용지침).

> 각 Phase에서 해당 reference 파일을 열어 복붙·적용한다. 코드 템플릿은 placeholder만 교체하면 동작.

## Phase 2 디자인 원칙 (핵심)
- **구조 = 코드 복제**: `design-system-skeleton.css`를 그대로 복제(브랜드 무관·검증됨). 변수명·공통클래스·reveal·반응형·접근성 변경 금지.
- **비주얼 = 프롬프트**: `design-phase-prompt.md`로 매번 새로 팔레트·폰트·무드 결정 → 토큰 값만 주입.
- ⚠️ 라이브 granter 레포를 참조하지 말 것 — 번들 스냅샷이 단일 출처.

## 연계 스킬 (해당 Phase에서 같이 호출)
- `vercel-plugin:nextjs`, `vercel-plugin:bootstrap` — 최신 Next.js/Vercel API 시그니처(P1·P4).
- `korean-landing-bootstrap` — 정적 섹션 골격이 별도로 필요할 때(P3).
- `korean-social-auth-stack` — OAuth 3사 셋업(P9).
- `toss-payments-setup`, `kr-payment-merchant-onboarding` — 결제·PG 심사(P6).
- `earlybird-tier-counter` — 얼리버드 티어 카운터(P6).
- `gtm-funnel-tracking` — GA4 퍼널 이벤트(P8).
- `ui-ux-pro-max`, `design-shotgun`, `design-review` — 비주얼 시안(P2).
- `acceptance-criteria` — 기획 합격기준(P0). `qa`/`browse` — QA(P13).

## 사용자 컨벤션 (반드시 따를 것)
- 패키지 매니저 **npm**(`cd apps/web && npm run dev`).
- `cohort`·가격·카피는 **상품마다 교체**(하드코딩 금지).
- 완성 섹션은 `~/Desktop/dev/ld_archive/`에 모으고, 섹션 완성 시 저장 여부를 먼저 묻는다.

## 완료 기준
`features-checklist.md`의 P0~P13 전 항목 체크 + P13 런치 게이트 통과.
