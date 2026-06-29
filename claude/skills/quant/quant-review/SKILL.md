---
name: quant-review
description: |
  Pre-PR review orchestrator for quant / data-pipeline code. Path-routes a diff
  against the integration branch to scoped reviewers — built-in Code Reviewer
  (always), conditional Data Engineer / Security Engineer, plus any custom
  project reviewers (methodology / experiment / runbook drift) the repo defines.
  Synthesizes findings as PR-comment-ready markdown with severity tags.

  Use BEFORE opening a PR, before a release/promotion step, or whenever asked to
  "review this branch", "check before merging", "is this ready to PR", "review
  my changes", "quant review", "check for spec drift", "verify methodology
  match".

  Detects silent drift: model code changed without its methodology doc bumped;
  pipeline code changed without its runbook bumped; naive Python loops in
  hot-path quant code (iterrows over time index, per-date weight-engine calls,
  misleading "vectorized" docstrings).

  Mandatory inputs: current branch is a non-integration working branch; the
  integration branch is reachable as merge-base. Skips cleanly with a one-line
  "no quant code in diff" when no relevant paths are touched.
---

# /quant-review

Pre-PR review orchestrator for quant / data-pipeline code. You are the
orchestrator; specialist subagents do narrow audits and you synthesize. Output
is **read-only advice** — you never push, open PRs, or edit files.

## Adapting to your project (read first)

This skill ships with sensible defaults but is meant to be parameterized. Resolve
these from the repo before running; if the repo doesn't define them, use the
defaults in brackets.

| Knob | How to resolve | Default |
|---|---|---|
| **Integration branch** | `git symbolic-ref --short refs/remotes/origin/HEAD` (strip `origin/`), or a repo convention doc | `main` (then `master`, then `dev`) |
| **Working-branch rule** | any branch ≠ integration branch | current branch if ≠ integration |
| **Routing table** | project layout — map changed paths to reviewers (see template below) | the generic table below |
| **Custom reviewers** | subagent types the repo defines (e.g. `methodology-reviewer`); skip if none | none → built-ins only |
| **Contract docs** | review-rule files the reviewers must read (`.claude/rules/*.md`, `CONTRIBUTING.md`, style guides) | none → reviewers use their own judgment |
| **Hot-paths list** | perf-critical modules where naive time-loops are BLOCKER | infer from the routing table's model/pipeline lanes |

A worked dm-evo example is in the **Reference: example project mapping** section
at the bottom — copy it as a starting point and edit the path patterns.

## When to use

- Before opening any PR from a non-integration working branch
- Before a release / promotion step
- When the user says: "review this branch", "check before merging",
  "is this ready to PR", "review my changes", "quant review",
  "check for spec drift", "verify methodology match"

## Process

### 1. Pre-flight

Resolve the integration branch, confirm we're on a working branch, confirm
merge-base reachability. Abort cleanly (exit 0) if pre-conditions aren't met.

```bash
# Resolve integration branch (override per "Adapting" table)
intb=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##')
for cand in "$intb" main master dev; do
  [ -n "$cand" ] && git rev-parse --verify "$cand" >/dev/null 2>&1 && intb="$cand" && break
done

branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$branch" = "$intb" ]; then
  echo "On integration branch '$intb'. Switch to a working branch and re-run."
  exit 0
fi

if ! git merge-base "$intb" HEAD >/dev/null 2>&1; then
  echo "Cannot reach '$intb' as merge-base. Aborting."
  exit 0
fi

echo "Branch: $branch"
echo "Integration: $intb"
echo "Merge base: $(git merge-base "$intb" HEAD)"
```

### 2. Diff scan

```bash
git diff "$intb"...HEAD --name-only          # changed files → routing
git log --format='%H%n%B%n---' "$intb"..HEAD # commit messages → noop directives
git diff "$intb"...HEAD --stat               # shape (inspect for parameter changes)
```

### 3. Route reviewers

Walk the changed-file list; classify each path per the routing table. Use the
project's table if it defines one; otherwise this generic default:

| Path pattern (edit per project) | Fires |
|---|---|
| model/library code (`src/**`, `lib/**`) | Code Reviewer; + **custom methodology reviewer** if defined (silent-drift if the paired methodology/spec doc is NOT also touched; vectorization audit if file is a hot path) |
| methodology / spec docs | custom methodology reviewer (if defined) |
| research experiments (`research/**/experiments/**`) | custom experiment reviewer (if defined; frontmatter + provenance + naive-backtest scan) |
| pipeline / orchestration code (`pipelines/**`) | Code Reviewer; custom runbook reviewer if defined (silent-drift if runbook NOT touched); + methodology reviewer if file is a hot path |
| operational runbooks / ops docs | custom runbook reviewer (if defined) |
| any code change | **Code Reviewer (built-in, always)** |
| data / ETL paths (`pipelines/datasets/**`, `**/etl/**`) | Data Engineer (built-in) |
| diff matches `\.env\|KEY\|TOKEN\|SECRET\|credentials` | Security Engineer (built-in) |

**Hot-path override**: any changed file in the project's hot-paths list ALSO
fires the methodology reviewer (with that file in scope) on top of its normal
owner — so vectorization findings always reach a domain-aware reviewer no matter
which directory the file lives in.

**Cap: 5 reviewers max per invocation.** If routing fires 6, drop Security
Engineer (rarest, most specialized — user can re-run focused on secrets) and
surface "Security Engineer skipped due to cap" as a NIT.

If no reviewers match (no quant/pipeline code in diff), output exactly:

```
No quant code in diff. Nothing to review.
```

and stop.

### 4. Parse noop directives

Scan commit messages for lines:

```
quant-review-noop: <reviewer-name> — <reason>
```

(Em-dash `—` or two-hyphen `--` both accepted.) Build a map
`{reviewer-name → [(commit_sha, reason), ...]}` to demote findings later.

### 5. Suspicious-noop pre-check

If any noop directive targets the methodology or runbook reviewer, scan the diff
for parameter-shaped changes:

- Numeric literals: `=\s*[-]?\d+\.\d+` in code or config paths
- Lookback / window constants: `lookback\s*=`, `window\s*=`, `period\s*=`
- Polarity flips: `\* -1`, `* (-1)`, sign flips on signal columns
- Locked-param identifiers listed in any methodology/spec doc's parameters table

If matched → record a `SUSPICIOUS_NOOP` warning to surface in output (does NOT
block):

> The methodology noop directive may be hiding a real change: parameter-shaped
> diff at `<file>:<line>`. Review whether the noop is still appropriate.

### 6. Parallel dispatch

In a SINGLE message, fire ALL relevant Agent calls in parallel — do not sequence
them. For each subagent provide: the full diff (from step 2), their scoped file
slice, the contract docs they should read (project knob), the paired doc(s) to
audit (diff path → doc path), and their output format.

**Custom reviewers** (only if the project defines these subagent types):
`methodology-reviewer`, `experiment-reviewer`, `runbook-reviewer`.
**Built-in reviewers**: `Code Reviewer` (any code change), `Data Engineer`
(data/ETL paths), `Security Engineer` (secret patterns, subject to cap).

Example dispatch prompt (custom methodology reviewer):

> You are reviewing the diff between `<integration>` and HEAD on branch
> `<branch>`. Files in your scope:
> - `<model-file-a>` (modified)
> - `<hot-path-file>` (modified — HOT PATH; run the vectorization scan)
>
> No paired methodology/spec doc change in this diff — silent-drift check
> applies (default MAJOR).
>
> Read your contract docs first: `<project contract docs>`. Then read the
> paired spec doc; walk its parameters table and verify each value matches its
> cited Location. Run the naive-time-loop / "vectorized"-docstring scan over the
> hot-path file.
>
> Diff context:
> ```
> <relevant diff hunks>
> ```
> Output findings in your format. Begin.

Example dispatch prompt (built-in Code Reviewer):

