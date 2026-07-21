"""
Configuration Management for AI SMC Multi-Agent Trading System
"""

import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field

# Load environment variables
load_dotenv(override=True)


class GeminiConfig(BaseSettings):
    """Google Gemini API Configuration"""
    api_key: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    model: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))
    timeout: int = Field(default_factory=lambda: int(os.getenv("GEMINI_REQUEST_TIMEOUT", "30")))
    max_retries: int = Field(default_factory=lambda: int(os.getenv("MAX_RETRIES", "3")))
    max_tokens: int = Field(default_factory=lambda: int(os.getenv("GEMINI_MAX_TOKENS", "2048")))
    temperature: float = Field(default_factory=lambda: float(os.getenv("GEMINI_TEMPERATURE", "0.7")))

    class Config:
        env_prefix = "GEMINI_"


class QdrantConfig(BaseSettings):
    """Qdrant Vector Database Configuration"""
    url: str = Field(default_factory=lambda: os.getenv("QDRANT_URL", "http://localhost:6333"))
    api_key: str = Field(default_factory=lambda: os.getenv("QDRANT_API_KEY", ""))
    collection_name: str = Field(default_factory=lambda: os.getenv("QDRANT_COLLECTION", "ai_smc_trading"))
    vector_size: int = 1536  # Claude embeddings

    class Config:
        env_prefix = "QDRANT_"


class MT5Config(BaseSettings):
    """MetaTrader 5 Configuration"""
    use_mt5: bool = Field(default_factory=lambda: os.getenv("USE_MT5", "True").lower() == "true")
    login: int = Field(default_factory=lambda: int(os.getenv("MT5_LOGIN", "0") or "0"))
    password: str = Field(default_factory=lambda: os.getenv("MT5_PASSWORD", ""))
    server: str = Field(default_factory=lambda: os.getenv("MT5_SERVER", ""))
    path: str = Field(default_factory=lambda: os.getenv("MT5_PATH", ""))

    class Config:
        env_prefix = "MT5_"



class TradingConfig(BaseSettings):
    """Trading Configuration"""
    symbol: str = Field(default_factory=lambda: os.getenv("SYMBOL", "XAUUSD"))
    timeframes: list = Field(default_factory=lambda: os.getenv("TIMEFRAMES", "M15,H1,H4,D1").split(","))
    base_currency: str = Field(default_factory=lambda: os.getenv("BASE_CURRENCY", "USD"))
    account_size: float = Field(default_factory=lambda: float(os.getenv("ACCOUNT_SIZE", "10000")))
    
    # Risk Management
    max_position_size: float = Field(default_factory=lambda: float(os.getenv("MAX_POSITION_SIZE", "5000")))
    stop_loss_percent: float = Field(default_factory=lambda: float(os.getenv("STOP_LOSS_PERCENT", "2.0")))
    take_profit_percent: float = Field(default_factory=lambda: float(os.getenv("TAKE_PROFIT_PERCENT", "5.0")))
    risk_reward_ratio: str = Field(default_factory=lambda: os.getenv("RISK_REWARD_RATIO", "1:2"))

    class Config:
        env_prefix = "TRADING_"


class AgentConfig(BaseSettings):
    """Agent Configuration"""
    decision_model: str = Field(default_factory=lambda: os.getenv("DECISION_AGENT_MODEL", "claude-3-5-sonnet-20241022"))
    decision_timeout: int = Field(default_factory=lambda: int(os.getenv("DECISION_TIMEOUT", "30")))
    max_retries: int = Field(default_factory=lambda: int(os.getenv("MAX_RETRIES", "3")))
    xgb_model_path: str = Field(default_factory=lambda: os.getenv("XGB_MODEL_PATH", "./models/xgboost_model.pkl"))
    xgb_threshold: float = Field(default_factory=lambda: float(os.getenv("XGB_THRESHOLD", "0.65")))

    class Config:
        env_prefix = "AGENT_"


class BacktestConfig(BaseSettings):
    """Backtest Configuration"""
    start_date: str = Field(default_factory=lambda: os.getenv("BACKTEST_START_DATE", "2024-01-01"))
    end_date: str = Field(default_factory=lambda: os.getenv("BACKTEST_END_DATE", "2024-12-31"))
    initial_capital: float = Field(default_factory=lambda: float(os.getenv("BACKTEST_INITIAL_CAPITAL", "10000")))

    class Config:
        env_prefix = "BACKTEST_"


class AppConfig(BaseSettings):
    """Application Configuration"""
    debug: bool = Field(default_factory=lambda: os.getenv("DEBUG", "False").lower() == "true")
    verbose: bool = Field(default_factory=lambda: os.getenv("VERBOSE", "True").lower() == "true")
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_dir: str = Field(default_factory=lambda: os.getenv("LOG_DIR", "./logs"))

    class Config:
        env_prefix = "APP_"


# Initialize configuration objects
gemini_config = GeminiConfig()
qdrant_config = QdrantConfig()
mt5_config = MT5Config()
trading_config = TradingConfig()
agent_config = AgentConfig()
backtest_config = BacktestConfig()
app_config = AppConfig()


# Validate API key
if not gemini_config.api_key:
    raise ValueError("❌ GEMINI_API_KEY not found. Please set it in .env file")

print("✅ Configuration loaded successfully (Gemini API)")