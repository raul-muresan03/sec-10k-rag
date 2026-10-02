import argparse
from datetime import date, datetime, timezone
import json
import time

import etl_pipeline
from etl_pipeline.ingest import EARLIEST_EDGAR_YEAR
from etl_pipeline.pipeline import ensure_index
from etl_pipeline.rag_engine import get_llm_response
from etl_pipeline.model_config import ModelConfig
from etl_pipeline.vector_store import get_most_similar_chunks

DEFAULT_MODEL = "gemma3:1b"
DEFAULT_TOP_N = 5
QUERY_LOG_FILENAME = "query_log.jsonl"


def _append_query_log(record: dict) -> None:
    log_path = etl_pipeline.DATA_DIR / QUERY_LOG_FILENAME
    try:
        with log_path.open("a") as log:
            log.write(json.dumps(record) + "\n")
    except OSError as error:
        print(f"Warning: query could not be logged: {error}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask a question about the indexed SEC filing.")
    parser.add_argument("question", help="Question to answer from the filing")
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N, help="Number of chunks to retrieve")
    parser.add_argument("--model", help="Generation model for the selected RAG_RUNTIME profile")
    parser.add_argument("--ticker", required=True, help="Stock ticker of the company to query")
    parser.add_argument("--year", type=int, required=True, help="SEC filing year")
    args = parser.parse_args()

    ticker = args.ticker.strip().upper()
    if not ticker:
        parser.error("ticker cannot be empty")

    current_year = date.today().year
    if not EARLIEST_EDGAR_YEAR <= args.year <= current_year:
        parser.error(f"year must be between {EARLIEST_EDGAR_YEAR} and {current_year}")

    try:
        config = ModelConfig.from_env(model=args.model)
        config.require_local_indexes()
        args.model = config.model
        index_path = ensure_index(ticker, args.year)
    except (RuntimeError, ValueError) as error:
        parser.error(str(error))

    print(f"Vector store: {index_path}", flush=True)

    print(f"Retrieving the top {args.top_n} relevant chunks...", flush=True)
    retrieval_start = time.perf_counter()
    try:
        chunks = get_most_similar_chunks(args.question, args.top_n, index_path)
    except (OSError, ValueError, RuntimeError) as error:
        parser.error(str(error))
    retrieval_end = time.perf_counter()
    retrieval_seconds = retrieval_end - retrieval_start
    print(f"Retrieved {len(chunks)} chunks in {retrieval_seconds:.2f}s.", flush=True)

    print(f"Generating an answer with {args.model}...", flush=True)
    generation_start = time.perf_counter()
    try:
        answer, ollama_metrics = get_llm_response(args.question, chunks, args.model)
    except (ValueError, RuntimeError) as error:
        parser.error(str(error))
    generation_end = time.perf_counter()
    generation_seconds = generation_end - generation_start
    print(f"Generation completed in {generation_seconds:.2f}s.")

    _append_query_log(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ticker": ticker,
            "filing_year": args.year,
            "question": args.question,
            "answer": answer,
            "model": args.model,
            "chunks": [{"score": score, "text": text} for score, text in chunks],
            "latency_seconds": {
                "retrieval": retrieval_seconds,
                "generation": generation_seconds,
                "total": retrieval_seconds + generation_seconds,
            },
            "ollama": ollama_metrics,
        }
    )

    print("\nAnswer:")
    print(answer)


if __name__ == "__main__":
    main()
