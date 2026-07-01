# 토스페이먼츠 결제 코드 템플릿 (브랜드 중립)

> **출처**: `granter-landing/apps/web/app/pay/**` + `app/api/counter/route.ts` 실제 구현을 그대로 추출.
> **브랜드 중립화**: 상호·가격·기수(cohort)·상품명은 `{{PLACEHOLDER}}`로 치환. 토스 키는 env 참조 그대로 유지.
> **스택**: Next.js App Router(서버 컴포넌트) + Supabase(service_role) + NextAuth(`auth()`) + 토스 v2 위젯.
> **결제 흐름**: `/pay`(가드·신청조회·티어산정) → `PayWidget`(위젯 SDK·requestPayment) →
>   `/pay/success`(서버 confirm → payments INSERT → applications paid → 메일) / `/pay/fail`.
>   `/api/counter`는 얼리버드 카운트(approved 수). **신규** `/api/toss/webhook`은 결제상태 재동기화·멱등 보강.
>
> ## 전역 교체지점 (한 번에 grep)
> - `{{BRAND}}` — 상호/브랜드명 (예: "그랜터 × 조코딩AX 파트너스")
> - `{{COHORT}}` — 기수 코드 (예: "beta-2026")
> - `{{ORDER_NAME}}` — 결제창 상품명
> - `{{REVIEW_EMAIL_DOMAIN}}` — PG 심사용 계정 이메일 도메인 (예: "@review.granter.local")
> - `{{SUPPORT_EMAIL}}` — 실패 안내 문의 메일
> - 가격/티어 상수 — `lib/config.ts`의 `PRICING`·`SEATS`·`getAmount`·`formatKRW` (아래 ⓪ 참조)
> - DB 테이블/컬럼 — `users` / `applications` / `payments` (스키마는 `reference/db-schema.sql`)
> - env — `NEXT_PUBLIC_TOSS_CLIENT_KEY`(클라) · `TOSS_SECRET_KEY`(서버) · `NEXT_PUBLIC_SUPABASE_URL` · `SUPABASE_SERVICE_ROLE_KEY` · (신규) `TOSS_WEBHOOK_SECRET`

---

## ⓪ 가격·티어 설정 (lib/config.ts 발췌 — placeholder로 둠)

가격·좌석 수·기수는 **여기 한 곳**에서만 바꾸도록 모은다. 모든 파일이 이 상수를 참조한다.

```ts
// lib/config.ts (발췌)
// 교체지점: 숫자(가격·좌석)는 프로젝트 값으로. 통화 포맷은 ko-KR 고정.

export type CourseType = "offline" | "online";

// {{PRICING}} — 코스별 정가/얼리버드가
export const PRICING = {
  offline: { regular: 500_000, earlybird: 400_000 },
  online: { regular: 500_000, earlybird: 300_000 },
} as const;

/** 주어진 코스·티어에 맞는 결제 금액 */
export function getAmount(courseType: CourseType, isEarlybird: boolean): number {
  return isEarlybird ? PRICING[courseType].earlybird : PRICING[courseType].regular;
}

// {{SEATS}} — 얼리버드 좌석 cap (approved 누적 카운트로 티어 결정)
export const SEATS = {
  earlybirdTotal: 40,
  tier1Cap: 20, // approved < 20 → tier1
  tier2Cap: 40, // approved < 40 → tier2, 이상 → regular
} as const;

export const formatKRW = (n: number) => n.toLocaleString("ko-KR") + "원";
```

> **티어 산정 규칙(전 파일 공통)**: `payments` 중 `status='approved'` **누적 COUNT**로 결정.
> `count < tier1Cap → earlybird-tier1` / `< tier2Cap → earlybird-tier2` / `else regular`.
> 가격은 클라이언트 신뢰 금지 — success에서 서버가 동일 규칙으로 `expectedAmount` 재계산해 검증한다.

---

## ① /pay — 결제 페이지 (로그인 가드 · 신청 조회/생성 · 얼리버드 티어 산정)

