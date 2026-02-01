from langchain_community.tools import DuckDuckGoSearchResults

# Initialize the tool
# We set num_results=10 to give the LLM plenty of context
duckduckgo_search_tool = DuckDuckGoSearchResults(num_results=10, handle_tool_error=True)