"""
Pure SMC (Smart Money Concepts) Logic Implementation
Core: Liquidity Sweep → CHoCH → FVG Pattern Recognition
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np
from enum import Enum


class SMCSignal(Enum):
    """SMC Trading Signals"""
    NO_SIGNAL = 0
    BULLISH = 1
    BEARISH = -1


@dataclass
class Candle:
    """Represents a single candle/bar"""
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: str
    
    @property
    def body(self) -> float:
        """Candle body size"""
        return abs(self.close - self.open)
    
    @property
    def upper_wick(self) -> float:
        """Upper wick size"""
        return self.high - max(self.open, self.close)
    
    @property
    def lower_wick(self) -> float:
        """Lower wick size"""
        return min(self.open, self.close) - self.low
    
    @property
    def is_bullish(self) -> bool:
        return self.close > self.open
    
    @property
    def is_bearish(self) -> bool:
        return self.close < self.open


class SMCAnalyzer:
    """Smart Money Concepts Analyzer"""
    
    def __init__(self, lookback: int = 20):
        self.lookback = lookback
    
    # ==================== LIQUIDITY SWEEP ====================
    
    def detect_liquidity_sweep(self, candles: List[Candle]) -> Optional[Tuple[int, str]]:
        """
        Detect Liquidity Sweep (Break of Structure)
        Liquidity Sweep = Price breaks recent swing high/low then reverses
        
        Returns:
            (index, direction) - Index of sweep, 'BULLISH' or 'BEARISH'
        """
        if len(candles) < 5:
            return None
        
        recent = candles[-1]
        prev_high = max([c.high for c in candles[-5:-1]])
        prev_low = min([c.low for c in candles[-5:-1]])
        
        # Bullish Liquidity Sweep: Breaks above resistance, closes below
        if recent.high > prev_high and recent.close < prev_high:
            return (len(candles) - 1, "BULLISH")
        
        # Bearish Liquidity Sweep: Breaks below support, closes above
        if recent.low < prev_low and recent.close > prev_low:
            return (len(candles) - 1, "BEARISH")
        
        return None
    
    # ==================== CHANGE OF CHARACTER (CHoCH) ====================
    
    def detect_choch(self, candles: List[Candle]) -> Optional[Tuple[int, str]]:
        """
        Detect Change of Character (CHoCH)
        CHoCH = Shift from creating higher lows to lower lows (or vice versa)
        
        Returns:
            (index, direction) - Index of CHoCH, 'BULLISH' or 'BEARISH'
        """
        if len(candles) < 5:
            return None
        
        # Calculate recent swing points (last 5 candles)
        recent_lows = [c.low for c in candles[-5:]]
        recent_highs = [c.high for c in candles[-5:]]
        
        # Previous pattern (5 candles before)
        if len(candles) >= 10:
            prev_lows = [c.low for c in candles[-10:-5]]
            prev_highs = [c.high for c in candles[-10:-5]]
            
            # Bullish CHoCH: Was making lower lows, now making higher lows
            if min(recent_lows) > min(prev_lows):
                return (len(candles) - 1, "BULLISH")
            
            # Bearish CHoCH: Was making higher highs, now making lower highs
            if max(recent_highs) < max(prev_highs):
                return (len(candles) - 1, "BEARISH")
        
        return None
    
    # ==================== FAIR VALUE GAP (FVG) ====================
    
    def detect_fvg(self, candles: List[Candle]) -> Optional[Tuple[float, float, str]]:
        """
        Detect Fair Value Gap (FVG)
        FVG = Gap between candle highs/lows that price hasn't filled
        
        Returns:
            (gap_low, gap_high, direction) - Gap boundaries and direction
        """
        if len(candles) < 3:
            return None
        
        # Check last 3 candles for gap
        c1, c2, c3 = candles[-3], candles[-2], candles[-1]
        
        # Bullish FVG: Gap up, low of c3 > high of c1
        if c1.high < c2.low < c3.high and c3.low > c1.high:
            return (c1.high, c2.low, "BULLISH")
        
        # Bearish FVG: Gap down, high of c3 < low of c1
        if c1.low > c2.high > c3.low and c3.high < c1.low:
            return (c2.high, c1.low, "BEARISH")
        
        return None
    
    # ==================== SELL LIMIT LEVEL ====================
    
    def calculate_sell_limit(self, candles: List[Candle], fvg: Optional[Tuple] = None) -> float:
        """
        Calculate Sell Limit Entry Level (50% of FVG or recent support)
        FVG Sell Limit = 50% of the Fair Value Gap
        """
        if fvg:
            gap_low, gap_high, direction = fvg
            if direction == "BEARISH":
                # 50% of gap
                return (gap_low + gap_high) / 2
        
        # Fallback: Recent support level
        recent_low = min([c.low for c in candles[-10:]])
        return recent_low
    
    # ==================== INTEGRATED SMC SIGNAL ====================
    
    def analyze(self, candles: List[Candle]) -> dict:
        """
        Comprehensive SMC Analysis: Liquidity → CHoCH → FVG → Entry
        
        Returns:
            {
                'liquidity_sweep': (index, direction) or None,
                'choch': (index, direction) or None,
                'fvg': (gap_low, gap_high, direction) or None,
                'signal': SMCSignal,
                'entry_level': float,
                'confidence': float (0-1)
            }
        """
        liquidity = self.detect_liquidity_sweep(candles)
        choch = self.detect_choch(candles)
        fvg = self.detect_fvg(candles)
        
        signal = SMCSignal.NO_SIGNAL
        confidence = 0.0
        entry_level = candles[-1].close
        
        # Signal logic: Liquidity Sweep → CHoCH → FVG Sell Limit
        if liquidity and choch and fvg:
            confidence = 0.9  # High confidence: all 3 aligned
            
            if liquidity[1] == "BULLISH" and choch[1] == "BULLISH" and fvg[2] == "BULLISH":
                signal = SMCSignal.BULLISH
                entry_level = self.calculate_sell_limit(candles, fvg)
            elif liquidity[1] == "BEARISH" and choch[1] == "BEARISH" and fvg[2] == "BEARISH":
                signal = SMCSignal.BEARISH
                entry_level = self.calculate_sell_limit(candles, fvg)
        elif liquidity and choch:
            confidence = 0.7  # Medium confidence
            if liquidity[1] == choch[1]:
                signal = SMCSignal.BULLISH if liquidity[1] == "BULLISH" else SMCSignal.BEARISH
                entry_level = self.calculate_sell_limit(candles, fvg)
        elif fvg:
            confidence = 0.5  # Lower confidence
            signal = SMCSignal.BULLISH if fvg[2] == "BULLISH" else SMCSignal.BEARISH
            entry_level = self.calculate_sell_limit(candles, fvg)
        
        return {
            'liquidity_sweep': liquidity,
            'choch': choch,
            'fvg': fvg,
            'signal': signal,
            'entry_level': entry_level,
            'confidence': confidence
        }


# Example usage
if __name__ == "__main__":
    # Create sample candles
    sample_candles = [
        Candle(100, 105, 99, 104, 1000, "2024-01-01"),
        Candle(104, 108, 103, 107, 1200, "2024-01-02"),
        Candle(107, 112, 106, 111, 1500, "2024-01-03"),
        Candle(111, 115, 110, 114, 1800, "2024-01-04"),
        Candle(114, 116, 108, 109, 2000, "2024-01-05"),  # Liquidity sweep down
    ]
    
    analyzer = SMCAnalyzer()
    result = analyzer.analyze(sample_candles)
    print(f"SMC Analysis Result: {result}")
