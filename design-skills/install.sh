#!/usr/bin/env bash
# design-skills 활성화 — 번들된 애니메이션/디자인 스킬을 ~/.claude/skills/ 로 심볼릭 링크한다.
# 실행: bash design-skills/install.sh   (레포 루트 또는 어디서든)
set -euo pipefail

BUNDLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="${HOME}/.claude/skills"
mkdir -p "${SKILLS_DIR}"

SKILLS=(
  emil-design-eng
  review-animations
  improve-animations
  find-animation-opportunities
  animation-vocabulary
  apple-design
)

echo "번들 원본: ${BUNDLE_DIR}"
echo "링크 대상: ${SKILLS_DIR}"
echo

for s in "${SKILLS[@]}"; do
  src="${BUNDLE_DIR}/${s}"
  dst="${SKILLS_DIR}/${s}"
  if [[ ! -d "${src}" ]]; then
    echo "  ✕ ${s} — 원본 없음(건너뜀)"; continue
  fi
  if [[ -e "${dst}" && ! -L "${dst}" ]]; then
    echo "  ⚠ ${s} — 같은 이름의 실제 폴더가 이미 있음(수동 확인 필요, 건너뜀)"; continue
  fi
  ln -sfn "${src}" "${dst}"
  echo "  ✓ ${s} -> ${dst}"
done

echo
echo "완료. Claude Code에서 review-animations 등으로 호출하거나,"
echo "design-skills/<name>/SKILL.md 를 직접 열어 규칙을 적용하세요."
