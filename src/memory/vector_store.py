"""
Qdrant Vector Store Integration
Store and retrieve trading decisions, patterns, and agent memory
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import hashlib

logger = logging.getLogger(__name__)


class VectorStore:
    """Qdrant Vector Store for Agent Memory"""
    
    def __init__(self, url: str, api_key: str, collection_name: str = "ai_smc_trading"):
        """
        Initialize Qdrant Vector Store
        
        Args:
            url: Qdrant server URL (e.g., http://localhost:6333)
            api_key: Qdrant API key
            collection_name: Collection name for storing vectors
        """
        self.client = QdrantClient(url=url, api_key=api_key if api_key else None)
        self.collection_name = collection_name
        self.vector_size = 1536  # Claude embeddings dimension
        
        self._initialize_collection()
    
    def _initialize_collection(self):
        """Create collection if it doesn't exist"""
        try:
            # Try to get collection info
            self.client.get_collection(self.collection_name)
            logger.info(f"✅ Collection '{self.collection_name}' exists")
        except Exception:
            # Create new collection
            logger.info(f"📦 Creating collection '{self.collection_name}'...")
            try:
                self.client.recreate_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✅ Collection '{self.collection_name}' created successfully")
            except Exception as e:
                logger.error(f"❌ Failed to create collection: {e}")
                raise
    
    def _generate_id(self, text: str) -> int:
        """Generate unique ID from text hash"""
        hash_object = hashlib.md5(text.encode())
        return int(hash_object.hexdigest(), 16) % (10 ** 8)
    
    def store_memory(self, memory_type: str, content: Dict[str, Any], embedding: List[float]):
        """
        Store memory in vector database
        
        Args:
            memory_type: Type of memory (trade_decision, pattern, signal, analysis, etc.)
            content: Dictionary containing the memory content
            embedding: Vector embedding from Claude
        """
        try:
            # Create metadata payload
            payload = {
                "type": memory_type,
                "content": json.dumps(content),
                "timestamp": datetime.now().isoformat(),
                "symbol": content.get("symbol", "XAUUSD"),
                "timeframe": content.get("timeframe", "H1"),
            }
            
            # Generate ID
            content_str = json.dumps(content, sort_keys=True)
            point_id = self._generate_id(content_str)
            
            # Create point
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload
            )
            
            # Upsert to collection
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.info(f"💾 Memory stored: {memory_type} (ID: {point_id})")
            return point_id
            
        except Exception as e:
            logger.error(f"❌ Failed to store memory: {e}")
            raise
    
    def search_memory(self, embedding: List[float], limit: int = 5, 
                     memory_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search similar memories using vector similarity
        
        Args:
            embedding: Query vector embedding
            limit: Number of results
            memory_type: Filter by memory type (optional)
        
        Returns:
            List of similar memories with scores
        """
        try:
            # Build query filter if memory_type specified
            query_filter = None
            if memory_type:
                query_filter = {
                    "must": [
                        {
                            "key": "type",
                            "match": {"value": memory_type}
                        }
                    ]
                }
            
            # Search
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=embedding,
                query_filter=query_filter,
                limit=limit
            )
            
            # Format results
            memories = []
            for result in results:
                memory = {
                    "id": result.id,
                    "score": result.score,
                    "type": result.payload.get("type"),
                    "content": json.loads(result.payload.get("content", "{}")),
                    "timestamp": result.payload.get("timestamp"),
                    "symbol": result.payload.get("symbol"),
                    "timeframe": result.payload.get("timeframe"),
                }
                memories.append(memory)
            
            logger.info(f"🔍 Found {len(memories)} similar memories (type: {memory_type})")
            return memories
            
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return []
    
    def get_recent_memories(self, memory_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent memories by type (sorted by timestamp)
        
        Args:
            memory_type: Type of memory to retrieve
            limit: Number of results
        
        Returns:
            List of recent memories
        """
        try:
            # Scroll through collection to get memories
            points, _ = self.client.scroll(
                collection_name=self.collection_name,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            
            # Filter by type and sort by timestamp
            filtered = [
                {
                    "id": p.id,
                    "type": p.payload.get("type"),
                    "content": json.loads(p.payload.get("content", "{}")),
                    "timestamp": p.payload.get("timestamp"),
                    "symbol": p.payload.get("symbol"),
                    "timeframe": p.payload.get("timeframe"),
                }
                for p in points
                if p.payload.get("type") == memory_type
            ]
            
            # Sort by timestamp descending
            filtered.sort(
                key=lambda x: x["timestamp"],
                reverse=True
            )
            
            return filtered[:limit]
            
        except Exception as e:
            logger.error(f"❌ Failed to get recent memories: {e}")
            return []
    
    def delete_memory(self, memory_id: int):
        """Delete a specific memory"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=memory_id
            )
            logger.info(f"🗑️  Memory deleted: {memory_id}")
        except Exception as e:
            logger.error(f"❌ Failed to delete memory: {e}")
    
    def clear_collection(self):
        """Clear all memories in collection"""
        try:
            self.client.delete_collection(self.collection_name)
            self._initialize_collection()
            logger.info(f"🧹 Collection '{self.collection_name}' cleared")
        except Exception as e:
            logger.error(f"❌ Failed to clear collection: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "collection_name": self.collection_name,
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "status": info.status,
            }
        except Exception as e:
            logger.error(f"❌ Failed to get stats: {e}")
            return {}


# Example usage
if __name__ == "__main__":
    # Initialize
    vs = VectorStore(
        url="http://localhost:6333",
        api_key="",
        collection_name="ai_smc_trading"
    )
    
    # Example memory
    sample_memory = {
        "symbol": "XAUUSD",
        "timeframe": "H1",
        "signal_type": "SMC_BULLISH",
        "entry_level": 2050.5,
        "confidence": 0.85,
        "reasoning": "Liquidity sweep + CHoCH + FVG aligned"
    }
    
    # Mock embedding (normally from Claude)
    mock_embedding = [0.1] * 1536
    
    # Store
    memory_id = vs.store_memory("trade_decision", sample_memory, mock_embedding)
    print(f"✅ Memory stored with ID: {memory_id}")
    
    # Stats
    stats = vs.get_stats()
    print(f"📊 Collection Stats: {stats}")
