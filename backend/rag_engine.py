from typing import List, Any, Optional
from backend.llm_factory import LLMFactory
from langchain_ollama import OllamaEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from pydantic import Field
from config import settings
from backend.token_tracker import TokenTrackerCallback, log_query_usage

SYSTEM_PROMPT = (
    "You are a Senior Financial Analyst expert in SEC filings (10-K, 10-Q). "
    "Use the provided context, which includes financial tables in Markdown format, to answer the user's question. "
    "\n\n"
    "Rules:\n"
    "1. If the data is in a table, analyze columns and rows carefully to extract the correct value.\n"
    "2. Always mention the fiscal year and currency (e.g., 'in millions').\n"
    "3. Format all financial figures in **bold** for readability.\n"
    "4. If the user asks for a calculation (e.g., growth rate), show your logic step-by-step.\n"
    "5. If you cannot find the exact answer in the context, strictly state: 'Information not available in the provided context'. Do not hallucinate numbers.\n"
    "6. Use a professional, concise tone suitable for an investment memo.\n"
    "\n\n"
    "Context: {context}"
)

COMPARISON_SYSTEM_PROMPT = (
    "You are a Senior Financial Analyst expert in SEC filings (10-K, 10-Q). "
    "You are given financial data from two different fiscal years for the same company. "
    "Your task is to COMPARE the same metric across both years.\n\n"
    "Rules:\n"
    "1. Extract the requested metric from each year's data.\n"
    "2. Calculate the year-over-year change (absolute difference and percentage).\n"
    "3. Always mention the fiscal years and currency (e.g., 'in millions').\n"
    "4. Format all financial figures in **bold** for readability.\n"
    "5. Present the comparison clearly: Year1 → Year2 → Change.\n"
    "6. If data for both years is not available, state: 'Comparative data not available for one or both years'.\n"
    "7. Use a professional, concise tone suitable for an investment memo.\n\n"
    "Context: {context}"
)

class PineconeScoreRetriever(BaseRetriever):
    vector_store: PineconeVectorStore = Field(...)
    search_kwargs: dict = Field(default_factory=lambda: {"k": 5})

    def _get_relevant_documents(self, query: str) -> List[Document]:
        docs_with_scores = self.vector_store.similarity_search_with_score(
            query, **self.search_kwargs
        )
        for doc, score in docs_with_scores:
            doc.metadata["score"] = score
        return [doc for doc, _ in docs_with_scores]

class RAGEngine:
    def __init__(self, index_name=None, k=5):
        self.index_name = index_name or settings.pinecone_index_name
        self.k = k

        self.embeddings = OllamaEmbeddings(
            model=settings.embedding_model,
            base_url=settings.ollama_base_url
        )

        self.vector_store = PineconeVectorStore(
            index_name=self.index_name,
            embedding=self.embeddings
        )

    def _calculate_confidence(self, retrieved_docs: list[Document]) -> float:
        if not retrieved_docs:
            return 0.0

        scores = [d.metadata.get('score') for d in retrieved_docs if d.metadata.get('score') is not None]
        if not scores:
            return 0.0

        avg = sum(scores) / len(scores)
        spread = max(scores) - min(scores)

        SIM_MIN, SIM_MAX = 0.55, 0.95
        retrieval = max(0.0, min(1.0, (avg - SIM_MIN) / (SIM_MAX - SIM_MIN)))

        coverage = len(scores) / self.k

        sections = set(d.metadata.get('section', '') for d in retrieved_docs if d.metadata.get('section'))
        diversity = min(len(sections) / 3.0, 1.0)

        consistency = max(0.0, 1.0 - spread * 1.5)

        confidence = (
            0.35 * retrieval +
            0.25 * coverage +
            0.20 * diversity +
            0.20 * consistency
        )

        return round(min(max(confidence, 0.0), 1.0), 4)

    def _comparison_query(self, search_kwargs: dict[str, Any], compare_year: Optional[str], llm: BaseChatModel, query: str):
        retriever1 = PineconeScoreRetriever(vector_store=self.vector_store, search_kwargs=search_kwargs)
        filter2 = dict(search_kwargs.get("filter", {}))
        filter2["year"] = compare_year
        retriever2 = PineconeScoreRetriever(vector_store=self.vector_store, search_kwargs={"k": self.k, "filter": filter2})
        prompt_template = ChatPromptTemplate.from_messages([("system", COMPARISON_SYSTEM_PROMPT), ("human", "{input}"), ])
        question_answer_chain = create_stuff_documents_chain(llm, prompt_template)

        cb = TokenTrackerCallback()
        docs1 = retriever1._get_relevant_documents(query)
        docs2 = retriever2._get_relevant_documents(query)
        retrieved_docs = docs1 + docs2

        answer = question_answer_chain.invoke({"input": query, "context": retrieved_docs}, config={"callbacks": [cb]})

        return answer, retrieved_docs, cb

    def _single_year_query(self, search_kwargs: dict[str, Any], llm: BaseChatModel, query: str):
        retriever = PineconeScoreRetriever(vector_store=self.vector_store, search_kwargs=search_kwargs)
        prompt_template = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("human", "{input}"),])
        question_answer_chain = create_stuff_documents_chain(llm, prompt_template)
        chain = create_retrieval_chain(retriever, question_answer_chain)
        cb = TokenTrackerCallback()
        response = chain.invoke({"input": query}, config={"callbacks": [cb]})
        answer = response["answer"]
        retrieved_docs = response.get("context", [])

        return answer, retrieved_docs, cb

    @staticmethod
    def _build_sources(retrieved_docs: list[Document]) -> list[str]:
        sources = []
        for doc in retrieved_docs:
            page = doc.metadata.get('page', 'N/A')
            section = doc.metadata.get('section', 'Unknown Section')
            ticker = doc.metadata.get('ticker', 'Unknown Ticker')
            source_str = f"{ticker} - Page {page} ({section})"
            if source_str not in sources:
                sources.append(source_str)

        return sources

    def _build_search_kwargs(self, namespace: str) -> dict[str, Any]:
        search_kwargs = {"k": self.k}
        filter_dict = {}
        if namespace and namespace != "default":
            filter_dict["ticker"] = namespace

        if filter_dict:
            search_kwargs["filter"] = filter_dict

        return search_kwargs

    def ask(self, query: str, namespace: str = "default", compare_year: Optional[str] = None, provider: str = "google", model_name: str = "gemini-3.1-flash"):
        try:
            search_kwargs = self._build_search_kwargs(namespace)
            llm = LLMFactory.get_llm(provider, model_name)

            if compare_year:
                answer, retrieved_docs, cb = self._comparison_query(search_kwargs, compare_year, llm, query)
            else:
                answer, retrieved_docs, cb = self._single_year_query(search_kwargs, llm, query)

            sources = self._iterate_sources(retrieved_docs)

            confidence_score = self._calculate_confidence(retrieved_docs)
            usage = log_query_usage(query, namespace, cb.input_tokens, cb.output_tokens, provider, model_name)

            return {
                "answer": answer,
                "sources": sources,
                "usage": usage,
                "confidence_score": confidence_score
            }

        except Exception as e:
            return {
                "answer": f"Error processing request: {str(e)}",
                "sources": [],
                "usage": None,
                "confidence_score": 0.0
            }

if __name__ == "__main__":
    engine = RAGEngine()
    print(engine.ask("What is the company's revenue vs profit?"))
