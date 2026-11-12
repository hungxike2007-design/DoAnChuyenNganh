USE RevenueSystemDB;
GO

IF OBJECT_ID('dbo.audit_logs', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.audit_logs (
        id INT IDENTITY(1,1) PRIMARY KEY,
        user_id INT NULL,
        user_email NVARCHAR(150) NOT NULL DEFAULT '',
        user_role NVARCHAR(50) NOT NULL DEFAULT '',
        action NVARCHAR(50) NOT NULL,
        target_table NVARCHAR(50) NOT NULL,
        target_id NVARCHAR(100) NOT NULL DEFAULT '',
        old_value NVARCHAR(MAX) NOT NULL DEFAULT '',
        new_value NVARCHAR(MAX) NOT NULL DEFAULT '',
        ip_address NVARCHAR(50) NOT NULL DEFAULT '',
        user_agent NVARCHAR(500) NOT NULL DEFAULT '',
        created_at DATETIME2 NOT NULL DEFAULT GETDATE()
    );
END;
GO

IF COL_LENGTH('dbo.audit_logs', 'user_agent') IS NULL
    ALTER TABLE dbo.audit_logs ADD user_agent NVARCHAR(500) NOT NULL DEFAULT '';
GO

CREATE OR ALTER TRIGGER dbo.TR_audit_users_role_update
ON dbo.users
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    IF ISNULL(APP_NAME(), N'') = N'RevenueSystemAPI' RETURN;
    INSERT INTO dbo.audit_logs (user_email, user_role, action, target_table, target_id, old_value, new_value, ip_address)
    SELECT LEFT(SUSER_SNAME(), 150), N'database', N'CHANGE_ROLE', N'users', CONVERT(NVARCHAR(100), i.id),
           CONCAT(N'{"role":"', d.role, N'"}'), CONCAT(N'{"role":"', i.role, N'"}'),
           CONVERT(NVARCHAR(50), CONNECTIONPROPERTY('client_net_address'))
    FROM inserted i JOIN deleted d ON d.id = i.id
    WHERE ISNULL(d.role, N'') <> ISNULL(i.role, N'');
END;
GO
