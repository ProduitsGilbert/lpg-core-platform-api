/*
ERP production costing snapshot schema
Target DB: Cedule (SQL Server)

Purpose:
1) Persist full snapshots of RoutingLines and ProductionBOMLines payloads
2) Keep per-source (routing/bom) watermark based on header Last Modified Date
3) Track scan runs (manual/scheduler) and outcomes

Safe for existing data: idempotent CREATE/INDEX statements.
*/

IF OBJECT_ID('[Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SCANS]', 'U') IS NULL
BEGIN
    CREATE TABLE [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SCANS] (
        [scan_id] UNIQUEIDENTIFIER NOT NULL,
        [scan_started_at] DATETIME2(3) NOT NULL CONSTRAINT [DF_EPCScans_started] DEFAULT SYSUTCDATETIME(),
        [scan_finished_at] DATETIME2(3) NULL,
        [scan_mode] NVARCHAR(10) NOT NULL,
        [trigger_source] NVARCHAR(30) NOT NULL,
        [status] NVARCHAR(20) NOT NULL,
        [since_modified_at] DATETIME2(3) NULL,
        [until_modified_at] DATETIME2(3) NULL,
        [routing_headers_count] INT NOT NULL CONSTRAINT [DF_EPCScans_rh] DEFAULT (0),
        [bom_headers_count] INT NOT NULL CONSTRAINT [DF_EPCScans_bh] DEFAULT (0),
        [routing_lines_count] INT NOT NULL CONSTRAINT [DF_EPCScans_rl] DEFAULT (0),
        [bom_lines_count] INT NOT NULL CONSTRAINT [DF_EPCScans_bl] DEFAULT (0),
        [error_message] NVARCHAR(MAX) NULL,

        CONSTRAINT [PK_EPCScans] PRIMARY KEY ([scan_id]),
        CONSTRAINT [CK_EPCScans_mode] CHECK ([scan_mode] IN ('full', 'delta')),
        CONSTRAINT [CK_EPCScans_status] CHECK ([status] IN ('running', 'success', 'failed'))
    );
END
GO

IF OBJECT_ID('[Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_STATE]', 'U') IS NULL
BEGIN
    CREATE TABLE [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_STATE] (
        [source_type] NVARCHAR(20) NOT NULL,
        [last_successful_modified_at] DATETIME2(3) NULL,
        [last_scan_id] UNIQUEIDENTIFIER NULL,
        [updated_at] DATETIME2(3) NOT NULL CONSTRAINT [DF_EPCSState_updated] DEFAULT SYSUTCDATETIME(),

        CONSTRAINT [PK_EPCSState] PRIMARY KEY ([source_type]),
        CONSTRAINT [CK_EPCSState_source] CHECK ([source_type] IN ('routing', 'bom')),
        CONSTRAINT [FK_EPCSState_scan] FOREIGN KEY ([last_scan_id])
            REFERENCES [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SCANS]([scan_id])
    );
END
GO

IF OBJECT_ID('[Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SNAPSHOT]', 'U') IS NULL
BEGIN
    CREATE TABLE [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SNAPSHOT] (
        [snapshot_id] BIGINT IDENTITY(1,1) NOT NULL,
        [scan_id] UNIQUEIDENTIFIER NOT NULL,
        [source_type] NVARCHAR(20) NOT NULL,
        [source_no] NVARCHAR(100) NOT NULL,
        [source_base_item_no] NVARCHAR(50) NOT NULL,
        [header_last_modified_at] DATETIME2(3) NULL,
        [line_key] NVARCHAR(200) NULL,
        [row_json] NVARCHAR(MAX) NOT NULL,
        [created_at] DATETIME2(3) NOT NULL CONSTRAINT [DF_EPCSLine_created] DEFAULT SYSUTCDATETIME(),

        CONSTRAINT [PK_EPCSLine] PRIMARY KEY ([snapshot_id]),
        CONSTRAINT [FK_EPCSLine_scan] FOREIGN KEY ([scan_id])
            REFERENCES [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SCANS]([scan_id]) ON DELETE CASCADE,
        CONSTRAINT [CK_EPCSLine_source] CHECK ([source_type] IN ('routing', 'bom'))
    );
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_EPCSLine_item_lookup'
      AND object_id = OBJECT_ID('[Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SNAPSHOT]')
)
BEGIN
    CREATE INDEX [IX_EPCSLine_item_lookup]
        ON [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SNAPSHOT]([source_base_item_no], [source_type], [source_no], [scan_id]);
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_EPCSLine_scan_lookup'
      AND object_id = OBJECT_ID('[Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SNAPSHOT]')
)
BEGIN
    CREATE INDEX [IX_EPCSLine_scan_lookup]
        ON [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SNAPSHOT]([scan_id], [source_type], [source_no]);
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_EPCScans_started'
      AND object_id = OBJECT_ID('[Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SCANS]')
)
BEGIN
    CREATE INDEX [IX_EPCScans_started]
        ON [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SCANS]([scan_started_at] DESC);
END
GO
