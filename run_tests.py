from core import agent_loop
from test_cases import TEST_CASES
import sys

def run_tests():
    print(f"🧪 Running {len(TEST_CASES)} test cases...\n")
    passed = 0
    failed = 0

    for test in TEST_CASES:
        print(f"▶️  Running Test: {test['id']} - {test['description']}")
        print(f"   Prompt: '{test['prompt']}'")
        
        try:
            # Run the agent
            generated_sql = agent_loop(test['prompt'])
            
            # Basic Validation: Check if it returned an error string
            if generated_sql.startswith("Failed") or "VALIDATION ERROR" in generated_sql:
                print(f"❌ FAILED: Agent failed to generate valid SQL.")
                failed += 1
                continue

            # Check for expected keywords
            missing_keywords = []
            for keyword in test.get('expected_keywords', []):
                if keyword.lower() not in generated_sql.lower():
                    missing_keywords.append(keyword)
            
            if missing_keywords:
                print(f"❌ FAILED: Missing expected keywords: {missing_keywords}")
                print(f"   Generated SQL:\n{generated_sql}\n")
                failed += 1
            else:
                print(f"✅ PASSED\n")
                passed += 1
                
        except Exception as e:
            print(f"❌ ERROR: Exception occurred: {e}")
            failed += 1

    print("="*30)
    print(f"Test Summary: {passed} Passed, {failed} Failed")
    print("="*30)

    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
