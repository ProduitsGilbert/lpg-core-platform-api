-- Tool shortage prediction storage
-- Creates a dedicated database + daily KPI snapshot table.
-- Table prefix requirement: 90_USINAGE_ToolPrediction_

SET NOCOUNT ON;

IF DB_ID(N'USINAGE_ToolPrediction') IS NULL
BEGIN
    CREATE DATABASE [USINAGE_ToolPrediction];
END;
GO

USE [USINAGE_ToolPrediction];
GO

IF OBJECT_ID(N'[dbo].[90_USINAGE_ToolPrediction_DailySnapshot]', N'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[90_USINAGE_ToolPrediction_DailySnapshot] (
        [snapshot_date] DATE NOT NULL,
        [generated_at] DATETIME2(0) NOT NULL,
        [work_center_no] NVARCHAR(32) NOT NULL,
        [machine_center] NVARCHAR(64) NOT NULL,
        [tool_id] NVARCHAR(80) NOT NULL,

        [total_required_use_time_seconds] INT NOT NULL,
        [rows_count] INT NOT NULL,
        [program_count] INT NOT NULL,

        [total_remaining_life] FLOAT NOT NULL CONSTRAINT [DF_90_USINAGE_ToolPrediction_DailySnapshot_total_remaining_life] DEFAULT (0),
        [inventory_instances] INT NOT NULL CONSTRAINT [DF_90_USINAGE_ToolPrediction_DailySnapshot_inventory_instances] DEFAULT (0),
        [available_instances] INT NOT NULL CONSTRAINT [DF_90_USINAGE_ToolPrediction_DailySnapshot_available_instances] DEFAULT (0),
        [sister_count_total] INT NOT NULL CONSTRAINT [DF_90_USINAGE_ToolPrediction_DailySnapshot_sister_count_total] DEFAULT (0),
        [sister_count_available] INT NOT NULL CONSTRAINT [DF_90_USINAGE_ToolPrediction_DailySnapshot_sister_count_available] DEFAULT (0),
        [sister_count_machine] INT NOT NULL CONSTRAINT [DF_90_USINAGE_ToolPrediction_DailySnapshot_sister_count_machine] DEFAULT (0),

        [time_since_last_use_hours] FLOAT NOT NULL CONSTRAINT [DF_90_USINAGE_ToolPrediction_DailySnapshot_time_since_last_use_hours] DEFAULT (0),
        [uses_last_24h] INT NOT NULL CONSTRAINT [DF_90_USINAGE_ToolPrediction_DailySnapshot_uses_last_24h] DEFAULT (0),
        [uses_last_7d] INT NOT NULL CONSTRAINT [DF_90_USINAGE_ToolPrediction_DailySnapshot_uses_last_7d] DEFAULT (0),
        [wear_rate_24h] FLOAT NOT NULL CONSTRAINT [DF_90_USINAGE_ToolPrediction_DailySnapshot_wear_rate_24h] DEFAULT (0),
        [wear_rate_7d] FLOAT NOT NULL CONSTRAINT [DF_90_USINAGE_ToolPrediction_DailySnapshot_wear_rate_7d] DEFAULT (0),

        [tool_usage_minutes_90d] FLOAT NOT NULL CONSTRAINT [DF_90_USINAGE_ToolPrediction_DailySnapshot_tool_usage_minutes_90d] DEFAULT (0),
        [future_usage_minutes_24h] FLOAT NOT NULL CONSTRAINT [DF_90_USINAGE_ToolPrediction_DailySnapshot_future_usage_minutes_24h] DEFAULT (0),
        [future_usage_minutes_48h] FLOAT NOT NULL CONSTRAINT [DF_90_USINAGE_ToolPrediction_DailySnapshot_future_usage_minutes_48h] DEFAULT (0),
        [future_usage_minutes_7d] FLOAT NOT NULL CONSTRAINT [DF_90_USINAGE_ToolPrediction_DailySnapshot_future_usage_minutes_7d] DEFAULT (0),

        [shortage_probability] FLOAT NULL,
        [shortage_label] NVARCHAR(32) NULL,
        [prediction_payload_json] NVARCHAR(MAX) NULL,
        [predictor_response_json] NVARCHAR(MAX) NULL,

        [updated_at] DATETIME2(0) NOT NULL CONSTRAINT [DF_90_USINAGE_ToolPrediction_DailySnapshot_updated_at] DEFAULT (SYSUTCDATETIME()),

        CONSTRAINT [PK_90_USINAGE_ToolPrediction_DailySnapshot]
            PRIMARY KEY CLUSTERED ([snapshot_date], [machine_center], [tool_id])
    );
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'[dbo].[90_USINAGE_ToolPrediction_DailySnapshot]')
      AND name = N'IX_90_USINAGE_ToolPrediction_SnapshotMachineProbability'
)
BEGIN
    CREATE NONCLUSTERED INDEX [IX_90_USINAGE_ToolPrediction_SnapshotMachineProbability]
    ON [dbo].[90_USINAGE_ToolPrediction_DailySnapshot] (
        [snapshot_date] DESC,
        [machine_center] ASC,
        [shortage_probability] DESC
    )
    INCLUDE (
        [tool_id],
        [total_required_use_time_seconds],
        [future_usage_minutes_24h],
        [total_remaining_life],
        [available_instances],
        [shortage_label],
        [updated_at]
    );
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'[dbo].[90_USINAGE_ToolPrediction_DailySnapshot]')
      AND name = N'IX_90_USINAGE_ToolPrediction_MachineToolDate'
)
BEGIN
    CREATE NONCLUSTERED INDEX [IX_90_USINAGE_ToolPrediction_MachineToolDate]
    ON [dbo].[90_USINAGE_ToolPrediction_DailySnapshot] (
        [machine_center] ASC,
        [tool_id] ASC,
        [snapshot_date] DESC
    )
    INCLUDE (
        [shortage_probability],
        [shortage_label],
        [updated_at]
    );
END;
GO

PRINT 'USINAGE_ToolPrediction schema ready';
PRINT 'Table: [dbo].[90_USINAGE_ToolPrediction_DailySnapshot]';
