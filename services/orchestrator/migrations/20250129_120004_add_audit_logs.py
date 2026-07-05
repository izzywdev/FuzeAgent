"""
Migration: Add Audit Logging
Created: 2025-01-29T12:00:04
Description: Adds audit logging capabilities for tracking changes to organizations, teams, and agents
"""


async def upgrade(conn):
    """Apply the migration"""

    # Create audit log table
    await conn.execute(
        """
        CREATE TABLE audit_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            table_name VARCHAR(50) NOT NULL,
            record_id UUID NOT NULL,
            action VARCHAR(20) NOT NULL, -- INSERT, UPDATE, DELETE
            old_values JSONB,
            new_values JSONB,
            changed_by VARCHAR(255),
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address INET,
            user_agent TEXT
        );
    """
    )

    # Create index for efficient querying
    await conn.execute(
        "CREATE INDEX idx_audit_logs_table_record ON audit_logs(table_name, record_id);"
    )
    await conn.execute(
        "CREATE INDEX idx_audit_logs_changed_at ON audit_logs(changed_at);"
    )
    await conn.execute("CREATE INDEX idx_audit_logs_action ON audit_logs(action);")

    # Create audit trigger function
    await conn.execute(
        """
        CREATE OR REPLACE FUNCTION audit_trigger_function()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                INSERT INTO audit_logs (table_name, record_id, action, old_values)
                VALUES (TG_TABLE_NAME, OLD.id, 'DELETE', row_to_json(OLD));
                RETURN OLD;
            ELSIF TG_OP = 'UPDATE' THEN
                INSERT INTO audit_logs (table_name, record_id, action, old_values, new_values)
                VALUES (TG_TABLE_NAME, NEW.id, 'UPDATE', row_to_json(OLD), row_to_json(NEW));
                RETURN NEW;
            ELSIF TG_OP = 'INSERT' THEN
                INSERT INTO audit_logs (table_name, record_id, action, new_values)
                VALUES (TG_TABLE_NAME, NEW.id, 'INSERT', row_to_json(NEW));
                RETURN NEW;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    # Add audit triggers to key tables
    tables_to_audit = ["organizations", "teams", "agents"]

    for table in tables_to_audit:
        await conn.execute(
            f"""
            CREATE TRIGGER audit_trigger_{table}
            AFTER INSERT OR UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();
        """
        )

    print("✅ Created audit logging system with triggers")


async def downgrade(conn):
    """Rollback the migration"""

    # Drop triggers
    tables_to_audit = ["organizations", "teams", "agents"]
    for table in tables_to_audit:
        await conn.execute(f"DROP TRIGGER IF EXISTS audit_trigger_{table} ON {table};")

    # Drop function
    await conn.execute("DROP FUNCTION IF EXISTS audit_trigger_function();")

    # Drop audit logs table
    await conn.execute("DROP TABLE IF EXISTS audit_logs CASCADE;")

    print("✅ Removed audit logging system")
