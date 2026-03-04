/*
Adds fee/tax breakdown fields to carrier statement transactions.
Target DB: Cedule
Table: [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_AP_Transport_Carrier_Statement_Transaction]
*/

DECLARE @table_name NVARCHAR(256);

SELECT TOP (1) @table_name = t.name
FROM [Cedule].sys.tables t
JOIN [Cedule].sys.schemas s ON s.schema_id = t.schema_id
WHERE s.name = 'dbo'
  AND t.name LIKE '30_COMPTABILITÉ ET FINANCES_AP_Transport_Carrier_Statement_Transaction'
ORDER BY t.name;

IF @table_name IS NULL
BEGIN
    THROW 50000, 'Carrier statement transaction table not found in Cedule.dbo', 1;
END;

IF NOT EXISTS (
    SELECT 1
    FROM [Cedule].sys.columns c
    JOIN [Cedule].sys.tables t ON t.object_id = c.object_id
    JOIN [Cedule].sys.schemas s ON s.schema_id = t.schema_id
    WHERE s.name = 'dbo'
      AND t.name = @table_name
      AND c.name = 'subtotal_before_tax'
)
BEGIN
    EXEC (
        N'ALTER TABLE [Cedule].[dbo].[' + @table_name
        + N'] ADD subtotal_before_tax DECIMAL(18,2) NULL;'
    );
END;

IF NOT EXISTS (
    SELECT 1
    FROM [Cedule].sys.columns c
    JOIN [Cedule].sys.tables t ON t.object_id = c.object_id
    JOIN [Cedule].sys.schemas s ON s.schema_id = t.schema_id
    WHERE s.name = 'dbo'
      AND t.name = @table_name
      AND c.name = 'tax_lines_json'
)
BEGIN
    EXEC (N'ALTER TABLE [Cedule].[dbo].[' + @table_name + N'] ADD tax_lines_json NVARCHAR(MAX) NULL;');
END;

IF NOT EXISTS (
    SELECT 1
    FROM [Cedule].sys.columns c
    JOIN [Cedule].sys.tables t ON t.object_id = c.object_id
    JOIN [Cedule].sys.schemas s ON s.schema_id = t.schema_id
    WHERE s.name = 'dbo'
      AND t.name = @table_name
      AND c.name = 'tax_total'
)
BEGIN
    EXEC (
        N'ALTER TABLE [Cedule].[dbo].[' + @table_name
        + N'] ADD tax_total DECIMAL(18,2) NULL;'
    );
END;

IF NOT EXISTS (
    SELECT 1
    FROM [Cedule].sys.columns c
    JOIN [Cedule].sys.tables t ON t.object_id = c.object_id
    JOIN [Cedule].sys.schemas s ON s.schema_id = t.schema_id
    WHERE s.name = 'dbo'
      AND t.name = @table_name
      AND c.name = 'tax_tps'
)
BEGIN
    EXEC (
        N'ALTER TABLE [Cedule].[dbo].[' + @table_name
        + N'] ADD tax_tps DECIMAL(18,2) NULL;'
    );
END;

IF NOT EXISTS (
    SELECT 1
    FROM [Cedule].sys.columns c
    JOIN [Cedule].sys.tables t ON t.object_id = c.object_id
    JOIN [Cedule].sys.schemas s ON s.schema_id = t.schema_id
    WHERE s.name = 'dbo'
      AND t.name = @table_name
      AND c.name = 'tax_tvq'
)
BEGIN
    EXEC (
        N'ALTER TABLE [Cedule].[dbo].[' + @table_name
        + N'] ADD tax_tvq DECIMAL(18,2) NULL;'
    );
END;
