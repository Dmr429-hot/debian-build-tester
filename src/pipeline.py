from __future__ import annotations
import subprocess
from pathlib import Path

from detector import detect_build_plan
from builder import execute_build_plan
from models import BuildPlan, BuildResult


def cleanup_repo(repo_dir: Path) -> None:
    if repo_dir.exists():
        subprocess.run(["rm", "-rf", str(repo_dir)], check=False)


def run_package_pipeline(repo_dir: Path, timeout_s: int = 300) -> tuple[BuildPlan, BuildResult]:
    plan = detect_build_plan(repo_dir)
    try:
        result = execute_build_plan(plan, timeout_s=timeout_s)
        return plan, result
    finally:
        cleanup_repo(repo_dir)