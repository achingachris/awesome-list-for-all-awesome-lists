# Repository Guidelines

## Project Structure & Module Organization

This repository maintains an automatically generated directory of GitHub repositories named exactly `awesome` or `awesome-list`.

- `scripts/update_awesome_lists.py` contains discovery, metadata refresh, sorting, and rendering logic.
- `awesome-repositories.json` is the machine-readable generated dataset.
- `README.md` is generated from the same dataset and presents the catalog as Markdown.
- `.github/workflows/update-awesome-lists.yml` runs the refresh daily and commits changed outputs.

Keep reusable logic in the update script. Treat `README.md` and `awesome-repositories.json` as synchronized generated artifacts; changes to their format should be made in the script.

## Build, Test, and Development Commands

The project uses Python 3.12 and only the standard library; there is no build step or package installation.

- `GITHUB_TOKEN=... python scripts/update_awesome_lists.py` refreshes metadata and rewrites both generated files. Use a token that can read public repository metadata.
- `python -m py_compile scripts/update_awesome_lists.py` performs a quick syntax check without contacting GitHub.
- `python -m json.tool awesome-repositories.json >/dev/null` validates the generated JSON.
- `git diff --check` detects whitespace errors before committing.

The refresh makes many GitHub API requests and may take several minutes. Review `git diff -- README.md awesome-repositories.json` after it finishes.

## Coding Style & Naming Conventions

Follow PEP 8 with four-space indentation, type hints, and descriptive `snake_case` names. Use `UPPER_CASE` for module constants such as `SEARCH_URL`. Keep functions focused on one stage of the pipeline and preserve deterministic ordering: descending star count, then case-insensitive full repository name. No formatter or linter is currently configured, so match the existing style.

## Testing Guidelines

There is no automated test suite or coverage threshold. For script changes, run the syntax and JSON checks above, then confirm that only exact-name repositories remain, required fields are present, and README summary counts match the JSON. Avoid committing partial output from an interrupted refresh.

## Commit & Pull Request Guidelines

Recent commits use short, imperative, sentence-case subjects, for example `Prioritize high-star repositories during discovery`. Keep each commit focused. Pull requests should explain the behavior or data-format change, list validation commands, and note generated-file changes. Link relevant issues when available; screenshots are unnecessary unless Markdown rendering changes materially.

## Security & Automation

Never commit `GITHUB_TOKEN` or other credentials. Preserve the workflow's least-privilege `contents: write` permission, concurrency guard, and commit-only-when-changed behavior.
