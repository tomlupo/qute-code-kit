# /research:index

Display the research index showing all hypotheses, experiments, findings, and papers.

## Usage

```
/research:index [--filter <type>] [--status <status>]
```

## Arguments

- `--filter` - (Optional) Show only: hypotheses, experiments, findings, papers
- `--status` - (Optional) Filter by status: testing, validated, rejected, complete

## Behavior

1. **Scan research directories**
   - `docs/research/hypotheses/`
   - `docs/research/experiments/`
   - `docs/research/findings/`
   - `docs/research/papers/`

2. **Parse document metadata**
   - Extract title, date, status from each document
   - Build summary table

3. **Display formatted index**:
   ```
   📊 Research Index

   ## Hypotheses (3)
   | Status | Title | Date | Experiments |
   |--------|-------|------|-------------|
   | 🔬 | Dropout reduces overfitting | 2026-01-10 | 2 |
   | ✅ | Batch norm improves convergence | 2026-01-08 | 3 |
   | ❌ | Higher LR is always better | 2026-01-05 | 1 |

   ## Experiments (6)
   | Status | Name | Date | Hypothesis |
   |--------|------|------|------------|
   | ✅ | dropout-test-v1 | 2026-01-12 | dropout-overfitting |
   | ✅ | dropout-test-v2 | 2026-01-13 | dropout-overfitting |
   | 🏃 | lr-sweep-01 | 2026-01-13 | - |

   ## Findings (2)
   | Confidence | Title | Date |
   |------------|-------|------|
   | 🟢 | Dropout 0.3 optimal | 2026-01-13 |
   | 🟡 | Adam outperforms SGD | 2026-01-11 |

   ## Papers (4)
   | Title | Authors | Date Read |
   |-------|---------|-----------|
   | Attention Is All You Need | Vaswani et al. | 2026-01-10 |
   | BERT | Devlin et al. | 2026-01-08 |
   ```

4. **Update index.md file**
   - Regenerate `docs/research/index.md` with current data

## Example

```
/research:index --filter hypotheses --status testing

# Output:
📊 Research Index (filtered: hypotheses, status: testing)

## Hypotheses (1)
| Status | Title | Date | Experiments |
|--------|-------|------|-------------|
| 🔬 | Dropout reduces overfitting | 2026-01-10 | 2 |

Full index: docs/research/index.md
```

## Status Icons

**Hypotheses:**
- 🔬 Testing
- ✅ Validated
- ❌ Rejected
- ⏸️ Paused

**Experiments:**
- 🏃 Running
- ✅ Complete
- ❌ Failed
- ⏸️ Paused

**Findings:**
- 🟢 High confidence
- 🟡 Medium confidence
- 🔴 Low confidence
