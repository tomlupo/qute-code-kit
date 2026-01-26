# Context Management for Database Operations

## Core Principles

Database queries can return massive results. Always:
1. **LIMIT first** - Default to 100 rows max in conversation
2. **Count before query** - Know what you're getting into
3. **Save to files** - Large results go to CSV/JSON, not chat
4. **Aggregate** - Show summaries, not raw dumps

## Smart Query Result Handling

### Strategy 1: Limit Results Proactively

```sql
-- Always use LIMIT for exploration
-- BAD (fills context):
SELECT * FROM large_table;

-- GOOD (context-efficient):
SELECT * FROM large_table LIMIT 10;

-- Show user there's more:
SELECT COUNT(*) as total_rows FROM large_table;
-- "Showing 10 of 1,500,000 rows. Run with higher LIMIT if needed."
```

### Strategy 2: Save Large Results to Files

```bash
# Instead of showing 10,000 rows in context:
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
  COPY (SELECT * FROM big_query)
  TO STDOUT WITH CSV HEADER
" > query_results.csv

echo "✓ Saved 10,000 rows to query_results.csv"
echo "Summary: Top 10 rows:"
head -n 11 query_results.csv
```

### Strategy 3: Aggregate Instead of Details

```sql
-- Instead of returning all customer records:
-- BAD: SELECT * FROM customers; (1M rows)

-- GOOD: Provide summary stats
SELECT
  COUNT(*) as total_customers,
  COUNT(DISTINCT country) as countries,
  MIN(created_at) as earliest_signup,
  MAX(created_at) as latest_signup,
  AVG(lifetime_value) as avg_ltv
FROM customers;

-- Then offer: "Want details on a specific segment?"
```

### Strategy 4: Incremental Exploration

```markdown
## Database Exploration: Progressive Discovery

**Phase 1: Overview (Low Context)**
- List schemas and tables
- Get row counts
- Identify key tables

**Phase 2: Schema Details (As Needed)**
- Describe specific tables user asks about
- Show relationships for relevant tables only

**Phase 3: Data Sampling (Targeted)**
- Sample data from tables of interest
- Keep samples small (10-20 rows)

**Phase 4: Analysis (Focused)**
- Run specific queries user requests
- Save large results to files
```

## Handling Low Context During Analysis

**When Context Warning Appears:**

```markdown
⚠️ Context Low Detected

**Current Status**:
- Explored: 15 tables ✓
- Ran 8 queries ✓
- Key findings: documented ✓

**Saving state**:
- Query history → saved to scratch/queries.sql
- Key findings → saved to scratch/analysis_summary.md

**Options**:
A) Run `/compact` to continue exploring
B) Focus on specific question now
C) Wrap up with executive summary
```

## Smart Result Presentation

### Progressive Detail Disclosure

```markdown
## Query Results: Top Customers

**Summary**: Found 1,000 customers with LTV > $10K

**Top 10** (showing sample, full results in file):
| customer_id | name | ltv |
|-------------|------|-----|
| 1234 | Acme Corp | $45,678 |
| 5678 | Tech Systems | $32,456 |
... (8 more)

**Full Results**: Saved to `top_customers.csv` (1,000 rows)

**Statistics**:
- Average LTV: $15,234
- Median LTV: $12,500
- Total Value: $15.2M

💡 Want details on any specific customer? Just ask!
```

## Proactive Context Management

### Before Large Operations

```markdown
"This query will return ~50,000 rows.

**Context Management Plan**:
✓ Execute query
✓ Save full results to CSV
✓ Show summary statistics in chat
✓ Display top 20 rows as preview

This keeps our conversation efficient. Proceed?"
```

### Auto-Save Triggers

When results exceed thresholds:
- More than 100 rows → Save to file, show sample
- More than 20 columns → Select most relevant
- Query takes > 30 seconds → Warn and offer to limit

## Best Practices Checklist

**Before Each Query:**
- [ ] Will results be >100 rows? → Use LIMIT or save to file
- [ ] Multiple columns (20+)? → SELECT only needed columns
- [ ] Already at 70% context? → Save next result to file

**During Exploration:**
- [ ] Monitor context usage every 5-10 queries
- [ ] Save intermediate findings to files
- [ ] Aggregate instead of showing raw data

**When Context Low:**
- [ ] Immediately save current state
- [ ] Summarize findings so far
- [ ] Suggest `/compact` or file-based continuation
- [ ] Offer focused next steps

**Always:**
- [ ] Provide file paths for saved results
- [ ] Show summaries, not full data
- [ ] Keep query library for reuse
- [ ] Warn user before large operations

## File-Based Result Storage

### Save Query Results Externally

```bash
# For large analytical queries
psql -h $DB_HOST -d $DB_NAME \
  -c "SELECT * FROM analysis" \
  -o "results.csv"

echo "✓ Query complete"
echo "Rows saved: $(wc -l < results.csv)"
echo "File: results.csv"
echo ""
echo "Preview (first 5 rows):"
head -n 6 results.csv
```

### Maintain Query Library

```bash
# Save reusable queries instead of repeating
mkdir -p .claude/queries/

cat > .claude/queries/active_users.sql << 'EOF'
-- Active users in last 30 days
SELECT COUNT(DISTINCT user_id) as active_users
FROM user_activities
WHERE activity_date >= CURRENT_DATE - INTERVAL '30 days';
EOF

# Just reference the file, don't repeat query text
echo "Running saved query: .claude/queries/active_users.sql"
psql -f .claude/queries/active_users.sql
```