```ts
// app/pay/page.tsx
// ─────────────────────────────────────────────────────────────────────────
// 출처: granter-landing app/pay/page.tsx
// 역할: (1) 로그인 가드 → (2) users·applications 조회/연결 → (3) approved 카운트로
//       티어 산정 → (4) PayWidget에 금액·주문명·고객정보 전달.
// 교체지점: {{COHORT}}, {{BRAND}}, {{ORDER_NAME}}, {{REVIEW_EMAIL_DOMAIN}}, 가격은 lib/config.
// 스냅샷 템플릿: UI(JSX) 마크업은 프로젝트 디자인에 맞게 갈아끼울 것. 데이터 흐름만 보존.
// ─────────────────────────────────────────────────────────────────────────
import { auth } from "@/lib/auth";
import { redirect } from "next/navigation";
import { getSupabaseAdmin } from "@/lib/supabase/server";
import Link from "next/link";
import { PRICING, SEATS, formatKRW, getAmount, type CourseType } from "@/lib/config";
import { PayWidget } from "./PayWidget";

export const metadata = { title: "결제 | {{BRAND}}" };

type Tier = "earlybird-tier1" | "earlybird-tier2" | "regular";

// 티어 산정: approved 누적 수 기준 (전 파일 공통 규칙)
function determineTier(paidCount: number): Tier {
  if (paidCount < SEATS.tier1Cap) return "earlybird-tier1";
  if (paidCount < SEATS.tier2Cap) return "earlybird-tier2";
  return "regular";
}

export default async function PayPage({
  searchParams,
}: {
  searchParams: Promise<{ type?: string }>;
}) {
  const params = await searchParams;
  const courseType: CourseType = params.type === "online" ? "online" : "offline";

  // (1) 로그인 가드
  const session = await auth();
  if (!session?.user?.id) redirect("/signin?from=/pay");

  // (2) DB 미연결 가드 (env 없으면 결제 비활성 UI)
  const supabase = getSupabaseAdmin();
  if (!supabase) {
    return (
      <main className="pay-wrap">
        <article className="pay-card">
          <h1>결제 시스템 준비 중</h1>
          <p>결제가 활성화되지 않았습니다. 잠시 후 다시 시도해주세요.</p>
          <Link href="/">← 홈으로 돌아가기</Link>
        </article>
      </main>
    );
  }

  // (3) 회원 조회
  const { data: user } = await supabase
    .from("users")
    .select("id, name, email, phone")
    .eq("id", session.user.id)
    .maybeSingle();
  if (!user) redirect("/apply");

  // (4) 이번 기수 신청 조회
  let application = (
    await supabase
      .from("applications")
      .select("id, status, cohort")
      .eq("user_id", session.user.id)
      .eq("cohort", "{{COHORT}}")
      .maybeSingle()
  ).data;

  // (4-b) user_id 없이 이메일로만 만들어진 orphan 신청을 현재 계정에 연결
  if (!application && user.email) {
    const { data: orphan } = await supabase
      .from("applications")
      .select("id, status, cohort")
      .is("user_id", null)
      .eq("email", user.email)
      .eq("cohort", "{{COHORT}}")
      .maybeSingle();

    if (orphan) {
      await supabase
        .from("applications")
        .update({ user_id: session.user.id })
        .eq("id", orphan.id);
      application = orphan;
    }
  }

  // (4-c) PG 심사용 계정은 /apply 폼을 건너뛰고 /pay 직접 접근 허용 → 즉석 pending 행 생성.
  //       실유저는 기존대로 /apply로 보내 정보를 입력받는다.
  const isReviewAccount = user.email?.endsWith("{{REVIEW_EMAIL_DOMAIN}}") ?? false;
  if (!application && isReviewAccount) {
    const { data: created } = await supabase
      .from("applications")
      .insert({
        user_id: session.user.id,
        name: user.name,
        email: user.email,
        phone: user.phone ?? "010-0000-0000",
        marketing_consent: false,
        cohort: "{{COHORT}}",
        status: "pending",
      })
      .select("id, status, cohort")
      .single();
    application = created;
  }

  if (!application) redirect("/apply");

  // (5) 이미 결제 완료면 중복 결제 차단
  if (application.status === "paid") {
    return (
      <main className="pay-wrap">
        <article className="pay-card">
          <h1>이미 결제가 완료되었습니다.</h1>
          <p>강의 안내는 입력하신 이메일({user.email})로 발송됩니다.</p>
          <Link href="/">← 홈으로 돌아가기</Link>
        </article>
      </main>
    );
  }

  // (6) 티어 산정 — approved 누적 COUNT
  const { count: paidCount } = await supabase
    .from("payments")
    .select("*", { count: "exact", head: true })
    .eq("status", "approved");

  const tier = determineTier(paidCount ?? 0);
  const isEarlybird = tier !== "regular";
  const amount = getAmount(courseType, isEarlybird);
  const regularPrice = PRICING[courseType].regular;
  const courseLabel = courseType === "offline" ? "오프라인" : "온라인";
  const orderName = `{{ORDER_NAME}} (${courseLabel}) — {{BRAND}}`;

  // (7) UI는 스냅샷일 뿐 — 핵심은 PayWidget에 넘기는 props.
  return (
    <main className="pay-wrap">
      <article className="pay-card">
        <h1>수강 신청 내역</h1>
        {/* 금액 표시: isEarlybird면 정가/할인/최종 분해, 아니면 정가 단독 */}
        {isEarlybird ? (
          <p>
            정가 {formatKRW(regularPrice)} − 할인 {formatKRW(regularPrice - amount)} ={" "}
            <strong>{formatKRW(amount)}</strong>
          </p>
        ) : (
          <p><strong>{formatKRW(amount)}</strong></p>
        )}

        <PayWidget
          applicationId={application.id}
          userId={user.id}
          amount={amount}
          tier={tier}
          orderName={orderName}
          customerEmail={user.email}
          customerName={user.name ?? ""}
          customerMobilePhone={user.phone ?? ""}
        />
      </article>
    </main>
  );
}
```

