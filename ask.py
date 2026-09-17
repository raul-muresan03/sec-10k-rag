import argparse
from time import perf_counter

import etl_pipeline
from etl_pipeline.rag_engine import get_llm_response
from etl_pipeline.vector_store import get_most_similar_chunks


DEFAULT_MODEL = "gemma3:1b"
DEFAULT_TOP_N = 5


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask a question about the indexed SEC filing.")
    parser.add_argument("question", help="Question to answer from the filing")
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N, help="Number of chunks to retrieve")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model used to generate the answer")
    args = parser.parse_args()

    vector_store_path = etl_pipeline.DATA_DIR / "all_chunks_embeddings.json"
    if not vector_store_path.is_file():
        parser.error(f"vector store not found: {vector_store_path}")

    print(f"Vector store: {vector_store_path}", flush=True)
    print(f"Retrieving the top {args.top_n} relevant chunks...", flush=True)
    retrieval_started = perf_counter()
    chunks = get_most_similar_chunks(args.question, args.top_n)
    retrieval_seconds = perf_counter() - retrieval_started
    print(f"Retrieved {len(chunks)} chunks in {retrieval_seconds:.2f}s.", flush=True)

    print(f"Generating an answer with {args.model}...", flush=True)
    generation_started = perf_counter()
    answer = get_llm_response(args.question, chunks, args.model)
    generation_seconds = perf_counter() - generation_started

    print(f"Generation completed in {generation_seconds:.2f}s.")
    print("\nAnswer:")
    print(answer)


if __name__ == "__main__":
    main()
