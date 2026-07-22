"""
Exit Optimizer Agent — AI Hybrid Phase 2
Monitors open positions and dynamically adjusts TP/SL or exits early.

Instead of fixed TP=5% / SL=2%, the AI reads current price action
and decides: HOLD | MOVE_TP | TIGHTEN_SL | PARTIAL_EXIT | CLOSE_ALL
"""

import logging
import os
import sys
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.agents.llm_provider import LLMProvider, create_provider_from_env

logger = logging.getLogger(__name__)


ANALYSIS_PROMPT = """
You are an expert trader managing an open XAUUSD (Gold) position.

=== OPEN TRADE ===
Direction    : {direction}
Entry Price  : {entry_price:.2f}
Current Price: {current_price:.2f}
Unrealized P&L: {pnl_pct:+.2f}%
Stop Loss    : {stop_loss:.2f}  (distance: {sl_dist:.2f} pts)
Take Profit  : {take_profit:.2f} (distance: {tp_dist:.2f} pts)
Time in Trade: {hours_in_trade:.1f} hours

=== MARKET CONTEXT ===
Trend Direction : {trend}
Momentum        : {momentum}
Volatility (ATR): {atr:.2f}
Recent Candles (last 5, newest first):
{candle_summary}
Session: {session}

=== YOUR TASK ===
Decide the BEST exit management action RIGHT NOW.

Consider:
1. Is momentum still in our favor? Should we let it run?
2. Is the trade in profit? Should we protect it with a tighter SL?
3. Is price stalling near resistance/support? Take partial profit?
4. Are there reversal signals? Exit early?
5. Is the trend weakening? Move SL to breakeven?

Respond ONLY with this JSON (keep strings under 12 words):
{{
  "action": "HOLD" or "MOVE_TP" or "TIGHTEN_SL" or "PARTIAL_EXIT" or "CLOSE_ALL",
  "new_tp": null or price,
  "new_sl": null or price,
  "partial_percent": null or 0.2-0.5,
  "confidence": 0.0 to 1.0,
  "reasoning": "max 10 words"
}}

Rules:
- new_sl must NEVER move against the trade (only lock in profit or move to breakeven)
- new_tp must be higher than current price for LONG, lower for SHORT
- partial_percent must be between 0.20 and 0.50
- If unsure, use HOLD
"""