---

## ② PayWidget — 토스 v2 위젯 SDK 초기화 · requestPayment

```ts
// app/pay/PayWidget.tsx
// ─────────────────────────────────────────────────────────────────────────
// 출처: granter-landing app/pay/PayWidget.tsx (클라이언트 컴포넌트)
// 까다로운 부분(반드시 보존):
//   widgets({ customerKey }) → setAmount → renderPaymentMethods/renderAgreement
//   → requestPayment({ orderId, orderName, successUrl, failUrl })
// 로딩 순서: <Script afterInteractive> onLoad → window.TossPayments 사용 가능.
// env: NEXT_PUBLIC_TOSS_CLIENT_KEY (클라이언트 노출 키)
// orderId 포맷: `ord-${applicationId.slice(0,8)}-${Date.now()}` (DB toss_order_id unique와 매칭)
// ─────────────────────────────────────────────────────────────────────────
"use client";

import { useEffect, useRef, useState } from "react";
import Script from "next/script";
import Link from "next/link";

type Props = {
  applicationId: string;
  userId: string;
  amount: number;
  tier: string;
  orderName: string;
  customerEmail: string;
  customerName: string;
  customerMobilePhone: string;
};

// 토스 v2 위젯 인스턴스 최소 타입 (SDK 전역 주입)
type TossWidgets = {
  setAmount: (a: { value: number; currency: string }) => Promise<void>;
  renderPaymentMethods: (opts: { selector: string; variantKey?: string }) => Promise<void>;
  renderAgreement: (opts: { selector: string; variantKey?: string }) => Promise<void>;
  requestPayment: (opts: {
    orderId: string;
    orderName: string;
    customerEmail?: string;
    customerName?: string;
    customerMobilePhone?: string;
    successUrl: string;
    failUrl: string;
  }) => Promise<void>;
};

declare global {
  interface Window {
    TossPayments?: (clientKey: string) => {
      widgets: (opts: { customerKey: string }) => TossWidgets;
    };
  }
}

export function PayWidget(props: Props) {
  const {
    applicationId,
    userId,
    amount,
    orderName,
    customerEmail,
    customerName,
    customerMobilePhone,
  } = props;

  const widgetsRef = useRef<TossWidgets | null>(null);
  const [scriptLoaded, setScriptLoaded] = useState(false);
  const [widgetReady, setWidgetReady] = useState(false);
  const [agreed, setAgreed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clientKey = process.env.NEXT_PUBLIC_TOSS_CLIENT_KEY;

  // 위젯 초기화: customerKey=userId로 묶고 → setAmount → 두 위젯 병렬 렌더
  useEffect(() => {
    if (!scriptLoaded || !clientKey || !window.TossPayments) return;

    const tossPayments = window.TossPayments(clientKey);
    const widgetsInstance = tossPayments.widgets({ customerKey: userId });
    widgetsRef.current = widgetsInstance;

    (async () => {
      await widgetsInstance.setAmount({ value: amount, currency: "KRW" });
      await Promise.all([
        widgetsInstance.renderPaymentMethods({ selector: "#payment-method", variantKey: "DEFAULT" }),
        widgetsInstance.renderAgreement({ selector: "#agreement", variantKey: "AGREEMENT" }),
      ]);
      setWidgetReady(true);
    })().catch((e: unknown) => {
      setError(e instanceof Error ? e.message : "결제 위젯 초기화에 실패했습니다.");
    });
  }, [scriptLoaded, clientKey, userId, amount]);

  const handlePayment = async () => {
    if (!widgetsRef.current) return;
    if (!agreed) {
      setError("이용약관·개인정보처리방침·환불정책에 동의해주세요.");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      // orderId 포맷 — 서버 confirm·webhook이 이 값으로 payments.toss_order_id를 매칭한다.
      const orderId = `ord-${applicationId.slice(0, 8)}-${Date.now()}`;
      await widgetsRef.current.requestPayment({
        orderId,
        orderName,
        customerEmail,
        customerName,
        customerMobilePhone: customerMobilePhone.replace(/[^0-9]/g, ""), // 숫자만
        // successUrl: 토스가 paymentKey·orderId·amount를 쿼리로 붙여 리다이렉트.
        // courseType을 쿼리로 같이 넘겨 서버에서 expectedAmount 재계산에 사용.
        successUrl: `${window.location.origin}/pay/success?courseType=${new URLSearchParams(window.location.search).get("type") ?? "offline"}`,
        failUrl: `${window.location.origin}/pay/fail`,
      });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "결제 요청에 실패했습니다.");
      setSubmitting(false);
    }
  };

  // 키 미설정 시 결제 비활성 UI
  if (!clientKey) {
    return (
      <section className="pay-widget">
        <h2>결제 수단</h2>
        <p>결제 시스템이 아직 활성화되지 않았습니다. 관리자에게 문의해주세요.</p>
      </section>
    );
  }

  return (
    <>
      {/* 토스 v2 표준 위젯 SDK */}
      <Script
        src="https://js.tosspayments.com/v2/standard"
        strategy="afterInteractive"
        onLoad={() => setScriptLoaded(true)}
      />
      <section className="pay-widget">
        <h2>결제 수단</h2>
        <div id="payment-method" className="pay-method" />
        <div id="agreement" className="pay-agreement" />
        <label className="pay-policy-agree">
          <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} />
          <span>
            <Link href="/terms" target="_blank">이용약관</Link>,{" "}
            <Link href="/privacy" target="_blank">개인정보처리방침</Link>,{" "}
            <Link href="/refund" target="_blank">환불정책</Link>에 동의합니다. (필수)
          </span>
        </label>
        {error && <p className="pay-error">{error}</p>}
        <button
          type="button"
          className="btn btn-primary pay-submit"
          disabled={!widgetReady || !agreed || submitting}
          onClick={handlePayment}
        >
          {submitting ? "결제 진행 중..." : "결제하기"}
        </button>
        {!widgetReady && <p className="pay-loading meta">결제 위젯 로딩 중...</p>}
      </section>
    </>
  );
}
```

