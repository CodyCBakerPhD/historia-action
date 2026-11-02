import os
import pathlib
import re
import shutil
import subprocess

import pytest
import yaml

_REPOSITORY_ROOT = pathlib.Path(__file__).parent.parent
_COMPOSITE_ACTION_PATH = _REPOSITORY_ROOT / "action.yml"
_README_PATH = _REPOSITORY_ROOT / "README.md"
_VERSION_PATH = _REPOSITORY_ROOT / "VERSION"
_ACTION_PATHS = sorted(_REPOSITORY_ROOT.glob("*/action.yml"))
_IMAGE_PATTERN = re.compile(r"^docker://ghcr\.io/codycbakerphd/historia:(\d+\.\d+\.\d+)$")
_ANY_SELF_REFERENCE_PATTERN = re.compile(r"CodyCBakerPhD/historia-action(?:/[a-z-]+)?@(v\d+)")

# The tag this tree is meant to be published under. Every reference to this repository, in the
# composite and in the README, must name it, and the release workflow checks the tag against it.
_MAJOR_TAG = _VERSION_PATH.read_text(encoding="utf-8").strip()


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

    Only an explicit `X.Y.Z` counts. A floating tag such as `latest` or `dev` would make a published
    action run whatever was pushed to that tag most recently, so a workflow pinned to one tag of this
    repository would silently change under it, which is the whole thing these pins exist to prevent.
    """
    images = [yaml.safe_load(path.read_text(encoding="utf-8"))["runs"]["image"] for path in _ACTION_PATHS]
    matches = [_IMAGE_PATTERN.match(image) for image in images]

    assert all(matches), f"every image must be pinned to an explicit version, got {images}"
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

    The siblings share the composite's major tag, so these references are rewritten only when
    `VERSION` names a new one. A package version here would have to be bumped on every release.

    The expected tag comes from `VERSION` rather than from a literal here. A literal only proves the
    references agree with this test, which is satisfied just as well by every one of them naming the
    previous tag.
    """
    steps = _composite_action()["runs"]["steps"]
    historia_refs = [step["uses"] for step in steps if step.get("uses", "").startswith("CodyCBakerPhD/historia-action")]

    expected = [
        f"CodyCBakerPhD/historia-action/{name}@{_MAJOR_TAG}" for name in ("update-github", "project-populate")
    ]
    assert historia_refs == expected


@pytest.mark.ai_generated
def test_every_self_reference_names_the_version_being_published() -> None:
    """
    Nothing in the repository may point at a tag other than the one `VERSION` names.

    A reference left on the previous tag resolves and runs, and keeps running what it ran the day it
    was cut, so neither a test of the files against each other nor a workflow run catches it.

    What it costs is independence. A tag whose composite reaches outside itself is only as stable as
    the tag it reaches for, and major tags move. Move or delete the older one and every workflow on
    the newer one changes with it, having pinned a tag that was never touched.
    """
    sources = [_COMPOSITE_ACTION_PATH, _README_PATH, *_ACTION_PATHS]

    stale = {
        f"{path.relative_to(_REPOSITORY_ROOT)}: {tag}"
        for path in sources
        for tag in _ANY_SELF_REFERENCE_PATTERN.findall(path.read_text(encoding="utf-8"))
        if tag != _MAJOR_TAG
    }

    assert stale == set()


@pytest.mark.ai_generated
def test_version_file_names_a_major_tag() -> None:
    """`VERSION` is compared against the release tag, so it has to be shaped like one."""
    assert re.fullmatch(r"v\d+", _MAJOR_TAG) is not None, _MAJOR_TAG


@pytest.mark.ai_generated
def test_composite_action_leaves_the_date_refresh_out() -> None:
    """
    `project-update-dates` walks the whole board, so its cost follows board size, not recent activity.

    A board of a few thousand items exhausts the hourly GraphQL budget before the pass finishes.
    Populating already dates the items it adds, so a scheduled update does not need the refresh, and a
    workflow that wants it can run the action on a schedule of its own.
    """
    steps = _composite_action()["runs"]["steps"]
    historia_refs = [step.get("uses", "") for step in steps]

    assert f"CodyCBakerPhD/historia-action/project-update-dates@{_MAJOR_TAG}" not in historia_refs


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
def test_composite_action_commits_what_populating_rewrites() -> None:
    """
    Populating rewrites the records of items that moved since they were recorded.

    The new content is committed before populating, so a failed populate cannot cost it. The rewrites
    therefore need a commit of their own afterwards, or they are discarded with the runner.
    """
    steps = _composite_action()["runs"]["steps"]
    step_names = [step["name"] for step in steps]

    assert step_names.index("Commit and push new content") < step_names.index("Populate the GitHub project")
    assert step_names.index("Commit and push rewritten records") == step_names.index("Populate the GitHub project") + 1


