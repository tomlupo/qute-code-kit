<!-- prose source: shipping v1 — /setup-qute-repo writes this as a CLAUDE.md section; it is NOT stamped as a .claude/rules file (TOM-386) -->
# Shipping

- `/ship` is the **only** version writer: it bumps the version, regenerates
  `CHANGELOG.md` from Conventional Commits, and creates the annotated
  `vX.Y.Z` tag. Never bump versions or edit the changelog by hand, and never
  add a CI workflow that bumps versions.
- Release only from the default branch, from a clean tree, after tests pass.
- If this repo's shipping mode is "none" (lab / simple repo), deliverables go
  to `reports/` and no versions or tags are cut.
