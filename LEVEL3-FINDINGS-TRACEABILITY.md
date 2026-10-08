# Level 3 findings traceability

This document is review evidence, not candidate implementation scope.

| Review finding | Required behavior | Fix location | Reproducible fixture | Result |
|---|---|---|---|---|
| v1 normalized version | Lock, installed.json and installed.php normalized versions must agree and use valid representation. | `git-init` Composer validator | `lock-normalized-*`, `normalized-coordinated-invalid-*`, `normalized-coordinated-type-*`, `normalized-supported-*`, `normalized-invalid-*`, `normalized-php-only-type-*` | Equality checks retained; independent representation/type validation now required in all three files, including optional-field and uninstalled-dev gaps. |
| v1 absent lock reference | No usable lock reference requires metadata reference `null`. | `git-init` Composer validator | `absent-reference-*`, `null-reference-*` | Null cases PASS; stale reference BLOCK. |
| v1 metapackage path | Both installed metadata forms require null install path for metapackages. | `git-init` Composer validator | `metapackage-valid`, `metapackage-json-path`, `metapackage-php-path` | Null path PASS; either non-null path BLOCK. |
| v2 source/dist fallback | Non-empty source wins; null/missing/empty source falls back to non-empty dist; no usable reference requires null PHP metadata reference. | `git-init` reference precedence | `source-reference-{null,missing,empty}-dist-*`, `source-reference-precedence-*`, `references-empty-source-dist-*` | Positive cases PASS; metadata mismatch BLOCK. |
| v3 reference types | References are only non-empty strings. Any non-null non-string source/dist is fail-closed, even when installed.php has a matching literal; valid source does not mask invalid dist. | `git-init` `ReferenceTypeError` path; category `vendor Composer reference type invalid` | Matrix `source-reference-*` and `dist-reference-*` for integer, float, list, object, true and false | Every check/dry-run/init negative fixture asserts exit 4, the exact category, no generic metadata category, no sensitive value output and no mutation. |
| v4 equality without validity | Coordinated invalid normalized values must BLOCK independently of equality. | `git-init` `validate_normalized_version` / `NormalizedVersionError`; category `vendor Composer normalized version invalid` | `normalized-coordinated-invalid-*` and `normalized-coordinated-type-*` | Three modes require exit 4, exact redacted category, no metadata/content leak, no files/index/config/refs mutation. |

The previous reference-only regression log is `/tmp/git-init-reference-full-tests-final.log` (ephemeral execution evidence). It records the earlier reference matrix plus `37 passed, 0 failed` and `76 passed, 0 failed`; real commitlint was skipped because local `node_modules` is intentionally absent.

Authorized normalized-version fix evidence:

- Strict TDD red: `/tmp/git-init-normalized-tdd-red.log`; first coordinated-invalid
  string returned 0 instead of 4 in check/dry-run/init before implementation;
  init visibly mutated only the isolated fixture. This confirms the v4 bypass.
- Source URLs/version/commit and supported output grammar are recorded in
  `GIT-INIT-V2-SPEC.md`: Composer 2.10.3 -> composer/semver 3.4.4 at
  `198166618906cb2de69b95d7d47e5fa8aa1b2b95`.
- All 86 expected `successfulNormalizedVersions`/`successfulNormalizedBranches` outputs from the pinned upstream
  tests were read and accepted by the validator in a local compatibility check.
  Persisted integration positives cover stable, padded/date/CalVer, alpha/beta/RC,
  patch and compound identifiers, numeric/date/named dev branches and legacy alias.
- v1-v4 findings were reread from existing review evidence. Reference types are
  independently checked before precedence/equality; no usable reference still
  requires PHP null; both metapackage paths independently require null. Their
  existing negative/positive matrices remain in full regression. No further
  production fixes were needed outside normalized-version validation.
- Additional directly needed coverage validates each JSON normalized field alone,
  PHP normalized values/types without optional JSON fields, and uninstalled lock
  dev entries. No review was started and no commit was made.

