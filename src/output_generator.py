from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from models import BuildPlan, BuildResult


SUPPORTED_BUILD_TYPES = {"CMAKE", "MESON", "AUTOTOOLS", "MAKEFILE"}


def make_supported_success_row(
    package_name: str,
    repo_url: str,
    plan: BuildPlan,
) -> dict[str, Any]:
    return {
        "软件包名": package_name,
        "GitHub链接": repo_url,
        "类型": plan.detected_type,
    }


def make_supported_fail_row(
    package_name: str,
    repo_url: str,
    plan: BuildPlan,
    result: BuildResult,
) -> dict[str, Any]:
    return {
        "软件包名": package_name,
        "GitHub链接": repo_url,
        "类型": plan.detected_type,
        "失败阶段": result.failure_stage,
        "失败原因": result.failure_reason,
        "关键日志片段": result.key_log,
    }


def make_unsupported_row(
    package_name: str,
    repo_url: str,
    plan: BuildPlan | None,
) -> dict[str, Any]:
    return {
        "软件包名": package_name,
        "GitHub链接": repo_url,
        "类型": plan.detected_type if plan else "UNKNOWN",
    }


def make_clone_fail_row(
    package_name: str,
    repo_url: str,
    clone_log: str,
) -> dict[str, Any]:
    return {
        "软件包名": package_name,
        "GitHub链接": repo_url,
        "类型": "CLONE_FAIL",
        "失败阶段": "CLONE",
        "失败原因": "仓库获取失败",
        "关键日志片段": clone_log,
    }


def write_rows_to_csv(rows: list[dict[str, Any]], output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        return

    fieldnames = list(rows[0].keys())

    with output_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_summary(
    unsupported_rows: list[dict[str, Any]],
    success_rows: list[dict[str, Any]],
    fail_rows: list[dict[str, Any]],
) -> None:
    unsupported_count = len(unsupported_rows)
    success_count = len(success_rows)
    fail_count = len(fail_rows)
    total = unsupported_count + success_count + fail_count

    print("=" * 60)
    print(f"总数: {total}")
    print(f"非四类构建类型: {unsupported_count}")
    print(f"四类构建成功: {success_count}")
    print(f"四类构建失败: {fail_count}")
    print("=" * 60)