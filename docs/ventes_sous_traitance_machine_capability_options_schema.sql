/*
Ventes Sous-Traitance machine capability options catalog
Target DB: Cedule (SQL Server)

Purpose:
1) Store reusable capability options to drive UI forms.
2) Allow POST/PATCH on machine capability options without touching machine rows.
*/

IF OBJECT_ID('[dbo].[40_VENTES_SOUSTRAITANCE_machine_capability_options]', 'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[40_VENTES_SOUSTRAITANCE_machine_capability_options] (
        [option_id] UNIQUEIDENTIFIER NOT NULL CONSTRAINT [DF_40VSS_mco_id] DEFAULT NEWID(),
        [capability_code] NVARCHAR(100) NOT NULL,
        [capability_value] NVARCHAR(200) NULL,
        [unit] NVARCHAR(20) NULL,
        [is_active] BIT NOT NULL CONSTRAINT [DF_40VSS_mco_active] DEFAULT (1),
        [notes] NVARCHAR(MAX) NULL,
        [created_at] DATETIME2(3) NOT NULL CONSTRAINT [DF_40VSS_mco_created] DEFAULT SYSUTCDATETIME(),
        [updated_at] DATETIME2(3) NOT NULL CONSTRAINT [DF_40VSS_mco_updated] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [PK_40VSS_mco] PRIMARY KEY ([option_id]),
        CONSTRAINT [UQ_40VSS_mco_unique] UNIQUE ([capability_code], [capability_value], [unit])
    );
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_40VSS_mco_code_active'
      AND object_id = OBJECT_ID('[dbo].[40_VENTES_SOUSTRAITANCE_machine_capability_options]')
)
BEGIN
    CREATE INDEX [IX_40VSS_mco_code_active]
        ON [dbo].[40_VENTES_SOUSTRAITANCE_machine_capability_options]([capability_code], [is_active]);
END
GO
