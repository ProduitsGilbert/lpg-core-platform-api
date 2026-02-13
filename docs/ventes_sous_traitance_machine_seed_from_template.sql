/*
Seed script for Ventes Sous-Traitance machine configuration.
Safe to run multiple times (upsert behavior).
Requires:
  - [dbo].[40_VENTES_SOUSTRAITANCE_machine_groups]
  - [dbo].[40_VENTES_SOUSTRAITANCE_machines]
  - [dbo].[40_VENTES_SOUSTRAITANCE_machine_capabilities]
*/

SET NOCOUNT ON;
GO

/* -------------------------
   1) Machine groups
------------------------- */

IF EXISTS (SELECT 1 FROM [dbo].[40_VENTES_SOUSTRAITANCE_machine_groups] WHERE [machine_group_id] = 'CNC_BORING_LARGE_4AX')
BEGIN
    UPDATE [dbo].[40_VENTES_SOUSTRAITANCE_machine_groups]
    SET
        [name] = N'CNC Boring Large 4-Axis',
        [process_families_json] = N'["milling","boring","drilling","tapping"]',
        [config_json] = N'{"version":1,"seed":"template"}',
        [updated_at] = SYSUTCDATETIME()
    WHERE [machine_group_id] = 'CNC_BORING_LARGE_4AX';
END
ELSE
BEGIN
    INSERT INTO [dbo].[40_VENTES_SOUSTRAITANCE_machine_groups]
    ([machine_group_id], [name], [process_families_json], [config_json])
    VALUES
    ('CNC_BORING_LARGE_4AX', N'CNC Boring Large 4-Axis', N'["milling","boring","drilling","tapping"]', N'{"version":1,"seed":"template"}');
END
GO

IF EXISTS (SELECT 1 FROM [dbo].[40_VENTES_SOUSTRAITANCE_machine_groups] WHERE [machine_group_id] = 'CNC_TURN_BAR_MEDIUM')
BEGIN
    UPDATE [dbo].[40_VENTES_SOUSTRAITANCE_machine_groups]
    SET
        [name] = N'CNC Turning - Bar Work Medium',
        [process_families_json] = N'["turning","drilling","tapping"]',
        [config_json] = N'{"version":1,"seed":"template"}',
        [updated_at] = SYSUTCDATETIME()
    WHERE [machine_group_id] = 'CNC_TURN_BAR_MEDIUM';
END
ELSE
BEGIN
    INSERT INTO [dbo].[40_VENTES_SOUSTRAITANCE_machine_groups]
    ([machine_group_id], [name], [process_families_json], [config_json])
    VALUES
    ('CNC_TURN_BAR_MEDIUM', N'CNC Turning - Bar Work Medium', N'["turning","drilling","tapping"]', N'{"version":1,"seed":"template"}');
END
GO

IF EXISTS (SELECT 1 FROM [dbo].[40_VENTES_SOUSTRAITANCE_machine_groups] WHERE [machine_group_id] = 'PLASMA_TABLE_LARGE')
BEGIN
    UPDATE [dbo].[40_VENTES_SOUSTRAITANCE_machine_groups]
    SET
        [name] = N'Plasma Cutting Table Large',
        [process_families_json] = N'["plasma_cut"]',
        [config_json] = N'{"version":1,"seed":"template"}',
        [updated_at] = SYSUTCDATETIME()
    WHERE [machine_group_id] = 'PLASMA_TABLE_LARGE';
END
ELSE
BEGIN
    INSERT INTO [dbo].[40_VENTES_SOUSTRAITANCE_machine_groups]
    ([machine_group_id], [name], [process_families_json], [config_json])
    VALUES
    ('PLASMA_TABLE_LARGE', N'Plasma Cutting Table Large', N'["plasma_cut"]', N'{"version":1,"seed":"template"}');
END
GO

IF EXISTS (SELECT 1 FROM [dbo].[40_VENTES_SOUSTRAITANCE_machine_groups] WHERE [machine_group_id] = 'WELD_FAB_STANDARD')
BEGIN
    UPDATE [dbo].[40_VENTES_SOUSTRAITANCE_machine_groups]
    SET
        [name] = N'Welding / Fabrication Standard Bay',
        [process_families_json] = N'["welding","fitting","grinding"]',
        [config_json] = N'{"version":1,"seed":"template"}',
        [updated_at] = SYSUTCDATETIME()
    WHERE [machine_group_id] = 'WELD_FAB_STANDARD';
