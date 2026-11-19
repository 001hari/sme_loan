from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SME Loan Risk API"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://postgres:CHANGE_ME@localhost:5432/sme_loan"

    # JWT Authentication
    jwt_secret_key: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120

    # Default Admin Seeder Credentials
    seed_admin_email: str = "admin@smeloan.com"
    seed_admin_password: str = "Admin@12345"
    seed_admin_name: str = "System Administrator"
    seed_admin_phone: str = "+1234567890"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