---

## ③ /pay/success — 서버 승인 confirm → payments INSERT → applications paid → 메일

```ts
// app/pay/success/page.tsx
// ─────────────────────────────────────────────────────────────────────────
// 출처: granter-landing app/pay/success/page.tsx (서버 컴포넌트)
// 흐름: 파라미터 검증 → 세션·신청 가드 → 멱등 체크(toss_order_id) → 금액 재검증
//       → 토스 confirm(POST /v1/payments/confirm, Basic 인증) → payments INSERT
//       → applications.status=paid → 확인 메일(논블로킹).
// 보안 핵심: amount는 클라이언트 신뢰 금지. 서버가 티어 재산정해 expectedAmount와 대조.
// env: TOSS_SECRET_KEY (Basic 인증, "secretKey:" base64)
// ─────────────────────────────────────────────────────────────────────────
import { auth } from "@/lib/auth";
import { redirect } from "next/navigation";
import Link from "next/link";
import { getSupabaseAdmin } from "@/lib/supabase/server";
import { SEATS, formatKRW, getAmount, type CourseType } from "@/lib/config";
import { sendPaymentConfirmEmail } from "@/lib/email";

export const metadata = { title: "결제 완료 | {{BRAND}}" };

type Tier = "earlybird-tier1" | "earlybird-tier2" | "regular";

function determineTier(paidCount: number): Tier {
  if (paidCount < SEATS.tier1Cap) return "earlybird-tier1";
  if (paidCount < SEATS.tier2Cap) return "earlybird-tier2";
  return "regular";
}

type TossConfirmResponse = {
  paymentKey: string;
  orderId: string;
  status: string;
  totalAmount: number;
  approvedAt?: string;
  [k: string]: unknown;
};

// 토스 결제 승인 — Basic 인증은 "{secretKey}:"를 base64 (콜론 뒤 비번 공란).
async function confirmTossPayment(
  paymentKey: string,
  orderId: string,
  amount: number,
): Promise<TossConfirmResponse> {
  const secretKey = process.env.TOSS_SECRET_KEY;
  if (!secretKey) throw new Error("TOSS_SECRET_KEY not configured");

  const basicAuth = Buffer.from(`${secretKey}:`).toString("base64");
  const res = await fetch("https://api.tosspayments.com/v1/payments/confirm", {
    method: "POST",
    headers: {
      Authorization: `Basic ${basicAuth}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ paymentKey, orderId, amount }),
    cache: "no-store",
  });

  const json = await res.json();
  if (!res.ok) {
    const code = typeof json?.code === "string" ? json.code : "UNKNOWN";
    const message = typeof json?.message === "string" ? json.message : "결제 승인에 실패했습니다.";
    throw new Error(`${code}: ${message}`);
  }
  return json as TossConfirmResponse;
}

