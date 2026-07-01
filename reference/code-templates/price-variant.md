# 가격 변형 — 단일 배포 · 경로 분기 (Price Variant Routing)

> **출처**: 강의 랜딩 사례 (공개 50만 `/` · 제휴 클럽 40만 `/<추측 어려운 슬러그>`).
> **언제**: 같은 랜딩을 가격만 다르게 여러 대상에 뿌릴 때(공개가 vs 제휴/클럽 할인가).
> **핵심 원칙**: ① 단일 배포 — 페이지는 1벌, 경로로 variant만 분기. ② **가격은 항상 서버가
> variant 키로 매핑**(클라이언트 금액 불신). ③ 비공개 변형은 `noindex` + 추측 어려운 슬러그.
> ④ **좌석/카운터는 공유 풀**(variant 무관 동일 `applications` 테이블·동일 cohort).

---

## 1. variant 모듈 (서버·클라 공용, config 의존 없음)

`lib/variant.ts` — 가벼운 단일 출처. config를 import하지 않아 어디서든 안전하게 쓴다.

```ts
// 가격 변형(variant) — 단일 배포에서 경로로 가격만 분기.
export type PriceVariant = "standard" | "primer";

export const DEFAULT_VARIANT: PriceVariant = "standard";

/** 비공개 변형 전용 경로 (추측 어려운 슬러그로 교체 + noindex). */
export const PRIMER_SLUG = "partner-vip"; // 예시 — 실제로는 추측 어려운 값으로

/** 외부 입력(쿼리·바디)을 안전하게 variant로 변환. 알 수 없으면 기본(공개가). */
export function resolveVariant(v?: string | null): PriceVariant {
  return v === "primer" ? "primer" : "standard";
}
```

## 2. config 가격 매핑 (서버 단일 출처)

`lib/config.ts` — `PRICE_BY_VARIANT`로 variant→금액. `satisfies Record<PriceVariant, number>`로 누락 방지.

```ts
import type { PriceVariant } from "./variant";

export const PRICING = {
  regular: 1_000_000,   // 정가
  earlybird: 500_000,   // 공개 판매가 = standard
  clubExtra: 100_000,   // 변형 추가 할인액 (standard − clubExtra = primer)
} as const;

/** 가격은 항상 서버가 variant 키로 매핑(클라이언트 금액 불신). */
export const PRICE_BY_VARIANT = {
  standard: PRICING.earlybird,                    // 500_000
  primer:   PRICING.earlybird - PRICING.clubExtra, // 400_000
} as const satisfies Record<PriceVariant, number>;

export const priceForVariant = (v: PriceVariant): number => PRICE_BY_VARIANT[v];
```

## 3. 경로 = 페이지 2벌, 본문은 1벌

`app/page.tsx`(공개) / `app/<PRIMER_SLUG>/page.tsx`(비공개)가 같은 `<LandingPage>`에 variant만 다르게 전달.

```tsx
// app/page.tsx — 공개(standard)
import { LandingPage } from "@/components/LandingPage";
export default function Home() {
  return <LandingPage variant="standard" />;
}
```

```tsx
// app/<PRIMER_SLUG>/page.tsx — 비공개(primer), 검색 노출 차단
import type { Metadata } from "next";
import { LandingPage } from "@/components/LandingPage";

export const metadata: Metadata = {
  robots: { index: false, follow: false }, // 전용 링크 — 색인 금지
};

export default function PrimerClubPage() {
  return <LandingPage variant="primer" />;
}
```

> ⚠️ `sitemap.ts`·`robots.ts`에 비공개 변형 경로를 **넣지 말 것**(전용 링크 유지).

## 4. variant 컨텍스트 주입 (하위 클라 컴포넌트가 읽음)

`components/VariantProvider.tsx` — 루트에서 주입 → `Cta`·`FloatingBar`·`StickyCTA`가 `useVariant()`로 읽음.

