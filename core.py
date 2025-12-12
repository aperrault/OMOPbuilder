import google.generativeai as genai
from AllOfUSMockDB import AllOfUsMockDB
import os
import sys
import logging
import datetime
import json
import re

# Initialize DB globally
db = AllOfUsMockDB() 

# Global storage for the last session history
last_history = []

def setup_logger():
    """Sets up a file logger for the agent session."""
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"logs/agent_trace_{timestamp}.log"
    
    logger = logging.getLogger(f"AgentLogger_{timestamp}")
    logger.setLevel(logging.INFO)
    
    # File Handler
    fh = logging.FileHandler(log_filename, encoding='utf-8')
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s\n%(message)s\n' + '-'*50)
    fh.setFormatter(formatter)
    
    logger.addHandler(fh)
    return logger, log_filename

def build_system_prompt(vocab_loaded):
    schema_desc = db.get_schema_description()
    base_prompt = f"""
    You are an expert Data Scientist for the NIH 'All of Us' program.
    Your goal is to generate BigQuery SQL (OMOP CDM v5.3) for a user's cohort request.
    
    SCHEMA:
{schema_desc}
    
    RULES:
    1. Do NOT use DATE_DIFF. Use simple subtraction: (date_2 - date_1) to get days.
    2. Do NOT use DATE_ADD or DATE_SUB. They vary by dialect.
    3. To add/subtract time, use operators: 
       - Days: date_col - 30
       - Years/Months: date_col - INTERVAL 1 YEAR
    4. HIERARCHIES: ALWAYS use `concept_ancestor` for ALL clinical codes 
       (Conditions, Drugs, Procedures, AND Measurements). 
       Do not rely on lists of IDs found via lookup.
    """    
    if vocab_loaded:
        return base_prompt + "\nMODE: PRECISE. Use 'LOOKUP: term' to find IDs. Use standard IDs (Female=8532) where possible."
    else:
        return base_prompt + "\nMODE: FUZZY. Do NOT guess IDs. Use `REGEXP_CONTAINS(concept_name, '(?i)term')`."

