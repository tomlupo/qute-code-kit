# qute-code-kit

Tom's personal skills & templates library. The `qute-essentials` plugin — the
runtime regime (safety, release, continuity) that other repos adopt — moved to
`tomlupo/qute-platform` (`agent-kit/plugins/qute-essentials/`) on 2026-07-29;
the glossary below describes that regime and is kept here as reference until it
moves with a future plugin doc pass. Terms describe the regime, not any single
repo that installs it.

## Language

### Branches

Four terms below name branches. They frequently coincide and are not synonyms;
conflating them is what let one release policy drift across seven files in a
consuming repo. Where a repo's arrangement makes two of them the same branch,
that is a fact about that repo, not about the words.

**Release branch**:
The branch a version tag is cut on. Named by `conductor.yml`'s `release.branch`
where a repo declares one; `main` by house rule otherwise.
_Avoid_: production branch, stable branch, "main" used as a synonym

**Integration branch**:
The branch feature work merges into before a release is cut from it. Present only
in a two-stage flow; a repo may legitimately have none.
_Avoid_: develop, staging branch, "dev" used as a synonym

**Protected branch**:
A branch the git-workflow guard refuses direct commits and pushes to. A property
of guard policy, not of git — the term does not imply GitHub branch protection,
which is unavailable on the plans these repos use.
_Avoid_: locked branch, restricted branch

**Default branch**:
The branch a fresh clone checks out and that pull requests target unless told
otherwise. A git fact, readable from the remote and independent of any policy.
_Avoid_: trunk, primary branch

**Feature branch**:
A short-lived branch holding one change until its pull request merges. Never a
release target.
_Avoid_: topic branch, working branch

**Two-stage flow**:
A repo whose feature work reaches the release branch through an integration
branch, so bumping and tagging happen on different branches.
_Avoid_: gitflow

**Single-stage flow**:
A repo whose feature work merges directly to the release branch, so bumping and
tagging happen together.
_Avoid_: trunk-based

### Releasing

**Bump**:
Advancing the declared version across a repo's version files and writing the
corresponding changelog entry. One half of a release.
_Avoid_: version commit, releasing (for this act alone)

**Tag**:
An annotated git tag naming a released version. Lightweight tags are never a tag
in this sense — they do not survive `git push --follow-tags`.
_Avoid_: version marker, label

**Release**:
A bump and its tag, both landed and pushed. Incomplete until the tag is reachable
from the release branch.
_Avoid_: deploy, cut (as a noun)

**In-flight bump**:
A bump whose tag does not yet exist — the interval between bumping on the
integration branch and tagging on the release branch.
_Avoid_: pending release, unreleased version

### Sessions

**Attended session**:
A session with a human at the prompt, able to answer a permission request.
_Avoid_: interactive (ambiguous — it also names a tracker lane)

**Unattended session**:
A session with nobody at the prompt. Not determinable from a hook payload: a
backgrounded session and a headless one report the same permission mode.
_Avoid_: headless (narrower — one kind of unattended session), autonomous

**Backgrounded session**:
An unattended session a human may later attach to. Distinct from a headless
one-shot because a permission request will render and wait rather than being
declined.
_Avoid_: detached session, daemon session

### Guards

**Guard**:
A hook shipped with the plugin that inspects a tool call and may refuse it.
Observes Claude tool calls only — never a human's shell, and never git itself.
_Avoid_: hook (broader), check, policy

**Opt-in marker**:
The presence of a per-repo config file, which is what subjects that repo to a
guard. Absence means the guard is a no-op there.
_Avoid_: enable flag, toggle (which names the separate on/off switch)
