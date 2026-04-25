"""
Streaming Gradio UI for Legal AI Agent
Shows agent's thought process (steps, tool calls, plans) in real-time.
Persists sessions to disk so the agent never forgets across refreshes/restarts.
"""
import re
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from smolagents.agents import ActionStep, MultiStepAgent, PlanningStep, FinalAnswerStep
from smolagents.memory import MemoryStep

import session_store as ss

# Observability — optional, no-op if keys not set
try:
    import observability as _obs
except Exception:
    _obs = None


def _clean_text(text: str) -> str:
    """Remove problematic Unicode characters for Windows display."""
    if not text:
        return ""
    replacements = {
        '\u2013': '-',
        '\u2014': '--',
        '\u2018': "'",
        '\u2019': "'",
        '\u201c': '"',
        '\u201d': '"',
        '\u2022': '*',
        '\u2026': '...',
        '\u00a0': ' ',
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text


class GradioUI:
    """Streaming Gradio UI with persistent session memory."""

    def __init__(self, agent: MultiStepAgent, file_upload_folder: str = None):
        self.agent = agent
        self.file_upload_folder = file_upload_folder

    # ------------------------------------------------------------------
    # Session helpers
    # ------------------------------------------------------------------

    def _init_session(self, session_state: dict) -> str:
        """
        Ensure session_state has a valid session_id and the agent memory
        is restored from disk if this is a reconnect.
        Returns the session_id.
        """
        if "session_id" not in session_state:
            # Brand new browser session — create a fresh ID
            sid = ss.new_session_id()
            session_state["session_id"] = sid
            ss.create_session(sid)
            print(f"[GradioUI] New session: {sid}")
        else:
            sid = session_state["session_id"]

        # Restore agent memory from disk if not already done this tab session
        if not session_state.get("memory_restored"):
            restored = ss.restore_agent_memory(sid, self.agent)
            session_state["memory_restored"] = True
            if restored:
                print(f"[GradioUI] Restored memory for session {sid}")

        return sid

    def _load_messages(self, session_state: dict) -> list:
        """Load persisted chat messages for the current session."""
        import gradio as gr
        sid = session_state.get("session_id")
        if not sid:
            return []
        data = ss.load_session(sid)
        if not data or not data.get("messages"):
            return []
        # Reconstruct gr.ChatMessage objects
        msgs = []
        for m in data["messages"]:
            msgs.append(gr.ChatMessage(
                role=m.get("role", "user"),
                content=m.get("content", ""),
                metadata=m.get("metadata", {}),
            ))
        return msgs

    # ------------------------------------------------------------------
    # Main interaction loop
    # ------------------------------------------------------------------

    def interact_with_agent(self, prompt, messages, session_state):
        """Stream agent steps to the chatbot in real-time, saving after each turn."""
        import gradio as gr

        sid = self._init_session(session_state)

        if "agent" not in session_state:
            session_state["agent"] = self.agent

        agent = session_state["agent"]

        # Start a Langfuse trace for this user turn
        trace = None
        if _obs:
            trace = _obs.start_trace(
                name="legal_query",
                session_id=sid,
                user_query=prompt,
                metadata={"session_id": sid},
            )
            # Attach trace to model so LLM calls can reference it
            if hasattr(agent, "model"):
                agent.model._current_trace = trace

        # Add user message
        messages.append(gr.ChatMessage(role="user", content=prompt))
        yield messages, sid

        try:
            for step_log in agent.run(task=prompt, stream=True, reset=False):

                # --- Planning Step ---
                if isinstance(step_log, PlanningStep):
                    plan_text = _clean_text(step_log.plan or "Planning...")
                    messages.append(
                        gr.ChatMessage(
                            role="assistant",
                            content="**Plan:**\n" + plan_text,
                            metadata={"title": "Agent Plan"},
                        )
                    )
                    yield messages, sid

                # --- Action Step ---
                elif isinstance(step_log, ActionStep):
                    step_num = step_log.step_number

                    if step_log.model_output:
                        thought = _clean_text(str(step_log.model_output))
                        messages.append(
                            gr.ChatMessage(
                                role="assistant",
                                content=thought,
                                metadata={"title": f"Step {step_num} - Thinking"},
                            )
                        )
                        yield messages, sid

                    if step_log.tool_calls:
                        for tc in step_log.tool_calls:
                            tool_name = tc.name if hasattr(tc, "name") else str(tc)
                            tool_args = tc.arguments if hasattr(tc, "arguments") else ""
                            args_str = str(tool_args)[:300] if tool_args else ""
                            messages.append(
                                gr.ChatMessage(
                                    role="assistant",
                                    content=f"**Tool:** `{tool_name}`\n**Args:** {_clean_text(args_str)}",
                                    metadata={"title": f"Step {step_num} - Tool Call"},
                                )
                            )
                            yield messages, sid

                    if step_log.observations:
                        obs = _clean_text(str(step_log.observations))
                        if len(obs) > 1500:
                            obs = obs[:1500] + "\n\n... (truncated)"
                        messages.append(
                            gr.ChatMessage(
                                role="assistant",
                                content=f"```\n{obs}\n```",
                                metadata={"title": f"Step {step_num} - Result"},
                            )
                        )
                        yield messages, sid

                    if step_log.error:
                        err = _clean_text(str(step_log.error))
                        messages.append(
                            gr.ChatMessage(
                                role="assistant",
                                content=f"Error: {err}",
                                metadata={"title": f"Step {step_num} - Error"},
                            )
                        )
                        yield messages, sid

                # --- Final Answer ---
                elif isinstance(step_log, FinalAnswerStep):
                    # smolagents renamed .final_answer to .output in newer versions
                    final = (
                        getattr(step_log, "final_answer", None)
                        or getattr(step_log, "output", None)
                        or getattr(step_log, "answer", None)
                    )
                    if final is not None:
                        answer_text = _clean_text(str(final))
                        messages.append(
                            gr.ChatMessage(role="assistant", content=answer_text)
                        )
                        yield messages, sid

        except Exception as e:
            error_msg = _clean_text(str(e))
            messages.append(
                gr.ChatMessage(role="assistant", content=f"Error: {error_msg}")
            )
            yield messages, sid

        # --- Persist after every turn ---
        try:
            ss.save_messages(sid, messages)
            ss.save_agent_memory(sid, agent)
        except Exception as e:
            print(f"[GradioUI] Warning: could not persist session {sid}: {e}")

        # End Langfuse trace
        if _obs and trace:
            final_text = next(
                (m.content for m in reversed(messages) if getattr(m, "role", "") == "assistant" and not getattr(m, "metadata", {})),
                None,
            )
            _obs.end_trace(trace, output=final_text)
            _obs.flush()

    # ------------------------------------------------------------------
    # Launch
    # ------------------------------------------------------------------

    def launch(self, **kwargs):
        import gradio as gr

        with gr.Blocks(title="Legal AI Assistant", fill_height=True) as demo:

            session_state = gr.State({})

            gr.Markdown("# Legal AI Assistant")
            gr.Markdown(
                "Describe your legal situation and get guidance on FIRs, complaints, RTI, and more.\n\n"
                "*Your session is saved automatically — you can close and reopen this page and the conversation will still be here.*"
            )

            with gr.Row():
                with gr.Column(scale=8):
                    chatbot = gr.Chatbot(height=520, autoscroll=True)
                with gr.Column(scale=2, min_width=180):
                    gr.Markdown("### Session")
                    session_id_box = gr.Textbox(
                        label="Session ID",
                        placeholder="auto-assigned",
                        interactive=True,
                        info="Paste a previous ID to resume that session",
                    )
                    resume_btn = gr.Button("Resume Session", size="sm")
                    new_btn = gr.Button("New Session", size="sm", variant="stop")
                    gr.Markdown(
                        "<small>Copy your Session ID to resume later from any device.</small>"
                    )

            with gr.Row():
                msg = gr.Textbox(
                    label="Your Message",
                    placeholder="e.g., I bought a defective phone and want to file a consumer complaint...",
                    lines=2,
                    scale=8,
                )
                submit_btn = gr.Button("Send", variant="primary", scale=1)

            # ---- on page load: restore session if one exists in state ----
            def on_load(session_state):
                """Called when the page loads. Restores previous messages if any."""
                sid = session_state.get("session_id", "")
                if not sid:
                    sid = ss.new_session_id()
                    session_state["session_id"] = sid
                    ss.create_session(sid)
                msgs = self._load_messages(session_state)
                return msgs, sid, session_state

            demo.load(
                on_load,
                inputs=[session_state],
                outputs=[chatbot, session_id_box, session_state],
            )

            # ---- resume a session by pasting its ID ----
            def resume_session(sid_input, session_state):
                sid_input = sid_input.strip()
                if not sid_input:
                    return [], "No session ID entered.", session_state

                data = ss.load_session(sid_input)
                if data is None:
                    return [], f"Session '{sid_input}' not found.", session_state

                # Reset agent memory so we can inject the saved one
                self.agent.memory.steps.clear()
                session_state["session_id"] = sid_input
                session_state["memory_restored"] = False  # force re-restore

                # Restore agent memory
                ss.restore_agent_memory(sid_input, self.agent)
                session_state["memory_restored"] = True

                msgs = self._load_messages(session_state)
                return msgs, sid_input, session_state

            resume_btn.click(
                resume_session,
                inputs=[session_id_box, session_state],
                outputs=[chatbot, session_id_box, session_state],
            )

            # ---- start a brand new session ----
            def new_session(session_state):
                sid = ss.new_session_id()
                ss.create_session(sid)
                session_state["session_id"] = sid
                session_state["memory_restored"] = True
                # Clear agent memory for the new session
                self.agent.memory.steps.clear()
                return [], sid, session_state

            new_btn.click(
                new_session,
                inputs=[session_state],
                outputs=[chatbot, session_id_box, session_state],
            )

            # ---- main send handler ----
            def respond(prompt, history, session_state):
                if not prompt.strip():
                    sid = session_state.get("session_id", "")
                    yield history, "", sid, session_state
                    return
                for updated_history, sid in self.interact_with_agent(prompt, history, session_state):
                    yield updated_history, "", sid, session_state

            submit_btn.click(
                respond,
                inputs=[msg, chatbot, session_state],
                outputs=[chatbot, msg, session_id_box, session_state],
            )
            msg.submit(
                respond,
                inputs=[msg, chatbot, session_state],
                outputs=[chatbot, msg, session_id_box, session_state],
            )

        demo.launch(
            debug=False,
            share=kwargs.get("share", False),
            server_name="0.0.0.0",
            server_port=7860,
        )


__all__ = ["GradioUI"]
