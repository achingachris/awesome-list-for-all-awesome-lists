# Awesome List for All Awesome Lists

A searchable dataset of GitHub repositories whose names are exactly `awesome` or `awesome-list` (case-insensitive).

## Dataset

The repository includes [`awesome-repositories.csv`](./awesome-repositories.csv) with **795 deduplicated repositories**:

- **102** named `awesome`
- **693** named `awesome-list`

Columns:

| Column | Description |
| --- | --- |
| `repository_full_name` | Repository in `owner/name` format |
| `name` | Repository name |
| `owner` | GitHub owner or organization |
| `url` | Repository URL |
| `visibility` | Repository visibility |
| `archived` | Whether the repository is archived |
| `default_branch` | Default branch |
| `clone_url` | HTTPS clone URL |

## Scope and limitations

The data was collected on **2026-07-18** using GitHub repository search and deduplicated by full repository name. GitHub exposes at most 1,000 results for a single search query, so the dataset reflects that platform limit and may not contain every matching repository.

## License

Repository metadata originates from GitHub. Review each linked repository's own license before reusing its content.
