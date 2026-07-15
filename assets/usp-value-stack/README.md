# usp-value-stack — USP / 가치 총정리 그리드 섹션

랜딩페이지용 **다크 배경 "가치 총정리" 섹션**. "{기간} 동안, **이만큼** 배우고 남깁니다 /
다른 {카테고리} 강의엔 없는 N가지" 헤드라인 아래, 강의가 주는 차별적 가치를 **번호 박스
그리드**로 한 화면에 모아 각인시킨다. 해결(Solution) 직후 *"왜 하필 이 강의냐"*에 답하거나,
가격 앞에서 *"이만큼 남으니 그 값을 한다"*로 가치를 쌓는 자리에 재사용.

출처: `granter-landing`(셀러OS 강의, `USP` 섹션) + `axacademy-landing`(`ValueStack` 각색 — 동일 의도의 3열 체크리스트 변형).

---

## 🤖 적용 지침 (이 폴더를 받은 Claude에게)

> "이 폴더의 섹션을 적용해줘"라는 요청을 받으면 아래대로 한다. **외부 의존성 없음 — placeholder만 교체하면 동작한다.**

1. **CSS 이식**: `usp-value-stack.css`를 대상 프로젝트 전역 CSS에 붙여넣거나 import.
   - 대상에 `design-system-skeleton.css`(또는 동일 토큰 `--signal`/`--paper`/`--font-display`/`--ease` +
     헬퍼 `.section`/`.section-dark`/`.wrap`/`.section-head`/`.sig`/`.section-sub`)가 이미 있으면
     **`.usp-*` 규칙만** 추가하면 된다(이 파일은 그 전제로 작성됨).
2. **컴포넌트 이식**: `USP.tsx`를 `components/`(또는 `components/sections/`)로 복사.
   비-Next/비-React 스택이면 동일 클래스명으로 마크업만 옮긴다(JSX → HTML).
3. **콘텐츠 교체**: 파일 상단 `USPS` 배열의 `title`·`desc`와 헤드라인의 `{기간}`·`{카테고리}`를
   대상 상품 값으로 교체. **박스 개수는 자유**(그리드가 자동 배치, 부제의 "N가지"는 `USPS.length`로 자동 반영).
   - `desc` 안 줄바꿈은 `\n`(CSS `white-space: pre-line`).
4. **배치**: 페이지에 `<USP />` 삽입. 위치는 아래 "배치" 참고.
5. **헤더 높이 무관**: sticky/pin 없음 → 오프셋 조정 불필요.

**동작 보증**: 순수 마크업 + CSS. `.reveal`/`.reveal-stagger`가 없어도 박스는 기본 노출(opacity 0 아님)이라
드롭인 즉시 보인다. 있으면 스크롤 등장 애니메이션이 얹힌다. **숨은 의존성 없음.**

---

## 파일 구성

| 파일 | 역할 |
|---|---|
| `USP.tsx` | 컴포넌트 (데이터 배열 + 마크업, JS 로직 없음) |
| `usp-value-stack.css` | `.usp*` 전용 스타일 (스켈레톤 토큰/헬퍼 전제, 그 외 자기완결) |

---

## 레이어 구조 (핵심)

```
.usp.section-dark            다크 배경 · min-height:100svh 풀스크린(옵션)
└─ .wrap
   ├─ .section-head          h2("이만큼 <span class=sig>강조</span> 배우고 남깁니다") + .section-sub("…없는 N가지")
   └─ .usp-grid              데스크톱 4열 → 태블릿 2열 → 모바일 1열
      └─ .usp-box (×N)       .usp-n(번호·signal색) / .usp-box-title / .usp-box-desc
                             hover 시 테두리가 --signal 로 물듦
```

---

## 변형 (두 가지 레이아웃, 같은 "일")

같은 설득 목적("이만큼 남는다")을 두 가지로 구현할 수 있다:

1. **번호 박스 그리드 (이 자산 · granter USP)** — 차별점을 `첫 번째~N번째`로 나열. 항목이 **동급 병렬**이고
   개수가 많을 때(6~8개) 적합. 기본값.
2. **그룹 체크리스트 (axacademy ValueStack)** — `배우는 것 / 만드는 것 / 받는 혜택` 3열로 묶고 각 항목에 ✓.
   가치를 **범주로 묶어** 보여주고 싶을 때. 이 자산의 그리드를 3열 `<ul>` + 체크 아이콘으로 바꾸면 됨
   (헤드라인·다크 배경·`.section-head`는 동일 재사용).

---

## 배치 (섹션 순서에서 어디에)

`reference/guides/section-narrative.md`의 "USP / 가치 총정리" 항목 참조. 두 자리가 유효하다:
- **해결(Solution) 직후** — "이게 답이다" 다음에 "그중에서도 이 강의만 주는 게 이것들"로 차별화(granter 실제 배치).
- **결과물(TakeHome)~가격(Pricing) 사이** — 가치를 총정리해 **가격 정당화** 직전에 쌓기.

⚠️ TakeHome(결과물)과 역할이 겹칠 수 있다. 둘 다 쓰면 **USP=남들과의 차별점 / TakeHome=끝나고 손에 남는 산출물**로
초점을 분리하고, 겹치면 하나로 합친다.

---

## 의존성 / 주의

- **외부 라이브러리·JS 없음.** 순수 마크업 + CSS.
- `color-mix()` 사용(hover·desc 색) — 최신 브라우저 기준. 구형 대응이 필요하면 rgba 고정값으로 치환.
- granter 원본은 hover 색에 브랜드 주황(`rgba(200,74,31,...)`)을 하드코딩했으나, 재사용 위해 `--signal` 로 일반화함.
- 폰트는 `--font-display`(Pretendard 가정, 토큰에서 교체 가능).

---

_저장일: 2026-07-15 · 원본 기준 granter-landing main · axacademy-landing ValueStack_
