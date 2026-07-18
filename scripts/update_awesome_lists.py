#!/usr/bin/env python3
"""Refresh the awesome repository dataset and README using GitHub Search."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

SEARCH_URL = "https://api.github.com/search/repositories"
REPO_URL = "https://api.github.com/repos"
EXACT_NAMES = {"awesome", "awesome-list"}
PER_PAGE = 100
MAX_PAGES = 10
ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "awesome-repositories.json"
README_PATH = ROOT / "README.md"


def github_get(url: str, params: dict[str, str | int] | None = None) -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required")

    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "awesome-list-for-all-awesome-lists",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )

    for attempt in range(6):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return {}
            if error.code not in {403, 429, 500, 502, 503, 504} or attempt == 5:
                raise
            retry_after = int(error.headers.get("Retry-After", "0"))
            time.sleep(max(retry_after, 2**attempt))

    raise RuntimeError("GitHub API request failed after retries")


def normalize(repository: dict) -> dict:
    return {
        "repository_full_name": repository["full_name"],
        "name": repository["name"],
        "owner": repository["owner"]["login"],
        "url": repository["html_url"],
        "stars": repository.get("stargazers_count", 0),
        "visibility": repository.get("visibility", "public"),
        "archived": repository.get("archived", False),
        "default_branch": repository.get("default_branch", ""),
        "clone_url": repository.get("clone_url", ""),
    }


def load_existing() -> dict[str, dict]:
    repositories: dict[str, dict] = {}
    if not JSON_PATH.exists():
        return repositories

    with JSON_PATH.open(encoding="utf-8") as handle:
        rows = json.load(handle)

    for row in rows:
        name = str(row.get("name") or "").lower()
        full_name = str(row.get("repository_full_name") or "")
        if name not in EXACT_NAMES or not full_name:
            continue
        row["stars"] = int(row.get("stars") or 0)
        row["archived"] = bool(row.get("archived", False))
        repositories[full_name.lower()] = row
    return repositories


def discover(repositories: dict[str, dict]) -> None:
    for query in ("awesome in:name", "awesome-list in:name"):
        for page in range(1, MAX_PAGES + 1):
            payload = github_get(
                SEARCH_URL,
                {"q": query, "per_page": PER_PAGE, "page": page},
            )
            items = payload.get("items", [])
            if not items:
                break

            for repository in items:
                if repository["name"].lower() in EXACT_NAMES:
                    repositories[repository["full_name"].lower()] = normalize(repository)

            if len(items) < PER_PAGE:
                break


def refresh_one(full_name: str) -> tuple[str, dict]:
    encoded_name = urllib.parse.quote(full_name, safe="/")
    repository = github_get(f"{REPO_URL}/{encoded_name}")
    return full_name.lower(), repository


def enrich(repositories: dict[str, dict]) -> None:
    stale: list[str] = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(refresh_one, repository["repository_full_name"]): key
            for key, repository in repositories.items()
        }
        for future in as_completed(futures):
            key = futures[future]
            try:
                _, repository = future.result()
            except Exception as error:
                print(f"Warning: could not refresh {key}: {error}", file=sys.stderr)
                continue

            if not repository or repository["name"].lower() not in EXACT_NAMES:
                stale.append(key)
                continue
            repositories[key] = normalize(repository)

    for key in stale:
        repositories.pop(key, None)


def collect_repositories() -> list[dict]:
    repositories = load_existing()
    discover(repositories)
    enrich(repositories)
    return sorted(
        repositories.values(),
        key=lambda repository: (
            -int(repository["stars"]),
            repository["repository_full_name"].lower(),
        ),
    )


def write_json(repositories: list[dict]) -> None:
    with JSON_PATH.open("w", encoding="utf-8") as handle:
        json.dump(repositories, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


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
        "[`awesome-repositories.json`](./awesome-repositories.json).",
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
            f"{int(repository['stars']):,} |"
        )

    lines.extend(
        [
            "",
            "## Automation",
            "",
            "A scheduled GitHub Action refreshes this table and the JSON dataset daily. "
            "It preserves the existing catalog, discovers additional exact-name "
            "matches through GitHub Search, refreshes repository metadata and stars, "
            "removes unavailable repositories, and commits only when data changes.",
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

    write_json(repositories)
    write_readme(repositories)
    print(f"Wrote {len(repositories)} repositories.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
