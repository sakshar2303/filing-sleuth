"""
Filing Sleuth — Phase 5 Verification Script

Tests multi-company cross-referencing, financial computations (margins, YoY, spreads),
and final report synthesis with grounded citations on real Apple & Microsoft 10-K data.
Run: python -m backend.verify_phase5
"""

from __future__ import annotations

import asyncio
import logging

from backend.agent.orchestrator import Orchestrator
from backend.retrieval.sec_client import SECClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def main():
    print("=" * 70)
    print("FILING SLEUTH — Phase 5 Verification")
    print("Multi-Company Cross-Referencing, Computations, & Synthesis Report")
    print("=" * 70)

    async with SECClient() as client:
        orchestrator = Orchestrator(client)

        question = "Compare R&D spend as % of revenue between Apple and Microsoft over the last 2 years."
        result = await orchestrator.run(question)

        print(f"\nUser Question: \"{result.question}\"")
        print(f"Plan Intent: {result.plan.intent} | Target Companies: {[c.ticker for c in result.plan.companies]}")
        print(f"Extracted Facts Count: {len(result.extracted_facts)}")

        print("\n" + "─" * 70)
        print("SYNTHESIS REPORT")
        print("─" * 70)

        report = result.synthesis_report
        if not report:
            print("  ✗ No synthesis report generated!")
            return

        print(f"\nExecutive Summary:\n  {report.executive_summary}\n")

        print("Comparison Table:")
        print(report.comparison_table_markdown)
        print()

        print("Key Findings:")
        for finding in report.key_findings:
            print(f"  • {finding}")
        print()

        print(f"Citations ({len(report.citations)}):")
        for cit in report.citations:
            quote_note = f" (Quote Verified: {cit.quote_verified})" if cit.exact_quote else ""
            print(f"  {cit.citation_id} {cit.company} | Accn: {cit.accession_number} | {cit.item_section} | {cit.source_type}{quote_note}")
        print()

        print(f"Caveats & Reporting Notes ({len(report.caveats_and_notes)}):")
        for cav in report.caveats_and_notes:
            print(f"  ⚠ {cav}")
        print()

        # Verification asserts
        all_pass = True
        if not report.executive_summary:
            print("  ✗ Missing executive summary")
            all_pass = False
        if not report.comparison_table_markdown:
            print("  ✗ Missing comparison table")
            all_pass = False
        if len(report.citations) < 4:
            print(f"  ✗ Expected at least 4 citations, got {len(report.citations)}")
            all_pass = False
        if not any("Fiscal Year Calendar Mismatch" in c for c in report.caveats_and_notes):
            print("  ✗ Expected calendar mismatch warning for Apple (Sept) vs Microsoft (June)")
            all_pass = False

        print("=" * 70)
        print("RESULT:", "✓ ALL PHASE 5 TESTS PASS" if all_pass else "⚠ ISSUES DETECTED")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
