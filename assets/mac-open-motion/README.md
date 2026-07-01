# mac-open-motion — 핀 고정 스크럽 + 맥북 데모 섹션

랜딩페이지용 **"하나의 화면에 고정(pin)된 채 스크롤로 챕터가 넘어가는"** 섹션.
출처: `granter-landing` (조코딩AX 셀러OS 랜딩, W1~W4 커리큘럼 섹션).

스크린샷처럼 가운데 **맥북(순수 CSS, 이미지 아님)** 안에 라이브 데모 iframe이 들어가고,
위에는 챕터 헤드라인, 아래에는 인용구·불릿·배너가 배치된다. 휠/키 한 번에 정확히
한 챕터씩 스냅되며, 모바일·JS 비활성·reduced-motion에서는 세로 스택 정적 레이아웃으로 자동 폴백.

---

## 🤖 적용 지침 (이 폴더를 받은 Claude에게)

> "이 폴더의 레이어를 적용해줘"라는 요청을 받으면 아래대로 한다. **외부 라이브러리 없음 — React 훅과 CSS만으로 동작한다.**

1. **CSS 이식**: `mac-open-motion.css`를 대상 프로젝트 전역 CSS에 붙여넣거나 import.
   - 대상에 이미 `--ink / --paper / --signal / --rule / --mute / --radius / --ease / --font-display` 토큰이
     **모두** 있으면, 파일 상단 `[DESIGN TOKENS]`·`[레이아웃 헬퍼]` 블록은 제거(중복 방지). 하나라도 없으면 둔다.
2. **컴포넌트 이식**: `Curriculum.tsx`를 `components/`로 복사. **Next.js/React 전용**(`"use client"` + `useEffect/useRef/useState`).
   - 비-React 스택이면 그대로는 못 쓴다 → 스크럽 엔진(스크롤→인덱스→opacity 페인트 + 휠 스냅) 로직을
     대상 프레임워크로 포팅해야 함. 정적 폴백 레이아웃(`.curri-track:not(.curri-scrub)`)만 필요하면 마크업+CSS로 가능.
3. **데모 iframe**: `examples/*.html` 4개를 대상의 `public/examples/`에 복사. 컴포넌트가 `/examples/xxx.html`를
   참조하므로 경로 수정 불필요. 내용은 granter 더미데이터이므로 새 프로젝트용으로 교체 권장.
   - iframe 없이 텍스트 카드로 쓰려면 `WEEKS[].detail.artifact`에서 `iframe`를 빼고 `rows`만 채우면 됨(자동 폴백).
4. **데이터 교체(핵심)**: `Curriculum.tsx` 상단 `WEEKS: Week[]` 배열만 갈아끼운다. 스키마는 아래 "데이터 교체" 절 참고.
   `detail` 있는 항목 수 = 스크럽 챕터 수(자동, `--n`).
5. **⚠️ 헤더 오프셋 조정(필수 통합 포인트)**: `mac-open-motion.css`의
   `.curri-scrub .curri-scene { top: 62px }` 와 `min-height: calc(100svh - 62px)` 의 `62px`를
   **대상 사이트의 고정 헤더 높이**로 바꾼다. 고정 헤더가 없으면 `0`.
6. 페이지에 `<Curriculum />` 배치.

**동작 보증**: 스크럽 애니메이션·휠 스냅은 컴포넌트 `useEffect` 안에서 자체 처리(외부 옵저버 불필요).
제목 등장도 CSS-only(`@keyframes cmFadeUp`). 모바일/reduced-motion에서는 자동으로 세로 스택 정적 레이아웃. **숨은 의존성 없음.**

---

## 파일 구성

| 파일 | 역할 |
|---|---|
| `Curriculum.tsx` | 컴포넌트 + 스크럽 애니메이션 엔진(JS). `WEEKS` 데이터 배열 포함 |
| `mac-open-motion.css` | 전체 스타일 (디자인 토큰·레이아웃 헬퍼·맥북·애니메이션 키프레임 포함, 자기완결적) |
| `examples/*.html` | 맥북 안에 뜨는 라이브 데모 iframe 4개 (skill-demo / os-data-layer / os-seller / os-mygranter) |

---

## 동작 원리 (핵심만)

### 1. 핀 고정 + 겹쳐 쌓기
- `.curri-scrub` 트랙 높이 = `N * 100svh` (챕터 수만큼 긴 스크롤).
- `.curri-scene`이 `position: sticky`로 화면에 고정.
- 헤드/맥북/바디 3개 스택 각각이 **N개 챕터 패널을 같은 grid-area(`1/1`)에 겹쳐** 둔다.

