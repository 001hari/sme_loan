# Database Contract — first vertical slice

Tables:
- `loan_applications`: one row per submitted application.
- `loan_predictions`: one or more prediction records per application.

The database team should review:
- data types, precision and currency conventions;
- whether applicant/business entities need separate normalized tables;
- unique identifiers and indexes;
- retention and privacy requirements;
- role permissions for application users;
- migration ownership and office DBA approval.

This starter's schema is deliberately minimal for an integration demo. It is not a finalized enterprise schema.
