---
name: research-reproduce
description: |
  Reproduce a result via INDEPENDENT paths (different implementation, different inputs, different
  library) in parallel, then cross-check: agreement = trust, divergence = a likely bug. Use to
  validate a metric/number before it ships. Triggers: "reproduce X", "cross-check this result/metric",
  "can we replicate this number", "independent check of X", "/research-reproduce". Launches a
  multi-agent Workflow (this skill authorizes the Workflow call).
---

# research-reproduce — independent reproduction + cross-check

Catches the silent-bug class (NaN-drops, off-by-one windows, wrong join keys) by computing the same
result two-or-three independent ways and comparing. The reproducers must NOT read the original number
first — they compute, then report.

## When invoked
1. Get the **result/metric** to reproduce and where its inputs live from args/prompt.
2. Invoke the `Workflow` tool with the script below, passing `args: { result, paths }`.
3. Present: **AGREE / DIVERGE**, the per-path values, and — if they diverge — the most likely cause
   (which the cross-check agent names). Treat divergence as a bug to chase, not noise to average.

## Workflow
```js
export const meta = {
  name: 'research-reproduce',
  description: 'Independent reproduction of a result + cross-check',
  phases: [{ title: 'Reproduce' }, { title: 'Cross-check' }],
}
const REP = { type:'object', required:['path','value','method','notes'], properties:{
  path:{type:'string'}, value:{type:'string'}, method:{type:'string'}, notes:{type:'string'} } }
const result = (args && args.result) || 'the result/metric named in the invocation'
const PATHS = (args && args.paths) || [
  'from the raw inputs via your own independent implementation',
  'from the committed intermediate artifacts (parquet/csv), recomputing the final step',
  'via a different library or formulation that should agree mathematically',
]
const reps = (await parallel(PATHS.map(p => () =>
  agent(`Independently reproduce this result: ${result}. Use this path ONLY: ${p}. Do NOT look up the original author's number before computing — compute it yourself, then report your value and exactly how you got it.`,
    { label: `repro:${p.slice(0,18)}`, phase: 'Reproduce', schema: REP, agentType: 'parity-reproduction-engineer' }))
)).filter(Boolean)
const verdict = await agent(`These are independent reproductions of "${result}". Do they AGREE within reasonable tolerance? If they diverge, the divergence is almost certainly a bug — name the single most probable cause and where to look. Reproductions: ${JSON.stringify(reps)}`,
  { phase: 'Cross-check', schema: { type:'object', required:['agree','spread','likely_cause'], properties:{
    agree:{type:'boolean'}, spread:{type:'string'}, likely_cause:{type:'string'} } } })
return { result, reproductions: reps, verdict }
```
Lead with `verdict.agree` (AGREE/DIVERGE); if DIVERGE, surface `verdict.likely_cause` prominently.
