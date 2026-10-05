# Work Project Bootstrap SOP

行為契約以 `GIT-INIT-V2-SPEC.md` 為準；本文件不構成任何 Gate 授權。

此 SOP 適用未知專案與 production-adjacent 專案。M6 與 PROD 必須分開記錄；沒有實際 task 時不得造成 drift。`git-init` 只提供 machine preflight，不能取代 James HumanGate。

## 1. Environment

記錄 host、user、OS、architecture、project path、runtime 版本、sandbox write 範圍與 network policy。不得假設其他主機的路徑、版本、權限或登入狀態相同；token 僅可報存在與否。

## 2. Project

辨識專案類型、framework、tree、相依套件、runtime、test/build 指令與 production/development 用途。未收到實際 task 不得修改 source。

## 3. Agents

確認 agents availability、version 與 invocation strategy：Hermes 使用 `hermes --oneshot "<核准 scope task>"`；OpenClaw 使用 `agent exec --json`。tools、rules、AGENTS.md 與 approval 邊界仍生效；oneshot 自己的 approval bypass 不等於 James 授權。Work 的 filesystem/network permissions 才是真實邊界。每個 agent 都須明確列出 scope、filesystem、network 權限；不能假設同一台主機或共用路徑。

PROD policy：先唯讀 discovery、最小權限、mutation 前先確認 rollback；不得自動安裝套件、重啟 service、commit、push、deploy 或觸碰 production data。M6 仍須 James HumanGate。

## 4. Git

先唯讀確認 repo/worktree/bare/nested 狀態、HEAD/branch/status/conflicts/refs/remotes、local identity、ignore、secret risk、hooks/template/config。所有 blocker 必須在 mutation 前處理；禁止 add、commit、push、checkout、merge、rebase、reset、clean、fetch 或 force。

## 5. GitHub

確認本機 `gh` metadata、remote、visibility、default branch 與 auth evidence。預設不得網路呼叫；無法離線確認即記錄 `UNKNOWN`。不得 create repo、push 或改 remote。

## 6. Workflow

固定順序：OpenClaw → WorkReview → Hermes → WorkValidation → JamesHumanValidation。新 source 差異不受舊 PASS 涵蓋。commit 與 push 是獨立批准；FAIL 立即停止，無自動 retry。

## 7. Ready

只有 Work 在七階段均完成且無 blocker 時，才能記錄 `PROJECT READY`。摘要必須包含 Environment、Project、Agents、Git、GH、Permissions、Outstanding blockers。任何 BLOCK 都不得標示完全 READY；`PREFLIGHT_OK` 只表示 machine preflight 沒有已知 blocker。
