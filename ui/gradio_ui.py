"""
Streaming Gradio UI for Legal AI Agent
Shows agent's thought process (steps, tool calls, plans) in real-time
"""
import re
import os
from smolagents.agents import ActionStep, MultiStepAgent, PlanningStep, FinalAnswerStep
from smolagents.memory import MemoryStep


def _clean_text(text: str) -> str:
    """Remove problematic Unicode characters for Windows display."""
    if not text:
        return ""
    # Replace common problematic Unicode chars with ASCII equivalents
    replacements = {
        '\u2013': '-',   # en dash
        '\u2014': '--',  # em dash
        '\u2018': "'",   # left single quote
        '\u2019': "'",   # right single quote
        '\u201c': '"',   # left double quote
        '\u201d': '"',   # right double quote
        '\u2022': '*',   # bullet
        '\u2026': '...',  # ellipsis
        '\u00a0': ' ',   # non-breaking space
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text


class GradioUI:
    """Streaming Gradio UI that shows agent thoughts in real-time."""

    def __init__(self, agent: MultiStepAgent, file_upload_folder: str = None):
        self.agent = agent
        self.file_upload_folder = file_upload_folder

    def interact_with_agent(self, prompt, messages, session_state):
        """Stream agent steps to the chatbot in real-time."""
        import gradio as gr

        if "agent" not in session_state:
            session_state["agent"] = self.agent

        agent = session_state["agent"]

        # Add user message
        messages.append(gr.ChatMessage(role="user", content=prompt))
        yield messages

        try:
            # Run agent in streaming mode - yields steps as they happen
            for step_log in agent.run(task=prompt, stream=True, reset=False):
                # --- Planning Step ---
                if isinstance(step_log, PlanningStep):
                    plan_text = _clean_text(step_log.plan or "Planning...")
                    messages.append(
                        gr.ChatMessage(
                            role="assistant",
                            content="**Plan:**\n" + plan_text,
                            metadata={"title": "Agent Plan"}
                        )
                    )
                    yield messages

                # --- Action Step (tool call, code execution) ---
                elif isinstance(step_log, ActionStep):
                    step_num = step_log.step_number

                    # Show the model's thought/reasoning
                    if step_log.model_output:
                        thought = _clean_text(str(step_log.model_output))
                        messages.append(
                            gr.ChatMessage(
                                role="assistant",
                                content=thought,
                                metadata={"title": f"Step {step_num} - Thinking"}
                            )
                        )
                        yield messages

                    # Show tool calls
                    if step_log.tool_calls:
                        for tc in step_log.tool_calls:
                            tool_name = tc.name if hasattr(tc, 'name') else str(tc)
                            tool_args = tc.arguments if hasattr(tc, 'arguments') else ""
                            args_str = str(tool_args)[:300] if tool_args else ""
                            messages.append(
                                gr.ChatMessage(
                                    role="assistant",
                                    content=f"**Tool:** `{tool_name}`\n**Args:** {_clean_text(args_str)}",
                                    metadata={"title": f"Step {step_num} - Tool Call"}
                                )
                            )
                            yield messages

                    # Show observations/output
                    if step_log.observations:
                        obs = _clean_text(str(step_log.observations))
                        # Truncate very long observations
                        if len(obs) > 1500:
                            obs = obs[:1500] + "\n\n... (truncated)"
                        messages.append(
                            gr.ChatMessage(
                                role="assistant",
                                content=f"```\n{obs}\n```",
                                metadata={"title": f"Step {step_num} - Result"}
                            )
                        )
                        yield messages

                    # Show errors
                    if step_log.error:
                        err = _clean_text(str(step_log.error))
                        messages.append(
                            gr.ChatMessage(
                                role="assistant",
                                content=f"Error: {err}",
                                metadata={"title": f"Step {step_num} - Error"}
                            )
                        )
                        yield messages

                # --- Final Answer ---
                elif isinstance(step_log, FinalAnswerStep):
                    final = step_log.final_answer
                    if final is not None:
                        answer_text = _clean_text(str(final))
                        messages.append(
                            gr.ChatMessage(
                                role="assistant",
                                content=answer_text,
                            )
                        )
                        yield messages

        except Exception as e:
            error_msg = _clean_text(str(e))
            messages.append(
                gr.ChatMessage(role="assistant", content=f"Error: {error_msg}")
            )
            yield messages

    def launch(self, **kwargs):
        import gradio as gr

        with gr.Blocks(
            title="Legal AI Assistant",
            fill_height=True,
        ) as demo:
            session_state = gr.State({})

            gr.Markdown("# Legal AI Assistant")
            gr.Markdown("Describe your legal situation and get guidance on FIRs, complaints, RTI, and more.\n\n*Watch the agent think through your problem step-by-step below.*")

            chatbot = gr.Chatbot(
                height=550,
                autoscroll=True,
            )

            with gr.Row():
                msg = gr.Textbox(
                    label="Your Message",
                    placeholder="e.g., I bought a defective phone and want to file a consumer complaint...",
                    lines=2,
                    scale=8,
                )
                submit_btn = gr.Button("Send", variant="primary", scale=1)

            def respond(prompt, history, session_state):
                if not prompt.strip():
                    yield history, "", session_state
                    return
                for updated_history in self.interact_with_agent(prompt, history, session_state):
                    yield updated_history, "", session_state

            submit_btn.click(
                respond,
                [msg, chatbot, session_state],
                [chatbot, msg, session_state]
            )
            msg.submit(
                respond,
                [msg, chatbot, session_state],
                [chatbot, msg, session_state]
            )

        demo.launch(
            debug=False,
            share=kwargs.get("share", False),
            server_name="0.0.0.0",
            server_port=7860,
        )


__all__ = ["GradioUI"]