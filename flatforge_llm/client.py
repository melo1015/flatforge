"""Optional LLM integration helper."""
import os
def get_api_key() -> str | None:
    """Read credentials from environment; never commit secrets."""
    return os.getenv("OPENAI_API_KEY")
