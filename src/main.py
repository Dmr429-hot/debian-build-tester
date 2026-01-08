from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from io_csv import read_repo_urls
from git_ops import controlled_clone
from detect import detect_build_type


def parse_args():
    p = argparse.ArgumentParser(description="Week1: CSV -> controlled clone -> build type detect")
    p.add_argument("--csv", required=True, help="CSV path with column repo_url")
    p.add_argument("--workspace", default="workspace", help="Workspace dir for cloned repos")
    p.add_argument("--out", default="results/week1_results.jsonl", help="Output JSONL path")
    p.add_argument("--clone-timeout", type=int, default=300, help="Clone timeout in seconds")
    return p.parse_args()


def main():
    args = parse_args()
    csv_path = Path(args.csv)
    workspace_dir = Path(args.workspace)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    repo_urls = read_repo_urls(csv_path)

    with out_path.open("a", encoding="utf-8") as f:
        for url in repo_urls:
            ok, repo_path, clone_log = controlled_clone(url, workspace_dir, timeout_s=args.clone_timeout)

            record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "repo_url": url,
                "clone_status": "OK" if ok else "FAIL",
                "clone_log": clone_log[:2000],  # avoid huge output
                "build_type": "OTHER",
                "evidence": [],
            }

            if ok and repo_path:
                build_type, evidence = detect_build_type(repo_path)
                record["build_type"] = build_type
                record["evidence"] = evidence

            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(f"{url} -> clone={record['clone_status']} type={record['build_type']}")

    print(f"Done. Results: {out_path}")


if __name__ == "__main__":
    main()
