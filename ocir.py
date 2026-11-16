import json
import os
import subprocess
import sys


def oci(*args):
    result = subprocess.run(
        ["oci", *args, "--output", "json"],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    return json.loads(result.stdout)["data"]


def main():
    compartment = os.environ["INPUT_COMPARTMENT"]
    name = os.environ["INPUT_NAME"]
    tenancy = os.environ["OCI_CLI_TENANCY"]
    user = os.environ["OCI_CLI_USER"]
    region = os.environ["OCI_CLI_REGION"]

    if not all((compartment, name, tenancy, user, region)):
        raise ValueError("Required OCI settings and action inputs must not be empty")

    region_code = next(
        (
            item["key"].lower()
            for item in oci("iam", "region", "list")
            if item["name"] == region
        ),
        None,
    )
    if not region_code:
        raise ValueError("Unable to determine OCIR endpoint for OCI_CLI_REGION")

    endpoint = f"{region_code}.ocir.io"

    namespace = oci(
        "artifacts", "container", "configuration", "get", "--compartment-id", tenancy
    )["namespace"]

    username = oci("iam", "user", "get", "--user-id", user)["name"]

    repositories = oci(
        "artifacts",
        "container",
        "repository",
        "list",
        "--compartment-id",
        compartment,
        "--display-name",
        name,
        "--all",
    )["items"]

    repository = next(
        (item for item in repositories if item["display-name"] == name), None
    )

    if repository is None:
        repository = oci(
            "artifacts",
            "container",
            "repository",
            "create",
            "--compartment-id",
            compartment,
            "--display-name",
            name,
            "--is-public",
            "false",
            "--is-immutable",
            "false",
        )

    outputs = {
        "repo_path": f"{endpoint}/{namespace}/{repository['display-name']}",
        "repo_ocid": repository["id"],
        "ocir_endpoint": endpoint,
        "ocir_username": f"{namespace}/{username}",
    }

    if any("\n" in value or "\r" in value for value in outputs.values()):
        raise ValueError("OCI response contains invalid output characters")

    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        for key, value in outputs.items():
            print(f"{key}={value}", file=output)


if __name__ == "__main__":
    try:
        main()
    except (KeyError, ValueError, subprocess.CalledProcessError) as error:
        print(f"OCIR preparation failed: {error}", file=sys.stderr)
        sys.exit(1)
