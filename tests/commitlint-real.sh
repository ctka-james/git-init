#!/usr/bin/env bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
BIN="$ROOT/node_modules/.bin/commitlint"
if [[ ! -x $BIN ]]; then
  printf '%s\n' 'SKIP: 尚未建立 project-local node_modules；本測試不安裝相依套件。'
  exit 0
fi
TMP="$(mktemp -d "${TMPDIR:-/tmp}/commitlint-v2.XXXXXX")"
trap 'rm -rf -- "$TMP"' EXIT
pass=0; fail=0
case_file() { printf '%s' "$2" > "$TMP/message"; if "$BIN" --config "$ROOT/commitlint.config.cjs" --edit "$TMP/message" >/dev/null 2>&1; then got=0; else got=1; fi; if [[ $got == "$3" ]]; then printf 'PASS: %s\n' "$1"; pass=$((pass+1)); else printf 'FAIL: %s\n' "$1" >&2; fail=$((fail+1)); fi; }
case_file 'valid Traditional Chinese body' $'feat(初始化): 加入本機規則\n\n- 實際變更說明\n' 0
case_file 'invalid type' $'perf(初始化): 不允許的類型\n\n- 說明\n' 1
case_file 'missing scope' $'feat: 缺少範圍\n\n- 說明\n' 1
case_file 'missing body' $'docs(文件): 缺少 body\n' 1
case_file 'missing leading blank' $'fix(修正): 空行錯誤\n- 說明\n' 1
case_file 'empty subject' $'test(測試): \n\n- 說明\n' 1
printf 'RESULT: %d passed, %d failed\n' "$pass" "$fail"
(( fail == 0 )) || exit 10
