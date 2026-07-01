# GTM / GA4 설정 절차

> env 키: `NEXT_PUBLIC_GTM_ID`(`GTM-XXXXXXX`). 미설정 시 스크립트 미렌더.
> GA4 Measurement ID는 **코드에 넣지 않고 GTM 컨테이너 내부 태그로** 구성.
> 코드는 `dataLayer`에 GA4 표준 이벤트만 push(헬퍼 `lib/gtm.ts`).
> 이벤트 5종 상세는 `reference/gtm-events.md` 참조.
> 콘솔 UI 라벨은 자주 바뀌므로 "~ 찾기"로 기술.

## 1. GTM 컨테이너 생성
1. https://tagmanager.google.com → 계정/컨테이너 생성. 플랫폼 = **Web**.
2. 발급된 컨테이너 ID(`GTM-XXXXXXX`) → `NEXT_PUBLIC_GTM_ID`.
3. 코드 설치는 이미 되어 있음(`components/ui/GTMScript.tsx` + `app/layout.tsx`의
   `<GTMScript />`/`<GTMNoScript />`). ID env만 채우면 렌더된다.

## 2. GA4 속성 / 측정 ID
1. https://analytics.google.com → GA4 **속성(Property)** 생성 → **웹 데이터 스트림** 추가.
2. 데이터 스트림에서 **측정 ID**(`G-XXXXXXXXXX`) 복사. (코드에 넣지 않고 GTM 태그에 넣는다.)

## 3. GTM 안에서 태그 구성 (웹 UI)
### 3-1. GA4 Configuration(구성) 태그
- 새 태그 → 유형 **GA4 구성/Google 태그** 찾기 → 측정 ID 입력.
- 트리거 = **All Pages**(Initialization/All Pages).

### 3-2. GA4 Event 태그 5종
코드가 push하는 dataLayer 이벤트명마다 1개씩, 각각 **Custom Event 트리거**로 연결:

| dataLayer event | GA4 Event 태그명(예) | Custom Event 트리거 조건 |
|---|---|---|
| `view_item` | GA4 - view_item | Event = `view_item` |
| `begin_checkout` | GA4 - begin_checkout | Event = `begin_checkout` |
| `login` | GA4 - login | Event = `login` |
| `generate_lead` | GA4 - generate_lead | Event = `generate_lead` |
| `purchase` | GA4 - purchase | Event = `purchase` |

- 각 Event 태그는 위 3-1의 구성 태그(또는 측정 ID)를 참조.
- **ecommerce 파라미터**(`view_item`/`begin_checkout`/`purchase`): Event 태그에서
  "More Settings → Ecommerce → Send Ecommerce data → **Data Layer**" 찾아 켠다.
- `begin_checkout`의 `button_location`(nav/hero/final-cta 등)을 분석하려면 dataLayer
  변수로 받아 파라미터로 보낸다.

### 3-3. Custom Event 트리거
- 트리거 유형 **맞춤 이벤트(Custom Event)** 찾기 → 이벤트 이름에 위 dataLayer 이름 정확히 입력.

## 4. 전환 표시(별표)
GA4 → 관리 → **이벤트** 또는 **전환수(Key events)** 에서 다음을 **전환/주요 이벤트로 표시(별표 ON)**:
- `begin_checkout`
- `generate_lead`
- `purchase`
> 데이터가 한 번씩 들어온 뒤 목록에 나타난다. 안 보이면 미리보기로 이벤트를 먼저 발생시킨다.

## 5. 미리보기 → 게시
1. GTM **미리보기(Preview, Tag Assistant)** 로 실제 페이지에서 각 이벤트가 발화·태그 적중하는지 확인:
   - 랜딩 진입 → `view_item`
   - CTA 클릭 → `begin_checkout`
   - 로그인 후 → `login`
   - 사전예약/신청 완료 → `generate_lead`
   - 결제 성공 → `purchase`
2. 이상 없으면 GTM **제출(Submit) → 게시(Publish)**. 게시해야 운영에 반영된다.

## 흔한 함정 요약
- GTM에서 **게시(Publish)를 안 함** → 미리보기는 되는데 실사용자 데이터가 안 들어옴.
- 코드가 push하는 이름과 Custom Event 트리거 이름 **철자 불일치** → 태그 미적중.
- ecommerce를 Data Layer에서 보내도록 안 켬 → value/items가 GA4에 비어 들어감.
- 측정 ID를 코드에 하드코딩 → 이 스택 설계 위반(컨테이너 태그로만 관리).
- `NEXT_PUBLIC_GTM_ID` 미설정 → GTM 스크립트 자체가 미렌더(아무 이벤트도 안 감).
