---
name: acceptance-gates
description: "Deterministic robustness/acceptance gates for a quant backtest finding — Deflated Sharpe Ratio (DSR, Bailey/López de Prado), Newey-West HAC t-stat + min-OOS-window, and factor-decomposition (Jensen's alpha). Pure statistical methodology, portable to any quant repo — no harness/config/universe knowledge required. Triggers: DSR gate, deflated sharpe, is this overfit, multiple-testing correction, Newey-West t-stat, HAC standard errors, factor decomposition, Jensen's alpha, is this just beta, acceptance gate, robustness gate before promotion."
---

# acceptance-gates — DSR / Newey-West / factor-decomposition robustness gates

Three deterministic, pure-math CLI gates that answer three DIFFERENT questions about
a candidate strategy's backtest result, before it's trusted enough to promote:

| Gate | Question | Script |
|---|---|---|
| **DSR** | Is the Sharpe ratio real once you deflate for the return distribution's actual skew/kurtosis AND how many trials were tried? | `scripts/dsr-gate.py` |
| **Newey-West** | Is the mean OOS return significant once autocorrelation is corrected for, AND was the OOS window long enough to trust at all? | `scripts/nw-tstat-gate.py` |
| **Factor decomposition** | Is the return NOVEL, or just paid-for exposure to a known factor (beta, momentum, carry)? | `scripts/factor-decomp-gate.py` |

None of these need to know anything about a specific harness, config format, or
dataset — they take a return series (CSV/Parquet) and print a JSON verdict. That's
what makes this skill portable: copy it into any quant repo unchanged.

**What stays OUT of this skill on purpose:** anything that knows how to BUILD the
input series from harness-specific data (e.g. a crypto factor panel from a specific
dataset/universe) belongs to the consuming repo, not here — see quantbox-lab's
`crypto_factors.py`. This skill only consumes an already-built return/factor series.

## Ethos — assume overfit until proven

Run ALL THREE gates before trusting a backtest headline. Each catches a different
failure mode a single Sharpe number hides:

- **DSR catches**: multiple-testing overfit (you tried 50 configs and cherry-picked
  the best) and fat-tail distortion (skew/kurtosis inflate the variance of the Sharpe
  estimator, so a naive normal-null test overstates confidence).
- **Newey-West catches**: autocorrelation-inflated significance (overlapping signals
  make a naive t-test look more confident than it is) and a too-short OOS window
  hiding behind an otherwise-clean Sharpe.
- **Factor decomposition catches**: an edge that's actually just leveraged beta or a
  well-known factor re-packaged as a "novel" strategy.

A strategy passing DSR + Newey-West but failing factor decomposition is not
worthless — it may be a legitimate, honest factor bet — but it is NOT a novel edge
and should not be promoted as one.

## The DSR range convention (read this before running dsr-gate.py)

`n_trials` — how many configs/hypotheses were tried before landing on this one — is
almost never an honest, uncontested single number. It depends on how you bound "the
search" (this exact sweep? every variant ever tried? every hypothesis filed in the
vault?). **Do not report DSR at one n_trials value and let the verdict hinge on that
judgment call.** Instead:

```
dsr-gate.py --returns oos_returns.csv --n-trials 1,5,10,20,50,100 --periods 365
```

