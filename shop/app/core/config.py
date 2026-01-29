from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database (shared with trader-cms)
    DATABASE_URL: str

    # Backend API
    ADMIN_API_BASE_URL: str

    # JWT for customer auth
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Session
    SESSION_SECRET_KEY: str

    # Shop Configuration (single-tenant)
    TRADER_ID: int
    SHOP_NAME: str = "My Shop"

    class Config:
        env_file = ".env"


settings = Settings()
