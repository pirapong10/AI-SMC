"""
LangGraph Pipeline - Multi-Agent Orchestration
Connects all 9 agents into a cohesive workflow:
Liquidity → CHoCH → FVG → Scoring → Decision → Risk → Portfolio → Backtest → Executor
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class TradingPipeline:
    """Multi-Agent Trading Pipeline using LangGraph principles"""
    
    def __init__(self, agents: Dict[str, Any]):
        """
        Initialize Trading Pipeline
        
        Args:
            agents: Dictionary of all agents {agent_name: agent_instance}
        """
        self.agents = agents
        self.execution_history = []
        self.current_state = {}
        logger.info("🌐 Trading Pipeline initialized")
    
    def run(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute full trading pipeline
        
        Pipeline Flow:
        1. Liquidity Detection → Liquidity Output
        2. CHoCH Detection → CHoCH Output
        3. FVG Detection → FVG Output
        4. XGBoost Scoring → Score Output
        5. Claude Decision → Decision Output
        6. Risk Management → Position Size
        7. Portfolio Tracking → Portfolio State
        8. Backtest (optional) → Backtest Results
        9. Execution (if approved) → Trade Confirmation
        
        Args:
            market_data: Current market data with candles
        
        Returns:
            Complete pipeline execution result
        """
        
        execution_start = datetime.now()
        result = {
            "timestamp": execution_start.isoformat(),
            "symbol": market_data.get("symbol", "XAUUSD"),
            "status": "IN_PROGRESS",
            "stage": None,
            "stages": {}
        }
        
        try:
            candles = market_data.get("candles", [])
            
            # ==================== STAGE 1: LIQUIDITY DETECTION ====================
            result["stage"] = "LIQUIDITY_DETECTION"
            logger.info("📍 Stage 1: Liquidity Detection")
            
            liquidity_result = self.agents["liquidity"].execute(candles)
            result["stages"]["liquidity"] = liquidity_result
            self.current_state["liquidity"] = liquidity_result
            
            if not liquidity_result.get("signal"):
                logger.info("⏭️  No liquidity sweep detected - Pipeline stops")
                result["status"] = "NO_SIGNAL"
                return result
            
            # ==================== STAGE 2: CHOCH DETECTION ====================
            result["stage"] = "CHOCH_DETECTION"
            logger.info("📍 Stage 2: CHoCH Detection")
            
            choch_result = self.agents["choch"].execute(candles)
            result["stages"]["choch"] = choch_result
            self.current_state["choch"] = choch_result
            
            # ==================== STAGE 3: FVG DETECTION ====================
            result["stage"] = "FVG_DETECTION"
            logger.info("📍 Stage 3: FVG Detection")
            
            fvg_result = self.agents["fvg"].execute(candles)
            result["stages"]["fvg"] = fvg_result
            self.current_state["fvg"] = fvg_result
            
            # ==================== STAGE 4: XGBOOST SCORING ====================
            result["stage"] = "SCORING"
            logger.info("📍 Stage 4: XGBoost Scoring")
            
            scoring_input = {
                "liquidity": liquidity_result,
                "choch": choch_result,
                "fvg": fvg_result
            }
            
            scoring_result = self.agents["scoring"].execute(scoring_input)
            result["stages"]["scoring"] = scoring_result
            self.current_state["scoring"] = scoring_result
            
            if scoring_result.get("recommendation") == "SKIP":
                logger.info("⏭️  Low score - Pipeline stops")
                result["status"] = "LOW_SCORE"
                return result
            
            # ==================== STAGE 5: CLAUDE DECISION ====================
            result["stage"] = "DECISION_MAKING"
            logger.info("📍 Stage 5: Claude Decision Making")
            
            decision_input = {
                "liquidity": liquidity_result,
                "choch": choch_result,
                "fvg": fvg_result,
                "score": scoring_result
            }
            
            decision_result = self.agents["decision"].execute(decision_input)
            result["stages"]["decision"] = decision_result
            self.current_state["decision"] = decision_result
            
            if decision_result.get("decision") == "ERROR":
                logger.error("❌ Decision agent error - Pipeline stops")
                result["status"] = "ERROR"
                return result
            
            if decision_result.get("decision") == "SKIP":
                logger.info("⏭️  Claude recommended skip - Pipeline stops")
                result["status"] = "CLAUDE_SKIP"
                return result
            
            # ==================== STAGE 6: RISK MANAGEMENT ====================
            result["stage"] = "RISK_MANAGEMENT"
            logger.info("📍 Stage 6: Risk Management")
            
            risk_result = self.agents["risk"].execute(decision_result)
            result["stages"]["risk"] = risk_result
            self.current_state["risk"] = risk_result
            
            if risk_result.get("status") == "REJECTED":
                logger.info("⏭️  Risk limits exceeded - Pipeline stops")
                result["status"] = "RISK_REJECTED"
                return result
            
            # ==================== STAGE 7: PORTFOLIO TRACKING ====================
            result["stage"] = "PORTFOLIO_UPDATE"
            logger.info("📍 Stage 7: Portfolio Tracking")
            
            portfolio_result = self.agents["portfolio"].execute(decision_result)
            result["stages"]["portfolio"] = portfolio_result
            self.current_state["portfolio"] = portfolio_result
            
            # ==================== STAGE 8: BACKTEST (OPTIONAL) ====================
            result["stage"] = "BACKTEST"
            logger.info("📍 Stage 8: Backtesting")
            
            backtest_result = self.agents["backtest"].execute({})
            result["stages"]["backtest"] = backtest_result
            self.current_state["backtest"] = backtest_result
            
            # ==================== STAGE 9: TRADE EXECUTION ====================
            result["stage"] = "EXECUTION"
            logger.info("📍 Stage 9: Trade Execution")
            
            # Note: This is MOCK execution - not real trading
            if decision_result.get("decision") == "TRADE":
                executor_input = {
                    "type": "MOCK_ORDER",
                    "direction": "BUY",
                    "position_size": risk_result.get("position_size", 0),
                    "entry": fvg_result.get("mid_level", 0)
                }
                
                execution_result = self.agents["executor"].execute(executor_input)
                result["stages"]["execution"] = execution_result
                result["status"] = "TRADE_EXECUTED"
            else:
                result["status"] = "TRADE_SKIPPED"
            
            # ==================== PIPELINE COMPLETE ====================
            execution_end = datetime.now()
            execution_time = (execution_end - execution_start).total_seconds()
            
            result["execution_time_seconds"] = execution_time
            result["status"] = "COMPLETED"
            
            logger.info(f"✅ Pipeline completed in {execution_time:.2f}s")
            
            # Store in history
            self.execution_history.append(result)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Pipeline error: {e}")
            result["status"] = "ERROR"
            result["error"] = str(e)
            return result
    
    def get_summary(self, result: Dict[str, Any]) -> str:
        """
        Generate human-readable summary of pipeline execution
        
        Args:
            result: Pipeline execution result
        
        Returns:
            Formatted summary string
        """
        summary = f"""
╔════════════════════════════════════════════════════════╗
║          AI SMC TRADING PIPELINE SUMMARY              ║
╚════════════════════════════════════════════════════════╝

⏰ Timestamp: {result['timestamp']}
📊 Symbol: {result['symbol']}
✅ Status: {result['status']}
⚡ Execution Time: {result.get('execution_time_seconds', 0):.2f}s

📍 STAGE RESULTS:
────────────────────────────────────────────────────────
"""
        
        for stage_name, stage_result in result.get("stages", {}).items():
            signal = stage_result.get("signal", "N/A")
            confidence = stage_result.get("confidence", 0)
            summary += f"\n  ✓ {stage_name.upper()}: {signal} (Confidence: {confidence:.2f})"
        
        summary += f"""

💡 FINAL DECISION: {result.get("stages", {}).get("decision", {}).get("decision", "N/A")}
🎯 POSITION SIZE: {result.get("stages", {}).get("risk", {}).get("position_size", 0):.2f}
⚠️  RISK: {result.get("stages", {}).get("risk", {}).get("max_risk_per_trade", 0):.2f}

╔════════════════════════════════════════════════════════╗
"""
        
        return summary
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get execution history"""
        return self.execution_history
    
    def clear_history(self):
        """Clear execution history"""
        self.execution_history = []
        logger.info("🧹 Execution history cleared")
