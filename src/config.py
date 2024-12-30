import os

class Settings:
    """Application settings and environment variables."""
    
    # API Keys (still using environment variables)
    CONGRESS_API_KEY: str = os.getenv("CONGRESS_API_KEY", "default_congress_api_key")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "default_openai_api_key")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "default_supabase_url")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "default_supabase_key")
    
    # Application Settings
    APP_NAME: str = "Congress Bill Analysis Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # API Settings
    API_PREFIX: str = "/api/v1"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Database Settings
    DB_MAX_CONNECTIONS: int = 20
    DB_TIMEOUT: int = 30
    
    # Congress.gov API Settings
    CONGRESS_API_BASE_URL: str = "https://api.congress.gov/v3"
    CONGRESS_UPDATE_INTERVAL: int = 24  # hours
    
    # OpenAI Settings
    OPENAI_MODEL: str = "gpt-4-1106-preview"
    OPENAI_MAX_TOKENS: int = 1000
    OPENAI_TEMPERATURE: float = 0.7
    
    # Processing Settings
    BATCH_SIZE: int = 100
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 60  # seconds

# Create global settings instance
settings = Settings()

def get_settings() -> Settings:
    """Get application settings."""
    return settings 