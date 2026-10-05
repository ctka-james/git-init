#!/usr/bin/env bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
SCRIPT="$ROOT/git-init"
BASE="$(mktemp -d "${TMPDIR:-/tmp}/git-init-v2.XXXXXX")"
trap 'rm -rf -- "$BASE"' EXIT
export GIT_CONFIG_GLOBAL="$BASE/global.gitconfig"
export GIT_CONFIG_SYSTEM=/dev/null
export GIT_CONFIG_NOSYSTEM=1
: > "$GIT_CONFIG_GLOBAL"
PASS=0
FAIL=0

pass() { printf 'PASS: %s\n' "$1"; PASS=$((PASS + 1)); }
fail() { printf 'FAIL: %s\n' "$1" >&2; FAIL=$((FAIL + 1)); }
run() { if ( cd "$1" && "$SCRIPT" "${@:2}" ) >"$BASE/out" 2>&1; then RUN_RC=0; else RUN_RC=$?; fi; }
expect_code() { local got=$1 want=$2 label=$3; [[ $got == "$want" ]] && pass "$label" || fail "$label（exit $got，預期 $want）"; }
expect_out() { grep -Fq -- "$2" "$BASE/out" && pass "$1" || fail "$1"; }
newdir() { mkdir -p "$BASE/$1"; printf '%s' "$BASE/$1"; }
setup_repo() {
  local d=$1
  git -C "$d" init -q -b main
  git -C "$d" config --local user.name 'Temporary Fixture'
  git -C "$d" config --local user.email 'fixture@example.test'
  printf 'baseline\n' > "$d/source.txt"
  git -C "$d" add source.txt
  git -C "$d" commit -qm 'test(fixture): 建立暫存基線' --no-verify
}

# 1 empty, dry-run, and no source mutations.
d=$(newdir empty)
run "$d" --check; rc=$RUN_RC; expect_code "$rc" 0 'empty directory check is read-only ready'; expect_out 'reports PREFLIGHT_OK' 'PREFLIGHT_OK'
run "$d" --dry-run; rc=$RUN_RC; expect_code "$rc" 0 'empty dry-run succeeds'; [[ ! -e $d/.git ]] && pass 'dry-run did not init Git' || fail 'dry-run mutated Git'
run "$d" --init --user-name '測試使用者' --user-email 'tester@example.test'; rc=$RUN_RC; expect_code "$rc" 0 'empty init succeeds'; git -C "$d" rev-parse --verify HEAD >/dev/null 2>&1 && fail 'init made a commit' || pass 'init made no commit'; [[ $(git -C "$d" symbolic-ref --short HEAD) == main ]] && pass 'unborn main preserved' || fail 'main not unborn'; [[ -x $d/.githooks/commit-msg ]] && pass 'local hook created' || fail 'local hook absent'

# 2 source/ignore/Unicode/identity blockers.
d=$(newdir source); printf 'source\n' > "$d/應用.js"
run "$d" --init --user-name '測試' --user-email 'tester@example.test'; rc=$RUN_RC; expect_code "$rc" 3 'nonempty source without ignore blocks'; expect_out 'lists ignore blocker' '缺少 .gitignore'
printf 'node_modules/\n' > "$d/.gitignore"
run "$d" --init --user-name '測試' --user-email 'tester@example.test'; rc=$RUN_RC; expect_code "$rc" 0 'Unicode path with existing ignore initializes'
d=$(newdir missing-identity); setup_repo "$d"; git -C "$d" config --local --unset user.name; git -C "$d" config --local --unset user.email
run "$d" --init; rc=$RUN_RC; expect_code "$rc" 2 'init requires explicit identity'; [[ -z $(git -C "$d" config --local --get user.name || true) ]] && pass 'missing local identity was not sourced globally' || fail 'identity unexpectedly set'

# 3 remote redaction, secret value non-disclosure, binary and symlink risk.
d=$(newdir remote); setup_repo "$d"; git -C "$d" remote add origin 'https://user:password@example.test/path?token=hidden#fragment'
run "$d" --check; rc=$RUN_RC; expect_code "$rc" 0 'remote-only repo check succeeds'; expect_out 'remote userinfo is redacted' 'https://example.test/path'; grep -Fq 'password' "$BASE/out" && fail 'remote credential leaked' || pass 'remote credential not printed'
d=$(newdir secret); printf 'token=temporarysecretvalue123\n' > "$d/config.env"
run "$d" --check; rc=$RUN_RC; expect_code "$rc" 4 'secret heuristic blocks'; grep -Fq 'temporarysecretvalue123' "$BASE/out" && fail 'secret value leaked' || pass 'secret value redacted'
d=$(newdir symlink); ln -s /etc/passwd "$d/escape-link"
run "$d" --check; rc=$RUN_RC; expect_code "$rc" 4 'symlink escape blocks init'; expect_out 'marks symlink unscanned' 'symlink 未掃描'