Final verification for this authorized fix:

- `bash tests/run.sh`: PASS (exit 0), all 273 reported checks/fixtures;
  `/tmp/git-init-normalized-full-regression-final.log` includes the complete
  dependency and Composer matrices. The earlier interrupted run is superseded.
- `python3 tests/receipt.py`: PASS, 14 fixtures;
  `/tmp/git-init-normalized-receipt.log`.
- `python3 tests/preflight.py`: PASS, 76 checks;
  `/tmp/git-init-normalized-preflight.log`.
- Shell syntax, Python test/embedded vendor validator syntax and `git diff --check`:
  PASS. `bash tests/commitlint-real.sh`: SKIP because project-local node_modules
  is absent; no dependencies were installed.

Plan A follow-up (2026-10-08): only numeric stable output acceptance removed.
The coordinated `1.2.3.0-stable` fixture was added and run before the production
change; [RED evidence](tests/corpus/plan-a-tdd.md) records all three unexpected
exit-0 results. [Corpus method](tests/corpus/README.md) documents SHA-256-verified
static extraction of all 86 pinned successful normalization/branch rows and
source-derived lowercase stable behavior. Every corpus output passes the custom
policy; this is corpus verification, not parser equivalence. No material corpus
grammar gap was found, no grammar expansion made, no commit or review started.

Four-secret-risk remediation (2026-10-08), James-authorized scope only:

| Observed source risk | Representation-only change | Equivalence evidence |
|---|---|---|
| `tests/dependencies.py` URL metadata | Split credential URL literal into runtime concatenation. | Execute actual URL loop and capture every metadata argument byte. |
| `tests/preflight.py` private remote | Split credential URL literal into runtime concatenation. | Execute actual Git call and capture remote argument bytes. |
| `tests/run.sh` remote | Assemble URL with shell variable append. | Execute actual remote setup with capture Git function. |
| `git-init` secret regex literal | Assemble the same regex with shell variable appends; use it in both existing grep calls. | Capture actual regex bytes/flags and compare 22 representative match results with pre-change baseline. |

[Strict TDD record](tests/runtime-equivalence-tdd.md) preserves baseline/RED before
production/harness edits. No scanner ignore, exception, bypass or weaker
matching; existing BLOCK/redaction/no-mutation assertions remain. Linked-worktree
detection, identity/ref preflight behavior and Composer policy are outside this
scope. Existing unrelated worktree changes are preserved. Formal validation uses
a newly materialized full candidate patch from fixed base
`05db4835607375d74945093843c67bd102775d3a`; identity/ref issues are reported
separately from the four-source secret-risk result. No commit/push/merge/review.

Validation for the four-risk scope: full `bash tests/run.sh` PASS (278 reported
PASS lines including the new equivalence checks); receipt PASS (14 fixtures);
preflight PASS (76 checks); real installed commitlint PASS (6 cases); Bash/Python
syntax and `git diff --check` PASS. All four original source risks are absent in
the unchanged scanner's source regressions; the regression source also passes
its self-scan. The saved runtime baseline SHA-256 remains
`7f6134d0c227fbccc07fb648f7a473e1f5fc2a770ecd96528c92e0c7fdf70e0e`.

Formal full-candidate evidence is in `/tmp/git-init-four-risk-evidence/`:
`materialize.py`, `candidate.patch`, `candidate-manifest.json`, and
`candidate-check.log`. The full patch includes all 13 prior Plan A candidate
paths plus the two additional fixture files, three runtime-equivalence evidence
files and this traceability document (19 declared paths). Every materialized
file is compared byte-for-byte. Installed node_modules are copied without
installing packages; generated caches and historical review artifacts are not
candidate source. `identity-ref-preflight.json` separates identity/ref blockers
and the actual secret-risk summary; a nonzero overall preflight exit is never
reported as a secret-risk failure or a full preflight PASS.
