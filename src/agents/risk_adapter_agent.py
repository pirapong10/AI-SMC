"""
Risk Adapter Agent — AI Hybrid Phase 3
Adjusts position size and risk level based on current market conditions.

Instead of always risking 2%, the AI reads volatility, trend strength,
drawdown, and news risk to recommend 1.0% – 3.0% per trade.
"""

import logging
import os
import sys
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.agents.llm_provider import LLMProvider, create_provider_from_env

logger = logging.getLogger(__name__)


ANALYSIS_PROMPT = """
You are a professional risk manager for an algorithmic XAUUSD (Gold) trading system.

=== MARKET CONDITIONS ===
Current Price    : {current_price:.2f}
Volatility (ATR) : {atr:.2f} (typical: 15-35)
Trend Strength   : {trend_strength} (0=choppy, 1=strong trend)
Trend Direction  : {trend_direction}
Confluence Score : {confluence_score:.2f} (0-1, higher = stronger SMC signal)
Session          : {session}

=== ACCOUNT CONDITIONS ===
Current Capital  : ${current_capital:.2f}
Current Drawdown : {current_drawdown:.1f}%
Recent P&L (last 5): {recent_pnl}
Win Streak       : {win_streak}
Loss Streak      : {loss_streak}

=== UPCOMING RISKS ===
Minutes to next major news: {mins_to_news}
Market condition: {market_condition}

=== YOUR TASK ===
Determine the appropriate risk level (as % of capital) for the next trade.

Guidelines:
- Base risk: 2.0%
- High volatility (ATR > 30): reduce risk → 1.0-1.5%
- Low volatility (ATR < 15): neutral → 2.0%
- Strong trending + high confluence (>0.7): increase → 2.5-3.0%
- Drawdown > 10%: reduce → 1.0-1.5%
- Drawdown > 15%: reduce → 0.5-1.0% or SKIP
- Loss streak >= 3: reduce → 1.0-1.5%
- News within 30 min: reduce → 0.5% or SKIP
- News within 15 min: SKIP
- Win streak >= 3 + strong trend: maintain or slight increase

Respond ONLY with this JSON (no extra text):
{{
  "recommended_risk_pct": 0.5 to 3.0,
  "is_safe_to_trade": true or false,
  "market_condition": "TRENDING" or "CHOPPY" or "RANGING" or "NEWS_RISK" or "HIGH_VOLATILITY",
  "risk_level": "LOW" or "NORMAL" or "HIGH",
  "reasoning": "one sentence explanation",
  "skip_reason": null or "reason why to skip"
}}
"""