This is the convention already used in quantbox-lab's
`scripts/analysis/carver_prelive_gauntlet.py` (see its `N_TRIALS` sensitivity sweep
and its own comment on why: *"DSR is reported across a range of N so the verdict does
not hinge on one count"*). The gate's `dsr_pass` is decided from the **conservative
end** (the highest n_trials in the range — most deflation, lowest DSR), never from
whichever n_trials value happens to pass. Default range: `1,5,10,20,50,100`. Default
threshold: **0.95**, one-sided (Bailey/López de Prado standard — do not lower it to
make a result pass). `--threshold` must be finite and strictly between 0 and 1 — a
threshold of 0 or negative would make nearly any DSR pass.

**Kurtosis convention (load-bearing, easy to get wrong):** `--kurtosis` and the
return-series path both use **PEARSON (non-excess) kurtosis**, where 3.0 = normal
distribution — NOT excess kurtosis (0.0 = normal). `scipy.stats.kurtosis()` returns
EXCESS kurtosis by **default** (`fisher=True`); you must pass `fisher=False` to get
the convention this gate expects. Passing excess kurtosis silently understates the
Mertens variance term and can flip a FAIL to a PASS. `scripts/lib/dsr.py` now rejects
any skew/kurtosis pair that is mathematically impossible under the Pearson convention
(`kurtosis < skew**2 + 1` — an algebraic identity, not a modelling choice), which
catches the most common form of this mixup, e.g. `skew=0, kurtosis=0`.

**IID assumption:** the annualisation (`sqrt(periods)` scaling between per-period and
annualised Sharpe) assumes returns are i.i.d. — no serial autocorrelation. If the
return series is autocorrelated (overlapping windows, slow-moving positions), the
annualisation is biased and the gate's threshold comparison is not reliable as stated.

## Quick start

```bash
# 1. DSR — from a raw OOS return series (recommended: real skew/kurtosis, not assumed)
python3 scripts/dsr-gate.py --returns oos_returns.csv --n-trials 1,5,10,20,50,100 --periods 365

# 2. Newey-West + min-OOS-window
python3 scripts/nw-tstat-gate.py --returns oos_returns.csv --t-threshold 2.0 --min-oos-periods 252

# 3. Factor decomposition (needs a factor panel built by the consuming repo)
python3 scripts/factor-decomp-gate.py --returns oos_returns.csv --factors factor_panel.csv \
    --factor-columns mkt,mom,carry --t-threshold 2.0
```

All three print JSON with a `gate_pass: bool` field. All three exit non-zero and
print `{"error": "..."}` on degenerate input — **never treat a non-zero exit as "the
gate didn't run, ignore it" — it means the input itself is broken and needs fixing,
not bypassing.**

## Runtime dependencies

`numpy`, `scipy`, `pandas` (all three gates). Tests additionally need `pytest`. Not
pinned in this repo's `pyproject.toml` on purpose (see repo `CLAUDE.md` — this repo
is a plugin marketplace, not a Python package) — the consuming repo's own environment
is expected to already carry these (any quant harness does). To run this skill's own
test suite in isolation:

```bash
uv run --with numpy --with scipy --with pandas --with pytest \
    pytest claude/skills/quant/acceptance-gates/scripts/tests/ -q
```

## Degenerate input — every gate fails loudly, never silently passes

This is the load-bearing invariant of the whole skill; each gate was hardened
specifically against a class of silent-pass bug found by adversarial (codex) review:

- **`dsr-gate.py`**: rejects inf/NaN Sharpe, `n_trials<=0` (any entry in the range),
  `periods<=0`, `n_obs<=1`, negative SR-estimator variance (garbage skew/kurtosis
  combos), zero-variance returns. `--sharpe` without `--skew`/`--kurtosis`/`--n-obs`
  is refused outright — there is no default skew=0/kurtosis=3 (that WAS the original
  bug: see `scripts/lib/dsr.py`'s module docstring and the pinned false-PASS-band
  regression test).
- **`nw-tstat-gate.py`**: NaN/Inf return observations now RAISE by default instead of
  being silently dropped before `n_obs` is counted (`--allow-nonfinite-drop` opts
  back in explicitly, and the output then records `n_obs_raw` /
  `n_nonfinite_dropped` so the drop is visible, never hidden). `--oos-periods` can
  only narrow the recorded window, never claim more than the actual finite-return
  count — exceeding it raises.
- **`factor-decomp-gate.py`**: an empty factor-column list (explicit
  `--factor-columns ","`, or in principle a factor file with zero numeric columns)
  raises rather than silently running an intercept-only "regression" that can PASS
  on raw mean return alone — an intercept-only fit is not a factor decomposition.

See `scripts/tests/` for the pinned regression covering each hole, and `references/`
for the design write-ups this hardening pass produced.

## Files

```
scripts/
  lib/dsr.py              shared DSR math (SINGLE SOURCE OF TRUTH — do not
                           reimplement skew/kurtosis/expected-max-SR elsewhere)
  dsr-gate.py              DSR CLI gate (n_trials range, conservative-end decision)
  nw-tstat-gate.py         Newey-West HAC t-stat + min-OOS-window CLI gate
  factor-decomp-gate.py    factor-decomposition (Jensen's alpha) CLI gate
  tests/
    test_dsr_gate.py
    test_nw_tstat_gate.py
    test_factor_decomp_gate.py
```

## Provenance

Ported from quantbox-lab (which knows the crypto-trend harness and originally hosted
these gates) 2026-07-19, after Tom approved the split: pure statistical methodology
→ here (portable to any quant repo); anything that knows quantbox's configs,
universes, or dataset paths → stays in quantbox-lab's `.claude/skills/`. See the sync
mechanism (provenance stamp + drift checker) documented at the repo level for how
quantbox-lab's copy is kept honest against this canonical version.
