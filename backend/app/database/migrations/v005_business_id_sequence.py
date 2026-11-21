"""Add a data-preserving PostgreSQL sequence default for generated business IDs."""

VERSION = "005_business_id_sequence"

UP = (
    "CREATE SEQUENCE IF NOT EXISTS businesses_business_id_seq AS BIGINT START WITH 1",
    """SELECT setval(
           'businesses_business_id_seq'::regclass,
           GREATEST(COALESCE(MAX(business_id), 1),
                    (SELECT last_value FROM businesses_business_id_seq), 1),
           COUNT(*) > 0 OR (SELECT is_called FROM businesses_business_id_seq)
       ) FROM businesses""",
    "ALTER SEQUENCE businesses_business_id_seq OWNED BY businesses.business_id",
    "ALTER TABLE businesses ALTER COLUMN business_id SET DEFAULT nextval('businesses_business_id_seq'::regclass)",
    """DO $$ DECLARE item RECORD; BEGIN
        FOR item IN SELECT conname FROM pg_constraint
                    WHERE conrelid='loan_applications'::regclass AND contype='c'
                      AND pg_get_constraintdef(oid) ILIKE '%previous_year_revenue%'
        LOOP EXECUTE format('ALTER TABLE loan_applications DROP CONSTRAINT %I', item.conname); END LOOP;
        ALTER TABLE loan_applications ADD CONSTRAINT loan_applications_previous_year_revenue_check
            CHECK (previous_year_revenue >= 0);
    END $$""",
)
