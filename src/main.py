from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from io_csv import read_repo_urls
from git_ops import controlled_clone
from detect import detect_build_type
from build import build_project


def parse_args():
    p = argparse.ArgumentParser(description="Week1: CSV -> controlled clone -> build type detect")
    p.add_argument("--csv", required=True, help="CSV path with column repo_url")
    p.add_argument("--workspace", default="workspace", help="Workspace dir for cloned repos")
    p.add_argument("--out", default="results/week1_results.jsonl", help="Output JSONL path")
    p.add_argument("--clone-timeout", type=int, default=300, help="Clone timeout in seconds")
    return p.parse_args()

def get_repo_name(url: str) -> str:
    """
    从 GitHub 仓库 URL 中提取仓库名
    例如： 'https://github.com/user/repo.git' -> 'repo'
    """
    # 去掉 '.git' 后缀，获取仓库名
    return url.rstrip('/').split('/')[-1].replace('.git', '')

def main():
    args = parse_args()
    print("已执行完parse_args()")
    csv_path = Path(args.csv)
    workspace_dir = Path(args.workspace)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    repo_urls = read_repo_urls(csv_path)
    print(f"Found {len(repo_urls)} repositories to process.")  # 输出找到的仓库数

    with out_path.open("a", encoding="utf-8") as f:
        # 初始化序号
        index = 1

        for url in repo_urls:
            print(f"Processing repository: {url}")  # 输出当前正在处理的仓库
            # 提取仓库名
            repo_name = get_repo_name(url)

            # 执行 Git clone
            ok, repo_path, clone_log = controlled_clone(url, workspace_dir, timeout_s=args.clone_timeout)

            # 生成记录内容
            record = {
                "index": index,  # 添加序号
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "repo_url": url,
                "repo_name": repo_name,  # 添加仓库名
                "clone_status": "OK" if ok else "FAIL",
                "clone_log": clone_log[:2000],
                "build_type": "OTHER",
                "build_status": "PENDING",  # 初始状态
                "build_log": "",
                "failure_stage": "NONE",  # 新增：记录失败阶段
                "evidence": [],
            }

            # 如果 clone 成功，执行构建
            if ok and repo_path:
                build_type, evidence = detect_build_type(repo_path)
                record["build_type"] = build_type
                record["evidence"] = evidence

                build_status, build_log, failure_stage = build_project(repo_path, build_type, timeout_s=args.clone_timeout)
                record["build_status"] = build_status
                record["build_log"] = build_log[:2000]
                record["failure_stage"] = failure_stage  # 新增：记录失败的阶段

            # 将序号和仓库信息写入文件
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(f"{index}. {repo_name} -> clone={record['clone_status']} build={record['build_status']} stage={record['failure_stage']}")

            # 增加序号
            index += 1

    print(f"Done. Results: {out_path}")

