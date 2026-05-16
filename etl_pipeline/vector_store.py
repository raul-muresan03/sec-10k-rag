import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from langchain_ollama import OllamaEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document
from pinecone import Pinecone, ServerlessSpec
from config import settings

def get_embedding_model():
    return OllamaEmbeddings(
        model=settings.embedding_model,
        base_url=settings.ollama_base_url
    )

def verify_and_create_index(index_name: str):
    pc = Pinecone(api_key=settings.pinecone_api_key)
    existing_indexes = [index.name for index in pc.list_indexes()]

    if index_name not in existing_indexes:
        print(f"Index '{index_name}' not found. Creating it...")
        try:
            pc.create_index(
                name=index_name,
                dimension=settings.embedding_dimension,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
            print(f"Index '{index_name}' created successfully.")
        except Exception as e:
            print(f"Error creating index: {e}")
            return False
    else:
        print(f"Index '{index_name}' exists.")

    try:
        index = pc.Index(index_name)
        stats = index.describe_index_stats()
        print(f"Status Pinecone ('{index_name}'): {stats['total_vector_count']} total vectors.")
        return True
    except Exception as e:
        print(f"Error connecting to index: {e}")
        return False

def delete_all_vectors(index_name=None):
    index_name = index_name or settings.pinecone_index_name
    pc = Pinecone(api_key=settings.pinecone_api_key)

    if index_name not in [index.name for index in pc.list_indexes()]:
        print(f"Index '{index_name}' not found. Nothing to delete.")
        return

    index = pc.Index(index_name)
    print(f"Deleting all vectors from index '{index_name}'...")
    try:
        index.delete(delete_all=True)
        print("Successfully deleted all vectors.")
    except Exception as e:
        print(f"An error occurred while deleting vectors: {e}")

def upload_chunks_to_pinecone(chunks, index_name=None):
    index_name = index_name or settings.pinecone_index_name
    if not chunks:
        print("No chunks to upload.")
        return None

    if not verify_and_create_index(index_name):
        return None

    print(f"Upserting {len(chunks)} chunks to Pinecone index '{index_name}'...")

    documents = []
    ids = []
    for chunk in chunks:
        if isinstance(chunk, dict) and "id" in chunk and "text" in chunk:
            ids.append(chunk['id'])
            meta = chunk.copy()
            text_content = meta.pop("text")
            meta.pop("id")
            doc = Document(page_content=text_content, metadata=meta)
            documents.append(doc)

    if not documents:
        print("No valid documents with IDs were created from chunks.")
        return None

    embeddings = get_embedding_model()
    batch_size = 100

    try:
        vector_store = PineconeVectorStore(index_name=index_name, embedding=embeddings)
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i : i + batch_size]
            batch_ids = ids[i : i + batch_size]
            print(f"Uploading batch {i // batch_size + 1}...")
            vector_store.add_documents(documents=batch_docs, ids=batch_ids)

        print(f"Upsert completed.")
        return vector_store
    except Exception as e:
        print(f"CRITICAL ERROR during upload: {e}")
        return None
