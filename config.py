import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    google_api_key: str = Field("", alias="GOOGLE_API_KEY")
    pinecone_api_key: str = Field(..., alias="PINECONE_API_KEY")
    pinecone_index_name: str = Field("sec-rag-tool", alias="PINECONE_INDEX_NAME")
    openai_api_key: str = Field("", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field("", alias="ANTHROPIC_API_KEY")
    sec_api_email: str = Field("", alias="SEC_API_EMAIL")

    embedding_model: str = Field("nomic-embed-text", alias="EMBEDDING_MODEL")
    embedding_dimension: int = Field(768, alias="EMBEDDING_DIMENSION")
    llm_model: str = Field("gemini-3.1-flash", alias="LLM_MODEL")

    ollama_base_url: str = Field("http://localhost:11434", alias="OLLAMA_BASE_URL")
    backend_url: str = Field("http://localhost:8000", alias="BACKEND_URL")

settings = Settings()

os.environ["GOOGLE_API_KEY"] = settings.google_api_key
os.environ["PINECONE_API_KEY"] = settings.pinecone_api_key
os.environ["OPENAI_API_KEY"] = settings.openai_api_key
os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key
