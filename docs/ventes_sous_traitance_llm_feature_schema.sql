/*
Ventes Sous-Traitance LLM feature schema
Target DB: Cedule (SQL Server)

Purpose:
1) Persist normalized Step 4 machining features from LLM output
2) Persist part-level feature summary/additional operations/general notes
3) Enrich existing routing scenarios with confidence/assumptions/unknowns metadata
*/

IF OBJECT_ID('[dbo].[40_VENTES_SOUSTRAITANCE_part_feature_sets]', 'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[40_VENTES_SOUSTRAITANCE_part_feature_sets] (
        [feature_set_id] UNIQUEIDENTIFIER NOT NULL CONSTRAINT [DF_40VSS_feature_set_id] DEFAULT NEWID(),
        [part_id] UNIQUEIDENTIFIER NOT NULL,
        [source] NVARCHAR(20) NOT NULL CONSTRAINT [DF_40VSS_feature_set_source] DEFAULT ('llm'),
        [source_run_id] UNIQUEIDENTIFIER NULL,
        [feature_confidence] DECIMAL(5,4) NULL,
        [part_summary_json] NVARCHAR(MAX) NULL,
        [additional_operations_json] NVARCHAR(MAX) NULL,
        [general_notes_json] NVARCHAR(MAX) NULL,
        [created_at] DATETIME2(3) NOT NULL CONSTRAINT [DF_40VSS_feature_set_created] DEFAULT SYSUTCDATETIME(),
        [updated_at] DATETIME2(3) NOT NULL CONSTRAINT [DF_40VSS_feature_set_updated] DEFAULT SYSUTCDATETIME(),

        CONSTRAINT [PK_40VSS_part_feature_sets] PRIMARY KEY ([feature_set_id]),
        CONSTRAINT [UQ_40VSS_part_feature_sets_part] UNIQUE ([part_id]),
        CONSTRAINT [FK_40VSS_part_feature_sets_part] FOREIGN KEY ([part_id])
            REFERENCES [dbo].[40_VENTES_SOUSTRAITANCE_quote_parts]([part_id]) ON DELETE CASCADE,
        CONSTRAINT [FK_40VSS_part_feature_sets_run] FOREIGN KEY ([source_run_id])
            REFERENCES [dbo].[40_VENTES_SOUSTRAITANCE_llm_runs]([run_id]),
        CONSTRAINT [CK_40VSS_feature_set_source] CHECK ([source] IN ('llm', 'rules', 'user')),
        CONSTRAINT [CK_40VSS_feature_set_conf] CHECK ([feature_confidence] IS NULL OR ([feature_confidence] >= 0 AND [feature_confidence] <= 1))
    );
END
GO

