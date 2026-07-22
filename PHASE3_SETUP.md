# 🚀 Phase 3: MT5 Integration & Paper Trading - Setup Guide

## Overview

Phase 3 moves from historical backtesting (Phase 1) to **live paper trading** with real MT5 data.

```
Phase 1: Backtest on historical data (2024) ✅ COMPLETE
Phase 2: Enhanced filters (SKIPPED - made it worse)
Phase 3: Paper trading on live MT5 data 🔄 NOW
```

**Key Improvements:**
- ✅ Real-time data from live MT5 terminal
- ✅ Realistic spreads and slippage
- ✅ Phase 1 SMC logic unchanged (proven profitable)
- ✅ Simulated execution (no real money at risk)
- ✅ Live P&L tracking
- ✅ Trade journal and monitoring

---

## Prerequisites

### 1. MetaTrader5 Installation

You need MetaTrader5 installed and running on your machine with:
- ✅ Active MT5 account (demo or live)
- ✅ Connection to broker server
- ✅ XAUUSD symbol available
- ✅ AutoTrading enabled in Options

**How to check:**
1. Open MT5
2. Look for "XAUUSD" in Market Watch
3. Go to Tools → Options → Expert Advisors → Check "Allow Automated Trading"

### 2. Python Dependencies

```bash
cd D:\Project\AI-SMC
venv\Scripts\activate

# Install MT5 library
pip install MetaTrader5==5.0.45

# Install monitoring tools (optional, for dashboard)
pip install streamlit
pip install plotly

# Install alerting (optional, for Telegram)
pip install python-telegram-bot

# Verify installation
python -c "import MetaTrader5; print(MetaTrader5.__version__)"
```

---

## File Structure

```
D:\Project\AI-SMC\
├── phase3_paper_trading.py    ← Main script (START HERE)
├── mt5_connector.py           ← MT5 data feed
├── paper_trading_engine.py    ← Trade simulation
├── smc_logic.py               ← Phase 1 logic (unchanged)
├── backtest_engine.py         ← Shared (from Phase 1)
├── data_loader.py             ← Shared (from Phase 1)
├── config.py                  ← Configuration
│
├── logs/                      ← Trading logs
│   └── phase3_*.log
│
├── data/                      ← Trade history
│   └── paper_trading_journal_phase3.json
│
└── PHASE3_SETUP.md            ← This file
```

---

## Quick Start (5 Minutes)

### Step 1: Verify MT5 Connection

```bash
cd D:\Project\AI-SMC
venv\Scripts\activate

# Test MT5 connection
python mt5_connector.py
```

**Expected output:**
```
============================================================
🔌 MT5 CONNECTION TEST
============================================================

✅ MT5 initialized
📊 Account: Account Name (1234567)
   Company: Company Name
   Balance: $10,000.00
   Equity: $10,000.00

✅ Symbol XAUUSD ready
   Bid: 2543.45
   Ask: 2543.52
   Spread: 0.0700

📊 Fetched 20 H1 candles
📊 Fetched 5 H4 candles

✅ MT5 Connection test complete!
```

**If it fails:**
- ❌ "MT5 initialization failed" → MT5 terminal not running
- ❌ "Symbol XAUUSD not found" → Add symbol to Market Watch
- ❌ "No data for XAUUSD" → Broker doesn't have XAUUSD or no quotes

### Step 2: Run Paper Trading Bot (Test Mode)

```bash
# Start paper trading with 10 iterations
python phase3_paper_trading.py

# Output will show:
# - Connected to MT5 ✅
# - Loading candles ✅
# - Running 10 iterations (5 minutes total with 30s sleep)
# - Executing trades based on SMC signals
# - Saving journal to paper_trading_journal_phase3.json
```

### Step 3: Check Results

```bash
# View trade journal
cat paper_trading_journal_phase3.json

# Or open in Python
import json
with open("paper_trading_journal_phase3.json") as f:
    journal = json.load(f)
    print(f"Trades: {journal['metrics']['total_trades']}")
    print(f"P&L: ${journal['metrics']['total_pnl']:.2f}")
    print(f"Win Rate: {journal['metrics']['win_rate']:.1f}%")
```