@pytest.mark.ai_generated
def test_composite_action_publishes_the_archive_through_dist_bundle() -> None:
    """
    The archive is the collected data alone, as `content.tar.gz` on an orphan branch, skipped when the branch is empty.

    `dist-bundle-action` builds its commit without checking the branch out, so the archive no longer has to come last.
    It is pinned to a major tag like any other action rather than to this repository's `VERSION`.
    """
    steps = {step["name"]: step for step in _composite_action()["runs"]["steps"]}
    archive = steps["Push the compressed archive"]

    assert re.fullmatch(r"CodyCBakerPhD/dist-bundle-action@v\d+", archive["uses"]) is not None, archive["uses"]
    assert archive["if"] == "inputs.archive-branch != ''"
    assert archive["with"] == {"paths": "${{ inputs.directory }}", "branch": "${{ inputs.archive-branch }}"}


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


_FAKE_GH = """#!/usr/bin/env bash
printf '%s\\x1f' "$@" >> "$FAKE_GH_LOG"
printf '\\x1e' >> "$FAKE_GH_LOG"
case "$1 $2" in
  "issue list")
    if [ -n "${FAKE_GH_FAIL:-}" ]; then exit 1; fi
    printf '%s' "${FAKE_OPEN_ISSUE:-}"
    ;;
  "issue view")
    printf '%s' "${FAKE_EARLIER_COMMENTS:-0}"
    ;;
esac
"""


