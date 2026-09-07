# Agent instructions

## What this repository is

GitHub Actions that run **Historia** from a published container image. The package itself lives in
[`CodyCBakerPhD/historia`](https://github.com/CodyCBakerPhD/historia).

## Versioning

- These actions are versioned by their own interface, never by the **Historia** release they run.
  A **Historia** release changes nothing here.
- `runs.image` names one published image and stays there. Edit it only when cutting the next major
  tag, and choose the image that tag needs rather than whatever released last.
- The composite reaches its siblings by the same major tag it is published under, so those
  references are written once when the tag is cut.
- Cut a new major tag when the actions' inputs or requirements change incompatibly.

## Code style

- Avoid excessive em-dashes, colons, and semicolons in written text such as documentation. Prefer
  breaking into separate, shorter sentences instead.
- Keep inline comments sparse. Only explain non-obvious "why", not "what" the code does.

## Tests

- Run `pytest` before pushing, and `pre-commit run --all-files`.
- Follow assertion style: actual on left, expected on right.
- Always mark AI-generated tests with the `ai_generated` pytest marker.
