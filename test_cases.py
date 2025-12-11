# Define your test cases here
# Each test case should have a 'prompt' and an 'expected_sql' (or key elements to check)

TEST_CASES = [
    {
        "id": "t2d_women_60",
        "prompt": "Cohort of women over 60 with Type 2 Diabetes",
        "description": "Basic demographic and condition filter",
        # You can store the full expected SQL, or just keywords to validate
        "expected_keywords": [
            "SELECT",
            "FROM person",
            "JOIN condition_occurrence",
            "gender_concept_id = 8532", # Female
            "condition_concept_id"
        ]
    },
    {
        "id": "hypertension_men",
        "prompt": "Men with Hypertension",
        "description": "Simple condition lookup for men",
        "expected_keywords": [
            "gender_concept_id = 8507", # Male
            "condition_concept_id"
        ]
    },
    {
        "id": "hypertension_men",
        "prompt": "Men with Hypertension",
        "description": "Simple condition lookup for men",
        "expected_keywords": [
            "gender_concept_id = 8507", # Male
            "condition_concept_id"
        ]
    }
]
