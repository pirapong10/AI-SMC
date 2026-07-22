"""
MetaTrader5 Connector - Real-time Data Feed
Connects to MT5 terminal and provides XAUUSD H1/H4 data
"""

import MetaTrader5 as mt5
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
import pandas as pd
import pytz

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MTCandle:
    """MT5 Candle data"""
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume
        }


class MT5Connector:
    """
    MetaTrader5 Connector
    
    Provides real-time data feed from MT5 terminal
    Supports XAUUSD and other symbols
    """
    
    def __init__(self, symbol: str = "XAUUSD"):
        """
        Initialize MT5 connector
        
        Args:
            symbol: Trading symbol (e.g., "XAUUSD")
        """
        self.symbol = symbol
        self.connected = False
        self.timezone = pytz.timezone("UTC")
        
        logger.info(f"🔌 Initializing MT5 Connector for {symbol}")
    
    def connect(self) -> bool:
        """
        Connect to MT5 terminal
        
        Returns:
            True if connected successfully
        """
        try:
            # Initialize MT5
            if not mt5.initialize():
                logger.error(f"❌ MT5 initialization failed: {mt5.last_error()}")
                return False
            
            logger.info("✅ MT5 initialized")
            
            # Get account info
            account_info = mt5.account_info()
            if account_info is None:
                logger.error("❌ Failed to get account info")
                return False
            
            logger.info(f"📊 Account: {account_info.name}")
            logger.info(f"   Company: {account_info.company}")
            logger.info(f"   Balance: ${account_info.balance:.2f}")
            logger.info(f"   Equity: ${account_info.equity:.2f}")
            
            # Check symbol
            symbol_info = mt5.symbol_info(self.symbol)
            if symbol_info is None:
                logger.error(f"❌ Symbol {self.symbol} not found")
                return False
            
            # Enable symbol for quotes
            if not symbol_info.visible:
                if not mt5.symbol_select(self.symbol, True):
                    logger.warning(f"⚠️ Could not enable {self.symbol} for quotes")
            
            logger.info(f"✅ Symbol {self.symbol} ready")
            logger.info(f"   Bid: {symbol_info.bid}")
            logger.info(f"   Ask: {symbol_info.ask}")
            logger.info(f"   Spread: {(symbol_info.ask - symbol_info.bid):.4f}")
            
            self.connected = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MT5"""
        try:
            mt5.shutdown()
            self.connected = False
            logger.info("✅ MT5 disconnected")
        except Exception as e:
            logger.warning(f"⚠️ Disconnect warning: {e}")
    
    def get_candles(self, timeframe: str = "H1", bars: int = 100) -> List[MTCandle]:
        """
        Get historical candles
        
        Args:
            timeframe: "M15", "H1", "H4", "D1"
            bars: Number of bars to fetch
        
        Returns:
            List of MTCandle objects
        """
        if not self.connected:
            logger.error("❌ Not connected to MT5")
            return []
        
        try:
            # Map timeframe string to MT5 constant
            timeframe_map = {
                "M15": mt5.TIMEFRAME_M15,
                "H1": mt5.TIMEFRAME_H1,
                "H4": mt5.TIMEFRAME_H4,
                "D1": mt5.TIMEFRAME_D1
            }
            
            if timeframe not in timeframe_map:
                logger.error(f"❌ Unknown timeframe: {timeframe}")
                return []
            
            tf = timeframe_map[timeframe]
            
            # Fetch candles
            rates = mt5.copy_rates_from_pos(self.symbol, tf, 0, bars)
            
            if rates is None or len(rates) == 0:
                logger.warning(f"⚠️ No data for {self.symbol} {timeframe}")
                return []
            
            # Convert to MTCandle objects
            candles = []
            for rate in rates:
                dt = datetime.fromtimestamp(rate['time'], tz=self.timezone)
                timestamp = dt.strftime("%Y-%m-%dT%H:%M:%S")
                
                candle = MTCandle(
                    timestamp=timestamp,
                    open=float(rate['open']),
                    high=float(rate['high']),
                    low=float(rate['low']),
                    close=float(rate['close']),
                    volume=int(rate['tick_volume'])
                )
                candles.append(candle)
            
            logger.info(f"📊 Fetched {len(candles)} {timeframe} candles")
            return candles
            
        except Exception as e:
            logger.error(f"❌ Error fetching candles: {e}")
            return []
    
    def get_recent_candles(self, timeframe: str = "H1", hours: int = 24) -> List[MTCandle]:
        """
        Get candles from recent time period
        
        Args:
            timeframe: "M15", "H1", "H4", "D1"
            hours: Hours to look back
        
        Returns:
            List of MTCandle objects
        """
        if not self.connected:
            logger.error("❌ Not connected to MT5")
            return []
        
        try:
            timeframe_map = {
                "M15": mt5.TIMEFRAME_M15,
                "H1": mt5.TIMEFRAME_H1,
                "H4": mt5.TIMEFRAME_H4,
                "D1": mt5.TIMEFRAME_D1
            }
            
            if timeframe not in timeframe_map:
                logger.error(f"❌ Unknown timeframe: {timeframe}")
                return []
            
            tf = timeframe_map[timeframe]
            
            # Calculate lookback
            utc_now = datetime.now(tz=self.timezone)
            lookback_time = utc_now - timedelta(hours=hours)
            
            # Fetch candles from time
            rates = mt5.copy_rates_range(
                self.symbol, tf,
                lookback_time, utc_now
            )
            
            if rates is None or len(rates) == 0:
                logger.warning(f"⚠️ No data for {self.symbol} {timeframe} (last {hours}h)")
                return []
            
            # Convert to MTCandle objects
            candles = []
            for rate in rates:
                dt = datetime.fromtimestamp(rate['time'], tz=self.timezone)
                timestamp = dt.strftime("%Y-%m-%dT%H:%M:%S")
                
                candle = MTCandle(
                    timestamp=timestamp,
                    open=float(rate['open']),
                    high=float(rate['high']),
                    low=float(rate['low']),
                    close=float(rate['close']),
                    volume=int(rate['tick_volume'])
                )
                candles.append(candle)
            
            logger.info(f"📊 Fetched {len(candles)} {timeframe} candles (last {hours}h)")
            return candles
            
        except Exception as e:
            logger.error(f"❌ Error fetching recent candles: {e}")
            return []
    
    def get_ticks(self, count: int = 100) -> List[Dict]:
        """
        Get recent ticks
        
        Args:
            count: Number of ticks
        
        Returns:
            List of tick data
        """
        if not self.connected:
            logger.error("❌ Not connected to MT5")
            return []
        
        try:
            ticks = mt5.copy_ticks_from_pos(self.symbol, 0, count, mt5.COPY_TICKS_ALL)
            
            if ticks is None or len(ticks) == 0:
                logger.warning(f"⚠️ No ticks for {self.symbol}")
                return []
            
            result = []
            for tick in ticks:
                dt = datetime.fromtimestamp(tick['time'], tz=self.timezone)
                result.append({
                    "time": dt.strftime("%Y-%m-%dT%H:%M:%S"),
                    "bid": float(tick['bid']),
                    "ask": float(tick['ask']),
                    "volume": int(tick['volume'])
                })
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error fetching ticks: {e}")
            return []
    
    def get_current_price(self) -> Optional[Tuple[float, float]]:
        """
        Get current bid/ask prices
        
        Returns:
            Tuple of (bid, ask) or None if error
        """
        if not self.connected:
            logger.error("❌ Not connected to MT5")
            return None
        
        try:
            tick = mt5.symbol_info_tick(self.symbol)
            if tick is None:
                logger.warning(f"⚠️ Could not get tick for {self.symbol}")
                return None
            
            return (float(tick.bid), float(tick.ask))
            
        except Exception as e:
            logger.error(f"❌ Error getting current price: {e}")
            return None
    
    def get_spread(self) -> Optional[float]:
        """
        Get current spread in points
        
        Returns:
            Spread in points or None
        """
        prices = self.get_current_price()
        if prices is None:
            return None
        
        bid, ask = prices
        return ask - bid
    
    def resample_to_m15(self, h1_candles: List[MTCandle]) -> List[MTCandle]:
        """
        Resample H1 candles to M15
        
        Args:
            h1_candles: List of H1 candles
        
        Returns:
            List of M15 candles (placeholder - uses H1 data)
        """
        # For real M15, fetch from MT5
        # This is just a helper for quick testing
        return h1_candles
    
    def resample_to_h4(self, h1_candles: List[MTCandle]) -> List[MTCandle]:
        """
        Resample H1 candles to H4
        
        Args:
            h1_candles: List of H1 candles
        
        Returns:
            List of H4 candles
        """
        h4_candles = []
        
        i = 0
        while i + 3 < len(h1_candles):
            group = h1_candles[i:i+4]
            
            h4_candle = MTCandle(
                timestamp=group[3].timestamp,
                open=group[0].open,
                high=max(c.high for c in group),
                low=min(c.low for c in group),
                close=group[3].close,
                volume=sum(c.volume for c in group)
            )
            h4_candles.append(h4_candle)
            i += 4
        
        return h4_candles


def test_mt5_connection():
    """Test MT5 connection and data fetch"""
    
    print("\n" + "="*60)
    print("🔌 MT5 CONNECTION TEST")
    print("="*60 + "\n")
    
    connector = MT5Connector(symbol="XAUUSD")
    
    # Connect
    if not connector.connect():
        print("❌ Connection failed!")
        return
    
    # Get current price
    prices = connector.get_current_price()
    if prices:
        bid, ask = prices
        spread = connector.get_spread()
        print(f"💰 Current Prices:")
        print(f"   Bid: {bid:.2f}")
        print(f"   Ask: {ask:.2f}")
        print(f"   Spread: {spread:.4f}\n")
    
    # Fetch H1 candles
    h1_candles = connector.get_candles(timeframe="H1", bars=20)
    if h1_candles:
        print(f"📊 Recent H1 Candles:")
        for i, candle in enumerate(h1_candles[-5:]):
            print(f"   {candle.timestamp}: O:{candle.open:.2f} H:{candle.high:.2f} L:{candle.low:.2f} C:{candle.close:.2f}")
    
    # Fetch H4 candles
    h4_candles = connector.get_candles(timeframe="H4", bars=20)
    if h4_candles:
        print(f"\n📊 Recent H4 Candles:")
        for i, candle in enumerate(h4_candles[-3:]):
            print(f"   {candle.timestamp}: O:{candle.open:.2f} H:{candle.high:.2f} L:{candle.low:.2f} C:{candle.close:.2f}")
    
    # Disconnect
    connector.disconnect()
    
    print("\n✅ MT5 Connection test complete!")


if __name__ == "__main__":
    test_mt5_connection()
