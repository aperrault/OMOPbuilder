import importlib
import sys
from unittest.mock import MagicMock

# Mock genai before importing core to avoid API key check issues or network calls
mock_genai = MagicMock()
sys.modules["google.genai"] = mock_genai
sys.modules["google"] = MagicMock(genai=mock_genai)

# Mock the client and model response
mock_client = MagicMock()
mock_genai.Client.return_value = mock_client
mock_model = mock_client.models

# Use real concept ID (201826 = Type 2 diabetes mellitus) and valid SQL
INITIAL_SQL = "SELECT * FROM condition_occurrence WHERE condition_concept_id = 201826"
REVISED_SQL = "SELECT co.*, p.gender_concept_id FROM condition_occurrence co JOIN person p ON co.person_id = p.person_id WHERE co.condition_concept_id = 201826"

# Setup mock responses
def side_effect(*, model=None, contents=None, **kwargs):
    last_msg = contents[-1]['parts'][0]

    # 1. Initial request -> return SQL
    if "USER REQUEST:" in last_msg:
        response = MagicMock()
        response.parts = [f"SQL: {INITIAL_SQL}"]
        response.text = f"SQL: {INITIAL_SQL}"
        return response

    # 2. Verification step -> confirm SQL unchanged
    if "verifying" in last_msg.lower():
        response = MagicMock()
        # Check if we're in the continuation flow (gender query)
        has_gender = any("gender" in str(m['parts'][0]).lower() and "USER FEEDBACK:" in str(m['parts'][0])
                        for m in contents if m['role'] == 'user')
        sql = REVISED_SQL if has_gender else INITIAL_SQL
        response.parts = [f"SQL: {sql}"]
        response.text = f"SQL: {sql}"
        return response

    # 3. Continuation feedback -> return revised SQL
    if "USER FEEDBACK:" in last_msg:
        response = MagicMock()
        response.parts = [f"SQL: {REVISED_SQL}"]
        response.text = f"SQL: {REVISED_SQL}"
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
assert "condition_occurrence" in sql_output, "Initial query should return valid SQL"
assert "201826" in sql_output, "Initial query should use correct concept ID"

# 2. Simulate Feedback / Continuation
feedback = "I also need to include the gender of these patients in the result."
print(f"\n\n🔄 Simulating User Feedback: '{feedback}'")
print("-" * 50)

revised_sql = agent_loop(feedback, is_continuation=True)

print("\n" + "="*20 + " REVISED SQL " + "="*20)
print(revised_sql)
assert "gender_concept_id" in revised_sql, "Revised query should include gender"
assert "201826" in revised_sql, "Revised query should keep correct concept ID"

# Verify History
print("\n" + "="*20 + " HISTORY CHECK " + "="*20)
print(f"History length: {len(core.last_history)}")
assert len(core.last_history) > 0, "History should be preserved for continuation"

for i, msg in enumerate(core.last_history):
    role = msg['role']
    content = str(msg['parts'][0])[:60] + "..."
    print(f"{i+1}. {role}: {content}")

print("\n✅ All assertions passed!")
