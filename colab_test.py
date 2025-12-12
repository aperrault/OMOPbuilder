import importlib
import core
importlib.reload(core)
from core import agent_loop

print("✅ Setup Complete!")
print("-" * 50)

# Change this text to test your specific cohort
user_query = "Calculate the total cumulative dose of Warfarin (in milligrams) for each patient who started the drug in 2023. Return the top 5 patients with the highest cumulative exposure."
sql_output = agent_loop(user_query)

print("\n" + "="*20 + " FINAL SQL " + "="*20)
print(sql_output)