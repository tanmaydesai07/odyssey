import ollama
import re

class LLM:
    def __init__(self, model_name="qwen3.5:2b"):
        self.model_name = model_name
        self.system_prompt = (
            "You are DialCraft, a helpful and friendly voice assistant on a phone call. "
            "Keep your answers brief, conversational, and natural — like a real person on the phone. "
            "Limit responses to 2-3 sentences max. Don't use bullet points, markdown, or emojis. "
            "Speak naturally as if having a phone conversation. /no_think"
        )

    def generate_stream(self, text, history=None):
        """Streams response and yields full sentences for the TTS engine.
        
        Args:
            text: The user's latest message.
            history: Optional list of previous conversation turns.
                     Each item is {"role": "user"|"assistant", "content": "..."}.
        """
        print("[🧠 Thinking...]")
        
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Add conversation history for context
        if history:
            messages.extend(history)
        
        # Add the current user message
        messages.append({"role": "user", "content": text})
        
        stream = ollama.chat(
            model=self.model_name,
            messages=messages,
            stream=True,
            think=False,
        )

        buffer = ""
        inside_think = False
        
        for chunk in stream:
            content = chunk['message']['content']
            
            # Filter out <think>...</think> blocks (qwen3.5 thinking mode)
            if '<think>' in content:
                inside_think = True
            if inside_think:
                if '</think>' in content:
                    inside_think = False
                    # Keep only text after </think>
                    content = content.split('</think>', 1)[-1]
                    if not content:
                        continue
                else:
                    continue  # Skip everything inside <think> block
            
            buffer += content
            
            # If the chunk contains a punctuation mark, yield the sentence
            if any(punct in content for punct in ['.', '!', '?', '\n']):
                cleaned = buffer.strip()
                if cleaned:
                    yield cleaned
                    buffer = ""
                    
        # Yield any leftover text at the very end
        if buffer.strip():
            yield buffer.strip()