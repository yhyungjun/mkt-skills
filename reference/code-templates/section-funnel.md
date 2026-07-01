# 섹션 도달 퍼널 트래킹 (sec_NN — 스크롤 이탈 분석)

> **출처**: axacademy-landing (`lib/sections.ts` + `components/ui/SectionFunnelTracker.tsx`).
> **왜**: 기본 5이벤트(view_item·begin_checkout…)는 "어느 섹션에서 이탈했는가"를 못 본다.
> 섹션마다 처음 뷰포트 진입 시 `sec_NN_*` 이벤트를 쏘면 **섹션별 도달률·이탈 지점**을 GA4·어드민 퍼널로 본다.
> **핵심**: ① 순서 = `page.tsx` 렌더 순서와 **반드시 일치**(단일 출처 `lib/sections.ts`). ② DOM 추가 없이
> **기존 `<section id>`를 직접 관찰**(레이아웃/CSS 무영향). ③ `sessionStorage` 가드로 세션당 1회.
> ④ 어드민 트래픽 차트가 **같은 순서/이벤트명을 공유**.

---

## 1. 단일 출처 — `lib/sections.ts`

```ts
// 클라 트래커(SectionFunnelTracker)와 어드민(TrafficCharts)이 같은 순서/이벤트명을 공유.
// domId = 각 섹션 <section id>; event = GA4 이벤트명. 순서는 app/page.tsx 렌더 순서와 일치해야 한다.
export type LandingSection = { domId: string; event: string; label: string };

export const LANDING_SECTIONS: readonly LandingSection[] = [
  { domId: "hero",      event: "sec_01_hero",     label: "히어로" },
  { domId: "benefits",  event: "sec_02_benefits", label: "혜택" },
  // …page.tsx 순서대로…
  { domId: "pricing",   event: "sec_16_pricing",  label: "가격" },
  { domId: "faq",       event: "sec_19_faq",      label: "FAQ" },
  { domId: "footer",    event: "sec_20_footer",   label: "푸터" }, // <footer> 태그로 폴백
];
```

## 2. 관찰자 — `components/ui/SectionFunnelTracker.tsx`

```tsx
"use client";
import { useEffect } from "react";
import { LANDING_SECTIONS } from "@/lib/sections";
import { trackSectionView } from "@/lib/gtm";

const PREFIX = "gtm_sec_fired:";

export function SectionFunnelTracker() {
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return;
    const fired = new Set<string>();
    const observer = new IntersectionObserver((entries, obs) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        const event = (entry.target as HTMLElement).dataset.funnelEvent;
        if (!event || fired.has(event)) continue;
        fired.add(event);
        obs.unobserve(entry.target);
        try {
          if (sessionStorage.getItem(PREFIX + event) === "1") continue;
          trackSectionView(event);
          sessionStorage.setItem(PREFIX + event, "1");
        } catch { trackSectionView(event); }
      }
    }, { threshold: 0 });

    for (const s of LANDING_SECTIONS) {
      const el = document.getElementById(s.domId)
        ?? (s.domId === "footer" ? document.querySelector<HTMLElement>("footer") : null);
      if (!el) continue;
      el.dataset.funnelEvent = s.event;
      observer.observe(el);
    }
    return () => observer.disconnect();
  }, []);
  return null; // 렌더 없음
}
```

`LandingPage` 상단에 `<SectionFunnelTracker />` 한 줄. 각 섹션 컴포넌트는 `<section id="hero">`처럼 **`id`만 정확히** 맞추면 됨.

## 3. gtm 헬퍼 한 줄

```ts
// lib/gtm.ts
/** 섹션 도달 — 섹션이 처음 뷰포트에 들어올 때 세션당 1회. event = GA4 이벤트명(sec_NN_*). */
export function trackSectionView(event: string): void {
  pushDataLayer({ event });
}
```

## 4. GTM/GA4 설정
- GTM: `sec_01_*`~`sec_NN_*`를 **하나의 정규식 트리거**(`^sec_\d+_`)로 묶어 GA4 Event 태그 1개로 전달 → 태그 N개 안 만들어도 됨.
- GA4 탐색(깔때기) 보고서에서 `sec_01 → … → sec_16(pricing)` 단계별 도달률 = 이탈 지점.
- 어드민 트래픽 페이지는 `LANDING_SECTIONS` 순서를 그대로 읽어 자체 SVG 퍼널/막대로 시각화(같은 단일 출처).

## 함정
- **순서 드리프트**: `page.tsx`에 섹션을 추가/이동하면 `lib/sections.ts`도 같이 고쳐야 함(순서·id 일치가 깨지면 퍼널이 뒤섞임).
- `threshold:0`이라 섹션이 길어도 상단이 살짝 보이면 발화 — "도달"의 정의가 "진입"임에 유의(완독 아님).
- `id` 누락 섹션은 조용히 스킵(에러 없음) → 신규 섹션 추가 시 `id` 빠뜨림 주의.
