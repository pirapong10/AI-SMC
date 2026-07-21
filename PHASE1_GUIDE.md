# 📊 Phase 1: Data & Backtest - Integration Guide

## ✅ Files Created

```
backtest.py              ← Main backtest runner
data_loader.py          ← Load CSV and resample data
backtest_engine.py      ← Simulation engine
```

## 🚀 Quick Start

### **Step 1: Prepare Your Data**

Export XAUUSD H1 data from MT5:

```
Terminal → Right-click XAUUSD → Export data
Date Range: 2023-01-01 to 2024-12-31
Timeframe: H1
Save as: D:\Project\AI-SMC\data\XAUUSD_H1_2024.csv
```

**File should be in:**
```
D:\Project\AI-SMC\
└── data\
    └── XAUUSD_H1_2024.csv
```

### **Step 2: Run Backtest**

```bash
# Activate venv
venv\Scripts\activate

# Run backtest
python backtest.py --data XAUUSD_H1_2024.csv --start 2024-01-01 --end 2024-12-31 --capital 10000
```

**Arguments:**
- `--data`: CSV filename
- `--start`: Start date (optional)
- `--end`: End date (optional)
- `--capital`: Initial capital (default: 10000)

### **Step 3: View Results**

Output files:
```
backtest_report.json    ← Detailed metrics (JSON)
trades_history.txt      ← All trades list
Console output          ← Summary report
```

---

## 📊 Expected Output

```
============================================================
🎯 BACKTEST STARTING
============================================================

📊 STEP 1: Loading historical data...
   Total candles: 4520
   Date range: 2024-01-01 to 2024-12-31
   Price range: 2000.50 - 2100.75

⚙️  STEP 2: Initializing backtest engine...
   ✅ SMC analyzer ready

🚀 STEP 3: Running backtest simulation...

📈 STEP 4: Calculating metrics...
============================================================
📊 BACKTEST RESULTS
============================================================
Total Trades:        45
Winning Trades:      31
Losing Trades:       14
Win Rate:            68.89%
Profit Factor:       2.15
Total P&L:           $5,234.50
Max Drawdown:        -12.50%
ROI:                 52.35%
Final Capital:       $15,234.50
============================================================

💾 Saving detailed report...
✅ Trade history saved to: trades_history.txt

✅ BACKTEST COMPLETE!
```

---

## 📈 Understanding Metrics

| Metric | What it means | Good value |
|--------|---------------|-----------|
| **Win Rate** | % of profitable trades | > 55% |
| **Profit Factor** | Total wins / Total losses | > 1.5 |
| **Max Drawdown** | Largest loss from peak | < -20% |
| **ROI** | Return on investment | > 30% per year |
| **Total P&L** | Profit/Loss in dollars | > 0 |

---

## 🔍 Backtest Report (JSON)

`backtest_report.json` contains:

```json
{
  "metrics": {
    "total_trades": 45,
    "winning_trades": 31,
    "losing_trades": 14,
    "win_rate": 68.89,
    "profit_factor": 2.15,
    "total_profit": 5234.50,
    "max_drawdown": -12.50,
    "roi_percent": 52.35,
    "final_capital": 15234.50
  },
  "trades": [
    {
      "trade_id": 1,
      "entry_time": "2024-01-15T10:00:00",
      "entry_price": 2050.50,
      "direction": "LONG",
      "stop_loss": 2049.50,
      "take_profit": 2055.50,
      "exit_time": "2024-01-15T14:30:00",
      "exit_price": 2055.50,
      "exit_reason": "TP",
      "profit_loss": 50.00,
      "profit_pct": 0.24
    },
    ...
  ]
}
```

---

## 🧪 Test Data Issues

### ❌ "File not found: XAUUSD_H1_2024.csv"

**Solution:**
1. Create `data/` folder in project root
2. Export CSV from MT5
3. Place in `data/` folder

### ❌ "No trades generated"

**Reasons:**
- Data too short (need minimum 50+ candles)
- No strong SMC patterns in data
- Thresholds too high (adjust confidence)

**Fix:**
```python
# In backtest.py, line ~87, lower confidence threshold:
if not backtest.open_position and signal.value == 1 and confidence > 0.50:  # Was 0.70
```

### ❌ "CSV format error"

**Expected columns:**
```
Date,Time,Open,High,Low,Close,Volume
2024-01-01,00:00,2050.50,2052.30,2049.80,2051.20,1000
```

**Or MT5 format:**
```
<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<VOLUME>
```

---

## 💡 Advanced Options

### **Resample to Different Timeframe**

```python
# In Python console
from data_loader import DataLoader

loader = DataLoader()
candles_h1 = loader.process_csv("XAUUSD_H1_2024.csv")
candles_h4 = loader.resample_timeframe(candles_h1, "H1", "H4")
```

### **Filter Specific Date Range**

```bash
python backtest.py --data XAUUSD_H1_2024.csv --start 2024-06-01 --end 2024-06-30
```

### **Test Different Capital**

```bash
python backtest.py --data XAUUSD_H1_2024.csv --capital 50000
```

---

## 📋 Checklist

- [ ] MT5 data exported to `data/XAUUSD_H1_2024.csv`
- [ ] Files copied: `backtest.py`, `data_loader.py`, `backtest_engine.py`
- [ ] Run: `python backtest.py`
- [ ] Review: `backtest_report.json` and `trades_history.txt`
- [ ] Document findings

---

## 🎯 Next Steps After Backtest

1. **Review Results**
   - Analyze win rate, drawdown, ROI
   - Identify weak periods

2. **Optimize (Phase 2)**
   - Adjust SMC parameters
   - Fine-tune entry/exit logic
   - Improve signal filtering

3. **Paper Trade (Phase 3)**
   - Connect to MT5
   - Test real-time signals
   - Monitor for issues

---

## ❓ Troubleshooting

| Problem | Solution |
|---------|----------|
| Import errors | `pip install -r requirements.txt` |
| Data not found | Check `data/` folder path |
| No trades | Lower confidence threshold or get better data |
| Out of memory | Filter date range with `--start` `--end` |
| Slow backtest | Reduce candle count or increase timeframe |

---

## 📞 Support

Check logs in console output for detailed error messages.

**Good luck with Phase 1! 🚀**
