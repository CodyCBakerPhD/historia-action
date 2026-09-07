# historia-action

GitHub Actions that run [**Historia**](https://historia.readthedocs.io/en/latest/) from a pinned container image.

## The whole process in one step

`CodyCBakerPhD/historia-action` is a composite action that runs the entire scheduled update for a work history data repository:

```yaml
name: Update work history data

on:
  workflow_dispatch:
  schedule:
    - cron: "0 0 * * *"

jobs:
  Update:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - uses: CodyCBakerPhD/historia-action@v2
        with:
          username: CodyCBakerPhD
          project-url: https://github.com/users/CodyCBakerPhD/projects/1
          token: ${{ secrets.GH_PAT }}
```

It checks out the data repository, fetches recent activity, commits and pushes the new content, populates the project board, and force-pushes a compressed archive to a `dist` branch.

Refreshing the dates already on the board is not part of it. See [Refreshing the board's dates](#refreshing-the-boards-dates).

| Input | Required | Default | Description |
| --- | --- | --- | --- |
| `username` | yes | | GitHub username whose activity is tracked. |
| `project-url` | yes | | URL of the GitHub Project v2 to keep up to date. |
| `token` | yes | | Personal access token that reads the activity and writes the board. See [Setup](#setup). |
| `recency` | no | `2` | Number of most recent days to fetch. |
| `directory` | no | `history` | Directory in the repository holding the JSON files. |
| `placeholder` | no | `180` | Days after creation to use as a placeholder end date for open items. |
| `archive-branch` | no | `dist` | Orphan branch for the `content.tar.gz` archive. Empty string skips it. |
| `commit-message` | no | `update` | Message for each run's commit. |

## Setup

The action needs one personal access token, set as the `GH_PAT` secret, plus the workflow's own `GITHUB_TOKEN` for the pushes.

Which kind of token depends on who owns the project board:

1. **Board owned by an organization (recommended).** Create a [fine-grained token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-fine-grained-personal-access-token).

   Set:

   a. `Resource owner:` to the organization.

   b. `Repository access:` to the repositories to track. Choose all public repositories, or select them individually to include private ones.

   c. `Repository permissions:` with `Issues` and `Pull requests` as `Access: read-only`.
     - Note: `Metadata` will automatically be included as `Access: Read-only`.

   d. `Organization permissions:` with `Projects` as `Access: Read and write`.

   This token reads only the repositories you selected, cannot write to any of them, and sees nothing private outside that organization.

2. **Board owned by your user account.** Create a [classic token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-personal-access-token-classic).

   Set:

   a. The full `project` scope, plus full `repo` scope if any repository you want to track is private; otherwise, `repo: public_repo` is sufficient for only public repositories.

   Unfortunately, GitHub offers no fine-grained permission for user-owned Projects, and `repo` cannot be limited to selected repositories or to reading. We recommend using an organization to avoid this.

## The individual steps

The composite is built from three narrower actions, each wrapping one command. Use them directly to run only part of the process, or to insert steps of your own in between. The [expanded workflow](https://historia.readthedocs.io/en/latest/tutorial/manual-automation-setup.html) shows them wired together.

| Action | Command it runs |
| --- | --- |
| `update-github` | `historia update github` |
| `project-populate` | `historia project populate` |
| `project-update-dates` | `historia project update dates` |

```yaml
- uses: CodyCBakerPhD/historia-action/update-github@v2
  with:
    directory: history
    username: CodyCBakerPhD
    recency: "2"
    token: ${{ secrets.GH_PAT }}
```

## Refreshing the board's dates

Populating already sets the dates on each item it adds, so a scheduled update does not need this to keep new items right. What it catches is items whose dates moved after they were added, mostly ones closed since. That is worth its own step rather than a place in the composite:

```yaml
- uses: CodyCBakerPhD/historia-action/project-update-dates@v2
  with:
    url: https://github.com/users/CodyCBakerPhD/projects/1
    recency: "7"
    token: ${{ secrets.GH_PAT }}
```

| Input | Required | Default | Description |
| --- | --- | --- | --- |
| `url` | yes | | URL of the GitHub Project v2 whose dates are refreshed. |
| `token` | yes | | Personal access token that writes the board. See [Setup](#setup). |
| `recency` | no | `2` | Only update items created or closed within this many most recent days. |
| `placeholder` | no | `180` | Days after creation to use as a placeholder end date for open items. |

`recency` is what makes this affordable. Each item costs two GraphQL mutations, so a pass over a board of a few thousand items spends tens of minutes and the whole hourly budget, and an item untouched over the window is only ever written back the value it already holds. Widening the window past the schedule's interval makes the step self-healing, since a skipped or failed run leaves nothing permanently stale.

A full pass over every item is a different job. It is what a first run needs, or a board whose items predate the date fields, and it is deliberate enough to run by hand:

```bash
docker run --rm -e GITHUB_TOKEN ghcr.io/codycbakerphd/historia:0.11.1 \
  project update dates --url https://github.com/users/CodyCBakerPhD/projects/1
```
