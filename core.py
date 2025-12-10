import google.generativeai as genai
from AllOfUSMockDB import AllOfUsMockDB
import re

# SETUP
genai.configure(api_key="AIzaSyCGB_53aLA0begX2_U7-VkvlsrBxYdbWbs") # Replace with your key
model = genai.GenerativeModel('gemini-3-pro-preview')

# Initialize DB (Pass path to Athena folder if you have it, else None)
# db = AllOfUsMockDB(vocab_path="./athena_vocab_folder") 
db = AllOfUsMockDB() 

def build_system_prompt(vocab_loaded):
    """Dynamically builds the instructions based on available tools."""
    
    base_prompt = """
    You are an expert Data Scientist for the NIH 'All of Us' program.
    Your goal is to generate BigQuery SQL (OMOP CDM v5.3) for a user's cohort request.
    
    SCHEMA:
    - person (person_id, year_of_birth, gender_concept_id, race_concept_id)
    - condition_occurrence (person_id, condition_concept_id)
    - drug_exposure (person_id, drug_concept_id)
    - concept (concept_id, concept_name, domain_id)
    
    PROTOCOL:
    You must think step-by-step.
    """
    
    if vocab_loaded:
        # Precise Mode Instructions
        return base_prompt + """
    MODE: PRECISE (Vocabulary Available)
    1. Look up Concept IDs for Conditions and Drugs using "LOOKUP: term".
    2. IMPORTANT: For Demographics, use these standard IDs if possible without lookup:
       - Female: 8532
       - Male: 8507
       - Hispanic: 38003563
    3. Once you have IDs, output the final SQL using: "SQL: SELECT ..."    """
    else:
        # Fuzzy Mode Instructions
        return base_prompt + """
    MODE: FUZZY (No Vocabulary)
    1. Do NOT guess Concept IDs.
    2. Write SQL that joins the `concept` table and uses `REGEXP_CONTAINS(concept_name, '(?i)term')`.
    3. Output the final SQL using: "SQL: SELECT ..."
    """

def agent_loop(user_request, max_turns=5):
    print(f"\n🚀 Starting Agent for: '{user_request}'\n")
    
    history = [
        {"role": "user", "parts": [f"{build_system_prompt(db.vocab_loaded)}\n\nUSER REQUEST: {user_request}"]}
    ]

    for turn in range(max_turns):
        # 1. Model Thinks
        response = model.generate_content(history)
        text = response.text.strip()
        print(f"🤖 Agent: {text}")
        
        # 2. Check for Tool Use (LOOKUP)
        if text.startswith("LOOKUP:"):
            term = text.replace("LOOKUP:", "").strip()
            result = db.lookup_code(term)
            print(f"📚 Database Tool: Found {result}")
            
            # Feed result back to history
            history.append({"role": "model", "parts": [text]})
            history.append({"role": "user", "parts": [f"TOOL RESULT: {result}"]})
            continue # Loop again to let agent use the result

        # 3. Check for SQL Output
        elif "SQL:" in text or "SELECT" in text:
            
            # FIX: Robust SQL Extraction using Regex
            # This ignores "Step 1:..." and grabs only the code block
            sql_match = re.search(r"```sql\n(.*?)```", text, re.DOTALL)
            if sql_match:
                sql_candidate = sql_match.group(1).strip()
            else:
                # Fallback if the agent didn't use markdown blocks
                # We try to grab everything after the first SELECT
                if "SELECT" in text:
                    sql_candidate = text[text.find("SELECT"):]
                else:
                    sql_candidate = text.strip()

            # Now validate...
            is_valid, error_msg = db.validate_query(sql_candidate) 
       
        else:
            # Agent is just chatting? Nudge it.
            history.append({"role": "model", "parts": [text]})
            history.append({"role": "user", "parts": ["Please output a command: either 'LOOKUP: term' or 'SQL: query'."]})

    return "Failed to generate valid SQL."

# --- RUN IT ---
final_query = agent_loop("Cohort of women over 60 with Type 2 Diabetes")
print("-" * 20)
print(final_query)