# Git Init

一個快速初始化 Git Repository 的 Shell Script。

此工具可自動完成 Git Repository 初始化、建立 `.gitignore`、建立第一次 Commit，並建立符合團隊開發流程的分支，避免每次建立新專案都要重複相同的設定。

## 功能特色

執行一次即可完成以下工作：

- 初始化 Git Repository
- 預設主要分支為 `main`
- 自動建立標準 `.gitignore`
- 建立第一次 Commit (`Initial commit`)
- 建立 `doc` 分支
- 建立 `develop` 分支
- 建立 `feat` (Feature) 分支
- 自動切換至 `feat`
- 顯示目前所有 Branch
- 顯示目前 Git Global 設定

### 建立的 Branch

```text
main
├── docs
├── develop
└── feat   (目前所在分支)
```

初始化完成後，目前工作分支會停留在：

```text
feat
```

方便直接開始開發新功能。

## 安裝方式

1. 建立腳本

   建立 `/usr/local/bin/git-init`

   ```bash
   sudo vim /usr/local/bin/git-init
   ```

   將 Shell Script 內容貼上。

2. 加入執行權限

   ```bash
   sudo chmod +x /usr/local/bin/git-init
   ```

3. 確認 PATH

   確認 `/usr/local/bin` 已存在 `PATH`

   ```bash
   echo $PATH
   ```

   若看到：

   ```text
   /usr/local/bin
   ```

   即可直接使用。

4. 確認安裝成功

   ```bash
   which git-init
   ```

   應看到：

   ```text
   /usr/local/bin/git-init
   ```

5. 使用預設的 commit message

   ```bash
   cp .gitmessage ~/.gitmessage
   git config --global commit.template ~/.gitmessage
   ```

## 使用方式

1. 切換到欲建立 Git Repository 的專案目錄

   ```bash
   cd my-project
   ```

2. 執行

   ```bash
   git-init
   ```

   即可完成所有初始化流程。

## 執行流程

程式依序執行：

1. 檢查目前目錄是否已有 Git Repository
2. `git init -b main`
3. 建立 `.gitignore`
4. `git add .`
5. `git commit -m "Initial commit"`
6. 建立 `develop`
7. 建立 `feat`
8. 切換至 `feat`
9. 顯示目前 Branch
10. 顯示 Git Global Config

## 自動建立的 `.gitignore`

包含下列常見忽略項目：

- macOS
- Windows
- VS Code
- JetBrains IDE
- Log Files
- Temporary Files
- Composer
- Node.js
- Environment Variables
- Vim Swap Files

內容包含：

```gitignore
.DS_Store
Thumbs.db
.vscode/
.idea/
*.log
tmp/
temp/
vendor/
node_modules/
.env
.env.*
*.swp
*.swo
```

## 執行結果範例

```text
====================================
 Git Repository Initialization
====================================

▶ Initializing Git...
Initialized empty Git repository

▶ Creating .gitignore...

▶ Creating first commit...
[main (root-commit)] Initial commit

▶ Creating development branch...

====================================
 Repository Created Successfully
====================================

  docs
  develop
* feat
  main

====================================
 git config --global --list
====================================

user.name=Your Name
user.email=your@email.com
init.defaultbranch=main
```

## 注意事項

第一次使用 Git 前，請先設定使用者資訊：

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

建議同時設定 Git 預設主分支為 `main`：

```bash
git config --global init.defaultBranch main
```

## 適用環境

- Linux
- Ubuntu
- Debian
- Kali Linux
- Hestia Control Panel
- Bash Shell
- Git 2.28 以上（支援 `git init -b main`）

## License

MIT License
