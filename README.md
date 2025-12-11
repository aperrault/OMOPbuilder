# 🧬 All of Us Cohort Scout

**Stop wasting computation credits on syntax errors.**

Cohort Scout is an AI agent that generates, validates, and refines SQL queries for the NIH *All of Us* Researcher Workbench. It uses a mock database to ensure your code works.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue) ![DuckDB](https://img.shields.io/badge/Database-DuckDB-yellow) ![OMOP](https://img.shields.io/badge/Standard-OMOP%20v5.3-green)

## ⚡️ Why use this?

* **🔒 Privacy First:** No patient data is ever accessed or needed.
* **🧠 "Thinking" Agent:** Unlike standard chatbots, this agent uses a feedback loop. If it writes bad SQL, the local database catches the error, and the agent fixes itself automatically.
* **📚 Smart Vocabulary:** Can look up *real* standard Concept IDs (SNOMED, RxNorm, LOINC) to ensure you aren't guessing codes.

## 🛠️ Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/aou-cohort-scout.git](https://github.com/your-username/aou-cohort-scout.git)
    cd aou-cohort-scout
    ```

2.  **Install requirements:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Get a Gemini API Key:**
    * Get a free key from [Google AI Studio](https://aistudio.google.com/).
    * Open `core.py` and paste your key:
        ```python
        genai.configure(api_key="PASTE_YOUR_KEY_HERE")
        ```

## 🚀 Usage

**Basic Run:**
Just run the script. It comes pre-loaded with a test query.
```bash
python core.py
````

**Custom Query:**
Edit the bottom of `core.py` to describe your specific cohort:

```python
if __name__ == "__main__":
    query = agent_loop("Find Hispanic women over 60 with Type 2 Diabetes who have never taken Metformin.")
    print(query)
```

-----

## 💎 Pro Mode: Enable "Precise Lookups"

By default, the agent runs in **Fuzzy Mode**, creating queries that match text strings (e.g., `LIKE '%Diabetes%'`). This is safe but slower.

To enable **Precise Mode** (where the agent finds exact IDs like `201826`), you need the OMOP Vocabulary:

1.  Go to [Athena OHDSI](https://athena.ohdsi.org/vocabulary/list).
2.  Log in and select these vocabularies: **SNOMED**, **RxNorm**, **LOINC**, **PPI** (All of Us Surveys) or any other vocabularies your query might need.
3.  Download and unzip the bundle.
4.  Copy the file `CONCEPT.csv` into the root folder of this project.

**That's it.** The tool will detect the file automatically:

> `✅ Vocabulary Loaded! Agent uses 'Precise Mode'.`

-----

## 🧠 How It Works

1.  **User Request:** You describe your cohort in plain English.
2.  **Drafting:** The Agent (Gemini 3 by default) converts this into a BigQuery SQL draft.
3.  **Simulation:** The tool spins up an in-memory **DuckDB** database that mimics the *All of Us* OMOP schema.
4.  **Validation:** It tries to "compile" the query.
      * *If it fails:* The database returns the error (e.g., `Column 'age' not found`). The Agent reads the error and rewrites the code.
      * *If it succeeds:* It outputs the clean SQL.
5.  **Output:** You copy the final SQL into your Jupyter Notebook in the Researcher Workbench.

## ⚠️ Limitations

  * **Mock Data:** The local database contains the *vocabulary* (concepts) but **zero patient data**. Running the query locally will return an empty result set. This is intentional. The goal is to generate *valid code*, not *results*.
  * **Dialects:** The tool uses a middleware layer to translate BigQuery-specific functions (like `EXTRACT(YEAR from CURRENT_DATE())`) into DuckDB logic for validation. It is 99% accurate, but extremely niche BigQuery functions might flag false errors.

## License

MIT License. Free to use for all researchers.

```
```