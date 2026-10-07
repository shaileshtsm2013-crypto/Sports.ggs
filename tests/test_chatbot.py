"""Tests for AI chatbot, RAG engine, and chat API endpoint (Phase 6)."""
import pytest
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.ai.rules import RulesAssistant
from backend.app.ai.rag import RAGEngine, DocumentChunk
from backend.app.ai.chatbot import SimpleChatbot, GeminiChatbot, AIProvider


# ── Fixtures ───────────────────────────────────────────────────────────

RULES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rules")


@pytest.fixture
def rules_assistant():
    return RulesAssistant(RULES_DIR)


@pytest.fixture
def rag_engine():
    return RAGEngine(RULES_DIR)


@pytest.fixture
def simple_chatbot(rules_assistant):
    return SimpleChatbot(rules_assistant)


@pytest.fixture
def gemini_chatbot_offline(rules_assistant, rag_engine, simple_chatbot):
    """GeminiChatbot with no API key — always falls back to SimpleChatbot."""
    return GeminiChatbot(
        rules_assistant=rules_assistant,
        rag_engine=rag_engine,
        api_key="",
        fallback=simple_chatbot,
    )


# ── AIProvider abstract ───────────────────────────────────────────────

class TestAIProvider:
    def test_abstract_cannot_instantiate(self):
        with pytest.raises(TypeError):
            AIProvider()


# ── SimpleChatbot ─────────────────────────────────────────────────────

class TestSimpleChatbot:
    def test_empty_messages_returns_greeting(self, simple_chatbot):
        result = asyncio.get_event_loop().run_until_complete(
            simple_chatbot.chat([], context="volleyball")
        )
        assert "Sports Analyzer AI" in result

    def test_chat_returns_relevant_results(self, simple_chatbot):
        messages = [{"role": "user", "content": "What are the scoring rules?"}]
        result = asyncio.get_event_loop().run_until_complete(
            simple_chatbot.chat(messages, context="volleyball")
        )
        # Should find something about volleyball
        assert len(result) > 50

    def test_chat_no_match_returns_fallback(self, simple_chatbot):
        messages = [{"role": "user", "content": "xyznonexistent123"}]
        result = asyncio.get_event_loop().run_until_complete(
            simple_chatbot.chat(messages, context="volleyball")
        )
        assert "couldn't find" in result.lower() or "try asking" in result.lower()

    def test_chat_kabaddi_context(self, simple_chatbot):
        messages = [{"role": "user", "content": "raider rules"}]
        result = asyncio.get_event_loop().run_until_complete(
            simple_chatbot.chat(messages, context="kabaddi")
        )
        # Should reference kabaddi in some form
        assert len(result) > 20

    def test_chat_accepts_live_context(self, simple_chatbot):
        """Ensure live_context param is accepted (offline ignores it)."""
        messages = [{"role": "user", "content": "scoring"}]
        result = asyncio.get_event_loop().run_until_complete(
            simple_chatbot.chat(messages, context="volleyball", live_context="Rally state: ACTIVE")
        )
        assert isinstance(result, str) and len(result) > 0


# ── RAG Engine ─────────────────────────────────────────────────────────

class TestRAGEngine:
    def test_index_builds_chunks(self, rag_engine):
        assert len(rag_engine.chunks) > 0

    def test_query_returns_relevant_chunks(self, rag_engine):
        results = rag_engine.query("scoring rules", sport="volleyball", top_k=3)
        assert len(results) > 0
        assert "content" in results[0]

    def test_query_filters_by_sport(self, rag_engine):
        results = rag_engine.query("raider", sport="kabaddi", top_k=3)
        for r in results:
            assert r["sport"] == "kabaddi"

    def test_query_empty_returns_empty(self, rag_engine):
        results = rag_engine.query("", top_k=3)
        assert results == []

    def test_document_chunk_to_dict(self):
        chunk = DocumentChunk(content="Test rule", sport="volleyball", source="rules.md")
        d = chunk.to_dict()
        assert d["content"] == "Test rule"
        assert d["sport"] == "volleyball"
        assert d["source"] == "rules.md"


# ── GeminiChatbot (offline fallback) ──────────────────────────────────

class TestGeminiChatbot:
    def test_no_api_key_falls_back(self, gemini_chatbot_offline):
        """With no API key, _client should be None."""
        assert gemini_chatbot_offline._client is None

    def test_offline_fallback_works(self, gemini_chatbot_offline):
        messages = [{"role": "user", "content": "What are fouls in volleyball?"}]
        result = asyncio.get_event_loop().run_until_complete(
            gemini_chatbot_offline.chat(messages, context="volleyball")
        )
        assert isinstance(result, str)
        assert len(result) > 20

    def test_sport_display_names(self, gemini_chatbot_offline):
        assert "FIVB" in gemini_chatbot_offline.sport_display_names["volleyball"]
        assert "IKF" in gemini_chatbot_offline.sport_display_names["kabaddi"]
        assert "KKFI" in gemini_chatbot_offline.sport_display_names["kho_kho"]

    def test_system_template_has_placeholders(self, gemini_chatbot_offline):
        tmpl = gemini_chatbot_offline._SYSTEM_TEMPLATE
        assert "{sport_display}" in tmpl
        assert "{rules_context}" in tmpl
        assert "{live_section}" in tmpl


# ── Chat API endpoint ────────────────────────────────────────────────

class TestChatAPI:
    def test_chat_endpoint_import(self):
        from backend.app.api.chat import router, ChatRequest, ChatResponse
        assert router.prefix == "/api/chat"

    def test_chat_request_schema(self):
        from backend.app.api.chat import ChatRequest, ChatMessage
        req = ChatRequest(
            messages=[ChatMessage(role="user", content="hello")],
            sport="kabaddi",
            live_context="Raid active",
        )
        assert req.sport == "kabaddi"
        assert req.live_context == "Raid active"

    def test_chat_response_schema(self):
        from backend.app.api.chat import ChatResponse
        resp = ChatResponse(response="hi", sport="volleyball", provider="offline")
        assert resp.provider == "offline"
        assert resp.sport == "volleyball"

    def test_chat_status_endpoint_exists(self):
        from backend.app.api.chat import router
        paths = [r.path for r in router.routes]
        assert "/api/chat/status" in paths
