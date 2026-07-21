"""
Backtest Engine
Simulate trading strategy on historical data and calculate metrics
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import numpy as np
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Represents a single trade"""
    trade_id: int
    entry_time: str
    entry_price: float
    position_size: float
    direction: str  # LONG or SHORT
    stop_loss: float
    take_profit: float
    exit_time: Optional[str] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None  # TP, SL, timeout
    profit_loss: float = 0.0
    profit_pct: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "entry_time": self.entry_time,
            "entry_price": self.entry_price,
            "position_size": self.position_size,
            "direction": self.direction,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "exit_time": self.exit_time,
            "exit_price": self.exit_price,
            "exit_reason": self.exit_reason,
            "profit_loss": self.profit_loss,
            "profit_pct": self.profit_pct
        }


class BacktestEngine:
    """Backtest trading strategy on historical data"""
    
    def __init__(self, initial_capital: float = 10000, 
                 risk_per_trade: float = 2.0,
                 max_position_size: float = 5000,
                 max_daily_loss: float = 5.0,
                 max_drawdown_limit: float = 20.0):
        """
        Initialize backtest engine
        
        Args:
            initial_capital: Starting capital
            risk_per_trade: Max risk per trade (%)
            max_position_size: Max position size per trade
            max_daily_loss: Max loss allowed per day (%)
            max_drawdown_limit: Max allowed drawdown (%)
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.peak_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.max_position_size = max_position_size
        self.max_daily_loss = max_daily_loss
        self.max_drawdown_limit = max_drawdown_limit
        
        self.trades: List[Trade] = []
        self.open_position: Optional[Trade] = None
        self.equity_curve: List[Tuple[str, float]] = []
        self.trade_id = 0
        self.daily_loss = 0.0
        self.current_day = None
        
        logger.info(f"🎯 Backtest initialized: Capital=${initial_capital}")
        logger.info(f"   Risk/trade: {risk_per_trade}%, Daily loss limit: {max_daily_loss}%, Max drawdown: {max_drawdown_limit}%")
    
    def calculate_position_size(self, entry_price: float, stop_loss: float) -> float:
        """
        Calculate position size based on risk management rules
        
        Position size = (Capital × Risk%) / (Entry - SL in pips)
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
        
        Returns:
            Position size (number of units/lots)
        """
        risk_amount = self.current_capital * (self.risk_per_trade / 100)
        price_distance = abs(entry_price - stop_loss)
        
        if price_distance <= 0:
            return 0
        
        # Calculate position size (units, not dollars)
        # For XAUUSD: 1 unit = 1 ounce of gold
        position_size = risk_amount / price_distance
        
        # Cap at maximum
        if position_size > self.max_position_size:
            position_size = self.max_position_size
        
        return position_size
    
    def place_trade(self, timestamp: str, price: float, direction: str,
                   position_size: float, stop_loss: float, 
                   take_profit: float) -> Trade:
        """
        Open a new trade with proper position sizing
        
        Args:
            timestamp: Entry timestamp
            price: Entry price
            direction: LONG or SHORT
            position_size: Size of position (units/lots)
            stop_loss: Stop loss price
            take_profit: Take profit price
        
        Returns:
            Trade object
        """
        if self.open_position:
            logger.warning("⚠️ Position already open, closing it first")
            self.close_trade(timestamp, price, "forced")
        
        # Auto-calculate position size if not provided
        if position_size <= 0:
            position_size = self.calculate_position_size(price, stop_loss)
        
        # Validate position size
        if position_size > self.max_position_size:
            position_size = self.max_position_size
            logger.info(f"⚠️ Position size capped at {position_size} units")
        
        # Validate SL and TP
        if direction == "LONG":
            if stop_loss >= price:
                logger.warning(f"⚠️ Invalid SL for LONG: SL {stop_loss} >= Entry {price}")
                return None
            if take_profit <= price:
                logger.warning(f"⚠️ Invalid TP for LONG: TP {take_profit} <= Entry {price}")
                return None
        else:  # SHORT
            if stop_loss <= price:
                logger.warning(f"⚠️ Invalid SL for SHORT: SL {stop_loss} <= Entry {price}")
                return None
            if take_profit >= price:
                logger.warning(f"⚠️ Invalid TP for SHORT: TP {take_profit} >= Entry {price}")
                return None
        
        self.trade_id += 1
        trade = Trade(
            trade_id=self.trade_id,
            entry_time=timestamp,
            entry_price=price,
            position_size=position_size,
            direction=direction,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        self.open_position = trade
        sl_distance = abs(price - stop_loss)
        tp_distance = abs(take_profit - price)
        risk_reward = tp_distance / sl_distance if sl_distance > 0 else 0
        
        logger.info(f"📈 Trade #{trade.trade_id} opened: {direction} {position_size:.2f} units @ {price}")
        logger.info(f"   SL: {stop_loss} ({sl_distance:.2f}), TP: {take_profit} ({tp_distance:.2f})")
        logger.info(f"   R:R ratio: 1:{risk_reward:.2f}, Capital at risk: ${risk_reward * (self.current_capital * (self.risk_per_trade / 100)):.2f}")
        return trade
    
    def close_trade(self, timestamp: str, exit_price: float, 
                   exit_reason: str = "signal") -> Optional[Trade]:
        """
        Close open position
        
        Args:
            timestamp: Exit timestamp
            exit_price: Exit price
            exit_reason: Reason for exit (TP, SL, signal, timeout)
        
        Returns:
            Closed Trade object or None
        """
        if not self.open_position:
            return None
        
        trade = self.open_position
        trade.exit_time = timestamp
        trade.exit_price = exit_price
        trade.exit_reason = exit_reason
        
        # Calculate P&L
        if trade.direction == "LONG":
            trade.profit_loss = (exit_price - trade.entry_price) * trade.position_size
            trade.profit_pct = ((exit_price - trade.entry_price) / trade.entry_price) * 100
        else:  # SHORT
            trade.profit_loss = (trade.entry_price - exit_price) * trade.position_size
            trade.profit_pct = ((trade.entry_price - exit_price) / trade.entry_price) * 100
        
        # Update capital
        self.current_capital += trade.profit_loss
        
        # Record trade
        self.trades.append(trade)
        self.open_position = None
        
        # Log
        status = "✅ WIN" if trade.profit_loss > 0 else "❌ LOSS"
        logger.info(f"📉 Trade #{trade.trade_id} closed: {status} P&L: ${trade.profit_loss:.2f} ({trade.profit_pct:.2f}%)")
        
        return trade
    
    def check_exit_conditions(self, timestamp: str, candle: Dict[str, float]) -> bool:
        """
        Check if open position should be closed (TP, SL hit)
        
        Args:
            timestamp: Current timestamp
            candle: Current candle data
        
        Returns:
            True if position was closed
        """
        if not self.open_position:
            return False
        
        trade = self.open_position
        high = candle['high']
        low = candle['low']
        close = candle['close']
        
        # Check TP (Take Profit)
        if trade.direction == "LONG" and high >= trade.take_profit:
            self.close_trade(timestamp, trade.take_profit, "TP")
            return True
        
        if trade.direction == "SHORT" and low <= trade.take_profit:
            self.close_trade(timestamp, trade.take_profit, "TP")
            return True
        
        # Check SL (Stop Loss)
        if trade.direction == "LONG" and low <= trade.stop_loss:
            self.close_trade(timestamp, trade.stop_loss, "SL")
            return True
        
        if trade.direction == "SHORT" and high >= trade.stop_loss:
            self.close_trade(timestamp, trade.stop_loss, "SL")
            return True
        
        return False
    
    def record_equity(self, timestamp: str):
        """Record current equity level"""
        current_equity = self.current_capital
        
        # Add unrealized P&L if position open
        if self.open_position:
            trade = self.open_position
            # Assume closing at current price (estimate)
            current_equity += trade.profit_loss  # Simplified
        
        self.equity_curve.append((timestamp, current_equity))
    
    def get_metrics(self) -> Dict[str, Any]:
        """Calculate backtest metrics"""
        if not self.trades:
            return {"status": "No trades"}
        
        wins = [t for t in self.trades if t.profit_loss > 0]
        losses = [t for t in self.trades if t.profit_loss < 0]
        
        total_profit = sum(t.profit_loss for t in self.trades)
        total_loss = sum(t.profit_loss for t in losses)
        total_win = sum(t.profit_loss for t in wins)
        
        # Calculate metrics
        win_rate = (len(wins) / len(self.trades)) * 100 if self.trades else 0
        profit_factor = total_win / abs(total_loss) if total_loss != 0 else 0
        
        # Calculate max drawdown
        equity_values = [e[1] for e in self.equity_curve]
        peak = equity_values[0]
        max_dd = 0
        for eq in equity_values:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100 if peak > 0 else 0
            max_dd = max(max_dd, dd)
        
        # ROI
        roi = ((self.current_capital - self.initial_capital) / self.initial_capital) * 100
        
        # Avg win/loss
        avg_win = np.mean([t.profit_loss for t in wins]) if wins else 0
        avg_loss = np.mean([t.profit_loss for t in losses]) if losses else 0
        
        return {
            "total_trades": len(self.trades),
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "total_profit": round(total_profit, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "max_drawdown": round(max_dd, 2),
            "roi_percent": round(roi, 2),
            "final_capital": round(self.current_capital, 2),
            "starting_capital": self.initial_capital
        }
    
    def print_report(self):
        """Print backtest report"""
        metrics = self.get_metrics()
        
        print("\n" + "="*60)
        print("📊 BACKTEST REPORT")
        print("="*60)
        
        for key, value in metrics.items():
            print(f"{key.upper():.<40} {value}")
        
        print("="*60)
        
        if self.trades:
            print("\n📋 TRADE HISTORY:")
            print("-"*60)
            for trade in self.trades[:10]:  # First 10 trades
                print(f"Trade #{trade.trade_id}: {trade.direction} @ {trade.entry_price}")
                print(f"  Exit: ${trade.exit_price} | P&L: ${trade.profit_loss:.2f} ({trade.profit_pct:.2f}%)")
            if len(self.trades) > 10:
                print(f"... and {len(self.trades) - 10} more trades")
    
    def save_report(self, filename: str = "backtest_report.json"):
        """Save report to JSON"""
        report = {
            "metrics": self.get_metrics(),
            "trades": [t.to_dict() for t in self.trades],
            "timestamp": datetime.now().isoformat()
        }
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"💾 Report saved: {filename}")


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Create backtest engine
    backtest = BacktestEngine(initial_capital=10000, risk_per_trade=2.0)
    
    # Simulate some trades (example)
    trades_data = [
        {"timestamp": "2024-01-01", "price": 2050, "direction": "LONG", "size": 1000, "sl": 2045, "tp": 2060},
        {"timestamp": "2024-01-02", "price": 2059, "direction": "LONG", "size": 1000, "sl": 2050, "tp": 2070},
        {"timestamp": "2024-01-03", "price": 2048, "direction": "SHORT", "size": 1000, "sl": 2055, "tp": 2040},
    ]
    
    for i, trade_data in enumerate(trades_data):
        backtest.place_trade(**trade_data)
        # Simulate exit
        exit_price = trade_data["tp"] if i % 2 == 0 else trade_data["sl"]
        backtest.close_trade(trade_data["timestamp"], exit_price)
        backtest.record_equity(trade_data["timestamp"])
    
    # Print report
    backtest.print_report()
    backtest.save_report()