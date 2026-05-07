import os
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

def get_embedding_model():
    """
    Initializes and returns the GoogleGenerativeAIEmbeddings model using the API key from environment variables.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables.")

    return GoogleGenerativeAIEmbeddings(
        model=os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001"),
        google_api_key=api_key,
        output_dimensionality=int(os.getenv("EMBEDDING_DIMENSION", 768))
    )

def verify_and_create_index(index_name: str):
    """
    Verifies if the specified index exists. If not, creates a new Serverless index.
    """

    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        raise ValueError("PINECONE_API_KEY not found in environment variables.")

    pc = Pinecone(api_key=api_key)

    existing_indexes = [index.name for index in pc.list_indexes()]

    if index_name not in existing_indexes:
        print(f"Index '{index_name}' not found. Creating it...")
        try:
            pc.create_index(
                name=index_name,
                dimension=int(os.getenv("EMBEDDING_DIMENSION", 768)),
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

def delete_all_vectors(index_name=os.getenv("PINECONE_INDEX_NAME")):
    """
    Deletes all vectors from the specified Pinecone index.
    """
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        raise ValueError("PINECONE_API_KEY not found in environment variables.")

    pc = Pinecone(api_key=api_key)

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

def upload_chunks_to_pinecone(chunks, index_name=os.getenv("PINECONE_INDEX_NAME")):
    """
    Uploads or updates the provided chunks to Pinecone using stable IDs to prevent duplicates.
    This function handles the entire process: verifying the index, preparing documents with IDs,
    and upserting them to Pinecone.
    """
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
        else:
            print(f"Skipping a chunk because it's malformed or missing an 'id': {chunk}")
            continue

    if not documents:
        print("No valid documents with IDs were created from chunks.")
        return None

    embeddings = get_embedding_model()

    try:
        vector_store = PineconeVectorStore(index_name=index_name, embedding=embeddings)
        vector_store.add_documents(
            documents=documents,
            ids=ids
        )

        print(f"Upsert completed.")
        return vector_store

    except Exception as e:
        print(f"CRITICAL ERROR during upload: {e}")
        return None