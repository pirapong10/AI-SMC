"""
Backtest Runner
Integrate data loader + trading pipeline + backtest engine
Run full backtest on historical data
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_backtest(data_filename: str, start_date: str = None, end_date: str = None,
                initial_capital: float = 10000):
    """
    Run full backtest on historical data
    
    Args:
        data_filename: MT5 CSV export filename
        start_date: Start date filter (YYYY-MM-DD)
        end_date: End date filter (YYYY-MM-DD)
        initial_capital: Starting capital
    """
    
    try:
        # Import modules
        from data_loader import DataLoader
        from backtest_engine import BacktestEngine
        from smc_logic import SMCAnalyzer
        
        logger.info("="*60)
        logger.info("🎯 BACKTEST STARTING")
        logger.info("="*60)
        
        # ==================== STEP 1: Load Data ====================
        logger.info("\n📊 STEP 1: Loading historical data...")
        
        loader = DataLoader(data_dir="./data")
        candles = loader.process_csv(data_filename)
        
        # Get stats
        stats = loader.get_stats(candles)
        logger.info(f"   Total candles: {stats['total_candles']}")
        logger.info(f"   Date range: {stats['start_date']} to {stats['end_date']}")
        logger.info(f"   Price range: {stats['min_price']:.2f} - {stats['max_price']:.2f}")
        
        # Filter by date if specified
        if start_date and end_date:
            candles = loader.filter_by_date(candles, start_date, end_date)
            logger.info(f"   Filtered to: {start_date} to {end_date}")
        
        # ==================== STEP 2: Initialize Engine ====================
        logger.info("\n⚙️  STEP 2: Initializing backtest engine...")
        
        backtest = BacktestEngine(
            initial_capital=initial_capital,
            risk_per_trade=2.0,
            max_position_size=5000
        )
        
        # Initialize SMC analyzer
        smc = SMCAnalyzer(lookback=20)
        logger.info("   ✅ SMC analyzer ready")
        
        # ==================== STEP 3: Run Backtest ====================
        logger.info("\n🚀 STEP 3: Running backtest simulation...")
        
        trades_placed = 0
        signals = {
            "bullish": 0,
            "bearish": 0,
            "no_signal": 0
        }
        
        # Process each candle
        for i, candle in enumerate(candles):
            # Convert CandleData to dict
            candle_dict = {
                "timestamp": candle.timestamp,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume
            }
            
            # Check if current position should be closed (TP/SL)
            backtest.check_exit_conditions(candle_dict["timestamp"], candle_dict)
            
            # Need at least 10 candles for SMC analysis
            if i < 10:
                continue
            
            # Get last 20 candles for analysis
            recent_candles_obj = candles[max(0, i-19):i+1]
            
            # Convert CandleData objects to dictionaries for SMC analysis
            recent_candles = [
                {
                    "timestamp": c.timestamp,
                    "open": c.open,
                    "high": c.high,
                    "low": c.low,
                    "close": c.close,
                    "volume": c.volume
                }
                for c in recent_candles_obj
            ]
            
            # Run SMC analysis
            analysis = smc.analyze(recent_candles)
            signal = analysis.get("signal")
            confidence = analysis.get("confidence", 0)
            
            # Track signals
            if signal.value == 1:
                signals["bullish"] += 1
            elif signal.value == -1:
                signals["bearish"] += 1
            else:
                signals["no_signal"] += 1
            
            # Place trade if medium-high confidence bullish signal (lowered from 0.70)
            if not backtest.open_position and signal.value == 1 and confidence > 0.50:
                entry_level = analysis.get("entry_level", candle_dict["close"])
                stop_loss = entry_level - (entry_level * 0.01)  # 1% SL (tighter)
                take_profit = entry_level + (entry_level * 0.03)  # 3% TP
                
                # Calculate position size dynamically based on risk management
                position_size = backtest.calculate_position_size(entry_level, stop_loss)
                
                # Only place trade if position size is valid
                if position_size > 0:
                    backtest.place_trade(
                        timestamp=candle_dict["timestamp"],
                        price=entry_level,
                        direction="LONG",
                        position_size=position_size,
                        stop_loss=stop_loss,
                        take_profit=take_profit
                    )
                    trades_placed += 1
            
            # Record equity every 10 candles
            if i % 10 == 0:
                backtest.record_equity(candle.timestamp)
        
        # Close any open position
        if backtest.open_position:
            backtest.close_trade(candles[-1].timestamp, candles[-1].close, "timeout")
        
        # ==================== STEP 4: Generate Report ====================
        logger.info("\n📈 STEP 4: Calculating metrics...")
        
        metrics = backtest.get_metrics()
        
        logger.info("\n" + "="*60)
        logger.info("📊 BACKTEST RESULTS")
        logger.info("="*60)
        logger.info(f"Total Trades:        {metrics.get('total_trades', 0)}")
        logger.info(f"Winning Trades:      {metrics.get('winning_trades', 0)}")
        logger.info(f"Losing Trades:       {metrics.get('losing_trades', 0)}")
        logger.info(f"Win Rate:            {metrics.get('win_rate', 0):.2f}%")
        logger.info(f"Profit Factor:       {metrics.get('profit_factor', 0):.2f}")
        logger.info(f"Total P&L:           ${metrics.get('total_profit', 0):.2f}")
        logger.info(f"Max Drawdown:        {metrics.get('max_drawdown', 0):.2f}%")
        logger.info(f"ROI:                 {metrics.get('roi_percent', 0):.2f}%")
        logger.info(f"Final Capital:       ${metrics.get('final_capital', 0):.2f}")
        logger.info("="*60)
        
        logger.info("\n📊 Signal Statistics:")
        logger.info(f"   Bullish signals:   {signals['bullish']}")
        logger.info(f"   Bearish signals:   {signals['bearish']}")
        logger.info(f"   No signal:         {signals['no_signal']}")
        logger.info(f"   Trades placed:     {trades_placed}")
        
        # Save report
        logger.info("\n💾 Saving detailed report...")
        backtest.save_report("backtest_report.json")
        
        # Save trade history
        with open("trades_history.txt", "w") as f:
            f.write("TRADE HISTORY\n")
            f.write("="*60 + "\n\n")
            for trade in backtest.trades:
                f.write(f"Trade #{trade.trade_id}\n")
                f.write(f"  Entry:  {trade.entry_time} @ ${trade.entry_price} ({trade.direction})\n")
                f.write(f"  Exit:   {trade.exit_time} @ ${trade.exit_price} ({trade.exit_reason})\n")
                f.write(f"  P&L:    ${trade.profit_loss:.2f} ({trade.profit_pct:.2f}%)\n\n")
        
        logger.info("✅ Trade history saved to: trades_history.txt")
        
        logger.info("\n✅ BACKTEST COMPLETE!")
        logger.info("="*60)
        
        return metrics
        
    except Exception as e:
        logger.error(f"❌ Backtest error: {e}", exc_info=True)
        return None


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run backtest on historical data")
    parser.add_argument("--data", default="XAUUSD_H1_2024.csv", help="CSV filename")
    parser.add_argument("--start", default=None, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default=None, help="End date (YYYY-MM-DD)")
    parser.add_argument("--capital", type=float, default=10000, help="Initial capital")
    
    args = parser.parse_args()
    
    # Ensure data directory exists
    Path("./data").mkdir(exist_ok=True)
    
    # Run backtest
    metrics = run_backtest(
        data_filename=args.data,
        start_date=args.start,
        end_date=args.end,
        initial_capital=args.capital
    )
    
    return metrics


if __name__ == "__main__":
    main()