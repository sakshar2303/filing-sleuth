"""
Filing Sleuth — Quote Verifier

Verifies that exact quotes produced by extraction agents actually exist
in the retrieved filing chunk text. Prevents hallucinated quotations.

Uses:
1. Exact substring matching (normalized whitespace).
2. Fuzzy sliding-window matching via thefuzz (to tolerate minor HTML entity
   or whitespace stripping differences).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from thefuzz import fuzz

logger = logging.getLogger(__name__)

DEFAULT_VERIFICATION_THRESHOLD = 80.0  # Percentage similarity threshold


@dataclass
class QuoteVerificationResult:
    """Result of quote verification against source chunk text."""
    is_verified: bool
    match_score: float         # 0.0 to 100.0
    quote: str
    matched_snippet: str | None = None
    char_offset_start: int | None = None
    char_offset_end: int | None = None
    reason: str = ""


def _normalize_text(text: str) -> str:
    """Normalize whitespace and punctuation for quote comparison."""
    text = re.sub(r"\s+", " ", text).strip()
    # Normalize fancy quotes and dashes
    text = text.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    text = text.replace("—", "-").replace("–", "-")
    return text


class QuoteVerifier:
    """Verifies that quotes cited from SEC filings are authentic.

    Usage:
        verifier = QuoteVerifier()
        result = verifier.verify_quote(
            quote="The Company is subject to legal proceedings...",
            source_text=chunk.text,
        )
        if not result.is_verified:
            logger.warning("Hallucinated quote detected!")
    """

    def __init__(self, threshold: float = DEFAULT_VERIFICATION_THRESHOLD) -> None:
        self.threshold = threshold

    def verify_quote(
        self,
        quote: str,
        source_text: str,
    ) -> QuoteVerificationResult:
        """Verify if quote is present in source_text.

        Args:
            quote: The claim's exact quote string.
            source_text: The full text of the source SectionChunk.

        Returns:
            QuoteVerificationResult detailing verification status and match score.
        """
        if not quote or not quote.strip():
            return QuoteVerificationResult(
                is_verified=False,
                match_score=0.0,
                quote=quote,
                reason="Empty quote provided",
            )

        norm_quote = _normalize_text(quote)
        norm_source = _normalize_text(source_text)

        # 1. Fast exact substring match
        idx = norm_source.find(norm_quote)
        if idx != -1:
            snippet = norm_source[idx:idx + len(norm_quote)]
            return QuoteVerificationResult(
                is_verified=True,
                match_score=100.0,
                quote=quote,
                matched_snippet=snippet,
                char_offset_start=idx,
                char_offset_end=idx + len(norm_quote),
                reason="Exact substring match",
            )

        # 2. Case-insensitive exact substring match
        lower_source = norm_source.lower()
        lower_quote = norm_quote.lower()
        idx_case = lower_source.find(lower_quote)
        if idx_case != -1:
            snippet = norm_source[idx_case:idx_case + len(norm_quote)]
            return QuoteVerificationResult(
                is_verified=True,
                match_score=98.0,
                quote=quote,
                matched_snippet=snippet,
                char_offset_start=idx_case,
                char_offset_end=idx_case + len(norm_quote),
                reason="Case-insensitive exact match",
            )

        # 3. Fuzzy match: check partial ratio & token set ratio
        partial_score = float(fuzz.partial_ratio(norm_quote, norm_source))
        token_set_score = float(fuzz.token_set_ratio(norm_quote, norm_source))
        best_score = max(partial_score, token_set_score)

        # Locate best matching sliding window
        window_size = len(norm_quote)
        best_window = None
        best_win_score = 0.0
        best_win_start = 0

        # Step by 10% of window size for speed
        step = max(1, window_size // 10)
        for w_start in range(0, max(1, len(norm_source) - window_size + 1), step):
            window = norm_source[w_start:w_start + window_size]
            w_score = float(fuzz.ratio(norm_quote, window))
            if w_score > best_win_score:
                best_win_score = w_score
                best_window = window
                best_win_start = w_start

        effective_score = max(best_score, best_win_score)
        is_verified = effective_score >= self.threshold

        reason = (
            f"Fuzzy match score: {effective_score:.1f}% (threshold: {self.threshold:.1f}%)"
            if is_verified
            else f"Quote not found in source text (score: {effective_score:.1f}% < {self.threshold:.1f}%)"
        )

        return QuoteVerificationResult(
            is_verified=is_verified,
            match_score=effective_score,
            quote=quote,
            matched_snippet=best_window,
            char_offset_start=best_win_start if is_verified else None,
            char_offset_end=(best_win_start + window_size) if is_verified else None,
            reason=reason,
        )
