# Synapse → Hologres Conversion Examples

## Example 1: Complex Query with CTE, Window Functions, Joins

### Synapse (Before)

```sql
WITH monthly_sales AS (
    SELECT
        [CustomerID],
        [ProductCategory],
        DATEPART(month, [OrderDate]) AS order_month,
        SUM([Amount]) AS total_amount,
        COUNT(*) AS order_count
    FROM [dbo].[Sales]
    WHERE [OrderDate] >= '2024-01-01'
        AND [IsActive] = 1
    GROUP BY [CustomerID], [ProductCategory], DATEPART(month, [OrderDate])
)
SELECT TOP 100
    ms.[CustomerID],
    c.[CustomerName],
    ms.[ProductCategory],
    ms.total_amount,
    ms.order_count,
    ROW_NUMBER() OVER (PARTITION BY ms.[ProductCategory] ORDER BY ms.total_amount DESC) AS rank_in_category,
    ISNULL(c.[Email], 'N/A') AS email,
    CONVERT(VARCHAR(10), GETDATE(), 120) AS report_date,
    DATEDIFF(day, c.[RegisterDate], GETDATE()) AS days_since_registration,
    IIF(ms.total_amount > 10000, 'VIP', 'Regular') AS customer_tier
FROM monthly_sales ms
INNER JOIN [dbo].[Customers] c ON ms.[CustomerID] = c.[CustomerID]
WHERE ms.total_amount > 0
ORDER BY ms.total_amount DESC;
```

### Hologres (After)

```sql
WITH monthly_sales AS (
    SELECT
        customerid,
        productcategory,
        EXTRACT(MONTH FROM orderdate)::int AS order_month,
        SUM(amount) AS total_amount,
        COUNT(*) AS order_count
    FROM public.sales
    WHERE orderdate >= '2024-01-01'
        AND isactive = TRUE
    GROUP BY customerid, productcategory, EXTRACT(MONTH FROM orderdate)
)
SELECT
    ms.customerid,
    c.customername,
    ms.productcategory,
    ms.total_amount,
    ms.order_count,
    ROW_NUMBER() OVER (PARTITION BY ms.productcategory ORDER BY ms.total_amount DESC) AS rank_in_category,
    COALESCE(c.email, 'N/A') AS email,
    TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM-DD') AS report_date,
    (CURRENT_DATE - c.registerdate::date) AS days_since_registration,
    CASE WHEN ms.total_amount > 10000 THEN 'VIP' ELSE 'Regular' END AS customer_tier
FROM monthly_sales ms
INNER JOIN public.customers c ON ms.customerid = c.customerid
WHERE ms.total_amount > 0
ORDER BY ms.total_amount DESC
LIMIT 100;
```

### Key Changes

- `[]` → removed; identifiers unquoted (lowercase)
- `dbo.` → `public.`
- `TOP 100` → `LIMIT 100` (moved to end)
- `DATEPART(month, ...)` → `EXTRACT(MONTH FROM ...)`
- `ISNULL(...)` → `COALESCE(...)`
- `CONVERT(VARCHAR, GETDATE(), 120)` → `TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM-DD')`
- `DATEDIFF(day, a, b)` → `(b - a::date)`
- `IIF(...)` → `CASE WHEN ... END`
- `= 1` (BIT) → `= TRUE` (BOOLEAN)

---

## Example 2: DDL — Table with Distribution, Index, Partitioning

### Synapse (Before)

```sql
CREATE TABLE [dbo].[FactSales] (
    [SalesID] BIGINT IDENTITY(1,1) NOT NULL,
    [OrderDate] DATETIME2 NOT NULL,
    [CustomerID] INT NOT NULL,
    [ProductID] INT NOT NULL,
    [Quantity] SMALLINT NOT NULL,
    [UnitPrice] MONEY NOT NULL,
    [Discount] FLOAT DEFAULT 0,
    [TotalAmount] AS ([Quantity] * [UnitPrice] * (1 - [Discount])),
    [Notes] NVARCHAR(MAX) NULL,
    [IsReturned] BIT DEFAULT 0,
    [CreatedAt] DATETIME2 DEFAULT GETDATE()
)
WITH (
    DISTRIBUTION = HASH([CustomerID]),
    CLUSTERED COLUMNSTORE INDEX,
    PARTITION ([OrderDate] RANGE RIGHT FOR VALUES
        ('2024-01-01','2024-04-01','2024-07-01','2024-10-01'))
);
```

### Hologres (After)