export default async function PaySuccessPage({
  searchParams,
}: {
  searchParams: Promise<{ paymentKey?: string; orderId?: string; amount?: string; courseType?: string }>;
}) {
  const params = await searchParams;
  const { paymentKey, orderId, amount: amountStr } = params;
  const courseType: CourseType = params.courseType === "online" ? "online" : "offline";

  // (1) 토스 리다이렉트 파라미터 검증
  if (!paymentKey || !orderId || !amountStr) {
    redirect("/pay/fail?code=MISSING_PARAMS&message=" + encodeURIComponent("결제 정보가 누락되었습니다."));
  }
  const amount = Number(amountStr);
  if (!Number.isFinite(amount) || amount <= 0) {
    redirect("/pay/fail?code=INVALID_AMOUNT&message=" + encodeURIComponent("결제 금액이 유효하지 않습니다."));
  }

  // (2) 세션·DB 가드
  const session = await auth();
  if (!session?.user?.id) {
    redirect("/pay/fail?code=NO_SESSION&message=" + encodeURIComponent("로그인이 필요합니다."));
  }
  const supabase = getSupabaseAdmin();
  if (!supabase) {
    redirect("/pay/fail?code=DB_UNAVAILABLE&message=" + encodeURIComponent("데이터베이스가 활성화되지 않았습니다."));
  }

  // (3) 신청 가드
  const { data: application } = await supabase
    .from("applications")
    .select("id, status, user_id, cohort")
    .eq("user_id", session.user.id)
    .eq("cohort", "{{COHORT}}")
    .maybeSingle();
  if (!application) {
    redirect("/pay/fail?code=NO_APPLICATION&message=" + encodeURIComponent("신청 정보를 찾을 수 없습니다."));
  }

  // (4) 멱등 체크 — 같은 orderId가 이미 approved면 confirm 재호출 없이 성공 화면.
  //     (새로고침·이중 진입 방어. webhook과 함께 toss_order_id unique가 최종 방어선.)
  const { data: existingPayment } = await supabase
    .from("payments")
    .select("id, status, toss_payment_key")
    .eq("toss_order_id", orderId)
    .maybeSingle();
  if (existingPayment?.status === "approved") {
    return renderSuccess(amount);
  }

  // (5) 금액 재검증 — 서버가 티어 재산정해 기대 금액과 대조 (클라 금액 위변조 방어).
  const { count: paidCount } = await supabase
    .from("payments")
    .select("*", { count: "exact", head: true })
    .eq("status", "approved");
  const tier = determineTier(paidCount ?? 0);
  const isEarlybird = tier !== "regular";
  const expectedAmount = getAmount(courseType, isEarlybird);
  if (amount !== expectedAmount) {
    redirect("/pay/fail?code=AMOUNT_MISMATCH&message=" + encodeURIComponent("결제 금액이 일치하지 않습니다."));
  }

  // (6) 토스 승인
  let confirmed: TossConfirmResponse;
  try {
    confirmed = await confirmTossPayment(paymentKey, orderId, amount);
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "결제 승인 중 오류가 발생했습니다.";
    redirect("/pay/fail?code=CONFIRM_FAILED&message=" + encodeURIComponent(msg));
  }

  // (7) 기록 — payments INSERT (toss_order_id unique). raw_response에 원본 보관.
  await supabase.from("payments").insert({
    application_id: application.id,
    toss_payment_key: confirmed.paymentKey,
    toss_order_id: confirmed.orderId,
    amount,
    tier,
    status: "approved",
    paid_at: confirmed.approvedAt ?? new Date().toISOString(),
    raw_response: confirmed,
  });

  // (8) 신청 상태 전이
  await supabase.from("applications").update({ status: "paid" }).eq("id", application.id);

  // (9) 확인 메일 — 논블로킹(실패해도 결제는 성공 처리)
  const { data: paidUser } = await supabase
    .from("users")
    .select("name, email")
    .eq("id", session.user.id)
    .maybeSingle();
  if (paidUser?.email) {
    sendPaymentConfirmEmail(paidUser.email, paidUser.name ?? "고객").catch((e) =>
      console.error("[pay/success] email send error:", e),
    );
  }

  // 전환 추적 등은 purchase 메타로 렌더 컴포넌트에 넘긴다.
  return renderSuccess(amount, { transactionId: orderId, value: amount, tier });
}

