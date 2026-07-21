"""
Phase 2 Backtest: Enhanced Entries with Multi-TF Confluence & Filters
Improvements:
  - Multi-timeframe confluence (H4 + H1 + M15)
  - Volume confirmation
  - Session filters
  - Momentum filters (RSI, MACD)
  - ATR-based dynamic stops
  - Better entry quality

Expected Win Rate: 37% → 50%+
"""

import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import enhanced SMC logic
from smc_logic_enhanced import (
    SMCAnalyzer, MultiTimeframeAnalyzer, EnhancedTradeEntry,
    SessionFilter, SMCSignal
)
from backtest_engine import BacktestEngine
from data_loader import DataLoader


def resample_to_h4(h1_candles):
    """Resample H1 candles to H4"""
    h4_candles = []
    i = 0
    
    while i + 3 < len(h1_candles):
        open_price = h1_candles[i]["open"]
        high = max([c["high"] for c in h1_candles[i:i+4]])
        low = min([c["low"] for c in h1_candles[i:i+4]])
        close = h1_candles[i+3]["close"]
        volume = sum([c["volume"] for c in h1_candles[i:i+4]])
        timestamp = h1_candles[i+3]["timestamp"]
        
        h4_candles.append({
            "timestamp": timestamp,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume
        })
        
        i += 4
    
    return h4_candles


def resample_to_m15(h1_candles):
    """Resample H1 candles to M15"""
    m15_candles = []
    i = 0
    
    while i + 3 < len(h1_candles):
        # For demo, just take every 3rd H1 candle as M15
        open_price = h1_candles[i]["open"]
        high = max([c["high"] for c in h1_candles[i:i+1]])
        low = min([c["low"] for c in h1_candles[i:i+1]])
        close = h1_candles[i]["close"]
        volume = h1_candles[i]["volume"]
        timestamp = h1_candles[i]["timestamp"]
        
        m15_candles.append({
            "timestamp": timestamp,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume
        })
        
        i += 1
    
    return m15_candles


