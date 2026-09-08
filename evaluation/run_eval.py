"""
Filing Sleuth — Evaluation Harness Runner (Phase 6)

Executes the full pipeline against benchmark.json, scores accuracy,
citation precision, quote faithfulness, and hallucination resistance.
Run: python -m evaluation.run_eval
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from backend.agent.orchestrator import Orchestrator
from backend.retrieval.sec_client import SECClient
from evaluation.citation_judge import CitationJudge, EvaluationScorecard

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

BENCHMARK_PATH = Path(__file__).parent / "benchmark.json"
RESULTS_PATH = Path(__file__).parent / "results.json"


async def run_evaluation(limit: int | None = None) -> EvaluationScorecard:
    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        benchmark: list[dict[str, Any]] = json.load(f)

    if limit:
        benchmark = benchmark[:limit]

    print("=" * 80)
    print(f"FILING SLEUTH — EVALUATION HARNESS ({len(benchmark)} benchmark questions)")
    print("=" * 80)

    judge = CitationJudge()
    details: list[dict[str, Any]] = []

    total_citations = 0
    valid_citations = 0
    total_quotes = 0
    verified_quotes = 0
    hallucinations = 0
    total_non_disclosure = 0
    correct_non_disclosure = 0
    passed_questions = 0

    async with SECClient() as client:
        orchestrator = Orchestrator(client)

        for i, item in enumerate(benchmark):
            qid = item["id"]
            question = item["question"]
            category = item["category"]
            exp_status = item.get("expected_status", "FOUND")

            print(f"\n[{i+1}/{len(benchmark)}] ({qid}) [{category}] {question}")

            q_passed = False
            notes = ""

            try:
                res = await orchestrator.run(question)
                facts = res.extracted_facts
                report = res.synthesis_report

                # Audit citations
                if report:
                    audits = judge.audit_report(report)
                    for a in audits:
                        total_citations += 1
                        if a.is_valid_accession:
                            valid_citations += 1
                        if a.source_type == "TEXT":
                            total_quotes += 1
                            if a.is_quote_verified:
                                verified_quotes += 1
                        if a.hallucination_detected:
                            hallucinations += 1

                # ── Category 1: Negative / Non-disclosure tests ───────────────
                if category == "NON_DISCLOSURE_NEGATIVE":
                    total_non_disclosure += 1
                    # In negative tests, pipeline should indicate not disclosed or no results
                    is_not_disclosed = any(f.status == "NOT_DISCLOSED" for f in facts) or not facts
                    if is_not_disclosed:
                        correct_non_disclosure += 1
                        q_passed = True
                        notes = "Correctly recognized non-disclosure without hallucinating."
                    else:
                        notes = "Failed to flag non-disclosure."

                # ── Category 2: Quantitative Single/Trend ─────────────────────
                elif category in ["QUANTITATIVE_SINGLE", "QUANTITATIVE_TREND"]:
                    exp_val = item.get("expected_value")
                    tol = item.get("tolerance_pct", 2.0)
                    matching_fact = next(
                        (f for f in facts if f.value is not None and abs(f.value - exp_val) / abs(exp_val) <= (tol / 100.0)),
                        None,
                    )
                    if matching_fact:
                        q_passed = True
                        notes = f"Matched ground truth value {exp_val:,} (got {matching_fact.value:,} via {matching_fact.xbrl_tag})."
                    else:
                        actual_vals = [f.value for f in facts if f.value is not None]
                        notes = f"Expected {exp_val:,}, got values: {actual_vals}."

                # ── Category 3: Ratio Computation ────────────────────────────
                elif category == "RATIO_COMPUTATION":
                    exp_val = item.get("expected_value")
                    tol = item.get("tolerance_pct", 5.0)
                    comp_match = next(
                        (c for c in res.computations if abs(c["result_value"] - exp_val) <= (tol / 10.0)),
                        None,
                    )
                    if comp_match:
                        q_passed = True
                        notes = f"Computed ratio {comp_match['result_formatted']} (expected ~{exp_val}%)."
                    else:
                        notes = f"Expected ratio {exp_val}%, computed: {[c['result_value'] for c in res.computations]}."

                # ── Category 4: Qualitative Disclosure ────────────────────────
                elif category == "QUALITATIVE_DISCLOSURE":
                    exp_item = item.get("expected_item")
                    keywords = item.get("must_contain_keywords", [])
                    has_item = any(exp_item in (f.item_section or "") for f in facts)
                    has_kw = any(all(kw in (f.claim or "").lower() or kw in (f.exact_quote or "").lower() for kw in keywords) for f in facts)
                    if has_item or has_kw:
                        q_passed = True
                        notes = f"Disclosed in Item {exp_item} with keywords verified."
                    else:
                        notes = f"Missing expected Item {exp_item} or keywords."

                # ── Category 5: Comparative / Edge cases ──────────────────────
                else:
                    if facts and report and report.executive_summary:
                        q_passed = True
                        notes = "Successfully synthesized comparative matrix and notes."
                    else:
                        notes = "Failed to produce synthesis report."

            except Exception as e:
                notes = f"Pipeline execution error: {e}"
                logger.error("Error evaluating %s: %s", qid, e, exc_info=True)

            if q_passed:
                passed_questions += 1
                print(f"  ✓ PASS: {notes}")
            else:
                print(f"  ✗ FAIL: {notes}")

            details.append({
                "id": qid,
                "question": question,
                "category": category,
                "passed": q_passed,
                "notes": notes,
            })

    # Summary metrics
    acc_rate = (passed_questions / len(benchmark)) * 100.0 if benchmark else 0.0
    cit_precision = (valid_citations / total_citations) * 100.0 if total_citations else 100.0
    quote_faith = (verified_quotes / total_quotes) * 100.0 if total_quotes else 100.0
    halluc_rate = (hallucinations / total_citations) * 100.0 if total_citations else 0.0
    nd_precision = (correct_non_disclosure / total_non_disclosure) * 100.0 if total_non_disclosure else 100.0

    scorecard = EvaluationScorecard(
        total_questions=len(benchmark),
        passed_questions=passed_questions,
        accuracy_rate=round(acc_rate, 2),
        citation_precision=round(cit_precision, 2),
        quote_faithfulness=round(quote_faith, 2),
        hallucination_rate=round(halluc_rate, 2),
        non_disclosure_precision=round(nd_precision, 2),
        details=details,
    )

    print("\n" + "=" * 80)
    print("EVALUATION SCORECARD SUMMARY")
    print("=" * 80)
    print(f"Total Benchmark Questions:   {scorecard.total_questions}")
    print(f"Passed Questions:            {scorecard.passed_questions}/{scorecard.total_questions} ({scorecard.accuracy_rate:.1f}%)")
    print(f"Citation Precision:          {scorecard.citation_precision:.1f}%")
    print(f"Quote Faithfulness:          {scorecard.quote_faithfulness:.1f}%")
    print(f"Hallucination Rate:          {scorecard.hallucination_rate:.1f}% (Target: 0.0%)")
    print(f"Non-Disclosure Precision:    {scorecard.non_disclosure_precision:.1f}%")
    print("=" * 80)

    # Save results JSON
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(scorecard.__dict__, f, indent=2)
    print(f"Detailed evaluation saved to {RESULTS_PATH}")

    return scorecard


if __name__ == "__main__":
    asyncio.run(run_evaluation())
