# git-init v2

行為契約以 `GIT-INIT-V2-SPEC.md` 為準；本文件不構成任何 Gate 授權。

`git-init` 是 Git／GitHub bootstrap layer。預設為唯讀 preflight，僅在明確指定 `--init`、所有 machine blocker 清除且 Human 已同意時，才寫入目標專案的 local Git 設定與受管理檔案。

它不取代 WorkSupervisor、WorkReview、WorkTests、James Human PASS 或 FinalGate。

## 安全邊界

- 無參數等同 `--check`；不寫檔、不初始化、不連網。
- 可唯讀回報 global Git identity，絕不修改 global identity、hooks、template、editor 或 npm。
- 不呼叫 npm、npx、curl、gh auth status、GitHub API，也不建立 remote。
- 永不執行 add、commit、push、checkout、merge、rebase、reset、clean、fetch 或 force。
- 不會自行建立 baseline commit；baseline 前只建立 unborn `main`，並輸出 `BRANCH_CREATION_DEFERRED`。
- Human PASS、local commit approval、push approval 是三個獨立 gate；工具不可偽造或推論任何一項。

## 使用

從要 bootstrap 的目標專案根目錄執行（腳本可位於另一個含資源檔的目錄）：

    /path/to/git-init --check
    /path/to/git-init --dry-run
    /path/to/git-init --init --user-name '明確提供的名稱' --user-email 'name@example.test'

`--init` 僅接受非空、無控制字元的 identity，並只寫 `git config --local user.name/user.email`。email 僅作結構檢查，不驗證所有權。既有 repo 的 local identity 已存在時，仍可明確提供同一組值；本工具不自 global identity 補值。

## 模式與 exit code

| 模式 | 行為 |
| --- | --- |
| `--check` / 無參數 | 完整唯讀 preflight。 |
| `--dry-run` | 走相同判斷，列出預計的 `--init` 工作，不寫入。 |
| `--init` | 僅在 preflight 無 blocker 時寫入 project-local 成果。 |

| Code | 意義 |
| ---: | --- |
| 0 | 成功完成，或唯讀盤點無 blocker。 |
| 2 | CLI 或 identity 格式錯誤。 |
| 3 | prerequisite/blocker；未 mutation。 |
| 4 | secrets、symlink、未掃描檔案等安全風險；未 mutation。 |
| 5 | 既有 Git/config/ref/managed-file 衝突；未覆寫。 |
| 6 | mutation 開始後失敗；保留現況，交由 Work/James recovery。 |
| 10 | 測試失敗（測試 harness 使用）。 |

## Preflight

輸出只列 machine 觀測：Git 版本、路徑可寫性、repo 型態、local identity 是否存在、remote 的遮蔽 URL、refs、`.gitignore`、managed-file/config 衝突、secret-risk heuristics、`gh` binary metadata 與 `GH_TOKEN` 是否存在。

- global identity 與 local identity 分開唯讀回報；不讀出 token 值，不修改 global config。
- 不執行 `gh auth status`；offline 時 authentication 永遠是 `UNKNOWN`。
- remote URL 不顯示 userinfo、query 或 fragment。
- scanner 不輸出疑似 secret 的內容；它不是安全保證。疑似值、疑似檔名、二進位檔案、大於 1 MiB 的檔案、symlink 或掃描錯誤均會阻擋 `--init`。
- `.git` gitfile/worktree、bare repo、`.git` symlink 與 nested repo 一律僅唯讀說明，不寫外部 Git directory。

`.gitignore` 已存在時永不變動。非空 non-Git 目錄缺少它會阻擋；空目錄的 `--init` 可產生下列候選，仍必須由 Work review，且不代表 staging 或提交授權：

    node_modules/
    *.log
    tmp/
    temp/
    .env
    .env.*
    .DS_Store
    Thumbs.db
    .vscode/
    .idea/

候選刻意不忽略 `*.php`、`*.js`、`*.md` 或其他可能是 source 的泛用檔案。

## Project-local 產物

`--init` 只會建立不存在且未衝突的項目：

- `.gitignore`（僅空目錄）
- `.gitmessage`（只有註解指引，不含可誤提交 header）
- `commitlint.config.cjs`
- `.githooks/commit-msg`
- `AI-WORKFLOW.template.md`
- local `core.hooksPath=.githooks`
- local `commit.template=.gitmessage`

既有 candidate file 會 preserve，絕不覆寫或以 template bytes 採用；不相容的兩個 local config key 仍會在 mutation 前以 conflict 停止。寫入檔案使用同目錄 temporary file + rename。

## Bootstrap trust receipt

