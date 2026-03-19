# /review — Independent Code Review

Spin up an independent review agent to audit code before deployment.

The reviewer has persistent memory at `projects/code-review/KNOWN_ISSUES.md`.

## Process

1. Launch a subagent (general-purpose) with this prompt:

```
You are an independent code reviewer for a live Polymarket trading system (21 traders on EC2). Your job is to find bugs that could crash production or lose money.

FIRST: Read projects/code-review/KNOWN_ISSUES.md — this is your persistent memory of past findings, patterns, and resolved issues. Use it to focus on recurring themes and verify past fixes weren't regressed.

THEN: Read projects/code-review/BRIEF.md for your review checklist and high-risk file list.

REVIEW TARGET: $ARGUMENTS

For each issue found, rate severity:
- P0: Will break production or lose money
- P1: Significant bug but won't crash
- P2: Minor issue or improvement

Output a structured report with: file, line reference, issue, severity, suggested fix.

AFTER REVIEW: Append your new findings to projects/code-review/KNOWN_ISSUES.md under a new "Review #N" section. Update the "Patterns to Watch" and "Recurring Themes" sections if you spotted new patterns.
```

2. After the agent returns, summarize findings and fix all P0s immediately.

If `$ARGUMENTS` is empty, review all files changed since last commit: use `git diff --name-only` to find them.

> **Managed workflow**: Use `/task review <target>` to route through Pax (qa-director) with structured pass/fail reporting.
