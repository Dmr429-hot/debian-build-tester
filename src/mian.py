import argparse
import csv
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Debian package build tester (skeleton)"
    )

    parser.add_argument(
        "--csv",
        help="Path to CSV file containing repository URLs",
        required=True,
    )

    return parser.parse_args()


def read_repos(csv_path: Path):
    repos = []

    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            repos.append(row["repo_url"])

    return repos


def main():
    args = parse_args()
    csv_path = Path(args.csv)

    repos = read_repos(csv_path)

    print(f"Loaded {len(repos)} repositories:")
    for repo in repos:
        print(f" - {repo}")


if __name__ == "__main__":
    main()