END
ELSE
BEGIN
    INSERT INTO [dbo].[40_VENTES_SOUSTRAITANCE_machine_groups]
    ([machine_group_id], [name], [process_families_json], [config_json])
    VALUES
    ('WELD_FAB_STANDARD', N'Welding / Fabrication Standard Bay', N'["welding","fitting","grinding"]', N'{"version":1,"seed":"template"}');
END
GO

/* -------------------------
   2) Machines
------------------------- */

IF EXISTS (SELECT 1 FROM [dbo].[40_VENTES_SOUSTRAITANCE_machines] WHERE [machine_code] = 'CNC_BORING_LARGE_4AX_M01')
BEGIN
    UPDATE [dbo].[40_VENTES_SOUSTRAITANCE_machines]
    SET
        [machine_name] = N'CNC Boring Large 4-Axis - Main',
        [machine_group_id] = 'CNC_BORING_LARGE_4AX',
        [is_active] = 1,
        [default_setup_time_min] = 120,
        [default_runtime_min] = 45,
        [envelope_x_mm] = 2500,
        [envelope_y_mm] = 1500,
        [envelope_z_mm] = 1200,
        [max_part_weight_kg] = 5000,
        [notes] = N'Prefer for large prismatic parts. Rotary B indexing.',
        [updated_at] = SYSUTCDATETIME()
    WHERE [machine_code] = 'CNC_BORING_LARGE_4AX_M01';
END
ELSE
BEGIN
    INSERT INTO [dbo].[40_VENTES_SOUSTRAITANCE_machines]
    (
        [machine_code], [machine_name], [machine_group_id], [is_active],
        [default_setup_time_min], [default_runtime_min],
        [envelope_x_mm], [envelope_y_mm], [envelope_z_mm], [max_part_weight_kg], [notes]
    )
    VALUES
    (
        'CNC_BORING_LARGE_4AX_M01', N'CNC Boring Large 4-Axis - Main', 'CNC_BORING_LARGE_4AX', 1,
        120, 45,
        2500, 1500, 1200, 5000, N'Prefer for large prismatic parts. Rotary B indexing.'
    );
END
GO

IF EXISTS (SELECT 1 FROM [dbo].[40_VENTES_SOUSTRAITANCE_machines] WHERE [machine_code] = 'CNC_TURN_BAR_MEDIUM_M01')
BEGIN
    UPDATE [dbo].[40_VENTES_SOUSTRAITANCE_machines]
    SET
        [machine_name] = N'CNC Turning - Bar Work Medium - Main',
        [machine_group_id] = 'CNC_TURN_BAR_MEDIUM',
        [is_active] = 1,
        [default_setup_time_min] = 45,
        [default_runtime_min] = 20,
        [envelope_x_mm] = NULL,
        [envelope_y_mm] = NULL,
        [envelope_z_mm] = NULL,
        [max_part_weight_kg] = 40,
        [notes] = N'2-axis turning bar work.',
        [updated_at] = SYSUTCDATETIME()
    WHERE [machine_code] = 'CNC_TURN_BAR_MEDIUM_M01';
END
ELSE
BEGIN
    INSERT INTO [dbo].[40_VENTES_SOUSTRAITANCE_machines]
    (
        [machine_code], [machine_name], [machine_group_id], [is_active],
        [default_setup_time_min], [default_runtime_min], [max_part_weight_kg], [notes]
    )
    VALUES
    (
        'CNC_TURN_BAR_MEDIUM_M01', N'CNC Turning - Bar Work Medium - Main', 'CNC_TURN_BAR_MEDIUM', 1,
        45, 20, 40, N'2-axis turning bar work.'
    );
END
GO

