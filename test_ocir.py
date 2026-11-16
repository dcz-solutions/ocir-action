import json
import runpy
import subprocess
from unittest.mock import Mock

import pytest

import ocir


@pytest.fixture
def settings(monkeypatch, tmp_path):
    output = tmp_path / "output"
    for key, value in {
        "INPUT_COMPARTMENT": "compartment",
        "INPUT_NAME": "repo",
        "OCI_CLI_TENANCY": "tenancy",
        "OCI_CLI_USER": "user-id",
        "OCI_CLI_REGION": "us-ashburn-1",
        "GITHUB_OUTPUT": str(output),
    }.items():
        monkeypatch.setenv(key, value)
    return output


def test_cli_command(monkeypatch):
    run = Mock(return_value=subprocess.CompletedProcess([], 0, '{"data": []}'))
    monkeypatch.setattr(subprocess, "run", run)

    assert ocir.oci("iam", "region", "list") == []
    assert run.call_args.args[0] == ["oci", "iam", "region", "list", "--output", "json"]
    assert run.call_args.kwargs["check"] is True
    assert "env" not in run.call_args.kwargs


def test_cli_failure_propagates(monkeypatch):
    monkeypatch.setattr(
        subprocess, "run", Mock(side_effect=subprocess.CalledProcessError(1, ["oci"]))
    )
    with pytest.raises(subprocess.CalledProcessError):
        ocir.oci("iam", "region", "list")


@pytest.mark.parametrize("response", ["not json", "{}"])
def test_invalid_cli_response(monkeypatch, response):
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(return_value=subprocess.CompletedProcess([], 0, response)),
    )
    with pytest.raises((ValueError, KeyError)):
        ocir.oci("iam", "region", "list")


@pytest.fixture
def api(monkeypatch):
    responses = {
        ("iam", "region", "list"): [{"name": "us-ashburn-1", "key": "IAD"}],
        ("artifacts", "container", "configuration", "get"): {"namespace": "namespace"},
        ("iam", "user", "get"): {"name": "user"},
        ("artifacts", "container", "repository", "list"): {"items": []},
        ("artifacts", "container", "repository", "create"): {
            "display-name": "repo",
            "id": "ocid",
        },
    }
    calls = []

    def fake_oci(*args):
        calls.append(args)
        return responses[args[:4] if args[0] == "artifacts" else args[:3]]

    monkeypatch.setattr(ocir, "oci", fake_oci)
    return responses, calls


@pytest.mark.parametrize("existing", [True, False])
def test_repository_outputs(settings, api, existing):
    responses, calls = api
    if existing:
        responses[("artifacts", "container", "repository", "list")]["items"] = [
            {"display-name": "other", "id": "other-id"},
            {"display-name": "repo", "id": "ocid"},
        ]
    settings.write_text("previous=value\n")

    ocir.main()

    assert settings.read_text().splitlines() == [
        "previous=value",
        "repo_path=iad.ocir.io/namespace/repo",
        "repo_ocid=ocid",
        "ocir_endpoint=iad.ocir.io",
        "ocir_username=namespace/user",
    ]
    assert (
        "artifacts",
        "container",
        "repository",
        "list",
        "--compartment-id",
        "compartment",
        "--display-name",
        "repo",
        "--all",
    ) in calls
    creates = [
        call
        for call in calls
        if call[:4] == ("artifacts", "container", "repository", "create")
    ]
    assert bool(creates) is not existing
    if creates:
        assert creates[0][4:] == (
            "--compartment-id",
            "compartment",
            "--display-name",
            "repo",
            "--is-public",
            "false",
            "--is-immutable",
            "false",
        )


@pytest.mark.parametrize(
    "key",
    [
        "INPUT_COMPARTMENT",
        "INPUT_NAME",
        "OCI_CLI_TENANCY",
        "OCI_CLI_USER",
        "OCI_CLI_REGION",
    ],
)
def test_empty_required_setting(settings, api, monkeypatch, key):
    monkeypatch.setenv(key, "")
    with pytest.raises(ValueError, match="must not be empty"):
        ocir.main()
    assert api[1] == []
    assert not settings.exists()


def test_missing_required_setting(settings, monkeypatch):
    monkeypatch.delenv("OCI_CLI_USER")
    with pytest.raises(KeyError, match="OCI_CLI_USER"):
        ocir.main()
    assert not settings.exists()


def test_unknown_region(settings, api):
    api[0][("iam", "region", "list")] = [{"name": "another-region", "key": "XXX"}]
    with pytest.raises(ValueError, match="Unable to determine OCIR endpoint"):
        ocir.main()
    assert len(api[1]) == 1
    assert not settings.exists()


@pytest.mark.parametrize("bad_value", ["bad\ninjected=value", "bad\rinjected=value"])
def test_rejects_multiline_output(settings, api, bad_value):
    api[0][("iam", "user", "get")]["name"] = bad_value
    with pytest.raises(ValueError, match="invalid output characters"):
        ocir.main()
    assert not settings.exists()


def test_cli_entrypoint_reports_errors(settings, monkeypatch, capsys):
    monkeypatch.setattr(
        subprocess, "run", Mock(side_effect=subprocess.CalledProcessError(1, ["oci"]))
    )
    with pytest.raises(SystemExit) as error:
        runpy.run_module("ocir", run_name="__main__")
    assert error.value.code == 1
    assert "OCIR preparation failed:" in capsys.readouterr().err
    assert not settings.exists()


def test_cli_entrypoint_success(settings, monkeypatch):
    responses = [
        [{"name": "us-ashburn-1", "key": "IAD"}],
        {"namespace": "namespace"},
        {"name": "user"},
        {"items": [{"display-name": "repo", "id": "ocid"}]},
    ]
    run = Mock(
        side_effect=[
            subprocess.CompletedProcess([], 0, json.dumps({"data": data}))
            for data in responses
        ]
    )
    monkeypatch.setattr(subprocess, "run", run)
    runpy.run_module("ocir", run_name="__main__")
    assert "repo_ocid=ocid\n" in settings.read_text()
    assert run.call_count == 4
