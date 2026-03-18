# @title 🧬 Setup & Run All of Us Cohort Scout
import os
import sys
import getpass
from google.colab import userdata

# 1. RESET DIRECTORY
os.chdir('/content')

# 2. UPDATE & RESTART
try:
    import google.generativeai as genai
    # Check for the configure method to ensure new version
    if not hasattr(genai, 'configure'): raise ImportError
except (ImportError, AttributeError):
    print("🔄 Updating libraries...")
    !pip install -q -U google-generativeai duckdb
    print("⚠️ Runtime updated. Restarting session...")
    os.kill(os.getpid(), 9)

# 3. CLONE OR UPDATE REPO
if os.path.exists("OMOPbuilder"):
    os.chdir("OMOPbuilder")
    print("⬇️ Updating code...")
    !git pull
else:
    print("⬇️ Cloning repository...")
    !git clone https://github.com/aperrault/OMOPbuilder.git
    os.chdir("OMOPbuilder")

# 4. SETUP API KEY
try:
    api_key = userdata.get('GEMINI_API_KEY')
except:
    print("🔑 Enter your Google Gemini API Key below:")
    api_key = getpass.getpass()

os.environ['GOOGLE_API_KEY'] = api_key

# 5. CHECK FOR RESOURCES (Conditional Instructions)
import glob

# Check for Schema
omop_files = glob.glob("OMOP_CDM_*.csv")
if omop_files:
    print(f"\n✅ SCHEMA DETECTED: {omop_files[0]}")
else:
    print("\n" + "="*55)
    print("⚠️ SCHEMA DEFINITION MISSING")
    print("To enable accurate schema validation:")
    print("  1. Go to https://github.com/OHDSI/CommonDataModel/releases/tag/v5.3.1")
    print("  2. Download 'OMOP_CDM_v5.3.1.zip' (Source code).")
    print("  3. Unzip and find 'OMOP_CDM_v5_3_1.csv'.")
    print("  4. Drag it into the 'OMOPbuilder' folder (left sidebar).")
    print("="*55)

# Check for Vocabulary
if os.path.exists("CONCEPT.csv"):
    if os.path.exists("CONCEPT_ANCESTOR.csv"):
        print("\n✅ PRECISE MODE: ACTIVE (Vocabulary & Ancestors Detected)")
    else:
        print("\n⚠️ PARTIAL PRECISE MODE: CONCEPT.csv found, but CONCEPT_ANCESTOR.csv missing.")
        print("   (Ancestor lookups will be disabled)")
else:
    print("\n" + "="*55)
    print("⚠️ PRECISE MODE IS OFF (Running in Fuzzy/String Mode)")
    print("To enable precise lookup of standard OMOP Concept IDs:")
    print("  1. Go to https://athena.ohdsi.org -> Login -> 'Vocabulary'.")
    print("  2. Check: SNOMED, RxNorm, LOINC, PPI.")
    print("  3. Download, unzip, and find 'CONCEPT.csv' and 'CONCEPT_ANCESTOR.csv'.")
    print("  4. Drag them into the 'OMOPbuilder' folder (left sidebar).")
    print("  5. Re-run this cell.")
    print("="*55 + "\n")

# 6. RUN AGENT
import importlib
import core
importlib.reload(core)
from core import agent_loop

print("✅ Setup Complete!")
print("-" * 50)

# Change this text to test your specific cohort
user_query = "Find Hispanic women over 60 with Type 2 Diabetes who have never taken Metformin."
sql_output = agent_loop(user_query)

print("\n" + "="*20 + " FINAL SQL " + "="*20)
print(sql_output)

# @title 🔄 Refine SQL (Paste Error or Request Here)
# Run this cell if you get an error in BigQuery or want to change the query.

feedback = "Paste your error message or change request here" # @param {type:"string"}

if feedback and feedback != "Paste your error message or change request here":
    print(f"🚀 Sending feedback to agent: '{feedback}'")
    print("-" * 50)
    
    # Continue the existing conversation
    new_sql = core.agent_loop(feedback, is_continuation=True)
    
    print("\n" + "="*20 + " REVISED SQL " + "="*20)
    print(new_sql)
else:
    print("⚠️ Please enter your feedback in the text box above.")