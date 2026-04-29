# Agent Instructions

This repository explicitly opts into the following installed Codex skills. Use them whenever the task matches.

## Installed Skills

- `frontend-design`
  Path: `~/.codex/skills/frontend-design/SKILL.md`
  Use for any UI, page, component, layout, visual polish, branding, or frontend styling work.

- `fullstack-developer`
  Path: `~/.codex/skills/fullstack-developer/SKILL.md`
  Use for end-to-end web app work, including React or Next.js frontend work, Node.js APIs, auth, database design, Prisma, PostgreSQL, MongoDB, deployment, and full-stack architecture.

- `webapp-testing`
  Path: `~/.codex/skills/webapp-testing/SKILL.md`
  Use for local browser testing, Playwright-based verification, UI flow checks, screenshots, browser log inspection, and debugging dynamic frontend behavior.

- `code-reviewer`
  Path: `~/.codex/skills/code-reviewer/SKILL.md`
  Use whenever the user asks for a review of local changes, staged changes, or a pull request.

## Preferred Combinations

- Use `frontend-design` together with `fullstack-developer` for user-facing product features that include both implementation and design quality.
- Add `webapp-testing` after frontend or full-stack changes that affect browser behavior, user flows, or UI regressions.
- Use `code-reviewer` for explicit review requests, including review-only passes after implementation.

## Working Rules

- State which of the above skill(s) are being used when starting relevant work.
- Follow the workflow and constraints from each selected `SKILL.md` before improvising.
- Preserve existing project conventions unless the user explicitly asks for a redesign or architecture change.
