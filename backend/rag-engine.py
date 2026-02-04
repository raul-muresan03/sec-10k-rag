import os
from dotenv import load_dotenv

from langchain.chat_models import init_chat_model
from langchain.embeddings import init_embeddings

from langchain_pinecone import PineconeVectorStore

from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain

from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

class RAGEngine:
    def __init__(self, index_name=os.getenv("PINECONE_INDEX_NAME")):
        self.index_name = index_name
        
        self.embeddings = init_embeddings(
            "google_genai:text-embedding-004"
        )
        
        self.vector_store = PineconeVectorStore(
            index_name=self.index_name, 
            embedding=self.embeddings
        )
        
        self.llm = init_chat_model(
            "gemini-2.5-flash", 
            model_provider="google_genai", 
            temperature=0
        )

        self.rag_chain = self._create_chain()
    
    def _create_chain(self):
        system_prompt = (
            "You are a Senior Financial Analyst expert in SEC filings. "
            "Context: {context}"
        )

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
        ])

        question_answer_chain = create_stuff_documents_chain(self.llm, prompt_template)
        
        chain = create_retrieval_chain(
            self.vector_store.as_retriever(search_kwargs={"k": 5}),
            question_answer_chain
        )
        
        return chain

    def ask(self, query: str):
        print(f"Thinking about: '{query}'...")
        try:
            response = self.rag_chain.invoke({"input": query})
            return response["answer"]
        except Exception as e:
            return f"Error: {str(e)}"

if __name__ == "__main__":
    engine = RAGEngine()
    print(engine.ask("What is the company's revenue vs profit?"))