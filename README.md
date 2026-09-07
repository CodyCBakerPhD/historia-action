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
      - uses: CodyCBakerPhD/historia-action@v0
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
- uses: CodyCBakerPhD/historia-action/update-github@v0
  with:
    directory: history
    username: CodyCBakerPhD
    recency: "2"
    token: ${{ secrets.GH_PAT }}
```

## Refreshing the board's dates

`project-update-dates` walks every item on the board and writes its start and end date, so its cost scales with the size of the board rather than with recent activity. A board of a few thousand items takes tens of minutes and can exhaust the hourly GraphQL budget before finishing, which is why the composite does not run it.

Populating already sets the dates on each item it adds, so a scheduled update does not need this to keep new items right. What it catches is items whose dates moved after they were added, mostly ones closed since. Run it as its own step when you want that, on a schedule that suits how much the board costs to walk:

```yaml
- uses: CodyCBakerPhD/historia-action/project-update-dates@v0
  with:
    url: https://github.com/users/CodyCBakerPhD/projects/1
    token: ${{ secrets.GH_PAT }}
```