```sql
BEGIN;

CREATE TABLE public.factsales (
    salesid BIGSERIAL NOT NULL,
    orderdate TIMESTAMP NOT NULL,
    customerid INT NOT NULL,
    productid INT NOT NULL,
    quantity SMALLINT NOT NULL,
    unitprice NUMERIC(19,4) NOT NULL,
    discount DOUBLE PRECISION DEFAULT 0,
    -- Hologres does not support computed columns; calculate in queries or use a view
    -- totalamount = quantity * unitprice * (1 - discount)
    notes TEXT,
    isreturned BOOLEAN DEFAULT FALSE,
    createdat TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
PARTITION BY LIST (orderdate);

CALL set_table_property('public.factsales', 'distribution_key', 'customerid');
CALL set_table_property('public.factsales', 'orientation', 'column');
CALL set_table_property('public.factsales', 'clustering_key', 'orderdate');

COMMIT;

-- Note: Create partition child tables as needed:
-- CREATE TABLE factsales_2024q1 PARTITION OF factsales FOR VALUES IN ('2024-01-01');
-- Or use RANGE partitioning if supported by your Hologres version.
```

### Key Changes

- `IDENTITY(1,1)` → `BIGSERIAL`
- `DATETIME2` → `TIMESTAMP`
- `MONEY` → `NUMERIC(19,4)`
- `FLOAT` → `DOUBLE PRECISION`
- `NVARCHAR(MAX)` → `TEXT`
- `BIT DEFAULT 0` → `BOOLEAN DEFAULT FALSE`
- `GETDATE()` → `CURRENT_TIMESTAMP`
- Computed column `TotalAmount AS (...)` → commented out (not supported)
- Distribution/index/partition → `set_table_property` calls
- Wrapped in `BEGIN...COMMIT` transaction

---

## Example 3: Stored Procedure → PL/pgSQL Function

### Synapse (Before)

```sql
CREATE PROCEDURE [dbo].[usp_GetCustomerSummary]
    @StartDate DATE,
    @EndDate DATE,
    @MinAmount MONEY = 0
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @TotalCustomers INT;

    -- Create temp table
    SELECT
        c.[CustomerID],
        c.[CustomerName],
        SUM(s.[Amount]) AS TotalSpent,
        COUNT(*) AS OrderCount,
        MAX(s.[OrderDate]) AS LastOrderDate
    INTO #CustomerSummary
    FROM [dbo].[Customers] c
    INNER JOIN [dbo].[Sales] s ON c.[CustomerID] = s.[CustomerID]
    WHERE s.[OrderDate] BETWEEN @StartDate AND @EndDate
    GROUP BY c.[CustomerID], c.[CustomerName]
    HAVING SUM(s.[Amount]) >= @MinAmount;

    SELECT @TotalCustomers = COUNT(*) FROM #CustomerSummary;

    SELECT
        cs.*,
        IIF(cs.TotalSpent > 10000, 'Premium', 'Standard') AS Tier,
        CAST(cs.TotalSpent AS FLOAT) / NULLIF(@TotalCustomers, 0) AS AvgPerCustomer,
        DATEDIFF(day, cs.LastOrderDate, GETDATE()) AS DaysSinceLastOrder
    FROM #CustomerSummary cs
    ORDER BY cs.TotalSpent DESC;

END;
```

### Hologres (After)

```sql
CREATE OR REPLACE FUNCTION public.usp_get_customer_summary(
    p_start_date DATE,
    p_end_date DATE,
    p_min_amount NUMERIC(19,4) DEFAULT 0
)
RETURNS TABLE (
    customerid INT,
    customername TEXT,
    totalspent NUMERIC(19,4),
    ordercount BIGINT,
    lastorderdate TIMESTAMP,
    tier TEXT,
    avgpercustomer DOUBLE PRECISION,
    dayssincelastorder INT
) AS $$
DECLARE
    v_total_customers INT;
BEGIN
    -- Count qualifying customers first
    SELECT COUNT(*) INTO v_total_customers
    FROM (
        SELECT c.customerid
        FROM public.customers c
        INNER JOIN public.sales s ON c.customerid = s.customerid
        WHERE s.orderdate BETWEEN p_start_date AND p_end_date
        GROUP BY c.customerid
        HAVING SUM(s.amount) >= p_min_amount
    ) sub;

    RETURN QUERY
    WITH customer_summary AS (
        SELECT
            c.customerid,
            c.customername,
            SUM(s.amount) AS totalspent,
            COUNT(*) AS ordercount,
            MAX(s.orderdate) AS lastorderdate
        FROM public.customers c
        INNER JOIN public.sales s ON c.customerid = s.customerid
        WHERE s.orderdate BETWEEN p_start_date AND p_end_date
        GROUP BY c.customerid, c.customername
        HAVING SUM(s.amount) >= p_min_amount
    )
    SELECT
        cs.customerid,
        cs.customername,
        cs.totalspent,
        cs.ordercount,
        cs.lastorderdate,
        CASE WHEN cs.totalspent > 10000 THEN 'Premium' ELSE 'Standard' END AS tier,
        cs.totalspent::double precision / NULLIF(v_total_customers, 0) AS avgpercustomer,
        (CURRENT_DATE - cs.lastorderdate::date) AS dayssincelastorder
    FROM customer_summary cs
    ORDER BY cs.totalspent DESC;
END;
$$ LANGUAGE plpgsql;

-- Usage:
-- SELECT * FROM public.usp_get_customer_summary('2024-01-01', '2024-12-31', 100);
```

