#!/usr/bin/env python3
"""Receipt integrity and deleted-artifact contract tests for git-init."""
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "git-init"


def run(directory, env, *args):
    return subprocess.run(
        [str(SCRIPT), *args], cwd=directory, env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )


def git(directory, env, *args):
    return subprocess.run(
        ["git", "-C", str(directory), *args], env=env, check=True,
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )


def refs(directory, env):
    return git(directory, env, "show-ref").stdout


def local_config(directory, env):
    return (directory / ".git" / "config").read_bytes()


def index(directory):
    return (directory / ".git" / "index").read_bytes()


def setup(base, name, env):
    directory = base / name
    directory.mkdir()
    git(directory, env, "init", "-q", "-b", "main")
    git(directory, env, "config", "--local", "user.name", "Fixture User")
    git(directory, env, "config", "--local", "user.email", "fixture@example.test")
    (directory / "baseline.txt").write_text("baseline\n")
    git(directory, env, "add", "baseline.txt")
    git(directory, env, "commit", "-qm", "test(fixture): baseline", "--no-verify")
    result = run(directory, env, "--init")
    assert result.returncode == 0, result.stdout
    assert (directory / ".git" / "git-init-v2-receipt").is_file()
    assert (directory / ".git" / "git-init-v2-receipt.sha256").is_file()
    return directory


def blocked(directory, env, label):
    before_refs = refs(directory, env)
    result = run(directory, env, "--init")
    assert result.returncode == 5, f"{label}: {result.returncode}\n{result.stdout}"
    assert refs(directory, env) == before_refs, f"{label}: refs changed"
    print(f"PASS: {label}")