function renderSuccess(
  amount: number,
  _purchase?: { transactionId: string; value: number; tier?: string },
) {
  return (
    <main className="pay-wrap">
      <article className="pay-card">
        <h1>결제가 완료되었습니다.</h1>
        <p>신청이 확정되었습니다. 안내 메일을 입력하신 이메일로 발송해드립니다.</p>
        <p><strong>{formatKRW(amount)}</strong></p>
        <Link href="/">← 홈으로 돌아가기</Link>
      </article>
    </main>
  );
}
```

---

## ④ /pay/fail — 실패 페이지

```ts
// app/pay/fail/page.tsx
// 출처: granter-landing app/pay/fail/page.tsx
// 역할: 토스 failUrl 또는 success 내부 redirect가 붙인 code·message 표시 + 재시도 동선.
// 교체지점: {{BRAND}}, {{SUPPORT_EMAIL}}
import Link from "next/link";

export const metadata = { title: "결제 실패 | {{BRAND}}" };

export default async function PayFailPage({
  searchParams,
}: {
  searchParams: Promise<{ code?: string; message?: string }>;
}) {
  const { code, message } = await searchParams;
  const displayMessage = message ?? "결제가 완료되지 않았습니다.";
  const displayCode = code ?? "UNKNOWN";

  return (
    <main className="pay-wrap">
      <article className="pay-card">
        <h1>결제가 완료되지 않았습니다.</h1>
        <p>{displayMessage}</p>
        <dl className="pay-info">
          <div><dt>코드</dt><dd><code>{displayCode}</code></dd></div>
          <div><dt>메시지</dt><dd>{displayMessage}</dd></div>
        </dl>
        <Link href="/pay" className="btn btn-primary">결제 다시 시도</Link>
        <p>
          반복해서 실패하는 경우{" "}
          <a href="mailto:{{SUPPORT_EMAIL}}">{{SUPPORT_EMAIL}}</a>로 문의해주세요.
        </p>
        <Link href="/">← 홈으로 돌아가기</Link>
      </article>
    </main>
  );
}
```

---

## ⑤ /api/counter — 얼리버드 카운트 (approved 수)

```ts
// app/api/counter/route.ts
// ─────────────────────────────────────────────────────────────────────────
// 출처: granter-landing app/api/counter/route.ts
// 역할: payments 중 status='approved' 누적 수를 반환 → 랜딩 "선착순 n명" 인디케이터.
// 방식: Supabase REST에 Prefer:count=exact + Range:0-0 → content-range 헤더에서 총계 파싱.
//       (SDK 없이 직접 fetch — 가벼운 카운트 전용. env 미설정 시 { paid: null }로 숨김.)
// env: NEXT_PUBLIC_SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
// ─────────────────────────────────────────────────────────────────────────
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!supabaseUrl || !serviceKey) {
    // 데이터소스 미연결 — 인디케이터 숨김 유지
    return NextResponse.json({ paid: null });
  }

  try {
    const res = await fetch(
      `${supabaseUrl}/rest/v1/payments?status=eq.approved&select=id`,
      {
        headers: {
          apikey: serviceKey,
          Authorization: `Bearer ${serviceKey}`,
          Prefer: "count=exact",
          Range: "0-0",
        },
      },
    );
    // "0-0/42" 형태 → 마지막 토막이 총계
    const contentRange = res.headers.get("content-range");
    const total = contentRange ? Number(contentRange.split("/").pop()) : 0;
    return NextResponse.json({ paid: Number.isFinite(total) ? total : 0 });
  } catch (err) {
    console.error("[counter] fetch failed:", err);
    return NextResponse.json({ paid: null });
  }
}
```

---

## ⑥ /api/toss/webhook — 멱등 웹훅 핸들러 (★신규 — 원본에 없음)

> **왜 필요한가**: success 페이지는 사용자가 리다이렉트로 돌아와야만 confirm이 실행된다.
> 사용자가 결제창에서 승인 직후 브라우저를 닫으면 `payments` 기록이 누락될 수 있다.
> 토스 웹훅은 이 누락을 서버-투-서버로 보완한다. `toss_order_id` unique 제약으로 중복 INSERT를
> 방지하고, 이미 있으면 상태만 동기화(멱등)한다.
>
> **⚠️ 토스 콘솔에서 확인할 것**:
> - 웹훅 URL 등록: `https://<도메인>/api/toss/webhook` (개발자센터 → 웹훅).
> - 페이로드 스키마(`eventType`, `data.*`)와 검증 방식은 토스 버전/콘솔 설정에 따라 다르다.
>   아래는 **일반적 형태** 기준 — 서명 헤더 이름·검증 알고리즘은 콘솔 문서로 확정하라.
> - confirm은 success에서 이미 끝났다고 가정. 웹훅은 **승인 상태 재동기화 전용**이며
>   여기서 `/v1/payments/confirm`을 다시 호출하지 않는다(이중 승인 방지).

