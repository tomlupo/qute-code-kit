---
name: sql-patterns
description: |
  SQL query patterns, best practices, and templates.
  Use when writing queries, exploring databases, or analyzing data.
  Triggers: SQL, database queries, data analysis, schema exploration, "write a query"
allowed-tools: Read, Grep, Glob
---

# SQL Query Patterns

Common patterns and best practices for database work.

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
-- Group by with multiple aggregates
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

## Query Safety Best Practices

### Always Use LIMIT for Exploration

```sql
-- ✅ GOOD
SELECT * FROM large_table LIMIT 100;

-- ❌ BAD
SELECT * FROM large_table;
```

### Check Row Count Before Operations

```sql
-- Before UPDATE/DELETE, check scope
SELECT COUNT(*) FROM table WHERE condition;

-- Then proceed with caution
UPDATE table SET ... WHERE condition;
```

### Use EXPLAIN Before Expensive Queries

```sql
EXPLAIN ANALYZE
SELECT ...
FROM large_join;
```

### Transaction Safety

```sql
BEGIN;
-- Make changes
UPDATE ...;
-- Verify results
SELECT ...;
-- If correct:
COMMIT;
-- If wrong:
ROLLBACK;
```

## Performance Tips

1. **Index columns used in WHERE, JOIN, ORDER BY**
2. **Avoid SELECT * in production** - specify columns
3. **Use LIMIT for debugging** - remove in production only if needed
4. **Filter early** - reduce rows before joins
5. **Check execution plans** - EXPLAIN shows bottlenecks

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

## Remember

- Start with exploratory queries to understand data shape
- Use CTEs for complex queries - readability matters
- Always LIMIT during exploration
- Check execution plans for slow queries
- Save large query results to files, show summaries in chat
