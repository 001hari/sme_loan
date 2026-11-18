Contributing Guidelines

Thank you for contributing to the SME Loan Default Risk Prediction System.

All team members should follow these guidelines to maintain consistent code and smooth integration.

1. Module Ownership

Each team is responsible for its assigned module.

Team| Responsibility
Frontend| Streamlit UI and API integration
Backend| FastAPI endpoints and business logic
Database| PostgreSQL schema and SQLAlchemy models
ML| Model training, evaluation and inference
Project Lead| Architecture, contracts and integration

2. Development Guidelines

- Work only within your assigned module unless changes are coordinated.
- Follow the existing project structure.
- Use meaningful variable, function and class names.
- Keep code modular and readable.
- Do not hardcode database credentials or secrets.
- Test your changes before submitting them.
- Coordinate changes to shared interfaces with the responsible team.

3. Git Workflow

Create a separate branch for each feature or task.

git checkout -b feature/your-feature-name

After making changes:

git add .
git commit -m "Describe your changes"
git push -u origin feature/your-feature-name

Create a Pull Request on GitHub and request a review before merging into "main".

4. Commit Message Guidelines

Use clear and meaningful commit messages.

Examples:

- "feat: add application submission API"
- "fix: resolve database connection issue"
- "docs: update project setup instructions"
- "refactor: improve API service structure"

5. Database Guidelines

- Coordinate schema changes with the database team.
- Update the SQLAlchemy model when changing a table.
- Apply corresponding SQL changes manually in PostgreSQL.
- Never delete or modify shared database data without approval.
- Do not commit database credentials or real applicant data.

6. API and ML Integration

- Follow the agreed API request and response contracts.
- Coordinate endpoint changes with the frontend team.
- Follow the agreed ML input and output contract.
- Clearly identify mock predictions until the trained model is integrated.

7. Pull Request Guidelines

Before creating a Pull Request:

- Ensure your code runs successfully.
- Test the functionality you changed.
- Check that unrelated files are not modified.
- Provide a short description of your changes.

All changes should be reviewed before merging into the main branch.

---

Note: Coordinate with the project lead before making changes that affect multiple modules or shared interfaces.