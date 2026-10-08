# git-init v2 Authoritative Behavioral Specification

本文件是 git-init v2 唯一 authoritative behavioral specification。歷史 Fix report、舊測試說明及舊設計文件若與本文件衝突，以本文件為準；歷史報告僅供 diagnostic 使用。AI Agent 不得自行修改 SPEC 讓 implementation 或 tests 通過。任何 behavioral change 必須先取得 James 明確批准。本文件不是修改、提交、推送或部署授權，也不是測試通過宣告。

## 用途與邊界

git-init 是 AI-safe project Git/GitHub bootstrap layer，不是 source-control replacement、security daemon 或 authorization authority。Git 是 project source 的版本控制 authority；receipt/ledger 只記錄 bootstrap ownership/state，不建立 project-wide source hash ledger。

## CLI 與 mutation

- 無參數及 `--check`：read-only inspection；回報環境、repository、branch、working tree、sanitized remotes、local/global identity 狀態、ignore、hooks、template、commitlint、GitHub CLI/auth evidence 與 secret-risk summary。不建檔、改檔、改 config/refs/index，不安裝、不登入、不連網。缺少 optional tools 回報 unavailable；無法離線確認 auth 回報 UNKNOWN。
- `--dry-run`：相同 read-only preflight，列出預計 bootstrap 工作，不 mutation。
- `--init`：只有明確授權 mutation scope 且 preflight 無 blocker 時，才能建立 repository、缺少且可安全建立的 bootstrap artifacts、必要 repository-local config 與允許的新 branch refs。普通 init 不是 repair/restore/migration，不以初始化成功推論任何下游 Gate 已批准。
- mutation 前的 BLOCK 不得造成 partial mutation。mutation 開始後若系統操作失敗，非零回報已完成範圍並停止；不得自行 reset、clean 或刪除使用者資料。recovery 由 Work/James 判斷。

## Bootstrap ownership

ownership 是 artifact/path-level，不是 working-tree-level 或 directory-level。現在的 candidate paths：`.gitignore`、`.gitmessage`、`commitlint.config.cjs`、`.githooks/commit-msg`、`AI-WORKFLOW.template.md`。

| Ownership / 狀態 | 行為 |
|---|---|
| CREATED unchanged | NO-OP |
| CREATED modified | BLOCK，不覆寫 |
| CREATED deleted | BLOCK，不重建 |
| PRESERVED unchanged | PRESERVE |
| PRESERVED modified | PRESERVE，不要求 template hash 相同 |
| PRESERVED deleted | BLOCK，不以工具模板恢復 |

首次 bootstrap 前已存在的 candidate 屬使用者，登記 PRESERVED；工具首次建立才是 CREATED。FRESH、尚未管理且 missing 的 candidate 可依安全規則建立。既有 `.gitignore` 保留原內容；非空 non-Git project 缺少 ignore 時先要求 review/處理，不能任意覆寫或排除真正 source。

## Trust state 與 threat model

v2 採 Model A — Project-local best effort。receipt、integrity marker、bootstrap config 與相關 metadata 必須 consistent。

- consistent state：continue，依 ownership 判斷 artifacts。
- partial、malformed、ambiguous 或 observable inconsistent state：BLOCK，不降級為 fresh、不隱式修復。
- marker missing 且其他 evidence 存在、receipt missing 且其他 evidence 存在、partial tampering：BLOCK。
- receipt 明確記錄 artifact 而該 artifact deleted：BLOCK；missing 不等於 never managed。

保護 ordinary mistakes、partial deletion/tampering、observable inconsistent state。所有 evidence 都在同權限可寫範圍，不能提供 tamper-proof 保證。complete erasure 或一致偽造所有 evidence，且 observable state 與 genuine fresh state 完全相同，屬 **outside v2 threat model**。此 boundary 不能擴大為 partial-state bypass。

普通 `--init` 不兼作 repair。未來 repair/restore-managed 必須另行 explicit design 與 James 批准。

