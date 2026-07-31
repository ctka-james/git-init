# Git Init

一個快速初始化 Git Repository 的 Shell Script。

此工具可自動完成 Git Repository 初始化、建立 `.gitignore`、建立第一次 Commit，並建立符合團隊開發流程的分支，避免每次建立新專案都要重複相同的設定。

## 功能特色

執行一次即可完成以下工作：

- 初始化 Git Repository
- 預設主要分支為 `main`
- 自動建立標準 `.gitignore`
- 建立第一次 Commit (`Initial commit`)
- 全域安裝與設定 `commitlint`
- 建立 `commit-msg` Hook 驗證提交訊息
- 建立 `commit-template.txt` 範本
- 統一設定 `core.editor` 為 `vim`
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

   複製 `git-init` Shell Script 到 `/usr/local/bin/git-init`。
   
   ```bash
   cd git-init
   sudo cp git-init /usr/local/bin/git-init
   ```

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
   ```

   ```bash
   cp .vimrc ~/.vimrc
   ```

   ```bash
   git config --global commit.template ~/.gitmessage
   ```

## Commitlint 與 Commit Template 安裝與操作說明

`git-init` 會在初始化流程中自動完成下列設定，讓新建專案可以直接使用一致的提交規範。

### 1. 安裝 Commitlint

若系統尚未安裝 `npm`，請先安裝 Node.js 與 npm。

若尚未安裝 `commitlint`，執行以下指令：

```bash
npm install -g \
    @commitlint/cli \
    @commitlint/config-conventional
```

若已安裝 `commitlint`，腳本會直接跳過安裝流程。

### 2. 建立全域 Commitlint 設定

腳本會檢查是否已存在以下設定檔：

```bash
~/.config/git/commitlint.config.cjs
```

若尚未存在，會自動建立：

```js
module.exports = {
    extends: ['@commitlint/config-conventional']
};
```

### 3. 建立 `commit-msg` Git Hook

腳本會建立全域 hook 目錄：

```bash
mkdir -p ~/.config/git/hooks
```

並建立 `commit-msg` hook：

```bash
vim ~/.config/git/hooks/commit-msg
```

內容如下：

```sh
#!/bin/sh
commitlint --config ~/.config/git/commitlint.config.cjs --edit "$1"
```

最後設定執行權限：

```bash
chmod +x ~/.config/git/hooks/commit-msg
```

### 4. 設定 Git 使用全域 Hook

```bash
git config --global core.hooksPath ~/.config/git/hooks
```

### 5. 建立 Commit Template

腳本會將目前專案的 `.gitmessage` 複製到：

```bash
~/.config/git/commit-template.txt
```

並設定全域 commit template：

```bash
git config --global commit.template ~/.config/git/commit-template.txt
```

之後於執行 `git commit` 時，Git 會以 `vim` 開啟模板讓使用者依照格式撰寫提交訊息。

### 6. 設定 Git Editor

若尚未設定 `core.editor`，腳本會自動設定：

```bash
git config --global core.editor "vim"
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
