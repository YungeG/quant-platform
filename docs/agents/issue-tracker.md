# Issue tracker: GitHub

Issues and specs for this repository live in GitHub Issues for `YungeG/quant-platform`. Use the `gh` CLI for issue operations.

- Create: `gh issue create --title "..." --body "..."`
- Read: `gh issue view <number> --comments`
- List: `gh issue list --state open`
- Update labels: `gh issue edit <number> --add-label "..."`
- Comment or close: `gh issue comment <number> --body "..."`; `gh issue close <number>`

## Pull requests as a triage surface

**PRs as a request surface: no.**

## Skill conventions

When a skill says to publish to the issue tracker, create a GitHub issue. Infer the repository from the Git remote.