```ts
// app/api/toss/webhook/route.ts
// ─────────────────────────────────────────────────────────────────────────
// 출처: ★신규 작성 (granter-landing 원본에 없음). ①~⑤의 DB 스키마·상수를 재사용.
// 역할: 토스 결제상태 변경 웹훅 수신 → payments 멱등 upsert로 success 누락 보완.
// 멱등성: toss_order_id unique. 행이 없으면 INSERT, 있으면 상태 변할 때만 UPDATE.
// 검증: TOSS_WEBHOOK_SECRET 기반 서명 헤더 검증(아래 verifySignature) — 헤더명·알고리즘은
//       토스 콘솔에서 확정. 검증 실패/시크릿 미설정 시 401.
// env: TOSS_SECRET_KEY(상태 재조회용, 선택) · TOSS_WEBHOOK_SECRET(서명 검증) ·
//      NEXT_PUBLIC_SUPABASE_URL · SUPABASE_SERVICE_ROLE_KEY
// 교체지점: 토스 status → 내부 status 매핑(STATUS_MAP), 서명 검증 방식.
// ─────────────────────────────────────────────────────────────────────────
import { NextResponse } from "next/server";
import crypto from "node:crypto";
import { getSupabaseAdmin } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs"; // crypto + raw body 필요

// 토스 결제 status(DONE/CANCELED/...) → 내부 payments.status
// ⚠️ 토스 콘솔에서 실제 status 값 목록 확인 후 매핑 보정할 것.
const STATUS_MAP: Record<string, "approved" | "cancelled" | "refunded" | "failed"> = {
  DONE: "approved",
  CANCELED: "cancelled",
  PARTIAL_CANCELED: "cancelled",
  ABORTED: "failed",
  EXPIRED: "failed",
};

// 토스 웹훅 페이로드(일반적 형태). 버전 의존부는 콘솔에서 확인.
type TossWebhookPayload = {
  eventType?: string; // 예: "PAYMENT_STATUS_CHANGED"
  data?: {
    paymentKey?: string;
    orderId?: string;
    status?: string;
    totalAmount?: number;
    approvedAt?: string;
    [k: string]: unknown;
  };
};

// 서명 검증 — HMAC-SHA256(raw body, secret)을 헤더와 timing-safe 비교.
// ⚠️ 헤더 이름·서명 인코딩(base64/hex)·서명 대상은 토스 콘솔 스펙으로 확정.
function verifySignature(rawBody: string, signatureHeader: string | null, secret: string): boolean {
  if (!signatureHeader) return false;
  const expected = crypto.createHmac("sha256", secret).update(rawBody, "utf8").digest("base64");
  const a = Buffer.from(signatureHeader);
  const b = Buffer.from(expected);
  if (a.length !== b.length) return false;
  return crypto.timingSafeEqual(a, b);
}

export async function POST(req: Request) {
  // (1) 시크릿 가드
  const webhookSecret = process.env.TOSS_WEBHOOK_SECRET;
  if (!webhookSecret) {
    console.error("[toss/webhook] TOSS_WEBHOOK_SECRET not configured");
    return NextResponse.json({ error: "not_configured" }, { status: 500 });
  }

  // (2) raw body 확보 후 서명 검증 (JSON 파싱 전에 검증해야 함)
  const rawBody = await req.text();
  const signature =
    req.headers.get("tosspayments-webhook-signature") ?? // ⚠️ 콘솔에서 실제 헤더명 확인
    req.headers.get("x-toss-signature");
  if (!verifySignature(rawBody, signature, webhookSecret)) {
    return NextResponse.json({ error: "invalid_signature" }, { status: 401 });
  }

  // (3) 페이로드 파싱·검증
  let payload: TossWebhookPayload;
  try {
    payload = JSON.parse(rawBody) as TossWebhookPayload;
  } catch {
    return NextResponse.json({ error: "invalid_json" }, { status: 400 });
  }

  const data = payload.data;
  const orderId = data?.orderId;
  const tossStatus = data?.status;
  if (!orderId || !tossStatus) {
    return NextResponse.json({ error: "missing_fields" }, { status: 400 });
  }

  const mappedStatus = STATUS_MAP[tossStatus];
  if (!mappedStatus) {
    // 처리 대상 아님 — 200으로 ack해 재전송 폭주 방지.
    return NextResponse.json({ ok: true, ignored: tossStatus });
  }

  const supabase = getSupabaseAdmin();
  if (!supabase) {
    // 일시 장애 — 5xx로 응답하면 토스가 재시도한다.
    return NextResponse.json({ error: "db_unavailable" }, { status: 503 });
  }

  // (4) 멱등 처리 — toss_order_id로 기존 행 조회
  const { data: existing } = await supabase
    .from("payments")
    .select("id, status, application_id")
    .eq("toss_order_id", orderId)
    .maybeSingle();

  if (existing) {
    // 이미 동일 상태면 no-op (멱등). 상태 전이가 있을 때만 UPDATE.
    if (existing.status !== mappedStatus) {
      await supabase
        .from("payments")
        .update({
          status: mappedStatus,
          toss_payment_key: data?.paymentKey ?? undefined,
          paid_at: mappedStatus === "approved" ? data?.approvedAt ?? new Date().toISOString() : undefined,
          raw_response: payload,
        })
        .eq("id", existing.id);

      // approved로 전이 시 신청 상태도 동기화 (success 누락 보완 지점)
      if (mappedStatus === "approved" && existing.application_id) {
        await supabase
          .from("applications")
          .update({ status: "paid" })
          .eq("id", existing.application_id);
      }
    }
    return NextResponse.json({ ok: true, idempotent: true });
  }

  // (5) success가 기록을 남기지 못한 경우 — orderId로 신청을 역추적해 보강 INSERT.
  //     orderId 포맷 `ord-${app_id8}-${ts}`에서 앞 8자리는 식별 힌트일 뿐 신뢰 금지.
  //     application 매핑이 불확실하면 application_id 없이 기록만 남기고 운영에서 reconcile.
  //     (toss_order_id unique 제약이 동시 success/webhook 이중 INSERT를 최종 차단.)
  const { error: insertError } = await supabase.from("payments").insert({
    application_id: existing?.application_id ?? null, // null이면 reconcile 대상
    toss_payment_key: data?.paymentKey ?? null,
    toss_order_id: orderId,
    amount: data?.totalAmount ?? 0,
    status: mappedStatus,
    paid_at: mappedStatus === "approved" ? data?.approvedAt ?? new Date().toISOString() : null,
    raw_response: payload,
  });

  // unique 위반(=success가 방금 INSERT) → 멱등 성공으로 흡수
  if (insertError && insertError.code === "23505") {
    return NextResponse.json({ ok: true, idempotent: true });
  }
  if (insertError) {
    console.error("[toss/webhook] insert error:", insertError);
    return NextResponse.json({ error: "insert_failed" }, { status: 500 });
  }

  return NextResponse.json({ ok: true });
}
```

> **운영 노트**
> - `application_id`가 null인 webhook-only 행은 별도 reconcile 작업으로 신청과 매칭한다
>   (orderId·paymentKey로 토스 조회 → 고객 식별). DB에서 `application_id is null and status='approved'` 모니터링.
> - 토스는 2xx를 받을 때까지 재시도한다. 처리 불가/무시 케이스는 200, 일시 장애는 5xx로 응답해 재시도를 유도.
> - `payments.toss_order_id`에 **unique 제약 필수** (db-schema.sql 기준 이미 있음) — 멱등성의 최종 방어선.
```
