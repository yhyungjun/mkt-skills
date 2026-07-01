# instructor-spotlight — 글로우 오라 + 인물 컷아웃 강사소개 섹션

랜딩페이지용 **다크 배경 인물 스포트라이트** 섹션. 가운데 인물 컷아웃이 방사형
글로우(파랑·보라·주황) 위에 떠 있고, 하단이 배경으로 페이드되며, 이름 → 리드 카피 →
✓ 크레덴셜 리스트가 중앙 정렬된다. 강사/창업자/대표 소개 등 "한 사람을 띄우는" 모든 곳에 재사용.

출처: `granter-landing` (셀러OS 강의 랜딩, 강사소개 섹션).

---

## 🤖 적용 지침 (이 폴더를 받은 Claude에게)

> "이 폴더의 레이어를 적용해줘"라는 요청을 받으면 아래대로 한다. **외부 의존성 없음 — 그대로 동작한다.**

1. **CSS 이식**: `instructor-spotlight.css`를 대상 프로젝트 전역 CSS에 통째로 붙여넣거나 import.
   - 대상에 이미 `--ink / --paper / --signal / --maxw / --pad-x / --pad-y / --font-display` 토큰이
     **모두** 정의돼 있으면, 파일 상단 `[DESIGN TOKENS]`·`[레이아웃 헬퍼]` 블록은 제거(중복 방지).
     하나라도 없으면 그대로 둔다.
2. **컴포넌트 이식**: `Instructor.tsx`를 `components/`(또는 대상 구조에 맞는 위치)로 복사.
   비-Next/비-React 스택이면 동일 클래스명으로 마크업만 옮긴다(JSX → HTML).
3. **이미지**: `portrait-sample.png`를 대상의 `public/`에 복사. 컴포넌트는 `/portrait-sample.png`를
   참조하므로 경로 수정 불필요. 실제 인물로 바꿀 땐 같은 파일명으로 덮거나 `src`만 교체.
   - 권장 이미지: 배경 투명 PNG(누끼), 1:1 근처, 어깨까지 상반신.
4. **텍스트 교체**: `.inst-name` / `.inst-lead` / `.inst-creds > li` 안의 문구를 대상 인물 정보로 교체.
   리드의 `{"\n"}`는 의도된 줄바꿈(`white-space: pre-line`).
5. **헤더 높이 무관**: 이 섹션은 sticky/pin 없음 → 별도 오프셋 조정 불필요.
6. 페이지에 `<Instructor />` 배치.

**동작 보증**: `.inst-hero`는 CSS-only 등장 애니메이션(`@keyframes instReveal`)을 쓰므로 JS·옵저버 없이
마운트 즉시 보인다. reduced-motion이면 애니메이션 생략하고 바로 표시. **숨은 의존성 없음.**

---

## 파일 구성

| 파일 | 역할 |
|---|---|
| `Instructor.tsx` | 컴포넌트 (마크업만, JS 로직 없음) |
| `instructor-spotlight.css` | 전체 스타일 (토큰·레이아웃 헬퍼·글로우·마스크 포함, 자기완결적) |
| `portrait-sample.png` | 인물 컷아웃 **샘플** (512×512 RGBA, 배경 투명) — 실제 사용 시 교체 |

---

## 레이어 구조 (핵심)

```
.instructor.section-dark           다크 배경 (position: relative; overflow: hidden)
├─ ::before                        ★ 글로우 오라 — 방사형 그라데이션 3겹 + blur(72px)
│                                    + 상/하 mask 페이드 (z-index: 0, 인물 뒤)
└─ .wrap (z-index: 1)
   └─ .inst-hero                   중앙 정렬 세로 스택
      ├─ .inst-portrait            인물 — 하단 fade mask로 배경에 녹아듦
      ├─ .inst-name                이름 + "강사" 보조 라벨
      ├─ .inst-lead                리드 카피 (\n 줄바꿈 = white-space: pre-line)
      └─ .inst-creds               ✓ 크레덴셜 리스트 (좌측 정렬)
```

**재사용 시 가장 중요한 두 가지 트릭**
1. **글로우 오라** (`::before`): 방사형 그라데이션을 `blur(72px)`로 번지게 하고, 위아래를
   `mask-image` linear-gradient로 페이드 → 빛 띠가 공중에 뜬 느낌. 색은 rgba 3줄만 바꾸면 톤 변경.
2. **인물 하단 페이드** (`.inst-portrait` mask): 컷아웃 PNG 아랫부분을 투명하게 깎아 배경과
   이음새 없이 연결. 인물 사진에 배경이 남아 있어도 자연스럽게 묻힌다.

---

## 새 랜딩페이지에 붙이는 법

1. `Instructor.tsx`를 `components/`로 복사.
2. `instructor-spotlight.css`를 전역 CSS에 import (또는 붙여넣기).
   - 이미 `--ink/--paper/--signal` 토큰이 있으면 CSS 상단 `[DESIGN TOKENS]`·`[레이아웃 헬퍼]` 삭제.
3. **인물 이미지**: `portrait-sample.png`를 `public/`에 복사(컴포넌트가 `/portrait-sample.png` 참조).
   실제 인물로 바꿀 땐 같은 파일명으로 덮거나 `src`만 교체.
   - 권장: **배경 투명 PNG**(누끼), 정사각(1:1) 근처. 어깨까지 들어오는 상반신이 마스크와 잘 맞음.
4. 텍스트(이름·리드·크레덴셜 li) 교체.
5. 페이지에서 `<Instructor />` 렌더.

### 톤 커스터마이징
- 글로우 색: `instructor-spotlight.css`의 `::before` 안 `radial-gradient` rgba 3줄.
- 글로우 번짐 정도: `filter: blur(72px)` 값.
- 인물 페이드 시작점: `.inst-portrait`의 mask `#000 76%` 비율.

---

## 의존성 / 주의

- **외부 라이브러리·JS 없음.** 순수 마크업 + CSS. 등장 애니메이션도 CSS-only(`@keyframes instReveal`)라
  옵저버 불필요 — 드롭인 즉시 보인다.
- `mask-image`는 Safari 대비 `-webkit-mask-image`도 함께 선언되어 있음(그대로 유지).
- 폰트는 Pretendard 가정(토큰에서 교체 가능).
- `portrait-sample.png`는 실제 인물(특정인)이므로 **반드시 교체**해서 사용할 것.

---

_저장일: 2026-06-11 · 원본 기준 granter-landing main_
