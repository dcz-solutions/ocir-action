# Contributing

Open an issue or pull request describing the problem and proposed change. Keep changes focused and add tests for behavior changes.

Run `uv run --locked pytest`, `uv run --locked ruff check .`, and
`uv run --locked ruff format --check .` before submitting. Tests mock OCI calls
and need no credentials; CI requires at least 90% branch-aware coverage.

Use Conventional Commits for commits merged into `main`: `fix:` for patches,
`feat:` for minor versions, and `!` or a `BREAKING CHANGE:` footer for major
versions. When squash-merging, use a Conventional Commit pull request title.
Release Please derives versions from release tags and Conventional Commits and
updates `CHANGELOG.md` through release pull requests. No version file is needed.
