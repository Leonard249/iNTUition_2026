from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Ollama Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5vl:7b"  # Updated to vision model!
    
    # FasterWhisper Configuration
    WHISPER_MODEL: str = "base"
    WHISPER_DEVICE: str = "cpu"  # Change to "cuda" if you have NVIDIA GPU
    WHISPER_COMPUTE_TYPE: str = "float32"
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: list = ["*"]
    
    # API Security
    API_KEY: Optional[str] = None
    
    class Config:
        env_file = ".env"

settings = Settings()