from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "UrbanSync AI"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql://urbansync:urbansync_dev_password@localhost:5432/urbansync"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # ML
    ML_MODELS_PATH: str = "./ml_pipeline/artifacts"
    GNN_MODEL_VERSION: str = "gnn-v1.0"
    LSTM_MODEL_VERSION: str = "lstm-v1.0"
    XGB_MODEL_VERSION: str = "xgb-v1.0"

    # Simulation
    DEFAULT_MONTE_CARLO_RUNS: int = 100
    MAX_MONTE_CARLO_RUNS: int = 500

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 5  # seconds

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