## Mutation-scope 與 ordinary source

ordinary source 的 dirty、staged、deleted、untracked 狀態均 **REPORT, not automatically BLOCK**，前提為 git-init 不 owns、不 intends to mutate 該 path，無 bootstrap conflict，且 scanner 無風險。不得改 source、format、restore deleted source、stage/unstage/restage 或修改 index。使用者正常 source development 不要求 whole working tree clean。

managed directory **!= ownership of every child**。例如 `.githooks/commit-msg` 可為 managed；`.githooks/unmanaged.txt`、`.githooks/pre-commit` 若不在管理契約中，仍為 unmanaged/user-owned。新增、修改、刪除這些 unrelated children 不應單獨 BLOCK，不改寫、不恢復。candidate 本身與妨礙其安全建立的 ancestor/descendant/type conflict 仍受保護。

## Secret scanner

Scanner 是 independent safety layer；ordinary source 即使在 mutation scope 外，secret-risk 仍可 BLOCK。輸出只列 file/risk category 與摘要，credential/token/private material 必須 redacted；remote userinfo/query/fragment 不原樣輸出。production 無 general bypass 或 `--skip-secret-scan`。fake-secret fixtures 只能由 isolated harness 建立，仍使用相同 scanner 驗證 BLOCK/no leak/no mutation，不因放在 tests directory 而免掃描。PASS 僅表示目前規則未偵測到風險，不代表 repository 絕對沒有 secrets。

## Git / GitHub invariants

- preserve existing history、refs、index、remote 與 local identity；不得 reset/rebase/amend/force 或任意移動 refs。
- 既有 repository-local identity 優先；缺少時只能用 James 明確批准的 input，否則 BLOCK。global identity 可分開唯讀回報，不得默默複製或當成 project 授權。
- no global Git mutation；hooks/template/config 優先 repository-local；工具不自動安裝 package 或改 system config。
- no automatic stage、commit、push、GitHub repository creation、gh login 或 remote mutation。
- 允許明確建立尚不存在且符合 branch plan 的 refs，不改既有 refs；若既有 ref 與要求衝突則 BLOCK。

| Branch | Purpose |
|---|---|
| main | stable |
| docs | documentation |
| develop | integration |
| feat | feature development |

新 repository 無 valid baseline 時保持 unborn branch，無法安全建立全部 refs 就 defer until valid baseline exists。既有符合預期的 refs 視為 satisfied/no-op；不得 delete/recreate/reset/move 來假裝 idempotent。merge 需 James 另行明確批准。

## Roles 與 Approval Gates

James → ChatGPT Work（Supervisor / validation / permission gate）→ OpenClaw（Planner）→ Hermes + OMH（Builder）。角色及可用工具不等於 mutation authorization；OMH 的可用性/能力須實際確認，不因列出角色而自動安裝或啟動。

1. Validation Gate：Work independent static/runtime/fixture tests；Agent 自述不能取代驗證。
2. Human Acceptance Gate：James 明確人工驗收 PASS；Work validation PASS 不代表 Human PASS。
3. Commit Gate：James Human PASS 與 local commit 授權後，Work Final Gate 檢查 status、diff/staged content、branch、secrets-risk、unexpected files、實際 commit message；新 source difference 不受舊 PASS 涵蓋。
4. Push Gate：commit ≠ push；push 需 James 另外明確批准。merge/release/deployment/force 也需各自批准。

一個 Gate 的批准不得自動批准下一個。Conventional Commit 使用允許 type（feat/fix/refactor/docs/test/chore/style）、scope、繁體中文 subject/body；machine format validation 不能判斷 Human PASS、文意或變更真實性。FAIL 停止，不無限自動 retry。

## Superseded historical behavior

以下不再是有效 contract：

