# AI 工作流程模板

git-init 行為契約以 git-init v2 工具 repository 的 `GIT-INIT-V2-SPEC.md` 為準；本文件不構成任何 Gate 授權。

本檔是 project-local 規範，不是 James 的 PASS、提交、推送、合併、部署或發版授權。

## 角色與 branches

- James：Human Final Approval。
- Work：Supervisor。
- OpenClaw：Planner。
- Hermes：Builder，one-shot，僅在核准 scope 內實作。
- branches：`main` stable、`develop` integration、`feat` feature development、`docs` documentation；不得用重設或移動既有 ref 偽造一致。

## 固定流程

`OpenClaw → WorkReview → Hermes → WorkValidation → JamesHumanValidation`。

James PASS 前不得 commit。任何新 source 差異都要重新驗收，不受先前 PASS 自動涵蓋。FAIL 必須停止；不得無限 retry，也不能用 approval file、環境變數、flag 或 agent 自述取代人工 gate。

## FinalGate

FinalGate 必須實際檢查：`git status`、diff、staged diff、branch、secret risk、unexpected files、測試結果，以及實際繁中 Conventional Commit subject/body/review。Commit 不等於 push；push 需 James 另一次明確批准。merge、deploy、release 與 force 一律需要各自單次明確批准。

繁中 Conventional Commit 使用 `type(scope): subject`，type 可用 `feat`、`fix`、`refactor`、`docs`、`test`、`chore`、`style`；header 後必須空行，body 以繁中描述變更、風險與驗證。

`LEARNING` 是可驗證的學習紀錄；`AIWORKFLOW` 是本規範。兩者分離，不能互相充當批准證據。
