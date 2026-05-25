"""
Utilities for publishing the latest HTML report to GitHub Pages.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def _run_git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=check,
        text=True,
        capture_output=True,
    )


def _repo_root_from(start: Path) -> Path:
    result = _run_git(["rev-parse", "--show-toplevel"], cwd=start)
    return Path(result.stdout.strip())


def publish_to_github_pages(
    report_html_path: str | Path,
    *,
    branch: str = "gh-pages",
    remote: str = "origin",
    repo_root: str | Path | None = None,
    commit_message: str = "Update test report",
) -> str:
    """
    Publish a single HTML report as index.html on the GitHub Pages branch.

    Uses a temporary git worktree so the caller's current branch and local
    modifications are left untouched.
    """
    report_path = Path(report_html_path).resolve()
    if not report_path.is_file():
        raise FileNotFoundError(f"Report not found: {report_path}")

    root = Path(repo_root).resolve() if repo_root else _repo_root_from(report_path.parent)

    with tempfile.TemporaryDirectory(prefix="gh-pages-publish-") as temp_dir:
        worktree_dir = Path(temp_dir) / "worktree"
        _run_git(["worktree", "add", "--detach", str(worktree_dir), "HEAD"], cwd=root)

        try:
            existing_branch = _run_git(
                ["show-ref", "--verify", f"refs/heads/{branch}"],
                cwd=root,
                check=False,
            ).returncode == 0

            if existing_branch:
                _run_git(["checkout", "--detach", branch], cwd=worktree_dir)
            else:
                _run_git(["checkout", "--orphan", branch], cwd=worktree_dir)

            for child in worktree_dir.iterdir():
                if child.name == ".git":
                    continue
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()

            published_report = worktree_dir / "index.html"
            shutil.copy2(report_path, published_report)

            _run_git(["add", "index.html"], cwd=worktree_dir)

            diff_result = _run_git(["diff", "--cached", "--quiet"], cwd=worktree_dir, check=False)
            if diff_result.returncode == 0:
                logger.info("GitHub Pages already matches %s; nothing to publish.", report_path)
                return f"{branch}: no changes to publish"

            _run_git(["commit", "-m", commit_message], cwd=worktree_dir)
            _run_git(["push", remote, f"HEAD:{branch}"], cwd=worktree_dir)
        finally:
            _run_git(["worktree", "remove", "--force", str(worktree_dir)], cwd=root, check=False)

    return f"{remote}/{branch}"
