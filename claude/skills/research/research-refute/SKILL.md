---
name: research-refute
description: |
  Adversarially verify a research finding by spawning a panel of skeptics that each try to BREAK
  it via a DIFFERENT failure mode (lookahead, overfitting, regime-dependence, data quality,
  multiple-testing, fair-baseline). Use before trusting a quant/data result. Triggers: "refute X",
  "is this finding real?", "stress-test this claim/signal/result", "verify this before I trust it",
  "/research-refute". Launches a multi-agent Workflow (this skill authorizes the Workflow call).
---

# research-refute — adversarial verification panel

Research's failure mode is *plausible-but-wrong*, not incomplete. This panel kills it before it
becomes a finding: N skeptics, each on a distinct failure lens, prompted to refute. Keep the
finding only if it survives (no fatal/serious refutation).

## When invoked
1. Get the **claim** + where its **evidence/code** lives from the user's args/prompt. If the claim
   is vague, ask exactly one clarifying question (what's asserted + which script/report/parquet backs it).
2. Invoke the `Workflow` tool with the script below, passing `args: { claim, evidence }`. Scale lens
   count to effort (low → 3 lenses, high → all 6 + 2 generalists).
3. Present: lead with **SURVIVES / REFUTED**, then the fatal/serious refutations (with the fix each
   implies), then the full panel. Never bury a fatal verdict.

## Workflow
```js
export const meta = {
  name: 'research-refute',
  description: 'Adversarial verification of a research finding',
  phases: [{ title: 'Refute' }],
}
const VERDICT = { type:'object', required:['lens','refuted','reason','severity'], properties:{
  lens:{type:'string'}, refuted:{type:'boolean'}, reason:{type:'string'},
  severity:{type:'string', enum:['fatal','serious','minor','none']},
  suggested_fix:{type:'string'} } }
const claim = (args && args.claim) || 'the finding stated in the invocation'
const evidence = (args && args.evidence) || 'the lab worktree / report referenced in the finding'
const LENSES = [
  'lookahead / data-snooping bias — is any future information leaking into the signal or labels?',
  'overfitting / parameter sensitivity — does it survive a small change to every threshold/param?',
  'regime-dependence / subsample instability — does it hold out-of-window and per-regime, or only full-sample?',
  'data quality — survivorship, NaN-drops, stale/frozen prices, a single missing week killing rolling stats',
  'multiple-testing / p-hacking — how many variants were tried? does it survive a deflated-Sharpe / Bonferroni haircut?',
  'fair baseline — is it beating an honest baseline (passive ETF, naive rule), or just collecting beta?',
]
// Typed skeptics carry the checklist (deployed via agent-kit/.claude/agents → each lab repo).
// The data-quality lens goes to the pit-data-auditor (input/provenance forensics); every other
// lens goes to the quant-verifier (lookahead/overfit/baseline/multiple-testing checklist). Falls
// back gracefully if a repo lacks the typed agents.
// Widened so a reworded data lens (point-in-time, provenance, universe, mcap, volume) still routes
// to the data auditor rather than silently falling through to the verifier.
const lensAgentType = lens =>
  /data quality|survivorship|stale|frozen|point.?in.?time|provenance|universe|mcap|market.?cap|volume|delisting/i.test(lens)
    ? 'pit-data-auditor' : 'quant-verifier'
const verdicts = (await parallel(LENSES.map(lens => () =>
  agent(`You are a hostile quant reviewer. Try HARD to REFUTE this finding through the single lens "${lens}". Read the referenced code/data; do not take the author's word. Default refuted=true if you find any plausible failure on this lens. Finding: ${claim}. Evidence location: ${evidence}.`,
    { label: `refute:${lens.split(' ')[0]}`, phase: 'Refute', schema: VERDICT, agentType: lensAgentType(lens) }))
)).filter(Boolean)
const killers = verdicts.filter(v => v.refuted && (v.severity === 'fatal' || v.severity === 'serious'))
return { claim, survives: killers.length === 0, killers, verdicts }
```
After it returns: state SURVIVES/REFUTED, list `killers` first (each with its `suggested_fix`), then the rest. If it survives, say what *would* still strengthen it.
