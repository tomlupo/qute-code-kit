---
name: acceptance-gates
description: "Deterministic robustness/acceptance gates for a quant backtest finding — Deflated Sharpe Ratio (DSR, Bailey/López de Prado), Newey-West HAC t-stat + min-OOS-window, and factor-decomposition (Jensen's alpha). Thin CLIs over the quantbox framework's tested statistics (quantbox.analysis); requires quantbox installed. Triggers: DSR gate, deflated sharpe, is this overfit, multiple-testing correction, Newey-West t-stat, HAC standard errors, factor decomposition, Jensen's alpha, is this just beta, acceptance gate, robustness gate before promotion."
---

# acceptance-gates — DSR / Newey-West / factor-decomposition robustness gates

Three deterministic, thin CLI gates that answer three DIFFERENT questions about a
candidate strategy's backtest result, before it's trusted enough to promote:

| Gate | Question | Script |
|---|---|---|
| **DSR** | Is the Sharpe ratio real once you deflate for the return distribution's actual skew/kurtosis AND how many trials were tried? | `scripts/dsr-gate.py` |
| **Newey-West** | Is the mean OOS return significant once autocorrelation is corrected for, AND was the OOS window long enough to trust at all? | `scripts/nw-tstat-gate.py` |
| **Factor decomposition** | Is the return NOVEL, or just paid-for exposure to a known factor (beta, momentum, carry)? | `scripts/factor-decomp-gate.py` |

Each takes a return series (CSV/Parquet) and prints a JSON verdict. None of them
know anything about a specific harness, config format, or dataset — they consume
an already-built return/factor series.

**The statistics themselves are NOT in this skill.** They live in the quantbox
framework (`quantbox.analysis`), which is tested there (parity proof against the
retired hand-rolled implementations, plus the pinned DSR false-PASS-band
regression). Each script here is a THIN wrapper: it loads the data, calls the
framework, applies the gate's threshold/policy, and prints JSON. This is
deliberate — three independent hand-rolled copies of the DSR math once co-existed
and drifted (one silently passed overfit strategies with a naive normal null),
which is exactly what centralising the math into one tested home prevents.

**What stays OUT of the gates on purpose:** anything that knows how to BUILD the
input series from harness-specific data (e.g. a point-in-time crypto factor panel
from a specific dataset/universe) belongs to the consuming research repo, not
here. These gates only consume an already-built return/factor series.

## Runtime dependencies (state them before you run)

These gates import the framework:

```python
from quantbox.analysis import deflated_sharpe_ratio_from_returns   # dsr-gate.py
from quantbox.analysis import newey_west_tstat                     # nw-tstat-gate.py
from quantbox.analysis import factor_regression                    # factor-decomp-gate.py
```

- **`quantbox`** (with `quantbox.analysis`, i.e. a version that carries the
  `analysis.dsr` + `analysis.hac` modules — statsmodels-backed HAC landed
  alongside DSR). This is the ONE hard dependency; everything else
  (`numpy`, `scipy`, `pandas`, `patsy`, `statsmodels`) comes transitively with
  it. If `import quantbox.analysis` fails, install quantbox in the environment
  you run these from — do not reintroduce a local copy of the math.
- **`pytest`** additionally, to run this skill's own CLI test suite.

Because the gates now depend on quantbox, "portable to any quant repo" narrows to
"portable to any repo that has quantbox installed" — the trade for never
hand-rolling (and re-bugging) the statistics again.

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

The gate's `dsr_pass` is decided from the **conservative end** (the highest n_trials
in the range — most deflation, lowest DSR), never from whichever n_trials value
happens to pass. Default range: `1,5,10,20,50,100`. Default threshold: **0.95**,
one-sided (Bailey/López de Prado standard — do not lower it to make a result pass).
`--threshold` must be finite and strictly between 0 and 1.

**Kurtosis convention (load-bearing, easy to get wrong):** `--kurtosis` and the
return-series path both use **PEARSON (non-excess) kurtosis**, where 3.0 = normal
distribution — NOT excess kurtosis (0.0 = normal). `scipy.stats.kurtosis()` returns
EXCESS kurtosis by **default** (`fisher=True`); you must pass `fisher=False` to get
the convention this gate expects. Passing excess kurtosis silently understates the
Mertens variance term and can flip a FAIL to a PASS. `quantbox.analysis.dsr` rejects
any skew/kurtosis pair that is mathematically impossible under the Pearson convention
(`kurtosis < skew**2 + 1` — an algebraic identity), which catches the most common
form of this mixup, e.g. `skew=0, kurtosis=0`.

**IID assumption:** the annualisation (`sqrt(periods)` scaling between per-period and
annualised Sharpe) assumes returns are i.i.d. — no serial autocorrelation. If the
return series is autocorrelated (overlapping windows, slow-moving positions), the
annualisation is biased and the gate's threshold comparison is not reliable as stated
(use the Newey-West gate for an autocorrelation-robust t-stat).

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

## Degenerate input — every gate fails loudly, never silently passes

The load-bearing invariant, enforced in the framework so every caller inherits it:

- **DSR** (`quantbox.analysis.dsr`): rejects inf/NaN Sharpe, `n_trials<=0`,
  `periods<=0`, `n_obs<=1`, negative SR-estimator variance (garbage
  skew/kurtosis), zero-variance returns, and impossible Pearson moments.
  `--sharpe` without `--skew`/`--kurtosis`/`--n-obs` is refused outright — there
  is no default skew=0/kurtosis=3 (that WAS the original normal-null bug).
- **Newey-West** (`quantbox.analysis.hac.newey_west_tstat` +
  `nw-tstat-gate.py`): NaN/Inf return observations RAISE by default
  (`--allow-nonfinite-drop` opts back in explicitly, and the output records
  `n_obs_raw` / `n_nonfinite_dropped`). `--oos-periods` can only narrow the
  recorded window, never claim more than the actual finite-return count.
- **Factor decomposition** (`quantbox.analysis.hac.factor_regression` +
  `factor-decomp-gate.py`): an empty factor-column list raises rather than
  silently running an intercept-only "regression" that can PASS on raw mean
  return alone.

## Files

```
scripts/
  dsr-gate.py              DSR CLI gate (n_trials range, conservative-end decision)
  nw-tstat-gate.py         Newey-West HAC t-stat + min-OOS-window CLI gate
  factor-decomp-gate.py    factor-decomposition (Jensen's alpha) CLI gate
  tests/
    test_dsr_gate.py           CLI-level tests (the math regression lives in quantbox)
    test_nw_tstat_gate.py
    test_factor_decomp_gate.py
```

The DSR / Newey-West / factor-regression math and its regression suite live in the
`quantbox` framework (`quantbox.analysis.dsr`, `quantbox.analysis.hac`), not here.
Do NOT reimplement skew/kurtosis/expected-max-SR or a HAC sandwich in this repo —
import from `quantbox.analysis`.

## Provenance

The gates originally hand-rolled their statistics inside these scripts (and, in
quantbox-lab, in a `scripts/lib/dsr.py` and in `carver_prelive_gauntlet.py`).
2026-07-19 those statistics were consolidated into the quantbox framework
(`quantbox.analysis`), where they are packaged, typed, and tested — including a
numeric-parity proof that the statsmodels-backed HAC reproduces the retired
hand-rolled estimator to machine precision. These scripts became thin wrappers.
The framework-usage linter (`scripts/lint/check_framework_usage.py`) now hard-gates
re-introducing a hand-rolled DSR / Newey-West / OLS in the lab.
