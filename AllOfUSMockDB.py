import duckdb
import os

class AllOfUsMockDB:
    def __init__(self):
        # Initialize in-memory DuckDB
        self.con = duckdb.connect(':memory:')
        self.vocab_loaded = False
        
        # 1. Initialize Schema
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
                person_id BIGINT, year_of_birth INT, gender_concept_id INT, race_concept_id INT, ethnicity_concept_id INT
            );
            CREATE TABLE IF NOT EXISTS condition_occurrence (
                person_id BIGINT, condition_concept_id INT, condition_start_date DATE
            );
            CREATE TABLE IF NOT EXISTS drug_exposure (
                person_id BIGINT, drug_concept_id INT, drug_exposure_start_date DATE
            );
            CREATE TABLE IF NOT EXISTS measurement (
                person_id BIGINT, measurement_concept_id INT, value_as_number DOUBLE
            );
            CREATE TABLE IF NOT EXISTS concept (
                concept_id INT, concept_name VARCHAR, domain_id VARCHAR, vocabulary_id VARCHAR, standard_concept VARCHAR, concept_code VARCHAR
            );
            CREATE TABLE IF NOT EXISTS concept_ancestor (
                ancestor_concept_id INT, descendant_concept_id INT, min_levels_of_separation INT, max_levels_of_separation INT
            );
        """)

    def _load_vocab(self, file_path):
        print(f"📂 Loading Vocabulary from {file_path}...")
        try:
            # FIX: ignore_errors=true to skip bad rows in Athena download
            self.con.execute(f"""
                INSERT INTO concept 
                SELECT concept_id, concept_name, domain_id, vocabulary_id, standard_concept, concept_code
                FROM read_csv_auto('{file_path}', ignore_errors=true)
            """)
            self.vocab_loaded = True
            print("✅ Vocabulary Loaded! Agent uses 'Precise Mode'.")
        except Exception as e:
            print(f"❌ Failed to load vocab: {e}")

    def validate_query(self, sql):
        # --- MIDDLEWARE CLEANING ---
        clean_sql = sql.replace("`", '"') \
                       .replace("CURRENT_DATE()", "CURRENT_DATE") \
                       .replace("CURRENT_TIMESTAMP()", "CURRENT_TIMESTAMP") \
                       .replace("REGEXP_CONTAINS", "regexp_matches") # Fix for DuckDB Regex
        
        try:
            self.con.execute(f"EXPLAIN {clean_sql}")
            return True, "Syntax Valid"
        except Exception as e:
            return False, str(e)

    def check_concept_ids(self, sql):
        """Scans SQL for potential Concept IDs and verifies them against the loaded vocab."""
        if not self.vocab_loaded:
            return "SKIPPED: Vocab not loaded."
            
        # Find all integer sequences
        import re
        potential_ids = set(re.findall(r'\b\d+\b', sql))
        
        found_info = []
        missing_ids = []
        
        for pid in potential_ids:
            # Skip small numbers likely to be constants/ages
            if int(pid) < 1000: 
                continue
            # Skip likely years
            if 1900 <= int(pid) <= 2100:
                continue
                
            res = self.con.execute(f"SELECT concept_id, concept_name, domain_id FROM concept WHERE concept_id = {pid}").fetchone()
            if res:
                found_info.append(f"ID {pid} -> {res[1]} ({res[2]})")
            else:
                missing_ids.append(pid)
                
        report = "Concept ID Check:\n"
        if found_info:
            report += "✅ Valid Concepts:\n" + "\n".join(found_info) + "\n"
        
        if missing_ids:
            report += f"⚠️ Unknown IDs (Not in Vocab): {', '.join(missing_ids)}\n(Ignore if these are years or other constants)"
            
        return report

    def lookup_code(self, search_term):
        if not self.vocab_loaded:
            return "TOOL_ERROR: Vocabulary not loaded."
            
        # Strip markdown and quotes from the term
        terms = [t.strip().strip("*`_\"'") for t in search_term.split(',')]
        results = []
        
        for t in terms:
            # Use '?' to safely handle quotes in terms like 'Type 2 Diabetes'
            query = """
                SELECT concept_id, concept_name, domain_id, vocabulary_id
                FROM concept 
                WHERE concept_name ILIKE ? 
                AND standard_concept = 'S'
                ORDER BY length(concept_name) ASC 
                LIMIT 20
            """
            rows = self.con.execute(query, [f"%{t}%"]).fetchall()
            if rows:
                results.extend(rows)
        
        return str(results[:20]) if results else "No standard code found."