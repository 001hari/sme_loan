from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SME Loan Risk API"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://postgres:CHANGE_ME@localhost:5432/sme_loan"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
