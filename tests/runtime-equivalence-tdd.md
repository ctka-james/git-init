# Four-risk representation TDD evidence (2026-10-08)

Before editing production or existing harness behavior, added
`runtime_equivalence.py` and recorded `runtime-equivalence-baseline.json` from
current code. The baseline stores exact argument/regex bytes as hex, both grep
flag lists, and 22 representative matching/nonmatching results (exit codes,
stdout and stderr bytes). Baseline SHA-256:
`7f6134d0c227fbccc07fb648f7a473e1f5fc2a770ecd96528c92e0c7fdf70e0e`.

The Python AST statements are executed with capture functions: dependency
metadata receives every URL from the actual fixture loop; preflight's actual
private-remote call supplies its argument. The shell remote setup is executed
with a capture Git function. The actual `scan_file` function is executed with a
logging grep function that delegates to real grep; both secret-regex calls are
captured. This tests runtime values rather than inspecting literal spellings.

Baseline command: `python3 tests/runtime_equivalence.py --record` (exit 0).
RED command: `python3 tests/runtime_equivalence.py --remediated` (exit 1).
Before changes, output included:

    PASS: exact runtime fixture bytes, regex bytes, grep flags and matches
    AssertionError: static representation still raises risks: ['git-init', 'tests/dependencies.py', 'tests/preflight.py', 'tests/run.sh']

After changes, the same command exits 0 with both runtime equivalence and all
four static-source scan assertions passing. The baseline is never regenerated
as part of the regression command. Raw logs and pre-change sources are preserved
in `/tmp/git-init-four-risk-evidence/` (ephemeral local execution evidence).

Only three fixture URL representations and the scanner regex construction
changed; existing BLOCK, redaction and no-mutation assertions remain. No
linked-worktree handling, ignore rule, exception, bypass, or detection policy
changed. No commit, push, merge or review is authorized by this evidence.

The first formal candidate check exposed a new self-match in the added match
corpus. A failing scan assertion for the regression source was added before
splitting that literal; `/tmp/git-init-four-risk-evidence/test-source-red.log`
preserves this additional RED. Corpus runtime bytes and the original baseline
hash remain unchanged. The regression now also scans its own source.

Complete regression finished with exit 0: `bash tests/run.sh` (278 PASS lines),
receipt (14 fixtures), preflight (76 checks), installed commitlint (6 cases).
Shell/Python syntax and whitespace checks passed. The final full candidate is
newly materialized only after these checks; its patch/manifest/check output and
separate identity/ref record are retained in the evidence directory.
