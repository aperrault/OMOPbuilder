# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OMOPbuilder (All of Us Cohort Scout) is an AI-powered agent that generates, validates, and refines BigQuery SQL queries for the NIH "All of Us" Researcher Workbench. It uses Google Gemini to draft SQL from natural language, then validates syntax and concept IDs against a local DuckDB mock database — no patient data is ever accessed.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python run_tests.py                       # Full test suite (generates SQL and checks keywords)
python -m unittest test_concept_check.py  # Unit tests for concept ID extraction/validation
python local_continuation_test.py         # Integration test for session continuation (mocks Gemini)

# Environment
export GOOGLE_API_KEY="..."               # Required for Gemini API access
```

## Architecture

### Agent Loop (`core.py`)

`agent_loop(user_request, max_turns=5, is_continuation=False)` orchestrates multi-turn conversation with Gemini. Each turn:
1. Gemini generates BigQuery SQL from the user's natural language request
2. SQL is extracted and run through three validation tools via `AllOfUsMockDB`:
   - **LOOKUP** — fuzzy concept name search (`lookup_code`)
   - **SQL Validation** — syntax check via DuckDB `EXPLAIN` (`validate_query`)
   - **Concept ID Check** — extracts IDs from SQL and validates against vocabulary (`check_concept_ids`)
3. Validation errors are fed back as tool results; agent self-corrects up to `max_turns`

Session state is preserved in a global `last_history` for continuation requests.

The model is `gemini-3.1-pro-preview`. Two modes: **Precise** (CONCEPT.csv loaded, exact ID lookups) and **Fuzzy** (regex fallback without vocabulary).

### Mock Database (`AllOfUSMockDB.py`)

In-memory DuckDB database initialized from:
- `OMOP_CDM_v5_3_1.csv` — schema definition (creates all OMOP CDM tables)
- `CONCEPT.csv` (~256MB) — SNOMED/RxNorm/LOINC/PPI vocabulary
- `CONCEPT_ANCESTOR.csv` (~218MB) — concept hierarchy

Key middleware translates BigQuery dialect to DuckDB (backticks → double quotes, `REGEXP_CONTAINS` → `regexp_matches`, `CURRENT_DATE()` → `CURRENT_DATE`, etc.).

### Colab Integration (`colab_cell.py`)

Multi-cell template for running in Google Colab: clones repo, installs deps, detects available CSVs, runs agent, and supports iterative refinement.

## Logging

Agent traces are written to `logs/agent_trace_YYYYMMDD_HHMMSS.log` with full conversation history, extracted SQL, validation results, and concept ID checks.
