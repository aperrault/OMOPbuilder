import google.generativeai as genai
from IPython.display import Markdown

# 1. SETUP (User inputs their key)
GOOGLE_API_KEY = "PASTE_YOUR_KEY_HERE"
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro-latest')

# 2. THE SYSTEM PROMPT (The "Context")
# We hard-code the OMOP schema so the LLM knows the structure perfectly.
omop_context = """
You are an expert SQL Generator for the NIH All of Us dataset (BigQuery).
Schema: OMOP CDM v5.3.

Core Tables:
- person (person_id, year_of_birth, gender_concept_id, race_concept_id)
- condition_occurrence (person_id, condition_concept_id, condition_start_date)
- drug_exposure (person_id, drug_concept_id, drug_exposure_start_date)
- measurement (person_id, measurement_concept_id, value_as_number)
- concept (concept_id, concept_name, domain_id, vocabulary_id)

RULES:
1. DIALECT: Use Google Standard SQL.
2. NO HALLUCINATION: Do NOT guess integer Concept IDs.
3. LOOKUP LOGIC: To find a disease or drug, you MUST join the `concept` table and match on `concept_name` using REGEXP_CONTAINS(concept_name, r'(?i)YOUR_TERM').
4. OPTIMIZATION: Always select `DISTINCT person_id` to avoid duplicates.
"""

# 3. THE GENERATOR FUNCTION
def generate_cohort_query(user_request):
    prompt = f"{omop_context}\n\nUSER REQUEST: {user_request}\n\nSQL:"
    response = model.generate_content(prompt)
    return response.text

# 4. RUN IT
user_request = "Find me all Hispanic women over age 60 who have Type 2 Diabetes."
sql_output = generate_cohort_query(user_request)

# Display pretty output
print("### Generated SQL for All of Us Workbench")
print(sql_output)