IF EXISTS (SELECT 1 FROM [dbo].[40_VENTES_SOUSTRAITANCE_machines] WHERE [machine_code] = 'PLASMA_TABLE_LARGE_M01')
BEGIN
    UPDATE [dbo].[40_VENTES_SOUSTRAITANCE_machines]
    SET
        [machine_name] = N'Plasma Cutting Table Large - Main',
        [machine_group_id] = 'PLASMA_TABLE_LARGE',
        [is_active] = 1,
        [default_setup_time_min] = 30,
        [default_runtime_min] = 15,
        [envelope_x_mm] = 3000,
        [envelope_y_mm] = 1500,
        [envelope_z_mm] = 0,
        [max_part_weight_kg] = NULL,
        [notes] = N'Small holes may require drilling instead of plasma.',
        [updated_at] = SYSUTCDATETIME()
    WHERE [machine_code] = 'PLASMA_TABLE_LARGE_M01';
END
ELSE
BEGIN
    INSERT INTO [dbo].[40_VENTES_SOUSTRAITANCE_machines]
    (
        [machine_code], [machine_name], [machine_group_id], [is_active],
        [default_setup_time_min], [default_runtime_min],
        [envelope_x_mm], [envelope_y_mm], [envelope_z_mm], [notes]
    )
    VALUES
    (
        'PLASMA_TABLE_LARGE_M01', N'Plasma Cutting Table Large - Main', 'PLASMA_TABLE_LARGE', 1,
        30, 15,
        3000, 1500, 0, N'Small holes may require drilling instead of plasma.'
    );
END
GO

IF EXISTS (SELECT 1 FROM [dbo].[40_VENTES_SOUSTRAITANCE_machines] WHERE [machine_code] = 'WELD_FAB_STANDARD_M01')
BEGIN
    UPDATE [dbo].[40_VENTES_SOUSTRAITANCE_machines]
    SET
        [machine_name] = N'Welding / Fabrication Standard Bay - Main',
        [machine_group_id] = 'WELD_FAB_STANDARD',
        [is_active] = 1,
        [default_setup_time_min] = 60,
        [default_runtime_min] = 30,
        [envelope_x_mm] = 6000,
        [envelope_y_mm] = 2500,
        [envelope_z_mm] = 2500,
        [max_part_weight_kg] = 8000,
        [notes] = N'Welding and fabrication standard bay.',
        [updated_at] = SYSUTCDATETIME()
    WHERE [machine_code] = 'WELD_FAB_STANDARD_M01';
END
ELSE
BEGIN
    INSERT INTO [dbo].[40_VENTES_SOUSTRAITANCE_machines]
    (
        [machine_code], [machine_name], [machine_group_id], [is_active],
        [default_setup_time_min], [default_runtime_min],
        [envelope_x_mm], [envelope_y_mm], [envelope_z_mm], [max_part_weight_kg], [notes]
    )
    VALUES
    (
        'WELD_FAB_STANDARD_M01', N'Welding / Fabrication Standard Bay - Main', 'WELD_FAB_STANDARD', 1,
        60, 30,
        6000, 2500, 2500, 8000, N'Welding and fabrication standard bay.'
    );
END
GO

/* -------------------------
   3) Capabilities (upsert)
------------------------- */

DELETE mc
FROM [dbo].[40_VENTES_SOUSTRAITANCE_machine_capabilities] mc
WHERE mc.[machine_id] IN (
    SELECT [machine_id]
    FROM [dbo].[40_VENTES_SOUSTRAITANCE_machines]
    WHERE [machine_code] IN (
        'CNC_BORING_LARGE_4AX_M01',
        'CNC_TURN_BAR_MEDIUM_M01',
        'PLASMA_TABLE_LARGE_M01',
        'WELD_FAB_STANDARD_M01'
    )
);
GO

DECLARE @cnc4ax UNIQUEIDENTIFIER = (SELECT [machine_id] FROM [dbo].[40_VENTES_SOUSTRAITANCE_machines] WHERE [machine_code] = 'CNC_BORING_LARGE_4AX_M01');
DECLARE @turnbar UNIQUEIDENTIFIER = (SELECT [machine_id] FROM [dbo].[40_VENTES_SOUSTRAITANCE_machines] WHERE [machine_code] = 'CNC_TURN_BAR_MEDIUM_M01');
DECLARE @plasma UNIQUEIDENTIFIER = (SELECT [machine_id] FROM [dbo].[40_VENTES_SOUSTRAITANCE_machines] WHERE [machine_code] = 'PLASMA_TABLE_LARGE_M01');
DECLARE @weldfab UNIQUEIDENTIFIER = (SELECT [machine_id] FROM [dbo].[40_VENTES_SOUSTRAITANCE_machines] WHERE [machine_code] = 'WELD_FAB_STANDARD_M01');

