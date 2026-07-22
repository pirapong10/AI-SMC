"""
Signal Confidence Agent — AI Hybrid Phase 1
Analyzes SMC signals and confirms whether to trade or skip.

Flow:
  SMC detects signal → SignalConfidenceAgent → confirmed/rejected → place/skip trade
"""

import json
import logging
import os
import sys
from typing import Dict, Any, List, Optional

# Allow running from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.agents.llm_provider import LLMProvider, create_provider_from_env

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
You are a professional SMC (Smart Money Concepts) trading analyst.
Your job is to evaluate whether a detected trading signal is a genuine 
high-probability setup or a fakeout/noise.

You MUST respond ONLY with a valid JSON object. No explanation text outside JSON.
"""

ANALYSIS_PROMPT = """
Analyze this SMC trading signal and determine if it is worth trading.

=== DETECTED SIGNALS ===
Liquidity Sweep : {liquidity}
Change of Character (CHoCH): {choch}
Fair Value Gap (FVG): {fvg}
Initial Confidence Score: {confidence:.2f}
Signal Direction: {direction}

=== MARKET CONTEXT ===
Current Price   : {current_price}
Recent Candles  (last 5, newest first):
{candle_summary}

Trend (recent 20 candles): {trend}
Volatility (ATR-14)      : {atr:.2f}
Session                  : {session}

=== YOUR TASK ===
1. Is this a TRUE signal or a FAKEOUT?
2. Do all SMC components align?
3. Is market structure supporting the direction?
4. Is the risk/reward favorable?

