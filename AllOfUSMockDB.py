import duckdb
import os

class AllOfUsMockDB:
    def __init__(self):
        # Initialize in-memory DuckDB
        self.con = duckdb.connect(':memory:')
        self.vocab_loaded = False
        
        # 1. Initialize the Schema (Empty tables for syntax checking)
        self._init_schema()
        
        # 2. Load Vocabulary (Check root)
        if os.path.exists("CONCEPT.csv"):
            self._load_vocab("CONCEPT.csv")
        else:
            print("⚠️ CONCEPT.csv not found in root. Agent will run in 'Fuzzy Mode' (String matching).")

    def _init_schema(self):
        # Create standard OMOP tables
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS person (
                person_id BIGINT, 
                year_of_birth INT, 
                gender_concept_id INT, 
                race_concept_id INT, 
                ethnicity_concept_id INT
            );
            CREATE TABLE IF NOT EXISTS condition_occurrence (
                person_id BIGINT, 
                condition_concept_id INT, 
                condition_start_date DATE
            );
            CREATE TABLE IF NOT EXISTS drug_exposure (
                person_id BIGINT, 
                drug_concept_id INT, 
                drug_exposure_start_date DATE
            );
            CREATE TABLE IF NOT EXISTS measurement (
                person_id BIGINT, 
                measurement_concept_id INT, 
                value_as_number DOUBLE
            );
            -- Create concept table structure even if empty
            CREATE TABLE IF NOT EXISTS concept (
                concept_id INT, 
                concept_name VARCHAR, 
                domain_id VARCHAR, 
                vocabulary_id VARCHAR, 
                standard_concept VARCHAR, 
                concept_code VARCHAR
            );
        """)

        # This allows the Agent to use REGEXP_CONTAINS (BigQuery) and DuckDB will understand it.
        try:
            self.con.execute("CREATE MACRO REGEXP_CONTAINS(text, pattern) AS regexp_matches(text, pattern);")
        except:
            pass # Macro might already exist

    def _load_vocab(self, file_path):
        print(f"📂 Loading Vocabulary from {file_path}...")
        try:
            # Load only what we need for lookups
            self.con.execute(f"""
                INSERT INTO concept 
                SELECT concept_id, concept_name, domain_id, vocabulary_id, standard_concept, concept_code
                FROM read_csv_auto('{file_path}')
            """)
            self.vocab_loaded = True
            print("✅ Vocabulary Loaded! Agent uses 'Precise Mode'.")
        except Exception as e:
            print(f"❌ Failed to load vocab: {e}")

    def validate_query(self, sql):
        """Runs EXPLAIN to check SQL syntax without processing data."""
        try:
            self.con.execute(f"EXPLAIN {sql}")
            return True, "Syntax Valid"
        except Exception as e:
            return False, str(e)

    def lookup_code(self, search_term):
            if not self.vocab_loaded:
                return "TOOL_ERROR: Vocabulary not loaded."
                
            # Split multiple terms (e.g., "Diabetes, Female")
            terms = [t.strip() for t in search_term.split(',')]
            results = []
            
            for t in terms:
                # IMPROVED SQL:
                # 1. Use ILIKE for flexible matching
                # 2. ORDER BY length(concept_name): Prefer "Diabetes" over "Diabetes with complications..."
                # 3. LIMIT 20: Give the agent enough context to pick the right one
                rows = self.con.execute(f"""
                    SELECT concept_id, concept_name, domain_id, vocabulary_id
                    FROM concept 
                    WHERE concept_name ILIKE '%{t}%' 
                    AND standard_concept = 'S'
                    ORDER BY length(concept_name) ASC
                    LIMIT 20
                """).fetchall()
                
                if rows:
                    results.extend(rows)
            
            if not results:
                return "No standard code found. Try a different synonym."
                
            # Format the output so the Agent can read it clearly
            # We limit the text return to prevent overflowing the context window
            formatted_results = str(results[:20]) 
            return formatted_results