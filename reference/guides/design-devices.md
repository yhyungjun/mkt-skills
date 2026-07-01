# 디자인 장치 & 모션/인터랙션 (설득 목적까지)

> 강의 랜딩의 디자인 요소는 "예쁘게"가 아니라 **각자 설득 역할**을 한다. 시각 장치 → 모션 → 인터랙션
> 순으로, 각각의 **목적 + 구현 포인트 + 코드 위치 + 접근성**을 정리. 일반 프레임워크 + granter 예시.
> 색·폰트 토큰은 `design-system-skeleton.css` / `design-phase-prompt.md`, 구조는 `playbook.md` Phase 2/5.

---

## A. 정적 시각 장치 (Static devices)

### A1. 다크/라이트 섹션 리듬
- **목적**: 배경 톤 교차로 "강조 리듬"을 만든다 — 다크=감정·권위, 라이트=정보·명료. 톤 전환 = 분위기 전환 신호.
- **구현**: `.section-dark`(ink 배경/paper 텍스트) ↔ 일반/크림(`.offer-pre`). 연속 다크는 border-top 제거로 한 덩어리처럼.
- **주의**: 다크를 남발하면 강조가 사라짐 — 핵심(약속·통증·권위·클로징)에만.

### A2. 강조색 희소성 (Signal scarcity)
- **목적**: 강조색(`--signal`)을 **CTA·포인트에만** → 시선이 "행동"으로 빨려감. 본문 대량 텍스트에 쓰면 강조가 죽음.
- **구현**: 버튼 primary, `.sig` 인라인 강조, 메타 pip, 아티팩트 라벨에만.

### A3. 글로우 오라 (Glow aura)
- **목적**: 인물/문제를 "스포트라이트"로 띄워 프리미엄·집중. (인물 신뢰, 문제 강조)
- **구현**: 다크 배경 `::before`에 방사형 그라데이션 3겹 + `blur(72px)` + 상하 `mask` 페이드. → `assets/instructor-spotlight`.

### A4. 아티팩트 카드 (Artifact card)
- **목적**: 추상적 주장 대신 **구체적 데이터 한 조각**(수치·결과)을 보여 신뢰. "말"보다 "증거".
- **구현**: `.artifact`(테두리+라벨 ::before), 다크 변형 `.artifact-dark`. 데모/결과 스니펫에.

### A5. 라이브 데모 = 맥북 프레임
- **목적**: "이게 진짜 작동한다"를 실물로 — 해결(Solution)·과정(Curriculum)의 가장 강한 증거.
- **구현**: 순수 CSS 맥북(베젤·노치·은색 하판) 안에 정적 HTML iframe. `assets/mac-open-motion`.

---

## B. 모션 (Motion) — 스크롤·등장

### B1. Reveal on scroll (가장 기본)
- **목적**: 한 화면씩 "드러나며" 읽게 → 몰입 유지·살아있는 느낌. 한꺼번에 다 보이면 지나침.
- **구현**: `RevealOnScroll.tsx`(IntersectionObserver, `threshold 0.12` → `.in` 토글). `.reveal { opacity:0; translateY(12px) }` → `.in { opacity:1 }`, `.6s cubic-bezier(0.16,1,0.3,1)`.
- **스태거**: `.reveal-stagger` 자식 카드가 80ms 간격 순차 등장(`staggerIn`) — 카드 그룹(혜택·페르소나)에.

### B2. 핀 고정 스크럽 데모 (Pin-scrub)
- **목적**: 커리큘럼/제품을 **스크롤로 탐색**시켜 체류·이해↑. 수동적 보기 → 능동적 탐색.
- **구현**: sticky 씬 + 스크롤 진행도→인덱스→opacity 페인트, 휠 한 번=한 챕터 스냅. `assets/mac-open-motion`(🤖 적용지침). React 전용.

### B3. 무한 마퀴 (Marquee)
- **목적**: 로고/증거가 "계속 흐르며" 풍성해 보임 → 사회적 증거 증폭. 정적 나열보다 양감↑.
- **구현**: `.marquee-track` 무한 스크롤 애니메이션, **hover 시 일시정지**(`animation-play-state: paused`), 모바일은 wrap+정지. 로고는 평소 `grayscale(1)` → hover 컬러.

