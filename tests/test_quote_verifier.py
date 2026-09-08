"""
Unit tests for backend.verification.quote_verifier.
"""

import pytest
from backend.verification.quote_verifier import QuoteVerifier


def test_exact_quote_verification():
    verifier = QuoteVerifier()
    source = "Apple designs, manufactures and markets smartphones, personal computers, tablets, wearables and accessories."
    quote = "smartphones, personal computers, tablets, wearables"

    res = verifier.verify_quote(quote, source)
    assert res.is_verified is True
    assert res.match_score == 100.0
    assert "Exact" in res.reason


def test_fuzzy_quote_verification_whitespace():
    verifier = QuoteVerifier()
    source = "The company is subject to various\n\nlegal proceedings and claims that have arisen\nin the ordinary course."
    quote = "The company is subject to various legal proceedings and claims that have arisen in the ordinary course."

    res = verifier.verify_quote(quote, source)
    assert res.is_verified is True
    assert res.match_score >= 90.0


def test_hallucination_rejection():
    verifier = QuoteVerifier()
    source = "Total net sales increased 8% during fiscal year 2025 compared to 2024 due to growth in Services."
    fake_quote = "Management announced plans to divest all hardware divisions and focus exclusively on crypto mining."

    res = verifier.verify_quote(fake_quote, source)
    assert res.is_verified is False
    assert res.match_score < 50.0


def test_empty_quote():
    verifier = QuoteVerifier()
    res = verifier.verify_quote("", "Some source text")
    assert res.is_verified is False
