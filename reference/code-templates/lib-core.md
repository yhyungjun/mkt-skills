# lib-core — config / supabase-admin / RevealOnScroll

> Brand-neutral templates extracted from `granter-landing` (apps/web).
> Snapshot: 2026-06-11. Source repo: a Next.js (App Router) Korean landing page.
> Replace every `__PLACEHOLDER__` token. Keys come from env, never hardcode secrets.
>
> Files in this doc:
> - `lib/config.ts` — pricing, deadlines, `PAYMENT_ENABLED` branch, CTA routing
> - `lib/supabase/server.ts` — `getSupabaseAdmin` (null-stub) / `requireSupabaseAdmin`
> - `components/ui/RevealOnScroll.tsx` — IntersectionObserver reveal (threshold 0.12)

---

## `lib/config.ts`

Source: `apps/web/lib/config.ts`.
Replacement points: `__BRAND__`, `__COHORT__`, pricing/seat numbers, the `DEADLINES`
dates, and the post-onboarding / CTA target paths (`/pay`, `/preorder`, `/signup`).

PRESERVE: the `PAYMENT_ENABLED` toggle pattern. It reads a **public** env flag
(`NEXT_PUBLIC_PAYMENT_ENABLED === "true"`) and flips routing between a pre-order
flow and a payment flow. It is a branch flag, not a secret — that is why
`NEXT_PUBLIC_` exposure is acceptable.

```ts
export const SITE = {
  brand: "__BRAND__", // e.g. "브랜드 × 파트너"
  cohort: "__COHORT__", // e.g. "2026 BETA"
} as const;

export type CourseType = "offline" | "online";

export const PRICING = {
  offline: { regular: 500_000, earlybird: 400_000 },
  online: { regular: 500_000, earlybird: 300_000 },
} as const;

/** 주어진 코스·티어에 맞는 결제 금액 */
export function getAmount(courseType: CourseType, isEarlybird: boolean): number {
  return isEarlybird
    ? PRICING[courseType].earlybird
    : PRICING[courseType].regular;
}

export const SEATS = {
  earlybirdTotal: 40,
  tier1Cap: 20,
  tier2Cap: 40,
} as const;

/** 모집/개강 마감일 (KST 날짜). 히어로 D-day 배지가 가장 가까운 마일스톤을 카운트다운. */
export const DEADLINES = {
  preorder: "__YYYY-MM-DD__", // 사전예약 모집 마감
  cohort1Open: "__YYYY-MM-DD__", // 얼리버드 결제 오픈
  cohort1Close: "__YYYY-MM-DD__", // 정규 1기 모집 마감
  cohort1Start: "__YYYY-MM-DD__", // 1기 개강
} as const;

export const formatKRW = (n: number) =>
  n.toLocaleString("ko-KR") + "원";

/**
 * PG(결제대행) 심사 통과 여부 토글.
 * false → /onboarding 완료 후 /preorder(사전예약)로 라우팅
 * true  → /onboarding 완료 후 /pay(결제)로 라우팅
 *
 * NEXT_PUBLIC_ 접두어가 붙어 클라이언트 번들에도 노출되지만 비밀이 아니라 분기 플래그.
 */
export const PAYMENT_ENABLED =
  process.env.NEXT_PUBLIC_PAYMENT_ENABLED === "true";

/** /onboarding 완료 후 보낼 다음 경로. */
export const POST_ONBOARDING_PATH = PAYMENT_ENABLED ? "/pay" : "/preorder";

/**
 * 메인 CTA 라우팅 — Hero·Offer·Nav 등 모든 "신청" 버튼이 참조.
 * 사전예약 기간엔 /preorder, 정식 오픈 후엔 /pay로 자동 전환.
 * 비로그인 사용자가 눌러도 /preorder가 알아서 /signin → /signup 흐름으로 보냄.
 */
export const PRIMARY_CTA_HREF = PAYMENT_ENABLED ? "/pay" : "/signup";
export const PRIMARY_CTA_LABEL = PAYMENT_ENABLED ? "교육 신청" : "사전예약 신청";
```

---

## `lib/supabase/server.ts`

Source: `apps/web/lib/supabase/server.ts`.
No brand placeholders. Env: `NEXT_PUBLIC_SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`.

PRESERVE: the **stub pattern**. `getSupabaseAdmin()` returns `null` when env is
missing so the app runs in "Phase 1 stub mode" (forms log-only, pages skip DB
reads). `requireSupabaseAdmin()` is the strict variant that throws. `server-only`
import guarantees the service-role key never reaches the browser bundle.

```ts
import "server-only";
import { createClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

/**
 * Returns a Supabase client with the service role key.
 * Server-only — never expose to the browser.
 * Returns null when env is missing (Phase 1 stub mode compatibility).
 */
export function getSupabaseAdmin() {
  if (!url || !serviceKey) return null;
  return createClient(url, serviceKey, {
    auth: { autoRefreshToken: false, persistSession: false },
  });
}

export function requireSupabaseAdmin() {
  const client = getSupabaseAdmin();
  if (!client) {
    throw new Error(
      "Supabase env not configured. Set NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
    );
  }
  return client;
}
```

---

## `components/ui/RevealOnScroll.tsx`

Source: `apps/web/components/ui/RevealOnScroll.tsx`.
No brand placeholders.

PRESERVE: `threshold: 0.12`, the `.reveal` → `.in` class swap, the no-IO fallback
(adds `.in` to all elements when `IntersectionObserver` is unavailable), and
`io.unobserve` after first reveal. Pair with CSS that animates `.reveal.in`.

```tsx
"use client";

import { useEffect } from "react";

export function RevealOnScroll() {
  useEffect(() => {
    const els = document.querySelectorAll(".reveal");
    if (!("IntersectionObserver" in window)) {
      els.forEach((e) => e.classList.add("in"));
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((en) => {
          if (en.isIntersecting) {
            en.target.classList.add("in");
            io.unobserve(en.target);
          }
        });
      },
      { threshold: 0.12 }
    );
    els.forEach((e) => io.observe(e));
    return () => io.disconnect();
  }, []);

  return null;
}
```