### B4. 라이브 카운트다운·잔여석
- **목적**: **실시간 긴급성/희소성** — "지금 안 하면 놓친다". 전환의 마지막 밀기.
- **구현**: `CountdownTimer`(마감 D-day), `/api/counter`(결제수→잔여석), `viewerBands`(관람수 시뮬). FloatingBar에 결합.
- ⚠️ **진짜 수치만**. 가짜 카운트는 신뢰·표시광고법 리스크(`pg-review-guide.md`).

---

## C. 인터랙션 (Interaction) — 호버·상시

### C1. 버튼 마이크로 인터랙션
- **목적**: 클릭 가능을 몸으로 알림 → 행동 유도. 망설임↓.
- **구현**: primary hover `translateY(-2px)` + signal 그림자, `:active`/`:disabled` 상태, `min-height:44px` 터치타깃.

### C2. 호버로 의미 드러내기 (Reveal-on-hover)
- **목적**: 기본은 깔끔, 관심(호버) 시에만 디테일 → 정보 과부하 방지.
- **예시**: 로고 grayscale→컬러, **퍼널 막대→단계 연결 슬로프 페이드인**(`opacity 0→1 .35s`, `useState(hover)`), 마퀴 일시정지.
- ⚠️ granter 어드민 퍼널 = **기본 막대 + 호버 시 연결**이 확정 디자인(상시 연결형 금지).

### C3. 상시 전환 장치 (Persistent CTA)
- **목적**: 마음이 넘어온 *어느 순간이든* 결제로. 스크롤 끝까지 안 가도 잡는다.
- **구현**: `FloatingBar`(혜택 섹션 통과 후 등장, blur 배경, `aria-live`로 상태 갱신), `StickyCTA`(모바일 하단 고정). 모든 CTA는 `CheckoutCTA` 래퍼(위치별 `begin_checkout` 추적, `gtm-events.md`).

### C4. 스크롤 기반 헤더
- **목적**: 스크롤 시 헤더에 그림자/배경 → 컨텍스트 유지, CTA 항상 접근.
- **구현**: `NavScrollEffect`(스크롤 감지), sticky nav `z-index:100`.

---

## D. 접근성 = 디자인의 일부 (필수)
- **`prefers-reduced-motion`**: reveal·스태거·스크럽·마퀴 **전부 비활성**(즉시 표시). `design-system-skeleton.css`에 가드 포함.
- **터치타깃 44px** 이상(nav·버튼·푸터 링크), **최소 글자 12px** (실제 design-review에서 교정된 기준).
- **모션은 거들 뿐**: 모션 없이도 정보·전환 동선이 완결돼야 함(JS/모션 실패해도 작동).
- `prefers-reduced-motion`에서 핀 스크럽은 세로 스택 정적 폴백(`assets/mac-open-motion` 내장).

---

## E. 모션 강도 가이드 (과하지 않게)
| 강도 | 쓸 곳 | 예 |
|---|---|---|
| 약(필수) | 거의 모든 섹션 | reveal 페이드업 |
| 중 | 핵심 증거 | 스태거 카드, 마퀴, 호버 디테일 |
| 강(절제) | 1~2곳 한정 | 핀 스크럽 데모, 글로우 |
- 원칙: **강한 모션은 페이지당 1~2개**. 다 움직이면 아무것도 안 움직이는 것과 같다.
- 60fps 유지: `transform`/`opacity`만 애니메이트(레이아웃 속성 금지), `will-change` 절제.

---

## 적용 체크
- [ ] 다크/라이트가 "강조 리듬"으로 의도됐는가(남발 아님)?
- [ ] 강조색이 CTA·포인트에만?
- [ ] 강한 모션 1~2개로 절제?
- [ ] 모든 모션이 `prefers-reduced-motion`에서 꺼지는가?
- [ ] 터치타깃 44px·최소 12px?
- [ ] 카운트다운·잔여석이 **진짜 수치**인가?
- 섹션이 전하는 "의미"는 `section-narrative.md`, 카피는 `copywriting-guide.md`와 함께.
