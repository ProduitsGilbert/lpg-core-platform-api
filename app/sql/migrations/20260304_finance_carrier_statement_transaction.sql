/*
Creates storage for OCR-extracted carrier statement shipments.
Target DB: Cedule
Table: [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_AP_Transport_Carrier_Statement_Transaction]
*/

IF OBJECT_ID('[Cedule].[dbo].[Finance_Carrier_Statement_Transaction]', 'U') IS NOT NULL
   AND OBJECT_ID('[Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_AP_Transport_Carrier_Statement_Transaction]', 'U') IS NULL
BEGIN
    EXEC sp_rename
        @objname = N'[Cedule].[dbo].[Finance_Carrier_Statement_Transaction]',
        @newname = N'30_COMPTABILITÉ ET FINANCES_AP_Transport_Carrier_Statement_Transaction';
END;

IF OBJECT_ID('[Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_AP_Transport_Carrier_Statement_Transaction]', 'U') IS NULL
BEGIN
    CREATE TABLE [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_AP_Transport_Carrier_Statement_Transaction] (
        id BIGINT IDENTITY(1,1) NOT NULL,
        carrier NVARCHAR(50) NOT NULL,
        workflow_type NVARCHAR(20) NOT NULL CONSTRAINT DF_Finance_CarrierStmt_WorkflowType DEFAULT N'sales',
        status NVARCHAR(50) NOT NULL CONSTRAINT DF_Finance_CarrierStmt_Status DEFAULT N'new',
        matched BIT NOT NULL CONSTRAINT DF_Finance_CarrierStmt_Matched DEFAULT (0),

        statement_filename NVARCHAR(260) NULL,
        account_number NVARCHAR(100) NULL,
        invoice_number NVARCHAR(100) NULL,
        invoice_date DATE NULL,
        due_date DATE NULL,
        currency NVARCHAR(10) NOT NULL CONSTRAINT DF_Finance_CarrierStmt_Currency DEFAULT N'CAD',
        amount_due DECIMAL(18,2) NULL,
        sales_invoice_number NVARCHAR(100) NULL,
        sales_transport_charge_line_amount DECIMAL(18,2) NULL,
        sales_total_amount_incl_vat DECIMAL(18,2) NULL,

        shipment_date DATE NOT NULL,
        tracking_number NVARCHAR(128) NOT NULL,
        shipped_from_address NVARCHAR(MAX) NOT NULL,
        shipped_to_address NVARCHAR(MAX) NOT NULL,
        piece_count INT NULL,
        billed_weight DECIMAL(18,3) NULL,
        billed_weight_unit NVARCHAR(20) NULL,
        service_description NVARCHAR(255) NULL,
        charges_json NVARCHAR(MAX) NULL,
        subtotal_before_tax DECIMAL(18,2) NULL,
        tax_lines_json NVARCHAR(MAX) NULL,
        tax_total DECIMAL(18,2) NULL,
        tax_tps DECIMAL(18,2) NULL,
        tax_tvq DECIMAL(18,2) NULL,
        total_charges DECIMAL(18,2) NOT NULL,
        ref_1 NVARCHAR(255) NULL,
        ref_2 NVARCHAR(255) NULL,
        manifest_number NVARCHAR(255) NULL,
        billing_note NVARCHAR(1000) NULL,
        source_page INT NULL,
        shipment_payload_json NVARCHAR(MAX) NULL,

        created_at DATETIME2 NOT NULL CONSTRAINT DF_Finance_CarrierStmt_CreatedAt DEFAULT SYSUTCDATETIME(),
        updated_at DATETIME2 NOT NULL CONSTRAINT DF_Finance_CarrierStmt_UpdatedAt DEFAULT SYSUTCDATETIME(),

        CONSTRAINT PK_Finance_Carrier_Statement_Transaction PRIMARY KEY CLUSTERED (id),
        CONSTRAINT CK_Finance_CarrierStmt_WorkflowType CHECK (workflow_type IN (N'purchase', N'sales'))
    );
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'UX_Finance_CarrierStmt_CarrierInvoiceShipment'
      AND object_id = OBJECT_ID('[Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_AP_Transport_Carrier_Statement_Transaction]')
)
BEGIN
    CREATE UNIQUE NONCLUSTERED INDEX UX_Finance_CarrierStmt_CarrierInvoiceShipment
        ON [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_AP_Transport_Carrier_Statement_Transaction] (
            carrier,
            invoice_number,
            shipment_date,
            tracking_number
        );
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_Finance_CarrierStmt_UnmatchedQueue'
      AND object_id = OBJECT_ID('[Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_AP_Transport_Carrier_Statement_Transaction]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_Finance_CarrierStmt_UnmatchedQueue
        ON [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_AP_Transport_Carrier_Statement_Transaction] (
            carrier,
            matched,
            status,
            workflow_type,
            shipment_date DESC
        );
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_Finance_CarrierStmt_UpdatedAt'
      AND object_id = OBJECT_ID('[Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_AP_Transport_Carrier_Statement_Transaction]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_Finance_CarrierStmt_UpdatedAt
        ON [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_AP_Transport_Carrier_Statement_Transaction] (updated_at DESC);
END;
