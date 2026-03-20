# OMOPbuilder

OMOPbuilder generates, validates, and self-corrects BigQuery SQL for the NIH All of Us Researcher Workbench. It uses Google Gemini 3.1 to draft queries from plain English and validates them against a local DuckDB mock of the OMOP CDM schema. No patient data is accessed.

## Install

```bash
git clone https://github.com/aperrault/OMOPbuilder.git
cd OMOPbuilder
pip install -r requirements.txt
```

Set your Gemini API key as an environment variable:

```bash
export GOOGLE_API_KEY="your-key-here"
```

You can get a free key from [Google AI Studio](https://aistudio.google.com/).

## Usage

```bash
python core.py
```

Edit the bottom of `core.py` to change the query:

```python
if __name__ == "__main__":
    query = agent_loop("Find Hispanic women over 60 with Type 2 Diabetes who have never taken Metformin.")
    print(query)
```

## Schema and vocabulary files

The agent needs the OMOP CDM schema definition to validate SQL. Download `OMOP_CDM_v5_3_1.csv` from the [OHDSI CommonDataModel v5.3.1 release](https://github.com/OHDSI/CommonDataModel/releases/tag/v5.3.1) and place it in the repo root.

### Precise vs Fuzzy mode

By default the agent runs in **Fuzzy mode** -- it generates queries using string matching (`LIKE '%Diabetes%'`). This works without any vocabulary files.

To enable **Precise mode** (real OMOP concept IDs like `201826`):

1. Go to [Athena OHDSI](https://athena.ohdsi.org/vocabulary/list) and log in.
2. Select vocabularies: SNOMED, RxNorm, LOINC, PPI. Optionally add UCUM (Units), ATC (Drug Classes), and CPT4/ICD10CM (Billing).
3. Download and unzip.
4. Copy `CONCEPT.csv` and optionally `CONCEPT_ANCESTOR.csv` into the repo root.

The agent detects these files automatically and switches to precise lookups.

## How it works

`agent_loop()` in `core.py` runs a multi-turn loop (up to 5 turns by default):

1. Gemini drafts BigQuery SQL from your natural language request.
2. The SQL is validated against a local DuckDB mock database (`AllOfUSMockDB.py`) using three checks: syntax validation, concept ID verification, and vocabulary lookup.
3. If validation fails, the errors are fed back to Gemini, which rewrites the query.
4. Once the query passes all checks, the final SQL is returned.

The mock database loads the OMOP CDM v5.3 schema from `OMOP_CDM_v5_3_1.csv` and translates BigQuery dialect to DuckDB for local validation.

## Colab / Jupyter

Open `aou_scout.ipynb` in Google Colab (or any Jupyter environment). It handles cloning the repo, installing dependencies, detecting schema/vocabulary files, and running the agent. A second cell lets you iteratively refine the generated SQL by pasting errors or change requests.

`colab_cell.py` contains the same cells as plain Python for reference.

## Limitations

- The local database contains vocabulary but no patient data. Queries will return empty results locally -- the goal is to produce valid SQL, not results.
- A middleware layer translates BigQuery functions to DuckDB equivalents. Most functions are covered, but very niche BigQuery-specific syntax may cause false validation errors.

## License

[MIT](LICENSE)
