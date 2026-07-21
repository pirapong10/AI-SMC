"""
MetaTrader 5 (MT5) Market Data Connector
Provides live and historical candle data from MetaTrader 5 terminal
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Try importing MetaTrader5 SDK
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False


class MT5Connector:
    """MetaTrader 5 Data Connector"""
    
    def __init__(self, login: int = 0, password: str = "", server: str = "", path: str = ""):
        """
        Initialize MT5 Connector configuration
        
        Args:
            login: MT5 account login number
            password: MT5 account password
            server: MT5 broker server name
            path: Path to terminal64.exe (optional)
        """
        self.login = login
        self.password = password
        self.server = server
        self.path = path
        self.connected = False
        
        if not MT5_AVAILABLE:
            logger.warning("⚠️ MetaTrader5 Python package is not available")
            return
            
        self.timeframe_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M2": mt5.TIMEFRAME_M2,
            "M3": mt5.TIMEFRAME_M3,
            "M4": mt5.TIMEFRAME_M4,
            "M5": mt5.TIMEFRAME_M5,
            "M6": mt5.TIMEFRAME_M6,
            "M10": mt5.TIMEFRAME_M10,
            "M12": mt5.TIMEFRAME_M12,
            "M15": mt5.TIMEFRAME_M15,
            "M20": mt5.TIMEFRAME_M20,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H2": mt5.TIMEFRAME_H2,
            "H3": mt5.TIMEFRAME_H3,
            "H4": mt5.TIMEFRAME_H4,
            "H6": mt5.TIMEFRAME_H6,
            "H8": mt5.TIMEFRAME_H8,
            "H12": mt5.TIMEFRAME_H12,
            "D1": mt5.TIMEFRAME_D1,
            "W1": mt5.TIMEFRAME_W1,
            "MN1": mt5.TIMEFRAME_MN1,
        }
    
    def connect(self) -> bool:
        """
        Connect to MetaTrader 5 terminal
        
        Returns:
            True if connection successful, False otherwise
        """
        if not MT5_AVAILABLE:
            logger.warning("⚠️ Cannot connect: MetaTrader5 module not installed")
            return False
            
        init_kwargs = {}
        if self.path:
            init_kwargs["path"] = self.path
            
        if self.login and self.password and self.server:
            init_kwargs["login"] = self.login
            init_kwargs["password"] = self.password
            init_kwargs["server"] = self.server

        # Attempt connection
        if not mt5.initialize(**init_kwargs):
            error_code = mt5.last_error()
            logger.warning(f"⚠️ MT5 initialize failed. Error: {error_code}")
            return False
            
        # Verify account if login credentials provided
        if self.login and self.password and self.server:
            authorized = mt5.login(self.login, password=self.password, server=self.server)
            if not authorized:
                logger.warning(f"⚠️ MT5 login failed for account {self.login}. Error: {mt5.last_error()}")
                return False
                
        terminal_info = mt5.terminal_info()
        if terminal_info:
            logger.info(f"✅ Connected to MT5: {terminal_info.name} ({terminal_info.company})")
        else:
            logger.info("✅ Connected to MT5 terminal")
            
        self.connected = True
        return True
    
    def get_candles(self, symbol: str, timeframe: str = "H1", num_candles: int = 100) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch market candles from MT5
        
        Args:
            symbol: Trading symbol (e.g., 'XAUUSD', 'EURUSD', 'GOLD')
            timeframe: Timeframe code (e.g., 'M15', 'H1', 'H4', 'D1')
            num_candles: Number of candles to fetch
            
        Returns:
            List of candle dictionaries or None if fetch fails
        """
        if not self.connected:
            if not self.connect():
                return None
                
        tf_code = self.timeframe_map.get(timeframe.upper(), mt5.TIMEFRAME_H1)
        
        # Ensure symbol is selected in Market Watch
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            logger.warning(f"⚠️ Symbol {symbol} not found in MT5")
            return None
            
        if not symbol_info.visible:
            if not mt5.symbol_select(symbol, True):
                logger.warning(f"⚠️ Failed to enable symbol {symbol} in Market Watch")
                return None
                
        rates = mt5.copy_rates_from_pos(symbol, tf_code, 0, num_candles)
        if rates is None or len(rates) == 0:
            logger.warning(f"⚠️ No candle rates received for {symbol} {timeframe}. Error: {mt5.last_error()}")
            return None
            
        candles = []
        for rate in rates:
            dt = datetime.fromtimestamp(rate['time'])
            candles.append({
                "open": float(rate['open']),
                "high": float(rate['high']),
                "low": float(rate['low']),
                "close": float(rate['close']),
                "volume": int(rate['tick_volume']),
                "timestamp": dt.isoformat()
            })
            
        logger.info(f"✅ Fetched {len(candles)} candles from MT5 for {symbol} {timeframe}")
        return candles
        
    def disconnect(self):
        """Disconnect from MT5 terminal"""
        if MT5_AVAILABLE and self.connected:
            mt5.shutdown()
            self.connected = False
            logger.info("🔌 Disconnected from MT5")
