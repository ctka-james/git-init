# 測試說明

行為契約以 `../GIT-INIT-V2-SPEC.md` 為準；本文件不構成任何 Gate 授權。

`run.sh` 使用隔離 fixture，不修改真 HOME 或 global Git config：

    GIT_CONFIG_GLOBAL=<fixture file>
    GIT_CONFIG_SYSTEM=/dev/null
    GIT_CONFIG_NOSYSTEM=1

只允許 fixture 的 `git add`/`git commit` 來建立既有 baseline 情境；不會對正式副本執行任何 Git mutation。測試同時驗證 fake `npm`、`npx`、`gh`、`curl` 無呼叫，並涵蓋 empty/source/repo/identity/remote/secret/Unicode/dirty/ref/config/hook/partial state 等安全邊界。

`commitlint-real.sh` 不安裝依賴。若批准的 Work 尚未建立 `node_modules`，它會以 SKIP 結束；完成 project-local install 後會測真實 commitlint 的 type、scope、header、leading blank、body 與 Unicode。

`receipt.py` 以五個 candidate path 驗證 ledger-authoritative ownership：`PRESERVED` 的既有內容變更（含 tracked）為 PASS/no-op，但該 path 遭刪除時會在任何 mutation 前 BLOCK，且 receipt、marker、config、refs 與 index 維持不變。`CREATED` 的修改或刪除仍為 BLOCK。普通 unrelated source 的 dirty/staged/deleted/untracked 狀態只 report；若無 bootstrap conflict 或 scanner risk，rerun PASS 且 source、index、refs、config 不變。

## Controlled-secret fixture：隔離測試與 scanner 邊界

Fake private-key headers、credential URLs 與 token-like values 都是測試資料，僅在 isolated fixture／test harness 中產生。Scanner 仍應偵測這些 pattern；harness 以「預期 BLOCK、沒有 mutation、輸出不洩漏值」作為測試 PASS，而不是略過掃描。

Fixture mechanism 只服務隔離測試，不得提供 production `--skip-secret-scan` 或 general scanner bypass。一般 project source 出現相同 pattern 時，`--init` 仍必須 BLOCK；把資料放進 `tests/fixtures` 或標記為 fake 不能繞過 scanner。

Scanner PASS 只表示目前規則沒有偵測到風險，不代表 repository 絕對沒有 secrets。測試不得印出完整 credential、token 或 private-key value。
