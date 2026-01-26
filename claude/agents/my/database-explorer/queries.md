# SQL Query Patterns

## Schema Inspection

### PostgreSQL

```sql
-- List all tables
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema NOT IN ('pg_catalog', 'information_schema');

-- Describe table structure
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'your_table';

-- Get foreign key relationships
SELECT
  tc.table_name, kcu.column_name,
  ccu.table_name AS foreign_table,
  ccu.column_name AS foreign_column
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY';

-- Table sizes and row counts
SELECT
  schemaname, tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
  n_live_tup AS row_count
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### MySQL

```sql
-- List tables
SHOW TABLES;

-- Describe table
DESCRIBE table_name;
SHOW CREATE TABLE table_name;

-- Table sizes
SELECT
  table_name,
  ROUND(data_length / 1024 / 1024, 2) AS data_mb,
  table_rows
FROM information_schema.tables
WHERE table_schema = DATABASE();
```

## Exploratory Queries

```sql
-- Sample data
SELECT * FROM table_name LIMIT 10;

-- Row count
SELECT COUNT(*) FROM table_name;

-- Column value distribution
SELECT column_name, COUNT(*) as count
FROM table_name
GROUP BY column_name
ORDER BY count DESC
LIMIT 20;

-- Date range of data
SELECT
  MIN(created_at) as earliest,
  MAX(created_at) as latest,
  COUNT(*) as total_records
FROM table_name;

-- Check for NULLs
SELECT
  COUNT(*) as total,
  COUNT(column_name) as non_null,
  COUNT(*) - COUNT(column_name) as nulls
FROM table_name;

-- Find duplicates
SELECT column_name, COUNT(*) as count
FROM table_name
GROUP BY column_name
HAVING COUNT(*) > 1;
```

## Analytical Patterns

### Aggregations

```sql
SELECT
  category,
  COUNT(*) as count,
  AVG(price) as avg_price,
  SUM(revenue) as total_revenue,
  MIN(price) as min_price,
  MAX(price) as max_price
FROM products
GROUP BY category
ORDER BY total_revenue DESC;
```

### Time-Series Analysis

```sql
-- Daily counts
SELECT
  DATE_TRUNC('day', created_at) as date,
  COUNT(*) as daily_count
FROM orders
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY date
ORDER BY date;

-- Month-over-month comparison
SELECT
  DATE_TRUNC('month', created_at) as month,
  COUNT(*) as orders,
  SUM(total_amount) as revenue
FROM orders
WHERE created_at >= NOW() - INTERVAL '12 months'
GROUP BY month
ORDER BY month;
```

### Cohort Analysis

```sql
WITH user_cohorts AS (
  SELECT
    user_id,
    DATE_TRUNC('month', MIN(created_at)) as cohort_month
  FROM orders
  GROUP BY user_id
)
SELECT
  cohort_month,
  COUNT(*) as cohort_size
FROM user_cohorts
GROUP BY cohort_month
ORDER BY cohort_month;
```

### Window Functions

```sql
-- Running total
SELECT
  date,
  revenue,
  SUM(revenue) OVER (ORDER BY date) as running_total
FROM daily_revenue;

-- Rank within groups
SELECT
  category,
  product_name,
  revenue,
  RANK() OVER (PARTITION BY category ORDER BY revenue DESC) as rank
FROM products;

-- Moving average
SELECT
  date,
  value,
  AVG(value) OVER (
    ORDER BY date
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
  ) as moving_avg_7d
FROM metrics;
```

### CTEs for Readability

```sql
WITH
  active_users AS (
    SELECT DISTINCT user_id
    FROM user_activities
    WHERE activity_date >= CURRENT_DATE - INTERVAL '30 days'
  ),
  user_orders AS (
    SELECT user_id, SUM(total_amount) as total_spent
    FROM orders
    GROUP BY user_id
  )
SELECT
  COUNT(*) as active_customers,
  AVG(total_spent) as avg_spend
FROM active_users au
JOIN user_orders uo ON au.user_id = uo.user_id;
```

## Common Patterns

### Top N per Group

```sql
SELECT * FROM (
  SELECT
    *,
    ROW_NUMBER() OVER (PARTITION BY category ORDER BY sales DESC) as rn
  FROM products
) ranked
WHERE rn <= 5;
```

### Pivot Data

```sql
SELECT
  user_id,
  SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
  SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
  SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
FROM orders
GROUP BY user_id;
```

### Gap Detection

```sql
WITH numbered AS (
  SELECT
    date,
    ROW_NUMBER() OVER (ORDER BY date) as rn
  FROM daily_data
)
SELECT
  a.date as gap_start,
  b.date as gap_end
FROM numbered a
JOIN numbered b ON a.rn = b.rn - 1
WHERE b.date - a.date > INTERVAL '1 day';
```

## Output Formats

### Query Results Presentation

```markdown
## Query Results: [Description]

**Database**: production_db
**Table**: customers
**Rows Returned**: 50
**Execution Time**: 0.23s

| customer_id | name          | total_orders | lifetime_value |
|-------------|---------------|--------------|----------------|
| 1234        | Acme Corp     | 156          | $45,678.90    |
| 5678        | Tech Systems  | 98           | $32,456.12    |
...

### Key Findings:
- 60% of customers have made repeat purchases
- Average order value has increased 15% QoQ
- Top 20% of customers drive 80% of revenue
```

### Schema Visualization

```markdown
## Database Schema Overview

**Database**: ecommerce_prod
**Tables**: 23
**Total Size**: 145 GB

### Core Tables:
1. **customers** (1.2M rows)
   - customer_id (PK)
   - email, name, created_at
   - → orders (FK: customer_id)

2. **orders** (3.4M rows)
   - order_id (PK)
   - customer_id (FK → customers)
   - total_amount, status, created_at
   - → order_items (FK: order_id)

3. **products** (45K rows)
   - product_id (PK)
   - name, price, category
   - ← order_items (FK: product_id)

### Relationships:
customers → orders → order_items → products
```

## Error Handling

### Connection Issues
```markdown
❌ **Connection Failed**: Could not connect to database

**Possible Causes**:
- Database server is down or unreachable
- Invalid credentials
- Network/firewall blocking connection
- Database name incorrect

**Troubleshooting**:
1. Verify connection string
2. Check if database server is running
3. Test network connectivity
4. Verify credentials are current
```

### Query Errors
```markdown
❌ **Query Failed**: Column 'order_date' does not exist

**Original Query**:
SELECT order_date FROM orders;

**Issue**: Column name mismatch

**Suggestion**: Run `\d orders` to see actual column names
```
