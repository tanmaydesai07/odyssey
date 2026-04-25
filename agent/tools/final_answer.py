from smolagents.tools import Tool


class FinalAnswerTool(Tool):
    name = "final_answer"
    description = "Provides the final answer to the user. Use this when the task is complete."
    inputs = {"answer": {"type": "any", "description": "The final answer to present to the user"}}
    output_type = "any"

    def forward(self, answer: any) -> any:
        return answer