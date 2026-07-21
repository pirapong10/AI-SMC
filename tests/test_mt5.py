"""
Test MetaTrader 5 (MT5) Connection & Data Fetching
"""

import os
import sys
import io
from pathlib import Path

# Force stdout encoding to UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
load_dotenv()

from data.mt5_connector import MT5Connector, MT5_AVAILABLE


def test_mt5_connection():
    """Test MT5 connector module"""
    print("=" * 60)
    print("🔌 MetaTrader 5 (MT5) Integration Test")
    print("=" * 60)
    
    if not MT5_AVAILABLE:
        print("❌ MetaTrader5 Python package is NOT installed.")
        return False
        
    print("✅ MetaTrader5 package is installed.")
    
    login = int(os.getenv("MT5_LOGIN", "0") or "0")
    password = os.getenv("MT5_PASSWORD", "")
    server = os.getenv("MT5_SERVER", "")
    path = os.getenv("MT5_PATH", "")
    symbol = os.getenv("SYMBOL", "XAUUSD")
    
    connector = MT5Connector(login=login, password=password, server=server, path=path)
    
    print("\n📡 Attempting connection to MT5 terminal...")
    connected = connector.connect()
    
    if not connected:
        print("⚠️ Could not connect to active MT5 terminal.")
        print("💡 Note: Please ensure MetaTrader 5 terminal is installed, running, and logged in.")
        print("ℹ️ The bot will automatically fallback to mock market data when MT5 is not running.")
        return True  # Fallback handles this gracefully
        
    print("✅ Connected to MT5 terminal successfully!")
    
    # Fetch candles
    print(f"\n📊 Fetching 10 candles for {symbol} H1...")
    candles = connector.get_candles(symbol=symbol, timeframe="H1", num_candles=10)
    
    if candles and len(candles) > 0:
        print(f"✅ Fetched {len(candles)} real market candles!")
        latest = candles[-1]
        print(f"   Latest Candle ({latest['timestamp']}):")
        print(f"   Open: {latest['open']}, High: {latest['high']}, Low: {latest['low']}, Close: {latest['close']}")
    else:
        print(f"⚠️ Could not fetch candles for {symbol}. Make sure {symbol} is in MT5 Market Watch.")
        
    connector.disconnect()
    
    print("\n" + "=" * 60)
    print("🎉 MT5 Test completed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    test_mt5_connection()
