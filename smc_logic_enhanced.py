"""
Enhanced SMC (Smart Money Concepts) Logic with Confluence & Filters
Improvements:
  - Multi-timeframe confluence (H4 + H1 + M15)
  - Volume confirmation
  - Session filters
  - Momentum filters (RSI, MACD)
  - ATR-based dynamic stops
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import statistics


class SMCSignal(Enum):
    """SMC Trading Signals"""
    NO_SIGNAL = 0
    BULLISH = 1
    BEARISH = -1


class SessionType(Enum):
    """Trading sessions"""
    LONDON = "LONDON"  # 08:00-16:00 UTC
    NEW_YORK = "NY"    # 13:00-21:00 UTC
    ASIA = "ASIA"      # 22:00-06:00 UTC
    OFF_HOURS = "OFF"  # Low liquidity


class Momentum:
    """Simple momentum indicators"""
    
    @staticmethod
    def rsi(candles: List[Dict[str, float]], period: int = 14) -> float:
        """Calculate RSI indicator"""
        if len(candles) < period + 1:
            return 50  # Neutral
        
        closes = [c["close"] for c in candles]
        gains = []
        losses = []
        
        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def macd(candles: List[Dict[str, float]]) -> Tuple[float, float, float]:
        """Calculate MACD (12, 26, 9)"""
        if len(candles) < 26:
            return 0, 0, 0
        
        closes = [c["close"] for c in candles]
        
        # EMA 12
        ema12 = Momentum._ema(closes, 12)
        # EMA 26
        ema26 = Momentum._ema(closes, 26)
        
        macd_line = ema12 - ema26
        
        # Signal line (EMA of MACD)
        macd_values = [ema12 - ema26 for ema12, ema26 in 
                       zip(Momentum._ema_series(closes, 12),
                           Momentum._ema_series(closes, 26))]
        signal_line = Momentum._ema(macd_values[-9:], 9) if len(macd_values) >= 9 else macd_line
        
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def _ema(values: List[float], period: int) -> float:
        """Calculate EMA of last value"""
        if not values or len(values) < period:
            return sum(values) / len(values) if values else 0
        
        multiplier = 2 / (period + 1)
        ema = sum(values[:period]) / period
        
        for i in range(period, len(values)):
            ema = values[i] * multiplier + ema * (1 - multiplier)
        
        return ema
    
    @staticmethod
    def _ema_series(values: List[float], period: int) -> List[float]:
        """Calculate EMA series"""
        if not values or len(values) < period:
            return values
        
        ema_series = []
        multiplier = 2 / (period + 1)
        ema = sum(values[:period]) / period
        ema_series.append(ema)
        
        for i in range(period, len(values)):
            ema = values[i] * multiplier + ema * (1 - multiplier)
            ema_series.append(ema)
        
        return ema_series
    
    @staticmethod
    def atr(candles: List[Dict[str, float]], period: int = 14) -> float:
        """Calculate ATR (Average True Range)"""
        if len(candles) < period:
            return 0
        
        true_ranges = []
        
        for i in range(1, len(candles)):
            high = candles[i]["high"]
            low = candles[i]["low"]
            close_prev = candles[i-1]["close"]
            
            tr = max(
                high - low,
                abs(high - close_prev),
                abs(low - close_prev)
            )
            true_ranges.append(tr)
        
        atr = sum(true_ranges[-period:]) / period
        return atr


class VolumenFilter:
    """Volume-based entry confirmation"""
    
    @staticmethod
    def is_volume_confirmed(candles: List[Dict[str, float]], threshold: float = 1.2) -> bool:
        """
        Check if current candle has above-average volume
        
        Args:
            candles: Recent candles with volume data
            threshold: Volume multiplier (1.2 = 120% of average)
        
        Returns:
            True if volume confirms entry
        """
        if len(candles) < 20:
            return True  # Not enough data
        
        volumes = [c["volume"] for c in candles[:-1]]  # Exclude current
        avg_volume = sum(volumes) / len(volumes)
        
        current_volume = candles[-1]["volume"]
        
        return current_volume >= avg_volume * threshold


class SessionFilter:
    """Trading session filters"""
    
    @staticmethod
    def get_session(timestamp: str) -> SessionType:
        """
        Determine trading session from timestamp
        
        Args:
            timestamp: ISO format timestamp (YYYY-MM-DDTHH:MM:SS)
        
        Returns:
            SessionType
        """
        try:
            hour = int(timestamp.split("T")[1].split(":")[0])
        except:
            return SessionType.OFF_HOURS
        
        if 8 <= hour < 16:
            return SessionType.LONDON
        elif 13 <= hour < 21:
            return SessionType.NEW_YORK
        elif 22 <= hour or hour < 6:
            return SessionType.ASIA
        else:
            return SessionType.OFF_HOURS
    
    @staticmethod
    def is_high_liquidity(timestamp: str) -> bool:
        """
        Check if current time is high liquidity session
        
        Args:
            timestamp: ISO format timestamp
        
        Returns:
            True if in London or NY session
        """
        session = SessionFilter.get_session(timestamp)
        return session in [SessionType.LONDON, SessionType.NEW_YORK]


class MultiTimeframeAnalyzer:
    """Multi-timeframe confluence analysis"""
    
    def __init__(self):
        self.lookback = 20
    
    def analyze_confluence(self, 
                          h4_candles: List[Dict[str, float]],
                          h1_candles: List[Dict[str, float]],
                          m15_candles: List[Dict[str, float]]) -> Dict[str, Any]:
        """
        Analyze signals across multiple timeframes
        
        Args:
            h4_candles: 4-hour candles (trend)
            h1_candles: 1-hour candles (entry)
            m15_candles: 15-min candles (timing)
        
        Returns:
            Confluence analysis
        """
        smc = SMCAnalyzer()
        
        # Analyze each timeframe
        h4_analysis = smc.analyze(h4_candles)
        h1_analysis = smc.analyze(h1_candles)
        m15_analysis = smc.analyze(m15_candles)
        
        # Check confluence
        confluence_score = 0
        signals = []
        
        # H4 provides trend bias
        h4_signal = h4_analysis["signal"].value
        if h4_signal != 0:
            confluence_score += 0.3
            signals.append(f"H4: {h4_analysis['signal'].name}")
        
        # H1 provides entry
        h1_signal = h1_analysis["signal"].value
        if h1_signal != 0:
            confluence_score += 0.35
            signals.append(f"H1: {h1_analysis['signal'].name}")
        
        # M15 provides timing
        m15_signal = m15_analysis["signal"].value
        if m15_signal != 0:
            confluence_score += 0.35
            signals.append(f"M15: {m15_analysis['signal'].name}")
        
        # Only take trade if signals align
        final_signal = SMCSignal.NO_SIGNAL
        if h1_signal != 0 and m15_signal == h1_signal:
            # H1 and M15 agree
            if h4_signal == 0 or h4_signal == h1_signal:
                # H4 either neutral or agrees
                final_signal = SMCSignal(h1_signal)
                confluence_score = min(1.0, confluence_score + 0.3)
        
        return {
            "final_signal": final_signal,
            "confluence_score": confluence_score,
            "h4_signal": h4_analysis["signal"],
            "h1_signal": h1_analysis["signal"],
            "m15_signal": m15_analysis["signal"],
            "signals": signals,
            "h4_confidence": h4_analysis["confidence"],
            "h1_confidence": h1_analysis["confidence"],
            "m15_confidence": m15_analysis["confidence"]
        }


class EnhancedTradeEntry:
    """Enhanced entry validation with multiple filters"""
    
    def __init__(self):
        self.smc = SMCAnalyzer()
        self.momentum = Momentum()
        self.volume_filter = VolumenFilter()
        self.session_filter = SessionFilter()
    
    def validate_entry(self,
                      signal: SMCSignal,
                      candles: List[Dict[str, float]],
                      timestamp: str,
                      confluence_score: float = 0.7) -> Dict[str, Any]:
        """
        Comprehensive entry validation
        
        Args:
            signal: SMC signal
            candles: Recent candles
            timestamp: Current timestamp
            confluence_score: Multi-TF confluence score
        
        Returns:
            Entry validation result
        """
        if signal == SMCSignal.NO_SIGNAL:
            return {"valid": False, "reason": "No SMC signal"}
        
        # Check 1: Session liquidity
        if not self.session_filter.is_high_liquidity(timestamp):
            return {"valid": False, "reason": "Low liquidity session"}
        
        # Check 2: Volume confirmation
        if not self.volume_filter.is_volume_confirmed(candles):
            return {"valid": False, "reason": "Insufficient volume"}
        
        # Check 3: Momentum confirmation
        rsi = self.momentum.rsi(candles)
        macd_line, signal_line, histogram = self.momentum.macd(candles)
        
        if signal == SMCSignal.BULLISH:
            if rsi < 40:  # Too bearish
                return {"valid": False, "reason": "RSI too low for bullish"}
            if macd_line < signal_line:  # MACD not bullish
                return {"valid": False, "reason": "MACD not bullish"}
        elif signal == SMCSignal.BEARISH:
            if rsi > 60:  # Too bullish
                return {"valid": False, "reason": "RSI too high for bearish"}
            if macd_line > signal_line:  # MACD not bearish
                return {"valid": False, "reason": "MACD not bearish"}
        
        # Check 4: Confluence score
        if confluence_score < 0.6:
            return {"valid": False, "reason": "Low confluence score"}
        
        # Calculate dynamic stops using ATR
        atr = self.momentum.atr(candles)
        current_price = candles[-1]["close"]
        
        if signal == SMCSignal.BULLISH:
            stop_loss = current_price - (atr * 1.5)
            take_profit = current_price + (atr * 3.0)
        else:  # BEARISH
            stop_loss = current_price + (atr * 1.5)
            take_profit = current_price - (atr * 3.0)
        
        return {
            "valid": True,
            "signal": signal,
            "rsi": rsi,
            "macd_histogram": histogram,
            "atr": atr,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "confluence_score": confluence_score,
            "session": self.session_filter.get_session(timestamp).value
        }


class SMCAnalyzer:
    """Pure SMC Logic - Simplified"""
    
    def __init__(self, lookback: int = 20):
        self.lookback = lookback
    
    def detect_liquidity_sweep(self, candles: List[Dict[str, float]]) -> Optional[Tuple[int, str]]:
        """Detect Liquidity Sweep"""
        if len(candles) < 5:
            return None
        
        recent = candles[-1]
        prev_high = max([c["high"] for c in candles[-5:-1]])
        prev_low = min([c["low"] for c in candles[-5:-1]])
        
        # Bullish Sweep: Break above, close below
        if recent["high"] > prev_high and recent["close"] < prev_high:
            return (len(candles) - 1, "BULLISH")
        
        # Bearish Sweep: Break below, close above
        if recent["low"] < prev_low and recent["close"] > prev_low:
            return (len(candles) - 1, "BEARISH")
        
        return None
    
    def detect_choch(self, candles: List[Dict[str, float]]) -> Optional[Tuple[int, str]]:
        """Detect Change of Character"""
        if len(candles) < 10:
            return None
        
        recent_lows = [c["low"] for c in candles[-5:]]
        prev_lows = [c["low"] for c in candles[-10:-5]]
        
        recent_highs = [c["high"] for c in candles[-5:]]
        prev_highs = [c["high"] for c in candles[-10:-5]]
        
        # Bullish: Higher lows
        if min(recent_lows) > min(prev_lows):
            return (len(candles) - 1, "BULLISH")
        
        # Bearish: Lower highs
        if max(recent_highs) < max(prev_highs):
            return (len(candles) - 1, "BEARISH")
        
        return None
    
    def detect_fvg(self, candles: List[Dict[str, float]]) -> Optional[Tuple[float, float, str]]:
        """Detect Fair Value Gap"""
        if len(candles) < 3:
            return None
        
        c1, c2, c3 = candles[-3], candles[-2], candles[-1]
        
        # Bullish FVG
        if c1["high"] < c2["low"] < c3["high"] and c3["low"] > c1["high"]:
            return (c1["high"], c2["low"], "BULLISH")
        
        # Bearish FVG
        if c1["low"] > c2["high"] > c3["low"] and c3["high"] < c1["low"]:
            return (c2["high"], c1["low"], "BEARISH")
        
        return None
    
    def analyze(self, candles: List[Dict[str, float]]) -> Dict[str, Any]:
        """Comprehensive SMC Analysis"""
        liquidity = self.detect_liquidity_sweep(candles)
        choch = self.detect_choch(candles)
        fvg = self.detect_fvg(candles)
        
        signal = SMCSignal.NO_SIGNAL
        confidence = 0.0
        entry_level = candles[-1]["close"]
        
        # Scoring logic
        score = 0
        if liquidity:
            score += 0.3
        if choch:
            score += 0.3
        if fvg:
            score += 0.4
        
        confidence = score
        
        # Signal determination
        if liquidity and choch and fvg:
            if all(x[1] == "BULLISH" for x in [liquidity, choch, fvg]):
                signal = SMCSignal.BULLISH
                entry_level = (fvg[0] + fvg[1]) / 2 if fvg else entry_level
            elif all(x[1] == "BEARISH" for x in [liquidity, choch, fvg]):
                signal = SMCSignal.BEARISH
                entry_level = (fvg[0] + fvg[1]) / 2 if fvg else entry_level
        elif liquidity and choch:
            if liquidity[1] == choch[1] == "BULLISH":
                signal = SMCSignal.BULLISH
            elif liquidity[1] == choch[1] == "BEARISH":
                signal = SMCSignal.BEARISH
        elif fvg:
            signal = SMCSignal.BULLISH if fvg[2] == "BULLISH" else SMCSignal.BEARISH
            entry_level = (fvg[0] + fvg[1]) / 2
        
        return {
            "liquidity_sweep": liquidity,
            "choch": choch,
            "fvg": fvg,
            "signal": signal,
            "entry_level": entry_level,
            "confidence": confidence
        }
