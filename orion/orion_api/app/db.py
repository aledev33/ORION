from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    MARIADB_USER: str
    MARIADB_PASSWORD: str
    MARIADB_HOST: str = "127.0.0.1"
    MARIADB_PORT: int = 3306
    MARIADB_DB: str

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.MARIADB_USER}:{self.MARIADB_PASSWORD}"
            f"@{self.MARIADB_HOST}:{self.MARIADB_PORT}/{self.MARIADB_DB}"
        )


settings = Settings()


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()