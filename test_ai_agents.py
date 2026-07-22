"""Quick integration test for all 3 AI Agents"""
import os, sys, random
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, '.')

from src.agents.llm_provider import create_provider_from_env
from src.agents.signal_confidence_agent import SignalConfidenceAgent
from src.agents.exit_optimizer_agent import ExitOptimizerAgent
from src.agents.risk_adapter_agent import RiskAdapterAgent
from smc_logic import SMCSignal

provider = create_provider_from_env()
print("Provider:", provider.provider_name)
print()

# Build sample candles (bullish XAUUSD)
random.seed(99)
price = 4100.0
candles = []
for i in range(25):
    o = price
    h = o + random.uniform(8, 25)
    l = o - random.uniform(5, 12)
    c = o + random.uniform(2, 18)
    candles.append({"timestamp": f"2026-07-22T{i:02d}:00:00",
                    "open": o, "high": h, "low": l, "close": c, "volume": 6000})
    price = c

smc_analysis = {
    "signal": SMCSignal.BULLISH,
    "confidence": 0.6,
    "liquidity_sweep": (20, "BULLISH"),
    "choch": (24, "BULLISH"),
    "fvg": None,
}
open_trade = {
    "direction": "LONG",
    "entry_price": 4110.0,
    "stop_loss": 4090.0,
    "take_profit": 4160.0,
    "entry_time": "2026-07-22T05:00:00",
    "position_size": 9.5,
}

# --- Agent 1 ---
print("=" * 50)
print("AGENT 1: SignalConfidenceAgent")
print("=" * 50)
sig_agent = SignalConfidenceAgent(provider, min_confidence=0.60)
sig = sig_agent.analyze(smc_analysis, candles, session="LONDON")
print("  Approved:", sig["approved"])
print("  Strength:", sig["signal_strength"])
print("  Confidence:", sig["confidence_score"])
print("  Reasoning:", sig["reasoning"])

# --- Agent 2 ---
print()
print("=" * 50)
print("AGENT 2: ExitOptimizerAgent")
print("=" * 50)
exit_agent = ExitOptimizerAgent(provider, min_confidence=0.55, check_interval_bars=1)
ex = exit_agent.optimize(open_trade, candles, session="LONDON", force_check=True)
print("  Action:", ex["action"])
print("  Confidence:", ex["confidence"])
print("  New TP:", ex["new_tp"])
print("  New SL:", ex["new_sl"])
print("  Reasoning:", ex["reasoning"])

# --- Agent 3 ---
print()
print("=" * 50)
print("AGENT 3: RiskAdapterAgent")
print("=" * 50)
risk_agent = RiskAdapterAgent(provider, base_risk_pct=2.0)
rk = risk_agent.calculate(
    candles, current_capital=10000,
    confluence_score=0.6, current_drawdown=2.5,
    session="LONDON", mins_to_news=120
)
print("  Safe to trade:", rk["is_safe_to_trade"])
print("  Recommended risk:", rk["recommended_risk_pct"], "%")
print("  Market condition:", rk["market_condition"])
print("  Risk level:", rk["risk_level"])
print("  Reasoning:", rk["reasoning"])
