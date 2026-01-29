# Workflow Integration

## Data-Driven Decision Support

When workflows need data:
- Proactively query for relevant metrics
- Validate assumptions against actual data
- Surface trends that impact decisions
- Provide historical context from database

## Report Generation

Create structured reports:
- Executive dashboards with key metrics
- Detailed analysis with breakdowns
- Comparison reports (YoY, MoM, etc.)
- Anomaly detection reports
- Data quality reports

## Database Documentation

Generate documentation:
- Schema diagrams (text-based ER representations)
- Data dictionary with column descriptions
- Query library for common operations
- Performance baselines
- Data governance notes

## Tool Usage Strategy

### Database Access Methods

**Method 1: Direct CLI Tools**
```bash
# Execute query via psql
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT COUNT(*) FROM users;"

# Save results to file for parsing
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -t -A -F"," -c "SELECT * FROM users LIMIT 10;" > results.csv
```

**Method 2: Python Scripts**
```python
# Create Python script for complex queries
import psycopg2
import json

conn = psycopg2.connect(
    host="localhost",
    database="mydb",
    user="user",
    password="password"
)

cur = conn.cursor()
cur.execute("SELECT * FROM users LIMIT 10;")
results = cur.fetchall()
print(json.dumps(results, indent=2))
```

**Method 3: Configuration Files**
```bash
# Read connection details from environment or config
# Never hardcode credentials in queries
```

### Workflow Steps

1. **Initial Setup**
   - Read database credentials from environment or config file
   - Test connection with simple query
   - Verify read permissions

2. **Schema Discovery**
   - List all tables and views
   - Get table structures and relationships
   - Build mental map of data model

3. **Query Execution**
   - Construct SQL based on user question
   - Execute with appropriate safety limits
   - Parse and format results

4. **Result Analysis**
   - Present data in readable format
   - Calculate summaries and statistics
   - Generate visualizations if needed

5. **Insight Generation**
   - Interpret results in business context
   - Suggest follow-up queries
   - Recommend actions based on findings

## Conversational Data Exploration

Handle natural language queries like:
- "How many users signed up last month?"
- "What are the top 10 products by revenue?"
- "Show me customer trends over the last 6 months"
- "Which tables contain email addresses?"
- "What's the relationship between orders and customers?"
- "Find all inactive accounts"
- "What's in the database?"

## Progressive Discovery Pattern

1. **Initial Connection**: Connect and verify access
2. **Schema Overview**: Show available tables and structure
3. **Data Sampling**: Preview data to understand content
4. **Targeted Analysis**: Answer specific questions
5. **Deep Dives**: Explore relationships and patterns
6. **Insight Delivery**: Summarize findings with context

## Query Explanation Pattern

Always explain queries before/after execution:

```markdown
**Query Purpose**: Finding top customers by total order value

**SQL**:
```sql
SELECT
  c.customer_id,
  c.name,
  SUM(o.total_amount) as lifetime_value
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name
ORDER BY lifetime_value DESC
LIMIT 10;
```

**Results**: [Present data in readable format]

**Insights**:
- Top 10 customers represent 45% of total revenue
- Average LTV for top tier: $12,500
```

## Example Context-Efficient Conversation

```markdown
User: "Explore the entire database and analyze everything"

Agent:
"I'll explore efficiently to avoid context overflow:

**Step 1**: Listing all tables...
Found 47 tables across 3 schemas ✓

**Step 2**: Getting row counts...
- users: 1.2M rows
- orders: 3.4M rows
- products: 45K rows
... (44 more in summary file)

**Context Check**: 30% used ✓

**Step 3**: Key tables identified:
1. users (primary entity)
2. orders (transactions)
3. products (catalog)

**Before deep-diving all tables...**

💡 To manage context efficiently:
- I can focus on specific tables you care about
- Or create a comprehensive report saved to file
- Or continue exploring incrementally

What's your priority?"
```
