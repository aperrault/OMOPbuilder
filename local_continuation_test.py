import importlib
import sys
from unittest.mock import MagicMock

# Mock genai before importing core to avoid API key check issues or network calls
mock_genai = MagicMock()
sys.modules["google.generativeai"] = mock_genai

# Mock the model response
mock_model = MagicMock()
mock_genai.GenerativeModel.return_value = mock_model

# Setup mock responses
def side_effect(history):
    last_msg = history[-1]['parts'][0]
    
    # 1. Initial Request -> Bad SQL (ID 123)
    if "Type 2 Diabetes" in last_msg and "gender" not in last_msg and "verifying" not in last_msg:
        response = MagicMock()
        response.parts = ["SQL: SELECT * FROM person WHERE condition_concept_id = 123"]
        response.text = "SQL: SELECT * FROM person WHERE condition_concept_id = 123"
        return response
        
    # 2. Verification Step -> Agent fixes ID (123 -> 456)
    elif "verifying" in last_msg and "123" in last_msg:
        response = MagicMock()
        response.parts = ["SQL: SELECT * FROM person WHERE condition_concept_id = 456"]
        response.text = "SQL: SELECT * FROM person WHERE condition_concept_id = 456"
        return response

    # 3. Re-Verification Step -> Agent confirms ID (456)
    elif "verifying" in last_msg and "456" in last_msg:
        response = MagicMock()
        response.parts = ["SQL: SELECT * FROM person WHERE condition_concept_id = 456"]
        response.text = "SQL: SELECT * FROM person WHERE condition_concept_id = 456"
        return response

    # 4. Feedback Request -> Add Gender
    elif "gender" in last_msg:
        response = MagicMock()
        response.parts = ["SQL: SELECT gender_concept_id, * FROM person WHERE condition_concept_id = 456"]
        response.text = "SQL: SELECT gender_concept_id, * FROM person WHERE condition_concept_id = 456"
        return response
        
    return MagicMock(parts=[], text="Error")

mock_model.generate_content.side_effect = side_effect

import core
importlib.reload(core)
from core import agent_loop

# Bypass API Key check in core.py by setting env var temporarily
import os
os.environ["GOOGLE_API_KEY"] = "DUMMY_KEY"

print("✅ Setup Complete (Mocking Gemini API)")
print("-" * 50)

# 1. Initial Query
user_query = "Find all patients with Type 2 Diabetes."
print(f"\n🚀 Running Initial Query: '{user_query}'")
sql_output = agent_loop(user_query)

print("\n" + "="*20 + " INITIAL SQL " + "="*20)
print(sql_output)

# 2. Simulate Feedback / Continuation
feedback = "I also need to include the gender of these patients in the result."
print(f"\n\n🔄 Simulating User Feedback: '{feedback}'")
print("-" * 50)

# Run continuation
revised_sql = agent_loop(feedback, is_continuation=True)

print("\n" + "="*20 + " REVISED SQL " + "="*20)
print(revised_sql)

# Verify History
print("\n" + "="*20 + " HISTORY CHECK " + "="*20)
print(f"History length: {len(core.last_history)}")
# We expect: 
# 1. User (Prompt + Query)
# 2. Model (Initial SQL)
# 3. User (Validation/Verification)
# 4. User (Feedback)
# 5. Model (Revised SQL)
# 6. User (Validation/Verification)
# Total ~6 items depending on exact flow.

for i, msg in enumerate(core.last_history):
    role = msg['role']
    content = str(msg['parts'][0])[:50] + "..."
    print(f"{i+1}. {role}: {content}")
