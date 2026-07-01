# GA4 / GTM 이벤트 매핑 레퍼런스 (전환 퍼널)

> GA4 Measurement ID는 **코드에 하드코딩하지 않고 GTM 컨테이너 안에서 태그로** 구성.
> 코드는 `dataLayer`에 GA4 표준 이벤트만 push. GTM에서 GA4 이벤트 태그 + 트리거로 매핑.

## 설치 (2곳)
- `components/ui/GTMScript.tsx` — `<Script id="gtm-init" strategy="afterInteractive">` 로 gtm.js 로드.
- `app/layout.tsx` — `<GTMScript />` + `<GTMNoScript />`(ns.html iframe) 삽입.
- ID: `process.env.NEXT_PUBLIC_GTM_ID`.

## 헬퍼 (`lib/gtm.ts`)
```ts
// 상품 상수
const ITEM = { item_id: "course-2026", item_name: "...", item_category: "교육" };
function pushDataLayer(e) {
  if (typeof window === "undefined") return;
  window.dataLayer = window.dataLayer || [];
  window.dataLayer.push({ ecommerce: null });   // GA4 권장: 직전 ecommerce 클리어
  window.dataLayer.push(e);
}
export const trackViewItem = () => pushDataLayer({ event:"view_item", ecommerce:{ currency:"KRW", value, items:[ITEM] }});
export const trackBeginCheckout = (button_location) => pushDataLayer({ event:"begin_checkout", button_location, ecommerce:{...} });
export const trackLogin = (method) => pushDataLayer({ event:"login", method });
export const trackGenerateLead = () => pushDataLayer({ event:"generate_lead", currency:"KRW", value });
export const trackPurchase = ({transaction_id,value,tier}) => pushDataLayer({ event:"purchase", ecommerce:{ transaction_id, value, currency:"KRW", tax:0, shipping:0, items:[{...ITEM, item_variant:tier}] }});
```

## 이벤트 5종 (퍼널)

| 이벤트 | 발화 위치(파일) | 발화 조건 | 중복방지 |
|---|---|---|---|
| `view_item` | `ViewItemTracker.tsx` (홈 page.tsx) | 랜딩 진입 1회 | sessionStorage `gtm_view_item_fired` |
| `begin_checkout` | `CheckoutCTA.tsx` (모든 CTA 래핑) | CTA 클릭 (위치 파라미터 동반) | 없음(클릭마다) |
| `login` | `GTMTracker.tsx` (apply/preorder/pay) | OAuth 로그인 후 페이지 로드 | sessionStorage `gtm_login_fired` |
| `generate_lead` | `GenerateLeadTracker.tsx` (preorder/done) | 사전예약/신청 완료 | sessionStorage `gtm_generate_lead_fired` |
| `purchase` | `PurchaseTracker.tsx` (pay/success) | 결제 승인 완료 | sessionStorage `gtm_purchase_fired_{txid}` |

### begin_checkout `button_location` 값 (CTA 위치별 세분화)
`nav` · `hero` · `offer-live` · `offer-closed` · `whynow` · `howtojoin` · `final-cta` · `sticky` · `floating`
→ 어떤 CTA가 전환에 기여하는지 GA4에서 분해 분석 가능.

## 패턴 핵심
- **Tracker 컴포넌트 = 클라이언트 컴포넌트**가 페이지에 얹혀 `useEffect`로 1회 발화 + sessionStorage 가드.
- **CheckoutCTA = CTA 버튼 래퍼**, `onClick`에서 `trackBeginCheckout(location)`.
- purchase는 `transaction_id` 단위 가드(새로고침 중복 집계 방지).

## GTM 컨테이너 쪽 설정(웹 UI에서)
1. GA4 Configuration 태그(Measurement ID) — All Pages.
2. GA4 Event 태그 5개 — 각 dataLayer 이벤트명을 Custom Event 트리거로.
3. ecommerce 파라미터는 GA4 Event 태그에서 "Send Ecommerce data → Data Layer".
4. 전환 표시(별표): `begin_checkout`, `generate_lead`, `purchase`.