INSERT INTO [dbo].[40_VENTES_SOUSTRAITANCE_machine_capabilities]
([machine_id], [capability_code], [capability_value], [numeric_value], [bool_value], [unit], [notes])
VALUES
(@cnc4ax, 'PROCESS_FAMILIES', '["milling","boring","drilling","tapping"]', NULL, NULL, NULL, NULL),
(@cnc4ax, 'AXES', NULL, 4, NULL, NULL, NULL),
(@cnc4ax, 'TABLE_X_MM', NULL, 2000, NULL, 'mm', NULL),
(@cnc4ax, 'TABLE_Y_MM', NULL, 1200, NULL, 'mm', NULL),
(@cnc4ax, 'HAS_ROTARY', NULL, NULL, 1, NULL, NULL),
(@cnc4ax, 'ROTARY_TYPE', 'indexing', NULL, NULL, NULL, NULL),
(@cnc4ax, 'ROTARY_AXIS', 'B', NULL, NULL, NULL, NULL),
(@cnc4ax, 'CAN_TURN', NULL, NULL, 0, NULL, NULL),
(@cnc4ax, 'CAN_BORE', NULL, NULL, 1, NULL, NULL),
(@cnc4ax, 'CAN_THREADMILL', NULL, NULL, 1, NULL, NULL),
(@cnc4ax, 'CAN_PROBE', NULL, NULL, 1, NULL, NULL),
(@cnc4ax, 'COOLANT_THROUGH_SPINDLE', NULL, NULL, 1, NULL, NULL),
(@cnc4ax, 'MIN_HOLE_DIA_MM', NULL, 3, NULL, 'mm', NULL),
(@cnc4ax, 'MAX_BORE_DIA_MM', NULL, 300, NULL, 'mm', NULL),
(@cnc4ax, 'MIN_WALL_THICKNESS_MM', NULL, 4, NULL, 'mm', NULL),
(@cnc4ax, 'MAX_TOOL_STICKOUT_MM', NULL, 250, NULL, 'mm', NULL),
(@cnc4ax, 'TYPICAL_TOLERANCE_MM', NULL, 0.05, NULL, 'mm', NULL),
(@cnc4ax, 'BEST_TOLERANCE_MM', NULL, 0.02, NULL, 'mm', NULL),
(@cnc4ax, 'TYPICAL_SURFACE_FINISH_RA_UM', NULL, 3.2, NULL, 'um', NULL),
(@cnc4ax, 'BEST_SURFACE_FINISH_RA_UM', NULL, 1.6, NULL, 'um', NULL),
(@cnc4ax, 'MATERIAL_ALLOWED', '["steel","stainless","aluminum"]', NULL, NULL, NULL, NULL),
(@cnc4ax, 'SHOP_RATE_PER_HR', NULL, 150, NULL, 'CAD/hr', NULL),
(@cnc4ax, 'SETUP_RATE_PER_HR', NULL, 150, NULL, 'CAD/hr', NULL),
(@cnc4ax, 'LOAD_UNLOAD_MIN', NULL, 10, NULL, 'min', NULL),
(@cnc4ax, 'FLIP_RECLAMP_MIN', NULL, 15, NULL, 'min', NULL),
(@cnc4ax, 'TOOL_CHANGE_SEC', NULL, 8, NULL, 'sec', NULL),
(@cnc4ax, 'BASELINE_SETUP_MIN', NULL, 120, NULL, 'min', NULL),
(@cnc4ax, 'EXTRA_SETUP_EACH_MIN', NULL, 45, NULL, 'min', NULL),
(@cnc4ax, 'HEAVY_PART_OVER_2000KG_MIN', NULL, 30, NULL, 'min', NULL),
(@cnc4ax, 'TIGHT_TOLERANCE_MULTIPLIER', NULL, 1.25, NULL, NULL, NULL),
(@cnc4ax, 'COMPLEX_FIXTURING_MULTIPLIER', NULL, 1.30, NULL, NULL, NULL),

