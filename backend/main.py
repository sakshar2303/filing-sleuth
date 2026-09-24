"""
Filing Sleuth — FastAPI Application & WebSocket Server (Phase 7)

Provides REST endpoints and WebSocket streaming for:
- One-click benchmark queries
- Interactive question submission with streaming execution trace
- Investor report synthesis with verified citations and provenance
"""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.agent.orchestrator import Orchestrator, PipelineResult, PipelineTraceStep
from backend.retrieval.sec_client import SECClient
from backend.retrieval.ticker_resolver import TickerResolver

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("filing_sleuth.api")

BENCHMARK_PATH = Path(__file__).resolve().parent.parent / "evaluation" / "benchmark.json"

sec_client_instance: SECClient | None = None
ticker_resolver_instance: TickerResolver | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global sec_client_instance, ticker_resolver_instance
    logger.info("Initializing SECClient instance...")
    async with SECClient() as client:
        sec_client_instance = client
        ticker_resolver_instance = TickerResolver(sec_client_instance)
        yield
    logger.info("Closing SECClient instance...")
    sec_client_instance = None
    ticker_resolver_instance = None


app = FastAPI(
    title="Filing Sleuth API",
    description="Grounded SEC EDGAR Financial Research Agent",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for Vite dev server & frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    question: str
    skeptic_mode: bool = False


def serialize_pipeline_result(res: PipelineResult) -> dict[str, Any]:
    """Serialize PipelineResult into frontend-ready JSON dictionary."""
    return {
        "question": res.question,
        "plan": res.plan.model_dump() if res.plan else None,
        "extracted_facts": [f.model_dump() for f in res.extracted_facts],
        "computations": res.computations,
        "forensic_scorecard": res.forensic_scorecard,
        "financial_dossier": res.financial_dossier,
        "chart_data": res.chart_data,
        "synthesis_report": res.synthesis_report.model_dump() if res.synthesis_report else None,
        "trace": [
            {
                "step_name": s.step_name,
                "description": s.description,
                "data": s.data,
            }
            for s in res.trace
        ],
        "total_chunks_indexed": res.total_chunks_indexed,
        "all_quotes_verified": res.all_quotes_verified,
        "skeptic_mode": res.skeptic_mode,
    }


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "Filing Sleuth API", "version": "1.0.0"}


@app.get("/api/companies")
async def search_companies(q: str = "", limit: int = 8):
    """Autocomplete search over SEC public companies by ticker or name."""
    global sec_client_instance, ticker_resolver_instance
    if not sec_client_instance:
        sec_client_instance = SECClient()
    if not ticker_resolver_instance:
        ticker_resolver_instance = TickerResolver(sec_client_instance)

    try:
        results = await ticker_resolver_instance.search_companies(q, limit=limit)
        return {"companies": results}
    except Exception as e:
        logger.error("Error searching companies: %s", e)
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/benchmark")
async def get_benchmark_questions():
    """Return categorized questions from benchmark.json for 1-click test queries."""
    if not BENCHMARK_PATH.exists():
        raise HTTPException(status_code=404, detail="Benchmark dataset not found.")
    try:
        with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"questions": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query")
async def execute_query(req: QueryRequest):
    """Execute research pipeline synchronously and return complete report."""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    global sec_client_instance
    if not sec_client_instance:
        sec_client_instance = SECClient()

    try:
        orchestrator = Orchestrator(sec_client_instance)
        result = await orchestrator.run(req.question, skeptic_mode=req.skeptic_mode)
        return serialize_pipeline_result(result)
    except Exception as e:
        logger.error("Error executing query: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/query")
async def websocket_query(websocket: WebSocket):
    """Streaming WebSocket endpoint that emits live reasoning trace steps as they happen."""
    await websocket.accept()
    global sec_client_instance
    if not sec_client_instance:
        sec_client_instance = SECClient()

    try:
        while True:
            data_str = await websocket.receive_text()
            data = json.loads(data_str)
            question = data.get("question", "").strip()
            skeptic_mode = bool(data.get("skeptic_mode", False))

            if not question:
                await websocket.send_json({"type": "error", "message": "Empty question received."})
                continue

            async def stream_trace_step(step: PipelineTraceStep) -> None:
                await websocket.send_json({
                    "type": "trace",
                    "step_name": step.step_name,
                    "description": step.description,
                    "data": step.data,
                })

            orchestrator = Orchestrator(sec_client_instance)
            result = await orchestrator.run(question, on_trace_step=stream_trace_step, skeptic_mode=skeptic_mode)

            await websocket.send_json({
                "type": "result",
                "data": serialize_pipeline_result(result),
            })

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception as e:
        logger.error("WebSocket error: %s", e, exc_info=True)
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
