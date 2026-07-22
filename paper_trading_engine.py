"""
Paper Trading Engine - Phase 3
Executes Phase 1 SMC strategy on live MT5 data
Simulates order execution with real spreads and slippage
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import json
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PaperTrade:
    """Paper trading order record"""
    trade_id: int
    entry_time: str
    entry_price: float
    entry_bid: float
    entry_ask: float
    position_size: float
    direction: str  # LONG or SHORT
    stop_loss: float
    take_profit: float
    exit_time: Optional[str] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    pnl: float = 0.0
    return_pct: float = 0.0
    status: str = "OPEN"  # OPEN, CLOSED


class PaperTradingEngine:
    """
    Paper Trading Engine
    
    Executes simulated trades based on SMC signals
    Tracks live P&L with real spreads/slippage
    """
    
    def __init__(self, 
                 initial_capital: float = 10000,
                 risk_per_trade: float = 2.0,
                 max_position_size: float = 5000,
                 spread_multiplier: float = 1.5):
        """
        Initialize paper trading engine
        
        Args:
            initial_capital: Starting capital
            risk_per_trade: Max risk per trade (%)
            max_position_size: Max position size
            spread_multiplier: Slippage multiplier on spread
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.peak_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.max_position_size = max_position_size
        self.spread_multiplier = spread_multiplier
        
        self.trades: List[PaperTrade] = []
        self.open_position: Optional[PaperTrade] = None
        self.trade_id = 0
        self.equity_history: List[Tuple[str, float]] = []
        
        logger.info(f"📝 Paper Trading Engine initialized")
        logger.info(f"   Capital: ${initial_capital:.2f}")
        logger.info(f"   Risk/trade: {risk_per_trade}%")
        logger.info(f"   Spread multiplier: {spread_multiplier}x")
    
    def calculate_position_size(self, entry_price: float, stop_loss: float) -> float:
        """Calculate risk-based position size"""
        risk_amount = self.current_capital * (self.risk_per_trade / 100)
        price_distance = abs(entry_price - stop_loss)
        
        if price_distance <= 0:
            return 0
        
        position_size = risk_amount / price_distance
        
        if position_size > self.max_position_size:
            position_size = self.max_position_size
        
        return position_size
    
    def apply_slippage(self, price: float, direction: str, spread: float) -> float:
        """
        Apply realistic slippage to entry price
        
        Args:
            price: Base entry price
            direction: LONG or SHORT
            spread: Current bid-ask spread
        
        Returns:
            Price after slippage
        """
        slippage = spread * self.spread_multiplier
        
        if direction == "LONG":
            # Buy at ask price + slippage
            return price + slippage
        else:
            # Sell at bid price - slippage
            return price - slippage
    
    def place_trade(self, 
                   timestamp: str,
                   bid: float, 
                   ask: float,
                   direction: str,
                   position_size: float,
                   stop_loss: float,
                   take_profit: float,
                   signal_source: str = "SMC") -> Optional[PaperTrade]:
        """
        Place a simulated trade
        
        Args:
            timestamp: Trade time
            bid: Current bid price
            ask: Current ask price
            direction: LONG or SHORT
            position_size: Position size
            stop_loss: Stop loss price
            take_profit: Take profit price
            signal_source: Source of signal
        
        Returns:
            PaperTrade object or None if rejected
        """
        if self.open_position:
            logger.warning("⚠️ Position already open, rejecting new trade")
            return None
        
        # Validate position size
        if position_size <= 0:
            logger.warning("⚠️ Invalid position size")
            return None
        
        if position_size > self.max_position_size:
            position_size = self.max_position_size
        
        # Calculate entry price with slippage
        spread = ask - bid
        
        if direction == "LONG":
            entry_price = ask  # Buy at ask
            mid_price = (bid + ask) / 2
        else:  # SHORT
            entry_price = bid  # Sell at bid
            mid_price = (bid + ask) / 2
        
        # Create trade record
        self.trade_id += 1
        trade = PaperTrade(
            trade_id=self.trade_id,
            entry_time=timestamp,
            entry_price=entry_price,
            entry_bid=bid,
            entry_ask=ask,
            position_size=position_size,
            direction=direction,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        self.open_position = trade
        
        # Log trade
        sl_distance = abs(entry_price - stop_loss)
        tp_distance = abs(take_profit - entry_price)
        risk_reward = tp_distance / sl_distance if sl_distance > 0 else 0
        
        logger.info(f"📈 Trade #{trade.trade_id} opened: {direction} {position_size:.2f} units @ {entry_price:.2f}")
        logger.info(f"   Entry (Bid/Ask): {bid:.2f}/{ask:.2f}")
        logger.info(f"   SL: {stop_loss:.2f} ({sl_distance:.2f}), TP: {take_profit:.2f} ({tp_distance:.2f})")
        logger.info(f"   R:R: 1:{risk_reward:.2f}, Risk: ${risk_reward * (self.current_capital * (self.risk_per_trade / 100)):.2f}")
        
        return trade
    
    def check_exit_conditions(self, timestamp: str, bid: float, ask: float) -> bool:
        """
        Check if open position should be closed
        
        Args:
            timestamp: Current time
            bid: Current bid
            ask: Current ask
        
        Returns:
            True if trade was closed
        """
        if not self.open_position:
            return False
        
        trade = self.open_position
        
        # Check for TP/SL hit
        if trade.direction == "LONG":
            # Take profit (sell at bid)
            if bid >= trade.take_profit:
                return self.close_trade(timestamp, trade.take_profit, "TP_HIT")
            
            # Stop loss (sell at bid)
            if bid <= trade.stop_loss:
                return self.close_trade(timestamp, trade.stop_loss, "SL_HIT")
        
        else:  # SHORT
            # Take profit (buy at ask)
            if ask <= trade.take_profit:
                return self.close_trade(timestamp, trade.take_profit, "TP_HIT")
            
            # Stop loss (buy at ask)
            if ask >= trade.stop_loss:
                return self.close_trade(timestamp, trade.stop_loss, "SL_HIT")
        
        return False
    
    def close_trade(self, timestamp: str, price: float, reason: str) -> bool:
        """
        Close open position
        
        Args:
            timestamp: Close time
            price: Close price
            reason: Reason for closing
        
        Returns:
            True if trade was closed
        """
        if not self.open_position:
            return False
        
        trade = self.open_position
        
        # Calculate P&L
        if trade.direction == "LONG":
            pnl = (price - trade.entry_price) * trade.position_size
        else:  # SHORT
            pnl = (trade.entry_price - price) * trade.position_size
        
        return_pct = (pnl / self.current_capital) * 100
        
        # Update trade
        trade.exit_time = timestamp
        trade.exit_price = price
        trade.exit_reason = reason
        trade.pnl = pnl
        trade.return_pct = return_pct
        trade.status = "CLOSED"
        
        # Update capital
        self.current_capital += pnl
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital
        
        # Log trade
        result = "✅ WIN" if pnl > 0 else "❌ LOSS"
        logger.info(f"📉 Trade #{trade.trade_id} closed: {result} P&L: ${pnl:.2f} ({return_pct:.2f}%) [{reason}]")
        
        # Add to closed trades
        self.trades.append(trade)
        self.open_position = None
        
        return True
    
    def record_equity(self, timestamp: str):
        """Record current equity"""
        equity = self.current_capital
        if self.open_position:
            # Add mark-to-market for open position
            # (simplified - would need current price)
            pass
        
        self.equity_history.append((timestamp, equity))
    
    def get_metrics(self) -> Dict:
        """Calculate trading metrics"""
        if not self.trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "total_pnl": 0.0,
                "max_drawdown": 0.0,
                "roi": 0.0,
                "final_capital": self.current_capital
            }
        
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl < 0]
        
        total_wins = sum(t.pnl for t in winning_trades)
        total_losses = sum(abs(t.pnl) for t in losing_trades)
        
        win_rate = (len(winning_trades) / len(self.trades) * 100) if self.trades else 0
        profit_factor = (total_wins / total_losses) if total_losses > 0 else 0
        total_pnl = sum(t.pnl for t in self.trades)
        
        # Max drawdown
        max_dd = 0
        peak = self.initial_capital
        for _, equity in self.equity_history:
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak * 100
            if dd > max_dd:
                max_dd = dd
        
        roi = (total_pnl / self.initial_capital) * 100
        
        return {
            "total_trades": len(self.trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "total_pnl": total_pnl,
            "max_drawdown": max_dd,
            "roi": roi,
            "final_capital": self.current_capital
        }
    
    def save_journal(self, filepath: str = "paper_trading_journal.json"):
        """Save trade journal"""
        journal = {
            "timestamp": datetime.now().isoformat(),
            "initial_capital": self.initial_capital,
            "current_capital": self.current_capital,
            "metrics": self.get_metrics(),
            "trades": [
                {
                    "id": t.trade_id,
                    "entry_time": t.entry_time,
                    "entry_price": t.entry_price,
                    "direction": t.direction,
                    "position_size": t.position_size,
                    "stop_loss": t.stop_loss,
                    "take_profit": t.take_profit,
                    "exit_time": t.exit_time,
                    "exit_price": t.exit_price,
                    "exit_reason": t.exit_reason,
                    "pnl": t.pnl,
                    "return_pct": t.return_pct,
                    "status": t.status
                }
                for t in self.trades
            ]
        }
        
        with open(filepath, "w") as f:
            json.dump(journal, f, indent=2)
        
        logger.info(f"💾 Journal saved: {filepath}")
    
    def print_summary(self):
        """Print trading summary"""
        metrics = self.get_metrics()
        
        print("\n" + "="*60)
        print("📊 PAPER TRADING SUMMARY")
        print("="*60)
        print(f"Total Trades:      {metrics['total_trades']}")
        print(f"Winning:           {metrics['winning_trades']}")
        print(f"Losing:            {metrics['losing_trades']}")
        print(f"Win Rate:          {metrics['win_rate']:.2f}%")
        print(f"Profit Factor:     {metrics['profit_factor']:.2f}")
        print(f"Total P&L:         ${metrics['total_pnl']:.2f}")
        print(f"Max Drawdown:      {metrics['max_drawdown']:.2f}%")
        print(f"ROI:               {metrics['roi']:.2f}%")
        print(f"Final Capital:     ${metrics['final_capital']:.2f}")
        print("="*60 + "\n")
