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


class ZenModel(Model):
    """OpenCode Zen model - OpenAI compatible API
    
    Implements __call__ which is the method smolagents actually invokes
    when the agent needs a model response.
    """
    
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
            "Content-Type": "application/json"
        }
    
    def _serialize_content(self, content):
        """Safely serialize message content for the API.
        
        smolagents passes content in several formats:
        - str: plain text
        - list[dict]: structured content blocks e.g. [{"type": "text", "text": "..."}]
        - None: empty message
        """
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
        """Convert smolagents roles to OpenAI-compatible roles."""
        role_str = str(role).lower()
        # Handle MessageRole enum values
        if "system" in role_str:
            return "system"
        if "assistant" in role_str:
            return "assistant"
        if "tool" in role_str:
            return "user"  # Zen API doesn't support "tool" role  
        return "user"
    
    def _fix_truncated_code(self, content: str) -> str:
        """Fix code blocks that were truncated by the API.
        
        The big-pickle model sometimes stops mid-output, leaving code blocks
        without closing ``` and <end_code> tags. This causes smolagents to
        fail with 'regex pattern not found' errors.
        """
        import re
        
        # Check if there's an opening code block
        has_opening = bool(re.search(r'```(?:py|python)\n', content))
        has_closing = bool(re.search(r'\n```', content))
        
        if not has_opening:
            return content  # No code block to fix
        
        if has_opening and not has_closing:
            print("[ZenModel._fix_truncated_code] Detected truncated code block, fixing...")
            
            # Get everything after the last ```py opening
            match = list(re.finditer(r'```(?:py|python)\n', content))
            if match:
                last_open = match[-1]
                code_part = content[last_open.end():]
                
                # Fix incomplete last line — balance parentheses
                open_parens = code_part.count('(') - code_part.count(')')
                if open_parens > 0:
                    code_part = code_part.rstrip()
                    code_part += ')' * open_parens
                    content = content[:last_open.end()] + code_part
                
            # Append closing markers
            content = content.rstrip() + '\n```<end_code>'
            print(f"[ZenModel._fix_truncated_code] Fixed content tail: ...{content[-80:]!r}")
        
        # Also ensure <end_code> is present if ``` is there but <end_code> is missing
        if has_opening and has_closing and '<end_code>' not in content:
            content = content.rstrip() + '<end_code>'
            print("[ZenModel._fix_truncated_code] Added missing <end_code> tag")
        
        return content
    
    def __call__(
        self,
        messages: List[Dict[str, str]],
        stop_sequences: Optional[List[str]] = None,
        grammar: Optional[str] = None,
        tools_to_call_from: Optional[List[Tool]] = None,
        **kwargs,
    ) -> ChatMessage:
        """Process input messages and return model response.
        
        This is the method smolagents actually calls. Messages come as 
        plain dicts with 'role' and 'content' keys.
        """
        print(f"\n[ZenModel.__call__] Received {len(messages)} messages")
        
        # Convert messages to API-compatible format
        api_messages = []
        for i, msg in enumerate(messages):
            if msg is None:
                print(f"  [msg {i}] SKIPPED: None message")
                continue
            
            # Get role and content from dict
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            # Convert role
            role = self._convert_role(role)
            
            # Serialize content (handles str, list, None)
            content = self._serialize_content(content)
            
            print(f"  [msg {i}] role={role}, content_len={len(content)}, content_preview={content[:100]!r}...")
            
            # Skip empty messages (except system)
            if not content.strip() and role != "system":
                print(f"  [msg {i}] SKIPPED: empty content")
                continue
            
            api_messages.append({
                "role": role,
                "content": content,
            })
        
        if not api_messages:
            print("[ZenModel.__call__] WARNING: No valid messages to send! Returning default response.")
            return ChatMessage(
                role="assistant",
                content="I need more information to help you. Could you please describe your legal situation in detail?",
            )
        
        print(f"[ZenModel.__call__] Sending {len(api_messages)} messages to Zen API...")
        
        # Make the API call with retry
        import time as _time
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model_id,
            "messages": api_messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        
        # NOTE: We intentionally do NOT pass stop_sequences to the API.
        # smolagents passes '<end_code>' as a stop sequence, which causes the
        # API to truncate output BEFORE the closing ``` backticks appear,
        # leading to repeated parsing errors. Instead we let the model finish
        # naturally and post-process the output.
        if stop_sequences:
            print(f"[ZenModel.__call__] stop_sequences received (not forwarded): {stop_sequences}")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    url,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=120,
                )
                
                print(f"[ZenModel.__call__] Response status: {response.status_code}")
                
                if response.status_code == 429:
                    # Rate limited — wait and retry
                    wait = min(2 ** attempt * 3, 15)
                    print(f"[ZenModel.__call__] Rate limited, retrying in {wait}s (attempt {attempt+1}/{max_retries})")
                    _time.sleep(wait)
                    continue
                
                if response.status_code != 200:
                    error_text = response.text[:500]
                    print(f"[ZenModel.__call__] ERROR: {response.status_code} - {error_text}")
                    return ChatMessage(
                        role="assistant",
                        content=f'Thought: The API returned an error ({response.status_code}). I will provide the best answer I can.\n\nCode:\n```py\nfinal_answer("I encountered a temporary issue. Please try your question again.")\n```<end_code>',
                    )
                
                result = response.json()
                
                if not result.get("choices"):
                    print(f"[ZenModel.__call__] ERROR: No choices in response: {json.dumps(result)[:500]}")
                    return ChatMessage(
                        role="assistant",
                        content='Thought: No response was generated. Let me try again.\n\nCode:\n```py\nfinal_answer("I could not generate a response. Please try asking your question again.")\n```<end_code>',
                    )
                
                choice = result["choices"][0]
                finish_reason = choice.get("finish_reason", "unknown")
                response_message = choice["message"]
                content = response_message.get("content") or response_message.get("reasoning_content") or ""
                
                if not content and response_message.get("reasoning"):
                    content = response_message.get("reasoning")
                
                if not content:
                    content = 'Thought: The model returned an empty response. Let me provide a fallback.\n\nCode:\n```py\nfinal_answer("I need more information to help you. Could you please describe your legal situation in detail?")\n```<end_code>'
                    print("[ZenModel.__call__] WARNING: Empty content from API, using fallback")
                
                # Update token counts
                usage = result.get("usage", {})
                if usage:
                    self.last_input_token_count = usage.get("prompt_tokens", 0)
                    self.last_output_token_count = usage.get("completion_tokens", 0)
                
                print(f"[ZenModel.__call__] SUCCESS: content_len={len(content)}, tokens_in={self.last_input_token_count}, tokens_out={self.last_output_token_count}, finish_reason={finish_reason}")
                print(f"[ZenModel.__call__] Content preview: {content[:200]!r}...")
                
                # Post-process: fix truncated code blocks
                content = self._fix_truncated_code(content)
                
                return ChatMessage(
                    role=response_message.get("role", "assistant"),
                    content=content,
                )
                
            except requests.exceptions.Timeout:
                print(f"[ZenModel.__call__] ERROR: Timeout (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    _time.sleep(2 ** attempt)
                    continue
                return ChatMessage(
                    role="assistant", 
                    content='Thought: The request timed out. Let me provide a helpful response.\n\nCode:\n```py\nfinal_answer("The request timed out. Please try again with a simpler query.")\n```<end_code>',
                )
            except requests.exceptions.ConnectionError as e:
                print(f"[ZenModel.__call__] ERROR: Connection error (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    _time.sleep(2 ** attempt * 2)
                    continue
                return ChatMessage(
                    role="assistant",
                    content='Thought: Connection error occurred. Let me provide a fallback response.\n\nCode:\n```py\nfinal_answer("Connection error. Please check your internet and try again.")\n```<end_code>',
                )
            except Exception as e:
                print(f"[ZenModel.__call__] ERROR: Unexpected error: {type(e).__name__}: {e}")
                return ChatMessage(
                    role="assistant",
                    content=f'Thought: An error occurred: {str(e)}. Let me provide a fallback.\n\nCode:\n```py\nfinal_answer("An error occurred. Please try again.")\n```<end_code>',
                )
    
    def generate(
        self,
        messages: list,
        stop: list = None,
        **kwargs,
    ) -> ChatMessage:
        """Compatibility wrapper - delegates to __call__"""
        # Convert ChatMessage objects to dicts if needed
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
        return self.__call__(message_dicts, stop_sequences=stop, **kwargs)
    
    def generate_stream(self, messages: list, stop: list = None, **kwargs):
        """Streaming not supported for Zen, fallback to regular"""
        yield self.generate(messages, stop=stop, **kwargs)
    
    def get_client(self):
        return self


if __name__ == "__main__":
    # Quick test
    from dotenv import load_dotenv
    load_dotenv()
    
    model = ZenModel(model_id="minimax-m2.5-free")
    
    # Test with dict messages (how smolagents actually calls it)
    messages = [
        {"role": "user", "content": "What is 2+2? Reply in one word."}
    ]
    resp = model(messages)
    print(f"\nTest result: {resp.content}")