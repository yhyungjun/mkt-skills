# mkt-landing

한국어 **강의·교육 상품 랜딩페이지**를 기획(PRD)부터 QA·배포까지 순차 빌드하는 [Claude Code](https://claude.com/claude-code) 스킬(플레이북).
소셜로그인(Google·Kakao·Naver)·토스결제·SMS인증·자동메일·GA4/GTM 트래킹·어드민·SEO/성능까지 포함하며,
`granter-landing` 실제 구현을 역설계한 캐논에 실전 빌드 학습을 흡수했다.

## 무엇을 하나
- **STEP 0 결제방식 선택**(토스 PG / 계좌이체 / 외부폼)이 전체 구성을 분기 → 필요한 단계만 빌드.
- **14단계 플레이북**(P0 기획 → P13 QA)을 순서·의존성·함정까지 정리한 단일 출처.
- 복붙 가능한 **코드 템플릿**(인증·결제·폼·메일·트래킹·어드민·가격변형·Slack알림·섹션퍼널)과
  **드롭인 섹션**(맥북 스크럽 커리큘럼·강사 스포트라이트), 브랜드 중립 **디자인 스켈레톤**.

## 기술 스택
Next.js 16 App Router · React 19 · Tailwind 4 · Supabase · Auth.js v5 · Toss Payments · Resend · Cloudflare Workers · GTM→GA4.

## 설치
Claude Code 스킬 디렉터리에 클론한다.
```bash
git clone https://github.com/yhyungjun/mkt-landing.git ~/.claude/skills/mkt-landing
```
이후 Claude Code에서 "강의 랜딩 처음부터 만들어" / "랜딩 빌드 순서대로" 등으로 스킬이 발동한다.
진입점은 `SKILL.md` → 마스터 가이드는 `reference/playbook.md`.

## 구조
```
SKILL.md                     진입점(발동 조건·빌드 순서·번들 목록)
reference/playbook.md        마스터 14단계 상세(단일 출처)
reference/features-checklist.md  순차 체크리스트
reference/code-templates/    복붙 코드(auth·payment·forms·email·tracking·admin·price-variant·slack-notify·section-funnel …)
reference/guides/            판단·작문·정책 가이드(섹션 설득 아크·카피·법무·데모섹션·계좌이체 …)
reference/setup/             외부 콘솔 설정 절차(Supabase·OAuth·Toss·Resend·Cloudflare·GTM)
assets/                      드롭인 섹션(mac-open-motion · instructor-spotlight)
```

## 커스터마이즈
가격·기수·도메인·발신 이메일·브랜드 문구는 예시값(placeholder)이므로 **자기 상품에 맞게 교체**한다.
법무 페이지(약관·개인정보·환불)는 반드시 **법적 검토** 후 사용.

## 라이선스
개인용 플레이북을 공개한 것으로, 자유롭게 참고·포크해도 된다. 예시에 포함된 서드파티/브랜드명은 각 소유자의 것이다.
