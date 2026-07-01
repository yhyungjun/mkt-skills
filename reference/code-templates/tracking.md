# Tracking Code Templates (GA4 / GTM)

Brand-neutral, copy-paste implementation of the 5-event GA4 e-commerce funnel via
Google Tag Manager in a Next.js (App Router) landing page.

- **Source:** extracted verbatim from `granter-landing/apps/web` (snapshot 2026-06-11),
  then de-branded.
- **Scope of this file:** application code only. GTM container console setup
  (triggers, tags, GA4 config) lives in `reference/gtm-events.md` — do not duplicate it here.
- **Placeholders to replace** (search & swap when adopting):
  - `course-2026` → your real `ITEM_ID`
  - `<상품명>` → your real product display name
  - `<카테고리>` → your real `item_category`
  - `PRICING.*` → wire to your own pricing source/config
  - `NEXT_PUBLIC_GTM_ID` → set in env (keep the var name)
- **Preserved core behavior (do not drop when porting):**
  - 5 events: `view_item` · `begin_checkout` · `login` · `generate_lead` · `purchase`
  - `pushDataLayer({ ecommerce: null })` clear **before** every ecommerce push
  - `sessionStorage` dedupe guards on view_item / generate_lead / login / purchase
  - `begin_checkout` carries a `button_location` (9-value union)
  - `purchase` dedupe is keyed per `transaction_id` (`gtm_purchase_fired_<txid>`)

---

## ① `lib/gtm.ts` — dataLayer push + 5 event helpers

```ts
// lib/gtm.ts
// ---------------------------------------------------------------------------
// Source: granter-landing/apps/web/lib/gtm.ts (snapshot 2026-06-11), de-branded.
// GA4 e-commerce funnel via GTM dataLayer.
// REPLACE: ITEM_ID / ITEM_NAME / ITEM_CATEGORY constants, and the PRICING source.
// GTM ID stays in env as NEXT_PUBLIC_GTM_ID.
// ---------------------------------------------------------------------------
import { PRICING } from "@/lib/config"; // REPLACE: your pricing source

type DataLayerEvent = Record<string, unknown>;

declare global {
  interface Window {
    dataLayer?: DataLayerEvent[];
  }
}

export const GTM_ID = process.env.NEXT_PUBLIC_GTM_ID;

const CURRENCY = "KRW";
const ITEM_ID = "course-2026"; // REPLACE: real product id
const ITEM_NAME = "<상품명>"; // REPLACE: real product name
const ITEM_CATEGORY = "<카테고리>"; // REPLACE: real category

export type ItemVariant = "earlybird-tier1" | "earlybird-tier2" | "regular";

interface BaseItem {
  item_id: string;
  item_name: string;
  item_category: string;
  item_variant?: string;
  price: number;
  quantity: number;
}

function buildItem(price: number, variant?: string): BaseItem {
  return {
    item_id: ITEM_ID,
    item_name: ITEM_NAME,
    item_category: ITEM_CATEGORY,
    item_variant: variant,
    price,
    quantity: 1,
  };
}

export function pushDataLayer(event: DataLayerEvent): void {
  if (typeof window === "undefined") return;
  window.dataLayer = window.dataLayer ?? [];
  window.dataLayer.push(event);
}

export function trackViewItem(): void {
  const price = PRICING.offline.earlybird; // REPLACE: your price source
  pushDataLayer({ ecommerce: null }); // clear before ecommerce push
  pushDataLayer({
    event: "view_item",
    ecommerce: {
      currency: CURRENCY,
      value: price,
      items: [buildItem(price, "earlybird")],
    },
  });
}

// 9-value union — every CTA passes one of these as button_location.
export type CheckoutLocation =
  | "nav"
  | "hero"
  | "offer-live"
  | "offer-closed"
  | "whynow"
  | "howtojoin"
  | "final-cta"
  | "sticky"
  | "floating";

export function trackBeginCheckout(location: CheckoutLocation): void {
  const price = PRICING.offline.earlybird; // REPLACE
  pushDataLayer({ ecommerce: null }); // clear before ecommerce push
  pushDataLayer({
    event: "begin_checkout",
    button_location: location,
    ecommerce: {
      currency: CURRENCY,
      value: price,
      items: [buildItem(price, "earlybird")],
    },
  });
}

export function trackLogin(method: string): void {
  pushDataLayer({ event: "login", method });
}

/** 섹션 도달 퍼널 — 섹션이 처음 뷰포트에 들어올 때 세션당 1회. event = GA4 이벤트명(sec_NN_*). */
export function trackSectionView(event: string): void {
  pushDataLayer({ event });
}

export function trackGenerateLead(): void {
  // GA4 standard event — application/lead form submit (pre-payment step)
  pushDataLayer({
    event: "generate_lead",
    currency: CURRENCY,
    value: PRICING.offline.earlybird, // REPLACE
  });
}

export function trackPurchase(params: {
  transactionId: string;
  value: number;
  tier?: string;
}): void {
  pushDataLayer({ ecommerce: null }); // clear before ecommerce push
  pushDataLayer({
    event: "purchase",
    ecommerce: {
      transaction_id: params.transactionId,
      value: params.value,
      currency: CURRENCY,
      tax: 0,
      shipping: 0,
      items: [buildItem(params.value, params.tier)],
    },
  });
}
```

