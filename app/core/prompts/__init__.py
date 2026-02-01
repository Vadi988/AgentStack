import os
from datetime import datetime
from app.core.config import settings

def load_system_prompt(**kwargs) -> str:
    """
    Loads the system prompt from the markdown file and injects dynamic variables.
    """
    prompt_path = os.path.join(os.path.dirname(__file__), "system.md")
    
    with open(prompt_path, "r") as f:
        return f.read().format(
            agent_name=settings.PROJECT_NAME + " Agent",
            current_date_and_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            **kwargs, # Inject dynamic variables like 'long_term_memory'
        )