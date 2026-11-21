"""Interactive local utility to provision an RM or Loan Officer account."""

from backend.app.database.connection import DatabaseConnection
from backend.app.database.migrations.v004_company_applicant_identity import VERSION as REQUIRED_SCHEMA_VERSION
from backend.app.repositories.workflow_repository import WorkflowRepository
from backend.app.services.auth_service import DuplicateEmailError
from backend.app.services.workflow_service import WorkflowService
from backend.app.services.validation_service import validate_password


def main() -> int:
    database = DatabaseConnection()
    try:
        if not database.has_migration(REQUIRED_SCHEMA_VERSION):
            print("Database schema is not current. Run python -m backend.app.database.migrate first.")
            return 1
        service = WorkflowService(WorkflowRepository(database))
        print("Staff account provisioning (not available from public applicant registration)")
        print("1. Relationship Manager\n2. Loan Officer")
        choice = input("Select staff role: ").strip()
        role = {"1": "RELATIONSHIP_MANAGER", "2": "LOAN_OFFICER"}.get(choice)
        if role is None:
            print("No account created.")
            return 1
        name = input("Full name: ").strip()
        email = input("Email: ").strip()
        phone = input("Phone number: ").strip()
        while True:
            password = input("Create Password: ")
            try:
                validate_password(password)
            except ValueError as exc:
                print(str(exc))
                continue
            while True:
                confirmation = input("Confirm Password: ")
                if password != confirmation:
                    print("[!] ERROR: Passwords do not match.\nPlease enter the confirmation password again.")
                    continue
                break
            break
        user_id = service.provision_staff(name, email, phone, password, confirmation, role)
        print(f"Staff account created. User ID: {user_id}; role: {role}.")
        return 0
    except DuplicateEmailError as exc:
        print(str(exc))
        return 1
    except (ValueError, KeyboardInterrupt) as exc:
        print(str(exc) or "Provisioning cancelled.")
        return 1
    except Exception:
        print("Staff provisioning failed. Check database availability and configuration.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
