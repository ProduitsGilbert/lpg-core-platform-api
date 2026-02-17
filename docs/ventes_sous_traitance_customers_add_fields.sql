/*
Ventes Sous-Traitance customers table extension
Target DB: Cedule (SQL Server)

Purpose:
1) Add ship-to address block
2) Add customer contact name
3) Add global quote comment / LLM cue

Safe for existing data: idempotent ALTERs, all new columns nullable.
*/

IF COL_LENGTH('[dbo].[40_VENTES_SOUSTRAITANCE_customers]', 'ship_to_address') IS NULL
BEGIN
    ALTER TABLE [dbo].[40_VENTES_SOUSTRAITANCE_customers]
        ADD [ship_to_address] NVARCHAR(MAX) NULL;
END
GO

IF COL_LENGTH('[dbo].[40_VENTES_SOUSTRAITANCE_customers]', 'contact_name') IS NULL
BEGIN
    ALTER TABLE [dbo].[40_VENTES_SOUSTRAITANCE_customers]
        ADD [contact_name] NVARCHAR(200) NULL;
END
GO

IF COL_LENGTH('[dbo].[40_VENTES_SOUSTRAITANCE_customers]', 'global_quote_comment') IS NULL
BEGIN
    ALTER TABLE [dbo].[40_VENTES_SOUSTRAITANCE_customers]
        ADD [global_quote_comment] NVARCHAR(MAX) NULL;
END
GO
