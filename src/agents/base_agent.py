"""
Base Agent Class for Multi-Agent Trading System
All agents inherit from this base class
"""

import logging
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from datetime import datetime
import google.generativeai as genai

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all trading agents"""
    
    def __init__(self, name: str, role: str, gemini_api_key: str):
        """
        Initialize Base Agent
        
        Args:
            name: Agent name (e.g., 'LiquidityAgent')
            role: Agent role/description
            gemini_api_key: Google Gemini API key
        """
        self.name = name
        self.role = role
        genai.configure(api_key=gemini_api_key)
        self.model = "gemini-2.5-flash"
        self.memory: List[Dict[str, Any]] = []
        self.created_at = datetime.now()
        logger.info(f"🤖 {self.name} initialized")
    
    @abstractmethod
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute agent logic
        Must be implemented by subclass
        
        Args:
            input_data: Input data for processing
        
        Returns:
            Agent output
        """
        pass
    
    def call_gemini(self, system_prompt: str, user_message: str, 
                   temperature: float = 0.7) -> str:
        """
        Call Google Gemini API with system and user prompts
        
        Args:
            system_prompt: System context
            user_message: User message
            temperature: Temperature for response generation
        
        Returns:
            Gemini's response
        """
        try:
            model = genai.GenerativeModel(
                model_name=self.model,
                system_instruction=system_prompt
            )
            
            response = model.generate_content(
                user_message,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=1024
                )
            )
            return response.text
        except Exception as e:
            logger.error(f"❌ {self.name} - Gemini API error: {e}")
            raise
    
    def add_memory(self, key: str, value: Any):
        """Add to agent memory"""
        self.memory.append({
            "timestamp": datetime.now().isoformat(),
            "key": key,
            "value": value
        })
        logger.debug(f"💾 {self.name} - Memory added: {key}")
    
    def get_memory(self, key: str) -> Optional[Any]:
        """Retrieve from agent memory"""
        for item in reversed(self.memory):
            if item["key"] == key:
                return item["value"]
        return None
    
    def clear_memory(self):
        """Clear all agent memory"""
        self.memory = []
        logger.debug(f"🧹 {self.name} - Memory cleared")
    
    def log_execution(self, result: Dict[str, Any]):
        """Log agent execution result"""
        logger.info(f"✅ {self.name} execution result:")
        for key, value in result.items():
            logger.info(f"   {key}: {value}")
    
    def __repr__(self) -> str:
        return f"{self.name} (Role: {self.role})"