class RiskAdapterAgent:
    """
    AI Agent #3: Adapts position size risk based on market conditions.

    Usage:
        agent = RiskAdapterAgent(provider)
        result = agent.calculate(market_data, account_data)

        if result['is_safe_to_trade']:
            risk_pct = result['recommended_risk_pct']  # Use this instead of fixed 2%
            position_size = calculate_position(risk_pct)
        else:
            skip_trade(result['skip_reason'])
    """

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        base_risk_pct: float = 2.0,
        min_risk_pct: float = 0.5,
        max_risk_pct: float = 3.0,
        enabled: bool = True,
    ):
        """
        Args:
            provider: LLMProvider (uses env config if None)
            base_risk_pct: Default risk % (used when AI is disabled)
            min_risk_pct: Floor for AI recommendations
            max_risk_pct: Ceiling for AI recommendations
            enabled: If False, always returns base_risk_pct
        """
        self.provider = provider or create_provider_from_env()
        self.base_risk_pct = base_risk_pct
        self.min_risk_pct = min_risk_pct
        self.max_risk_pct = max_risk_pct
        self.enabled = enabled
        self.decisions: List[Dict] = []

        logger.info("🛡️  RiskAdapterAgent ready")
        logger.info(f"   Provider  : {self.provider.provider_name}")
        logger.info(f"   Risk range: {min_risk_pct}% – {max_risk_pct}%")
        logger.info(f"   Enabled   : {enabled}")

    def calculate(
        self,
        candles: List[Dict],
        current_capital: float,
        confluence_score: float = 0.5,
        current_drawdown: float = 0.0,
        session: str = "UNKNOWN",
        recent_trades: Optional[List[Dict]] = None,
        mins_to_news: int = 999,
    ) -> Dict[str, Any]:
        """
        Calculate recommended risk % for the next trade.

        Args:
            candles: Recent H1 candles
            current_capital: Current account balance
            confluence_score: SMC confluence score (0-1)
            current_drawdown: Current drawdown from peak (%)
            session: Trading session
            recent_trades: List of recent trade dicts with 'profit_loss' key
            mins_to_news: Minutes until next major news event

        Returns:
            {
                'recommended_risk_pct': float,
                'is_safe_to_trade': bool,
                'market_condition': str,
                'risk_level': str,
                'reasoning': str,
                'skip_reason': str | None
            }
        """
        # Bypass mode
        if not self.enabled:
            return self._default_result()

        # Emergency rules (no AI needed)
        if mins_to_news <= 15:
            return self._skip("Major news in ≤15 min — skip trade")
        if current_drawdown > 20.0:
            return self._skip(f"Drawdown {current_drawdown:.1f}% exceeds 20% — protect capital")

        # Calculate market stats
        atr = self._calc_atr(candles)
        trend_direction, trend_strength = self._calc_trend(candles)
        current_price = candles[-1]["close"] if candles else 0.0

        # Recent trade streak
        recent_trades = recent_trades or []
        win_streak = self._count_streak(recent_trades, winning=True)
        loss_streak = self._count_streak(recent_trades, winning=False)
        recent_pnl_str = ", ".join(
            f"{'WIN' if t.get('profit_loss', 0) > 0 else 'LOSS'}"
            for t in recent_trades[-5:]
        ) or "No trades yet"

        market_condition = self._classify_market(atr, trend_strength, mins_to_news)

        prompt = ANALYSIS_PROMPT.format(
            current_price=current_price,
            atr=atr,
            trend_strength=f"{trend_strength:.2f}",
            trend_direction=trend_direction,
            confluence_score=confluence_score,
            session=session,
            current_capital=current_capital,
            current_drawdown=current_drawdown,
            recent_pnl=recent_pnl_str,
            win_streak=win_streak,
            loss_streak=loss_streak,
            mins_to_news=mins_to_news,
            market_condition=market_condition,
        )

        try:
            result = self.provider.generate_json(prompt)
        except Exception as e:
            logger.error(f"❌ RiskAdapterAgent API error: {e}")
            return self._default_result()

        if not result:
            return self._default_result()

        # Clamp risk to safe range
        risk_pct = float(result.get("recommended_risk_pct", self.base_risk_pct))
        risk_pct = max(self.min_risk_pct, min(self.max_risk_pct, risk_pct))

        decision = {
            "recommended_risk_pct": round(risk_pct, 2),
            "is_safe_to_trade": bool(result.get("is_safe_to_trade", True)),
            "market_condition": result.get("market_condition", market_condition),
            "risk_level": result.get("risk_level", "NORMAL"),
            "reasoning": result.get("reasoning", ""),
            "skip_reason": result.get("skip_reason"),
        }

        self.decisions.append(decision)

        safe_emoji = "✅" if decision["is_safe_to_trade"] else "🚫"
        logger.info(
            f"   Risk AI: {safe_emoji} {risk_pct:.1f}% | "
            f"{decision['market_condition']} | "
            f"{decision['reasoning'][:60]}"
        )

        return decision

    # ─── Helpers ──────────────────────────────────────────────────────

    def _default_result(self) -> Dict:
        return {
            "recommended_risk_pct": self.base_risk_pct,
            "is_safe_to_trade": True,
            "market_condition": "UNKNOWN",
            "risk_level": "NORMAL",
            "reasoning": "Using default risk (AI bypassed)",
            "skip_reason": None,
        }

    @staticmethod
    def _skip(reason: str) -> Dict:
        return {
            "recommended_risk_pct": 0.0,
            "is_safe_to_trade": False,
            "market_condition": "NEWS_RISK",
            "risk_level": "LOW",
            "reasoning": reason,
            "skip_reason": reason,
        }

    @staticmethod
    def _calc_atr(candles: List[Dict], period: int = 14) -> float:
        if len(candles) < 2:
            return 20.0
        trs = []
        for i in range(1, len(candles)):
            h, l, pc = candles[i]["high"], candles[i]["low"], candles[i-1]["close"]
            trs.append(max(h - l, abs(h - pc), abs(l - pc)))
        return round(sum(trs[-period:]) / min(period, len(trs)), 2)

    @staticmethod
    def _calc_trend(candles: List[Dict]) -> tuple:
        if len(candles) < 10:
            return "UNKNOWN", 0.5
        closes = [c["close"] for c in candles[-20:]]
        first = sum(closes[:len(closes)//2]) / (len(closes)//2)
        second = sum(closes[len(closes)//2:]) / (len(closes) - len(closes)//2)
        diff = (second - first) / first
        strength = min(abs(diff) * 100, 1.0)
        direction = "BULLISH" if diff > 0 else "BEARISH"
        return direction, strength

    @staticmethod
    def _classify_market(atr: float, trend_strength: float, mins_to_news: int) -> str:
        if mins_to_news <= 60:
            return "NEWS_RISK"
        if atr > 30:
            return "HIGH_VOLATILITY"
        if trend_strength > 0.5:
            return "TRENDING"
        if atr < 15:
            return "RANGING"
        return "CHOPPY"

    @staticmethod
    def _count_streak(trades: List[Dict], winning: bool) -> int:
        streak = 0
        for t in reversed(trades):
            pnl = t.get("profit_loss", t.get("pnl", 0))
            is_win = pnl > 0
            if is_win == winning:
                streak += 1
            else:
                break
        return streak

    def get_stats(self) -> Dict:
        if not self.decisions:
            return {"total": 0}
        total = len(self.decisions)
        safe = sum(1 for d in self.decisions if d["is_safe_to_trade"])
        avg_risk = sum(d["recommended_risk_pct"] for d in self.decisions) / total
        return {
            "total_assessments": total,
            "safe_to_trade": safe,
            "skipped": total - safe,
            "avg_recommended_risk": f"{avg_risk:.2f}%",
        }
