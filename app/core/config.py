from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Backend API connection
    ADMIN_API_BASE_URL: str

    # JWT Authentication
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Session
    SESSION_SECRET_KEY: str

    # Shop Configuration
    SHOP_NAME: str = "My Shop"
    SHOP_DOMAIN: str = "localhost"
    TRADER_ID: int = 1

    # File uploads
    MAX_IMAGE_SIZE_MB: int = 5
    UPLOAD_DIR: str = "static/uploads"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
