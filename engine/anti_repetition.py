##review done
import re
import math
import logging
from typing import List, Tuple, Set

logger = logging.getLogger("adaptive_engine.anti_repetition")

class AntiRepetitionEngine:
    """
    Prevents asking questions or concepts that are too similar to previously asked questions.
    Uses token n-gram Jaccard similarity and concept set overlap with extensible embedding hooks.
    """
    def __init__(self, similarity_threshold: float = 0.65, concept_overlap_threshold: float = 0.70):
        self.similarity_threshold = similarity_threshold
        self.concept_overlap_threshold = concept_overlap_threshold

    def _tokenize(self, text: str) -> List[str]:
        # Lowercase and extract alphanumeric words
        clean = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
        stopwords = {
            "a", "an", "the", "in", "on", "of", "and", "or", "for", "with", "to", "at", "by",
            "is", "are", "was", "were", "be", "been", "being", "how", "what", "why", "when",
            "where", "which", "who", "whom", "this", "that", "these", "those", "you", "your",
            "explain", "describe", "discuss", "would", "could", "should", "can", "tell", "me"
        }
        tokens = [w for w in clean.split() if len(w) > 2 and w not in stopwords]
        return tokens

    def _get_ngrams(self, tokens: List[str], n: int = 2) -> Set[str]:
        if len(tokens) < n:
            return set(tokens)
        return { " ".join(tokens[i:i+n]) for i in range(len(tokens) - n + 1) }

    def compute_text_similarity(self, text1: str, text2: str) -> float:
        """Computes combined unigram and bigram Jaccard similarity."""
        tokens1 = self._tokenize(text1)
        tokens2 = self._tokenize(text2)

        if not tokens1 or not tokens2:
            return 0.0

        set1_uni = set(tokens1)
        set2_uni = set(tokens2)
        jaccard_uni = len(set1_uni & set2_uni) / max(1, len(set1_uni | set2_uni))

        ngrams1 = self._get_ngrams(tokens1, 2)
        ngrams2 = self._get_ngrams(tokens2, 2)
        jaccard_bi = len(ngrams1 & ngrams2) / max(1, len(ngrams1 | ngrams2))

        # Weight bigram overlap higher as it captures exact phrasing
        return 0.4 * jaccard_uni + 0.6 * jaccard_bi

    def compute_concept_overlap(self, new_concepts: List[str], covered_concepts: List[str]) -> float:
        """Computes overlap ratio between new question concepts and already covered concepts."""
        if not new_concepts or not covered_concepts:
            return 0.0

        new_set = {c.strip().lower() for c in new_concepts if c.strip()}
        cov_set = {c.strip().lower() for c in covered_concepts if c.strip()}

        if not new_set:
            return 0.0

        overlap = len(new_set & cov_set)
        return overlap / len(new_set)

    def check_repetition(
        self,
        new_question: str,
        asked_questions: List[str],
        new_concepts: List[str],
        covered_concepts: List[str],
        is_followup: bool = False
    ) -> Tuple[bool, float, str]:
        """
        Evaluates whether a candidate question is a duplicate or overly repetitive.
        Returns: (is_duplicate: bool, max_similarity: float, reason: str)
        """
        if not asked_questions:
            return False, 0.0, "First question, no history."

        max_sim = 0.0
        most_similar_q = ""

        for prev_q in asked_questions:
            sim = self.compute_text_similarity(new_question, prev_q)
            if sim > max_sim:
                max_sim = sim
                most_similar_q = prev_q

        # Follow-ups are allowed to reference the same concepts, but questions shouldn't have high lexical duplicate
        effective_threshold = self.similarity_threshold + (0.15 if is_followup else 0.0)

        if max_sim >= effective_threshold:
            return True, max_sim, f"Question text too similar ({max_sim:.2f}) to previously asked question: '{most_similar_q[:60]}...'"

        if not is_followup:
            concept_overlap = self.compute_concept_overlap(new_concepts, covered_concepts)
            if concept_overlap >= self.concept_overlap_threshold and len(new_concepts) >= 2:
                return True, concept_overlap, f"Concepts ({new_concepts}) overlap heavily ({concept_overlap:.2f}) with already covered concepts."

        return False, max_sim, "Question is novel."