> You are reviewing the diff between `<integration>` and HEAD on branch
> `<branch>`. Standard scope (correctness, maintainability, security,
> performance). If the project ships review-contract docs, read them first:
> `<project contract docs>`. Hot paths are covered by the methodology reviewer
> for naive-loop / vectorization findings — defer there, don't double-report.
> Your unique value: pandas/numpy idiom misuse, unsafe casts, unhandled NaN,
> off-by-one in date slicing, silent type widening, resource leaks, etc.
>
> Diff context:
> ```
> <relevant diff hunks>
> ```

### 7. Apply noop directives

- If a finding's reviewer is in the noop map AND severity ≤ `MAJOR` → demote to
  `ACKNOWLEDGED`, attach the noop reason + citing commit.
- BLOCKERs cannot be demoted (naive backtest loops, leakage, import-direction
  violations don't get hand-waved away).

### 8. Cluster overlapping findings

Group by `(file, line)`. If ≥2 reviewers concur on the same location: emit ONE
entry, list concurring reviewers in `*Concur:* <list>`, severity = max.

### 9. Rank and format output

```markdown
# /quant-review · <branch-name>

**Reviewers fired:** <comma-separated list>

<if SUSPICIOUS_NOOP detected>
> ⚠ **Suspicious noop:** <warning text>
</if>

## Blockers (N)
- **[<reviewer>]** `<file>:<line>` — <finding>. <fix>. Cite: `<contract-doc>`.
  - *Concur: <other reviewers>* (only if cluster)

## Majors (N)
...same shape...

## Minors / Nits (N)
...same shape...

## Acknowledged (N)
- **[<reviewer>]** noop'd by commit `<sha>`: "<reason>" — <original finding>

## Summary
<N> reviewers fired. **<N> blocker(s)** — PR not ready.
                  / **0 blockers, M majors** — fix-then-merge.
                  / **All reviewers passed.** PR ready for human review.
```

If zero findings across all reviewers, the entire output is:

```markdown
# /quant-review · <branch-name>

**Reviewers fired:** <list>

All reviewers passed. PR ready for human review.
```

### 10. Exit signal

- No surviving BLOCKERs after noop application → success (PR can proceed).
- Any surviving BLOCKER → render the markdown, then state:
  `Exit signal: BLOCKER — do not merge until resolved.`

## Anti-patterns

| Don't | Do |
|---|---|
| Run `git push` or `gh pr create` | Output is read-only; the user opens the PR |
| Auto-edit files based on findings | Findings are advisory; the user decides |
| Fire all reviewers regardless of diff | Routing exists for a reason — narrow scope = signal |
| Blend reviewer outputs into prose | Keep findings discrete and citation-bearing |
| Generate >5 blocks of synthesis on a clean PR | Zero findings → one-line "All reviewers passed" |
| Sequence Agent calls one-by-one | Single message, parallel dispatch — that's the point |
| Re-derive rules from training data | Read the project's contract docs first |
| Demote a BLOCKER via noop | BLOCKERs are intentionally non-demotable |
| Hardcode another repo's paths | Resolve the routing table from THIS repo's layout |

## Reference: example project mapping (dm-evo)

A concrete instantiation, for reference when adapting the knobs:

- **Integration branch:** `dev` (working branches `feat/{alias}-*`,
  `research/{alias}-*`; runs before `/promote` and `/ship`).
- **Contract docs:** `.claude/rules/methodology.md`,
  `.claude/rules/quant-coding.md`, `.claude/rules/runbooks.md`,
  `.claude/rules/general-rules.md`.
- **Custom reviewers:** `methodology-reviewer` (src + methodology drift),
  `experiment-reviewer` (research experiments), `runbook-reviewer` (pipelines +
  runbooks).
- **Routing:** `src/{model}/**` → methodology-reviewer; `docs/methodology/**` →
  methodology-reviewer; `research/{model}/experiments/**` → experiment-reviewer;
  `pipelines/**` → runbook-reviewer; `pipelines/datasets/**` → Data Engineer.
- **Hot paths:** `src/taa_signals/`, `src/fund_scoring/`, `src/vectorbt_tools/`,
  `pipelines/tactical_signals/`, `pipelines/fund_selection/`.
