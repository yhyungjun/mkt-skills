# design-skills — 랜딩 디자인·모션 폴리시 번들

`mkt-landing`의 **P2 디자인 / P3 섹션** 단계에서 랜딩페이지의 애니메이션·인터랙션·시각 디테일을
"장인 수준(craft bar)"으로 끌어올릴 때 선택해서 쓰는 스킬 묶음이다.

## 출처 (서드파티 · MIT)
- 원본: **[emilkowalski/skills](https://github.com/emilkowalski/skills)** — Emil Kowalski (Sonner·Vaul 제작자, ex-Vercel/Linear)
- 라이선스: MIT (`./LICENSE` 포함, 저작권 표기 유지)
- 최신본 갱신: `npx skills@latest add emilkowalski/skills` 후 이 폴더로 다시 복사

## 수록 스킬 (6)
| 스킬 | 언제 |
|---|---|
| `mkt-emil-design-eng` | 디자인·애니메이션 결정의 **코어 철학**(easing·duration·spring·성능·접근성 프레임워크). 디자인 판단이 필요할 때 먼저 참조. |
| `mkt-review-animations` | 작성한 모션 코드를 **엄격히 리뷰**(승인 아닌 지적 기본). `disable-model-invocation`이라 명시 호출 전용. |
| `mkt-improve-animations` | 코드베이스 **전체 모션 감사** → 우선순위 표 → `plans/`에 자립 실행계획. 소스 직접 수정 안 함. |
| `mkt-find-animation-opportunities` | 모션이 **필요한 곳 / 넣으면 안 되는 곳** 탐색. |
| `mkt-animation-vocabulary` | 원하는 모션을 **정확한 용어**로 지시하는 어휘집. |
| `mkt-apple-design` | Apple의 인터페이스·모션 원칙(WWDC 디자인 토크)을 웹용으로 번역. |

## 사용 방법 (두 가지 — 자립형)

### 1) 경로 참조 (clone만으로 즉시 동작 · 추가설치 불필요)
디자인 단계에서 각 스킬의 `SKILL.md`를 **읽어 규칙을 그대로 적용**한다.
예: `design-skills/mkt-emil-design-eng/SKILL.md`를 열어 easing·duration·`:active` 스케일·popover origin 등을 적용,
`design-skills/mkt-review-animations/STANDARDS.md`로 완성 모션을 체크.

### 2) 라이브 스킬로 활성화 (선택 · 호출형)
`design-skills/install.sh`를 실행하면 `~/.claude/skills/`로 심볼릭 링크되어
`mkt-review-animations` 같은 이름으로 직접 호출된다.
```bash
bash design-skills/install.sh    # mkt-landing 레포 루트에서
```

> 어느 방식이든 원본 파일은 이 폴더가 단일 출처다. 직접 수정하지 말고, 갱신은 위 `npx` 경로로.