```tsx
"use client";
import { createContext, useContext } from "react";
import { DEFAULT_VARIANT, type PriceVariant } from "@/lib/variant";

const VariantContext = createContext<PriceVariant>(DEFAULT_VARIANT);

export function VariantProvider({ variant, children }: {
  variant: PriceVariant; children: React.ReactNode;
}) {
  return <VariantContext.Provider value={variant}>{children}</VariantContext.Provider>;
}

export const useVariant = (): PriceVariant => useContext(VariantContext);
```

`LandingPage`는 `<VariantProvider variant={variant}>`로 본문을 감싸고, 가격을 보여주는 섹션
(`Pricing`·`Benefits`)엔 `variant` prop을 직접 내려준다. JSON-LD `Course.offers.price`도 `priceForVariant(variant)`로.

## 5. CTA가 variant를 다음 페이지로 전달 (쿼리스트링)

`components/ui/Cta.tsx` — 비기본 변형이면 신청 링크에 `?v=primer` 부착. 클릭 추적에도 variant 전달.

```tsx
"use client";
import { PRIMARY_CTA_HREF, PRIMARY_CTA_LABEL } from "@/lib/config";
import { trackBeginCheckout } from "@/lib/gtm";
import { useVariant } from "@/components/VariantProvider";
import { DEFAULT_VARIANT } from "@/lib/variant";

export function Cta({ location, label }: { location: string; label?: string }) {
  const priceVariant = useVariant();
  const href = priceVariant === DEFAULT_VARIANT
    ? PRIMARY_CTA_HREF
    : `${PRIMARY_CTA_HREF}?v=${priceVariant}`; // 가격 분기 전달
  return (
    <a href={href} onClick={() => trackBeginCheckout(location, priceVariant)}>
      {label ?? PRIMARY_CTA_LABEL}
    </a>
  );
}
```

신청 페이지(`/apply`)는 `searchParams.v`를 읽어 hidden 필드로 폼에 싣고, 제출 바디에 `variant`로 포함시킨다.

## 6. 서버 재검증 (진실의 원천)

`/api/applications` POST에서 **클라가 보낸 금액이 아니라 variant 키만 신뢰**하고 서버에서 재해석·저장.

```ts
import { resolveVariant } from "@/lib/variant";

const variant = resolveVariant(typeof body.variant === "string" ? body.variant : null);
const row = { /* …필드… */ variant, cohort: SITE.cohort };
// 메일·Slack도 variant로 금액 재계산: priceForVariant(variant)
await sendApplicationEmail(email, name, variant); // 메일 본문 금액 = priceForVariant
```

DB: `applications`에 `variant text not null default 'standard'` 컬럼 추가(마이그레이션). 어드민에서 변형별 집계 가능.

## 7. 좌석·카운터는 공유 풀

남은 자리/카운터는 **variant와 무관**하게 같은 cohort·같은 테이블에서 센다 → 두 경로가 한 정원을 나눠 쓴다.
(variant별로 좌석을 나누고 싶으면 카운터 쿼리에 `.eq("variant", v)` 추가. 실제 빌드는 공유 풀.)

---

## 변형 추가 체크리스트
- [ ] `lib/variant.ts`에 새 키 + `resolveVariant` 분기 + (비공개면) `*_SLUG`.
- [ ] `PRICE_BY_VARIANT`에 금액 추가(`satisfies`가 누락 시 컴파일 에러로 잡아줌).
- [ ] `app/<slug>/page.tsx` 생성 + 비공개면 `robots: { index:false }`.
- [ ] 가격 노출 섹션(Pricing·Benefits)·JSON-LD에 variant 반영.
- [ ] CTA·신청폼·API·메일·Slack까지 variant 관통(클라 금액 불신).
- [ ] sitemap/robots에 비공개 경로 누락 확인. 좌석 풀(공유 vs 분리) 결정.
