from __future__ import annotations
import csv
from pathlib import Path
from typing import List


def read_repo_urls(csv_path: Path) -> List[str]:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    urls: List[str] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if "repo_url" not in (reader.fieldnames or []):
            raise ValueError("CSV must contain a header column named 'repo_url'")

        for row in reader:
            url = (row.get("repo_url") or "").strip()
            if url:
                urls.append(url)
    return urls