- “any dirty working tree → BLOCK”：已廢止，改用 artifact/path mutation scope；dirty 仍如實 report。
- “managed directory → every child managed”：不成立。
- “missing artifact → always recreate”：不成立；CREATED/PRESERVED deleted 與 never managed missing 必須區分。
- “PRESERVED content must match template”：不成立；使用者內容 preserve，deleted 才 BLOCK。

## Validation checkpoint

目前 suites 僅驗證契約，不提供 commit/push 授權。consolidated checkpoint 即使全 PASS，也不是 git-init v2 Final E2E PASS；Existing Git/User-owned/Failure-path E2E、Final regression 與 James Human Acceptance 必須各自完成。

## Approved root dependency scan policy

僅 project root 的 `node_modules` 使用此專用 policy，沒有 CLI bypass。
若該 path 存在，必須是 physical directory（不可 symlink／一般檔案），必須在既有
Git repository 被 Git ignore，且 index 不可有該 path 或其 descendants 的 tracked
contents；無法確認以上條件即 RISK/BLOCK。non-Git project 有 root dependencies 時
亦 fail closed。工具不安裝、不改 ignore、不 untrack dependencies。

Root dependency content 不走 generic content scanner（包含 binary、large files 與
套件文件中的 secret-like examples），但整棵樹仍檢查 high-risk filenames，包含
`.env*`、credential、secret、private key、id_rsa、pem/key/p12/sqlite/sql 等；
大小寫不影響此專用檔名檢查。特殊檔案及 traversal errors 也 BLOCK。
只有直接位於 physical `node_modules/.bin` 的 symlink，且完整解析後為 root
`node_modules` 內 existing regular file，才接受。其他位置、directory target、
external（即使在 project 內）、broken、cycle links 一律 BLOCK。
不跟隨 dependency directory links。root `node_modules` 的所有 descendants（含 transitive `node_modules`）使用 dependency policy；
root subtree 以外的 nested `node_modules` 與普通 source 仍走原有
完整 generic scanner（任何 traversal error 均 fail closed）；測試資料沒有免掃描資格。

存在 root dependencies 時，需要可用的 Python 3.9+ validator，以及 physical、可讀、
不超過 1 MiB 的 `package.json`／`package-lock.json`。JSON 重複 keys、錯誤型別、
缺少 packages/root entry 或非 lockfileVersion 2/3 均 BLOCK。manifest 的
 dependencies/devDependencies/optionalDependencies 必須與 lock root 完全一致；
直接 dependency 必須 pin exact SemVer 2.0 version（core/prerelease numeric identifiers 不可有 leading zero） 並與對應 package entry version
一致。每個非 root package entry 必須是 node_modules 內合法 path、非 link entry，
含 exact SemVer 2.0 version、HTTPS resolved URL（port 若存在須為 1–65535）（無 userinfo，包括 encoded userinfo；無 query、
fragment 或控制字元）及有效 sha256/sha384/sha512 SRI base64 digest，長度需符合
演算法。無法讀取或驗證即 BLOCK，輸出僅 risk category，不印 metadata／credential。
此驗證檢查 metadata 結構，不驗證 downloaded bytes 或 registry provenance。

## Level 3 Composer root vendor policy

Only project-root `vendor` qualifies. It must be a physical directory in an
existing Git repository, ignored by Git and contain no indexed files (including
staged additions). No install, ignore edits, untracking or CLI bypass occurs.
Python 3.9+ validates the entire tree: case-insensitive high-risk filenames use
the root node_modules rules; every symlink (including vendor/bin), special file
and traversal error blocks. Nested vendor outside this root uses the generic scanner.

