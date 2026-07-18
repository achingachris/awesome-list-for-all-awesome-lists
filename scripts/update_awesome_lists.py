#!/usr/bin/env python3
"""Refresh the awesome repository dataset and README using GitHub Search."""

from __future__ import annotations

import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

API_URL = "https://api.github.com/search/repositories"
EXACT_NAMES = {"awesome", "awesome-list"}
PER_PAGE = 100
MAX_PAGES = 10
ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "awesome-repositories.csv"
README_PATH = ROOT / "README.md"


def github_get(params: dict[str, str | int]) -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required")

    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "awesome-list-for-all-awesome-lists",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )

    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code not in {403, 429, 500, 502, 503, 504} or attempt == 4:
                raise
            retry_after = int(error.headers.get("Retry-After", "0"))
            time.sleep(max(retry_after, 2**attempt))

    raise RuntimeError("GitHub API request failed after retries")


def collect_repositories() -> list[dict]:
    repositories: dict[str, dict] = {}

    for query in ("awesome in:name", "awesome-list in:name"):
        for page in range(1, MAX_PAGES + 1):
            payload = github_get(
                {
                    "q": query,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": PER_PAGE,
                    "page": page,
                }
            )
            items = payload.get("items", [])
            if not items:
                break

            for repository in items:
                if repository["name"].lower() not in EXACT_NAMES:
                    continue

                full_name = repository["full_name"]
                repositories[full_name.lower()] = {
                    "repository_full_name": full_name,
                    "name": repository["name"],
                    "owner": repository["owner"]["login"],
                    "url": repository["html_url"],
                    "stars": repository["stargazers_count"],
                    "visibility": repository.get("visibility", "public"),
                    "archived": repository["archived"],
                    "default_branch": repository["default_branch"],
                    "clone_url": repository["clone_url"],
                }

            if len(items) < PER_PAGE:
                break

    return sorted(
        repositories.values(),
        key=lambda repository: (
            repository["name"].lower(),
            -repository["stars"],
            repository["repository_full_name"].lower(),
        ),
    )


def write_csv(repositories: list[dict]) -> None:
    fieldnames = [
        "repository_full_name",
        "name",
        "owner",
        "url",
        "stars",
        "visibility",
        "archived",
        "default_branch",
        "clone_url",
    ]
    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(repositories)


def write_readme(repositories: list[dict]) -> None:
    awesome_count = sum(
        repository["name"].lower() == "awesome" for repository in repositories
    )
    awesome_list_count = len(repositories) - awesome_count

    lines = [
        "# Awesome List for All Awesome Lists",
        "",
        "An automatically updated directory of GitHub repositories whose names are "
        "exactly `awesome` or `awesome-list` (case-insensitive).",
        "",
        "## Summary",
        "",
        f"- **{len(repositories):,} repositories total**",
        f"- **{awesome_count:,}** named `awesome`",
        f"- **{awesome_list_count:,}** named `awesome-list`",
        f"- Last updated: **{date.today().isoformat()}**",
        "",
        "The machine-readable dataset is available in "
        "[`awesome-repositories.csv`](./awesome-repositories.csv).",
        "",
        "## Repositories",
        "",
        "| Repository | Owner | Stars |",
        "| --- | --- | ---: |",
    ]

    for repository in repositories:
        archived = " _(archived)_" if repository["archived"] else ""
        lines.append(
            f"| [{repository['repository_full_name']}]({repository['url']})"
            f"{archived} | {repository['owner']} | "
            f"{repository['stars']:,} |"
        )

    lines.extend(
        [
            "",
            "## Automation",
            "",
            "A scheduled GitHub Action refreshes this table and the CSV daily. "
            "It searches up to GitHub's 1,000-result limit for each query, "
            "deduplicates repositories by full name, and commits only when data changes.",
            "",
            "## License",
            "",
            "Repository metadata originates from GitHub. Review the license of each "
            "linked repository before reusing its content.",
            "",
        ]
    )
    README_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    repositories = collect_repositories()
    if not repositories:
        print("No exact-name repositories found; refusing to overwrite existing files.")
        return 1

    write_csv(repositories)
    write_readme(repositories)
    print(f"Wrote {len(repositories)} repositories.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
