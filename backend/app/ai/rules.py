"""AI Rules Knowledge Base — loads and searches structured sports rules."""
import os
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("sports_analyzer.ai.rules")


class RulesAssistant:
    """
    Loads structured rules from the rules/ knowledge base directory and
    provides keyword-based search across rules, fouls, scoring, and terminology.
    """

    def __init__(self, rules_dir: str):
        self.rules_dir = rules_dir
        self.knowledge: Dict[str, Dict[str, Any]] = {}
        self._load_all_rules()

    def _load_all_rules(self):
        """Loads all rules files for each sport from the knowledge base."""
        if not os.path.exists(self.rules_dir):
            logger.warning(f"Rules directory not found: {self.rules_dir}")
            return

        for sport_dir in os.listdir(self.rules_dir):
            sport_path = os.path.join(self.rules_dir, sport_dir)
            if not os.path.isdir(sport_path):
                continue

            sport_key = sport_dir.lower().replace("-", "_")
            self.knowledge[sport_key] = {
                "rules_md": "",
                "scoring": {},
                "fouls": [],
                "terminology": []
            }

            # Load rules.md
            rules_md_path = os.path.join(sport_path, "rules.md")
            if os.path.exists(rules_md_path):
                with open(rules_md_path, "r", encoding="utf-8") as f:
                    self.knowledge[sport_key]["rules_md"] = f.read()

            # Load JSON files
            for json_name in ["scoring.json", "fouls.json", "terminology.json"]:
                json_path = os.path.join(sport_path, json_name)
                if os.path.exists(json_path):
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        key = json_name.replace(".json", "")
                        self.knowledge[sport_key][key] = data

        logger.info(f"Rules loaded for sports: {list(self.knowledge.keys())}")

    def search_rules(self, sport: str, query: str) -> List[Dict[str, Any]]:
        """
        Searches the knowledge base for a sport using keyword matching.
        Returns a list of relevant matching entries.
        """
        sport_key = sport.lower().replace("-", "_").replace(" ", "_")
        results: List[Dict[str, Any]] = []

        if sport_key not in self.knowledge:
            return results

        kb = self.knowledge[sport_key]
        query_lower = query.lower()
        query_words = set(query_lower.split())

        # Search rules markdown for paragraph-level matches
        if kb.get("rules_md"):
            paragraphs = kb["rules_md"].split("\n\n")
            for para in paragraphs:
                para_lower = para.lower()
                if any(word in para_lower for word in query_words if len(word) > 2):
                    results.append({
                        "source": "rules",
                        "category": "general",
                        "content": para.strip()
                    })

        # Search fouls
        fouls = kb.get("fouls", {})
        foul_list = fouls if isinstance(fouls, list) else fouls.get("fouls", [])
        for foul in foul_list:
            name = foul.get("name", "").lower()
            desc = foul.get("description", "").lower()
            if any(word in name or word in desc for word in query_words if len(word) > 2):
                results.append({
                    "source": "fouls",
                    "category": "foul",
                    "title": foul.get("name", ""),
                    "content": foul.get("description", ""),
                    "penalty": foul.get("penalty", "")
                })

        # Search terminology
        terms = kb.get("terminology", {})
        term_list = terms if isinstance(terms, list) else terms.get("terms", [])
        for term in term_list:
            t = term.get("term", "").lower()
            d = term.get("definition", "").lower()
            if any(word in t or word in d for word in query_words if len(word) > 2):
                results.append({
                    "source": "terminology",
                    "category": "term",
                    "title": term.get("term", ""),
                    "content": term.get("definition", "")
                })

        # Search scoring
        scoring = kb.get("scoring", {})
        if scoring:
            scoring_text = json.dumps(scoring).lower()
            if any(word in scoring_text for word in query_words if len(word) > 2):
                results.append({
                    "source": "scoring",
                    "category": "scoring",
                    "content": scoring
                })

        return results

    def get_all_rules(self, sport: str) -> Dict[str, Any]:
        """Returns all loaded knowledge for a given sport."""
        sport_key = sport.lower().replace("-", "_").replace(" ", "_")
        return self.knowledge.get(sport_key, {})
