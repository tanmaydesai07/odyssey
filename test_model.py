"""Test multiple models for smolagents code format compliance"""
import os, requests, json, time
from dotenv import load_dotenv
load_dotenv('.env')

api_key = os.getenv('ZEN_API_KEY')
url = 'https://opencode.ai/zen/v1/chat/completions'

prompt = """You must respond with a Thought and Code block like this:
Thought: your reasoning
Code:
```py
# your code here
```<end_code>

Task: Call the function case_classifier with argument situation_description="I got scammed at my store". Then print the result.
"""

models = ['big-pickle', 'nemotron-3-super-free', 'ling-2.6-flash-free']

for model_name in models:
    print(f"\n{'='*60}")
    print(f"Testing: {model_name}")
    print(f"{'='*60}")
    
    payload = {
        'model': model_name,
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': 0.3,
        'max_tokens': 2048,
    }
    
    start = time.time()
    try:
        resp = requests.post(url, headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}, json=payload, timeout=30)
        elapsed = time.time() - start
        print(f"Status: {resp.status_code}, Time: {elapsed:.2f}s")
        if resp.status_code == 200:
            content = resp.json()['choices'][0]['message']['content']
            
            # Check if it has the right format
            has_thought = 'Thought:' in content
            has_code = '```py' in content
            has_end = '<end_code>' in content or '```' in content
            
            print(f"Format check: Thought={has_thought}, Code={has_code}, EndCode={has_end}")
            print(f"Response:\n{content[:500]}")
        else:
            print(f"Error: {resp.text[:300]}")
    except Exception as e:
        elapsed = time.time() - start
        print(f"ERROR ({elapsed:.2f}s): {e}")