(@turnbar, 'PROCESS_FAMILIES', '["turning","drilling","tapping"]', NULL, NULL, NULL, NULL),
(@turnbar, 'AXES', NULL, 2, NULL, NULL, NULL),
(@turnbar, 'MAX_BAR_DIA_MM', NULL, 80, NULL, 'mm', NULL),
(@turnbar, 'MAX_TURN_LENGTH_MM', NULL, 400, NULL, 'mm', NULL),
(@turnbar, 'MAX_SWING_MM', NULL, 250, NULL, 'mm', NULL),
(@turnbar, 'CAN_TURN', NULL, NULL, 1, NULL, NULL),
(@turnbar, 'CAN_LIVE_TOOLING', NULL, NULL, 0, NULL, NULL),
(@turnbar, 'CAN_SUBSPINDLE', NULL, NULL, 0, NULL, NULL),
(@turnbar, 'TYPICAL_TOLERANCE_MM', NULL, 0.05, NULL, 'mm', NULL),
(@turnbar, 'BEST_TOLERANCE_MM', NULL, 0.02, NULL, 'mm', NULL),
(@turnbar, 'SHOP_RATE_PER_HR', NULL, 120, NULL, 'CAD/hr', NULL),
(@turnbar, 'SETUP_RATE_PER_HR', NULL, 120, NULL, 'CAD/hr', NULL),
(@turnbar, 'BASELINE_SETUP_MIN', NULL, 45, NULL, 'min', NULL),
(@turnbar, 'NEW_PROGRAMMING_MIN', NULL, 30, NULL, 'min', NULL),
(@turnbar, 'THREADING_MULTIPLIER', NULL, 1.15, NULL, NULL, NULL),
(@turnbar, 'TIGHT_TOLERANCE_MULTIPLIER', NULL, 1.20, NULL, NULL, NULL),

(@plasma, 'PROCESS_FAMILIES', '["plasma_cut"]', NULL, NULL, NULL, NULL),
(@plasma, 'MAX_THICKNESS_MM', NULL, 50, NULL, 'mm', NULL),
(@plasma, 'MIN_HOLE_DIA_MM', NULL, 8, NULL, 'mm', NULL),
(@plasma, 'SHOP_RATE_PER_HR', NULL, 95, NULL, 'CAD/hr', NULL),
(@plasma, 'PIERCE_TIME_SEC_EACH', NULL, 3, NULL, 'sec', NULL),
(@plasma, 'LEADIN_OUT_SEC_EACH', NULL, 2, NULL, 'sec', NULL),
(@plasma, 'SPEED_STEEL_6_MM_PER_MIN', NULL, 6000, NULL, 'mm/min', NULL),
(@plasma, 'SPEED_STEEL_12_MM_PER_MIN', NULL, 3500, NULL, 'mm/min', NULL),
(@plasma, 'SPEED_STEEL_25_MM_PER_MIN', NULL, 1800, NULL, 'mm/min', NULL),
(@plasma, 'SPEED_STEEL_50_MM_PER_MIN', NULL, 800, NULL, 'mm/min', NULL),

(@weldfab, 'PROCESS_FAMILIES', '["welding","fitting","grinding"]', NULL, NULL, NULL, NULL),
(@weldfab, 'WELD_PROCESSES', '["MIG","TIG"]', NULL, NULL, NULL, NULL),
(@weldfab, 'HAS_POSITIONER', NULL, NULL, 0, NULL, NULL),
(@weldfab, 'SHOP_RATE_PER_HR', NULL, 110, NULL, 'CAD/hr', NULL),
(@weldfab, 'WELD_MIN_PER_M_3MM', NULL, 10, NULL, 'min/m', NULL),
(@weldfab, 'WELD_MIN_PER_M_6MM', NULL, 18, NULL, 'min/m', NULL),
(@weldfab, 'WELD_MIN_PER_M_10MM', NULL, 30, NULL, 'min/m', NULL),
(@weldfab, 'FITTING_MIN_PER_JOINT', NULL, 8, NULL, 'min', NULL),
(@weldfab, 'GRIND_MIN_PER_M', NULL, 6, NULL, 'min/m', NULL);
GO
