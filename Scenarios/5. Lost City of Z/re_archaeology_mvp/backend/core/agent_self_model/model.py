import json
import time
import logging
import redis
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from backend.models.database import AgentState
from backend.utils.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class REAgentSelfModel:
    """
    Implements the Persistent Agent Self-Model for the RE-Archaeology Agent.
    This class handles the agent's memory, reasoning chains, and maintains a coherent state
    over time, even when interacting with different systems.
    """
    
    def __init__(self, db_session: Session, redis_client: Optional[redis.Redis] = None):
        """Initialize the RE Agent Self-Model"""
        self.db = db_session
        self.redis = redis_client or redis.from_url(settings.REDIS_URL)
        
        # Internal state
        self._state = {
            "memory": [],
            "reasoning_chains": [],
            "active_investigations": {},
            "confidence_levels": {},
            "last_actions": [],
            "creation_time": time.time(),
            "last_save_time": time.time()
        }
        
        # Load the latest state if it exists
        self._load_state()
    
    def _load_state(self) -> None:
        """Load the latest agent state from the database"""
        try:
            # First try to get from Redis (faster, more recent)
            cached_state = self.redis.get("re_agent:latest_state")
            if cached_state:
                self._state = json.loads(cached_state)
                logger.info("Loaded agent state from Redis cache")
                return
                
            # Otherwise load from database
            latest_state = self.db.query(AgentState).order_by(AgentState.id.desc()).first()
            if latest_state:
                self._state.update(latest_state.state_snapshot)
                if latest_state.memory_context:
                    self._state["memory"] = latest_state.memory_context
                if latest_state.reasoning_chains:
                    self._state["reasoning_chains"] = latest_state.reasoning_chains
                logger.info("Loaded agent state from database")
        except Exception as e:
            logger.error(f"Failed to load agent state: {e}")
    
    def save_state(self) -> None:
        """Save the current agent state to persistence storage"""
        try:
            # Save to Redis (fast, temporary)
            self.redis.set("re_agent:latest_state", json.dumps(self._state))
            
            # Periodically save to database (permanent)
            if time.time() - self._state["last_save_time"] > settings.AGENT_STATE_PERSISTENCE_INTERVAL:
                new_state = AgentState(
                    state_snapshot=self._state,
                    memory_context=self._state["memory"],
                    reasoning_chains=self._state["reasoning_chains"]
                )
                self.db.add(new_state)
                self.db.commit()
                self._state["last_save_time"] = time.time()
                logger.info("Saved agent state to database")
        except Exception as e:
            logger.error(f"Failed to save agent state: {e}")
    
    def add_memory(self, memory_entry: Dict[str, Any]) -> None:
        """Add a new memory entry to the agent's memory"""
        memory_entry["timestamp"] = time.time()
        self._state["memory"].append(memory_entry)
        
        # Trim memory if it exceeds the maximum size
        if len(self._state["memory"]) > settings.AGENT_MEMORY_SIZE:
            self._state["memory"] = self._state["memory"][-settings.AGENT_MEMORY_SIZE:]
        
        # Save the updated state
        self.save_state()
    
    def add_reasoning_chain(self, reasoning_chain: Dict[str, Any]) -> None:
        """Add a reasoning chain to the agent's reasoning history"""
        reasoning_chain["timestamp"] = time.time()
        self._state["reasoning_chains"].append(reasoning_chain)
        self.save_state()
    
    def start_investigation(self, region_id: str, parameters: Dict[str, Any]) -> None:
        """Start a new investigation for a specific region"""
        self._state["active_investigations"][region_id] = {
            "start_time": time.time(),
            "parameters": parameters,
            "observations": [],
            "status": "active"
        }
        self.save_state()
    
    def add_observation(self, region_id: str, observation: Dict[str, Any]) -> None:
        """Add an observation to an active investigation"""
        if region_id in self._state["active_investigations"]:
            observation["timestamp"] = time.time()
            self._state["active_investigations"][region_id]["observations"].append(observation)
            self.save_state()
    
    def set_confidence(self, region_id: str, confidence_level: float, reasoning: str) -> None:
        """Set confidence level for a specific region"""
        self._state["confidence_levels"][region_id] = {
            "level": confidence_level,
            "reasoning": reasoning,
            "timestamp": time.time()
        }
        self.save_state()
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get a summary of the current agent state"""
        return {
            "memory_count": len(self._state["memory"]),
            "reasoning_chains_count": len(self._state["reasoning_chains"]),
            "active_investigations_count": len(self._state["active_investigations"]),
            "confidence_assessments_count": len(self._state["confidence_levels"]),
            "agent_age": time.time() - self._state["creation_time"],
            "last_save_time": self._state["last_save_time"]
        }
    
    def get_memory_by_topic(self, topic: str) -> List[Dict[str, Any]]:
        """Retrieve memories related to a specific topic"""
        return [m for m in self._state["memory"] if topic in m.get("topics", [])]
    
    def get_investigation(self, region_id: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific investigation"""
        return self._state["active_investigations"].get(region_id)
    
    def get_confidence(self, region_id: str) -> Optional[Dict[str, Any]]:
        """Get confidence assessment for a specific region"""
        return self._state["confidence_levels"].get(region_id)
    
    def add_action(self, action: Dict[str, Any]) -> None:
        """Record an action taken by the agent"""
        action["timestamp"] = time.time()
        self._state["last_actions"].append(action)
        # Keep only the latest 100 actions
        if len(self._state["last_actions"]) > 100:
            self._state["last_actions"] = self._state["last_actions"][-100:]
        self.save_state()

    def get_related_memories(self, query: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get memories related to a specific query.
        This is a simple implementation that would be replaced with
        a more sophisticated semantic similarity search in production.
        """
        # This is a placeholder implementation
        query_topics = set(query.get("topics", []))
        query_keywords = set(query.get("keywords", []))
        
        scored_memories = []
        
        for memory in self._state["memory"]:
            memory_topics = set(memory.get("topics", []))
            memory_keywords = set(memory.get("keywords", []))
            
            # Calculate simple relevance score
            topic_overlap = len(query_topics.intersection(memory_topics))
            keyword_overlap = len(query_keywords.intersection(memory_keywords))
            
            relevance = topic_overlap * 2 + keyword_overlap
            if relevance > 0:
                scored_memories.append((relevance, memory))
        
        # Sort by relevance and return top matches
        scored_memories.sort(reverse=True, key=lambda x: x[0])
        return [memory for score, memory in scored_memories[:limit]]
