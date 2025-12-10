# All of Us Cohort Builder Agent 🧬

A "Local First" AI agent that generates accurate, syntax-validated SQL queries for the NIH *All of Us* Researcher Workbench.

**Why use this?**

  * **Save Credits:** The agent validates SQL syntax locally *before* you spend computation credits in the cloud.
  * **No Hallucinations:** It uses a local simulation of the OMOP database to verify that tables and columns actually exist.
  * **Smart Vocab:** Can look up *real* Concept IDs (e.g., SNOMED codes for diseases) locally if you provide the vocabulary files.
  * **Privacy First:** Your research ideas stay local (or in your private Colab); no patient data is ever touched.

-----

## 🚀 Quick Start (Google Colab / Jupyter)

1.  **Get a Gemini API Key:**

      * Go to [Google AI Studio](https://aistudio.google.com/).
      * Create a free API key.

2.  **Install Requirements:**

    ```bash
    pip install google-generativeai duckdb
    ```

3.  **Run the Agent:**
    Open `core.py`, paste your API key where indicated, and run:

    ```python
    query = agent_loop("Find Hispanic women over age 50 with Type 2 Diabetes")
    print(query)
    ```

-----

## 🧠 How It Works

This tool uses an **Agentic Loop** to ensure code quality:

1.  **User Request:** You describe your cohort in plain English.
2.  **Drafting:** The AI (Gemini) drafts a SQL query.
3.  **Local Validation:** The agent spins up a temporary **DuckDB** database (mocking the *All of Us* OMOP schema) and tries to "run" the query.
4.  **Self-Correction:**
      * *If the query fails (e.g., "Column 'age' does not exist"):* The agent reads the error, fixes it (changing 'age' to 'year\_of\_birth'), and tries again.
      * *If the query works:* It outputs the final SQL for you to copy into the Workbench.

-----

## 🔌 Advanced Setup: "Precise Mode" (Recommended)

By default, the agent runs in **Fuzzy Mode**. It writes SQL that searches for text strings (e.g., `WHERE concept_name LIKE '%Diabetes%'`). This is safe but slower to run in the Workbench.

To enable **Precise Mode** (where the agent looks up exact Concept IDs like `201826`), follow these steps:

### 1\. Download Vocabulary from Athena

Go to [athena.ohdsi.org](https://athena.ohdsi.org) and download the **Standard OMOP Vocabulary**.

  * **Must Select:** `SNOMED`, `RxNorm`, `LOINC`, `PPI` (AllOfUs Surveys).
  * *Note:* You do not need CPT4 unless you are researching procedural billing codes.

### 2\. Extract and Load

Unzip the download. You should see a file named `CONCEPT.csv`. Place this folder in your project directory.

### 3\. Update the Script

In `core.py`, point the agent to your folder:

```python
# Initialize DB with your vocabulary path
db = AllOfUsMockDB(vocab_path="./athena_download_folder")
```

**Now, when you ask for "Diabetes", the Agent will:**

1.  Pause.
2.  Search your local `CONCEPT.csv` for "Diabetes".
3.  Find ID `201826` (Standard SNOMED code).
4.  Write the query: `WHERE condition_concept_id = 201826`.

-----

## 📂 Project Structure

  * `core.py` - The main script. Contains the Gemini API logic and the Agent Loop.
  * `AllOfUsMockDB.py` - The simulation engine. Uses DuckDB to create empty OMOP tables, load vocabulary, and handle syntax validation.

-----

## 🛠 Troubleshooting

**"I'm getting a Syntax Error regarding `REGEXP_CONTAINS`"**

  * Ensure you are using the latest version of DuckDB (`pip install -U duckdb`).

**"The Agent keeps trying to use 'age'"**

  * The Agent is trained to prefer `year_of_birth` (standard OMOP), but sometimes slips. The validation loop usually catches this. If it persists, try being more specific in your prompt: "Calculate age from year\_of\_birth."

-----

## 📜 License

MIT License. Free to use for any *All of Us* researcher.