def _run_rate_limit_tracking(*, tmp_path: pathlib.Path, environment: dict[str, str]) -> tuple[str, list[list[str]]]:
    """Run the tracking step's script as GitHub runs a composite `bash` step, with a fake `gh` on the path."""
    steps = {step["name"]: step for step in _composite_action()["runs"]["steps"]}
    script_path = tmp_path / "track.sh"
    script_path.write_text(steps["Track rate limiting"]["run"], encoding="utf-8")
    bin_directory = tmp_path / "bin"
    bin_directory.mkdir()
    fake_gh = bin_directory / "gh"
    fake_gh.write_text(_FAKE_GH, encoding="utf-8")
    fake_gh.chmod(0o755)
    log_path = tmp_path / "gh.log"
    log_path.write_text("", encoding="utf-8")

    env = {
        "PATH": f"{bin_directory}{os.pathsep}{os.environ['PATH']}",
        "FAKE_GH_LOG": str(log_path),
        "GITHUB_SERVER_URL": "https://github.com",
        "GITHUB_REPOSITORY": "octocat/history",
        "GITHUB_RUN_ID": "42",
        "LABEL": "historia-rate-limit",
        "USERNAME": "octocat",
        **environment,
    }
    bash = shutil.which("bash")
    assert bash is not None
    result = subprocess.run(  # noqa: S603
        [bash, "--noprofile", "--norc", "-eo", "pipefail", str(script_path)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    calls = [entry.split("\x1f")[:-1] for entry in log_path.read_text(encoding="utf-8").split("\x1e")[:-1]]
    return result.stdout, calls


@pytest.mark.ai_generated
def test_composite_action_passes_the_rate_limit_on() -> None:
    action = _composite_action()
    steps = {step["name"]: step for step in action["runs"]["steps"]}
    update_github = yaml.safe_load((_REPOSITORY_ROOT / "update-github" / "action.yml").read_text(encoding="utf-8"))

    assert "rate-limited" in update_github["outputs"]
    assert steps["Update work history data"]["id"] == "update"
    assert action["outputs"]["rate-limited"]["value"] == "${{ steps.update.outputs.rate-limited }}"


@pytest.mark.ai_generated
def test_composite_action_tracks_rate_limits_after_committing_with_the_workflow_token() -> None:
    """The tracking runs once the fetched data is committed, and before populating, which can fail on its own."""
    steps = _composite_action()["runs"]["steps"]
    step_names = [step["name"] for step in steps]
    tracking = {step["name"]: step for step in steps}["Track rate limiting"]

    assert step_names.index("Track rate limiting") == step_names.index("Commit and push new content") + 1
    assert step_names.index("Track rate limiting") < step_names.index("Populate the GitHub project")
    assert tracking["if"] == "inputs.rate-limit-label != '' && steps.update.outputs.rate-limited != ''"
    assert tracking["env"]["GH_TOKEN"] == "${{ github.token }}"  # noqa: S105
    assert "${{" not in tracking["run"]


@pytest.mark.ai_generated
@pytest.mark.parametrize(
    ("environment", "expected_commands"),
    [
        pytest.param(
            {"RATE_LIMITED": "true", "FAKE_OPEN_ISSUE": ""},
            [["issue", "list"], ["label", "create"], ["issue", "create"]],
            id="first-rate-limited-run-opens-the-issue",
        ),
        pytest.param(
            {"RATE_LIMITED": "true", "FAKE_OPEN_ISSUE": "7", "FAKE_EARLIER_COMMENTS": "2"},
            [["issue", "list"], ["issue", "view"], ["issue", "comment"]],
            id="later-rate-limited-run-comments",
        ),
        pytest.param(
            {"RATE_LIMITED": "false", "FAKE_OPEN_ISSUE": "7"},
            [["issue", "list"], ["issue", "close"]],
            id="clean-run-closes-the-issue",
        ),
        pytest.param(
            {"RATE_LIMITED": "false", "FAKE_OPEN_ISSUE": ""},
            [["issue", "list"]],
            id="clean-run-without-an-issue-does-nothing",
        ),
    ],
)
def test_rate_limit_tracking_keeps_one_issue_open_while_runs_are_rate_limited(
    tmp_path: pathlib.Path,
    environment: dict[str, str],
    expected_commands: list[list[str]],
) -> None:
    stdout, calls = _run_rate_limit_tracking(tmp_path=tmp_path, environment=environment)

    assert [call[:2] for call in calls] == expected_commands
    assert "::warning" not in stdout
    for call in calls:
        assert call[call.index("--repo") + 1] == "octocat/history"


@pytest.mark.ai_generated
def test_rate_limit_tracking_mentions_the_user_and_counts_consecutive_runs(tmp_path: pathlib.Path) -> None:
    (tmp_path / "first").mkdir()
    (tmp_path / "later").mkdir()

    _, first_calls = _run_rate_limit_tracking(
        tmp_path=tmp_path / "first",
        environment={"RATE_LIMITED": "true", "FAKE_OPEN_ISSUE": ""},
    )
    _, later_calls = _run_rate_limit_tracking(
        tmp_path=tmp_path / "later",
        environment={"RATE_LIMITED": "true", "FAKE_OPEN_ISSUE": "7", "FAKE_EARLIER_COMMENTS": "2"},
    )

    create = first_calls[-1]
    issue_body = create[create.index("--body") + 1]
    assert create[create.index("--label") + 1] == "historia-rate-limit"
    assert issue_body.startswith("<!-- historia-rate-limit -->\n@octocat, ")
    assert "https://github.com/octocat/history/actions/runs/42" in issue_body

    comment = later_calls[-1]
    assert comment[2] == "7"
    comment_body = comment[comment.index("--body") + 1]
    assert comment_body.startswith("<!-- historia-rate-limit -->\n")
    assert "That makes 4 runs in a row." in comment_body


@pytest.mark.ai_generated
def test_rate_limit_tracking_never_fails_the_run(tmp_path: pathlib.Path) -> None:
    """Without `issues: write` the listing fails, which must warn rather than fail a run that saved its data."""
    stdout, calls = _run_rate_limit_tracking(
        tmp_path=tmp_path,
        environment={"RATE_LIMITED": "true", "FAKE_GH_FAIL": "1"},
    )

    assert [call[:2] for call in calls] == [["issue", "list"]]
    assert stdout.startswith("::warning title=Rate limit tracking skipped::Could not list the issues.")