---

## Running Phase 3

### Option A: Test Run (Recommended First)

```bash
# Test with 10 iterations, 30-second sleep
python phase3_paper_trading.py

# Time: ~5 minutes
# Risk: None (simulated)
# Purpose: Verify everything works
```

**Expected behavior:**
- Loads H1 and H4 candles
- Detects SMC signals
- Places simulated trades
- Executes on TP/SL
- Saves journal

### Option B: Extended Run (24 Hours)

```bash
# Run continuously for 24 hours (288 iterations × 5 min each)
# Edit: phase3_paper_trading.py line 244
#   max_iterations=None  # Remove to run forever
#   sleep_seconds=300    # 5 minutes between iterations
```

**Expected:**
- ~5 trades per day (typical for XAUUSD H1)
- Real spread simulation
- Realistic P&L
- 24-hour monitoring

### Option C: Production Run (Weeks)

```bash
# Let it run 7+ days to get statistical significance
# Need:
- Stable MT5 connection
- Python running continuously
- Logs and monitoring

# Tips:
- Use screen/tmux to run in background
- Monitor logs for errors
- Save daily journals
```

---

## Understanding the Output

### Trade Log Entry

```
📈 Trade #1 opened: LONG 10.50 units @ 2543.52
   Entry (Bid/Ask): 2543.45/2543.52
   SL: 2536.20 (7.32), TP: 2557.18 (14.64)
   R:R: 1:2.00, Risk: $200.00

📉 Trade #1 closed: ✅ WIN P&L: $200.00 (0.50%) [TP_HIT]
```

**Meaning:**
- LONG 10.50 units: Buying 10.50 ounces of gold
- Entry 2543.52: Price we entered at (ask price + slippage)
- SL 2536.20: Stop loss 7.32 points away
- TP 2557.18: Take profit 14.64 points away
- R:R 1:2.00: Risk 1, profit potential 2
- Risk $200: If SL hit, lose $200
- P&L +$200: Made $200 profit when TP hit

### Metrics

```
📊 PAPER TRADING SUMMARY
============================================================
Total Trades:      15
Winning:           6
Losing:            9
Win Rate:          40.00%
Profit Factor:     1.45
Total P&L:         $287.50
Max Drawdown:      8.50%
ROI:               2.88%
Final Capital:     $10,287.50
============================================================
```

---

## Monitoring & Alerts (Optional)

### Telegram Alerts

```bash
# 1. Create Telegram bot
#    - Message @BotFather on Telegram
#    - Create bot, get TOKEN

# 2. Get your chat ID
#    - Message your bot anything
#    - curl https://api.telegram.org/botTOKEN/getUpdates

# 3. Add to phase3_paper_trading.py
#    (see alerting section)

# Now you'll get alerts when:
# - Trade entry
# - Trade exit
# - Drawdown warning
# - Daily summary
```

### Streamlit Dashboard

```bash
# 1. Create dashboard.py
pip install streamlit

# 2. Run dashboard
streamlit run dashboard_phase3.py

# 3. Access at http://localhost:8501
# Shows:
# - Equity curve
# - Active trades
# - Trade history
# - P&L breakdown
```

---

## Troubleshooting

### "MT5 initialization failed"

**Problem:** MT5 terminal not running

**Solution:**
```bash
# 1. Open MetaTrader5
# 2. Wait 5 seconds for connection
# 3. Try script again
```

### "Symbol XAUUSD not found"

**Problem:** Broker doesn't have XAUUSD

**Solution:**
```bash
# 1. Check Market Watch in MT5
# 2. If missing, right-click → Show All Symbols
# 3. Search for XAUUSD, click Add
# 4. Close and retry
```

### "No data for XAUUSD"

**Problem:** Broker not streaming quotes

**Solution:**
```bash
# 1. In MT5: Tools → Options → Quotes
# 2. Find XAUUSD, right-click → Show
# 3. Watch for bid/ask to update
# 4. Retry script
```

### "No module named MetaTrader5"