Respond ONLY with this JSON:
{{
  "is_valid_signal": true or false,
  "confidence_score": 0.0 to 1.0,
  "signal_strength": "WEAK" or "MEDIUM" or "STRONG",
  "reasoning": "one sentence explanation",
  "key_concern": "main risk if any, or null"
}}
"""


class SignalConfidenceAgent:
    """
    AI Agent #1: Confirms or rejects SMC trade signals.

    Usage:
        agent = SignalConfidenceAgent(provider)
        result = agent.analyze(smc_analysis, candles)
        if result['is_valid_signal'] and result['confidence_score'] >= 0.60:
            place_trade()
    """

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        min_confidence: float = 0.60,
        enabled: bool = True
    ):
        """
        Args:
            provider: LLMProvider instance (uses env config if None)
            min_confidence: Minimum AI confidence to approve a trade (0.0–1.0)
            enabled: If False, passes all signals through (bypass mode)
        """
        self.provider = provider or create_provider_from_env()
        self.min_confidence = min_confidence
        self.enabled = enabled
        self.decisions: List[Dict] = []   # audit log

        logger.info(f"🤖 SignalConfidenceAgent ready")
        logger.info(f"   Provider   : {self.provider.provider_name}")
        logger.info(f"   Min confidence: {min_confidence:.0%}")
        logger.info(f"   Enabled    : {enabled}")

    def analyze(
        self,
        smc_analysis: Dict[str, Any],
        candles: List[Dict],
        session: str = "UNKNOWN"
    ) -> Dict[str, Any]:
        """
        Evaluate an SMC signal using AI.

        Args:
            smc_analysis: Output from SMCAnalyzer.analyze()
                          Expected keys: signal, confidence, liquidity_sweep, choch, fvg
            candles: List of recent candle dicts (timestamp, open, high, low, close, volume)
            session: Current market session (LONDON, NEW_YORK, ASIA)

        Returns:
            {
              "is_valid_signal": bool,
              "confidence_score": float,
              "signal_strength": str,
              "reasoning": str,
              "key_concern": str | None,
              "approved": bool   ← True if confidence >= min_confidence
            }
        """
        # Bypass mode — no AI call, approve everything
        if not self.enabled:
            return self._bypass_result(smc_analysis)

        # Build context
        liquidity = smc_analysis.get("liquidity_sweep")
        choch = smc_analysis.get("choch")
        fvg = smc_analysis.get("fvg")
        confidence = smc_analysis.get("confidence", 0)
        signal = smc_analysis.get("signal")
        direction = signal.name if hasattr(signal, "name") else str(signal)

        current_price = candles[-1]["close"] if candles else 0
        atr = self._calc_atr(candles)
        trend = self._calc_trend(candles)
        candle_summary = self._format_candles(candles[-5:])

        prompt = ANALYSIS_PROMPT.format(
            liquidity=self._fmt(liquidity),
            choch=self._fmt(choch),
            fvg=self._fmt(fvg),
            confidence=confidence,
            direction=direction,
            current_price=current_price,
            candle_summary=candle_summary,
            trend=trend,
            atr=atr,
            session=session
        )

        try:
            result = self.provider.generate_json(prompt)
        except Exception as e:
            logger.error(f"❌ SignalConfidenceAgent API error: {e}")
            return self._fallback_result(smc_analysis)

        if not result:
            logger.warning("⚠️ Empty response from AI, falling back")
            return self._fallback_result(smc_analysis)

        # Enrich result
        result["approved"] = (
            result.get("is_valid_signal", False) and
            result.get("confidence_score", 0) >= self.min_confidence
        )

        # Audit log
        self.decisions.append({
            "direction": direction,
            "smc_confidence": confidence,
            "ai_confidence": result.get("confidence_score"),
            "approved": result["approved"],
            "strength": result.get("signal_strength"),
            "reasoning": result.get("reasoning"),
        })

        action = "✅ APPROVED" if result["approved"] else "❌ REJECTED"
        logger.info(
            f"   AI Signal Check: {action} | "
            f"AI conf={result.get('confidence_score', 0):.2f} | "
            f"{result.get('signal_strength')} | "
            f"{result.get('reasoning', '')[:60]}"
        )

        return result

    # ─── Helpers ─────────────────────────────────────────────

    @staticmethod
    def _fmt(val) -> str:
        if val is None:
            return "Not detected"
        if isinstance(val, (list, tuple)) and len(val) >= 2:
            return f"Detected ({val[1]})"
        return str(val)

    @staticmethod
    def _calc_atr(candles: List[Dict], period: int = 14) -> float:
        if len(candles) < 2:
            return 0.0
        trs = []
        for i in range(1, len(candles)):
            h, l, pc = candles[i]["high"], candles[i]["low"], candles[i-1]["close"]
            trs.append(max(h - l, abs(h - pc), abs(l - pc)))
        return sum(trs[-period:]) / min(period, len(trs))

    @staticmethod
    def _calc_trend(candles: List[Dict]) -> str:
        if len(candles) < 10:
            return "UNKNOWN"
        closes = [c["close"] for c in candles]
        first_half = sum(closes[:len(closes)//2]) / (len(closes)//2)
        second_half = sum(closes[len(closes)//2:]) / (len(closes) - len(closes)//2)
        diff_pct = (second_half - first_half) / first_half * 100
        if diff_pct > 0.3:
            return f"UPTREND (+{diff_pct:.2f}%)"
        elif diff_pct < -0.3:
            return f"DOWNTREND ({diff_pct:.2f}%)"
        return f"RANGING ({diff_pct:.2f}%)"

    @staticmethod
    def _format_candles(candles: List[Dict]) -> str:
        lines = []
        for c in reversed(candles):
            ts = str(c.get("timestamp", ""))[:16]
            lines.append(
                f"  {ts}  O:{c['open']:.2f}  H:{c['high']:.2f}  "
                f"L:{c['low']:.2f}  C:{c['close']:.2f}"
            )
        return "\n".join(lines) if lines else "  No candles"

    def _bypass_result(self, smc_analysis: Dict) -> Dict:
        """Pass-through when agent is disabled."""
        conf = smc_analysis.get("confidence", 0.5)
        return {
            "is_valid_signal": True,
            "confidence_score": conf,
            "signal_strength": "MEDIUM",
            "reasoning": "AI bypass mode — signal passed through",
            "key_concern": None,
            "approved": True
        }

    def _fallback_result(self, smc_analysis: Dict) -> Dict:
        """Conservative fallback on API failure — reject the trade."""
        return {
            "is_valid_signal": False,
            "confidence_score": 0.0,
            "signal_strength": "WEAK",
            "reasoning": "AI unavailable — trade rejected for safety",
            "key_concern": "API error",
            "approved": False
        }

    def get_stats(self) -> Dict:
        """Return decision statistics for the current session."""
        if not self.decisions:
            return {"total": 0}
        total = len(self.decisions)
        approved = sum(1 for d in self.decisions if d["approved"])
        return {
            "total_analyzed": total,
            "approved": approved,
            "rejected": total - approved,
            "approval_rate": f"{approved/total*100:.1f}%",
            "avg_ai_confidence": f"{sum(d['ai_confidence'] or 0 for d in self.decisions)/total:.2f}"
        }
