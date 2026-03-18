import importlib
import core
importlib.reload(core)
from core import agent_loop

print("✅ Setup Complete!")
print("-" * 50)

# Change this text to test your specific cohort
user_query = "Find me Hispanic patients who have neoplasm of uncertain behavior of uterus"
sql_output = agent_loop(user_query)

print("\n" + "="*20 + " FINAL SQL " + "="*20)
print(sql_output)