---
name: research-robustness
description: |
  Stress a method or signal across a matrix of windows × regimes × parameters in parallel, collect
  a robustness grid, and flag where it breaks. Use to check "does this hold out-of-sample / across
  regimes?" before locking a methodology. Triggers: "robustness of X", "stress-test this signal
  across windows/regimes", "sensitivity matrix", "does this hold out of sample", "/research-robustness".
  Launches a multi-agent Workflow (this skill authorizes the Workflow call).
---

# research-robustness — robustness / sensitivity matrix

Automates the "lock nothing until it persists across windows" rule: run the *same* method over many
conditions concurrently, then report where the headline metric is stable vs fragile.

## When invoked
1. Get the **method/signal** (and where to run it) from args/prompt. Default the matrix to 3 windows ×
   4 regimes unless the user names their own; ask only if the method isn't runnable as described.
2. Invoke the `Workflow` tool with the script below, passing `args: { method, windows, regimes }`.
3. Present the grid as a compact table (cell → metric, stable?), lead with **ROBUST / FRAGILE** and the
   cells that break, and name the condition that breaks it.

## Workflow
```js
export const meta = {
  name: 'research-robustness',
  description: 'Robustness/sensitivity matrix for a method or signal',
  phases: [{ title: 'Grid' }, { title: 'Synthesize' }],
}
const CELL = { type:'object', required:['cell','metric','stable','note'], properties:{
  cell:{type:'string'}, metric:{type:'number'}, stable:{type:'boolean'}, note:{type:'string'} } }
const method  = (args && args.method)  || 'the method/signal named in the invocation'
const WINDOWS = (args && args.windows) || ['trailing 156w', 'trailing 104w', 'trailing 52w']
const REGIMES = (args && args.regimes) || ['full sample', 'risk-on', 'risk-off', 'high-vol']
const cells = WINDOWS.flatMap(w => REGIMES.map(r => ({ w, r })))
const grid = (await parallel(cells.map(c => () =>
  agent(`Evaluate "${method}" on window=${c.w}, regime=${c.r}. Actually run the backtest/metric in the repo (do not estimate). Report the headline metric (Sharpe / IC / hit-rate as appropriate), whether it is STABLE vs the full-sample value (±25%), and any caveat.`,
    { label: `cell:${c.w}|${c.r}`, phase: 'Grid', schema: CELL, agentType: 'engineering-data-engineer' }))
)).filter(Boolean)
const unstable = grid.filter(c => !c.stable)
const synth = await agent(`Given this robustness grid for "${method}", state ROBUST or FRAGILE, the single condition under which it most degrades, and whether it is safe to lock. Grid: ${JSON.stringify(grid)}`,
  { phase: 'Synthesize', schema: { type:'object', required:['verdict','breaks_under','safe_to_lock'], properties:{
    verdict:{type:'string',enum:['robust','fragile','mixed']}, breaks_under:{type:'string'}, safe_to_lock:{type:'boolean'} } } })
return { method, cells: grid.length, unstable: unstable.length, grid, synth }
```
Render `grid` as a table; lead with `synth.verdict` + `synth.breaks_under`.
