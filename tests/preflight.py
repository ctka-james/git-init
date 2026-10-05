#!/usr/bin/env python3
"""Direct read-only preflight contract tests for git-init."""
import hashlib
import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "git-init"
PASS = 0


def check(condition, label):
    global PASS
    if not condition:
        raise AssertionError(label)
    PASS += 1
    print(f"PASS: {label}")


def run(directory, global_config, path=None):
    env = os.environ.copy()
    env.update({"GIT_CONFIG_GLOBAL": str(global_config), "GIT_CONFIG_SYSTEM": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1"})
    if path is not None:
        env["PATH"] = path
    before = tree_snapshot(directory / ".git") if (directory / ".git").is_dir() else None
    result = subprocess.run([str(SCRIPT), "--check"], cwd=directory, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    after = tree_snapshot(directory / ".git") if (directory / ".git").is_dir() else None
    check(before == after, f"read-only audit: {directory.name}")
    return result.returncode, result.stdout


def tree_snapshot(root):
    if not root.exists():
        return None
    result = []
    for path in sorted(root.rglob("*")):
        info = path.lstat()
        if path.is_file():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        elif path.is_symlink():
            digest = os.readlink(path)
        else:
            digest = ""
        result.append((str(path.relative_to(root)), stat.S_IFMT(info.st_mode), info.st_mode & 0o7777, info.st_size, info.st_mtime_ns, digest))
    return result


def git(directory, *args, env):
    subprocess.run(["git", "-C", str(directory), *args], check=True, env=env, stdout=subprocess.DEVNULL)


def setup_repo(base, name, env):
    directory = base / name
    directory.mkdir()
    git(directory, "init", "-q", "-b", "main", env=env)
    git(directory, "config", "--local", "user.name", "Fixture User", env=env)
    git(directory, "config", "--local", "user.email", "fixture@example.test", env=env)
    (directory / "tracked.txt").write_text("baseline\n")
    git(directory, "add", "tracked.txt", env=env)
    git(directory, "commit", "-qm", "test(fixture): baseline", "--no-verify", env=env)
    return directory


def expect(output, *lines):
    for line in lines:
        check(line in output, f"report contains {line}")


def main():
    with tempfile.TemporaryDirectory(prefix="git-init-preflight-") as temp:
        base = Path(temp)
        global_config = base / "global.gitconfig"
        global_config.touch()
        env = os.environ.copy()
        env.update({"GIT_CONFIG_GLOBAL": str(global_config), "GIT_CONFIG_SYSTEM": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1"})

        # 1: non-Git; 2: clean Git; 3: dirty Git.
        non_git = base / "non-git"; non_git.mkdir()
        rc, out = run(non_git, global_config)
        check(rc == 0, "non-Git check succeeds")
        expect(out, "GIT_REPOSITORY: no", "CURRENT_BRANCH: none; state=unavailable", "WORKTREE_STATUS: NO_REPO", "REMOTES: none")
        clean = setup_repo(base, "clean", env)
        rc, out = run(clean, global_config)
        check(rc == 0, "clean Git check succeeds")
        expect(out, "GIT_REPOSITORY: yes", "CURRENT_BRANCH: main; state=existing", "WORKTREE_STATUS: clean", "REMOTES: none")
        (clean / "tracked.txt").write_text("dirty\n")
        rc, out = run(clean, global_config)
        check(rc == 0 and (clean / "tracked.txt").read_text() == "dirty\n", "ordinary dirty Git check succeeds without changing source")
        expect(out, "WORKTREE_STATUS: dirty")

        # 4: local identity set/unset; 5: isolated global identity set/unset.
        identity = setup_repo(base, "identity", env)
        rc, out = run(identity, global_config)
        expect(out, "LOCAL_IDENTITY: present (redacted)", "Local Git user.name: set (redacted)", "Local Git user.email: set (redacted)", "GLOBAL_IDENTITY: unset")
        git(identity, "config", "--local", "--unset", "user.name", env=env)
        git(identity, "config", "--local", "--unset", "user.email", env=env)
        git(base, "config", "--global", "user.name", "Global Fixture", env=env)
        git(base, "config", "--global", "user.email", "global@example.test", env=env)
        rc, out = run(identity, global_config)
        expect(out, "LOCAL_IDENTITY: unset", "Local Git user.name: unset", "Local Git user.email: unset", "GLOBAL_IDENTITY: present (redacted)", "Global Git user.name: set (redacted)", "Global Git user.email: set (redacted)")

        # 6: no, normal, credential, and multiple remotes.
        remotes = setup_repo(base, "remotes", env)
        git(remotes, "remote", "add", "origin", "https://example.test/path", env=env)
        git(remotes, "remote", "add", "private", "https://user:password@example.test/private?token=hidden", env=env)
        rc, out = run(remotes, global_config)
        check(rc == 0, "remote fixture check succeeds")
        expect(out, "REMOTES: 2", "REMOTE: origin https://example.test/path", "REMOTE: private https://example.test/private")
        check("password" not in out and "token=hidden" not in out, "credential remote is redacted")

        # 7: hooks absent/present/configured missing.
        hooks = setup_repo(base, "hooks", env)
        rc, out = run(hooks, global_config)
        expect(out, "HOOKS: hooksPath not configured; effective path present", "HOOK_COMMIT_MSG: absent")
        hook_file = hooks / ".git" / "hooks" / "commit-msg"
        hook_file.write_text("#!/bin/sh\nexit 0\n"); hook_file.chmod(0o755)
        rc, out = run(hooks, global_config)
        expect(out, "HOOK_COMMIT_MSG: present; executable")
        git(hooks, "config", "--local", "core.hooksPath", "missing-hooks", env=env)
        rc, out = run(hooks, global_config)
        expect(out, "HOOKS: hooksPath configured; effective path absent", "HOOK_COMMIT_MSG: absent")

        # 8: templates absent/present/configured missing.
        templates = setup_repo(base, "templates", env)
        rc, out = run(templates, global_config)
        expect(out, "COMMIT_TEMPLATE: not configured; file absent")
        (templates / "message.txt").write_text("template\n")
        git(templates, "config", "--local", "commit.template", "message.txt", env=env)
        rc, out = run(templates, global_config)
        expect(out, "COMMIT_TEMPLATE: configured; file present")
        git(templates, "config", "--local", "commit.template", "missing.txt", env=env)
        rc, out = run(templates, global_config)
        expect(out, "COMMIT_TEMPLATE: configured; file absent")

        # 9: commitlint unavailable/config-only; 10: GH unavailable.
        optional = setup_repo(base, "optional", env)
        (optional / "commitlint.config.cjs").write_text("module.exports = {}\n")
        no_gh_bin = base / "bin"; no_gh_bin.mkdir()
        for command in ("bash", "git", "whoami", "hostname", "uname", "find", "grep", "wc", "od", "readlink", "awk", "dirname", "pwd", "cut", "cmp", "sha256sum"):
            os.symlink(shutil.which(command), no_gh_bin / command)
        rc, out = run(optional, global_config, str(no_gh_bin))
        check(rc == 5, "optional tools unavailable retain existing conflict exit")
        expect(out, "COMMITLINT: executable unavailable", "COMMITLINT_CONFIG: present", "GH: unavailable", "GITHUB_AUTH: UNKNOWN")

        # 11: secret fixture and 12: all stable top-level keys.
        secret = base / "secret"; secret.mkdir()
        (secret / "config.env").write_text("token=temporarysecretvalue123\n")
        rc, out = run(secret, global_config)
        check(rc == 4, "secret fixture retains risk exit")
        expect(out, "RISK_SUMMARY: 1 risk(s) detected by current rules (RISK)")
        check("temporarysecretvalue123" not in out, "secret fixture value is not rendered")
        for key in ("WHOAMI:", "HOSTNAME:", "OS:", "ARCH:", "CURRENT_DIRECTORY:", "GIT:", "GIT_REPOSITORY:", "CURRENT_BRANCH:", "WORKTREE_STATUS:", "REMOTES:", "LOCAL_IDENTITY:", "GLOBAL_IDENTITY:", "GITIGNORE:", "HOOKS:", "COMMIT_TEMPLATE:", "COMMITLINT:", "GH:", "GITHUB_AUTH:", "RISK_SUMMARY:"):
            check(key in out, f"stable key {key}")

    print(f"RESULT: {PASS} passed, 0 failed")


if __name__ == "__main__":
    main()
