-- Create Finance_Cashflow table in Cedule database
USE [Cedule];
GO

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Finance_Cashflow]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[Finance_Cashflow](
        [id] [int] IDENTITY(1,1) NOT NULL,
        [description] [nvarchar](255) NOT NULL,
        [amount] [decimal](18, 2) NOT NULL,
        [currency_code] [nvarchar](10) NOT NULL, -- 'CAD', 'USD', 'EUR'
        [transaction_type] [nvarchar](20) NOT NULL, -- 'Deposit', 'Payment'
        
        -- For one-time entries
        [transaction_date] [date] NULL,
        
        -- For periodic entries
        [is_periodic] [bit] NOT NULL DEFAULT 0,
        [recurrence_frequency] [nvarchar](20) NULL, -- 'Weekly', 'Monthly', 'Yearly'
        [recurrence_interval] [int] NULL, -- e.g., 2 for "every 2 weeks"
        [recurrence_count] [int] NULL, -- Total number of occurrences (optional, null for infinite?) -> Let's say null is infinite or handled by logic
        [recurrence_end_date] [date] NULL, -- Alternative to count, end date for recurrence

        [created_at] [datetime] NOT NULL DEFAULT GETUTCDATE(),
        [updated_at] [datetime] NOT NULL DEFAULT GETUTCDATE(),
        
        CONSTRAINT [PK_Finance_Cashflow] PRIMARY KEY CLUSTERED 
        (
            [id] ASC
        )
    );
    
    -- Add indexes for performance
    CREATE NONCLUSTERED INDEX [IX_Finance_Cashflow_Date] ON [dbo].[Finance_Cashflow]
    (
        [transaction_date] ASC
    );
    
    CREATE NONCLUSTERED INDEX [IX_Finance_Cashflow_Periodic] ON [dbo].[Finance_Cashflow]
    (
        [is_periodic] ASC
    );
END
GO







