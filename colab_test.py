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