from backend.llm_factory import LLMFactory
from langchain_ollama import OllamaEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
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

class RAGEngine:
    def __init__(self, index_name=None):
        self.index_name = index_name or settings.pinecone_index_name

        self.embeddings = OllamaEmbeddings(
            model=settings.embedding_model,
            base_url=settings.ollama_base_url
        )

        self.vector_store = PineconeVectorStore(
            index_name=self.index_name,
            embedding=self.embeddings
        )

    def _calculate_confidence(self, retrieved_docs, query: str) -> float:
        if not retrieved_docs:
            return 0.0

        scores = []
        for doc in retrieved_docs:
            score = doc.metadata.get('score', None)
            if score is not None:
                scores.append(score)

        if not scores:
            return 0.0

        avg_score = sum(scores) / len(scores)
        min_score = min(scores)
        coverage_ratio = len(scores) / 5.0  # top-k = 5

        confidence = avg_score * 0.6 + (1.0 - min_score) * 0.2 + min(coverage_ratio, 1.0) * 0.2
        return round(min(max(confidence, 0.0), 1.0), 4)

    def ask(self, query: str, namespace: str = "default", provider: str = "google", model_name: str = "gemini-3.1-flash"):
        print(f"Thinking about: '{query}' with namespace='{namespace}', model='{provider}:{model_name}'...")
        try:
            search_kwargs = {"k": 5}
            filter_dict = {}
            if namespace and namespace != "default":
                filter_dict["ticker"] = namespace

            if filter_dict:
                search_kwargs["filter"] = filter_dict

            retriever = self.vector_store.as_retriever(search_kwargs=search_kwargs)

            prompt_template = ChatPromptTemplate.from_messages([
                ("system", SYSTEM_PROMPT),
                ("human", "{input}"),
            ])

            llm = LLMFactory.get_llm(provider, model_name)
            question_answer_chain = create_stuff_documents_chain(llm, prompt_template)
            chain = create_retrieval_chain(retriever, question_answer_chain)
            cb = TokenTrackerCallback()
            response = chain.invoke({"input": query}, config={"callbacks": [cb]})
            answer = response["answer"]

            sources = []
            retrieved_docs = []
            if "context" in response:
                retrieved_docs = response["context"]
                for doc in retrieved_docs:
                    page = doc.metadata.get('page', 'N/A')
                    section = doc.metadata.get('section', 'Unknown Section')
                    ticker = doc.metadata.get('ticker', 'Unknown Ticker')
                    source_str = f"{ticker} - Page {page} ({section})"

                    if source_str not in sources:
                        sources.append(source_str)

            confidence_score = self._calculate_confidence(retrieved_docs, query)
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