def main():
    with tempfile.TemporaryDirectory(prefix="git-init-receipt-", dir="/tmp") as temp:
        base = Path(temp)
        global_config = base / "global.gitconfig"
        global_config.touch()
        env = os.environ.copy()
        env.update({
            "GIT_CONFIG_GLOBAL": str(global_config),
            "GIT_CONFIG_SYSTEM": "/dev/null",
            "GIT_CONFIG_NOSYSTEM": "1",
        })

        unchanged = setup(base, "unchanged", env)
        before_receipt = (unchanged / ".git" / "git-init-v2-receipt").read_bytes()
        result = run(unchanged, env, "--init")
        assert result.returncode == 0, result.stdout
        assert (unchanged / ".git" / "git-init-v2-receipt").read_bytes() == before_receipt
        print("PASS: unchanged receipt is a no-op")

        # Fix4 exact regression: deleting a generated artifact, its ledger row,
        # and the marker is ambiguous bootstrap evidence, never a fresh init.
        fix4 = setup(base, "fix4-marker-missing", env)
        receipt = fix4 / ".git" / "git-init-v2-receipt"
        marker = fix4 / ".git" / "git-init-v2-receipt.sha256"
        (fix4 / ".gitignore").unlink()
        receipt.write_text("\n".join(
            line for line in receipt.read_text().splitlines()
            if "\t.gitignore\t" not in line
        ) + "\n")
        marker.unlink()
        before_config = local_config(fix4, env)
        before_refs = refs(fix4, env)
        before_index = index(fix4)
        result = run(fix4, env, "--init")
        assert result.returncode == 5, result.stdout
        assert "ambiguous/inconsistent" in result.stdout, result.stdout
        assert not (fix4 / ".gitignore").exists()
        assert not marker.exists()
        assert local_config(fix4, env) == before_config
        assert refs(fix4, env) == before_refs
        assert index(fix4) == before_index
        print("PASS: Fix4 deleted artifact plus missing row/marker blocks without restoration")

        # Latest ownership contract: a ledger-authorized PRESERVED artifact
        # remains user-owned after content edits, including when tracked.
        preserved = base / "preserved-identical-ignore"
        preserved.mkdir()
        git(preserved, env, "init", "-q", "-b", "main")
        git(preserved, env, "config", "--local", "user.name", "Fixture User")
        git(preserved, env, "config", "--local", "user.email", "fixture@example.test")
        (preserved / ".gitignore").write_bytes((ROOT / ".gitignore").read_bytes())
        (preserved / "baseline.txt").write_text("baseline\n")
        git(preserved, env, "add", ".gitignore", "baseline.txt")
        git(preserved, env, "commit", "-qm", "test(fixture): preserved ignore", "--no-verify")
        result = run(preserved, env, "--init")
        assert result.returncode == 0, result.stdout
        ledger = (preserved / ".git" / "git-init-v2-receipt").read_text()
        assert "PRESERVED\t.gitignore\t-" in ledger, ledger
        (preserved / ".gitignore").write_text("user-owned change\n")
        result = run(preserved, env, "--init")
        assert result.returncode == 0, result.stdout
        assert "CREATED 的 .gitignore" not in result.stdout
        assert (preserved / ".gitignore").read_text() == "user-owned change\n"
        print("PASS: semantic update: tracked PRESERVED edit passes as known user ownership")

        custom = base / "preserved-custom-ignore"
        custom.mkdir()
        git(custom, env, "init", "-q", "-b", "main")
        git(custom, env, "config", "--local", "user.name", "Fixture User")
        git(custom, env, "config", "--local", "user.email", "fixture@example.test")
        (custom / ".gitignore").write_text("custom-cache/\n")
        (custom / "baseline.txt").write_text("baseline\n")
        git(custom, env, "add", ".gitignore", "baseline.txt")
        git(custom, env, "commit", "-qm", "test(fixture): custom ignore", "--no-verify")
        result = run(custom, env, "--init")
        assert result.returncode == 0, result.stdout
        assert "PRESERVED\t.gitignore\t-" in (custom / ".git" / "git-init-v2-receipt").read_text()
        result = run(custom, env, "--init")
        assert result.returncode == 0, result.stdout
        print("PASS: preserved custom ignore has no managed-template conflict")

        # Every candidate path is PRESERVED before deletion.  A missing
        # user-owned artifact blocks before any init mutation or restoration.
        for managed_path in (
            ".gitmessage", "commitlint.config.cjs", "AI-WORKFLOW.template.md",
            ".githooks/commit-msg", ".gitignore",
        ):
            deleted = base / f"deleted-preserved-{managed_path.replace('/', '-') }"
            deleted.mkdir()
            git(deleted, env, "init", "-q", "-b", "main")
            git(deleted, env, "config", "--local", "user.name", "Fixture User")
            git(deleted, env, "config", "--local", "user.email", "fixture@example.test")
            target = deleted / managed_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"user-owned {managed_path}\n")
            (deleted / "baseline.txt").write_text("baseline\n")
            git(deleted, env, "add", ".")
            git(deleted, env, "commit", "-qm", "test(fixture): preserved artifact", "--no-verify")
            result = run(deleted, env, "--init")
            assert result.returncode == 0, result.stdout
            receipt = deleted / ".git" / "git-init-v2-receipt"
            marker = deleted / ".git" / "git-init-v2-receipt.sha256"
            before_receipt = receipt.read_bytes()
            before_marker = marker.read_bytes()
            before_config = local_config(deleted, env)
            before_refs = refs(deleted, env)
            before_index = index(deleted)
            target.unlink()
            result = run(deleted, env, "--init")
            assert result.returncode == 5, result.stdout
            assert not target.exists(), managed_path
            assert f"PRESERVED\t{managed_path}\t-".encode() in before_receipt
            assert receipt.read_bytes() == before_receipt
            assert marker.read_bytes() == before_marker
            assert local_config(deleted, env) == before_config
            assert refs(deleted, env) == before_refs
            assert index(deleted) == before_index
            print(f"PASS: deleted PRESERVED {managed_path} blocks without template restoration or state mutation")

        modified = setup(base, "modified", env)
        (modified / ".gitmessage").write_text("user modification\n")
        blocked(modified, env, "recorded modified artifact blocks")
        assert (modified / ".gitmessage").read_text() == "user modification\n"

        missing = setup(base, "missing", env)
        (missing / ".git" / "git-init-v2-receipt").unlink()
        blocked(missing, env, "missing receipt cannot become first run")

        truncated = setup(base, "truncated", env)
        receipt = truncated / ".git" / "git-init-v2-receipt"
        receipt.write_text(receipt.read_text().splitlines()[0] + "\n")
        blocked(truncated, env, "truncated receipt blocks")

        unknown = setup(base, "unknown", env)
        receipt = unknown / ".git" / "git-init-v2-receipt"
        receipt.write_text(receipt.read_text() + "unknown-path\t" + "0" * 64 + "\n")
        blocked(unknown, env, "unknown receipt entry blocks")

        changed_hash = setup(base, "changed-hash", env)
        receipt = changed_hash / ".git" / "git-init-v2-receipt"
        receipt.write_text(receipt.read_text().replace("a", "b", 1))
        blocked(changed_hash, env, "changed receipt hash blocks")


if __name__ == "__main__":
    main()
