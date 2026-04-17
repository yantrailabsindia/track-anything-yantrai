"""
Chatroom management router — create/list/delete chatrooms and manage conversation history.
Fully SQL-backed via SQLAlchemy.
User-scoped: Users can only see and manage their own chatrooms.
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.auth import verify_token
from backend.database import get_db
from backend.models import Chatroom, ChatMessage, User
from typing import Optional, List
from datetime import datetime

router = APIRouter()


def _get_token_data(request: Request):
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth_header:
        return None
    token = auth_header.replace("Bearer ", "")
    return verify_token(token)


class CreateChatroomRequest(BaseModel):
    name: str
    description: Optional[str] = ""


class UpdateChatroomRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_shared: Optional[bool] = None


class ChatMessageData(BaseModel):
    role: str  # "user" or "ai"
    content: str
    response_data: Optional[dict] = None


class SaveConversationRequest(BaseModel):
    chatroom_id: str
    messages: List[ChatMessageData]


@router.get("/")
def list_chatrooms(request: Request, db: Session = Depends(get_db)):
    """List all chatrooms created by the current user."""
    token_data = _get_token_data(request)
    if not token_data:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = token_data["id"]

    # Users can only see chatrooms they created
    chatrooms = db.query(Chatroom).filter(Chatroom.creator_id == user_id).order_by(Chatroom.created_at.desc()).all()

    result = []
    for room in chatrooms:
        msg_count = db.query(ChatMessage).filter(ChatMessage.chatroom_id == room.id).count()
        result.append({
            "id": room.id,
            "name": room.name,
            "description": room.description or "",
            "created_at": room.created_at.isoformat() if room.created_at else None,
            "updated_at": room.updated_at.isoformat() if room.updated_at else None,
            "message_count": msg_count,
            "is_shared": room.is_shared,
        })
    return result


@router.post("/")
def create_chatroom(req: CreateChatroomRequest, request: Request, db: Session = Depends(get_db)):
    """Create a new chatroom."""
    token_data = _get_token_data(request)
    if not token_data:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = token_data["id"]
    org_id = token_data.get("org_id")

    # Check if chatroom with same name exists for this user
    existing = db.query(Chatroom).filter(
        Chatroom.creator_id == user_id,
        Chatroom.name.ilike(req.name)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Chatroom '{req.name}' already exists")

    new_room = Chatroom(
        name=req.name,
        description=req.description or "",
        creator_id=user_id,
        org_id=org_id,
        is_shared=False,  # Private by default
    )
    db.add(new_room)
    db.commit()
    db.refresh(new_room)

    return {
        "id": new_room.id,
        "name": new_room.name,
        "description": new_room.description,
        "created_at": new_room.created_at.isoformat(),
        "is_shared": new_room.is_shared,
    }


@router.get("/{chatroom_id}")
def get_chatroom(chatroom_id: str, request: Request, db: Session = Depends(get_db)):
    """Get chatroom details (creator only)."""
    token_data = _get_token_data(request)
    if not token_data:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = token_data["id"]

    room = db.query(Chatroom).filter(Chatroom.id == chatroom_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Chatroom not found")

    # Only creator can access
    if room.creator_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    msg_count = db.query(ChatMessage).filter(ChatMessage.chatroom_id == room.id).count()

    return {
        "id": room.id,
        "name": room.name,
        "description": room.description or "",
        "creator_id": room.creator_id,
        "created_at": room.created_at.isoformat(),
        "updated_at": room.updated_at.isoformat(),
        "message_count": msg_count,
        "is_shared": room.is_shared,
    }


@router.get("/{chatroom_id}/messages")
def get_chatroom_messages(
    chatroom_id: str,
    request: Request,
    db: Session = Depends(get_db),
    limit: int = 100,
    offset: int = 0
):
    """Get messages from a chatroom (creator only), with pagination."""
    token_data = _get_token_data(request)
    if not token_data:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = token_data["id"]

    room = db.query(Chatroom).filter(Chatroom.id == chatroom_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Chatroom not found")

    # Only creator can access
    if room.creator_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get total count
    total = db.query(ChatMessage).filter(ChatMessage.chatroom_id == chatroom_id).count()

    # Get paginated messages
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.chatroom_id == chatroom_id)
        .order_by(ChatMessage.created_at.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    result = []
    for msg in messages:
        result.append({
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "response_data": msg.response_data,
            "created_at": msg.created_at.isoformat(),
        })

    return {
        "messages": result,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.patch("/{chatroom_id}")
def update_chatroom(
    chatroom_id: str,
    req: UpdateChatroomRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Update chatroom (creator only)."""
    token_data = _get_token_data(request)
    if not token_data:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = token_data["id"]

    room = db.query(Chatroom).filter(Chatroom.id == chatroom_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Chatroom not found")

    # Only creator can update
    if room.creator_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if req.name:
        room.name = req.name
    if req.description is not None:
        room.description = req.description
    if req.is_shared is not None:
        room.is_shared = req.is_shared

    room.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(room)

    return {
        "id": room.id,
        "name": room.name,
        "description": room.description,
        "updated_at": room.updated_at.isoformat(),
        "is_shared": room.is_shared,
    }


@router.delete("/{chatroom_id}")
def delete_chatroom(chatroom_id: str, request: Request, db: Session = Depends(get_db)):
    """Delete chatroom and all its messages (creator only)."""
    token_data = _get_token_data(request)
    if not token_data:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = token_data["id"]

    room = db.query(Chatroom).filter(Chatroom.id == chatroom_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Chatroom not found")

    # Only creator can delete
    if room.creator_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Delete all messages
    db.query(ChatMessage).filter(ChatMessage.chatroom_id == chatroom_id).delete()

    # Delete chatroom
    db.delete(room)
    db.commit()

    return {"status": "Chatroom deleted"}


@router.post("/{chatroom_id}/save-conversation")
def save_conversation(
    chatroom_id: str,
    req: SaveConversationRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Save a conversation (list of messages) to a chatroom."""
    token_data = _get_token_data(request)
    if not token_data:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = token_data["id"]

    room = db.query(Chatroom).filter(Chatroom.id == chatroom_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Chatroom not found")

    # Only creator can save to their chatroom
    if room.creator_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Save all messages
    saved_count = 0
    for msg_data in req.messages:
        msg = ChatMessage(
            chatroom_id=chatroom_id,
            user_id=user_id,
            role=msg_data.role,
            content=msg_data.content,
            response_data=msg_data.response_data,
        )
        db.add(msg)
        saved_count += 1

    room.updated_at = datetime.utcnow()
    db.commit()

    return {
        "status": "Conversation saved",
        "messages_saved": saved_count,
        "chatroom_id": chatroom_id,
    }
