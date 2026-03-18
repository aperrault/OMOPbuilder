import duckdb
import os
import glob

class AllOfUsMockDB:
    def __init__(self):
        # Initialize in-memory DuckDB
        self.con = duckdb.connect(':memory:')
        self.vocab_loaded = False
        self.schema_structure = {}
        self.omop_version = "v5.3.1" # Default fallback
        
        # 1. Initialize Schema
        self._init_schema()
        
        # 2. Load Vocabulary (Check root)
        if os.path.exists("CONCEPT.csv"):
            self._load_vocab("CONCEPT.csv")
        else:
            print("⚠️ CONCEPT.csv not found in root. Agent will run in 'Fuzzy Mode' (String matching).")

    def _find_omop_csv(self):
        # Look for any CSV starting with OMOP_CDM_
        files = glob.glob("OMOP_CDM_*.csv")
        if files:
            # Sort to pick the "latest" if multiple exist (e.g. v5.4 > v5.3)
            return sorted(files)[-1]
        return None

    def _init_schema(self):
        # Always create vocab tables as they are not in the CDM definition usually
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS concept (
                concept_id INT, concept_name VARCHAR, domain_id VARCHAR, vocabulary_id VARCHAR, standard_concept VARCHAR, concept_code VARCHAR
            );
            CREATE TABLE IF NOT EXISTS concept_ancestor (
                ancestor_concept_id INT, descendant_concept_id INT, min_levels_of_separation INT, max_levels_of_separation INT
            );
        """)

        csv_path = self._find_omop_csv()
        if csv_path:
            print(f"📂 Loading Schema from {csv_path}...")
            # Extract version from filename: OMOP_CDM_v5_3_1.csv -> v5.3.1
            try:
                # Remove prefix and extension, replace underscores with dots
                version_part = csv_path.replace("OMOP_CDM_", "").replace(".csv", "")
                self.omop_version = version_part.replace("_", ".")
            except:
                self.omop_version = csv_path # Fallback to filename if parsing fails
                
            self._create_tables_from_csv(csv_path)
        else:
            print("⚠️ OMOP CDM CSV not found (looked for 'OMOP_CDM_*.csv').")
            print("⚠️ Please download the latest OMOP CDM CSV definition to the root directory.")
            print("⚠️ Using hardcoded schema fallback.")
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
            """)

    def _create_tables_from_csv(self, csv_path):
        import csv
        tables = {}
        seen_columns = {} # Track seen columns per table to avoid duplicates

        try:
            # Use errors='replace' to handle potential encoding issues (e.g. smart quotes)
            with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    table = row['table']
                    # Sanitize field name (remove asterisks etc)
                    field = row['field'].strip().replace('*', '')
                    dtype = row['type']
                    
                    if table not in tables:
                        tables[table] = []
                        seen_columns[table] = set()
                    
                    # Skip duplicate columns (fixes issue with malformed note_nlp rows in some CSVs)
                    if field in seen_columns[table]:
                        continue
                    seen_columns[table].add(field)

                    # Map types to DuckDB
                    duck_type = "VARCHAR"
                    dtype_upper = dtype.upper()
                    if "INTEGER" in dtype_upper: duck_type = "BIGINT" # Use BIGINT for safety
                    elif "FLOAT" in dtype_upper: duck_type = "DOUBLE"
                    elif "DATETIME" in dtype_upper: duck_type = "TIMESTAMP"
                    elif "DATE" in dtype_upper: duck_type = "DATE"
                    
                    # Wrap field in quotes to handle spaces or reserved words
                    tables[table].append(f'"{field}" {duck_type}')
            
            # Store structure for prompt generation (clean field names)
            self.schema_structure = {t: list(cols) for t, cols in seen_columns.items()}

            for table, columns in tables.items():
                col_str = ", ".join(columns)
                self.con.execute(f"CREATE TABLE IF NOT EXISTS {table} ({col_str});")
            print(f"✅ Schema loaded from CSV: {len(tables)} tables created.")
            
        except Exception as e:
            print(f"❌ Failed to load schema from CSV: {e}")

    def get_schema_description(self):
        if not self.schema_structure:
            return """
    - person (person_id, year_of_birth, gender_concept_id, race_concept_id, ethnicity_concept_id)
    - condition_occurrence (person_id, condition_concept_id, condition_start_date, condition_end_date)
    - drug_exposure (person_id, drug_concept_id, drug_exposure_start_date, drug_exposure_end_date)
    - measurement (person_id, measurement_concept_id, measurement_date, value_as_number)
    - procedure_occurrence (person_id, procedure_concept_id, procedure_date) -- Surgeries/Procedures
    - observation (person_id, observation_concept_id, observation_date) -- Social history, family history, etc.
    - concept (concept_id, concept_name, domain_id, standard_concept)
    - concept_ancestor (ancestor_concept_id, descendant_concept_id) -- Use this to find all specific drugs/conditions
            """
        
        schema_str = ""
        for table, fields in self.schema_structure.items():
            schema_str += f"    - {table} ({', '.join(fields)})\n"
            
        # Add vocab tables manually as they might not be in the CSV
        if "concept" not in self.schema_structure:
            schema_str += "    - concept (concept_id, concept_name, domain_id, standard_concept)\n"
        if "concept_ancestor" not in self.schema_structure:
            schema_str += "    - concept_ancestor (ancestor_concept_id, descendant_concept_id) -- Use this to find all specific drugs/conditions\n"
        
        return schema_str

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
            
            # Try to load Ancestors
            ancestor_path = file_path.replace("CONCEPT.csv", "CONCEPT_ANCESTOR.csv")
            if os.path.exists(ancestor_path):
                print(f"📂 Loading Ancestors from {ancestor_path}...")
                self.con.execute(f"""
                    INSERT INTO concept_ancestor 
                    SELECT ancestor_concept_id, descendant_concept_id, min_levels_of_separation, max_levels_of_separation
                    FROM read_csv_auto('{ancestor_path}', ignore_errors=true)
                """)
                print("✅ Ancestors Loaded!")
                
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
            
        import re
        potential_ids = set()
        
        # 1. Equality matches (e.g. gender_concept_id = 8532)
        matches_eq = re.findall(r'[\w\.]*concept_id\s*=\s*(\d+)', sql, re.IGNORECASE)
        potential_ids.update(matches_eq)
        
        # 2. IN clause matches (e.g. condition_concept_id IN (123, 456))
        matches_in = re.findall(r'[\w\.]*concept_id\s+(?:NOT\s+)?IN\s*\(([\d\s,]+)\)', sql, re.IGNORECASE)
        for match in matches_in:
            ids = [s.strip() for s in match.split(',')]
            potential_ids.update([i for i in ids if i.isdigit()])

        # 3. CTE/Select Aliases (e.g. SELECT 8532 AS gender_concept_id)
        matches_alias = re.findall(r'(\d+)\s+AS\s+[\w\.]*concept_id', sql, re.IGNORECASE)
        potential_ids.update(matches_alias)
        
        found_info = []
        missing_ids = []
        
        for pid in potential_ids:
            # No heuristics needed - we targeted concept_id columns specifically
            
            res = self.con.execute(f"SELECT concept_id, concept_name, domain_id FROM concept WHERE concept_id = {pid}").fetchone()
            if res:
                # Check if it is an ancestor (has descendants other than itself)
                is_ancestor = self.con.execute(f"""
                    SELECT 1 FROM concept_ancestor 
                    WHERE ancestor_concept_id = {pid} 
                    AND descendant_concept_id != {pid} 
                    LIMIT 1
                """).fetchone()
                ancestor_tag = " [ANCESTOR]" if is_ancestor else ""
                
                found_info.append(f"ID {pid} -> {res[1]} ({res[2]}){ancestor_tag}")
            else:
                missing_ids.append(pid)
                
        report = "Concept ID Check:\n"
        if found_info:
            report += "✅ Valid Concepts:\n" + "\n".join(found_info) + "\n"
        
        if missing_ids:
            # report += f"⚠️ Unknown IDs (Not in Vocab): {', '.join(missing_ids)}"
            report += (
                f"⛔ CRITICAL ERROR: The Concept IDs {', '.join(missing_ids)} are invalid or hallucinated.\n"
                f"STOP GUESSING. You do NOT know these IDs.\n"
                f"ACTION REQUIRED: Call the `LOOKUP: term` tool immediately for the terms associated with these IDs."
            )
            
        if not found_info and not missing_ids:
             report += "ℹ️ No Concept IDs found in query."

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
            
            for row in rows:
                cid = row[0]
                # Check if it is an ancestor (has descendants other than itself)
                is_ancestor = self.con.execute(f"""
                    SELECT 1 FROM concept_ancestor 
                    WHERE ancestor_concept_id = {cid} 
                    AND descendant_concept_id != {cid} 
                    LIMIT 1
                """).fetchone()
                ancestor_tag = " [ANCESTOR]" if is_ancestor else ""
                
                # Format as string to include the tag
                results.append(f"{str(row)}{ancestor_tag}")
        
        return "\n".join(results[:20]) if results else "No standard code found."