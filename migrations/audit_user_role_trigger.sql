USE RevenueSystemDB;
GO

CREATE OR ALTER TRIGGER dbo.TR_audit_users_role_update
ON dbo.users
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;

    -- API role updates are already logged with the signed-in user's identity.
    IF ISNULL(APP_NAME(), N'') = N'RevenueSystemAPI' RETURN;

    INSERT INTO dbo.audit_logs (
        user_id, user_email, user_role, action, target_table, target_id,
        old_value, new_value, ip_address
    )
    SELECT NULL, LEFT(SUSER_SNAME(), 150), N'database', N'CHANGE_ROLE', N'users',
           CONVERT(NVARCHAR(100), i.id),
           CONCAT(N'{"role":"', d.role, N'"}'),
           CONCAT(N'{"role":"', i.role, N'"}'),
           CONVERT(NVARCHAR(50), CONNECTIONPROPERTY('client_net_address'))
    FROM inserted i
    JOIN deleted d ON d.id = i.id
    WHERE ISNULL(d.role, N'') <> ISNULL(i.role, N'');
END;
GO
