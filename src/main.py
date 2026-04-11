from __future__ import annotations

import argparse
from pathlib import Path

from io_csv import read_repo_urls
from git_ops import controlled_clone, safe_repo_dir_name
from pipeline import run_package_pipeline
from output_generator import (
    SUPPORTED_BUILD_TYPES,
    make_clone_fail_row,
    make_supported_fail_row,
    make_supported_success_row,
    make_unsupported_row,
    print_summary,
    write_rows_to_csv,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="输入CSV文件路径")
    parser.add_argument("--workspace", required=True, help="仓库克隆工作目录")
    parser.add_argument("--output-dir", required=True, help="输出结果目录")
    parser.add_argument("--timeout", type=int, default=600, help="单个软件包超时时间（秒）")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    workspace_dir = Path(args.workspace)
    output_dir = Path(args.output_dir)

    workspace_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    repo_urls = read_repo_urls(csv_path)

    unsupported_rows: list[dict] = []
    success_rows: list[dict] = []
    fail_rows: list[dict] = []

    total = len(repo_urls)

    for idx, repo_url in enumerate(repo_urls, start=1):
        package_name = safe_repo_dir_name(repo_url)

        print(f"[{idx}/{total}] 开始处理: {package_name}")

        ok, repo_path, clone_log = controlled_clone(
            repo_url=repo_url,
            workspace_dir=workspace_dir,
            timeout_s=args.timeout,
        )

        if not ok or repo_path is None:
            print(f"[{idx}/{total}] clone失败: {package_name}")
            fail_rows.append(make_clone_fail_row(package_name, repo_url, clone_log))
            continue

        try:
            plan, result = run_package_pipeline(repo_path, timeout_s=args.timeout)

            # 四个构建测试类型以外，单独输出
            if plan.detected_type not in SUPPORTED_BUILD_TYPES:
                unsupported_rows.append(make_unsupported_row(package_name, repo_url, plan))
                print(f"[{idx}/{total}] 非四类类型，已归入 unsupported: {package_name} | 类型={plan.detected_type}")
                continue

            # 四个构建测试类型以内：按成功/失败分开
            if result.status == "OK":
                success_rows.append(make_supported_success_row(package_name, repo_url, plan))
                print(f"[{idx}/{total}] 成功: {package_name} | 类型={plan.detected_type}")
            else:
                fail_rows.append(make_supported_fail_row(package_name, repo_url, plan, result))
                print(
                    f"[{idx}/{total}] 失败: {package_name} | "
                    f"类型={plan.detected_type} | 阶段={result.failure_stage} | 原因={result.failure_reason}"
                )

        except Exception as e:
            print(f"[{idx}/{total}] pipeline异常: {package_name} -> {e}")
            fail_rows.append(make_clone_fail_row(package_name, repo_url, f"pipeline异常: {e}"))

    unsupported_csv = output_dir / "unsupported_results.csv"
    success_csv = output_dir / "success_results.csv"
    fail_csv = output_dir / "fail_results.csv"

    write_rows_to_csv(unsupported_rows, unsupported_csv)
    write_rows_to_csv(success_rows, success_csv)
    write_rows_to_csv(fail_rows, fail_csv)

    print_summary(unsupported_rows, success_rows, fail_rows)

    print(f"非四类输出: {unsupported_csv}")
    print(f"成功输出: {success_csv}")
    print(f"失败输出: {fail_csv}")


if __name__ == "__main__":
    main()