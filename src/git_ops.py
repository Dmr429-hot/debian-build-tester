from __future__ import annotations
import subprocess
from pathlib import Path
from typing import Tuple


def safe_repo_dir_name(repo_url: str) -> str:
    # e.g. https://github.com/user/repo.git -> repo
    name = repo_url.rstrip("/").split("/")[-1]
    if name.endswith(".git"):
        name = name[:-4]
    return name or "unknown_repo"


def run_cmd(cmd: list[str], cwd: Path | None = None, timeout_s: int = 300) -> Tuple[int, str]:
    p = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout_s,
    )
    return p.returncode, p.stdout


def controlled_clone(repo_url: str, workspace_dir: Path, timeout_s: int = 300) -> Tuple[bool, Path | None, str]:
    """
    Returns: (ok, repo_path, log)
    """
    workspace_dir.mkdir(parents=True, exist_ok=True)
    repo_name = safe_repo_dir_name(repo_url)
    repo_path = workspace_dir / repo_name

    # If already exists, skip clone to keep Week1 simple
    if repo_path.exists():
        return True, repo_path, f"SKIP: already exists: {repo_path}"

    cmd = [
        "git", "clone",
        "--depth", "1",
        "--single-branch",
        repo_url,
        str(repo_path),
    ]
    try:
        code, out = run_cmd(cmd, timeout_s=timeout_s)
        if code == 0:
            return True, repo_path, out
        return False, None, out
    except subprocess.TimeoutExpired:
        return False, None, f"TIMEOUT after {timeout_s}s"
