from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging
from datetime import datetime

from backend.api.database import get_db
from backend.models.database import Discussion, DiscussionMessage, MapState
import redis
from backend.utils.config import settings
from backend.core.agent_self_model.model import REAgentSelfModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Redis client for real-time updates
redis_client = redis.from_url(settings.REDIS_URL)

# Pydantic models
class DiscussionBase(BaseModel):
    title: str
    description: Optional[str] = None
    
    class Config:
        orm_mode = True

class DiscussionCreate(DiscussionBase):
    pass

class DiscussionResponse(DiscussionBase):
    id: int
    status: str
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = 0

class MessageBase(BaseModel):
    author_type: str  # 'agent' or 'human'
    author_name: str
    message_content: str
    map_state_reference: Optional[Dict[str, Any]] = None
    attachment_urls: Optional[List[str]] = None
    
    class Config:
        orm_mode = True

class MessageCreate(MessageBase):
    parent_message_id: Optional[int] = None

class MessageResponse(MessageBase):
    id: int
    discussion_id: int
    parent_message_id: Optional[int] = None
    created_at: datetime
    
    # Include replies count for threaded discussions
    replies_count: Optional[int] = 0

class AgentResponse(BaseModel):
    message: str
    map_state_reference: Optional[Dict[str, Any]] = None
    reasoning: Optional[str] = None

# Endpoints
@router.get("/discussions/", response_model=List[DiscussionResponse])
def get_discussions(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None
):
    """
    Get all discussions, optionally filtered by status
    """
    query = db.query(Discussion)
    
    if status:
        query = query.filter(Discussion.status == status)
    
    # Count messages for each discussion
    discussions = []
    for discussion in query.order_by(Discussion.updated_at.desc()).offset(skip).limit(limit).all():
        message_count = db.query(DiscussionMessage).filter(
            DiscussionMessage.discussion_id == discussion.id
        ).count()
        
        disc_dict = discussion.__dict__
        disc_dict["message_count"] = message_count
        discussions.append(disc_dict)
    
    return discussions

