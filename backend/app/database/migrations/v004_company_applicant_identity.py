"""Add a dedicated company identity for SME applicant accounts."""

VERSION = "004_company_applicant_identity"

UP = (
    "ALTER TABLE users ADD COLUMN company_name VARCHAR(200)",
    "ALTER TABLE users ALTER COLUMN email DROP NOT NULL",
    "ALTER TABLE users ALTER COLUMN phone_number DROP NOT NULL",
    "ALTER TABLE users ADD CONSTRAINT users_company_name_role_check CHECK (company_name IS NULL OR role='SME_APPLICANT')",
    "CREATE UNIQUE INDEX users_company_name_ci_key ON users (lower(btrim(company_name))) WHERE company_name IS NOT NULL",
)

# Rollback is allowed only while no company identity has been stored and all
# legacy contact fields remain populated; it never fabricates or discards data.
DOWN = (
    """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM users WHERE company_name IS NOT NULL OR email IS NULL OR phone_number IS NULL) THEN
            RAISE EXCEPTION 'Cannot roll back company identity while company-only account data exists';
        END IF;
    END $$""",
    "DROP INDEX users_company_name_ci_key",
    "ALTER TABLE users DROP CONSTRAINT users_company_name_role_check",
    "ALTER TABLE users DROP COLUMN company_name",
    "ALTER TABLE users ALTER COLUMN email SET NOT NULL",
    "ALTER TABLE users ALTER COLUMN phone_number SET NOT NULL",
)