---

## ② `GTMScript.tsx` + layout insertion

`GTMScript` loads the GTM container (head); `GTMNoScript` is the `<noscript>`
fallback iframe (top of body). Both render `null` when `GTM_ID` is unset, so the
app stays clean in environments without the env var.

```tsx
// components/ui/GTMScript.tsx
// Source: granter-landing/apps/web/components/ui/GTMScript.tsx (snapshot 2026-06-11).
// Standard GTM bootstrap snippet. No brand-specific values — only NEXT_PUBLIC_GTM_ID.
import Script from "next/script";
import { GTM_ID } from "@/lib/gtm";

export function GTMScript() {
  if (!GTM_ID) return null;
  return (
    <Script id="gtm-init" strategy="afterInteractive">
      {`(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
})(window,document,'script','dataLayer','${GTM_ID}');`}
    </Script>
  );
}

export function GTMNoScript() {
  if (!GTM_ID) return null;
  return (
    <noscript>
      <iframe
        src={`https://www.googletagmanager.com/ns.html?id=${GTM_ID}`}
        height="0"
        width="0"
        style={{ display: "none", visibility: "hidden" }}
      />
    </noscript>
  );
}
```

```tsx
// app/layout.tsx — insertion points (excerpt)
// GTMScript in <head>, GTMNoScript as first child of <body>.
import { GTMScript, GTMNoScript } from "@/components/ui/GTMScript";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <head>
        {/* ...preconnect / fonts... */}
        <GTMScript />
      </head>
      <body>
        <GTMNoScript />
        {children}
      </body>
    </html>
  );
}
```

---

## ③ Tracker components (4)

All four are `"use client"` no-render (`return null`) effect components. Each
uses a `sessionStorage` guard so the event fires at most once per session, and
falls back to firing anyway if `sessionStorage` throws (private mode, etc.).

```tsx
// components/ui/ViewItemTracker.tsx
// Source: granter-landing/apps/web/components/ui/ViewItemTracker.tsx (snapshot 2026-06-11).
// Fires view_item once per session. Mount on the landing page.
"use client";

import { useEffect } from "react";
import { trackViewItem } from "@/lib/gtm";

const FIRED_KEY = "gtm_view_item_fired";

export function ViewItemTracker() {
  useEffect(() => {
    try {
      if (sessionStorage.getItem(FIRED_KEY) === "1") return;
      trackViewItem();
      sessionStorage.setItem(FIRED_KEY, "1");
    } catch {
      trackViewItem();
    }
  }, []);

  return null;
}
```

```tsx
// components/ui/GenerateLeadTracker.tsx
// Source: granter-landing/apps/web/components/ui/GenerateLeadTracker.tsx (snapshot 2026-06-11).
// Fires generate_lead once per session. Mount on the lead/application "done" page.
"use client";

import { useEffect } from "react";
import { trackGenerateLead } from "@/lib/gtm";

const FIRED_KEY = "gtm_generate_lead_fired";

export function GenerateLeadTracker() {
  useEffect(() => {
    try {
      if (sessionStorage.getItem(FIRED_KEY) === "1") return;
      trackGenerateLead();
      sessionStorage.setItem(FIRED_KEY, "1");
    } catch {
      trackGenerateLead();
    }
  }, []);

  return null;
}
```

```tsx
// components/ui/PurchaseTracker.tsx
// Source: granter-landing/apps/web/components/ui/PurchaseTracker.tsx (snapshot 2026-06-11).
// Fires purchase once per transaction_id (dedupe key includes the txid).
// Mount on the payment success page with real order data.
"use client";

import { useEffect } from "react";
import { trackPurchase } from "@/lib/gtm";

interface PurchaseTrackerProps {
  transactionId: string;
  value: number;
  tier?: string;
}

const FIRED_PREFIX = "gtm_purchase_fired_";

export function PurchaseTracker({ transactionId, value, tier }: PurchaseTrackerProps) {
  useEffect(() => {
    const key = FIRED_PREFIX + transactionId; // per-txid guard
    try {
      if (sessionStorage.getItem(key) === "1") return;
      trackPurchase({ transactionId, value, tier });
      sessionStorage.setItem(key, "1");
    } catch {
      trackPurchase({ transactionId, value, tier });
    }
  }, [transactionId, value, tier]);

  return null;
}
```

```tsx
// components/ui/GTMTracker.tsx
// Source: granter-landing/apps/web/components/ui/GTMTracker.tsx (snapshot 2026-06-11).
// Two jobs:
//  1) login: fire once per session from the authed user's provider.
//  2) generate_lead via ?signup=1 query flag, then strip the flag from the URL.
// Uses useSearchParams → mount inside a <Suspense> boundary.
"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { trackLogin, trackGenerateLead } from "@/lib/gtm";

