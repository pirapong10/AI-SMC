"""
Phase 3: Paper Trading with Live MT5 Data
Executes Phase 1 SMC strategy on real-time XAUUSD data
"""

import logging
import time
from datetime import datetime
from typing import List, Dict, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import components
from mt5_connector import MT5Connector, MTCandle
from paper_trading_engine import PaperTradingEngine
from smc_logic import SMCAnalyzer, SMCSignal


class Phase3PaperTradingBot:
    """
    Phase 3 Paper Trading Bot
    
    - Connects to live MT5 terminal
    - Streams real-time XAUUSD H1 data
    - Executes Phase 1 SMC strategy
    - Simulates order execution with real spreads
    - Tracks live P&L
    - Sends alerts on trades
    """
    
    def __init__(self,
                 symbol: str = "XAUUSD",
                 initial_capital: float = 10000,
                 risk_per_trade: float = 2.0):
        """
        Initialize paper trading bot
        
        Args:
            symbol: Trading symbol
            initial_capital: Starting capital
            risk_per_trade: Risk per trade (%)
        """
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        
        # Components
        self.mt5 = MT5Connector(symbol=symbol)
        self.engine = PaperTradingEngine(
            initial_capital=initial_capital,
            risk_per_trade=risk_per_trade
        )
        self.smc = SMCAnalyzer()
        
        # State
        self.is_running = False
        self.last_h1_candle = None
        self.h1_candles: List[MTCandle] = []
        self.h4_candles: List[MTCandle] = []
        
        logger.info("🤖 Phase 3 Paper Trading Bot initialized")
        logger.info(f"   Symbol: {symbol}")
        logger.info(f"   Capital: ${initial_capital:.2f}")
        logger.info(f"   Risk/trade: {risk_per_trade}%")
    
    def startup(self) -> bool:
        """
        Startup bot and connect to MT5
        
        Returns:
            True if startup successful
        """
        logger.info("\n" + "="*60)
        logger.info("🚀 PHASE 3: PAPER TRADING STARTUP")
        logger.info("="*60 + "\n")
        
        # Connect to MT5
        logger.info("📡 Connecting to MT5...")
        if not self.mt5.connect():
            logger.error("❌ Failed to connect to MT5")
            return False
        
        logger.info("✅ Connected to MT5\n")
        
        # Get initial candles
        logger.info("📊 Loading initial candles...")
        self.h1_candles = self.mt5.get_candles(timeframe="H1", bars=50)
        self.h4_candles = self.mt5.get_candles(timeframe="H4", bars=20)
        
        if not self.h1_candles:
            logger.error("❌ Failed to load initial candles")
            return False
        
        logger.info(f"✅ Loaded {len(self.h1_candles)} H1 candles")
        logger.info(f"✅ Loaded {len(self.h4_candles)} H4 candles\n")
        
        self.is_running = True
        logger.info("✅ Bot startup complete!\n")
        return True
    
    def run_iteration(self) -> bool:
        """
        Run one trading iteration
        
        Returns:
            True if successful
        """
        try:
            # Get current price
            prices = self.mt5.get_current_price()
            if not prices:
                logger.warning("⚠️ Could not get current price")
                return False
            
            bid, ask = prices
            timestamp = datetime.now().isoformat()
            
            # Get latest candles
            latest_h1 = self.mt5.get_candles(timeframe="H1", bars=50)
            if not latest_h1:
                logger.warning("⚠️ Could not get H1 candles")
                return False
            
            # Check if we have a new candle
            if len(latest_h1) > len(self.h1_candles):
                new_candles = len(latest_h1) - len(self.h1_candles)
                logger.info(f"📊 New candles: {new_candles}")
                self.h1_candles = latest_h1
            else:
                self.h1_candles = latest_h1
            
            # Update H4 candles periodically
            if len(self.h1_candles) % 4 == 0:
                self.h4_candles = self.mt5.get_candles(timeframe="H4", bars=20)
            
            # Analyze signals
            if len(self.h1_candles) >= 20:
                signal_analysis = self._analyze_signals()
                
                # Check exit conditions
                self._check_exits(timestamp, bid, ask)
                
                # Check entry conditions
                if signal_analysis and signal_analysis["signal"] != SMCSignal.NO_SIGNAL:
                    self._check_entries(
                        timestamp=timestamp,
                        bid=bid,
                        ask=ask,
                        analysis=signal_analysis
                    )
            
            # Record equity
            self.engine.record_equity(timestamp)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Iteration error: {e}")
            return False
    
    def _analyze_signals(self) -> Optional[Dict]:
        """Analyze SMC signals from current candles"""
        if not self.h1_candles or len(self.h1_candles) < 20:
            return None
        
        # Convert to dict format
        candle_dicts = [
            {
                "timestamp": c.timestamp,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume
            }
            for c in self.h1_candles[-20:]
        ]
        
        # Run SMC analysis
        analysis = self.smc.analyze(candle_dicts)
        
        # Diagnostic logging — show what was detected
        liq = analysis.get('liquidity_sweep')
        choch = analysis.get('choch')
        fvg = analysis.get('fvg')
        sig = analysis.get('signal')
        conf = analysis.get('confidence', 0)
        logger.info(f"   SMC: Liquidity={'✅'+liq[1] if liq else '❌None'} | "
                    f"CHoCH={'✅'+choch[1] if choch else '❌None'} | "
                    f"FVG={'✅'+fvg[2] if fvg else '❌None'} | "
                    f"Signal={sig.name} conf={conf:.1f}")
        
        return analysis
    
    def _check_exits(self, timestamp: str, bid: float, ask: float):
        """Check and execute exit conditions"""
        if self.engine.open_position:
            self.engine.check_exit_conditions(timestamp, bid, ask)
    
    def _check_entries(self, timestamp: str, bid: float, ask: float, analysis: Dict):
        """Check and execute entry conditions"""
        if self.engine.open_position:
            return  # Already in trade
        
        signal = analysis.get("signal", SMCSignal.NO_SIGNAL)
        confidence = analysis.get("confidence", 0)
        entry_level = analysis.get("entry_level", ask if signal == SMCSignal.BULLISH else bid)
        
        # Only take signals with minimum confidence (CHoCH alone = 0.3, Liquidity+CHoCH = 0.6)
        if signal == SMCSignal.NO_SIGNAL or confidence < 0.30:
            logger.info(f"   ⏭️  Skip: signal={signal.name} conf={confidence:.1f} (min 0.30)")
            return
        
        # Calculate stops
        atr = self._calculate_atr(self.h1_candles[-20:])
        
        if signal == SMCSignal.BULLISH:
            stop_loss = entry_level - (atr * 1.5)
            take_profit = entry_level + (atr * 3.0)
        else:  # BEARISH
            stop_loss = entry_level + (atr * 1.5)
            take_profit = entry_level - (atr * 3.0)
        
        # Calculate position size
        position_size = self.engine.calculate_position_size(entry_level, stop_loss)
        
        if position_size > 0:
            direction = "LONG" if signal == SMCSignal.BULLISH else "SHORT"
            self.engine.place_trade(
                timestamp=timestamp,
                bid=bid,
                ask=ask,
                direction=direction,
                position_size=position_size,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
    
    @staticmethod
    def _calculate_atr(candles: List[MTCandle], period: int = 14) -> float:
        """Calculate Average True Range"""
        if len(candles) < period:
            return 0
        
        true_ranges = []
        for i in range(1, len(candles)):
            high = candles[i].high
            low = candles[i].low
            close_prev = candles[i-1].close
            
            tr = max(
                high - low,
                abs(high - close_prev),
                abs(low - close_prev)
            )
            true_ranges.append(tr)
        
        atr = sum(true_ranges[-period:]) / period
        return atr
    
    def run_loop(self, max_iterations: Optional[int] = None, sleep_seconds: int = 60):
        """
        Run continuous trading loop
        
        Args:
            max_iterations: Max iterations (None = infinite)
            sleep_seconds: Sleep between iterations
        """
        if not self.startup():
            logger.error("❌ Failed to startup")
            return
        
        iteration = 0
        
        try:
            while self.is_running:
                iteration += 1
                
                if max_iterations and iteration > max_iterations:
                    logger.info(f"✅ Reached max iterations: {max_iterations}")
                    break
                
                logger.info(f"\n--- Iteration {iteration} ---")
                
                if not self.run_iteration():
                    logger.warning("⚠️ Iteration failed")
                
                # Log current state
                metrics = self.engine.get_metrics()
                logger.info(f"📊 Trades: {metrics['total_trades']} | "
                          f"P&L: ${metrics['total_pnl']:.2f} | "
                          f"Capital: ${self.engine.current_capital:.2f}")
                
                # Sleep before next iteration
                logger.info(f"💤 Sleeping {sleep_seconds}s...\n")
                time.sleep(sleep_seconds)
                
        except KeyboardInterrupt:
            logger.info("\n🛑 Interrupted by user")
        
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Shutdown bot"""
        logger.info("\n" + "="*60)
        logger.info("🛑 PHASE 3: PAPER TRADING SHUTDOWN")
        logger.info("="*60 + "\n")
        
        # Close any open positions
        if self.engine.open_position:
            prices = self.mt5.get_current_price()
            if prices:
                bid, ask = prices
                self.engine.close_trade(
                    datetime.now().isoformat(),
                    (bid + ask) / 2,
                    "SHUTDOWN"
                )
        
        # Save journal
        self.engine.save_journal("paper_trading_journal_phase3.json")
        
        # Print summary
        self.engine.print_summary()
        
        # Disconnect
        self.mt5.disconnect()
        
        self.is_running = False
        logger.info("✅ Shutdown complete")


def main():
    """Main entry point"""
    
    # Initialize bot
    bot = Phase3PaperTradingBot(
        symbol="XAUUSD",
        initial_capital=10000,
        risk_per_trade=2.0
    )
    
    # Run trading loop
    # sleep_seconds=300 (5 min) matches H1 candle pace
    # For quick test use sleep_seconds=30, max_iterations=10
    bot.run_loop(max_iterations=10, sleep_seconds=300)


if __name__ == "__main__":
    main()
