"""
Historical Data Loader
Load and process XAUUSD data from CSV exports (MT5)
"""

import pandas as pd
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)


class CandleData:
    """Candle data object"""
    def __init__(self, timestamp: str, open_price: float, high: float, 
                 low: float, close: float, volume: int):
        self.timestamp = timestamp
        self.open = open_price
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume
        }


class DataLoader:
    """Load and process historical OHLCV data"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        logger.info(f"📂 Data directory: {self.data_dir}")
    
    def load_csv(self, filename: str) -> pd.DataFrame:
        """
        Load CSV file from data directory
        
        Expected columns: Date, Time, Open, High, Low, Close, Volume
        (MT5 export format)
        
        Args:
            filename: CSV filename
        
        Returns:
            DataFrame with OHLCV data
        """
        filepath = self.data_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"❌ File not found: {filepath}")
        
        try:
            # MT5 exports each row wrapped in double-quotes with tab separators inside,
            # e.g.: "<DATE>\t<TIME>\t<OPEN>\t..."
            # We must ignore quoting and split on tabs.
            import csv
            with open(filepath, 'r', encoding='utf-8') as f:
                first_line = f.readline()
            
            if '\t' in first_line:
                # Tab-separated (MT5 format, possibly quoted rows)
                df = pd.read_csv(
                    filepath,
                    sep='\t',
                    quoting=csv.QUOTE_NONE,
                    escapechar=None,
                )
                # Strip any residual leading/trailing quotes from column names
                df.columns = [c.strip('"') for c in df.columns]
            else:
                df = pd.read_csv(filepath)
            
            logger.info(f"✅ Loaded: {filename} ({len(df)} rows)")
            return df
        except Exception as e:
            logger.error(f"❌ Error loading {filename}: {e}")
            raise
    
    def process_csv(self, filename: str, combine_datetime: bool = True) -> List[CandleData]:
        """
        Process MT5 CSV export to Candle objects
        
        Args:
            filename: CSV filename
            combine_datetime: Combine Date + Time columns
        
        Returns:
            List of Candle objects
        """
        df = self.load_csv(filename)
        
        # Combine Date and Time if separate
        if combine_datetime and 'Date' in df.columns and 'Time' in df.columns:
            df['Timestamp'] = pd.to_datetime(df['Date'] + ' ' + df['Time'])
        elif 'Timestamp' not in df.columns and '<DATE>' in df.columns:
            # MT5 tab-separated export format: dates use dots (e.g. 2024.01.02)
            # QUOTE_NONE leaves literal " chars in first/last field values — strip them
            date_str = df['<DATE>'].astype(str).str.strip('"')
            time_str = df['<TIME>'].astype(str).str.strip('"')
            df['Timestamp'] = pd.to_datetime(
                date_str + ' ' + time_str,
                format='%Y.%m.%d %H:%M:%S'
            )
        else:
            df['Timestamp'] = pd.to_datetime(df.iloc[:, 0])  # First column as timestamp
        
        # Standardize column names
        df.columns = df.columns.str.lower()
        df.columns = df.columns.str.replace('<', '').str.replace('>', '')
        
        # Map MT5 column aliases to standard names
        # MT5 exports both <TICKVOL> and <VOL>; prefer tickvol as volume
        if 'tickvol' in df.columns:
            df.rename(columns={'tickvol': 'volume'}, inplace=True)
        elif 'tick_volume' in df.columns:
            df.rename(columns={'tick_volume': 'volume'}, inplace=True)
        elif 'vol' in df.columns and 'volume' not in df.columns:
            df.rename(columns={'vol': 'volume'}, inplace=True)
        
        # Drop duplicate columns (keep first occurrence)
        df = df.loc[:, ~df.columns.duplicated()]
        
        # Ensure required columns exist
        required = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"❌ Missing columns: {missing}")
        
        # Create Candle objects
        candles = []
        for _, row in df.iterrows():
            candle = CandleData(
                timestamp=row['timestamp'].isoformat(),
                open_price=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=int(row['volume'])
            )
            candles.append(candle)
        
        logger.info(f"✅ Processed {len(candles)} candles")
        return candles
    
    def resample_timeframe(self, candles: List[CandleData], 
                          from_tf: str = "H1", to_tf: str = "H4") -> List[CandleData]:
        """
        Resample candles to different timeframe
        E.g., H1 → H4
        
        Args:
            candles: List of candle data
            from_tf: Source timeframe (H1, M15, etc.)
            to_tf: Target timeframe (H4, D1, etc.)
        
        Returns:
            Resampled candles
        """
        # Convert to DataFrame for easier resampling
        df = pd.DataFrame([c.to_dict() for c in candles])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        # Resample OHLC
        resampled = df.resample(self._get_freq(to_tf)).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        # Convert back to Candle objects
        resampled_candles = []
        for timestamp, row in resampled.iterrows():
            candle = CandleData(
                timestamp=timestamp.isoformat(),
                open_price=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=int(row['volume'])
            )
            resampled_candles.append(candle)
        
        logger.info(f"✅ Resampled {len(candles)} candles {from_tf}→{to_tf} ({len(resampled_candles)} candles)")
        return resampled_candles
    
    def _get_freq(self, timeframe: str) -> str:
        """Convert timeframe to pandas frequency"""
        freq_map = {
            'M1': '1min',
            'M5': '5min',
            'M15': '15min',
            'M30': '30min',
            'H1': '1H',
            'H4': '4H',
            'D1': '1D',
            'W1': '1W',
            'MN': '1M'
        }
        return freq_map.get(timeframe, '1H')
    
    def get_date_range(self, candles: List[CandleData]) -> tuple:
        """Get min and max dates"""
        timestamps = [pd.to_datetime(c.timestamp) for c in candles]
        return min(timestamps), max(timestamps)
    
    def filter_by_date(self, candles: List[CandleData], 
                      start_date: str, end_date: str) -> List[CandleData]:
        """
        Filter candles by date range
        
        Args:
            candles: List of candles
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        
        Returns:
            Filtered candles
        """
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        
        filtered = [
            c for c in candles
            if start <= pd.to_datetime(c.timestamp) <= end
        ]
        
        logger.info(f"✅ Filtered {len(filtered)} candles ({start_date} to {end_date})")
        return filtered
    
    def get_stats(self, candles: List[CandleData]) -> Dict[str, Any]:
        """Get data statistics"""
        if not candles:
            return {}
        
        closes = [c.close for c in candles]
        opens = [c.open for c in candles]
        
        return {
            "total_candles": len(candles),
            "start_date": candles[0].timestamp,
            "end_date": candles[-1].timestamp,
            "min_price": min([c.low for c in candles]),
            "max_price": max([c.high for c in candles]),
            "avg_price": np.mean(closes),
            "price_range": max([c.high for c in candles]) - min([c.low for c in candles]),
            "avg_volume": np.mean([c.volume for c in candles])
        }


# Example usage
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Load data
    loader = DataLoader(data_dir="./data")
    
    try:
        # Load XAUUSD H1 data from MT5 export
        candles = loader.process_csv("XAUUSD_H1_2024.csv")
        
        # Get stats
        stats = loader.get_stats(candles)
        print("\n📊 Data Statistics:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        # Filter to 2024 data only
        candles_2024 = loader.filter_by_date(candles, "2024-01-01", "2024-12-31")
        
        # Resample to H4
        candles_h4 = loader.resample_timeframe(candles_2024, from_tf="H1", to_tf="H4")
        
        print(f"\n✅ Successfully loaded and processed data!")
        print(f"   H1 candles: {len(candles_2024)}")
        print(f"   H4 candles: {len(candles_h4)}")
        
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print("   Place your MT5 export CSV in ./data/ directory")