**Problem:** Library not installed

**Solution:**
```bash
pip install MetaTrader5
python -c "import MetaTrader5; print('OK')"
```

### "Position already open"

**Problem:** Script tried to open trade while one is open

**Solution:** This is normal - script rejects overlapping trades
- No risk (safety feature)
- Wait for position to close

---

## Comparison: Phase 1 vs Phase 3

| Aspect | Phase 1 (Backtest) | Phase 3 (Paper Trade) |
|--------|-------------------|----------------------|
| **Data** | Historical CSV | Live MT5 feed |
| **Price** | Close prices only | Real bid/ask |
| **Spread** | Fixed | Real market spread |
| **Slippage** | Ignored | Simulated |
| **Speed** | 1 second per candle | Real-time ticks |
| **Execution** | Instant | Realistic delays |
| **Validation** | Past data | Current market |
| **Risk** | None (history) | None (simulated) |
| **Duration** | 1 month in 1 sec | Real-time continuous |
| **Value** | Concept proof | Real validation |

---

## Next Steps After Phase 3

### If Results Are Good (Win Rate >40%, Profit Factor >1.3)

```
✅ Proceed to Phase 4: Live Trading on Demo Account
   - Use small position sizes
   - Monitor closely for 2 weeks
   - If successful → Live account
```

### If Results Are Poor (Win Rate <35%, Profit Factor <1.0)

```
⚠️ Troubleshooting needed:
   - Review SMC signal quality
   - Check spread impact
   - Adjust stops/targets
   - Consider seasonal data
   - Evaluate market conditions
```

---

## Key Configuration Options

Edit `phase3_paper_trading.py` line 193:

```python
bot = Phase3PaperTradingBot(
    symbol="XAUUSD",              # Change symbol if needed
    initial_capital=10000,         # Starting capital ($)
    risk_per_trade=2.0             # Risk per trade (%)
)

# Change trading loop (line 200):
bot.run_loop(
    max_iterations=10,             # Test: 10, Production: None
    sleep_seconds=30               # Test: 30s, Production: 300s (5min)
)
```

---

## Expected Results

Based on Phase 1 backtest (which should hold up):

```
After 50 trades:
- Win Rate: 35-45%
- Profit Factor: 1.3-1.8
- Drawdown: 5-15%
- ROI: 20-40%

After 100+ trades:
- More statistical confidence
- Patterns become clearer
- Can validate for live trading
```

**Important:** Live market ≠ backtest
- Results may vary from Phase 1
- Real spreads impact profitability
- Market conditions matter

---

## Safety Features Built-in

```python
✅ Prevents overlapping trades
✅ Position size limits
✅ Risk management (2% max per trade)
✅ Realistic spread simulation
✅ Slippage modeling
✅ Automatic journal saves
✅ Equity tracking
✅ Drawdown monitoring
```

---

## Monitoring Checklist

- [ ] MT5 terminal running
- [ ] XAUUSD in Market Watch
- [ ] Demo/live account connected
- [ ] Python venv activated
- [ ] Dependencies installed (pip list)
- [ ] MT5 connection test passes
- [ ] First test run (10 iterations) complete
- [ ] Journal saved successfully
- [ ] Results reviewed

---

## Support & Questions

If you encounter issues:

1. **Check MT5 Connection**
   ```bash
   python mt5_connector.py
   ```

2. **Review Logs**
   ```bash
   tail -f logs/phase3_*.log
   ```

3. **Verify Configuration**
   - Symbol available in MT5
   - Account has sufficient balance
   - AutoTrading enabled
   - Network stable

4. **Test with Minimal Config**
   - Start with 1 iteration
   - Use demo account
   - Check each component separately

---

## Ready to Start?

```bash
cd D:\Project\AI-SMC
venv\Scripts\activate

# 1. Test connection
python mt5_connector.py

# 2. If successful, run paper trading
python phase3_paper_trading.py

# 3. Monitor output
# 4. Check journal when complete
# 5. Analyze results

# Happy trading! 🎯
```

---

**Proceed to Phase 3 now!** 🚀
