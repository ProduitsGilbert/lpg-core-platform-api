/*
Ventes Sous-Traitance machine configuration schema
Target DB: Cedule (SQL Server)

Purpose:
1) Store machine master data in SQL (instead of YAML in code)
2) Store machine capabilities/features in normalized form
3) Preserve FK to existing machine groups table
*/

IF OBJECT_ID('[dbo].[40_VENTES_SOUSTRAITANCE_machines]', 'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[40_VENTES_SOUSTRAITANCE_machines] (
        [machine_id] UNIQUEIDENTIFIER NOT NULL CONSTRAINT [DF_40VSS_machines_id] DEFAULT NEWID(),
        [machine_code] NVARCHAR(100) NOT NULL,
        [machine_name] NVARCHAR(200) NOT NULL,
        [machine_group_id] NVARCHAR(100) NULL,
        [is_active] BIT NOT NULL CONSTRAINT [DF_40VSS_machines_active] DEFAULT (1),

        -- LLM fallback defaults when confidence is low
        [default_setup_time_min] DECIMAL(10,2) NOT NULL CONSTRAINT [DF_40VSS_machines_setup] DEFAULT (0),
        [default_runtime_min] DECIMAL(10,2) NOT NULL CONSTRAINT [DF_40VSS_machines_runtime] DEFAULT (0),

        -- envelope and capacity
        [envelope_x_mm] DECIMAL(12,3) NULL,
        [envelope_y_mm] DECIMAL(12,3) NULL,
        [envelope_z_mm] DECIMAL(12,3) NULL,
        [max_part_weight_kg] DECIMAL(12,3) NULL,

        [notes] NVARCHAR(MAX) NULL,
        [created_at] DATETIME2(3) NOT NULL CONSTRAINT [DF_40VSS_machines_created] DEFAULT SYSUTCDATETIME(),
        [updated_at] DATETIME2(3) NOT NULL CONSTRAINT [DF_40VSS_machines_updated] DEFAULT SYSUTCDATETIME(),

        CONSTRAINT [PK_40VSS_machines] PRIMARY KEY ([machine_id]),
        CONSTRAINT [UQ_40VSS_machines_code] UNIQUE ([machine_code]),
        CONSTRAINT [FK_40VSS_machines_group] FOREIGN KEY ([machine_group_id])
            REFERENCES [dbo].[40_VENTES_SOUSTRAITANCE_machine_groups]([machine_group_id]),
        CONSTRAINT [CK_40VSS_machines_setup] CHECK ([default_setup_time_min] >= 0),
        CONSTRAINT [CK_40VSS_machines_runtime] CHECK ([default_runtime_min] >= 0)
    );
END
GO

IF OBJECT_ID('[dbo].[40_VENTES_SOUSTRAITANCE_machine_capabilities]', 'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[40_VENTES_SOUSTRAITANCE_machine_capabilities] (
        [capability_id] UNIQUEIDENTIFIER NOT NULL CONSTRAINT [DF_40VSS_machinecap_id] DEFAULT NEWID(),
        [machine_id] UNIQUEIDENTIFIER NOT NULL,
        [capability_code] NVARCHAR(100) NOT NULL,     -- e.g. AXES, CAN_BORE, MAX_RPM
        [capability_value] NVARCHAR(200) NULL,        -- free-form text
        [numeric_value] DECIMAL(18,4) NULL,           -- numeric capability value
        [bool_value] BIT NULL,                        -- true/false capability
        [unit] NVARCHAR(20) NULL,                     -- mm, kg, min, rpm, etc.
        [notes] NVARCHAR(MAX) NULL,
        [created_at] DATETIME2(3) NOT NULL CONSTRAINT [DF_40VSS_machinecap_created] DEFAULT SYSUTCDATETIME(),
        [updated_at] DATETIME2(3) NOT NULL CONSTRAINT [DF_40VSS_machinecap_updated] DEFAULT SYSUTCDATETIME(),

        CONSTRAINT [PK_40VSS_machinecap] PRIMARY KEY ([capability_id]),
        CONSTRAINT [FK_40VSS_machinecap_machine] FOREIGN KEY ([machine_id])
            REFERENCES [dbo].[40_VENTES_SOUSTRAITANCE_machines]([machine_id]) ON DELETE CASCADE,
        CONSTRAINT [UQ_40VSS_machinecap_code] UNIQUE ([machine_id], [capability_code])
    );
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_40VSS_machines_group'
      AND object_id = OBJECT_ID('[dbo].[40_VENTES_SOUSTRAITANCE_machines]')
)
BEGIN
    CREATE INDEX [IX_40VSS_machines_group]
        ON [dbo].[40_VENTES_SOUSTRAITANCE_machines]([machine_group_id], [is_active]);
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_40VSS_machinecap_machine'
      AND object_id = OBJECT_ID('[dbo].[40_VENTES_SOUSTRAITANCE_machine_capabilities]')
)
BEGIN
    CREATE INDEX [IX_40VSS_machinecap_machine]
        ON [dbo].[40_VENTES_SOUSTRAITANCE_machine_capabilities]([machine_id]);
END
GO