def agent_loop(user_request, max_turns=5, is_continuation=False):
    global last_history
    # Lazy Config
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key: return "ERROR: GOOGLE_API_KEY missing."
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-3-pro-preview') 
    
    # Setup Logging
    logger, log_file = setup_logger()
    print(f"📝 Logging trace to: {log_file}")

    if is_continuation and last_history:
        print(f"\n🔄 Continuing Session with feedback: '{user_request}'\n")
        history = last_history
        # Append the user's feedback to the existing history
        history.append({"role": "user", "parts": [f"USER FEEDBACK: {user_request}"]})
    else:
        print(f"\n🚀 Starting Agent for: '{user_request}'\n")
        system_prompt = build_system_prompt(db.vocab_loaded)
        logger.info(f"SYSTEM PROMPT:\n{system_prompt}")
        logger.info(f"USER REQUEST:\n{user_request}")
        
        history = [
            {"role": "user", "parts": [f"{system_prompt}\n\nUSER REQUEST: {user_request}"]}
        ]

    for turn in range(max_turns):
        print(f"🤖 Agent: ", end="", flush=True)
        
        # Log History before sending
        logger.info(f"TURN {turn+1} - HISTORY SENT:\n{json.dumps(history, indent=2)}")
        
        try:
            response = model.generate_content(history)
            
            # Check if response was blocked or empty
            if not response.parts:
                logger.error(f"API BLOCKED: Finish Reason: {response.prompt_feedback}")
                return "API Error: Response was blocked by safety filters."
                
            full_text = response.text
            print(full_text)
            
            # Log Raw Response
            logger.info(f"TURN {turn+1} - RAW RESPONSE:\n{full_text}")
            
        except Exception as e:
            logger.error(f"API ERROR: {e}")
            return f"\nAPI Error: {e}"

        text = full_text.strip()
        
        # Tool: LOOKUP
        if "LOOKUP:" in text:
            print(f"\n📚 Database Tool: Running lookup...", end="", flush=True)
            lines = text.split('\n')
            results = []
            lookup_commands = []
            for line in lines:
                if "LOOKUP:" in line:
                    # Capture the term and aggressively strip markdown/quotes
                    term = line.split("LOOKUP:")[1].strip().split("->")[0].strip("*`_\"' ")                   
                    if term:
                        res = db.lookup_code(term)
                        results.append(f"Search '{term}': {res}")
                        lookup_commands.append(line)
            
            final_result = "\n".join(results)
            print(f"\r📚 Database Tool: Found {len(results)} results.") # Overwrite previous line
            
            # Log Tool Result
            logger.info(f"TURN {turn+1} - TOOL RESULT:\n{final_result}")
            
            # IMPORTANT: Only append the LOOKUP commands to history, ignoring any hallucinated follow-up text
            clean_model_text = "\n".join(lookup_commands)
            history.append({"role": "model", "parts": [clean_model_text]})
            history.append({"role": "user", "parts": [f"TOOL RESULTS:\n{final_result}"]})
            continue

        # Tool: SQL Validation
        elif "SQL:" in text or "SELECT" in text:
            # 1. Try to find a Markdown Code Block first (Most Robust)
            # Looks for ```sql ... ``` or just ``` ... ```
            match = re.search(r"```\w*\n(.*?)\n```", text, re.DOTALL)
            
            if match:
                sql_candidate = match.group(1).strip()
            else:
                # 2. Fallback: Heuristic Extraction if no markdown found
                # Look for the first occurrence of SELECT or WITH (case insensitive)
                clean_text = text.replace("SQL:", "").strip()
                
                # Find start indices
                match_select = re.search(r"\bSELECT\b", clean_text, re.IGNORECASE)
                match_with = re.search(r"\bWITH\b", clean_text, re.IGNORECASE)
                
                start_index = -1
                
                # Determine which comes first (CTE 'WITH' or standard 'SELECT')
                if match_select and match_with:
                    start_index = min(match_select.start(), match_with.start())
                elif match_select:
                    start_index = match_select.start()
                elif match_with:
                    start_index = match_with.start()
                
                if start_index != -1:
                    sql_candidate = clean_text[start_index:]
                else:
                    # If we still can't find code, verify failure but don't crash
                    sql_candidate = clean_text

            logger.info(f"TURN {turn+1} - EXTRACTED SQL:\n{sql_candidate}")
            print(f"   🔍 Validating SQL...", end="", flush=True) 
            
            # --- ALWAYS CHECK CONCEPT IDs (Even if SQL is invalid) ---
            id_report = db.check_concept_ids(sql_candidate)
            # ---------------------------------------------------------

            is_valid, error_msg = db.validate_query(sql_candidate)

            if is_valid:
                print(f"\r✅ SUCCESS: Valid SQL generated.      ") # Overwrite
                
                # Check if we are already in a verification loop
                last_user_msg = history[-1]["parts"][0] if history else ""
                is_verifying = "Now verifying Concept IDs" in last_user_msg

                if is_verifying:
                    print(f"\r✅ SUCCESS: SQL Verified.")
                    print(f"\n{id_report}")
                    logger.info(f"TURN {turn+1} - SUCCESS (Verified):\n{sql_candidate}")
                    # Save history for continuation
                    last_history = history
                    return sql_candidate

                print(f"\r🔍 Verifying Concept IDs...")
                print(f"\n{id_report}")
                logger.info(f"TURN {turn+1} - ID CHECK:\n{id_report}")
                
                history.append({"role": "model", "parts": [text]})
                history.append({
                    "role": "user", 
                    "parts": [f"SQL Validated. Now verifying Concept IDs:\n{id_report}\n\nIf these concepts are correct, output the SQL again. If any are incorrect (e.g. wrong domain or specific concept), please fix the SQL."]
                })
                continue
            else:
                print(f"\r❌ VALIDATION ERROR: {error_msg}")
                print(f"\n{id_report}") # Show ID report even on error
                logger.warning(f"TURN {turn+1} - VALIDATION ERROR:\n{error_msg}")
                history.append({"role": "model", "parts": [text]})
                history.append({
                    "role": "user", 
                    "parts": [f"Database Error: {error_msg}.\n\nAlso, here is a check on the Concept IDs you used:\n{id_report}\n\nIMPORTANT: Ensure you are using standard BigQuery syntax. Return ONLY the corrected SQL."]
                })
        
        else:
            history.append({"role": "model", "parts": [text]})
            history.append({"role": "user", "parts": ["Please output a command: either 'LOOKUP: term' or 'SQL: query'."]})

    print(f"\n🛑 STOPPING: Reached maximum turn limit ({max_turns}).")
    logger.error("STOPPING: Reached maximum turn limit.")
    # Save history even on failure to allow debugging/continuation
    last_history = history
    return "Failed to generate valid SQL."

if __name__ == "__main__":
    pass
