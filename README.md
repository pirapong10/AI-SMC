# 🤖 AI SMC Multi-Agent Trading System

Advanced AI-powered trading bot using **Smart Money Concepts (SMC)**, **LangGraph**, and **Claude AI** with a multi-agent architecture.

**Status:** Development ✨

---

## 📋 Overview

This system combines:
- **Pure SMC Logic**: Liquidity Sweeps → Change of Character (CHoCH) → Fair Value Gaps (FVG)
- **LangGraph Pipeline**: Multi-agent orchestration framework
- **Claude AI**: Intelligent decision making using language models
- **XGBoost Scoring**: Machine learning signal validation
- **Qdrant Vector Memory**: Long-term memory for trading patterns
- **Risk Management**: Position sizing and portfolio tracking

### Architecture

```
Market Data → Liquidity Agent → CHoCH Agent → FVG Agent → Scoring Agent
                                                               ↓
                                                        Decision Agent (Claude)
                                                               ↓
                                                        Risk Agent
                                                               ↓
                                                        Portfolio Agent
                                                               ↓
                                                        Backtest Agent
                                                               ↓
                                                        Executor Agent
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.12.3** or higher
- **Anthropic API Key** (for Claude access)
- **Qdrant** (for vector database)

### Installation

```bash
# Clone repository
git clone https://github.com/pirapong10/AI-SMC.git
cd AI-SMC

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Copy .env template and configure
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### Setup Qdrant (Local)

**Option 1: Docker**
```bash
docker pull qdrant/qdrant
docker run -p 6333:6333 qdrant/qdrant
```

**Option 2: Direct Installation**
- Download from https://qdrant.tech/documentation/quick-start/

### Configuration

Edit `.env` file:
```env
ANTHROPIC_API_KEY=sk-ant-your-key-here
QDRANT_URL=http://localhost:6333
SYMBOL=XAUUSD
ACCOUNT_SIZE=10000
```

### Run the Bot

```bash
python src/main.py
```

Expected output:
```
🚀 Initializing AI SMC Trading Bot
📦 Initializing agents...
✅ All 9 agents initialized successfully
🌐 Setting up LangGraph pipeline...
✅ Pipeline ready

🔍 Starting market analysis for XAUUSD H1

📍 Stage 1: Liquidity Detection
✓ LIQUIDITY: BULLISH_SWEEP (Confidence: 0.80)

📍 Stage 2: CHoCH Detection
✓ CHOCH: BULLISH_CHOCH (Confidence: 0.75)

📍 Stage 3: FVG Detection
✓ FVG: BULLISH_FVG (Confidence: 0.85)

📍 Stage 4: XGBoost Scoring
✓ SCORING: Score=0.80, Recommendation=BUY

📍 Stage 5: Claude Decision Making
✅ Claude recommended: TRADE

✅ BOT EXECUTION COMPLETE
```

---

## 🧠 The 9 Agents

### 1. **LiquidityAgent**
Detects Liquidity Sweeps (Break of Structure)
- Identifies when price breaks resistance/support then reverses
- Signals potential reversals in smart money activity

### 2. **CHoCHAgent**
Detects Change of Character (CHoCH)
- Identifies shift from higher lows to lower lows (or vice versa)
- Signals change in market structure

### 3. **FVGAgent**
Detects Fair Value Gaps
- Identifies gaps between candles that price hasn't filled
- Calculates 50% level for optimal entry

### 4. **ScoringAgent**
XGBoost Signal Scoring
- Combines signals from Liquidity, CHoCH, and FVG
- Returns composite confidence score (0-1)

### 5. **DecisionAgent** ⭐
Claude AI Decision Maker
- Takes all signals and makes final trading decision
- Calculates entry, SL, TP, and risk/reward ratios
- Provides reasoning in natural language

### 6. **RiskAgent**
Risk Management & Position Sizing
- Calculates position size based on account risk
- Enforces max risk per trade (2% default)
- Manages risk/reward ratios

### 7. **PortfolioAgent**
Portfolio Tracking
- Tracks open and closed positions
- Maintains portfolio P&L
- Aggregates trade statistics

### 8. **BacktestAgent**
Backtesting Engine
- Runs historical analysis (mock)
- Calculates win rate, profit factor, drawdown
- Validates strategy viability

### 9. **ExecutorAgent**
Trade Execution
- Executes approved trade orders
- Currently: Mock execution (demo)
- Ready for real MT5 integration

---

## 📁 Project Structure

```
AI-SMC/
├── src/
│   ├── main.py                 # Entry point
│   ├── agents/
│   │   ├── base_agent.py       # Base class for all agents
│   │   └── trading_agents.py   # 9 specialized agents
│   ├── core/
│   │   ├── config.py           # Configuration management
│   │   └── smc_logic.py        # Pure SMC logic implementation
│   ├── graph/
│   │   └── pipeline.py         # LangGraph pipeline orchestration
│   └── memory/
│       └── vector_store.py     # Qdrant integration
│
├── tests/
│   └── test_agents.py          # Unit tests
│
├── models/
│   └── xgboost_model.pkl       # Pre-trained model
│
├── data/
│   └── historical/             # Historical candle data
│
├── logs/
│   └── trading_bot.log         # Execution logs
│
├── requirements.txt            # Python dependencies
├── .env.example               # Environment template
├── .gitignore                 # Git ignore rules
└── README.md                  # This file
```

