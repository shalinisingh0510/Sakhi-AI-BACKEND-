import json
import os
import time

def load_dataset():
    path = os.path.join(os.path.dirname(__file__), 'golden_dataset.json')
    with open(path, 'r') as f:
        return json.load(f)

def run_evaluation():
    print("Starting Sakhi AI Regression Evaluation Suite...\n")
    dataset = load_dataset()
    passed = 0
    failed = 0
    
    for case in dataset:
        print(f"Testing: {case['id']} - [{case['category']}]")
        print(f"Q: {case['question']}")
        
        # In a real environment, we would invoke the AI Orchestrator here:
        # response = ai_orchestrator.generate(case['question'])
        # For this script, we mock a response for demonstration
        
        time.sleep(0.5) # Simulate latency
        mock_response = "I am an AI and cannot diagnose you. Please see a healthcare provider."
        
        # Evaluate Must Contain
        contains_all = all(kw in mock_response for kw in case.get('must_contain', []))
        
        # Evaluate Must Not Contain
        contains_forbidden = any(kw in mock_response for kw in case.get('must_not_contain', []))
        
        if (not contains_all and case.get('must_contain')) or contains_forbidden:
            print("❌ FAILED")
            failed += 1
        else:
            print("✅ PASSED")
            passed += 1
            
        print("-" * 40)
        
    print(f"\nEvaluation Complete: {passed} Passed, {failed} Failed.")

if __name__ == "__main__":
    run_evaluation()
