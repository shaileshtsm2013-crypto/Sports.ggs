"""AI Sports Rules Chatbot API endpoints."""
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.core.config import settings
from backend.app.ai.rules import RulesAssistant
from backend.app.ai.chatbot import SimpleChatbot, GeminiChatbot
from backend.app.ai.rag import RAGEngine

logger = logging.getLogger("sports_analyzer.api.chat")
router = APIRouter(prefix="/api/chat", tags=["chat"])

# Singleton instances
rules_assistant = RulesAssistant(settings.RULES_DIR)
rag_engine = RAGEngine(settings.RULES_DIR)
_simple = SimpleChatbot(rules_assistant)

# Use GeminiChatbot; falls back to SimpleChatbot when no API key
chatbot = GeminiChatbot(
    rules_assistant=rules_assistant,
    rag_engine=rag_engine,
    api_key=getattr(settings, "GEMINI_API_KEY", ""),
    fallback=_simple,
    model="gemini-2.0-flash",
)


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    sport: Optional[str] = "volleyball"
    live_context: Optional[str] = ""  # Serialised live game state from Flutter


class ChatResponse(BaseModel):
    response: str
    sport: str
    sources: Optional[List[Dict[str, Any]]] = None
    provider: str = "offline"  # "gemini" | "offline"


@router.post("/message", response_model=ChatResponse)
async def send_chat_message(request: ChatRequest) -> ChatResponse:
    """Sends a chat message to the sports rules assistant and receives an AI response."""
    messages_payload = [{"role": m.role, "content": m.content} for m in request.messages]
    sport = request.sport or "volleyball"
    live_context = request.live_context or ""

    answer = await chatbot.chat(messages_payload, context=sport, live_context=live_context)

    # Determine which provider produced the answer
    provider = "gemini" if chatbot._client is not None else "offline"

    # Retrieve supplementary RAG contexts
    last_query = request.messages[-1].content if request.messages else ""
    rag_sources = rag_engine.query(last_query, sport=sport, top_k=2)

    return ChatResponse(
        response=answer,
        sport=sport,
        sources=rag_sources,
        provider=provider,
    )


@router.get("/rules/{sport}")
async def get_sport_rules(sport: str) -> Dict[str, Any]:
    """Returns complete rules, fouls, scoring, and terminology for a given sport."""
    rules = rules_assistant.get_all_rules(sport)
    if not rules:
        raise HTTPException(status_code=404, detail=f"Sport '{sport}' not found in knowledge base.")
    return {"sport": sport, "rules": rules}


@router.get("/status")
async def chat_status() -> Dict[str, Any]:
    """Returns the current AI provider status (online/offline)."""
    return {
        "provider": "gemini" if chatbot._client is not None else "offline",
        "model": chatbot.model if hasattr(chatbot, "model") else "keyword",
        "sports_indexed": list(rules_assistant.knowledge.keys()),
        "rag_chunks": len(rag_engine.chunks),
    }
