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
    - measurement (person_id, measurement_concept_id, value_as_number)
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

def agent_loop(user_request, max_turns=20):
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
        if "LOOKUP:" in text:
            # Find ALL lines that start with LOOKUP:
            lines = text.split('\n')
            lookup_results = []
            
            for line in lines:
                if line.strip().startswith("LOOKUP:"):
                    term = line.replace("LOOKUP:", "").strip()
                    # Run the lookup
                    res = db.lookup_code(term)
                    lookup_results.append(f"Search '{term}': {res}")
            
            # Combine results into one block
            final_result = "\n".join(lookup_results)
            print(f"📚 Database Tool: \n{final_result}")
            
            history.append({"role": "model", "parts": [text]})
            history.append({"role": "user", "parts": [f"TOOL RESULTS:\n{final_result}"]})
        
        # 3. Check for SQL Output
        elif "SQL:" in text or "SELECT" in text:
            # CLEANING: Remove "SQL:" prefix and standard markdown
            clean_text = text.replace("SQL:", "").replace("```sql", "").replace("```", "").strip()
            
            # EXTRACTION: Find the start of the query
            # This handles cases where the agent writes: "Here is the code: SELECT ..."
            start_index = clean_text.find("SELECT")
            if start_index != -1:
                sql_candidate = clean_text[start_index:]
            else:
                sql_candidate = clean_text

            # VALIDATION
            print(f"   🔍 Validating SQL...") # Visual feedback
            is_valid, error_msg = db.validate_query(sql_candidate)
            
            if is_valid:
                print("\n✅ SUCCESS: Valid SQL generated.")
                print("-" * 20)
                return sql_candidate
            else:
                print(f"❌ VALIDATION ERROR: {error_msg}")
                
                # FEEDBACK: Add the error to history so the agent fixes it
                history.append({"role": "model", "parts": [text]})
                history.append({
                    "role": "user", 
                    "parts": [f"Database Error: {error_msg}. \nIMPORTANT: Ensure you are using standard BigQuery syntax. Return ONLY the corrected SQL."]
                })       

        else:
            # Agent is just chatting? Nudge it.
            history.append({"role": "model", "parts": [text]})
            history.append({"role": "user", "parts": ["Please output a command: either 'LOOKUP: term' or 'SQL: query'."]})

    print(f"\n🛑 STOPPING: Reached maximum turn limit ({max_turns}).")
    return "Failed to generate valid SQL."

# --- RUN IT ---
if __name__ == "__main__":
    final_query = agent_loop("Create a cohort of Type 2 Diabetes patients over age 50 who are new users of Metformin. Exclude any patients who had a diagnosis of Dementia or Chronic Kidney Disease (CKD) before their first Metformin prescription.")
    print("-" * 20)
    print(final_query)