首次成功初始化會寫入 repository-local `.git/git-init-v2-receipt` 與
`.git/git-init-v2-receipt.sha256`。receipt 是 versioned complete ledger：每個已知
candidate path 都有 `CREATED` 或 `PRESERVED` disposition；marker 覆蓋整份 ledger。
僅本次建立的 `CREATED` path 會檢查 template hash，且被刪除或修改時一律 conflict，
不會 restore。既有檔案（即使 bytes 與 template 相同）永遠記為 `PRESERVED`；其後即使
內容已修改仍維持 preserve，只有刪除或非一般檔案才會 conflict。普通、不相干的 tracked
或 untracked source 仍如實回報為 dirty，但不會單獨阻止本工具，因為工具不擁有或修改它們。
candidate 本身及其祖先／子孫型別衝突仍在 mutation scope 內，會接受 receipt 與型別檢查。

receipt、marker、bootstrap local config 或 recognized metadata 只要部分存在、不一致、
遺失、legacy 或格式錯誤，就在任何 mutation 前 fail closed；正常 `--init` 不會重建
marker、receipt row 或 managed file。只有所有可觀測 bootstrap evidence 都消失且狀態
確實等同 fresh 時，v2 沒有歷史偵測保證；這是 complete-erasure、範圍外情境，不是
partial-state 例外或 scanner bypass。

Hook 只會呼叫 `./node_modules/.bin/commitlint --config ./commitlint.config.cjs --edit "$1"`。本機 executable 缺失時 fail closed；不會使用 npx、下載或 global fallback。`package.json` pin 了 `@commitlint/cli` 與 `@commitlint/config-conventional` 21.2.3，但本工具不安裝相依套件或生成 lockfile；此 repository 已有測試依賴 lockfile。依 James 批准的 Work 流程以 project-local、無 scripts/audit/fund 的安裝完成前，不得宣稱 commitlint integration 已完成。

規則要求允許的 type、非空 scope、非空 subject、header 後空行與非空 body；`subject-case` 關閉以支援 Unicode／繁中，`defaultIgnores: false` 使 merge/revert 等訊息不會 silent bypass。格式驗證不能判斷繁中文意、描述真實性或 James PASS。

## Branch defer 與既有 repo

新 repo 的 `git init -b main` 不會產生 commit，所以只能有 unborn `main`。Baseline local commit 取得 James 明確批准後，才可明確重新執行 `--init`。

既有 repo 在 HEAD 有效且無 ref name/path collision 時，從目前 `HEAD` 建立缺少的 `docs/develop/feat`；已存在且符合 baseline 的 branch 視為 satisfied/no-op，衝突時 BLOCK，不移動既有 refs。普通、不相干 source 的 dirty 狀態不會單獨阻止 branch 計畫，因為本工具不修改那些路徑；bootstrap candidate 的 receipt、型別、部分或模糊狀態則仍會在 mutation 前 fail closed。它不改 HEAD、upstream、remote、既有 ref 或 default branch。

發生 partial failure 時，工具會回報已完成 mutation，並以 code 6 結束；它不會刪除 `.git`、reset、clean 或清除使用者資料。下一步是先 `--check`，由 Work/James 判讀 recovery；普通 `--init` 不會隱式 repair 不一致 state。

## 七階段 Work SOP

詳見 `WORK-PROJECT-BOOTSTRAP.md`。摘要如下：

1. Environment：確認 host/user/OS/arch/path/runtime、可寫範圍、sandbox 與 network policy。
2. Project：確認 type/framework/tree、依賴、test/build、prod/dev；無 task 不改 source。
3. Agents：確認 OpenClaw/Hermes command/version/invocation 與 one-shot 邊界；不得自行擴權或開 agent。
4. Git preflight：repo/worktree/status/refs/remotes、identity、ignore、secrets、hooks/template；blocker 必須在 mutation 前排除。
5. GitHub：auth、remote、visibility、default branch 預設 offline；無法離線確認即 `UNKNOWN`。
6. Workflow gates：Planner → WorkReview → Hermes → WorkTests → James PASS → FinalGate；commit/push 分別批准；FAIL 停止。
7. Ready：僅 Work 可在全檢無 blocker 後宣告 `PROJECT READY`；本工具最多輸出 `PREFLIGHT_OK`。

## 測試

    bash -n git-init
    bash tests/run.sh
    bash tests/commitlint-real.sh

`tests/run.sh` 只建立隔離 fixture，透過 `GIT_CONFIG_GLOBAL`、`GIT_CONFIG_SYSTEM=/dev/null`、`GIT_CONFIG_NOSYSTEM=1` 避免使用真 global 設定；temporary fixture commit 僅用於測試 baseline。它 mock network/npm/npx 路徑並驗證無呼叫。`tests/commitlint-real.sh` 在 `node_modules` 不存在時明確 SKIP，不會安裝；Work 安裝批准相依套件後，該測試會執行真實 commitlint parser/header/body/Unicode 案例。

## Breaking changes

v2 刻意移除舊版自動 global npm install、global Git config、identity prompt、`.gitignore` 覆寫、auto add/commit/checkout、baseline 前 branch 建立及全域 hook/template/editor 行為。已依賴 global hooks 的專案不會被自動遷移。這些改變是安全邊界，不是回歸缺陷。
