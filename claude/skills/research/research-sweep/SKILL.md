---
name: research-sweep
description: |
  Multi-modal evidence sweep + synthesis for an open research question: fan out agents that each
  gather evidence a DIFFERENT way (own data, correlation/benchmark, prior notes via atlas, external
  literature via web, the code), blind to each other, then synthesize a cited, decisive answer that
  surfaces agreements and conflicts. Use for "what do we know about X / what's the right Y". Triggers:
  "research X", "what's the right benchmark/approach for X", "gather the evidence on X", "deep dive X",
  "/research-sweep". Launches a multi-agent Workflow (this skill authorizes the Workflow call).
---

# research-sweep — multi-modal evidence → synthesis

One search angle never finds everything. Each agent is blind to the others and reports only what its
mode shows; the synthesizer reconciles them into a decisive, confidence-rated answer.

## When invoked
1. Get the **question** from args/prompt. Trim the modes to what's relevant (drop "web" for a purely
   internal-data question; drop "atlas" if no vault).
2. Invoke the `Workflow` tool with the script below, passing `args: { question, modes }`.
3. Present the synthesized **answer + confidence**, then the conflicts between angles (those are the
   interesting part), then the per-mode evidence as backup.

## Workflow
```js
export const meta = {
  name: 'research-sweep',
  description: 'Multi-modal evidence sweep + synthesis for a research question',
  phases: [{ title: 'Gather' }, { title: 'Synthesize' }],
}
const EV = { type:'object', required:['mode','findings','confidence'], properties:{
  mode:{type:'string'}, findings:{type:'string'}, confidence:{type:'string', enum:['high','medium','low']} } }
const question = (args && args.question) || 'the question named in the invocation'
const MODES = (args && args.modes) || [
  'the data itself — compute from the fund/return series, do not assume',
  'correlation / benchmark-ETF evidence',
  'prior research + decisions in the vault (use atlas-query)',
  'external literature (use web search)',
  'the existing code / implementation',
]
// The "data itself" mode is routed to the pit-data-auditor so the data angle is a typed audit
// (PIT/provenance/integrity) rather than a blank subagent. Falls back gracefully where the agent
// isn't deployed. Deployed via agent-kit/.claude/agents → each lab repo.
const modeAgentType = m => /the data itself|from the fund\/return series|own data/i.test(m)
  ? 'pit-data-auditor' : undefined
const evidence = (await parallel(MODES.map(m => () =>
  agent(`Investigate "${question}" using ONLY this mode: ${m}. Report what THIS angle shows and your confidence; stay blind to other angles — do not speculate beyond your mode.`,
    { label: `mode:${m.slice(0,16)}`, phase: 'Gather', schema: EV, agentType: modeAgentType(m) }))
)).filter(Boolean)
const report = await agent(`Synthesize a cited, DECISIVE answer to "${question}" from this multi-angle evidence. State the answer, your confidence, and — most important — where the angles CONFLICT (and which to trust). Evidence: ${JSON.stringify(evidence)}`,
  { phase: 'Synthesize', schema: { type:'object', required:['answer','confidence','conflicts'], properties:{
    answer:{type:'string'}, confidence:{type:'string'}, conflicts:{type:'string'} } } })
return { question, evidence, report }
```
Lead with `report.answer` + confidence; surface `report.conflicts` before the raw evidence.