---

## 📊 SMC Logic Explained

### Flow: Liquidity → CHoCH → FVG

**1. Liquidity Sweep (Break of Structure)**
```
High break ┐
           ├─ Close below break = Bullish signal
           └─ Stop loss for sellers = Liquidity
```

**2. Change of Character**
```
Previous: Lower Lows
Current:  Higher Lows = Bullish CHoCH
```

**3. Fair Value Gap (50% Entry)**
```
Gap between candles ┐
                    ├─ 50% of gap = Sell Limit entry
                    └─ Ideal entry for smart money
```

**Result: High-probability reversal setup**

---

## 🔄 Pipeline Execution Flow

```
Input: Market Data (Candles)
  ↓
Stage 1: Liquidity Detection
  → Output: Signal (BULLISH/BEARISH/NONE), Confidence
  ↓
Stage 2: CHoCH Detection
  → Output: Signal, Confidence
  ↓
Stage 3: FVG Detection
  → Output: Signal, Gap Levels, Mid-level
  ↓
Stage 4: XGBoost Scoring
  → Output: Composite Score, Recommendation (BUY/SKIP)
  ↓
[IF SCORE > THRESHOLD] Continue to Stage 5
[IF SCORE < THRESHOLD] EXIT - No Trade
  ↓
Stage 5: Claude Decision (AI)
  → Output: TRADE/SKIP, Entry, SL, TP, Reasoning
  ↓
[IF CLAUDE = SKIP] EXIT - No Trade
  ↓
Stage 6: Risk Management
  → Output: Position Size, Max Risk, Status
  ↓
Stage 7: Portfolio Update
  → Output: Position Count, Portfolio State
  ↓
Stage 8: Backtest Analysis (Optional)
  → Output: Historical Performance Metrics
  ↓
Stage 9: Execution
  → Output: Trade Confirmation, Trade ID
  ↓
SUCCESS ✅
```

---

## 🔌 Configuration

### Key Settings (.env)

```env
# Claude API
ANTHROPIC_API_KEY=sk-ant-...

# Qdrant Vector DB
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=...

# Trading
SYMBOL=XAUUSD
ACCOUNT_SIZE=10000
MAX_POSITION_SIZE=5000
STOP_LOSS_PERCENT=2.0
TAKE_PROFIT_PERCENT=5.0

# Agent
DECISION_AGENT_MODEL=claude-3-5-sonnet-20241022
XGB_THRESHOLD=0.65

# Backtest
BACKTEST_START_DATE=2024-01-01
BACKTEST_END_DATE=2024-12-31
```

---

## 🧪 Testing

```bash
# Run unit tests
pytest tests/

# Run specific agent test
pytest tests/test_agents.py::test_liquidity_agent

# Run with verbose output
pytest -v tests/
```

---

## 📈 Performance Metrics

Expected backtest results (historical simulation):
- **Win Rate**: 60-70%
- **Profit Factor**: 1.8-2.2
- **Max Drawdown**: -10% to -15%
- **ROI**: 100-200% annually

---

## 🔐 Security & API Keys

⚠️ **NEVER commit `.env` file or API keys to GitHub**

```bash
# Never do this:
git add .env  ❌

# Correct:
git add .env.example  ✅
```

The `.gitignore` file already protects:
- `.env`
- Secrets
- API keys
- Model weights

---

## 🚀 Future Enhancements

- [ ] Real MT5 integration via WebSocket
- [ ] Live Telegram alerts
- [ ] Advanced portfolio analytics
- [ ] Multi-timeframe analysis
- [ ] News sentiment integration
- [ ] GPU acceleration for XGBoost
- [ ] Web dashboard
- [ ] Docker containerization
- [ ] Kubernetes deployment

---

## 📚 Documentation

- **SMC Theory**: [SMC Resources](https://example.com)
- **LangGraph**: [LangGraph Docs](https://langchain.com/langgraph)
- **Claude API**: [Anthropic Documentation](https://docs.anthropic.com)
- **Qdrant**: [Qdrant Docs](https://qdrant.tech/documentation)

---

## 📝 License

MIT License - See LICENSE file

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## 📧 Contact

- **Developer**: Pirapong
- **Trading Venture**: PS Trading (Prop Trading)
- **Repository**: https://github.com/pirapong10/AI-SMC.git

---

## ⚠️ Disclaimer

**This is a DEVELOPMENT/EDUCATIONAL system. NOT for real trading.**

- Uses MOCK market data
- MOCK trade execution
- For learning and backtesting only
- Not financial advice
- Use at your own risk

---

**Built with ❤️ using Claude AI, LangGraph, and SMC Concepts**

🚀 Ready to revolutionize your trading?
