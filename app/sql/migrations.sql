-- LPG Core Platform API Database Migrations
-- Target: Microsoft SQL Server (Business Central Database)
-- Version: 1.0.0
-- 
-- This script creates the required application tables for:
-- 1. Idempotency key storage
-- 2. Audit logging
--
-- Note: These tables are for application state only.
-- The ERP data remains in Business Central tables.

-- ============================================================================
-- IDEMPOTENCY TABLE
-- ============================================================================

-- Drop table if exists (for development - remove in production)
IF OBJECT_ID('[platform-code-app_idempotency]', 'U') IS NOT NULL
    DROP TABLE [platform-code-app_idempotency];

-- Create idempotency table
CREATE TABLE [platform-code-app_idempotency] (
    [key] NVARCHAR(128) NOT NULL,
    created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    response_json NVARCHAR(MAX) NULL,
    
    CONSTRAINT PK_platform_code_app_idempotency PRIMARY KEY CLUSTERED ([key])
);

-- Create index on created_at for cleanup queries
CREATE NONCLUSTERED INDEX IX_platform_code_app_idempotency_created_at 
ON [platform-code-app_idempotency] (created_at);

-- Add comment
EXEC sp_addextendedproperty 
    @name = N'MS_Description',
    @value = N'Stores idempotency keys and responses for request deduplication',
    @level0type = N'SCHEMA', @level0name = N'dbo',
    @level1type = N'TABLE', @level1name = N'platform-code-app_idempotency';

-- ============================================================================
-- AUDIT TABLE
-- ============================================================================

-- Drop table if exists (for development - remove in production)
IF OBJECT_ID('[platform-code-app_audit]', 'U') IS NOT NULL
    DROP TABLE [platform-code-app_audit];

-- Create audit table
CREATE TABLE [platform-code-app_audit] (
    id BIGINT IDENTITY(1,1) NOT NULL,
    at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    actor NVARCHAR(100) NOT NULL,
    action NVARCHAR(100) NOT NULL,
    po_id NVARCHAR(50) NULL,
    line_no INT NULL,
    previous NVARCHAR(MAX) NULL,
    [next] NVARCHAR(MAX) NULL,
    reason NVARCHAR(200) NULL,
    trace_id NVARCHAR(64) NULL,
    
    CONSTRAINT PK_platform_code_app_audit PRIMARY KEY CLUSTERED (id)
);

-- Create indexes for common queries
CREATE NONCLUSTERED INDEX IX_platform_code_app_audit_at 
ON [platform-code-app_audit] (at DESC);

CREATE NONCLUSTERED INDEX IX_platform_code_app_audit_actor 
ON [platform-code-app_audit] (actor);

CREATE NONCLUSTERED INDEX IX_platform_code_app_audit_action 
ON [platform-code-app_audit] (action);

CREATE NONCLUSTERED INDEX IX_platform_code_app_audit_po_id 
ON [platform-code-app_audit] (po_id) 
WHERE po_id IS NOT NULL;

CREATE NONCLUSTERED INDEX IX_platform_code_app_audit_trace_id 
ON [platform-code-app_audit] (trace_id) 
WHERE trace_id IS NOT NULL;

-- Add comment
EXEC sp_addextendedproperty 
    @name = N'MS_Description',
    @value = N'Audit trail for all ERP-modifying operations',
    @level0type = N'SCHEMA', @level0name = N'dbo',
    @level1type = N'TABLE', @level1name = N'platform-code-app_audit';

-- ============================================================================
-- OPTIONAL: APP LOCK TABLE (for scheduler coordination)
-- ============================================================================

-- Only create if using APScheduler with multiple instances
IF OBJECT_ID('[platform-code-app_lock]', 'U') IS NOT NULL
    DROP TABLE [platform-code-app_lock];

CREATE TABLE [platform-code-app_lock] (
    lock_name NVARCHAR(64) NOT NULL,
    locked_by NVARCHAR(100) NOT NULL,
    locked_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    expires_at DATETIME2 NOT NULL,
    
    CONSTRAINT PK_platform_code_app_lock PRIMARY KEY CLUSTERED (lock_name)
);

-- Add comment
EXEC sp_addextendedproperty 
    @name = N'MS_Description',
    @value = N'Distributed lock table for scheduler coordination',
    @level0type = N'SCHEMA', @level0name = N'dbo',
    @level1type = N'TABLE', @level1name = N'platform-code-app_lock';

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify tables were created
SELECT 
    t.name AS TableName,
    p.rows AS RowCount,
    SUM(a.total_pages) * 8 AS TotalSpaceKB,
    CAST(ROUND(((SUM(a.total_pages) * 8) / 1024.00), 2) AS NUMERIC(36, 2)) AS TotalSpaceMB
FROM sys.tables t
INNER JOIN sys.indexes i ON t.object_id = i.object_id
INNER JOIN sys.partitions p ON i.object_id = p.object_id AND i.index_id = p.index_id
INNER JOIN sys.allocation_units a ON p.partition_id = a.container_id
WHERE t.name IN ('platform-code-app_idempotency', 'platform-code-app_audit', 'platform-code-app_lock')
    AND t.is_ms_shipped = 0
    AND i.object_id > 255
GROUP BY t.name, p.rows
ORDER BY t.name;

-- ============================================================================
-- ROLLBACK SCRIPT (if needed)
-- ============================================================================

/*
-- To rollback, run these commands:
DROP TABLE IF EXISTS [platform-code-app_idempotency];
DROP TABLE IF EXISTS [platform-code-app_audit];
DROP TABLE IF EXISTS [platform-code-app_lock];
*/

-- ============================================================================
-- SAMPLE DATA (for testing only - remove in production)
-- ============================================================================

/*
-- Sample idempotency record
INSERT INTO [platform-code-app_idempotency] ([key], response_json)
VALUES ('test-key-001', '{"status": "success", "data": {"po_id": "PO-001"}}');

-- Sample audit record
INSERT INTO [platform-code-app_audit] 
(actor, action, po_id, line_no, previous, [next], reason, trace_id)
VALUES 
('user:test', 'POLine.PromiseDateChanged', 'PO-001', 1, 
 '{"promise_date": "2024-01-01"}', 
 '{"promise_date": "2024-02-01"}', 
 'Vendor delay notification', 
 'trace-001');

-- Verify inserts
SELECT * FROM [platform-code-app_idempotency];
SELECT * FROM [platform-code-app_audit];
*/

PRINT 'Migration completed successfully';
PRINT 'Tables created:';
PRINT '  - [platform-code-app_idempotency]';
PRINT '  - [platform-code-app_audit]';
PRINT '  - [platform-code-app_lock]';