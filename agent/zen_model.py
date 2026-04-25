"""
Custom OpenAI-compatible model for OpenCode Zen
"""
import os
import sys
import json
import re
import requests
from typing import Any, List, Dict, Optional
from dotenv import load_dotenv
from pathlib import Path

# Load .env
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

from smolagents.models import Model, ChatMessage
from smolagents.tools import Tool

# Observability — optional, no-op if keys not set
try:
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent))
    import observability as _obs
except Exception:
    _obs = None


def _count_unmatched_parens(code: str) -> int:
    """Count unmatched open parens in code, ignoring parens inside strings."""
    depth = 0
    in_single = False
    in_double = False
    i = 0
    while i < len(code):
        c = code[i]
        # Handle escape sequences
        if c == '\\' and i + 1 < len(code):
            i += 2
            continue
        if c == "'" and not in_double:
            in_single = not in_single
        elif c == '"' and not in_single:
            in_double = not in_double
        elif not in_single and not in_double:
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
        i += 1
    return depth


def _is_string_terminated(line: str) -> bool:
    """Return True if all string literals on the line are properly closed."""
    in_single = False
    in_double = False
    i = 0
    while i < len(line):
        c = line[i]
        if c == '\\' and i + 1 < len(line):
            i += 2
            continue
        if c == "'" and not in_double:
            in_single = not in_single
        elif c == '"' and not in_single:
            in_double = not in_double
        i += 1
    return not in_single and not in_double


