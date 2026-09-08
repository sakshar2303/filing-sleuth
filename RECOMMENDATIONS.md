# Filing Sleuth — Future Enhancements & Feature Roadmap

This document outlines high-impact architectural and product recommendations to expand **Filing Sleuth** from an end-to-end SEC EDGAR research agent into an institutional-grade financial intelligence platform.

---

## Current Foundation (Completed Phases 1–9)

* **Data Foundations**: Direct SEC EDGAR REST API integration, ticker-to-CIK resolution, Submissions API, CompanyFacts XBRL engine, and disk caching.
* **Structure-Aware 10-K Parsing**: HTML cleaner with financial table schema preservation, 10-K Item boundary detection (Item 1, 1A, 7, 8), and running header suppression.
* **Hybrid Retrieval (RRF)**: SentenceTransformers (`all-MiniLM-L6-v2`) dense vector store in ChromaDB combined with sparse Okapi BM25 keyword search via Reciprocal Rank Fusion.
* **Extraction & Auditability**: Query Planner for atomic sub-question routing, XBRL machine-readable fact extraction, and sliding-window fuzzy quote verification (>85% Levenshtein threshold).
* **Cross-Company Synthesis**: Fiscal year calendar mismatch detection, deterministic Python financial computation, and markdown report synthesis with provenance footnotes.
* **Evaluation & Accuracy**: 20/20 benchmark passed (100% precision, 100% quote faithfulness, 0% hallucination) with 57 unit tests.
* **Frontend**: React + Vite application with Oceanic Deep Teal light theme, live WebSocket streaming reasoning trace, interactive citation drawer, and 4-tab methodology guide.

---

## Recommended Next Features

### 1. Interactive Financial Visualizations (High Priority)
* **Goal**: Automatically render interactive financial charts when queries return quantitative trends or multi-company comparisons.
* **Analyst Value**: Visualizing metrics side-by-side with official XBRL data points and fiscal mismatch warnings instantly makes reports executive- and investor-ready.
* **Technical Details**:
  * **Frontend**: Integrate `recharts` or lightweight Canvas/SVG visualizations into `ResultReport.jsx`.
  * **Bar Charts**: Peer comparison metrics (e.g., Apple vs. Microsoft R&D % of revenue with peer margin spread callout).
  * **Line & Area Charts**: Longitudinal multi-year trends (e.g., Tesla regulatory credits across FY2021, FY2022, FY2023 with YoY growth rates).
  * **Data Contract**: Backend orchestrator tags quantitative synthesis results with structured JSON chart payloads (`chart_type: "trend" | "comparison"`, data points, units, and series).
* **Effort**: Low–Medium (1–2 days) | **Impact**: Very High

---

### 2. One-Click Report Export (PDF, Markdown & Audit Excel)
* **Goal**: Enable equity research analysts and auditors to export research outputs with full provenance.
* **Analyst Value**: In real investment banking, equity research, and compliance workflows, analysts must attach evidence packets to investment memos.
* **Technical Details**:
  * **Executive PDF**: Formal letterhead, company metadata, comparison tables, verified quotes, and bibliography footnotes via `@react-pdf/renderer` or browser print stylesheets.
  * **Financial Memo (Markdown)**: Clean, copy-pasteable Markdown ready for Notion, Obsidian, or investment committee docs.
  * **Audit Excel / CSV**: Tabular workbook containing raw XBRL tag names, values, units, fiscal period end dates, accession numbers, and character offsets for every data point.
* **Effort**: Low (1 day) | **Impact**: High

---

### 3. Side-by-Side 10-K Redline & Disclosure Diff Viewer
* **Goal**: Provide an interactive tool to compare disclosures between consecutive fiscal years (e.g., 2022 vs. 2023).
* **Analyst Value**: Directly answers: *"What specific risk factors did management quietly add, modify, or remove this year?"*
* **Technical Details**:
  * **Backend**: Add `backend/diffing/disclosure_diff.py` using Myers diff or sentence-level semantic alignment to compare Item 1A (Risk Factors) or Item 7 (MD&A) across two accession numbers.
  * **Frontend**: Split-screen or unified redline viewer highlighting added text in green/emerald and deleted clauses in rose/red.
  * **Classification**: Classify changes into material additions (new regulatory risks, geopolitical factors) vs. routine boilerplate edits.
* **Effort**: Medium (2–3 days) | **Impact**: Very High

---

### 4. SEC EDGAR Live Ticker Autocomplete & Company Directory
* **Goal**: Provide an intelligent search bar dropdown with fuzzy search across the ~10,000 SEC EDGAR public companies.
* **Analyst Value**: Eliminates ticker guesswork, confirms company coverage, and displays fiscal year-end month before running queries.
* **Technical Details**:
  * **Backend**: Expose `/api/companies?q={search}` querying the pre-cached SEC `company_tickers.json`.
  * **Frontend**: Combobox / Autocomplete dropdown with keyboard navigation in `QueryInput.jsx`.
  * **Metadata Card**: Displays CIK, industry SIC code, state of incorporation, and fiscal calendar (e.g., "Fiscal Year Ends: September 30").
* **Effort**: Low (1 day) | **Impact**: Medium–High

---

### 5. 10-Q (Quarterly) & 8-K (Material Events) Ingestion
* **Goal**: Expand the ingestion engine beyond annual 10-Ks to support quarterly seasonality and intra-year corporate events.
* **Analyst Value**: Allows intra-year tracking (e.g., *"How did automotive gross margin trend from Q1 to Q3?"*) and event-driven analysis (*"What executive changes or litigation updates were disclosed in recent 8-Ks?"*).
* **Technical Details**:
  * **Backend**: Extend `submissions.py` and `orchestrator.py` to accept `form_types=["10-K", "10-Q", "8-K"]`.
  * **Quarterly Aggregation**: Account for cumulative vs. discrete quarterly XBRL periods (Q1, Q2, Q3, Q4).
  * **8-K Item Extraction**: Parse 8-K Items (Item 1.01 Entry into Material Agreement, Item 2.02 Results of Operations, Item 5.02 Departure of Directors).
* **Effort**: Medium–High (3–4 days) | **Impact**: Very High

---

### 6. Custom Watchlist & Saved Research Notebook
* **Goal**: Allow users to save research sessions, pin favorite companies, and compare metrics across a personal watchlist.
* **Analyst Value**: Enables continuous tracking of portfolio companies without re-typing queries.
* **Technical Details**:
  * **Storage**: Local browser storage (`localStorage` / `IndexedDB`) or SQLite backend.
  * **Features**: Pinned peer groups (e.g., "Big Tech Cloud: MSFT, AMZN, GOOGL"), query history, and bookmarked citations.
* **Effort**: Low–Medium (1–2 days) | **Impact**: Medium

---

## Suggested Implementation Roadmap

| Priority | Feature | Category | Key Benefit |
| :--- | :--- | :--- | :--- |
| **Phase 1** | **Interactive Financial Visualizations** | UX & Analysis | High visual impact, instant comprehension of spreads and YoY trends |
| **Phase 2** | **One-Click Report Export (PDF & CSV)** | Workflow & Audit | Shareable reports with verifiable audit trails |
| **Phase 3** | **Live Ticker Autocomplete Directory** | Usability | Instant CIK and fiscal calendar discovery |
| **Phase 4** | **10-K Redline & Disclosure Diff Viewer** | Forensic Research | Automated detection of new vs. retired risk disclosures |
| **Phase 5** | **10-Q & 8-K Quarterly/Event Ingestion** | Data Coverage | Intra-year granularity and material event tracking |
