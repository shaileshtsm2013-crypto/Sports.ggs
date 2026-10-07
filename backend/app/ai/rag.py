"""Retrieval-Augmented Generation (RAG) engine for sports rules documents."""
import os
import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("sports_analyzer.ai.rag")


class DocumentChunk:
    """Represents a text chunk with metadata for retrieval."""

    def __init__(self, content: str, sport: str, source: str, metadata: Optional[Dict[str, Any]] = None):
        self.content = content.strip()
        self.sport = sport.lower()
        self.source = source
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "sport": self.sport,
            "source": self.source,
            "metadata": self.metadata,
        }


class RAGEngine:
    """
    Lightweight, dependency-free local RAG index using token-overlap / BM25-style scoring.
    Indexes markdown rules, terminology, and foul specifications.
    """

    def __init__(self, rules_dir: str):
        self.rules_dir = rules_dir
        self.chunks: List[DocumentChunk] = []
        self._build_index()

    def _build_index(self):
        """Indexes all text and JSON files across sport directories."""
        if not os.path.exists(self.rules_dir):
            logger.warning(f"Rules directory not found for RAG: {self.rules_dir}")
            return

        import json as _json

        for sport_name in os.listdir(self.rules_dir):
            sport_path = os.path.join(self.rules_dir, sport_name)
            if not os.path.isdir(sport_path):
                continue

            # Index rules.md by markdown sections
            rules_md = os.path.join(sport_path, "rules.md")
            if os.path.exists(rules_md):
                with open(rules_md, "r", encoding="utf-8") as f:
                    text = f.read()
                sections = re.split(r"\n(?=#{1,3}\s)", text)
                for sec in sections:
                    if sec.strip():
                        self.chunks.append(DocumentChunk(
                            content=sec.strip(),
                            sport=sport_name,
                            source="rules.md",
                        ))

            # Index fouls.json
            fouls_path = os.path.join(sport_path, "fouls.json")
            if os.path.exists(fouls_path):
                with open(fouls_path, "r", encoding="utf-8") as f:
                    fouls_data = _json.load(f)
                foul_list = fouls_data if isinstance(fouls_data, list) else fouls_data.get("fouls", [])
                for foul in foul_list:
                    name = foul.get("name", "")
                    desc = foul.get("description", "")
                    penalty = foul.get("penalty", "")
                    text = f"Foul: {name}. {desc}"
                    if penalty:
                        text += f" Penalty: {penalty}"
                    if text.strip():
                        self.chunks.append(DocumentChunk(
                            content=text.strip(),
                            sport=sport_name,
                            source="fouls.json",
                            metadata={"name": name, "penalty": penalty},
                        ))

            # Index scoring.json
            scoring_path = os.path.join(sport_path, "scoring.json")
            if os.path.exists(scoring_path):
                with open(scoring_path, "r", encoding="utf-8") as f:
                    scoring_data = _json.load(f)
                scoring_text = "Scoring rules: " + "; ".join(
                    f"{k.replace('_', ' ')}: {v}" for k, v in scoring_data.items()
                    if not isinstance(v, (dict, list))
                )
                if scoring_text.strip():
                    self.chunks.append(DocumentChunk(
                        content=scoring_text.strip(),
                        sport=sport_name,
                        source="scoring.json",
                    ))

            # Index terminology.json
            terms_path = os.path.join(sport_path, "terminology.json")
            if os.path.exists(terms_path):
                with open(terms_path, "r", encoding="utf-8") as f:
                    terms_data = _json.load(f)
                term_list = terms_data if isinstance(terms_data, list) else terms_data.get("terms", [])
                for term in term_list:
                    t = term.get("term", "")
                    d = term.get("definition", "")
                    if t and d:
                        self.chunks.append(DocumentChunk(
                            content=f"{t}: {d}",
                            sport=sport_name,
                            source="terminology.json",
                        ))

        logger.info(f"RAG Engine indexed {len(self.chunks)} chunks across all sports.")

    def query(self, query_text: str, sport: Optional[str] = None, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieves top_k most relevant chunks matching query tokens.
        """
        query_tokens = set(re.findall(r"\w+", query_text.lower()))
        if not query_tokens:
            return []

        scored_chunks = []
        for chunk in self.chunks:
            if sport and chunk.sport != sport.lower():
                continue

            chunk_tokens = re.findall(r"\w+", chunk.content.lower())
            chunk_token_set = set(chunk_tokens)

            # Jaccard + frequency match score
            overlap = query_tokens.intersection(chunk_token_set)
            if not overlap:
                continue

            score = sum(chunk_tokens.count(t) for t in overlap) / (len(chunk_tokens) + 1e-5)
            scored_chunks.append((score, chunk))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        return [chunk.to_dict() for _, chunk in scored_chunks[:top_k]]