# 4 existing repo, dirty/ref/config conflicts and branch policy.
d=$(newdir repo); setup_repo "$d"
run "$d" --init --user-name 'Temporary Fixture' --user-email 'fixture@example.test'; rc=$RUN_RC; expect_code "$rc" 0 'clean baseline repo receives local bootstrap'; git -C "$d" show-ref --verify --quiet refs/heads/docs && pass 'docs branch created without checkout' || fail 'docs branch missing'; [[ $(git -C "$d" branch --show-current) == main ]] && pass 'HEAD branch preserved' || fail 'HEAD changed'
printf 'dirty\n' >> "$d/source.txt"
before_source=$(sha256sum "$d/source.txt"); before_refs=$(git -C "$d" show-ref); before_index=$(sha256sum "$d/.git/index")
run "$d" --init; rc=$RUN_RC; expect_code "$rc" 0 'ordinary dirty source rerun succeeds'
[[ $(sha256sum "$d/source.txt") == "$before_source" && $(git -C "$d" show-ref) == "$before_refs" && $(sha256sum "$d/.git/index") == "$before_index" ]] && pass 'ordinary source refs and index unchanged' || fail 'ordinary source or Git state changed'
d=$(newdir config-conflict); setup_repo "$d"; git -C "$d" config --local core.hooksPath custom-hooks
run "$d" --init --user-name 'Temporary Fixture' --user-email 'fixture@example.test'; rc=$RUN_RC; expect_code "$rc" 5 'local config conflict blocks'; [[ $(git -C "$d" config --local --get core.hooksPath) == custom-hooks ]] && pass 'conflicting config not overwritten' || fail 'config overwritten'
d=$(newdir ref-conflict); setup_repo "$d"; git -C "$d" branch feat; printf 'diverged\n' >> "$d/source.txt"; git -C "$d" add source.txt; git -C "$d" commit -qm 'test(fixture): 產生 divergent baseline' --no-verify
run "$d" --check; rc=$RUN_RC; expect_code "$rc" 5 'existing branch ref conflict blocks'; git -C "$d" show-ref --verify --quiet refs/heads/feat && pass 'existing ref preserved' || fail 'existing ref lost'

# 5 hook fail-closed; no npm/npx/curl calls; partial failure returns 6.
d=$(newdir hook); cp "$ROOT/.githooks/commit-msg" "$d/hook"; chmod 755 "$d/hook"; printf 'x\n' > "$d/msg"
( cd "$d" && ./hook msg ) >"$BASE/hook.out" 2>&1 && fail 'missing local commitlint hook passed' || pass 'hook fails closed without node_modules'
grep -Fq 'fail closed' "$BASE/hook.out" && pass 'hook reports fail-closed reason' || fail 'hook reason missing'
FAKE="$BASE/fake"; mkdir "$FAKE"
for cmd in npm npx curl; do printf '#!/bin/sh\nprintf "%s\\n" "$0" >> "%s/calls"\nexit 97\n' "$cmd" "$BASE" > "$FAKE/$cmd"; chmod 755 "$FAKE/$cmd"; done
d=$(newdir offline); PATH="$FAKE:$PATH" run "$d" --check; rc=$RUN_RC; expect_code "$rc" 0 'check has no package/network requirement'; [[ ! -s $BASE/calls ]] && pass 'npm npx curl were not called' || fail 'forbidden command called'
FAKE_GIT="$BASE/fake-git"; mkdir "$FAKE_GIT"
printf '#!/bin/sh\nif [ "$1" = config ] && [ "$2" = --local ] && [ "$3" = commit.template ]; then exit 99; fi\nexec /usr/bin/git "$@"\n' > "$FAKE_GIT/git"; chmod 755 "$FAKE_GIT/git"
d=$(newdir partial)
PATH="$FAKE_GIT:$PATH" run "$d" --init --user-name '測試' --user-email 'tester@example.test'; rc=$RUN_RC; expect_code "$rc" 6 'mid-init failure reports partial state'; expect_out 'partial state lists mutation steps' 'PARTIAL_INIT_FAILURE'; [[ -d $d/.git ]] && pass 'partial recovery retains Git directory' || fail 'partial recovery removed Git directory'

# 6 global isolation is byte-for-byte stable and shell syntax is separately checked.
before=$(cksum "$GIT_CONFIG_GLOBAL")
bash -n "$SCRIPT" || { fail 'bash syntax'; }
after=$(cksum "$GIT_CONFIG_GLOBAL")
[[ $before == "$after" ]] && pass 'fixture global config unchanged' || fail 'fixture global config changed'

printf 'RESULT: %d passed, %d failed\n' "$PASS" "$FAIL"
(( FAIL == 0 )) || exit 10
