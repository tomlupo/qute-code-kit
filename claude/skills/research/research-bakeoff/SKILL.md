---
name: research-bakeoff
description: |
  Bake-off / tournament: implement + evaluate N candidate approaches to a research problem in
  parallel (each in its own worktree), judge each on the metrics that matter, and pick a winner —
  synthesizing from the winner while grafting the best ideas from the runners-up. Use when the
  solution space is wide and you want evidence, not a guess. Triggers: "bake-off X", "compare these
  approaches", "which method is best for X", "tournament of approaches", "/research-bakeoff".
  Launches a multi-agent Workflow (this skill authorizes the Workflow call).
---

# research-bakeoff — approach tournament

Beats one-attempt-iterated when the solution space is wide. Each approach is built + measured
independently, judged on the same rubric, then synthesized.

## When invoked
1. Get the **problem** and the **candidate approaches** from args/prompt. If approaches aren't given,
   propose 3 distinct ones (e.g. simple-baseline / risk-first / signal-rich) and confirm in one line.
2. Invoke the `Workflow` tool with the script below, passing `args: { problem, approaches, rubric }`.
   Each builder runs in `isolation:'worktree'` so they don't collide.
3. Present: the scored table, the **winner + why**, and the 1-2 ideas worth grafting from the losers.

## Workflow
```js
export const meta = {
  name: 'research-bakeoff',
  description: 'Implement + evaluate N approaches, judge, pick a winner',
  phases: [{ title: 'Build' }, { title: 'Judge' }],
}
const BUILT = { type:'object', required:['approach','metrics','branch'], properties:{
  approach:{type:'string'}, metrics:{type:'object'}, branch:{type:'string'}, notes:{type:'string'} } }
const SCORE = { type:'object', required:['approach','scores','verdict'], properties:{
  approach:{type:'string'}, scores:{type:'object'}, verdict:{type:'string'}, keep_ideas:{type:'string'} } }
const problem    = (args && args.problem)    || 'the research problem named in the invocation'
const APPROACHES = (args && args.approaches) || ['baseline / simplest defensible approach', 'risk-first approach', 'signal-rich approach']
const rubric     = (args && args.rubric)     || 'IC, deflated-Sharpe, turnover/churn, explainability, robustness across windows'
const scored = await pipeline(APPROACHES,
  a => agent(`Implement AND evaluate this approach to "${problem}": ${a}. Work entirely in your own worktree; produce the headline metrics. Report the metrics + your branch name.`,
        { label: `build:${a.slice(0,18)}`, phase: 'Build', isolation: 'worktree', agentType: 'engineering-senior-developer', schema: BUILT }),
  built => agent(`Judge this approach on the rubric "${rubric}". Be quantitative and skeptical. Approach + measured metrics: ${JSON.stringify(built)}`,
        { label: `judge:${(built&&built.approach||'').slice(0,16)}`, phase: 'Judge', schema: SCORE, agentType: 'engineering-code-reviewer' })
)
return { problem, rubric, approaches: scored.filter(Boolean) }
```
Synthesize the winner yourself from the scored set; call out ideas to graft from runners-up.
