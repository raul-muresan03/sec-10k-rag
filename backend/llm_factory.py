from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama
from config import settings

class LLMFactory:
    @staticmethod
    def get_llm(provider: str, model_name: str, temperature: float = 0):
        provider = provider.lower().strip()

        if provider == "google":
            return ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temperature,
                google_api_key=settings.google_api_key
            )
        elif provider == "openai":
            return ChatOpenAI(
                model=model_name,
                temperature=temperature,
                openai_api_key=settings.openai_api_key
            )
        elif provider == "anthropic":
            return ChatAnthropic(
                model=model_name,
                temperature=temperature,
                api_key=settings.anthropic_api_key
            )
        elif provider == "ollama":
            return ChatOllama(
                model=model_name,
                temperature=temperature,
                base_url=settings.ollama_base_url
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")