class ExitOptimizerAgent:
    """
    AI Agent #2: Dynamically manages open trade exits.

    Usage:
        agent = ExitOptimizerAgent(provider)
        decision = agent.optimize(open_trade, candles, session)

        if decision['action'] == 'MOVE_TP':
            trade.take_profit = decision['new_tp']
        elif decision['action'] == 'TIGHTEN_SL':
            trade.stop_loss = decision['new_sl']
        elif decision['action'] == 'PARTIAL_EXIT':
            close_partial(decision['partial_percent'])
        elif decision['action'] == 'CLOSE_ALL':
            close_trade()
    """

    VALID_ACTIONS = {"HOLD", "MOVE_TP", "TIGHTEN_SL", "PARTIAL_EXIT", "CLOSE_ALL"}

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        min_confidence: float = 0.55,
        enabled: bool = True,
        check_interval_bars: int = 3,   # Check AI every N candles
    ):
        """
        Args:
            provider: LLMProvider (uses env config if None)
            min_confidence: Minimum AI confidence to act (below = HOLD)
            enabled: If False, always returns HOLD (bypass mode)
            check_interval_bars: How often to call AI (every N candles)
        """
        self.provider = provider or create_provider_from_env()
        self.min_confidence = min_confidence
        self.enabled = enabled
        self.check_interval_bars = check_interval_bars
        self._bar_counter = 0
        self.decisions: List[Dict] = []

        logger.info("🎯 ExitOptimizerAgent ready")
        logger.info(f"   Provider      : {self.provider.provider_name}")
        logger.info(f"   Min confidence: {min_confidence:.0%}")
        logger.info(f"   Enabled       : {enabled}")

    def optimize(
        self,
        open_trade: Dict[str, Any],
        candles: List[Dict],
        session: str = "UNKNOWN",
        force_check: bool = False,
    ) -> Dict[str, Any]:
        """
        Evaluate an open trade and recommend an exit action.

        Args:
            open_trade: {
                'direction': 'LONG' or 'SHORT',
                'entry_price': float,
                'stop_loss': float,
                'take_profit': float,
                'entry_time': str (ISO),
                'position_size': float
            }
            candles: Recent H1 candles (list of dicts)
            session: Current trading session
            force_check: Skip interval counter and check immediately

        Returns:
            {
                'action': str,
                'new_tp': float | None,
                'new_sl': float | None,
                'partial_percent': float | None,
                'confidence': float,
                'reasoning': str,
                'applied': bool
            }
        """
        self._bar_counter += 1

        # Bypass mode
        if not self.enabled:
            return self._hold("Exit optimizer disabled")

        # Interval throttle
        if not force_check and self._bar_counter % self.check_interval_bars != 0:
            return self._hold(f"Skipping (bar {self._bar_counter} / every {self.check_interval_bars})")

        if not candles:
            return self._hold("No candles available")

        # Build context
        direction = open_trade.get("direction", "LONG")
        entry = open_trade.get("entry_price", 0.0)
        sl = open_trade.get("stop_loss", 0.0)
        tp = open_trade.get("take_profit", 0.0)
        current = candles[-1]["close"]

        pnl_pct = ((current - entry) / entry * 100) if direction == "LONG" \
                  else ((entry - current) / entry * 100)
        sl_dist = abs(current - sl)
        tp_dist = abs(tp - current)

        # Time in trade
        from datetime import datetime
        entry_time_str = open_trade.get("entry_time", "")
        try:
            entry_dt = datetime.fromisoformat(entry_time_str)
            hours_in_trade = (datetime.now() - entry_dt).total_seconds() / 3600
        except Exception:
            hours_in_trade = 0.0

        atr = self._calc_atr(candles)
        trend = self._calc_trend(candles, direction)
        momentum = self._calc_momentum(candles)
        candle_summary = self._format_candles(candles[-5:])

        prompt = ANALYSIS_PROMPT.format(
            direction=direction,
            entry_price=entry,
            current_price=current,
            pnl_pct=pnl_pct,
            stop_loss=sl,
            sl_dist=sl_dist,
            take_profit=tp,
            tp_dist=tp_dist,
            hours_in_trade=hours_in_trade,
            trend=trend,
            momentum=momentum,
            atr=atr,
            candle_summary=candle_summary,
            session=session,
        )

        try:
            result = self.provider.generate_json(prompt)
        except Exception as e:
            logger.error(f"❌ ExitOptimizerAgent API error: {e}")
            return self._hold("API error — holding position")

        if not result:
            return self._hold("Empty AI response — holding")

        action = result.get("action", "HOLD").upper()
        confidence = float(result.get("confidence", 0.0))

        # Validate action
        if action not in self.VALID_ACTIONS:
            logger.warning(f"⚠️ Invalid action '{action}', defaulting to HOLD")
            action = "HOLD"

        # Low confidence → HOLD
        if confidence < self.min_confidence and action != "HOLD":
            logger.info(f"   ⬇️  Confidence {confidence:.2f} < {self.min_confidence:.2f} → overriding to HOLD")
            action = "HOLD"

        # Safety checks
        new_tp = result.get("new_tp")
        new_sl = result.get("new_sl")
        partial = result.get("partial_percent")

        if action == "MOVE_TP" and new_tp:
            if direction == "LONG" and float(new_tp) <= current:
                action = "HOLD"
                logger.warning("⚠️ new_tp below current price for LONG — ignoring")
            elif direction == "SHORT" and float(new_tp) >= current:
                action = "HOLD"
                logger.warning("⚠️ new_tp above current price for SHORT — ignoring")

        if action == "TIGHTEN_SL" and new_sl:
            if direction == "LONG" and float(new_sl) < sl:
                action = "HOLD"
                logger.warning("⚠️ new_sl moves against LONG trade — ignoring")
            elif direction == "SHORT" and float(new_sl) > sl:
                action = "HOLD"
                logger.warning("⚠️ new_sl moves against SHORT trade — ignoring")

        if action == "PARTIAL_EXIT" and partial:
            partial = max(0.20, min(0.50, float(partial)))

        decision = {
            "action": action,
            "new_tp": float(new_tp) if new_tp and action == "MOVE_TP" else None,
            "new_sl": float(new_sl) if new_sl and action == "TIGHTEN_SL" else None,
            "partial_percent": partial if action == "PARTIAL_EXIT" else None,
            "confidence": confidence,
            "reasoning": result.get("reasoning", ""),
            "applied": action != "HOLD",
        }

        self.decisions.append({**decision, "pnl_pct": pnl_pct})

        emoji = {"HOLD": "⏸️", "MOVE_TP": "🎯", "TIGHTEN_SL": "🔒",
                 "PARTIAL_EXIT": "💰", "CLOSE_ALL": "🚪"}.get(action, "❓")
        logger.info(
            f"   Exit AI: {emoji} {action} | conf={confidence:.2f} | "
            f"P&L={pnl_pct:+.2f}% | {decision['reasoning'][:60]}"
        )

        return decision

    # ─── Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _hold(reason: str = "") -> Dict:
        return {
            "action": "HOLD",
            "new_tp": None,
            "new_sl": None,
            "partial_percent": None,
            "confidence": 1.0,
            "reasoning": reason,
            "applied": False,
        }

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
    def _calc_trend(candles: List[Dict], direction: str) -> str:
        if len(candles) < 5:
            return "UNKNOWN"
        closes = [c["close"] for c in candles[-10:]]
        slope = closes[-1] - closes[0]
        if slope > 0:
            return "UPTREND" + (" ✅ aligned" if direction == "LONG" else " ⚠️ against")
        elif slope < 0:
            return "DOWNTREND" + (" ✅ aligned" if direction == "SHORT" else " ⚠️ against")
        return "RANGING"

    @staticmethod
    def _calc_momentum(candles: List[Dict]) -> str:
        if len(candles) < 3:
            return "UNKNOWN"
        last3 = candles[-3:]
        bulls = sum(1 for c in last3 if c["close"] > c["open"])
        if bulls == 3:
            return "STRONG BULLISH"
        elif bulls == 2:
            return "MILD BULLISH"
        elif bulls == 1:
            return "MILD BEARISH"
        return "STRONG BEARISH"

    @staticmethod
    def _format_candles(candles: List[Dict]) -> str:
        lines = []
        for c in reversed(candles):
            ts = str(c.get("timestamp", ""))[:16]
            body = c["close"] - c["open"]
            candle_type = "🟢" if body >= 0 else "🔴"
            lines.append(
                f"  {candle_type} {ts}  O:{c['open']:.2f}  H:{c['high']:.2f}"
                f"  L:{c['low']:.2f}  C:{c['close']:.2f}"
            )
        return "\n".join(lines) if lines else "  No candles"

    def get_stats(self) -> Dict:
        """Return statistics about exit decisions this session."""
        if not self.decisions:
            return {"total": 0}
        total = len(self.decisions)
        action_counts: Dict[str, int] = {}
        for d in self.decisions:
            a = d["action"]
            action_counts[a] = action_counts.get(a, 0) + 1
        return {
            "total_checks": total,
            "actions": action_counts,
            "avg_confidence": f"{sum(d['confidence'] for d in self.decisions)/total:.2f}",
        }
