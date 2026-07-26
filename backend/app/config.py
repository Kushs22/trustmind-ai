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

    # Evidence-based confidence calibration (dissertation)
    enable_confidence_calibration: bool = True
    consistency_runs: int = 3
    # Slight temperature for multi-run consistency when primary temp is near 0
    consistency_temperature: float = 0.3

    # Grounding status thresholds (0–100 trust-signal scale)
    grounding_retrieval_quality_min: int = 55
    grounding_evidence_strength_min: int = 50

    # --- Multimodal input limits ---
    max_audio_duration_seconds: int = 180
    max_audio_size_mb: float = 15.0
    allowed_audio_types: str = "audio/webm,audio/mp4,audio/mpeg,audio/wav,audio/x-wav,audio/ogg"

    max_image_count: int = 5
    max_image_size_mb: float = 8.0
    max_image_pixels: int = 20_000_000
    max_image_dimension: int = 8192
    allowed_image_types: str = "image/jpeg,image/png,image/webp"

    max_pdf_count: int = 3
    max_pdf_size_mb: float = 15.0
    max_pdf_pages: int = 50
    allowed_pdf_types: str = "application/pdf"

    max_total_upload_mb: float = 40.0

    # Transcription / vision providers (never hardcode model names in services)
    transcription_provider: str = "openai"
    transcription_model: str = "whisper-1"
    transcription_timeout_seconds: float = 60.0
    image_processing_model: str = "gpt-4.1"
    image_processing_timeout_seconds: float = 60.0
    enable_scanned_pdf_ocr: bool = False

    # Upload rate limiting (requests per window per client key)
    upload_rate_limit_count: int = 30
    upload_rate_limit_window_seconds: int = 60

    # Development: allow logging truncated transcripts (off by default)
    enable_dev_content_logging: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def allowed_audio_type_list(self) -> list[str]:
        return [x.strip() for x in self.allowed_audio_types.split(",") if x.strip()]

    @property
    def allowed_image_type_list(self) -> list[str]:
        return [x.strip() for x in self.allowed_image_types.split(",") if x.strip()]

    @property
    def allowed_pdf_type_list(self) -> list[str]:
        return [x.strip() for x in self.allowed_pdf_types.split(",") if x.strip()]


settings = Settings()
