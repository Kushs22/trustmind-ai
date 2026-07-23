from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,https://trustmind-ai.vercel.app"
    )

    secret_key: str = "dev-only-change-me-in-production"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    database_url: str = "sqlite:///./trustmind.db"

    # Analyse backend: "auto" uses LLM when OPENAI_API_KEY is set, else keywords
    analyse_backend: str = "auto"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1"
    openai_temperature: float = 0.2

    # Mode A (false) = standalone LLM | Mode B (true) = hybrid RAG
    use_rag: bool = False
    rag_top_k: int = 5

    # Trust / ethics controls
    confidence_threshold: float = 0.75
    enable_abstention: bool = True
    enable_source_display: bool = True
    enable_support_resources: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