@router.post("/discussions/", response_model=DiscussionResponse)
def create_discussion(
    discussion: DiscussionCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new discussion thread
    """
    db_discussion = Discussion(**discussion.dict())
    db.add(db_discussion)
    db.commit()
    db.refresh(db_discussion)
    
    # Add message count field
    result = db_discussion.__dict__
    result["message_count"] = 0
    
    return result

@router.get("/discussions/{discussion_id}", response_model=DiscussionResponse)
def get_discussion(
    discussion_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific discussion by ID
    """
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if not discussion:
        raise HTTPException(status_code=404, detail="Discussion not found")
    
    message_count = db.query(DiscussionMessage).filter(
        DiscussionMessage.discussion_id == discussion_id
    ).count()
    
    result = discussion.__dict__
    result["message_count"] = message_count
    
    return result

@router.get("/discussions/{discussion_id}/messages", response_model=List[MessageResponse])
def get_discussion_messages(
    discussion_id: int,
    db: Session = Depends(get_db),
    parent_id: Optional[int] = None
):
    """
    Get messages in a discussion thread, optionally filtered by parent message ID for threaded discussions
    """
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if not discussion:
        raise HTTPException(status_code=404, detail="Discussion not found")
    
    query = db.query(DiscussionMessage).filter(
        DiscussionMessage.discussion_id == discussion_id
    )
    
    if parent_id is not None:
        # Get specific thread
        query = query.filter(DiscussionMessage.parent_message_id == parent_id)
    else:
        # Get top-level messages only
        query = query.filter(DiscussionMessage.parent_message_id == None)
    
    messages = []
    for message in query.order_by(DiscussionMessage.created_at).all():
        # Count replies for each message
        replies_count = db.query(DiscussionMessage).filter(
            DiscussionMessage.parent_message_id == message.id
        ).count()
        
        msg_dict = message.__dict__
        msg_dict["replies_count"] = replies_count
        messages.append(msg_dict)
    
    return messages

@router.post("/discussions/{discussion_id}/messages", response_model=MessageResponse)
def create_message(
    discussion_id: int,
    message: MessageCreate,
    db: Session = Depends(get_db)
):
    """
    Add a message to a discussion thread
    """
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if not discussion:
        raise HTTPException(status_code=404, detail="Discussion not found")
    
    # If this is a reply, verify the parent message exists
    if message.parent_message_id:
        parent = db.query(DiscussionMessage).filter(
            DiscussionMessage.id == message.parent_message_id,
            DiscussionMessage.discussion_id == discussion_id
        ).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent message not found")
    
    # Create the message
    db_message = DiscussionMessage(
        discussion_id=discussion_id,
        **message.dict()
    )
    db.add(db_message)
    
    # Update discussion timestamp
    discussion.updated_at = datetime.now()
    
    db.commit()
    db.refresh(db_message)
    
    # Add replies count field
    result = db_message.__dict__
    result["replies_count"] = 0
    
    # Notify subscribers through Redis pubsub
    try:
        redis_client.publish(
            f"discussion:{discussion_id}:new_message",
            f"{db_message.id}:{db_message.author_name}"
        )
    except Exception as e:
        logger.error(f"Failed to publish message event to Redis: {e}")
    
    return result

@router.post("/discussions/{discussion_id}/agent_response", response_model=MessageResponse)
def get_agent_response(
    discussion_id: int,
    message_id: int,
    db: Session = Depends(get_db)
):
    """
    Generate a response from the RE agent to a user message
    """
    message = db.query(DiscussionMessage).filter(
        DiscussionMessage.id == message_id,
        DiscussionMessage.discussion_id == discussion_id
    ).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Initialize the agent self-model
    agent = REAgentSelfModel(db)
    
    try:
        # In a real implementation, this would invoke more sophisticated agent reasoning
        # Here we just create a simple response as a demonstration
        
        # Record the user's message in the agent's memory
        agent.add_memory({
            "type": "user_message",
            "content": message.message_content,
            "author": message.author_name,
            "discussion_id": discussion_id,
            "message_id": message_id,
            "topics": ["archaeology", "amazon", "investigation"]
        })
        
        # Generate a simple response based on the user's message
        response_content = f"Thank you for your message about {message.message_content[:30]}... I've analyzed this and have some thoughts."
        
        # Create a reasoning chain for this response
        agent.add_reasoning_chain({
            "input": message.message_content,
            "thought_process": "User is discussing archaeological findings. I should respond with relevant analysis.",
            "confidence": 0.85,
            "output": response_content
        })
        
        # Create the agent's response message
        agent_message = DiscussionMessage(
            discussion_id=discussion_id,
            parent_message_id=message_id,
            author_type="agent",
            author_name="RE-Archaeology Agent",
            message_content=response_content,
            # Copy any map state reference from the original message
            map_state_reference=message.map_state_reference
        )
        
        db.add(agent_message)
        
        # Update discussion timestamp
        discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
        discussion.updated_at = datetime.now()
        
        db.commit()
        db.refresh(agent_message)
        
        # Add replies count field
        result = agent_message.__dict__
        result["replies_count"] = 0
        
        return result
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error generating agent response: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating agent response: {e}")

@router.put("/discussions/{discussion_id}", response_model=DiscussionResponse)
def update_discussion(
    discussion_id: int,
    discussion_update: DiscussionCreate,
    db: Session = Depends(get_db)
):
    """
    Update a discussion's title or description
    """
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if not discussion:
        raise HTTPException(status_code=404, detail="Discussion not found")
    
    discussion.title = discussion_update.title
    discussion.description = discussion_update.description
    discussion.updated_at = datetime.now()
    
    db.commit()
    db.refresh(discussion)
    
    # Get message count
    message_count = db.query(DiscussionMessage).filter(
        DiscussionMessage.discussion_id == discussion_id
    ).count()
    
    result = discussion.__dict__
    result["message_count"] = message_count
    
    return result
