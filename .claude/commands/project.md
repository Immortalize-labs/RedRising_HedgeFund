# /project — Load Project Context

Load a project's BRIEF.md and LOG.md to get up to speed on a workstream.

Usage: `/project <name>` — e.g., `/project ui-dashboard`, `/project risk-infra`

Read the project brief and log from `projects/$ARGUMENTS/`:

1. Read `projects/$ARGUMENTS/BRIEF.md` — goals, scope, constraints, resources
2. Read `projects/$ARGUMENTS/LOG.md` — what's been done, decisions made
3. Read `projects/README.md` — project rules

Then summarize:
- Current status and what's been done
- What's next / open items
- Any blockers or cross-project conflicts noted in the log

If `$ARGUMENTS` is empty, list all projects from `projects/README.md`.

Do NOT start working on anything — just load context and report status. Wait for instructions.
