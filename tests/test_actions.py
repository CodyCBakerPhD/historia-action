import pathlib
import re

import pytest
import yaml

_REPOSITORY_ROOT = pathlib.Path(__file__).parent.parent
_COMPOSITE_ACTION_PATH = _REPOSITORY_ROOT / "action.yml"
_ACTION_PATHS = sorted(_REPOSITORY_ROOT.glob("*/action.yml"))
_IMAGE_PATTERN = re.compile(r"^docker://ghcr\.io/codycbakerphd/historia:(\d+\.\d+\.\d+)$")


def _composite_action() -> dict:
    return yaml.safe_load(_COMPOSITE_ACTION_PATH.read_text(encoding="utf-8"))


@pytest.mark.ai_generated
def test_actions_are_discovered() -> None:
    action_names = [path.parent.name for path in _ACTION_PATHS]

    assert action_names == ["project-populate", "project-update-dates", "update-github"]


@pytest.mark.ai_generated
def test_actions_pin_one_released_image() -> None:
    """
    The actions name the image they were built against, and every one of them must name the same one.

    That pin is deliberate rather than derived. It changes when the actions are given a new major tag,
    not when Historia releases, so a workflow keeps running what its tag was built against.
    """
    images = [yaml.safe_load(path.read_text(encoding="utf-8"))["runs"]["image"] for path in _ACTION_PATHS]
    matches = [_IMAGE_PATTERN.match(image) for image in images]

    assert all(matches), images
    pinned_versions = {match.group(1) for match in matches if match is not None}
    assert len(pinned_versions) == 1, pinned_versions


@pytest.mark.ai_generated
@pytest.mark.parametrize("action_path", _ACTION_PATHS, ids=lambda path: path.parent.name)
def test_action_passes_the_token_and_no_empty_arguments(action_path: pathlib.Path) -> None:
    action = yaml.safe_load(action_path.read_text(encoding="utf-8"))

    assert action["runs"]["using"] == "docker"
    # S105: an unevaluated Actions expression that forwards the input, not a credential.
    assert action["runs"]["env"]["GITHUB_TOKEN"] == "${{ inputs.token }}"  # noqa: S105
    # Docker actions pass every entry of `args` through as its own argv element, including empty
    # strings, which the CLI would reject. Every optional input therefore needs a default.
    for argument in action["runs"]["args"]:
        assert argument != ""
    for name, specification in action["inputs"].items():
        assert specification["required"] is True or "default" in specification, name


@pytest.mark.ai_generated
def test_composite_action_reaches_its_siblings_by_major_tag() -> None:
    """
    The composite reaches its siblings by full reference, since `uses:` accepts no expressions.

    The siblings share the composite's major tag, so this reference is written once when that tag is
    cut and never rewritten. A package version here would have to be bumped on every release.
    """
    steps = _composite_action()["runs"]["steps"]
    historia_refs = [step["uses"] for step in steps if step.get("uses", "").startswith("CodyCBakerPhD/historia-action")]

    expected = [
        f"CodyCBakerPhD/historia-action/{name}@v0"
        for name in ("update-github", "project-populate", "project-update-dates")
    ]
    assert historia_refs == expected


@pytest.mark.ai_generated
def test_composite_action_needs_only_a_token_and_two_identifiers() -> None:
    """A data repository should be able to adopt this with three inputs and no other setup."""
    action = _composite_action()

    required = {name for name, spec in action["inputs"].items() if spec.get("required") is True}
    optional = {name for name, spec in action["inputs"].items() if spec.get("required") is not True}

    assert required == {"username", "project-url", "token"}
    for name in optional:
        assert "default" in action["inputs"][name], name


@pytest.mark.ai_generated
def test_composite_action_commits_only_after_reclaiming_root_owned_files() -> None:
    steps = _composite_action()["runs"]["steps"]
    step_names = [step["name"] for step in steps]

    assert step_names.index("Restore workspace ownership") == step_names.index("Update work history data") + 1
    assert step_names.index("Restore workspace ownership") < step_names.index("Commit and push new content")


@pytest.mark.ai_generated
def test_composite_action_pushes_the_archive_last() -> None:
    """The archive step leaves the checkout on an orphan branch, so nothing may run after it."""
    steps = _composite_action()["runs"]["steps"]

    assert steps[-1]["name"] == "Push the compressed archive"
    assert steps[-1]["if"] == "inputs.archive-branch != ''"


@pytest.mark.ai_generated
def test_composite_action_keeps_the_token_out_of_command_lines() -> None:
    """Interpolating the token into a `run:` body would place it in the command GitHub echoes."""
    for step in _composite_action()["runs"]["steps"]:
        assert "inputs.token" not in step.get("run", "")


@pytest.mark.ai_generated
def test_composite_action_pushes_with_the_workflow_token_only() -> None:
    """
    The personal token never pushes.

    The checkout persists its credential for every later `git push`, so handing it the workflow's own
    token is what keeps the personal token unable to write to any repository. The Historia steps are
    the only ones that receive the personal token.
    """
    action = _composite_action()
    steps = {step["name"]: step for step in action["runs"]["steps"]}

    assert [name for name in action["inputs"] if "token" in name] == ["token"]
    assert steps["Check out the data repository"]["with"]["token"] == "${{ github.token }}"  # noqa: S105
    for step in action["runs"]["steps"]:
        if step.get("uses", "").startswith("CodyCBakerPhD/historia-action"):
            assert step["with"]["token"] == "${{ inputs.token }}", step["name"]  # noqa: S105
