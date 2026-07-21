"""
Main Entry Point - AI SMC Multi-Agent Trading System
Orchestrates all components and starts the trading bot
"""

import logging
import sys
import os
import io
from pathlib import Path
from typing import Dict, Any, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Force stdout to UTF-8 so emoji in print() work on Thai Windows terminals
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Configure logging with UTF-8 to support emoji on all terminals
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./logs/trading_bot.log', encoding='utf-8'),
        logging.StreamHandler(stream=open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False))
    ]
)

logger = logging.getLogger(__name__)


class AISmcTradingBot:
    """Main Trading Bot Class"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Trading Bot
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.agents = {}
        self.pipeline = None
        self.market_data = {}
        logger.info("🚀 Initializing AI SMC Trading Bot")
    
    def setup_agents(self):
        """Initialize all trading agents"""
        from agents.trading_agents import (
            LiquidityAgent, CHoCHAgent, FVGAgent, ScoringAgent,
            DecisionAgent, RiskAgent, PortfolioAgent, BacktestAgent, ExecutorAgent
        )
        
        api_key = self.config.get("gemini_api_key", "")
        
        logger.info("📦 Initializing agents...")
        
        self.agents = {
            "liquidity": LiquidityAgent(api_key),
            "choch": CHoCHAgent(api_key),
            "fvg": FVGAgent(api_key),
            "scoring": ScoringAgent(api_key),
            "decision": DecisionAgent(api_key),
            "risk": RiskAgent(api_key, self.config.get("account_size", 10000)),
            "portfolio": PortfolioAgent(api_key),
            "backtest": BacktestAgent(api_key),
            "executor": ExecutorAgent(api_key),
        }
        
        logger.info("✅ All 9 agents initialized successfully")
    
    def setup_pipeline(self):
        """Initialize LangGraph pipeline"""
        from graph.pipeline import TradingPipeline
        
        logger.info("🌐 Setting up LangGraph pipeline...")
        self.pipeline = TradingPipeline(self.agents)
        logger.info("✅ Pipeline ready")
    
    def load_market_data(self, symbol: str, timeframe: str, num_candles: int = 100) -> List[Dict[str, float]]:
        """
        Load market data for testing and analysis
        First attempts to fetch real market data from MetaTrader 5 (MT5).
        If MT5 is disabled, unavailable, or fails, falls back to mock data.
        
        Args:
            symbol: Trading symbol (e.g., 'XAUUSD')
            timeframe: Timeframe (e.g., 'H1', 'M15')
            num_candles: Number of candles to load
        
        Returns:
            List of candle data
        """
        import random
        from datetime import datetime, timedelta
        
        # Try MT5 if enabled
        if self.config.get("use_mt5", True):
            try:
                from data.mt5_connector import MT5Connector
                connector = MT5Connector(
                    login=self.config.get("mt5_login", 0),
                    password=self.config.get("mt5_password", ""),
                    server=self.config.get("mt5_server", ""),
                    path=self.config.get("mt5_path", "")
                )
                mt5_candles = connector.get_candles(symbol, timeframe, num_candles)
                if mt5_candles and len(mt5_candles) > 0:
                    logger.info(f"✅ Loaded {len(mt5_candles)} real MT5 candles for {symbol} {timeframe}")
                    return mt5_candles
                else:
                    logger.warning("⚠️ MT5 data fetch empty/failed. Falling back to mock market data...")
            except Exception as e:
                logger.warning(f"⚠️ MT5 connection notice ({e}). Falling back to mock market data...")

        logger.info(f"📊 Generating mock market data for {symbol} {timeframe}")
        
        candles = []
        base_price = 2050.0  # Mock XAUUSD price
        
        for i in range(num_candles):
            # Generate realistic candle
            open_price = base_price + random.uniform(-5, 5)
            close_price = open_price + random.uniform(-8, 8)
            high = max(open_price, close_price) + random.uniform(0, 3)
            low = min(open_price, close_price) - random.uniform(0, 3)
            volume = random.randint(1000, 5000)
            
            candle = {
                "open": round(open_price, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(close_price, 2),
                "volume": volume,
                "timestamp": (datetime.now() - timedelta(hours=num_candles - i)).isoformat()
            }
            
            candles.append(candle)
            base_price = close_price  # Update base for next candle
        
        logger.info(f"✅ Generated {len(candles)} mock candles")
        return candles
    
    def analyze_market(self, symbol: str = "XAUUSD", timeframe: str = "H1"):
        """
        Analyze market and run trading pipeline
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
        
        Returns:
            Pipeline execution result
        """
        logger.info(f"🔍 Starting market analysis for {symbol} {timeframe}")
        
        # Load market data
        candles = self.load_market_data(symbol, timeframe)
        
        # Prepare input for pipeline
        market_data = {
            "symbol": symbol,
            "timeframe": timeframe,
            "candles": candles
        }
        
        # Run pipeline
        result = self.pipeline.run(market_data)
        
        # Print summary
        summary = self.pipeline.get_summary(result)
        print(summary)
        
        return result
    
    def run(self):
        """Run the trading bot"""
        try:
            logger.info("=" * 60)
            logger.info("🤖 AI SMC TRADING BOT STARTED")
            logger.info("=" * 60)
            
            # Setup
            self.setup_agents()
            self.setup_pipeline()
            
            # Analysis loop (demo - runs once)
            logger.info("\n📈 Running market analysis...\n")
            result = self.analyze_market(symbol="XAUUSD", timeframe="H1")
            
            logger.info("\n" + "=" * 60)
            logger.info("✅ BOT EXECUTION COMPLETE")
            logger.info("=" * 60)
            
            return result
            
        except KeyboardInterrupt:
            logger.info("\n⏹️  Bot interrupted by user")
        except Exception as e:
            logger.error(f"❌ Bot error: {e}", exc_info=True)
            raise


def main():
    """Main entry point"""
    
    # Load configuration from environment
    config = {
        "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
        "qdrant_url": os.getenv("QDRANT_URL", "http://localhost:6333"),
        "qdrant_api_key": os.getenv("QDRANT_API_KEY", ""),
        "symbol": os.getenv("SYMBOL", "XAUUSD"),
        "account_size": float(os.getenv("ACCOUNT_SIZE", "10000")),
        "debug": os.getenv("DEBUG", "False").lower() == "true",
        "use_mt5": os.getenv("USE_MT5", "True").lower() == "true",
        "mt5_login": int(os.getenv("MT5_LOGIN", "0") or "0"),
        "mt5_password": os.getenv("MT5_PASSWORD", ""),
        "mt5_server": os.getenv("MT5_SERVER", ""),
        "mt5_path": os.getenv("MT5_PATH", "")
    }
    
    # Validate API key
    if not config["gemini_api_key"]:
        logger.error("❌ GEMINI_API_KEY not set. Please set it in .env file")
        sys.exit(1)
    
    # Create and run bot
    bot = AISmcTradingBot(config)
    result = bot.run()
    
    return result


if __name__ == "__main__":
    import dotenv
    
    # Load .env file
    dotenv.load_dotenv()
    
    # Ensure logs directory exists
    os.makedirs("./logs", exist_ok=True)
    
    # Run bot
    main()