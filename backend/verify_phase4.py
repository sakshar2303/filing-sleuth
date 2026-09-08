"""
Filing Sleuth — Phase 4 Verification Script

Verifies Query Planner, Extraction Agent, Quote Verifier, and Orchestrator
against real SEC filings.
Run: python -m backend.verify_phase4
"""

from __future__ import annotations

import asyncio
import logging

from backend.agent.orchestrator import Orchestrator
from backend.retrieval.sec_client import SECClient
from backend.verification.quote_verifier import QuoteVerifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def main():
    print("=" * 70)
    print("FILING SLEUTH — Phase 4 Verification")
    print("Testing Query Planner, Extraction Agent, Quote Verifier, & Orchestrator")
    print("=" * 70)

    all_pass = True

    # ── Test 1: Quote Verifier Unit Check ──────────────────────────────────────
    print("\n" + "─" * 70)
    print("TEST 1: Quote Verifier Grounding & Hallucination Resistance")
    print("─" * 70)

    verifier = QuoteVerifier()
    source_sample = (
        "Microsoft plays a central role in the world’s digital ecosystem. "
        "We have made it a top corporate priority to protect the company, our customers, "
        "and our partners from cybersecurity threats."
    )

    # Legitimate quote
    legit_quote = "protect the company, our customers, and our partners from cybersecurity threats"
    res_legit = verifier.verify_quote(legit_quote, source_sample)
    print(f"Legitimate Quote Test: Verified={res_legit.is_verified} (Score: {res_legit.match_score}%)")
    if not res_legit.is_verified:
        print("  ✗ Failed legitimate quote test")
        all_pass = False
    else:
        print("  ✓ PASS: Legitimate quote verified")

    # Hallucinated quote
    fake_quote = "Microsoft has decided to discontinue Windows and migrate exclusively to Linux distributions."
    res_fake = verifier.verify_quote(fake_quote, source_sample)
    print(f"Hallucination Test: Verified={res_fake.is_verified} (Score: {res_fake.match_score}%)")
    if res_fake.is_verified:
        print("  ✗ Failed hallucination resistance test (hallucinated quote was accepted!)")
        all_pass = False
    else:
        print("  ✓ PASS: Hallucinated quote properly rejected")

    # ── Test 2: End-to-End Orchestrator: Quantitative + Ratios ──────────────────
    print("\n" + "─" * 70)
    print("TEST 2: End-to-End Quantitative Pipeline (AAPL R&D as % of Revenue)")
    print("─" * 70)

    async with SECClient() as client:
        orchestrator = Orchestrator(client)

        q1 = "What was Apple's R&D spend as a percent of revenue over the last 2 years?"
        res1 = await orchestrator.run(q1)

        print(f"Question: \"{res1.question}\"")
        print(f"Plan Intent: {res1.plan.intent} | Sub-questions: {len(res1.plan.sub_questions)}")
        print(f"Extracted Facts: {len(res1.extracted_facts)}")

        for fact in res1.extracted_facts:
            print(f"  [{fact.sub_question_id}] {fact.claim} | Source: {fact.source_type} ({fact.xbrl_tag})")

        print(f"\nComputations ({len(res1.computations)}):")
        for comp in res1.computations:
            print(f"  {comp['description']} (Ratio: {comp['result_formatted']})")

        if not res1.extracted_facts:
            print("  ✗ No facts extracted")
            all_pass = False
        elif not res1.computations:
            print("  ✗ No ratio computations performed")
            all_pass = False
        else:
            print("  ✓ PASS: Extracted XBRL facts and computed verified ratios")

        # ── Test 3: End-to-End Orchestrator: Qualitative + Quote Verification ────
        print("\n" + "─" * 70)
        print("TEST 3: End-to-End Qualitative Pipeline (MSFT Cybersecurity Disclosures)")
        print("─" * 70)

        q2 = "What cybersecurity risk management strategy did Microsoft disclose in its 10-K?"
        res2 = await orchestrator.run(q2)

        print(f"Question: \"{res2.question}\"")
        print(f"Extracted Facts: {len(res2.extracted_facts)}")

        for fact in res2.extracted_facts:
            print(f"  Claim: {fact.claim}")
            print(f"  Section: {fact.item_section}")
            print(f"  Source Type: {fact.source_type}")
            print(f"  Exact Quote: \"{fact.exact_quote}\"")
            print(f"  Quote Verified: {fact.quote_verified} (Score: {fact.quote_verification_score}%)")

        if not res2.extracted_facts:
            print("  ✗ No qualitative facts extracted")
            all_pass = False
        elif not any(f.quote_verified for f in res2.extracted_facts):
            print("  ✗ No quote was verified")
            all_pass = False
        else:
            print("  ✓ PASS: Qualitative disclosure extracted with verified quote")

    print("\n" + "=" * 70)
    print("RESULT:", "✓ ALL PHASE 4 TESTS PASS" if all_pass else "⚠ SOME TESTS FAILED")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
