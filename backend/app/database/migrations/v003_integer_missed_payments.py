"""Align missed_payments_12m to the specified INTEGER type."""

VERSION = "003_integer_missed_payments"

UP = (
    "ALTER TABLE loan_applications ALTER COLUMN missed_payments_12m TYPE INTEGER USING missed_payments_12m::INTEGER",
)

DOWN = (
    """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM loan_applications WHERE missed_payments_12m < -32768 OR missed_payments_12m > 32767) THEN
            RAISE EXCEPTION 'missed_payments_12m values cannot be represented by SMALLINT';
        END IF;
    END $$""",
    "ALTER TABLE loan_applications ALTER COLUMN missed_payments_12m TYPE SMALLINT USING missed_payments_12m::SMALLINT",
)