Content is excluded from the generic scanner only after all vendor checks pass.
`composer.lock`, `vendor/composer/installed.json` and `installed.php` must be
physical readable regular files, with physical ancestors, at most 1 MiB each.
JSON duplicate keys and malformed structures block. Lock packages/packages-dev
must have unique safe Composer names and nonempty versions; installed packages
must equal either production packages or all locked packages. Installed JSON
supports the legacy package list or Composer 2 packages/dev object. Versions and
source/dist metadata must match the lock. Installed PHP is parsed as a restricted
literal returned array (array()/[], strings, integers, booleans, null,
__DIR__, dirname and concatenation); PHP is never executed. Its root/versions
ledger must contain exactly the installed packages plus the project root;
pretty versions, optional normalized versions and source/dist references must
agree. Every present JSON `version_normalized` and every installed package PHP
`version` must independently be a nonempty string in the supported normalized
output grammar, before equality can authorize the vendor exemption. Invalid values
(including null, non-string types, non-normalized spellings and control characters)
emit only `vendor Composer normalized version invalid`. Validate lock entries even
when dev packages are not installed; optional JSON fields do not bypass PHP validation.
Accept four-part classical versions with preserved zero padding; date/time numeric
outputs; canonical alpha/beta/RC/patch modifiers with compound numeric
identifiers and optional -dev; four-part numeric dev branches (9999999 wildcards),
legacy `9999999-dev`, and nonempty `dev-` branch names, preserving case, slash,
plus, internal spaces and comparison characters. Reject surrounding whitespace
and control characters conservatively. This validates representation and existing
metadata equality; it does not derive normalized values from pretty versions.

Official source pin (authorized normalized-version fix): Composer **2.10.3**
[`composer.lock`](https://github.com/composer/composer/blob/2.10.3/composer.lock)
resolves **composer/semver 3.4.4**, commit
`198166618906cb2de69b95d7d47e5fa8aa1b2b95`.
Composer's [Package VersionParser](https://github.com/composer/composer/blob/2.10.3/src/Composer/Package/Version/VersionParser.php)
extends `Composer\Semver\VersionParser` without overriding normalization.
The custom policy is corpus-verified against the pinned [upstream parser](https://github.com/composer/semver/blob/198166618906cb2de69b95d7d47e5fa8aa1b2b95/src/VersionParser.php)
(`normalize`, `normalizeBranch`, `normalizeDefaultBranch`, `expandStability`) and
[upstream tests](https://github.com/composer/semver/blob/198166618906cb2de69b95d7d47e5fa8aa1b2b95/tests/VersionParserTest.php)
(`successfulNormalizedVersions`, `successfulNormalizedBranches`, rejection cases).
The complete successful normalized-version and branch providers are statically
extracted into `tests/corpus/normalized-outputs.json` with source SHA-256 verification
(see `tests/corpus/README.md`). Every output is tested against the local policy.
Lowercase numeric `-stable` is an input spelling: upstream returns the numeric
base, so the policy rejects that spelling as a normalized numeric output.
Changed input spellings are not broadly rejected; arbitrary `dev-` names remain
accepted. This custom policy is corpus-verified, not claimed equivalent to the
upstream parser or its entire possible output language;
no PHP or upstream code executes during policy validation.

In both lock and installed JSON, source/dist references must be strings or
null (missing/empty means absent); validate both types before PHP parsing and
source-over-dist selection. Invalid types emit only the risk category
`vendor Composer reference type invalid`, even with matching installed PHP values
or a valid source and invalid dist. Non-metapackage install paths in both installed
files must resolve to the same existing directory strictly inside root vendor; metapackages have null paths.
Unsupported executable/dynamic PHP, virtual-only ledger entries and ambiguous
metadata fail closed. This validates metadata consistency, not downloaded bytes
or package provenance. Risk output contains categories, never metadata values.

`tests/vendor.py` creates isolated fixtures and checks check/dry-run/init rejection,
redaction and unchanged files/index/config/refs. It covers valid ignored content,
unignored/tracked/staged vendor, root types, symlinks/path escapes, risky names,
special files, traversal failures, metadata mismatches, executable PHP rejection,
ordinary source secrets and nested vendor. `tests/run.sh` runs this alongside
`dependencies.py`, preserving the node_modules regression coverage.
