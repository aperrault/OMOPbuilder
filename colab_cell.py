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
if os.path.exists("aou_scout"):
    os.chdir("aou_scout")
    print("⬇️ Updating code from Gist...")
    !git pull
else:
    print("⬇️ Cloning repository...")
    !git clone https://gist.github.com/1e2a38b932ccb22433be9b065fb3673d.git aou_scout
    os.chdir("aou_scout")

# 4. SETUP API KEY
try:
    api_key = userdata.get('GEMINI_API_KEY')
except:
    print("🔑 Enter your Google Gemini API Key below:")
    api_key = getpass.getpass()

os.environ['GOOGLE_API_KEY'] = api_key

# 5. CHECK FOR PRECISE MODE (Conditional Instructions)
if os.path.exists("CONCEPT.csv"):
    print("\n✅ PRECISE MODE: ACTIVE (Vocabulary Detected)")
else:
    print("\n" + "="*55)
    print("⚠️ PRECISE MODE IS OFF (Running in Fuzzy/String Mode)")
    print("To enable precise lookup of standard OMOP Concept IDs:")
    print("  1. Go to https://athena.ohdsi.org -> Login -> 'Vocabulary'.")
    print("  2. Check: SNOMED, RxNorm, LOINC, PPI.")
    print("  3. Download, unzip, and find 'CONCEPT.csv'.")
    print("  4. Drag 'CONCEPT.csv' into the 'aou_scout' folder (left sidebar).")
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