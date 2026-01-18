from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    ADMIN_API_BASE_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    SESSION_SECRET_KEY: str
    MAX_IMAGE_SIZE_MB: int = 5
    UPLOAD_DIR: str = "static/uploads"

    class Config:
        env_file = ".env"


settings = Settings()
