import re

with open('agent/server.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace _clean_final_answer function
# Use a pattern to find the function
start_marker = 'def _clean_final_answer(text: str) -> str:'
end_marker = 'def _extract_thought_only'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print(f"ERROR: markers not found! start={start_idx}, end={end_idx}")
    exit(1)

new_func = '''def _clean_final_answer(text: str) -> str:
    """
    Strip raw Python code, code fences, tool call lines, and smolagents
    internal markers from the final answer so only human-readable text
    reaches the frontend chat bubble.
    """
    if not text:
        return text

    original = text
    was_all_code = _looks_like_raw_code(original)

    # Remove fenced code blocks
    text = re.sub(r\'```(?:py|python)?[\\s\\S]*?```\', \'\', text)
    # Remove <end_code> markers
    text = re.sub(r\'<end_code>\', \'\', text)
    # Remove Python tool call lines: var = tool(...) or tool(...)
    text = re.sub(r\'^[\\w_]+ ?= ?[\\w_]+\\(.*\\)\\s*$\', \'\', text, flags=re.MULTILINE)
    text = re.sub(r\'^print\\(.*\\)\\s*$\', \'\', text, flags=re.MULTILINE)
    text = re.sub(r\'^[\\w_]+\\(.*\\)\\s*$\', \'\', text, flags=re.MULTILINE)
    # Remove lone "code" header
    text = re.sub(r\'^code\\s*$\', \'\', text, flags=re.MULTILINE | re.IGNORECASE)
    # Remove "Thought:" prefix lines
    text = re.sub(r\'^Thought\\s*:.*$\', \'\', text, flags=re.MULTILINE | re.IGNORECASE)
    # Remove "Code:" header lines
    text = re.sub(r\'^Code\\s*:\\s*$\', \'\', text, flags=re.MULTILINE | re.IGNORECASE)
    # Collapse multiple blank lines
    text = re.sub(r\'\\n{3,}\', \'\\n\\n\', text)
    cleaned = text.strip()

    # If the original was raw code and cleaning left too little, return empty
    # so the caller can substitute a proper fallback
    if was_all_code and len(cleaned) < 60:
        return \'\'
    return cleaned


'''

new_content = content[:start_idx] + new_func + content[end_idx:]

with open('agent/server.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("SUCCESS: _clean_final_answer updated")
print(f"New function length: {len(new_func)} chars")
