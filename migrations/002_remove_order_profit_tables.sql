USE RevenueSystemDB;
GO

IF OBJECT_ID('dbo.order_fee_status', 'U') IS NOT NULL
    DROP TABLE dbo.order_fee_status;
GO

IF OBJECT_ID('dbo.order_costs', 'U') IS NOT NULL
    DROP TABLE dbo.order_costs;
GO