### Key Changes

- `CREATE PROCEDURE` → `CREATE FUNCTION ... RETURNS TABLE`
- `@param` → `p_param` (PG naming convention)
- `DECLARE @var type` → `DECLARE v_var type;`
- `SET NOCOUNT ON` → removed (not needed)
- `SELECT INTO #temp` → CTE (no temp table needed)
- `IIF(...)` → `CASE WHEN ... END`
- `CAST(x AS FLOAT)` → `x::double precision`
- `DATEDIFF(day, a, GETDATE())` → `(CURRENT_DATE - a::date)`

---

## Example 4: MERGE → INSERT ON CONFLICT (Upsert)

### Synapse (Before)

```sql
MERGE [dbo].[ProductInventory] AS target
USING [dbo].[StagingInventory] AS source
ON target.[ProductID] = source.[ProductID]
    AND target.[WarehouseID] = source.[WarehouseID]
WHEN MATCHED THEN
    UPDATE SET
        target.[Quantity] = source.[Quantity],
        target.[LastUpdated] = GETDATE()
WHEN NOT MATCHED THEN
    INSERT ([ProductID], [WarehouseID], [Quantity], [LastUpdated])
    VALUES (source.[ProductID], source.[WarehouseID], source.[Quantity], GETDATE());
```

### Hologres (After)

```sql
INSERT INTO public.productinventory (productid, warehouseid, quantity, lastupdated)
SELECT productid, warehouseid, quantity, CURRENT_TIMESTAMP
FROM public.staginginventory
ON CONFLICT (productid, warehouseid) DO UPDATE SET
    quantity = EXCLUDED.quantity,
    lastupdated = CURRENT_TIMESTAMP;
```

### Key Changes

- `MERGE...USING...WHEN MATCHED/NOT MATCHED` → `INSERT...ON CONFLICT DO UPDATE`
- Requires a unique constraint or primary key on `(productid, warehouseid)`
- `EXCLUDED` refers to the proposed row (equivalent to `source.` in MERGE)
- `GETDATE()` → `CURRENT_TIMESTAMP`

---

## Example 5: CROSS APPLY / OUTER APPLY → LATERAL JOIN

### Synapse (Before)

```sql
SELECT
    o.[OrderID],
    o.[CustomerID],
    t.TopProduct,
    t.TopAmount
FROM [dbo].[Orders] o
CROSS APPLY (
    SELECT TOP 1
        d.[ProductName] AS TopProduct,
        d.[Amount] AS TopAmount
    FROM [dbo].[OrderDetails] d
    WHERE d.[OrderID] = o.[OrderID]
    ORDER BY d.[Amount] DESC
) t;
```

### Hologres (After)

```sql
SELECT
    o.orderid,
    o.customerid,
    t.topproduct,
    t.topamount
FROM public.orders o
CROSS JOIN LATERAL (
    SELECT
        d.productname AS topproduct,
        d.amount AS topamount
    FROM public.orderdetails d
    WHERE d.orderid = o.orderid
    ORDER BY d.amount DESC
    LIMIT 1
) t;
```

### Key Changes

- `CROSS APPLY` → `CROSS JOIN LATERAL`
- `TOP 1` → `LIMIT 1` (moved to end of subquery)
- For `OUTER APPLY`, use `LEFT JOIN LATERAL (...) t ON TRUE`

---

## Example 6: String Aggregation with Ordering

### Synapse (Before)

```sql
SELECT
    [DepartmentID],
    STRING_AGG([EmployeeName], ', ') WITHIN GROUP (ORDER BY [EmployeeName]) AS employees
FROM [dbo].[Employees]
GROUP BY [DepartmentID];
```

### Hologres (After)

```sql
SELECT
    departmentid,
    STRING_AGG(employeename, ', ' ORDER BY employeename) AS employees
FROM public.employees
GROUP BY departmentid;
```

### Key Changes

- `WITHIN GROUP (ORDER BY ...)` → ORDER BY placed inside `STRING_AGG()`
