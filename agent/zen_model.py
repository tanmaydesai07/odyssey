"""
Custom OpenAI-compatible model for OpenCode Zen
"""
import os
import sys
import json
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

        # Required for smolagents CodeAgent
        self.custom_role_conversions = {"tool-response": "tool"}

        if not self.api_key:
            print("[ZenModel] WARNING: ZEN_API_KEY not found in environment!")
        else:
            print(f"[ZenModel] Initialized with model={self.model_id}, base_url={self.base_url}")

    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

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

    def _fix_truncated_code(self, content: str) -> str:
        """Fix code blocks that were truncated or malformed by the API.

        Handles these patterns:
        1. Pure Thought with no code block at all — inject final_answer fallback
        2. Code: section but no ```py fence — inject the fence
        3. Has ```py opener but missing closing ```
        4. Unbalanced parentheses in code
        """
        import re

        # ------------------------------------------------------------------ #
        # Pattern 0: Pure "Thought: ..." with NO Code: section at all.        #
        # The model forgot to write any code. Inject a final_answer call.     #
        # This is what causes the infinite "regex pattern not found" loop.    #
        # ------------------------------------------------------------------ #
        has_code_section = bool(re.search(r'\bCode:\s*\n', content, re.IGNORECASE))
        has_fence_opener = bool(re.search(r'```(?:py|python)\n', content))
        has_end_code = '<end_code>' in content

        if not has_code_section and not has_fence_opener and not has_end_code:
            # Pure thought, no code at all — wrap the thought as a final_answer
            # Escape any quotes in the content
            safe = content.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            injected = (
                content.rstrip()
                + '\n\nCode:\n```py\nfinal_answer("'
                + safe[:800]
                + '\\n\\nDisclaimer: This is informational guidance only, not legal advice.")\n```<end_code>'
            )
            print("[ZenModel._fix_truncated_code] (p0) Injected final_answer for pure-thought response")
            return injected

        # ------------------------------------------------------------------ #
        # Pattern 1: "Code:\n\n<code>" but no ```py fence                     #
        # ------------------------------------------------------------------ #
        if has_code_section and not has_fence_opener:
            fixed = re.sub(
                r'(Code:\s*\n\s*)',
                lambda m: m.group(0) + '```py\n',
                content,
                count=1,
                flags=re.IGNORECASE,
            )
            fixed = fixed.replace('<end_code>', '').rstrip()
            code_start = re.search(r'```py\n', fixed)
            if code_start:
                code_body = fixed[code_start.end():]
                open_parens = code_body.count('(') - code_body.count(')')
                open_brackets = code_body.count('[') - code_body.count(']')
                if open_parens > 0:
                    fixed = fixed.rstrip() + ')' * open_parens
                if open_brackets > 0:
                    fixed = fixed.rstrip() + ']' * open_brackets
            fixed = fixed.rstrip() + '\n```<end_code>'
            print("[ZenModel._fix_truncated_code] (p1) Injected missing ```py fence")
            return fixed

        if not has_fence_opener:
            return content

        # ------------------------------------------------------------------ #
        # Patterns 2 & 3: has opener, check for missing closing               #
        # ------------------------------------------------------------------ #
        content_clean = content.replace('<end_code>', '')
        all_opens = list(re.finditer(r'```(?:py|python)\n', content_clean))
        last_open = all_opens[-1]
        before_code = content_clean[:last_open.end()]
        code_after = content_clean[last_open.end():]

        # Check for closing ``` on its own line
        closing_match = re.search(r'\n```\s*$', code_after, re.MULTILINE)

        if closing_match:
            result = content_clean.rstrip() + '<end_code>'
        else:
            code_lines = code_after.rstrip().split('\n')
            full_code = '\n'.join(code_lines)
            open_parens = full_code.count('(') - full_code.count(')')
            open_brackets = full_code.count('[') - full_code.count(']')
            if open_parens > 0:
                code_lines[-1] = code_lines[-1].rstrip() + ')' * open_parens
                print(f"[ZenModel._fix_truncated_code] Fixed {open_parens} unclosed parens")
            if open_brackets > 0:
                code_lines[-1] = code_lines[-1].rstrip() + ']' * open_brackets
            fixed_code = '\n'.join(code_lines)
            result = before_code + fixed_code + '\n```<end_code>'
            print(f"[ZenModel._fix_truncated_code] Fixed truncated code block, tail: {result[-80:]!r}")

        return result

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
            role = msg.get("role", "user")
            content = msg.get("content", "")
            role = self._convert_role(role)
            content = self._serialize_content(content)
            print(f"  [msg {i}] role={role}, len={len(content)}, preview={content[:80]!r}...")
            if not content.strip() and role != "system":
                continue
            api_messages.append({"role": role, "content": content})

        if not api_messages:
            print("[ZenModel.__call__] WARNING: No valid messages.")
            return ChatMessage(
                role="assistant",
                content='Thought: No input received.\n\nCode:\n```py\nfinal_answer("Please describe your legal situation.")\n```<end_code>',
            )

        print(f"[ZenModel.__call__] Sending {len(api_messages)} messages to Zen API...")

        if stop_sequences:
            print(f"[ZenModel.__call__] stop_sequences received (not forwarded): {stop_sequences}")

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
                response = requests.post(
                    url, headers=self._get_headers(), json=payload, timeout=120
                )
                print(f"[ZenModel.__call__] Response status: {response.status_code}")

                if response.status_code == 429:
                    wait = min(2 ** attempt * 3, 15)
                    print(f"[ZenModel.__call__] Rate limited, retrying in {wait}s")
                    _time.sleep(wait)
                    continue

                if response.status_code != 200:
                    print(f"[ZenModel.__call__] ERROR: {response.status_code} - {response.text[:300]}")
                    return ChatMessage(
                        role="assistant",
                        content='Thought: API error.\n\nCode:\n```py\nfinal_answer("I encountered a temporary issue. Please try again.")\n```<end_code>',
                    )

                result = response.json()
                if not result.get("choices"):
                    return ChatMessage(
                        role="assistant",
                        content='Thought: No response.\n\nCode:\n```py\nfinal_answer("Could not generate a response. Please try again.")\n```<end_code>',
                    )

                choice = result["choices"][0]
                finish_reason = choice.get("finish_reason", "unknown")
                response_message = choice["message"]
                content = (
                    response_message.get("content")
                    or response_message.get("reasoning_content")
                    or response_message.get("reasoning")
                    or ""
                )

                if not content:
                    content = 'Thought: Empty response.\n\nCode:\n```py\nfinal_answer("Please describe your legal situation in more detail.")\n```<end_code>'
                    print("[ZenModel.__call__] WARNING: Empty content, using fallback")

                usage = result.get("usage", {})
                if usage:
                    self.last_input_token_count = usage.get("prompt_tokens", 0)
                    self.last_output_token_count = usage.get("completion_tokens", 0)

                print(f"[ZenModel.__call__] SUCCESS: len={len(content)}, tokens_in={self.last_input_token_count}, tokens_out={self.last_output_token_count}, finish={finish_reason}")
                print(f"[ZenModel.__call__] Preview: {content[:200]!r}...")

                # Log to Langfuse if enabled
                if _obs and _obs.is_enabled():
                    _trace = getattr(self, "_current_trace", None)
                    _obs.log_llm_call(
                        trace=_trace,
                        model=self.model_id,
                        prompt_tokens=self.last_input_token_count,
                        completion_tokens=self.last_output_token_count,
                        input_preview=api_messages[-1].get("content", "")[:300] if api_messages else "",
                        output_preview=content[:300],
                    )

                content = self._fix_truncated_code(content)

                return ChatMessage(
                    role=response_message.get("role", "assistant"),
                    content=content,
                )

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
                    content='Thought: Connection error.\n\nCode:\n```py\nfinal_answer("Connection error. Please check your internet and try again.")\n```<end_code>',
                )
            except Exception as e:
                print(f"[ZenModel.__call__] Unexpected error: {type(e).__name__}: {e}")
                return ChatMessage(
                    role="assistant",
                    content=f'Thought: Error: {str(e)}\n\nCode:\n```py\nfinal_answer("An error occurred. Please try again.")\n```<end_code>',
                )

    def generate(
        self,
        messages: list,
        stop: list = None,
        **kwargs,
    ) -> ChatMessage:
        """Compatibility wrapper - delegates to __call__"""
        message_dicts = []
        for msg in messages:
            if msg is None:
                continue
            if isinstance(msg, dict):
                message_dicts.append(msg)
            else:
                message_dicts.append({
                    "role": getattr(msg, "role", "user"),
                    "content": getattr(msg, "content", ""),
                })
        # Newer smolagents passes stop_sequences as a kwarg — pop to avoid duplicate
        stop_sequences = kwargs.pop("stop_sequences", stop)
        return self.__call__(message_dicts, stop_sequences=stop_sequences, **kwargs)

    def generate_stream(self, messages: list, stop: list = None, **kwargs):
        """Streaming not supported — fallback to regular"""
        stop_sequences = kwargs.pop("stop_sequences", stop)
        yield self.generate(messages, stop=stop_sequences, **kwargs)

    def get_client(self):
        return self


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    model = ZenModel(model_id="minimax-m2.5-free")
    messages = [{"role": "user", "content": "What is 2+2? Reply in one word."}]
    resp = model(messages)
    print(f"\nTest result: {resp.content}")
