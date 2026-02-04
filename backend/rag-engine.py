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
            "You are a Senior Financial Analyst expert in SEC filings (10-K, 10-Q). "
            "Use the provided context, which includes financial tables in Markdown format, to answer the user's question. "
            "\n\n"
            "Rules:\n"
            "1. If the data is in a table, analyze columns and rows carefully to extract the correct value for the requested year.\n"
            "2. Always mention the fiscal year and currency (e.g., 'in millions').\n"
            "3. Format all financial figures in **bold** for readability.\n"
            "4. If the user asks for a calculation (e.g., growth rate), show your logic step-by-step.\n"
            "5. If you cannot find the exact answer in the context, strictly state: 'Information not available in the provided context'. Do not hallucinate numbers.\n"
            "6. Use a professional, concise tone suitable for an investment memo.\n"
            "\n\n"
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
            answer = response["answer"]
        
            sources = []
            if "context" in response:
                for doc in response["context"]:
                    page = doc.metadata.get('page', 'N/A')
                    section = doc.metadata.get('section', 'Unknown Section')
                    source_str = f"Page {page} ({section})"
                    
                    if source_str not in sources:
                        sources.append(source_str)
            
            return {
                "answer": answer,
                "sources": sources
            }

        except Exception as e:
            return {
                "answer": f"Error processing request: {str(e)}", 
                "sources": []
            }

if __name__ == "__main__":
    engine = RAGEngine()
    print(engine.ask("What is the company's revenue vs profit?"))