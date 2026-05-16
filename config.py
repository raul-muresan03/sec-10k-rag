from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    google_api_key: str = Field(..., alias="GOOGLE_API_KEY")
    pinecone_api_key: str = Field(..., alias="PINECONE_API_KEY")
    pinecone_index_name: str = Field("sec-rag-index", alias="PINECONE_INDEX_NAME")
    sec_api_email: str = Field("", alias="SEC_API_EMAIL")

    embedding_model: str = Field("models/gemini-embedding-001", alias="EMBEDDING_MODEL")
    embedding_dimension: int = Field(768, alias="EMBEDDING_DIMENSION")
    llm_model: str = Field("gemini-3-flash-preview", alias="LLM_MODEL")

    backend_url: str = Field("http://localhost:8000", alias="BACKEND_URL")


settings = Settings()
