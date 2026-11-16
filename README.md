# OCIR Action

Find or create an Oracle Cloud Infrastructure Registry (OCIR) repository and log in to its registry in one GitHub Actions step.

- Reuses an existing repository or creates a private, mutable one.
- Installs the OCI CLI with `uv tool install` and caches uv packages across workflow runs.
- Exposes the repository path, repository OCID, registry endpoint, and username.
- Logs Docker out at the end of the job through `docker/login-action`.

## Requirements

- A Linux runner with Python 3 and Docker.
- An OCI API key and an auth token for the OCI user. Configure the user and tenancy to allow region and user lookup, container configuration lookup, and repository listing and creation in the target compartment.
- These OCI CLI environment variables, typically configured as GitHub secrets:

| Environment variable | Description |
| --- | --- |
| `OCI_CLI_TENANCY` | Tenancy OCID |
| `OCI_CLI_USER` | User OCID |
| `OCI_CLI_FINGERPRINT` | API key fingerprint |
| `OCI_CLI_KEY_CONTENT` | Contents of the API private key |
| `OCI_CLI_REGION` | OCI region identifier, such as `us-ashburn-1` |

Workflow-level and job-level environment variables are inherited automatically. The auth token is passed separately through the `auth_token` input.

## Usage

Replace `v1` with a published tag or commit SHA. The image is built before it is pushed.

```yaml
name: Publish image
on: [push]

env:
  OCI_CLI_TENANCY: ${{ secrets.OCI_CLI_TENANCY }}
  OCI_CLI_USER: ${{ secrets.OCI_CLI_USER }}
  OCI_CLI_FINGERPRINT: ${{ secrets.OCI_CLI_FINGERPRINT }}
  OCI_CLI_KEY_CONTENT: ${{ secrets.OCI_CLI_KEY_CONTENT }}
  OCI_CLI_REGION: ${{ secrets.OCI_CLI_REGION }}

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - name: Prepare OCIR
        id: ocir
        uses: dczsolutions/ocir-action@v1
        with:
          name: my-image
          compartment: ${{ secrets.OCI_COMPARTMENT_OCID }}
          auth_token: ${{ secrets.OCI_AUTH_TOKEN }}
      - name: Build and push
        env:
          REPO_PATH: ${{ steps.ocir.outputs.repo_path }}
        run: |
          docker build -t "$REPO_PATH:latest" .
          docker push "$REPO_PATH:latest"
```

## Inputs

| Input | Required | Description |
| --- | --- | --- |
| `name` | Yes | Repository name. |
| `compartment` | Yes | OCID of the repository compartment. |
| `auth_token` | Yes | OCI user auth token for registry login. Pass a GitHub secret. |

## Outputs

| Output | Description |
| --- | --- |
| `repo_path` | Full repository path, such as `iad.ocir.io/namespace/my-image`. |
| `repo_ocid` | Repository OCID. |
| `ocir_endpoint` | Registry endpoint, such as `iad.ocir.io`. |
| `ocir_username` | Registry username in `namespace/username` format. |

## Migrating from Oracle actions

Replace `oracle-actions/login-ocir` and `oracle-actions/get-ocir-repository` with one step. Keep the repository step ID to preserve references to `steps.get-ocir-repository.outputs.repo_path`:

```yaml
- name: Prepare OCIR
  id: get-ocir-repository
  uses: dczsolutions/ocir-action@v1
  with:
    name: gedpag2026-${{ steps.conf.outputs.deploy_env }}
    compartment: ${{ steps.conf.outputs.compartment_id }}
    auth_token: ${{ secrets.OCI_AUTH_TOKEN }}
```

Existing workflow-level `OCI_CLI_*` variables do not need to change. Existing repositories are not modified. Parallel jobs creating the same missing repository can race; a failed creation fails the action.

The action authenticates Docker. Podman can use the credentials if configured to read Docker's configuration.

## Development

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and run
`uv run --locked pytest` for tests and branch coverage, `uv run --locked ruff check .`
for lint, and `uv run --locked ruff format --check .` for formatting. Run
`uv run --locked ruff format .` to apply formatting. Tests mock OCI calls and
do not require credentials. CI requires at least 90% branch-aware coverage.

## Releases

The Test workflow runs on pull requests and pushes to `main`. The separate Release
workflow runs after successful tests for a push to the current `main` commit;
failed tests, pull requests, and outdated test runs cannot trigger a release.
Release Please opens or updates a release pull request based on Conventional Commits:

| Commit | Version change |
| --- | --- |
| `fix: correct repository lookup` | Patch, such as `1.0.0` to `1.0.1` |
| `feat: add a registry output` | Minor, such as `1.0.0` to `1.1.0` |
| `feat!: change required inputs` | Major, such as `1.0.0` to `2.0.0` |
| `docs:`, `test:`, or `chore:` | Does not trigger a release by itself |

The first release starts at `1.0.0`. Merge the release pull request to publish
the GitHub release and full version tag. The workflow also updates the matching
major tag, so `dczsolutions/ocir-action@v1` follows releases in the `1.x` series.
Versions are derived from release tags and Conventional Commits; no version file
is needed. Release Please maintains `CHANGELOG.md`. Its `go` release strategy is
used for changelog-only updates and does not require Go code or tooling.

Enable **Allow GitHub Actions to create and approve pull requests** in repository
Settings > Actions > General. The workflow uses the built-in `GITHUB_TOKEN`.
Bot-created release pull requests do not trigger CI with this token; tests still
run on `main` before publishing. If branch protection requires checks on the
release pull request, configure Release Please with a GitHub App token or PAT
that can trigger those checks. Tag rules must allow the workflow to update major
version tags. Use a full commit SHA instead of a major tag for immutable pinning.

## License

[MIT](LICENSE), copyright 2026 dczsolutions. Upstream Oracle attribution and its
UPL 1.0 reference are retained in [NOTICE](NOTICE).
