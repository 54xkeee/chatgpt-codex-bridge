#!/bin/zsh

set -euo pipefail

readonly REPO_ROOT="${0:A:h:h:h}"
readonly README="${REPO_ROOT}/README.md"
readonly README_ZH="${REPO_ROOT}/README.zh-CN.md"
readonly RENDERER="${REPO_ROOT}/scripts/docs/render-widget-demo.py"
readonly TEMP_PARENT="${TMPDIR:-/tmp}"
fixture_root="$(mktemp -d "${TEMP_PARENT%/}/chatgpt-code-readme-demo.XXXXXX")"

cleanup() {
  [[ -n "${fixture_root:-}" && ! -L "$fixture_root" ]] || return
  case "$fixture_root" in
    "${TEMP_PARENT%/}"/chatgpt-code-readme-demo.*) ;;
    *) return ;;
  esac
  find "$fixture_root" -depth -mindepth 1 -delete
  rmdir "$fixture_root"
}
trap cleanup EXIT

[[ -f "$README" && -f "$README_ZH" && -x "$RENDERER" ]]
grep -Fq '## Durable status cards' "$README"
grep -Fq '## 可持久恢复的状态卡片' "$README_ZH"

for state in running completed interrupted; do
  image="${REPO_ROOT}/docs/assets/readme/codex-job-${state}.jpg"
  html="${fixture_root}/${state}.html"
  [[ -s "$image" ]]
  file "$image" | grep -Fq 'JPEG image data'
  python3 "$RENDERER" --state "$state" --output "$html"
  grep -Fq 'DEMO · SYNTHETIC DATA' "$html"
  grep -Fq "demo-job-" "$html"
  ! grep -Fq '/Users/' "$html"
  grep -Fq "docs/assets/readme/codex-job-${state}.jpg" "$README"
  grep -Fq "docs/assets/readme/codex-job-${state}.jpg" "$README_ZH"
done

print 'README inline demo tests: PASS'
