"""AI Chatbot module — abstract provider, offline SimpleChatbot, and GeminiChatbot."""
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from backend.app.ai.rules import RulesAssistant

logger = logging.getLogger("sports_analyzer.ai.chatbot")


class AIProvider(ABC):
    """Abstract base class for AI chat providers (OpenAI, Gemini, Local LLM, etc.)."""

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        context: str = "",
        live_context: str = "",
    ) -> str:
        pass


class SimpleChatbot(AIProvider):
    """
    Keyword-based rules chatbot that works fully offline without any API key.
    Searches the structured knowledge base and formats helpful answers.
    """

    def __init__(self, rules_assistant: RulesAssistant):
        self.rules_assistant = rules_assistant
        self.sport_display_names = {
            "volleyball": "Volleyball",
            "kabaddi": "Kabaddi",
            "kho_kho": "Kho Kho",
        }

    async def chat(
        self,
        messages: List[Dict[str, str]],
        context: str = "",
        live_context: str = "",
    ) -> str:
        """Process the last user message, search rules, and produce a helpful response."""
        if not messages:
            return (
                "Hello! I'm the Sports Analyzer AI Rules Assistant. "
                "Ask me about the rules of Volleyball, Kabaddi, or Kho Kho."
            )

        last_message = ""
        sport = context if context else "volleyball"
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_message = msg.get("content", "")
                break

        if not last_message:
            return "I didn't catch that. Could you ask a specific question about the rules?"

        results = self.rules_assistant.search_rules(sport, last_message)
        sport_name = self.sport_display_names.get(sport, sport.title())

        if not results:
            return (
                f"I couldn't find specific information about that in the {sport_name} rules database. "
                f"Try asking about scoring, fouls, terminology, or specific rules. "
                f"For example: 'What is a rotation fault?' or 'How does scoring work?'"
            )

        response_parts = [f"Here's what I found about **{sport_name}**:\n"]
        seen_content: set = set()

        for r in results[:5]:
            category = r.get("category", "general")
            title = r.get("title", "")
            content = r.get("content", "")
            penalty = r.get("penalty", "")

            if category == "term" and title:
                response_parts.append(f"**{title}**: {content}")
            elif category == "foul" and title:
                response_parts.append(f"**{title}** (Foul): {content}")
                if penalty:
                    response_parts.append(f"  *Penalty*: {penalty}")
            elif category == "scoring":
                if isinstance(content, dict):
                    scoring_lines = [
                        f"  - {k.replace('_', ' ').title()}: {v}" for k, v in content.items()
                    ]
                    response_parts.append("**Scoring Rules**:\n" + "\n".join(scoring_lines))
                else:
                    response_parts.append(str(content))
            elif category == "general" and content:
                content_key = content[:80]
                if content_key not in seen_content:
                    response_parts.append(content)
                    seen_content.add(content_key)

        response_parts.append(
            f"\n*Source: {sport_name} Official Rules Knowledge Base. "
            f"Rules may vary by federation/competition level.*"
        )
        return "\n\n".join(response_parts)


class GeminiChatbot(AIProvider):
    """
    Gemini API-backed chatbot (gemini-2.0-flash) via google.genai SDK.
    Uses RAG-retrieved rule chunks as system context.
    Falls back to SimpleChatbot on missing API key or any API error.
    """

    _SYSTEM_TEMPLATE = """\
You are an expert AI sports analyst and rules referee assistant for the Sports Analyzer AI platform.
You have deep, authoritative knowledge of:
  - Volleyball (FIVB official rules)
  - Kabaddi (IKF official rules)
  - Kho Kho (KKFI official rules)

Current active sport: {sport_display}
{live_section}
Relevant rules context retrieved for this query:
{rules_context}

Response guidelines:
- Be concise and accurate; cite the relevant federation when referencing a rule.
- Use **bold** for rule names and bullet points for lists.
- Reference live game data when provided to give contextual commentary.
- Keep responses under 350 words unless detailed analysis is explicitly requested.
- If the question is out of scope or unclear, ask for clarification.
"""

    def __init__(
        self,
        rules_assistant: RulesAssistant,
        rag_engine: Any,
        api_key: str,
        fallback: SimpleChatbot,
        model: str = "gemini-2.0-flash",
    ):
        self.rules_assistant = rules_assistant
        self.rag_engine = rag_engine
        self.api_key = api_key
        self.fallback = fallback
        self.model = model
        self._client: Optional[Any] = None
        self.sport_display_names = {
            "volleyball": "Volleyball (FIVB)",
            "kabaddi": "Kabaddi (IKF)",
            "kho_kho": "Kho Kho (KKFI)",
        }
        self._init_client()

    def _init_client(self) -> None:
        if not self.api_key:
            logger.info("GeminiChatbot: No GEMINI_API_KEY — will use offline fallback.")
            return
        try:
            from google import genai  # type: ignore
            self._client = genai.Client(api_key=self.api_key)
            logger.info(f"GeminiChatbot: Gemini client ready (model={self.model}).")
        except Exception as exc:
            logger.warning(f"GeminiChatbot: init failed ({exc}) — offline fallback active.")
            self._client = None

    async def chat(
        self,
        messages: List[Dict[str, str]],
        context: str = "",
        live_context: str = "",
    ) -> str:
        if self._client is None:
            return await self.fallback.chat(messages, context=context, live_context=live_context)

        sport = context if context else "volleyball"
        sport_display = self.sport_display_names.get(sport, sport.title())

        # Grab last user message for RAG
        last_user = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user = msg.get("content", "")
                break

        # Retrieve RAG context
        rag_hits = self.rag_engine.query(last_user, sport=sport, top_k=3)
        rules_ctx = (
            "\n\n".join(h["content"] for h in rag_hits)
            if rag_hits
            else "No specific rule chunks retrieved."
        )

        live_section = f"Live game context:\n{live_context}\n" if live_context else ""

        system_prompt = self._SYSTEM_TEMPLATE.format(
            sport_display=sport_display,
            live_section=live_section,
            rules_context=rules_ctx,
        )

        try:
            from google import genai  # type: ignore
            from google.genai import types  # type: ignore

            contents = []
            for msg in messages:
                role = msg.get("role", "user")
                if role == "system":
                    continue
                gemini_role = "user" if role == "user" else "model"
                contents.append(
                    types.Content(
                        role=gemini_role,
                        parts=[types.Part(text=msg.get("content", ""))],
                    )
                )

            response = self._client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.3,
                    max_output_tokens=512,
                ),
            )
            return response.text or "I couldn't generate a response. Please try again."

        except Exception as exc:
            logger.warning(f"GeminiChatbot.chat error — falling back: {exc}")
            return await self.fallback.chat(messages, context=context, live_context=live_context)
