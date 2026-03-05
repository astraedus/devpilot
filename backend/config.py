from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Azure AI Foundry
    azure_project_connection_string: str = ""
    azure_model_deployment: str = "gpt-4o"

    # Groq (fallback — free tier, OpenAI-compatible, llama-3.1-70b)
    groq_api_key: str = ""

    # Gemini (secondary fallback — free tier, OpenAI-compatible)
    gemini_api_key: str = ""

    # GitHub
    github_token: str = ""
    github_webhook_secret: str = ""

    # App
    port: int = 8000
    log_level: str = "INFO"

    class Config:
        env_file = ".env"


settings = Settings()
