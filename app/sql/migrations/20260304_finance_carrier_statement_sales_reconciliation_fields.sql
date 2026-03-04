/*
Adds sales-order reconciliation fields to carrier statement transactions.
Target DB: Cedule
Target table pattern: %Carrier_Statement_Transaction%
*/

DECLARE @table_name NVARCHAR(256);

SELECT TOP (1) @table_name = t.name
FROM [Cedule].sys.tables t
JOIN [Cedule].sys.schemas s ON s.schema_id = t.schema_id
WHERE s.name = 'dbo'
  AND t.name LIKE '%Carrier_Statement_Transaction%'
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
      AND c.name = 'sales_invoice_number'
)
BEGIN
    EXEC (N'ALTER TABLE [Cedule].[dbo].[' + @table_name + N'] ADD sales_invoice_number NVARCHAR(100) NULL;');
END;

IF NOT EXISTS (
    SELECT 1
    FROM [Cedule].sys.columns c
    JOIN [Cedule].sys.tables t ON t.object_id = c.object_id
    JOIN [Cedule].sys.schemas s ON s.schema_id = t.schema_id
    WHERE s.name = 'dbo'
      AND t.name = @table_name
      AND c.name = 'sales_transport_charge_line_amount'
)
BEGIN
    EXEC (
        N'ALTER TABLE [Cedule].[dbo].[' + @table_name
        + N'] ADD sales_transport_charge_line_amount DECIMAL(18,2) NULL;'
    );
END;

IF NOT EXISTS (
    SELECT 1
    FROM [Cedule].sys.columns c
    JOIN [Cedule].sys.tables t ON t.object_id = c.object_id
    JOIN [Cedule].sys.schemas s ON s.schema_id = t.schema_id
    WHERE s.name = 'dbo'
      AND t.name = @table_name
      AND c.name = 'sales_total_amount_incl_vat'
)
BEGIN
    EXEC (
        N'ALTER TABLE [Cedule].[dbo].[' + @table_name
        + N'] ADD sales_total_amount_incl_vat DECIMAL(18,2) NULL;'
    );
END;