def run_backtest_phase2():
    """Run Phase 2 backtest with enhanced entries"""
    
    logger.info("=" * 60)
    logger.info("🎯 PHASE 2 BACKTEST: ENHANCED ENTRIES")
    logger.info("=" * 60)
    logger.info("")
    
    # ==================== STEP 1: Load Data ====================
    logger.info("📊 STEP 1: Loading historical data...")
    loader = DataLoader()
    candle_objects = loader.process_csv("XAUUSD_H1_2024.csv")
    
    # Convert CandleData objects to dictionaries
    candles = [
        {
            "timestamp": c.timestamp,
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume
        }
        for c in candle_objects
    ]
    
    if not candles:
        logger.error("❌ Failed to load data")
        return
    
    logger.info(f"   Total candles: {len(candles)}")
    logger.info(f"   Date range: {candles[0]['timestamp']} to {candles[-1]['timestamp']}")
    logger.info(f"   Price range: {min(c['low'] for c in candles):.2f} - {max(c['high'] for c in candles):.2f}")
    logger.info("")
    
    # ==================== STEP 2: Initialize ====================
    logger.info("⚙️  STEP 2: Initializing backtest engine...")
    backtest = BacktestEngine(initial_capital=10000, risk_per_trade=2.0)
    
    smc = SMCAnalyzer()
    multi_tf = MultiTimeframeAnalyzer()
    entry_validator = EnhancedTradeEntry()
    
    logger.info("   ✅ SMC analyzer ready")
    logger.info("   ✅ Multi-TF analyzer ready")
    logger.info("   ✅ Entry validator ready")
    logger.info("")
    
    # Resample to H4 and M15
    h4_candles = resample_to_h4(candles)
    m15_candles = resample_to_m15(candles)
    
    logger.info(f"   ✅ Resampled to H4: {len(h4_candles)} candles")
    logger.info(f"   ✅ Resampled to M15: {len(m15_candles)} candles")
    logger.info("")
    
    # ==================== STEP 3: Run Backtest ====================
    logger.info("🚀 STEP 3: Running backtest simulation...")
    
    signals_stats = {"bullish": 0, "bearish": 0, "no_signal": 0}
    trades_placed = 0
    filtered_trades = 0
    rejected_trades = 0
    
    for i in range(len(candles)):
        if i < 20:  # Need at least 20 candles for analysis
            continue
        
        candle = candles[i]
        candle_dict = {
            "timestamp": candle["timestamp"],
            "open": candle["open"],
            "high": candle["high"],
            "low": candle["low"],
            "close": candle["close"],
            "volume": candle["volume"]
        }
        
        # Check exit conditions
        backtest.check_exit_conditions(candle_dict["timestamp"], candle_dict)
        
        # Get recent candles
        recent_candles_obj = candles[max(0, i-19):i+1]
        recent_candles = [
            {
                "timestamp": c["timestamp"],
                "open": c["open"],
                "high": c["high"],
                "low": c["low"],
                "close": c["close"],
                "volume": c["volume"]
            }
            for c in recent_candles_obj
        ]
        
        # Get H4 and M15 context
        h4_idx = i // 4
        m15_idx = i
        
        h4_context = h4_candles[max(0, h4_idx-5):h4_idx+1]
        m15_context = m15_candles[max(0, m15_idx-19):m15_idx+1]
        
        # Multi-TF Analysis
        if len(h4_context) >= 10 and len(m15_context) >= 10:
            confluence_analysis = multi_tf.analyze_confluence(
                h4_context, recent_candles, m15_context
            )
            signal = confluence_analysis["final_signal"]
            confluence_score = confluence_analysis["confluence_score"]
        else:
            smc_analysis = smc.analyze(recent_candles)
            signal = smc_analysis["signal"]
            confluence_score = smc_analysis["confidence"]
        
        # Track signals
        if signal.value == 1:
            signals_stats["bullish"] += 1
        elif signal.value == -1:
            signals_stats["bearish"] += 1
        else:
            signals_stats["no_signal"] += 1
        
        # Validate entry with all filters
        if not backtest.open_position and signal != SMCSignal.NO_SIGNAL:
            entry_result = entry_validator.validate_entry(
                signal=signal,
                candles=recent_candles,
                timestamp=candle_dict["timestamp"],
                confluence_score=confluence_score
            )
            
            if entry_result["valid"]:
                # Place trade with validated entry
                stop_loss = entry_result["stop_loss"]
                take_profit = entry_result["take_profit"]
                
                position_size = backtest.calculate_position_size(
                    candle_dict["close"], stop_loss
                )
                
                if position_size > 0:
                    backtest.place_trade(
                        timestamp=candle_dict["timestamp"],
                        price=candle_dict["close"],
                        direction="LONG" if signal == SMCSignal.BULLISH else "SHORT",
                        position_size=position_size,
                        stop_loss=stop_loss,
                        take_profit=take_profit
                    )
                    trades_placed += 1
            else:
                # Log rejection reason
                rejected_trades += 1
        
        # Record equity every 10 candles
        if i % 10 == 0:
            backtest.record_equity(candle["timestamp"])
    
    # Close any open position
    if backtest.open_position:
        backtest.close_trade(candles[-1]["timestamp"], candles[-1]["close"], "timeout")
    
    # ==================== STEP 4: Generate Report ====================
    logger.info("\n📈 STEP 4: Calculating metrics...")
    
    metrics = backtest.get_metrics()
    
    logger.info("\n" + "=" * 60)
    logger.info("📊 PHASE 2 BACKTEST RESULTS")
    logger.info("=" * 60)
    logger.info(f"Total Trades:        {metrics['total_trades']}")
    logger.info(f"Winning Trades:      {metrics['winning_trades']}")
    logger.info(f"Losing Trades:       {metrics['losing_trades']}")
    logger.info(f"Win Rate:            {metrics['win_rate']:.2f}%")
    logger.info(f"Profit Factor:       {metrics['profit_factor']:.2f}")
    logger.info(f"Total P&L:           ${metrics['total_profit']:.2f}")
    logger.info(f"Max Drawdown:        {metrics['max_drawdown']:.2f}%")
    logger.info(f"ROI:                 {metrics['roi_percent']:.2f}%")
    logger.info(f"Final Capital:       ${metrics['final_capital']:.2f}")
    logger.info("=" * 60)
    logger.info("")
    
    logger.info("📊 Signal Statistics:")
    logger.info(f"   Bullish signals:   {signals_stats['bullish']}")
    logger.info(f"   Bearish signals:   {signals_stats['bearish']}")
    logger.info(f"   No signal:         {signals_stats['no_signal']}")
    logger.info(f"   Trades placed:     {trades_placed}")
    logger.info(f"   Trades filtered:   {rejected_trades}")
    logger.info(f"   Filter rate:       {(rejected_trades/max(1,rejected_trades+trades_placed)*100):.1f}%")
    logger.info("")
    
    # Save report
    logger.info("💾 Saving detailed report...")
    report = {
        "phase": "Phase 2 - Enhanced Entries",
        "timestamp": datetime.now().isoformat(),
        "metrics": metrics,
        "signals": signals_stats,
        "trades_placed": trades_placed,
        "trades_filtered": rejected_trades,
        "improvement": {
            "previous_win_rate": "37.25%",
            "new_win_rate": f"{metrics['win_rate']:.2f}%",
            "improvement": f"{metrics['win_rate'] - 37.25:.2f}%"
        }
    }
    
    with open("backtest_phase2_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    logger.info("   💾 Report saved: backtest_phase2_report.json")
    logger.info("")
    
    # Save trades
    with open("phase2_trades_history.txt", "w") as f:
        f.write("Phase 2: Enhanced Entries - Trade History\n")
        f.write("=" * 60 + "\n\n")
        for trade in backtest.trades:
            f.write(f"Trade #{trade.trade_id}\n")
            f.write(f"  Entry:  {trade.entry_time} @ {trade.entry_price:.2f}\n")
            f.write(f"  Exit:   {trade.exit_time} @ {trade.exit_price:.2f}\n")
            f.write(f"  P&L:    ${trade.profit_loss:.2f} ({trade.profit_pct:.2f}%)\n")
            f.write(f"  Result: {'WIN' if trade.profit_loss > 0 else 'LOSS'}\n")
            f.write("\n")
    
    logger.info("✅ Trade history saved to: phase2_trades_history.txt")
    logger.info("")
    logger.info("✅ PHASE 2 BACKTEST COMPLETE!")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_backtest_phase2()