IF OBJECT_ID('[dbo].[40_VENTES_SOUSTRAITANCE_part_features]', 'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[40_VENTES_SOUSTRAITANCE_part_features] (
        [feature_id] UNIQUEIDENTIFIER NOT NULL CONSTRAINT [DF_40VSS_part_feature_id] DEFAULT NEWID(),
        [part_id] UNIQUEIDENTIFIER NOT NULL,
        [source] NVARCHAR(20) NOT NULL CONSTRAINT [DF_40VSS_part_feature_source] DEFAULT ('llm'),
        [source_run_id] UNIQUEIDENTIFIER NULL,
        [feature_ref] NVARCHAR(50) NULL,
        [feature_type] NVARCHAR(100) NOT NULL,
        [description] NVARCHAR(2000) NULL,
        [quantity] INT NOT NULL CONSTRAINT [DF_40VSS_part_feature_qty] DEFAULT (1),
        [width_mm] DECIMAL(12,3) NULL,
        [length_mm] DECIMAL(12,3) NULL,
        [depth_mm] DECIMAL(12,3) NULL,
        [diameter_mm] DECIMAL(12,3) NULL,
        [thread_spec] NVARCHAR(50) NULL,
        [tolerance_note] NVARCHAR(100) NULL,
        [surface_finish_ra_um] DECIMAL(12,3) NULL,
        [location_note] NVARCHAR(200) NULL,
        [complexity_factors_json] NVARCHAR(MAX) NULL,
        [estimated_operation_time_min] DECIMAL(12,3) NULL,
        [is_user_override] BIT NOT NULL CONSTRAINT [DF_40VSS_part_feature_override] DEFAULT (0),
        [created_at] DATETIME2(3) NOT NULL CONSTRAINT [DF_40VSS_part_feature_created] DEFAULT SYSUTCDATETIME(),
        [updated_at] DATETIME2(3) NOT NULL CONSTRAINT [DF_40VSS_part_feature_updated] DEFAULT SYSUTCDATETIME(),

        CONSTRAINT [PK_40VSS_part_features] PRIMARY KEY ([feature_id]),
        CONSTRAINT [FK_40VSS_part_features_part] FOREIGN KEY ([part_id])
            REFERENCES [dbo].[40_VENTES_SOUSTRAITANCE_quote_parts]([part_id]) ON DELETE CASCADE,
        CONSTRAINT [FK_40VSS_part_features_run] FOREIGN KEY ([source_run_id])
            REFERENCES [dbo].[40_VENTES_SOUSTRAITANCE_llm_runs]([run_id]),
        CONSTRAINT [CK_40VSS_part_feature_source] CHECK ([source] IN ('llm', 'rules', 'user')),
        CONSTRAINT [CK_40VSS_part_feature_qty] CHECK ([quantity] >= 1),
        CONSTRAINT [CK_40VSS_part_feature_dims] CHECK (
            ([width_mm] IS NULL OR [width_mm] >= 0) AND
            ([length_mm] IS NULL OR [length_mm] >= 0) AND
            ([depth_mm] IS NULL OR [depth_mm] >= 0) AND
            ([diameter_mm] IS NULL OR [diameter_mm] >= 0) AND
            ([surface_finish_ra_um] IS NULL OR [surface_finish_ra_um] >= 0) AND
            ([estimated_operation_time_min] IS NULL OR [estimated_operation_time_min] >= 0)
        )
    );
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_40VSS_part_features_part'
      AND object_id = OBJECT_ID('[dbo].[40_VENTES_SOUSTRAITANCE_part_features]')
)
BEGIN
    CREATE INDEX [IX_40VSS_part_features_part]
        ON [dbo].[40_VENTES_SOUSTRAITANCE_part_features]([part_id], [created_at]);
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_40VSS_part_features_run'
      AND object_id = OBJECT_ID('[dbo].[40_VENTES_SOUSTRAITANCE_part_features]')
)
BEGIN
    CREATE INDEX [IX_40VSS_part_features_run]
        ON [dbo].[40_VENTES_SOUSTRAITANCE_part_features]([source_run_id]);
END
GO

IF COL_LENGTH('[dbo].[40_VENTES_SOUSTRAITANCE_part_routings]', 'confidence_score') IS NULL
BEGIN
    ALTER TABLE [dbo].[40_VENTES_SOUSTRAITANCE_part_routings]
        ADD [confidence_score] DECIMAL(5,4) NULL;
END
GO

IF COL_LENGTH('[dbo].[40_VENTES_SOUSTRAITANCE_part_routings]', 'assumptions_json') IS NULL
BEGIN
    ALTER TABLE [dbo].[40_VENTES_SOUSTRAITANCE_part_routings]
        ADD [assumptions_json] NVARCHAR(MAX) NULL;
END
GO

IF COL_LENGTH('[dbo].[40_VENTES_SOUSTRAITANCE_part_routings]', 'unknowns_json') IS NULL
BEGIN
    ALTER TABLE [dbo].[40_VENTES_SOUSTRAITANCE_part_routings]
        ADD [unknowns_json] NVARCHAR(MAX) NULL;
END
GO

IF COL_LENGTH('[dbo].[40_VENTES_SOUSTRAITANCE_part_routings]', 'source_run_id') IS NULL
BEGIN
    ALTER TABLE [dbo].[40_VENTES_SOUSTRAITANCE_part_routings]
        ADD [source_run_id] UNIQUEIDENTIFIER NULL;
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.foreign_keys
    WHERE name = 'FK_40VSS_routings_run'
      AND parent_object_id = OBJECT_ID('[dbo].[40_VENTES_SOUSTRAITANCE_part_routings]')
)
BEGIN
    ALTER TABLE [dbo].[40_VENTES_SOUSTRAITANCE_part_routings]
        ADD CONSTRAINT [FK_40VSS_routings_run]
            FOREIGN KEY ([source_run_id])
            REFERENCES [dbo].[40_VENTES_SOUSTRAITANCE_llm_runs]([run_id]);
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.check_constraints
    WHERE name = 'CK_40VSS_part_routings_conf'
      AND parent_object_id = OBJECT_ID('[dbo].[40_VENTES_SOUSTRAITANCE_part_routings]')
)
BEGIN
    ALTER TABLE [dbo].[40_VENTES_SOUSTRAITANCE_part_routings]
        ADD CONSTRAINT [CK_40VSS_part_routings_conf]
            CHECK ([confidence_score] IS NULL OR ([confidence_score] >= 0 AND [confidence_score] <= 1));
END
GO