class ZenModel(Model):
    """OpenCode Zen model - OpenAI compatible API"""

    def __init__(
        self,
        model_id: str = "minimax-m2.5-free",
        api_key: str = None,
        base_url: str = "https://opencode.ai/zen/v1",
        **kwargs,
    ):
        self.model_id = model_id
        self.api_key = api_key or os.getenv("ZEN_API_KEY")
        self.base_url = base_url
        self.max_tokens = kwargs.get("max_tokens", 4096)
        self.temperature = kwargs.get("temperature", 0.3)
        self.last_input_token_count = 0
        self.last_output_token_count = 0
        self.custom_role_conversions = {"tool-response": "tool"}

        if not self.api_key:
            print("[ZenModel] WARNING: ZEN_API_KEY not found in environment!")
        else:
            print(f"[ZenModel] Initialized with model={self.model_id}, base_url={self.base_url}")

    def _get_headers(self):
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _serialize_content(self, content):
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        parts.append(str(item.get("text", "")))
                    elif "text" in item:
                        parts.append(str(item["text"]))
                    elif "content" in item:
                        parts.append(str(item["content"]))
                    else:
                        parts.append(json.dumps(item))
                else:
                    parts.append(str(item))
            return "\n".join(parts) if parts else ""
        return str(content)

    def _convert_role(self, role):
        role_str = str(role).lower()
        if "system" in role_str:
            return "system"
        if "assistant" in role_str:
            return "assistant"
        if "tool" in role_str:
            return "user"
        return "user"

    # ------------------------------------------------------------------
    # Code body fixer
    # ------------------------------------------------------------------
    def _fix_code_body(self, code: str) -> str:
        """Fix common issues inside a code block:
        1. final_answer() with no args — find the variable and inject it
        2. Unterminated string on last line — close the quote
        3. Unbalanced parentheses — counted correctly, ignoring parens inside strings
        """
        lines = code.rstrip().split('\n')
        if not lines:
            return code

        # Fix 1: final_answer() with no args
        for i, line in enumerate(lines):
            if re.match(r'\s*final_answer\(\s*\)\s*$', line):
                for j in range(i - 1, max(i - 15, -1), -1):
                    var_match = re.match(r'\s*(\w+)\s*=\s*["\']', lines[j])
                    if var_match:
                        var_name = var_match.group(1)
                        lines[i] = re.sub(r'final_answer\(\s*\)', f'final_answer({var_name})', lines[i])
                        print(f"[ZenModel._fix_code_body] Fixed final_answer() -> final_answer({var_name})")
                        break

        # Find last non-empty line index
        last_idx = len(lines) - 1
        while last_idx >= 0 and not lines[last_idx].strip():
            last_idx -= 1
        if last_idx < 0:
            return '\n'.join(lines)

        # Fix 2: Unterminated string on last line
        if not _is_string_terminated(lines[last_idx]):
            # Figure out which quote type is open
            in_single = False
            in_double = False
            i = 0
            line = lines[last_idx]
            while i < len(line):
                c = line[i]
                if c == '\\' and i + 1 < len(line):
                    i += 2
                    continue
                if c == "'" and not in_double:
                    in_single = not in_single
                elif c == '"' and not in_single:
                    in_double = not in_double
                i += 1
            if in_single:
                lines[last_idx] = lines[last_idx] + "'"
                print("[ZenModel._fix_code_body] Fixed unterminated single quote")
            elif in_double:
                lines[last_idx] = lines[last_idx] + '"'
                print("[ZenModel._fix_code_body] Fixed unterminated double quote")

        # Fix 3: Unbalanced parens — count correctly ignoring parens inside strings
        full_code = '\n'.join(lines)
        open_parens = _count_unmatched_parens(full_code)
        if open_parens > 0:
            lines[last_idx] = lines[last_idx].rstrip() + ')' * open_parens
            print(f"[ZenModel._fix_code_body] Fixed {open_parens} unclosed parens")
        elif open_parens < 0:
            # More closing than opening — strip excess from end
            excess = abs(open_parens)
            tail = lines[last_idx].rstrip()
            while excess > 0 and tail.endswith(')'):
                tail = tail[:-1]
                excess -= 1
            lines[last_idx] = tail
            print(f"[ZenModel._fix_code_body] Removed {abs(open_parens)} excess closing parens")

        return '\n'.join(lines)

    # ------------------------------------------------------------------
    # Main code fixer
    # ------------------------------------------------------------------
    def _fix_truncated_code(self, content: str) -> str:
        """Fix code blocks that were truncated or malformed by the API."""

        has_code_section = bool(re.search(r'\bCode:\s*\n', content, re.IGNORECASE))
        has_fence_opener = bool(re.search(r'```(?:py|python)\n', content))
        has_end_code = '<end_code>' in content

        # Pattern 0: No code at all — but skip planning steps
        if not has_code_section and not has_fence_opener and not has_end_code:
            is_planning = bool(re.search(
                r'(^#{1,3}\s|^Plan:|^Step \d|^Facts|^Updated facts)',
                content, re.MULTILINE | re.IGNORECASE
            ))
            if not is_planning:
                safe = content.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
                injected = (
                    content.rstrip()
                    + '\n\nCode:\n```py\nfinal_answer("'
                    + safe[:800]
                    + '\\n\\nDisclaimer: This is informational guidance only, not legal advice.")\n```<end_code>'
                )
                print("[ZenModel._fix_truncated_code] (p0) Injected final_answer for pure-thought response")
                return injected
            return content

        # Pattern 1: Code: section but no fence
        if has_code_section and not has_fence_opener:
            fixed = re.sub(
                r'(Code:\s*\n\s*)',
                lambda m: m.group(0) + '```py\n',
                content, count=1, flags=re.IGNORECASE,
            )
            fixed = fixed.replace('<end_code>', '').rstrip()
            code_start = re.search(r'```py\n', fixed)
            if code_start:
                code_body = fixed[code_start.end():]
                fixed_body = self._fix_code_body(code_body)
                fixed = fixed[:code_start.end()] + fixed_body
            fixed = fixed.rstrip() + '\n```<end_code>'
            print("[ZenModel._fix_truncated_code] (p1) Injected missing ```py fence")
            return fixed

        if not has_fence_opener:
            return content

        # Patterns 2+: has fence opener — extract code body and fix it
        content_clean = content.replace('<end_code>', '')
        all_opens = list(re.finditer(r'```(?:py|python)\n', content_clean))
        last_open = all_opens[-1]
        before_code = content_clean[:last_open.end()]
        code_after = content_clean[last_open.end():]

        # Strip any existing closing fence from code_after before fixing
        closing_fence = chr(96) * 3
        code_body_raw = re.sub(r'\n' + closing_fence + r'\s*$', '', code_after, flags=re.MULTILINE)

        fixed_body = self._fix_code_body(code_body_raw)
        result = before_code + fixed_body + '\n' + closing_fence + '<end_code>'

        if code_body_raw != code_after.rstrip():
            print(f"[ZenModel._fix_truncated_code] Fixed code body, tail: {result[-80:]!r}")

        return result

    # ------------------------------------------------------------------
    # API call
    # ------------------------------------------------------------------
    def __call__(
        self,
        messages: List[Dict[str, str]],
        stop_sequences: Optional[List[str]] = None,
        grammar: Optional[str] = None,
        tools_to_call_from: Optional[List[Tool]] = None,
        **kwargs,
    ) -> ChatMessage:
        print(f"\n[ZenModel.__call__] Received {len(messages)} messages")

        api_messages = []
        for i, msg in enumerate(messages):
            if msg is None:
                continue
            role = self._convert_role(msg.get("role", "user"))
            content = self._serialize_content(msg.get("content", ""))
            print(f"  [msg {i}] role={role}, len={len(content)}, preview={content[:80]!r}...")
            if not content.strip() and role != "system":
                continue
            api_messages.append({"role": role, "content": content})

        if not api_messages:
            return ChatMessage(
                role="assistant",
                content='Thought: No input.\n\nCode:\n```py\nfinal_answer("Please describe your legal situation.")\n```<end_code>',
            )

        if stop_sequences:
            print(f"[ZenModel.__call__] stop_sequences (not forwarded): {stop_sequences}")

        import time as _time
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model_id,
            "messages": api_messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=self._get_headers(), json=payload, timeout=120)
                print(f"[ZenModel.__call__] Status: {response.status_code}")

                if response.status_code == 429:
                    wait = min(2 ** attempt * 3, 15)
                    print(f"[ZenModel.__call__] Rate limited, retrying in {wait}s")
                    _time.sleep(wait)
                    continue

                if response.status_code != 200:
                    return ChatMessage(
                        role="assistant",
                        content='Thought: API error.\n\nCode:\n```py\nfinal_answer("Temporary issue. Please try again.")\n```<end_code>',
                    )

                result = response.json()
                if not result.get("choices"):
                    return ChatMessage(
                        role="assistant",
                        content='Thought: No response.\n\nCode:\n```py\nfinal_answer("Could not generate response. Please try again.")\n```<end_code>',
                    )

                choice = result["choices"][0]
                finish_reason = choice.get("finish_reason", "unknown")
                rm = choice["message"]
                content = rm.get("content") or rm.get("reasoning_content") or rm.get("reasoning") or ""

                if not content:
                    content = 'Thought: Empty.\n\nCode:\n```py\nfinal_answer("Please describe your situation in more detail.")\n```<end_code>'

                usage = result.get("usage", {})
                if usage:
                    self.last_input_token_count = usage.get("prompt_tokens", 0)
                    self.last_output_token_count = usage.get("completion_tokens", 0)

                print(f"[ZenModel.__call__] OK: len={len(content)}, in={self.last_input_token_count}, out={self.last_output_token_count}, finish={finish_reason}")
                print(f"[ZenModel.__call__] Preview: {content[:200]!r}...")

                if _obs and _obs.is_enabled():
                    _trace = getattr(self, "_current_trace", None)
                    _obs.log_llm_call(
                        trace=_trace, model=self.model_id,
                        prompt_tokens=self.last_input_token_count,
                        completion_tokens=self.last_output_token_count,
                        input_preview=api_messages[-1].get("content", "")[:300] if api_messages else "",
                        output_preview=content[:300],
                    )

                content = self._fix_truncated_code(content)
                return ChatMessage(role=rm.get("role", "assistant"), content=content)

            except requests.exceptions.Timeout:
                print(f"[ZenModel.__call__] Timeout (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    _time.sleep(2 ** attempt)
                    continue
                return ChatMessage(
                    role="assistant",
                    content='Thought: Timeout.\n\nCode:\n```py\nfinal_answer("Request timed out. Please try again.")\n```<end_code>',
                )
            except requests.exceptions.ConnectionError as e:
                print(f"[ZenModel.__call__] Connection error (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    _time.sleep(2 ** attempt * 2)
                    continue
                return ChatMessage(
                    role="assistant",
                    content='Thought: Connection error.\n\nCode:\n```py\nfinal_answer("Connection error. Please check your internet.")\n```<end_code>',
                )
            except Exception as e:
                print(f"[ZenModel.__call__] Error: {type(e).__name__}: {e}")
                return ChatMessage(
                    role="assistant",
                    content='Thought: Error.\n\nCode:\n```py\nfinal_answer("An error occurred. Please try again.")\n```<end_code>',
                )

    def generate(self, messages: list, stop: list = None, **kwargs) -> ChatMessage:
        message_dicts = []
        for msg in messages:
            if msg is None:
                continue
            if isinstance(msg, dict):
                message_dicts.append(msg)
            else:
                message_dicts.append({"role": getattr(msg, "role", "user"), "content": getattr(msg, "content", "")})
        stop_sequences = kwargs.pop("stop_sequences", stop)
        return self.__call__(message_dicts, stop_sequences=stop_sequences, **kwargs)

    def generate_stream(self, messages: list, stop: list = None, **kwargs):
        stop_sequences = kwargs.pop("stop_sequences", stop)
        yield self.generate(messages, stop=stop_sequences, **kwargs)

    def get_client(self):
        return self


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    model = ZenModel(model_id="minimax-m2.5-free")
    resp = model([{"role": "user", "content": "What is 2+2? Reply in one word."}])
    print(f"\nTest result: {resp.content}")
