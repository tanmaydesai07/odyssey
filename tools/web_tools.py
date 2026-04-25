from smolagents.tools import Tool


class WebSearchTool(Tool):
    name = "web_search"
    description = "Performs a web search using DuckDuckGo and returns top results with titles and snippets."
    inputs = {
        "query": {"type": "string", "description": "The search query to perform."}
    }
    output_type = "string"

    def __init__(self, max_results: int = 10, **kwargs):
        super().__init__(**kwargs)
        self.max_results = max_results

    def forward(self, query: str) -> str:
        from duckduckgo_search import DDGS
        ddgs = DDGS()
        results = ddgs.text(query, max_results=self.max_results)
        
        if not results:
            return "No results found for your query."
        
        formatted = []
        for r in results:
            formatted.append(f"**{r['title']}**\n{r['body']}\n{r['href']}")
        
        return "## Search Results\n\n\n\n".join(formatted)


class VisitWebpageTool(Tool):
    name = "visit_webpage"
    description = "Visits a webpage at the given URL and reads its content as markdown."
    inputs = {
        "url": {"type": "string", "description": "The URL of the webpage to visit."}
    }
    output_type = "string"

    def forward(self, url: str) -> str:
        import requests
        from markdownify import markdownify
        
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            markdown_content = markdownify(response.text).strip()
            # Truncate if too long
            if len(markdown_content) > 10000:
                markdown_content = markdown_content[:10000] + "\n\n[Content truncated...]"
            return markdown_content
        except Exception as e:
            return f"Error fetching webpage: {str(e)}"