### 2. 스크롤 → 페이드 (Curriculum.tsx)
- 스크롤 진행도 `P(0~1)` → 가상 인덱스 `t = P*(n-1)`.
- `requestAnimationFrame`으로 매 프레임 `paintVisual`(맥북) / `paintText`(카피) 호출.
- `opacityFor`: `PLT=0.34`(완전 표시) + `FADE=0.3`(크로스페이드). 합 > 0.5라 인접 챕터가
  겹쳐서 **빈 화면 없이** 전환.
- `paintText`가 `--ip`(0→1)를 올리면, CSS의 `--s` 오프셋으로 head→quote→bullet 01~04→banner
  순서로 하나씩 등장.

### 3. 스냅 스테핑
- `lockRef` + `IDLE_MS=180ms`: 한 번의 휠 제스처(트랙패드 fling 포함) = 정확히 한 챕터.
  첫 이벤트만 받고 모멘텀은 삼킨 뒤, 스트림이 멈추면 재무장.
- 양 끝(첫/마지막 챕터)에서는 네이티브 스크롤로 빠져나감.

### 4. 맥북 (순수 CSS, `mac-open-motion.css`의 `.laptop-*`)
- `.laptop-screen` 검은 베젤 + `.laptop-notch` 카메라 노치 + `.laptop-base` 은색 하판/힌지.
- **iframe 트릭**: `width/height: 133.333%` + `transform: scale(0.75)` → 더 넓은 화면을
  한 프레임에 축소해 담음.

---

## 새 랜딩페이지에 붙이는 법

### A. Next.js / React 프로젝트
1. `Curriculum.tsx`를 `components/` 아래로 복사.
2. `mac-open-motion.css`를 전역 CSS에 import (또는 내용 붙여넣기).
   - 프로젝트에 이미 `--ink/--paper/--signal/--rule/--mute` 같은 토큰이 있으면 CSS 상단
     `[DESIGN TOKENS]`·`[레이아웃 헬퍼]` 블록은 지워도 됨.
3. `examples/*.html`을 `public/examples/`에 복사.
   `Curriculum.tsx`의 `iframe` 필드 경로(`/examples/xxx.html`)가 이걸 가리킨다.
4. 페이지에서 `<Curriculum />` 렌더.
5. **헤더 높이 조정**: `mac-open-motion.css`의 `.curri-scrub .curri-scene { top: 62px }`와
   `min-height: calc(100svh - 62px)`의 `62px`를 실제 고정 헤더 높이로 바꾼다.

### B. 데이터 교체 (가장 자주 하는 작업)
`Curriculum.tsx` 상단 `WEEKS: Week[]` 배열만 갈아끼우면 된다. 각 항목 구조:

```ts
{
  badge: "W1",            // 배지(인덱스용 식별자 겸용 — 고유해야 함)
  topic: "스킬 만들기",
  summary: "...\n...",    // 상단 카드용. \n = 줄바꿈
  time: "90 MIN",
  variant?: "free" | "climax",   // 카드 스타일 변형(선택)
  detail?: {              // detail 있는 항목만 스크럽 씬에 등장 (FREE처럼 detail 없으면 카드만)
    head: "헤드라인",
    quote: "인용구",
    bullets: [{ n: "01", text: "..." }, ...],
    artifact: {
      label: "캡션",
      iframe: "/examples/skill-demo.html",  // ← 맥북 안 데모. 생략 시 rows 텍스트카드로 폴백
      rows: [{ k: "...", v: "...", sig: true, sub: false }],  // iframe 없을 때만 렌더
    },
    banner: "하단 배너 문구",
    bannerVariant?: "climax",
  },
}
```

- 챕터 수(`detail` 있는 항목 수)가 곧 스크럽 길이. 자동 계산됨(`--n`).
- `iframe`을 주면 맥북 데모, 안 주면 `rows`로 텍스트 아티팩트 카드가 뜬다.

---

## 의존성 / 주의

- **외부 라이브러리 없음.** 순수 React + CSS + 스크롤 이벤트. GSAP 등 불필요.
- 폰트는 Pretendard 가정(토큰에서 교체 가능).
- `examples/*.html`은 granter 셀러OS 더미 데이터가 들어있는 **샘플**이다. 새 프로젝트에선
  내용만 새로 만들고 같은 경로/구조로 두면 된다. (`os-seller.html`은 50KB로 가장 무거움)
- iframe 데모는 정적 HTML이라 빌드 파이프라인과 독립적 — 디자이너가 따로 만들어 끼우기 좋다.

---

_저장일: 2026-06-09 · 원본 커밋 기준 granter-landing main_