interface GTMTrackerProps {
  provider?: string;
}

const LOGIN_FIRED_KEY = "gtm_login_fired";

export function GTMTracker({ provider }: GTMTrackerProps) {
  const router = useRouter();
  const params = useSearchParams();
  const pathname = usePathname();

  useEffect(() => {
    if (!provider) return;
    try {
      if (sessionStorage.getItem(LOGIN_FIRED_KEY) === "1") return;
      trackLogin(provider);
      sessionStorage.setItem(LOGIN_FIRED_KEY, "1");
    } catch {
      trackLogin(provider);
    }
  }, [provider]);

  useEffect(() => {
    if (params.get("signup") !== "1") return;
    trackGenerateLead();
    const url = new URL(window.location.href);
    url.searchParams.delete("signup");
    const next = url.pathname + (url.search || "");
    router.replace(next, { scroll: false });
  }, [params, router, pathname]);

  return null;
}
```

---

## ④ `CheckoutCTA.tsx` — begin_checkout wrapper

Wrap any link that starts checkout. The `location` prop is the `button_location`
dimension on the `begin_checkout` event.

```tsx
// components/ui/CheckoutCTA.tsx
// Source: granter-landing/apps/web/components/ui/CheckoutCTA.tsx (snapshot 2026-06-11).
// Anchor wrapper that fires begin_checkout(location) on click.
"use client";

import type { ReactNode } from "react";
import { trackBeginCheckout, type CheckoutLocation } from "@/lib/gtm";

interface CheckoutCTAProps {
  href: string;
  location: CheckoutLocation;
  className?: string;
  children: ReactNode;
}

export function CheckoutCTA({ href, location, className, children }: CheckoutCTAProps) {
  return (
    <a
      href={href}
      className={className}
      onClick={() => trackBeginCheckout(location)}
    >
      {children}
    </a>
  );
}
```

Usage:

```tsx
<CheckoutCTA href={PRIMARY_CTA_HREF} location="hero" className="btn btn-primary btn-lg">
  지금 신청하기
</CheckoutCTA>
```

---

## ⑤ Event wiring map (where each event is mounted)

| Event | Helper / Component | Mount location (in source) | Dedupe key |
|---|---|---|---|
| `view_item` | `<ViewItemTracker />` | landing page `app/page.tsx` | `gtm_view_item_fired` (1/session) |
| `begin_checkout` | `<CheckoutCTA location=... />` | every primary CTA (see table below) | none (fires each click) |
| `login` | `<GTMTracker provider=... />` | post-auth pages (`app/apply`, `app/preorder`) | `gtm_login_fired` (1/session) |
| `generate_lead` | `<GenerateLeadTracker />` **or** `<GTMTracker>` `?signup=1` | lead "done" page; or any page reached with `?signup=1` | `gtm_generate_lead_fired` (1/session) |
| `purchase` | `<PurchaseTracker .../>` | payment success page `app/pay/success` | `gtm_purchase_fired_<txid>` (1/txid) |
| (infra) | `GTMScript` / `GTMNoScript` | `app/layout.tsx` head + body | — |

### `begin_checkout` `button_location` — 9-value union

| Value | Where it's placed (source component) | Wired in snapshot? |
|---|---|---|
| `nav` | `components/ui/Nav.tsx` | yes |
| `hero` | `components/sections/Hero.tsx` | yes |
| `offer-live` | `components/sections/Pricing.tsx` (offer open) | yes |
| `offer-closed` | pricing/offer section when closed | reserved (slot defined, not wired) |
| `whynow` | `components/sections/WhyNow.tsx` | reserved (slot defined, not wired) |
| `howtojoin` | `components/sections/HowToJoin.tsx` | reserved (slot defined, not wired) |
| `final-cta` | `components/sections/FinalCTA.tsx` | yes |
| `sticky` | `components/ui/StickyCTA.tsx` | yes |
| `floating` | `components/ui/FloatingBar.tsx` | yes |

> The union defines all 9 slots so any CTA position has a stable label; in the
> snapshot 6 are actively wired and 3 (`offer-closed`, `whynow`, `howtojoin`) are
> reserved labels not yet attached to a live CTA.

### Notes on the `?signup=1` lead pattern

`app/apply/page.tsx` redirects to `/pay?signup=1` after a successful application
(`redirect("/pay?signup=1")`). `GTMTracker` on the destination reads the flag,
fires `generate_lead`, then strips `signup` from the URL via `router.replace`.
Use this when the lead-completion and the next page are the same navigation;
use `<GenerateLeadTracker />` when there is a dedicated done/thank-you page.

`GTMTracker` calls `useSearchParams()`, so it must be rendered inside a
`<Suspense>` boundary (Next.js App Router requirement).
